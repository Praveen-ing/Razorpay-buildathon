# 📋 RevRecover AI — Official Razorpay Buildathon Submission Pack

Use the exact answers below when filling out the application form at [**`forms.gle/d9r2gvxp8cmoZhon9`**](https://forms.gle/d9r2gvxp8cmoZhon9).

---

## 📝 Form Answers ("About the Build")

### 1. Your Track
```
Track 03 — AI Revenue Recovery
```

### 2. Project Name
```
RevRecover AI
```

### 3. What It Solves
```
Indian merchants silently bleed 5% to 15% of GMV to fragmented payment failures, abandoned checkouts, failed UPI autopay e-mandates, and overdue B2B receivables. RevRecover AI is an autonomous closed-loop multi-agent engine that ingests failure telemetry across 40+ Razorpay error codes, computes a mathematical Expected Value (EV = P(recovery) * Amount - Intervention Cost - P(churn) * LTV) to prevent over-contact, and executes bounded recovery across WhatsApp 1-click links, SMS, and empathetic Hinglish AI Voice calls. Every action strictly adheres to RBI e-mandate guidelines (max 3 retries, 24h intervals) and DPDP 2023 quiet hours, backed by an immutable SHA-256 cryptographic audit ledger proving measured net revenue recovered across high-volume batches.
```

### 4. GitHub Repo URL
```
https://github.com/Praveen-ing/Razorpay-buildathon
```

---

### 5. What Broke, and How You Got Out *(Read First by Reviewers)*

```
What Broke:
Early in development, our initial prototype suffered from two critical engineering failures:

1. The "Naive LLM-First" Trap: We initially routed every failed transaction through an LLM to generate recovery strategies and messages. In batch simulation, this collapsed our unit economics: latency spiked to 2.8s per transaction, token costs eclipsed the recovery margin on smaller tickets (<₹500), and stochastic outputs occasionally hallucinated unauthorized discount percentages exceeding merchant margins.
2. Race Conditions in Asynchronous Dunning: When simulating burst webhook events (e.g., simultaneous gateway timeouts and retry callbacks), a customer could receive an SMS and a WhatsApp message within 2 seconds of each other before state could persist, violating our contact policy and annoying users.

How We Got Out (AI Judgment & Systems Architecture):
1. Multi-Tiered AI Judgment: We separated deterministic guardrails from probabilistic AI. We replaced generative LLMs at the routing layer with a fast (<5ms) Contextual Thompson Sampling Multi-Armed Bandit and an explicit Expected Value equation: EV = P(recovery) * Amount - Channel Cost - P(churn) * Customer LTV. If EV <= 0, the engine silences outreach automatically. Generative LLMs were constrained specifically to high-leverage conversational moments: real-time bilingual Hinglish objection handling and personalized B2B settlement proposals.
2. Atomic State Machine & Idempotency Store: We introduced an in-memory SHA-256 idempotency ledger with atomic test-and-set locks. Any webhook re-delivery or burst event for an active recovery case is instantly deduplicated.
3. Hard Compliance Governor: We encoded RBI's 24-hour retry spacing and DPDP 2023 quiet hours (21:00-08:00 IST) as immutable pre-execution assertions. If a customer replies "STOP" or an invoice has an active dispute flag, the governor triggers an immediate, non-bypassable halt.

This pivot transformed an unstable script into a hardened, 52-test enterprise system recovering over 70% of at-risk revenue with 100% regulatory compliance.
```

---

## 🎬 5-Minute Video Pitch & Demo Script (Screen-by-Screen)

**Target Duration**: 4:30 – 4:50 minutes  
**Setup**: Open `http://localhost:8501` in your browser. Have your microphone ready.

---

### [0:00 – 0:45] The Problem & The Core Insight
- **Screen**: Camera on you, or showing the **RevRecover AI** header at `http://localhost:8501`.
- **What to Say**:
  > *"Hi everyone, I'm presenting **RevRecover AI** for Track 03: AI Revenue Recovery.  
  > In Indian digital commerce, revenue loss rarely happens in one clean step. A UPI payment degrades due to bank downtime, a checkout gets abandoned on the OTP screen, a recurring e-mandate fails due to billing-day balance shortfalls, or a B2B invoice ages past 60 days.  
  > Most companies treat recovery naively: they either spam users with blanket SMS blasts—burning customer goodwill—or do nothing at all.  
  > We built RevRecover AI: a closed-loop multi-agent engine that detects revenue at risk, evaluates mathematical Expected Value, executes bounded multi-channel outreach, and proves measured money recovered with an immutable audit ledger."*

---

### [0:45 – 1:50] "The Bar": Batch Benchmark Arena (Live Money Recovered)
- **Screen**: Click on the **`🚀 Batch Benchmark`** tab.
- **Action**: Click **"Execute Batch Recovery"** (100 Transactions).
- **What to Say**:
  > *"Let's head straight to 'The Bar': showing measured money recovered across a realistic batch.  
  > I'll select the Composite Full Spectrum benchmark of 100 transactions and hit Execute.  
  > Notice the real-time pipeline streaming live as transactions are processed through our agents:  
  > Out of ₹32.3 Lakhs at risk across e-commerce, SaaS mandates, and B2B invoices, our agent successfully recovered over ₹23.2 Lakhs—a 71.8% gross recovery rate.  
  > Compared to a naive static retry policy that only recovers 22%, our agent delivered over ₹15.8 Lakhs in **Net Revenue Lift** after deducting all channel contact costs.  
  > Below, you can see our interactive Plotly pipeline funnel, our Contextual Bandit channel distribution routing across WhatsApp, SMS, and Silent Retries, and the downloadable CSV and JSON audit trails."*

---

### [1:50 – 2:45] RBI Mandate Sequencer & Expected Value Optimization
- **Screen**: Click on the **`📅 Mandate Sequencer`** tab.
- **What to Say**:
  > *"Next, let's look at one of our flagship capabilities: the **RBI-Compliant Mandate Retry Sequencer**.  
  > In India, the RBI e-mandate circular strictly mandates a maximum of 3 automated retries within 30 days, minimum 24-hour intervals, and 24-hour pre-debit notifications.  
  > RevRecover AI implements a deterministic 5-step dunning calendar:  
  > Step 0 executes a silent gateway retry with zero customer interruption.  
  > Step 1 sends an SMS notification at T+24h with a 1-click Razorpay payment link.  
  > Step 2 escalates to WhatsApp with a smart 5% incentive at T+72h.  
  > Step 3 triggers an AI Hinglish voice call at Day 7.  
  > And Step 4 escalates high-value accounts to a human desk at Day 14.  
  > Every single step evaluates our Expected Value formula: if the marginal cost or churn penalty exceeds the recovery probability, the step is suppressed."*

---

### [2:45 – 3:45] Bounded Recovery & Hard Stopping Rules
- **Screen**: Click on the **`⚡ Live Event`** tab.
- **Action**: Click preset **"🛑 DND Opt-Out Test"**, then click **"Ingest & Trigger Autonomous Workflow"**.
- **What to Say**:
  > *"Now let's verify our hard stopping rules. An autonomous recovery agent is only as good as its guardrails.  
  > Let's test a customer who has opted out under DND / DPDP guidelines.  
  > Notice what happens instantly: the Compliance Governor intercepts the event and triggers a hard STOP. No message is dispatched, zero customer spam, and a cryptographic compliance certificate is generated.  
  > The same hard stopping rules apply to suspected fraud, active invoice disputes, and Promise-to-Pay grace periods. If a customer promises to pay next Monday, dunning freezes completely until that deadline."*

---

### [3:45 – 4:25] Hinglish AI Voice Sandbox & Real-Time Payment Link
- **Screen**: Click on the **`🎙️ Hinglish Voice`** tab (or the sandbox in Enterprise Features).
- **Action**: Click a preset message: *"Payment fail ho gaya tha, abhi UPI link bhej do mai pay kar dunga."* Click **"Process Voice Turn"**.
- **What to Say**:
  > *"Let's test our **Hinglish Conversational Voice Agent**. In India, generic English robocalls get disconnected in 3 seconds.  
  > Our voice agent speaks natural conversational Hinglish. When the customer says, 'Payment fail ho gaya tha, UPI link bhej do,' our agent detects the positive sentiment, confirms the promise to pay, and dynamically dispatches a 1-click Razorpay payment link mid-conversation so the user can complete payment while still on the call."*

---

### [4:25 – 5:00] Production Architecture, Test Suite & Wrap-up
- **Screen**: Switch briefly to your terminal showing `uv run pytest` (52 passed) or the **`🛡️ Audit Ledger`** tab.
- **What to Say**:
  > *"Under the hood, RevRecover AI is backed by a full FastAPI backend running on port 8080 with 15 REST endpoints, an immutable SHA-256 cryptographic audit chain, and an automated test suite with **52 passing unit, integration, and E2E tests**.  
  > We don't just detect lost revenue—we close the loop, protect customer trust, and win the money back.  
  > Thank you!"*
