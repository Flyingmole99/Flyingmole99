"""Datenmodelle – die Verträge zwischen den Modulen."""

from valeri.modelle.energie import Energiepreis, Erloes, Lastgangquelle, Verbrauch
from valeri.modelle.ergebnis import Jahreszahlung, Kennzahlen, Zahlungsreihe
from valeri.modelle.erzeuger import Erzeuger, Erzeugerpark, Erzeugertyp
from valeri.modelle.finanzen import Finanzrahmen, Preisaenderung, Steuerparameter
from valeri.modelle.investition import (
    Betriebsparameter,
    Foerderung,
    Investition,
    Investitionsposition,
    Positionsdaten,
)
from valeri.modelle.projekt import Projekt, Variante
from valeri.modelle.speicher import Speicher

__all__ = [
    "Betriebsparameter",
    "Energiepreis",
    "Erloes",
    "Erzeuger",
    "Erzeugerpark",
    "Erzeugertyp",
    "Finanzrahmen",
    "Foerderung",
    "Investition",
    "Investitionsposition",
    "Jahreszahlung",
    "Kennzahlen",
    "Lastgangquelle",
    "Positionsdaten",
    "Preisaenderung",
    "Projekt",
    "Speicher",
    "Steuerparameter",
    "Variante",
    "Verbrauch",
    "Zahlungsreihe",
]
