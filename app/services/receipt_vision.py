from __future__ import annotations

import asyncio
import base64
import json
import os
import re
from collections import defaultdict, deque
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any
from urllib import error, request

try:
    from groq import Groq
except ImportError:  # pragma: no cover - optional at runtime until installed
    Groq = None

GROQ_API_URL = "https://api.groq.com/openai/v1/chat/completions"


class ReceiptAnalysisError(RuntimeError):
    pass


@dataclass
class ReceiptSnapshot:
    seen_at: str
    total_price: float
    unit_cost: float | None


def _safe_float(value: Any, *, fallback: float = 0.0) -> float:
    if value is None:
        return fallback

    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return fallback

    if parsed < 0:
        return fallback

    return parsed


def _extract_json_block(content: str) -> str:
    fenced_match = re.search(r"```(?:json)?\s*(\{[\s\S]*\})\s*```", content)
    if fenced_match:
        return fenced_match.group(1)

    brace_match = re.search(r"\{[\s\S]*\}", content)
    if brace_match:
        return brace_match.group(0)

    raise ReceiptAnalysisError("Groq response did not include valid JSON.")


def _normalize_item_key(name: str) -> str:
    return re.sub(r"\s+", " ", re.sub(r"[^a-z0-9\s]", " ", name.lower())).strip()


class GroqVisionClient:
    def __init__(self) -> None:
        self.api_key = os.getenv("GROQ_API_KEY", "").strip()
        self.model = os.getenv(
            "GROQ_VISION_MODEL",
            "meta-llama/llama-4-scout-17b-16e-instruct",
        )
        self._sdk_client = Groq(api_key=self.api_key) if Groq and self.api_key else None

    @property
    def configured(self) -> bool:
        return bool(self.api_key)

    def _build_prompt(self) -> str:
        return (
            "You are a receipt parser. Extract every purchasable line item from the bill image "
            "and return JSON only. Use this schema exactly: "
            "{"
            '"merchant": string|null, '
            '"currency": string, '
            '"bill_date": string|null, '
            '"items": ['
            "{"
            '"name": string, '
            '"quantity": number, '
            '"total_price": number, '
            '"weight_grams": number|null, '
            '"volume_ml": number|null, '
            '"category": string, '
            '"confidence": number '
            "}"
            "]"
            "}. "
            "Rules: quantity must be >= 1, confidence between 0 and 1, and only include actual bought items. "
            "category is mandatory and must never be null/none/empty. "
            "Choose from exactly one of: Groceries, Food & Dining, Transport, Shopping, Bills & Utilities, Health, Entertainment, Miscellaneous. "
            "Ignore taxes, subtotal, total, discounts, tendered cash, and change rows. "
            "If no weight/volume is visible, return null for those fields."
        )

    def _build_category_prompt(self, item_names: list[str]) -> str:
        return (
            "Classify each item name into one spending category and return JSON only. "
            "Use this schema exactly: {\"items\":[{\"name\":string,\"category\":string}]}. "
            "Rules: category is mandatory, never null, and must be one of: "
            "Groceries, Food & Dining, Transport, Shopping, Bills & Utilities, Health, Entertainment, Miscellaneous. "
            f"Item names: {json.dumps(item_names)}"
        )

    def _extract_content_from_completion(self, completion: Any) -> str:
        choices = getattr(completion, "choices", None)
        if not choices:
            raise ReceiptAnalysisError("Groq response had no choices.")

        message = getattr(choices[0], "message", None)
        content = getattr(message, "content", None)
        if not content:
            raise ReceiptAnalysisError("Groq response had empty message content.")

        if isinstance(content, str):
            return content

        # Some SDK/tooling modes may return multipart content blocks.
        if isinstance(content, list):
            text_parts = [
                str(block.get("text", ""))
                for block in content
                if isinstance(block, dict) and block.get("type") == "text"
            ]
            joined = "\n".join(part for part in text_parts if part)
            if joined:
                return joined

        raise ReceiptAnalysisError("Groq response content format was not recognized.")

    def _analyze_image_via_sdk(self, image_data_url: str) -> dict[str, Any]:
        if not self._sdk_client:
            raise ReceiptAnalysisError("Groq SDK client is unavailable.")

        completion = self._sdk_client.chat.completions.create(
            model=self.model,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {
                    "role": "system",
                    "content": "You extract structured fields from shopping receipts.",
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": self._build_prompt()},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": image_data_url,
                            },
                        },
                    ],
                },
            ],
        )

        content = self._extract_content_from_completion(completion)
        json_blob = _extract_json_block(content)
        return json.loads(json_blob)

    def _analyze_image_sync(self, image_bytes: bytes, mime_type: str) -> dict[str, Any]:
        if not self.configured:
            raise ReceiptAnalysisError("GROQ_API_KEY is not configured.")

        image_base64 = base64.b64encode(image_bytes).decode("ascii")
        image_data_url = f"data:{mime_type};base64,{image_base64}"

        if self._sdk_client is not None:
            try:
                return self._analyze_image_via_sdk(image_data_url)
            except Exception as exc:  # noqa: BLE001
                # Fall back to raw HTTP below only when SDK path fails.
                sdk_error = str(exc)
        else:
            sdk_error = "Groq SDK is not installed."

        payload = {
            "model": self.model,
            "temperature": 0,
            "response_format": {"type": "json_object"},
            "messages": [
                {
                    "role": "system",
                    "content": "You extract structured fields from shopping receipts.",
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": self._build_prompt()},
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": image_data_url,
                            },
                        },
                    ],
                },
            ],
        }

        req = request.Request(
            GROQ_API_URL,
            method="POST",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "User-Agent": "finance-receipt-analyzer/1.0",
            },
        )

        try:
            with request.urlopen(req, timeout=45) as response:
                raw = response.read().decode("utf-8")
        except error.HTTPError as exc:
            details = exc.read().decode("utf-8", errors="replace") if exc.fp else ""
            raise ReceiptAnalysisError(
                f"Groq API HTTP {exc.code}. {details[:500]} SDK fallback error: {sdk_error}"
            ) from exc
        except error.URLError as exc:
            raise ReceiptAnalysisError(f"Groq API request failed: {exc.reason}") from exc

        try:
            parsed = json.loads(raw)
            content = parsed["choices"][0]["message"]["content"]
            json_blob = _extract_json_block(content)
            return json.loads(json_blob)
        except (KeyError, IndexError, json.JSONDecodeError) as exc:
            raise ReceiptAnalysisError("Unable to parse Groq JSON response.") from exc

    def _categorize_items_sync(self, item_names: list[str]) -> dict[str, str]:
        if not self.configured:
            return {}

        if not item_names:
            return {}

        message_payload = [
            {
                "role": "system",
                "content": "You classify grocery receipt item names into spending categories.",
            },
            {
                "role": "user",
                "content": self._build_category_prompt(item_names),
            },
        ]

        try:
            if self._sdk_client is not None:
                completion = self._sdk_client.chat.completions.create(
                    model=self.model,
                    temperature=0,
                    response_format={"type": "json_object"},
                    messages=message_payload,
                )
                content = self._extract_content_from_completion(completion)
                parsed = json.loads(_extract_json_block(content))
            else:
                payload = {
                    "model": self.model,
                    "temperature": 0,
                    "response_format": {"type": "json_object"},
                    "messages": message_payload,
                }
                req = request.Request(
                    GROQ_API_URL,
                    method="POST",
                    data=json.dumps(payload).encode("utf-8"),
                    headers={
                        "Authorization": f"Bearer {self.api_key}",
                        "Content-Type": "application/json",
                        "User-Agent": "finance-receipt-analyzer/1.0",
                    },
                )
                with request.urlopen(req, timeout=30) as response:
                    raw = response.read().decode("utf-8")
                response_payload = json.loads(raw)
                content = response_payload["choices"][0]["message"]["content"]
                parsed = json.loads(_extract_json_block(content))
        except Exception:  # noqa: BLE001
            return {}

        category_map: dict[str, str] = {}
        for entry in parsed.get("items", []):
            name = str(entry.get("name", "")).strip()
            category = str(entry.get("category", "")).strip()
            if not name:
                continue
            category_map[_normalize_item_key(name)] = category or "Miscellaneous"

        return category_map

    async def analyze_image(self, image_bytes: bytes, mime_type: str) -> dict[str, Any]:
        return await asyncio.to_thread(self._analyze_image_sync, image_bytes, mime_type)

    async def categorize_items(self, item_names: list[str]) -> dict[str, str]:
        return await asyncio.to_thread(self._categorize_items_sync, item_names)


class ReceiptAnalyzer:
    def __init__(self, history_size: int = 20) -> None:
        self.client = GroqVisionClient()
        self._history: dict[str, deque[ReceiptSnapshot]] = defaultdict(
            lambda: deque(maxlen=history_size)
        )

    @property
    def configured(self) -> bool:
        return self.client.configured

    @property
    def model(self) -> str:
        return self.client.model

    async def analyze_receipt(self, image_bytes: bytes, mime_type: str) -> dict[str, Any]:
        raw_payload = await self.client.analyze_image(image_bytes, mime_type)
        now_iso = datetime.now(timezone.utc).isoformat()

        unresolved_category_names: list[str] = []
        unresolved_keys: set[str] = set()
        normalized_items: list[dict[str, Any]] = []
        for raw_item in raw_payload.get("items", []):
            name = str(raw_item.get("name", "")).strip()
            if not name:
                continue

            quantity = max(_safe_float(raw_item.get("quantity"), fallback=1.0), 1.0)
            total_price = _safe_float(raw_item.get("total_price"))
            if total_price <= 0:
                continue

            weight_grams = _safe_float(raw_item.get("weight_grams"), fallback=0.0)
            volume_ml = _safe_float(raw_item.get("volume_ml"), fallback=0.0)
            measurable_amount = weight_grams if weight_grams > 0 else volume_ml if volume_ml > 0 else 0

            cost_per_item = total_price / quantity if quantity > 0 else total_price
            cost_per_unit = (
                total_price / measurable_amount if measurable_amount > 0 else None
            )

            category = str(raw_item.get("category", "")).strip()
            if category.lower() in {"", "none", "null", "n/a", "na"}:
                category = ""
                normalized_name = _normalize_item_key(name)
                if normalized_name and normalized_name not in unresolved_keys:
                    unresolved_keys.add(normalized_name)
                    unresolved_category_names.append(name)

            confidence = _safe_float(raw_item.get("confidence"), fallback=0.7)
            confidence = max(0.0, min(confidence, 1.0))

            normalized_items.append(
                {
                    "name": name,
                    "quantity": round(quantity, 3),
                    "total_price": round(total_price, 2),
                    "weight_grams": round(weight_grams, 3) if weight_grams > 0 else None,
                    "volume_ml": round(volume_ml, 3) if volume_ml > 0 else None,
                    "category": category or "Miscellaneous",
                    "confidence": round(confidence, 3),
                    "cost_per_item": round(cost_per_item, 2),
                    "cost_per_unit": round(cost_per_unit, 6) if cost_per_unit else None,
                    "unit_label": (
                        "per gram" if weight_grams > 0 else "per ml" if volume_ml > 0 else None
                    ),
                }
            )

        if unresolved_category_names:
            groq_categories = await self.client.categorize_items(unresolved_category_names)
            for item in normalized_items:
                if item["category"] != "Miscellaneous":
                    continue

                category = groq_categories.get(_normalize_item_key(item["name"]))
                if category:
                    item["category"] = category

        price_increases: list[dict[str, Any]] = []
        better_value_items: list[dict[str, Any]] = []

        for item in normalized_items:
            item_key = _normalize_item_key(item["name"])
            if not item_key:
                continue

            prev_snapshot = self._history[item_key][-1] if self._history[item_key] else None
            if prev_snapshot and item["total_price"] > prev_snapshot.total_price:
                delta = item["total_price"] - prev_snapshot.total_price
                percent = (
                    (delta / prev_snapshot.total_price) * 100
                    if prev_snapshot.total_price > 0
                    else 0
                )
                price_increases.append(
                    {
                        "name": item["name"],
                        "previous_price": round(prev_snapshot.total_price, 2),
                        "current_price": item["total_price"],
                        "absolute_increase": round(delta, 2),
                        "percent_increase": round(percent, 2),
                    }
                )

            if item["cost_per_unit"]:
                historical_units = [
                    snap.unit_cost for snap in self._history[item_key] if snap.unit_cost is not None
                ]
                previous_best = min(historical_units) if historical_units else None

                if previous_best is None or item["cost_per_unit"] < previous_best:
                    savings_percent = (
                        ((previous_best - item["cost_per_unit"]) / previous_best) * 100
                        if previous_best and previous_best > 0
                        else 0
                    )
                    better_value_items.append(
                        {
                            "name": item["name"],
                            "cost_per_unit": item["cost_per_unit"],
                            "unit_label": item["unit_label"],
                            "previous_best_cost_per_unit": round(previous_best, 6)
                            if previous_best is not None
                            else None,
                            "savings_vs_previous_best_percent": round(savings_percent, 2),
                        }
                    )

            self._history[item_key].append(
                ReceiptSnapshot(
                    seen_at=now_iso,
                    total_price=item["total_price"],
                    unit_cost=item["cost_per_unit"],
                )
            )

        best_unit_cost_items = sorted(
            [item for item in normalized_items if item["cost_per_unit"] is not None],
            key=lambda item: item["cost_per_unit"],
        )[:5]

        return {
            "merchant": raw_payload.get("merchant"),
            "currency": raw_payload.get("currency") or "INR",
            "bill_date": raw_payload.get("bill_date"),
            "items": normalized_items,
            "insights": {
                "price_increases": sorted(
                    price_increases,
                    key=lambda item: item["absolute_increase"],
                    reverse=True,
                ),
                "better_value_items": sorted(
                    better_value_items,
                    key=lambda item: item["savings_vs_previous_best_percent"],
                    reverse=True,
                ),
                "lowest_unit_cost_items": [
                    {
                        "name": item["name"],
                        "cost_per_unit": item["cost_per_unit"],
                        "unit_label": item["unit_label"],
                    }
                    for item in best_unit_cost_items
                ],
            },
            "analyzed_at": now_iso,
        }