import random
import pytest
from agents.orchestrator import RecoveryOrchestrator
from integrations.razorpay_client import razorpay_client
from integrations.simulator import RecoveryBatchSimulator


def test_batch_recovery_100_cases(monkeypatch):
    # Set mock_mode to True for ultra-fast unit test execution without 100 network roundtrips
    monkeypatch.setattr(razorpay_client, "mock_mode", True)
    random.seed(42)
    
    orchestrator = RecoveryOrchestrator()
    events = RecoveryBatchSimulator.generate_synthetic_batch(100)
    assert len(events) == 100

    result = orchestrator.process_batch("TEST-BATCH-100", events)

    assert result.total_transactions == 100
    assert result.total_revenue_at_risk > 0.0
    assert result.total_revenue_recovered > 0.0
    assert result.recovered_count >= 35
    assert result.compliance_adherence_pct == 100.0
    assert len(result.records) == 100
    assert result.stopped_count >= 1  # Verify stopping rules triggered on opt-out/dispute/fraud cases
    assert len(result.channel_distribution) > 0

    # Verify Baseline Lift & Unit Economics Metrics
    bm = result.baseline_metrics
    assert bm.total_at_risk_inr == result.total_revenue_at_risk
    assert bm.agent_gross_recovered_inr == result.total_revenue_recovered
    assert bm.agent_contact_costs_inr > 0.0
    assert bm.agent_net_recovered_inr > 0.0
    assert bm.lift_inr > 0.0  # Proves agent outperforms naive baseline
    assert bm.compliance_violations_count == 0
    assert bm.audit_completeness_pct == 100.0
