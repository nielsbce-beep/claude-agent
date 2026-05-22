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


def create_calendar(name: str) -> str:
    client = _get_client()
    principal = client.principal()
    principal.make_calendar(name=name)
    return f"Agenda '{name}' aangemaakt."


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
    def _sort_key(e):
        s = e["start"]
        if not isinstance(s, datetime):
            s = datetime.combine(s, datetime.min.time())
        if s.tzinfo is not None:
            s = s.replace(tzinfo=None)
        return s

    return sorted(result, key=_sort_key)


def _to_naive(dt) -> datetime:
    if not isinstance(dt, datetime):
        return datetime.combine(dt, datetime.min.time())
    return dt.replace(tzinfo=None) if dt.tzinfo else dt


def get_overlapping_events(
    start: datetime,
    end: datetime,
    calendar_name: str | None = None,
) -> list[dict]:
    client = _get_client()
    cal = _get_calendar(client, calendar_name)
    candidates = cal.date_search(start=start, end=end, expand=True)
    overlaps = []
    for event in candidates:
        try:
            vevent = list(event.vobject_instance.vevent_list)[0]
            e_start = _to_naive(vevent.dtstart.value)
            e_end = _to_naive(vevent.dtend.value) if hasattr(vevent, "dtend") else e_start + timedelta(hours=1)
            s = _to_naive(start)
            e = _to_naive(end)
            if e_start < e and e_end > s:
                overlaps.append({
                    "summary": str(vevent.summary.value) if hasattr(vevent, "summary") else "?",
                    "start": e_start,
                    "end": e_end,
                })
        except Exception:
            continue
    return overlaps


def add_event(
    summary: str,
    start: datetime,
    end: datetime,
    description: str = "",
    calendar_name: str | None = None,
    skip_if_overlap: bool = False,
) -> str:
    if skip_if_overlap:
        overlaps = get_overlapping_events(start, end, calendar_name)
        if overlaps:
            names = ", ".join(o["summary"] for o in overlaps)
            return f"OVERGESLAGEN: '{summary}' overlapt met: {names}"

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
