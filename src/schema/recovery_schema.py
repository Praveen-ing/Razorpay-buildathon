from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import uuid4
from pydantic import BaseModel, Field


class FailureCategory(StrEnum):
    TRANSIENT_GATEWAY = "TRANSIENT_GATEWAY"
    BANK_DOWNTIME = "BANK_DOWNTIME"
    USER_FRICTION = "USER_FRICTION"
    STRUCTURAL_CHURN = "STRUCTURAL_CHURN"
    MANDATE_ISSUE = "MANDATE_ISSUE"
    SUBSCRIPTION_CHURN = "SUBSCRIPTION_CHURN"
    B2B_OVERDUE = "B2B_OVERDUE"
    CHECKOUT_ABANDONMENT = "CHECKOUT_ABANDONMENT"
    FRAUD_RISK = "FRAUD_RISK"
    UNKNOWN = "UNKNOWN"


class RecoveryVector(StrEnum):
    INSTANT_SMART_RETRY = "INSTANT_SMART_RETRY"
    GATEWAY_REROUTE_RETRY = "GATEWAY_REROUTE_RETRY"
    WHATSAPP_ONE_CLICK_LINK = "WHATSAPP_ONE_CLICK_LINK"
    SMS_PAYMENT_LINK = "SMS_PAYMENT_LINK"
    EMAIL_PAYMENT_LINK = "EMAIL_PAYMENT_LINK"
    HINGLISH_VOICE_CALL = "HINGLISH_VOICE_CALL"
    SMART_DUNNING_WITH_DISCOUNT = "SMART_DUNNING_WITH_DISCOUNT"
    SALARY_CYCLE_RETRY_SCHEDULE = "SALARY_CYCLE_RETRY_SCHEDULE"
    B2B_POLITE_STATEMENT = "B2B_POLITE_STATEMENT"
    B2B_FIRM_ESCALATION = "B2B_FIRM_ESCALATION"
    B2B_EXECUTIVE_VOICE_SETTLEMENT = "B2B_EXECUTIVE_VOICE_SETTLEMENT"
    HUMAN_ESCALATION = "HUMAN_ESCALATION"
    HARD_STOP_NO_CONTACT = "HARD_STOP_NO_CONTACT"


class CommunicationChannel(StrEnum):
    WHATSAPP = "WHATSAPP"
    SMS = "SMS"
    VOICE_HINGLISH = "VOICE_HINGLISH"
    EMAIL = "EMAIL"
    SILENT_API_RETRY = "SILENT_API_RETRY"
    MANUAL_DESK = "MANUAL_DESK"
    NONE = "NONE"


class CustomerTier(StrEnum):
    STANDARD = "STANDARD"
    GOLD = "GOLD"
    PLATINUM = "PLATINUM"
    VIP_PLATINUM = "VIP_PLATINUM"
    ENTERPRISE = "ENTERPRISE"


class RecoveryStatus(StrEnum):
    AT_RISK = "AT_RISK"
    DIAGNOSED = "DIAGNOSED"
    INTERVENTION_PLANNED = "INTERVENTION_PLANNED"
    OUTREACH_ACTIVE = "OUTREACH_ACTIVE"
    RECOVERED = "RECOVERED"
    PROMISE_TO_PAY_SET = "PROMISE_TO_PAY_SET"
    STOPPED_PAYMENT_DETECTED = "STOPPED_PAYMENT_DETECTED"
    STOPPED_OPT_OUT = "STOPPED_OPT_OUT"
    STOPPED_FRAUD_RISK = "STOPPED_FRAUD_RISK"
    STOPPED_NEGATIVE_EV = "STOPPED_NEGATIVE_EV"
    STOPPED_DISPUTE_ESCALATED = "STOPPED_DISPUTE_ESCALATED"
    STOPPED_PTP_ACTIVE = "STOPPED_PTP_ACTIVE"
    STOPPED_MAX_ATTEMPTS_EXHAUSTED = "STOPPED_MAX_ATTEMPTS_EXHAUSTED"
    CLOSED_UNRECOVERABLE = "CLOSED_UNRECOVERABLE"


class TransactionFailureEvent(BaseModel):
    transaction_id: str = Field(..., description="Unique ID of transaction or order")
    customer_id: str = Field(..., description="Customer identifier")
    customer_name: str = Field("Customer", description="Full name of customer")
    customer_phone: str = Field(..., description="E.164 phone number (+91...)")
    customer_email: str = Field("", description="Customer email address")
    customer_tier: CustomerTier = Field(default=CustomerTier.STANDARD)
    customer_ltv: float = Field(default=15000.0, description="Customer lifetime value in INR")
    past_successful_payments: int = Field(default=3, description="Number of historical successful payments")
    channel_consent: list[CommunicationChannel] = Field(
        default_factory=lambda: [CommunicationChannel.WHATSAPP, CommunicationChannel.SMS, CommunicationChannel.EMAIL, CommunicationChannel.VOICE_HINGLISH],
        description="Channels customer has consented to receive recovery messages on",
    )
    amount: float = Field(..., description="Amount in INR (₹)")
    currency: str = Field("INR", description="Currency code")
    scenario: str = Field("PAYMENT_FAILURE", description="Scenario type (PAYMENT_FAILURE, CHECKOUT_ABANDONMENT, RECURRING_SUBSCRIPTION, B2B_INVOICE_OVERDUE)")
    error_code: str = Field("GATEWAY_ERROR", description="Razorpay error code or drop-off reason")
    bank: str = Field("HDFC", description="Bank involved (HDFC, SBI, ICICI, etc.)")
    payment_method: str = Field("UPI", description="Payment instrument used")
    failure_timestamp: datetime = Field(default_factory=datetime.now)
    attempt_count: int = Field(default=0)
    opted_out: bool = Field(default=False)
    disputed: bool = Field(default=False)
    has_active_ptp: bool = Field(default=False)
    fraud_suspected: bool = Field(default=False)
    metadata: dict[str, Any] = Field(default_factory=dict)


class RootCauseDiagnosis(BaseModel):
    category: FailureCategory = Field(default=FailureCategory.TRANSIENT_GATEWAY)
    confidence: float = Field(default=0.95, ge=0.0, le=1.0)
    is_retryable: bool = Field(default=True)
    recoverable: bool = Field(default=True)
    root_cause_explanation: str = Field(..., description="Clear explanation of why payment failed or dropped off")
    bank_health_status: str = Field(default="OPTIMAL")
    customer_intent_score: float = Field(default=0.85, ge=0.0, le=1.0)
    expected_recovery_probability: float = Field(default=0.75, ge=0.0, le=1.0, description="P(recovery)")
    churn_risk_if_contacted: float = Field(default=0.03, ge=0.0, le=1.0, description="P(churn)")
    suggested_action: str = Field("send_razorpay_link", description="Recommended action vector")
    urgency_level: str = Field(default="MEDIUM", description="LOW, MEDIUM, HIGH, CRITICAL")


class RecoveryIntervention(BaseModel):
    vector: RecoveryVector = Field(default=RecoveryVector.WHATSAPP_ONE_CLICK_LINK)
    channel: CommunicationChannel = Field(default=CommunicationChannel.WHATSAPP)
    delay_seconds: int = Field(default=0)
    discount_pct_authorized: float = Field(default=0.0, description="Discount or waiver approved (0-15%)")
    razorpay_payment_link: str | None = Field(default=None, description="Pre-filled 1-click Razorpay payment link URL")
    message_content: str = Field("", description="Personalized outreach text or email body")
    voice_script_hinglish: str = Field("", description="Conversational script for Hinglish AI Voice Agent")
    requires_human_approval: bool = Field(default=False)
    scheduled_time: datetime | None = Field(default=None)
    contact_cost_inr: float = Field(default=0.40, description="Unit cost of executing this intervention")
    expected_value_inr: float = Field(default=0.0, description="Net Expected Value = P(rec)*amt - cost - P(churn)*LTV")
    churn_penalty_inr: float = Field(default=0.0, description="P(churn) * LTV")


class ComplianceDecision(BaseModel):
    is_compliant: bool = Field(default=True)
    action_permitted: bool = Field(default=True)
    triggered_stopping_rule: str | None = Field(default=None)
    reason: str = Field("All compliance checks and cooldown limits satisfied.")
    enforced_cooldown_hours: int = Field(default=0)


class PromiseToPayRecord(BaseModel):
    transaction_id: str
    customer_id: str
    promised_amount: float
    promised_date: str
    status: str = Field(default="PENDING", description="PENDING, FULFILLED, BROKEN")
    notes: str = Field(default="")
    recorded_at: datetime = Field(default_factory=datetime.now)


class AuditLogEntry(BaseModel):
    log_id: str
    timestamp: datetime = Field(default_factory=datetime.now)
    transaction_id: str
    customer_id: str
    agent_name: str
    action_taken: str
    state_before: str
    state_after: str
    compliance_verified: bool = True
    previous_hash: str = Field(default="0" * 64, description="SHA-256 hash of previous audit log entry")
    entry_hash: str = Field(default="", description="Cryptographic SHA-256 hash of this entry")
    details: dict[str, Any] = Field(default_factory=dict)


class TransactionRecoveryRecord(BaseModel):
    event: TransactionFailureEvent
    diagnosis: RootCauseDiagnosis | None = None
    intervention: RecoveryIntervention | None = None
    compliance: ComplianceDecision | None = None
    status: RecoveryStatus = Field(default=RecoveryStatus.AT_RISK)
    money_recovered: float = Field(default=0.0)
    baseline_recovered: float = Field(default=0.0, description="Amount recovered by baseline static policy")
    recovery_timestamp: datetime | None = None
    audit_logs: list[AuditLogEntry] = Field(default_factory=list)
    ptp_record: PromiseToPayRecord | None = None


class BaselineComparisonMetrics(BaseModel):
    total_at_risk_inr: float = 0.0
    agent_gross_recovered_inr: float = 0.0
    agent_contact_costs_inr: float = 0.0
    agent_net_recovered_inr: float = 0.0
    baseline_recovered_inr: float = 0.0
    lift_inr: float = 0.0
    lift_percentage: float = 0.0
    cost_per_recovered_rupee: float = 0.0
    agent_recovery_rate_pct: float = 0.0
    baseline_recovery_rate_pct: float = 0.0
    compliance_violations_count: int = 0
    audit_completeness_pct: float = 100.0


class BatchRecoveryRequest(BaseModel):
    batch_id: str
    transactions: list[TransactionFailureEvent]
    auto_execute: bool = True


class BatchRecoveryResult(BaseModel):
    batch_id: str
    total_transactions: int
    total_revenue_at_risk: float
    total_revenue_recovered: float
    recovery_rate_pct: float
    recovered_count: int
    stopped_count: int
    escalated_count: int
    compliance_adherence_pct: float = 100.0
    channel_distribution: dict[str, int] = Field(default_factory=dict)
    average_recovery_time_minutes: float = 0.0
    records: list[TransactionRecoveryRecord] = Field(default_factory=list)
    baseline_metrics: BaselineComparisonMetrics = Field(default_factory=BaselineComparisonMetrics)
    execution_duration_sec: float = 0.0


class RecoveryKPIs(BaseModel):
    total_at_risk_inr: float = 0.0
    total_recovered_inr: float = 0.0
    net_recovery_rate_pct: float = 0.0
    total_events_processed: int = 0
    active_recovery_pipelines: int = 0
    total_ptp_secured_inr: float = 0.0
    compliance_violation_count: int = 0
    channel_recovery_rates: dict[str, float] = Field(default_factory=dict)
    total_contact_costs_inr: float = 0.0
    net_revenue_lift_inr: float = 0.0


# =============================================================================
# NEW: PTP State Machine
# =============================================================================

class PTPStatus(StrEnum):
    PROPOSED = "PROPOSED"
    ACCEPTED = "ACCEPTED"
    PENDING = "PENDING"
    FULFILLED = "FULFILLED"
    BROKEN = "BROKEN"


# =============================================================================
# NEW: Channel Delivery Result (explicit — never fake success)
# =============================================================================

class ChannelDeliveryStatus(StrEnum):
    """Explicit delivery outcome — never fabricate SENT without provider confirmation."""
    MESSAGE_FORMATTED = "MESSAGE_FORMATTED"      # message text built; not sent yet
    QUEUED = "QUEUED"                            # queued with provider
    SENT = "SENT"                                # provider confirmed dispatch
    DELIVERED = "DELIVERED"                      # provider confirmed delivery
    FAILED = "FAILED"                            # provider returned error
    NOT_CONFIGURED = "NOT_CONFIGURED"            # no provider credentials
    PROVIDER_ERROR = "PROVIDER_ERROR"            # provider returned non-fatal error


class ChannelDeliveryResult(BaseModel):
    channel: CommunicationChannel
    status: ChannelDeliveryStatus = ChannelDeliveryStatus.NOT_CONFIGURED
    provider: str | None = Field(default=None, description="Provider name e.g. meta_whatsapp, sendgrid")
    provider_message_id: str | None = None
    message_preview: str = Field(default="", description="First 200 chars of formatted message")
    attempted_at: datetime = Field(default_factory=datetime.now)
    error_detail: str | None = None


# =============================================================================
# NEW: Payment Link Record (real Razorpay link vs mock)
# =============================================================================

class PaymentLinkSource(StrEnum):
    RAZORPAY_TEST_MODE = "RAZORPAY_TEST_MODE"    # Real Test Mode API — authoritative
    MOCK_SANDBOX = "MOCK_SANDBOX"                 # High-fidelity local mock
    SYNTHETIC_BENCHMARK = "SYNTHETIC_BENCHMARK"   # Deterministic test fixture


class PaymentLinkRecord(BaseModel):
    link_id: str = Field(default_factory=lambda: f"plink_mock_{uuid4().hex[:8]}")
    short_url: str = Field(default="")
    source: PaymentLinkSource = PaymentLinkSource.MOCK_SANDBOX
    recovery_case_id: str = ""
    transaction_id: str = ""
    amount_inr: float = 0.0
    customer_id: str = ""
    created_at: datetime = Field(default_factory=datetime.now)
    expires_at: datetime | None = None
    status: str = Field("created", description="created, paid, cancelled, expired")
    # Set only after real payment via webhook/API reconciliation
    payment_id: str | None = Field(default=None, description="Razorpay payment ID after payment.captured")
    payment_amount_inr: float | None = Field(default=None, description="Actual amount paid (after reconciliation)")
    payment_confirmed_at: datetime | None = None


# =============================================================================
# NEW: Execution Result (canonical output of the Executor layer)
# =============================================================================

class ExecutionStatus(StrEnum):
    PAYMENT_LINK_CREATED = "PAYMENT_LINK_CREATED"    # Real or mock link created
    RETRY_SCHEDULED = "RETRY_SCHEDULED"               # Silent API retry queued
    CHANNEL_MESSAGE_SENT = "CHANNEL_MESSAGE_SENT"     # Channel dispatch attempted
    ESCALATED_TO_HUMAN = "ESCALATED_TO_HUMAN"         # Handed to human desk
    BLOCKED_BY_GOVERNOR = "BLOCKED_BY_GOVERNOR"       # Governor halted execution
    PROVIDER_NOT_CONFIGURED = "PROVIDER_NOT_CONFIGURED"
    EXECUTION_FAILED = "EXECUTION_FAILED"


class ExecutionResult(BaseModel):
    """Canonical output of the Executor layer. Records what actually happened."""
    execution_id: str = Field(default_factory=lambda: f"exec_{uuid4().hex[:12]}")
    recovery_case_id: str = ""
    transaction_id: str = ""
    status: ExecutionStatus = ExecutionStatus.PROVIDER_NOT_CONFIGURED
    payment_link: PaymentLinkRecord | None = None
    channel_result: ChannelDeliveryResult | None = None
    executed_at: datetime = Field(default_factory=datetime.now)
    # Synthetic flag: if True, this execution used probabilistic simulation (benchmark)
    is_synthetic: bool = Field(default=False, description="True if outcome is simulated for benchmark purposes")
    synthetic_outcome: bool | None = Field(default=None, description="Simulated recovery outcome (benchmark only)")
    error: str | None = None


# =============================================================================
# NEW: Recovery Case State Machine
# =============================================================================

class RecoveryCaseStatus(StrEnum):
    """Explicit state machine — every transition must be audited."""
    RECEIVED = "RECEIVED"
    DIAGNOSED = "DIAGNOSED"
    STRATEGIZED = "STRATEGIZED"
    GOVERNANCE_APPROVED = "GOVERNANCE_APPROVED"
    GOVERNANCE_BLOCKED = "GOVERNANCE_BLOCKED"
    PAYMENT_LINK_CREATED = "PAYMENT_LINK_CREATED"
    OUTREACH_SENT = "OUTREACH_SENT"
    PAYMENT_PENDING = "PAYMENT_PENDING"
    RECOVERED = "RECOVERED"          # Evidence: real Razorpay payment_id OR synthetic_outcome=True
    FAILED = "FAILED"
    EXPIRED = "EXPIRED"
    ESCALATED = "ESCALATED"
    PTP_ACTIVE = "PTP_ACTIVE"
