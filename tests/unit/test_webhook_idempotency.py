"""
Unit tests for webhook idempotency and payment capture reconciliation.

Verifies:
  - Duplicate webhooks are silently deduplicated (no double-count)
  - payment.captured webhook extracts correct payment info
  - payment_link.paid webhook extracts correct payment info
  - Non-failure events are properly routed to reconciliation path
"""

import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../src"))

import pytest
from integrations.webhook_handler import (
    RazorpayWebhookParser,
    WebhookIdempotencyStore,
)


# ─── Idempotency Store Tests ─────────────────────────────────────────────────

def test_idempotency_store_first_event_is_not_duplicate():
    store = WebhookIdempotencyStore()
    assert store.is_duplicate("evt_test_001") is False


def test_idempotency_store_marks_and_detects_duplicate():
    store = WebhookIdempotencyStore()
    store.mark_seen("evt_test_001")
    assert store.is_duplicate("evt_test_001") is True


def test_idempotency_store_different_event_ids_not_duplicate():
    store = WebhookIdempotencyStore()
    store.mark_seen("evt_test_001")
    assert store.is_duplicate("evt_test_002") is False


def test_idempotency_store_clear():
    store = WebhookIdempotencyStore()
    store.mark_seen("evt_aaa")
    store.mark_seen("evt_bbb")
    assert store.size() == 2
    store.clear()
    assert store.size() == 0
    assert store.is_duplicate("evt_aaa") is False


def test_idempotency_prevents_double_processing():
    """
    Critical: processing the same event twice must be safe.
    
    This test simulates what happens in the webhook endpoint:
    first occurrence → process; second occurrence → skip.
    """
    store = WebhookIdempotencyStore()
    event_id = "evt_payment_failed_12345"

    # First occurrence
    is_dup_first = store.is_duplicate(event_id)
    store.mark_seen(event_id)

    # Second occurrence (same event_id from duplicate webhook delivery)
    is_dup_second = store.is_duplicate(event_id)

    assert is_dup_first is False, "First event should not be a duplicate"
    assert is_dup_second is True, "Second event with same ID must be detected as duplicate"


# ─── Payment Capture Reconciliation Tests ────────────────────────────────────

PAYMENT_CAPTURED_PAYLOAD = {
    "entity": "event",
    "account_id": "acc_test_123",
    "event": "payment.captured",
    "contains": ["payment"],
    "payload": {
        "payment": {
            "entity": {
                "id": "pay_test_abc123",
                "entity": "payment",
                "amount": 499900,  # ₹4,999.00 in paise
                "currency": "INR",
                "status": "captured",
                "order_id": "order_test_001",
                "method": "upi",
                "captured": True,
                "contact": "+919876543210",
                "email": "customer@example.com",
                "notes": {
                    "transaction_id": "txn_original_001",
                    "recovery_case_id": "rcase_test_456",
                    "source": "RevRecover_AI_Executor",
                },
            }
        }
    },
    "created_at": 1724000000,
}

PAYMENT_LINK_PAID_PAYLOAD = {
    "entity": "event",
    "event": "payment_link.paid",
    "contains": ["payment_link", "payment"],
    "payload": {
        "payment_link": {
            "entity": {
                "id": "plink_test_xyz789",
                "status": "paid",
                "amount": 250000,  # ₹2,500.00 in paise
                "notes": {
                    "transaction_id": "txn_original_002",
                    "recovery_case_id": "rcase_test_789",
                },
            }
        },
        "payment": {
            "entity": {
                "id": "pay_test_def456",
                "amount": 250000,
                "status": "captured",
            }
        },
    },
    "created_at": 1724000001,
}


def test_parse_event_payment_captured_returns_none():
    """payment.captured is a success event — not a failure, should return None from parse_event."""
    result = RazorpayWebhookParser.parse_event(PAYMENT_CAPTURED_PAYLOAD)
    assert result is None, "payment.captured should not produce a TransactionFailureEvent"


def test_extract_payment_captured_info_correct():
    """payment.captured webhook correctly extracts payment reconciliation info."""
    info = RazorpayWebhookParser.extract_payment_captured_info(PAYMENT_CAPTURED_PAYLOAD)
    assert info is not None
    assert info["payment_id"] == "pay_test_abc123"
    assert info["amount_inr"] == pytest.approx(4999.0, abs=0.01)
    assert info["transaction_id"] == "txn_original_001"
    assert info["recovery_case_id"] == "rcase_test_456"


def test_extract_payment_link_paid_info_correct():
    """payment_link.paid webhook correctly extracts payment reconciliation info."""
    info = RazorpayWebhookParser.extract_payment_captured_info(PAYMENT_LINK_PAID_PAYLOAD)
    assert info is not None
    assert info["payment_id"] == "pay_test_def456"
    assert info["amount_inr"] == pytest.approx(2500.0, abs=0.01)
    assert info["payment_link_id"] == "plink_test_xyz789"
    assert info["transaction_id"] == "txn_original_002"


def test_extract_payment_info_returns_none_for_failure_event():
    """parse failure events should not be treated as captures."""
    failure_payload = {
        "event": "payment.failed",
        "payload": {"payment": {"entity": {"id": "pay_fail_001", "amount": 100000}}},
        "created_at": 1724000002,
    }
    info = RazorpayWebhookParser.extract_payment_captured_info(failure_payload)
    assert info is None


def test_parse_payment_failed_produces_domain_event():
    """payment.failed should produce a TransactionFailureEvent."""
    failure_payload = {
        "event": "payment.failed",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_fail_789",
                    "amount": 750000,  # ₹7,500
                    "status": "failed",
                    "contact": "+919876500000",
                    "email": "",
                    "method": "card",
                    "bank": "SBI",
                    "error_code": "BAD_REQUEST_PAYMENT_DECLINED_BY_BANK",
                    "error_description": "Declined by bank",
                    "notes": {"customer_id": "cust_test_webhook"},
                }
            }
        },
        "created_at": 1724000003,
    }
    event = RazorpayWebhookParser.parse_event(failure_payload)
    assert event is not None
    assert event.transaction_id == "pay_fail_789"
    assert event.amount == pytest.approx(7500.0, abs=0.01)
    assert event.scenario == "PAYMENT_FAILURE"
    assert event.customer_id == "cust_test_webhook"
