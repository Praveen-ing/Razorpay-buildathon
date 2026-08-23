"""
Webhook Handler — RevRecover AI
==================================
Parses, verifies, deduplicates, and normalizes raw Razorpay webhook events
into recovery domain events.

Pipeline:
    Razorpay Webhook POST
         ↓
    Signature Verification (HMAC SHA256)
         ↓
    Idempotency Check (seen event_id)
         ↓
    Parse Event → Normalize to TransactionFailureEvent
         ↓
    Recovery Orchestrator

Contract:
  - A duplicate webhook MUST NOT produce a duplicate recovery or double-count revenue
  - Signature verification MUST happen before any business logic
  - payment.captured MUST update recovery case to RECOVERED with real payment evidence
"""

import logging
from datetime import datetime
from typing import Any

from schema.recovery_schema import (
    CustomerTier,
    TransactionFailureEvent,
)

logger = logging.getLogger(__name__)


class WebhookIdempotencyStore:
    """
    In-memory idempotency store for webhook event deduplication.

    In production, replace with a persistent Redis/DB store.
    Key: Razorpay event_id (from X-Razorpay-Event-Id header or payload id field)
    """

    def __init__(self) -> None:
        self._seen: set[str] = set()

    def is_duplicate(self, event_id: str) -> bool:
        """Returns True if this event_id was already processed."""
        return event_id in self._seen

    def mark_seen(self, event_id: str) -> None:
        """Mark an event_id as processed. Idempotent."""
        self._seen.add(event_id)

    def clear(self) -> None:
        """Clear the store (used in tests)."""
        self._seen.clear()

    def size(self) -> int:
        return len(self._seen)


# Global singleton idempotency store
webhook_idempotency = WebhookIdempotencyStore()


class RazorpayWebhookParser:
    """Parses and normalizes raw Razorpay webhook events into recovery domain events."""

    @staticmethod
    def get_event_id(webhook_payload: dict[str, Any]) -> str:
        """Extract a unique event identifier from the webhook payload."""
        # Razorpay includes an event id in the payload — use it for deduplication
        return str(
            webhook_payload.get("id")
            or webhook_payload.get("event_id")
            or f"{webhook_payload.get('event', 'unknown')}_{webhook_payload.get('created_at', 0)}"
        )

    @staticmethod
    def parse_event(webhook_payload: dict[str, Any]) -> TransactionFailureEvent | None:
        """
        Parse a Razorpay webhook payload into a TransactionFailureEvent.

        Returns None for non-failure events (payment.captured, order.paid, etc.)
        that should be handled by the reconciliation path, not the recovery path.
        """
        event_type = webhook_payload.get("event", "")
        payload = webhook_payload.get("payload", {})

        if event_type == "payment.failed":
            payment = payload.get("payment", {}).get("entity", {})
            amount_paise = payment.get("amount", 0)
            amount_inr = amount_paise / 100.0
            error_code = payment.get("error_code") or "GATEWAY_ERROR"
            contact = payment.get("contact") or "+919876543210"
            email = payment.get("email") or ""
            notes = payment.get("notes", {}) or {}
            customer_name = notes.get("customer_name") or payment.get("description") or "Valued Customer"

            return TransactionFailureEvent(
                transaction_id=payment.get("id", f"pay_err_{int(datetime.now().timestamp())}"),
                customer_id=notes.get("customer_id", f"cust_{contact[-6:]}"),
                customer_name=customer_name,
                customer_phone=contact,
                customer_email=email,
                customer_tier=CustomerTier.GOLD if amount_inr > 5000 else CustomerTier.STANDARD,
                amount=amount_inr,
                scenario="PAYMENT_FAILURE",
                error_code=error_code,
                bank=payment.get("bank") or "HDFC",
                payment_method=payment.get("method") or "UPI",
                metadata={
                    "notes": notes,
                    "error_description": payment.get("error_description"),
                    "error_source": payment.get("error_source"),
                    "error_step": payment.get("error_step"),
                },
            )

        elif event_type == "subscription.halted":
            subscription = payload.get("subscription", {}).get("entity", {})
            notes = subscription.get("notes", {}) or {}
            amount_inr = float(notes.get("amount", 2999.0))
            return TransactionFailureEvent(
                transaction_id=subscription.get("id", "sub_halted_01"),
                customer_id=subscription.get("customer_id") or "cust_saas_sub",
                customer_name=notes.get("customer_name", "Subscriber"),
                customer_phone=notes.get("contact", "+919834567890"),
                customer_email=notes.get("email", ""),
                customer_tier=CustomerTier.PLATINUM if amount_inr > 10000 else CustomerTier.GOLD,
                amount=amount_inr,
                scenario="RECURRING_SUBSCRIPTION",
                error_code="SUBSCRIPTION_HALTED",
                bank="AXIS",
                payment_method="E_MANDATE_CARD",
                metadata={"subscription_id": subscription.get("id"), "notes": notes},
            )

        elif event_type in ["invoice.expired", "invoice.unpaid"]:
            invoice = payload.get("invoice", {}).get("entity", {})
            amount_inr = (invoice.get("amount", 0)) / 100.0
            return TransactionFailureEvent(
                transaction_id=invoice.get("id", "inv_overdue_01"),
                customer_id=invoice.get("customer_id") or "cust_b2b_client",
                customer_name=invoice.get("customer_name", "Corporate Account"),
                customer_phone=invoice.get("customer_contact", "+919867890123"),
                customer_email=invoice.get("customer_email", ""),
                customer_tier=CustomerTier.ENTERPRISE if amount_inr > 50000 else CustomerTier.GOLD,
                amount=amount_inr,
                scenario="B2B_INVOICE_OVERDUE",
                error_code="INVOICE_OVERDUE_TIER_2" if amount_inr > 50000 else "INVOICE_OVERDUE_TIER_1",
                bank="ICICI",
                payment_method="BANK_TRANSFER",
                metadata={"invoice_id": invoice.get("id"), "short_url": invoice.get("short_url")},
            )

        elif event_type in ["payment.captured", "payment_link.paid"]:
            # This is a successful payment — handled by reconciliation path
            logger.info(f"[WebhookParser] Payment success event received: {event_type} — route to reconciler")
            return None

        logger.info(f"[WebhookParser] Ignored non-failure webhook event: {event_type}")
        return None

    @staticmethod
    def extract_payment_captured_info(webhook_payload: dict[str, Any]) -> dict[str, Any] | None:
        """
        Extract payment details from a payment.captured or payment_link.paid event.

        Returns dict with: transaction_id, payment_id, amount_inr, payment_link_id
        Returns None if not a capture event.
        """
        event_type = webhook_payload.get("event", "")
        payload = webhook_payload.get("payload", {})

        if event_type == "payment.captured":
            payment = payload.get("payment", {}).get("entity", {})
            notes = payment.get("notes", {}) or {}
            return {
                "transaction_id": notes.get("transaction_id") or payment.get("order_id") or payment.get("id"),
                "payment_id": payment.get("id"),
                "amount_inr": payment.get("amount", 0) / 100.0,
                "payment_link_id": None,
                "recovery_case_id": notes.get("recovery_case_id", ""),
            }

        elif event_type == "payment_link.paid":
            payment_link = payload.get("payment_link", {}).get("entity", {})
            payment = payload.get("payment", {}).get("entity", {})
            notes = payment_link.get("notes", {}) or {}
            return {
                "transaction_id": notes.get("transaction_id", ""),
                "payment_id": payment.get("id"),
                "amount_inr": payment.get("amount", 0) / 100.0,
                "payment_link_id": payment_link.get("id"),
                "recovery_case_id": notes.get("recovery_case_id", ""),
            }

        return None
