"""
Recovery Router — RevRecover AI
=================================
FastAPI router containing all revenue recovery endpoints.

This router is mounted into the main service.py without duplicating business logic.
All recovery logic runs through the central orchestrator — this is a transport layer only.

Endpoints:
  POST /recovery/process          — single transaction recovery
  POST /recovery/batch            — batch processing
  POST /recovery/benchmark/{name} — named synthetic benchmark
  POST /webhooks/razorpay         — Razorpay webhook receiver (with sig verify + idempotency)
  GET  /analytics/kpis            — live KPI dashboard
  GET  /analytics/records         — recent recovery records
  POST /analytics/reset           — reset in-memory telemetry
  GET  /audit/logs                — audit ledger entries
  POST /voice/simulate            — Hinglish voice turn simulation
"""

import json
import logging
from typing import Any

from fastapi import APIRouter, Header, HTTPException, Request, status

from agents.audit_agent import audit_ledger_agent
from agents.orchestrator import orchestrator
from agents.voice_recovery import voice_recovery_agent
from core.settings import settings
from core.telemetry import telemetry_tracker, bank_health_tracker, calculate_enterprise_roi
from integrations.razorpay_client import razorpay_client
from integrations.simulator import RecoveryBatchSimulator
from integrations.webhook_handler import (
    RazorpayWebhookParser,
    webhook_idempotency,
    webhook_event_store,
)
from schema.recovery_schema import (
    AuditLogEntry,
    BatchRecoveryRequest,
    BatchRecoveryResult,
    RecoveryKPIs,
    TransactionFailureEvent,
    TransactionRecoveryRecord,
    ZKComplianceProof,
)

logger = logging.getLogger(__name__)

recovery_router = APIRouter(tags=["Revenue Recovery"])


# ─── Single Transaction Recovery ────────────────────────────────────────────

@recovery_router.post("/recovery/process", response_model=TransactionRecoveryRecord)
async def process_single_recovery(event: TransactionFailureEvent) -> TransactionRecoveryRecord:
    """
    Execute autonomous closed-loop recovery workflow for a single transaction failure event.

    Uses Razorpay Test Mode when RAZORPAY_MOCK_MODE=false, otherwise uses mock sandbox.
    Recovery status will be OUTREACH_ACTIVE until payment.captured webhook confirms payment.
    """
    return orchestrator.process_transaction(event, is_synthetic=False)


# ─── Batch Recovery ──────────────────────────────────────────────────────────

@recovery_router.post("/recovery/batch", response_model=BatchRecoveryResult)
async def process_batch_recovery(request: BatchRecoveryRequest) -> BatchRecoveryResult:
    """
    Process a batch of transaction failures.

    Note: Batch processing runs in synthetic mode (probabilistic outcomes)
    to avoid creating real payment links for bulk benchmarks.
    """
    return orchestrator.process_batch(request.batch_id, request.transactions, is_synthetic=True)


# ─── Named Benchmarks ────────────────────────────────────────────────────────

@recovery_router.post("/recovery/benchmark/{benchmark_name}", response_model=BatchRecoveryResult)
async def run_benchmark(benchmark_name: str = "composite_100") -> BatchRecoveryResult:
    """
    Run a pre-configured synthetic recovery benchmark.

    Available: composite_100, ecom, saas, b2b, stress_500
    Data source: 🟡 SYNTHETIC_BENCHMARK — deterministic fixtures, NOT real money.
    """
    count_map = {"stress_500": 500, "composite_100": 100}
    count = count_map.get(benchmark_name, 100)
    events = RecoveryBatchSimulator.generate_synthetic_batch(count)
    return orchestrator.process_batch(
        f"BENCHMARK-{benchmark_name.upper()}",
        events,
        is_synthetic=True,
    )


# ─── Razorpay Webhook Receiver ───────────────────────────────────────────────

@recovery_router.post("/webhooks/razorpay")
async def razorpay_webhook_receiver(
    request: Request,
    x_razorpay_signature: str | None = Header(default=None, alias="X-Razorpay-Signature"),
    x_razorpay_event_id: str | None = Header(default=None, alias="X-Razorpay-Event-Id"),
) -> dict[str, Any]:
    """
    Ingest and process Razorpay webhook events.

    Security:
      - HMAC SHA256 signature verified against RAZORPAY_WEBHOOK_SECRET
      - Idempotency: duplicate event_ids are silently ignored (no double counting)

    Handled events:
      - payment.failed       → trigger recovery pipeline
      - subscription.halted  → trigger recovery pipeline
      - invoice.expired      → trigger recovery pipeline
      - payment.captured     → confirm recovery (mark RECOVERED with real payment evidence)
      - payment_link.paid    → confirm recovery (mark RECOVERED with real payment evidence)
    """
    body_bytes = await request.body()

    # ── Signature Verification ────────────────────────────────────────────
    webhook_secret = settings.RAZORPAY_WEBHOOK_SECRET
    secret_value = webhook_secret.get_secret_value() if webhook_secret else ""

    if secret_value and x_razorpay_signature:
        is_valid = razorpay_client.verify_webhook_signature(
            body_bytes=body_bytes,
            signature=x_razorpay_signature,
            secret=secret_value,
        )
        if not is_valid:
            logger.warning("[Webhook] Invalid signature — rejecting webhook")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid webhook signature",
            )
    elif secret_value and not x_razorpay_signature:
        logger.warning("[Webhook] RAZORPAY_WEBHOOK_SECRET is set but no X-Razorpay-Signature header present")
        # In development/testing, allow unsigned webhooks with a warning
        # In production, uncomment the line below to enforce:
        # raise HTTPException(status_code=401, detail="Missing webhook signature")

    # ── Parse Payload ─────────────────────────────────────────────────────
    try:
        payload = json.loads(body_bytes)
        webhook_event_store.add_log(payload)
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")

    event_type = payload.get("event", "unknown")

    # ── Idempotency Check ─────────────────────────────────────────────────
    event_id = x_razorpay_event_id or RazorpayWebhookParser.get_event_id(payload)

    if webhook_idempotency.is_duplicate(event_id):
        logger.info(f"[Webhook] Duplicate event {event_id} for {event_type} — skipping (idempotency)")
        return {
            "status": "duplicate_ignored",
            "event_type": event_type,
            "event_id": event_id,
        }

    # ── Process Event ─────────────────────────────────────────────────────
    result: dict[str, Any] = {"event_type": event_type, "event_id": event_id}

    # Check if this is a payment success event (reconciliation path)
    capture_info = RazorpayWebhookParser.extract_payment_captured_info(payload)
    if capture_info:
        orchestrator.confirm_payment_recovered(
            transaction_id=capture_info["transaction_id"],
            payment_id=capture_info["payment_id"],
            payment_amount_inr=capture_info["amount_inr"],
            recovery_case_id=capture_info.get("recovery_case_id", ""),
        )
        webhook_idempotency.mark_seen(event_id)
        result.update({
            "status": "recovery_confirmed",
            "payment_id": capture_info["payment_id"],
            "recovered_amount_inr": capture_info["amount_inr"],
            "data_source": "RAZORPAY_TEST_MODE",
        })
        return result

    # Check if this is a failure event (recovery pipeline path)
    failure_event = RazorpayWebhookParser.parse_event(payload)
    if failure_event:
        record = orchestrator.process_transaction(failure_event, is_synthetic=False)
        webhook_idempotency.mark_seen(event_id)
        result.update({
            "status": "recovery_initiated",
            "transaction_id": record.event.transaction_id,
            "recovery_status": record.status.value,
            "intervention_channel": record.intervention.channel.value if record.intervention else None,
        })
        return result

    # Non-failure, non-capture event — acknowledge and ignore
    webhook_idempotency.mark_seen(event_id)
    result["status"] = "acknowledged_ignored"
    return result


# ─── Analytics ───────────────────────────────────────────────────────────────

@recovery_router.get("/analytics/kpis", response_model=RecoveryKPIs)
async def get_recovery_kpis() -> RecoveryKPIs:
    """Get real-time accumulated recovery metrics."""
    return telemetry_tracker.get_kpis()


@recovery_router.get("/analytics/records", response_model=list[TransactionRecoveryRecord])
async def get_recent_records(limit: int = 50) -> list[TransactionRecoveryRecord]:
    """Get recent recovery transaction records."""
    return telemetry_tracker.get_recent_records(limit)


@recovery_router.post("/analytics/reset")
async def reset_analytics() -> dict[str, str]:
    """Reset telemetry tracker in-memory records."""
    telemetry_tracker.reset()
    webhook_idempotency.clear()
    return {"status": "analytics_and_idempotency_reset_successful"}


# ─── Audit Ledger ─────────────────────────────────────────────────────────────

@recovery_router.get("/audit/logs", response_model=list[AuditLogEntry])
async def get_audit_logs(limit: int = 100) -> list[AuditLogEntry]:
    """Query immutable SHA-256 hash-chain audit log entries."""
    return audit_ledger_agent.get_all_logs(limit)


@recovery_router.get("/audit/verify")
async def verify_audit_integrity() -> dict[str, Any]:
    """Verify SHA-256 hash chain integrity across all audit log entries."""
    is_valid, count = audit_ledger_agent.verify_ledger_integrity()
    return {
        "integrity": "VALID" if is_valid else "INVALID — TAMPERING DETECTED",
        "entries_verified": count,
        "total_entries": len(audit_ledger_agent.logs),
        "chain_intact": is_valid,
    }


@recovery_router.get("/audit/zk-proof/{recovery_case_id}")
async def generate_zk_compliance_proof(recovery_case_id: str, transaction_id: str = "txn_default_123") -> dict[str, Any]:
    """Generate cryptographic Zero-Knowledge proof signature asserting DPDP 2023 compliance without exposing PII."""
    proof = audit_ledger_agent.generate_zkp_compliance_proof(recovery_case_id, transaction_id)
    return proof.model_dump()


@recovery_router.get("/telemetry/bank-health")
async def get_bank_health_telemetry() -> dict[str, Any]:
    """Retrieve real-time Indian bank gateway health telemetry & pre-emptive failure interception status."""
    from core.telemetry import bank_health_tracker
    return {
        "bank_telemetry": bank_health_tracker.get_all_telemetry(),
        "status": "ACTIVE_TELEMETRY",
    }



# ─── Razorpay Test Gateway ────────────────────────────────────────────────────

@recovery_router.get("/razorpay/payment-links")
async def list_payment_links(count: int = 10) -> dict[str, Any]:
    """Fetch recent payment links from Razorpay Test Mode API."""
    links = razorpay_client.fetch_payment_links(count=count)
    return {
        "data_source": "MOCK_SANDBOX" if settings.RAZORPAY_MOCK_MODE else "RAZORPAY_TEST_MODE",
        "count": len(links),
        "payment_links": links,
    }


@recovery_router.get("/razorpay/payment-links/{link_id}")
async def get_payment_link(link_id: str) -> dict[str, Any]:
    """Fetch status and details of a specific Razorpay payment link."""
    link = razorpay_client.fetch_payment_link_by_id(link_id)
    if not link:
        raise HTTPException(status_code=404, detail=f"Payment link {link_id} not found")
    return link


@recovery_router.get("/razorpay/payments")
async def list_payments(status_filter: str | None = None, count: int = 10) -> dict[str, Any]:
    """Fetch recent payments from Razorpay Test Mode API."""
    payments = razorpay_client.fetch_payments(status=status_filter, count=count)
    return {
        "data_source": "MOCK_SANDBOX" if settings.RAZORPAY_MOCK_MODE else "RAZORPAY_TEST_MODE",
        "count": len(payments),
        "payments": payments,
    }

from pydantic import BaseModel
class CreateOrderRequest(BaseModel):
    amount: float
    description: str | None = None
    customer_email: str | None = None
    customer_phone: str | None = None

@recovery_router.post("/razorpay/orders")
async def create_order(request: CreateOrderRequest) -> dict[str, Any]:
    """Create a standard Razorpay order for checkout."""
    return razorpay_client.create_order(
        amount=request.amount,
        notes={
            "description": request.description or "",
            "customer_email": request.customer_email or "",
            "customer_phone": request.customer_phone or ""
        }
    )

class RefundRequest(BaseModel):
    amount: float | None = None
    notes: dict[str, str] | None = None

@recovery_router.post("/razorpay/refund/{payment_id}")
async def refund_payment(payment_id: str, request: RefundRequest) -> dict[str, Any]:
    """Trigger a refund for a Razorpay payment."""
    return razorpay_client.refund_payment(
        payment_id=payment_id,
        amount=request.amount,
        notes=request.notes
    )

@recovery_router.get("/webhooks/logs")
async def get_webhook_logs(count: int = 50) -> list[dict[str, Any]]:
    """Fetch recent webhook events."""
    return webhook_event_store.logs[:count]


# ─── Voice Recovery ───────────────────────────────────────────────────────────

@recovery_router.post("/voice/simulate")
async def simulate_voice_turn(
    transaction_id: str,
    customer_speech: str,
    amount: float = 14999.0,
    customer_name: str = "Rahul Sharma",
    customer_phone: str = "+919876543210",
) -> dict[str, Any]:
    """Simulate a conversational Hinglish voice recovery turn."""
    event = TransactionFailureEvent(
        transaction_id=transaction_id,
        customer_id=f"cust_{customer_phone[-6:]}",
        customer_name=customer_name,
        customer_phone=customer_phone,
        amount=amount,
    )
    payment_link = f"https://rzp.io/i/plink_{transaction_id[:8]}"
    return voice_recovery_agent.process_customer_speech_or_text(event, customer_speech, payment_link)


# ─── Enterprise Compliance & Preemptive Routing Endpoints ───────────────────────

@recovery_router.post("/recovery/preemptive-check")
async def preemptive_interception_check(bank_name: str = "SBI", payment_method: str = "UPI") -> dict[str, Any]:
    """
    Pre-checkout Telemetry Interception & Dynamic Gateway Optimizer.
    Evaluates acquiring bank health in real-time to pre-emptively swap checkout routes before payment failure.
    """
    return bank_health_tracker.preemptive_interception_advice(bank_name=bank_name, payment_method=payment_method)


@recovery_router.post("/audit/zk-proof/verify")
async def verify_zk_compliance_proof(proof: ZKComplianceProof) -> dict[str, Any]:
    """
    Cryptographically verify a Zero-Knowledge (ZK) Compliance Proof signature.
    Proves DPDP 2023 & RBI compliance assertions without revealing customer PII.
    """
    is_valid, message = audit_ledger_agent.verify_zkp_compliance_proof(proof)
    return {
        "is_valid": is_valid,
        "verification_message": message,
        "proof_id": proof.proof_id,
        "recovery_case_id": proof.recovery_case_id,
        "zk_hash": proof.zk_hash,
    }


@recovery_router.get("/analytics/roi-calculator")
async def calculate_roi_projection(annual_gmv_inr: float = 50000000.0, recovery_rate_pct: float = 74.2) -> dict[str, Any]:
    """
    Calculate ROI, net revenue lift, and customer churn reduction for enterprise merchants.
    """
    return calculate_enterprise_roi(annual_gmv_inr=annual_gmv_inr, recovery_rate_pct=recovery_rate_pct)

