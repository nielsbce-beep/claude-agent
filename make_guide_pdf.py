"""
Generates Life Agent — Installation Guide.pdf
"""
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER

# ── Colours ────────────────────────────────────────────────────────────────────
BG       = colors.HexColor("#0d0d0d")
ACCENT   = colors.HexColor("#00d4ff")
WHITE    = colors.HexColor("#f0f0f0")
GREY     = colors.HexColor("#888888")
GREEN    = colors.HexColor("#00ff88")
CODEBG   = colors.HexColor("#1a1a1a")
DARKGREY = colors.HexColor("#2a2a2a")

W, H = A4

# ── Styles ─────────────────────────────────────────────────────────────────────
styles = getSampleStyleSheet()

def S(name, **kw):
    return ParagraphStyle(name, **kw)

title_style = S("Title",
    fontName="Helvetica-Bold", fontSize=28, textColor=WHITE,
    spaceAfter=4, leading=34, alignment=TA_LEFT)

subtitle_style = S("Subtitle",
    fontName="Helvetica", fontSize=13, textColor=ACCENT,
    spaceAfter=20, leading=18)

h1_style = S("H1",
    fontName="Helvetica-Bold", fontSize=16, textColor=ACCENT,
    spaceBefore=18, spaceAfter=8, leading=20)

h2_style = S("H2",
    fontName="Helvetica-Bold", fontSize=12, textColor=WHITE,
    spaceBefore=12, spaceAfter=6, leading=16)

body_style = S("Body",
    fontName="Helvetica", fontSize=10, textColor=WHITE,
    spaceAfter=6, leading=15)

grey_style = S("Grey",
    fontName="Helvetica", fontSize=9, textColor=GREY,
    spaceAfter=4, leading=13)

code_style = S("Code",
    fontName="Courier", fontSize=9, textColor=GREEN,
    spaceAfter=2, leading=13, leftIndent=0)

bullet_style = S("Bullet",
    fontName="Helvetica", fontSize=10, textColor=WHITE,
    spaceAfter=4, leading=15, leftIndent=12, bulletIndent=0)

# ── Code block helper ──────────────────────────────────────────────────────────
def code_block(lines):
    """Returns a Table styled as a dark code block."""
    content = "\n".join(lines)
    cell = Paragraph(f'<font name="Courier" color="#00ff88">{content}</font>',
                     ParagraphStyle("cb", fontName="Courier", fontSize=9,
                                    textColor=GREEN, leading=14))
    t = Table([[cell]], colWidths=[155*mm])
    t.setStyle(TableStyle([
        ("BACKGROUND", (0,0), (-1,-1), CODEBG),
        ("ROUNDEDCORNERS", [4]),
        ("TOPPADDING",    (0,0), (-1,-1), 8),
        ("BOTTOMPADDING", (0,0), (-1,-1), 8),
        ("LEFTPADDING",   (0,0), (-1,-1), 12),
        ("RIGHTPADDING",  (0,0), (-1,-1), 12),
        ("BOX", (0,0), (-1,-1), 0.5, DARKGREY),
    ]))
    return t

def spacer(h=6):
    return Spacer(1, h)

def hr():
    return HRFlowable(width="100%", thickness=0.5, color=DARKGREY, spaceAfter=8, spaceBefore=4)

def bullet(text):
    return Paragraph(f"<bullet>&bull;</bullet> {text}", bullet_style)

# ── Page background ────────────────────────────────────────────────────────────
def on_page(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(BG)
    canvas.rect(0, 0, W, H, fill=1, stroke=0)
    # footer
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(GREY)
    canvas.drawString(20*mm, 12*mm, "Life Agent — Installation Guide")
    canvas.drawRightString(W - 20*mm, 12*mm, f"Page {doc.page}")
    canvas.restoreState()

# ── Build ──────────────────────────────────────────────────────────────────────
OUTPUT = "C:/Users/niels/Claude agent/gumroad-product/Life Agent — Installation Guide.pdf"

doc = SimpleDocTemplate(
    OUTPUT, pagesize=A4,
    leftMargin=20*mm, rightMargin=20*mm,
    topMargin=22*mm, bottomMargin=22*mm,
)

story = []

# ── Cover / Header ─────────────────────────────────────────────────────────────
story.append(spacer(10))
story.append(Paragraph("Life Agent", title_style))
story.append(Paragraph("Installation &amp; Setup Guide", subtitle_style))
story.append(hr())
story.append(Paragraph(
    "This guide walks you through installing, configuring and running "
    "the Life Agent system — from zero to your first morning briefing.",
    body_style))
story.append(spacer(4))
story.append(Paragraph(
    "Estimated setup time: 10–15 minutes   •   Requires Python 3.11+",
    grey_style))
story.append(spacer(16))

# ── 1. Requirements ────────────────────────────────────────────────────────────
story.append(Paragraph("1. Requirements", h1_style))
story.append(hr())

story.append(Paragraph("<b>Required</b>", h2_style))
story.append(bullet("Python 3.11 or higher — <font color='#00d4ff'>python.org/downloads</font>"))
story.append(bullet("An Anthropic API key — <font color='#00d4ff'>console.anthropic.com</font>"))
story.append(spacer(4))
story.append(Paragraph(
    "The API costs roughly €0.01 per morning briefing. "
    "At daily use, expect €0.10–0.20 per month.",
    grey_style))

story.append(spacer(8))
story.append(Paragraph("<b>Optional</b>", h2_style))
story.append(bullet("Whoop device + developer account — for recovery data"))
story.append(bullet("iCloud account — for calendar integration"))
story.append(Paragraph(
    "The system works without both. Recovery sections will show "
    "'No data available' and calendar will show 'No events'. Everything else works.",
    grey_style))

story.append(spacer(16))

# ── 2. Installation ────────────────────────────────────────────────────────────
story.append(Paragraph("2. Installation", h1_style))
story.append(hr())

story.append(Paragraph("<b>Step 1 — Unzip the file</b>", h2_style))
story.append(Paragraph(
    "Unzip <font name='Courier' color='#00ff88'>life-agent-v1.0.zip</font> "
    "to a folder of your choice, for example:", body_style))
story.append(code_block(["C:\\Projects\\life-agent\\     (Windows)",
                          "~/Projects/life-agent/       (Mac/Linux)"]))
story.append(spacer(10))

story.append(Paragraph("<b>Step 2 — Open a terminal in that folder</b>", h2_style))
story.append(Paragraph(
    "Windows: open the folder in Explorer, click the address bar, "
    "type <font name='Courier' color='#00ff88'>cmd</font> and press Enter.<br/>"
    "Mac/Linux: right-click the folder → Open Terminal.",
    body_style))
story.append(spacer(10))

story.append(Paragraph("<b>Step 3 — Install dependencies</b>", h2_style))
story.append(code_block(["pip install -r requirements.txt"]))
story.append(spacer(10))

story.append(Paragraph("<b>Step 4 — Create your .env file</b>", h2_style))
story.append(Paragraph(
    "Rename <font name='Courier' color='#00ff88'>.env.example</font> to "
    "<font name='Courier' color='#00ff88'>.env</font> and open it in any text editor.",
    body_style))
story.append(code_block([
    "# Minimum required:",
    "ANTHROPIC_API_KEY=sk-ant-api03-...",
    "",
    "# Optional — iCloud calendar:",
    "ICLOUD_USERNAME=your@icloud.com",
    "ICLOUD_APP_PASSWORD=xxxx-xxxx-xxxx-xxxx",
    "",
    "# Optional — Whoop:",
    "WHOOP_CLIENT_ID=your-client-id",
    "WHOOP_CLIENT_SECRET=your-client-secret",
]))
story.append(spacer(4))
story.append(Paragraph(
    "Get your Anthropic key at console.anthropic.com → API Keys → Create key.",
    grey_style))

story.append(spacer(16))

# ── 3. Configuration ───────────────────────────────────────────────────────────
story.append(Paragraph("3. Configuration", h1_style))
story.append(hr())

story.append(Paragraph("<b>Calendar name</b>", h2_style))
story.append(Paragraph(
    "Open <font name='Courier' color='#00ff88'>config.py</font> and set "
    "<font name='Courier' color='#00ff88'>CALENDAR_NAME</font> to the exact name "
    "of your iCloud calendar (case-sensitive). Or set it in your .env file:",
    body_style))
story.append(code_block(["CALENDAR_NAME=My Calendar"]))
story.append(spacer(10))

story.append(Paragraph("<b>Your goals</b>", h2_style))
story.append(Paragraph(
    "Copy the example file and edit it, or use the interactive coach:",
    body_style))
story.append(code_block([
    "# Option A — edit manually:",
    "cp data/goals_example.json data/goals.json",
    "",
    "# Option B — interactive setup:",
    "python goals_coach.py chat",
]))
story.append(spacer(10))

story.append(Paragraph("<b>Your portfolio (optional)</b>", h2_style))
story.append(code_block([
    "cp data/portfolio_example.json data/portfolio.json",
    "# Then edit portfolio.json with your own holdings",
]))

story.append(spacer(16))
story.append(PageBreak())

# ── 4. Optional integrations ───────────────────────────────────────────────────
story.append(Paragraph("4. Optional — Whoop &amp; iCloud", h1_style))
story.append(hr())

story.append(Paragraph("<b>Connecting Whoop</b>", h2_style))
story.append(Paragraph(
    "1. Go to <font color='#00d4ff'>developer.whoop.com</font> and create an app.<br/>"
    "2. Copy your Client ID and Secret into <font name='Courier' color='#00ff88'>.env</font>.<br/>"
    "3. Run the login command — a browser window opens for OAuth:",
    body_style))
story.append(code_block(["python cli.py whoop_login"]))
story.append(Paragraph(
    "Your token is saved locally and refreshes automatically. "
    "You only need to do this once.",
    grey_style))
story.append(spacer(10))

story.append(Paragraph("<b>Connecting iCloud Calendar</b>", h2_style))
story.append(Paragraph(
    "1. Go to <font color='#00d4ff'>appleid.apple.com</font> → "
    "Security → App-Specific Passwords → Generate.<br/>"
    "2. Add your iCloud email and that password to "
    "<font name='Courier' color='#00ff88'>.env</font>.<br/>"
    "3. Check which calendars are available:",
    body_style))
story.append(code_block(["python cli.py agendas"]))
story.append(Paragraph(
    "Copy the exact calendar name into "
    "<font name='Courier' color='#00ff88'>config.py</font> or your .env file.",
    grey_style))

story.append(spacer(16))

# ── 5. Running the system ──────────────────────────────────────────────────────
story.append(Paragraph("5. Running the System", h1_style))
story.append(hr())

story.append(Paragraph("<b>First run — test everything</b>", h2_style))
story.append(code_block(["python morning_briefing.py"]))
story.append(Paragraph(
    "You should see a morning briefing in your terminal with Whoop data (if connected), "
    "today's calendar events, your goals and 3 AI-generated focus points.",
    body_style))
story.append(spacer(10))

story.append(Paragraph("<b>Daily commands</b>", h2_style))

cmd_data = [
    ["Command", "What it does"],
    ["python morning_briefing.py",   "Morning overview — recovery, agenda, goals, focus"],
    ["python avond_checkin.py",      "Evening check-in — wins, blockers, tomorrow's commitment"],
    ["python weekly_review.py",      "Full week analysis with AI insights"],
    ["python goals_coach.py chat",   "Chat with your AI goals coach"],
    ["python journal_agent.py schrijven", "Write a journal entry with AI follow-up"],
    ['python board.py "question"',   "Ask all 6 agents and get a consensus answer"],
    ["python financieel_agent.py projectie", "Portfolio projection to your target"],
]

cmd_table = Table(cmd_data, colWidths=[72*mm, 83*mm])
cmd_table.setStyle(TableStyle([
    ("BACKGROUND",    (0, 0), (-1,  0), DARKGREY),
    ("BACKGROUND",    (0, 1), (-1, -1), CODEBG),
    ("TEXTCOLOR",     (0, 0), (-1,  0), ACCENT),
    ("TEXTCOLOR",     (0, 1), ( 0, -1), GREEN),
    ("TEXTCOLOR",     (1, 1), (-1, -1), WHITE),
    ("FONTNAME",      (0, 0), (-1,  0), "Helvetica-Bold"),
    ("FONTNAME",      (0, 1), ( 0, -1), "Courier"),
    ("FONTNAME",      (1, 1), (-1, -1), "Helvetica"),
    ("FONTSIZE",      (0, 0), (-1, -1), 9),
    ("ROWBACKGROUNDS",(0, 1), (-1, -1), [CODEBG, DARKGREY]),
    ("TOPPADDING",    (0, 0), (-1, -1), 7),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ("LEFTPADDING",   (0, 0), (-1, -1), 10),
    ("BOX",           (0, 0), (-1, -1), 0.5, DARKGREY),
    ("INNERGRID",     (0, 0), (-1, -1), 0.3, DARKGREY),
    ("LEADING",       (0, 0), (-1, -1), 13),
]))
story.append(cmd_table)
story.append(spacer(14))

story.append(Paragraph("<b>Run automatically every day</b>", h2_style))
story.append(Paragraph(
    "To run the full schedule automatically "
    "(briefing at 07:00, check-in at 21:00, review on Sundays):",
    body_style))
story.append(code_block(["python scheduler.py"]))
story.append(Paragraph(
    "Add this to your startup apps or Windows Task Scheduler so it runs in the background.",
    grey_style))

story.append(spacer(16))

# ── 6. Troubleshooting ─────────────────────────────────────────────────────────
story.append(Paragraph("6. Troubleshooting", h1_style))
story.append(hr())

issues = [
    ("API key error",
     "Make sure .env is in the same folder as the scripts and your key has no "
     "leading/trailing spaces."),
    ("iCloud timeout",
     "iCloud CalDAV can be slow. Try again — it usually connects on the second attempt. "
     "Check that your app-specific password is correct (not your main iCloud password)."),
    ("No Whoop data",
     "If the live API shows no data, the current cycle may still be open. "
     "Place your Whoop CSV exports in the data/ folder as a fallback."),
    ("Module not found",
     "Run pip install -r requirements.txt again. "
     "Make sure you're using Python 3.11+: python --version"),
    ("Calendar not found",
     "Run python cli.py agendas to see the exact names of your calendars. "
     "Copy the name exactly (case-sensitive) into config.py."),
]

for title, desc in issues:
    story.append(Paragraph(f"<b>{title}</b>", h2_style))
    story.append(Paragraph(desc, body_style))

story.append(spacer(10))
story.append(hr())
story.append(Paragraph(
    "Still stuck? Open an issue on GitHub or reach out directly. "
    "This system is used daily — bugs get fixed fast.",
    grey_style))

# ── Build PDF ──────────────────────────────────────────────────────────────────
doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
print(f"PDF created: {OUTPUT}")
