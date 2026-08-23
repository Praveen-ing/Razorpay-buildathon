"""
Unit tests for Recovery State Machine and PTP lifecycle.

Verifies:
  - RecoveryCaseStatus enum is correctly defined
  - PTPStatus transitions are well-defined
  - Active PTP suppresses outreach (governor stopping rule 5)
  - PTP state transitions (PENDING → FULFILLED / BROKEN)
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src"))

import pytest
from datetime import datetime

from agents.governor import ComplianceGovernor
from schema.recovery_schema import (
    CommunicationChannel,
    ComplianceDecision,
    PTPStatus,
    PromiseToPayRecord,
    RecoveryCaseStatus,
    RecoveryIntervention,
    RecoveryVector,
    TransactionFailureEvent,
)


# ─── RecoveryCaseStatus State Machine ────────────────────────────────────────

def test_recovery_case_status_has_required_states():
    """All required states for the recovery lifecycle must be present."""
    required = {
        RecoveryCaseStatus.RECEIVED,
        RecoveryCaseStatus.DIAGNOSED,
        RecoveryCaseStatus.STRATEGIZED,
        RecoveryCaseStatus.GOVERNANCE_APPROVED,
        RecoveryCaseStatus.GOVERNANCE_BLOCKED,
        RecoveryCaseStatus.PAYMENT_LINK_CREATED,
        RecoveryCaseStatus.OUTREACH_SENT,
        RecoveryCaseStatus.PAYMENT_PENDING,
        RecoveryCaseStatus.RECOVERED,
        RecoveryCaseStatus.FAILED,
        RecoveryCaseStatus.EXPIRED,
        RecoveryCaseStatus.ESCALATED,
        RecoveryCaseStatus.PTP_ACTIVE,
    }
    actual = set(RecoveryCaseStatus)
    missing = required - actual
    assert not missing, f"Missing required states in RecoveryCaseStatus: {missing}"


def test_recovery_case_status_values_are_strings():
    """All state values must be non-empty strings (StrEnum)."""
    for state in RecoveryCaseStatus:
        assert isinstance(state.value, str)
        assert len(state.value) > 0


# ─── PTP Status State Machine ─────────────────────────────────────────────────

def test_ptp_status_has_required_states():
    """PTP lifecycle states must all be defined."""
    required = {
        PTPStatus.PROPOSED,
        PTPStatus.ACCEPTED,
        PTPStatus.PENDING,
        PTPStatus.FULFILLED,
        PTPStatus.BROKEN,
    }
    actual = set(PTPStatus)
    missing = required - actual
    assert not missing, f"Missing PTP states: {missing}"


def test_ptp_record_creation():
    """PromiseToPayRecord can be created with required fields."""
    ptp = PromiseToPayRecord(
        transaction_id="txn_b2b_001",
        customer_id="cust_corp_001",
        promised_amount=125000.0,
        promised_date="2026-08-26",
        status="PENDING",
        notes="CFO confirmed payment by Friday.",
    )
    assert ptp.promised_amount == 125000.0
    assert ptp.status == "PENDING"
    assert ptp.transaction_id == "txn_b2b_001"


def test_ptp_active_suppresses_outreach():
    """
    Critical: Active PTP must prevent new outreach (Governor rule 5).
    
    When a customer has an active promise-to-pay, the system must not
    send additional collection attempts during the grace window.
    """
    governor = ComplianceGovernor()

    event = TransactionFailureEvent(
        transaction_id="txn_ptp_test_01",
        customer_id="cust_ptp_001",
        customer_name="Reliable Corp",
        customer_phone="+919800000002",
        amount=75000.0,
        has_active_ptp=True,  # Active PTP
        scenario="B2B_INVOICE_OVERDUE",
        error_code="INVOICE_OVERDUE_TIER_2",
    )

    intervention = RecoveryIntervention(
        vector=RecoveryVector.B2B_POLITE_STATEMENT,
        channel=CommunicationChannel.EMAIL,
        expected_value_inr=60000.0,
        contact_cost_inr=0.05,
    )

    decision = governor.evaluate(event, intervention)

    assert decision.action_permitted is False, "Active PTP must block outreach"
    assert decision.triggered_stopping_rule == "STOP_PROMISE_TO_PAY_ACTIVE"


def test_ptp_fulfilled_allows_recovery():
    """
    After a PTP is fulfilled, the transaction should no longer have an active PTP.
    
    Tests that a fulfilled PTP does not suppress new recovery actions.
    """
    governor = ComplianceGovernor()

    # Event where PTP has been fulfilled (has_active_ptp=False)
    event = TransactionFailureEvent(
        transaction_id="txn_ptp_test_02",
        customer_id="cust_ptp_002",
        customer_name="New Customer",
        customer_phone="+919800000003",
        amount=10000.0,
        has_active_ptp=False,  # PTP fulfilled — not active
        scenario="PAYMENT_FAILURE",
        error_code="GATEWAY_ERROR",
    )

    intervention = RecoveryIntervention(
        vector=RecoveryVector.WHATSAPP_ONE_CLICK_LINK,
        channel=CommunicationChannel.WHATSAPP,
        expected_value_inr=8000.0,
        contact_cost_inr=0.40,
    )

    decision = governor.evaluate(event, intervention)
    # Should be allowed (no active PTP, standard payment failure)
    assert decision.triggered_stopping_rule != "STOP_PROMISE_TO_PAY_ACTIVE"


def test_ptp_record_defaults():
    """PromiseToPayRecord has sensible defaults."""
    ptp = PromiseToPayRecord(
        transaction_id="txn_default_ptp",
        customer_id="cust_default",
        promised_amount=5000.0,
        promised_date="Within 3 business days",
    )
    assert ptp.status == "PENDING"
    assert isinstance(ptp.recorded_at, datetime)
    assert ptp.notes == ""
