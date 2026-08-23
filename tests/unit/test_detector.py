import pytest
from agents.detector import RevenueLeakageDetector
from schema.recovery_schema import (
    CustomerTier,
    FailureCategory,
    TransactionFailureEvent,
)


def test_detector_diagnose_gateway_timeout():
    detector = RevenueLeakageDetector()
    event = TransactionFailureEvent(
        transaction_id="txn_test_001",
        customer_id="cust_001",
        customer_phone="+919876543210",
        amount=14999.0,
        scenario="PAYMENT_FAILURE",
        error_code="BAD_REQUEST_PAYMENT_TIMED_OUT",
        bank="HDFC",
    )

    diagnosis = detector.diagnose(event)
    assert diagnosis.category == FailureCategory.TRANSIENT_GATEWAY
    assert diagnosis.is_retryable is True
    assert diagnosis.confidence >= 0.90
    assert diagnosis.bank_health_status in ["OPTIMAL", "MODERATE", "DEGRADED"]
    assert diagnosis.expected_recovery_probability >= 0.70
    assert diagnosis.churn_risk_if_contacted <= 0.10


def test_detector_diagnose_cart_abandonment():
    detector = RevenueLeakageDetector()
    event = TransactionFailureEvent(
        transaction_id="txn_test_002",
        customer_id="cust_002",
        customer_phone="+919876543210",
        customer_tier=CustomerTier.VIP_PLATINUM,
        amount=25000.0,
        scenario="CHECKOUT_ABANDONMENT",
        error_code="CHECKOUT_DROP_OFF",
        bank="ICICI",
        metadata={"intent_score": 0.95},
    )

    diagnosis = detector.diagnose(event)
    assert diagnosis.category == FailureCategory.CHECKOUT_ABANDONMENT
    assert diagnosis.customer_intent_score >= 0.90
    assert diagnosis.urgency_level in ["HIGH", "CRITICAL"]
    assert diagnosis.expected_recovery_probability > 0.60


def test_detector_diagnose_subscription_insufficient_funds():
    detector = RevenueLeakageDetector()
    event = TransactionFailureEvent(
        transaction_id="txn_test_003",
        customer_id="cust_003",
        customer_phone="+919876543210",
        amount=2999.0,
        scenario="RECURRING_SUBSCRIPTION",
        error_code="INSUFFICIENT_FUNDS",
        bank="SBI",
    )

    diagnosis = detector.diagnose(event)
    assert diagnosis.category == FailureCategory.STRUCTURAL_CHURN
    assert diagnosis.is_retryable is True


def test_detector_diagnose_fraud_suspected():
    detector = RevenueLeakageDetector()
    event = TransactionFailureEvent(
        transaction_id="txn_test_fraud",
        customer_id="cust_fraud",
        customer_phone="+919876543210",
        amount=45000.0,
        scenario="PAYMENT_FAILURE",
        error_code="FRAUD_SUSPECTED",
        fraud_suspected=True,
    )

    diagnosis = detector.diagnose(event)
    assert diagnosis.category == FailureCategory.FRAUD_RISK
    assert diagnosis.recoverable is False
    assert diagnosis.expected_recovery_probability == 0.0
    assert diagnosis.suggested_action == "hard_stop_no_contact"
