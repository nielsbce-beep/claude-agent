"""
Verplaatst alle events van vandaag naar morgen in 'Niels AI agenda'.
Gebruik: python verplaats_naar_morgen.py
"""
import sys
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env", override=True)

sys.stdout.reconfigure(encoding="utf-8")

from datetime import datetime, timedelta, date
from tools.calendar_tools import get_events, add_event, delete_event

CALENDAR = "Niels AI agenda"

today     = date.today()
tomorrow  = today + timedelta(days=1)
t_start   = datetime.combine(today, datetime.min.time())
t_end     = t_start.replace(hour=23, minute=59)

events = get_events(t_start, t_end, calendar_name=CALENDAR)

if not events:
    print("Geen events gevonden voor vandaag.")
    sys.exit(0)

print(f"Events gevonden: {len(events)}\n")

for e in events:
    s = e["start"]
    end = e["end"]
    title = e["summary"]

    # Shift naar morgen, behoud tijdstip
    if isinstance(s, datetime):
        new_start = s.replace(year=tomorrow.year, month=tomorrow.month, day=tomorrow.day, tzinfo=None)
        new_end   = end.replace(year=tomorrow.year, month=tomorrow.month, day=tomorrow.day, tzinfo=None) if end else new_start + timedelta(hours=1)
    else:
        new_start = datetime.combine(tomorrow, datetime.min.time())
        new_end   = new_start + timedelta(hours=1)

    # Verwijder vandaag
    result = delete_event(title, t_start, calendar_name=CALENDAR)
    print(f"✗ Verwijderd:  {title}  ({s.strftime('%H:%M') if isinstance(s, datetime) else s})")

    # Maak morgen aan
    result = add_event(title, new_start, new_end, calendar_name=CALENDAR)
    print(f"✓ Verplaatst:  {title}  → {new_start.strftime('%H:%M')} morgen\n")

print("Klaar.")
