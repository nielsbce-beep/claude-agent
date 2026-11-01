"""
Gedeelde lees/schrijf-logica voor de lokale JSON-data van Life OS
(todo's, commitments, calorieën, portfolio, journal-samenvatting).
"""

import json
from datetime import date, datetime, timedelta
from pathlib import Path

DATA = Path(__file__).parent.parent / "data"
CALORIES_FILE = DATA / "calories.json"
TODOS_FILE = DATA / "todos.json"
GROWTH_FILE = DATA / "growth_log.json"
PORTFOLIO_FILE = DATA / "portfolio.json"
JOURNAL_FILE = DATA / "journal.json"

PRIO_ORDE = {"high": 0, "medium": 1, "low": 2}
STANDAARD_KCAL = 2500


def lees(pad: Path, standaard):
    try:
        return json.loads(pad.read_text(encoding="utf-8"))
    except (FileNotFoundError, json.JSONDecodeError):
        return standaard


def schrijf(pad: Path, data) -> None:
    pad.write_text(json.dumps(data, indent=2, ensure_ascii=False, default=str), encoding="utf-8")


# ── Todo's ─────────────────────────────────────────────────────────────────────

def todos() -> list[dict]:
    return lees(TODOS_FILE, {"todos": []}).get("todos", [])


def open_todos() -> list[dict]:
    return sorted((t for t in todos() if not t.get("done")),
                  key=lambda t: (PRIO_ORDE.get(t.get("priority"), 3), t.get("created_at", "")))


def todo_toggle(todo_id: str) -> None:
    data = lees(TODOS_FILE, {"todos": []})
    for t in data["todos"]:
        if t["id"] == todo_id:
            t["done"] = not t.get("done")
            t["done_at"] = date.today().isoformat() if t["done"] else None
    schrijf(TODOS_FILE, data)


def todo_toevoegen(titel: str, prio: str = "medium") -> dict:
    data = lees(TODOS_FILE, {"todos": []})
    nummers = [int(t["id"].split("_")[-1]) for t in data["todos"] if t["id"].split("_")[-1].isdigit()]
    todo = {
        "id": f"todo_{(max(nummers, default=0) + 1):03d}",
        "title": titel,
        "description": "",
        "priority": prio if prio in PRIO_ORDE else "medium",
        "done": False,
        "created_at": date.today().isoformat(),
    }
    data["todos"].append(todo)
    schrijf(TODOS_FILE, data)
    return todo


# ── Commitments (growth_log) ───────────────────────────────────────────────────

def growth_entries() -> list[dict]:
    return lees(GROWTH_FILE, {"entries": []}).get("entries", [])


def commitment_vandaag() -> dict | None:
    vandaag = date.today().isoformat()
    return next((e for e in reversed(growth_entries()) if e.get("date") == vandaag), None)


def commitment_zetten(tekst: str) -> None:
    data = lees(GROWTH_FILE, {"entries": []})
    vandaag = date.today().isoformat()
    data["entries"] = [e for e in data["entries"] if e.get("date") != vandaag]
    data["entries"].append({"date": vandaag, "commitment": tekst, "achieved": False})
    schrijf(GROWTH_FILE, data)


def commitment_toggle() -> None:
    data = lees(GROWTH_FILE, {"entries": []})
    vandaag = date.today().isoformat()
    for e in reversed(data["entries"]):
        if e.get("date") == vandaag:
            e["achieved"] = not e.get("achieved")
            break
    schrijf(GROWTH_FILE, data)


def streak() -> int:
    gehaald = {e["date"] for e in growth_entries() if e.get("achieved")}
    dag = date.today() if date.today().isoformat() in gehaald else date.today() - timedelta(days=1)
    n = 0
    while dag.isoformat() in gehaald:
        n += 1
        dag -= timedelta(days=1)
    return n


def commitment_historie(dagen: int = 14) -> list[dict]:
    """Per dag: 'achieved', 'missed' of 'none' (geen commitment)."""
    per_dag = {e["date"]: e for e in growth_entries()}
    uit = []
    for i in range(dagen - 1, -1, -1):
        d = (date.today() - timedelta(days=i)).isoformat()
        e = per_dag.get(d)
        uit.append({"date": d, "state": "none" if not e else "achieved" if e.get("achieved") else "missed"})
    return uit


# ── Calorieën ──────────────────────────────────────────────────────────────────

def calorieen() -> dict:
    dag = lees(CALORIES_FILE, {}).get(date.today().isoformat(), {"doel": STANDAARD_KCAL, "innames": []})
    return {"goal": dag.get("doel", STANDAARD_KCAL), "items": dag.get("innames", []),
            "total": sum(i["kcal"] for i in dag.get("innames", []))}


def calorie_toevoegen(item: str, kcal: int) -> None:
    data = lees(CALORIES_FILE, {})
    dag = data.setdefault(date.today().isoformat(), {"doel": STANDAARD_KCAL, "innames": []})
    dag["innames"].append({"item": item, "kcal": kcal, "time": datetime.now().strftime("%H:%M")})
    schrijf(CALORIES_FILE, data)


def calorie_verwijderen(index: int) -> None:
    data = lees(CALORIES_FILE, {})
    dag = data.get(date.today().isoformat())
    if dag and 0 <= index < len(dag["innames"]):
        dag["innames"].pop(index)
        schrijf(CALORIES_FILE, data)


def caloriedoel_zetten(doel: int) -> None:
    data = lees(CALORIES_FILE, {})
    data.setdefault(date.today().isoformat(), {"doel": doel, "innames": []})["doel"] = doel
    schrijf(CALORIES_FILE, data)


# ── Portfolio ──────────────────────────────────────────────────────────────────

def portfolio() -> dict:
    p = lees(PORTFOLIO_FILE, {})
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
    totaal = sum(onderdelen.values())
    doel = p.get("doel", {}).get("bedrag", 25000)
    deadline = p.get("doel", {}).get("deadline", "")
    # Simpele lineaire projectie (zonder rendement) naar de deadline
    try:
        maanden = max(0, (date.fromisoformat(deadline) - date.today()).days / 30.44)
    except ValueError:
        maanden = 0
    return {
        "total": round(totaal, 2),
        "parts": {k: round(v, 2) for k, v in onderdelen.items()},
        "goal": doel,
        "deadline": deadline,
        "monthly": round(per_maand),
        "projection": round(totaal + per_maand * maanden),
        "updated": p.get("last_updated", "?"),
        "top": sorted(h.get("aandelen", {}).get("posities", []),
                      key=lambda x: x.get("rendement_pct", 0), reverse=True)[:3],
    }


# ── Journal ────────────────────────────────────────────────────────────────────

def journal_entries(dagen: int = 30) -> list[dict]:
    grens = (date.today() - timedelta(days=dagen)).isoformat()
    entries = [e for e in lees(JOURNAL_FILE, {"entries": []}).get("entries", []) if e.get("date", "") >= grens]
    return sorted(entries, key=lambda e: e["date"], reverse=True)


def journal_opslaan(entry: dict) -> None:
    data = lees(JOURNAL_FILE, {"entries": []})
    data["entries"] = [e for e in data["entries"] if e.get("date") != entry["date"]]
    data["entries"].append(entry)
    schrijf(JOURNAL_FILE, data)
