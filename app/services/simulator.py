from __future__ import annotations

import asyncio
import random
from collections import deque
from datetime import datetime, timezone
from decimal import Decimal
from typing import Deque
from uuid import uuid4

from app.services.categorizer import categorize_message

SAMPLE_MERCHANTS = [
    "Amazon",
    "FreshMart Supermarket",
    "Uber",
    "City Fuel Station",
    "Netflix",
    "BookMyShow",
    "Aqua Water Bill",
    "PowerGrid Electricity",
    "Swiggy",
    "MediCare Pharmacy",
    "Flipkart",
    "ATM Withdrawal",
]

SCENARIO_AMOUNT_BOUNDS: dict[str, tuple[int, int]] = {
    "balanced": (50, 1000),
    "inflation": (180, 2800),
    "subscription-heavy": (80, 1400),
}

DEFAULT_SCENARIO_ID = "balanced"


class SmsSimulator:
    def __init__(self, interval_seconds: float = 2.0, history_size: int = 100) -> None:
        self.interval_seconds = interval_seconds
        self._running = False
        self._task: asyncio.Task | None = None
        self._subscribers: set[asyncio.Queue] = set()
        self._history: Deque[dict] = deque(maxlen=history_size)
        self._scenario_id = DEFAULT_SCENARIO_ID

    @property
    def running(self) -> bool:
        return self._running

    def history(self) -> list[dict]:
        return list(self._history)

    @property
    def scenario_id(self) -> str:
        return self._scenario_id

    def set_scenario(self, scenario_id: str) -> None:
        if scenario_id in SCENARIO_AMOUNT_BOUNDS:
            self._scenario_id = scenario_id

    async def start(self) -> None:
        if self._running:
            return
        self._running = True
        self._task = asyncio.create_task(self._run())

    async def stop(self) -> None:
        if not self._running:
            return
        self._running = False
        if self._task is not None:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

    async def subscribe(self) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue(maxsize=200)
        self._subscribers.add(queue)
        return queue

    def unsubscribe(self, queue: asyncio.Queue) -> None:
        self._subscribers.discard(queue)

    async def _run(self) -> None:
        while self._running:
            message = self._generate_message()
            self._history.appendleft(message)
            await self._broadcast(message)
            await asyncio.sleep(self.interval_seconds)

    async def _broadcast(self, message: dict) -> None:
        dead_queues: list[asyncio.Queue] = []
        for queue in self._subscribers:
            try:
                queue.put_nowait(message)
            except asyncio.QueueFull:
                dead_queues.append(queue)

        for queue in dead_queues:
            self._subscribers.discard(queue)

    async def inject_messages(self, messages: list[dict]) -> int:
        injected = 0

        for message in messages:
            self._history.appendleft(message)
            await self._broadcast(message)
            injected += 1

        return injected

    def _generate_message(self) -> dict:
        min_amount, max_amount = SCENARIO_AMOUNT_BOUNDS.get(
            self._scenario_id,
            SCENARIO_AMOUNT_BOUNDS[DEFAULT_SCENARIO_ID],
        )
        merchant = random.choice(SAMPLE_MERCHANTS)
        amount = Decimal(random.randint(min_amount, max_amount)) + Decimal(random.random()).quantize(
            Decimal("0.01")
        )
        account_tail = random.randint(1000, 9999)
        txn_id = uuid4().hex[:10].upper()

        sms_text = (
            f"INR {amount} debited from A/C XX{account_tail} on card at {merchant}. "
            f"Txn ID {txn_id}."
        )

        category = categorize_message(sms_text)
        return {
            "id": uuid4().hex,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "message": sms_text,
            "amount": float(amount),
            "merchant": merchant,
            "bucket": category,
            "account_last4": str(account_tail),
            "transaction_id": txn_id,
        }
