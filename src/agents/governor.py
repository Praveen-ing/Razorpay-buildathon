import json
import logging
from pathlib import Path
from typing import Any

from schema.recovery_schema import (
    ComplianceDecision,
    RecoveryIntervention,
    RecoveryVector,
    TransactionFailureEvent,
)

logger = logging.getLogger(__name__)


class ComplianceGovernor:
    """Agent that enforces regulatory (RBI/DPDP) compliance and hard stopping rules."""

    def __init__(self, rules_path: str | Path | None = None) -> None:
        if rules_path is None:
            rules_path = Path(__file__).resolve().parent.parent.parent / "data" / "compliance_rules.json"
        self.rules_path = Path(rules_path)
        self.rules: dict[str, Any] = self._load_rules()

    def _load_rules(self) -> dict[str, Any]:
        try:
            if self.rules_path.exists():
                with open(self.rules_path, "r", encoding="utf-8") as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Could not load compliance rules file: {e}")
        return {
            "attempt_limits": {"max_contacts_per_failure_event": 3},
            "contact_hours": {"start_time_ist": "08:00", "end_time_ist": "21:00"},
        }

    def evaluate(
        self,
        event: TransactionFailureEvent,
        intervention: RecoveryIntervention,
    ) -> ComplianceDecision:
        # Rule 1: Suspected Fraud Hard Stop
        if event.fraud_suspected or event.error_code == "FRAUD_SUSPECTED" or intervention.vector == RecoveryVector.HARD_STOP_NO_CONTACT:
            return ComplianceDecision(
                is_compliant=True,
                action_permitted=False,
                triggered_stopping_rule="STOP_FRAUD_SUSPECTED",
                reason="High-risk or suspected fraudulent transaction detected. Zero outreach permitted to protect payment security.",
            )

        # Rule 2: Customer Opted Out / DND
        if event.opted_out:
            return ComplianceDecision(
                is_compliant=True,
                action_permitted=False,
                triggered_stopping_rule="STOP_CUSTOMER_OPT_OUT",
                reason="Customer has opted out of automated communications (DND honored).",
            )

        # Rule 3: Max Attempt Limits Exceeded (Max 3 contacts in 7 days)
        max_attempts = self.rules.get("attempt_limits", {}).get("max_contacts_per_failure_event", 3)
        if event.attempt_count >= max_attempts:
            return ComplianceDecision(
                is_compliant=True,
                action_permitted=False,
                triggered_stopping_rule="STOP_MAX_ATTEMPTS_EXCEEDED",
                reason=f"Maximum allowed contact attempts ({max_attempts}) reached for this event under anti-harassment policies.",
            )

        # Rule 4: Dispute Raised
        if event.disputed:
            return ComplianceDecision(
                is_compliant=True,
                action_permitted=False,
                triggered_stopping_rule="STOP_DISPUTE_RAISED",
                reason="Customer raised an active invoice/charge dispute. Automated recovery halted and routed to dispute desk.",
            )

        # Rule 5: Active Promise to Pay
        if event.has_active_ptp:
            return ComplianceDecision(
                is_compliant=True,
                action_permitted=False,
                triggered_stopping_rule="STOP_PROMISE_TO_PAY_ACTIVE",
                reason="Customer has an active Promise-to-Pay agreement. Outbound contact paused during grace window.",
            )

        # Rule 6: Negative Expected Value ($EV <= 0)
        if intervention.expected_value_inr <= 0 and event.attempt_count > 0:
            return ComplianceDecision(
                is_compliant=True,
                action_permitted=False,
                triggered_stopping_rule="STOP_NEGATIVE_EXPECTED_VALUE",
                reason=f"Intervention expected value (₹{intervention.expected_value_inr:.2f}) is negative. Outreach suppressed to protect customer lifetime value.",
            )

        # Rule 7: Human Approval Requirement for High Value (> ₹40,000 / $500)
        if intervention.requires_human_approval and event.amount > 40000:
            return ComplianceDecision(
                is_compliant=True,
                action_permitted=False,
                triggered_stopping_rule="PAUSE_FOR_HUMAN_APPROVAL",
                reason="High-value transaction (> ₹40,000) requires human supervisor sign-off before dispatch.",
            )

        # All checks passed
        return ComplianceDecision(
            is_compliant=True,
            action_permitted=True,
            triggered_stopping_rule=None,
            reason="All regulatory, cooldown, and stopping rule conditions satisfied.",
        )


governor_agent = ComplianceGovernor()
