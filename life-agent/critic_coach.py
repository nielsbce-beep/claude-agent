import sys
import json
import anthropic
from datetime import datetime
from dotenv import load_dotenv
load_dotenv()

sys.stdout.reconfigure(encoding="utf-8")

from tools.goals_store import get_active, format_goals_summary

client = anthropic.Anthropic()
MODEL = "claude-sonnet-4-6"
TODAY = datetime.now().strftime("%A %d %B %Y")

SYSTEM_PROMPT = f"""Je bent de Criticus — een onbarmhartige maar opbouwende gesprekspartner.
Je spreekt altijd in het Nederlands. Je doel: de gebruiker slimmer maken door hun denken te challengen.

Jouw rol:
- Benoem aannames die de gebruiker niet uitspreekt maar wel maakt
- Wijs op tegenstrijdigheden tussen wat de gebruiker zegt en wat hij doet
- Stel de harde vraag die anderen vermijden
- Leg blinde vlekken bloot: optimisme bias, sunk cost, uitstellen via planning
- Accepteer geen vage plannen of mooie praatjes zonder bewijs
- Als iemand zegt "ik ga X doen" — vraag WHY NOW en wat hem eerder heeft tegengehouden
- Trek motivaties in twijfel als ze oppervlakkig klinken
- Houd bij wat de gebruiker eerder zei en wijs op inconsistenties in het gesprek

Je bent NIET negatief of destructief. Je helpt de gebruiker betere, eerlijkere beslissingen nemen.
Je bent scherp, direct, en ongenadig eerlijk — maar altijd met respect.

Stijl:
- Kort en krachtig. Geen lange lezingen.
- Stel één scherpe vraag per bericht, of benoem één concrete zwakte.
- Sluit nooit af met bemoediging tenzij echt verdiend.
- Zeg wat de gebruiker NIET wil horen als het de waarheid is.

Vandaag is: {TODAY}

Je hebt toegang tot de doelen van de gebruiker als context. Gebruik dit om inconsistenties
te spotten tussen wat de gebruiker zegt en wat hij werkelijk prioriteert."""


def _build_goals_context() -> str:
    goals = get_active()
    if not goals:
        return ""
    lines = ["Actieve doelen van de gebruiker (gebruik dit om inconsistenties te spotten):"]
    for g in goals:
        done = sum(1 for m in g["milestones"] if m["done"])
        total = len(g["milestones"])
        last_checkin = ""
        if g["check_ins"]:
            last = g["check_ins"][-1]
            last_checkin = f" | Laatste check-in: {last['date'][:10]}"
        lines.append(
            f"  [{g['id']}] {g['title']} — {g['progress']}% — {done}/{total} mijlpalen"
            f" — deadline {g['deadline']}{last_checkin}"
        )
    return "\n".join(lines)


def challenge(topic: str | None = None):
    print("\n" + "=" * 55)
    print("CRITICUS")
    print(f"{TODAY}")
    print("=" * 55)
    print("Vertel je plan, idee of beslissing — ik challenge het.")
    print("Typ 'stop' om te stoppen.\n")

    goals_context = _build_goals_context()
    system = SYSTEM_PROMPT
    if goals_context:
        system += f"\n\n{goals_context}"

    history = []

    # Optioneel: start met een topic als meegegeven via CLI
    if topic:
        first_msg = topic
    else:
        try:
            first_msg = input("Jij: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nGeen input. Stop.")
            return

    if not first_msg or first_msg.lower() in ("stop", "exit"):
        return

    history.append({"role": "user", "content": first_msg})

    while True:
        response = client.messages.create(
            model=MODEL,
            max_tokens=512,
            system=system,
            messages=history,
        )
        reply = response.content[0].text.strip()
        print(f"\nCriticus: {reply}\n")
        history.append({"role": "assistant", "content": reply})

        try:
            user_input = input("Jij: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nTot de volgende keer.")
            break

        if user_input.lower() in ("stop", "exit", "quit"):
            print("Tot de volgende keer.")
            break
        if not user_input:
            continue

        history.append({"role": "user", "content": user_input})


def roast():
    """Eenmalige kritische analyse van alle actieve doelen."""
    goals = get_active()
    if not goals:
        print("Geen actieve doelen om te challengen.")
        return

    print(f"\n{'='*55}\nDOELEN ROAST — {TODAY}\n{'='*55}")
    summary = format_goals_summary()

    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": (
                f"Dit zijn mijn actieve doelen:\n{summary}\n\n"
                "Geef een ongenadige maar eerlijke analyse: "
                "welke doelen zijn vaag, onrealistisch, tegenstrijdig of gewoon wishful thinking? "
                "Waar is de kans het grootst dat ik mezelf voor de gek houd? "
                "Wees concreet en direct."
            )
        }],
    )
    print(f"\nCriticus: {response.content[0].text.strip()}\n")


def blind_spots():
    """Vraagt de criticus om blinde vlekken te benoemen op basis van alle doelen samen."""
    goals = get_active()
    if not goals:
        print("Geen actieve doelen.")
        return

    print(f"\n{'='*55}\nBLINDE VLEKKEN ANALYSE — {TODAY}\n{'='*55}")

    lines = []
    for g in goals:
        done = sum(1 for m in g["milestones"] if m["done"])
        total = len(g["milestones"])
        lines.append(
            f"[{g['id']}] {g['title']} ({g['category']}) — "
            f"{g['progress']}% — {done}/{total} mijlpalen — deadline {g['deadline']}"
        )
    doelen_tekst = "\n".join(lines)

    response = client.messages.create(
        model=MODEL,
        max_tokens=1024,
        system=SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": (
                f"Dit zijn al mijn actieve doelen:\n{doelen_tekst}\n\n"
                "Analyseer het totaalplaatje: "
                "1) Welke doelen bijten elkaar (tijd, energie, focus)? "
                "2) Wat ontbreekt er in mijn doelen dat ik waarschijnlijk wél zou moeten hebben? "
                "3) Welke aanname zit in bijna al mijn doelen die mogelijk fout is? "
                "Wees concreet. Max 5 zinnen per punt."
            )
        }],
    )
    print(f"\nCriticus: {response.content[0].text.strip()}\n")


if __name__ == "__main__":
    args = sys.argv[1:]

    if not args or args[0] == "chat":
        topic = " ".join(args[1:]) if len(args) > 1 else None
        challenge(topic)
    elif args[0] == "roast":
        roast()
    elif args[0] == "blindspot":
        blind_spots()
    else:
        print("Gebruik:")
        print("  python critic_coach.py                    → gesprek met de criticus")
        print('  python critic_coach.py chat "mijn plan"   → begin direct met een onderwerp')
        print("  python critic_coach.py roast              → kritische analyse van al je doelen")
        print("  python critic_coach.py blindspot          → blinde vlekken in je totaalplaatje")
