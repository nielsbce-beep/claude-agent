"""
Financiële agent — portfolio overzicht, projectie naar €25k doel,
en analyse via Claude. Update handmatig met nieuwe screenshots.
"""
import sys
import json
import anthropic
from datetime import datetime, date
from pathlib import Path
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env", override=True)

sys.stdout.reconfigure(encoding="utf-8")

client   = anthropic.Anthropic()
MODEL    = "claude-sonnet-4-6"
TODAY    = datetime.now().strftime("%A %d %B %Y")
PORTFOLIO = Path(__file__).parent / "data" / "portfolio.json"
W = 57


# ── Storage ────────────────────────────────────────────────────────────────────

def _load() -> dict:
    return json.loads(PORTFOLIO.read_text(encoding="utf-8"))


def _save(data: dict):
    PORTFOLIO.write_text(
        json.dumps(data, ensure_ascii=False, indent=2, default=str),
        encoding="utf-8"
    )


# ── Berekeningen ───────────────────────────────────────────────────────────────

def _totaal(data: dict) -> float:
    h = data["holdings"]
    aandelen_waarde = sum(p["waarde"] for p in h["aandelen"]["posities"])
    return h["bnd"]["waarde"] + h["goud"]["waarde"] + aandelen_waarde + h["bitcoin"]["waarde"]


def _maandelijkse_inleg(data: dict) -> float:
    i = data["inleg"]
    return i["bnd_maand"] + i["goud_maand"] + (i["aandelen_week"] * 52 / 12) + (i["bitcoin_week"] * 52 / 12)


def _projectie(huidig: float, maand_inleg: float, rendement_pct: float, doel: float, deadline: str) -> list[dict]:
    """
    Compound growth projectie per jaar tot deadline.
    Rendement is jaarlijks, inleg maandelijks.
    """
    r_maand = rendement_pct / 100 / 12
    doel_datum = date.fromisoformat(deadline)
    maanden_resterend = (doel_datum.year - date.today().year) * 12 + (doel_datum.month - date.today().month)

    waarde = huidig
    rows   = []
    for m in range(1, maanden_resterend + 1):
        waarde = waarde * (1 + r_maand) + maand_inleg
        if m % 12 == 0:
            jaar = date.today().year + m // 12
            rows.append({"jaar": jaar, "waarde": round(waarde, 2)})

    # Voeg eindrij toe als de deadline niet op een jaargrens valt
    if maanden_resterend % 12 != 0:
        # Vervang het laatste jaar als dat al 'deadline jaar' is, anders voeg toe
        if rows and rows[-1]["jaar"] == doel_datum.year:
            rows[-1]["waarde"] = round(waarde, 2)
        else:
            rows.append({"jaar": doel_datum.year, "waarde": round(waarde, 2)})

    return rows


def _benodigde_inleg(huidig: float, doel: float, rendement_pct: float, deadline: str) -> float:
    """Bereken welke maandelijkse inleg nodig is om het doel te halen."""
    doel_datum = date.fromisoformat(deadline)
    n = (doel_datum.year - date.today().year) * 12 + (doel_datum.month - date.today().month)
    r = rendement_pct / 100 / 12
    if n <= 0:
        return 0.0
    # FV = PV*(1+r)^n + PMT * ((1+r)^n - 1) / r
    # Oplossen naar PMT:
    factor = (1 + r) ** n
    pmt = (doel - huidig * factor) * r / (factor - 1)
    return round(pmt, 2)


def _bar(value: float, max_val: float, width: int = 20) -> str:
    pct = min(value / max_val, 1.0)
    filled = int(pct * width)
    return "█" * filled + "░" * (width - filled)


# ── Context voor agents ────────────────────────────────────────────────────────

def portfolio_context() -> str:
    """Compacte string voor gebruik in money agent en weekly review."""
    data  = _load()
    totaal = _totaal(data)
    doel   = data["doel"]["bedrag"]
    pct    = round(totaal / doel * 100, 1)
    maand  = _maandelijkse_inleg(data)

    h = data["holdings"]
    aandelen_waarde = sum(p["waarde"] for p in h["aandelen"]["posities"])
    winnaars = sorted(h["aandelen"]["posities"], key=lambda p: p["rendement_pct"], reverse=True)[:3]
    verliezers = sorted(h["aandelen"]["posities"], key=lambda p: p["rendement_pct"])[:2]

    winnaars_str   = ", ".join(p["ticker"] + " +" + str(p["rendement_pct"]) + "%" for p in winnaars)
    verliezers_str = ", ".join(p["ticker"] + " "  + str(p["rendement_pct"]) + "%" for p in verliezers)
    lines = [
        f"Portfolio stand ({data['last_updated']}):",
        f"  Totaal:   €{totaal:,.2f}  ({pct}% van €{doel:,} doel)",
        f"  BND:      €{h['bnd']['waarde']:,.2f}",
        f"  Goud:     €{h['goud']['waarde']:,.2f}  ({h['goud']['rendement_pct']}%)",
        f"  Aandelen: €{aandelen_waarde:,.2f}",
        f"  Bitcoin:  €{h['bitcoin']['waarde']:,.2f}",
        f"  Inleg:    €{maand:.0f}/maand",
        f"  Winnaars: {winnaars_str}",
        f"  Verliezers: {verliezers_str}",
    ]
    return "\n".join(lines)


# ── Modi ───────────────────────────────────────────────────────────────────────

def overzicht():
    data   = _load()
    totaal = _totaal(data)
    doel   = data["doel"]["bedrag"]
    maand  = _maandelijkse_inleg(data)
    h      = data["holdings"]
    aandelen_waarde = sum(p["waarde"] for p in h["aandelen"]["posities"])

    print("\n" + "━" * W)
    print(f"  PORTFOLIO OVERZICHT — {TODAY}")
    print("━" * W)

    # Totaal + doel progress
    pct = totaal / doel * 100
    print(f"\nTOTAAL    €{totaal:>9,.2f}  van €{doel:,}")
    print(f"          {_bar(totaal, doel)}  {pct:.1f}%")
    print(f"INLEG     €{maand:.0f}/maand  (BND €{data['inleg']['bnd_maand']} + "
          f"Goud €{data['inleg']['goud_maand']} + "
          f"Aandelen €{data['inleg']['aandelen_week']}/wk + "
          f"BTC €{data['inleg']['bitcoin_week']}/wk)")

    # BND
    print(f"\nBRAND NEW DAY     €{h['bnd']['waarde']:,.2f}")
    for p in h["bnd"]["posities"]:
        print(f"  {p['weging']:5.1f}%  {p['naam'][:38]:<38}  €{p['waarde']:>8,.2f}")

    # Goud
    rend_goud = h["goud"]["rendement_pct"]
    rend_icon = "↑" if rend_goud >= 0 else "↓"
    print(f"\nGOUD              €{h['goud']['waarde']:,.2f}  "
          f"({rend_icon}{abs(rend_goud):.2f}%  aankoopwaarde €{h['goud']['aankoopwaarde']:,.2f})")

    # Aandelen
    print(f"\nLOSSE AANDELEN    €{aandelen_waarde:,.2f}")
    for p in sorted(h["aandelen"]["posities"], key=lambda x: x["waarde"], reverse=True):
        rend = p["rendement_pct"]
        icon = "+" if rend >= 0 else ""
        bar_w = 8
        bar_filled = min(int(abs(rend) / 30 * bar_w), bar_w)
        bar = ("█" if rend >= 0 else "░") * bar_filled + "░" * (bar_w - bar_filled)
        print(f"  {p['ticker']:<6}  {p['naam']:<22}  €{p['waarde']:>6,.2f}  {icon}{rend:>6.2f}%  {bar}")

    # Bitcoin
    if h["bitcoin"]["waarde"] > 0:
        rend_btc = h["bitcoin"]["rendement_pct"]
        print(f"\nBITCOIN           €{h['bitcoin']['waarde']:,.2f}  ({rend_btc:+.2f}%)")
    else:
        print(f"\nBITCOIN           nog niet ingevuld")

    print()


def projectie(rendement: float = 10.0):
    data   = _load()
    totaal = _totaal(data)
    maand  = _maandelijkse_inleg(data)
    doel   = data["doel"]["bedrag"]
    deadline = data["doel"]["deadline"]

    print("\n" + "━" * W)
    print(f"  PROJECTIE NAAR €{doel:,}")
    print("━" * W)
    print(f"\n  Huidig:   €{totaal:,.2f}")
    print(f"  Inleg:    €{maand:.0f}/maand")
    print(f"  Deadline: {deadline}")
    print(f"  Aanname:  {rendement}% rendement/jaar\n")

    rows = _projectie(totaal, maand, rendement, doel, deadline)
    for r in rows:
        bar = _bar(r["waarde"], doel, 20)
        pct = min(r["waarde"] / doel * 100, 100)
        reached = " ✓ DOEL BEREIKT" if r["waarde"] >= doel else ""
        print(f"  {r['jaar']}  €{r['waarde']:>9,.2f}  {bar}  {pct:.0f}%{reached}")

    # Benodigde inleg check
    benodig = _benodigde_inleg(totaal, doel, rendement, deadline)
    print(f"\n  Benodigde inleg voor doel: €{benodig:.0f}/maand")
    verschil = maand - benodig
    if verschil >= 0:
        print(f"  Huidige inleg (€{maand:.0f}) is €{verschil:.0f} méér dan nodig ✓")
    else:
        print(f"  Tekort: €{abs(verschil):.0f}/maand extra nodig om doel te halen")

    # Gevoeligheidsanalyse
    print(f"\n  Gevoeligheidsanalyse (eindwaarde {deadline}):")
    for r in [6, 8, 10, 12]:
        rows_r = _projectie(totaal, maand, r, doel, deadline)
        eind = rows_r[-1]["waarde"] if rows_r else totaal
        icon = "✓" if eind >= doel else "✗"
        print(f"  {r:2d}% rendement  →  €{eind:>9,.2f}  {icon}")
    print()


def update(component: str, waarde: float, extra: dict = None):
    """Update een component handmatig na een nieuwe screenshot."""
    data = _load()
    today = date.today().isoformat()

    if component == "bnd":
        oud = data["holdings"]["bnd"]["waarde"]
        data["holdings"]["bnd"]["waarde"] = waarde
        data["updates"].append({"datum": today, "component": "bnd", "oud": oud, "nieuw": waarde})
    elif component == "goud":
        oud = data["holdings"]["goud"]["waarde"]
        data["holdings"]["goud"]["waarde"] = waarde
        if extra and "aankoopwaarde" in extra:
            data["holdings"]["goud"]["aankoopwaarde"] = extra["aankoopwaarde"]
            pct = (waarde - extra["aankoopwaarde"]) / extra["aankoopwaarde"] * 100
            data["holdings"]["goud"]["rendement_pct"] = round(pct, 2)
        data["updates"].append({"datum": today, "component": "goud", "oud": oud, "nieuw": waarde})
    elif component == "bitcoin":
        oud = data["holdings"]["bitcoin"]["waarde"]
        data["holdings"]["bitcoin"]["waarde"] = waarde
        if extra and "aankoopwaarde" in extra:
            data["holdings"]["bitcoin"]["aankoopwaarde"] = extra["aankoopwaarde"]
            pct = (waarde - extra["aankoopwaarde"]) / extra["aankoopwaarde"] * 100
            data["holdings"]["bitcoin"]["rendement_pct"] = round(pct, 2)
        data["updates"].append({"datum": today, "component": "bitcoin", "oud": oud, "nieuw": waarde})

    data["last_updated"] = today
    _save(data)
    print(f"✓ {component} bijgewerkt naar €{waarde:,.2f}")


def analyse():
    """Claude geeft een directe analyse van het portfolio."""
    data = _load()
    ctx  = portfolio_context()
    totaal = _totaal(data)
    maand  = _maandelijkse_inleg(data)

    print(f"\n{'='*W}\nPORTFOLIO ANALYSE\n{'='*W}\n")

    response = client.messages.create(
        model=MODEL,
        max_tokens=600,
        system=(
            "Je bent een directe financiële coach. Je spreekt Nederlands. Geen inleiding. "
            "Geef een eerlijke analyse van het portfolio in vier punten:\n"
            "1. STERK: wat werkt goed aan deze opbouw\n"
            "2. RISICO: het grootste concrete risico nu\n"
            "3. ACTIE: één specifieke actie die de kans op €25.000 vergroot\n"
            "4. PATROON: één patroon in de posities dat aandacht verdient\n"
            "Max 2 zinnen per punt. Gebruik de exacte cijfers."
        ),
        messages=[{"role": "user", "content": ctx}],
    )
    print(response.content[0].text.strip())
    print()


if __name__ == "__main__":
    args = sys.argv[1:]

    if not args or args[0] == "overzicht":
        overzicht()
    elif args[0] == "projectie":
        r = float(args[1]) if len(args) > 1 else 10.0
        projectie(r)
    elif args[0] == "analyse":
        analyse()
    elif args[0] == "update":
        if len(args) < 3:
            print("Gebruik: python financieel_agent.py update [bnd|goud|bitcoin] [waarde]")
        else:
            update(args[1], float(args[2]))
    else:
        print("Gebruik:")
        print("  python financieel_agent.py              → portfolio overzicht")
        print("  python financieel_agent.py projectie    → projectie naar €25.000 (10% rendement)")
        print("  python financieel_agent.py projectie 8  → projectie met 8% rendement")
        print("  python financieel_agent.py analyse      → AI analyse van je portfolio")
        print("  python financieel_agent.py update bnd 2950  → update BND waarde na screenshot")
