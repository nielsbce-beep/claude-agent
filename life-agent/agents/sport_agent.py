from datetime import datetime
from agents.base_agent import BoardAgent
from tools import whoop_api


class SportAgent(BoardAgent):
    name = "Sport"
    emoji = "💪"
    system_prompt = """Je bent de sport- en gezondheidsadviseur in een persoonlijk life-board.
Je spreekt altijd in het Nederlands. Je bent direct, no-nonsense en evidence-based.
Je beoordeelt alles vanuit fysieke prestaties, herstel en gezondheid op de lange termijn.
Je gebruikt Whoop-data (recovery, HRV, slaap) als die beschikbaar is.
Je geeft concrete adviezen: wat te trainen, wanneer te rusten, hoe te progresseren.
Vandaag is: {today}"""

    def __init__(self):
        self.system_prompt = self.system_prompt.format(today=datetime.now().strftime("%A %d %B %Y"))

    def respond(self, question: str, board_context=None) -> str:
        try:
            recovery = whoop_api.get_latest_recovery()
            score = recovery.get("score", {}).get("recovery_score")
            hrv = recovery.get("score", {}).get("hrv_rmssd_milli")
            slaap = recovery.get("score", {}).get("sleep_performance_percentage")
            whoop_context = f"\nWhoop data vandaag: recovery {score:.0f}%, HRV {hrv:.0f}ms, slaap {slaap:.0f}%" if score else ""
        except Exception:
            whoop_context = ""

        import anthropic
        client = anthropic.Anthropic()
        from agents.base_agent import MODEL

        prev = ""
        if board_context:
            prev = "\n".join(f"[{n}]: {r}" for n, r in board_context)
            user_msg = f"De vraag: {question}{whoop_context}\n\nAndere board-leden:\n{prev}\n\nJouw sportperspectief (max 4 zinnen):"
        else:
            user_msg = f"{question}{whoop_context}\n\nJouw sportperspectief (max 4 zinnen):"

        resp = client.messages.create(
            model=MODEL, max_tokens=512,
            system=self.system_prompt,
            messages=[{"role": "user", "content": user_msg}],
        )
        return resp.content[0].text
