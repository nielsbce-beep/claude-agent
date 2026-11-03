"""
Generates Life Agent — Whoop Connection Guide.pdf
"""
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable, PageBreak
)
from reportlab.lib.enums import TA_LEFT

# ── Colours (matches Installation Guide) ────────────────────────────────────────
BG       = colors.HexColor("#0d0d0d")
ACCENT   = colors.HexColor("#00d4ff")
WHITE    = colors.HexColor("#f0f0f0")
GREY     = colors.HexColor("#888888")
GREEN    = colors.HexColor("#00ff88")
AMBER    = colors.HexColor("#ffb300")
CODEBG   = colors.HexColor("#1a1a1a")
DARKGREY = colors.HexColor("#2a2a2a")

W, H = A4

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

warn_style = S("Warn",
    fontName="Helvetica-Bold", fontSize=9, textColor=AMBER,
    spaceAfter=4, leading=13)

bullet_style = S("Bullet",
    fontName="Helvetica", fontSize=10, textColor=WHITE,
    spaceAfter=4, leading=15, leftIndent=12, bulletIndent=0)

def code_block(lines):
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

def on_page(canvas, doc):
    canvas.saveState()
    canvas.setFillColor(BG)
    canvas.rect(0, 0, W, H, fill=1, stroke=0)
    canvas.setFont("Helvetica", 8)
    canvas.setFillColor(GREY)
    canvas.drawString(20*mm, 12*mm, "Life Agent — Whoop Connection Guide")
    canvas.drawRightString(W - 20*mm, 12*mm, f"Page {doc.page}")
    canvas.restoreState()

OUTPUT = "C:/Users/niels/Claude agent/gumroad-product/Life Agent - Whoop Connection Guide.pdf"

doc = SimpleDocTemplate(
    OUTPUT, pagesize=A4,
    leftMargin=20*mm, rightMargin=20*mm,
    topMargin=22*mm, bottomMargin=22*mm,
)

story = []

# ── Cover ────────────────────────────────────────────────────────────────────
story.append(spacer(10))
story.append(Paragraph("Life Agent", title_style))
story.append(Paragraph("Whoop Connection Guide", subtitle_style))
story.append(hr())
story.append(Paragraph(
    "This guide walks you through connecting your Whoop account to Life Agent — "
    "what it unlocks, how the login actually works under the hood, and how to "
    "troubleshoot it when something goes wrong.",
    body_style))
story.append(spacer(4))
story.append(Paragraph(
    "Estimated setup time: 5 minutes   •   Requires a Whoop device + active membership",
    grey_style))
story.append(spacer(16))

# ── 0. What this unlocks ──────────────────────────────────────────────────────
story.append(Paragraph("0. What This Unlocks", h1_style))
story.append(hr())
story.append(Paragraph(
    "Life Agent is fully usable without Whoop — goals, calendar, journal and the "
    "board all work without it. Connecting Whoop adds your real recovery data "
    "into four places:",
    body_style))
story.append(spacer(6))

unlock_data = [
    ["Where", "What it adds"],
    ["Morning briefing", "Recovery %, HRV, resting heart rate, 14-day recovery/sleep\ntrend, training load, an overtraining warning"],
    ["Sport board agent", "Live recovery score woven into its advice when you ask\nthe board a training question"],
    ["Planning agent", "Recovery-aware day/week plans — dagplan and weekplan\nadjust training suggestions to how recovered you are"],
    ["Weekly review", "7-day recovery, sleep and training summary in the\nAI-generated week analysis"],
]
unlock_table = Table(unlock_data, colWidths=[45*mm, 110*mm])
unlock_table.setStyle(TableStyle([
    ("BACKGROUND",    (0, 0), (-1,  0), DARKGREY),
    ("BACKGROUND",    (0, 1), (-1, -1), CODEBG),
    ("TEXTCOLOR",     (0, 0), (-1,  0), ACCENT),
    ("TEXTCOLOR",     (0, 1), (-1, -1), WHITE),
    ("FONTNAME",      (0, 0), (-1,  0), "Helvetica-Bold"),
    ("FONTNAME",      (0, 1), (-1, -1), "Helvetica"),
    ("FONTSIZE",      (0, 0), (-1, -1), 9),
    ("ROWBACKGROUNDS",(0, 1), (-1, -1), [CODEBG, DARKGREY]),
    ("TOPPADDING",    (0, 0), (-1, -1), 7),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 7),
    ("LEFTPADDING",   (0, 0), (-1, -1), 10),
    ("VALIGN",        (0, 0), (-1, -1), "TOP"),
    ("BOX",           (0, 0), (-1, -1), 0.5, DARKGREY),
    ("INNERGRID",     (0, 0), (-1, -1), 0.3, DARKGREY),
    ("LEADING",       (0, 0), (-1, -1), 12),
]))
story.append(unlock_table)
story.append(spacer(6))
story.append(Paragraph(
    "Everything below happens between your machine and Whoop's servers directly — "
    "no third party sees your data, and nothing is uploaded anywhere except to "
    "Claude for generating the text advice.",
    grey_style))

story.append(spacer(16))

# ── 1. How the login works ───────────────────────────────────────────────────
story.append(Paragraph("1. How the Login Works (in plain terms)", h1_style))
story.append(hr())
story.append(Paragraph(
    "Life Agent never sees or asks for your Whoop password. Instead it uses OAuth2, "
    "the same mechanism as \"Sign in with Google\":",
    body_style))
story.append(spacer(4))
story.append(bullet("You run <font name='Courier' color='#00ff88'>python cli.py whoop-login</font>."))
story.append(bullet("The script starts a tiny, temporary web server on your own machine (localhost:8080) and opens your browser to Whoop's real login page."))
story.append(bullet("You log in on Whoop's own site and click Authorize — your password never touches Life Agent."))
story.append(bullet("Whoop redirects your browser back to that local server with a one-time authorization code."))
story.append(bullet("The script trades that code for an access token + refresh token, and saves them to a local file."))
story.append(bullet("Every future command reads that file — you don't log in again."))
story.append(spacer(4))
story.append(Paragraph(
    "This is why the redirect URI has to point at localhost:8080 — that's the "
    "address of the temporary local server catching Whoop's redirect.",
    grey_style))

story.append(spacer(16))
story.append(PageBreak())

# ── 2. Create a Whoop developer app ──────────────────────────────────────────
story.append(Paragraph("2. Create a Whoop Developer App", h1_style))
story.append(hr())
story.append(Paragraph(
    "1. Go to <font color='#00d4ff'>developer.whoop.com</font> and sign in with your "
    "normal Whoop account.<br/>"
    "2. Create a new app (any name, e.g. \"Life Agent\").<br/>"
    "3. In the app settings, set the <b>Redirect URI</b> to exactly:",
    body_style))
story.append(code_block(["http://localhost:8080/callback"]))
story.append(Paragraph(
    "This must match character-for-character — Whoop rejects the login if it doesn't. "
    "Don't change the port (8080): the local script that catches the login always "
    "listens there.",
    grey_style))
story.append(spacer(10))
story.append(Paragraph(
    "4. Under scopes, enable at least the six the code actually requests:",
    body_style))

scope_data = [
    ["Scope", "Why Life Agent needs it"],
    ["offline", "Issues a refresh token so you only log in once, ever"],
    ["read:recovery", "Recovery %, HRV, resting heart rate"],
    ["read:sleep", "Sleep performance % and sleep stages"],
    ["read:cycles", "Daily strain / today's physiological cycle"],
    ["read:workout", "Workout history for the training-load summary"],
    ["read:body_measurement", "Height/weight/max HR, used for some calculations"],
]
scope_table = Table(scope_data, colWidths=[45*mm, 110*mm])
scope_table.setStyle(TableStyle([
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
    ("TOPPADDING",    (0, 0), (-1, -1), 6),
    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ("LEFTPADDING",   (0, 0), (-1, -1), 10),
    ("BOX",           (0, 0), (-1, -1), 0.5, DARKGREY),
    ("INNERGRID",     (0, 0), (-1, -1), 0.3, DARKGREY),
    ("LEADING",       (0, 0), (-1, -1), 12),
]))
story.append(scope_table)
story.append(spacer(4))
story.append(Paragraph(
    "Skipping a scope doesn't break anything — the affected section just won't have "
    "data. If you'd rather not share body measurements, for example, leave that "
    "scope out.",
    grey_style))
story.append(spacer(8))
story.append(Paragraph(
    "5. Save the app. You'll see a <b>Client ID</b> and <b>Client Secret</b> — treat the "
    "secret like a password, copy both, you'll need them next.",
    body_style))

story.append(spacer(16))

# ── 3. Add credentials to .env ───────────────────────────────────────────────
story.append(Paragraph("3. Add Credentials to .env", h1_style))
story.append(hr())
story.append(Paragraph(
    "Open <font name='Courier' color='#00ff88'>.env</font> in the life-agent folder "
    "(copy it from <font name='Courier' color='#00ff88'>.env.example</font> first if you "
    "haven't already) and fill in:",
    body_style))
story.append(code_block([
    "WHOOP_CLIENT_ID=your-client-id",
    "WHOOP_CLIENT_SECRET=your-client-secret",
    "WHOOP_REDIRECT_URI=http://localhost:8080/callback",
]))
story.append(Paragraph(
    "The redirect URI here must be identical to the one you registered in section 2.",
    grey_style))

story.append(spacer(16))

# ── 4. Log in ─────────────────────────────────────────────────────────────────
story.append(Paragraph("4. Log In", h1_style))
story.append(hr())
story.append(Paragraph(
    "From the life-agent folder, run:",
    body_style))
story.append(code_block(["python cli.py whoop-login"]))
story.append(Paragraph(
    "A browser window opens asking you to log in to Whoop and authorize the app. "
    "Approve it — the tab will show \"Login gelukt! Sluit dit venster.\" and you can "
    "close it.",
    body_style))
story.append(spacer(4))
story.append(Paragraph(
    "Behind the scenes, a token is saved to "
    "<font name='Courier' color='#00ff88'>.whoop_token.json</font> in the life-agent "
    "folder. It refreshes itself automatically from then on — you only do this once.",
    grey_style))

story.append(spacer(16))

# ── 5. Verify ─────────────────────────────────────────────────────────────────
story.append(Paragraph("5. Verify It Works", h1_style))
story.append(hr())
story.append(Paragraph("Test the pieces one at a time so a problem is easy to isolate:", body_style))
story.append(code_block([
    "python cli.py status              # recovery + agenda, fastest check",
    "python morning_briefing.py        # full briefing, recovery section at the top",
    "python board.py sport \"How should I train today?\"   # sport agent using recovery",
]))
story.append(Paragraph(
    "You should see your recovery score, HRV and resting heart rate. "
    "If Whoop's servers haven't closed your current cycle yet, recovery can briefly "
    "show as unavailable — that's normal, it resolves after your next sleep.",
    body_style))

story.append(spacer(16))
story.append(PageBreak())

# ── 6. Token lifecycle & security ────────────────────────────────────────────
story.append(Paragraph("6. Token Lifecycle &amp; Security", h1_style))
story.append(hr())
story.append(Paragraph(
    "<b>How refreshing works</b> — the script doesn't track when your token expires. "
    "Every API call just tries the saved access token first; if Whoop responds "
    "\"401 Unauthorized\", it silently uses the refresh token to get a new one and "
    "retries. You never see this happen.",
    body_style))
story.append(spacer(8))
story.append(Paragraph(
    "<b>Where it's stored</b> — plain JSON at "
    "<font name='Courier' color='#00ff88'>.whoop_token.json</font> in the life-agent "
    "folder, containing your access and refresh token. Anyone with that file can "
    "read your Whoop data until you revoke access.",
    body_style))
story.append(spacer(8))
story.append(Paragraph("<b>Keep it out of git</b>", warn_style))
story.append(Paragraph(
    "This file is not a secret you type in — it's generated locally after login. "
    "Make sure your project's <font name='Courier' color='#00ff88'>.gitignore</font> "
    "includes it before you ever commit:",
    body_style))
story.append(code_block([".whoop_token.json"]))
story.append(Paragraph(
    "If it ever does end up in a commit or a shared zip, treat the token as leaked: "
    "revoke the app's access from your Whoop account settings and log in again to "
    "generate a fresh one.",
    grey_style))
story.append(spacer(8))
story.append(Paragraph(
    "<b>Revoking access</b> — you can disconnect Life Agent at any time from your "
    "Whoop account's connected-apps settings, without touching your Whoop membership "
    "itself. The local token file becomes useless immediately; delete it and run "
    "<font name='Courier' color='#00ff88'>whoop-login</font> again if you reconnect later.",
    body_style))

story.append(spacer(16))

# ── 7. Optional: CSV fallback ────────────────────────────────────────────────
story.append(Paragraph("7. Optional — CSV History Fallback", h1_style))
story.append(hr())
story.append(Paragraph(
    "For trend analysis (recovery/sleep trends over 14 days, overtraining signal), the "
    "system can also read Whoop's exported CSV history instead of the live API.",
    body_style))
story.append(spacer(4))
story.append(Paragraph(
    "1. In the Whoop app: Settings → Data Export → request your export (you'll get an "
    "email with a download link).<br/>"
    "2. Place these three files in the folder that <b>contains</b> your life-agent "
    "folder (one level up, next to it — not inside it):",
    body_style))
story.append(code_block([
    "physiological_cycles.csv",
    "sleeps.csv",
    "workouts.csv",
]))
story.append(Paragraph(
    "This step is optional — the live API path in sections 2-5 is what powers the "
    "daily briefing. The CSVs only add historical trend context.",
    grey_style))

story.append(spacer(16))
story.append(PageBreak())

# ── 8. Troubleshooting ────────────────────────────────────────────────────────
story.append(Paragraph("8. Troubleshooting", h1_style))
story.append(hr())

issues = [
    ("\"redirect_uri mismatch\" error",
     "The URI in .env doesn't exactly match the one registered on developer.whoop.com. "
     "Check for a trailing slash, http vs https, or a typo — they must be identical, "
     "character for character."),
    ("Browser doesn't open / login hangs forever",
     "Make sure nothing else is using port 8080 on your machine (another dev server, "
     "a previous stuck run) — the local callback server can't bind if it's taken. "
     "Close whatever's on that port, then run python cli.py whoop-login again."),
    ("\"Geen autorisatiecode ontvangen van Whoop\"",
     "You closed the browser tab before approving, denied access, or the redirect "
     "landed somewhere it couldn't be caught. Run the login command again and click "
     "Authorize before closing the tab."),
    ("401 / token errors after it worked before",
     "The token normally refreshes itself on any 401. If it's genuinely stuck (e.g. "
     "you revoked access on Whoop's side), delete .whoop_token.json and run "
     "python cli.py whoop-login again."),
    ("No recovery data / empty section",
     "Your most recent sleep cycle may still be open — Whoop typically closes it a "
     "few hours after you wake up. It resolves on its own, or use the CSV fallback "
     "for older data in the meantime."),
    ("Client Secret rejected / invalid_client error",
     "Double-check you copied the Secret, not the Client ID, into "
     "WHOOP_CLIENT_SECRET, and that there's no stray space or quote character "
     "pasted in from the developer portal."),
    ("Works on one machine, not on another",
     "The token file is local — it doesn't travel with the code. Run "
     "python cli.py whoop-login once on each machine you use."),
]

for title, desc in issues:
    story.append(Paragraph(f"<b>{title}</b>", h2_style))
    story.append(Paragraph(desc, body_style))

story.append(spacer(16))

# ── 9. FAQ ─────────────────────────────────────────────────────────────────────
story.append(Paragraph("9. FAQ", h1_style))
story.append(hr())

faqs = [
    ("Do I need a paid Whoop membership?",
     "Yes — the API reflects your live Whoop account, so it needs an active "
     "membership the same way the Whoop app does."),
    ("Does this affect my Whoop device or app?",
     "No. It only reads data Whoop already collected; nothing is written back, and "
     "your phone app keeps working exactly as before."),
    ("Do I have to log in every day?",
     "No. The offline scope gives Life Agent a refresh token, so one login lasts "
     "until you revoke access or delete the token file."),
    ("What if I don't want to connect Whoop at all?",
     "Skip this guide entirely. Recovery sections will just show \"No data "
     "available\" and every other feature — goals, calendar, journal, board — "
     "works normally without it."),
    ("Is my data sent anywhere besides Whoop and my own machine?",
     "The raw numbers stay local. Only when a feature generates AI text (e.g. the "
     "3 focus points or the sport agent's advice) does a short summary of that data "
     "get sent to Claude to generate the response."),
]

for q, a in faqs:
    story.append(Paragraph(f"<b>{q}</b>", h2_style))
    story.append(Paragraph(a, body_style))

story.append(spacer(10))
story.append(hr())
story.append(Paragraph(
    "This is a supplement to the main Installation Guide — see that document for the "
    "rest of the setup (Anthropic API key, goals, calendar).",
    grey_style))

doc.build(story, onFirstPage=on_page, onLaterPages=on_page)
print(f"PDF created: {OUTPUT}")
