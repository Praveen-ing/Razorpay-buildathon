"""
Unit tests for MandateRetrySequencer — RevRecover AI
Tests RBI e-mandate dunning calendars, stopping rules, and step sequencing.
"""

import pytest
from agents.mandate_sequencer import (
    MandateRetrySequencer,
    DunningStepStatus,
)
from schema.recovery_schema import (
    CommunicationChannel,
    FailureCategory,
    TransactionFailureEvent,
)


@pytest.fixture
def sequencer():
    return MandateRetrySequencer()


@pytest.fixture
def base_subscription_event():
    return TransactionFailureEvent(
        transaction_id="txn_sub_test_001",
        customer_id="cust_sub_001",
        customer_name="Aarav Sharma",
        customer_email="aarav@example.com",
        customer_phone="+919876543210",
        amount=1499.0,
        currency="INR",
        category=FailureCategory.SUBSCRIPTION_CHURN,
        scenario="SUBSCRIPTION_AUTOPAY_FAILED",
        error_code="MANDATE_INSUFFICIENT_FUNDS",
        channel_consent=[
            CommunicationChannel.SMS,
            CommunicationChannel.WHATSAPP,
            CommunicationChannel.VOICE_HINGLISH,
            CommunicationChannel.EMAIL,
        ],
    )


def test_create_subscription_sequence(sequencer, base_subscription_event):
    seq = sequencer.create_sequence(base_subscription_event)
    assert seq.transaction_id == "txn_sub_test_001"
    assert len(seq.steps) == 5
    assert seq.steps[0].channel == CommunicationChannel.SILENT_API_RETRY
    assert seq.steps[1].channel == CommunicationChannel.SMS
    assert seq.steps[2].channel == CommunicationChannel.WHATSAPP
    assert seq.steps[3].channel == CommunicationChannel.VOICE_HINGLISH
    assert seq.status == "ACTIVE"


def test_voice_consent_suppression(sequencer, base_subscription_event):
    base_subscription_event.channel_consent = [
        CommunicationChannel.SMS,
        CommunicationChannel.WHATSAPP,
    ]
    seq = sequencer.create_sequence(base_subscription_event)
    voice_steps = [s for s in seq.steps if s.channel == CommunicationChannel.VOICE_HINGLISH]
    for vs in voice_steps:
        assert vs.status == DunningStepStatus.SKIPPED_COMPLIANCE
        assert "consent" in vs.outcome.lower()


def test_b2b_scenario_steps(sequencer):
    b2b_event = TransactionFailureEvent(
        transaction_id="txn_b2b_test_001",
        customer_id="cust_b2b_001",
        customer_name="TechCorp India Pvt Ltd",
        customer_email="ap@techcorp.in",
        customer_phone="+919988776655",
        amount=150000.0,
        currency="INR",
        category=FailureCategory.B2B_OVERDUE,
        scenario="B2B_INVOICE_OVERDUE",
        error_code="INVOICE_AGING_30_DAYS",
        channel_consent=[CommunicationChannel.EMAIL, CommunicationChannel.WHATSAPP],
    )
    seq = sequencer.create_sequence(b2b_event)
    assert len(seq.steps) == 5
    assert seq.steps[0].channel == CommunicationChannel.EMAIL
    assert seq.steps[1].channel == CommunicationChannel.WHATSAPP


def test_opt_out_hard_stop(sequencer, base_subscription_event):
    base_subscription_event.opted_out = True
    seq = sequencer.create_sequence(base_subscription_event)
    result = sequencer.simulate_sequence_execution(base_subscription_event, seq)
    assert result.status == "STOPPED"
    assert result.stop_reason == "CUSTOMER_OPT_OUT"
    assert result.total_recovered == 0.0


def test_fraud_suspected_hard_stop(sequencer, base_subscription_event):
    base_subscription_event.fraud_suspected = True
    seq = sequencer.create_sequence(base_subscription_event)
    result = sequencer.simulate_sequence_execution(base_subscription_event, seq)
    assert result.status == "STOPPED"
    assert result.stop_reason == "FRAUD_SUSPECTED"


def test_dispute_hard_stop(sequencer, base_subscription_event):
    base_subscription_event.disputed = True
    seq = sequencer.create_sequence(base_subscription_event)
    result = sequencer.simulate_sequence_execution(base_subscription_event, seq)
    assert result.status == "STOPPED"
    assert result.stop_reason == "ACTIVE_DISPUTE"


def test_sequence_summary_df_data(sequencer, base_subscription_event):
    seq = sequencer.create_sequence(base_subscription_event)
    rows = sequencer.get_sequence_summary_df_data([seq])
    assert len(rows) == len(seq.steps)
    assert "Customer" in rows[0]
    assert "Step Name" in rows[0]
    assert "Channel" in rows[0]
