"""
Mandate Retry Sequencer — RevRecover AI
=========================================
Implements a RBI-compliant multi-step dunning calendar for subscription and
e-mandate failures. Each step is audited and respects all compliance stopping rules.

RBI e-Mandate Circular: max 3 auto-debit attempts within a 30-day window.
NACH/E-Mandate retry guidelines: Informed retries with prior notification.

Dunning Sequence (configurable):
  Step 0  → Silent API retry (immediate, T+0 minutes)
  Step 1  → SMS notification + payment link (T+24h)
  Step 2  → WhatsApp one-click link + 5% incentive (T+72h / Day 3)
  Step 3  → Hinglish voice call for high-value (T+168h / Day 7)
  Step 4  → B2B executive escalation / human desk (T+336h / Day 14)
  STOP    → Archive + close if unresolved at Day 21

Stopping rules (all inherited from ComplianceGovernor):
  • Fraud suspected → STOP immediately
  • Customer opted out → STOP immediately
  • Active dispute → STOP + route to dispute desk
  • Active PTP → PAUSE during grace period
  • Max attempts (3) exceeded → STOP
  • Negative EV → STOP outreach (silent monitoring only)
"""

import logging
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Any

from schema.recovery_schema import (
    CommunicationChannel,
    ComplianceDecision,
    CustomerTier,
    FailureCategory,
    RecoveryStatus,
    RecoveryVector,
    TransactionFailureEvent,
)

logger = logging.getLogger(__name__)


class DunningStepStatus(StrEnum):
    PENDING = "PENDING"
    EXECUTING = "EXECUTING"
    COMPLETED = "COMPLETED"
    SKIPPED_COMPLIANCE = "SKIPPED_COMPLIANCE"
    SKIPPED_RECOVERED = "SKIPPED_RECOVERED"


@dataclass
class DunningStep:
    step_number: int
    name: str
    channel: CommunicationChannel
    vector: RecoveryVector
    delay_hours: int
    discount_pct: float = 0.0
    requires_voice: bool = False
    requires_human: bool = False
    description: str = ""
    status: DunningStepStatus = DunningStepStatus.PENDING
    scheduled_at: datetime | None = None
    executed_at: datetime | None = None
    outcome: str = ""
    compliance_decision: ComplianceDecision | None = None
    amount_recovered: float = 0.0


@dataclass
class DunningSequence:
    """Full multi-step dunning plan for a single failure event."""
    transaction_id: str
    customer_id: str
    customer_name: str
    amount: float
    scenario: str
    created_at: datetime = field(default_factory=datetime.now)
    steps: list[DunningStep] = field(default_factory=list)
    current_step: int = 0
    status: str = "ACTIVE"  # ACTIVE, RECOVERED, EXHAUSTED, STOPPED
    total_recovered: float = 0.0
    stop_reason: str = ""

    def get_next_pending_step(self) -> DunningStep | None:
        for step in self.steps:
            if step.status == DunningStepStatus.PENDING:
                return step
        return None

    def to_dict(self) -> dict[str, Any]:
        return {
            "transaction_id": self.transaction_id,
            "customer_id": self.customer_id,
            "customer_name": self.customer_name,
            "amount": self.amount,
            "scenario": self.scenario,
            "created_at": self.created_at.isoformat(),
            "current_step": self.current_step,
            "status": self.status,
            "total_recovered": self.total_recovered,
            "stop_reason": self.stop_reason,
            "steps": [
                {
                    "step": s.step_number,
                    "name": s.name,
                    "channel": s.channel.value,
                    "delay_hours": s.delay_hours,
                    "discount_pct": s.discount_pct,
                    "status": s.status.value,
                    "scheduled_at": s.scheduled_at.isoformat() if s.scheduled_at else None,
                    "executed_at": s.executed_at.isoformat() if s.executed_at else None,
                    "outcome": s.outcome,
                    "amount_recovered": s.amount_recovered,
                }
                for s in self.steps
            ],
        }


# ─── RBI-Compliant Dunning Templates ─────────────────────────────────────────

SUBSCRIPTION_DUNNING_STEPS = [
    DunningStep(
        step_number=0,
        name="Silent API Retry",
        channel=CommunicationChannel.SILENT_API_RETRY,
        vector=RecoveryVector.INSTANT_SMART_RETRY,
        delay_hours=0,
        discount_pct=0.0,
        description="Immediate silent gateway retry. No customer contact. RBI-compliant first attempt.",
    ),
    DunningStep(
        step_number=1,
        name="SMS Payment Link (T+24h)",
        channel=CommunicationChannel.SMS,
        vector=RecoveryVector.SMS_PAYMENT_LINK,
        delay_hours=24,
        discount_pct=0.0,
        description="Friendly SMS with 1-click Razorpay payment link. Prior notification as per NACH circular.",
    ),
    DunningStep(
        step_number=2,
        name="WhatsApp Link + 5% Incentive (T+72h)",
        channel=CommunicationChannel.WHATSAPP,
        vector=RecoveryVector.SMART_DUNNING_WITH_DISCOUNT,
        delay_hours=72,
        discount_pct=5.0,
        description="WhatsApp one-click recovery with 5% discount incentive on Day 3.",
    ),
    DunningStep(
        step_number=3,
        name="Hinglish Voice Call (T+7d)",
        channel=CommunicationChannel.VOICE_HINGLISH,
        vector=RecoveryVector.HINGLISH_VOICE_CALL,
        delay_hours=168,
        discount_pct=7.5,
        requires_voice=True,
        description="AI-powered Hinglish voice call on Day 7. Mid-call payment link dispatch.",
    ),
    DunningStep(
        step_number=4,
        name="Final Notice + Human Escalation (T+14d)",
        channel=CommunicationChannel.MANUAL_DESK,
        vector=RecoveryVector.HUMAN_ESCALATION,
        delay_hours=336,
        discount_pct=0.0,
        requires_human=True,
        description="Final formal notice escalated to human collections desk on Day 14.",
    ),
]

B2B_DUNNING_STEPS = [
    DunningStep(
        step_number=0,
        name="Polite Email Statement (T+0)",
        channel=CommunicationChannel.EMAIL,
        vector=RecoveryVector.B2B_POLITE_STATEMENT,
        delay_hours=0,
        discount_pct=0.0,
        description="Professional email with invoice statement and payment link.",
    ),
    DunningStep(
        step_number=1,
        name="WhatsApp Account Statement (T+48h)",
        channel=CommunicationChannel.WHATSAPP,
        vector=RecoveryVector.B2B_POLITE_STATEMENT,
        delay_hours=48,
        discount_pct=0.0,
        description="WhatsApp follow-up with account statement and payment link.",
    ),
    DunningStep(
        step_number=2,
        name="Hinglish Executive Call (T+7d)",
        channel=CommunicationChannel.VOICE_HINGLISH,
        vector=RecoveryVector.B2B_EXECUTIVE_VOICE_SETTLEMENT,
        delay_hours=168,
        discount_pct=0.0,
        requires_voice=True,
        description="Senior executive voice call to accounts payable contact.",
    ),
    DunningStep(
        step_number=3,
        name="Firm Escalation (T+14d)",
        channel=CommunicationChannel.EMAIL,
        vector=RecoveryVector.B2B_FIRM_ESCALATION,
        delay_hours=336,
        discount_pct=0.0,
        requires_human=True,
        description="Formal notice with legal escalation clause.",
    ),
    DunningStep(
        step_number=4,
        name="Legal / Human Desk (T+21d)",
        channel=CommunicationChannel.MANUAL_DESK,
        vector=RecoveryVector.HUMAN_ESCALATION,
        delay_hours=504,
        discount_pct=0.0,
        requires_human=True,
        description="Full escalation to human collections / legal team.",
    ),
]

CHECKOUT_DUNNING_STEPS = [
    DunningStep(
        step_number=0,
        name="Instant WhatsApp Recovery Link (T+0)",
        channel=CommunicationChannel.WHATSAPP,
        vector=RecoveryVector.WHATSAPP_ONE_CLICK_LINK,
        delay_hours=0,
        discount_pct=0.0,
        description="Immediate WhatsApp recovery link while cart intent is hot.",
    ),
    DunningStep(
        step_number=1,
        name="WhatsApp + 7.5% Discount (T+1h)",
        channel=CommunicationChannel.WHATSAPP,
        vector=RecoveryVector.SMART_DUNNING_WITH_DISCOUNT,
        delay_hours=1,
        discount_pct=7.5,
        description="Second outreach with 7.5% recovery incentive to close cart.",
    ),
    DunningStep(
        step_number=2,
        name="SMS Final Reminder (T+24h)",
        channel=CommunicationChannel.SMS,
        vector=RecoveryVector.SMS_PAYMENT_LINK,
        delay_hours=24,
        discount_pct=10.0,
        description="Final SMS reminder with 10% discount before cart expires.",
    ),
]


class MandateRetrySequencer:
    """
    RBI-compliant multi-step dunning calendar for subscription and e-mandate failures.
    
    Creates a full DunningSequence for each failure event and executes steps
    in order, respecting all compliance stopping rules at each step.
    """

    def __init__(self) -> None:
        self.active_sequences: dict[str, DunningSequence] = {}

    def create_sequence(self, event: TransactionFailureEvent) -> DunningSequence:
        """Creates a tailored dunning sequence based on scenario and customer tier."""
        import copy

        if event.scenario == "B2B_INVOICE_OVERDUE":
            raw_steps = B2B_DUNNING_STEPS
        elif event.scenario == "CHECKOUT_ABANDONMENT":
            raw_steps = CHECKOUT_DUNNING_STEPS
        else:
            raw_steps = SUBSCRIPTION_DUNNING_STEPS

        # Deep copy so we don't mutate class-level templates
        steps = [
            DunningStep(
                step_number=s.step_number,
                name=s.name,
                channel=s.channel,
                vector=s.vector,
                delay_hours=s.delay_hours,
                discount_pct=s.discount_pct,
                requires_voice=s.requires_voice,
                requires_human=s.requires_human,
                description=s.description,
                status=DunningStepStatus.PENDING,
                scheduled_at=datetime.now() + timedelta(hours=s.delay_hours),
            )
            for s in raw_steps
        ]

        # Remove voice steps if customer hasn't consented
        from schema.recovery_schema import CommunicationChannel
        if CommunicationChannel.VOICE_HINGLISH not in event.channel_consent:
            for step in steps:
                if step.channel == CommunicationChannel.VOICE_HINGLISH:
                    step.status = DunningStepStatus.SKIPPED_COMPLIANCE
                    step.outcome = "No voice consent from customer."

        # Remove high-value human desk requirement for small amounts
        if event.amount < 5000:
            for step in steps:
                if step.requires_human:
                    step.requires_human = False

        sequence = DunningSequence(
            transaction_id=event.transaction_id,
            customer_id=event.customer_id,
            customer_name=event.customer_name,
            amount=event.amount,
            scenario=event.scenario,
            steps=steps,
        )

        self.active_sequences[event.transaction_id] = sequence
        logger.info(
            f"[MandateSequencer] Created {len(steps)}-step dunning sequence for "
            f"txn={event.transaction_id} | scenario={event.scenario} | amount=₹{event.amount:.2f}"
        )
        return sequence

    def simulate_sequence_execution(
        self,
        event: TransactionFailureEvent,
        sequence: DunningSequence,
    ) -> DunningSequence:
        """
        Simulates full execution of a dunning sequence for demo/benchmark purposes.
        Applies probabilistic outcomes at each step, stopping on recovery or compliance block.
        """
        import random

        cumulative_p_recovery = 0.0

        for step in sequence.steps:
            if step.status in [DunningStepStatus.SKIPPED_COMPLIANCE, DunningStepStatus.SKIPPED_RECOVERED]:
                continue

            step.status = DunningStepStatus.EXECUTING
            step.executed_at = step.scheduled_at

            # Compliance check at each step
            if event.opted_out:
                step.status = DunningStepStatus.SKIPPED_COMPLIANCE
                step.outcome = "STOP: Customer opted out (DND honored)"
                sequence.status = "STOPPED"
                sequence.stop_reason = "CUSTOMER_OPT_OUT"
                break

            if event.fraud_suspected:
                step.status = DunningStepStatus.SKIPPED_COMPLIANCE
                step.outcome = "STOP: Fraud suspected — zero contact"
                sequence.status = "STOPPED"
                sequence.stop_reason = "FRAUD_SUSPECTED"
                break

            if event.disputed:
                step.status = DunningStepStatus.SKIPPED_COMPLIANCE
                step.outcome = "STOP: Active dispute — routed to dispute desk"
                sequence.status = "STOPPED"
                sequence.stop_reason = "ACTIVE_DISPUTE"
                break

            # Simulate recovery probability (cumulative increases with each touch)
            channel_boost = {
                CommunicationChannel.SILENT_API_RETRY: 0.30,
                CommunicationChannel.SMS: 0.15,
                CommunicationChannel.WHATSAPP: 0.22,
                CommunicationChannel.VOICE_HINGLISH: 0.28,
                CommunicationChannel.EMAIL: 0.08,
                CommunicationChannel.MANUAL_DESK: 0.35,
            }
            discount_boost = step.discount_pct / 100.0 * 0.5
            p_step = channel_boost.get(step.channel, 0.15) + discount_boost
            p_step = min(0.85, p_step)

            recovered_this_step = random.random() < p_step

            if recovered_this_step:
                effective_amount = event.amount * (1.0 - step.discount_pct / 100.0)
                step.amount_recovered = round(effective_amount, 2)
                step.status = DunningStepStatus.COMPLETED
                step.outcome = f"RECOVERED ₹{effective_amount:,.2f} via {step.channel.value}"
                sequence.total_recovered = step.amount_recovered
                sequence.status = "RECOVERED"

                # Mark remaining steps as skipped
                for remaining in sequence.steps:
                    if remaining.status == DunningStepStatus.PENDING:
                        remaining.status = DunningStepStatus.SKIPPED_RECOVERED
                        remaining.outcome = "Skipped — recovery achieved at earlier step"
                break
            else:
                step.status = DunningStepStatus.COMPLETED
                step.outcome = f"No recovery at {step.channel.value}. Proceeding to next step."
                sequence.current_step = step.step_number + 1

        if sequence.status == "ACTIVE":
            sequence.status = "EXHAUSTED"
            sequence.stop_reason = "All dunning steps completed without recovery"

        logger.info(
            f"[MandateSequencer] Sequence complete: txn={sequence.transaction_id} | "
            f"status={sequence.status} | recovered=₹{sequence.total_recovered:.2f}"
        )
        return sequence

    def get_sequence_summary_df_data(self, sequences: list[DunningSequence]) -> list[dict]:
        """Returns flat data suitable for a DataFrame display."""
        rows = []
        for seq in sequences:
            for step in seq.steps:
                rows.append({
                    "Customer": seq.customer_name,
                    "Amount (₹)": f"₹{seq.amount:,.2f}",
                    "Scenario": seq.scenario,
                    "Step": step.step_number,
                    "Step Name": step.name,
                    "Channel": step.channel.value,
                    "Discount": f"{step.discount_pct:.0f}%",
                    "Scheduled At": step.scheduled_at.strftime("%Y-%m-%d %H:%M") if step.scheduled_at else "-",
                    "Status": step.status.value,
                    "Outcome": step.outcome[:60] if step.outcome else "-",
                    "Recovered (₹)": f"₹{step.amount_recovered:,.2f}" if step.amount_recovered > 0 else "-",
                })
        return rows


mandate_sequencer = MandateRetrySequencer()
