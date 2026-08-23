import pytest
from integrations.razorpay_client import RazorpayClient
from integrations.webhook_handler import RazorpayWebhookParser


def test_razorpay_mock_payment_link_generation():
    client = RazorpayClient(mock_mode=True)
    resp = client.create_payment_link(
        amount=14999.0,
        customer_name="Rahul Sharma",
        customer_phone="+919876543210",
        customer_email="rahul.s@example.com",
    )

    assert resp.id.startswith("plink_")
    assert resp.short_url.startswith("https://rzp.io/i/")
    assert resp.amount == 14999.0
    assert resp.currency == "INR"


def test_razorpay_webhook_parsing_payment_failed():
    raw_payload = {
        "event": "payment.failed",
        "payload": {
            "payment": {
                "entity": {
                    "id": "pay_29QQoUBcxBqqIL",
                    "amount": 425000,
                    "contact": "+919812345678",
                    "email": "priya.p@example.com",
                    "error_code": "BAD_REQUEST_PAYMENT_OTP_VALIDATION_FAILED",
                    "bank": "ICICI",
                    "method": "card",
                    "notes": {"customer_name": "Priya Patel", "customer_id": "cust_102"},
                }
            }
        },
    }

    event = RazorpayWebhookParser.parse_event(raw_payload)
    assert event is not None
    assert event.transaction_id == "pay_29QQoUBcxBqqIL"
    assert event.amount == 4250.0
    assert event.error_code == "BAD_REQUEST_PAYMENT_OTP_VALIDATION_FAILED"
    assert event.bank == "ICICI"
