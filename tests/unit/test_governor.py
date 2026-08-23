import pytest
from agents.governor import ComplianceGovernor
from schema.recovery_schema import (
    CommunicationChannel,
    RecoveryIntervention,
    RecoveryVector,
    TransactionFailureEvent,
)


def test_governor_stopping_rule_dnd_opt_out():
    gov = ComplianceGovernor()
    event = TransactionFailureEvent(
        transaction_id="txn_gov_01",
        customer_id="cust_01",
        customer_phone="+919876543210",
        amount=5000.0,
        opted_out=True,
    )
    intervention = RecoveryIntervention(
        vector=RecoveryVector.WHATSAPP_ONE_CLICK_LINK,
        channel=CommunicationChannel.WHATSAPP,
    )

    decision = gov.evaluate(event, intervention)
    assert decision.action_permitted is False
    assert decision.triggered_stopping_rule == "STOP_CUSTOMER_OPT_OUT"


def test_governor_stopping_rule_dispute():
    gov = ComplianceGovernor()
    event = TransactionFailureEvent(
        transaction_id="txn_gov_02",
        customer_id="cust_02",
        customer_phone="+919876543210",
        amount=25000.0,
        disputed=True,
    )
    intervention = RecoveryIntervention(
        vector=RecoveryVector.B2B_POLITE_STATEMENT,
        channel=CommunicationChannel.WHATSAPP,
    )

    decision = gov.evaluate(event, intervention)
    assert decision.action_permitted is False
    assert decision.triggered_stopping_rule == "STOP_DISPUTE_RAISED"


def test_governor_stopping_rule_max_attempts():
    gov = ComplianceGovernor()
    event = TransactionFailureEvent(
        transaction_id="txn_gov_03",
        customer_id="cust_03",
        customer_phone="+919876543210",
        amount=1200.0,
        attempt_count=3,
    )
    intervention = RecoveryIntervention(
        vector=RecoveryVector.SMS_PAYMENT_LINK,
        channel=CommunicationChannel.SMS,
    )

    decision = gov.evaluate(event, intervention)
    assert decision.action_permitted is False
    assert decision.triggered_stopping_rule == "STOP_MAX_ATTEMPTS_EXCEEDED"


def test_governor_stopping_rule_fraud():
    gov = ComplianceGovernor()
    event = TransactionFailureEvent(
        transaction_id="txn_gov_04",
        customer_id="cust_04",
        customer_phone="+919876543210",
        amount=35000.0,
        fraud_suspected=True,
    )
    intervention = RecoveryIntervention(
        vector=RecoveryVector.HARD_STOP_NO_CONTACT,
        channel=CommunicationChannel.NONE,
    )

    decision = gov.evaluate(event, intervention)
    assert decision.action_permitted is False
    assert decision.triggered_stopping_rule == "STOP_FRAUD_SUSPECTED"


def test_governor_stopping_rule_negative_ev():
    gov = ComplianceGovernor()
    event = TransactionFailureEvent(
        transaction_id="txn_gov_05",
        customer_id="cust_05",
        customer_phone="+919876543210",
        amount=299.0,
        attempt_count=1,
    )
    intervention = RecoveryIntervention(
        vector=RecoveryVector.WHATSAPP_ONE_CLICK_LINK,
        channel=CommunicationChannel.WHATSAPP,
        expected_value_inr=-15.50,
    )

    decision = gov.evaluate(event, intervention)
    assert decision.action_permitted is False
    assert decision.triggered_stopping_rule == "STOP_NEGATIVE_EXPECTED_VALUE"
