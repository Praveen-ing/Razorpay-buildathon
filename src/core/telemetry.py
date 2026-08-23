import threading
from datetime import datetime
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

            return RecoveryKPIs(
                total_at_risk_inr=round(self.total_at_risk, 2),
                total_recovered_inr=round(self.total_recovered, 2),
                net_recovery_rate_pct=round(recovery_rate, 1),
                total_events_processed=len(self.records),
                active_recovery_pipelines=len([r for r in self.records if r.status in [RecoveryStatus.AT_RISK, RecoveryStatus.OUTREACH_ACTIVE]]),
                total_ptp_secured_inr=round(self.active_ptp_total, 2),
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


# Global singleton instance
telemetry_tracker = RecoveryTelemetryTracker()
