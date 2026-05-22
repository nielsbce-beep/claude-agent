import anthropic

client = anthropic.Anthropic()
MODEL = "claude-sonnet-4-6"


class BoardAgent:
    name: str
    emoji: str
    system_prompt: str

    def respond(self, question: str, board_context: list[tuple[str, str]] = None) -> str:
        messages = []

        if board_context:
            prev = "\n".join(f"[{name}]: {resp}" for name, resp in board_context)
            messages.append({
                "role": "user",
                "content": f"De vraag: {question}\n\nWat andere board-leden al zeiden:\n{prev}\n\nGeef jouw perspectief. Wees kort (max 4 zinnen).",
            })
        else:
            messages.append({
                "role": "user",
                "content": f"{question}\n\nGeef jouw perspectief. Wees kort (max 4 zinnen).",
            })

        response = client.messages.create(
            model=MODEL,
            max_tokens=512,
            system=self.system_prompt,
            messages=messages,
        )
        return response.content[0].text
