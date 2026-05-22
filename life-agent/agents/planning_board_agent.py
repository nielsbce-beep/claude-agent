from datetime import datetime, timedelta
from agents.base_agent import BoardAgent
from tools import calendar_tools


class PlanningBoardAgent(BoardAgent):
    name = "Planning"
    emoji = "📅"
    system_prompt = """Je bent de planning- en tijdsbeheeradviseur in een persoonlijk life-board.
Je spreekt altijd in het Nederlands. Je bent gestructureerd, realistisch over tijd en prioriteiten.
Je kijkt altijd naar de agenda: wat staat er deze week, wanneer zijn deadlines, waar zit ruimte.
Je waarschuwt bij overbelasting en adviseert concrete tijdsblokken.
Vandaag is: {today}"""

    def __init__(self):
        self.system_prompt = self.system_prompt.format(today=datetime.now().strftime("%A %d %B %Y"))

    def respond(self, question: str, board_context=None) -> str:
        try:
            now = datetime.now()
            events = calendar_tools.get_events(now, now + timedelta(days=7), "Niels AI agenda")
            agenda = "\n".join(f"- {e['start'].strftime('%a %d %b %H:%M') if hasattr(e['start'], 'strftime') else str(e['start'])}: {e['summary']}" for e in events[:10])
            agenda_context = f"\nAgenda komende 7 dagen:\n{agenda}" if events else ""
        except Exception:
            agenda_context = ""

        import anthropic
        client = anthropic.Anthropic()
        from agents.base_agent import MODEL

        prev = ""
        if board_context:
            prev = "\n".join(f"[{n}]: {r}" for n, r in board_context)
            user_msg = f"De vraag: {question}{agenda_context}\n\nAndere board-leden:\n{prev}\n\nJouw planningsperspectief (max 4 zinnen):"
        else:
            user_msg = f"{question}{agenda_context}\n\nJouw planningsperspectief (max 4 zinnen):"

        resp = client.messages.create(
            model=MODEL, max_tokens=512,
            system=self.system_prompt,
            messages=[{"role": "user", "content": user_msg}],
        )
        return resp.content[0].text
