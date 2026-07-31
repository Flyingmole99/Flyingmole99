"""Rechenkontext – Datendrehscheibe zwischen den Modulen.

Der Kontext ist der einzige Weg, auf dem Module Daten austauschen. Jeder
Schreibzugriff wird protokolliert (Modul, Version, Grundlage). Damit ist die
von DIN EN 17463 geforderte Nachvollziehbarkeit der Eingangsgrößen und
Rechenschritte automatisch gegeben.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from valeri.modelle.projekt import Projekt, Variante


@dataclass
class Protokolleintrag:
    modul_id: str
    version: str
    schluessel: str
    grundlage: str = ""
    hinweis: str = ""


@dataclass
class Rechenkontext:
    """Zustand einer Variantenberechnung."""

    projekt: Projekt
    variante: Variante
    werte: dict[str, Any] = field(default_factory=dict)
    protokoll: list[Protokolleintrag] = field(default_factory=list)
    hinweise: list[str] = field(default_factory=list)
    _aktives_modul: tuple[str, str, str] = ("", "", "")

    # ------------------------------------------------------------------ Zugriff

    def hat(self, schluessel: str) -> bool:
        return schluessel in self.werte

    def get(self, schluessel: str) -> Any:
        if schluessel not in self.werte:
            raise KeyError(
                f"{schluessel!r} nicht im Rechenkontext. Fehlt ein vorgelagertes Modul?"
            )
        return self.werte[schluessel]

    def get_oder(self, schluessel: str, vorgabe: Any = None) -> Any:
        return self.werte.get(schluessel, vorgabe)

    def setze(self, schluessel: str, wert: Any) -> None:
        modul_id, version, grundlage = self._aktives_modul
        self.werte[schluessel] = wert
        self.protokoll.append(
            Protokolleintrag(modul_id, version, schluessel, grundlage)
        )

    def notiere(self, text: str) -> None:
        """Fachlicher Hinweis für Bericht und Plausibilitätsprüfung."""
        modul_id = self._aktives_modul[0]
        self.hinweise.append(f"[{modul_id}] {text}" if modul_id else text)

    # -------------------------------------------------------------- Verwaltung

    def betrete_modul(self, modul_id: str, version: str, grundlage: str) -> None:
        self._aktives_modul = (modul_id, version, grundlage)

    def verlasse_modul(self) -> None:
        self._aktives_modul = ("", "", "")

    def zusammenfassung(self) -> dict[str, Any]:
        """Skalare Ergebniswerte für Bericht/Export (Zeitreihen ausgenommen)."""
        return {
            k: v
            for k, v in self.werte.items()
            if isinstance(v, (int, float, str, bool)) or v is None
        }
