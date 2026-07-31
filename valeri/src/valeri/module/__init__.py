"""Rechenmodule.

Ein Modul = eine fachliche Funktion. Der Import dieses Pakets registriert alle
mitgelieferten Module; die Reihenfolge im Ablauf ergibt sich aus den in den
Modulen deklarierten Daten-Verträgen, nicht aus dieser Datei.

Eigenes Modul ergänzen:
    1. Datei anlegen, ``Rechenmodul`` ableiten, ``id``/``benoetigt``/``liefert``
       setzen und ``@registriere()`` verwenden
    2. Import hier eintragen (oder Paket per Plug-in nachladen)

Bestehendes Modul ersetzen:
    Gleiche ``id``, gleiche ``liefert`` – und ``@registriere(ersetzt=True)``.
"""

from valeri.module import (  # noqa: F401  (Import = Registrierung)
    m10_stammdaten,
    m20_finanzrahmen,
    m30_bedarf,
    m35_speicher,
    m40_erzeuger,
    m50_energiekosten,
    m60_investition,
    m61_kennwerte,
    m62_betriebskosten,
    m70_zahlungsreihe,
    m75_steuern,
    m80_valeri,
    m81_vdi2067,
    m85_kennzahlen,
    m95_bericht,
)
from valeri.module.vergleich import (
    Vergleich,
    Vergleichszeile,
    sensitivitaet,
    sensitivitaet_energiepreis,
    sensitivitaet_investition,
    sensitivitaet_zins,
    vergleiche,
)

__all__ = [
    "Vergleich",
    "Vergleichszeile",
    "sensitivitaet",
    "sensitivitaet_energiepreis",
    "sensitivitaet_investition",
    "sensitivitaet_zins",
    "vergleiche",
]
