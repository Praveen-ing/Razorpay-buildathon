import logging
from typing import Any
from integrations.channels.voice_hinglish import HinglishVoiceAgentAdapter
from schema.recovery_schema import (
    PromiseToPayRecord,
    TransactionFailureEvent,
)

logger = logging.getLogger(__name__)


class VoiceRecoveryAgent:
    """Conversational Hinglish Voice AI recovery agent for high-touch and B2B cases."""

    def __init__(self) -> None:
        self.channel_adapter = HinglishVoiceAgentAdapter()

    def generate_call_script(self, event: TransactionFailureEvent, payment_link: str) -> str:
        return self.channel_adapter.generate_opening_script(event, payment_link)

    def process_customer_speech_or_text(
        self,
        event: TransactionFailureEvent,
        customer_utterance: str,
        payment_link: str,
    ) -> dict[str, Any]:
        """Processes live speech/text from a customer and returns the agent's Hinglish response + state update."""
        utterance_lower = customer_utterance.lower()

        if any(k in utterance_lower for k in ["stop", "mat call karo", "don't call", "dnd", "nahi chahiye", "cancel"]):
            response = "Theek hai ji, maine aapka number DND list mein daal diya hai. Aapko aage se koi call nahi aayega. Dhanyawad."
            outcome = "STOPPED_OPT_OUT"
            ptp = None
        elif any(k in utterance_lower for k in ["dispute", "return", "galat bill", "fraud", "already returned", "refund"]):
            response = "Samajh gaya ji. Main turant ye dunning process halt kar raha hoon aur hamari finance dispute team ko escalate kar raha hoon. Wo aapse contact karenge."
            outcome = "STOPPED_DISPUTE_ESCALATED"
            ptp = None
        elif any(k in utterance_lower for k in ["kal", "tomorrow", "baad mein", "salary", "shaam", "next week", "monday", "promise"]):
            response = "Bilkul ji! Maine aapka payment promise schedule kar diya hai. Tab tak ke liye saari automated reminders pause rahengi. Shukriya!"
            outcome = "PROMISE_TO_PAY_RECORDED"
            ptp = PromiseToPayRecord(
                transaction_id=event.transaction_id,
                customer_id=event.customer_id,
                promised_amount=event.amount,
                promised_date="Scheduled Callback/Promise Date",
                status="PENDING",
                notes=f"Customer promised during voice call: '{customer_utterance}'",
            )
        else:
            response = f"Bahut badhiya! Maine aapke WhatsApp pe 1-click Razorpay payment link bhej diya hai: {payment_link}. Payment karte hi turant confirmation mil jayega."
            outcome = "RECOVERED_VIA_WHATSAPP_LINK"
            ptp = None

        return {
            "agent_response": response,
            "outcome": outcome,
            "ptp_record": ptp,
        }


voice_recovery_agent = VoiceRecoveryAgent()
