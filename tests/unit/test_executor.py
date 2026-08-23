"""
Unit tests for the Executor layer.

Verifies:
  - Executor creates payment links (real or mock)
  - Executor returns explicit ChannelDeliveryStatus (NOT_CONFIGURED without provider)
  - Executor NEVER returns RECOVERED status — that requires webhook confirmation
  - Silent retry returns RETRY_SCHEDULED (no link)
  - Synthetic benchmark flag disables real API calls
"""

import sys
import os

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src"))

from agents.detector import RevenueLeakageDetector
from agents.executor import RecoveryExecutor
from agents.strategist import InterventionStrategist
from schema.recovery_schema import (
    ChannelDeliveryStatus,
    CommunicationChannel,
    ExecutionStatus,
    RecoveryVector,
    TransactionFailureEvent,
    CustomerTier,
)


def make_event(**kwargs) -> TransactionFailureEvent:
    defaults = dict(
        transaction_id="txn_exec_test_01",
        customer_id="cust_exec_001",
        customer_name="Test Customer",
        customer_phone="+919800000001",
        customer_email="test@example.com",
        amount=5000.0,
        scenario="PAYMENT_FAILURE",
        error_code="GATEWAY_ERROR",
    )
    defaults.update(kwargs)
    return TransactionFailureEvent(**defaults)


def test_executor_creates_mock_payment_link():
    """Executor creates a mock payment link when RAZORPAY_MOCK_MODE=true."""
    executor = RecoveryExecutor()
    detector = RevenueLeakageDetector()
    strategist = InterventionStrategist()

    event = make_event(amount=5000.0, scenario="PAYMENT_FAILURE", error_code="GATEWAY_ERROR",
                       attempt_count=1)  # attempt_count=1 ensures WhatsApp path, not silent retry
    diag = detector.diagnose(event)
    plan = strategist.plan_intervention(event, diag)

    result = executor.execute(event, plan, recovery_case_id="rcase_test_001", is_synthetic=False)

    # The executor should have created a payment link
    assert result.payment_link is not None, "Executor must create a payment link"
    assert result.payment_link.link_id is not None
    assert result.payment_link.short_url != ""
    assert result.status == ExecutionStatus.PAYMENT_LINK_CREATED


def test_executor_no_recovery_status_without_payment_evidence():
    """
    CRITICAL TEST: Executor must never produce a RECOVERED status.
    Only webhook confirmation (payment.captured) can mark recovery.
    """
    executor = RecoveryExecutor()
    detector = RevenueLeakageDetector()
    strategist = InterventionStrategist()

    event = make_event(amount=3000.0, attempt_count=1)
    diag = detector.diagnose(event)
    plan = strategist.plan_intervention(event, diag)

    result = executor.execute(event, plan, recovery_case_id="rcase_test_002", is_synthetic=False)

    # The executor creates the link/sends outreach — it does NOT mark as recovered
    assert result.status != ExecutionStatus.EXECUTION_FAILED
    # RECOVERED is not a valid ExecutionStatus — it's a RecoveryStatus set by orchestrator
    # via webhook reconciliation only
    assert "RECOVERED" not in result.status.value


def test_executor_channel_result_not_configured_without_provider():
    """Channel adapters must return NOT_CONFIGURED or MESSAGE_FORMATTED — never fake SENT."""
    executor = RecoveryExecutor()
    detector = RevenueLeakageDetector()
    strategist = InterventionStrategist()

    event = make_event(
        amount=5000.0,
        scenario="CHECKOUT_ABANDONMENT",
        error_code="CHECKOUT_DROP_OFF",
        attempt_count=1,
    )
    diag = detector.diagnose(event)
    plan = strategist.plan_intervention(event, diag)

    result = executor.execute(event, plan, recovery_case_id="rcase_test_003", is_synthetic=False)

    if result.channel_result is not None:
        # Without a real WhatsApp/SMS/Email provider, status must be MESSAGE_FORMATTED or NOT_CONFIGURED
        # It must NOT be SENT or DELIVERED (those require real provider confirmation)
        assert result.channel_result.status not in [
            ChannelDeliveryStatus.SENT,
            ChannelDeliveryStatus.DELIVERED,
        ], (
            f"Channel status '{result.channel_result.status}' implies successful delivery, "
            "but no provider is configured. Never fake success."
        )


def test_executor_silent_retry_has_no_payment_link():
    """Silent API retry should not create a payment link or send a message."""
    executor = RecoveryExecutor()
    detector = RevenueLeakageDetector()
    strategist = InterventionStrategist()

    # This event should trigger silent retry (transient gateway error, attempt 0)
    event = make_event(
        amount=2000.0,
        scenario="PAYMENT_FAILURE",
        error_code="BAD_REQUEST_PAYMENT_TIMED_OUT",
        attempt_count=0,
    )
    diag = detector.diagnose(event)
    plan = strategist.plan_intervention(event, diag)

    # If strategist chose silent retry, test executor accordingly
    if plan.vector == RecoveryVector.INSTANT_SMART_RETRY:
        result = executor.execute(event, plan, recovery_case_id="rcase_test_004", is_synthetic=False)
        assert result.status == ExecutionStatus.RETRY_SCHEDULED
        assert result.payment_link is None
        assert result.channel_result is None


def test_executor_synthetic_mode_skips_api_calls():
    """Synthetic (benchmark) mode must not create real payment links."""
    executor = RecoveryExecutor()
    detector = RevenueLeakageDetector()
    strategist = InterventionStrategist()

    event = make_event(amount=8000.0, attempt_count=1)
    diag = detector.diagnose(event)
    plan = strategist.plan_intervention(event, diag)

    result = executor.execute(event, plan, recovery_case_id="rcase_bench_001", is_synthetic=True)

    # Synthetic mode: no payment links created (the orchestrator uses probabilistic outcome)
    assert result.is_synthetic is True
    assert result.payment_link is None
