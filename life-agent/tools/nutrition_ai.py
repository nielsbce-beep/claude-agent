"""
AI-voedingsanalyse — schat kcal, macro's en micronutriënten van een
maaltijdomschrijving (vrije tekst) via Claude, en berekent een dynamisch
dagdoel op basis van de trainingsintensiteit van vandaag (Whoop-strain).
"""
from pathlib import Path

import anthropic
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent / ".env", override=True)

client = anthropic.Anthropic()
MODEL = "claude-sonnet-4-6"

MICRONUTRIENTEN = [
    "vitamine_c_mg", "vitamine_d_mcg", "b12_mcg", "ijzer_mg",
    "calcium_mg", "magnesium_mg", "zink_mg", "kalium_mg", "omega3_g",
]

# Indicatieve ADH/RDA voor een volwassen man — gebruikt om de micronutriëntenscore te berekenen.
RDA = {
    "vitamine_c_mg": 90, "vitamine_d_mcg": 20, "b12_mcg": 2.4, "ijzer_mg": 8,
    "calcium_mg": 1000, "magnesium_mg": 400, "zink_mg": 11, "kalium_mg": 3400, "omega3_g": 1.6,
}

LABELS = {
    "vitamine_c_mg": "Vitamine C", "vitamine_d_mcg": "Vitamine D", "b12_mcg": "B12",
    "ijzer_mg": "IJzer", "calcium_mg": "Calcium", "magnesium_mg": "Magnesium",
    "zink_mg": "Zink", "kalium_mg": "Kalium", "omega3_g": "Omega-3",
}

TOOL = {
    "name": "log_voeding",
    "description": "Sla de geschatte voedingswaarden van een maaltijd of dagomschrijving op.",
    "input_schema": {
        "type": "object",
        "properties": {
            "kcal": {"type": "number"},
            "eiwit_g": {"type": "number"},
            "koolhydraten_g": {"type": "number"},
            "vet_g": {"type": "number"},
            "vezels_g": {"type": "number"},
            "verwerkt_score": {
                "type": "number",
                "description": "0 = volledig onbewerkt/vers (groente, fruit, vlees, vis, eieren, peulvruchten, "
                               "noten, volkoren granen), 1 = ultrabewerkt (snoep, frisdrank, chips, kant-en-klaar, "
                               "fastfood, witbrood, bewerkt vlees). Gebruik de NOVA-classificatie als richtlijn, "
                               "en middel als de omschrijving meerdere producten bevat.",
            },
            "micros": {
                "type": "object",
                "description": "Geschatte hoeveelheid van elke micronutriënt in de totale omschrijving.",
                "properties": {k: {"type": "number"} for k in MICRONUTRIENTEN},
                "required": MICRONUTRIENTEN,
            },
            "toelichting": {"type": "string", "description": "Max 1 korte zin: wat valt op aan deze voeding."},
        },
        "required": ["kcal", "eiwit_g", "koolhydraten_g", "vet_g", "vezels_g", "verwerkt_score", "micros", "toelichting"],
    },
}


def analyseer(beschrijving: str) -> dict:
    """Vraagt Claude om een zo nauwkeurig mogelijke voedingswaarde-schatting (USDA/NEVO-niveau)."""
    resp = client.messages.create(
        model=MODEL, max_tokens=800,
        system=(
            "Je bent een sportdiëtist met encyclopedische kennis van voedingswaardetabellen (USDA/NEVO-niveau). "
            "Schat op basis van de omschrijving zo realistisch mogelijk de voedingswaarden in voor normale, "
            "gangbare portiegroottes als er geen hoeveelheid genoemd wordt. Wees precies en eerlijk: rond niet "
            "overdreven af, onderschat bewerkte voeding of suiker niet, en overschat groente/fruit niet. "
            "Gebruik je kennis van een Nederlands/westers voedingspatroon."
        ),
        tools=[TOOL], tool_choice={"type": "tool", "name": "log_voeding"},
        messages=[{"role": "user", "content": beschrijving}],
    )
    for block in resp.content:
        if block.type == "tool_use":
            data = dict(block.input)
            data["item"] = beschrijving
            return data
    raise ValueError("Geen voedingsanalyse ontvangen van Claude")


def dagdoel(basis_kcal: int, strain_info: dict | None) -> dict:
    """
    Dynamisch kcal- en macrodoel op basis van de trainingsintensiteit van vandaag.
    strain_info: {"strain": 0-21, "kilojoule": verbruikte energie vandaag} of None.
    """
    strain = (strain_info or {}).get("strain")
    kj = (strain_info or {}).get("kilojoule")
    verbruik_kcal = round(kj / 4.184) if kj else None

    if strain is None:
        profiel, pct = "onbekend", {"koolhydraten": 0.40, "eiwit": 0.27, "vet": 0.33}
    elif strain < 8:
        profiel, pct = "rustig", {"koolhydraten": 0.35, "eiwit": 0.30, "vet": 0.35}
    elif strain < 14:
        profiel, pct = "gemiddeld", {"koolhydraten": 0.45, "eiwit": 0.25, "vet": 0.30}
    else:
        profiel, pct = "zwaar", {"koolhydraten": 0.55, "eiwit": 0.22, "vet": 0.23}

    kcal_doel = max(basis_kcal, verbruik_kcal + 300) if verbruik_kcal else basis_kcal
    return {
        "profiel": profiel,
        "strain": strain,
        "verbruik_kcal": verbruik_kcal,
        "basis_kcal": basis_kcal,
        "kcal": kcal_doel,
        "koolhydraten_g": round(kcal_doel * pct["koolhydraten"] / 4),
        "eiwit_g": round(kcal_doel * pct["eiwit"] / 4),
        "vet_g": round(kcal_doel * pct["vet"] / 9),
    }
