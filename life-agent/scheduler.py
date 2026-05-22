"""
Automatische dagelijkse planning — draait elke ochtend.
Start met: python scheduler.py
Of eenmalig uitvoeren: python scheduler.py --now
"""
import sys
import schedule
import time
from dotenv import load_dotenv
load_dotenv()

from agents.planning_agent import run


def ochtendplanning():
    print("=== Dagelijkse planning ===")
    result = run(
        "Goedemorgen! Maak mijn dagplan: "
        "1) Haal mijn Whoop recovery en slaapdata op. "
        "2) Bekijk mijn agenda van vandaag. "
        "3) Plan een training in op basis van mijn recovery (voeg toe aan agenda). "
        "4) Geef me 3 prioriteiten voor vandaag. "
        "Wees kort en praktisch."
    )
    print(result)
    print("===========================\n")


if __name__ == "__main__":
    if "--now" in sys.argv:
        ochtendplanning()
    else:
        schedule.every().day.at("07:30").do(ochtendplanning)
        print("Scheduler actief — dagplan wordt elke dag om 07:30 gegenereerd.")
        print("Stop met Ctrl+C\n")
        while True:
            schedule.run_pending()
            time.sleep(60)
