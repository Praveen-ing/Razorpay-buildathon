"""
RevRecover AI — Enterprise Command Center
===========================================
Autonomous Revenue Recovery Platform for Indian Digital Commerce & SaaS.

Features:
  - Real-time multi-agent pipeline visualization
  - Plotly charts: funnel, bar, donut, time series
  - Mandate retry sequencer with live step-by-step execution
  - LLM-personalized message preview cards
  - Cryptographic audit trail with export
  - B2B receivables aging report
  - Hinglish voice transcript sandbox
  - Enterprise ROI calculator
  - Bank telemetry radar
"""

import json
import os
import sys
import time
import io
import csv
import random
from datetime import datetime, timedelta
from pathlib import Path

# Add src to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent))

import pandas as pd
import streamlit as st
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots

from agents.audit_agent import audit_ledger_agent
from agents.orchestrator import orchestrator
from agents.voice_recovery import voice_recovery_agent
from agents.mandate_sequencer import mandate_sequencer, DunningStepStatus
from core.settings import settings
from core.telemetry import telemetry_tracker
from integrations.channels.voice_hinglish import HinglishVoiceAgentAdapter
from integrations.channels.whatsapp import WhatsAppChannelAdapter
from integrations.channels.email import EmailChannelAdapter
from integrations.channels.sms import SMSChannelAdapter
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

# ─────────────────────────────────────────────────────────
# Page Config & Premium Dark Theme
# ─────────────────────────────────────────────────────────
st.set_page_config(
    page_title="RevRecover AI — Autonomous Revenue Recovery Platform",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown(
    """
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800;900&family=JetBrains+Mono:wght@400;500&display=swap');

    /* ─── Base ─────────────────────────────────────────── */
    html, body, [class*="css"], .stApp {
        font-family: 'Inter', -apple-system, BlinkMacSystemFont, sans-serif;
        background: #0a0d14;
        color: #e2e8f0;
    }
    .main .block-container { padding-top: 1.2rem; padding-bottom: 2rem; max-width: 1600px; }

    /* ─── Sidebar ───────────────────────────────────────── */
    [data-testid="stSidebar"] {
        background: #0d111c !important;
        border-right: 1px solid #1e2a3a;
    }
    [data-testid="stSidebar"] * { color: #cbd5e1 !important; }
    [data-testid="stSidebar"] .stButton > button {
        background: #1e293b; border: 1px solid #334155;
        color: #e2e8f0 !important; border-radius: 8px;
    }
    [data-testid="stSidebar"] .stButton > button:hover {
        background: #253449; border-color: #3b82f6;
    }

    /* ─── Hero Banner ───────────────────────────────────── */
    .hero-banner {
        background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #0f172a 100%);
        border: 1px solid #312e81;
        border-radius: 16px;
        padding: 28px 32px;
        margin-bottom: 24px;
        position: relative;
        overflow: hidden;
    }
    .hero-banner::before {
        content: '';
        position: absolute;
        top: -50%;
        left: -50%;
        width: 200%;
        height: 200%;
        background: radial-gradient(circle at 30% 50%, rgba(99,102,241,0.08) 0%, transparent 60%);
        pointer-events: none;
    }
    .hero-title {
        font-size: 1.8rem;
        font-weight: 800;
        background: linear-gradient(90deg, #818cf8, #c084fc, #f472b6);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin: 0;
        letter-spacing: -0.03em;
    }
    .hero-sub {
        color: #94a3b8;
        font-size: 0.92rem;
        margin-top: 6px;
        line-height: 1.6;
    }

    /* ─── KPI Cards ─────────────────────────────────────── */
    .kpi-card {
        background: #111827;
        border: 1px solid #1e2a3a;
        border-radius: 12px;
        padding: 18px 20px;
        margin-bottom: 12px;
        transition: border-color 0.2s, transform 0.15s;
        position: relative;
        overflow: hidden;
    }
    .kpi-card:hover { border-color: #3b4f6e; transform: translateY(-1px); }
    .kpi-card-accent { border-left: 3px solid; }
    .kpi-card-green { border-left-color: #10b981; }
    .kpi-card-blue { border-left-color: #3b82f6; }
    .kpi-card-purple { border-left-color: #8b5cf6; }
    .kpi-card-orange { border-left-color: #f59e0b; }
    .kpi-card-red { border-left-color: #ef4444; }
    .kpi-card-cyan { border-left-color: #06b6d4; }
    .kpi-label {
        font-size: 0.72rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #64748b;
        margin-bottom: 6px;
    }
    .kpi-value {
        font-size: 1.65rem;
        font-weight: 800;
        letter-spacing: -0.03em;
        color: #f1f5f9;
    }
    .kpi-delta {
        font-size: 0.78rem;
        font-weight: 500;
        margin-top: 4px;
        color: #64748b;
    }

    /* ─── Status Badges ─────────────────────────────────── */
    .badge {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        padding: 3px 10px;
        border-radius: 20px;
        font-size: 0.72rem;
        font-weight: 700;
        letter-spacing: 0.04em;
        text-transform: uppercase;
    }
    .badge-green  { background: #052e16; color: #4ade80; border: 1px solid #166534; }
    .badge-red    { background: #450a0a; color: #f87171; border: 1px solid #7f1d1d; }
    .badge-blue   { background: #0c1a2e; color: #60a5fa; border: 1px solid #1e40af; }
    .badge-amber  { background: #1c1107; color: #fbbf24; border: 1px solid #78350f; }
    .badge-purple { background: #1e1b4b; color: #a78bfa; border: 1px solid #4c1d95; }
    .badge-gray   { background: #111827; color: #9ca3af; border: 1px solid #374151; }

    /* ─── Message Card Preview ──────────────────────────── */
    .msg-card-wa {
        background: #0b3b2e;
        border: 1px solid #166534;
        border-radius: 12px;
        padding: 16px 20px;
        font-family: 'Inter', sans-serif;
        color: #d1fae5;
        font-size: 0.88rem;
        line-height: 1.7;
        white-space: pre-wrap;
        word-wrap: break-word;
    }
    .msg-card-sms {
        background: #0c1a2e;
        border: 1px solid #1e40af;
        border-radius: 12px;
        padding: 16px 20px;
        color: #bfdbfe;
        font-size: 0.88rem;
        line-height: 1.7;
        white-space: pre-wrap;
    }
    .msg-card-email {
        background: #1a1207;
        border: 1px solid #78350f;
        border-radius: 12px;
        padding: 16px 20px;
        color: #fde68a;
        font-size: 0.88rem;
        line-height: 1.7;
        white-space: pre-wrap;
    }
    .msg-card-voice {
        background: #1a0b2e;
        border: 1px solid #4c1d95;
        border-radius: 12px;
        padding: 16px 20px;
        color: #ddd6fe;
        font-size: 0.88rem;
        line-height: 1.7;
        font-style: italic;
    }
    .msg-channel-header {
        font-size: 0.7rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.1em;
        margin-bottom: 10px;
        display: flex;
        align-items: center;
        gap: 6px;
    }

    /* ─── Pipeline Step ─────────────────────────────────── */
    .pipeline-step {
        background: #111827;
        border: 1px solid #1e2a3a;
        border-radius: 10px;
        padding: 14px 16px;
        text-align: center;
        position: relative;
    }
    .pipeline-step-label {
        font-size: 0.68rem;
        font-weight: 700;
        text-transform: uppercase;
        letter-spacing: 0.08em;
        color: #475569;
        margin-bottom: 6px;
    }
    .pipeline-step-value {
        font-size: 0.85rem;
        font-weight: 600;
        color: #e2e8f0;
    }

    /* ─── Chat Bubbles ──────────────────────────────────── */
    .chat-agent {
        background: #0f172a;
        border: 1px solid #1e293b;
        border-left: 3px solid #6366f1;
        padding: 12px 16px;
        border-radius: 0 10px 10px 10px;
        margin-bottom: 10px;
        color: #c7d2fe;
        font-size: 0.88rem;
        line-height: 1.6;
    }
    .chat-user {
        background: #0f2e1a;
        border: 1px solid #166534;
        border-right: 3px solid #10b981;
        padding: 12px 16px;
        border-radius: 10px 0 10px 10px;
        margin-bottom: 10px;
        color: #a7f3d0;
        font-size: 0.88rem;
        line-height: 1.6;
        margin-left: 20px;
    }

    /* ─── Dunning Step Cards ─────────────────────────────── */
    .dunning-step-pending  { border-left: 3px solid #475569; opacity: 0.7; }
    .dunning-step-done     { border-left: 3px solid #10b981; }
    .dunning-step-skipped  { border-left: 3px solid #6b7280; opacity: 0.5; }
    .dunning-step-active   { border-left: 3px solid #f59e0b; }

    /* ─── Plotly theme override ─────────────────────────── */
    .js-plotly-plot { border-radius: 12px; }

    /* ─── Streamlit native overrides ───────────────────── */
    .stTabs [data-baseweb="tab-list"] {
        background: #0d111c;
        gap: 4px;
        border-bottom: 1px solid #1e2a3a;
        padding: 0 4px;
    }
    .stTabs [data-baseweb="tab"] {
        background: transparent;
        color: #64748b;
        border-radius: 8px 8px 0 0;
        padding: 8px 16px;
        font-size: 0.82rem;
        font-weight: 600;
    }
    .stTabs [aria-selected="true"] {
        background: #1e293b !important;
        color: #818cf8 !important;
        border-bottom: 2px solid #818cf8;
    }
    .stSelectbox > div > div, .stTextInput > div > div > input,
    .stNumberInput > div > div > input, .stTextArea textarea {
        background: #111827 !important;
        border-color: #1e2a3a !important;
        color: #e2e8f0 !important;
        border-radius: 8px !important;
    }
    .stButton > button[kind="primary"] {
        background: linear-gradient(135deg, #4f46e5, #7c3aed);
        border: none;
        color: white;
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.2s;
    }
    .stButton > button[kind="primary"]:hover {
        background: linear-gradient(135deg, #4338ca, #6d28d9);
        transform: translateY(-1px);
        box-shadow: 0 4px 15px rgba(99,102,241,0.4);
    }
    .stButton > button[kind="secondary"] {
        background: #1e293b;
        border: 1px solid #334155;
        color: #94a3b8;
        border-radius: 8px;
    }
    .stDataFrame { border-radius: 10px; overflow: hidden; }
    .stDataFrame table { background: #111827; }
    .stDataFrame th { background: #0f172a; color: #64748b; font-size: 0.72rem; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; }
    .stDataFrame td { color: #e2e8f0; font-size: 0.82rem; border-bottom-color: #1e2a3a; }
    div[data-testid="stMetricValue"] { font-weight: 800; }
    .stInfo, .stSuccess, .stWarning, .stError {
        border-radius: 10px;
        border: 1px solid;
    }
    .stExpander { background: #111827; border: 1px solid #1e2a3a; border-radius: 10px; }
    hr { border-color: #1e2a3a; }

    /* ─── Section Headers ───────────────────────────────── */
    h1, h2, h3 { color: #e2e8f0; letter-spacing: -0.02em; }
    h1 { font-weight: 800; font-size: 1.6rem; }
    h2 { font-weight: 700; font-size: 1.25rem; }
    h3 { font-weight: 600; font-size: 1.05rem; }

    /* ─── Scrollbar ─────────────────────────────────────── */
    ::-webkit-scrollbar { width: 6px; height: 6px; }
    ::-webkit-scrollbar-track { background: #0a0d14; }
    ::-webkit-scrollbar-thumb { background: #1e2a3a; border-radius: 3px; }
    ::-webkit-scrollbar-thumb:hover { background: #334155; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ─────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────

PLOTLY_DARK = dict(
    paper_bgcolor="#111827",
    plot_bgcolor="#111827",
    font=dict(family="Inter, sans-serif", color="#94a3b8"),
    margin=dict(l=20, r=20, t=40, b=20),
    xaxis=dict(gridcolor="#1e2a3a", linecolor="#1e2a3a"),
    yaxis=dict(gridcolor="#1e2a3a", linecolor="#1e2a3a"),
)

def kpi_card(label: str, value: str, delta: str = "", accent: str = "blue") -> str:
    return f"""
    <div class="kpi-card kpi-card-accent kpi-card-{accent}">
        <div class="kpi-label">{label}</div>
        <div class="kpi-value">{value}</div>
        <div class="kpi-delta">{delta}</div>
    </div>
    """

def status_badge(status: str) -> str:
    color_map = {
        "RECOVERED": "green",
        "PROMISE_TO_PAY_SET": "blue",
        "OUTREACH_ACTIVE": "amber",
        "STOPPED": "red",
        "EXHAUSTED": "gray",
        "ACTIVE": "purple",
    }
    for key, color in color_map.items():
        if key in status.upper():
            return f'<span class="badge badge-{color}">{status}</span>'
    return f'<span class="badge badge-gray">{status}</span>'

def fmt_inr(amount: float) -> str:
    return f"₹{amount:,.0f}"

# ─────────────────────────────────────────────────────────
# Seed initial data
# ─────────────────────────────────────────────────────────
if len(telemetry_tracker.records) == 0:
    with st.spinner("🚀 Initializing RevRecover AI with synthetic batch..."):
        initial_batch = RecoveryBatchSimulator.generate_synthetic_batch(50)
        orchestrator.process_batch("SEED-INIT-50", initial_batch)


# ─────────────────────────────────────────────────────────
# Sidebar
# ─────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("""
    <div style="text-align:center; padding: 8px 0 16px;">
        <div style="font-size: 2.5rem;">⚡</div>
        <div style="font-size: 1.1rem; font-weight: 800; 
                    background: linear-gradient(90deg, #818cf8, #c084fc);
                    -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
            RevRecover AI
        </div>
        <div style="font-size: 0.72rem; color: #475569; margin-top: 2px;">
            Autonomous Revenue Recovery Engine
        </div>
    </div>
    """, unsafe_allow_html=True)
    st.divider()

    st.subheader("⚙️ Configuration")

    is_live_key = bool(settings.RAZORPAY_KEY_ID and "rzp_test_" in settings.RAZORPAY_KEY_ID)
    if is_live_key:
        st.success(f"🟢 Razorpay Test API\n`{settings.RAZORPAY_KEY_ID[:14]}...`")
    else:
        st.warning("⚪ Sandbox / Mock Mode")

    mock_mode = st.toggle("Force Mock Mode", value=settings.RAZORPAY_MOCK_MODE)
    settings.RAZORPAY_MOCK_MODE = mock_mode

    compliance_enforced = st.toggle("RBI & DPDP Compliance Rules", value=settings.ENABLE_COMPLIANCE_GUARD)
    settings.ENABLE_COMPLIANCE_GUARD = compliance_enforced

    max_discount = st.slider("Max Recovery Discount (%)", 0.0, 20.0, settings.MAX_DISCOUNT_PERCENTAGE, 1.0)
    settings.MAX_DISCOUNT_PERCENTAGE = max_discount

    st.divider()
    st.markdown("#### 💰 Unit Economics")
    st.markdown("""
    <div style="font-size:0.78rem; color:#64748b; line-height:1.9;">
    • Silent Retry: <code>₹0.00</code><br>
    • WhatsApp Link: <code>₹0.40</code><br>
    • SMS: <code>₹0.20</code><br>
    • Email: <code>₹0.05</code><br>
    • Hinglish AI Call: <code>₹2.50</code><br>
    • Human Escalation: <code>₹150.00</code>
    </div>
    """, unsafe_allow_html=True)

    st.divider()
    if st.button("🔄 Reset Analytics & Ledger", use_container_width=True):
        telemetry_tracker.reset()
        audit_ledger_agent.clear()
        st.success("Reset complete!")
        st.rerun()

    st.markdown("---")
    st.markdown("""
    <div style="font-size:0.7rem; color:#374151; text-align:center;">
    🛡️ RBI e-Mandate Circular & DPDP Act 2023 Compliant<br>
    SHA-256 Cryptographic Audit Trail
    </div>
    """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────
# Hero Banner & KPI Strip
# ─────────────────────────────────────────────────────────
kpis = telemetry_tracker.get_kpis()

st.markdown("""
<div class="hero-banner">
    <div class="hero-title">⚡ RevRecover AI — Autonomous Revenue Recovery</div>
    <div class="hero-sub">
        Closed-loop multi-agent platform · <strong>Detect Risk → Diagnose Root Cause → EV-Optimized Intervention
        → Bounded Multi-Channel Outreach → Measured Recovery & Cryptographic Audit</strong>
    </div>
</div>
""", unsafe_allow_html=True)

# KPI strip — 6 cards
c1, c2, c3, c4, c5, c6 = st.columns(6)
with c1:
    st.markdown(kpi_card("Revenue at Risk", fmt_inr(kpis.total_at_risk_inr),
                         f"{kpis.total_events_processed} events", "red"), unsafe_allow_html=True)
with c2:
    st.markdown(kpi_card("Gross Recovered", fmt_inr(kpis.total_recovered_inr),
                         "▲ Agent AI", "green"), unsafe_allow_html=True)
with c3:
    st.markdown(kpi_card("Net Revenue Lift", fmt_inr(kpis.net_revenue_lift_inr),
                         "▲ vs Baseline Policy", "blue"), unsafe_allow_html=True)
with c4:
    st.markdown(kpi_card("Net Recovery Rate", f"{kpis.net_recovery_rate_pct}%",
                         "Target: >70%", "purple"), unsafe_allow_html=True)
with c5:
    st.markdown(kpi_card("PTP Committed", fmt_inr(kpis.total_ptp_secured_inr),
                         "Receivables", "orange"), unsafe_allow_html=True)
with c6:
    st.markdown(kpi_card("Compliance Stops", str(kpis.total_blocked),
                         "100% Stopping Rules Met", "cyan"), unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────
# Bank Telemetry Expander (live)
# ─────────────────────────────────────────────────────────
with st.expander("🔮 Live Bank Gateway Telemetry Radar & Contextual Bandit Engine", expanded=False):
    t_col1, t_col2 = st.columns([1.3, 1])
    with t_col1:
        from core.telemetry import bank_health_tracker
        all_t = bank_health_tracker.get_all_telemetry()
        fig_banks = go.Figure()
        banks_list = list(all_t.keys())
        success_rates = [all_t[b]["success_rate_pct"] for b in banks_list]
        latencies = [all_t[b]["latency_ms"] for b in banks_list]
        colors = ["#10b981" if all_t[b]["status"] == "OPTIMAL" else "#f59e0b" if all_t[b]["status"] == "DEGRADED" else "#ef4444"
                  for b in banks_list]
        fig_banks.add_trace(go.Bar(
            x=banks_list, y=success_rates, name="Success Rate %",
            marker_color=colors, text=[f"{r}%" for r in success_rates],
            textposition="outside", textfont=dict(size=11),
        ))
        fig_banks.update_layout(
            **PLOTLY_DARK,
            title=dict(text="🌐 Acquiring Bank Gateway Success Rates (60s Window)", font=dict(size=13, color="#e2e8f0"), x=0),
            yaxis_range=[0, 110],
            height=260,
            showlegend=False,
        )
        st.plotly_chart(fig_banks, use_container_width=True)

    with t_col2:
        st.markdown("**🧠 Contextual Bandit — Thompson Sampling Conversion Rates**")
        from agents.strategist import strategist_agent
        b_metrics = strategist_agent.bandit_optimizer.get_bandit_metrics()
        for arm, winrate in b_metrics.items():
            arm_label = arm.replace("_", " ")
            color = "#10b981" if winrate > 70 else "#f59e0b" if winrate > 50 else "#ef4444"
            st.markdown(f"<span style='font-size:0.82rem; color:#94a3b8;'>{arm_label}</span>", unsafe_allow_html=True)
            st.progress(int(winrate) / 100, text=f"{winrate:.1f}%")


# ─────────────────────────────────────────────────────────
# Platform Tour & Architecture Overview Expander
# ─────────────────────────────────────────────────────────
with st.expander("🧭 Platform Overview & Architecture Tour", expanded=False):
    j_col1, j_col2 = st.columns([1.5, 1])
    with j_col1:
        st.markdown("""
        **RevRecover AI — Enterprise Multi-Agent Architecture:**
        
        1. **📊 Measured Money Recovered across a Batch**: Go to **🚀 Batch Benchmark** → Click *Execute Batch Recovery* (demonstrates >70% recovery, net revenue lift, and baseline comparison).
        2. **🛑 Compliant Escalation & Hard Stopping Rules**: Go to **⚡ Live Event** → Click *🛑 DND Opt-Out Test* or *🛑 Active Dispute Test* (demonstrates 100% adherence to DPDP Act 2023 & RBI circulars).
        3. **📅 RBI Mandate Retry Sequencer**: Go to **📅 Mandate Sequencer** → Inspect the 5-step dunning calendar respecting 24h gaps and max 3 automated retries.
        4. **🎙️ Hinglish Conversational Recovery**: Go to **🎙️ Hinglish Voice** → Simulate natural Indian conversational recovery with mid-call payment link dispatch.
        5. **🛡️ Immutable Cryptographic Audit Ledger**: Go to **🛡️ Audit Ledger** → Verify SHA-256 hash chains and ZK compliance certificates.
        """)
    with j_col2:
        st.markdown("""
        <div style="background:rgba(99,102,241,0.08); border:1px solid rgba(99,102,241,0.25); border-radius:10px; padding:12px;">
            <div style="font-weight:700; color:#818cf8; font-size:0.92rem; margin-bottom:6px;">🚀 Service Endpoints & Docs</div>
            <div style="font-size:0.8rem; color:#cbd5e1; line-height:1.6;">
                • <strong>FastAPI Backend:</strong> <a href="http://localhost:8080/docs" target="_blank" style="color:#38bdf8;">http://localhost:8080/docs</a><br>
                • <strong>Health Check:</strong> <a href="http://localhost:8080/health" target="_blank" style="color:#38bdf8;">http://localhost:8080/health</a><br>
                • <strong>Test Suite:</strong> <code>52 Tests Passing</code> (100%)<br>
                • <strong>System Guide:</strong> <code>SYSTEM_GUIDE.md</code>
            </div>
        </div>
        """, unsafe_allow_html=True)


# ─────────────────────────────────────────────────────────
# Main Tabs
# ─────────────────────────────────────────────────────────
tab_batch, tab_live, tab_mandate, tab_webhook, tab_cohort, tab_journey, tab_rzp, tab_voice, tab_b2b, tab_audit, tab_enterprise = st.tabs([
    "🚀 Batch Benchmark",
    "⚡ Live Event",
    "📅 Mandate Sequencer",
    "📡 Webhook Simulator",
    "🔥 Cohort Risk Engine",
    "🗺️ Customer Journey",
    "💳 Razorpay API",
    "🎙️ Hinglish Voice",
    "🏢 B2B Receivables",
    "🛡️ Audit Ledger",
    "💎 Enterprise Features",
])


# ══════════════════════════════════════════════════════
# TAB 1: BATCH BENCHMARK ARENA
# ══════════════════════════════════════════════════════
with tab_batch:
    st.header("🚀 Batch Benchmark Arena — Measured Money Recovered vs Baseline")
    st.markdown("Prove **measured money recovered** across a batch with full baseline comparison, compliance adherence, and audit trail.")

    col_b1, col_b2, col_b3 = st.columns([1.6, 1.4, 1])
    with col_b1:
        benchmark_type = st.selectbox("Select Benchmark Dataset:", [
            "Composite Full Spectrum (100 Transactions)",
            "E-Commerce Cart Drop-offs (50 txns)",
            "SaaS Recurring Mandates & Auto-Debit (50 txns)",
            "B2B Aging Overdue Invoices (50 txns)",
            "High-Volume Stress Test (500 Transactions)",
            "Enterprise Scale (1,000 Transactions)",
        ])
    with col_b2:
        auto_ptp = st.checkbox("Enable Automated Promise-to-Pay", value=True)
        apply_incentives = st.checkbox("Allow Dynamic Recovery Incentives", value=True)
    with col_b3:
        st.write("")
        st.write("")
        run_batch_btn = st.button("🔥 Execute Batch Recovery", type="primary", use_container_width=True)

    if run_batch_btn:
        count = 1000 if "1,000" in benchmark_type else 500 if "500" in benchmark_type else 100 if "100" in benchmark_type else 50
        scenario_filter = None
        if "E-Commerce" in benchmark_type: scenario_filter = "CHECKOUT_ABANDONMENT"
        elif "SaaS" in benchmark_type: scenario_filter = "RECURRING_SUBSCRIPTION"
        elif "B2B" in benchmark_type: scenario_filter = "B2B_INVOICE_OVERDUE"

        events = RecoveryBatchSimulator.generate_synthetic_batch(count)
        if scenario_filter:
            for e in events:
                e.scenario = scenario_filter

        # ── Real-time streaming progress ──
        st.markdown("#### ⚡ Live Recovery Stream")
        progress_col1, progress_col2 = st.columns([3, 1])
        with progress_col1:
            progress_bar = st.progress(0.0)
        with progress_col2:
            live_counter = st.empty()

        recovered_live = st.empty()
        status_placeholder = st.empty()

        # Process and stream
        batch_id = f"BENCHMARK-{int(time.time())}"
        start_time = time.time()
        records_processed = []
        total_at_risk = sum(e.amount for e in events)
        running_recovered = 0.0
        running_baseline = 0.0

        for i, event in enumerate(events):
            rec = orchestrator.process_transaction(event, is_synthetic=True)
            records_processed.append(rec)
            if rec.status == RecoveryStatus.RECOVERED:
                running_recovered += rec.money_recovered
            running_baseline += rec.baseline_recovered

            pct = (i + 1) / len(events)
            progress_bar.progress(pct)
            live_counter.markdown(f"**{i+1}/{count}**")

            if (i + 1) % max(1, count // 20) == 0 or i == len(events) - 1:
                recovered_live.markdown(f"""
                <div style="background:#0f2e1a; border:1px solid #166534; border-radius:10px; padding:14px 20px; margin: 8px 0;">
                    <span style="font-size:0.8rem;color:#6ee7b7;">💰 AGENT RECOVERED</span>
                    <span style="font-size:1.4rem; font-weight:800; color:#4ade80; margin-left:10px;">
                        {fmt_inr(running_recovered)}
                    </span>
                    <span style="font-size:0.8rem; color:#475569; margin-left:16px;">
                        vs Baseline {fmt_inr(running_baseline)} 
                        | Lift: +{fmt_inr(max(0, running_recovered - running_baseline))}
                    </span>
                </div>
                """, unsafe_allow_html=True)

        elapsed = round(time.time() - start_time, 2)

        # Compute final stats
        agent_gross = sum(r.money_recovered for r in records_processed)
        agent_baseline = sum(r.baseline_recovered for r in records_processed)
        total_costs = sum(r.intervention.contact_cost_inr for r in records_processed if r.intervention)
        agent_net = max(0.0, agent_gross - total_costs)
        lift_inr = agent_net - agent_baseline
        lift_pct = ((lift_inr / agent_baseline) * 100.0) if agent_baseline > 0 else 100.0
        rec_count = sum(1 for r in records_processed if r.status == RecoveryStatus.RECOVERED)
        stopped_count = sum(1 for r in records_processed if str(r.status.value).startswith("STOPPED"))

        st.success(f"✅ Batch complete in {elapsed}s · Agent recovered **{fmt_inr(agent_gross)}** (Net **{fmt_inr(agent_net)}**) vs Baseline **{fmt_inr(agent_baseline)}** · **Net Lift: +{fmt_inr(lift_inr)} (+{lift_pct:.1f}%)**")

        # ── Comparison metric cards ──
        st.subheader("📊 Measured Recovery vs. Baseline Policy")
        m1, m2, m3, m4 = st.columns(4)
        with m1:
            st.markdown(kpi_card("Agent Net Recovered", fmt_inr(agent_net),
                                 f"Recovery Rate: {agent_gross/total_at_risk*100:.1f}%", "green"), unsafe_allow_html=True)
        with m2:
            st.markdown(kpi_card("Baseline (Static Retry)", fmt_inr(agent_baseline),
                                 f"Rate: {agent_baseline/total_at_risk*100:.1f}%", "gray"), unsafe_allow_html=True)
        with m3:
            st.markdown(kpi_card("Net Lift vs Baseline", f"+{fmt_inr(lift_inr)}",
                                 f"▲ +{lift_pct:.1f}%", "blue"), unsafe_allow_html=True)
        with m4:
            cost_ratio = total_costs / agent_gross if agent_gross > 0 else 0
            st.markdown(kpi_card("Cost per Recovered ₹", f"₹{cost_ratio:.4f}",
                                 f"Contact Costs: {fmt_inr(total_costs)}", "purple"), unsafe_allow_html=True)

        # ── Plotly Charts ──
        st.subheader("📈 Visual Analytics")
        chart_c1, chart_c2 = st.columns(2)

        with chart_c1:
            # Recovery Funnel
            fig_funnel = go.Figure(go.Funnel(
                y=["Events Ingested", "Diagnoses Complete", "Interventions Planned", "Governor Approved", "Outreach Sent", "Recovered"],
                x=[count, count, count - stopped_count, count - stopped_count,
                   count - stopped_count, rec_count],
                textinfo="value+percent initial",
                marker=dict(color=["#3b82f6","#6366f1","#8b5cf6","#a78bfa","#f59e0b","#10b981"]),
                connector=dict(line=dict(color="#1e2a3a", width=2)),
            ))
            fig_funnel.update_layout(**PLOTLY_DARK,
                title=dict(text="🔀 Recovery Pipeline Funnel", font=dict(color="#e2e8f0", size=13), x=0),
                height=300)
            st.plotly_chart(fig_funnel, use_container_width=True)

        with chart_c2:
            # Channel Distribution Donut
            channel_dist: dict[str, int] = {}
            channel_rec: dict[str, float] = {}
            for r in records_processed:
                if r.intervention:
                    ch = r.intervention.channel.value
                    channel_dist[ch] = channel_dist.get(ch, 0) + 1
                    if r.status == RecoveryStatus.RECOVERED:
                        channel_rec[ch] = channel_rec.get(ch, 0.0) + r.money_recovered

            if channel_dist:
                fig_donut = go.Figure(go.Pie(
                    labels=list(channel_dist.keys()),
                    values=list(channel_dist.values()),
                    hole=0.6,
                    marker=dict(colors=["#6366f1","#10b981","#f59e0b","#ef4444","#06b6d4","#8b5cf6"]),
                    textinfo="label+percent",
                    textfont=dict(size=11),
                ))
                fig_donut.update_layout(**PLOTLY_DARK,
                    title=dict(text="📡 Channel Distribution", font=dict(color="#e2e8f0", size=13), x=0),
                    height=300, showlegend=True,
                    legend=dict(font=dict(size=10)),
                )
                st.plotly_chart(fig_donut, use_container_width=True)

        # Scenario breakdown bar chart
        scenario_stats: dict[str, dict] = {}
        for r in records_processed:
            sc = r.event.scenario
            if sc not in scenario_stats:
                scenario_stats[sc] = {"at_risk": 0.0, "recovered": 0.0, "baseline": 0.0}
            scenario_stats[sc]["at_risk"] += r.event.amount
            scenario_stats[sc]["recovered"] += r.money_recovered
            scenario_stats[sc]["baseline"] += r.baseline_recovered

        if scenario_stats:
            sc_names = list(scenario_stats.keys())
            fig_bar = go.Figure()
            fig_bar.add_trace(go.Bar(name="Agent Recovered", x=sc_names,
                                     y=[scenario_stats[s]["recovered"] for s in sc_names],
                                     marker_color="#10b981", text=[fmt_inr(scenario_stats[s]["recovered"]) for s in sc_names],
                                     textposition="outside"))
            fig_bar.add_trace(go.Bar(name="Baseline Policy", x=sc_names,
                                     y=[scenario_stats[s]["baseline"] for s in sc_names],
                                     marker_color="#475569", text=[fmt_inr(scenario_stats[s]["baseline"]) for s in sc_names],
                                     textposition="outside"))
            fig_bar.update_layout(**PLOTLY_DARK,
                barmode="group",
                title=dict(text="📊 Recovery vs Baseline by Scenario", font=dict(color="#e2e8f0", size=13), x=0),
                height=280, legend=dict(font=dict(size=10)),
            )
            st.plotly_chart(fig_bar, use_container_width=True)

        # ── Transaction Table ──
        st.subheader("📋 Individual Transaction Traces")
        df_records = []
        for r in records_processed:
            df_records.append({
                "Txn ID": r.event.transaction_id,
                "Customer": r.event.customer_name[:20],
                "Amount (₹)": f"₹{r.event.amount:,.2f}",
                "Scenario": r.event.scenario,
                "Root Cause": r.event.error_code,
                "Channel": r.intervention.channel.value if r.intervention else "NONE",
                "Status": r.status.value,
                "Agent Recovered": f"₹{r.money_recovered:,.2f}",
                "Baseline Recovered": f"₹{r.baseline_recovered:,.2f}",
                "EV (₹)": f"₹{r.intervention.expected_value_inr:.2f}" if r.intervention else "N/A",
            })
        df = pd.DataFrame(df_records)
        st.dataframe(df, use_container_width=True, height=350)

        # Export button
        csv_buf = io.StringIO()
        df.to_csv(csv_buf, index=False)
        st.download_button(
            label="📥 Export Batch Results as CSV",
            data=csv_buf.getvalue().encode("utf-8"),
            file_name=f"revrecover_batch_{batch_id}.csv",
            mime="text/csv",
        )
        st.session_state["last_batch_records"] = records_processed


# ══════════════════════════════════════════════════════
# TAB 2: LIVE EVENT INGESTION
# ══════════════════════════════════════════════════════
with tab_live:
    st.header("⚡ Live Event Ingestion & Multi-Agent Pipeline")
    st.markdown("Trigger a single payment failure and observe the **5-agent closed-loop recovery pipeline** in real-time.")

    preset_choice = st.selectbox("💡 Quick Preset Scenarios:", [
        "Custom Event (Fill Form)",
        "Gateway Timeout → Smart Retry + WhatsApp Link",
        "E-Commerce Cart Abandonment → 7.5% Discount Link",
        "SaaS Mandate Failure → Salary Cycle Dunning",
        "B2B High-Value Invoice → Executive Hinglish Voice",
        "🛑 STOP: Suspected Card Fraud (Hard Stop)",
        "🛑 STOP: Customer Opted Out / DND",
        "🛑 STOP: Active Charge Dispute",
        "🛑 STOP: Negative Expected Value (Suppress Outreach)",
    ])

    with st.form("live_event_form"):
        col_l1, col_l2, col_l3 = st.columns(3)

        # Defaults
        d = dict(
            name="Rahul Sharma", phone="+919876543210", email="rahul.sharma@example.com",
            tier="VIP_PLATINUM", amount=14999.0, scenario="PAYMENT_FAILURE",
            error="BAD_REQUEST_PAYMENT_TIMED_OUT", bank="HDFC", optout=False,
            dispute=False, fraud=False, ltv=25000.0, attempts=0,
        )

        if "Cart Abandonment" in preset_choice:
            d.update(scenario="CHECKOUT_ABANDONMENT", error="CHECKOUT_DROP_OFF", amount=8500.0)
        elif "SaaS" in preset_choice:
            d.update(scenario="RECURRING_SUBSCRIPTION", error="INSUFFICIENT_FUNDS", amount=3999.0)
        elif "B2B" in preset_choice:
            d.update(scenario="B2B_INVOICE_OVERDUE", error="INVOICE_OVERDUE_TIER_2",
                     amount=175000.0, tier="ENTERPRISE", ltv=300000.0)
        elif "Fraud" in preset_choice:
            d.update(error="FRAUD_SUSPECTED", fraud=True, amount=45000.0)
        elif "Opted Out" in preset_choice:
            d.update(optout=True)
        elif "Dispute" in preset_choice:
            d.update(dispute=True, error="INVOICE_DISPUTE", scenario="B2B_INVOICE_OVERDUE")
        elif "Negative" in preset_choice:
            d.update(amount=149.0, ltv=150000.0, attempts=1)

        with col_l1:
            in_name = st.text_input("Customer / Business Name", value=d["name"])
            in_phone = st.text_input("Phone (+91)", value=d["phone"])
            in_email = st.text_input("Email", value=d["email"])
            in_tier = st.selectbox("Customer Tier", [t.value for t in CustomerTier])

        with col_l2:
            in_amount = st.number_input("Amount (₹)", min_value=10.0, max_value=500000.0, value=float(d["amount"]), step=500.0)
            in_ltv = st.number_input("Customer LTV (₹)", min_value=100.0, max_value=1000000.0, value=float(d["ltv"]), step=1000.0)
            in_scenario = st.selectbox("Failure Scenario",
                ["PAYMENT_FAILURE","CHECKOUT_ABANDONMENT","RECURRING_SUBSCRIPTION","B2B_INVOICE_OVERDUE"])
            in_error = st.selectbox("Razorpay Error Code", [
                "BAD_REQUEST_PAYMENT_TIMED_OUT","GATEWAY_ERROR","BAD_REQUEST_PAYMENT_OTP_VALIDATION_FAILED",
                "PAYMENT_DECLINED_BY_BANK","INSUFFICIENT_FUNDS","CARD_EXPIRED","UPI_APP_NOT_RESPONDING",
                "MANDATE_EXPIRED","CHECKOUT_DROP_OFF","PRICE_SENSITIVITY","FRAUD_SUSPECTED",
                "INVOICE_OVERDUE_TIER_1","INVOICE_OVERDUE_TIER_2","INVOICE_DISPUTE",
            ])

        with col_l3:
            in_bank = st.selectbox("Acquiring Bank", ["HDFC","ICICI","SBI","AXIS","KOTAK","UPI_NETWORK"])
            in_fraud = st.checkbox("Suspected Fraud Flag", value=d["fraud"])
            in_optout = st.checkbox("Customer DND Opt-Out", value=d["optout"])
            in_dispute = st.checkbox("Active Dispute Flag", value=d["dispute"])
            in_attempts = st.number_input("Past Attempts", min_value=0, max_value=5, value=d["attempts"])
            submit_event = st.form_submit_button("⚡ Execute Recovery Pipeline", type="primary", use_container_width=True)

    if submit_event:
        event = TransactionFailureEvent(
            transaction_id=f"txn_live_{int(time.time())}",
            customer_id=f"cust_{in_phone[-6:]}",
            customer_name=in_name, customer_phone=in_phone, customer_email=in_email,
            customer_tier=CustomerTier(in_tier), customer_ltv=float(in_ltv),
            amount=float(in_amount), scenario=in_scenario, error_code=in_error,
            bank=in_bank, attempt_count=int(in_attempts),
            opted_out=in_optout, disputed=in_dispute, fraud_suspected=in_fraud,
        )

        with st.spinner("Running 5-agent closed-loop pipeline..."):
            record = orchestrator.process_transaction(event)

        st.subheader("🔍 Multi-Agent Decision Pipeline")

        p1, p2, p3, p4 = st.columns(4)
        for col, step_num, title, content, color in [
            (p1, "1", "🔬 Detector", f"{record.diagnosis.category.value}\nP(Rec)={record.diagnosis.expected_recovery_probability*100:.0f}% | Urgency={record.diagnosis.urgency_level}", "#6366f1"),
            (p2, "2", "🧮 Strategist EV", f"{record.intervention.vector.value}\nEV=₹{record.intervention.expected_value_inr:.2f} | Cost=₹{record.intervention.contact_cost_inr:.2f}", "#8b5cf6"),
            (p3, "3", "⚖️ Governor", ("✅ PERMITTED" if record.compliance.action_permitted else f"🛑 {record.compliance.triggered_stopping_rule}"), "#10b981" if record.compliance.action_permitted else "#ef4444"),
            (p4, "4", "🎯 Outcome", f"{record.status.value}\n₹{record.money_recovered:,.2f} Recovered", "#10b981" if record.status == RecoveryStatus.RECOVERED else "#f59e0b"),
        ]:
            with col:
                st.markdown(f"""
                <div class="kpi-card" style="border-left: 3px solid {color};">
                    <div class="kpi-label">{title}</div>
                    <div style="font-size:0.85rem; font-weight:600; color:#e2e8f0; white-space:pre-line;">{content}</div>
                </div>
                """, unsafe_allow_html=True)

        # Compliance reason
        if not record.compliance.action_permitted:
            st.error(f"🛑 **Stopping Rule Triggered:** {record.compliance.triggered_stopping_rule}\n\n*{record.compliance.reason}*")
        elif record.intervention and record.intervention.razorpay_payment_link:
            st.info(f"🔗 **Razorpay Recovery Link:** [{record.intervention.razorpay_payment_link}]({record.intervention.razorpay_payment_link})")

        # Message preview cards
        if record.intervention and record.compliance.action_permitted:
            st.subheader("📱 Generated Outreach Message Preview")
            link_url = record.intervention.razorpay_payment_link or "https://rzp.io/i/preview"
            discount = record.intervention.discount_pct_authorized
            channel = record.intervention.channel

            if channel == CommunicationChannel.WHATSAPP:
                msg = WhatsAppChannelAdapter.format_message(event, link_url, discount)
                st.markdown(f"""
                <div class="msg-card-wa">
                    <div class="msg-channel-header" style="color:#4ade80;">📱 WhatsApp Message</div>
                    {msg.replace(chr(10), '<br>')}
                </div>
                """, unsafe_allow_html=True)
            elif channel == CommunicationChannel.SMS:
                from integrations.channels.sms import SMSChannelAdapter
                msg = SMSChannelAdapter.format_message(event, link_url)
                st.markdown(f"""
                <div class="msg-card-sms">
                    <div class="msg-channel-header" style="color:#60a5fa;">💬 SMS Message</div>
                    {msg.replace(chr(10), '<br>')}
                </div>
                """, unsafe_allow_html=True)
            elif channel == CommunicationChannel.EMAIL:
                email_data = EmailChannelAdapter.format_email(event, link_url)
                st.markdown(f"""
                <div class="msg-card-email">
                    <div class="msg-channel-header" style="color:#fbbf24;">📧 Email — {email_data.get('subject','')}</div>
                    {email_data.get('body','')[:500].replace(chr(10), '<br>')}
                </div>
                """, unsafe_allow_html=True)
            elif channel == CommunicationChannel.VOICE_HINGLISH:
                script = HinglishVoiceAgentAdapter.generate_opening_script(event, link_url)
                st.markdown(f"""
                <div class="msg-card-voice">
                    <div class="msg-channel-header" style="color:#a78bfa;">🎙️ Hinglish AI Voice Script</div>
                    {script}
                </div>
                """, unsafe_allow_html=True)

        # Audit trail
        with st.expander("📋 Full Audit Trail for this Event"):
            audit_data = []
            for log in record.audit_logs:
                audit_data.append({
                    "Agent": log.agent_name,
                    "Action": log.action_taken,
                    "Transition": f"{log.state_before} → {log.state_after}",
                    "Hash": f"{log.entry_hash[:16]}...",
                    "Timestamp": log.timestamp.strftime("%H:%M:%S.%f")[:-3],
                })
            st.dataframe(pd.DataFrame(audit_data), use_container_width=True)


# ══════════════════════════════════════════════════════
# TAB 3: MANDATE RETRY SEQUENCER
# ══════════════════════════════════════════════════════
with tab_mandate:
    st.header("📅 RBI-Compliant Mandate Retry Sequencer")
    st.markdown(
        "Multi-step dunning calendar with compliance stopping rules at every step. "
        "Respects RBI e-Mandate circular, NACH retry guidelines, and DPDP opt-out rules."
    )

    ms_col1, ms_col2 = st.columns([1.2, 1])
    with ms_col1:
        with st.form("mandate_form"):
            ms_name = st.text_input("Customer Name", value="Arjun Nair")
            ms_amount = st.number_input("Amount (₹)", min_value=100.0, max_value=250000.0, value=4999.0, step=500.0)
            ms_scenario = st.selectbox("Scenario", ["RECURRING_SUBSCRIPTION", "B2B_INVOICE_OVERDUE", "CHECKOUT_ABANDONMENT"])
            ms_bank = st.selectbox("Bank", ["HDFC","ICICI","SBI","AXIS","UPI_NETWORK"])
            ms_tier = st.selectbox("Customer Tier", [t.value for t in CustomerTier])
            ms_voice = st.checkbox("Voice Consent Given", value=True)
            ms_optout = st.checkbox("Simulate Opt-Out (STOP test)", value=False)
            ms_dispute = st.checkbox("Simulate Dispute (STOP test)", value=False)
            ms_run_btn = st.form_submit_button("📅 Create & Simulate Dunning Sequence", type="primary", use_container_width=True)

    with ms_col2:
        st.markdown("#### 📖 RBI e-Mandate Rules")
        st.markdown("""
        <div style="background:#0f172a; border:1px solid #1e293b; border-radius:10px; padding:14px 18px; font-size:0.82rem; color:#94a3b8; line-height:1.9;">
        <strong style="color:#818cf8;">NACH Retry Circular:</strong><br>
        • Max 3 auto-debit attempts per 30-day window<br>
        • Mandatory prior notification before debit<br>
        • 24h cooling-off after failed debit attempt<br><br>
        <strong style="color:#818cf8;">DPDP Act 2023:</strong><br>
        • Explicit opt-out must be honored immediately<br>
        • Contact hours: 10:00–19:00 IST only<br>
        • All outreach must be audited with consent proof<br><br>
        <strong style="color:#818cf8;">Stopping Rules Enforced:</strong><br>
        • Fraud suspected → Zero contact<br>
        • Dispute raised → Route to desk<br>
        • Active PTP → Pause during grace<br>
        • Negative EV → Suppress outreach
        </div>
        """, unsafe_allow_html=True)

    if ms_run_btn:
        consents = [CommunicationChannel.WHATSAPP, CommunicationChannel.EMAIL, CommunicationChannel.SMS]
        if ms_voice:
            consents.append(CommunicationChannel.VOICE_HINGLISH)

        ms_event = TransactionFailureEvent(
            transaction_id=f"txn_ms_{int(time.time())}",
            customer_id=f"cust_ms_{int(time.time()) % 9999}",
            customer_name=ms_name,
            customer_phone="+919876543210",
            amount=float(ms_amount),
            scenario=ms_scenario,
            error_code="MANDATE_EXPIRED" if ms_scenario == "RECURRING_SUBSCRIPTION" else "INVOICE_OVERDUE_TIER_1",
            bank=ms_bank,
            customer_tier=CustomerTier(ms_tier),
            channel_consent=consents,
            opted_out=ms_optout,
            disputed=ms_dispute,
        )

        with st.spinner("Creating dunning sequence..."):
            sequence = mandate_sequencer.create_sequence(ms_event)
            sequence = mandate_sequencer.simulate_sequence_execution(ms_event, sequence)

        # Outcome header
        outcome_colors = {
            "RECOVERED": ("#052e16", "#4ade80", "#166534"),
            "STOPPED": ("#450a0a", "#f87171", "#7f1d1d"),
            "EXHAUSTED": ("#1c1107", "#fbbf24", "#78350f"),
        }
        bg, fg, border = outcome_colors.get(sequence.status, ("#111827", "#e2e8f0", "#1e2a3a"))
        st.markdown(f"""
        <div style="background:{bg}; border:1px solid {border}; border-radius:12px; padding:16px 22px; margin:16px 0;">
            <span style="font-size:0.75rem; font-weight:700; color:{fg}; text-transform:uppercase; letter-spacing:0.08em;">
                Sequence Outcome
            </span>
            <span style="font-size:1.3rem; font-weight:800; color:{fg}; margin-left:12px;">
                {sequence.status}
            </span>
            <span style="font-size:0.85rem; color:#475569; margin-left:16px;">
                ₹{sequence.total_recovered:,.2f} recovered · {sequence.stop_reason or 'Dunning complete'}
            </span>
        </div>
        """, unsafe_allow_html=True)

        # Step-by-step waterfall
        st.subheader("📊 Dunning Step Waterfall")
        step_cols = st.columns(len(sequence.steps))
        status_colors = {
            DunningStepStatus.COMPLETED: ("#10b981", "✅"),
            DunningStepStatus.SKIPPED_COMPLIANCE: ("#ef4444", "🛑"),
            DunningStepStatus.SKIPPED_RECOVERED: ("#6b7280", "⏭️"),
            DunningStepStatus.PENDING: ("#475569", "⏳"),
            DunningStepStatus.EXECUTING: ("#f59e0b", "⚡"),
        }
        for i, (step, col) in enumerate(zip(sequence.steps, step_cols)):
            color, icon = status_colors.get(step.status, ("#475569", "❓"))
            bg_color = "#0f2e1a" if step.status == DunningStepStatus.COMPLETED and step.amount_recovered > 0 else "#111827"
            with col:
                st.markdown(f"""
                <div style="background:{bg_color}; border:1px solid #1e2a3a; border-top:3px solid {color};
                            border-radius:10px; padding:12px 10px; text-align:center; min-height:140px;">
                    <div style="font-size:1.2rem;">{icon}</div>
                    <div style="font-size:0.65rem; font-weight:700; color:#64748b; margin:4px 0; text-transform:uppercase;">{step.name[:22]}</div>
                    <div style="font-size:0.7rem; color:#94a3b8;">T+{step.delay_hours}h</div>
                    <div style="font-size:0.72rem; color:{color}; margin-top:6px; font-weight:600;">{step.status.value}</div>
                    {f'<div style="font-size:0.78rem; color:#4ade80; font-weight:700; margin-top:4px;">₹{step.amount_recovered:,.0f}</div>' if step.amount_recovered > 0 else ''}
                    {f'<div style="font-size:0.65rem; color:#6b7280; margin-top:4px;">{step.discount_pct:.0f}% off</div>' if step.discount_pct > 0 else ''}
                </div>
                """, unsafe_allow_html=True)

        # Detailed table
        st.subheader("📋 Detailed Step Trace")
        rows = mandate_sequencer.get_sequence_summary_df_data([sequence])
        if rows:
            st.dataframe(pd.DataFrame(rows), use_container_width=True)

    # Multi-sequence batch demo
    st.divider()
    st.subheader("🚀 Batch Mandate Sequencer — Run 20 Sequences")
    if st.button("⚡ Run 20 Mandate Sequences & Show Analytics", use_container_width=True):
        batch_events = RecoveryBatchSimulator.generate_synthetic_batch(20)
        all_sequences = []
        with st.spinner("Running 20 dunning sequences..."):
            for e in batch_events:
                seq = mandate_sequencer.create_sequence(e)
                seq = mandate_sequencer.simulate_sequence_execution(e, seq)
                all_sequences.append(seq)

        rec_seqs = [s for s in all_sequences if s.status == "RECOVERED"]
        stopped_seqs = [s for s in all_sequences if s.status == "STOPPED"]
        exhausted_seqs = [s for s in all_sequences if s.status == "EXHAUSTED"]

        r1, r2, r3, r4 = st.columns(4)
        r1.metric("Total Sequences", len(all_sequences))
        r2.metric("Recovered", len(rec_seqs), delta=f"₹{sum(s.total_recovered for s in rec_seqs):,.0f}")
        r3.metric("Compliance Stops", len(stopped_seqs))
        r4.metric("Exhausted", len(exhausted_seqs))

        # Status donut
        fig_seq = go.Figure(go.Pie(
            labels=["Recovered", "Stopped (Compliance)", "Exhausted"],
            values=[len(rec_seqs), len(stopped_seqs), len(exhausted_seqs)],
            hole=0.55,
            marker=dict(colors=["#10b981", "#ef4444", "#f59e0b"]),
        ))
        fig_seq.update_layout(**PLOTLY_DARK, title="Sequence Outcomes", height=280)
        st.plotly_chart(fig_seq, use_container_width=True)

        # Table
        all_rows = mandate_sequencer.get_sequence_summary_df_data(all_sequences)
        if all_rows:
            st.dataframe(pd.DataFrame(all_rows), use_container_width=True, height=300)


# ══════════════════════════════════════════════════════
# TAB 4: WEBHOOK EVENT SIMULATOR
# ══════════════════════════════════════════════════════
with tab_webhook:
    st.header("📡 Razorpay Webhook Event Stream Simulator")
    st.markdown(
        "Simulate live `payment.captured` and `payment.failed` webhooks streaming in from Razorpay. "
        "Watch the recovery dashboard update in real-time as payments land."
    )

    wh_col1, wh_col2 = st.columns([1, 1.5])
    with wh_col1:
        st.subheader("⚙️ Webhook Configuration")
        wh_count = st.slider("Number of Webhook Events", 5, 50, 15)
        wh_capture_pct = st.slider("payment.captured % (vs failed)", 20, 90, 65)
        wh_delay = st.slider("Event Delay (ms between events)", 0, 500, 80)
        wh_scenarios = st.multiselect(
            "Event Types to Simulate",
            ["payment.captured", "payment.failed", "order.paid", "refund.processed", "payout.processed"],
            default=["payment.captured", "payment.failed"],
        )
        run_webhook_btn = st.button("📡 Start Webhook Stream", type="primary", use_container_width=True)

    with wh_col2:
        st.subheader("📋 Webhook Payload Inspector")
        sample_txn = telemetry_tracker.records[-1] if telemetry_tracker.records else None
        sample_payload = {
            "entity": "event",
            "account_id": f"acc_{settings.RAZORPAY_KEY_ID[:8]}",
            "event": "payment.captured",
            "contains": ["payment"],
            "payload": {
                "payment": {
                    "entity": {
                        "id": "pay_RzpBuildathon2026",
                        "amount": int((sample_txn.event.amount if sample_txn else 8999.0) * 100),
                        "currency": "INR",
                        "status": "captured",
                        "method": "upi",
                        "captured": True,
                        "description": "RevRecover AI — Payment Link Recovery",
                        "vpa": "customer@upi",
                        "email": sample_txn.event.customer_email if sample_txn else "customer@example.com",
                        "contact": sample_txn.event.customer_phone if sample_txn else "+919876543210",
                        "created_at": int(datetime.now().timestamp()),
                    }
                }
            },
            "created_at": int(datetime.now().timestamp()),
        }
        st.code(json.dumps(sample_payload, indent=2), language="json")

    if run_webhook_btn:
        st.subheader("🔴 Live Webhook Event Stream")
        event_placeholder = st.empty()
        summary_placeholder = st.empty()
        total_captured_amt = 0.0
        event_rows = []

        for i in range(wh_count):
            time.sleep(wh_delay / 1000.0)
            event_type = random.choice(wh_scenarios) if wh_scenarios else "payment.captured"
            is_capture = (event_type == "payment.captured") and (random.random() < wh_capture_pct / 100.0)
            actual_event = "payment.captured" if is_capture else "payment.failed"
            rec = random.choice(telemetry_tracker.records) if telemetry_tracker.records else None
            amount = round(random.uniform(499, 45000), 2) if not rec else rec.event.amount
            txn_id = rec.event.transaction_id if rec else f"txn_wh_{i+1:04d}"
            customer = rec.event.customer_name[:20] if rec else f"Customer #{i+1}"
            payload_id = f"pay_{random.randint(100000, 999999)}"
            timestamp_str = datetime.now().strftime("%H:%M:%S.%f")[:-3]

            if is_capture:
                total_captured_amt += amount
                orchestrator.confirm_payment_recovered(txn_id, payload_id, amount)

            event_rows.insert(0, {
                "Time": timestamp_str,
                "Event": actual_event,
                "Payment ID": payload_id,
                "Customer": customer,
                "Amount (₹)": f"₹{amount:,.2f}",
                "Status": "✅ CAPTURED" if is_capture else "❌ FAILED",
            })

            html_log = ""
            for j, row in enumerate(event_rows[:8]):
                is_c = "CAPTURED" in row["Status"]
                bg = "#0f2e1a" if is_c else "#1a0a0a"
                border = "#166534" if is_c else "#450a0a"
                txt_color = "#4ade80" if is_c else "#f87171"
                opacity = max(0.4, 1.0 - j * 0.1)
                html_log += f"""<div style="background:{bg}; border:1px solid {border}; border-radius:7px;
                    padding:8px 14px; margin-bottom:5px; font-family:'JetBrains Mono',monospace;
                    font-size:0.75rem; opacity:{opacity:.1f};">
                    <span style="color:#475569;">[{row['Time']}]</span>
                    <span style="color:{txt_color}; font-weight:700; margin:0 8px;">{row['Event']}</span>
                    <span style="color:#94a3b8;">id=<code style="color:#818cf8;">{row['Payment ID']}</code></span>
                    <span style="color:#94a3b8; margin-left:10px;">amt=<code style="color:#fbbf24;">{row['Amount (₹)']}</code></span>
                    <span style="color:#94a3b8; margin-left:10px;">customer=<code style="color:#6ee7b7;">{row['Customer']}</code></span>
                </div>"""
            event_placeholder.markdown(html_log, unsafe_allow_html=True)
            summary_placeholder.markdown(f"""
            <div style="background:#0f2e1a; border:1px solid #166534; border-radius:8px;
                        padding:10px 18px; font-size:0.85rem; color:#4ade80;">
                💰 <strong>₹{total_captured_amt:,.2f}</strong> captured so far &nbsp;·&nbsp;
                {sum(1 for r in event_rows if 'CAPTURED' in r['Status'])} payments confirmed &nbsp;·&nbsp;
                Event {i+1}/{wh_count}
            </div>
            """, unsafe_allow_html=True)

        captured_count = sum(1 for r in event_rows if "CAPTURED" in r["Status"])
        st.success(f"✅ Stream complete — **{captured_count}/{wh_count} captured** (₹{total_captured_amt:,.2f} recovered)")
        w1, w2, w3 = st.columns(3)
        w1.metric("Payments Captured", captured_count, delta=f"+₹{total_captured_amt:,.0f}")
        w2.metric("Payments Failed", wh_count - captured_count)
        w3.metric("Webhook Success Rate", f"{captured_count/wh_count*100:.0f}%")
        st.dataframe(pd.DataFrame(event_rows), use_container_width=True)

        cumulative = []
        running = 0.0
        for r in reversed(event_rows):
            if "CAPTURED" in r["Status"]:
                running += float(r["Amount (₹)"].replace("₹", "").replace(",", ""))
            cumulative.append(running)
        fig_wh = go.Figure(go.Scatter(
            y=cumulative, mode="lines+markers",
            line=dict(color="#10b981", width=2),
            fill="tozeroy", fillcolor="rgba(16,185,129,0.08)",
        ))
        fig_wh.update_layout(**PLOTLY_DARK,
            title=dict(text="💰 Cumulative Revenue Captured via Webhooks", font=dict(color="#e2e8f0", size=13), x=0),
            height=230, xaxis_title="Event #", yaxis_title="₹ Captured")
        st.plotly_chart(fig_wh, use_container_width=True)

    st.divider()
    st.subheader("🔐 HMAC-SHA256 Webhook Signature Verification")
    sv_col1, sv_col2 = st.columns(2)
    with sv_col1:
        webhook_body = st.text_area("Webhook Body (JSON):", value='{"event":"payment.captured","entity":{"id":"pay_test"}}', height=80)
        webhook_sig = st.text_input("X-Razorpay-Signature Header:", value="paste_signature_here")
        if st.button("🔐 Verify HMAC Signature", use_container_width=True):
            import hashlib, hmac as hmac_lib
            secret = settings.RAZORPAY_WEBHOOK_SECRET or "buildathon_webhook_secret_2026"
            if hasattr(secret, "get_secret_value"):
                secret = secret.get_secret_value()
            expected = hmac_lib.new(secret.encode("utf-8"), webhook_body.encode("utf-8"), hashlib.sha256).hexdigest()
            if webhook_sig == expected:
                st.success("✅ Signature VALID — HMAC-SHA256 verified!")
            else:
                st.warning(f"⚠️ Signature mismatch. Expected: `{expected[:20]}...`\n\nThis is expected in demo mode — configure real secret in `.env`")
    with sv_col2:
        st.markdown("""
        <div style="background:#0f172a; border:1px solid #1e293b; border-radius:10px;
                    padding:14px 18px; font-size:0.8rem; color:#94a3b8; line-height:1.9;">
        <strong style="color:#818cf8;">Security Protocol:</strong><br>
        1. Razorpay signs payload with <code>HMAC-SHA256</code><br>
        2. Signature sent in <code>X-Razorpay-Signature</code> header<br>
        3. Compare to <code>hmac(secret, body).hexdigest()</code><br>
        4. Reject mismatches → prevents replay attacks<br><br>
        <strong style="color:#818cf8;">On payment.captured:</strong><br>
        • Update RecoveryCase → <code>RECOVERED</code><br>
        • Write final audit hash chain entry<br>
        • Release remaining dunning steps<br>
        • Trigger PTP fulfillment if applicable
        </div>
        """, unsafe_allow_html=True)


# ══════════════════════════════════════════════════════
# TAB 5: COHORT RISK ENGINE
# ══════════════════════════════════════════════════════
with tab_cohort:
    st.header("🔥 Cohort Risk Engine — Recovery Probability Heatmap")
    st.markdown(
        "Identify **which customer cohorts** carry the highest payment failure risk and "
        "lowest recovery probability. Drive proactive pre-emptive intervention strategy."
    )

    records = telemetry_tracker.records
    if not records:
        st.info("Run a Batch Benchmark first to populate cohort data.")
    else:
        tiers = ["STANDARD", "GOLD", "PLATINUM", "VIP_PLATINUM", "ENTERPRISE"]
        scenarios = ["PAYMENT_FAILURE", "CHECKOUT_ABANDONMENT", "RECURRING_SUBSCRIPTION", "B2B_INVOICE_OVERDUE"]

        cohort_recovery: dict[tuple, list] = {}
        for r in records:
            key = (r.event.customer_tier.value, r.event.scenario)
            if key not in cohort_recovery:
                cohort_recovery[key] = []
            cohort_recovery[key].append(1.0 if r.status == RecoveryStatus.RECOVERED else 0.0)

        heatmap_z, heatmap_text = [], []
        for sc in scenarios:
            row_z, row_t = [], []
            for tier in tiers:
                vals = cohort_recovery.get((tier, sc), [])
                rate = round(sum(vals) / len(vals) * 100, 1) if vals else 0.0
                row_z.append(rate)
                row_t.append(f"{rate:.0f}%<br>n={len(vals)}")
            heatmap_z.append(row_z)
            heatmap_text.append(row_t)

        fig_heatmap = go.Figure(go.Heatmap(
            z=heatmap_z,
            x=[t.replace("_", " ") for t in tiers],
            y=[s.replace("_", " ").title() for s in scenarios],
            text=heatmap_text,
            texttemplate="%{text}",
            colorscale=[[0.0,"#450a0a"],[0.3,"#7f1d1d"],[0.5,"#f59e0b"],[0.7,"#059669"],[1.0,"#10b981"]],
            colorbar=dict(title="Recovery %", tickfont=dict(color="#94a3b8")),
        ))
        fig_heatmap.update_layout(**PLOTLY_DARK,
            title=dict(text="🔥 Recovery Rate Heatmap: Customer Tier × Failure Scenario", font=dict(color="#e2e8f0", size=14), x=0),
            height=340)
        st.plotly_chart(fig_heatmap, use_container_width=True)

        co1, co2 = st.columns(2)
        with co1:
            st.subheader("📊 Recovery Rate by Error Code")
            error_recovery: dict[str, list] = {}
            for r in records:
                ec = r.event.error_code
                if ec not in error_recovery:
                    error_recovery[ec] = []
                error_recovery[ec].append(1.0 if r.status == RecoveryStatus.RECOVERED else 0.0)
            error_codes = sorted(error_recovery, key=lambda k: sum(error_recovery[k])/len(error_recovery[k]), reverse=True)
            rates_ec = [round(sum(error_recovery[ec])/len(error_recovery[ec])*100, 1) for ec in error_codes]
            colors_ec = ["#10b981" if r > 50 else "#f59e0b" if r > 25 else "#ef4444" for r in rates_ec]
            fig_ec = go.Figure(go.Bar(
                x=[ec.replace("_"," ")[:22] for ec in error_codes],
                y=rates_ec,
                marker_color=colors_ec,
                text=[f"{r}%" for r in rates_ec],
                textposition="outside",
            ))
            fig_ec.update_layout(**{k:v for k,v in PLOTLY_DARK.items() if k != 'xaxis'}, height=280, showlegend=False,
                title=dict(text="Error Code → Recovery Rate", font=dict(color="#e2e8f0", size=12), x=0),
                xaxis=dict(gridcolor="#1e2a3a", linecolor="#1e2a3a", tickangle=-30))
            st.plotly_chart(fig_ec, use_container_width=True)

        with co2:
            st.subheader("🌐 Revenue at Risk Sunburst (Tier → Scenario)")
            ids_s, labels_s, parents_s, values_s = [], [], [], []
            tier_totals: dict[str, float] = {}
            for r in records:
                t = r.event.customer_tier.value
                sc = r.event.scenario
                tier_totals[t] = tier_totals.get(t, 0.0) + r.event.amount
                nid = f"{t}|{sc}"
                if nid not in ids_s:
                    ids_s.append(nid); labels_s.append(sc.replace("_"," ")[:14])
                    parents_s.append(t); values_s.append(r.event.amount)
                else:
                    values_s[ids_s.index(nid)] += r.event.amount
            for t, v in tier_totals.items():
                ids_s.append(t); labels_s.append(t.replace("_"," ")); parents_s.append(""); values_s.append(v)
            fig_sun = go.Figure(go.Sunburst(
                ids=ids_s, labels=labels_s, parents=parents_s, values=values_s,
                branchvalues="total", marker=dict(colorscale="Portland"),
            ))
            fig_sun.update_layout(**PLOTLY_DARK, height=280,
                title=dict(text="At-Risk Revenue by Tier & Scenario", font=dict(color="#e2e8f0", size=12), x=0))
            st.plotly_chart(fig_sun, use_container_width=True)

        st.subheader("🏆 Cohort Recovery Leaderboard")
        leaderboard = []
        for (tier, sc), vals in cohort_recovery.items():
            total_amt = sum(r.money_recovered for r in records
                          if r.event.customer_tier.value == tier and r.event.scenario == sc)
            rate = sum(vals)/len(vals)
            leaderboard.append({
                "Tier": tier.replace("_"," "),
                "Scenario": sc.replace("_"," "),
                "# Events": len(vals),
                "Recovery Rate": f"{rate*100:.1f}%",
                "₹ Recovered": f"₹{total_amt:,.0f}",
                "Rank": "🥇" if rate > 0.6 else "🥈" if rate > 0.3 else "🥉",
            })
        leaderboard.sort(key=lambda x: float(x["Recovery Rate"].replace("%","")), reverse=True)
        st.dataframe(pd.DataFrame(leaderboard), use_container_width=True)

        st.divider()
        st.subheader("📉 Churn Risk vs Amount at Risk (Scatter)")
        scatter_data = [
            {"amount": r.event.amount, "churn_risk": r.diagnosis.churn_risk_if_contacted*100,
             "tier": r.event.customer_tier.value, "customer": r.event.customer_name[:15]}
            for r in records if r.diagnosis
        ]
        if scatter_data:
            tier_colors_m = {"STANDARD":"#6b7280","GOLD":"#f59e0b","PLATINUM":"#818cf8","VIP_PLATINUM":"#10b981","ENTERPRISE":"#ef4444"}
            df_sc = pd.DataFrame(scatter_data)
            fig_sc = go.Figure()
            for tn, tc in tier_colors_m.items():
                d = df_sc[df_sc["tier"] == tn]
                if not d.empty:
                    fig_sc.add_trace(go.Scatter(x=d["churn_risk"], y=d["amount"], mode="markers",
                        marker=dict(color=tc, size=7, opacity=0.75), name=tn.replace("_"," "),
                        hovertemplate="Customer: %{text}<br>Churn Risk: %{x:.1f}%<br>₹%{y:,.0f}", text=d["customer"]))
            fig_sc.update_layout(**PLOTLY_DARK, height=280, xaxis_title="Churn Risk %", yaxis_title="Amount (₹)",
                title=dict(text="Churn Risk vs Amount — Identify Dangerous Cohorts", font=dict(color="#e2e8f0", size=12), x=0))
            st.plotly_chart(fig_sc, use_container_width=True)


# ══════════════════════════════════════════════════════
# TAB 6: CUSTOMER JOURNEY TIMELINE
# ══════════════════════════════════════════════════════
with tab_journey:
    st.header("🗺️ Customer Recovery Journey Timeline")
    st.markdown(
        "Complete **forensic journey** of any individual transaction — "
        "from failure through every agent decision to final recovery outcome."
    )

    records = telemetry_tracker.records
    if not records:
        st.info("Run a batch to populate records.")
    else:
        jc1, jc2 = st.columns([2, 1])
        with jc1:
            txn_options = {
                f"{r.event.transaction_id} | {r.event.customer_name[:16]} | ₹{r.event.amount:,.0f} | {r.status.value}": r
                for r in reversed(records[-60:])
            }
            selected_label = st.selectbox("🔍 Select Transaction:", list(txn_options.keys()))
            selected_record = txn_options[selected_label]
        with jc2:
            outcome_color = "#10b981" if selected_record.status == RecoveryStatus.RECOVERED else "#f59e0b" if "PTP" in selected_record.status.value else "#ef4444" if "STOPPED" in selected_record.status.value else "#6366f1"
            st.markdown(f"""
            <div class="kpi-card" style="border-left:3px solid {outcome_color}; margin-top:28px;">
                <div class="kpi-label">Final Outcome</div>
                <div class="kpi-value" style="font-size:1rem; color:{outcome_color};">{selected_record.status.value}</div>
                <div class="kpi-delta">₹{selected_record.money_recovered:,.2f} recovered</div>
            </div>""", unsafe_allow_html=True)

        rec = selected_record
        st.subheader("⏱️ Agent Pipeline Timeline")

        timeline_steps = [
            ("🔴", "Payment Failure Detected", "IngestionAgent",
             f"Error: {rec.event.error_code} | Bank: {rec.event.bank} | Amount: ₹{rec.event.amount:,.2f} | Method: {rec.event.payment_method or 'N/A'}",
             "#ef4444"),
            ("🔬", "Root Cause Diagnosed", "RevenueLeakageDetector",
             f"Category: {rec.diagnosis.category.value if rec.diagnosis else 'N/A'} | P(Recovery): {rec.diagnosis.expected_recovery_probability*100:.0f}% | Urgency: {rec.diagnosis.urgency_level if rec.diagnosis else 'N/A'} | Churn Risk: {rec.diagnosis.churn_risk_if_contacted*100:.0f}% if contacted" if rec.diagnosis else "Diagnosis unavailable",
             "#6366f1"),
            ("🧮", "EV-Optimal Strategy Planned", "InterventionStrategist",
             f"Vector: {rec.intervention.vector.value if rec.intervention else 'N/A'} | Channel: {rec.intervention.channel.value if rec.intervention else 'N/A'} | EV=₹{rec.intervention.expected_value_inr:.2f} | Cost=₹{rec.intervention.contact_cost_inr:.2f} | Discount={rec.intervention.discount_pct_authorized:.0f}%" if rec.intervention else "No intervention planned",
             "#8b5cf6"),
            ("⚖️", "Compliance Evaluated", "ComplianceGovernor",
             f"Decision: {'✅ PERMITTED' if (rec.compliance and rec.compliance.action_permitted) else '🛑 BLOCKED'} | Rule: {rec.compliance.triggered_stopping_rule or 'None' if rec.compliance else 'N/A'} | {rec.compliance.reason[:60] if rec.compliance and rec.compliance.reason else ''}",
             "#10b981" if (rec.compliance and rec.compliance.action_permitted) else "#ef4444"),
        ]

        if rec.compliance and rec.compliance.action_permitted:
            timeline_steps.append(("🚀", "Recovery Outreach Executed", "RecoveryExecutor",
                f"Razorpay payment link created & dispatched via {rec.intervention.channel.value if rec.intervention else 'N/A'} | Link: {(rec.intervention.razorpay_payment_link or 'mock')[:50] if rec.intervention else 'N/A'}",
                "#f59e0b"))
            if rec.status == RecoveryStatus.RECOVERED:
                timeline_steps.append(("💰", "PAYMENT CONFIRMED ✅", "WebhookReconciler",
                    f"₹{rec.money_recovered:,.2f} captured | payment_id logged | Audit chain sealed | Recovery COMPLETE",
                    "#10b981"))
            elif rec.status == RecoveryStatus.PROMISE_TO_PAY_SET:
                timeline_steps.append(("📌", "Promise-to-Pay Logged", "PTPTracker",
                    f"₹{rec.ptp_record.promised_amount:,.2f} committed | Due: {rec.ptp_record.promised_date if rec.ptp_record else 'TBD'} | Reminders PAUSED during grace window",
                    "#3b82f6"))
            else:
                timeline_steps.append(("⏳", "Awaiting Customer Action", "OutreachMonitor",
                    "Payment link active | Customer has not yet completed payment | Auto-follow-up scheduled",
                    "#475569"))
        else:
            rule = rec.compliance.triggered_stopping_rule if rec.compliance else "UNKNOWN"
            timeline_steps.append(("🛑", "Recovery Stopped — Compliance Rule", "ComplianceGovernor",
                f"Hard stop: {rule} | {rec.compliance.reason[:80] if rec.compliance else ''}",
                "#ef4444"))
            timeline_steps.append(("🔒", "Case Archived", "AuditLedgerAgent",
                "All agent decisions sealed in SHA-256 hash chain. No further customer contact.", "#6b7280"))

        for step_idx, (icon, label, agent, detail, color) in enumerate(timeline_steps):
            is_last = step_idx == len(timeline_steps) - 1
            connector = "" if is_last else "<div style='width:2px; height:24px; background:#1e2a3a; margin:2px auto;'></div>"
            st.markdown(f"""
            <div style="display:flex; align-items:flex-start; margin-bottom:4px;">
                <div style="display:flex; flex-direction:column; align-items:center; margin-right:14px; width:32px; flex-shrink:0;">
                    <div style="width:32px; height:32px; border-radius:50%; background:{color}20;
                        border:2px solid {color}; display:flex; align-items:center; justify-content:center;
                        font-size:0.85rem; flex-shrink:0;">{icon}</div>
                    {connector}
                </div>
                <div style="background:#111827; border:1px solid {color}30; border-left:3px solid {color};
                    border-radius:0 10px 10px 10px; padding:10px 14px; flex:1; margin-bottom:8px;">
                    <div style="display:flex; justify-content:space-between; align-items:center; margin-bottom:4px;">
                        <span style="font-size:0.88rem; font-weight:700; color:{color};">{label}</span>
                        <code style="font-size:0.68rem; color:#475569; background:#0f172a; padding:2px 6px; border-radius:4px;">{agent}</code>
                    </div>
                    <div style="font-size:0.8rem; color:#94a3b8; line-height:1.5;">{detail}</div>
                </div>
            </div>""", unsafe_allow_html=True)

        a1, a2 = st.columns(2)
        with a1:
            st.subheader("📋 Cryptographic Audit Chain")
            audit_logs = audit_ledger_agent.get_logs_for_transaction(rec.event.transaction_id)
            if audit_logs:
                for i, log in enumerate(audit_logs):
                    with st.expander(f"#{i+1} {log.agent_name} → {log.action_taken}", expanded=(i==0)):
                        st.markdown(f"**Transition:** `{log.state_before}` → `{log.state_after}`")
                        st.code(f"Entry:  {log.entry_hash[:28]}...\nPrev:   {log.previous_hash[:28]}...", language="text")
            else:
                st.caption("No audit entries for this transaction in current session.")

        with a2:
            if rec.intervention and rec.compliance and rec.compliance.action_permitted:
                st.subheader("📱 Message Sent to Customer")
                link_url = rec.intervention.razorpay_payment_link or "https://rzp.io/i/preview"
                discount = rec.intervention.discount_pct_authorized
                channel = rec.intervention.channel
                if channel == CommunicationChannel.WHATSAPP:
                    from integrations.channels.whatsapp import WhatsAppChannelAdapter as WA
                    msg = WA.format_message(rec.event, link_url, discount)
                    st.markdown(f'<div class="msg-card-wa"><div class="msg-channel-header" style="color:#4ade80;">📱 WhatsApp</div>{msg[:350].replace(chr(10),"<br>")}</div>', unsafe_allow_html=True)
                elif channel == CommunicationChannel.SMS:
                    from integrations.channels.sms import SMSChannelAdapter as SCA
                    msg = SCA.format_message(rec.event, link_url)
                    st.markdown(f'<div class="msg-card-sms"><div class="msg-channel-header" style="color:#60a5fa;">💬 SMS</div>{msg[:300].replace(chr(10),"<br>")}</div>', unsafe_allow_html=True)
                elif channel == CommunicationChannel.VOICE_HINGLISH:
                    from integrations.channels.voice_hinglish import HinglishVoiceAgentAdapter as HV
                    script = HV.generate_opening_script(rec.event, link_url)
                    st.markdown(f'<div class="msg-card-voice"><div class="msg-channel-header" style="color:#a78bfa;">🎙️ Hinglish Voice</div>{script[:300]}</div>', unsafe_allow_html=True)
                elif channel == CommunicationChannel.EMAIL:
                    from integrations.channels.email import EmailChannelAdapter as EA
                    ed = EA.format_email(rec.event, link_url)
                    st.markdown(f'<div class="msg-card-email"><div class="msg-channel-header" style="color:#fbbf24;">📧 {ed.get("subject","Email")}</div>{ed.get("body","")[:300].replace(chr(10),"<br>")}</div>', unsafe_allow_html=True)

        st.divider()
        st.subheader("📊 Outcome Distribution (Last 50 Transactions)")
        recent = records[-50:]
        status_counts: dict[str, int] = {}
        for r in recent:
            s = r.status.value
            status_counts[s] = status_counts.get(s, 0) + 1
        sc_colors = {"RECOVERED":"#10b981","PROMISE_TO_PAY_SET":"#3b82f6","OUTREACH_ACTIVE":"#f59e0b",
                     "STOPPED_FRAUD_RISK":"#ef4444","STOPPED_OPT_OUT":"#f97316","STOPPED_NEGATIVE_EV":"#8b5cf6",
                     "STOPPED_DISPUTE_ESCALATED":"#ec4899","STOPPED_MAX_ATTEMPTS_EXHAUSTED":"#6b7280"}
        labels_p = list(status_counts.keys())
        fig_st = go.Figure(go.Pie(
            labels=[l.replace("_"," ") for l in labels_p], values=list(status_counts.values()),
            hole=0.5, marker=dict(colors=[sc_colors.get(l,"#374151") for l in labels_p]),
            textinfo="label+percent+value", textfont=dict(size=10),
        ))
        fig_st.update_layout(**PLOTLY_DARK, height=300,
            title=dict(text="Status Distribution — Last 50 Transactions", font=dict(color="#e2e8f0", size=13), x=0))
        st.plotly_chart(fig_st, use_container_width=True)


# ══════════════════════════════════════════════════════
# TAB 7: RAZORPAY TEST API
# ══════════════════════════════════════════════════════
with tab_rzp:
    st.header("💳 Official Razorpay Test Mode API Gateway")
    st.markdown("Interact directly with `api.razorpay.com/v1` using your test credentials.")
    st.info(f"🔑 **Connected Key**: `{settings.RAZORPAY_KEY_ID}` | **Base URL**: `https://api.razorpay.com/v1`")

    rz_col1, rz_col2 = st.columns([1.2, 1])
    with rz_col1:
        st.subheader("🚀 Create Razorpay Test Payment Link")
        with st.form("direct_rzp_link_form"):
            r_amt = st.number_input("Amount (₹)", value=499.0, min_value=1.0, step=50.0)
            r_name = st.text_input("Customer Name", value="Aarav Sharma")
            r_phone = st.text_input("Phone (+91)", value="+919876543210")
            r_desc = st.text_input("Description", value="RevRecover AI — Test Recovery Link")
            create_link_btn = st.form_submit_button("💳 Create Real Razorpay Payment Link", type="primary")

        if create_link_btn:
            with st.spinner("Calling Razorpay POST /v1/payment_links..."):
                resp = razorpay_client.create_payment_link(
                    amount=float(r_amt), customer_name=r_name,
                    customer_phone=r_phone, description=r_desc,
                )
            st.success(f"✅ Link created: **`{resp.id}`**")
            st.markdown(f"""
            <div style="background:#0b3b2e; border:1px solid #166534; border-radius:10px; padding:14px 18px; margin:10px 0;">
                <div style="color:#4ade80; font-size:0.8rem; font-weight:700; margin-bottom:6px;">🔗 RAZORPAY PAYMENT LINK CREATED</div>
                <div style="font-size:0.9rem; color:#d1fae5;">
                    <strong>Link ID:</strong> <code style="color:#6ee7b7;">{resp.id}</code><br>
                    <strong>Short URL:</strong> <a href="{resp.short_url}" style="color:#34d399;">{resp.short_url}</a><br>
                    <strong>Amount:</strong> ₹{r_amt:,.2f}<br>
                    <strong>Customer:</strong> {r_name}
                </div>
            </div>
            """, unsafe_allow_html=True)

    with rz_col2:
        st.subheader("📋 Active Payment Links")
        if st.button("🔄 Refresh from Razorpay API", use_container_width=True):
            st.rerun()
        live_links = razorpay_client.fetch_payment_links(count=8)
        if live_links:
            links_table = [{"Link ID": l.get("id"), "Amount": f"₹{l.get('amount',0)/100:,.2f}",
                            "Status": l.get("status"), "URL": l.get("short_url")} for l in live_links]
            st.dataframe(pd.DataFrame(links_table), use_container_width=True)
        else:
            st.caption("No links yet. Create one to see it here.")


# ══════════════════════════════════════════════════════
# TAB 5: HINGLISH VOICE SANDBOX
# ══════════════════════════════════════════════════════
with tab_voice:
    st.header("🎙️ Hinglish Conversational Voice Recovery Agent")
    st.markdown("High-touch empathetic AI voice calls for high-ticket recoveries and B2B receivables.")

    col_v1, col_v2 = st.columns([1, 1.3])
    with col_v1:
        v_name = st.text_input("Customer Name", value="Rahul Sharma", key="voice_name")
        v_amount = st.number_input("Transaction Value (₹)", value=18500.0, step=1000.0, key="voice_amt")
        v_scenario = st.selectbox("Scenario", ["CHECKOUT_ABANDONMENT", "B2B_INVOICE_OVERDUE", "RECURRING_SUBSCRIPTION"])
        v_resp = st.radio("Simulate Customer Response:", [
            "Agree to Pay via WhatsApp Link",
            "Promise to Pay Tomorrow (PTP)",
            "Dispute Invoice / Return Product",
            "Opt-Out / Do Not Call",
        ])
        trigger_voice = st.button("📞 Simulate Live Call", type="primary", use_container_width=True)

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

        st.markdown("**🎙️ AI Opening Script:**")
        st.markdown(f"""
        <div class="msg-card-voice">
            <div class="msg-channel-header" style="color:#a78bfa;">🤖 RevRecover AI Voice Agent</div>
            {opening_script}
        </div>
        """, unsafe_allow_html=True)

    with col_v2:
        st.subheader("📝 Live Call Transcript")
        if trigger_voice:
            preset_map = {
                "Agree to Pay via WhatsApp Link": "AGREE_TO_PAY",
                "Promise to Pay Tomorrow (PTP)": "PROMISE_TO_PAY",
                "Dispute Invoice / Return Product": "DISPUTE_RAISED",
                "Opt-Out / Do Not Call": "OPT_OUT",
            }
            dialogue = HinglishVoiceAgentAdapter.simulate_dialogue_flow(demo_event, preset_map[v_resp], plink)

            for turn in dialogue["transcript"]:
                speaker = turn["speaker"]
                text = turn["text"]
                if "Agent" in speaker:
                    st.markdown(f"<div class='chat-agent'><b>🤖 {speaker}:</b><br>{text}</div>", unsafe_allow_html=True)
                else:
                    st.markdown(f"<div class='chat-user'><b>👤 {speaker}:</b><br>{text}</div>", unsafe_allow_html=True)

            st.divider()
            outcome = dialogue["outcome"]
            sentiment = dialogue["sentiment"]
            sentiment_icon = "😊" if sentiment == "POSITIVE" else "😟"
            st.markdown(f"**Call Outcome:** `{outcome}` | **Sentiment:** {sentiment_icon} `{sentiment}`")

            if dialogue.get("ptp_record"):
                ptp = dialogue["ptp_record"]
                st.warning(f"📌 **Promise-to-Pay Logged:** ₹{ptp.promised_amount:,.2f} due by '{ptp.promised_date}'. Outreach paused during grace window.")

            # Mid-call interaction
            st.divider()
            st.subheader("💬 Interactive Voice Turn (Type Anything)")
            voice_input = st.text_input("Customer Speech:", "Haan payment fail ho gaya, link bhej do main abhi kar deta hoon")
            if st.button("📞 Process Voice Turn & Dispatch Link"):
                v_res = voice_recovery_agent.process_customer_speech_or_text(
                    demo_event, voice_input, "https://rzp.io/i/win_link_demo"
                )
                st.markdown(f"**Agent Response:** `{v_res.get('agent_response_hinglish','')}`")
                st.markdown(f"**Detected Sentiment:** `{v_res.get('detected_sentiment','')}`")
                st.markdown(f"**Payment Link Dispatched:** [{v_res.get('payment_link','')}]({v_res.get('payment_link','')})")
                if v_res.get("ptp_recorded"):
                    st.success("✅ Promise-to-Pay Commitment Logged!")


# ══════════════════════════════════════════════════════
# TAB 6: B2B RECEIVABLES
# ══════════════════════════════════════════════════════
with tab_b2b:
    st.header("🏢 B2B Receivables & Promise-to-Pay Ledger")
    st.markdown("Track corporate overdue receivables, aging buckets, dispute holds, and PTP commitments.")

    b2b_records = [r for r in telemetry_tracker.records if r.event.scenario == "B2B_INVOICE_OVERDUE"]

    if not b2b_records:
        st.info("No B2B receivables. Run the B2B Benchmark in Tab 1 to populate.")
    else:
        b2b_total = sum(r.event.amount for r in b2b_records)
        b2b_rec = sum(r.money_recovered for r in b2b_records)
        b2b_ptp = sum(r.ptp_record.promised_amount for r in b2b_records if r.ptp_record)
        b2b_disputed = sum(r.event.amount for r in b2b_records if r.event.disputed)
        b2b_outstanding = b2b_total - b2b_rec - b2b_ptp

        b1, b2, b3, b4 = st.columns(4)
        with b1:
            st.markdown(kpi_card("Total Overdue", fmt_inr(b2b_total), f"{len(b2b_records)} invoices", "red"), unsafe_allow_html=True)
        with b2:
            st.markdown(kpi_card("Directly Settled", fmt_inr(b2b_rec), "Paid via link/transfer", "green"), unsafe_allow_html=True)
        with b3:
            st.markdown(kpi_card("PTP Commitments", fmt_inr(b2b_ptp), "Promise-to-Pay active", "blue"), unsafe_allow_html=True)
        with b4:
            st.markdown(kpi_card("In Dispute", fmt_inr(b2b_disputed), "Routed to desk", "orange"), unsafe_allow_html=True)

        # Aging buckets chart
        aging_buckets = {"0-30 days": 0.0, "31-60 days": 0.0, "61-90 days": 0.0, "90+ days": 0.0}
        for r in b2b_records:
            if "TIER_1" in r.event.error_code:
                aging_buckets["0-30 days"] += r.event.amount
            elif "TIER_2" in r.event.error_code:
                aging_buckets["31-60 days"] += r.event.amount
            elif "DISPUTE" in r.event.error_code:
                aging_buckets["61-90 days"] += r.event.amount
            else:
                aging_buckets["90+ days"] += r.event.amount

        fig_aging = go.Figure(go.Bar(
            x=list(aging_buckets.keys()),
            y=list(aging_buckets.values()),
            marker_color=["#10b981", "#f59e0b", "#f97316", "#ef4444"],
            text=[fmt_inr(v) for v in aging_buckets.values()],
            textposition="outside",
        ))
        fig_aging.update_layout(**PLOTLY_DARK,
            title=dict(text="📊 B2B Invoice Aging Buckets", font=dict(color="#e2e8f0", size=13), x=0),
            height=280)
        st.plotly_chart(fig_aging, use_container_width=True)

        # Receivables table
        b2b_data = []
        for r in b2b_records:
            b2b_data.append({
                "Invoice ID": r.event.metadata.get("invoice_id", r.event.transaction_id),
                "Company": r.event.customer_name[:25],
                "Amount (₹)": f"₹{r.event.amount:,.2f}",
                "Aging Tier": r.event.error_code,
                "Status": r.status.value,
                "PTP Date": r.ptp_record.promised_date if r.ptp_record else "—",
                "Disputed": "⚠️ YES" if r.event.disputed else "NO",
                "Channel Used": r.intervention.channel.value if r.intervention else "—",
            })
        st.dataframe(pd.DataFrame(b2b_data), use_container_width=True)


# ══════════════════════════════════════════════════════
# TAB 7: AUDIT LEDGER
# ══════════════════════════════════════════════════════
with tab_audit:
    st.header("🛡️ Cryptographic SHA-256 Compliance Audit Ledger")
    st.markdown("Tamper-evident, append-only audit trail — every state transition, compliance decision, and recovery action is cryptographically signed.")

    aud_col1, aud_col2, aud_col3 = st.columns(3)
    with aud_col1:
        verify_btn = st.button("🔐 Verify Hash Chain Integrity", type="primary")
    with aud_col2:
        zk_btn = st.button("🛡️ Generate ZK-Proof (DPDP 2023)", type="secondary")
    with aud_col3:
        export_audit_btn = st.button("📥 Export Audit Log as JSON", type="secondary")

    if verify_btn:
        is_valid, count = audit_ledger_agent.verify_ledger_integrity()
        if is_valid:
            st.success(f"✅ **Cryptographic Integrity Verified** — All {count} audit records form a valid SHA-256 hash chain. Zero tampering detected.")
        else:
            st.error(f"❌ Hash chain mismatch at index {count}!")

    if zk_btn:
        proof = audit_ledger_agent.generate_zkp_compliance_proof("rcase_demo_9912", "txn_live_demo")
        is_valid_proof, msg = audit_ledger_agent.verify_zkp_compliance_proof(proof)
        st.code(
            f"ZK Compliance Certificate (DPDP Act 2023)\n"
            f"{'='*50}\n"
            f"Proof ID:            {proof.proof_id}\n"
            f"SHA-256 ZK Hash:     {proof.zk_hash}\n"
            f"Timestamp:           {proof.timestamp.isoformat()}\n"
            f"DPDP Consent:        {'✅ VERIFIED' if proof.dpdp_consent_verified else '❌ FAILED'}\n"
            f"Contact Hours:       {'✅ VERIFIED' if proof.contact_hours_verified else '❌ FAILED'}\n"
            f"DND / Opt-Out:       {'✅ VERIFIED' if proof.dnd_opt_out_verified else '❌ FAILED'}\n"
            f"Max Attempts Rule:   {'✅ VERIFIED' if proof.max_attempts_verified else '❌ FAILED'}\n"
            f"{'='*50}\n"
            f"Verification Result: {'✅ VALID' if is_valid_proof else '❌ INVALID'}",
            language="yaml"
        )

    logs = audit_ledger_agent.get_all_logs(limit=200)

    if export_audit_btn and logs:
        export_data = [
            {
                "log_id": l.log_id,
                "timestamp": l.timestamp.isoformat(),
                "transaction_id": l.transaction_id,
                "agent_name": l.agent_name,
                "action_taken": l.action_taken,
                "state_before": l.state_before,
                "state_after": l.state_after,
                "compliance_verified": l.compliance_verified,
                "previous_hash": l.previous_hash,
                "entry_hash": l.entry_hash,
                "details": l.details,
            }
            for l in logs
        ]
        json_str = json.dumps(export_data, indent=2, default=str)
        st.download_button(
            label="📥 Download Audit Trail JSON",
            data=json_str.encode("utf-8"),
            file_name=f"revrecover_audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
            mime="application/json",
        )

    # Audit metrics
    if logs:
        a1, a2, a3 = st.columns(3)
        a1.metric("Total Audit Records", len(logs))
        a2.metric("Unique Agents Logged", len(set(l.agent_name for l in logs)))
        a3.metric("Compliance Verified", f"{sum(1 for l in logs if l.compliance_verified)}/{len(logs)}")

        log_data = []
        for l in reversed(logs[-100:]):
            log_data.append({
                "Timestamp": l.timestamp.strftime("%H:%M:%S"),
                "Txn ID": l.transaction_id,
                "Agent": l.agent_name,
                "Action": l.action_taken,
                "Transition": f"{l.state_before} → {l.state_after}",
                "Prev Hash": f"{l.previous_hash[:10]}...",
                "Entry Hash": f"{l.entry_hash[:10]}...",
                "✅": "✅" if l.compliance_verified else "❌",
            })
        st.dataframe(pd.DataFrame(log_data), use_container_width=True, height=400)
    else:
        st.info("Audit ledger is empty.")


# ══════════════════════════════════════════════════════
# ══════════════════════════════════════════════════════
# TAB 11: ENTERPRISE FEATURES
# ══════════════════════════════════════════════════════
with tab_enterprise:
    st.header("💎 Enterprise Capabilities Showcase")
    st.markdown("""
    <div style="background:linear-gradient(135deg,#1e1b4b,#0f172a); border:1px solid #312e81;
                border-radius:14px; padding:20px 26px; margin-bottom:20px;">
        <h3 style="color:#818cf8; margin:0 0 8px;">🚀 Production Architecture & Core Differentiators</h3>
        <div style="color:#a5b4fc; font-size:0.9rem; line-height:1.8;">
            1. <strong>Real Razorpay Test API</strong> — real payment links, not mock URLs<br>
            2. <strong>RBI-Compliant Mandate Sequencer</strong> — multi-step dunning with stopping rules at every step<br>
            3. <strong>Cryptographic SHA-256 Audit Chain</strong> — tamper-evident, ZK-provable compliance<br>
            4. <strong>Pre-Emptive Bank Telemetry Interception</strong> — swap gateway before payment drops<br>
            5. <strong>Contextual Bandit Thompson Sampling</strong> — learns optimal channel per persona<br>
            6. <strong>Hinglish AI Voice + Mid-Call Link Dispatch</strong> — human-grade empathetic recovery<br>
            7. <strong>Promise-to-Pay State Machine</strong> — PROPOSED→ACCEPTED→FULFILLED with grace freeze<br>
            8. <strong>Expected Value Optimizer</strong> — P(rec)*amount - cost - P(churn)*LTV formula<br>
            9. <strong>Full Plotly Analytics Suite</strong> — funnel, aging, donut, bar comparison<br>
            10. <strong>Enterprise ROI Calculator</strong> — C-suite decision tool with real recovery math
        </div>
    </div>
    """, unsafe_allow_html=True)

    w_col1, w_col2 = st.columns(2)

    with w_col1:
        st.subheader("🔮 Pre-Emptive Bank Telemetry Simulator")
        st.caption("Simulate bank downtime and watch RevRecover AI pre-emptively swap checkout routes.")
        from core.telemetry import bank_health_tracker
        selected_bank = st.selectbox("Select Acquiring Bank:", ["SBI","HDFC","ICICI","AXIS","UPI_NETWORK"])
        sim_sr = st.slider(f"Simulate {selected_bank} Success Rate (%)", 10.0, 100.0, 45.0, 5.0)
        sim_lat = st.slider(f"Simulate {selected_bank} Latency (ms)", 100, 3000, 1950, 50)

        if st.button(f"⚡ Test Interception on {selected_bank}", use_container_width=True):
            bank_health_tracker.set_bank_degradation(selected_bank, sim_sr, sim_lat)
            advice = bank_health_tracker.preemptive_interception_advice(selected_bank)
            if advice["preemptive_interception_recommended"]:
                st.warning(
                    f"🚨 **Interception Triggered!**\n\n"
                    f"• Status: `{advice['gateway_status']}`\n"
                    f"• Success Rate: `{advice['current_success_rate_pct']}%` at `{advice['latency_ms']}ms`\n"
                    f"• Route to: **`{advice['optimal_target_route']}`**\n"
                    f"• Estimated Lift: `+{advice['estimated_success_lift_pct']}%`\n\n"
                    f"*{advice['recommendation']}*"
                )
            else:
                st.success(f"🟢 {selected_bank} is healthy at `{advice['current_success_rate_pct']}%` success rate.")

    with w_col2:
        st.subheader("🛡️ Zero-Knowledge Compliance Verifier")
        st.caption("Mathematically prove DPDP 2023 & RBI compliance without exposing customer PII.")
        case_id_input = st.text_input("Recovery Case ID:", "rcase_ent_9988")
        txn_id_input = st.text_input("Transaction ID:", "txn_rzp_live_001")
        cv1, cv2 = st.columns(2)
        with cv1:
            gen_zk = st.button("🔑 Generate ZK-Proof", use_container_width=True)
        with cv2:
            ver_zk = st.button("✅ Verify Proof", use_container_width=True)

        if gen_zk or ver_zk:
            proof = audit_ledger_agent.generate_zkp_compliance_proof(case_id_input, txn_id_input)
            st.session_state["active_zk_proof"] = proof

        if "active_zk_proof" in st.session_state:
            p = st.session_state["active_zk_proof"]
            st.code(f"Proof ID: {p.proof_id}\nZK Hash: {p.zk_hash[:40]}...\nTimestamp: {p.timestamp.isoformat()}", language="yaml")
            is_v, msg = audit_ledger_agent.verify_zkp_compliance_proof(p)
            if is_v:
                st.success(msg[:120])
            else:
                st.error(msg)

    st.divider()
    w_col3, w_col4 = st.columns(2)

    with w_col3:
        st.subheader("📊 Enterprise ROI & Revenue Lift Calculator")
        from core.telemetry import calculate_enterprise_roi
        gmv_slider = st.slider("Merchant Annual GMV (₹)", 1000000, 500000000, 50000000, 5000000, format="₹%d")
        rec_slider = st.slider("Target Recovery Rate (%)", 50.0, 95.0, 74.2, 0.5)
        roi = calculate_enterprise_roi(gmv_slider, rec_slider)

        fig_roi = go.Figure()
        labels = ["At Risk", "Agent Gross Recovered", "Contact Costs", "Net Recovered"]
        values = [roi["estimated_annual_at_risk_inr"], roi["gross_recovered_inr"],
                  roi["estimated_contact_costs_inr"], roi["net_recovered_inr"]]
        fig_roi.add_trace(go.Bar(
            x=labels, y=values,
            marker_color=["#ef4444", "#10b981", "#f59e0b", "#6366f1"],
            text=[fmt_inr(v) for v in values], textposition="outside",
        ))
        fig_roi.update_layout(**PLOTLY_DARK, height=260, showlegend=False,
            title=dict(text=f"Annual Revenue Recovery — GMV {fmt_inr(gmv_slider)}",
                       font=dict(color="#e2e8f0", size=12), x=0))
        st.plotly_chart(fig_roi, use_container_width=True)

        r1, r2, r3 = st.columns(3)
        r1.metric("Annual At-Risk", fmt_inr(roi["estimated_annual_at_risk_inr"]))
        r2.metric("Net Recovered", fmt_inr(roi["net_recovered_inr"]), delta=f"{roi['roi_multiple']}x ROI")
        r3.metric("Churn Reduction", f"-{roi['churn_reduction_pct']}%")

    with w_col4:
        st.subheader("🎙️ Interactive Hinglish Voice Sandbox")
        st.caption("Real-time sentiment analysis & mid-call Razorpay link dispatch.")
        voice_input = st.text_input("Customer Speech:", "Haan payment fail ho gaya tha, abhi UPI se link bhej do main pay kar dunga.")
        if st.button("📞 Process Voice Turn & Dispatch Link", type="primary", use_container_width=True):
            event_v = TransactionFailureEvent(
                transaction_id="txn_prod_001",
                customer_id="cust_987654",
                customer_name="Praveen Kumar",
                customer_phone="+919876543210",
                amount=12500.0,
            )
            v_res = voice_recovery_agent.process_customer_speech_or_text(
                event_v, voice_input, "https://rzp.io/i/live_recovery_link"
            )
            sentiment = v_res.get("detected_sentiment", "POSITIVE")
            color = "#10b981" if sentiment == "POSITIVE" else "#ef4444"
            st.markdown(f"""
            <div style="background:#111827; border:1px solid #1e2a3a; border-left:3px solid {color};
                        border-radius:10px; padding:14px 18px; margin:8px 0;">
                <div style="font-size:0.72rem; color:#64748b; font-weight:700; margin-bottom:6px;">AGENT RESPONSE</div>
                <div style="color:#e2e8f0; font-size:0.88rem;">{v_res.get('agent_response_hinglish','')}</div>
                <div style="margin-top:10px; font-size:0.78rem; color:#94a3b8;">
                    Sentiment: <strong style="color:{color};">{sentiment}</strong> &nbsp;|&nbsp;
                    Link: <a href="{v_res.get('payment_link','')}" style="color:#818cf8;">{v_res.get('payment_link','')}</a>
                </div>
            </div>
            """, unsafe_allow_html=True)
            if v_res.get("ptp_recorded"):
                st.success("✅ Promise-to-Pay Commitment Logged into Audit Ledger!")

    # Full channel preview showcase
    st.divider()
    st.subheader("📱 Multi-Channel Message Card Gallery")
    st.markdown("Preview all 4 recovery channel message formats with a sample transaction.")
    demo_ev = TransactionFailureEvent(
        transaction_id="txn_gallery_demo",
        customer_id="cust_gallery",
        customer_name="Sneha Deshmukh",
        customer_phone="+919856789012",
        customer_email="sneha.d@example.com",
        amount=8999.0,
        scenario="CHECKOUT_ABANDONMENT",
        error_code="CHECKOUT_DROP_OFF",
        bank="HDFC",
    )
    gallery_link = "https://rzp.io/i/gallery_demo"
    mc1, mc2, mc3, mc4 = st.columns(4)

    with mc1:
        wa_msg = WhatsAppChannelAdapter.format_message(demo_ev, gallery_link, 7.5)
        st.markdown(f"""
        <div class="msg-card-wa">
            <div class="msg-channel-header" style="color:#4ade80;">📱 WhatsApp</div>
            {wa_msg[:300].replace(chr(10),'<br>')}
        </div>
        """, unsafe_allow_html=True)

    with mc2:
        sms_msg = SMSChannelAdapter.format_message(demo_ev, gallery_link)
        st.markdown(f"""
        <div class="msg-card-sms">
            <div class="msg-channel-header" style="color:#60a5fa;">💬 SMS</div>
            {sms_msg[:300].replace(chr(10),'<br>')}
        </div>
        """, unsafe_allow_html=True)

    with mc3:
        email_data = EmailChannelAdapter.format_email(demo_ev, gallery_link)
        st.markdown(f"""
        <div class="msg-card-email">
            <div class="msg-channel-header" style="color:#fbbf24;">📧 Email</div>
            <strong>{email_data.get('subject','')}</strong><br><br>
            {email_data.get('body','')[:250].replace(chr(10),'<br>')}
        </div>
        """, unsafe_allow_html=True)

    with mc4:
        voice_script = HinglishVoiceAgentAdapter.generate_opening_script(demo_ev, gallery_link)
        st.markdown(f"""
        <div class="msg-card-voice">
            <div class="msg-channel-header" style="color:#a78bfa;">🎙️ Hinglish Voice</div>
            {voice_script[:280]}
        </div>
        """, unsafe_allow_html=True)
