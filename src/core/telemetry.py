import threading
from datetime import datetime
from typing import Any
from schema.recovery_schema import RecoveryKPIs, TransactionRecoveryRecord, RecoveryStatus



class RecoveryTelemetryTracker:
    """Thread-safe in-memory analytics and telemetry accumulator for AI Revenue Recovery."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.records: list[TransactionRecoveryRecord] = []
        self.total_at_risk: float = 0.0
        self.total_recovered: float = 0.0
        self.total_baseline_recovered: float = 0.0
        self.total_contact_costs: float = 0.0
        self.channel_counts: dict[str, int] = {}
        self.channel_recoveries: dict[str, float] = {}
        self.compliance_violations: int = 0
        self.active_ptp_total: float = 0.0

    def record_transaction(self, record: TransactionRecoveryRecord) -> None:
        with self._lock:
            self.records.append(record)
            self.total_at_risk += record.event.amount
            self.total_baseline_recovered += record.baseline_recovered

            if record.status == RecoveryStatus.RECOVERED:
                self.total_recovered += record.money_recovered

            if record.ptp_record and record.ptp_record.status == "PENDING":
                self.active_ptp_total += record.ptp_record.promised_amount

            if record.intervention:
                channel = record.intervention.channel.value
                self.channel_counts[channel] = self.channel_counts.get(channel, 0) + 1
                self.total_contact_costs += record.intervention.contact_cost_inr
                if record.status == RecoveryStatus.RECOVERED:
                    self.channel_recoveries[channel] = self.channel_recoveries.get(channel, 0.0) + record.money_recovered

            if record.compliance and not record.compliance.is_compliant:
                self.compliance_violations += 1

    def get_kpis(self) -> RecoveryKPIs:
        with self._lock:
            recovery_rate = (self.total_recovered / self.total_at_risk * 100.0) if self.total_at_risk > 0 else 0.0
            channel_rates = {}
            for channel, count in self.channel_counts.items():
                rec_amount = self.channel_recoveries.get(channel, 0.0)
                channel_rates[channel] = round(rec_amount, 2)

            net_recovered = self.total_recovered - self.total_contact_costs
            net_lift = net_recovered - self.total_baseline_recovered
            blocked_count = len([
                r for r in self.records 
                if (r.compliance and not r.compliance.action_permitted) 
                or (r.status and r.status.value.startswith("STOPPED"))
            ])

            return RecoveryKPIs(
                total_at_risk_inr=round(self.total_at_risk, 2),
                total_recovered_inr=round(self.total_recovered, 2),
                net_recovery_rate_pct=round(recovery_rate, 1),
                total_events_processed=len(self.records),
                active_recovery_pipelines=len([r for r in self.records if r.status in [RecoveryStatus.AT_RISK, RecoveryStatus.OUTREACH_ACTIVE]]),
                total_ptp_secured_inr=round(self.active_ptp_total, 2),
                total_blocked=blocked_count,
                compliance_violation_count=self.compliance_violations,
                channel_recovery_rates=channel_rates,
                total_contact_costs_inr=round(self.total_contact_costs, 2),
                net_revenue_lift_inr=round(net_lift, 2),
            )

    def get_recent_records(self, limit: int = 50) -> list[TransactionRecoveryRecord]:
        with self._lock:
            return self.records[-limit:]

    def reset(self) -> None:
        with self._lock:
            self.records.clear()
            self.total_at_risk = 0.0
            self.total_recovered = 0.0
            self.total_baseline_recovered = 0.0
            self.total_contact_costs = 0.0
            self.channel_counts.clear()
            self.channel_recoveries.clear()
            self.compliance_violations = 0
            self.active_ptp_total = 0.0


class BankHealthTracker:
    """Real-time Indian Bank Gateway Telemetry and Pre-Emptive Failure Interception Engine."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._bank_telemetry: dict[str, dict[str, Any]] = {
            "HDFC": {"success_rate_pct": 98.2, "latency_ms": 420, "status": "OPTIMAL", "recommended_route": "Razorpay Standard"},
            "SBI": {"success_rate_pct": 64.5, "latency_ms": 1850, "status": "DEGRADED", "recommended_route": "Razorpay Turbo UPI / ICICI Direct"},
            "ICICI": {"success_rate_pct": 99.1, "latency_ms": 310, "status": "OPTIMAL", "recommended_route": "Razorpay Direct Netbanking"},
            "AXIS": {"success_rate_pct": 97.8, "latency_ms": 490, "status": "OPTIMAL", "recommended_route": "Razorpay Standard"},
            "UPI_NETWORK": {"success_rate_pct": 99.5, "latency_ms": 280, "status": "OPTIMAL", "recommended_route": "Razorpay Flash UPI"},
        }

    def get_bank_health(self, bank_name: str) -> dict[str, Any]:
        with self._lock:
            return self._bank_telemetry.get(
                bank_name.upper(),
                {"success_rate_pct": 98.0, "latency_ms": 400, "status": "OPTIMAL", "recommended_route": "Razorpay Standard"}
            )

    def set_bank_degradation(self, bank_name: str, success_rate_pct: float, latency_ms: int) -> None:
        with self._lock:
            status = "OPTIMAL" if success_rate_pct >= 90.0 else ("DEGRADED" if success_rate_pct >= 60.0 else "DOWN")
            route = "Razorpay Turbo UPI / ICICI Direct" if status != "OPTIMAL" else "Razorpay Standard"
            self._bank_telemetry[bank_name.upper()] = {
                "success_rate_pct": success_rate_pct,
                "latency_ms": latency_ms,
                "status": status,
                "recommended_route": route,
            }

    def get_all_telemetry(self) -> dict[str, dict[str, Any]]:
        with self._lock:
            return dict(self._bank_telemetry)


# Global singleton instances
telemetry_tracker = RecoveryTelemetryTracker()
bank_health_tracker = BankHealthTracker()

