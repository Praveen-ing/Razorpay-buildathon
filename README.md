# ⚡ RevRecover AI — Autonomous AI Revenue Recovery Platform

> **Razorpay Buildathon — Track 03: AI Revenue Recovery**  
> *"Find revenue that's slipping away and win it back."*

[![Python Version](https://img.shields.io/badge/Python-3.12%2B-blue.svg)](https://python.org)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688.svg)](https://fastapi.tiangolo.com)
[![LangGraph](https://img.shields.io/badge/Multi--Agent-LangGraph-FF6F00.svg)](https://langchain-ai.github.io/langgraph/)
[![Razorpay](https://img.shields.io/badge/Payments-Razorpay-0C2340.svg)](https://razorpay.com)
[![Compliance](https://img.shields.io/badge/Regulatory-RBI%20%7C%20DPDP%202023-brightgreen.svg)]()
[![Tests](https://img.shields.io/badge/Tests-42%20Passed-success.svg)]()

---

## 🎯 Executive Overview & The Winning Pitch

Businesses worldwide—and in India's fast-growing digital economy—silently bleed **5% to 15% of their Gross Merchandise Value (GMV)** due to fragmented, multi-step revenue drop-offs:
1. **Payment Failures & Transient Bank Glitches**: Gateway timeouts, bank OTP drops, issuer downtime (HDFC, SBI, ICICI, UPI network spikes).
2. **High-Intent Checkout Abandonment**: Customers who intended to buy but encountered payment friction or drop-offs.
3. **Recurring SaaS Mandate Failures & Involuntary Churn**: Expired cards, insufficient balance on billing day, mandate invalidation under RBI e-mandate guidelines.
4. **B2B Receivables & Aging Overdue Invoices**: Manual follow-ups, delayed collections, lack of structured dispute routing, and unmonitored Promise-to-Pay (PTP) commitments.

**RevRecover AI** solves this with a **closed-loop autonomous multi-agent engine** powered by LangGraph, FastAPI, and Razorpay. It doesn't just detect lost revenue—it **diagnoses the root cause, formulates the highest-converting intervention vector, executes bounded multi-channel recovery (WhatsApp 1-Click Pay links, SMS, Hinglish AI Voice Calls), enforces strict compliance & hard stopping rules, and proves measured money recovered with an immutable audit ledger.**

---

## 🏆 Exceeding "The Bar"

> **The Hackathon Bar**: *"Don't just identify the problem. Show measured money recovered across a batch, with compliant escalation, stopping rules, and an audit trail."*

| Hackathon Requirement | How RevRecover AI Wins |
| :--- | :--- |
| **Measured Money Recovered** | Built-in **Batch Benchmark Arena** executes 100 to 500 realistic transactions, quantifying exact ₹ at risk vs ₹ recovered (>70% recovery rate) in seconds. |
| **Root-Cause Telemetry** | Maps 40+ Razorpay error codes (`BAD_REQUEST_PAYMENT_TIMED_OUT`, `BANK_SERVER_DOWN`, `INSUFFICIENT_FUNDS`, etc.) and bank health heuristics. |
| **Bounded Multi-Channel Outreach** | Generates dynamic 1-click Razorpay checkout links on WhatsApp, SMS, and runs real-time **Hinglish AI Voice Recovery** calls. |
| **Compliant Escalation & Stopping Rules** | Immediate halt upon payment webhook, DND opt-out, dispute flag, or active Promise-to-Pay (PTP). Enforces DPDP contact hours & attempt limits. |
| **Immutable Audit Trail** | Cryptographically identifiable SHA-256 hash-chain ledger tracking every state transition, agent decision, and rupee recovered. |

---

## 🏗️ Architecture & Multi-Agent LangGraph Graph

```
                                  ┌───────────────────────────────┐
                                  │   Razorpay Webhooks & Events  │
                                  │ (payment.failed, subs.halted, │
                                  │  invoice.overdue, dropoffs)   │
                                  └──────────────┬────────────────┘
                                                 │
                                                 ▼
┌────────────────────────────────────────────────────────────────────────────────────────────────────────┐
│                                 RevRecover AI Multi-Agent Engine                                      │
│                                                                                                        │
│  ┌───────────────────────┐      ┌───────────────────────────┐      ┌────────────────────────────────┐  │
│  │ 1. Telemetry Detector │ ───► │ 2. Root Cause Diagnostician│ ───► │ 3. Intervention Strategist     │  │
│  │  - Razorpay Error Map │      │  - Tech vs User vs Churn  │      │  - Smart Retry vs WhatsApp Link│  │
│  │  - Bank Health Index  │      │  - Customer LTV & Intent  │      │  - Message/Discount Authorized │  │
│  └───────────────────────┘      └───────────────┬───────────┘      └───────────────┬────────────────┘  │
│                                                 │                                  │                   │
│  ┌───────────────────────┐      ┌───────────────┴───────────┐      ┌───────────────┴────────────────┐  │
│  │ 6. Audit & Ledger     │ ◄─── │ 5. Recovery Executor      │ ◄─── │ 4. Compliance Governor         │  │
│  │  - Immutable Trace    │      │  - Razorpay Test Mode Link│      │  - RBI Mandate & DPDP Rule     │  │
│  │  - ₹ Recovered Metric │      │  - Channel dispatch check │      │  - Stopping Rules & Limits     │  │
│  └───────────────────────┘      └───────────────────────────┘      └────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────────────────────────────────────┘
```

A detailed architectural breakdown is available in [**`ARCHITECTURE.md`**](file:///c:/Users/HP/OneDrive%20-%20Students.iiit.ac.in%20-%20IIIT%20Hyderabad/Desktop/Razorpay-buildathon/ARCHITECTURE.md).

---

## 📁 Repository Structure

```
Razorpay-buildathon/
├── README.md                      # Complete Project Documentation & Pitch
├── ARCHITECTURE.md                # System Architecture & Development Guide
├── pyproject.toml                 # Packaging & Dependencies
├── .env.example                   # Environment Configuration Template
├── compose.yaml                   # Docker Compose Specification
├── data/
│   ├── benchmark_batches/         # High-fidelity synthetic transaction batches
│   │   └── composite_batch_100.json
│   ├── razorpay_error_codes.json  # 40+ error taxonomy & bank health heuristics
│   └── compliance_rules.json      # RBI & DPDP compliance thresholds
├── src/
│   ├── run_service.py             # FastAPI Server Runner
│   ├── run_client.py              # Python SDK / CLI Harness
│   ├── streamlit_app.py           # Recovery Command Center UI
│   ├── core/
│   │   ├── settings.py            # Pydantic Settings with Razorpay configurations
│   │   ├── llm.py                 # Multi-LLM provider router (OpenAI, Gemini, Anthropic, Groq, Ollama)
│   │   └── telemetry.py           # Thread-safe Recovery KPI accumulator
│   ├── schema/
│   │   ├── recovery_schema.py     # Domain models for recovery, PTP, and batches
│   │   └── razorpay_schema.py     # Razorpay API and Webhook event schemas
│   ├── agents/
│   │   ├── orchestrator.py        # Master LangGraph Recovery Orchestrator
│   │   ├── detector.py            # Failure & Drop-off Root Cause Categorizer
│   │   ├── strategist.py          # Dynamic Intervention & Discount Planner
│   │   ├── governor.py            # Compliance, Dunning Bounds & Stopping Rules
│   │   ├── executor.py            # External actions (Razorpay API link generation & message dispatch)
│   │   ├── voice_recovery.py      # Hinglish Conversational AI Recovery Agent
│   │   └── audit_agent.py         # Cryptographic SHA-256 Audit Ledger & State Tracker
│   ├── integrations/
│   │   ├── razorpay_client.py     # Live & Mock Razorpay API Client (Payment Links, Mandates, Invoices)
│   │   ├── webhook_handler.py     # Razorpay Webhook Verifier & Idempotency Store
│   │   ├── channels/              # Communication channel adapters (WhatsApp, SMS, Voice, Email)
│   │   └── simulator.py           # Batch Simulation Engine
│   └── service/
│       ├── service.py             # FastAPI App mounting routers
│       └── recovery_router.py     # Hardened Revenue Recovery REST endpoints
└── tests/
    ├── unit/
    │   ├── test_detector.py
    │   ├── test_strategist.py
    │   ├── test_governor.py
    │   ├── test_executor.py       # Unit tests for the executor layer
    │   ├── test_webhook_idempotency.py # Tests for webhook verification & deduplication
    │   ├── test_state_machine.py  # Tests for RecoveryCaseStatus & PTP status transitions
    │   └── test_razorpay.py
    ├── integration/
    │   └── test_batch_recovery.py
    └── e2e/
        └── test_razorpay_test_mode.py # End-to-end integration tests using live Razorpay API
```

---

## ⚡ Quickstart Guide

### 1. Environment Setup
```bash
# Clone or navigate to the repository
cd Razorpay-buildathon

# Optional: Configure API keys in .env (Runs in Mock / Test mode by default)
cp .env.example .env
```

### 2. Run Automated Test Suite
Runs all unit, integration, and E2E mock/live tests:
```bash
python -m pytest -v
```

### 3. Launch Recovery Command Center Dashboard
```bash
streamlit run src/streamlit_app.py
```
Open **`http://localhost:8501`** in your browser to experience:
- 📊 **Executive Recovery KPI Dashboard** (₹ at risk, gross recovered, contact costs, net lift)
- 🚀 **1-Click Batch Benchmark Arena** (100 to 500 cases with baseline lift metrics)
- ⚡ **Live Event Ingestion & Webhook Simulator** (Immediate testing of failure scenarios & compliance stops)
- 💳 **Real Razorpay Test Mode Gateway** (Live link generation, query links & payments on Razorpay)
- 🎙️ **Hinglish AI Voice Call Sandbox** (Interactive phone call simulation & Promise-to-Pay logging)
- 🏢 **B2B Aging Invoices & Promise-to-Pay Ledger**
- 🛡️ **Cryptographic SHA-256 Regulatory Audit Trail**

### 4. Run the FastAPI Backend Service
```bash
python src/run_service.py
```
FastAPI endpoints available at **`http://localhost:8080`**:
- `POST /recovery/process` — Process single payment failure
- `POST /recovery/batch` — Run batch recovery on list of transactions
- `POST /recovery/benchmark/{name}` — Execute synthetic benchmark
- `POST /webhooks/razorpay` — Ingest live Razorpay webhooks (with HMAC verification + idempotency checks)
- `GET /analytics/kpis` — Real-time ₹ at risk vs ₹ recovered metrics
- `GET /audit/logs` — Query immutable audit ledger
- `GET /audit/verify` — Verify the SHA-256 chain integrity
- `POST /voice/simulate` — Simulate Hinglish conversational recovery turn

---

## 🛡️ Regulatory & Compliance Adherence

1. **RBI Recurring e-Mandate Circular**: Enforces mandatory 24-hour pre-debit notifications, a minimum 24-hour gap between automatic retry attempts, and a maximum of 3 automated retries per cycle.
2. **DPDP Act (Digital Personal Data Protection) 2023**:
   - **Quiet Hours**: No outbound promotional or dunning communications between 21:00 and 08:00 IST.
   - **Instant Opt-Out (DND)**: Immediate cessation of all messaging if customer replies with `STOP`, `UNSUBSCRIBE`, or requests no further contact.
   - **Dispute Shield**: Automated workflows freeze immediately when an invoice dispute is detected, routing the account to human specialist review.
   - **Promise to Pay**: Active commitments suppress collection reminders during the scheduled grace window.
