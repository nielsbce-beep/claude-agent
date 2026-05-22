from datetime import datetime, timedelta
from tools import whoop_api, calendar_tools

DEFAULT_CALENDAR = "Niels AI agenda"

TRAINING_TYPES = {
    "rust": {
        "naam": "Rust / Actief herstel",
        "beschrijving": "Lichte wandeling of stretching. Geen zware belasting vandaag.",
        "duur_min": 30,
    },
    "licht": {
        "naam": "Lichte training",
        "beschrijving": "Zone 2 cardio: rustig fietsen, joggen of zwemmen op lage intensiteit.",
        "duur_min": 45,
    },
    "matig": {
        "naam": "Matige training",
        "beschrijving": "Krachtraining of cardio op middelhoge intensiteit. 60-70% van max.",
        "duur_min": 60,
    },
    "zwaar": {
        "naam": "Zware training",
        "beschrijving": "HIIT, zware krachtraining of lange duurloop. Geef alles.",
        "duur_min": 75,
    },
}


def _recovery_naar_type(recovery_score: float) -> str:
    if recovery_score < 34:
        return "rust"
    elif recovery_score < 50:
        return "licht"
    elif recovery_score < 67:
        return "matig"
    else:
        return "zwaar"


def _vrij_tijdslot(events: list[dict], datum: datetime, voorkeur_uur: int = 7) -> datetime:
    """Zoek een vrij uur op de gegeven datum, begin bij voorkeur_uur."""
    bezette_uren = set()
    for e in events:
        start = e["start"]
        end = e["end"]
        if not isinstance(start, datetime):
            start = datetime.combine(start, datetime.min.time())
        if end and not isinstance(end, datetime):
            end = datetime.combine(end, datetime.min.time())
        if start.date() == datum.date():
            uur = start.hour
            bezette_uren.add(uur)

    for uur in [voorkeur_uur, 8, 9, 17, 18, 6]:
        if uur not in bezette_uren:
            return datum.replace(hour=uur, minute=0, second=0, microsecond=0)
    return datum.replace(hour=voorkeur_uur, minute=0, second=0, microsecond=0)


def get_status() -> str:
    lijnen = []

    try:
        recovery = whoop_api.get_latest_recovery()
        score = recovery.get("score", {}).get("recovery_score", None)
        hrv = recovery.get("score", {}).get("hrv_rmssd_milli", None)
        slaap_perf = recovery.get("score", {}).get("sleep_performance_percentage", None)

        lijnen.append("=== Whoop Status ===")
        if score is not None:
            lijnen.append(f"Recovery score:   {score:.0f}%")
        if hrv is not None:
            lijnen.append(f"HRV:              {hrv:.1f} ms")
        if slaap_perf is not None:
            lijnen.append(f"Slaapkwaliteit:   {slaap_perf:.0f}%")

        if score is not None:
            training_type = _recovery_naar_type(score)
            t = TRAINING_TYPES[training_type]
            lijnen.append(f"\nAdvies vandaag:   {t['naam']}")
            lijnen.append(f"                  {t['beschrijving']}")
    except Exception as e:
        lijnen.append(f"Whoop niet beschikbaar: {e}")

    try:
        nu = datetime.now()
        events = calendar_tools.get_events(nu, nu + timedelta(days=2), DEFAULT_CALENDAR)
        lijnen.append("\n=== Agenda (vandaag & morgen) ===")
        if events:
            for e in events:
                start = e["start"]
                tijd = start.strftime("%a %d %b %H:%M") if isinstance(start, datetime) else str(start)
                lijnen.append(f"  {tijd}  {e['summary']}")
        else:
            lijnen.append("  Geen afspraken.")
    except Exception as e:
        lijnen.append(f"Agenda niet beschikbaar: {e}")

    return "\n".join(lijnen)


def maak_dagplan(toevoegen_aan_agenda: bool = True) -> str:
    lijnen = []

    try:
        recovery = whoop_api.get_latest_recovery()
        score = recovery.get("score", {}).get("recovery_score", 50)
    except Exception as e:
        lijnen.append(f"Whoop niet beschikbaar ({e}), gebruik standaard recovery van 50%.")
        score = 50

    training_type = _recovery_naar_type(score)
    t = TRAINING_TYPES[training_type]

    lijnen.append(f"Recovery vandaag: {score:.0f}%")
    lijnen.append(f"Training advies:  {t['naam']}")
    lijnen.append(f"                  {t['beschrijving']}")

    if toevoegen_aan_agenda:
        try:
            nu = datetime.now()
            events = calendar_tools.get_events(nu, nu + timedelta(days=1), DEFAULT_CALENDAR)
            start = _vrij_tijdslot(events, nu, voorkeur_uur=7)
            end = start + timedelta(minutes=t["duur_min"])
            calendar_tools.add_event(
                summary=f"Training: {t['naam']}",
                start=start,
                end=end,
                description=t["beschrijving"],
                calendar_name=DEFAULT_CALENDAR,
            )
            lijnen.append(f"\nTraining ingepland: {start.strftime('%H:%M')}–{end.strftime('%H:%M')}")
        except Exception as e:
            lijnen.append(f"\nKon training niet inplannen: {e}")

    return "\n".join(lijnen)


def maak_weekplan(toevoegen_aan_agenda: bool = True) -> str:
    lijnen = ["=== Weekplan trainingen ===\n"]

    try:
        recovery = whoop_api.get_latest_recovery()
        basis_score = recovery.get("score", {}).get("recovery_score", 50)
    except Exception:
        basis_score = 50

    # Afwisselend schema gebaseerd op huidige recovery
    # Patroon: training, rust, training, training, rust, training, rust
    patroon = ["training", "rust", "training", "training", "rust", "training", "rust"]

    nu = datetime.now()
    try:
        events = calendar_tools.get_events(nu, nu + timedelta(days=7), DEFAULT_CALENDAR)
    except Exception:
        events = []

    for dag_offset, dag_type in enumerate(patroon):
        dag = nu + timedelta(days=dag_offset)
        dagnaam = dag.strftime("%A %d %b")

        if dag_type == "rust":
            lijnen.append(f"{dagnaam}: Rust / actief herstel")
            continue

        # Score varieert per dag (herstel neemt toe na rustdagen)
        score = min(100, basis_score + (dag_offset * 3))
        training_type = _recovery_naar_type(score)
        t = TRAINING_TYPES[training_type]

        lijnen.append(f"{dagnaam}: {t['naam']} ({t['duur_min']} min)")

        if toevoegen_aan_agenda:
            try:
                start = _vrij_tijdslot(events, dag, voorkeur_uur=7)
                end = start + timedelta(minutes=t["duur_min"])
                calendar_tools.add_event(
                    summary=f"Training: {t['naam']}",
                    start=start,
                    end=end,
                    description=t["beschrijving"],
                    calendar_name=DEFAULT_CALENDAR,
                )
                lijnen[-1] += f" → {start.strftime('%H:%M')}"
            except Exception as e:
                lijnen[-1] += f" (niet ingepland: {e})"

    return "\n".join(lijnen)
