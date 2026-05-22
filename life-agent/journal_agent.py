"""
Journal agent — dagelijkse reflectie met AI-analyse.
Slaat entries op in data/journal.json.
Detecteert patronen over tijd en voedt de criticus en goals coach.
"""
import sys
import json
import anthropic
from datetime import datetime, date, timedelta
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()

sys.stdout.reconfigure(encoding="utf-8")

client = anthropic.Anthropic()
MODEL = "claude-sonnet-4-6"
TODAY = datetime.now().strftime("%A %d %B %Y")
TODAY_DATE = date.today().isoformat()
JOURNAL_FILE = Path(__file__).parent / "data" / "journal.json"


# ── Storage ────────────────────────────────────────────────────────────────────

def _load() -> dict:
    return json.loads(JOURNAL_FILE.read_text(encoding="utf-8"))


def _save(data: dict):
    JOURNAL_FILE.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8"
    )


def _get_entry(target_date: str) -> dict | None:
    data = _load()
    for e in reversed(data["entries"]):
        if e["date"] == target_date:
            return e
    return None


def _save_entry(entry: dict):
    data = _load()
    # Replace existing entry for same date, or append
    data["entries"] = [e for e in data["entries"] if e["date"] != entry["date"]]
    data["entries"].append(entry)
    _save(data)


def _recent_entries(days: int = 7) -> list[dict]:
    data = _load()
    cutoff = (date.today() - timedelta(days=days)).isoformat()
    return [e for e in data["entries"] if e["date"] >= cutoff]


# ── AI helpers ─────────────────────────────────────────────────────────────────

def _extract_metadata(raw_text: str) -> dict:
    """Ask Claude to extract structured metadata from free-form journal text."""
    response = client.messages.create(
        model=MODEL,
        max_tokens=400,
        system=(
            "Je analyseert een dagboekfragment en extraheert gestructureerde data. "
            "Antwoord altijd als geldig JSON, niets anders. "
            "Schema: "
            '{"mood": "goed|matig|slecht", '
            '"energie": "hoog|gemiddeld|laag", '
            '"wins": ["korte zin"], '
            '"blockers": ["korte zin"], '
            '"tags": ["max 4 tags uit: studie|sport|financieel|mindset|sociaal|werk|slaap|voeding|planning"], '
            '"kern": "één zin die de essentie van de dag vat"}'
        ),
        messages=[{"role": "user", "content": f"Dagboekfragment:\n{raw_text}"}],
    )
    try:
        raw = response.content[0].text.strip()
        # Strip markdown code fences if present
        if raw.startswith("```"):
            raw = raw.split("```")[1]
            if raw.startswith("json"):
                raw = raw[4:]
        return json.loads(raw.strip())
    except Exception:
        return {"mood": "?", "energie": "?", "wins": [], "blockers": [], "tags": [], "kern": ""}


def _follow_up_question(raw_text: str, history: list[dict]) -> str:
    """Generate one sharp follow-up question to deepen the reflection."""
    prev = "\n".join(f"Jij: {m['content']}" for m in history if m["role"] == "user")
    response = client.messages.create(
        model=MODEL,
        max_tokens=100,
        system=(
            "Je bent een scherpe gesprekspartner die iemand helpt dieper te reflecteren. "
            "Stel één concrete, prikkelende vervolgvraag op basis van wat er geschreven is. "
            "Geen open deuren. Geen 'hoe voelde je je daarbij'. "
            "Pak een specifiek detail en ga er dieper op in. "
            "Nederlands. Max 1 zin."
        ),
        messages=[{"role": "user", "content": f"Journaaltekst:\n{prev or raw_text}"}],
    )
    return response.content[0].text.strip()


def _detect_patterns(entries: list[dict]) -> str:
    """Analyse multiple entries for recurring themes, blockers and trends."""
    if len(entries) < 3:
        return "Te weinig entries voor patroonherkenning (minimaal 3 nodig)."

    summary = []
    for e in entries:
        summary.append(
            f"[{e['date']}] Mood: {e.get('mood','?')} | Energie: {e.get('energie','?')}\n"
            f"  Wins: {', '.join(e.get('wins',[]) or ['—'])}\n"
            f"  Blockers: {', '.join(e.get('blockers',[]) or ['—'])}\n"
            f"  Kern: {e.get('kern','')}"
        )

    response = client.messages.create(
        model=MODEL,
        max_tokens=600,
        system=(
            "Je analyseert meerdere dagboekentries en zoekt naar patronen. "
            "Spreek in het Nederlands. Wees concreet en direct. "
            "Geef: 1) Terugkerende blocker, 2) Sterkste patroon in mood/energie, "
            "3) Wat consistent goed gaat, 4) Één blinde vlek die de persoon zelf niet noemt. "
            "Geen inleiding. Maximaal 5 zinnen totaal."
        ),
        messages=[{"role": "user", "content": "\n\n".join(summary)}],
    )
    return response.content[0].text.strip()


# ── Modes ──────────────────────────────────────────────────────────────────────

def schrijven():
    """Interactieve schrijfsessie met 2-3 vervolgvragen."""
    print("\n" + "=" * 55)
    print("JOURNAL")
    print(f"{TODAY}")
    print("=" * 55)

    existing = _get_entry(TODAY_DATE)
    if existing:
        print(f"Je hebt vandaag al geschreven: \"{existing.get('kern','')}\"\n")
        try:
            ans = input("Doorgaan en aanvullen? (ja/nee): ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            return
        if ans not in ("ja", "j", "y", "yes"):
            return

    print("\nVertel hoe je dag was. Schrijf vrij — geen filters, geen mooie taal.")
    print("Typ een lege regel om af te ronden.\n")

    lines = []
    try:
        while True:
            line = input()
            if line == "":
                if lines:
                    break
            else:
                lines.append(line)
    except (EOFError, KeyboardInterrupt):
        pass

    if not lines:
        print("Niets geschreven.")
        return

    raw = "\n".join(lines)
    history = [{"role": "user", "content": raw}]

    # 2 follow-up rounds
    for i in range(2):
        question = _follow_up_question(raw, history)
        print(f"\nJournal: {question}\n")
        try:
            answer = input("Jij: ").strip()
        except (EOFError, KeyboardInterrupt):
            break
        if not answer or answer.lower() in ("stop", "klaar", "exit"):
            break
        history.append({"role": "assistant", "content": question})
        history.append({"role": "user", "content": answer})
        raw += f"\n\n{answer}"

    # Extract metadata
    print("\n[analyseren...]")
    meta = _extract_metadata(raw)

    entry = {
        "date":      TODAY_DATE,
        "timestamp": datetime.now().isoformat(),
        "raw":       raw,
        "mood":      meta.get("mood", "?"),
        "energie":   meta.get("energie", "?"),
        "wins":      meta.get("wins", []),
        "blockers":  meta.get("blockers", []),
        "tags":      meta.get("tags", []),
        "kern":      meta.get("kern", ""),
    }
    _save_entry(entry)

    print(f"\n✓ Opgeslagen")
    print(f"  Mood:     {entry['mood']} | Energie: {entry['energie']}")
    if entry["wins"]:
        print(f"  Wins:     {' · '.join(entry['wins'])}")
    if entry["blockers"]:
        print(f"  Blocker:  {' · '.join(entry['blockers'])}")
    print(f"  Kern:     {entry['kern']}")
    if entry["tags"]:
        print(f"  Tags:     {' '.join(entry['tags'])}")
    print()


def patronen(days: int = 14):
    """Analyseer de laatste N dagen op terugkerende patronen."""
    entries = _recent_entries(days)
    if not entries:
        print(f"Geen entries in de laatste {days} dagen.")
        return

    print(f"\n{'='*55}\nPATRONEN — laatste {days} dagen ({len(entries)} entries)\n{'='*55}\n")

    # Quick stats
    moods = [e.get("mood") for e in entries if e.get("mood") not in ("?", None)]
    if moods:
        goed   = moods.count("goed")
        matig  = moods.count("matig")
        slecht = moods.count("slecht")
        print(f"Mood:    goed {goed}x  |  matig {matig}x  |  slecht {slecht}x")

    energie = [e.get("energie") for e in entries if e.get("energie") not in ("?", None)]
    if energie:
        hoog = energie.count("hoog")
        gem  = energie.count("gemiddeld")
        laag = energie.count("laag")
        print(f"Energie: hoog {hoog}x  |  gemiddeld {gem}x  |  laag {laag}x")

    all_blockers = [b for e in entries for b in (e.get("blockers") or [])]
    all_wins     = [w for e in entries for w in (e.get("wins") or [])]
    if all_blockers:
        print(f"Blockers ({len(all_blockers)}x): {' · '.join(all_blockers[:5])}")
    if all_wins:
        print(f"Wins ({len(all_wins)}x): {' · '.join(all_wins[:5])}")

    print()
    print(_detect_patterns(entries))
    print()


def log(days: int = 7):
    """Toon overzicht van recente entries."""
    entries = _recent_entries(days)
    if not entries:
        print(f"Geen entries in de laatste {days} dagen.")
        return

    print(f"\n{'='*55}\nJOURNAL LOG — laatste {days} dagen\n{'='*55}")
    for e in sorted(entries, key=lambda x: x["date"], reverse=True):
        mood_icon = {"goed": "🟢", "matig": "🟡", "slecht": "🔴"}.get(e.get("mood",""), "·")
        print(f"\n{mood_icon}  {e['date']}  [{e.get('energie','?')} energie]")
        if e.get("kern"):
            print(f"   {e['kern']}")
        if e.get("wins"):
            print(f"   ✓ {' · '.join(e['wins'])}")
        if e.get("blockers"):
            print(f"   ✗ {' · '.join(e['blockers'])}")
    print()


def context_voor_agents(days: int = 7) -> str:
    """Geeft een compacte string terug voor gebruik in andere agents."""
    entries = _recent_entries(days)
    if not entries:
        return ""
    lines = [f"Journal context (laatste {days} dagen):"]
    for e in sorted(entries, key=lambda x: x["date"]):
        mood = e.get("mood", "?")
        kern = e.get("kern", "")
        blockers = ", ".join(e.get("blockers") or [])
        lines.append(f"  {e['date']} [{mood}]: {kern}" + (f" | blocker: {blockers}" if blockers else ""))
    return "\n".join(lines)


if __name__ == "__main__":
    args = sys.argv[1:]

    if not args or args[0] == "schrijven":
        schrijven()
    elif args[0] == "patronen":
        days = int(args[1]) if len(args) > 1 else 14
        patronen(days)
    elif args[0] == "log":
        days = int(args[1]) if len(args) > 1 else 7
        log(days)
    else:
        print("Gebruik:")
        print("  python journal_agent.py              → schrijf vandaag")
        print("  python journal_agent.py patronen     → analyse laatste 14 dagen")
        print("  python journal_agent.py patronen 30  → analyse laatste 30 dagen")
        print("  python journal_agent.py log          → overzicht laatste 7 dagen")
