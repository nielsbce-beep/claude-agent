"""
Life OS — lokale webserver voor het dashboard.
Start met:  python server.py      → opent http://localhost:8765
"""

import json
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path

import anthropic
from dotenv import load_dotenv

BASE = Path(__file__).parent
load_dotenv(BASE / ".env", override=True)
sys.path.insert(0, str(BASE))

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from tools import life_data as ld
from tools.goals_store import get_active
from tools.calendar_tools import get_events
from tools.whoop_api import get_latest_recovery, get_latest_sleep

CHAT_MODEL = "claude-opus-5-5"
KALENDER = "Niels AI agenda"
WEB = BASE / "web"

app = FastAPI(title="Life OS")
app.mount("/static", StaticFiles(directory=WEB), name="static")

ai = anthropic.Anthropic()


# ── Kleine TTL-cache voor trage externe bronnen (Whoop, iCloud) ────────────────

_cache: dict[str, tuple[float, object]] = {}


def gecached(sleutel: str, ttl: int, functie):
    nu = time.time()
    if sleutel in _cache and nu - _cache[sleutel][0] < ttl:
        return _cache[sleutel][1]
    waarde = functie()
    _cache[sleutel] = (nu, waarde)
    return waarde


def whoop() -> dict | None:
    def laad():
        try:
            score = get_latest_recovery().get("score", {})
            s_score = get_latest_sleep().get("score", {})
            if not score.get("recovery_score"):
                return None
            # Whoop v2: duur staat onder stage_summary; echte slaap = in bed − wakker
            stages = s_score.get("stage_summary", s_score)
            slaap_ms = stages.get("total_in_bed_time_milli", 0) - stages.get("total_awake_time_milli", 0)
            return {
                "recovery": round(score.get("recovery_score", 0)),
                "hrv": round(score.get("hrv_rmssd_milli", 0)),
                "rhr": round(score.get("resting_heart_rate", 0)),
                "sleep_hours": round(slaap_ms / 3_600_000, 1),
                "sleep_quality": round(s_score.get("sleep_performance_percentage", 0)),
            }
        except Exception:
            return None
    return gecached("whoop", 300, laad)


def agenda(dag: date) -> list[dict]:
    def laad():
        try:
            start = datetime.combine(dag, datetime.min.time())
            events = get_events(start, start.replace(hour=23, minute=59), calendar_name=KALENDER)
        except Exception:
            return []
        uit = []
        for e in events:
            s, eind = e.get("start"), e.get("end")
            heeft_tijd = hasattr(s, "hour")
            uit.append({
                "title": str(e.get("summary", "")),
                "start": s.strftime("%H:%M") if heeft_tijd else None,
                "end": eind.strftime("%H:%M") if hasattr(eind, "hour") else None,
                "allday": not heeft_tijd,
            })
        return sorted(uit, key=lambda x: x["start"] or "")
    return gecached(f"agenda-{dag}", 300, laad)


def doelen() -> list[dict]:
    try:
        actief = get_active()
    except Exception:
        return []
    uit = []
    for g in actief:
        try:
            dagen = (date.fromisoformat(g["deadline"]) - date.today()).days
        except Exception:
            dagen = None
        ms = g.get("milestones", [])
        uit.append({
            "id": g.get("id"),
            "title": g["title"],
            "category": g.get("category", ""),
            "progress": g.get("progress", 0),
            "deadline": g.get("deadline"),
            "days_left": dagen,
            "milestones_done": sum(1 for m in ms if m.get("done")),
            "milestones_total": len(ms),
            "next_milestone": next((m["text"] for m in ms if not m.get("done")), None),
        })
    return sorted(uit, key=lambda g: (g["days_left"] is None, g["days_left"] or 0))


# ── Overzicht ──────────────────────────────────────────────────────────────────

def overzicht() -> dict:
    journal = ld.journal_entries(30)
    return {
        "today": date.today().isoformat(),
        "whoop": whoop(),
        "agenda": {"today": agenda(date.today()), "tomorrow": agenda(date.today() + timedelta(days=1))},
        "goals": doelen(),
        "todos": ld.open_todos(),
        "commitment": ld.commitment_vandaag(),
        "streak": ld.streak(),
        "commit_history": ld.commitment_historie(14),
        "portfolio": ld.portfolio(),
        "calories": ld.calorieen(),
        "journal": {
            "latest": journal[0] if journal else None,
            "today_written": bool(journal) and journal[0]["date"] == date.today().isoformat(),
            "moods": [{"date": e["date"], "mood": e.get("mood"), "energie": e.get("energie")} for e in journal],
        },
    }


@app.get("/")
def index():
    return FileResponse(WEB / "index.html")


@app.get("/api/overview")
def api_overview():
    return overzicht()


@app.post("/api/refresh")
def api_refresh():
    _cache.clear()
    return overzicht()


# ── Todo's / commitment / calorieën ────────────────────────────────────────────

class TodoIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    priority: str = "medium"


@app.post("/api/todos")
def api_todo_add(t: TodoIn):
    return ld.todo_toevoegen(t.title.strip(), t.priority)


@app.post("/api/todos/{todo_id}/toggle")
def api_todo_toggle(todo_id: str):
    ld.todo_toggle(todo_id)
    return {"ok": True}


class TekstIn(BaseModel):
    text: str = Field(min_length=1, max_length=5000)


@app.post("/api/commitment")
def api_commit(c: TekstIn):
    ld.commitment_zetten(c.text.strip())
    return {"ok": True}


@app.post("/api/commitment/toggle")
def api_commit_toggle():
    ld.commitment_toggle()
    return {"ok": True, "streak": ld.streak()}


class CalorieIn(BaseModel):
    item: str = Field(min_length=1, max_length=120)
    kcal: int = Field(gt=0, le=5000)


@app.post("/api/calories")
def api_cal_add(c: CalorieIn):
    ld.calorie_toevoegen(c.item.strip(), c.kcal)
    return ld.calorieen()


@app.delete("/api/calories/{index}")
def api_cal_del(index: int):
    ld.calorie_verwijderen(index)
    return ld.calorieen()


class DoelIn(BaseModel):
    goal: int = Field(gt=500, le=8000)


@app.post("/api/calories/goal")
def api_cal_goal(d: DoelIn):
    ld.caloriedoel_zetten(d.goal)
    return ld.calorieen()


# ── Journal (hergebruikt journal_agent) ────────────────────────────────────────

@app.get("/api/journal")
def api_journal():
    return ld.journal_entries(60)


@app.post("/api/journal")
def api_journal_write(j: TekstIn):
    import journal_agent
    vandaag = date.today().isoformat()
    bestaand = next((e for e in ld.journal_entries(1) if e["date"] == vandaag), None)
    raw = f"{bestaand['raw']}\n\n{j.text.strip()}" if bestaand else j.text.strip()
    meta = journal_agent._extract_metadata(raw)
    entry = {
        "date": vandaag,
        "timestamp": datetime.now().isoformat(),
        "raw": raw,
        "mood": meta.get("mood", "?"),
        "energie": meta.get("energie", "?"),
        "wins": meta.get("wins", []),
        "blockers": meta.get("blockers", []),
        "tags": meta.get("tags", []),
        "kern": meta.get("kern", ""),
    }
    ld.journal_opslaan(entry)
    return entry


@app.post("/api/journal/question")
def api_journal_question(j: TekstIn):
    import journal_agent
    return {"question": journal_agent._follow_up_question(j.text, [{"role": "user", "content": j.text}])}


@app.post("/api/journal/patterns")
def api_journal_patterns():
    import journal_agent
    entries = ld.journal_entries(14)
    return {"text": journal_agent._detect_patterns(entries), "count": len(entries)}


# ── Board meeting (hergebruikt board.py + agents/) ─────────────────────────────

@app.get("/api/board/agents")
def api_board_agents():
    import board
    return [{"name": a.name, "emoji": a.emoji} for a in board.BOARD]


class BoardIn(BaseModel):
    question: str = Field(min_length=3, max_length=2000)
    agent: str | None = None   # één specifieke agent, of None voor het hele board


@app.post("/api/board")
def api_board(b: BoardIn):
    import board

    def events():
        leden = board.nieuw_board()
        if b.agent:
            leden = [a for a in leden if a.name.lower() == b.agent.lower()]
            if not leden:
                yield json.dumps({"type": "error", "text": "Onbekende agent"}) + "\n"
                return
        antwoorden = []
        for agent in leden:
            yield json.dumps({"type": "thinking", "name": agent.name}) + "\n"
            try:
                tekst = agent.respond(b.question, board_context=antwoorden or None)
            except Exception as e:
                tekst = f"⚠️ Fout: {e}"
            antwoorden.append((agent.name, tekst))
            yield json.dumps({"type": "agent", "name": agent.name, "emoji": agent.emoji, "text": tekst}) + "\n"
        if len(leden) > 1:
            yield json.dumps({"type": "thinking", "name": "Voorzitter"}) + "\n"
            try:
                tekst = board.consensus(b.question, antwoorden)
            except Exception as e:
                tekst = f"⚠️ Fout: {e}"
            yield json.dumps({"type": "consensus", "text": tekst}) + "\n"
        yield json.dumps({"type": "done"}) + "\n"

    return StreamingResponse(events(), media_type="application/x-ndjson")


# ── AI-chat (streaming) ────────────────────────────────────────────────────────

SYSTEEM = (
    "Je bent Niels' persoonlijke life-coach en assistent in zijn Life OS-dashboard. "
    "Je spreekt altijd Nederlands. Je bent direct, concreet en motiverend, zonder onnodige intro's. "
    "Gebruik de actuele data hieronder voor gepersonaliseerd advies. Houd antwoorden compact; "
    "gebruik korte lijstjes en **vet** voor kernpunten waar dat helpt."
)


def context_tekst(o: dict) -> str:
    d = []
    w = o["whoop"]
    if w:
        d.append(f"Whoop: herstel {w['recovery']}%, HRV {w['hrv']}ms, rusthartslag {w['rhr']}bpm, "
                 f"slaap {w['sleep_hours']}u ({w['sleep_quality']}%)")
    fmt = lambda ev: ", ".join(f"{e['start'] or 'hele dag'} {e['title']}" for e in ev) or "leeg"
    d.append(f"Agenda vandaag: {fmt(o['agenda']['today'])}")
    d.append(f"Agenda morgen: {fmt(o['agenda']['tomorrow'])}")
    if o["goals"]:
        d.append("Actieve doelen:\n" + "\n".join(
            f"- {g['title']} ({g['progress']}%, deadline {g['deadline']}, volgende mijlpaal: {g['next_milestone']})"
            for g in o["goals"]))
    if o["todos"]:
        d.append("Open todo's:\n" + "\n".join(f"- [{t['priority']}] {t['title']}" for t in o["todos"]))
    c = o["commitment"]
    if c:
        d.append(f"Commitment vandaag: {c['commitment']} ({'nagekomen' if c.get('achieved') else 'nog open'})")
    d.append(f"Streak nagekomen commitments: {o['streak']} dagen")
    p = o["portfolio"]
    d.append(f"Portfolio: €{p['total']:.0f} van €{p['goal']} (deadline {p['deadline']}, inleg ~€{p['monthly']}/mnd)")
    cal = o["calories"]
    d.append(f"Calorieën vandaag: {cal['total']}/{cal['goal']} kcal")
    j = o["journal"]["latest"]
    if j:
        d.append(f"Laatste journal ({j['date']}): mood {j.get('mood')}, energie {j.get('energie')} — {j.get('kern')}")
    return "\n".join(d)


class ChatIn(BaseModel):
    messages: list[dict]


@app.post("/api/chat")
def api_chat(c: ChatIn):
    berichten = [{"role": m["role"], "content": m["content"]}
                 for m in c.messages if m.get("role") in ("user", "assistant") and m.get("content")]
    if not berichten or berichten[-1]["role"] != "user":
        raise HTTPException(400, "Laatste bericht moet van de gebruiker zijn")
    systeem = f"{SYSTEEM}\n\nVandaag: {date.today().isoformat()}, {datetime.now():%H:%M}\n\nActuele data:\n{context_tekst(overzicht())}"

    def stream():
        try:
            with ai.beta.messages.stream(
                model=CHAT_MODEL,
                max_tokens=16000,
                system=systeem,
                output_config={"effort": "medium"},
                messages=berichten,
                # Bij een (onterechte) weigering neemt automatisch een ander model het over
                betas=["server-side-fallback-2026-07-01"],
                extra_body={"fallbacks": "default"},
            ) as s:
                yield from s.text_stream
                if s.get_final_message().stop_reason == "refusal":
                    yield "\n\n_(Claude kon deze vraag niet beantwoorden.)_"
        except anthropic.APIConnectionError:
            yield "⚠️ Geen verbinding met de Anthropic API."
        except anthropic.AuthenticationError:
            yield "⚠️ Ongeldige API-sleutel — controleer ANTHROPIC_API_KEY in .env."
        except anthropic.RateLimitError:
            yield "⚠️ Rate limit bereikt, probeer het zo opnieuw."
        except anthropic.APIStatusError as e:
            yield f"⚠️ API-fout ({e.status_code}): {e.message}"

    return StreamingResponse(stream(), media_type="text/plain; charset=utf-8")


if __name__ == "__main__":
    import threading
    import webbrowser
    import uvicorn

    poort = 8765
    if "--no-browser" not in sys.argv:
        threading.Timer(1.2, lambda: webbrowser.open(f"http://localhost:{poort}")).start()
    uvicorn.run(app, host="127.0.0.1", port=poort, log_level="warning")
