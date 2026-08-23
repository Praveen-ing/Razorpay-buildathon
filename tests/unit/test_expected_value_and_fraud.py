import pytest
from agents.audit_agent import audit_ledger_agent
from agents.detector import detector_agent
from agents.governor import governor_agent
from agents.orchestrator import orchestrator
from agents.strategist import strategist_agent
from schema.recovery_schema import (
    CommunicationChannel,
    CustomerTier,
    RecoveryStatus,
    TransactionFailureEvent,
)


def test_expected_value_calculation_and_decision():
    # Customer with high LTV, high churn sensitivity, small amount
    event = TransactionFailureEvent(
        transaction_id="txn_ev_01",
        customer_id="cust_high_ltv",
        customer_phone="+919876543210",
        customer_tier=CustomerTier.VIP_PLATINUM,
        customer_ltv=100000.0,
        amount=199.0,
        scenario="PAYMENT_FAILURE",
        error_code="BAD_REQUEST_PAYMENT_TIMED_OUT",
        attempt_count=2,
    )

    diag = detector_agent.diagnose(event)
    plan = strategist_agent.plan_intervention(event, diag)
    
    # Expected Value = (P(rec) * amt) - cost - (P(churn) * LTV)
    # With LTV = 100,000 and P(churn) >= 0.04, churn penalty >= 4,000, while gross recovery <= 199 -> negative EV!
    assert plan.expected_value_inr < 0.0
    
    decision = governor_agent.evaluate(event, plan)
    assert decision.action_permitted is False
    assert decision.triggered_stopping_rule == "STOP_NEGATIVE_EXPECTED_VALUE"


def test_cryptographic_audit_ledger_integrity():
    audit_ledger_agent.clear()
    
    # Create 5 sequenced logs
    for i in range(5):
        audit_ledger_agent.create_log(
            transaction_id=f"txn_{i}",
            customer_id=f"cust_{i}",
            agent_name="TestAgent",
            action_taken=f"ACTION_{i}",
            state_before="STATE_A",
            state_after="STATE_B",
            details={"step": i},
        )
    
    is_valid, count = audit_ledger_agent.verify_ledger_integrity()
    assert is_valid is True
    assert count == 5


def test_closed_loop_fraud_stop():
    event = TransactionFailureEvent(
        transaction_id="txn_fraud_999",
        customer_id="cust_fraud",
        customer_phone="+919876543210",
        amount=65000.0,
        fraud_suspected=True,
        error_code="FRAUD_SUSPECTED",
    )

    record = orchestrator.process_transaction(event)
    assert record.status == RecoveryStatus.STOPPED_FRAUD_RISK
    assert record.money_recovered == 0.0
    assert record.compliance.action_permitted is False
    assert record.compliance.triggered_stopping_rule == "STOP_FRAUD_SUSPECTED"
    assert len(record.audit_logs) >= 3
