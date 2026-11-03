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
BOOKS_FILE = DATA / "books.json"

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

def _laatste_doel(data: dict) -> int:
    """Het meest recent ingestelde caloriedoel loopt door naar nieuwe dagen."""
    dagen = sorted(k for k in data if isinstance(data[k], dict) and "doel" in data[k])
    return data[dagen[-1]]["doel"] if dagen else STANDAARD_KCAL


def calorieen() -> dict:
    data = lees(CALORIES_FILE, {})
    dag = data.get(date.today().isoformat(), {"doel": _laatste_doel(data), "innames": []})
    return {"goal": dag.get("doel", STANDAARD_KCAL), "items": dag.get("innames", []),
            "total": sum(i["kcal"] for i in dag.get("innames", []))}


def calorie_toevoegen(item: str, kcal: int) -> None:
    data = lees(CALORIES_FILE, {})
    dag = data.setdefault(date.today().isoformat(), {"doel": _laatste_doel(data), "innames": []})
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
        "Vanguard": h.get("vanguard", {}).get("waarde", 0),
        "Goud": h.get("goud", {}).get("waarde", 0),
        "Bitcoin": h.get("bitcoin", {}).get("waarde", 0),
    }
    inleg = p.get("inleg", {})
    per_maand = inleg.get("bnd_maand", 0) + inleg.get("goud_maand", 0) + \
        (inleg.get("aandelen_week", 0) + inleg.get("vanguard_week", 0) + inleg.get("bitcoin_week", 0)) * 52 / 12
    totaal = sum(onderdelen.values())
    historie = list(p.get("historie", []))
    if not historie or historie[-1]["datum"] != p.get("last_updated"):
        historie.append({"datum": p.get("last_updated", date.today().isoformat()), "totaal": round(totaal, 2)})
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
        "history": historie[-24:],
    }


def portfolio_ruw() -> dict:
    return lees(PORTFOLIO_FILE, {})


def portfolio_ververs_koersen() -> dict:
    """Haal live koersen op (Yahoo Finance) voor losse aandelen + Vanguard ETF, net als Trading 212."""
    from tools.stock_prices import ververs_posities, ververs_positie

    p = lees(PORTFOLIO_FILE, {})
    h = p.setdefault("holdings", {})
    vandaag = date.today().isoformat()
    updates = p.setdefault("updates", [])

    aandelen = h.setdefault("aandelen", {"naam": "Losse aandelen", "posities": []})
    oud_aandelen = sum(x.get("waarde", 0) for x in aandelen["posities"])
    ververs_posities(aandelen["posities"])
    nieuw_aandelen = sum(x.get("waarde", 0) for x in aandelen["posities"])
    if round(oud_aandelen, 2) != round(nieuw_aandelen, 2):
        updates.append({"datum": vandaag, "component": "aandelen", "oud": round(oud_aandelen, 2), "nieuw": round(nieuw_aandelen, 2)})

    vg = h.get("vanguard")
    if vg and vg.get("aantal"):
        oud_vg = vg.get("waarde", 0)
        ververs_positie(vg)
        if round(oud_vg, 2) != round(vg.get("waarde", 0), 2):
            updates.append({"datum": vandaag, "component": "vanguard", "oud": round(oud_vg, 2), "nieuw": round(vg.get("waarde", 0), 2)})

    p["last_updated"] = vandaag
    totaal = (h.get("bnd", {}).get("waarde", 0) + h.get("goud", {}).get("waarde", 0)
              + h.get("bitcoin", {}).get("waarde", 0) + h.get("vanguard", {}).get("waarde", 0)
              + sum(x.get("waarde", 0) for x in aandelen["posities"]))
    historie = p.setdefault("historie", [])
    historie[:] = [x for x in historie if x["datum"] != vandaag] + [{"datum": vandaag, "totaal": round(totaal, 2)}]
    schrijf(PORTFOLIO_FILE, p)
    return portfolio()


def _rendement(waarde: float, aankoop: float) -> float:
    return round((waarde - aankoop) / aankoop * 100, 2) if aankoop else 0.0


def portfolio_bijwerken(nieuw: dict) -> dict:
    """
    Werk portfolio.json bij vanuit het dashboard-formulier.
    nieuw = {bnd, goud, goud_aankoop, bitcoin, bitcoin_aankoop,
             aandelen: [{ticker, naam, waarde, rendement_pct}], inleg: {...}, doel: {bedrag, deadline}}
    """
    p = lees(PORTFOLIO_FILE, {})
    h = p.setdefault("holdings", {})
    vandaag = date.today().isoformat()
    updates = p.setdefault("updates", [])

    def log(component, oud, nieuw_w):
        if round(oud or 0, 2) != round(nieuw_w or 0, 2):
            updates.append({"datum": vandaag, "component": component, "oud": oud, "nieuw": nieuw_w})

    # Brand New Day: totaal bijwerken, posities proportioneel meeschalen (weging blijft gelijk)
    bnd = h.setdefault("bnd", {"naam": "Brand New Day", "waarde": 0, "posities": []})
    if "bnd" in nieuw:
        log("bnd", bnd.get("waarde"), nieuw["bnd"])
        oud = bnd.get("waarde") or 0
        if oud:
            factor = nieuw["bnd"] / oud
            for pos in bnd.get("posities", []):
                pos["waarde"] = round(pos["waarde"] * factor, 2)
        bnd["waarde"] = round(nieuw["bnd"], 2)

    for sleutel, naam in (("goud", "Goud"), ("bitcoin", "Bitcoin")):
        if sleutel in nieuw:
            item = h.setdefault(sleutel, {"naam": naam, "waarde": 0, "aankoopwaarde": 0, "rendement_pct": 0})
            log(sleutel, item.get("waarde"), nieuw[sleutel])
            item["waarde"] = round(nieuw[sleutel], 2)
            if nieuw.get(f"{sleutel}_aankoop") is not None:
                item["aankoopwaarde"] = round(nieuw[f"{sleutel}_aankoop"], 2)
            item["rendement_pct"] = _rendement(item["waarde"], item.get("aankoopwaarde", 0))

    if "vanguard" in nieuw:
        item = h.setdefault("vanguard", {"naam": "Vanguard FTSE All-World (Acc)", "ticker": "", "aantal": 0,
                                          "waarde": 0, "aankoopwaarde": 0, "rendement_pct": 0})
        log("vanguard", item.get("waarde"), nieuw["vanguard"])
        item["waarde"] = round(nieuw["vanguard"], 2)
        if nieuw.get("vanguard_aankoop") is not None:
            item["aankoopwaarde"] = round(nieuw["vanguard_aankoop"], 2)
        if nieuw.get("vanguard_ticker") is not None:
            item["ticker"] = nieuw["vanguard_ticker"].upper().strip()
        if nieuw.get("vanguard_aantal") is not None:
            item["aantal"] = round(float(nieuw["vanguard_aantal"]), 6)
        item["rendement_pct"] = _rendement(item["waarde"], item.get("aankoopwaarde", 0))

    if "aandelen" in nieuw:
        oud_tot = sum(x.get("waarde", 0) for x in h.get("aandelen", {}).get("posities", []))
        posities = [
            {"ticker": a.get("ticker", "").upper().strip(), "naam": a.get("naam", "").strip(),
             "aantal": round(float(a.get("aantal") or 0), 6),
             "waarde": round(float(a.get("waarde") or 0), 2), "rendement_pct": round(float(a.get("rendement_pct") or 0), 2)}
            for a in nieuw["aandelen"] if (a.get("ticker") or a.get("naam"))
        ]
        tot = sum(x["waarde"] for x in posities) or 1
        for x in posities:
            x["weging"] = round(x["waarde"] / tot * 100, 2)
        h.setdefault("aandelen", {"naam": "Losse aandelen"})["posities"] = posities
        log("aandelen", round(oud_tot, 2), round(sum(x["waarde"] for x in posities), 2))

    if "inleg" in nieuw:
        p["inleg"] = {k: float(v) for k, v in nieuw["inleg"].items()}
    if "doel" in nieuw:
        p["doel"] = {"bedrag": float(nieuw["doel"]["bedrag"]), "deadline": nieuw["doel"]["deadline"]}

    p["last_updated"] = vandaag
    totaal = (h.get("bnd", {}).get("waarde", 0) + h.get("goud", {}).get("waarde", 0)
              + h.get("bitcoin", {}).get("waarde", 0)
              + sum(x.get("waarde", 0) for x in h.get("aandelen", {}).get("posities", [])))
    historie = p.setdefault("historie", [])
    historie[:] = [x for x in historie if x["datum"] != vandaag] + [{"datum": vandaag, "totaal": round(totaal, 2)}]
    schrijf(PORTFOLIO_FILE, p)
    return portfolio()


# ── Todo's bewerken ────────────────────────────────────────────────────────────

def todo_bijwerken(todo_id: str, titel: str | None, prio: str | None, beschrijving: str | None) -> None:
    data = lees(TODOS_FILE, {"todos": []})
    for t in data["todos"]:
        if t["id"] == todo_id:
            if titel:
                t["title"] = titel
            if prio in PRIO_ORDE:
                t["priority"] = prio
            if beschrijving is not None:
                t["description"] = beschrijving
    schrijf(TODOS_FILE, data)


def todo_verwijderen(todo_id: str) -> None:
    data = lees(TODOS_FILE, {"todos": []})
    data["todos"] = [t for t in data["todos"] if t["id"] != todo_id]
    schrijf(TODOS_FILE, data)


# ── Boekenlijst ────────────────────────────────────────────────────────────────

def boeken() -> list[dict]:
    return lees(BOOKS_FILE, {"books": []}).get("books", [])


def boek_toevoegen(titel: str) -> dict:
    data = lees(BOOKS_FILE, {"books": []})
    nummers = [int(b["id"].split("_")[1]) for b in data["books"] if b["id"].startswith("boek_")]
    boek = {"id": f"boek_{(max(nummers, default=0) + 1):02d}", "titel": titel.strip(), "gelezen": False, "notities": ""}
    data["books"].append(boek)
    schrijf(BOOKS_FILE, data)
    return boek


def boek_toggle(boek_id: str) -> None:
    data = lees(BOOKS_FILE, {"books": []})
    for b in data["books"]:
        if b["id"] == boek_id:
            b["gelezen"] = not b.get("gelezen", False)
            break
    schrijf(BOOKS_FILE, data)


def boek_bijwerken(boek_id: str, titel: str | None, notities: str | None) -> None:
    data = lees(BOOKS_FILE, {"books": []})
    for b in data["books"]:
        if b["id"] == boek_id:
            if titel:
                b["titel"] = titel.strip()
            if notities is not None:
                b["notities"] = notities.strip()
    schrijf(BOOKS_FILE, data)


def boek_verwijderen(boek_id: str) -> None:
    data = lees(BOOKS_FILE, {"books": []})
    data["books"] = [b for b in data["books"] if b["id"] != boek_id]
    schrijf(BOOKS_FILE, data)


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
