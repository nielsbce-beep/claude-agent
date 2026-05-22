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
import avond_checkin
import weekly_review
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
        schedule.every().day.at("21:00").do(avond_checkin.run)
        schedule.every().sunday.at("10:00").do(weekly_review.run)
        print("Scheduler actief:")
        print("  07:00 — Morning briefing")
        print("  07:30 — Dagelijkse planning (Whoop + agenda + training)")
        print("  21:00 — Avond check-in")
        print("  Zondag 10:00 — Wekelijkse review")
        print("Stop met Ctrl+C\n")
        while True:
            schedule.run_pending()
            time.sleep(60)
