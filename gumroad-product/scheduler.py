"""
Automatische dagelijkse taken — draait elke ochtend.
Start met: python scheduler.py
Of eenmalig uitvoeren: python scheduler.py --now
"""
import sys
import schedule
import time
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env", override=True)

import morning_briefing
import avond_checkin
import weekly_review
from agents.planning_agent import maak_dagplan


def ochtend_briefing():
    morning_briefing.run()


def ochtendplanning():
    print("=== Dagelijkse planning ===")
    result = maak_dagplan(toevoegen_aan_agenda=True)
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
