from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field


class RazorpayPaymentEntity(BaseModel):
    id: str = Field(..., description="Razorpay payment ID e.g. pay_29QQoUBcxBqqIL")
    entity: str = "payment"
    amount: int = Field(..., description="Amount in paise (e.g. 10000 = ₹100.00)")
    currency: str = "INR"
    status: str = Field(..., description="failed, captured, authorized, refunded")
    order_id: str | None = None
    invoice_id: str | None = None
    international: bool = False
    method: str = Field("upi", description="upi, card, netbanking, wallet, emi")
    amount_refunded: int = 0
    refund_status: str | None = None
    captured: bool = False
    description: str | None = None
    card_id: str | None = None
    bank: str | None = None
    wallet: str | None = None
    vpa: str | None = None
    email: str | None = None
    contact: str | None = None
    error_code: str | None = None
    error_description: str | None = None
    error_source: str | None = None
    error_step: str | None = None
    error_reason: str | None = None
    created_at: int | None = None


class RazorpaySubscriptionEntity(BaseModel):
    id: str = Field(..., description="Razorpay subscription ID e.g. sub_1001")
    entity: str = "subscription"
    plan_id: str | None = None
    customer_id: str | None = None
    status: str = Field("active", description="active, pending, halted, cancelled, completed")
    current_start: int | None = None
    current_end: int | None = None
    ended_at: int | None = None
    quantity: int = 1
    notes: dict[str, Any] = Field(default_factory=dict)
    charge_at: int | None = None
    start_at: int | None = None
    end_at: int | None = None
    auth_attempts: int = 0
    total_count: int = 12
    paid_count: int = 0
    remaining_count: int = 12


class RazorpayInvoiceEntity(BaseModel):
    id: str = Field(..., description="Razorpay invoice ID e.g. inv_2026_9081")
    entity: str = "invoice"
    customer_id: str | None = None
    order_id: str | None = None
    status: str = Field("issued", description="draft, issued, partially_paid, paid, cancelled, expired")
    expire_by: int | None = None
    issued_at: int | None = None
    paid_at: int | None = None
    cancelled_at: int | None = None
    expired_at: int | None = None
    amount: int = Field(..., description="Amount in paise")
    amount_paid: int = 0
    amount_due: int = 0
    currency: str = "INR"
    short_url: str | None = None


class RazorpayWebhookPayload(BaseModel):
    entity: str = "event"
    account_id: str = Field("acc_test_razorpay", description="Merchant account ID")
    event: str = Field(..., description="payment.failed, payment.captured, subscription.halted, invoice.paid, etc.")
    contains: list[str] = Field(default_factory=list)
    payload: dict[str, Any] = Field(..., description="Contains payment, order, subscription, invoice objects")
    created_at: int = Field(default_factory=lambda: int(datetime.now().timestamp()))


class RazorpayPaymentLinkCreateRequest(BaseModel):
    amount: float = Field(..., description="Amount in INR (₹)")
    currency: str = "INR"
    accept_partial: bool = False
    description: str = Field("Payment Recovery Link")
    customer: dict[str, str] = Field(default_factory=dict, description="name, email, contact")
    notify: dict[str, bool] = Field(default_factory=lambda: {"sms": True, "email": True, "whatsapp": True})
    reminder_enable: bool = True
    notes: dict[str, str] = Field(default_factory=dict)
    expire_by_minutes: int = 1440  # 24 hours


class RazorpayPaymentLinkResponse(BaseModel):
    id: str
    short_url: str
    status: str = "created"
    amount: float
    currency: str = "INR"
    customer_name: str
    customer_contact: str
    created_at: datetime = Field(default_factory=datetime.now)

