import json
import random
from datetime import datetime, timedelta
from pathlib import Path

from schema.recovery_schema import (
    CommunicationChannel,
    CustomerTier,
    TransactionFailureEvent,
)


class RecoveryBatchSimulator:
    """Simulator for generating and executing realistic revenue recovery batches."""

    SAMPLE_NAMES = [
        ("Aarav Sharma", "+919876543210", "aarav.s@example.com"),
        ("Diya Patel", "+919812345678", "diya.p@example.com"),
        ("Vikram Malhotra", "+919823456789", "vikram.m@example.com"),
        ("Ananya Iyer", "+919834567890", "ananya.i@example.com"),
        ("Rohan Gupta", "+919845678901", "rohan.g@example.com"),
        ("Sneha Deshmukh", "+919856789012", "sneha.d@example.com"),
        ("Kavita Rao", "+919867890123", "kavita.r@example.com"),
        ("Arjun Nair", "+919878901234", "arjun.n@example.com"),
        ("Pooja Singhania", "+919889012345", "pooja.s@example.com"),
        ("Nikhil Verma", "+919890123456", "nikhil.v@example.com"),
        ("Bharat Dynamics Pvt Ltd", "+919801122334", "ap@bharatdynamics.in"),
        ("Apex Cloud Services", "+919811223344", "billing@apexcloud.co"),
        ("Matrix Retail Logistics", "+919822334455", "finance@matrixretail.in"),
        ("Zeta Tech Ventures", "+919833445566", "accounts@zetatech.io"),
        ("Quantum Health Analytics", "+919844556677", "receivables@quantumhealth.in"),
    ]

    BANKS = ["HDFC", "ICICI", "SBI", "AXIS", "KOTAK", "UPI_NETWORK"]
    SCENARIOS = [
        "PAYMENT_FAILURE",
        "CHECKOUT_ABANDONMENT",
        "RECURRING_SUBSCRIPTION",
        "B2B_INVOICE_OVERDUE",
    ]

    @classmethod
    def generate_synthetic_batch(cls, count: int = 100) -> list[TransactionFailureEvent]:
        events = []
        base_time = datetime.now()

        for i in range(1, count + 1):
            name, phone, email = random.choice(cls.SAMPLE_NAMES)
            phone_unique = f"{phone[:-4]}{i:04d}"
            scenario = random.choice(cls.SCENARIOS)

            # Assign customer tier and realistic LTV
            if i % 10 == 0:
                tier = CustomerTier.VIP_PLATINUM
                ltv = round(random.uniform(50000, 150000), 2)
                past_payments = random.randint(8, 25)
            elif i % 5 == 0:
                tier = CustomerTier.PLATINUM
                ltv = round(random.uniform(25000, 60000), 2)
                past_payments = random.randint(4, 12)
            elif scenario == "B2B_INVOICE_OVERDUE":
                tier = CustomerTier.ENTERPRISE
                ltv = round(random.uniform(100000, 500000), 2)
                past_payments = random.randint(3, 15)
            elif i % 3 == 0:
                tier = CustomerTier.GOLD
                ltv = round(random.uniform(10000, 30000), 2)
                past_payments = random.randint(2, 6)
            else:
                tier = CustomerTier.STANDARD
                ltv = round(random.uniform(3000, 12000), 2)
                past_payments = random.randint(0, 3)

            # Scenario-specific amounts and error codes
            fraud_suspected = False
            if scenario == "B2B_INVOICE_OVERDUE":
                amount = round(random.uniform(25000, 220000), 2)
                error_code = random.choice(["INVOICE_OVERDUE_TIER_1", "INVOICE_OVERDUE_TIER_2", "INVOICE_DISPUTE"])
                payment_method = random.choice(["NEFT", "RTGS", "BANK_TRANSFER"])
            elif scenario == "RECURRING_SUBSCRIPTION":
                amount = round(random.uniform(999, 14999), 2)
                error_code = random.choice(["CARD_EXPIRED", "INSUFFICIENT_FUNDS", "MANDATE_EXPIRED", "SUBSCRIPTION_HALTED"])
                payment_method = random.choice(["E_MANDATE_CARD", "E_MANDATE_UPI"])
            elif scenario == "CHECKOUT_ABANDONMENT":
                amount = round(random.uniform(799, 29999), 2)
                error_code = random.choice(["CHECKOUT_DROP_OFF", "PRICE_SENSITIVITY"])
                payment_method = random.choice(["UPI", "CREDIT_CARD", "EMI"])
            else:
                amount = round(random.uniform(499, 18999), 2)
                error_code = random.choice([
                    "BAD_REQUEST_PAYMENT_TIMED_OUT",
                    "GATEWAY_ERROR",
                    "BAD_REQUEST_PAYMENT_OTP_VALIDATION_FAILED",
                    "PAYMENT_DECLINED_BY_BANK",
                    "UPI_APP_NOT_RESPONDING",
                    "DO_NOT_HONOR",
                ])
                payment_method = random.choice(["UPI", "CREDIT_CARD", "DEBIT_CARD", "NETBANKING"])

            # Introduce realistic edge case flags
            if i % 45 == 0:
                fraud_suspected = True
                error_code = "FRAUD_SUSPECTED"

            opted_out = (i % 25 == 0)
            disputed = (i % 30 == 0 and scenario == "B2B_INVOICE_OVERDUE") or (error_code == "INVOICE_DISPUTE")
            bank = random.choice(cls.BANKS)
            event_time = base_time - timedelta(minutes=random.randint(5, 3600))

            # Channel consents
            consents = [CommunicationChannel.WHATSAPP, CommunicationChannel.EMAIL, CommunicationChannel.SMS]
            if tier in [CustomerTier.VIP_PLATINUM, CustomerTier.PLATINUM, CustomerTier.ENTERPRISE]:
                consents.append(CommunicationChannel.VOICE_HINGLISH)

            events.append(
                TransactionFailureEvent(
                    transaction_id=f"txn_{scenario[:4].lower()}_{1000 + i}",
                    customer_id=f"cust_{100 + i}",
                    customer_name=f"{name} #{i}",
                    customer_phone=phone_unique,
                    customer_email=f"user{i}@{email.split('@')[1]}",
                    customer_tier=tier,
                    customer_ltv=ltv,
                    past_successful_payments=past_payments,
                    channel_consent=consents,
                    amount=amount,
                    currency="INR",
                    scenario=scenario,
                    error_code=error_code,
                    bank=bank,
                    payment_method=payment_method,
                    failure_timestamp=event_time,
                    attempt_count=random.choice([0, 0, 1]),
                    opted_out=opted_out,
                    disputed=disputed,
                    fraud_suspected=fraud_suspected,
                    metadata={"batch_index": i, "intent_score": round(random.uniform(0.80, 0.98), 2)},
                )
            )
        return events

    @classmethod
    def load_benchmark_file(cls, filepath: str | Path) -> list[TransactionFailureEvent]:
        path = Path(filepath)
        if not path.exists():
            return cls.generate_synthetic_batch(100)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
            cases = data.get("cases", [])
            return [TransactionFailureEvent(**c) for c in cases]
