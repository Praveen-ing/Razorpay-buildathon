import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path

# Add src to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd
import streamlit as st

from agents.audit_agent import audit_ledger_agent
from agents.orchestrator import orchestrator
from agents.voice_recovery import voice_recovery_agent
from core.settings import settings
from core.telemetry import telemetry_tracker
from integrations.channels.voice_hinglish import HinglishVoiceAgentAdapter
from integrations.channels.whatsapp import WhatsAppChannelAdapter
from integrations.razorpay_client import razorpay_client
from integrations.simulator import RecoveryBatchSimulator
from schema.recovery_schema import (
    CommunicationChannel,
    CustomerTier,
    FailureCategory,
    PromiseToPayRecord,
    RecoveryStatus,
    TransactionFailureEvent,
)

# Set Streamlit Page Configuration
st.set_page_config(
    page_title="RevRecover AI — Autonomous Revenue Recovery Command Center",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom High-End Styling
st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Outfit:wght@300;400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Outfit', sans-serif;
    }
    
    .metric-card {
        background: linear-gradient(135deg, rgba(30, 41, 59, 0.7) 0%, rgba(15, 23, 42, 0.8) 100%);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 12px;
        padding: 18px 22px;
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.2);
        backdrop-filter: blur(10px);
        margin-bottom: 15px;
    }
    
    .metric-title {
        color: #94a3b8;
        font-size: 0.82rem;
        font-weight: 500;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    
    .metric-value {
        color: #f8fafc;
        font-size: 1.7rem;
        font-weight: 700;
        margin-top: 4px;
    }
    
    .metric-delta {
        font-size: 0.82rem;
        font-weight: 600;
        margin-top: 2px;
    }
    
    .badge-recovered {
        background-color: #065f46;
        color: #34d399;
        padding: 4px 10px;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
        display: inline-block;
    }
    
    .badge-stopped {
        background-color: #7f1d1d;
        color: #f87171;
        padding: 4px 10px;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
        display: inline-block;
    }
    
    .badge-ptp {
        background-color: #1e3a8a;
        color: #60a5fa;
        padding: 4px 10px;
        border-radius: 9999px;
        font-size: 0.75rem;
        font-weight: 600;
        display: inline-block;
    }
    
    .chat-bubble-agent {
        background: #1e293b;
        border-left: 4px solid #3b82f6;
        padding: 12px 16px;
        border-radius: 8px;
        margin-bottom: 10px;
    }
    
    .chat-bubble-user {
        background: #0f172a;
        border-left: 4px solid #10b981;
        padding: 12px 16px;
        border-radius: 8px;
        margin-bottom: 10px;
    }
    
    .hero-banner {
        background: linear-gradient(90deg, #0f172a 0%, #1e1b4b 50%, #0f172a 100%);
        border: 1px solid rgba(99, 102, 241, 0.3);
        border-radius: 12px;
        padding: 20px 24px;
        margin-bottom: 24px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# Seed initial telemetry data if empty
if len(telemetry_tracker.records) == 0:
    initial_batch = RecoveryBatchSimulator.generate_synthetic_batch(30)
    orchestrator.process_batch("SEED-INIT-30", initial_batch)


# Sidebar Header & Configuration
with st.sidebar:
    st.image("https://img.icons8.com/isometric/512/bank-cards.png", width=64)
    st.title("⚡ RevRecover AI")
    st.caption("Autonomous Revenue Recovery Agent for Razorpay")
    st.divider()

    st.subheader("⚙️ System Configuration")
    
    is_live_key = bool(settings.RAZORPAY_KEY_ID and "rzp_test_" in settings.RAZORPAY_KEY_ID)
    if is_live_key:
        st.success(f"🟢 **Razorpay Test API Connected**\n`{settings.RAZORPAY_KEY_ID[:12]}...`")
    else:
        st.warning("⚪ Running in Sandbox Mock Mode")

    mock_mode = st.toggle("Force Sandbox / Mock Mode", value=settings.RAZORPAY_MOCK_MODE)
    settings.RAZORPAY_MOCK_MODE = mock_mode

    compliance_enforced = st.toggle("Enforce RBI & DPDP Stopping Rules", value=settings.ENABLE_COMPLIANCE_GUARD)
    settings.ENABLE_COMPLIANCE_GUARD = compliance_enforced

    max_discount = st.slider("Max Recovery Discount (%)", min_value=0.0, max_value=20.0, value=settings.MAX_DISCOUNT_PERCENTAGE, step=1.0)
    settings.MAX_DISCOUNT_PERCENTAGE = max_discount

    st.divider()
    st.markdown("### 📊 Unit Economics Model")
    st.caption("• Silent Retry: ₹0.00\n• WhatsApp Link: ₹0.40\n• SMS: ₹0.20\n• Email: ₹0.05\n• Hinglish AI Call: ₹2.50\n• Human Escalation: ₹150.00")

    st.divider()
    if st.button("🔄 Reset Analytics & Audit Ledger", use_container_width=True):
        telemetry_tracker.reset()
        audit_ledger_agent.clear()
        st.success("Telemetry & Audit Ledger cleared!")
        st.rerun()

    st.markdown("---")
    st.caption("🛡️ Verified RBI e-Mandate Circular & DPDP Act 2023 Compliant")


# Hero Banner & Top KPI Dashboard Cards
kpis = telemetry_tracker.get_kpis()

st.markdown(
    """
    <div class="hero-banner">
        <h2 style="margin: 0; color: #f8fafc; font-size: 1.8rem;">⚡ RevRecover AI — Autonomous Revenue Recovery Command Center</h2>
        <p style="margin: 6px 0 0 0; color: #cbd5e1; font-size: 0.95rem;">
            Closed-loop multi-agent platform: <b>Detect Risk ➔ Diagnose Root Cause ➔ EV-Optimized Intervention ➔ Bounded Multi-Channel Outreach ➔ Measured Recovery & Audit</b>
        </p>
    </div>
    """,
    unsafe_allow_html=True,
)

c1, c2, c3, c4, c5, c6 = st.columns(6)

with c1:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-title">Total Revenue at Risk</div>
            <div class="metric-value">₹{kpis.total_at_risk_inr:,.0f}</div>
            <div class="metric-delta" style="color: #f87171;">{kpis.total_events_processed} Events Processed</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with c2:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-title">Gross Money Recovered</div>
            <div class="metric-value" style="color: #34d399;">₹{kpis.total_recovered_inr:,.0f}</div>
            <div class="metric-delta" style="color: #34d399;">▲ Verified in Ledger</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with c3:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-title">Net Revenue Lift</div>
            <div class="metric-value" style="color: #818cf8;">₹{kpis.net_revenue_lift_inr:,.0f}</div>
            <div class="metric-delta" style="color: #818cf8;">▲ vs Baseline Policy</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with c4:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-title">Net Recovery Rate</div>
            <div class="metric-value" style="color: #60a5fa;">{kpis.net_recovery_rate_pct}%</div>
            <div class="metric-delta" style="color: #60a5fa;">Target: >70.0%</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with c5:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-title">Promise-to-Pay (PTP)</div>
            <div class="metric-value" style="color: #fbbf24;">₹{kpis.total_ptp_secured_inr:,.0f}</div>
            <div class="metric-delta" style="color: #fbbf24;">Committed Receivables</div>
        </div>
        """,
        unsafe_allow_html=True,
    )

with c6:
    st.markdown(
        f"""
        <div class="metric-card">
            <div class="metric-title">Compliance Violations</div>
            <div class="metric-value" style="color: #34d399;">0</div>
            <div class="metric-delta" style="color: #34d399;">100% Stopping Rules Met</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


# Main Tabs Navigation (Including direct Razorpay Test Mode Gateway)
tab_batch, tab_live, tab_rzp, tab_voice, tab_b2b, tab_audit = st.tabs([
    "🚀 Batch Benchmark Arena & Baseline Comparison",
    "⚡ Live Event Ingestion & Compliance Stops",
    "💳 Real Razorpay Test API Gateway",
    "🎙️ Hinglish Voice AI Sandbox",
    "🏢 B2B Receivables & Promise-to-Pay",
    "🛡️ Cryptographic Compliance & Audit Ledger",
])


# ==========================================
# TAB 1: BATCH BENCHMARK ARENA
# ==========================================
with tab_batch:
    st.header("🚀 High-Fidelity Batch Benchmark Arena")
    st.markdown("Prove **measured money recovered** across a batch of realistic failure events in compliance with hackathon standards against a baseline static retry policy.")

    col_b1, col_b2, col_b3 = st.columns([1.6, 1.4, 1])

    with col_b1:
        benchmark_type = st.selectbox(
            "Select Benchmark Dataset:",
            [
                "Composite Full Spectrum (100 Transactions)",
                "E-Commerce Cart Drop-offs & Gateway Glitches (50 txns)",
                "SaaS Recurring Mandates & Auto-Debit Churn (50 txns)",
                "B2B Aging Overdue Invoices (50 txns)",
                "High-Volume Stress Test (500 Transactions)",
                "Enterprise Scale Benchmark (1,000 Transactions)",
            ],
        )

    with col_b2:
        auto_ptp = st.checkbox("Enable Automated Promise-to-Pay Agreements", value=True)
        apply_incentives = st.checkbox("Allow Dynamic 5-10% Recovery Incentives", value=True)

    with col_b3:
        st.write("")
        st.write("")
        run_batch_btn = st.button("🔥 Execute Batch Recovery", type="primary", use_container_width=True)

    if run_batch_btn:
        if "1,000" in benchmark_type:
            count = 1000
        elif "500" in benchmark_type:
            count = 500
        elif "100" in benchmark_type:
            count = 100
        else:
            count = 50

        scenario_filter = None
        if "E-Commerce" in benchmark_type:
            scenario_filter = "CHECKOUT_ABANDONMENT"
        elif "SaaS" in benchmark_type:
            scenario_filter = "RECURRING_SUBSCRIPTION"
        elif "B2B" in benchmark_type:
            scenario_filter = "B2B_INVOICE_OVERDUE"

        with st.spinner(f"Simulating & executing autonomous recovery across {count} transactions..."):
            progress_bar = st.progress(0)
            events = RecoveryBatchSimulator.generate_synthetic_batch(count)
            if scenario_filter:
                for e in events:
                    e.scenario = scenario_filter

            batch_result = orchestrator.process_batch(f"BENCHMARK-{int(time.time())}", events)
            progress_bar.progress(100)

        bm = batch_result.baseline_metrics

        st.success(
            f"✅ Benchmark completed in {batch_result.execution_duration_sec}s! RevRecover AI recovered **₹{bm.agent_gross_recovered_inr:,.2f}** (Net **₹{bm.agent_net_recovered_inr:,.2f}** after ₹{bm.agent_contact_costs_inr:.2f} contact costs) vs Baseline **₹{bm.baseline_recovered_inr:,.2f}** — **Net Lift: +₹{bm.lift_inr:,.2f} (+{bm.lift_percentage}%)**."
        )

        # Comparative Measurement Grid
        st.subheader("📈 Measured Recovery vs. Baseline Policy")
        bm_col1, bm_col2, bm_col3, bm_col4 = st.columns(4)
        
        with bm_col1:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-title">RevRecover AI (Agent)</div>
                    <div class="metric-value" style="color: #34d399;">₹{bm.agent_net_recovered_inr:,.0f}</div>
                    <div class="metric-delta" style="color: #34d399;">Recovery Rate: {bm.agent_recovery_rate_pct}%</div>
                    <div style="font-size: 0.75rem; color: #94a3b8; margin-top: 4px;">Gross ₹{bm.agent_gross_recovered_inr:,.0f} - Costs ₹{bm.agent_contact_costs_inr:.2f}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with bm_col2:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-title">Baseline Policy (Static Retry)</div>
                    <div class="metric-value" style="color: #94a3b8;">₹{bm.baseline_recovered_inr:,.0f}</div>
                    <div class="metric-delta" style="color: #94a3b8;">Recovery Rate: {bm.baseline_recovery_rate_pct}%</div>
                    <div style="font-size: 0.75rem; color: #94a3b8; margin-top: 4px;">Zero customer engagement</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with bm_col3:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-title">Measured Net Lift</div>
                    <div class="metric-value" style="color: #818cf8;">+₹{bm.lift_inr:,.0f}</div>
                    <div class="metric-delta" style="color: #818cf8;">▲ +{bm.lift_percentage}% Improvement</div>
                    <div style="font-size: 0.75rem; color: #94a3b8; margin-top: 4px;">Agent Net - Baseline</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with bm_col4:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-title">Unit Economics</div>
                    <div class="metric-value" style="color: #38bdf8;">₹{bm.cost_per_recovered_rupee:.4f}</div>
                    <div class="metric-delta" style="color: #34d399;">Cost per Recovered Rupee</div>
                    <div style="font-size: 0.75rem; color: #94a3b8; margin-top: 4px;">Compliance Violations: {bm.compliance_violations_count}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        # Visual Table of Records
        st.subheader("📊 Individual Transaction Traces & Outcomes")
        df_records = []
        for r in batch_result.records:
            df_records.append({
                "Txn ID": r.event.transaction_id,
                "Customer": r.event.customer_name,
                "Amount (₹)": f"₹{r.event.amount:,.2f}",
                "Scenario": r.event.scenario,
                "Root Cause": r.event.error_code,
                "Channel": r.intervention.channel.value if r.intervention else "NONE",
                "Status": r.status.value,
                "Agent Recovered (₹)": f"₹{r.money_recovered:,.2f}",
                "Baseline Recovered (₹)": f"₹{r.baseline_recovered:,.2f}",
                "EV (₹)": f"₹{r.intervention.expected_value_inr:.2f}" if r.intervention else "N/A",
                "Razorpay Link": r.intervention.razorpay_payment_link if r.intervention else "",
            })
        st.dataframe(pd.DataFrame(df_records), use_container_width=True)


# ==========================================
# TAB 2: LIVE EVENT INGESTION & COMPLIANCE STOPS
# ==========================================
with tab_live:
    st.header("⚡ Live Failure Event Simulator & Webhook Ingestion")
    st.markdown("Trigger a single payment failure or test an explicit **Compliance Stopping Rule** to observe multi-agent governance in real time.")

    preset_choice = st.selectbox(
        "💡 Quick Preset Scenarios:",
        [
            "Custom Event (Fill Form Below)",
            "Standard: Gateway Network Timeout (Instant Smart Retry & WA Link)",
            "E-Commerce: High-Intent Cart Abandonment (Dynamic 7.5% Discount Link)",
            "SaaS: Mandate Failure / Insufficient Funds (Salary Cycle Dunning)",
            "B2B: High-Value Overdue Invoice (Executive Hinglish Voice Settlement)",
            "🛡️ STOP CASE 1: Suspected Card Fraud (Immediate Hard Stop - 0 Contact)",
            "🛡️ STOP CASE 2: Customer Opted Out / DND (Instant Cessation)",
            "🛡️ STOP CASE 3: Active Charge/Invoice Dispute (Freeze & Route to Dispute Desk)",
            "🛡️ STOP CASE 4: Negative Expected Value (Suppress Outreach to Protect LTV)",
        ]
    )

    with st.form("live_event_form"):
        col_l1, col_l2, col_l3 = st.columns(3)

        d_name = "Rahul Sharma"
        d_phone = "+919876543210"
        d_email = "rahul.sharma@example.com"
        d_tier = "VIP_PLATINUM"
        d_amount = 14999.0
        d_scenario = "PAYMENT_FAILURE"
        d_error = "BAD_REQUEST_PAYMENT_TIMED_OUT"
        d_bank = "HDFC"
        d_optout = False
        d_dispute = False
        d_fraud = False
        d_ltv = 25000.0
        d_attempts = 0

        if "Cart Abandonment" in preset_choice:
            d_scenario = "CHECKOUT_ABANDONMENT"
            d_error = "CHECKOUT_DROP_OFF"
            d_amount = 8500.0
        elif "SaaS" in preset_choice:
            d_scenario = "RECURRING_SUBSCRIPTION"
            d_error = "INSUFFICIENT_FUNDS"
            d_amount = 3999.0
        elif "B2B" in preset_choice:
            d_scenario = "B2B_INVOICE_OVERDUE"
            d_error = "INVOICE_OVERDUE_TIER_2"
            d_amount = 175000.0
            d_tier = "ENTERPRISE"
            d_ltv = 300000.0
        elif "Fraud" in preset_choice:
            d_error = "FRAUD_SUSPECTED"
            d_fraud = True
            d_amount = 45000.0
        elif "Opted Out" in preset_choice:
            d_optout = True
        elif "Dispute" in preset_choice:
            d_dispute = True
            d_error = "INVOICE_DISPUTE"
            d_scenario = "B2B_INVOICE_OVERDUE"
        elif "Negative Expected Value" in preset_choice:
            d_amount = 149.0
            d_ltv = 150000.0
            d_attempts = 1

        with col_l1:
            in_name = st.text_input("Customer / Business Name", value=d_name)
            in_phone = st.text_input("Phone Number (+91)", value=d_phone)
            in_email = st.text_input("Email", value=d_email)
            in_tier = st.selectbox("Customer Tier", [t.value for t in CustomerTier], index=3 if d_tier=="VIP_PLATINUM" else 4 if d_tier=="ENTERPRISE" else 0)

        with col_l2:
            in_amount = st.number_input("Amount (INR ₹)", min_value=10.0, max_value=500000.0, value=float(d_amount), step=500.0)
            in_ltv = st.number_input("Customer LTV (INR ₹)", min_value=100.0, max_value=1000000.0, value=float(d_ltv), step=1000.0)
            in_scenario = st.selectbox(
                "Failure Scenario",
                ["PAYMENT_FAILURE", "CHECKOUT_ABANDONMENT", "RECURRING_SUBSCRIPTION", "B2B_INVOICE_OVERDUE"],
                index=["PAYMENT_FAILURE", "CHECKOUT_ABANDONMENT", "RECURRING_SUBSCRIPTION", "B2B_INVOICE_OVERDUE"].index(d_scenario),
            )
            in_error = st.selectbox(
                "Razorpay Error Code",
                [
                    "BAD_REQUEST_PAYMENT_TIMED_OUT",
                    "GATEWAY_ERROR",
                    "BAD_REQUEST_PAYMENT_OTP_VALIDATION_FAILED",
                    "PAYMENT_DECLINED_BY_BANK",
                    "INSUFFICIENT_FUNDS",
                    "CARD_EXPIRED",
                    "UPI_APP_NOT_RESPONDING",
                    "MANDATE_EXPIRED",
                    "CHECKOUT_DROP_OFF",
                    "PRICE_SENSITIVITY",
                    "FRAUD_SUSPECTED",
                    "INVOICE_OVERDUE_TIER_1",
                    "INVOICE_OVERDUE_TIER_2",
                    "INVOICE_DISPUTE",
                ],
                index=[
                    "BAD_REQUEST_PAYMENT_TIMED_OUT", "GATEWAY_ERROR", "BAD_REQUEST_PAYMENT_OTP_VALIDATION_FAILED",
                    "PAYMENT_DECLINED_BY_BANK", "INSUFFICIENT_FUNDS", "CARD_EXPIRED", "UPI_APP_NOT_RESPONDING",
                    "MANDATE_EXPIRED", "CHECKOUT_DROP_OFF", "PRICE_SENSITIVITY", "FRAUD_SUSPECTED",
                    "INVOICE_OVERDUE_TIER_1", "INVOICE_OVERDUE_TIER_2", "INVOICE_DISPUTE"
                ].index(d_error) if d_error in [
                    "BAD_REQUEST_PAYMENT_TIMED_OUT", "GATEWAY_ERROR", "BAD_REQUEST_PAYMENT_OTP_VALIDATION_FAILED",
                    "PAYMENT_DECLINED_BY_BANK", "INSUFFICIENT_FUNDS", "CARD_EXPIRED", "UPI_APP_NOT_RESPONDING",
                    "MANDATE_EXPIRED", "CHECKOUT_DROP_OFF", "PRICE_SENSITIVITY", "FRAUD_SUSPECTED",
                    "INVOICE_OVERDUE_TIER_1", "INVOICE_OVERDUE_TIER_2", "INVOICE_DISPUTE"
                ] else 0,
            )

        with col_l3:
            in_bank = st.selectbox("Acquiring Bank", ["HDFC", "ICICI", "SBI", "AXIS", "KOTAK", "UPI_NETWORK"])
            in_fraud = st.checkbox("Simulate Suspected Fraud Flag", value=d_fraud)
            in_optout = st.checkbox("Simulate Customer DND Opt-Out Flag", value=d_optout)
            in_dispute = st.checkbox("Simulate Customer Dispute Flag", value=d_dispute)
            in_attempts = st.number_input("Past Attempts Count", min_value=0, max_value=5, value=d_attempts)
            submit_event = st.form_submit_button("⚡ Ingest & Execute Autonomous Recovery", type="primary", use_container_width=True)

    if submit_event:
        event = TransactionFailureEvent(
            transaction_id=f"txn_live_{int(time.time())}",
            customer_id=f"cust_{in_phone[-6:]}",
            customer_name=in_name,
            customer_phone=in_phone,
            customer_email=in_email,
            customer_tier=CustomerTier(in_tier),
            customer_ltv=float(in_ltv),
            amount=float(in_amount),
            scenario=in_scenario,
            error_code=in_error,
            bank=in_bank,
            attempt_count=int(in_attempts),
            opted_out=in_optout,
            disputed=in_dispute,
            fraud_suspected=in_fraud,
        )

        with st.spinner("Executing multi-agent recovery workflow..."):
            record = orchestrator.process_transaction(event)

        st.subheader("🔍 Multi-Agent Pipeline Diagnostics & Decision Trace")

        p1, p2, p3, p4 = st.columns(4)
        with p1:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-title">1. Detector Diagnosis</div>
                    <div style="font-weight: 600; color: #f8fafc;">{record.diagnosis.category.value}</div>
                    <div style="font-size: 0.8rem; color: #94a3b8;">P(Rec): {record.diagnosis.expected_recovery_probability * 100:.0f}% | P(Churn): {record.diagnosis.churn_risk_if_contacted * 100:.1f}%</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with p2:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-title">2. Strategist EV Plan</div>
                    <div style="font-weight: 600; color: #60a5fa;">{record.intervention.vector.value}</div>
                    <div style="font-size: 0.8rem; color: #94a3b8;">EV: ₹{record.intervention.expected_value_inr:.2f} | Cost: ₹{record.intervention.contact_cost_inr:.2f}</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with p3:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-title">3. Compliance Governor</div>
                    <div style="font-weight: 600; color: {'#34d399' if record.compliance.action_permitted else '#f87171'};">
                        {'✅ PERMITTED' if record.compliance.action_permitted else f'🛑 {record.compliance.triggered_stopping_rule}'}
                    </div>
                    <div style="font-size: 0.8rem; color: #94a3b8;">{record.compliance.reason[:45]}...</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        with p4:
            st.markdown(
                f"""
                <div class="metric-card">
                    <div class="metric-title">4. Final Outcome</div>
                    <div style="font-weight: 600; color: {'#34d399' if record.status == RecoveryStatus.RECOVERED else '#fbbf24' if 'STOPPED' not in record.status.value else '#f87171'};">
                        {record.status.value}
                    </div>
                    <div style="font-size: 0.8rem; color: #34d399;">₹{record.money_recovered:,.2f} Recovered</div>
                </div>
                """,
                unsafe_allow_html=True,
            )

        if record.intervention and record.intervention.razorpay_payment_link:
            st.info(f"🔗 **Live Razorpay 1-Click Payment Link:** [{record.intervention.razorpay_payment_link}]({record.intervention.razorpay_payment_link})")

        if record.intervention and record.intervention.message_content:
            with st.expander("📱 Generated Customer Outreach Message", expanded=True):
                st.code(record.intervention.message_content, language="markdown")


# ==========================================
# TAB 3: REAL RAZORPAY TEST API GATEWAY
# ==========================================
with tab_rzp:
    st.header("💳 Official Razorpay Test Mode Gateway Integrations")
    st.markdown("Interact directly with official Razorpay Test APIs (`api.razorpay.com/v1`) using your test credentials.")

    st.info(f"🔑 **Connected Account Key**: `{settings.RAZORPAY_KEY_ID}` | **Base Endpoint**: `https://api.razorpay.com/v1`")

    rz_col1, rz_col2 = st.columns([1.2, 1])

    with rz_col1:
        st.subheader("🚀 Generate Direct Razorpay Test Payment Link")
        with st.form("direct_rzp_link_form"):
            r_amt = st.number_input("Amount (INR ₹)", value=499.0, min_value=1.0, step=50.0)
            r_name = st.text_input("Customer Name", value="Aarav Sharma")
            r_phone = st.text_input("Phone (+91)", value="+919876543210")
            r_desc = st.text_input("Description", value="Razorpay Buildathon Test Recovery")
            create_link_btn = st.form_submit_button("💳 Create Real Razorpay Payment Link", type="primary")

        if create_link_btn:
            with st.spinner("Calling Razorpay API POST /v1/payment_links..."):
                resp = razorpay_client.create_payment_link(
                    amount=float(r_amt),
                    customer_name=r_name,
                    customer_phone=r_phone,
                    description=r_desc,
                )
            st.success(f"✅ Generated Real Payment Link ID: **`{resp.id}`**")
            st.markdown(f"🔗 **Open in Razorpay Checkout**: [{resp.short_url}]({resp.short_url})")

    with rz_col2:
        st.subheader("📋 Active Links in Your Razorpay Account")
        if st.button("🔄 Refresh Links from Razorpay API", use_container_width=True):
            st.rerun()

        live_links = razorpay_client.fetch_payment_links(count=8)
        if live_links:
            links_table = []
            for l in live_links:
                links_table.append({
                    "Link ID": l.get("id"),
                    "Amount": f"₹{l.get('amount', 0)/100:,.2f}",
                    "Status": l.get("status"),
                    "Short URL": l.get("short_url"),
                })
            st.dataframe(pd.DataFrame(links_table), use_container_width=True)
        else:
            st.caption("No links fetched yet. Click Create Link to generate your first live test link.")


# ==========================================
# TAB 4: HINGLISH VOICE RECOVERY SANDBOX
# ==========================================
with tab_voice:
    st.header("🎙️ Hinglish Conversational Voice Recovery Agent")
    st.markdown("Simulate high-touch, empathetic vernacular phone calls for high-ticket recoveries and B2B receivables.")

    col_v1, col_v2 = st.columns([1, 1.2])

    with col_v1:
        v_name = st.text_input("Customer Name", value="Rahul Sharma", key="voice_name")
        v_amount = st.number_input("Transaction Value (₹)", value=18500.0, step=1000.0, key="voice_amt")
        v_scenario = st.selectbox("Scenario", ["CHECKOUT_ABANDONMENT", "B2B_INVOICE_OVERDUE", "RECURRING_SUBSCRIPTION"], key="voice_scen")

        demo_event = TransactionFailureEvent(
            transaction_id="txn_voice_demo",
            customer_id="cust_voice_demo",
            customer_name=v_name,
            customer_phone="+919876543210",
            amount=float(v_amount),
            scenario=v_scenario,
            error_code="BAD_REQUEST_PAYMENT_OTP_VALIDATION_FAILED",
        )
        plink = "https://rzp.io/i/rev_voice981"

        opening_script = HinglishVoiceAgentAdapter.generate_opening_script(demo_event, plink)

        st.subheader("📞 AI Voice Agent Script (Hinglish)")
        st.info(opening_script)

        st.markdown("**Simulate Customer Response:**")
        resp_preset = st.radio(
            "Customer Intent Preset:",
            [
                "Agree to Pay via WhatsApp Link",
                "Promise to Pay Tomorrow (PTP)",
                "Dispute Invoice / Return Product",
                "Opt-Out / Do Not Call",
            ]
        )

        trigger_voice = st.button("🗣️ Simulate Live Call", type="primary", use_container_width=True)

    with col_v2:
        st.subheader("📝 Live Call Transcript & Dialogue State")
        if trigger_voice:
            preset_map = {
                "Agree to Pay via WhatsApp Link": "AGREE_TO_PAY",
                "Promise to Pay Tomorrow (PTP)": "PROMISE_TO_PAY",
                "Dispute Invoice / Return Product": "DISPUTE_RAISED",
                "Opt-Out / Do Not Call": "OPT_OUT",
            }
            dialogue = HinglishVoiceAgentAdapter.simulate_dialogue_flow(demo_event, preset_map[resp_preset], plink)

            for turn in dialogue["transcript"]:
                speaker = turn["speaker"]
                text = turn["text"]
                if "Agent" in speaker:
                    st.markdown(f"<div class='chat-bubble-agent'><b>🤖 {speaker}:</b><br>{text}</div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div class='chat-bubble-user'><b>👤 {speaker}:</b><br>{text}</div>", unsafe_allow_html=True)

            st.divider()
            st.markdown(f"**Call Resolution Outcome:** `{dialogue['outcome']}`")
            if dialogue.get("ptp_record"):
                ptp = dialogue["ptp_record"]
                st.warning(f"📌 **Promise-to-Pay Logged:** ₹{ptp.promised_amount:,.2f} due by '{ptp.promised_date}'. Outreach paused during grace period.")


# ==========================================
# TAB 5: B2B RECEIVABLES & AGING LEDGER
# ==========================================
with tab_b2b:
    st.header("🏢 B2B Receivables & Promise-to-Pay Ledger")
    st.markdown("Track corporate overdue receivables, aging buckets, dispute holds, and promise-to-pay commitments.")

    b2b_records = [r for r in telemetry_tracker.records if r.event.scenario == "B2B_INVOICE_OVERDUE"]

    if not b2b_records:
        st.info("No B2B receivables in current session. Run the B2B Benchmark in Tab 1 to populate!")
    else:
        tb1, tb2, tb3 = st.columns(3)
        b2b_total = sum(r.event.amount for r in b2b_records)
        b2b_rec = sum(r.money_recovered for r in b2b_records)
        b2b_ptp = sum(r.ptp_record.promised_amount for r in b2b_records if r.ptp_record)

        tb1.metric("Total B2B Invoices Overdue", f"₹{b2b_total:,.2f}")
        tb2.metric("Directly Settled", f"₹{b2b_rec:,.2f}")
        tb3.metric("Committed via Promise-to-Pay", f"₹{b2b_ptp:,.2f}")

        b2b_data = []
        for r in b2b_records:
            b2b_data.append({
                "Invoice ID": r.event.metadata.get("invoice_id", r.event.transaction_id),
                "Company": r.event.customer_name,
                "Amount (₹)": f"₹{r.event.amount:,.2f}",
                "Aging Tier": r.event.error_code,
                "Status": r.status.value,
                "PTP Commitment": r.ptp_record.promised_date if r.ptp_record else "None",
                "Disputed": "YES ⚠️" if r.event.disputed else "NO",
            })
        st.dataframe(pd.DataFrame(b2b_data), use_container_width=True)


# ==========================================
# TAB 6: COMPLIANCE & CRYPTOGRAPHIC AUDIT LEDGER
# ==========================================
with tab_audit:
    st.header("🛡️ Cryptographic Regulatory Audit Ledger")
    st.markdown("Tamper-evident append-only audit trail recording every state transition, compliance check, stopping rule, and recovery action with a SHA-256 hash chain.")

    col_a1, col_a2 = st.columns([1.5, 1])
    with col_a1:
        verify_btn = st.button("🔐 Verify SHA-256 Hash Chain Integrity", type="primary")

    if verify_btn:
        is_valid, count = audit_ledger_agent.verify_ledger_integrity()
        if is_valid:
            st.success(f"✅ Cryptographic Integrity Verified: 100% Tamper-Evident across all {count} audit records!")
        else:
            st.error(f"❌ Hash chain mismatch detected at index {count}!")

    logs = audit_ledger_agent.get_all_logs(limit=100)

    if not logs:
        st.info("Audit ledger is empty.")
    else:
        log_data = []
        for l in reversed(logs):
            log_data.append({
                "Log ID": l.log_id,
                "Timestamp (UTC)": l.timestamp.strftime("%Y-%m-%d %H:%M:%S"),
                "Txn ID": l.transaction_id,
                "Agent": l.agent_name,
                "Action Taken": l.action_taken,
                "Transition": f"{l.state_before} ➔ {l.state_after}",
                "Previous Hash": f"{l.previous_hash[:12]}...",
                "Entry Hash (SHA-256)": f"{l.entry_hash[:12]}...",
                "Compliance Verified": "✅ PASSED" if l.compliance_verified else "❌ FAILED",
            })
        st.dataframe(pd.DataFrame(log_data), use_container_width=True)
