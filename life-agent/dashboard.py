"""
Life OS — hypermodern zwart dashboard voor de life-agent.
Start met: python -m streamlit run dashboard.py
"""

import html
import json
import sys
from datetime import datetime, date, timedelta
from pathlib import Path

import anthropic
import streamlit as st
import plotly.graph_objects as go
from dotenv import load_dotenv

# ── Setup ──────────────────────────────────────────────────────────────────────
BASE = Path(__file__).parent
load_dotenv(BASE / ".env", override=True)
sys.stdout.reconfigure(encoding="utf-8")

from tools.whoop_api import get_latest_recovery, get_latest_sleep
from tools.calendar_tools import get_events
from tools.goals_store import get_active

DATA = BASE / "data"
CALORIES_FILE = DATA / "calories.json"
TODOS_FILE = DATA / "todos.json"
GROWTH_FILE = DATA / "growth_log.json"
PORTFOLIO_FILE = DATA / "portfolio.json"
KALENDER = "Niels AI agenda"
MODEL = "claude-opus-5-5"

# ── Page config ────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Life OS",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="collapsed",
)

# ── CSS ────────────────────────────────────────────────────────────────────────
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;900&display=swap');

html, body, [class*="css"], .stApp {
    font-family: 'Inter', sans-serif;
    background-color: #080808;
    color: #e8e8e8;
}

#MainMenu, footer, header { visibility: hidden; }
.stDeployButton { display: none; }
section[data-testid="stSidebar"] { display: none; }

.main .block-container, .block-container {
    padding: 1.5rem 2rem 2rem 2rem;
    max-width: 1600px;
}

/* Cards: st.container(border=True, key="card_…") */
[class*="st-key-card"] {
    background: #0f0f0f !important;
    border: 1px solid #1e1e1e !important;
    border-radius: 16px !important;
    padding: 1.2rem 1.4rem !important;
}
.card-title {
    font-size: 0.65rem;
    font-weight: 600;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #555;
    margin-bottom: 0.4rem;
}

.metric-big { font-size: 3.2rem; font-weight: 900; line-height: 1; letter-spacing: -0.02em; }
.metric-sub { font-size: 0.85rem; color: #888; margin-top: 0.5rem; }
.red   { color: #ef4444; }
.white { color: #e8e8e8; }

.stat-row { display: flex; gap: 0.6rem; margin-top: 0.8rem; flex-wrap: wrap; }
.stat-pill { background: #161616; border: 1px solid #222; border-radius: 8px; padding: 0.4rem 0.75rem; }
.stat-pill-val { font-size: 1.05rem; font-weight: 700; color: #e8e8e8; }
.stat-pill-lbl { font-size: 0.6rem; color: #555; text-transform: uppercase; letter-spacing: 0.08em; }

.event-row { display: flex; align-items: center; gap: 0.75rem; padding: 0.5rem 0; border-bottom: 1px solid #161616; }
.event-row:last-child { border-bottom: none; }
.event-time { font-size: 0.72rem; font-weight: 600; color: #555; min-width: 38px; font-variant-numeric: tabular-nums; }
.event-dot { width: 6px; height: 6px; border-radius: 50%; background: #3b82f6; flex-shrink: 0; }
.event-title { font-size: 0.85rem; color: #ccc; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.no-events { color: #444; font-size: 0.85rem; padding: 0.5rem 0; }

.goal-row { margin-bottom: 0.9rem; }
.goal-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.3rem; }
.goal-name { font-size: 0.82rem; color: #ccc; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 70%; }
.goal-pct { font-size: 0.78rem; font-weight: 700; color: #555; }
.bar-bg { height: 4px; background: #1a1a1a; border-radius: 2px; overflow: hidden; }
.bar-fill { height: 100%; border-radius: 2px; }
.goal-deadline { font-size: 0.62rem; margin-top: 0.2rem; }

.cal-bar-bg { height: 8px; background: #1a1a1a; border-radius: 4px; overflow: hidden; margin: 0.6rem 0; }
.cal-bar-fill { height: 100%; border-radius: 4px; background: linear-gradient(90deg, #22c55e, #86efac); }
.cal-bar-over { background: linear-gradient(90deg, #ef4444, #fca5a5); }

.prio { font-size: 0.58rem; font-weight: 700; letter-spacing: 0.08em; text-transform: uppercase;
        padding: 0.1rem 0.4rem; border-radius: 4px; margin-left: 0.4rem; }
.prio-high   { background: #ef444422; color: #ef4444; }
.prio-medium { background: #eab30822; color: #eab308; }
.prio-low    { background: #3b82f622; color: #3b82f6; }

.commit-text { font-size: 0.95rem; color: #ddd; line-height: 1.45; }
.streak { font-size: 0.75rem; color: #555; margin-top: 0.5rem; }

.header-date { font-size: 0.75rem; color: #444; letter-spacing: 0.08em; text-transform: uppercase; margin-bottom: 0.2rem; }
.header-title { font-size: 1.6rem; font-weight: 900; letter-spacing: -0.03em; color: #e8e8e8; }
.section-divider { border: none; border-top: 1px solid #151515; margin: 1rem 0; }

/* Streamlit widgets */
.stTextInput input, div[data-testid="stNumberInput"] input {
    background: #0b0b0b !important; border: 1px solid #222 !important;
    color: #e8e8e8 !important; border-radius: 8px !important;
}
.stButton > button, .stFormSubmitButton > button {
    background: #111 !important; border: 1px solid #222 !important; color: #aaa !important;
    border-radius: 8px !important; font-size: 0.8rem !important;
}
.stButton > button:hover, .stFormSubmitButton > button:hover { border-color: #444 !important; color: #e8e8e8 !important; }
.stCheckbox label p { font-size: 0.85rem !important; color: #ccc !important; }
[data-testid="stChatMessage"] { background: #0b0b0b; border: 1px solid #171717; border-radius: 12px; }
</style>
""", unsafe_allow_html=True)


# ── JSON helpers ───────────────────────────────────────────────────────────────

def lees_json(pad: Path, standaard):
    try:
        return json.loads(pad.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return standaard


def schrijf_json(pad: Path, data) -> None:
    pad.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def esc(tekst) -> str:
    return html.escape(str(tekst))


def eur(bedrag: float) -> str:
    """€12.345 (Nederlandse duizendtallen-notatie)."""
    return "€" + f"{bedrag:,.0f}".replace(",", ".")


# ── Externe data (gecached) ────────────────────────────────────────────────────

@st.cache_data(ttl=300)
def laad_whoop() -> dict:
    try:
        score = get_latest_recovery().get("score", {})
        s_score = get_latest_sleep().get("score", {})
        return {
            "recovery":      round(score.get("recovery_score", 0)),
            "hrv":           round(score.get("hrv_rmssd_milli", 0)),
            "rhr":           round(score.get("resting_heart_rate", 0)),
            "sleep_hours":   round(s_score.get("total_in_bed_time_milli", 0) / 3_600_000, 1),
            "sleep_quality": round(s_score.get("sleep_performance_percentage", 0)),
        }
    except Exception:
        return {}


@st.cache_data(ttl=300)
def laad_agenda(dag: date) -> list:
    try:
        start = datetime.combine(dag, datetime.min.time())
        end = start.replace(hour=23, minute=59)
        return get_events(start, end, calendar_name=KALENDER)
    except Exception:
        return []


def laad_doelen() -> list:
    try:
        return get_active()
    except Exception:
        return []


# ── Calorieën ──────────────────────────────────────────────────────────────────

def laad_calories() -> dict:
    return lees_json(CALORIES_FILE, {}).get(date.today().isoformat(), {"doel": 2500, "innames": []})


def sla_calorie_op(item: str, kcal: int) -> None:
    data = lees_json(CALORIES_FILE, {})
    dag = data.setdefault(date.today().isoformat(), {"doel": 2500, "innames": []})
    dag["innames"].append({"item": item, "kcal": kcal, "time": datetime.now().strftime("%H:%M")})
    schrijf_json(CALORIES_FILE, data)


def verwijder_calorie(index: int) -> None:
    data = lees_json(CALORIES_FILE, {})
    dag = data.get(date.today().isoformat())
    if dag and 0 <= index < len(dag["innames"]):
        dag["innames"].pop(index)
        schrijf_json(CALORIES_FILE, data)


# ── Todo's ─────────────────────────────────────────────────────────────────────

PRIO_ORDE = {"high": 0, "medium": 1, "low": 2}


def laad_todos() -> list:
    return lees_json(TODOS_FILE, {"todos": []}).get("todos", [])


def zet_todo_done(todo_id: str, done: bool) -> None:
    data = lees_json(TODOS_FILE, {"todos": []})
    for t in data["todos"]:
        if t["id"] == todo_id:
            t["done"] = done
            if done:
                t["done_at"] = date.today().isoformat()
    schrijf_json(TODOS_FILE, data)


def voeg_todo_toe(titel: str, prio: str) -> None:
    data = lees_json(TODOS_FILE, {"todos": []})
    nummers = [int(t["id"].split("_")[-1]) for t in data["todos"] if t["id"].split("_")[-1].isdigit()]
    data["todos"].append({
        "id": f"todo_{(max(nummers, default=0) + 1):03d}",
        "title": titel,
        "description": "",
        "priority": prio,
        "done": False,
        "created_at": date.today().isoformat(),
    })
    schrijf_json(TODOS_FILE, data)


# ── Commitment (growth_log) ────────────────────────────────────────────────────

def laad_growth() -> list:
    return lees_json(GROWTH_FILE, {"entries": []}).get("entries", [])


def commitment_vandaag(entries: list) -> dict | None:
    vandaag = date.today().isoformat()
    return next((e for e in reversed(entries) if e.get("date") == vandaag), None)


def zet_commitment(tekst: str) -> None:
    data = lees_json(GROWTH_FILE, {"entries": []})
    data["entries"].append({"date": date.today().isoformat(), "commitment": tekst, "achieved": False})
    schrijf_json(GROWTH_FILE, data)


def markeer_commitment(achieved: bool) -> None:
    data = lees_json(GROWTH_FILE, {"entries": []})
    vandaag = date.today().isoformat()
    for e in reversed(data["entries"]):
        if e.get("date") == vandaag:
            e["achieved"] = achieved
            break
    schrijf_json(GROWTH_FILE, data)


def streak(entries: list) -> int:
    """Aantal opeenvolgende dagen (t/m gisteren of vandaag) met een nagekomen commitment."""
    gehaald = {e["date"] for e in entries if e.get("achieved")}
    dag = date.today() if date.today().isoformat() in gehaald else date.today() - timedelta(days=1)
    n = 0
    while dag.isoformat() in gehaald:
        n += 1
        dag -= timedelta(days=1)
    return n


# ── Portfolio ──────────────────────────────────────────────────────────────────

def portfolio_samenvatting() -> dict:
    p = lees_json(PORTFOLIO_FILE, {})
    h = p.get("holdings", {})
    onderdelen = {
        "BND": h.get("bnd", {}).get("waarde", 0),
        "Aandelen": sum(x.get("waarde", 0) for x in h.get("aandelen", {}).get("posities", [])),
        "Goud": h.get("goud", {}).get("waarde", 0),
        "Bitcoin": h.get("bitcoin", {}).get("waarde", 0),
    }
    inleg = p.get("inleg", {})
    per_maand = inleg.get("bnd_maand", 0) + inleg.get("goud_maand", 0) + \
        (inleg.get("aandelen_week", 0) + inleg.get("bitcoin_week", 0)) * 52 / 12
    return {
        "totaal": sum(onderdelen.values()),
        "onderdelen": onderdelen,
        "doel": p.get("doel", {}).get("bedrag", 25000),
        "deadline": p.get("doel", {}).get("deadline", ""),
        "per_maand": per_maand,
        "bijgewerkt": p.get("last_updated", "?"),
    }


# ── Visuele helpers ────────────────────────────────────────────────────────────

def recovery_kleur(pct: int) -> str:
    if pct >= 67: return "#22c55e"
    if pct >= 34: return "#eab308"
    return "#ef4444"


def recovery_advies(pct: int) -> str:
    if pct >= 67: return "Normaal trainen"
    if pct >= 50: return "Matige training"
    if pct >= 34: return "Lichte beweging"
    return "Rust vandaag"


def urgentie_kleur(dagen: int) -> str:
    if dagen <= 7:  return "#ef4444"
    if dagen <= 14: return "#f97316"
    if dagen <= 30: return "#eab308"
    return "#3b82f6"


def gauge_figuur(waarde: int, kleur: str) -> go.Figure:
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=waarde,
        number={"font": {"size": 42, "color": kleur, "family": "Inter"}, "suffix": "%"},
        gauge={
            "axis": {"range": [0, 100], "visible": False},
            "bar": {"color": kleur, "thickness": 0.22},
            "bgcolor": "#161616",
            "borderwidth": 0,
        },
    ))
    fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", margin=dict(t=20, b=10, l=20, r=20),
                      height=170, font={"family": "Inter"})
    return fig


def titel(tekst: str) -> None:
    st.markdown(f'<div class="card-title">{tekst}</div>', unsafe_allow_html=True)


def event_html(events: list, kleur: str = "#3b82f6", tekstkleur: str = "#ccc") -> str:
    rijen = []
    for e in events:
        s = e["start"]
        tijd = s.strftime("%H:%M") if hasattr(s, "hour") else "hele dag"
        rijen.append(
            f'<div class="event-row"><span class="event-time">{tijd}</span>'
            f'<span class="event-dot" style="background:{kleur}"></span>'
            f'<span class="event-title" style="color:{tekstkleur}">{esc(e["summary"])}</span></div>'
        )
    return "".join(rijen)


# ── AI ─────────────────────────────────────────────────────────────────────────

@st.cache_resource
def ai_client() -> anthropic.Anthropic:
    return anthropic.Anthropic()


SYSTEEM = (
    "Je bent Niels' persoonlijke life-coach en assistent in zijn Life OS-dashboard. "
    "Je spreekt altijd Nederlands. Je bent direct, concreet en motiverend, zonder onnodige intro's. "
    "Gebruik de actuele data hieronder voor gepersonaliseerd advies. Houd antwoorden compact; "
    "gebruik korte lijstjes waar dat helpt."
)


def stream_antwoord(context: str, geschiedenis: list):
    """Yield tekst-chunks van Claude op basis van de volledige chatgeschiedenis."""
    messages = [
        {"role": "user" if b["rol"] == "user" else "assistant", "content": b["inhoud"]}
        for b in geschiedenis
    ]
    try:
        with ai_client().beta.messages.stream(
            model=MODEL,
            max_tokens=16000,
            system=f"{SYSTEEM}\n\nVandaag: {date.today().isoformat()}\n\nActuele data:\n{context}",
            output_config={"effort": "medium"},
            messages=messages,
            # Bij een (onterechte) weigering automatisch een ander model laten overnemen
            betas=["server-side-fallback-2026-07-01"],
            extra_body={"fallbacks": "default"},
        ) as stream:
            yield from stream.text_stream
            if stream.get_final_message().stop_reason == "refusal":
                yield "\n\n_(Claude kon deze vraag niet beantwoorden.)_"
    except anthropic.APIConnectionError:
        yield "⚠️ Geen verbinding met de Anthropic API."
    except anthropic.AuthenticationError:
        yield "⚠️ Ongeldige API-sleutel — controleer ANTHROPIC_API_KEY in .env."
    except anthropic.RateLimitError:
        yield "⚠️ Rate limit bereikt, probeer het zo opnieuw."
    except anthropic.APIStatusError as e:
        yield f"⚠️ API-fout ({e.status_code}): {e.message}"


# ── Sessie state ───────────────────────────────────────────────────────────────

st.session_state.setdefault("chat", [])   # [{rol, inhoud, label?}]


# ═══════════════════════════════════════════════════════════════════════════════
# HEADER
# ═══════════════════════════════════════════════════════════════════════════════

now = datetime.now()
DAGEN = ["maandag", "dinsdag", "woensdag", "donderdag", "vrijdag", "zaterdag", "zondag"]
MAANDEN = ["januari", "februari", "maart", "april", "mei", "juni", "juli",
           "augustus", "september", "oktober", "november", "december"]
dagstr = f"{DAGEN[now.weekday()]} {now.day} {MAANDEN[now.month - 1]}"
groet = "Goedemorgen" if 5 <= now.hour < 12 else "Goedemiddag" if now.hour < 18 else "Goedenavond"

col_h1, col_h2 = st.columns([4, 1])
with col_h1:
    st.markdown(f'<div class="header-date">{dagstr}</div>'
                f'<div class="header-title">{groet}, Niels ⚡</div>', unsafe_allow_html=True)
with col_h2:
    if st.button("↻ Vernieuwen", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# RIJ 1: WHOOP + AGENDA + DOELEN
# ═══════════════════════════════════════════════════════════════════════════════

whoop = laad_whoop()
events = laad_agenda(date.today())
morgen_events = laad_agenda(date.today() + timedelta(days=1))
doelen = laad_doelen()

col1, col2, col3 = st.columns([1.2, 1, 1.4])

with col1, st.container(border=True, key="card_whoop"):
    titel("Whoop herstel")
    rec = whoop.get("recovery", 0)
    if rec:
        kleur = recovery_kleur(rec)
        st.plotly_chart(gauge_figuur(rec, kleur), use_container_width=True,
                        config={"displayModeBar": False})
        pills = [("hrv", "ms", "HRV"), ("rhr", "bpm", "Rusthf"),
                 ("sleep_hours", "u", "Slaap"), ("sleep_quality", "%", "Kwaliteit")]
        pills_html = "".join(
            f'<div class="stat-pill"><div class="stat-pill-val">{whoop.get(k, "—")}'
            f'<span style="font-size:0.65rem;color:#555"> {eenheid}</span></div>'
            f'<div class="stat-pill-lbl">{lbl}</div></div>'
            for k, eenheid, lbl in pills
        )
        st.markdown(
            f'<div style="text-align:center;margin-top:-0.5rem;">'
            f'<span style="color:{kleur};font-weight:700;font-size:0.9rem;">{recovery_advies(rec)}</span></div>'
            f'<div class="stat-row" style="justify-content:center;">{pills_html}</div>',
            unsafe_allow_html=True,
        )
    else:
        st.markdown('<div class="no-events" style="text-align:center;padding:2rem 0">'
                    'Geen Whoop data — draai <code>python cli.py whoop-login</code></div>',
                    unsafe_allow_html=True)

with col2, st.container(border=True, key="card_agenda"):
    titel("Agenda vandaag")
    st.markdown(event_html(events) or '<div class="no-events">Geen events vandaag</div>',
                unsafe_allow_html=True)
    st.markdown("<hr class='section-divider'>", unsafe_allow_html=True)
    titel("Morgen")
    st.markdown(event_html(morgen_events[:4], "#6366f1", "#777") or '<div class="no-events">Vrij</div>',
                unsafe_allow_html=True)

with col3, st.container(border=True, key="card_doelen"):
    titel(f"Actieve doelen · {len(doelen)}")
    if doelen:
        def dagen_tot(g):
            try:
                return (date.fromisoformat(g["deadline"]) - date.today()).days
            except Exception:
                return None

        gesorteerd = sorted(doelen, key=lambda g: (dagen_tot(g) is None, dagen_tot(g) or 0))
        rijen = []
        for g in gesorteerd[:7]:
            dagen = dagen_tot(g)
            pct = g.get("progress", 0)
            uk = urgentie_kleur(dagen) if dagen is not None else "#3b82f6"
            dl = ("verlopen" if dagen < 0 else f"nog {dagen} dagen") if dagen is not None else ""
            rijen.append(
                f'<div class="goal-row"><div class="goal-header">'
                f'<span class="goal-name">{esc(g["title"])}</span><span class="goal-pct">{pct}%</span></div>'
                f'<div class="bar-bg"><div class="bar-fill" style="width:{max(2, min(100, pct))}%;'
                f'background:linear-gradient(90deg,{uk}aa,{uk});"></div></div>'
                f'<div class="goal-deadline" style="color:{uk}99">{dl}</div></div>'
            )
        st.markdown("".join(rijen), unsafe_allow_html=True)
    else:
        st.markdown('<div class="no-events">Geen actieve doelen</div>', unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# RIJ 2: COMMITMENT + TODO'S + PORTFOLIO
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown("<div style='margin-top:0.6rem'></div>", unsafe_allow_html=True)
col_c, col_t, col_p = st.columns([1.1, 1.5, 1])

growth = laad_growth()
commit = commitment_vandaag(growth)
todos = laad_todos()
open_todos = sorted((t for t in todos if not t.get("done")),
                    key=lambda t: PRIO_ORDE.get(t.get("priority"), 3))
portfolio = portfolio_samenvatting()

with col_c, st.container(border=True, key="card_commit"):
    titel("Commitment vandaag")
    if commit:
        st.markdown(f'<div class="commit-text">{esc(commit["commitment"])}</div>', unsafe_allow_html=True)
        gehaald = st.toggle("Nagekomen", value=bool(commit.get("achieved")), key="commit_toggle")
        if gehaald != bool(commit.get("achieved")):
            markeer_commitment(gehaald)
            st.rerun()
    else:
        with st.form("commit_form", clear_on_submit=True, border=False):
            tekst = st.text_input("Commitment", placeholder="Wat ga je vandaag zeker doen?",
                                  label_visibility="collapsed")
            if st.form_submit_button("Vastleggen", use_container_width=True) and tekst.strip():
                zet_commitment(tekst.strip())
                st.rerun()
    s = streak(growth)
    st.markdown(f'<div class="streak">🔥 Streak: <b style="color:#e8e8e8">{s}</b> '
                f'{"dag" if s == 1 else "dagen"}</div>', unsafe_allow_html=True)

with col_t, st.container(border=True, key="card_todos"):
    titel(f"Todo's · {len(open_todos)} open")
    if not open_todos:
        st.markdown('<div class="no-events">Alles af 🎉</div>', unsafe_allow_html=True)
    for t in open_todos[:8]:
        prio = t.get("priority", "low")
        c_chk, c_prio = st.columns([6, 1])
        with c_chk:
            if st.checkbox(t["title"], key=f"todo_{t['id']}", help=t.get("description") or None):
                zet_todo_done(t["id"], True)
                st.toast(f"✓ {t['title']}")
                st.rerun()
        with c_prio:
            st.markdown(f'<span class="prio prio-{prio}">{prio[0].upper()}</span>', unsafe_allow_html=True)
    with st.form("todo_form", clear_on_submit=True, border=False):
        c_in, c_pr, c_bt = st.columns([4, 1.4, 1])
        nieuw = c_in.text_input("Nieuwe todo", placeholder="Nieuwe todo…", label_visibility="collapsed")
        prio_in = c_pr.selectbox("Prioriteit", ["medium", "high", "low"], label_visibility="collapsed")
        if c_bt.form_submit_button("+", use_container_width=True) and nieuw.strip():
            voeg_todo_toe(nieuw.strip(), prio_in)
            st.rerun()

with col_p, st.container(border=True, key="card_portfolio"):
    titel("Portfolio → doel")
    tot, doel = portfolio["totaal"], portfolio["doel"]
    pct = min(100, tot / doel * 100) if doel else 0
    st.markdown(
        f'<div style="display:flex;justify-content:space-between;align-items:baseline;">'
        f'<span class="metric-big white" style="font-size:2.4rem">{eur(tot)}</span>'
        f'<span class="metric-sub">/ {eur(doel)}</span></div>'
        f'<div class="cal-bar-bg"><div class="cal-bar-fill" style="width:{pct:.1f}%;'
        f'background:linear-gradient(90deg,#8b5cf6,#3b82f6)"></div></div>'
        f'<div style="font-size:0.75rem;color:#555">{pct:.1f}% · inleg ≈ {eur(portfolio["per_maand"])}/maand'
        f' · deadline {esc(portfolio["deadline"])}</div>',
        unsafe_allow_html=True,
    )
    pills_html = "".join(
        f'<div class="stat-pill"><div class="stat-pill-val">{eur(w)}</div>'
        f'<div class="stat-pill-lbl">{naam}</div></div>'
        for naam, w in portfolio["onderdelen"].items() if w
    )
    st.markdown(f'<div class="stat-row">{pills_html}</div>'
                f'<div class="streak">Bijgewerkt: {esc(portfolio["bijgewerkt"])}</div>',
                unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════════════════════
# RIJ 3: CALORIEËN + AI CHAT
# ═══════════════════════════════════════════════════════════════════════════════

st.markdown("<div style='margin-top:0.6rem'></div>", unsafe_allow_html=True)
col4, col5 = st.columns([1, 2])

cal_data = laad_calories()
cal_doel = cal_data.get("doel", 2500)
innames = cal_data.get("innames", [])
cal_totaal = sum(i["kcal"] for i in innames)

with col4, st.container(border=True, key="card_cal"):
    titel("Calorieën vandaag")
    over = cal_totaal > cal_doel
    cal_pct = min(100, round(cal_totaal / cal_doel * 100)) if cal_doel else 0
    st.markdown(
        f'<div style="display:flex;justify-content:space-between;align-items:baseline;">'
        f'<span class="metric-big {"red" if over else "white"}">{cal_totaal}</span>'
        f'<span class="metric-sub">/ {cal_doel} kcal</span></div>'
        f'<div class="cal-bar-bg"><div class="cal-bar-fill {"cal-bar-over" if over else ""}" '
        f'style="width:{cal_pct}%"></div></div>'
        f'<div style="font-size:0.75rem;color:#555;margin-bottom:0.6rem;">'
        f'{"🔴 " + str(cal_totaal - cal_doel) + " kcal over doel" if over else f"Nog {cal_doel - cal_totaal} kcal over"}</div>',
        unsafe_allow_html=True,
    )
    with st.form("calorie_form", clear_on_submit=True, border=False):
        c_naam, c_kcal = st.columns([3, 1.3])
        naam_in = c_naam.text_input("Wat heb je gegeten?", placeholder="bijv. Kwark 150g",
                                    label_visibility="collapsed")
        kcal_in = c_kcal.number_input("Kcal", min_value=0, max_value=5000, value=0, step=10,
                                      label_visibility="collapsed")
        if st.form_submit_button("+ Toevoegen", use_container_width=True) and naam_in and kcal_in > 0:
            sla_calorie_op(naam_in, int(kcal_in))
            st.rerun()
    if innames:
        titel("Recent")
        for idx in range(len(innames) - 1, max(-1, len(innames) - 7), -1):
            i = innames[idx]
            c_i, c_x = st.columns([6, 1])
            c_i.markdown(
                f'<div style="display:flex;justify-content:space-between;font-size:0.82rem;padding-top:0.35rem">'
                f'<span style="color:#888">{esc(i["time"])} · {esc(i["item"])}</span>'
                f'<span style="color:#666;font-weight:600">{i["kcal"]}</span></div>',
                unsafe_allow_html=True,
            )
            if c_x.button("✕", key=f"del_cal_{idx}"):
                verwijder_calorie(idx)
                st.rerun()


# Context voor de AI, opgebouwd uit wat het dashboard al geladen heeft
def bouw_context() -> str:
    delen = []
    if whoop.get("recovery"):
        delen.append(f"Whoop: herstel {whoop['recovery']}%, HRV {whoop.get('hrv')}ms, "
                     f"rusthartslag {whoop.get('rhr')}bpm, slaap {whoop.get('sleep_hours')}u "
                     f"({whoop.get('sleep_quality')}% kwaliteit)")
    fmt = lambda ev: ", ".join(
        f"{e['start'].strftime('%H:%M') if hasattr(e['start'], 'hour') else 'hele dag'} {e['summary']}" for e in ev)
    delen.append(f"Agenda vandaag: {fmt(events) or 'leeg'}")
    delen.append(f"Agenda morgen: {fmt(morgen_events) or 'leeg'}")
    if doelen:
        delen.append("Actieve doelen:\n" + "\n".join(
            f"- {g['title']} ({g.get('progress', 0)}%, deadline {g.get('deadline', '?')})" for g in doelen))
    if open_todos:
        delen.append("Open todo's:\n" + "\n".join(
            f"- [{t.get('priority')}] {t['title']}" for t in open_todos))
    if commit:
        delen.append(f"Commitment vandaag: {commit['commitment']} "
                     f"({'nagekomen' if commit.get('achieved') else 'nog niet nagekomen'})")
    delen.append(f"Streak nagekomen commitments: {streak(growth)} dagen")
    delen.append(f"Portfolio: €{portfolio['totaal']:.0f} van €{portfolio['doel']} doel")
    delen.append(f"Calorieën: {cal_totaal}/{cal_doel} kcal")
    return "\n".join(delen)


with col5, st.container(border=True, key="card_chat"):
    c_t, c_clear = st.columns([5, 1])
    with c_t:
        titel("AI assistent")
    with c_clear:
        if st.session_state.chat and st.button("Wissen", key="chat_clear", use_container_width=True):
            st.session_state.chat = []
            st.rerun()

    chat_box = st.container(height=430, border=False)
    with chat_box:
        if not st.session_state.chat:
            st.markdown('<div class="no-events">Vraag iets, of kies een snelle actie hieronder.</div>',
                        unsafe_allow_html=True)
        for b in st.session_state.chat:
            with st.chat_message(b["rol"], avatar="🧑" if b["rol"] == "user" else "⚡"):
                st.markdown(b.get("label") or b["inhoud"])

    dagdeel = "ochtend" if now.hour < 17 else "avond"
    snelle_acties = {
        "🌅 Briefing": f"Geef me mijn {dagdeel}briefing: herstel en wat dat betekent voor vandaag, "
                      "agenda, de 3 belangrijkste focuspunten en aankomende deadlines.",
        "📋 Focus": "Wat zijn de 3 belangrijkste dingen die ik vandaag moet doen, op basis van mijn "
                   "doelen, todo's en agenda? Geef een concrete volgorde.",
        "💪 Training": "Geef een concreet trainingsadvies voor vandaag op basis van mijn Whoop-herstel "
                      "en wat er in mijn agenda staat.",
        "🎯 Doelen": "Hoe sta ik ervoor met mijn actieve doelen? Welke lopen achter en wat moet ik "
                    "de komende week prioriteren?",
    }
    for (label, prompt), kolom in zip(snelle_acties.items(), st.columns(len(snelle_acties))):
        if kolom.button(label, use_container_width=True, key=f"btn_{label}"):
            st.session_state.chat.append({"rol": "user", "inhoud": prompt, "label": label})
            st.session_state.pending = True

    if vraag := st.chat_input("Typ hier…", key="chat_in"):
        st.session_state.chat.append({"rol": "user", "inhoud": vraag})
        st.session_state.pending = True

    # Antwoord direct in de chatbox streamen
    if st.session_state.pop("pending", False):
        laatste = st.session_state.chat[-1]
        with chat_box:
            with st.chat_message("user", avatar="🧑"):
                st.markdown(laatste.get("label") or laatste["inhoud"])
            with st.chat_message("assistant", avatar="⚡"):
                antwoord = st.write_stream(stream_antwoord(bouw_context(), st.session_state.chat))
        st.session_state.chat.append({"rol": "assistant", "inhoud": antwoord or "…"})
