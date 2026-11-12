# Spark2Pay — Hackathon Submission

**Track targets:** Best Use of Agentic Commerce · Best Use of PayPal + AI
**Also mapped to:** Technological Implementation · Design · Potential Impact ·
Innovation · Presentation (Devpost judging criteria)

---

## The pitch (Devpost description)

Subscription trackers tell you what to cancel — then leave the actual
cancelling to you. Spark2Pay closes that last mile. Its AI savings engine
analyzes your recurring expenses and, when it concludes a subscription should
go, it doesn't just say so: it renders a **Manage with PayPal** button. One
click walks you through approval, executes through PayPal's APIs, writes an
immutable audit record, and marks the subscription cancelled in your tracker.

**What we built**

1. **AI savings engine** (`backend/app/services/ai_service.py`)
   - A deterministic rules engine that finds long-unused subscriptions,
     duplicate category coverage, and costly underuse — zero keys, always on.
   - An optional LLM agent over one OpenAI-compatible client (OpenAI, Gemini,
     or local Ollama). The model receives your portfolio as JSON and can call
     the `manage_with_paypal(subscription_id, action, reason)` tool. Tool calls
     are *proposals*: they are validated against real data (hallucinated
     subscription ids are rejected), rendered as buttons, and never
     auto-executed.
2. **PayPal execution layer** (`backend/app/services/paypal_service.py`)
   - Orders v2 (`create_order`, `capture_order`) and Subscriptions v1
     (`cancel_subscription`, `suspend_subscription`, `activate_subscription`)
     behind a single interface.
   - OAuth 2.0 client-credentials token caching with expiry refresh,
     idempotent handling of `ORDER_ALREADY_CAPTURED` and re-cancellation,
     webhook signature verification against
     `/v1/notifications/verify-webhook-signature`, and event handling for
     `PAYMENT.CAPTURE.COMPLETED` + `BILLING.SUBSCRIPTION.CANCELLED`.
   - **Dual mode:** `PAYPAL_MODE=sandbox` hits the real PayPal sandbox;
     `PAYPAL_MODE=simulation` runs a deterministic local simulator with the
     same interface — so judges can run the full loop without any credentials.
3. **Audit trail** (`paypal_actions` table) — every attempt records the
   subscription snapshot, PayPal order/capture/subscription ids, mode
   (sandbox|simulation), outcome, and error details. The webhook path updates
   the same trail, so PayPal-side cancellations propagate even if they happen
   outside the app.
4. **Human-in-the-loop frontend** — a bespoke dark UI (React 18 + TypeScript +
   Tailwind, hand-built design system) with an advice feed, a PayPal-styled
   approval simulator (sandbox banner, buyer account, Agree & Pay / Cancel
   and return), savings count-up completion moment, a full Action Log, and a
   Settings page with live, editable AI/execution configuration.

**Why it's agentic:** the AI perceives (subscription + usage data), decides
(which actions merit a PayPal call), and acts (through the execution layer) —
with the approval step as a deliberate safety gate, not a missing automation.

## Tools used

| Tool | Where & how |
|------|-------------|
| **PayPal Orders v2 API** | One-off payments: create CAPTURE order → hosted approval → capture, with idempotent re-capture handling |
| **PayPal Subscriptions v1 API** | Cancel / suspend / activate recurring billing agreements; subscription details lookup |
| **PayPal OAuth 2.0 (client credentials)** | Server-side token management with cache + expiry refresh |
| **PayPal Webhooks + signature verification** | `PAYMENT.CAPTURE.COMPLETED`, `BILLING.SUBSCRIPTION.CANCELLED` → audit write-back + tracker sync |
| **AI: OpenAI `gpt-4o-mini` (function calling)** | The savings agent proposes `manage_with_paypal` tool calls; proposals validated, never auto-executed. Works with Gemini and Ollama through the same OpenAI-compatible protocol |
| **AI: deterministic rules engine** | Zero-key fallback implementing the same advice contract (unused-60-days, duplicate category, costly underuse) |
| Stack | Python 3 / Flask 3 / SQLAlchemy 2 / SQLite · React 18 / TypeScript / Vite / Tailwind CSS · pytest (33 tests) |

## Screenshots

Live-captured loop in [README.md](README.md#screenshots):
login → AI advice → approval → execution → audit → closed loop.

## Run it (judges)

```bash
cd backend && python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python seed_demo.py
python run.py                # :3038

cd ../frontend && npm install && npm run dev    # :5173
```

Sign in at http://localhost:5173 — `demo` / `Spark2Pay2026`. Then:

1. Dashboard: AI advice lists savings opportunities with savings amounts.
2. Click **Manage with PayPal** on a PayPal-managed card.
3. Approve on the PayPal-styled sandbox simulator (with real sandbox keys,
   pay orders open PayPal's hosted approval page instead — see README
   "Connecting the real PayPal sandbox").
4. Watch the savings count-up, then check **Action Log**: the audited record.
5. The subscription is now marked cancelled — the loop is closed.

## Judging-criteria mapping

| Criterion | Spark2Pay |
|-----------|-----------|
| **Best Use of Agentic Commerce** | LLM function calling drives real PayPal execution; the agent's tool calls become audited commerce actions. The full perceive→analyze→approve→execute→audit loop, with a webhook path for out-of-band events. |
| **Best Use of PayPal + AI** | A dedicated execution layer over four PayPal API surfaces (OAuth, Orders v2, Subscriptions v1, Webhooks), orchestrated by AI function calling with validated proposals. Sandbox and simulation modes share one code path. |
| **Technological Implementation** | 33 automated tests (execution layer mocked-HTTP tests, agent-loop tests, API loop tests); idempotency handling; token caching; graceful LLM fallback; strict-TypeScript frontend. |
| **Design** | Hand-tuned dark design system (Bricolage Grotesque / Inter / JetBrains Mono, PayPal-yellow execution buttons, spark-amber savings), one-purpose-per-screen layout, restrained motion with a single signature "dealt moment". |
| **Potential Impact** | Subscription waste is a universal pain point; executable savings convert insight into real money back. The simulation mode makes the product safely demoable by anyone, anywhere. |
| **Innovation / Idea** | "The AI doesn't just tell you, it does it" — with an honest human-in-the-loop gate and an audit-first architecture. |
| **Presentation** | 2-minute demo video (script below) follows one subscription from insight to money saved. |

## Demo video script (< 3 minutes)

1. **0:00–0:20 — Problem.** Subscription trackers stop at advice. Screen: dashboard header.
2. **0:20–0:50 — The advice.** AI savings feed: "Cancel Netflix Premium — unused for 92 days, saves $22.99/mo", confidence, PayPal-yellow button.
3. **0:50–1:20 — The approval.** Click *Manage with PayPal* → the PayPal-styled sandbox simulator: buyer account, order summary, what will happen, savings, billing agreement id. Click *Agree & Cancel*. (With real sandbox keys, pay orders open PayPal's hosted approval page — same shape.)
4. **1:20–1:50 — The money moment.** Green check "Done — via PayPal", savings count-up ($22.99/mo ≈ $275.88/yr) with the spark pulse.
5. **1:50–2:20 — The audit.** Action Log: the completed CANCEL record with PayPal reference and mode badge. Subscriptions page: Netflix now "cancelled", monthly total down.
6. **2:20–2:50 — Under the hood.** Settings page (AI provider + PayPal layer status), then a flash of `ai_service.py` tool schema and `paypal_service.py` cancel path. Closing line: "AI finds the waste. PayPal executes the savings. You stay in control."

## Scope notes

- Subscriptions can only be executed through PayPal when they are actually
  billed via PayPal Subscriptions (`paypal_subscription_id` linkage). Card-billed
  services are honestly marked "cancel on merchant site" — the demo portfolio
  includes both states.
- The simulation mode is a development/demo aid: it exercises the identical
  service interface and audit trail without network calls, and is never used to
  fake a real PayPal interaction in sandbox mode.
