"""
Verwijdert alle 'Studeren:' blokken uit de Niels AI agenda en plant
een nieuw schema op basis van exacte voortgang per vak.
"""
import sys
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env", override=True)

sys.stdout.reconfigure(encoding="utf-8")

from tools.calendar_tools import delete_events_by_prefix, add_event

CAL = "Niels AI agenda"

def run():
    print("=== STUDIE SCHEMA RESET ===\n")

    # 1. Verwijder alle bestaande 'Studeren:' blokken (25 mei – 30 jun)
    print("Verwijder bestaande studeerblokken...")
    n = delete_events_by_prefix(
        "Studeren:",
        start=datetime(2026, 5, 25),
        end=datetime(2026, 6, 30),
        calendar_name=CAL,
    )
    print(f"  {n} event(s) verwijderd.\n")

    events = [
        # ── 25 mei (Pinksterdag) ──────────────────────────────────────
        ("Studeren: Num. Wiskunde lecture 4",
         datetime(2026, 5, 25, 10), datetime(2026, 5, 25, 12)),

        # ── 26 mei ───────────────────────────────────────────────────
        ("Studeren: Num. Wiskunde lecture 5",
         datetime(2026, 5, 26, 9), datetime(2026, 5, 26, 11)),
        ("Studeren: Waterbouwkunde lecture 8",
         datetime(2026, 5, 26, 13), datetime(2026, 5, 26, 15)),

        # ── 27 mei ───────────────────────────────────────────────────
        ("Studeren: Num. Wiskunde lecture 6",
         datetime(2026, 5, 27, 9), datetime(2026, 5, 27, 11)),
        ("Studeren: Waterbouwkunde lecture 9",
         datetime(2026, 5, 27, 13), datetime(2026, 5, 27, 15)),

        # ── 28 mei ───────────────────────────────────────────────────
        ("Studeren: Num. Wiskunde lecture 7 (catch-up voor schoolles)",
         datetime(2026, 5, 28, 9), datetime(2026, 5, 28, 11)),
        ("Studeren: Waterbouwkunde lecture 10",
         datetime(2026, 5, 28, 13), datetime(2026, 5, 28, 15)),

        # ── 29 mei (werkcollege Hydrologie 8:45, uiteten 17:00) ──────
        ("Studeren: MUMIE opdracht 6",
         datetime(2026, 5, 29, 11), datetime(2026, 5, 29, 12, 30)),

        # ── 1 juni (Hydrologie les 10:45) ────────────────────────────
        ("Studeren: MUMIE opdracht 6 afronden",
         datetime(2026, 6, 1, 13, 30), datetime(2026, 6, 1, 15)),
        ("Studeren: Waterbouwkunde lecture 11",
         datetime(2026, 6, 1, 15, 30), datetime(2026, 6, 1, 17, 30)),

        # ── 2 juni ───────────────────────────────────────────────────
        ("Studeren: Waterbouwkunde lecture 12",
         datetime(2026, 6, 2, 9), datetime(2026, 6, 2, 11)),
        ("Studeren: MUMIE opdracht 3",
         datetime(2026, 6, 2, 13), datetime(2026, 6, 2, 14, 30)),

        # ── 3 juni (Hydrologie werkcollege 13:45) ────────────────────
        ("Studeren: Waterbouwkunde lecture 13",
         datetime(2026, 6, 3, 9), datetime(2026, 6, 3, 11)),

        # ── 4 juni ───────────────────────────────────────────────────
        ("Studeren: Waterbouwkunde lecture 14",
         datetime(2026, 6, 4, 9), datetime(2026, 6, 4, 11)),

        # ── 5 juni ───────────────────────────────────────────────────
        ("Studeren: Vloeistofmechanica week 1-2",
         datetime(2026, 6, 5, 9), datetime(2026, 6, 5, 11)),
        ("Studeren: Waterbouwkunde lecture 15",
         datetime(2026, 6, 5, 13), datetime(2026, 6, 5, 15)),

        # ── 8 juni ───────────────────────────────────────────────────
        ("Studeren: Waterbouwkunde lecture 16 (laatste!)",
         datetime(2026, 6, 8, 9), datetime(2026, 6, 8, 11)),
        ("Studeren: MUMIE opdracht 7",
         datetime(2026, 6, 8, 13), datetime(2026, 6, 8, 14, 30)),
        ("Studeren: Vloeistofmechanica week 3",
         datetime(2026, 6, 8, 15), datetime(2026, 6, 8, 16)),

        # ── 9 juni (Hydrologie voorbereiding 10:45) ──────────────────
        ("Studeren: MUMIE opdracht 4",
         datetime(2026, 6, 9, 13, 30), datetime(2026, 6, 9, 15)),
        ("Studeren: Vloeistofmechanica week 4",
         datetime(2026, 6, 9, 15, 30), datetime(2026, 6, 9, 16, 30)),

        # ── 10 juni ──────────────────────────────────────────────────
        ("Studeren: Vloeistofmechanica week 5-6",
         datetime(2026, 6, 10, 9), datetime(2026, 6, 10, 11)),
        ("Studeren: MUMIE opdrachten 7+4 afronden",
         datetime(2026, 6, 10, 13), datetime(2026, 6, 10, 14, 30)),

        # ── 11 juni (BBQ 17:00) ──────────────────────────────────────
        ("Studeren: Vloeistofmechanica week 7-8",
         datetime(2026, 6, 11, 9), datetime(2026, 6, 11, 11)),

        # ── 14 juni (2 dagen voor vloeistof tentamen) ────────────────
        ("Studeren: Vloeistofmechanica oefentoetsen",
         datetime(2026, 6, 14, 9), datetime(2026, 6, 14, 11)),

        # ── EXAM PREP BLOKKEN (na alle stof, vlak voor tentamen) ─────

        # Vloeistofmechanica: 14-15 juni (tentamen 16 jun) — 10h
        ("Studeren: Vloeistofmechanica oefentoetsen",
         datetime(2026, 6, 14, 13), datetime(2026, 6, 14, 16)),
        ("Studeren: Vloeistofmechanica oefentoetsen",
         datetime(2026, 6, 15, 9), datetime(2026, 6, 15, 12)),
        ("Studeren: Vloeistofmechanica oefentoetsen",
         datetime(2026, 6, 15, 13), datetime(2026, 6, 15, 16)),

        # Waterbouwkunde: 16-18 juni (tentamen 19 jun) — 12h
        ("Studeren: Waterbouwkunde oefentoetsen",
         datetime(2026, 6, 16, 13), datetime(2026, 6, 16, 16)),
        ("Studeren: Waterbouwkunde oefentoetsen",
         datetime(2026, 6, 17, 9), datetime(2026, 6, 17, 12)),
        ("Studeren: Waterbouwkunde oefentoetsen",
         datetime(2026, 6, 17, 13), datetime(2026, 6, 17, 16)),
        ("Studeren: Waterbouwkunde oefentoetsen",
         datetime(2026, 6, 18, 9), datetime(2026, 6, 18, 12)),

        # Hydrologie: 10-11 juni (deeltoets 12 jun) — 6h
        ("Studeren: Hydrologie oefentoetsen",
         datetime(2026, 6, 10, 15), datetime(2026, 6, 10, 18)),
        ("Studeren: Hydrologie oefentoetsen",
         datetime(2026, 6, 11, 13), datetime(2026, 6, 11, 16)),

        # Numerieke Wiskunde: 20-24 juni (tentamen 25 jun) — 12h
        ("Studeren: Num. Wiskunde oefentoetsen",
         datetime(2026, 6, 20, 9), datetime(2026, 6, 20, 12)),
        ("Studeren: Num. Wiskunde oefentoetsen",
         datetime(2026, 6, 20, 13), datetime(2026, 6, 20, 16)),
        ("Studeren: Num. Wiskunde oefentoetsen",
         datetime(2026, 6, 21, 9), datetime(2026, 6, 21, 12)),
        ("Studeren: Num. Wiskunde oefentoetsen",
         datetime(2026, 6, 21, 13), datetime(2026, 6, 21, 16)),
        ("Studeren: Num. Wiskunde oefentoetsen",
         datetime(2026, 6, 23, 9), datetime(2026, 6, 23, 12)),
        ("Studeren: Num. Wiskunde oefentoetsen",
         datetime(2026, 6, 24, 9), datetime(2026, 6, 24, 11)),
    ]

    print(f"Voeg {len(events)} studeerblokken toe...\n")
    for summary, start, end in events:
        result = add_event(summary, start, end, calendar_name=CAL, skip_if_overlap=True)
        print(f"  {result}")

    print("\n=== KLAAR ===")


if __name__ == "__main__":
    run()
