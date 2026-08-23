from typing import Any
from schema.recovery_schema import TransactionFailureEvent, PromiseToPayRecord


class HinglishVoiceAgentAdapter:
    """Generates natural, polite Hinglish conversational voice recovery scripts and dialogues."""

    @staticmethod
    def generate_opening_script(event: TransactionFailureEvent, payment_link: str) -> str:
        first_name = event.customer_name.split()[0] if event.customer_name else "Sir/Ma'am"
        amount_str = f"₹{event.amount:,.0f}"

        if event.scenario == "B2B_INVOICE_OVERDUE":
            return (
                f"Namaste {event.customer_name} ji! Main accounts assistance desk se bol raha hoon. "
                f"Aapke pending invoice jo ki {amount_str} ka hai, uske settlement ke regarding call kiya tha. "
                f"Kya aapko invoice details mil gayi thi, ya fir main aapke registered WhatsApp pe instant payment link bhej doon?"
            )
        elif event.scenario == "RECURRING_SUBSCRIPTION":
            return (
                f"Hello {first_name} ji! Main aapke subscription support team se baat kar raha hoon. "
                f"Aapka monthly renewal payment jo {amount_str} ka tha, {event.bank} ke network issue ki wajah se complete nahi ho paya. "
                f"Aapka service uninterrupted rahe, iske liye maine WhatsApp pe ek 1-click Razorpay secure link bheja hai. "
                f"Kya aap abhi UPI ya card se retry karna chahenge?"
            )
        else:
            return (
                f"Namaste {first_name} ji! Main customer success team se baat kar raha hoon. "
                f"Aapne jo {amount_str} ka order place karne ki koshish ki thi, wo {event.bank} ke network timeout ki wajah se fail ho gaya tha. "
                f"Aapke paise account se nahi kate hain. Agar aap chahein toh main aapko turant WhatsApp pe direct payment link bhej doon taaki aapka order confirm ho sake?"
            )

    @staticmethod
    def simulate_dialogue_flow(
        event: TransactionFailureEvent,
        customer_response_type: str = "AGREE_TO_PAY",
        payment_link: str = "https://rzp.io/i/example",
    ) -> dict[str, Any]:
        """Simulates an interactive Hinglish call transcript with intent classification and outcome."""
        first_name = event.customer_name.split()[0] if event.customer_name else "Customer"
        amount_str = f"₹{event.amount:,.0f}"

        opening = HinglishVoiceAgentAdapter.generate_opening_script(event, payment_link)

        if customer_response_type == "AGREE_TO_PAY":
            transcript = [
                {"speaker": "Agent (AI)", "text": opening},
                {"speaker": "Customer", "text": "Haan haan, bank mein OTP nahi aa raha tha. Mujhe WhatsApp pe link bhej dijiye, main abhi UPI se kar deta hoon."},
                {"speaker": "Agent (AI)", "text": f"Bahut dhanyawad {first_name} ji! Link maine aapke WhatsApp number {event.customer_phone} pe bhej diya hai. Payment hote hi confirmation aa jayega. Have a great day!"}
            ]
            outcome = "RECOVERED_VIA_WHATSAPP_LINK"
            ptp = None

        elif customer_response_type == "PROMISE_TO_PAY":
            transcript = [
                {"speaker": "Agent (AI)", "text": opening},
                {"speaker": "Customer", "text": "Actually aaj main thoda bahar hoon. Kya main kal shaam tak payment kar doon?"},
                {"speaker": "Agent (AI)", "text": f"Bilkul {first_name} ji, main aapka commitment kal 24 August shaam 6 baje tak note kar leta hoon. Tab tak koi extra reminder nahi aayega. Dhanyawad!"}
            ]
            outcome = "PROMISE_TO_PAY_RECORDED"
            ptp = PromiseToPayRecord(
                transaction_id=event.transaction_id,
                customer_id=event.customer_id,
                promised_amount=event.amount,
                promised_date="Tomorrow by 6:00 PM IST",
                status="PENDING",
                notes="Customer agreed during Hinglish voice call to pay tomorrow evening.",
            )

        elif customer_response_type == "DISPUTE_RAISED":
            transcript = [
                {"speaker": "Agent (AI)", "text": opening},
                {"speaker": "Customer", "text": "Bhai maine to product return kar diya tha, fir ye bill kaisa aa raha hai? Please check karo."},
                {"speaker": "Agent (AI)", "text": f"Shukriya batane ke liye {first_name} ji. Main turant dunning pause kar raha hoon aur hamare senior dispute resolution specialist ko aapka case assign kar raha hoon."}
            ]
            outcome = "STOPPED_DISPUTE_ESCALATED"
            ptp = None

        else:  # OPT_OUT
            transcript = [
                {"speaker": "Agent (AI)", "text": opening},
                {"speaker": "Customer", "text": "Mujhe abhi ye purchase nahi karni hai, please do not call again."},
                {"speaker": "Agent (AI)", "text": f"Understood {first_name} ji. Maine aapka number DND list mein add kar diya hai aur reminders stop kar diye hain. Khama chahenge asuvidha ke liye."}
            ]
            outcome = "STOPPED_OPT_OUT"
            ptp = None

        return {
            "transcript": transcript,
            "outcome": outcome,
            "sentiment": "POSITIVE" if outcome in ["RECOVERED_VIA_WHATSAPP_LINK", "PROMISE_TO_PAY_RECORDED"] else "NEGATIVE",
            "ptp_record": ptp,
        }
