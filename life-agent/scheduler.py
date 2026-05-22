"""
Automatische dagelijkse taken — draait elke ochtend.
Start met: python scheduler.py
Of eenmalig uitvoeren: python scheduler.py --now
"""
import sys
import schedule
import time
from dotenv import load_dotenv
load_dotenv()

import morning_briefing
from agents.planning_agent import run


def ochtend_briefing():
    morning_briefing.run()


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
        ochtend_briefing()
        ochtendplanning()
    else:
        schedule.every().day.at("07:00").do(ochtend_briefing)
        schedule.every().day.at("07:30").do(ochtendplanning)
        print("Scheduler actief:")
        print("  07:00 — Morning briefing")
        print("  07:30 — Dagelijkse planning (Whoop + agenda + training)")
        print("Stop met Ctrl+C\n")
        while True:
            schedule.run_pending()
            time.sleep(60)
