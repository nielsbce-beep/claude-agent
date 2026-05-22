import json
import os
from datetime import datetime, timedelta
import anthropic
from tools import whoop_api, calendar_tools

client = anthropic.Anthropic()
MODEL = "claude-opus-4-7"

TOOLS = [
    {
        "name": "get_whoop_recovery",
        "description": "Haal de laatste recovery score, HRV en slaapkwaliteit op uit Whoop.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_whoop_sleep",
        "description": "Haal de laatste slaapdata op uit Whoop (duur, efficiency, slaapscores).",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_whoop_strain",
        "description": "Haal de dagelijkse strain/belasting op uit Whoop.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
    {
        "name": "get_calendar_events",
        "description": "Haal agenda-afspraken op voor een bepaalde periode.",
        "input_schema": {
            "type": "object",
            "properties": {
                "days_ahead": {
                    "type": "integer",
                    "description": "Hoeveel dagen vooruit kijken (standaard 7)",
                },
                "calendar_name": {
                    "type": "string",
                    "description": "Naam van de agenda (optioneel, pakt standaard agenda)",
                },
            },
            "required": [],
        },
    },
    {
        "name": "add_calendar_event",
        "description": "Voeg een afspraak of training toe aan de agenda.",
        "input_schema": {
            "type": "object",
            "properties": {
                "summary": {"type": "string", "description": "Titel van de afspraak"},
                "start_iso": {"type": "string", "description": "Starttijd in ISO-8601 formaat, bijv. 2025-05-22T07:00:00"},
                "end_iso": {"type": "string", "description": "Eindtijd in ISO-8601 formaat"},
                "description": {"type": "string", "description": "Optionele beschrijving of notities"},
                "calendar_name": {"type": "string", "description": "Naam van de agenda (optioneel)"},
            },
            "required": ["summary", "start_iso", "end_iso"],
        },
    },
    {
        "name": "list_calendars",
        "description": "Geef een lijst van beschikbare agenda's in iCloud.",
        "input_schema": {"type": "object", "properties": {}, "required": []},
    },
]

SYSTEM_PROMPT = """Je bent een persoonlijke life-optimalisatie agent. Je helpt de gebruiker hun dag en week te plannen op basis van:
- Whoop recovery en slaapdata (als de recovery laag is, plan je lichtere trainingen)
- Bestaande agenda-afspraken
- De wensen van de gebruiker

Spreek altijd in het Nederlands. Wees direct en praktisch. Als je trainingen plant, houd dan rekening met:
- Recovery score 0-33%: alleen lichte activiteit of rust
- Recovery score 34-66%: matige training
- Recovery score 67-100%: zware training mogelijk

Vandaag is: {today}"""


def _execute_tool(name: str, inputs: dict) -> str:
    try:
        if name == "get_whoop_recovery":
            data = whoop_api.get_latest_recovery()
            return json.dumps(data, default=str)
        elif name == "get_whoop_sleep":
            data = whoop_api.get_latest_sleep()
            return json.dumps(data, default=str)
        elif name == "get_whoop_strain":
            data = whoop_api.get_todays_strain()
            return json.dumps(data, default=str)
        elif name == "get_calendar_events":
            days = inputs.get("days_ahead", 7)
            cal_name = inputs.get("calendar_name")
            start = datetime.now()
            end = start + timedelta(days=days)
            events = calendar_tools.get_events(start, end, cal_name)
            return json.dumps(events, default=str)
        elif name == "add_calendar_event":
            start = datetime.fromisoformat(inputs["start_iso"])
            end = datetime.fromisoformat(inputs["end_iso"])
            result = calendar_tools.add_event(
                summary=inputs["summary"],
                start=start,
                end=end,
                description=inputs.get("description", ""),
                calendar_name=inputs.get("calendar_name"),
            )
            return result
        elif name == "list_calendars":
            cals = calendar_tools.list_calendars()
            return json.dumps(cals)
        else:
            return f"Onbekende tool: {name}"
    except Exception as e:
        return f"Fout bij uitvoeren van {name}: {e}"


def run(user_message: str) -> str:
    messages = [{"role": "user", "content": user_message}]
    system = SYSTEM_PROMPT.format(today=datetime.now().strftime("%A %d %B %Y"))

    while True:
        response = client.messages.create(
            model=MODEL,
            max_tokens=4096,
            system=system,
            tools=TOOLS,
            messages=messages,
        )

        if response.stop_reason == "end_turn":
            return next(
                (block.text for block in response.content if hasattr(block, "text")),
                "(geen antwoord)"
            )

        if response.stop_reason == "tool_use":
            messages.append({"role": "assistant", "content": response.content})
            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result = _execute_tool(block.name, block.input)
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": block.id,
                        "content": result,
                    })
            messages.append({"role": "user", "content": tool_results})
        else:
            break

    return "(onverwacht einde van gesprek)"
