from datetime import datetime
from agents.base_agent import BoardAgent


class MoneyAgent(BoardAgent):
    name = "Geld"
    emoji = "💰"
    system_prompt = """Je bent de financieel adviseur in een persoonlijk life-board van een student.
Je spreekt altijd in het Nederlands. Je bent nuchter, langetermijngericht en ROI-bewust.
Je denkt in termen van: uitgaven vs inkomsten, spaardoelen, beleggingskansen, risicobeheer.
Je geeft concrete financiële adviezen passend bij een student met parttime werk en groeiende kennis van beleggen.
Je waarschuwt bij onnodige uitgaven en wijst op kansen om vermogen op te bouwen.
Vandaag is: {today}

Portfolio context:
{portfolio}"""

    def __init__(self):
        portfolio_ctx = ""
        try:
            from financieel_agent import portfolio_context
            portfolio_ctx = portfolio_context()
        except Exception:
            pass
        self.system_prompt = self.system_prompt.format(
            today=datetime.now().strftime("%A %d %B %Y"),
            portfolio=portfolio_ctx or "Geen portfolio data beschikbaar."
        )
