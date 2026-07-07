"""NamingEngine: setzt den vollständigen BAS-Schlüssel eines Datenpunkts zusammen.

Grundregel (siehe /docs/msr-tool/Beispiel-Gaskessel.md §3): Block 1-3 (Gewerk,
Anlage, Baugruppe) stammen aus dem Platzierungskontext (baugruppe.bas), Block 4-8
aus dem relativen Muster des Templates (aggregat_template_dp.bas_relativ). Der im
Template hinterlegte Beispiel-Ortsbezug wird dabei bewusst NICHT verwendet.
"""
from __future__ import annotations

FILLER_CHARS = set("#")


def _resolve_number(raw, variante: str) -> str:
    """Löst eine Nummern-Stelle auf.

    - 'xx'/'x'  -> Laufnummer (v1: erste Instanz = 01 bzw. 1)
    - Ziffern   -> unverändert (bereits konkret, z. B. '01')
    - '##'/None/leer -> '' (keine Nummer / Füllstelle)
    """
    if raw is None:
        return ""
    s = str(raw).strip()
    if not s or set(s) <= FILLER_CHARS:
        return ""
    low = s.lower()
    if low == "xx":
        return "1" if variante == "gekuerzt" else "01"
    if low == "x":
        return "1"
    if s.isdigit():
        return s
    return s


def _block(kennung, nummer, variante: str) -> str:
    """Ein BAS-Block = Kürzel + aufgelöste Nummer (Füll-Kürzel wie '#####' bleiben)."""
    k = None if kennung is None else str(kennung).strip()
    if not k:
        return ""
    return k + _resolve_number(nummer, variante)


class NamingEngine:
    def __init__(self, variante: str = "ungekuerzt", trennzeichen: str = "_"):
        self.variante = variante
        self.sep = trennzeichen

    def datapoint_bas(self, baugruppe_bas: str, bas_relativ: dict) -> str:
        """baugruppe_bas (Block 1-3) + bas_relativ (Block 4-8) -> vollständiger BAS."""
        r = bas_relativ or {}
        parts = [baugruppe_bas]
        # Block 4: Medium/Position
        medium = (r.get("medium") or "").strip()
        if medium:
            parts.append(medium)
        # Block 5: Aggregat
        parts.append(_block(r.get("agg_kennung"), r.get("agg_nr"), self.variante))
        # Block 6: Betriebsmittel
        parts.append(_block(r.get("bm_kennung"), r.get("bm_nr"), self.variante))
        # Block 7: BM-Funktion
        parts.append(_block(r.get("fn_kennung"), r.get("fn_nr"), self.variante))

        bas = self.sep.join(p for p in parts if p)
        # Block 8: Erweiterung (optional, angehängt)
        erweiterung = (r.get("erweiterung") or "").strip()
        if erweiterung:
            bas = bas + self.sep + erweiterung
        return bas

    def funktion(self, bas_relativ: dict) -> str:
        """Block 7 allein (BM-Funktion) für die Anzeige."""
        r = bas_relativ or {}
        return _block(r.get("fn_kennung"), r.get("fn_nr"), self.variante)
