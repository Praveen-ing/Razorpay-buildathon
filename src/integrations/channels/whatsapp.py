from schema.recovery_schema import TransactionFailureEvent, CustomerTier


class WhatsAppChannelAdapter:
    """Formats high-converting WhatsApp messages with interactive CTA buttons & 1-click Razorpay links."""

    @staticmethod
    def format_message(
        event: TransactionFailureEvent,
        payment_link: str,
        discount_pct: float = 0.0,
    ) -> str:
        first_name = event.customer_name.split()[0] if event.customer_name else "there"
        amount_formatted = f"₹{event.amount:,.2f}"

        if discount_pct > 0:
            discounted_amount = event.amount * (1.0 - (discount_pct / 100.0))
            discount_note = f"\n🎁 *Exclusive Recovery Offer:* We've applied a special *{discount_pct:.0f}% discount* for you! Pay only *₹{discounted_amount:,.2f}*.\n"
        else:
            discount_note = ""

        if event.scenario == "CHECKOUT_ABANDONMENT":
            body = (
                f"Namaste {first_name}! 🙏\n\n"
                f"We noticed you left items in your cart. Your order worth *{amount_formatted}* is reserved for the next 24 hours."
                f"{discount_note}\n"
                f"Complete your purchase with 1-click UPI / Card below:\n"
                f"👉 {payment_link}\n\n"
                f"_Reply 'STOP' at any time to opt out._"
            )
        elif event.scenario == "RECURRING_SUBSCRIPTION":
            body = (
                f"Hi {first_name}, 👋\n\n"
                f"Your subscription renewal for *{amount_formatted}* couldn't be processed due to a temporary bank issue ({event.bank})."
                f"{discount_note}\n"
                f"To keep your service uninterrupted, please update your payment method or complete the payment here:\n"
                f"🔗 {payment_link}\n\n"
                f"Thank you for being a valued member!"
            )
        elif event.scenario == "B2B_INVOICE_OVERDUE":
            body = (
                f"Dear {event.customer_name},\n\n"
                f"This is a gentle reminder regarding invoice #{event.metadata.get('invoice_id', 'INV-2026')} for *{amount_formatted}*.\n\n"
                f"You can quickly settle this via instant corporate payment:\n"
                f"💳 {payment_link}\n\n"
                f"If payment is already initiated, please reply with the UTR number."
            )
        else:
            body = (
                f"Namaste {first_name}! 🙏\n\n"
                f"Your recent payment of *{amount_formatted}* was interrupted by {event.bank} network timeout."
                f"{discount_note}\n"
                f"No funds were deducted from your account. You can securely complete your transaction with 1-tap UPI:\n"
                f"⚡ {payment_link}\n\n"
                f"Need help? Reply to this message directly."
            )

        return body
