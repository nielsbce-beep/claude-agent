"""
Wekelijkse review — elke zondag automatisch of handmatig.
Combineert goals, growth log, Whoop history en journal tot een
concreet weekplan met kleine stappen per doel.
"""
import sys
import json
import anthropic
from datetime import datetime, date, timedelta
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

sys.stdout.reconfigure(encoding="utf-8")

from tools.goals_store import get_all, get_active
from tools.whoop_history import get_recovery_trend, get_sleep_trend, get_training_summary
from journal_agent import context_voor_agents as _journal_context

client = anthropic.Anthropic()
MODEL  = "claude-sonnet-4-6"
TODAY  = datetime.now().strftime("%A %d %B %Y")
W      = 57

GROWTH_LOG  = Path(__file__).parent / "data" / "growth_log.json"
REVIEWS_LOG = Path(__file__).parent / "data" / "weekly_reviews.json"


# ── Persistence ────────────────────────────────────────────────────────────────

def _load_growth_log() -> dict:
    if GROWTH_LOG.exists():
        return json.loads(GROWTH_LOG.read_text(encoding="utf-8"))
    return {"entries": []}


def _load_reviews() -> dict:
    if REVIEWS_LOG.exists():
        return json.loads(REVIEWS_LOG.read_text(encoding="utf-8"))
    return {"reviews": []}


def _save_review(review: dict):
    data = _load_reviews()
    data["reviews"].append(review)
    REVIEWS_LOG.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8"
    )


# ── Data builders ──────────────────────────────────────────────────────────────

def _growth_log_week() -> dict:
    data  = _load_growth_log()
    week_ago = (date.today() - timedelta(days=7)).isoformat()
    entries  = [e for e in data["entries"] if e["date"] >= week_ago]
    total    = len(entries)
    kept     = sum(1 for e in entries if e["achieved"] is True)
    missed   = sum(1 for e in entries if e["achieved"] is False)
    open_    = sum(1 for e in entries if e["achieved"] is None)
    return {"total": total, "kept": kept, "missed": missed, "open": open_, "entries": entries}


def _bar(value: int, width: int = 16) -> str:
    if value is None:
        return "░" * width
    filled = int(value / 100 * width)
    return "█" * filled + "░" * (width - filled)


def _goals_context_full() -> str:
    goals = get_all()
    today = date.today()
    lines = []
    for g in goals:
        done  = sum(1 for m in g["milestones"] if m["done"])
        total = len(g["milestones"])
        try:
            days_left = (date.fromisoformat(g["deadline"]) - today).days
            deadline_str = f"{g['deadline']} ({days_left}d)"
        except Exception:
            deadline_str = g.get("deadline", "?")
        last = g["check_ins"][-1]["date"][:10] if g["check_ins"] else "nooit"
        open_ms = [m["text"] for m in g["milestones"] if not m["done"]]
        lines.append(
            f"[{g['id']}] [{g['category']}] {g['title']}\n"
            f"  Voortgang: {g['progress']}% | Mijlpalen: {done}/{total} | "
            f"Deadline: {deadline_str} | Check-in: {last}\n"
            f"  Open mijlpalen: {', '.join(open_ms[:3]) if open_ms else 'geen'}"
        )
    return "\n\n".join(lines)


# ── AI generators ──────────────────────────────────────────────────────────────

def _generate_weekly_steps(goals_ctx: str, whoop_ctx: str, log_ctx: str, journal_ctx: str) -> str:
    """
    Vraagt Claude om per doel één concrete actie voor deze week — kleine stappen.
    """
    context = f"""Doelen:\n{goals_ctx}

Whoop (afgelopen week):\n{whoop_ctx}

Groei-log (commitments week):\n{log_ctx}

Journal context:\n{journal_ctx}"""

    response = client.messages.create(
        model=MODEL,
        max_tokens=1200,
        system="""Je bent een wekelijkse planningscoach. Je spreekt Nederlands.
Je taak: geef per actief doel exact één kleine, concrete actie voor de komende week.
Klein betekent: haalbaar in 1-3 uur, meetbaar, specifiek.
Niet: "besteed meer tijd aan studie". Wel: "maak maandag lecture 8 Waterbouwkunde af (2u)".

Formaat (gebruik dit exact):
DOEL: [titel]
STAP: [concrete actie komende week]
WAAROM: [één zin — waarom dit nu]

Geen inleiding. Geen afsluiting. Alleen de blokken, één per doel.
Sla doelen met deadline >180 dagen over als er urgentere zijn.""",
        messages=[{"role": "user", "content": f"Geef de wekelijkse stappen:\n\n{context}"}],
    )
    return response.content[0].text.strip()


def _generate_analysis(goals_ctx: str, log_ctx: str, whoop_ctx: str) -> str:
    """Korte analyse: wat gaat goed, wat dreigt mis te gaan, patroon."""
    response = client.messages.create(
        model=MODEL,
        max_tokens=400,
        system="""Je bent een directe weekcoach. Nederlands. Geen inleiding.
Geef exact drie punten:
1. WAT GOED GAAT (één concreet ding)
2. WAT DREIGT FOUT TE GAAN (grootste risico komende week)
3. PATROON (één patroon dat je ziet over goals + log + Whoop samen)
Max 2 zinnen per punt.""",
        messages=[{"role": "user", "content": f"Goals:\n{goals_ctx}\n\nLog:\n{log_ctx}\n\nWhoop:\n{whoop_ctx}"}],
    )
    return response.content[0].text.strip()


# ── Print helpers ──────────────────────────────────────────────────────────────

def _print_goals_summary(goals: list[dict]):
    today = date.today()
    # Group by category
    cats: dict[str, list] = {}
    for g in goals:
        cats.setdefault(g["category"], []).append(g)

    for cat, items in cats.items():
        print(f"\n  {cat.upper()}")
        for g in items:
            done  = sum(1 for m in g["milestones"] if m["done"])
            total = len(g["milestones"])
            try:
                days_left = (date.fromisoformat(g["deadline"]) - today).days
                urgency = "🔴" if days_left <= 14 else "🟠" if days_left <= 35 else "🟡" if days_left <= 90 else "🟢"
            except Exception:
                days_left = "?"
                urgency = "·"
            pct = g["progress"]
            print(f"  {urgency} {g['title']}")
            print(f"     {pct}%  {_bar(pct)}  {done}/{total} mijlpalen  {days_left}d")


def _print_growth_log(log: dict):
    total = log["total"]
    kept  = log["kept"]
    pct   = int(kept / total * 100) if total else 0
    print(f"\n  Commitments: {kept}/{total} nagekomen ({pct}%)  {_bar(pct, 12)}")
    if log["entries"]:
        for e in log["entries"][-5:]:
            icon = "✓" if e["achieved"] is True else "✗" if e["achieved"] is False else "·"
            txt  = e["commitment"][:48] + ".." if len(e["commitment"]) > 50 else e["commitment"]
            print(f"  [{icon}] {e['date']}  {txt}")


# ── Main ───────────────────────────────────────────────────────────────────────

def run():
    print("\n" + "━" * W)
    print(f"  WEKELIJKSE REVIEW — {TODAY}")
    print("━" * W)

    # ── Data verzamelen ────────────────────────────────────────────────────────
    goals        = get_active()
    log          = _growth_log_week()
    whoop_trend  = get_recovery_trend(7)
    sleep_trend  = get_sleep_trend(7)
    training     = get_training_summary(7)
    journal_ctx  = _journal_context(days=7)

    # ── 1. Doelen overzicht ────────────────────────────────────────────────────
    print("\nDOELEN")
    _print_goals_summary(goals)

    # ── 2. Whoop week ──────────────────────────────────────────────────────────
    print("\n\nWHOOP — AFGELOPEN WEEK")
    if whoop_trend:
        print(f"  Gem. recovery:  {whoop_trend.get('avg')}%  "
              f"HRV {whoop_trend.get('hrv_avg')}ms  trend {whoop_trend.get('trend')}")
    if sleep_trend:
        print(f"  Gem. slaap:     {sleep_trend.get('avg_hours')}u  "
              f"kwaliteit {sleep_trend.get('avg_perf')}%  "
              f"diepe slaap {sleep_trend.get('avg_deep_min')} min")
    if training:
        acts = ", ".join(f"{v}x {k}" for k, v in training.get("activities", {}).items())
        print(f"  Training:       {training.get('total')}x  ({acts})")

    # ── 3. Growth log week ─────────────────────────────────────────────────────
    print("\n\nGROEI LOG — AFGELOPEN WEEK")
    _print_growth_log(log)

    # ── 4. AI analyse ──────────────────────────────────────────────────────────
    print("\n\nANALYSE")
    goals_ctx_full = _goals_context_full()
    whoop_ctx_str  = (
        f"Recovery gem. {whoop_trend.get('avg')}% trend {whoop_trend.get('trend')}, "
        f"slaap {sleep_trend.get('avg_hours')}u, training {training.get('total')}x/week"
        if whoop_trend else "Geen Whoop data"
    )
    log_ctx_str = (
        f"{log['kept']}/{log['total']} commitments nagekomen. "
        + ("Gemiste: " + "; ".join(
            e["commitment"] for e in log["entries"] if e["achieved"] is False
        ) if log["missed"] else "")
    )

    analysis = _generate_analysis(goals_ctx_full, log_ctx_str, whoop_ctx_str)
    for line in analysis.splitlines():
        print(f"  {line}")

    # ── 5. Wekelijkse stappen per doel ─────────────────────────────────────────
    print("\n\nSTAPPEN DEZE WEEK")
    steps = _generate_weekly_steps(goals_ctx_full, whoop_ctx_str, log_ctx_str, journal_ctx)
    for line in steps.splitlines():
        print(f"  {line}")

    print("\n" + "━" * W + "\n")

    # ── Sla review op ─────────────────────────────────────────────────────────
    _save_review({
        "date":     date.today().isoformat(),
        "goals_snapshot": [
            {"id": g["id"], "title": g["title"], "progress": g["progress"]}
            for g in goals
        ],
        "commitments": {"kept": log["kept"], "total": log["total"]},
        "whoop":    {"recovery_avg": whoop_trend.get("avg"), "sleep_avg": sleep_trend.get("avg_hours")} if whoop_trend else {},
        "analysis": analysis,
        "steps":    steps,
    })
    print("✓ Review opgeslagen in data/weekly_reviews.json\n")


if __name__ == "__main__":
    run()
