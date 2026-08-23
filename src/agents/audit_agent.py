import hashlib
import json
import logging
from datetime import datetime
from typing import Any
from schema.recovery_schema import AuditLogEntry

logger = logging.getLogger(__name__)


class AuditLedgerAgent:
    """Agent that creates immutable, cryptographically verifiable audit trail logs for all decisions, transitions, and recovered funds."""

    def __init__(self) -> None:
        self.logs: list[AuditLogEntry] = []
        self._last_hash: str = "0" * 64

    def create_log(
        self,
        transaction_id: str,
        customer_id: str,
        agent_name: str,
        action_taken: str,
        state_before: str,
        state_after: str,
        compliance_verified: bool = True,
        details: dict[str, Any] | None = None,
    ) -> AuditLogEntry:
        timestamp = datetime.now()
        raw_sig = f"{transaction_id}_{agent_name}_{action_taken}_{timestamp.isoformat()}"
        log_id = f"aud_{hashlib.sha256(raw_sig.encode()).hexdigest()[:12]}"
        
        details_clean = details or {}
        details_str = json.dumps(details_clean, sort_keys=True, default=str)
        payload_to_hash = (
            f"{self._last_hash}:{log_id}:{timestamp.isoformat()}:{transaction_id}:"
            f"{customer_id}:{agent_name}:{action_taken}:{state_before}:{state_after}:"
            f"{compliance_verified}:{details_str}"
        )
        entry_hash = hashlib.sha256(payload_to_hash.encode("utf-8")).hexdigest()

        entry = AuditLogEntry(
            log_id=log_id,
            timestamp=timestamp,
            transaction_id=transaction_id,
            customer_id=customer_id,
            agent_name=agent_name,
            action_taken=action_taken,
            state_before=state_before,
            state_after=state_after,
            compliance_verified=compliance_verified,
            previous_hash=self._last_hash,
            entry_hash=entry_hash,
            details=details_clean,
        )
        self._last_hash = entry_hash
        self.logs.append(entry)
        logger.info(
            f"[Audit Ledger] {log_id} | {transaction_id} | {agent_name} -> {action_taken} ({state_before} -> {state_after}) | Hash: {entry_hash[:8]}..."
        )
        return entry

    def verify_ledger_integrity(self) -> tuple[bool, int]:
        """Verifies the SHA-256 hash chain across all log entries to prove zero tampering."""
        prev_hash = "0" * 64
        for idx, entry in enumerate(self.logs):
            if entry.previous_hash != prev_hash:
                return False, idx
            details_str = json.dumps(entry.details, sort_keys=True, default=str)
            payload = (
                f"{entry.previous_hash}:{entry.log_id}:{entry.timestamp.isoformat()}:{entry.transaction_id}:"
                f"{entry.customer_id}:{entry.agent_name}:{entry.action_taken}:{entry.state_before}:{entry.state_after}:"
                f"{entry.compliance_verified}:{details_str}"
            )
            expected_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()
            if entry.entry_hash != expected_hash:
                return False, idx
            prev_hash = entry.entry_hash
        return True, len(self.logs)

    def get_logs_for_transaction(self, transaction_id: str) -> list[AuditLogEntry]:
        return [l for l in self.logs if l.transaction_id == transaction_id]

    def get_all_logs(self, limit: int = 100) -> list[AuditLogEntry]:
        return self.logs[-limit:]

    def clear(self) -> None:
        self.logs.clear()
        self._last_hash = "0" * 64


audit_ledger_agent = AuditLedgerAgent()
