import click
from dotenv import load_dotenv
load_dotenv()

from agents.planning_agent import run
from tools.whoop_api import authenticate
from tools.calendar_tools import list_calendars


@click.group()
def cli():
    """Life-optimalisatie agent."""
    pass


@cli.command()
@click.argument("bericht")
def chat(bericht):
    """Stuur een bericht naar de planning agent.

    Voorbeeld: python cli.py chat "Plan mijn trainingen voor deze week"
    """
    print(run(bericht))


@cli.command()
def dagplan():
    """Genereer automatisch een dagplan op basis van Whoop data en agenda."""
    result = run(
        "Kijk naar mijn Whoop recovery en slaapdata van vandaag. "
        "Bekijk ook mijn agenda voor de komende 3 dagen. "
        "Geef me een concreet dagplan: wanneer trainen, hoe intensief, en wat zijn de prioriteiten. "
        "Voeg de training ook toe aan mijn agenda."
    )
    print(result)


@cli.command()
def weekplan():
    """Genereer een volledig weektrainingsschema."""
    result = run(
        "Maak een trainingsschema voor de komende 7 dagen. "
        "Gebruik mijn Whoop recovery data om de intensiteit te bepalen. "
        "Houd rekening met bestaande agenda-afspraken. "
        "Voeg alle trainingen toe aan mijn agenda met tijden en beschrijvingen."
    )
    print(result)


@cli.command()
def status():
    """Toon huidige Whoop recovery en agenda voor vandaag."""
    result = run(
        "Geef me een kort overzicht: "
        "1) Mijn huidige recovery score en slaapkwaliteit van Whoop. "
        "2) Mijn afspraken van vandaag en morgen. "
        "3) Aanbeveling: wel of niet zwaar trainen vandaag?"
    )
    print(result)


@cli.command()
def whoop_login():
    """Authenticeer met Whoop (eerste keer instellen)."""
    authenticate()


@cli.command()
def agendas():
    """Toon beschikbare iCloud agenda's."""
    cals = list_calendars()
    for cal in cals:
        print(f"  - {cal}")


if __name__ == "__main__":
    cli()
