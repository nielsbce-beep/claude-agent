"""Live aandelen- en ETF-koersen via Yahoo Finance (gratis, geen API-key)."""
import yfinance as yf

_fx_cache: dict[str, float] = {}


def _fx_naar_eur(currency: str) -> float:
    """Wisselkoers om `currency` om te rekenen naar euro's."""
    currency = (currency or "EUR").upper()
    if currency == "EUR":
        return 1.0
    if currency in _fx_cache:
        return _fx_cache[currency]
    rate = yf.Ticker(f"EUR{currency}=X").fast_info.get("lastPrice")
    _fx_cache[currency] = (1 / rate) if rate else 1.0
    return _fx_cache[currency]


def live_koers_eur(ticker: str) -> float:
    """Huidige koers van `ticker`, omgerekend naar euro's."""
    info = yf.Ticker(ticker).fast_info
    prijs = info.get("lastPrice")
    if prijs is None:
        raise ValueError(f"Geen koers gevonden voor '{ticker}'")
    return round(prijs * _fx_naar_eur(info.get("currency", "EUR")), 4)


def ververs_positie(positie: dict) -> dict:
    """Werk koers/waarde/rendement_pct van één positie bij (in-place, ook returned)."""
    ticker, aantal = positie.get("ticker"), positie.get("aantal")
    if not ticker or not aantal:
        return positie
    koers = live_koers_eur(ticker)
    waarde = round(aantal * koers, 2)
    positie["koers"] = koers
    positie["waarde"] = waarde
    aankoop = positie.get("aankoopwaarde")
    if aankoop:
        positie["rendement_pct"] = round((waarde - aankoop) / aankoop * 100, 2)
    return positie


def ververs_posities(posities: list[dict]) -> list[dict]:
    """Werk koers/waarde/rendement_pct bij voor elke positie met ticker + aantal, herweegt daarna."""
    for p in posities:
        ververs_positie(p)
    tot = sum(x.get("waarde", 0) for x in posities) or 1
    for p in posities:
        p["weging"] = round(p.get("waarde", 0) / tot * 100, 2)
    return posities
