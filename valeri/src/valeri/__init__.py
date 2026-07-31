"""valeri – Wirtschaftlichkeitsberechnungen nach DIN EN 17463 und VDI 2067.

Kurzgebrauch:

    from valeri import lade_projekt, rechne

    projekt = lade_projekt("beispiele/beispiel_wp_vs_kessel.yaml")
    ergebnis = rechne(projekt)
    print(ergebnis.vergleich.als_text())
"""

from __future__ import annotations

from dataclasses import dataclass

from valeri.core.kontext import Rechenkontext
from valeri.core.pipeline import berechne_projekt, berechne_variante
from valeri.core.zeitreihe import Lastgang
from valeri.io import lade_projekt, speichere_projekt
from valeri.modelle.projekt import Projekt, Variante

# Import registriert alle mitgelieferten Module
from valeri import module as _module  # noqa: F401
from valeri.module.vergleich import Vergleich, vergleiche

__version__ = "0.1.0"


@dataclass
class Projektergebnis:
    varianten: dict[str, Rechenkontext]
    vergleich: Vergleich

    def bericht(self, variante: str) -> str:
        return self.varianten[variante].get("ergebnis.bericht")

    def gesamtbericht(self) -> str:
        teile = [self.varianten[name].get("ergebnis.bericht") for name in self.varianten]
        return "\n\n" + ("\n\n" + "=" * 78 + "\n\n").join(teile) + "\n\n" + (
            "=" * 78 + "\n\nVariantenvergleich\n\n" + self.vergleich.als_text()
        )


def rechne(projekt: Projekt) -> Projektergebnis:
    """Rechnet alle Varianten und stellt sie gegenüber."""
    ergebnisse = berechne_projekt(projekt)
    return Projektergebnis(ergebnisse, vergleiche(projekt, ergebnisse))


__all__ = [
    "Lastgang",
    "Projekt",
    "Projektergebnis",
    "Rechenkontext",
    "Variante",
    "berechne_projekt",
    "berechne_variante",
    "lade_projekt",
    "rechne",
    "speichere_projekt",
    "vergleiche",
]
