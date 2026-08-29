import json
import logging
from pathlib import Path
from typing import Any

from schema.recovery_schema import (
    CustomerTier,
    FailureCategory,
    RootCauseDiagnosis,
    TransactionFailureEvent,
)

logger = logging.getLogger(__name__)


class RevenueLeakageDetector:
    """Agent that analyzes failure signals, error taxonomies, customer history, and bank telemetry to determine root causes and probabilistic recovery/churn metrics."""

    def __init__(self, error_tax_path: str | Path | None = None) -> None:
        if error_tax_path is None:
            error_tax_path = Path(__file__).resolve().parent.parent.parent / "data" / "razorpay_error_codes.json"
        self.error_tax_path = Path(error_tax_path)
        self.taxonomy: dict[str, Any] = self._load_taxonomy()

    def _load_taxonomy(self) -> dict[str, Any]:
        try:
            if self.error_tax_path.exists():
                with open(self.error_tax_path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Could not load error taxonomy file: {e}")
        return {"error_codes": {}, "bank_health_benchmarks": {}}

    def diagnose(self, event: TransactionFailureEvent) -> RootCauseDiagnosis:
        error_info = self.taxonomy.get("error_codes", {}).get(event.error_code, {})
        bank_benchmarks = self.taxonomy.get("bank_health_benchmarks", {})
        bank_health = bank_benchmarks.get(event.bank, {}).get("status", "OPTIMAL")

        # Fraud / high risk check
        is_fraud = event.fraud_suspected or event.error_code == "FRAUD_SUSPECTED"
        if is_fraud:
            return RootCauseDiagnosis(
                category=FailureCategory.FRAUD_RISK,
                confidence=0.98,
                is_retryable=False,
                recoverable=False,
                root_cause_explanation="High risk score or suspected fraudulent card activity detected by risk engine.",
                bank_health_status=bank_health,
                customer_intent_score=0.05,
                expected_recovery_probability=0.0,
                churn_risk_if_contacted=0.95,
                suggested_action="hard_stop_no_contact",
                urgency_level="CRITICAL",
            )

        # Category mapping
        cat_str = error_info.get("category", "")
        try:
            category = FailureCategory(cat_str)
        except ValueError:
            if event.scenario == "CHECKOUT_ABANDONMENT":
                category = FailureCategory.CHECKOUT_ABANDONMENT
            elif event.scenario == "RECURRING_SUBSCRIPTION":
                category = FailureCategory.SUBSCRIPTION_CHURN
            elif event.scenario == "B2B_INVOICE_OVERDUE":
                category = FailureCategory.B2B_OVERDUE
            else:
                category = FailureCategory.TRANSIENT_GATEWAY

        # Intent scoring heuristics
        intent_score = 0.82
        if event.customer_tier in [CustomerTier.VIP_PLATINUM, CustomerTier.PLATINUM, CustomerTier.ENTERPRISE]:
            intent_score += 0.10
        if event.past_successful_payments >= 5:
            intent_score += 0.06
        if event.scenario == "CHECKOUT_ABANDONMENT":
            intent_score = event.metadata.get("intent_score", 0.88)

        intent_score = min(1.0, intent_score)

        # Recovery Probability P(recovery) estimation based on root cause & context
        p_recovery = 0.70
        suggested_action = "send_razorpay_link"
        
        if event.error_code in ["BAD_REQUEST_PAYMENT_TIMED_OUT", "GATEWAY_ERROR", "UPI_APP_NOT_RESPONDING"]:
            p_recovery = 0.88 if bank_health == "OPTIMAL" else 0.76
            suggested_action = "instant_smart_retry"
        elif event.error_code in ["INSUFFICIENT_FUNDS"]:
            p_recovery = 0.65
            suggested_action = "salary_cycle_retry_schedule"
        elif event.error_code in ["CARD_EXPIRED", "MANDATE_EXPIRED"]:
            p_recovery = 0.72
            suggested_action = "send_card_or_mandate_update_link"
        elif event.error_code in ["DO_NOT_HONOR", "PAYMENT_DECLINED_BY_BANK"]:
            p_recovery = 0.68
            suggested_action = "send_alternate_payment_link"
        elif event.error_code in ["CHECKOUT_DROP_OFF", "PRICE_SENSITIVITY"]:
            p_recovery = 0.78
            suggested_action = "send_discount_incentive_link"
        elif event.scenario == "B2B_INVOICE_OVERDUE":
            p_recovery = 0.85 if event.past_successful_payments > 2 else 0.60
            suggested_action = "executive_voice_or_statement"

        # Churn risk if contacted P(churn)
        p_churn = 0.02
        if event.attempt_count >= 1:
            p_churn += 0.03 * event.attempt_count
        if event.customer_tier in [CustomerTier.VIP_PLATINUM, CustomerTier.PLATINUM]:
            p_churn += 0.01  # High value customers are slightly more sensitive to spam
        if event.scenario == "CHECKOUT_ABANDONMENT":
            p_churn = 0.01

        p_churn = min(0.35, p_churn)

        # Urgency level
        if event.amount > 50000 or event.scenario == "B2B_INVOICE_OVERDUE":
            urgency = "HIGH" if event.amount < 150000 else "CRITICAL"
        elif event.customer_tier in [CustomerTier.VIP_PLATINUM, CustomerTier.PLATINUM]:
            urgency = "HIGH"
        else:
            urgency = "MEDIUM"

        explanation = error_info.get(
            "description",
            f"Transaction interrupted during {event.payment_method} processing at {event.bank}."
        )
        is_retryable = error_info.get("retryable", True)

        # Check real-time live telemetry from BankHealthTracker
        from core.telemetry import bank_health_tracker
        live_telemetry = bank_health_tracker.get_bank_health(event.bank)
        live_bank_status = live_telemetry.get("status", bank_health)
        is_preemptive = live_bank_status in ["DEGRADED", "DOWN"]
        suggested_swap = live_telemetry.get("recommended_route", "Razorpay Turbo UPI / Flash Checkout") if is_preemptive else None

        if is_preemptive:
            bank_health = live_bank_status
            explanation = f"[PRE-EMPTIVE INTERCEPTION] Real-time telemetry flagged {event.bank} gateway as {live_bank_status} ({live_telemetry.get('success_rate_pct', 65.0)}% success rate). Recommending instant swap to {suggested_swap}."

        return RootCauseDiagnosis(
            category=category,
            confidence=0.96,
            is_retryable=is_retryable,
            recoverable=True,
            root_cause_explanation=explanation,
            bank_health_status=bank_health,
            customer_intent_score=round(intent_score, 2),
            expected_recovery_probability=round(p_recovery, 2),
            churn_risk_if_contacted=round(p_churn, 3),
            suggested_action=suggested_action,
            urgency_level=urgency,
            is_preemptive_interception=is_preemptive,
            suggested_gateway_swap=suggested_swap,
        )


detector_agent = RevenueLeakageDetector()

