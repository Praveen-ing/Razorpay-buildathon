# ARCHITECTURE.md — RevRecover AI

> **IMPORTANT: Before modifying this repository, read this document in full.**
>
> Do NOT create parallel implementations of existing functionality.
> Do NOT bypass the Compliance Governor.
> Do NOT count a recovery as successful without authoritative payment evidence.
> Do NOT claim an external communication succeeded unless a provider confirms it.
> Keep business logic centralized in the Recovery Orchestrator and domain services.

---

## What This System Does

**RevRecover AI** is an autonomous AI revenue recovery agent that:

1. **Detects** revenue at risk (payment failure, checkout abandonment, subscription failure, B2B invoice overdue)
2. **Diagnoses** the root cause (expired card, insufficient funds, bank timeout, price sensitivity, mandate failure)
3. **Calculates** whether recovery is economically worth pursuing (Expected Value = P(recovery) × amount − cost − P(churn) × LTV)
4. **Governs** the action through compliance stopping rules (fraud, DND, dispute, max attempts, active PTP, negative EV, high-value hold)
5. **Executes** a bounded recovery action (real Razorpay Test Mode payment link, channel outreach)
6. **Observes** the actual payment outcome (webhook: `payment.captured` or `payment_link.paid`)
7. **Measures** actual recovered money (not "link created" — real payment evidence)
8. **Audits** every decision in a SHA-256 hash-chain ledger

---

## System Architecture

```
┌─────────────────────────────────────────────────────────┐
│                  Event Sources                          │
│  Razorpay Webhook │ Streamlit UI │ REST API │ Batch     │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│             FastAPI Service  (transport only)           │
│  src/service/service.py + service/recovery_router.py    │
└──────────────────┬──────────────────────────────────────┘
                   │ orchestrator.process_transaction()
                   ▼
┌─────────────────────────────────────────────────────────┐
│          Recovery Orchestrator (master pipeline)        │
│               src/agents/orchestrator.py                │
│                                                         │
│  [Detector] → [Strategist] → [Governor] → [Executor]   │
│       ↓             ↓            ↓             ↓        │
│   Diagnosis    Intervention  Compliance   Execution     │
│              (plan only, no  (allows or   (calls real   │
│               API calls)     blocks)       API)         │
└──────────────────┬──────────────────────────────────────┘
                   │
          ┌────────┴────────┐
          ▼                 ▼
┌──────────────────┐  ┌─────────────────────────────────┐
│  AuditLedger     │  │  External Systems               │
│  (SHA-256 chain) │  │  Razorpay API (Test Mode)       │
│  Telemetry       │  │  WhatsApp / SMS / Email / Voice │
└──────────────────┘  └─────────────────────────────────┘
```

---

## Agent Responsibilities

| Agent | File | Responsibility | Must NOT Do |
|-------|------|---------------|-------------|
| **Detector** | `agents/detector.py` | Diagnose root cause, calculate P(recovery), P(churn), urgency | Call Razorpay, send messages, bypass governance |
| **Strategist** | `agents/strategist.py` | Select channel/vector, calculate EV, authorize discount | Call Razorpay API, send messages, enforce compliance |
| **Governor** | `agents/governor.py` | Enforce stopping rules (7 rules), compliance checks | Override fraud/dispute/DND/max-attempts rules |
| **Executor** | `agents/executor.py` | Create payment links, dispatch channel messages | Decide if action is allowed (that's the Governor) |
| **AuditLedger** | `agents/audit_agent.py` | Create SHA-256 hash-chain entries | Modify existing entries |
| **Orchestrator** | `agents/orchestrator.py` | Wire agents, manage state, measure outcomes | Implement business logic (that's each agent's job) |

---

## Recovery Pipeline (Step by Step)

```
1. TransactionFailureEvent received
2. Detector.diagnose(event) → RootCauseDiagnosis
   - Category, confidence, P(recovery), P(churn), urgency, bank health
3. Strategist.plan_intervention(event, diagnosis) → RecoveryIntervention
   - Channel selection, EV calculation, discount authorization
   - razorpay_payment_link = None (executor creates it later)
4. Governor.evaluate(event, intervention) → ComplianceDecision
   - 7 stopping rules checked in order (see Governance section)
   - Returns action_permitted: True/False
5a. If BLOCKED → audit stop, return stopped status
5b. If APPROVED → Executor.execute(event, intervention, ...)
   - Creates real Razorpay Test Mode payment link (or mock if MOCK_MODE=true)
   - Dispatches channel message (formatted only — provider not configured)
   - Returns ExecutionResult with explicit status
6. Status = OUTREACH_ACTIVE (real mode) or RECOVERED (synthetic benchmark only)
7. AuditLedger creates entry for every state transition
8. Telemetry records the record
9. [Later] payment.captured webhook → orchestrator.confirm_payment_recovered()
   - Updates to RECOVERED with actual payment_id and amount
```

---

## Governance — Stopping Rules

Rules evaluated in strict priority order:

| # | Rule | Condition | Status |
|---|------|-----------|--------|
| 1 | `STOP_FRAUD_SUSPECTED` | `event.fraud_suspected` or error_code=FRAUD_SUSPECTED | STOPPED_FRAUD_RISK |
| 2 | `STOP_CUSTOMER_OPT_OUT` | `event.opted_out` | STOPPED_OPT_OUT |
| 3 | `STOP_MAX_ATTEMPTS_EXCEEDED` | `attempt_count ≥ max_attempts (3)` | STOPPED_MAX_ATTEMPTS_EXHAUSTED |
| 4 | `STOP_DISPUTE_RAISED` | `event.disputed` | STOPPED_DISPUTE_ESCALATED |
| 5 | `STOP_PROMISE_TO_PAY_ACTIVE` | `event.has_active_ptp` | STOPPED_PTP_ACTIVE |
| 6 | `STOP_NEGATIVE_EXPECTED_VALUE` | `EV ≤ 0 AND attempt_count > 0` | STOPPED_NEGATIVE_EV |
| 7 | `PAUSE_FOR_HUMAN_APPROVAL` | `requires_human_approval AND amount > ₹40,000` | OUTREACH_ACTIVE (paused) |

**The Governor cannot be bypassed. LLM output cannot override governance.**

---

## Recovery State Machine

```
RECEIVED
   ↓
DIAGNOSED
   ↓
INTERVENTION_PLANNED (note: pre-existing RecoveryStatus, maps to STRATEGIZED)
   ↓
COMPLIANCE_EVALUATED
   ↓
BLOCKED ──────────────────────────────────────────► STOPPED_* states
   OR
APPROVED
   ↓
OUTREACH_ACTIVE (link created / message formatted)
   ↓
   ├── payment.captured webhook → RECOVERED (with payment_id evidence)
   ├── No customer action → EXPIRED
   └── B2B scenario → PROMISE_TO_PAY_SET → OUTREACH_ACTIVE → RECOVERED/CLOSED
```

**RecoveryCaseStatus** (new state machine in recovery_schema.py):
`RECEIVED → DIAGNOSED → STRATEGIZED → GOVERNANCE_APPROVED/BLOCKED → PAYMENT_LINK_CREATED → OUTREACH_SENT → PAYMENT_PENDING → RECOVERED / FAILED / EXPIRED / ESCALATED / PTP_ACTIVE`

---

## Real vs Synthetic Data

This distinction is critical and must NEVER be blurred:

| Data Source | Badge | What it means |
|-------------|-------|---------------|
| 🟢 **RAZORPAY_TEST_MODE** | `PaymentLinkSource.RAZORPAY_TEST_MODE` | Real Razorpay API call, real test payment link, authoritative |
| 🟡 **MOCK_SANDBOX** | `PaymentLinkSource.MOCK_SANDBOX` | Local mock (RAZORPAY_MOCK_MODE=true), no API call |
| 🟡 **SYNTHETIC_BENCHMARK** | `is_synthetic=True` | Probabilistic simulation, benchmark only, NOT real money |
| 🔴 **NOT_CONFIGURED** | `ChannelDeliveryStatus.NOT_CONFIGURED` | Provider credentials missing, no delivery attempted |

**Rules:**
- `money_recovered > 0` in SYNTHETIC mode = benchmark simulation
- `money_recovered > 0` in REAL mode = requires actual `payment_id` from Razorpay
- A payment link being created ≠ revenue recovered
- A message being formatted ≠ message delivered

---

## Razorpay Test Mode Integration

### Payment Link Creation
```
Executor.execute(event, intervention)
    ↓
razorpay_client.create_payment_link(amount, customer, notes={transaction_id, recovery_case_id})
    ↓
POST https://api.razorpay.com/v1/payment_links
    ↓
PaymentLinkRecord(id, short_url, source=RAZORPAY_TEST_MODE, status=created)
```

### Payment Reconciliation (webhook)
```
POST /webhooks/razorpay
    ↓
Signature Verification (HMAC SHA256, RAZORPAY_WEBHOOK_SECRET)
    ↓
Idempotency Check (WebhookIdempotencyStore)
    ↓
Extract payment.captured info (payment_id, amount)
    ↓
orchestrator.confirm_payment_recovered(transaction_id, payment_id, amount)
    ↓
Audit entry: PAYMENT_CONFIRMED_VIA_WEBHOOK (data_source=RAZORPAY_TEST_MODE)
```

### Test Mode Credentials
Configure in `.env` (not tracked in git):
```
RAZORPAY_KEY_ID=rzp_test_...
RAZORPAY_KEY_SECRET=...
RAZORPAY_WEBHOOK_SECRET=...
RAZORPAY_MOCK_MODE=false
```

### Test Payment Cards
- **Success:** `4111 1111 1111 1111` (Visa) | OTP: `1234`
- **Decline:** `4000 0000 0000 0002`
- **Insufficient funds:** `4000 0000 0000 9995`
- **UPI Success:** `success@razorpay`

---

## Domain Models

Primary models in `src/schema/recovery_schema.py`:

```
TransactionFailureEvent   → input event (payment fail, checkout drop, subscription, B2B)
RootCauseDiagnosis        → detector output (category, P(recovery), P(churn), urgency)
RecoveryIntervention      → strategist output (channel, EV, discount, message)
ComplianceDecision        → governor output (allowed/blocked, stopping rule, reason)
ExecutionResult           → executor output (payment link, channel delivery, status)
PaymentLinkRecord         → tracks real/mock payment link (link_id, source, status, payment_id)
ChannelDeliveryResult     → channel dispatch result (explicit status, never fake SENT)
TransactionRecoveryRecord → complete pipeline record
AuditLogEntry             → single SHA-256 hash-chain entry
PromiseToPayRecord        → B2B PTP with lifecycle states
BatchRecoveryResult       → batch processing result with baseline comparison
BaselineComparisonMetrics → lift/ROI metrics vs naive baseline policy
RecoveryKPIs              → live dashboard metrics
```

Supporting models in `src/schema/razorpay_schema.py`:
```
RazorpayPaymentEntity, RazorpaySubscriptionEntity, RazorpayInvoiceEntity
RazorpayWebhookPayload, RazorpayPaymentLinkCreateRequest, RazorpayPaymentLinkResponse
```

---

## Audit — SHA-256 Hash Chain

Every state transition creates an immutable `AuditLogEntry`:

```python
payload = f"{prev_hash}:{log_id}:{timestamp}:{txn_id}:{cust_id}:{agent}:{action}:{state_before}:{state_after}:{compliance}:{details_json}"
entry_hash = sha256(payload)
```

Verify chain integrity:
```python
is_valid, count = audit_ledger_agent.verify_ledger_integrity()
```

**Rules:**
- Audit records are append-only
- Every record references the previous record's hash
- Any modification or deletion breaks the chain (detectable)
- Credentials and sensitive values must NOT appear in audit details

---

## File Structure

```
src/
├── agents/
│   ├── orchestrator.py    ← Master pipeline (wire all agents)
│   ├── detector.py        ← Root cause diagnosis (deterministic)
│   ├── strategist.py      ← EV optimization + channel selection (deterministic)
│   ├── governor.py        ← Compliance + stopping rules (deterministic)
│   ├── executor.py        ← External actions (Razorpay API, channel dispatch)
│   ├── audit_agent.py     ← SHA-256 hash-chain audit ledger
│   └── voice_recovery.py  ← Hinglish voice dialogue engine
│
├── schema/
│   ├── recovery_schema.py ← ALL domain models (single source of truth)
│   ├── razorpay_schema.py ← Razorpay API response models
│   └── models.py          ← LLM provider models
│
├── integrations/
│   ├── razorpay_client.py ← Single Razorpay API client (singleton)
│   ├── webhook_handler.py ← Webhook parsing + idempotency store
│   ├── simulator.py       ← Synthetic batch generator (benchmark only)
│   └── channels/
│       ├── whatsapp.py    ← Message formatting (not transport)
│       ├── sms.py         ← Message formatting (not transport)
│       ├── email.py       ← Message formatting (not transport)
│       └── voice_hinglish.py ← Hinglish script generation
│
├── core/
│   ├── settings.py        ← All configuration (pydantic-settings)
│   ├── telemetry.py       ← In-memory KPI accumulator
│   └── llm.py             ← LLM provider factory
│
├── memory/
│   ├── sqlite.py          ← SQLite checkpointer (LangGraph)
│   ├── postgres.py        ← Postgres checkpointer (production)
│   └── mongodb.py         ← MongoDB store (optional)
│
├── service/
│   ├── service.py         ← FastAPI app (transport layer, no business logic)
│   └── recovery_router.py ← All revenue recovery API endpoints
│
├── streamlit_app.py       ← 6-tab operator dashboard
└── run_service.py         ← Service startup entry point
```

---

## Configuration

All configuration via environment variables (pydantic-settings):

| Variable | Description | Default |
|----------|-------------|---------|
| `RAZORPAY_KEY_ID` | Razorpay API key (Test Mode: rzp_test_...) | placeholder |
| `RAZORPAY_KEY_SECRET` | Razorpay API secret | required |
| `RAZORPAY_WEBHOOK_SECRET` | Webhook HMAC verification secret | optional |
| `RAZORPAY_MOCK_MODE` | `true` = mock sandbox, `false` = real Test Mode | `true` |
| `MAX_DISCOUNT_PERCENTAGE` | Max authorized discount (%) | `15.0` |
| `ENABLE_COMPLIANCE_GUARD` | Enable governor stopping rules | `true` |
| `DATABASE_TYPE` | `sqlite` / `postgres` | `sqlite` |
| `HOST` / `PORT` | Service bind address | `0.0.0.0:8080` |

---

## API Endpoints

**Recovery:**
- `POST /recovery/process` — single event recovery
- `POST /recovery/batch` — batch (synthetic mode)
- `POST /recovery/benchmark/{name}` — named benchmark
- `POST /webhooks/razorpay` — webhook (sig verify + idempotency)

**Analytics:**
- `GET /analytics/kpis` — live KPIs
- `GET /analytics/records?limit=N` — recent records
- `POST /analytics/reset` — reset in-memory state

**Audit:**
- `GET /audit/logs?limit=N` — audit log entries
- `GET /audit/verify` — SHA-256 chain integrity check

**Razorpay Gateway:**
- `GET /razorpay/payment-links` — list Test Mode links
- `GET /razorpay/payment-links/{id}` — fetch specific link
- `GET /razorpay/payments` — list Test Mode payments

**Voice:**
- `POST /voice/simulate` — Hinglish voice turn simulation

**Health:**
- `GET /health` — service health check

---

## Running the System

```bash
# Install dependencies
pip install -e .

# Configure environment
cp .env.example .env
# Edit .env with your Razorpay Test Mode credentials

# Run FastAPI backend
python src/run_service.py

# Run Streamlit dashboard
streamlit run src/streamlit_app.py

# Run tests (mock mode, no real API calls)
python -m pytest -v

# Run E2E tests with real Razorpay Test Mode
# First: set RAZORPAY_MOCK_MODE=false in .env
python -m pytest tests/e2e/ -v -s

# Docker
docker compose up
```

---

## Development Rules for Future AI Agents

1. **One recovery pipeline** — add new scenarios to `orchestrator.process_transaction()`, not a new orchestrator
2. **New domain models go in `recovery_schema.py`** — never duplicate elsewhere
3. **New external calls go in `executor.py`** — strategist/governor are pure decision logic
4. **New Razorpay API methods go in `razorpay_client.py`** — there is exactly one Razorpay client
5. **New API endpoints go in `recovery_router.py`** — service.py is the mount point only
6. **All tests must pass after every change** — `python -m pytest -v` must stay green
7. **Never return fake success from channels** — use explicit `ChannelDeliveryStatus` values
8. **Never count revenue without payment_id** — only `payment.captured` or `payment_link.paid` confirms recovery
9. **Never bypass the Governor** — compliance rules protect against fraud, harassment, and regulatory violations
10. **Label everything Real vs Synthetic** — use `PaymentLinkSource` and `is_synthetic` fields
