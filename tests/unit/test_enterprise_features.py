import pytest
from agents.audit_agent import audit_ledger_agent
from core.telemetry import bank_health_tracker, calculate_enterprise_roi
from schema.recovery_schema import ZKComplianceProof


def test_zk_proof_generation_and_verification():
    proof = audit_ledger_agent.generate_zkp_compliance_proof("rcase_test_123", "txn_test_456")
    assert proof.proof_id.startswith("zkp_")
    assert proof.zk_hash.startswith("zkp_sha256_")
    assert proof.dpdp_consent_verified is True
    assert proof.dnd_opt_out_verified is True

    is_valid, msg = audit_ledger_agent.verify_zkp_compliance_proof(proof)
    assert is_valid is True
    assert "Cryptographic ZK Proof Verified" in msg or "Valid Cryptographic Signature Verified" in msg


def test_preemptive_bank_telemetry_interception():
    # Set bank to degraded
    bank_health_tracker.set_bank_degradation("SBI", success_rate_pct=42.0, latency_ms=2100)
    advice = bank_health_tracker.preemptive_interception_advice("SBI")

    assert advice["bank_name"] == "SBI"
    assert advice["gateway_status"] in ["DEGRADED", "DOWN"]
    assert advice["preemptive_interception_recommended"] is True
    assert advice["optimal_target_route"] == "Razorpay Turbo UPI / ICICI Direct"
    assert advice["estimated_success_lift_pct"] > 0


def test_enterprise_roi_calculator():
    res = calculate_enterprise_roi(annual_gmv_inr=100000000.0, recovery_rate_pct=75.0)
    assert res["annual_gmv_inr"] == 100000000.0
    assert res["estimated_annual_at_risk_inr"] == 8500000.0
    assert res["gross_recovered_inr"] == 6375000.0
    assert res["net_recovered_inr"] > 6000000.0
    assert res["roi_multiple"] > 100.0
