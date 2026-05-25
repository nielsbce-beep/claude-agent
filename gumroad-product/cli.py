import click
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env", override=True)

from agents.planning_agent import get_status, maak_dagplan, maak_weekplan
from tools.whoop_api import authenticate
from tools.calendar_tools import list_calendars


@click.group()
def cli():
    """Life-optimalisatie agent."""
    pass


@cli.command()
def status():
    """Whoop recovery + agenda voor vandaag en morgen."""
    print(get_status())


@cli.command()
@click.option("--geen-agenda", is_flag=True, help="Niet toevoegen aan agenda")
def dagplan(geen_agenda):
    """Maak een dagplan op basis van Whoop recovery."""
    print(maak_dagplan(toevoegen_aan_agenda=not geen_agenda))


@cli.command()
@click.option("--geen-agenda", is_flag=True, help="Niet toevoegen aan agenda")
def weekplan(geen_agenda):
    """Plan trainingen voor de komende 7 dagen."""
    print(maak_weekplan(toevoegen_aan_agenda=not geen_agenda))


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
