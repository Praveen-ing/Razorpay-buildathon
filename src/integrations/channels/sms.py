from schema.recovery_schema import TransactionFailureEvent


class SMSChannelAdapter:
    """Formats high-converting SMS dunning messages with short URLs."""

    @staticmethod
    def format_message(event: TransactionFailureEvent, payment_link: str) -> str:
        first_name = event.customer_name.split()[0] if event.customer_name else "Customer"
        amount_formatted = f"Rs.{event.amount:,.0f}"

        if event.scenario == "CHECKOUT_ABANDONMENT":
            return f"Hi {first_name}, your cart order ({amount_formatted}) is waiting. Tap to complete order securely: {payment_link} - Team RevRecover"
        elif event.scenario == "RECURRING_SUBSCRIPTION":
            return f"Alert: Your recurring subscription ({amount_formatted}) payment failed. Avoid account suspension by updating here: {payment_link}"
        elif event.scenario == "B2B_INVOICE_OVERDUE":
            return f"Notice: Overdue invoice of {amount_formatted} is pending. Settle instantly via Razorpay: {payment_link}"
        else:
            return f"Your payment of {amount_formatted} was incomplete. No funds deducted. Tap to retry securely: {payment_link}"
