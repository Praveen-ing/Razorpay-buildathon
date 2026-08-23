from schema.recovery_schema import TransactionFailureEvent


class EmailChannelAdapter:
    """Formats professional B2B escalation emails and customer invoices."""

    @staticmethod
    def format_email(event: TransactionFailureEvent, payment_link: str) -> dict[str, str]:
        invoice_id = event.metadata.get("invoice_id", f"INV-{event.transaction_id[:8]}")
        amount_formatted = f"INR {event.amount:,.2f}"

        subject = f"Action Required: Outstanding Invoice {invoice_id} ({amount_formatted})"
        body = (
            f"Dear {event.customer_name},\n\n"
            f"We are reaching out from the Finance & Accounts Department regarding outstanding invoice #{invoice_id}.\n\n"
            f"• Invoice Reference: {invoice_id}\n"
            f"• Total Overdue Amount: {amount_formatted}\n"
            f"• Due Date: Immediate\n\n"
            f"To prevent any service interruption or credit holds, please settle the outstanding balance using our secure Razorpay instant settlement link below:\n\n"
            f"Secure Payment Link: {payment_link}\n\n"
            f"Accepted Payment Modes: NEFT, RTGS, Corporate Netbanking, Corporate Credit Cards, UPI.\n\n"
            f"If this balance has already been remitted, please reply to this email with the bank transaction reference (UTR) for immediate ledger reconciliation.\n\n"
            f"Sincerely,\n"
            f"Accounts Receivable & Recovery Operations\n"
            f"RevRecover AI Automated Billing Engine"
        )
        return {"subject": subject, "body": body}
