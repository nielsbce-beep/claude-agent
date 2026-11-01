"""
Life OS — lokale webserver voor het dashboard.

  python server.py               → start en opent http://localhost:8765
  python server.py wachtwoord    → stel het inlogwachtwoord in (of wijzig het)

Op afstand: `tailscale serve --bg 8765` maakt hem bereikbaar op je eigen
tailnet (https://<pc>.<tailnet>.ts.net). De server zelf luistert alleen lokaal.
"""

import hashlib
import hmac
import json
import os
import secrets
import sys
import time
from datetime import date, datetime, timedelta
from pathlib import Path

import anthropic
from dotenv import load_dotenv, set_key

BASE = Path(__file__).parent
ENV_FILE = BASE / ".env"
load_dotenv(ENV_FILE, override=True)
sys.path.insert(0, str(BASE))

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from tools import life_data as ld
from tools.goals_store import get_active
from tools.calendar_tools import get_events
from tools.whoop_api import get_latest_recovery, get_latest_sleep

CHAT_MODEL = "claude-opus-5-5"
KALENDER = "Niels AI agenda"
WEB = BASE / "web"

app = FastAPI(title="Life OS", docs_url=None, redoc_url=None, openapi_url=None)
app.mount("/static", StaticFiles(directory=WEB), name="static")

ai = anthropic.Anthropic()


# ── Authenticatie ──────────────────────────────────────────────────────────────
# Wachtwoord als PBKDF2-hash in .env; sessie = HMAC-ondertekende cookie (90 dagen).

COOKIE = "lifeos_session"
SESSIE_DAGEN = 90
OPENBAAR = {"/login", "/api/login", "/manifest.webmanifest", "/static/login.css",
            "/static/icon.svg", "/static/icon-192.png", "/static/icon-512.png", "/static/apple-touch-icon.png"}


def hash_wachtwoord(wachtwoord: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    h = hashlib.pbkdf2_hmac("sha256", wachtwoord.encode(), bytes.fromhex(salt), 300_000).hex()
    return f"{salt}${h}"


def wachtwoord_klopt(wachtwoord: str) -> bool:
    opgeslagen = os.getenv("LIFEOS_PASSWORD_HASH", "")
    if "$" not in opgeslagen:
        return False
    salt, _ = opgeslagen.split("$", 1)
    return hmac.compare_digest(hash_wachtwoord(wachtwoord, salt), opgeslagen)


def geheim() -> bytes:
    s = os.getenv("LIFEOS_SECRET")
    if not s:
        s = secrets.token_hex(32)
        set_key(str(ENV_FILE), "LIFEOS_SECRET", s)
        os.environ["LIFEOS_SECRET"] = s
    return s.encode()


def maak_sessie() -> str:
    verloopt = str(int(time.time()) + SESSIE_DAGEN * 86400)
    return f"{verloopt}.{hmac.new(geheim(), verloopt.encode(), 'sha256').hexdigest()}"


def sessie_geldig(token: str | None) -> bool:
    if not token or "." not in token:
        return False
    verloopt, sig = token.split(".", 1)
    goed = hmac.new(geheim(), verloopt.encode(), "sha256").hexdigest()
    return hmac.compare_digest(sig, goed) and verloopt.isdigit() and int(verloopt) > time.time()


def wachtwoord_ingesteld() -> bool:
    return bool(os.getenv("LIFEOS_PASSWORD_HASH"))


def direct_lokaal(request: Request) -> bool:
    """Rechtstreeks vanaf deze pc — niet via een proxy zoals `tailscale serve`."""
    proxy = ("x-forwarded-for", "x-forwarded-host", "tailscale-user-login", "forwarded")
    return (request.client is not None and request.client.host in ("127.0.0.1", "::1")
            and not any(h in request.headers for h in proxy))


@app.middleware("http")
async def vereis_login(request: Request, call_next):
    pad = request.url.path
    # Zonder ingesteld wachtwoord: alleen toegang vanaf deze pc zelf
    if not wachtwoord_ingesteld() and direct_lokaal(request) and pad != "/login":
        return await call_next(request)
    if pad in OPENBAAR or sessie_geldig(request.cookies.get(COOKIE)):
        return await call_next(request)
    if pad.startswith("/api/"):
        return JSONResponse({"detail": "Niet ingelogd"}, status_code=401)
    return RedirectResponse("/login")


_mislukt: list[float] = []   # tijdstippen van mislukte pogingen (simpele brute-force rem)


class LoginIn(BaseModel):
    password: str = Field(max_length=200)


@app.get("/login")
def login_pagina(request: Request):
    if not wachtwoord_ingesteld() and direct_lokaal(request):
        return RedirectResponse("/")
    return FileResponse(WEB / "login.html")


@app.post("/api/login")
def api_login(l: LoginIn, request: Request):
    nu = time.time()
    _mislukt[:] = [t for t in _mislukt if nu - t < 900]
    if len(_mislukt) >= 10:
        raise HTTPException(429, "Te veel pogingen — probeer het over een kwartier opnieuw.")
    if not os.getenv("LIFEOS_PASSWORD_HASH"):
        raise HTTPException(503, "Nog geen wachtwoord ingesteld. Draai op je pc: python server.py wachtwoord")
    if not wachtwoord_klopt(l.password):
        _mislukt.append(nu)
        time.sleep(1)
        raise HTTPException(401, "Onjuist wachtwoord")
    https = request.headers.get("x-forwarded-proto") == "https" or request.url.scheme == "https"
    resp = JSONResponse({"ok": True})
    resp.set_cookie(COOKIE, maak_sessie(), max_age=SESSIE_DAGEN * 86400,
                    httponly=True, samesite="lax", secure=https)
    return resp


@app.post("/api/logout")
def api_logout():
    resp = JSONResponse({"ok": True})
    resp.delete_cookie(COOKIE)
    return resp


@app.get("/manifest.webmanifest")
def manifest():
    return FileResponse(WEB / "manifest.webmanifest", media_type="application/manifest+json")


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
        "goals_completed": sum(1 for g in gs.get_all() if g.get("status") == "completed"),
        "todos": ld.open_todos(),
        "commitment": ld.commitment_vandaag(),
        "streak": ld.streak(),
        "commit_history": ld.commitment_historie(14),
        "portfolio": ld.portfolio(),
        "calories": ld.calorieen(),
        "auth": wachtwoord_ingesteld(),
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


class TodoEdit(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    priority: str | None = None
    description: str | None = Field(default=None, max_length=2000)


@app.patch("/api/todos/{todo_id}")
def api_todo_edit(todo_id: str, t: TodoEdit):
    ld.todo_bijwerken(todo_id, (t.title or "").strip() or None, t.priority, t.description)
    return {"ok": True}


@app.delete("/api/todos/{todo_id}")
def api_todo_delete(todo_id: str):
    ld.todo_verwijderen(todo_id)
    return {"ok": True}


# ── Doelen bewerken (via tools/goals_store) ────────────────────────────────────

from tools import goals_store as gs

CATEGORIEEN = ["studie", "sport", "financieel", "persoonlijk", "werk", "gezondheid"]


def goal_detail(goal_id: str) -> dict:
    g = gs.get_goal(goal_id)
    if not g:
        raise HTTPException(404, "Doel niet gevonden")
    return {**g, "check_ins": g.get("check_ins", [])[-5:][::-1]}


@app.get("/api/goals")
def api_goals(status: str = "active"):
    return [{"id": g["id"], "title": g["title"], "category": g.get("category"), "progress": g.get("progress", 0),
             "deadline": g.get("deadline"), "completed_at": g.get("completed_at")}
            for g in gs.get_all() if g.get("status") == status]


@app.get("/api/goals/meta")
def api_goals_meta():
    bestaand = {g.get("category") for g in gs.get_all() if g.get("category")}
    return {"categories": sorted(set(CATEGORIEEN) | bestaand)}


@app.get("/api/goals/{goal_id}")
def api_goal(goal_id: str):
    return goal_detail(goal_id)


class GoalIn(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=3000)
    category: str = Field(default="persoonlijk", max_length=40)
    deadline: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    milestones: list[str] = []


@app.post("/api/goals")
def api_goal_add(g: GoalIn):
    nieuw = gs.add_goal(g.title.strip(), g.description.strip(), g.category.strip().lower(), g.deadline,
                        [m.strip() for m in g.milestones if m.strip()])
    return goal_detail(nieuw["id"])


class GoalEdit(BaseModel):
    title: str | None = Field(default=None, max_length=200)
    description: str | None = Field(default=None, max_length=3000)
    category: str | None = Field(default=None, max_length=40)
    deadline: str | None = Field(default=None, pattern=r"^\d{4}-\d{2}-\d{2}$")
    status: str | None = Field(default=None, pattern=r"^(active|completed|archived)$")


@app.patch("/api/goals/{goal_id}")
def api_goal_edit(goal_id: str, g: GoalEdit):
    if not gs.update_goal(goal_id, **g.model_dump()):
        raise HTTPException(404, "Doel niet gevonden")
    return goal_detail(goal_id)


class CheckIn(BaseModel):
    progress: int = Field(ge=0, le=100)
    note: str = Field(default="", max_length=2000)


@app.post("/api/goals/{goal_id}/checkin")
def api_goal_checkin(goal_id: str, c: CheckIn):
    goal_detail(goal_id)
    gs.log_check_in(goal_id, c.note.strip() or "Voortgang bijgewerkt via Life OS", c.progress)
    return goal_detail(goal_id)


class MijlpaalIn(BaseModel):
    text: str = Field(min_length=1, max_length=300)


@app.post("/api/goals/{goal_id}/milestones")
def api_ms_add(goal_id: str, m: MijlpaalIn):
    if not gs.add_milestone(goal_id, m.text.strip()):
        raise HTTPException(404, "Doel niet gevonden")
    return goal_detail(goal_id)


@app.post("/api/goals/{goal_id}/milestones/{index}/toggle")
def api_ms_toggle(goal_id: str, index: int):
    if not gs.toggle_milestone(goal_id, index):
        raise HTTPException(404, "Mijlpaal niet gevonden")
    return goal_detail(goal_id)


@app.delete("/api/goals/{goal_id}/milestones/{index}")
def api_ms_delete(goal_id: str, index: int):
    if not gs.remove_milestone(goal_id, index):
        raise HTTPException(404, "Mijlpaal niet gevonden")
    return goal_detail(goal_id)


# ── Portfolio bewerken ─────────────────────────────────────────────────────────

@app.get("/api/portfolio/raw")
def api_portfolio_raw():
    return ld.portfolio_ruw()


class Aandeel(BaseModel):
    ticker: str = Field(default="", max_length=12)
    naam: str = Field(default="", max_length=80)
    waarde: float = Field(ge=0, le=10_000_000)
    rendement_pct: float = Field(default=0, ge=-100, le=10_000)


class PortfolioIn(BaseModel):
    bnd: float = Field(ge=0, le=10_000_000)
    goud: float = Field(ge=0, le=10_000_000)
    goud_aankoop: float = Field(ge=0, le=10_000_000)
    bitcoin: float = Field(ge=0, le=10_000_000)
    bitcoin_aankoop: float = Field(ge=0, le=10_000_000)
    aandelen: list[Aandeel]
    inleg: dict[str, float]
    doel: dict


@app.put("/api/portfolio")
def api_portfolio_update(p: PortfolioIn):
    return ld.portfolio_bijwerken(p.model_dump())


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


@app.put("/api/calories/goal")
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


def stel_wachtwoord_in() -> None:
    from getpass import getpass
    pw = getpass("Nieuw Life OS-wachtwoord (min. 10 tekens): ")
    if len(pw) < 10:
        sys.exit("Te kort — kies minimaal 10 tekens.")
    if getpass("Herhaal: ") != pw:
        sys.exit("Wachtwoorden komen niet overeen.")
    set_key(str(ENV_FILE), "LIFEOS_PASSWORD_HASH", hash_wachtwoord(pw))
    set_key(str(ENV_FILE), "LIFEOS_SECRET", secrets.token_hex(32))   # logt alle apparaten uit
    print("✓ Wachtwoord opgeslagen. Herstart de server als die al draait.")


if __name__ == "__main__":
    if sys.argv[1:2] == ["wachtwoord"]:
        stel_wachtwoord_in()
        sys.exit(0)

    import threading
    import webbrowser
    import uvicorn

    if not os.getenv("LIFEOS_PASSWORD_HASH"):
        print("⚠️  Nog geen wachtwoord ingesteld — draai eerst: python server.py wachtwoord")

    poort = 8765
    if "--no-browser" not in sys.argv:
        threading.Timer(1.2, lambda: webbrowser.open(f"http://localhost:{poort}")).start()
    uvicorn.run(app, host="127.0.0.1", port=poort, log_level="warning")
