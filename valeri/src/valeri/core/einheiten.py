"""Grundbegriffe, Einheiten und Aufzählungstypen.

Konvention im gesamten Projekt (bewusst eng gehalten, damit Module ohne
Umrechnungslogik zusammenarbeiten):

* Energie   -> kWh
* Leistung  -> kW
* Geld      -> EUR
* Preise    -> EUR/kWh bzw. EUR/(kW*a)
* Zeit      -> Jahre (a), Zeitreihen in Minuten-Auflösung
* Anteile / Zinssätze -> dimensionslos (0.05 = 5 %)
"""

from __future__ import annotations

from enum import StrEnum


class Energieart(StrEnum):
    """Nutzenergiearten, die das Werkzeug abbildet."""

    WAERME = "waerme"
    KAELTE = "kaelte"
    STROM = "strom"


class Energietraeger(StrEnum):
    """Endenergieträger (Bezugsseite) – Grundlage der Energiekostenrechnung."""

    STROM = "strom"
    ERDGAS = "erdgas"
    HEIZOEL = "heizoel"
    PELLETS = "pellets"
    FERNWAERME = "fernwaerme"
    FERNKAELTE = "fernkaelte"
    WASSERSTOFF = "wasserstoff"


class Rechenmodus(StrEnum):
    """Bezugsrahmen der Zahlungsreihe.

    VOLLKOSTEN  – jede Variante wird absolut gerechnet, Vergleich über Differenz
                  der Kapitalwerte bzw. Annuitäten.
    DIFFERENZ   – nur die Zahlungsdifferenz Maßnahme ./. Referenz wird bewertet
                  (Vorgehen der DIN EN 17463 für einzelne Effizienzmaßnahmen).
    """

    VOLLKOSTEN = "vollkosten"
    DIFFERENZ = "differenz"


class Preisbasis(StrEnum):
    """Nominal = mit Preissteigerung, Real = preisbereinigt."""

    NOMINAL = "nominal"
    REAL = "real"


STUNDEN_PRO_JAHR = 8760
