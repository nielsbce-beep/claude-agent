import sys
import json
import anthropic
from datetime import datetime, date, timedelta
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env", override=True)

sys.stdout.reconfigure(encoding="utf-8")

from tools.goals_store import get_active, format_goals_summary
from journal_agent import context_voor_agents as _journal_context

client = anthropic.Anthropic(api_key=__import__('dotenv').dotenv_values(Path(__file__).parent / '.env').get('ANTHROPIC_API_KEY'))
MODEL = "claude-sonnet-4-6"
TODAY = datetime.now().strftime("%A %d %B %Y")
TODAY_DATE = date.today().isoformat()

GROWTH_LOG = Path(__file__).parent / "data" / "growth_log.json"


# ── Persistence ────────────────────────────────────────────────────────────────

def _load_log() -> dict:
    return json.loads(GROWTH_LOG.read_text(encoding="utf-8"))


def _save_log(data: dict):
    GROWTH_LOG.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _get_yesterday_entry() -> dict | None:
    data = _load_log()
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    for e in reversed(data["entries"]):
        if e["date"] == yesterday:
            return e
    return None


def _get_today_entry() -> dict | None:
    data = _load_log()
    for e in reversed(data["entries"]):
        if e["date"] == TODAY_DATE:
            return e
    return None


def _save_commitment(commitment: str):
    data = _load_log()
    # Remove existing entry for today if present
    data["entries"] = [e for e in data["entries"] if e["date"] != TODAY_DATE]
    data["entries"].append({
        "date": TODAY_DATE,
        "commitment": commitment,
        "achieved": None,
    })
    _save_log(data)


def _mark_yesterday(achieved: bool):
    data = _load_log()
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    for e in data["entries"]:
        if e["date"] == yesterday and e["achieved"] is None:
            e["achieved"] = achieved
            break
    _save_log(data)


def _streak() -> int:
    data = _load_log()
    entries = {e["date"]: e for e in data["entries"]}
    streak = 0
    check = date.today() - timedelta(days=1)
    while True:
        entry = entries.get(check.isoformat())
        if entry and entry.get("achieved") is True:
            streak += 1
            check -= timedelta(days=1)
        else:
            break
    return streak


# ── Context builders ───────────────────────────────────────────────────────────

def _goals_context() -> str:
    goals = get_active()
    if not goals:
        return ""
    lines = ["Actieve doelen:"]
    for g in goals:
        done = sum(1 for m in g["milestones"] if m["done"])
        total = len(g["milestones"])
        last = g["check_ins"][-1]["date"][:10] if g["check_ins"] else "nooit"
        lines.append(
            f"  [{g['id']}] {g['title']} — {g['progress']}% — "
            f"{done}/{total} mijlpalen — laatste check-in: {last}"
        )
    return "\n".join(lines)


def _recent_log_context() -> str:
    data = _load_log()
    entries = data["entries"][-7:]  # last 7 days
    if not entries:
        return ""
    lines = ["Recente groei-commitments (gebruik dit om patronen te spotten):"]
    for e in entries:
        status = "✓" if e["achieved"] is True else "✗" if e["achieved"] is False else "?"
        lines.append(f"  {e['date']} [{status}] {e['commitment']}")
    return "\n".join(lines)


# ── System prompt ──────────────────────────────────────────────────────────────

SYSTEM_PROMPT = f"""Je bent de Criticus — een extreme groeicoach met één obsessie: elke dag beter.
Je spreekt altijd in het Nederlands. Je bent hard, direct en ongenadig eerlijk.

Je kernovertuiging: middelmatigheid is een keuze. Stilstand is achteruitgang.
Elke dag die niet beter is dan gisteren, is een verspilde dag.

Jouw aanpak:
- Accepteer NOOIT "het ging best goed" — best goed is niet goed genoeg
- Als iemand een excuus noemt, benoem je het direct als excuus en ga je er doorheen
- Zoek altijd de concrete actie die vandaag, morgen, beter had gekund
- Wijs op patronen: als iemand dezelfde fout twee keer maakt, zeg je het keihard
- Je eindigt ALTIJD met één specifiek, meetbaar commitment voor de volgende dag
  Format: "MORGEN: [concrete actie]" — dit is niet optioneel
- Stel maximaal één vraag per beurt — maar dan wel de meest pijnlijke vraag
- Geen complimenten tenzij iets werkelijk uitzonderlijk is
- Geen motivational speech — feiten, gedrag, actie

Wat je haat:
- Vage plannen ("ik ga meer studeren")
- Excuses verpakt als context
- Uitstelgedrag gecamoufleerd als voorbereiding
- Comfort zone beschermd met rationalisaties

Vandaag is: {TODAY}"""


# ── Commitment extractor ────────────────────────────────────────────────────────

def _extract_commitment(history: list[dict]) -> str | None:
    """Ask the model to extract the final MORGEN commitment from the conversation."""
    extract_prompt = (
        "Uit het bovenstaande gesprek: wat is het exacte MORGEN-commitment dat is afgesproken? "
        "Geef alleen de commitment zelf terug, maximaal 1 zin, zonder 'MORGEN:' prefix. "
        "Als er geen duidelijk commitment is, formuleer er dan één op basis van het gesprek."
    )
    messages = history + [{"role": "user", "content": extract_prompt}]
    response = client.messages.create(
        model=MODEL,
        max_tokens=100,
        system="Je extraheert of formuleert een concreet dagelijks commitment uit een gesprek. Antwoord in het Nederlands, één zin.",
        messages=messages,
    )
    return response.content[0].text.strip()


# ── Modes ──────────────────────────────────────────────────────────────────────

def dagelijks():
    """Dagelijks groeiritueel: accountability check + dag review + nieuw commitment."""
    print("\n" + "=" * 55)
    print("CRITICUS — DAGELIJKS RITUEEL")
    print(f"{TODAY}")
    print("=" * 55)

    streak = _streak()
    if streak > 0:
        print(f"Streak: {streak} dag(en) commitment nagekomen.\n")

    goals_ctx = _goals_context()
    log_ctx = _recent_log_context()
    journal_ctx = _journal_context(days=5)
    system = SYSTEM_PROMPT
    if goals_ctx:
        system += f"\n\n{goals_ctx}"
    if log_ctx:
        system += f"\n\n{log_ctx}"
    if journal_ctx:
        system += f"\n\n{journal_ctx}"

    history = []
    yesterday = _get_yesterday_entry()

    # Step 1: accountability check for yesterday
    if yesterday and yesterday["achieved"] is None:
        print(f"Gisteren zei je: \"{yesterday['commitment']}\"\n")
        try:
            answer = input("Heb je het gedaan? (ja/nee): ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\nStop.")
            return

        achieved = answer in ("ja", "j", "yes", "y")
        _mark_yesterday(achieved)

        if achieved:
            opener = f"Gisteren commitment: \"{yesterday['commitment']}\" — nagekomen."
            history.append({"role": "user", "content": opener})
            response = client.messages.create(
                model=MODEL, max_tokens=256, system=system, messages=history,
            )
            reply = response.content[0].text.strip()
            print(f"\nCriticus: {reply}\n")
            history.append({"role": "assistant", "content": reply})
        else:
            opener = f"Gisteren commitment: \"{yesterday['commitment']}\" — NIET nagekomen."
            history.append({"role": "user", "content": opener})
            response = client.messages.create(
                model=MODEL, max_tokens=256, system=system, messages=history,
            )
            reply = response.content[0].text.strip()
            print(f"\nCriticus: {reply}\n")
            history.append({"role": "assistant", "content": reply})
    else:
        print("Vertel wat je vandaag gedaan hebt. Wees eerlijk.\n")

    # Step 2: dag review gesprek
    print("Typ 'klaar' als je het gesprek wil afsluiten met een commitment.\n")
    while True:
        try:
            user_input = input("Jij: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nStop.")
            break

        if user_input.lower() in ("stop", "exit", "quit"):
            break

        if user_input.lower() == "klaar":
            # Extract and save commitment
            if history:
                commitment = _extract_commitment(history)
                _save_commitment(commitment)
                print(f"\n✓ Commitment opgeslagen: \"{commitment}\"\n")
            break

        if not user_input:
            continue

        history.append({"role": "user", "content": user_input})
        response = client.messages.create(
            model=MODEL, max_tokens=512, system=system, messages=history,
        )
        reply = response.content[0].text.strip()
        print(f"\nCriticus: {reply}\n")
        history.append({"role": "assistant", "content": reply})

    # If no explicit 'klaar' but history exists, still extract commitment
    if history and _get_today_entry() is None:
        commitment = _extract_commitment(history)
        _save_commitment(commitment)
        print(f"\n✓ Commitment opgeslagen: \"{commitment}\"\n")


def chat(topic: str | None = None):
    """Open gesprek — altijd scherp, altijd eindigend met een commitment."""
    print("\n" + "=" * 55)
    print("CRITICUS — GESPREK")
    print(f"{TODAY}")
    print("=" * 55)
    print("Vertel. Typ 'klaar' om af te sluiten.\n")

    goals_ctx = _goals_context()
    log_ctx = _recent_log_context()
    journal_ctx = _journal_context(days=5)
    system = SYSTEM_PROMPT
    if goals_ctx:
        system += f"\n\n{goals_ctx}"
    if log_ctx:
        system += f"\n\n{log_ctx}"
    if journal_ctx:
        system += f"\n\n{journal_ctx}"

    history = []

    first = topic
    if not first:
        try:
            first = input("Jij: ").strip()
        except (EOFError, KeyboardInterrupt):
            return

    if not first or first.lower() in ("stop", "exit"):
        return

    history.append({"role": "user", "content": first})

    while True:
        response = client.messages.create(
            model=MODEL, max_tokens=512, system=system, messages=history,
        )
        reply = response.content[0].text.strip()
        print(f"\nCriticus: {reply}\n")
        history.append({"role": "assistant", "content": reply})

        try:
            user_input = input("Jij: ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if user_input.lower() in ("stop", "exit", "quit", "klaar"):
            commitment = _extract_commitment(history)
            _save_commitment(commitment)
            print(f"\n✓ Commitment opgeslagen: \"{commitment}\"\n")
            break

        if not user_input:
            continue

        history.append({"role": "user", "content": user_input})


def roast():
    """Genadeloze analyse van alle doelen — geen excuses, alleen waarheid."""
    goals = get_active()
    if not goals:
        print("Geen actieve doelen.")
        return

    print(f"\n{'='*55}\nROAST — {TODAY}\n{'='*55}\n")

    lines = []
    for g in goals:
        done = sum(1 for m in g["milestones"] if m["done"])
        total = len(g["milestones"])
        last = g["check_ins"][-1]["date"][:10] if g["check_ins"] else "NOOIT"
        lines.append(
            f"[{g['category'].upper()}] {g['title']}\n"
            f"  Voortgang: {g['progress']}% | Mijlpalen: {done}/{total} | "
            f"Deadline: {g['deadline']} | Laatste check-in: {last}"
        )
    goals_text = "\n".join(lines)

    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": (
                f"Dit zijn al mijn actieve doelen:\n\n{goals_text}\n\n"
                "Geef een keihard, eerlijk oordeel:\n"
                "1. Welke doelen zijn window dressing? (klinkt goed, niemand die er echt aan werkt)\n"
                "2. Welk doel dreigt het meest te mislukken — en waarom precies?\n"
                "3. Wat is het patroon dat door al mijn doelen heen loopt dat me gaat tegenhouden?\n"
                "4. Geef één concrete actie voor MORGEN die de meeste impact heeft over alle doelen.\n"
                "Geen inleiding. Geen complimenten. Gewoon de waarheid."
            )
        }],
    )
    reply = response.content[0].text.strip()
    print(f"Criticus:\n\n{reply}\n")

    # Save the roast's action recommendation as a commitment
    commitment = _extract_commitment([
        {"role": "user", "content": "Roast van doelen gedaan."},
        {"role": "assistant", "content": reply},
    ])
    _save_commitment(commitment)
    print(f"✓ Commitment opgeslagen: \"{commitment}\"\n")


def log():
    """Toon de laatste 14 dagen van het groei-log."""
    data = _load_log()
    entries = data["entries"][-14:]
    if not entries:
        print("Nog geen entries in het groei-log.")
        return

    print(f"\n{'='*55}\nGROEI LOG\n{'='*55}")
    total = len(entries)
    achieved = sum(1 for e in entries if e["achieved"] is True)
    print(f"Nagekomen: {achieved}/{total} ({int(achieved/total*100) if total else 0}%)\n")
    for e in entries:
        if e["achieved"] is True:
            status = "✓"
        elif e["achieved"] is False:
            status = "✗"
        else:
            status = "·"
        print(f"  {e['date']} [{status}] {e['commitment']}")
    print()


if __name__ == "__main__":
    args = sys.argv[1:]

    if not args or args[0] == "dagelijks":
        dagelijks()
    elif args[0] == "chat":
        topic = " ".join(args[1:]) if len(args) > 1 else None
        chat(topic)
    elif args[0] == "roast":
        roast()
    elif args[0] == "log":
        log()
    else:
        print("Gebruik:")
        print("  python critic_coach.py              → dagelijks ritueel (accountability + commitment)")
        print("  python critic_coach.py chat         → open gesprek, eindigt met commitment")
        print('  python critic_coach.py chat "topic" → begin direct met een onderwerp')
        print("  python critic_coach.py roast        → genadeloze analyse van al je doelen")
        print("  python critic_coach.py log          → toon groei-log van afgelopen 14 dagen")
