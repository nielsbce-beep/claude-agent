"""
Morning briefing — run daily at 07:00.
Pulls Whoop, calendar, goals and growth log into one scannable overview.
Claude only generates the 3 focus priorities at the bottom.
"""
import sys
import json
import anthropic
from datetime import datetime, date, timedelta
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env", override=True)

sys.stdout.reconfigure(encoding="utf-8")

from tools.calendar_tools import get_events
from tools.goals_store import get_active
from tools.whoop_api import get_latest_recovery, get_latest_sleep
from tools.whoop_history import (
    get_today_from_csv, get_recovery_trend, get_sleep_trend,
    get_training_summary, get_overtraining_signal,
)
from journal_agent import context_voor_agents as _journal_context, _recent_entries

client = anthropic.Anthropic()
MODEL = "claude-sonnet-4-6"
GROWTH_LOG = Path(__file__).parent / "data" / "growth_log.json"
W = 57  # line width


# ── Helpers ────────────────────────────────────────────────────────────────────

def _bar(value: int, width: int = 20) -> str:
    filled = int(value / 100 * width)
    return "█" * filled + "░" * (width - filled)


def _urgency_icon(days: int) -> str:
    if days <= 7:   return "🔴"
    if days <= 14:  return "🟠"
    if days <= 30:  return "🟡"
    return "🟢"


def _recovery_label(score: int) -> str:
    if score >= 67: return "Groen — normaal trainen"
    if score >= 50: return "Geel — matige training"
    if score >= 34: return "Oranje — lichte beweging"
    return "Rood — rust vandaag"


def _load_growth_log() -> dict:
    if GROWTH_LOG.exists():
        return json.loads(GROWTH_LOG.read_text(encoding="utf-8"))
    return {"entries": []}


def _yesterday_commitment() -> dict | None:
    data = _load_growth_log()
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    for e in reversed(data["entries"]):
        if e["date"] == yesterday:
            return e
    return None


def _today_commitment() -> dict | None:
    data = _load_growth_log()
    today = date.today().isoformat()
    for e in reversed(data["entries"]):
        if e["date"] == today:
            return e
    return None


# ── Data fetchers ──────────────────────────────────────────────────────────────

def _fetch_whoop() -> dict:
    # Try live API first; fall back to today's CSV row if cycle is still open
    data = {}
    try:
        recovery = get_latest_recovery()
        sleep    = get_latest_sleep()
        score    = recovery.get("score", {})
        sleep_score = sleep.get("score", {})
        if score.get("recovery_score"):
            data = {
                "recovery_pct":  round(score["recovery_score"]),
                "hrv_ms":        round(score.get("hrv_rmssd_milli", 0)),
                "rhr":           round(score.get("resting_heart_rate", 0)),
                "sleep_hours":   round(
                    sleep.get("score", {}).get("total_in_bed_time_milli", 0) / 3_600_000, 1
                ),
                "sleep_quality": round(sleep_score.get("sleep_performance_percentage", 0)),
                "source":        "live",
            }
    except Exception:
        pass

    if not data.get("recovery_pct"):
        # Fall back to CSV
        today = get_today_from_csv()
        if today and today.get("recovery"):
            data = {
                "recovery_pct":  round(today["recovery"]),
                "hrv_ms":        round(today["hrv"] or 0),
                "rhr":           round(today["rhr"] or 0),
                "sleep_hours":   round((today["sleep_min"] or 0) / 60, 1),
                "sleep_quality": round(today["sleep_perf"] or 0),
                "source":        "csv",
            }

    # Always attach 14-day trend from CSV
    trend = get_recovery_trend(14)
    if trend:
        data["trend_avg"]   = trend.get("avg")
        data["trend_arrow"] = trend.get("trend")
        data["best_day"]    = trend.get("best_day")
        data["worst_day"]   = trend.get("worst_day")
        data["hrv_avg"]     = trend.get("hrv_avg")

    sleep_t = get_sleep_trend(14)
    if sleep_t:
        data["sleep_avg_hours"] = sleep_t.get("avg_hours")
        data["deep_avg_min"]    = sleep_t.get("avg_deep_min")

    training = get_training_summary(14)
    if training:
        data["training_per_week"] = training.get("per_week")
        data["top_activity"]      = training.get("top_activity")

    data["overtraining"] = get_overtraining_signal()
    return data


def _fetch_calendar() -> list[dict]:
    try:
        today_start = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
        today_end   = today_start.replace(hour=23, minute=59)
        events = get_events(today_start, today_end, calendar_name="Niels AI agenda")
        return events
    except Exception:
        return []


def _fetch_goals() -> list[dict]:
    try:
        return get_active()
    except Exception:
        return []


# ── Section builders ───────────────────────────────────────────────────────────

def _section_whoop(w: dict) -> list[str]:
    lines = ["HERSTEL (WHOOP)"]
    if not w or w.get("recovery_pct") is None:
        lines.append("  Geen Whoop data beschikbaar.")
        return lines

    pct    = w["recovery_pct"]
    source = " (csv)" if w.get("source") == "csv" else ""
    lines.append(f"  Score    {pct}%  {_bar(pct, 18)}{source}")
    if w.get("hrv_ms"):
        lines.append(f"  HRV      {w['hrv_ms']} ms")
    if w.get("rhr"):
        lines.append(f"  Rusthf   {w['rhr']} bpm")
    if w.get("sleep_hours"):
        lines.append(f"  Slaap    {w['sleep_hours']}u  (kwaliteit {w.get('sleep_quality', '?')}%)")
    lines.append(f"  Advies   {_recovery_label(pct)}")

    # 14-day trend
    if w.get("trend_avg"):
        lines.append(
            f"  14-dag   gem. {w['trend_avg']}%  HRV {w.get('hrv_avg')}ms  "
            f"trend {w.get('trend_arrow', '?')}"
        )
    if w.get("best_day"):
        lines.append(
            f"  Patroon  beste dag: {w['best_day']}  |  "
            f"slechtste: {w.get('worst_day', '?')}"
        )
    if w.get("sleep_avg_hours"):
        lines.append(
            f"  Slaap14  gem. {w['sleep_avg_hours']}u  "
            f"diepe slaap {w.get('deep_avg_min', '?')} min/nacht"
        )
    if w.get("training_per_week"):
        lines.append(
            f"  Training {w['training_per_week']}x/week  "
            f"meest: {w.get('top_activity', '?')}"
        )
    if w.get("overtraining"):
        lines.append(f"  {w['overtraining']}")

    return lines


def _section_calendar(events: list[dict]) -> list[str]:
    lines = ["AGENDA VANDAAG"]
    if not events:
        lines.append("  Geen events gevonden.")
        return lines
    for e in events:
        s = e["start"]
        if hasattr(s, "hour"):
            time_str = f"{s.hour:02d}:{s.minute:02d}"
        else:
            time_str = "     "
        title = str(e["summary"])
        # Trim long titles
        if len(title) > 40:
            title = title[:38] + ".."
        lines.append(f"  {time_str}  {title}")
    return lines


def _section_goals(goals: list[dict]) -> list[str]:
    lines = ["DOELEN — URGENTIE"]
    today = date.today()
    urgent = []
    for g in goals:
        if not g.get("deadline"):
            continue
        try:
            dl = date.fromisoformat(g["deadline"])
            days_left = (dl - today).days
            urgent.append((days_left, g))
        except Exception:
            continue

    urgent.sort(key=lambda x: x[0])
    shown = 0
    for days_left, g in urgent:
        if shown >= 6:
            break
        icon = _urgency_icon(days_left)
        pct = g["progress"]
        title = g["title"]
        if len(title) > 32:
            title = title[:30] + ".."
        lines.append(f"  {icon}  {title}")
        lines.append(f"      {days_left} dagen  |  {pct}%  {_bar(pct, 12)}")
        shown += 1

    if not shown:
        lines.append("  Geen deadlines gevonden.")
    return lines


def _section_commitment() -> list[str]:
    lines = ["GISTEREN GEZEGD"]
    entry = _yesterday_commitment()
    if not entry:
        lines.append("  Geen commitment gevonden.")
        return lines

    text = entry["commitment"]
    if len(text) > 48:
        text = text[:46] + ".."
    status = entry.get("achieved")
    if status is True:
        icon = "✓ nagekomen"
    elif status is False:
        icon = "✗ NIET nagekomen"
    else:
        icon = "· nog niet gecheckt"
    lines.append(f"  \"{text}\"")
    lines.append(f"  {icon}")
    return lines


def _section_focus(whoop: dict, events: list[dict], goals: list[dict], commitment: dict | None, journal_ctx: str = "") -> list[str]:
    """Ask Claude for 3 concrete focus points based on all data."""
    today = date.today()

    # Build a tight context string for Claude
    ctx_parts = []

    if whoop.get("recovery_pct") is not None:
        ctx_parts.append(
            f"Whoop herstel: {whoop['recovery_pct']}% | HRV: {whoop['hrv_ms']}ms | "
            f"Slaap: {whoop['sleep_hours']}u ({whoop['sleep_quality']}%)"
        )

    if events:
        ev_str = ", ".join(
            f"{e['start'].strftime('%H:%M') if hasattr(e['start'], 'hour') else '?'} {e['summary']}"
            for e in events
        )
        ctx_parts.append(f"Agenda vandaag: {ev_str}")

    urgent_goals = []
    for g in goals:
        if not g.get("deadline"):
            continue
        try:
            days = (date.fromisoformat(g["deadline"]) - today).days
            if days <= 35:
                urgent_goals.append(f"{g['title']} ({days} dagen, {g['progress']}%)")
        except Exception:
            continue
    if urgent_goals:
        ctx_parts.append("Urgente doelen: " + "; ".join(urgent_goals))

    if commitment and commitment.get("achieved") is False:
        ctx_parts.append(f"Gisteren NIET nagekomen: \"{commitment['commitment']}\"")
    elif commitment and commitment.get("achieved") is None:
        ctx_parts.append(f"Open commitment van gisteren: \"{commitment['commitment']}\"")

    if journal_ctx:
        ctx_parts.append(journal_ctx)

    context = "\n".join(ctx_parts) if ctx_parts else "Geen data beschikbaar."

    try:
        response = client.messages.create(
            model=MODEL,
            max_tokens=256,
            system=(
                "Je bent een extreem directe ochtendcoach. "
                "Geef op basis van de data exact 3 focuspunten voor vandaag. "
                "Elk punt is concreet, meetbaar en haalbaar vandaag. "
                "Geen inleiding. Geen uitleg. Alleen de 3 punten, genummerd. "
                "Nederlands. Max 10 woorden per punt."
            ),
            messages=[{
                "role": "user",
                "content": f"Data:\n{context}\n\nGeef 3 focuspunten voor vandaag:"
            }],
        )
        raw = response.content[0].text.strip()
        lines = ["FOCUS VANDAAG"]
        for line in raw.splitlines():
            line = line.strip()
            if line:
                lines.append(f"  {line}")
        return lines
    except Exception as e:
        return ["FOCUS VANDAAG", f"  (API fout: {e})"]


# ── Main ───────────────────────────────────────────────────────────────────────

def run():
    now = datetime.now()
    day_str = now.strftime("%A %d %B %Y")

    print("\n" + "━" * W)
    print(f"  MORNING BRIEFING — {day_str}")
    print("━" * W)

    # Fetch all data
    whoop    = _fetch_whoop()
    events   = _fetch_calendar()
    goals    = _fetch_goals()
    commit   = _yesterday_commitment()
    journal  = _journal_context(days=3)

    # Print sections
    sections = [
        _section_whoop(whoop),
        _section_calendar(events),
        _section_goals(goals),
        _section_commitment(),
        _section_focus(whoop, events, goals, commit, journal),
    ]

    for section in sections:
        print()
        for line in section:
            print(line)

    print("\n" + "━" * W + "\n")


if __name__ == "__main__":
    run()
