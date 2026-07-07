"""Reine Transformationsfunktionen (ohne DB/Datei-Abhängigkeit, gut testbar)."""
from __future__ import annotations

# BACnet-Objekttypen, die physische Feld-I/O sind (Kabel/Klemme nötig).
HARDWARE_TYPES = {"AI", "AO", "BI", "BO"}
# An einen Basispunkt angehängte Objekte (referenzierte Meldung / Datenaufzeichnung).
ERWEITERUNG_TYPES = {"EE", "TL"}
# Präfixe, die eine Template-Referenz als Unter-Aggregat kennzeichnen.
AGGREGAT_PRAEFIXE = ("AGG_", "BGP_", "ANL_")


def clean(value) -> str | None:
    """Zellwert -> getrimmter String oder None (bei leer)."""
    if value is None:
        return None
    s = str(value).strip()
    return s or None


def ist_hardware(object_type: str | None) -> bool:
    return (object_type or "").strip().upper() in HARDWARE_TYPES


def ist_erweiterung(object_type: str | None) -> bool:
    return (object_type or "").strip().upper() in ERWEITERUNG_TYPES


def ist_unteraggregat(referenz_kennung: str | None) -> bool:
    """True, wenn die Referenz auf ein anderes Aggregat-Template zeigt."""
    return (referenz_kennung or "").strip().upper().startswith(AGGREGAT_PRAEFIXE)


def to_number(value):
    """Best-effort-Konvertierung nach float; None bei nicht-numerisch/Platzhalter."""
    s = clean(value)
    if s is None:
        return None
    s = s.replace(",", ".")
    try:
        return float(s)
    except ValueError:
        return None


def normalize_notification_class(value) -> str | None:
    """'200' / 'NC200' / '100,101' -> 'NC200'; None bei leer/ungültig."""
    s = clean(value)
    if s is None:
        return None
    s = s.split(",")[0].split(";")[0].strip()
    if not s:
        return None
    if s.upper().startswith("NC"):
        return "NC" + s[2:].strip()
    if s.isdigit():
        return "NC" + s
    return None


def bas_relativ(row_get, bas_blocks: dict) -> dict:
    """Baut das relative BAS-Muster (nur Block 4-8) aus den Blockspalten.

    row_get: Callable(spaltenindex) -> Zellwert.
    bas_blocks: {feldname: spaltenindex} aus dem Mapping.
    """
    out = {}
    for feld, idx in bas_blocks.items():
        val = clean(row_get(idx))
        if val is not None:
            out[feld] = val
    return out


def is_data_kennung(kennung: str | None) -> bool:
    """Echte Objekt-/Template-Kennung? (filtert Meta-/Leerzeilen der 8.x-Blätter)."""
    s = clean(kennung)
    return bool(s) and "AMEV" in s.upper()
