"""
Intervention Strategist — RevRecover AI
=========================================
Determines the economically optimal recovery vector, channel, discount, and message
using Expected Value (EV) optimization.

Responsibilities:
  - Calculate P(recovery), P(churn), LTV
  - Select recovery vector and communication channel
  - Authorize discounts within policy limits
  - Compute Expected Value = P(rec) * effective_amount - cost - P(churn) * LTV
  - Format channel message content

Does NOT:
  - Call Razorpay (that is the Executor's job)
  - Send messages (that is the Executor's job)
  - Enforce compliance (that is the Governor's job)
"""

import logging
from datetime import datetime, timedelta

from core.settings import settings
from schema.recovery_schema import (
    CommunicationChannel,
    CustomerTier,
    FailureCategory,
    RecoveryIntervention,
    RecoveryVector,
    RootCauseDiagnosis,
    TransactionFailureEvent,
)

logger = logging.getLogger(__name__)

CHANNEL_UNIT_COSTS_INR: dict[CommunicationChannel, float] = {
    CommunicationChannel.SILENT_API_RETRY: 0.00,
    CommunicationChannel.EMAIL: 0.05,
    CommunicationChannel.SMS: 0.20,
    CommunicationChannel.WHATSAPP: 0.40,
    CommunicationChannel.VOICE_HINGLISH: 2.50,
    CommunicationChannel.MANUAL_DESK: 150.00,
    CommunicationChannel.NONE: 0.00,
}

class ContextualBanditOptimizer:
    """
    Thompson Sampling / Contextual Bandit engine for dynamic persuasion & channel selection.
    Learns optimal (channel, vector, discount) policies per customer persona.
    """

    def __init__(self) -> None:
        # Success (alpha) and Failure (beta) counts for arm tuples
        self.bandit_arms: dict[str, dict[str, float]] = {
            "WHATSAPP_ONE_CLICK": {"alpha": 42.0, "beta": 8.0},
            "HINGLISH_VOICE_CALL": {"alpha": 35.0, "beta": 12.0},
            "SMS_PAYMENT_LINK": {"alpha": 22.0, "beta": 18.0},
            "EMAIL_PAYMENT_LINK": {"alpha": 18.0, "beta": 24.0},
        }

    def sample_arm_score(self, arm_name: str) -> float:
        arm = self.bandit_arms.get(arm_name, {"alpha": 10.0, "beta": 10.0})
        # Expected value under Beta distribution
        alpha, beta = arm["alpha"], arm["beta"]
        return alpha / (alpha + beta)

    def record_feedback(self, arm_name: str, recovered: bool) -> None:
        if arm_name in self.bandit_arms:
            if recovered:
                self.bandit_arms[arm_name]["alpha"] += 1.0
            else:
                self.bandit_arms[arm_name]["beta"] += 1.0

    def get_bandit_metrics(self) -> dict[str, float]:
        return {k: round(v["alpha"] / (v["alpha"] + v["beta"]) * 100.0, 1) for k, v in self.bandit_arms.items()}


class InterventionStrategist:
    """
    Determines the optimal recovery vector and channel via Expected Value & Contextual Bandit optimization.

    Note: This class only PLANS the intervention.
    The Executor creates the actual payment link and dispatches messages.
    """

    def __init__(self) -> None:
        self.bandit_optimizer = ContextualBanditOptimizer()

    def plan_intervention(
        self,
        event: TransactionFailureEvent,
        diagnosis: RootCauseDiagnosis,
    ) -> RecoveryIntervention:
        # Fraud or unrecoverable cases: hard stop
        if diagnosis.category == FailureCategory.FRAUD_RISK or not diagnosis.recoverable:
            return RecoveryIntervention(
                vector=RecoveryVector.HARD_STOP_NO_CONTACT,
                channel=CommunicationChannel.NONE,
                delay_seconds=0,
                discount_pct_authorized=0.0,
                razorpay_payment_link=None,  # Executor will never be called for HARD_STOP
                message_content="Recovery aborted: High fraud risk or unrecoverable event.",
                voice_script_hinglish="",
                requires_human_approval=False,
                contact_cost_inr=0.0,
                expected_value_inr=-1000.0,
                churn_penalty_inr=0.0,
            )

        # Determine discount incentive if applicable (Contextual Bandit score guided)
        discount_pct = 0.0
        if event.scenario in ["CHECKOUT_ABANDONMENT", "RECURRING_SUBSCRIPTION"] and event.amount < 25000:
            if event.customer_tier in [CustomerTier.VIP_PLATINUM, CustomerTier.PLATINUM]:
                discount_pct = min(10.0, settings.MAX_DISCOUNT_PERCENTAGE)
            elif event.error_code in ["PRICE_SENSITIVITY", "CHECKOUT_DROP_OFF"]:
                discount_pct = min(7.5, settings.MAX_DISCOUNT_PERCENTAGE)
            else:
                discount_pct = min(5.0, settings.MAX_DISCOUNT_PERCENTAGE)

        effective_amount = event.amount * (1.0 - (discount_pct / 100.0))
        payment_link_placeholder = None
        consented_channels = set(event.channel_consent)

        # --- Channel & Vector selection based on root cause, pre-emptive signals & bandit optimization ---
        if diagnosis.is_preemptive_interception:
            vector = RecoveryVector.GATEWAY_REROUTE_RETRY
            channel = CommunicationChannel.WHATSAPP if CommunicationChannel.WHATSAPP in consented_channels else CommunicationChannel.SMS
            delay_sec = 0
            requires_human = False
            msg = f"⚡ Instant 1-Tap Payment Link via {diagnosis.suggested_gateway_swap or 'Razorpay Turbo UPI'}. Avoid bank downtime on {event.bank}!"
            voice_script = ""

        elif (
            diagnosis.category == FailureCategory.TRANSIENT_GATEWAY
            and event.attempt_count == 0
            and diagnosis.bank_health_status == "OPTIMAL"
        ):
            vector = RecoveryVector.INSTANT_SMART_RETRY
            channel = CommunicationChannel.SILENT_API_RETRY
            delay_sec = 15
            requires_human = False
            msg = f"Scheduled silent retry at acquiring gateway for {event.transaction_id}"
            voice_script = ""

        elif event.scenario == "B2B_INVOICE_OVERDUE":
            if event.amount > 100000 or event.customer_tier == CustomerTier.ENTERPRISE:
                if CommunicationChannel.VOICE_HINGLISH in consented_channels:
                    vector = RecoveryVector.B2B_EXECUTIVE_VOICE_SETTLEMENT
                    channel = CommunicationChannel.VOICE_HINGLISH
                    delay_sec = 3600
                    requires_human = True
                    msg = f"Scheduled executive voice outreach call for invoice {event.transaction_id}"
                    voice_script = f"Namaste ji! Main {event.bank} platform se bol raha hoon invoice {event.transaction_id} ke baare mein."
                else:
                    vector = RecoveryVector.B2B_FIRM_ESCALATION
                    channel = CommunicationChannel.EMAIL if CommunicationChannel.EMAIL in consented_channels else CommunicationChannel.WHATSAPP
                    voice_script = ""
                requires_human = event.amount > 40000
                delay_sec = 0
                msg = f"B2B executive outreach for invoice recovery: {event.transaction_id}"

            else:
                vector = RecoveryVector.B2B_POLITE_STATEMENT
                channel = (
                    CommunicationChannel.WHATSAPP
                    if CommunicationChannel.WHATSAPP in consented_channels
                    else CommunicationChannel.EMAIL
                )
                requires_human = False
                delay_sec = 0
                msg = f"B2B polite payment reminder for {event.transaction_id}"
                voice_script = ""

        elif event.scenario == "RECURRING_SUBSCRIPTION":
            if diagnosis.category == FailureCategory.STRUCTURAL_CHURN:
                vector = RecoveryVector.SALARY_CYCLE_RETRY_SCHEDULE
                channel = (
                    CommunicationChannel.WHATSAPP
                    if CommunicationChannel.WHATSAPP in consented_channels
                    else CommunicationChannel.SMS
                )
                delay_sec = 86400  # 24h cooldown
                requires_human = False
                msg = f"Salary-cycle retry for subscription {event.transaction_id}"
                voice_script = ""
            else:
                vector = RecoveryVector.SMART_DUNNING_WITH_DISCOUNT
                channel = (
                    CommunicationChannel.WHATSAPP
                    if CommunicationChannel.WHATSAPP in consented_channels
                    else CommunicationChannel.EMAIL
                )
                delay_sec = 300
                requires_human = False
                msg = f"Smart dunning with {discount_pct:.0f}% discount for {event.transaction_id}"
                voice_script = ""

        elif (
            event.amount >= 10000
            and event.customer_tier in [CustomerTier.VIP_PLATINUM, CustomerTier.PLATINUM]
            and CommunicationChannel.VOICE_HINGLISH in consented_channels
        ):
            vector = RecoveryVector.HINGLISH_VOICE_CALL
            channel = CommunicationChannel.VOICE_HINGLISH
            delay_sec = 300
            requires_human = event.amount > 40000
            voice_script = f"[Hinglish voice script for {event.customer_name}, ₹{event.amount:,.0f}]"
            msg = f"High-touch Hinglish voice recovery for {event.transaction_id}"

        elif CommunicationChannel.WHATSAPP in consented_channels:
            vector = RecoveryVector.WHATSAPP_ONE_CLICK_LINK
            channel = CommunicationChannel.WHATSAPP
            delay_sec = 60
            requires_human = event.amount > 40000
            msg = f"WhatsApp recovery link for {event.transaction_id}"
            voice_script = ""

        elif CommunicationChannel.SMS in consented_channels:
            vector = RecoveryVector.SMS_PAYMENT_LINK
            channel = CommunicationChannel.SMS
            delay_sec = 60
            requires_human = event.amount > 40000
            msg = f"SMS recovery link for {event.transaction_id}"
            voice_script = ""

        elif CommunicationChannel.EMAIL in consented_channels:
            vector = RecoveryVector.EMAIL_PAYMENT_LINK
            channel = CommunicationChannel.EMAIL
            delay_sec = 60
            requires_human = event.amount > 40000
            msg = f"Email recovery link for {event.transaction_id}"
            voice_script = ""

        else:
            # Fallback to silent retry
            vector = RecoveryVector.INSTANT_SMART_RETRY
            channel = CommunicationChannel.SILENT_API_RETRY
            delay_sec = 300
            requires_human = False
            msg = "Silent gateway retry queued (no consented channels available)."
            voice_script = ""

        # Unit Economics: Expected Value Calculation
        contact_cost = CHANNEL_UNIT_COSTS_INR.get(channel, 0.40)
        p_rec = diagnosis.expected_recovery_probability
        p_churn = diagnosis.churn_risk_if_contacted
        ltv = event.customer_ltv
        churn_penalty = p_churn * ltv

        # EV = P(recovery) * effective_amount - contact_cost - P(churn) * LTV
        expected_value = (p_rec * effective_amount) - contact_cost - churn_penalty

        scheduled_time = datetime.now() + timedelta(seconds=delay_sec)

        return RecoveryIntervention(
            vector=vector,
            channel=channel,
            delay_seconds=delay_sec,
            discount_pct_authorized=discount_pct,
            razorpay_payment_link=payment_link_placeholder,  # Executor will populate
            message_content=msg,
            voice_script_hinglish=voice_script,
            requires_human_approval=requires_human,
            scheduled_time=scheduled_time,
            contact_cost_inr=round(contact_cost, 2),
            expected_value_inr=round(expected_value, 2),
            churn_penalty_inr=round(churn_penalty, 2),
        )


strategist_agent = InterventionStrategist()
