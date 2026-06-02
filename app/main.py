from __future__ import annotations

from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Literal
import os
from uuid import uuid4

from fastapi import FastAPI, File, HTTPException, UploadFile, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, Response
from pydantic import BaseModel, Field

from app.services.receipt_vision import ReceiptAnalysisError, ReceiptAnalyzer
from app.services.report_builder import ReportTransaction, build_monthly_spend_pdf
from app.services.simulator import SmsSimulator


def _load_env_file(path: Path) -> None:
    if not path.exists():
        return

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip().lstrip("\ufeff")
        value = value.strip().strip('"').strip("'")
        if key:
            os.environ.setdefault(key, value)


_PROJECT_ROOT = Path(__file__).resolve().parents[1]
_load_env_file(_PROJECT_ROOT / ".env")
_load_env_file(Path(__file__).resolve().parent / ".env")

simulator = SmsSimulator(interval_seconds=2.0)
receipt_analyzer = ReceiptAnalyzer()


@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        yield
    finally:
        await simulator.stop()


app = FastAPI(
    title="Finance SMS Simulator Backend",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SimulationStatusResponse(BaseModel):
    running: bool
    interval_seconds: float


class SimulationControlRequest(BaseModel):
    state: Literal["start", "stop"] = Field(
        description="Start or stop simulated incoming SMS messages"
    )


class ReceiptFeatureStatusResponse(BaseModel):
    configured: bool
    model: str


class DemoScenario(BaseModel):
    id: str
    name: str
    description: str
    running: bool = False


class DemoScenarioListResponse(BaseModel):
    scenarios: list[DemoScenario]
    activeScenarioId: str


class ActivateScenarioRequest(BaseModel):
    scenarioId: str


class ReportTransactionItem(BaseModel):
    date: str
    description: str
    amount: float
    direction: Literal["in", "out"]
    category: str = "Other"
    bucket: str = "Misc"


class MonthlySpendReportRequest(BaseModel):
    month: str = Field(description="Target month in YYYY-MM format")
    transactions: list[ReportTransactionItem] = Field(default_factory=list)
    currency: str = "INR"


class RecurringSeedResponse(BaseModel):
    created: int
    message: str


DEMO_SCENARIOS: list[DemoScenario] = [
    DemoScenario(
        id="balanced",
        name="Balanced Household",
        description="General spending mix across groceries, utilities, and lifestyle.",
    ),
    DemoScenario(
        id="inflation",
        name="Inflation Pressure",
        description="Higher grocery and essentials movement to test anomaly and trend views.",
    ),
    DemoScenario(
        id="subscription-heavy",
        name="Subscription Heavy",
        description="Recurring digital services to stress recurring transaction analysis.",
    ),
]

active_demo_scenario_id = DEMO_SCENARIOS[0].id


CONTROL_UI = """
<!doctype html>
<html lang="en">
    <head>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1" />
        <title>Finance Backend Demo Console</title>
        <style>
            :root {
                font-family: "Segoe UI", Arial, sans-serif;
                color-scheme: light;
                --ink: #112035;
                --muted: #516070;
                --line: #d8e2ec;
                --surface: #ffffff;
                --bg-a: #f8fcff;
                --bg-b: #e6f1fb;
                --ok: #147a42;
                --warn: #8a5a00;
                --danger: #a22d3c;
                --brand: #005ba8;
            }

            * {
                box-sizing: border-box;
            }

            body {
                margin: 0;
                min-height: 100vh;
                color: var(--ink);
                background: radial-gradient(circle at 5% 0%, #fef9e8 0%, transparent 42%),
                    radial-gradient(circle at 95% 10%, #dbedff 0%, transparent 38%),
                    linear-gradient(165deg, var(--bg-a), var(--bg-b));
            }

            .page {
                width: min(1200px, 95vw);
                margin: 20px auto 32px;
                display: grid;
                gap: 14px;
            }

            .hero {
                background: linear-gradient(130deg, #0a2340, #16417a);
                border-radius: 18px;
                color: #f8fcff;
                padding: 20px;
                border: 1px solid #1f4f8d;
                box-shadow: 0 14px 30px rgba(6, 23, 48, 0.22);
            }

            .hero h1 {
                margin: 0;
                font-size: clamp(22px, 4vw, 31px);
                letter-spacing: 0.2px;
            }

            .hero p {
                margin: 8px 0 0;
                color: #d5e8ff;
                max-width: 760px;
                font-size: 14px;
            }

            .hero-grid {
                margin-top: 12px;
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(170px, 1fr));
                gap: 10px;
            }

            .hero-tile {
                padding: 10px 12px;
                border-radius: 12px;
                background: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.18);
            }

            .hero-tile b {
                display: block;
                font-size: 11px;
                text-transform: uppercase;
                letter-spacing: 0.65px;
                color: #cae4ff;
            }

            .hero-tile span {
                display: block;
                margin-top: 4px;
                font-size: 14px;
                font-weight: 700;
                color: #fff;
            }

            .layout {
                display: grid;
                grid-template-columns: 1.2fr 1fr;
                gap: 14px;
            }

            .stack {
                display: grid;
                gap: 14px;
            }

            .card {
                border-radius: 14px;
                border: 1px solid var(--line);
                background: var(--surface);
                box-shadow: 0 10px 24px rgba(14, 34, 53, 0.08);
                padding: 15px;
            }

            .card h2 {
                margin: 0;
                font-size: 15px;
            }

            .subtext {
                margin: 6px 0 0;
                color: var(--muted);
                font-size: 12px;
            }

            .row {
                margin-top: 12px;
                display: flex;
                flex-wrap: wrap;
                gap: 8px;
                align-items: center;
            }

            button,
            .link-btn {
                border: 0;
                border-radius: 9px;
                padding: 8px 12px;
                font-size: 12px;
                font-weight: 700;
                cursor: pointer;
                text-decoration: none;
                display: inline-flex;
                align-items: center;
                justify-content: center;
            }

            .btn-brand {
                color: white;
                background: linear-gradient(120deg, #0067b8, #1d7ccb);
            }

            .btn-danger {
                color: white;
                background: linear-gradient(120deg, #cf3046, #dd4f62);
            }

            .btn-plain {
                color: #1e3c5d;
                background: #ebf5ff;
                border: 1px solid #c5ddf3;
            }

            .pill {
                border-radius: 999px;
                padding: 4px 9px;
                font-size: 11px;
                font-weight: 700;
            }

            .pill-ok {
                color: #116337;
                background: #dcf9e8;
            }

            .pill-warn {
                color: #815708;
                background: #fff2cf;
            }

            .pill-muted {
                color: #33516f;
                background: #e8f0f8;
            }

            .demo-steps {
                margin: 10px 0 0;
                padding: 0;
                list-style: none;
                display: grid;
                gap: 7px;
            }

            .demo-steps li {
                border: 1px dashed #cadef0;
                border-radius: 10px;
                padding: 8px 10px;
                font-size: 12px;
                color: #2d4864;
                background: #f6fbff;
            }

            .scenario-list {
                margin-top: 10px;
                display: grid;
                gap: 7px;
            }

            .scenario-btn {
                width: 100%;
                text-align: left;
                border: 1px solid #d2deea;
                border-radius: 10px;
                background: white;
                padding: 10px;
            }

            .scenario-btn.active {
                border-color: #6ab7ff;
                background: #ebf6ff;
            }

            .scenario-btn strong {
                display: block;
                font-size: 13px;
                color: #163a5a;
            }

            .scenario-btn span {
                display: block;
                margin-top: 3px;
                font-size: 11px;
                color: #55708b;
            }

            .messages {
                margin: 10px 0 0;
                padding: 0;
                list-style: none;
                max-height: 360px;
                overflow: auto;
                border-top: 1px solid #e1ebf4;
            }

            .messages li {
                font-size: 12px;
                padding: 8px 0;
                border-bottom: 1px solid #edf3f8;
            }

            .bucket {
                display: inline-block;
                margin-left: 6px;
                border-radius: 999px;
                padding: 1px 7px;
                font-size: 10px;
                font-weight: 700;
                background: #e7f3ff;
                color: #0e5396;
            }

            .api-links {
                margin-top: 10px;
                display: flex;
                flex-wrap: wrap;
                gap: 8px;
            }

            .status-grid {
                margin-top: 10px;
                display: grid;
                grid-template-columns: repeat(2, minmax(0, 1fr));
                gap: 8px;
            }

            .status-box {
                border: 1px solid #d5e2ef;
                border-radius: 10px;
                padding: 9px;
                background: #f8fbff;
            }

            .status-box b {
                display: block;
                font-size: 11px;
                text-transform: uppercase;
                color: #4a6784;
                letter-spacing: 0.55px;
            }

            .status-box span {
                display: block;
                margin-top: 3px;
                font-size: 12px;
                font-weight: 700;
                color: #173754;
            }

            input[type="file"] {
                display: block;
                width: 100%;
                border: 1px solid #cfd9e2;
                background: #f8fbfe;
                border-radius: 10px;
                padding: 8px;
                font-size: 12px;
            }

            table {
                width: 100%;
                border-collapse: collapse;
                margin-top: 8px;
                font-size: 12px;
            }

            th,
            td {
                text-align: left;
                border-bottom: 1px solid #ebf1f6;
                padding: 7px 6px;
                vertical-align: top;
            }

            th {
                font-size: 11px;
                text-transform: uppercase;
                color: #4a6784;
                letter-spacing: 0.45px;
                background: #f3f8fd;
            }

            .error {
                margin-top: 8px;
                font-size: 12px;
                color: var(--danger);
                font-weight: 700;
            }

            .hint {
                margin-top: 8px;
                font-size: 12px;
                color: #40607d;
            }

            .section-label {
                margin-top: 9px;
                font-size: 11px;
                font-weight: 700;
                text-transform: uppercase;
                letter-spacing: 0.65px;
                color: #4d6a87;
            }

            .list {
                margin: 7px 0 0;
                padding-left: 18px;
                color: #304a66;
                font-size: 12px;
            }

            @media (max-width: 940px) {
                .layout {
                    grid-template-columns: 1fr;
                }

                .page {
                    width: min(1120px, 96vw);
                }
            }
        </style>
    </head>
    <body>
        <div class="page">

            <section class="layout">
                <div class="stack">
                    <section class="card">
                        <h2>API Resources</h2>
                        <div class="api-links">
                            <a class="link-btn btn-plain" href="/docs" target="_blank" rel="noreferrer">Open Swagger</a>
                            <a class="link-btn btn-plain" href="/openapi.json" target="_blank" rel="noreferrer">OpenAPI JSON</a>
                        </div>
                    </section>

                    <section class="card">
                        <h2>Simulation Control</h2>
                        <p class="subtext">Manage live SMS generation and scenario state.</p>
                        <div class="row">
                            <button class="btn-brand" id="startBtn">Start Simulation</button>
                            <button class="btn-danger" id="stopBtn">Stop Simulation</button>
                            <button class="btn-plain" id="refreshBtn">Refresh Status</button>
                            <button class="btn-plain" id="seedRecurringBtn">Seed Recurring Demo</button>
                            <span class="pill pill-muted" id="simulationStatus">Checking...</span>
                        </div>
                        <p class="hint" id="seedRecurringStatus"></p>

                        <p class="section-label">Demo Scenarios</p>
                        <div class="scenario-list" id="scenarioList"></div>
                        <p id="scenarioError" class="error" style="display: none"></p>
                    </section>

                    <section class="card">
                        <h2>Live Message Stream</h2>
                        <p class="subtext">WebSocket stream from <code>/ws/messages</code> with rolling history.</p>
                        <div class="row">
                            <button class="btn-plain" id="loadHistoryBtn">Reload Message History</button>
                            <span class="pill pill-muted" id="messageCount">0 shown</span>
                        </div>
                        <ul class="messages" id="messages"></ul>
                    </section>
                </div>

                <div class="stack">
                    <section class="card">
                        <h2>Backend Status</h2>
                        <p class="subtext">Quick checks for runtime and vision model configuration.</p>
                        <div class="status-grid">
                            <div class="status-box">
                                <b>Health</b>
                                <span id="healthStatus">Checking...</span>
                            </div>
                            <div class="status-box">
                                <b>Receipt Feature</b>
                                <span id="receiptStatus">Checking...</span>
                            </div>
                            <div class="status-box">
                                <b>Vision Model</b>
                                <span id="visionModel">Checking...</span>
                            </div>
                            <div class="status-box">
                                <b>Interval</b>
                                <span id="intervalStatus">Checking...</span>
                            </div>
                        </div>
                    </section>

                    <section class="card">
                        <h2>Receipt Intelligence</h2>
                        <p class="subtext">Upload an image bill to demo OCR-style extraction and cost insights.</p>
                        <div class="row">
                            <input id="receiptFile" type="file" accept="image/*" />
                            <button class="btn-brand" id="analyzeReceiptBtn">Analyze Receipt</button>
                        </div>
                        <p id="receiptError" class="error" style="display: none"></p>
                        <div id="receiptOutput" style="display: none">
                            <p class="hint" id="receiptSummary"></p>

                            <p class="section-label">Line Items</p>
                            <div style="max-height: 270px; overflow: auto; border: 1px solid #e1ebf4; border-radius: 10px">
                                <table>
                                    <thead>
                                        <tr>
                                            <th>Item</th>
                                            <th>Category</th>
                                            <th>Qty</th>
                                            <th>Total</th>
                                            <th>Per Item</th>
                                            <th>Per Unit</th>
                                        </tr>
                                    </thead>
                                    <tbody id="receiptItems"></tbody>
                                </table>
                            </div>

                            <p class="section-label">Insights</p>
                            <ul class="list" id="receiptInsights"></ul>
                        </div>
                    </section>
                </div>
            </section>
        </div>

        <script>
            const simulationStatus = document.getElementById("simulationStatus");
            const intervalStatus = document.getElementById("intervalStatus");
            const heroSimulator = document.getElementById("heroSimulator");
            const heroScenario = document.getElementById("heroScenario");
            const heroVision = document.getElementById("heroVision");
            const heroSocket = document.getElementById("heroSocket");
            const healthStatus = document.getElementById("healthStatus");
            const receiptStatus = document.getElementById("receiptStatus");
            const visionModel = document.getElementById("visionModel");

            const scenarioList = document.getElementById("scenarioList");
            const scenarioError = document.getElementById("scenarioError");
            const seedRecurringStatus = document.getElementById("seedRecurringStatus");

            const messages = document.getElementById("messages");
            const messageCount = document.getElementById("messageCount");

            const receiptFile = document.getElementById("receiptFile");
            const analyzeReceiptBtn = document.getElementById("analyzeReceiptBtn");
            const receiptError = document.getElementById("receiptError");
            const receiptOutput = document.getElementById("receiptOutput");
            const receiptSummary = document.getElementById("receiptSummary");
            const receiptItems = document.getElementById("receiptItems");
            const receiptInsights = document.getElementById("receiptInsights");

            function setText(node, value) {
                if (node) {
                    node.textContent = value;
                }
            }

            function safeText(value) {
                if (value === null || value === undefined) {
                    return "";
                }
                return String(value)
                    .replace(/&/g, "&amp;")
                    .replace(/</g, "&lt;")
                    .replace(/>/g, "&gt;")
                    .replace(/\"/g, "&quot;")
                    .replace(/'/g, "&#039;");
            }

            function updateMessageCount() {
                messageCount.textContent = `${messages.children.length} shown`;
            }

            function renderMessage(item) {
                if (!item) {
                    return;
                }

                const when = safeText(item.timestamp || "unknown-time");
                const text = safeText(item.message || "");
                const bucket = safeText(item.bucket || "Miscellaneous");

                const li = document.createElement("li");
                li.innerHTML = `${when}<br/><span>${text}</span> <span class="bucket">${bucket}</span>`;
                messages.prepend(li);

                while (messages.children.length > 40) {
                    messages.removeChild(messages.lastChild);
                }

                updateMessageCount();
            }

            async function apiJson(url, options) {
                const res = await fetch(url, options);
                const payload = await res.json().catch(() => ({}));
                if (!res.ok) {
                    const detail = payload.detail ? `: ${payload.detail}` : "";
                    throw new Error(`HTTP ${res.status}${detail}`);
                }
                return payload;
            }

            async function refreshHealth() {
                try {
                    const payload = await apiJson("/health");
                    const ok = payload.status === "ok";
                    healthStatus.textContent = ok ? "Healthy" : "Unexpected";
                } catch {
                    healthStatus.textContent = "Unavailable";
                }
            }

            async function refreshSimulationStatus() {
                try {
                    const payload = await apiJson("/simulation/status");
                    const running = Boolean(payload.running);
                    simulationStatus.textContent = running
                        ? `Running (${payload.interval_seconds}s)`
                        : "Stopped";
                    intervalStatus.textContent = `${payload.interval_seconds}s`;
                    setText(heroSimulator, running ? "Running" : "Stopped");
                } catch {
                    simulationStatus.textContent = "Unavailable";
                    intervalStatus.textContent = "Unavailable";
                    setText(heroSimulator, "Unavailable");
                }
            }

            async function setSimulationState(state) {
                await apiJson("/simulation/control", {
                    method: "POST",
                    headers: { "Content-Type": "application/json" },
                    body: JSON.stringify({ state }),
                });
                await refreshSimulationStatus();
            }

            async function seedRecurringDemo() {
                seedRecurringStatus.textContent = "Seeding recurring demo transactions...";
                try {
                    const payload = await apiJson("/simulation/seed-recurring", {
                        method: "POST",
                    });
                    seedRecurringStatus.textContent = payload.message || "Recurring demo transactions seeded.";
                } catch (error) {
                    seedRecurringStatus.textContent = `Seed failed: ${error.message}`;
                }
            }

            function renderScenarios(payload) {
                const scenarios = Array.isArray(payload?.scenarios) ? payload.scenarios : [];
                const activeId = payload?.activeScenarioId || "";

                setText(heroScenario, activeId || "n/a");
                scenarioList.innerHTML = "";

                if (!scenarios.length) {
                    const p = document.createElement("p");
                    p.className = "hint";
                    p.textContent = "No scenarios available.";
                    scenarioList.appendChild(p);
                    return;
                }

                for (const scenario of scenarios) {
                    const btn = document.createElement("button");
                    btn.type = "button";
                    btn.className = "scenario-btn" + (scenario.id === activeId ? " active" : "");
                    btn.innerHTML = `<strong>${safeText(scenario.name)}</strong><span>${safeText(
                        scenario.description || ""
                    )}</span>`;
                    btn.addEventListener("click", async () => {
                        scenarioError.style.display = "none";
                        try {
                            const nextPayload = await apiJson("/simulation/scenarios/activate", {
                                method: "POST",
                                headers: { "Content-Type": "application/json" },
                                body: JSON.stringify({ scenarioId: scenario.id }),
                            });
                            renderScenarios(nextPayload);
                        } catch (error) {
                            scenarioError.style.display = "block";
                            scenarioError.textContent = `Scenario activation failed: ${error.message}`;
                        }
                    });
                    scenarioList.appendChild(btn);
                }
            }

            async function refreshScenarios() {
                scenarioError.style.display = "none";
                try {
                    const payload = await apiJson("/simulation/scenarios");
                    renderScenarios(payload);
                } catch (error) {
                    scenarioError.style.display = "block";
                    scenarioError.textContent = `Could not load scenarios: ${error.message}`;
                    scenarioList.innerHTML = "";
                    setText(heroScenario, "Unavailable");
                }
            }

            async function refreshReceiptStatus() {
                try {
                    const payload = await apiJson("/receipts/status");
                    const configured = Boolean(payload.configured);
                    receiptStatus.textContent = configured ? "Configured" : "Not configured";
                    visionModel.textContent = payload.model || "n/a";
                    setText(heroVision, configured ? "Configured" : "Not configured");
                } catch {
                    receiptStatus.textContent = "Unavailable";
                    visionModel.textContent = "Unavailable";
                    setText(heroVision, "Unavailable");
                }
            }

            function asMoney(value, currencyCode) {
                const numeric = Number(value);
                if (!Number.isFinite(numeric)) {
                    return "n/a";
                }

                try {
                    return new Intl.NumberFormat("en-IN", {
                        style: "currency",
                        currency: currencyCode || "INR",
                        maximumFractionDigits: 2,
                    }).format(numeric);
                } catch {
                    return numeric.toFixed(2);
                }
            }

            function renderReceiptResult(payload) {
                const currency = payload.currency || "INR";
                receiptSummary.textContent = `${payload.merchant || "Unknown merchant"} | ${
                    payload.bill_date || "Date unavailable"
                } | ${Array.isArray(payload.items) ? payload.items.length : 0} items`;

                receiptItems.innerHTML = "";
                for (const item of payload.items || []) {
                    const tr = document.createElement("tr");
                    const unitCost =
                        item.cost_per_unit && item.unit_label
                            ? `${asMoney(item.cost_per_unit, currency)} ${item.unit_label}`
                            : "n/a";
                    tr.innerHTML = `
                        <td>${safeText(item.name)}</td>
                        <td>${safeText(item.category || "Miscellaneous")}</td>
                        <td>${safeText(item.quantity)}</td>
                        <td>${safeText(asMoney(item.total_price, currency))}</td>
                        <td>${safeText(asMoney(item.cost_per_item, currency))}</td>
                        <td>${safeText(unitCost)}</td>
                    `;
                    receiptItems.appendChild(tr);
                }

                const insights = payload.insights || {};
                const increaseCount = Array.isArray(insights.price_increases)
                    ? insights.price_increases.length
                    : 0;
                const betterValueCount = Array.isArray(insights.better_value_items)
                    ? insights.better_value_items.length
                    : 0;
                const lowestUnitCount = Array.isArray(insights.lowest_unit_cost_items)
                    ? insights.lowest_unit_cost_items.length
                    : 0;

                receiptInsights.innerHTML = "";
                const insightEntries = [
                    `Price increases detected: ${increaseCount}`,
                    `Better value items detected: ${betterValueCount}`,
                    `Lowest unit-cost shortlist entries: ${lowestUnitCount}`,
                ];

                for (const line of insightEntries) {
                    const li = document.createElement("li");
                    li.textContent = line;
                    receiptInsights.appendChild(li);
                }

                receiptOutput.style.display = "block";
            }

            async function analyzeReceipt() {
                receiptError.style.display = "none";

                const file = receiptFile.files?.[0];
                if (!file) {
                    receiptError.textContent = "Select a receipt image file first.";
                    receiptError.style.display = "block";
                    return;
                }

                const formData = new FormData();
                formData.append("file", file);
                analyzeReceiptBtn.disabled = true;
                analyzeReceiptBtn.textContent = "Analyzing...";

                try {
                    const payload = await apiJson("/receipts/analyze", {
                        method: "POST",
                        body: formData,
                    });
                    renderReceiptResult(payload);
                } catch (error) {
                    receiptError.textContent = `Receipt analysis failed: ${error.message}`;
                    receiptError.style.display = "block";
                } finally {
                    analyzeReceiptBtn.disabled = false;
                    analyzeReceiptBtn.textContent = "Analyze Receipt";
                }
            }

            async function loadHistory() {
                try {
                    const history = await apiJson("/messages");
                    messages.innerHTML = "";
                    history
                        .slice()
                        .reverse()
                        .forEach((item) => renderMessage(item));
                    updateMessageCount();
                } catch {
                    messages.innerHTML = "";
                    const li = document.createElement("li");
                    li.textContent = "Message history unavailable.";
                    messages.appendChild(li);
                    updateMessageCount();
                }
            }

            function connectSocket() {
                const wsProtocol = location.protocol === "https:" ? "wss" : "ws";
                const ws = new WebSocket(`${wsProtocol}://${location.host}/ws/messages`);

                ws.onopen = () => {
                    setText(heroSocket, "Connected");
                };

                ws.onclose = () => {
                    setText(heroSocket, "Disconnected");
                    window.setTimeout(connectSocket, 1000);
                };

                ws.onerror = () => {
                    setText(heroSocket, "Error");
                };

                ws.onmessage = (event) => {
                    try {
                        const packet = JSON.parse(event.data);
                        if (packet.type === "history") {
                            messages.innerHTML = "";
                            (packet.messages || []).slice().reverse().forEach((item) => renderMessage(item));
                            updateMessageCount();
                            return;
                        }
                        if (packet.type === "message") {
                            renderMessage(packet.data);
                        }
                    } catch {
                        // Ignore malformed websocket payloads.
                    }
                };
            }

            document.getElementById("startBtn").addEventListener("click", () => setSimulationState("start"));
            document.getElementById("stopBtn").addEventListener("click", () => setSimulationState("stop"));
            document.getElementById("seedRecurringBtn").addEventListener("click", seedRecurringDemo);
            document.getElementById("refreshBtn").addEventListener("click", async () => {
                await refreshSimulationStatus();
                await refreshScenarios();
                await refreshHealth();
                await refreshReceiptStatus();
            });
            document.getElementById("loadHistoryBtn").addEventListener("click", loadHistory);
            analyzeReceiptBtn.addEventListener("click", analyzeReceipt);

            async function boot() {
                await Promise.all([
                    refreshHealth(),
                    refreshSimulationStatus(),
                    refreshScenarios(),
                    refreshReceiptStatus(),
                    loadHistory(),
                ]);
                connectSocket();
            }

            boot();
        </script>
    </body>
</html>
"""


@app.get("/", response_class=HTMLResponse)
async def control_ui() -> HTMLResponse:
    return HTMLResponse(CONTROL_UI)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/messages")
async def get_messages() -> list[dict]:
    return simulator.history()


@app.get("/receipts/status", response_model=ReceiptFeatureStatusResponse)
async def receipt_status() -> ReceiptFeatureStatusResponse:
    return ReceiptFeatureStatusResponse(
        configured=receipt_analyzer.configured,
        model=receipt_analyzer.model,
    )


@app.get("/simulation/scenarios", response_model=DemoScenarioListResponse)
async def simulation_scenarios() -> DemoScenarioListResponse:
    scenarios = [
        DemoScenario(
            id=item.id,
            name=item.name,
            description=item.description,
            running=item.id == active_demo_scenario_id,
        )
        for item in DEMO_SCENARIOS
    ]
    return DemoScenarioListResponse(
        scenarios=scenarios,
        activeScenarioId=active_demo_scenario_id,
    )


@app.post("/simulation/scenarios/activate", response_model=DemoScenarioListResponse)
async def activate_simulation_scenario(payload: ActivateScenarioRequest) -> DemoScenarioListResponse:
    global active_demo_scenario_id
    valid_scenario_ids = {item.id for item in DEMO_SCENARIOS}

    if payload.scenarioId not in valid_scenario_ids:
        raise HTTPException(status_code=404, detail="Scenario not found.")

    active_demo_scenario_id = payload.scenarioId
    simulator.set_scenario(payload.scenarioId)
    return await simulation_scenarios()


@app.post("/receipts/analyze")
async def analyze_receipt(file: UploadFile = File(...)) -> dict:
    if not file.content_type or not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Please upload an image file.")

    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="The uploaded image is empty.")

    try:
        return await receipt_analyzer.analyze_receipt(image_bytes, file.content_type)
    except ReceiptAnalysisError as exc:
        message = str(exc)
        if "GROQ_API_KEY is not configured" in message:
            raise HTTPException(
                status_code=503,
                detail="GROQ_API_KEY is not configured on the backend server.",
            ) from exc
        raise HTTPException(status_code=502, detail=message) from exc


@app.post("/reports/monthly-spend")
async def monthly_spend_report(payload: MonthlySpendReportRequest) -> Response:
    try:
        month_date = datetime.strptime(payload.month, "%Y-%m")
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Month must use YYYY-MM format.") from exc

    month_prefix = month_date.strftime("%Y-%m")
    report_transactions = [
        ReportTransaction(
            date=item.date,
            description=item.description,
            amount=item.amount,
            direction=item.direction,
            category=item.category,
            bucket=item.bucket,
        )
        for item in payload.transactions
        if item.date.startswith(month_prefix)
    ]

    pdf_bytes = build_monthly_spend_pdf(
        month=month_prefix,
        transactions=report_transactions,
        currency=payload.currency or "INR",
    )

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="monthly-spend-{month_prefix}.pdf"'
        },
    )


@app.post("/simulation/seed-recurring", response_model=RecurringSeedResponse)
async def seed_recurring_demo() -> RecurringSeedResponse:
    now = datetime.now(timezone.utc)
    recurring_templates = [
        {
            "merchant": "Netflix",
            "message": "Netflix subscription charged INR 649",
            "amount": 649.0,
            "day_offsets": [61, 31, 1],
            "bucket": "Entertainment",
        },
        {
            "merchant": "PowerFit Gym",
            "message": "Gym membership fee debited INR 1200",
            "amount": 1200.0,
            "day_offsets": [58, 29],
            "bucket": "Health",
        },
        {
            "merchant": "CloudVault",
            "message": "Cloud storage subscription charged INR 149",
            "amount": 149.0,
            "day_offsets": [21, 14, 7],
            "bucket": "Entertainment",
        },
    ]

    seeded_messages: list[dict] = []
    for template in recurring_templates:
        for day_offset in template["day_offsets"]:
            timestamp = now - timedelta(days=day_offset)
            seeded_messages.append(
                {
                    "id": uuid4().hex,
                    "timestamp": timestamp.isoformat(),
                    "message": template["message"],
                    "amount": template["amount"],
                    "merchant": template["merchant"],
                    "bucket": template["bucket"],
                    "account_last4": "1001",
                    "transaction_id": uuid4().hex[:10].upper(),
                }
            )

    created = await simulator.inject_messages(seeded_messages)
    return RecurringSeedResponse(
        created=created,
        message=f"Created {created} recurring/subscription demo transactions.",
    )


@app.get("/simulation/status", response_model=SimulationStatusResponse)
async def simulation_status() -> SimulationStatusResponse:
    return SimulationStatusResponse(
        running=simulator.running,
        interval_seconds=simulator.interval_seconds,
    )


@app.post("/simulation/control", response_model=SimulationStatusResponse)
async def simulation_control(payload: SimulationControlRequest) -> SimulationStatusResponse:
    if payload.state == "start":
        await simulator.start()
    else:
        await simulator.stop()

    return SimulationStatusResponse(
        running=simulator.running,
        interval_seconds=simulator.interval_seconds,
    )


@app.websocket("/ws/messages")
async def websocket_messages(websocket: WebSocket) -> None:
    await websocket.accept()
    queue = await simulator.subscribe()
    try:
        # Send current history first so client can render immediately.
        await websocket.send_json({"type": "history", "messages": simulator.history()})

        while True:
            message = await queue.get()
            await websocket.send_json({"type": "message", "data": message})
    except WebSocketDisconnect:
        pass
    finally:
        simulator.unsubscribe(queue)
