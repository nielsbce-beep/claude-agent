import sys
import json
import anthropic
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env", override=True)

sys.stdout.reconfigure(encoding="utf-8")

from tools.goals_store import (
    get_all, get_active, add_goal, log_check_in,
    complete_milestone, update_status, format_goals_summary,
)
from tools.calendar_tools import add_event
import config

client = anthropic.Anthropic()
MODEL = config.MODEL
TODAY = datetime.now().strftime("%A %d %B %Y")

SYSTEM_PROMPT = f"""Je bent een persoonlijke doelen coach. Je naam is Coach.
Je spreekt altijd in het Nederlands. Je bent warm maar direct — je accepteert geen vage doelen.
Je stelt scherpe vragen, helpt doelen SMART maken en houdt de gebruiker eerlijk accountable.
Je viert échte wins, maar je sust ook niet onnodig. Je doel is groei, niet comfort.
Vandaag is: {TODAY}

Je hebt toegang tot de doelen van de gebruiker via de context die je krijgt.
Als je een doel wil toevoegen, check-in wil loggen of mijlpaal wil markeren,
geef dit terug als JSON in dit formaat aan het eind van je antwoord:
<action>
{{"type": "add_goal", "title": "...", "description": "...", "category": "sport|studie|financieel|persoonlijk", "deadline": "YYYY-MM-DD", "milestones": ["...", "..."]}}
</action>

Of voor een check-in:
<action>
{{"type": "check_in", "goal_id": "...", "note": "...", "progress": 0-100}}
</action>

Of voor een mijlpaal:
<action>
{{"type": "milestone", "goal_id": "...", "index": 0}}
</action>

Of voor agenda:
<action>
{{"type": "calendar", "title": "...", "date": "YYYY-MM-DD", "hour": 9, "duration_hours": 1, "description": "..."}}
</action>

Geef altijd eerst je coach-tekst, dan pas de action tag als dat van toepassing is."""


def _parse_action(text: str) -> dict | None:
    if "<action>" not in text:
        return None
    try:
        raw = text.split("<action>")[1].split("</action>")[0].strip()
        return json.loads(raw)
    except Exception:
        return None


def _clean_text(text: str) -> str:
    if "<action>" in text:
        return text.split("<action>")[0].strip()
    return text.strip()


def _execute_action(action: dict):
    t = action.get("type")
    if t == "add_goal":
        goal = add_goal(
            title=action["title"],
            description=action.get("description", ""),
            category=action.get("category", "persoonlijk"),
            deadline=action.get("deadline", ""),
            milestones=action.get("milestones", []),
        )
        print(f"\n✅ Doel opgeslagen: [{goal['id']}] {goal['title']}")
        # Deadline in agenda
        if action.get("deadline"):
            try:
                dl = datetime.fromisoformat(action["deadline"])
                add_event(f"Deadline: {action['title']}", dl.replace(hour=9), dl.replace(hour=10), action.get("description",""), config.CALENDAR_NAME, skip_if_overlap=True)
                print(f"📅 Deadline toegevoegd aan agenda: {action['deadline']}")
            except Exception:
                pass

    elif t == "check_in":
        log_check_in(action["goal_id"], action.get("note",""), action.get("progress", 0))
        print(f"\n✅ Check-in gelogd voor doel {action['goal_id']}")

    elif t == "milestone":
        complete_milestone(action["goal_id"], action["index"])
        print(f"\n✅ Mijlpaal afgerond!")

    elif t == "calendar":
        try:
            dag = datetime.fromisoformat(action["date"])
            start = dag.replace(hour=action.get("hour", 9))
            end = start.replace(hour=start.hour + action.get("duration_hours", 1))
            add_event(action["title"], start, end, action.get("description",""), config.CALENDAR_NAME, skip_if_overlap=True)
            print(f"\n📅 Toegevoegd aan agenda: {action['title']} op {action['date']}")
        except Exception as e:
            print(f"\n⚠ Kon niet toevoegen aan agenda: {e}")


def _build_context() -> str:
    goals = get_active()
    if not goals:
        return "De gebruiker heeft nog geen doelen ingesteld."
    lines = ["Actieve doelen van de gebruiker:"]
    for g in goals:
        done = sum(1 for m in g["milestones"] if m["done"])
        total = len(g["milestones"])
        lines.append(f"\n[{g['id']}] {g['title']} ({g['category']})")
        lines.append(f"  Voortgang: {g['progress']}% | Deadline: {g['deadline']}")
        lines.append(f"  Beschrijving: {g['description']}")
        if g["milestones"]:
            lines.append(f"  Mijlpalen ({done}/{total} afgerond):")
            for i, m in enumerate(g["milestones"]):
                check = "✓" if m["done"] else "○"
                lines.append(f"    {i}. {check} {m['text']}")
        if g["check_ins"]:
            last = g["check_ins"][-1]
            lines.append(f"  Laatste check-in: {last['date'][:10]} — {last['note']}")
    return "\n".join(lines)


def chat():
    print("\n" + "=" * 55)
    print("DOELEN COACH")
    print(f"{TODAY}")
    print("=" * 55)
    print("Type je vraag of vertel wat je wil bereiken.")
    print("Typ 'stop' om te stoppen.\n")

    history = []
    goals_context = _build_context()

    while True:
        try:
            user_input = input("Jij: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nTot de volgende keer!")
            break

        if user_input.lower() in ("stop", "exit", "quit"):
            print("Tot de volgende keer!")
            break
        if not user_input:
            continue

        history.append({"role": "user", "content": user_input})

        response = client.messages.create(
            model=MODEL,
            max_tokens=1024,
            system=SYSTEM_PROMPT + f"\n\n{goals_context}",
            messages=history,
        )
        reply = response.content[0].text
        action = _parse_action(reply)
        clean = _clean_text(reply)

        print(f"\nCoach: {clean}\n")
        history.append({"role": "assistant", "content": reply})

        if action:
            _execute_action(action)
            goals_context = _build_context()


def check_in():
    goals = get_active()
    if not goals:
        print("Geen actieve doelen. Start met: python goals_coach.py")
        return

    summary = format_goals_summary()
    print(f"\n{'-'*55}\nCHECK-IN — {TODAY}\n{'-'*55}")

    response = client.messages.create(
        model=MODEL,
        max_tokens=512,
        system=SYSTEM_PROMPT + f"\n\n{_build_context()}",
        messages=[{"role": "user", "content": "Doe een korte dagelijkse check-in. Vraag naar elk actief doel en hoe het gaat. Wees kort en concreet."}],
    )
    reply = response.content[0].text
    print(f"\nCoach: {_clean_text(reply)}\n")


def review():
    goals = get_all()
    if not goals:
        print("Nog geen doelen.")
        return

    print(f"\n{'='*55}\nWEEKLIJKSE REVIEW — {TODAY}\n{'='*55}")
    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=SYSTEM_PROMPT + f"\n\n{_build_context()}",
        messages=[{"role": "user", "content": "Doe een wekelijkse review van alle doelen. Wat gaat goed, wat dreigt achter te raken, wat moet bijgesteld worden? Wees direct en geef concrete actiepunten."}],
    )
    print(f"\nCoach: {_clean_text(response.content[0].text)}\n")


def list_goals():
    goals = get_all()
    if not goals:
        print("Nog geen doelen ingesteld.")
        return
    print(f"\n{'='*55}\nJOUW DOELEN\n{'='*55}")
    for g in goals:
        done = sum(1 for m in g["milestones"] if m["done"])
        total = len(g["milestones"])
        status_icon = "✅" if g["status"] == "completed" else "⏸" if g["status"] == "paused" else "🎯"
        print(f"\n{status_icon} [{g['id']}] {g['title']}")
        print(f"   Categorie: {g['category']} | Deadline: {g['deadline']}")
        print(f"   Voortgang: {g['progress']}% | Mijlpalen: {done}/{total}")
        if g["check_ins"]:
            print(f"   Laatste check-in: {g['check_ins'][-1]['date'][:10]}")


if __name__ == "__main__":
    args = sys.argv[1:]
    if not args or args[0] == "chat":
        chat()
    elif args[0] == "check-in":
        check_in()
    elif args[0] == "review":
        review()
    elif args[0] == "lijst":
        list_goals()
    else:
        print("Gebruik:")
        print("  python goals_coach.py            → gesprek met coach")
        print("  python goals_coach.py check-in   → dagelijkse check-in")
        print("  python goals_coach.py review     → wekelijkse review")
        print("  python goals_coach.py lijst      → toon alle doelen")
