import sys
import anthropic
from dotenv import load_dotenv
load_dotenv()

sys.stdout.reconfigure(encoding="utf-8")

from agents.planning_board_agent import PlanningBoardAgent
from agents.sport_agent import SportAgent
from agents.money_agent import MoneyAgent
from agents.opportunity_agent import OpportunityAgent
from agents.critic_agent import CriticAgent
from agents.motivation_agent import MotivationAgent

MODEL = "claude-sonnet-4-6"

BOARD = [
    PlanningBoardAgent(),
    SportAgent(),
    MoneyAgent(),
    OpportunityAgent(),
    CriticAgent(),
    MotivationAgent(),
]

DIVIDER = "=" * 55


def board_meeting(question: str):
    print(f"\n{DIVIDER}")
    print(f"BOARD MEETING")
    print(f'"{question}"')
    print(DIVIDER)

    responses = []
    for agent in BOARD:
        response = agent.respond(question, board_context=responses if responses else None)
        responses.append((agent.name, response))
        print(f"\n{agent.emoji} [{agent.name.upper()}]")
        print(response)

    # Consensus
    print(f"\n{DIVIDER}")
    print("CONSENSUS")
    print(DIVIDER)

    board_summary = "\n".join(f"[{name}]: {resp}" for name, resp in responses)
    client = anthropic.Anthropic()
    consensus = client.messages.create(
        model=MODEL,
        max_tokens=512,
        system="""Je bent de voorzitter van een persoonlijk life-board.
Je taak: synthetiseer de adviezen van alle board-leden tot één concreet, gebalanceerd actieplan.
Spreek in het Nederlands. Wees kort (max 5 zinnen). Geef 2-3 concrete actiepunten.
Benoem waar het board het eens is én waar spanning zit.""",
        messages=[{
            "role": "user",
            "content": f"Vraag: {question}\n\nBoard-adviezen:\n{board_summary}\n\nGeef het consensus-advies:"
        }],
    )
    print(consensus.content[0].text)
    print(f"\n{DIVIDER}\n")


def quick(agent_name: str, question: str):
    agent_map = {a.name.lower(): a for a in BOARD}
    agent = agent_map.get(agent_name.lower())
    if not agent:
        names = ", ".join(a.name for a in BOARD)
        print(f"Agent niet gevonden. Kies uit: {names}")
        return
    print(f"\n{agent.emoji} [{agent.name.upper()}]")
    print(agent.respond(question))
    print()


if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Gebruik:")
        print("  python board.py \"jouw vraag\"               → board meeting")
        print("  python board.py sport \"jouw vraag\"         → één agent")
        print("\nAgents:", ", ".join(a.name for a in BOARD))
        sys.exit(0)

    if len(sys.argv) == 2:
        board_meeting(sys.argv[1])
    else:
        quick(sys.argv[1], sys.argv[2])
