"""
API-wrappers voor WK 2026 video agent.
Bronnen:
  - API-Football (api-sports.io)  → wedstrijddata, standen, uitslagen
  - The Odds API (the-odds-api.com) → bookmaker kansen
"""

import os
import requests

FOOTBALL_API_KEY = os.environ.get("FOOTBALL_API_KEY", "")
ODDS_API_KEY     = os.environ.get("ODDS_API_KEY", "")

FOOTBALL_BASE = "https://v3.football.api-sports.io"
ODDS_BASE     = "https://api.the-odds-api.com/v4"

WK_LEAGUE_ID = 1       # FIFA World Cup op api-football
WK_SEASON    = 2026
ODDS_SPORT   = "soccer_fifa_world_cup"

# Landnamen (Engels, API-Football) → ISO vlagcode
FLAG_CODES = {
    "Netherlands": "NL", "Japan": "JP", "Sweden": "SE", "Tunisia": "TN",
    "France": "FR", "Germany": "DE", "Spain": "ES", "Brazil": "BR",
    "Argentina": "AR", "England": "GB", "Portugal": "PT", "Belgium": "BE",
    "Morocco": "MA", "United States": "US", "Mexico": "MX", "Canada": "CA",
    "Australia": "AU", "Saudi Arabia": "SA", "Iran": "IR", "South Korea": "KR",
    "Uruguay": "UY", "Colombia": "CO", "Chile": "CL", "Ecuador": "EC",
    "Peru": "PE", "Paraguay": "PY", "Croatia": "HR", "Serbia": "RS",
    "Poland": "PL", "Switzerland": "CH", "Austria": "AT", "Denmark": "DK",
    "Norway": "NO", "Senegal": "SN", "Ghana": "GH", "Nigeria": "NG",
    "Cameroon": "CM", "Egypt": "EG", "Algeria": "DZ", "Ivory Coast": "CI",
    "Qatar": "QA", "United Arab Emirates": "AE", "Turkey": "TR",
    "Ukraine": "UA", "Greece": "GR", "Hungary": "HU", "Romania": "RO",
    "Costa Rica": "CR", "Panama": "PA", "Honduras": "HN", "Jamaica": "JM",
    "New Zealand": "NZ", "Japan": "JP",
}


def country_flag_code(name: str) -> str:
    return FLAG_CODES.get(name, name[:2].upper())


# ─── INTERNE REQUEST-HELPERS ──────────────────────────────────────────────────
def _football(endpoint: str, params: dict = None) -> dict:
    if not FOOTBALL_API_KEY:
        raise EnvironmentError("FOOTBALL_API_KEY niet ingesteld in .env")
    resp = requests.get(
        f"{FOOTBALL_BASE}/{endpoint}",
        headers={"x-apisports-key": FOOTBALL_API_KEY},
        params=params or {},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def _odds(endpoint: str, params: dict = None) -> dict:
    if not ODDS_API_KEY:
        raise EnvironmentError("ODDS_API_KEY niet ingesteld in .env")
    resp = requests.get(
        f"{ODDS_BASE}/{endpoint}",
        params={"apiKey": ODDS_API_KEY, **(params or {})},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


# ─── API-FOOTBALL: STANDEN ────────────────────────────────────────────────────
def get_group_standings(group_letter: str) -> list[dict]:
    """
    Haal actuele stand op voor WK-groep (bijv. group_letter="F").
    Returns lijst met dicts gesorteerd op rank.
    """
    data = _football("standings", {"league": WK_LEAGUE_ID, "season": WK_SEASON})
    all_groups = data["response"][0]["league"]["standings"]

    target = f"Group {group_letter}"
    for group in all_groups:
        if group and group[0].get("group", "") == target:
            return [
                {
                    "pos":     entry["rank"],
                    "country": entry["team"]["name"],
                    "flag":    country_flag_code(entry["team"]["name"]),
                    "points":  entry["points"],
                    "played":  entry["all"]["played"],
                    "wins":    entry["all"]["win"],
                    "draws":   entry["all"]["draw"],
                    "losses":  entry["all"]["lose"],
                    "gf":      entry["all"]["goals"]["for"],
                    "ga":      entry["all"]["goals"]["against"],
                }
                for entry in group
            ]
    raise ValueError(f"Groep {group_letter} niet gevonden. Beschikbare groepen: "
                     + ", ".join(g[0].get("group", "?") for g in all_groups if g))


# ─── API-FOOTBALL: WEDSTRIJDEN ────────────────────────────────────────────────
def get_group_fixtures(group_letter: str) -> list[dict]:
    """
    Haal alle wedstrijden op voor een WK-groep (gespeeld + gepland).
    WK-rondes staan in fixture['league']['round'] als 'Group F - Matchday 1'.
    """
    data = _football("fixtures", {"league": WK_LEAGUE_ID, "season": WK_SEASON})

    target = f"Group {group_letter}".lower()
    fixtures = []
    for f in data["response"]:
        round_str = f["league"].get("round", "").lower()
        if target not in round_str:
            continue

        status = f["fixture"]["status"]["short"]
        fixtures.append({
            "id":         f["fixture"]["id"],
            "date":       f["fixture"]["date"],
            "home":       f["teams"]["home"]["name"],
            "away":       f["teams"]["away"]["name"],
            "home_goals": f["goals"]["home"],
            "away_goals": f["goals"]["away"],
            "played":     status in ("FT", "AET", "PEN"),
        })

    return sorted(fixtures, key=lambda x: x["date"])


# ─── GECOMBINEERDE CONTEXT VOOR GROQ ─────────────────────────────────────────
def build_context_from_api(group_letter: str) -> tuple[str, list[dict]]:
    """
    Haal live WK-data op en bouw een context-string + eindstandlijst.
    Returns: (context_str, eindstand_lijst)
    eindstand_lijst heeft dicts met keys: pos, country, flag
    """
    standings = get_group_standings(group_letter)
    fixtures  = get_group_fixtures(group_letter)

    played   = [f for f in fixtures if f["played"]]
    upcoming = [f for f in fixtures if not f["played"]]

    lines = [f"Actuele stand Groep {group_letter} (WK 2026):"]
    for s in standings:
        lines.append(
            f"  {s['pos']}. {s['country']}: {s['points']}pt "
            f"({s['wins']}W {s['draws']}G {s['losses']}V, "
            f"doelpunten {s['gf']}-{s['ga']})"
        )

    if played:
        lines.append("\nGespeelde wedstrijden:")
        for f in played:
            lines.append(f"  {f['home']} {f['home_goals']}-{f['away_goals']} {f['away']}")

    if upcoming:
        lines.append("\nNog te spelen:")
        for f in upcoming:
            lines.append(f"  {f['home']} vs {f['away']}")

    context   = "\n".join(lines)
    eindstand = [
        {"pos": s["pos"], "country": s["country"].upper(), "flag": s["flag"]}
        for s in standings
    ]
    return context, eindstand


# ─── THE ODDS API: BOOKMAKER KANSEN ──────────────────────────────────────────
def get_wk_odds() -> list[dict]:
    """
    Haal 1X2-kansen op voor alle WK-wedstrijden (beste prijs per bookmaker).
    """
    data = _odds(f"sports/{ODDS_SPORT}/odds", {
        "regions":    "eu",
        "markets":    "h2h",
        "oddsFormat": "decimal",
    })

    results = []
    for event in data:
        home = event["home_team"]
        away = event["away_team"]
        best_home = best_draw = best_away = None

        for bookmaker in event.get("bookmakers", []):
            for market in bookmaker.get("markets", []):
                if market["key"] != "h2h":
                    continue
                for outcome in market["outcomes"]:
                    p = outcome["price"]
                    n = outcome["name"]
                    if n == home:
                        best_home = max(best_home or 0, p)
                    elif n == away:
                        best_away = max(best_away or 0, p)
                    elif n == "Draw":
                        best_draw = max(best_draw or 0, p)

        results.append({
            "home":       home,
            "away":       away,
            "odds_home":  best_home,
            "odds_draw":  best_draw,
            "odds_away":  best_away,
        })
    return results


def format_odds_context(fixtures: list[dict], all_odds: list[dict]) -> str:
    """Maak een leesbaar tekstblok van odds voor de Groq-prompt."""
    lines = ["Bookmaker kansen (Europees, beste odds):"]
    for f in fixtures:
        if f["played"]:
            continue
        home_l = f["home"].lower()
        away_l = f["away"].lower()
        odds = next(
            (o for o in all_odds
             if home_l in o["home"].lower() and away_l in o["away"].lower()),
            None,
        )
        if odds and odds["odds_home"]:
            lines.append(
                f"  {f['home']} vs {f['away']}: "
                f"thuis {odds['odds_home']:.2f} | "
                f"gelijk {odds['odds_draw']:.2f} | "
                f"uit {odds['odds_away']:.2f}"
            )
    return "\n".join(lines) if len(lines) > 1 else ""


# ─── HULP: BESCHIKBARE WK-SPORTS ─────────────────────────────────────────────
def list_wk_sports() -> list[str]:
    """Toon welke WK-sportsleutels beschikbaar zijn in The Odds API."""
    data = _odds("sports")
    return [s["key"] for s in data if "world_cup" in s["key"].lower() or "fifa" in s["key"].lower()]
