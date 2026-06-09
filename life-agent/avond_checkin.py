"""
Avond check-in — sluit de dag af in 5 minuten.
Checkt wat gepland stond, wat gedaan is, logt voortgang en zet commitment voor morgen.
"""
import sys
import json
import anthropic
from datetime import datetime, date, timedelta
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env", override=True)

sys.stdout.reconfigure(encoding="utf-8")

from tools.calendar_tools import get_events
from tools.goals_store import get_active, log_check_in, complete_milestone
from journal_agent import _save_entry, _extract_metadata, _get_entry

client = anthropic.Anthropic(api_key=__import__('dotenv').dotenv_values(Path(__file__).parent / '.env').get('ANTHROPIC_API_KEY'))
MODEL = "claude-sonnet-4-6"
TODAY = datetime.now().strftime("%A %d %B %Y")
TODAY_DATE = date.today().isoformat()
GROWTH_LOG = Path(__file__).parent / "data" / "growth_log.json"


# ── Growth log helpers ─────────────────────────────────────────────────────────

def _load_log() -> dict:
    return json.loads(GROWTH_LOG.read_text(encoding="utf-8"))


def _save_log(data: dict):
    GROWTH_LOG.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _get_today_commitment() -> dict | None:
    data = _load_log()
    for e in reversed(data["entries"]):
        if e["date"] == TODAY_DATE:
            return e
    return None


def _save_commitment(commitment: str):
    data = _load_log()
    data["entries"] = [e for e in data["entries"] if e["date"] != TODAY_DATE]
    data["entries"].append({
        "date": TODAY_DATE,
        "commitment": commitment,
        "achieved": None,
    })
    _save_log(data)


def _mark_today(achieved: bool):
    data = _load_log()
    for e in data["entries"]:
        if e["date"] == TODAY_DATE and e["achieved"] is None:
            e["achieved"] = achieved
            break
    _save_log(data)


# ── Data helpers ───────────────────────────────────────────────────────────────

def _get_planned_blocks() -> list[str]:
    """Haal geplande studeer- en trainingsblokken op uit de agenda van vandaag."""
    try:
        start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        end   = start.replace(hour=23, minute=59)
        events = get_events(start, end, calendar_name="Niels AI agenda")
        relevant = []
        for e in events:
            title = str(e["summary"])
            if any(kw in title.lower() for kw in ("studeren", "gym", "hardlopen", "mma", "training", "mumie")):
                s = e["start"]
                time_str = f"{s.hour:02d}:{s.minute:02d}" if hasattr(s, "hour") else ""
                relevant.append(f"{time_str}  {title}" if time_str else title)
        return relevant
    except Exception:
        return []


def _urgent_goals() -> list[dict]:
    """Doelen met deadline binnen 30 dagen."""
    goals = get_active()
    today = date.today()
    urgent = []
    for g in goals:
        if not g.get("deadline"):
            continue
        try:
            days = (date.fromisoformat(g["deadline"]) - today).days
            if days <= 40:
                urgent.append({**g, "days_left": days})
        except Exception:
            continue
    return sorted(urgent, key=lambda g: g["days_left"])


# ── AI helpers ─────────────────────────────────────────────────────────────────

def _generate_tomorrow_commitment(day_summary: str, goals_ctx: str) -> str:
    response = client.messages.create(
        model=MODEL,
        max_tokens=80,
        system=(
            "Je formuleert één concreet, meetbaar commitment voor morgen op basis van "
            "wat er vandaag gedaan (en niet gedaan) is. "
            "Eén zin, actief, specifiek, haalbaar in één dag. Nederlands."
        ),
        messages=[{"role": "user", "content": f"Dag samenvatting:\n{day_summary}\n\nUrgente doelen:\n{goals_ctx}"}],
    )
    return response.content[0].text.strip()


def _closing_reflection(day_summary: str) -> str:
    response = client.messages.create(
        model=MODEL,
        max_tokens=120,
        system=(
            "Je bent een directe dagcoach. Geef één scherpe observatie over deze dag — "
            "geen lof, geen medeleven, alleen de meest relevante les of patroon. "
            "Max 2 zinnen. Nederlands."
        ),
        messages=[{"role": "user", "content": day_summary}],
    )
    return response.content[0].text.strip()


# ── Input helper ───────────────────────────────────────────────────────────────

def _ask(prompt: str, default: str = "") -> str:
    try:
        answer = input(prompt).strip()
        return answer if answer else default
    except (EOFError, KeyboardInterrupt):
        return default


def _ask_yn(prompt: str) -> bool:
    ans = _ask(f"{prompt} (ja/nee): ").lower()
    return ans in ("ja", "j", "y", "yes")


# ── Main ───────────────────────────────────────────────────────────────────────

def run():
    print("\n" + "=" * 55)
    print("AVOND CHECK-IN")
    print(f"{TODAY}")
    print("=" * 55 + "\n")

    summary_parts = []

    # ── 1. Commitment van vandaag checken ──────────────────────────────────────
    commitment = _get_today_commitment()
    if commitment and commitment["achieved"] is None:
        print(f'Vandaag gezegd: "{commitment["commitment"]}"\n')
        done = _ask_yn("Gehaald?")
        _mark_today(done)
        result_str = "nagekomen ✓" if done else "NIET nagekomen ✗"
        print(f"  → {result_str}\n")
        summary_parts.append(f"Commitment: \"{commitment['commitment']}\" — {result_str}")
    else:
        summary_parts.append("Geen open commitment vandaag.")

    # ── 2. Geplande blokken vs. werkelijkheid ──────────────────────────────────
    planned = _get_planned_blocks()
    if planned:
        print("Gepland vandaag:")
        for i, b in enumerate(planned):
            print(f"  {i+1}. {b}")
        print()
        done_input = _ask("Welke nummers heb je gedaan? (bv. 1,3 of 'alles' of 'niets'): ", "")
        if done_input.lower() == "alles":
            done_blocks = planned
            missed_blocks = []
        elif done_input.lower() == "niets":
            done_blocks = []
            missed_blocks = planned
        else:
            try:
                done_idxs = {int(x.strip()) - 1 for x in done_input.split(",") if x.strip().isdigit()}
            except Exception:
                done_idxs = set()
            done_blocks   = [b for i, b in enumerate(planned) if i in done_idxs]
            missed_blocks = [b for i, b in enumerate(planned) if i not in done_idxs]

        if done_blocks:
            summary_parts.append(f"Gedaan: {', '.join(done_blocks)}")
        if missed_blocks:
            summary_parts.append(f"Gemist: {', '.join(missed_blocks)}")
        print()

    # ── 3. Één win en één blocker ──────────────────────────────────────────────
    win     = _ask("Grootste win van vandaag: ")
    blocker = _ask("Wat zat er in de weg? ")
    if win:
        summary_parts.append(f"Win: {win}")
    if blocker:
        summary_parts.append(f"Blocker: {blocker}")
    print()

    # ── 4. Urgente doelen update ───────────────────────────────────────────────
    urgent = _urgent_goals()
    goals_lines = []
    if urgent:
        print("Urgente doelen (deadline ≤30 dagen):")
        for g in urgent[:4]:
            done_m  = sum(1 for m in g["milestones"] if m["done"])
            total_m = len(g["milestones"])
            icon = "🔴" if g["days_left"] <= 7 else "🟠" if g["days_left"] <= 14 else "🟡"
        print(f"  {icon} [{g['days_left']}d] {g['title']} — {g['progress']}% — {done_m}/{total_m} mijlpalen")
        print()
        goals_lines = [f"{g['title']} ({g['days_left']} dagen, {g['progress']}%)" for g in urgent[:4]]

        # Quick milestone check
        for g in urgent[:2]:
            open_milestones = [(i, m) for i, m in enumerate(g["milestones"]) if not m["done"]]
            if open_milestones:
                i, m = open_milestones[0]
                if _ask_yn(f'Mijlpaal afgerond: "{m["text"]}"?'):
                    complete_milestone(g["id"], i)
                    print(f"  ✓ Mijlpaal gemarkeerd!\n")
                    summary_parts.append(f"Mijlpaal afgerond: {m['text']}")

    # ── 5. Voortgang loggen op doel ────────────────────────────────────────────
    if urgent:
        update = _ask("Wil je voortgang loggen op een doel? (goal_id of enter om te skippen): ")
        if update:
            note = _ask("Notitie: ")
            try:
                pct = int(_ask("Voortgang % (0-100): ", "0"))
            except Exception:
                pct = 0
            log_check_in(update, note, pct)
            print(f"  ✓ Check-in gelogd\n")
            summary_parts.append(f"Check-in op {update}: {note} ({pct}%)")

    # ── 6. Commitment voor morgen ──────────────────────────────────────────────
    print("[commitment voor morgen genereren...]\n")
    day_summary  = "\n".join(summary_parts)
    goals_ctx    = "\n".join(goals_lines) if goals_lines else "Geen urgente doelen."
    tomorrow_raw = _generate_tomorrow_commitment(day_summary, goals_ctx)

    # Let user override
    print(f"Voorstel voor morgen: \"{tomorrow_raw}\"")
    override = _ask("Aanpassen? (enter = overnemen): ")
    final_commitment = override if override else tomorrow_raw
    _save_commitment(final_commitment)
    print(f"\n✓ Commitment opgeslagen: \"{final_commitment}\"")

    # ── 7. Slotobservatie van de coach ─────────────────────────────────────────
    print("\n[afsluiting...]")
    closing = _closing_reflection(day_summary)
    print(f"\nCoach: {closing}\n")

    # ── 8. Sla op als journal entry als er nog geen is ─────────────────────────
    if not _get_entry(TODAY_DATE) and (win or blocker):
        raw_text = ". ".join(filter(None, [win, blocker, f"Commitment morgen: {final_commitment}"]))
        meta = _extract_metadata(raw_text)
        _save_entry({
            "date":      TODAY_DATE,
            "timestamp": datetime.now().isoformat(),
            "raw":       day_summary,
            "mood":      meta.get("mood", "?"),
            "energie":   meta.get("energie", "?"),
            "wins":      [win] if win else meta.get("wins", []),
            "blockers":  [blocker] if blocker else meta.get("blockers", []),
            "tags":      meta.get("tags", []),
            "kern":      meta.get("kern", win or ""),
        })
        print("✓ Ook opgeslagen als journal entry\n")

    print("=" * 55)
    print("Dag afgesloten. Morgen verder.")
    print("=" * 55 + "\n")


if __name__ == "__main__":
    run()
