import sys as _sys, os as _os; _sys.path.insert(0, str(__import__("pathlib").Path(__file__).parent.parent)); import config
import anthropic
from datetime import date

client = anthropic.Anthropic()
MODEL = config.MODEL


def _build_goals_context() -> str:
    try:
        from tools.goals_store import get_active
        goals = get_active()
        if not goals:
            return ""
        today = date.today()
        lines = ["Actieve doelen van de gebruiker:"]
        for g in goals:
            done  = sum(1 for m in g["milestones"] if m["done"])
            total = len(g["milestones"])
            try:
                days_left = (date.fromisoformat(g["deadline"]) - today).days
                deadline_str = f"{g['deadline']} ({days_left}d)"
            except Exception:
                deadline_str = g.get("deadline", "?")
            last = g["check_ins"][-1]["date"][:10] if g["check_ins"] else "nooit"
            lines.append(
                f"  [{g['category']}] {g['title']} — {g['progress']}% — "
                f"{done}/{total} mijlpalen — deadline {deadline_str} — check-in {last}"
            )
        return "\n".join(lines)
    except Exception:
        return ""


class BoardAgent:
    name: str
    emoji: str
    system_prompt: str

    def respond(self, question: str, board_context: list[tuple[str, str]] = None) -> str:
        goals_ctx = _build_goals_context()
        system = self.system_prompt
        if goals_ctx:
            system += f"\n\n{goals_ctx}"

        if board_context:
            prev = "\n".join(f"[{name}]: {resp}" for name, resp in board_context)
            user_msg = f"De vraag: {question}\n\nWat andere board-leden al zeiden:\n{prev}\n\nGeef jouw perspectief. Wees kort (max 4 zinnen)."
        else:
            user_msg = f"{question}\n\nGeef jouw perspectief. Wees kort (max 4 zinnen)."

        response = client.messages.create(
            model=MODEL,
            max_tokens=512,
            system=system,
            messages=[{"role": "user", "content": user_msg}],
        )
        return response.content[0].text
