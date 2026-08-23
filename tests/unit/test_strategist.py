"""
Unit tests for the Intervention Strategist.

Verifies that:
  - Strategist selects the correct channel and recovery vector
  - Strategist correctly calculates Expected Value
  - Strategist does NOT create payment links (that is the Executor's job)
  - Strategist does NOT make Razorpay API calls
"""

import pytest
from agents.detector import RevenueLeakageDetector
from agents.strategist import InterventionStrategist
from schema.recovery_schema import (
    CommunicationChannel,
    CustomerTier,
    RecoveryVector,
    TransactionFailureEvent,
)


def test_strategist_plan_checkout_dropoff():
    """Strategist selects WhatsApp channel for checkout abandonment and calculates positive EV."""
    detector = RevenueLeakageDetector()
    strategist = InterventionStrategist()

    event = TransactionFailureEvent(
        transaction_id="txn_test_strat_01",
        customer_id="cust_001",
        customer_name="Priya Patel",
        customer_phone="+919812345678",
        customer_tier=CustomerTier.GOLD,
        amount=4500.0,
        scenario="CHECKOUT_ABANDONMENT",
        error_code="CHECKOUT_DROP_OFF",
    )

    diag = detector.diagnose(event)
    plan = strategist.plan_intervention(event, diag)

    assert plan.channel == CommunicationChannel.WHATSAPP
    assert plan.vector == RecoveryVector.WHATSAPP_ONE_CLICK_LINK
    assert plan.discount_pct_authorized > 0.0
    assert plan.expected_value_inr > 0.0
    assert plan.contact_cost_inr == 0.40

    # IMPORTANT: Strategist does NOT create payment links — that is the Executor's job.
    # razorpay_payment_link must be None here; Executor will populate it after Governor approval.
    assert plan.razorpay_payment_link is None, (
        "Strategist must NOT create Razorpay payment links. "
        "The Executor layer creates links after Governor approval. "
        "This separation ensures: Governor → Executor → Razorpay API."
    )


def test_strategist_plan_b2b_overdue_executive():
    """Strategist selects voice channel for large B2B enterprise overdue invoices."""
    detector = RevenueLeakageDetector()
    strategist = InterventionStrategist()

    event = TransactionFailureEvent(
        transaction_id="txn_test_strat_02",
        customer_id="cust_b2b_corp",
        customer_name="Bharat Steel Corporation",
        customer_phone="+919867890123",
        customer_tier=CustomerTier.ENTERPRISE,
        amount=185000.0,
        scenario="B2B_INVOICE_OVERDUE",
        error_code="INVOICE_OVERDUE_TIER_2",
    )

    diag = detector.diagnose(event)
    plan = strategist.plan_intervention(event, diag)

    assert plan.vector == RecoveryVector.B2B_EXECUTIVE_VOICE_SETTLEMENT
    assert plan.channel == CommunicationChannel.VOICE_HINGLISH
    assert len(plan.voice_script_hinglish) > 0
    assert plan.expected_value_inr > 10000.0
