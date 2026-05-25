"""
Reads Whoop historical data from the exported CSV files.
Used as primary data source when the live API returns an incomplete cycle,
and for trend/pattern analysis.
"""
import csv
from datetime import datetime, date, timedelta
from pathlib import Path

CSV_DIR = Path(__file__).parent.parent.parent  # repo root where CSVs live
CYCLES_CSV  = CSV_DIR / "physiological_cycles.csv"
SLEEPS_CSV  = CSV_DIR / "sleeps.csv"
WORKOUTS_CSV = CSV_DIR / "workouts.csv"


def _parse_float(v: str) -> float | None:
    try:
        return float(v) if v.strip() else None
    except Exception:
        return None


def _parse_date(v: str) -> date | None:
    try:
        return datetime.fromisoformat(v.strip()).date()
    except Exception:
        return None


# ── Loaders ────────────────────────────────────────────────────────────────────

def load_cycles(days: int = 90) -> list[dict]:
    """Return parsed cycle rows for the last `days` days, newest first."""
    cutoff = date.today() - timedelta(days=days)
    rows = []
    if not CYCLES_CSV.exists():
        return rows
    with open(CYCLES_CSV, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            d = _parse_date(row.get("Cycle start time", ""))
            if d and d >= cutoff:
                rows.append({
                    "date":        d,
                    "recovery":    _parse_float(row.get("Recovery score %", "")),
                    "hrv":         _parse_float(row.get("Heart rate variability (ms)", "")),
                    "rhr":         _parse_float(row.get("Resting heart rate (bpm)", "")),
                    "sleep_perf":  _parse_float(row.get("Sleep performance %", "")),
                    "sleep_min":   _parse_float(row.get("Asleep duration (min)", "")),
                    "deep_min":    _parse_float(row.get("Deep (SWS) duration (min)", "")),
                    "rem_min":     _parse_float(row.get("REM duration (min)", "")),
                    "strain":      _parse_float(row.get("Day Strain", "")),
                    "spo2":        _parse_float(row.get("Blood oxygen %", "")),
                    "skin_temp":   _parse_float(row.get("Skin temp (celsius)", "")),
                })
    return sorted(rows, key=lambda r: r["date"], reverse=True)


def load_workouts(days: int = 60) -> list[dict]:
    """Return parsed workout rows for the last `days` days, newest first."""
    cutoff = date.today() - timedelta(days=days)
    rows = []
    if not WORKOUTS_CSV.exists():
        return rows
    with open(WORKOUTS_CSV, encoding="utf-8") as f:
        for row in csv.DictReader(f):
            d = _parse_date(row.get("Workout start time", ""))
            if d and d >= cutoff:
                rows.append({
                    "date":     d,
                    "activity": row.get("Activity name", "").strip(),
                    "duration": _parse_float(row.get("Duration (min)", "")),
                    "strain":   _parse_float(row.get("Activity Strain", "")),
                    "cal":      _parse_float(row.get("Energy burned (cal)", "")),
                    "max_hr":   _parse_float(row.get("Max HR (bpm)", "")),
                    "avg_hr":   _parse_float(row.get("Average HR (bpm)", "")),
                    "zone4_pct": _parse_float(row.get("HR Zone 4 %", "")),
                    "zone5_pct": _parse_float(row.get("HR Zone 5 %", "")),
                })
    return sorted(rows, key=lambda r: r["date"], reverse=True)


# ── Analysis ───────────────────────────────────────────────────────────────────

def get_today_from_csv() -> dict:
    """Get today's cycle data from CSV (useful when API cycle is still open)."""
    cycles = load_cycles(days=2)
    today = date.today()
    for c in cycles:
        if c["date"] == today:
            return c
    return {}


def get_recovery_trend(days: int = 14) -> dict:
    """
    Returns:
      avg       float  — average recovery over period
      hrv_avg   float  — average HRV
      trend     str    — '↑' / '↓' / '→' based on first vs second half of period
      best_day  str    — weekday name with highest avg recovery
      worst_day str    — weekday name with lowest avg recovery
    """
    cycles = load_cycles(days=days)
    if not cycles:
        return {}

    valid = [c for c in cycles if c["recovery"] is not None]
    if not valid:
        return {}

    scores = [c["recovery"] for c in valid]
    hrvs   = [c["hrv"] for c in valid if c["hrv"] is not None]

    # Trend: compare first half vs second half (list is newest-first)
    mid = len(scores) // 2
    recent_avg = sum(scores[:mid]) / mid if mid else scores[0]
    older_avg  = sum(scores[mid:]) / (len(scores) - mid) if mid < len(scores) else scores[0]
    if recent_avg > older_avg + 3:
        trend = "↑"
    elif recent_avg < older_avg - 3:
        trend = "↓"
    else:
        trend = "→"

    # Best/worst weekday
    day_scores: dict[str, list[float]] = {}
    for c in valid:
        wd = c["date"].strftime("%A")
        day_scores.setdefault(wd, []).append(c["recovery"])
    day_avgs = {d: sum(v) / len(v) for d, v in day_scores.items() if v}
    best_day  = max(day_avgs, key=day_avgs.get) if day_avgs else None
    worst_day = min(day_avgs, key=day_avgs.get) if day_avgs else None

    return {
        "avg":       round(sum(scores) / len(scores), 1),
        "hrv_avg":   round(sum(hrvs) / len(hrvs), 1) if hrvs else None,
        "trend":     trend,
        "best_day":  best_day,
        "worst_day": worst_day,
        "n":         len(valid),
    }


def get_sleep_trend(days: int = 14) -> dict:
    cycles = load_cycles(days=days)
    valid  = [c for c in cycles if c["sleep_perf"] is not None]
    if not valid:
        return {}
    perfs = [c["sleep_perf"] for c in valid]
    mins  = [c["sleep_min"]  for c in valid if c["sleep_min"] is not None]
    deeps = [c["deep_min"]   for c in valid if c["deep_min"]  is not None]
    return {
        "avg_perf":    round(sum(perfs) / len(perfs), 1),
        "avg_hours":   round(sum(mins)  / len(mins) / 60, 2) if mins else None,
        "avg_deep_min": round(sum(deeps) / len(deeps), 1) if deeps else None,
    }


def get_training_summary(days: int = 14) -> dict:
    """Workout frequency, dominant activity, avg strain."""
    workouts = load_workouts(days=days)
    if not workouts:
        return {}

    activity_counts: dict[str, int] = {}
    strains = []
    for w in workouts:
        a = w["activity"] or "Onbekend"
        activity_counts[a] = activity_counts.get(a, 0) + 1
        if w["strain"] is not None:
            strains.append(w["strain"])

    top_activity = max(activity_counts, key=activity_counts.get)
    return {
        "total":        len(workouts),
        "per_week":     round(len(workouts) / (days / 7), 1),
        "top_activity": top_activity,
        "activities":   activity_counts,
        "avg_strain":   round(sum(strains) / len(strains), 1) if strains else None,
    }


def get_overtraining_signal(days: int = 7) -> str | None:
    """
    Returns a warning string if overtraining indicators are present, else None.
    Checks: high strain + low recovery for 3+ consecutive days.
    """
    cycles = load_cycles(days=days)
    valid = [c for c in cycles if c["recovery"] is not None and c["strain"] is not None]
    if len(valid) < 3:
        return None

    consecutive = 0
    for c in valid[:5]:  # check most recent 5 days
        if c["recovery"] < 50 and c["strain"] > 14:
            consecutive += 1
        else:
            break

    if consecutive >= 3:
        return f"⚠️  {consecutive} dagen achter elkaar: lage recovery (<50%) + hoge strain (>14). Overtraining risico."
    return None


def format_context_for_agent(days: int = 14) -> str:
    """One-string summary for use in agent system prompts."""
    trend   = get_recovery_trend(days)
    sleep   = get_sleep_trend(days)
    training = get_training_summary(days)
    today   = get_today_from_csv()
    signal  = get_overtraining_signal()

    lines = [f"Whoop historische data (laatste {days} dagen):"]

    if today:
        r = today.get("recovery")
        h = today.get("hrv")
        lines.append(
            f"  Vandaag: recovery {r}%  |  HRV {h}ms  |  "
            f"slaap {round((today.get('sleep_min') or 0)/60,1)}u"
        )

    if trend:
        lines.append(
            f"  Trend {days}d: gem. recovery {trend['avg']}%  "
            f"HRV {trend.get('hrv_avg')}ms  richting {trend['trend']}"
        )
        if trend.get("best_day"):
            lines.append(f"  Beste dag: {trend['best_day']} | Slechtste dag: {trend.get('worst_day')}")

    if sleep:
        lines.append(
            f"  Slaap: gem. {sleep.get('avg_hours')}u  "
            f"kwaliteit {sleep.get('avg_perf')}%  "
            f"diepe slaap {sleep.get('avg_deep_min')} min"
        )

    if training:
        lines.append(
            f"  Training: {training['total']}x in {days} dagen  "
            f"({training['per_week']}x/week)  "
            f"meest: {training['top_activity']}  "
            f"gem. strain {training.get('avg_strain')}"
        )

    if signal:
        lines.append(f"  {signal}")

    return "\n".join(lines)
