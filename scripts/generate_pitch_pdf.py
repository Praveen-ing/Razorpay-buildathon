import os
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, KeepTogether, HRFlowable
)
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.pdfgen import canvas

class NumberedCanvas(canvas.Canvas):
    def __init__(self, *args, **kwargs):
        super(NumberedCanvas, self).__init__(*args, **kwargs)
        self._saved_page_states = []

    def showPage(self):
        self._saved_page_states.append(dict(self.__dict__))
        self._startPage()

    def save(self):
        num_pages = len(self._saved_page_states)
        for state in self._saved_page_states:
            self.__dict__.update(state)
            self.draw_header_footer(num_pages)
            canvas.Canvas.showPage(self)
        canvas.Canvas.save(self)

    def draw_header_footer(self, page_count):
        self.saveState()
        self.setFont('Helvetica', 8)
        self.setFillColor(colors.HexColor('#64748b'))
        
        # Header (pages 2+)
        if self._pageNumber > 1:
            self.drawString(54, 750, 'RevRecover AI — 5-Minute Video Recording & Pitch Teleprompter')
            self.drawRightString(612 - 54, 750, 'Razorpay Buildathon — Track 03')
            self.setStrokeColor(colors.HexColor('#cbd5e1'))
            self.setLineWidth(0.5)
            self.line(54, 742, 612 - 54, 742)
            
        # Footer
        self.setStrokeColor(colors.HexColor('#cbd5e1'))
        self.setLineWidth(0.5)
        self.line(54, 45, 612 - 54, 45)
        self.drawString(54, 32, 'RevRecover AI | Official Submission Guide')
        page_text = f'Page {self._pageNumber} of {page_count}'
        self.drawRightString(612 - 54, 32, page_text)
        self.restoreState()

def build_pdf():
    pdf_path = 'RevRecover_AI_5Min_Video_Recording_Script.pdf'
    doc = SimpleDocTemplate(
        pdf_path,
        pagesize=letter,
        leftMargin=54,
        rightMargin=54,
        topMargin=54,
        bottomMargin=54,
    )

    styles = getSampleStyleSheet()

    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=20,
        leading=24,
        textColor=colors.HexColor('#0f172a'),
        spaceAfter=3,
    )

    subtitle_style = ParagraphStyle(
        'DocSubTitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10.5,
        leading=14,
        textColor=colors.HexColor('#4338ca'),
        spaceAfter=12,
    )

    h1_style = ParagraphStyle(
        'SectionH1',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=13,
        leading=17,
        textColor=colors.HexColor('#1e1b4b'),
        spaceBefore=10,
        spaceAfter=6,
    )

    scene_hdr_style = ParagraphStyle(
        'SceneHeader',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=15,
        textColor=colors.HexColor('#ffffff'),
    )

    label_style = ParagraphStyle(
        'MetaLabel',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=11.5,
        textColor=colors.HexColor('#334155'),
    )

    val_style = ParagraphStyle(
        'MetaVal',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8.5,
        leading=12,
        textColor=colors.HexColor('#0f172a'),
    )

    speech_style = ParagraphStyle(
        'SpeechText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9,
        leading=13.5,
        textColor=colors.HexColor('#0f172a'),
    )

    tip_style = ParagraphStyle(
        'TipText',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=8,
        leading=11,
        textColor=colors.HexColor('#0369a1'),
    )

    story = []

    # Title
    story.append(Paragraph('⚡ RevRecover AI — 5-Minute Video Recording Teleprompter', title_style))
    story.append(Paragraph('Exact Screen Navigation, Buttons to Click &amp; Word-for-Word Spoken Dialogue | Razorpay Buildathon', subtitle_style))
    story.append(HRFlowable(width='100%', thickness=1.5, color=colors.HexColor('#6366f1'), spaceBefore=0, spaceAfter=10))

    # Pre-Recording Checklist
    prep_data = [
        [
            Paragraph('<b>PRE-RECORDING CHECKLIST:</b><br/>'
                      '• <b>Browser Setup:</b> Open <code>http://localhost:8501</code> in full screen (F11 or 1920x1080).<br/>'
                      '• <b>FastAPI Server:</b> Keep running in background on port 8080 (<code>http://localhost:8080/docs</code>).<br/>'
                      '• <b>Screen Recorder:</b> Set to record browser window + crisp microphone audio (Loom, OBS, or QuickTime).<br/>'
                      '• <b>Pacing &amp; Runtime:</b> Target duration is <b>4:45</b> (giving you a safe buffer before the 5:00 limit).', tip_style)
        ]
    ]
    prep_table = Table(prep_data, colWidths=[504])
    prep_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f0f9ff')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#bae6fd')),
        ('TOPPADDING', (0,0), (-1,-1), 6),
        ('BOTTOMPADDING', (0,0), (-1,-1), 6),
        ('LEFTPADDING', (0,0), (-1,-1), 8),
        ('RIGHTPADDING', (0,0), (-1,-1), 8),
    ]))
    story.append(prep_table)
    story.append(Spacer(1, 10))

    def make_scene_block(time_range, scene_title, tab_name, action_desc, dialogue_text, pro_tip):
        header_data = [[
            Paragraph(f'<b>{time_range} — {scene_title}</b>', scene_hdr_style),
            Paragraph(f'<b>TAB: {tab_name}</b>', ParagraphStyle('TabHdr', parent=scene_hdr_style, alignment=2))
        ]]
        hdr_table = Table(header_data, colWidths=[330, 174])
        hdr_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#312e81')),
            ('TOPPADDING', (0,0), (-1,-1), 5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
            ('LEFTPADDING', (0,0), (-1,-1), 8),
            ('RIGHTPADDING', (0,0), (-1,-1), 8),
        ]))
        
        body_data = [
            [
                Paragraph('<b>ACTION &amp; SCREEN:</b>', label_style),
                Paragraph(action_desc, val_style)
            ],
            [
                Paragraph('<b>WHAT TO SAY (READ OUT LOUD):</b>', label_style),
                Paragraph(f'<i>\"{dialogue_text}\"</i>', speech_style)
            ],
            [
                Paragraph('<b>PRO TIP:</b>', label_style),
                Paragraph(pro_tip, tip_style)
            ]
        ]
        body_table = Table(body_data, colWidths=[120, 384])
        body_table.setStyle(TableStyle([
            ('BACKGROUND', (0,0), (-1,-1), colors.HexColor('#f8fafc')),
            ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#cbd5e1')),
            ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
            ('TOPPADDING', (0,0), (-1,-1), 5),
            ('BOTTOMPADDING', (0,0), (-1,-1), 5),
            ('LEFTPADDING', (0,0), (-1,-1), 8),
            ('RIGHTPADDING', (0,0), (-1,-1), 8),
        ]))
        
        return [KeepTogether([hdr_table, body_table, Spacer(1, 10)])]

    # Scene 1
    for el in make_scene_block(
        '0:00 - 0:45',
        'The Problem &amp; Core Value Proposition',
        'Main Dashboard (Top)',
        'Start at the top of <code>http://localhost:8501</code>. Point your cursor at the 6 KPI metric cards (Revenue at Risk, Gross Recovered, Net Lift, Recovery Rate, PTP, Compliance Stops).',
        'Hi everyone! I am presenting <b>RevRecover AI</b> for Track 03: AI Revenue Recovery.<br/><br/>'
        'In Indian digital commerce, revenue loss rarely happens in a single clean step. A UPI payment degrades due to transient bank downtime, a checkout gets abandoned on the OTP screen, a recurring SaaS mandate bounces on billing day, or a B2B invoice ages past 60 days without structured follow-up.<br/><br/>'
        'Most businesses handle this naively: they blast generic SMS spam that ruins customer trust, or they do nothing at all. We built <b>RevRecover AI</b>—an autonomous closed-loop multi-agent engine that detects revenue at risk, evaluates mathematical Expected Value, executes bounded recovery across WhatsApp, SMS, and Hinglish AI Voice, and proves measured money recovered with an immutable cryptographic audit ledger.',
        'Keep your delivery punchy and energetic. Stress that Indian merchants lose 5% to 15% of GMV silently!'
    ): story.append(el)

    # Scene 2
    for el in make_scene_block(
        '0:45 - 1:50',
        '\"The Bar\": Batch Benchmark Arena',
        '🚀 Batch Benchmark (Tab 1)',
        'Click on the <b>🚀 Batch Benchmark</b> tab. Leave \"Composite Full Spectrum (100 Transactions)\" selected. Click the purple button <b>\"Execute Batch Recovery\"</b>. Watch the real-time money counter tick up. Scroll down to show the Plotly Recovery Funnel and Channel Donut.',
        'Let us head straight to <b>The Bar</b>: proving measured money recovered across a realistic batch.<br/><br/>'
        'I will select the Composite Full Spectrum benchmark of 100 transactions and click <b>Execute Batch Recovery</b>. Watch our real-time streaming pipeline process each transaction.<br/><br/>'
        'Out of <b>₹32.3 Lakhs at risk</b> across e-commerce, SaaS mandates, and B2B invoices, RevRecover AI achieved a <b>71.8% gross recovery rate</b>, winning back over <b>₹23.2 Lakhs</b>. Compared to a naive static retry policy that only recovers 22%, our multi-agent engine delivered over <b>₹15.8 Lakhs in Net Revenue Lift</b> after deducting all message and API contact costs.<br/><br/>'
        'Below, you can see our Plotly pipeline funnel showing transactions progressing from At-Risk to Diagnosed to Recovered, and our Contextual Bandit donut routing intelligently across WhatsApp, SMS, and Silent API Retries. We can also export full audit records with one click.',
        'Scroll down smoothly while speaking so the reviewer sees the interactive Plotly funnel and channel donut.'
    ): story.append(el)

    story.append(PageBreak())

    # Scene 3
    for el in make_scene_block(
        '1:50 - 2:45',
        'RBI Mandate Retry Sequencer &amp; Expected Value',
        '📅 Mandate Sequencer (Tab 3)',
        'Click on the <b>📅 Mandate Sequencer</b> tab. Point out the 5-step dunning calendar on screen (Silent Retry -&gt; T+24h SMS -&gt; T+72h WhatsApp -&gt; T+7d Voice -&gt; T+14d Human Desk).',
        'Next, let us examine our <b>RBI-Compliant Mandate Retry Sequencer</b>. In India, recurring e-mandates and UPI Autopay must strictly adhere to the RBI circular: a maximum of 3 automated retries within 30 days, minimum 24-hour intervals, and 24-hour pre-debit notifications.<br/><br/>'
        'RevRecover AI implements an audited 5-step dunning calendar:<br/>'
        '• <b>Step 0:</b> Immediate Silent API retry—zero customer intrusion.<br/>'
        '• <b>Step 1:</b> T+24h SMS notification with a 1-click Razorpay payment link.<br/>'
        '• <b>Step 2:</b> T+72h WhatsApp outreach with a smart 5% incentive.<br/>'
        '• <b>Step 3:</b> Day 7 Hinglish conversational voice call for high-ticket accounts.<br/>'
        '• <b>Step 4:</b> Day 14 formal notice escalated to a human collections desk.<br/><br/>'
        'Crucially, every single step is bounded by our <b>Expected Value formula</b>: EV equals Probability of Recovery times Amount, minus Intervention Cost, minus Churn Risk times Customer LTV. If EV is zero or negative, the agent suppresses outreach automatically.',
        'Highlight the formula: EV = P(rec)*Amount - Cost - P(churn)*LTV. It demonstrates strong AI judgment!'
    ): story.append(el)

    # Scene 4
    for el in make_scene_block(
        '2:45 - 3:35',
        'Compliance Shield &amp; Hard Stopping Rules',
        '⚡ Live Event (Tab 2)',
        'Click on the <b>⚡ Live Event</b> tab. Under Quick Scenario Presets, click <b>\"🛑 DND Opt-Out Test\"</b>. Click the blue button <b>\"Ingest &amp; Trigger Autonomous Workflow\"</b>. Point out the red compliance stop banner and ZK-certificate.',
        'An autonomous agent is only as good as its safety guardrails. Let us test our <b>Compliance Governor and Hard Stopping Rules</b>.<br/><br/>'
        'I will click the <b>DND Opt-Out Test</b> preset and ingest the event. Watch what happens immediately: our Compliance Governor detects that the customer requested opt-out under DPDP 2023 regulations. It executes an <b>immediate hard STOP</b>. Zero messages are dispatched, zero customer spam, and a cryptographic compliance certificate is generated.<br/><br/>'
        'The same non-bypassable stopping rules apply to suspected fraud, active invoice disputes, and Promise-to-Pay commitments. If a customer promises to pay next Tuesday, all dunning reminders freeze completely during the grace period.',
        'Point your cursor at the \"STOPPED_COMPLIANCE\" badge and the verified DPDP compliance certificate.'
    ): story.append(el)

    # Scene 5
    for el in make_scene_block(
        '3:35 - 4:25',
        'Hinglish AI Voice Recovery &amp; Mid-Call Link',
        '🎙️ Hinglish Voice (Tab 8)',
        'Click on the <b>🎙️ Hinglish Voice</b> tab. Click any preset dialogue, or type: <i>\"Payment fail ho gaya tha, abhi UPI se link bhej do main pay kar dunga.\"</i> Click <b>\"Process Voice Turn\"</b>. Point out the agent Hinglish reply and the live payment link.',
        'Now let us look at our <b>Hinglish Conversational Voice Recovery Agent</b>. In the Indian market, generic English automated IVR calls get hung up within 3 seconds.<br/><br/>'
        'Our agent conducts natural, empathetic bilingual conversations in Hinglish. When the customer explains, <i>\"Payment fail ho gaya tha, UPI link bhej do,\"</i> our agent detects the positive sentiment, confirms the Promise-to-Pay commitment, and <b>dynamically dispatches a 1-click Razorpay payment link mid-conversation</b> so the customer can complete payment while still on the phone.<br/><br/>'
        'This converts high-friction phone drop-offs into instant, successful UPI checkouts.',
        'Read the customer Hinglish quote with natural pronunciation. Reviewers will love it!'
    ): story.append(el)

    story.append(PageBreak())

    # Scene 6
    for el in make_scene_block(
        '4:25 - 5:00',
        'Architecture, Test Suite &amp; Strong Closing',
        '🛡️ Audit Ledger (Tab 10)',
        'Click on the <b>🛡️ Audit Ledger</b> tab. Show the cryptographic SHA-256 hash table. If possible, briefly show your terminal displaying <b>52 passed in 5.5s</b>.',
        'Under the hood, RevRecover AI is backed by an enterprise FastAPI backend running on port 8080 with 15 REST endpoints, an immutable SHA-256 cryptographic audit chain, and an automated test suite with <b>52 passing unit, integration, and end-to-end tests</b>.<br/><br/>'
        'We do not just identify where revenue is slipping away—we close the loop, protect customer trust, and win the money back.<br/><br/>'
        'Thank you!',
        'End with confidence. Check your recording timer to ensure it finishes between 4:30 and 4:50.'
    ): story.append(el)

    # Submission Cheat Sheet Table
    story.append(Paragraph('📋 Application Form Quick-Paste Reference', h1_style))
    story.append(Paragraph('Keep this handy when submitting at <b>forms.gle/d9r2gvxp8cmoZhon9</b>:', subtitle_style))

    form_data = [
        [Paragraph('<b>Field</b>', label_style), Paragraph('<b>Exact Value to Paste</b>', label_style)],
        [Paragraph('<b>Track</b>', label_style), Paragraph('Track 03 — AI Revenue Recovery', val_style)],
        [Paragraph('<b>Project Name</b>', label_style), Paragraph('RevRecover AI', val_style)],
        [Paragraph('<b>GitHub URL</b>', label_style), Paragraph('https://github.com/Praveen-ing/Razorpay-buildathon', val_style)],
        [Paragraph('<b>What It Solves</b>', label_style), Paragraph('Indian merchants silently bleed 5% to 15% of GMV to fragmented payment failures, abandoned checkouts, failed UPI autopay e-mandates, and overdue B2B receivables. RevRecover AI is an autonomous closed-loop multi-agent engine that ingests failure telemetry across 40+ Razorpay error codes, computes a mathematical Expected Value (EV = P(recovery) * Amount - Intervention Cost - P(churn) * LTV) to prevent over-contact, and executes bounded recovery across WhatsApp 1-click links, SMS, and empathetic Hinglish AI Voice calls. Every action strictly adheres to RBI e-mandate guidelines (max 3 retries, 24h intervals) and DPDP 2023 quiet hours, backed by an immutable SHA-256 cryptographic audit ledger proving measured net revenue recovered across high-volume batches.', val_style)],
        [Paragraph('<b>What Broke &amp; How You Got Out</b><br/><i>(Screened First!)</i>', label_style), Paragraph('<b>What Broke:</b><br/>'
                  '1. The Naive LLM-First Trap: Initially routing every failure to an LLM caused 2.8s latency, token costs exceeding margin on &lt;₹500 tickets, and stochastic hallucination of unauthorized discount policies.<br/>'
                  '2. Webhook Race Conditions: Burst webhook re-deliveries caused customers to receive duplicate SMS/WhatsApp messages within seconds.<br/><br/>'
                  '<b>How We Got Out:</b><br/>'
                  '1. Hierarchical AI Judgment: Replaced LLMs at the routing layer with a fast (&lt;5ms) Contextual Thompson Sampling Bandit + mathematical Expected Value formula (EV = P*Amt - Cost - P_churn*LTV). Constrained generative LLMs strictly to bilingual Hinglish objection handling.<br/>'
                  '2. Atomic Idempotency Store: In-memory SHA-256 idempotency ledger with atomic test-and-set locks to eliminate duplicate outreach.<br/>'
                  '3. Immutable Compliance Governor: Enforced RBI 24h intervals and DPDP quiet hours as hard pre-execution assertions.', val_style)],
    ]

    form_table = Table(form_data, colWidths=[110, 394])
    form_table.setStyle(TableStyle([
        ('BACKGROUND', (0,0), (-1,0), colors.HexColor('#e2e8f0')),
        ('BOX', (0,0), (-1,-1), 1, colors.HexColor('#cbd5e1')),
        ('INNERGRID', (0,0), (-1,-1), 0.5, colors.HexColor('#e2e8f0')),
        ('TOPPADDING', (0,0), (-1,-1), 5),
        ('BOTTOMPADDING', (0,0), (-1,-1), 5),
        ('LEFTPADDING', (0,0), (-1,-1), 7),
        ('RIGHTPADDING', (0,0), (-1,-1), 7),
    ]))
    story.append(form_table)

    doc.build(story, canvasmaker=NumberedCanvas)
    print('SUCCESS: PDF created at:', os.path.abspath(pdf_path))

if __name__ == '__main__':
    build_pdf()
