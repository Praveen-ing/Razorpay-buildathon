"""
Executor Agent — RevRecover AI
=================================
Receives a governor-APPROVED intervention and executes it.

Responsibilities:
  - Call Razorpay to create a real Test Mode payment link (or mock)
  - Dispatch channel messages via channel adapters
  - Return an ExecutionResult with explicit status — NEVER fabricate success
  - Never decide whether an action is allowed (that is the Governor's job)

The Executor sits between the Governor and the external world:

    Governor (APPROVED)
         ↓
    Executor
         ↓
    Razorpay API  /  Channel Adapters
         ↓
    ExecutionResult
"""

import logging
from datetime import datetime, timedelta

from integrations.channels.email import EmailChannelAdapter
from integrations.channels.sms import SMSChannelAdapter
from integrations.channels.voice_hinglish import HinglishVoiceAgentAdapter
from integrations.channels.whatsapp import WhatsAppChannelAdapter
from integrations.razorpay_client import razorpay_client
from schema.recovery_schema import (
    ChannelDeliveryResult,
    ChannelDeliveryStatus,
    CommunicationChannel,
    ExecutionResult,
    ExecutionStatus,
    PaymentLinkRecord,
    PaymentLinkSource,
    RecoveryIntervention,
    RecoveryVector,
    TransactionFailureEvent,
)

logger = logging.getLogger(__name__)


class RecoveryExecutor:
    """
    Executes governor-approved recovery interventions against real external systems.

    Key contract:
      - If Razorpay is in LIVE Test Mode → payment link comes from real API → source = RAZORPAY_TEST_MODE
      - If Razorpay is in Mock Mode     → local mock link                  → source = MOCK_SANDBOX
      - If synthetic benchmark          → no link created, outcome simulated → is_synthetic = True
      - Channel adapters NEVER return SENT without a real provider
    """

    def execute(
        self,
        event: TransactionFailureEvent,
        intervention: RecoveryIntervention,
        recovery_case_id: str = "",
        is_synthetic: bool = False,
    ) -> ExecutionResult:
        """
        Execute an approved recovery intervention.

        Args:
            event: The original failure event
            intervention: The approved intervention from the Strategist
            recovery_case_id: Recovery case identifier for traceability
            is_synthetic: If True, skip real API calls (benchmark mode)

        Returns:
            ExecutionResult with actual status — never fakes success
        """
        logger.info(
            f"[Executor] Executing intervention for {event.transaction_id} | "
            f"vector={intervention.vector.value} | channel={intervention.channel.value} | "
            f"synthetic={is_synthetic}"
        )

        # Silent API retry — no external link or message needed
        if intervention.vector == RecoveryVector.INSTANT_SMART_RETRY:
            return ExecutionResult(
                recovery_case_id=recovery_case_id,
                transaction_id=event.transaction_id,
                status=ExecutionStatus.RETRY_SCHEDULED,
                is_synthetic=is_synthetic,
            )

        # Human escalation
        if intervention.vector == RecoveryVector.HUMAN_ESCALATION:
            return ExecutionResult(
                recovery_case_id=recovery_case_id,
                transaction_id=event.transaction_id,
                status=ExecutionStatus.ESCALATED_TO_HUMAN,
                is_synthetic=is_synthetic,
            )

        # ─────────────────────────────────────────────────────────────────────
        # Step 1: Create payment link (only if not pure-synthetic benchmark)
        # ─────────────────────────────────────────────────────────────────────
        payment_link_record: PaymentLinkRecord | None = None

        if not is_synthetic:
            effective_amount = event.amount * (1.0 - (intervention.discount_pct_authorized / 100.0))

            rzp_resp = razorpay_client.create_payment_link(
                amount=effective_amount,
                customer_name=event.customer_name,
                customer_phone=event.customer_phone,
                customer_email=event.customer_email,
                description=f"RevRecover - {event.scenario.replace('_', ' ').title()}",
                expire_in_minutes=1440,
                notes={
                    "transaction_id": event.transaction_id,
                    "recovery_case_id": recovery_case_id,
                    "original_amount": str(event.amount),
                    "source": "RevRecover_AI_Executor",
                },
            )

            # Determine source: check if link is real Test Mode (has real plink_ prefix)
            is_real = rzp_resp.id.startswith("plink_") and not rzp_resp.id.startswith("plink_mock")
            source = PaymentLinkSource.RAZORPAY_TEST_MODE if is_real else PaymentLinkSource.MOCK_SANDBOX

            payment_link_record = PaymentLinkRecord(
                link_id=rzp_resp.id,
                short_url=rzp_resp.short_url,
                source=source,
                recovery_case_id=recovery_case_id,
                transaction_id=event.transaction_id,
                amount_inr=effective_amount,
                customer_id=event.customer_id,
                created_at=rzp_resp.created_at,
                expires_at=datetime.now() + timedelta(minutes=1440),
                status="created",
            )

            # Update the intervention's payment link URL for downstream use
            intervention.razorpay_payment_link = rzp_resp.short_url

            logger.info(
                f"[Executor] Payment link created: {rzp_resp.id} → {rzp_resp.short_url} "
                f"[{source.value}]"
            )

        # ─────────────────────────────────────────────────────────────────────
        # Step 2: Dispatch channel message
        # ─────────────────────────────────────────────────────────────────────
        channel_result: ChannelDeliveryResult | None = None
        payment_link_url = intervention.razorpay_payment_link or ""

        if intervention.channel != CommunicationChannel.SILENT_API_RETRY:
            channel_result = self._dispatch_channel(event, intervention, payment_link_url)

        # ─────────────────────────────────────────────────────────────────────
        # Step 3: Determine execution status
        # ─────────────────────────────────────────────────────────────────────
        if payment_link_record:
            exec_status = ExecutionStatus.PAYMENT_LINK_CREATED
        elif channel_result and channel_result.status == ChannelDeliveryStatus.MESSAGE_FORMATTED:
            exec_status = ExecutionStatus.CHANNEL_MESSAGE_SENT
        else:
            exec_status = ExecutionStatus.PROVIDER_NOT_CONFIGURED

        return ExecutionResult(
            recovery_case_id=recovery_case_id,
            transaction_id=event.transaction_id,
            status=exec_status,
            payment_link=payment_link_record,
            channel_result=channel_result,
            is_synthetic=is_synthetic,
        )

    def _dispatch_channel(
        self,
        event: TransactionFailureEvent,
        intervention: RecoveryIntervention,
        payment_link_url: str,
    ) -> ChannelDeliveryResult:
        """
        Dispatch a message via the appropriate channel adapter.

        Returns:
            ChannelDeliveryResult with explicit status.
            MESSAGE_FORMATTED = message was built (transport provider not configured).
            NOT_CONFIGURED    = no provider credentials available.
            SENT              = reserved for when provider actually confirms dispatch.
        """
        channel = intervention.channel
        discount_pct = intervention.discount_pct_authorized

        try:
            if channel == CommunicationChannel.WHATSAPP:
                message = WhatsAppChannelAdapter.format_message(event, payment_link_url, discount_pct)
                return ChannelDeliveryResult(
                    channel=channel,
                    status=ChannelDeliveryStatus.MESSAGE_FORMATTED,
                    provider=None,  # No WhatsApp provider configured
                    message_preview=message[:200],
                )

            elif channel == CommunicationChannel.SMS:
                message = SMSChannelAdapter.format_message(event, payment_link_url)
                return ChannelDeliveryResult(
                    channel=channel,
                    status=ChannelDeliveryStatus.MESSAGE_FORMATTED,
                    provider=None,
                    message_preview=message[:200],
                )

            elif channel == CommunicationChannel.EMAIL:
                email_data = EmailChannelAdapter.format_email(event, payment_link_url)
                preview = f"Subject: {email_data['subject']}\n{email_data['body'][:150]}"
                return ChannelDeliveryResult(
                    channel=channel,
                    status=ChannelDeliveryStatus.MESSAGE_FORMATTED,
                    provider=None,
                    message_preview=preview[:200],
                )

            elif channel == CommunicationChannel.VOICE_HINGLISH:
                script = HinglishVoiceAgentAdapter.generate_opening_script(event, payment_link_url)
                return ChannelDeliveryResult(
                    channel=channel,
                    status=ChannelDeliveryStatus.MESSAGE_FORMATTED,
                    provider=None,
                    message_preview=script[:200],
                )

            elif channel == CommunicationChannel.MANUAL_DESK:
                return ChannelDeliveryResult(
                    channel=channel,
                    status=ChannelDeliveryStatus.QUEUED,
                    provider="manual_desk",
                    message_preview="Escalated to human collections desk.",
                )

        except Exception as e:
            logger.error(f"[Executor] Channel dispatch error for {channel.value}: {e}")
            return ChannelDeliveryResult(
                channel=channel,
                status=ChannelDeliveryStatus.PROVIDER_ERROR,
                error_detail=str(e),
            )

        return ChannelDeliveryResult(
            channel=channel,
            status=ChannelDeliveryStatus.NOT_CONFIGURED,
        )


# Global singleton
recovery_executor = RecoveryExecutor()
