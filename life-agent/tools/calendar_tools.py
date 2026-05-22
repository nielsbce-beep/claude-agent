import os
from datetime import datetime, timedelta
import caldav
from caldav.elements import dav
import vobject

ICLOUD_URL = "https://caldav.icloud.com"


def _get_client() -> caldav.DAVClient:
    return caldav.DAVClient(
        url=ICLOUD_URL,
        username=os.environ["ICLOUD_USERNAME"],
        password=os.environ["ICLOUD_APP_PASSWORD"],
    )


def _get_calendar(client: caldav.DAVClient, calendar_name: str | None = None):
    principal = client.principal()
    calendars = principal.calendars()
    if not calendars:
        raise RuntimeError("Geen agenda's gevonden in iCloud.")
    if calendar_name:
        for cal in calendars:
            props = cal.get_properties([dav.DisplayName()])
            name = props.get("{DAV:}displayname", "")
            if name.lower() == calendar_name.lower():
                return cal
        raise ValueError(f"Agenda '{calendar_name}' niet gevonden.")
    return calendars[0]


def list_calendars() -> list[str]:
    client = _get_client()
    principal = client.principal()
    result = []
    for cal in principal.calendars():
        props = cal.get_properties([dav.DisplayName()])
        result.append(props.get("{DAV:}displayname", "Onbekend"))
    return result


def get_events(start: datetime, end: datetime, calendar_name: str | None = None) -> list[dict]:
    client = _get_client()
    cal = _get_calendar(client, calendar_name)
    events = cal.date_search(start=start, end=end, expand=True)
    result = []
    for event in events:
        try:
            vevent = list(event.vobject_instance.vevent_list)[0]
            result.append({
                "summary": str(vevent.summary.value) if hasattr(vevent, "summary") else "(geen titel)",
                "start": vevent.dtstart.value,
                "end": vevent.dtend.value if hasattr(vevent, "dtend") else None,
            })
        except Exception:
            continue
    return sorted(result, key=lambda e: e["start"] if isinstance(e["start"], datetime) else datetime.combine(e["start"], datetime.min.time()))


def add_event(
    summary: str,
    start: datetime,
    end: datetime,
    description: str = "",
    calendar_name: str | None = None,
) -> str:
    client = _get_client()
    cal = _get_calendar(client, calendar_name)

    cal_obj = vobject.iCalendar()
    vevent = cal_obj.add("vevent")
    vevent.add("summary").value = summary
    vevent.add("dtstart").value = start
    vevent.add("dtend").value = end
    if description:
        vevent.add("description").value = description
    vevent.add("uid").value = f"{summary.replace(' ', '_')}_{start.isoformat()}@life-agent"

    cal.save_event(cal_obj.serialize())
    return f"Event '{summary}' aangemaakt op {start.strftime('%d-%m-%Y %H:%M')}"


def delete_event(summary: str, date: datetime, calendar_name: str | None = None) -> str:
    client = _get_client()
    cal = _get_calendar(client, calendar_name)
    start = date.replace(hour=0, minute=0, second=0)
    end = date.replace(hour=23, minute=59, second=59)
    events = cal.date_search(start=start, end=end, expand=True)
    for event in events:
        try:
            vevent = list(event.vobject_instance.vevent_list)[0]
            if str(vevent.summary.value).lower() == summary.lower():
                event.delete()
                return f"Event '{summary}' verwijderd."
        except Exception:
            continue
    return f"Event '{summary}' op {date.strftime('%d-%m-%Y')} niet gevonden."
