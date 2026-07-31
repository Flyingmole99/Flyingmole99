"""Finanzmathematische Grundfunktionen.

Bewusst frei von Domänenwissen – hier stehen nur die Formeln, die von
mehreren Auswertemodulen (VALERI, VDI 2067, Kennzahlen) gebraucht werden.
"""

from __future__ import annotations

from collections.abc import Sequence


def barwert(zahlungen: Sequence[float], zins: float, ab_jahr: int = 0) -> float:
    """Barwert einer Zahlungsreihe (zahlungen[k] fällt in Jahr ab_jahr + k an)."""
    q = 1.0 + zins
    return sum(z / q ** (ab_jahr + k) for k, z in enumerate(zahlungen))


def annuitaetsfaktor(zins: float, jahre: int) -> float:
    """a = (q-1) / (1 - q^-T) – wandelt einen Barwert in gleiche Jahresraten."""
    if jahre <= 0:
        raise ValueError("Betrachtungszeitraum muss > 0 sein")
    if abs(zins) < 1e-12:
        return 1.0 / jahre
    q = 1.0 + zins
    return (q - 1.0) / (1.0 - q ** (-jahre))


def barwertfaktor(zins: float, preisaenderung: float, jahre: int) -> float:
    """Preisdynamischer Barwertfaktor b(q, r) nach VDI 2067 Blatt 1.

    b = (1 - (r/q)^T) / (q - r) mit q = 1+Zins, r = 1+Preisänderungsrate.
    Sonderfall q == r: b = T / q.
    """
    q = 1.0 + zins
    r = 1.0 + preisaenderung
    if abs(q - r) < 1e-12:
        return jahre / q
    return (1.0 - (r / q) ** jahre) / (q - r)


def interner_zinsfuss(
    zahlungen: Sequence[float],
    unten: float = -0.95,
    oben: float = 5.0,
    toleranz: float = 1e-10,
) -> float | None:
    """Interner Zinsfuß per Bisektion. None, wenn kein Vorzeichenwechsel.

    ``toleranz`` wirkt auf die Zinsspanne; da der Kapitalwert je nach
    Projektgröße stark skaliert, ist das der robustere Abbruchmaßstab.
    """
    f_unten = barwert(zahlungen, unten)
    f_oben = barwert(zahlungen, oben)
    if f_unten * f_oben > 0:
        return None
    for _ in range(200):
        mitte = (unten + oben) / 2.0
        f_mitte = barwert(zahlungen, mitte)
        if f_mitte == 0.0 or (oben - unten) < toleranz:
            return mitte
        if f_unten * f_mitte < 0:
            oben, f_oben = mitte, f_mitte
        else:
            unten, f_unten = mitte, f_mitte
    return (unten + oben) / 2.0


def amortisationszeit(zahlungen: Sequence[float], zins: float = 0.0) -> float | None:
    """Erstes Jahr, in dem der (ggf. diskontierte) Kapitalwert >= 0 wird.

    Rückgabe mit linearer Interpolation innerhalb des Jahres; None, wenn die
    Amortisation im Betrachtungszeitraum nicht erreicht wird.
    """
    q = 1.0 + zins
    kumuliert = 0.0
    vorher = 0.0
    for jahr, z in enumerate(zahlungen):
        vorher = kumuliert
        kumuliert += z / q**jahr
        if kumuliert >= 0 and jahr > 0:
            spanne = kumuliert - vorher
            anteil = (-vorher / spanne) if spanne > 0 else 0.0
            return jahr - 1 + anteil
    return None


def wacc(
    eigenkapitalquote: float,
    eigenkapitalrendite: float,
    fremdkapitalzins: float,
    steuersatz: float,
) -> float:
    """Gewichteter Kapitalkostensatz nach Steuern.

    WACC = q_EK * r_EK + (1 - q_EK) * r_FK * (1 - s)

    Der Faktor (1 - s) bildet die steuerliche Abzugsfähigkeit der
    Fremdkapitalzinsen ab (Tax Shield).
    """
    if not 0.0 <= eigenkapitalquote <= 1.0:
        raise ValueError("Eigenkapitalquote muss zwischen 0 und 1 liegen")
    return (
        eigenkapitalquote * eigenkapitalrendite
        + (1.0 - eigenkapitalquote) * fremdkapitalzins * (1.0 - steuersatz)
    )


def real_aus_nominal(nominalzins: float, inflation: float) -> float:
    """Fisher-Gleichung: (1+i_nom) = (1+i_real) * (1+Inflation)."""
    return (1.0 + nominalzins) / (1.0 + inflation) - 1.0


def annuitaetendarlehen(
    darlehen: float, zins: float, laufzeit: int, jahre: int
) -> list[tuple[float, float, float]]:
    """Tilgungsplan als Liste (Zins, Tilgung, Restschuld) je Jahr 1..jahre."""
    if darlehen <= 0 or laufzeit <= 0:
        return [(0.0, 0.0, 0.0) for _ in range(jahre)]
    rate = darlehen * annuitaetsfaktor(zins, laufzeit)
    plan: list[tuple[float, float, float]] = []
    rest = darlehen
    for jahr in range(1, jahre + 1):
        if jahr > laufzeit or rest <= 1e-9:
            plan.append((0.0, 0.0, 0.0))
            continue
        zinsanteil = rest * zins
        tilgung = min(rate - zinsanteil, rest)
        rest -= tilgung
        plan.append((zinsanteil, tilgung, rest))
    return plan
