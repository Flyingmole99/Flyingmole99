"""Modul-Vertrag.

Jede fachliche Funktion des Werkzeugs ist genau ein Modul. Ein Modul kennt
weder seine Vorgänger noch seine Nachfolger, sondern nur:

* ``benoetigt`` – Schlüssel, die es aus dem Rechenkontext liest
* ``liefert``   – Schlüssel, die es in den Rechenkontext schreibt

Dadurch lässt sich jedes Modul unabhängig austauschen, solange es denselben
Vertrag erfüllt. Die Pipeline bringt die Module allein anhand dieser beiden
Angaben in die richtige Reihenfolge.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Mapping
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:  # pragma: no cover
    from valeri.core.kontext import Rechenkontext


class Rechenmodul(ABC):
    """Basisklasse aller Rechenmodule."""

    #: Eindeutige, stabile Kennung (wird für Austausch/Override verwendet)
    id: str = ""
    #: Sprechender Titel für Protokoll und Bericht
    titel: str = ""
    #: Versionsstand des Rechenwegs – wandert in das Nachweisprotokoll
    version: str = "0.1.0"
    #: Normbezug / Quelle des Rechenwegs (DIN EN 17463 verlangt Nachvollziehbarkeit)
    grundlage: str = ""

    benoetigt: tuple[str, ...] = ()
    liefert: tuple[str, ...] = ()

    #: Modul überspringen, wenn die Eingangsdaten es nicht erfordern
    optional: bool = False

    @abstractmethod
    def berechne(self, ctx: "Rechenkontext") -> Mapping[str, Any]:
        """Berechnet die in ``liefert`` angekündigten Werte."""

    def ist_anwendbar(self, ctx: "Rechenkontext") -> bool:  # pragma: no cover - trivial
        """Hook für optionale Module (z. B. Speicher nur bei vorhandener Angabe)."""
        return True

    def __repr__(self) -> str:  # pragma: no cover - Debug-Hilfe
        return f"<{type(self).__name__} id={self.id!r} v{self.version}>"
