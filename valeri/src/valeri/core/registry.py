"""Registry der Rechenmodule.

Module melden sich per Dekorator an. Wer ein Modul ersetzen will, registriert
eine eigene Klasse mit derselben ``id`` und ``ersetzt=True`` – der Rest des
Werkzeugs bleibt unverändert.
"""

from __future__ import annotations

from collections.abc import Iterable

from valeri.core.modul import Rechenmodul

_REGISTRY: dict[str, type[Rechenmodul]] = {}


def registriere(ersetzt: bool = False):
    """Klassen-Dekorator zur Anmeldung eines Moduls."""

    def _deko(cls: type[Rechenmodul]) -> type[Rechenmodul]:
        if not cls.id:
            raise ValueError(f"{cls.__name__} hat keine id")
        if cls.id in _REGISTRY and not ersetzt:
            raise ValueError(
                f"Modul-id {cls.id!r} bereits vergeben durch "
                f"{_REGISTRY[cls.id].__name__}. Für bewussten Austausch "
                f"@registriere(ersetzt=True) verwenden."
            )
        _REGISTRY[cls.id] = cls
        return cls

    return _deko


def hole(modul_id: str) -> type[Rechenmodul]:
    if modul_id not in _REGISTRY:
        raise KeyError(f"Unbekanntes Modul: {modul_id!r}")
    return _REGISTRY[modul_id]


def alle() -> dict[str, type[Rechenmodul]]:
    return dict(_REGISTRY)


def instanzen(ids: Iterable[str] | None = None) -> list[Rechenmodul]:
    """Instanziiert die genannten Module (Vorgabe: alle registrierten)."""
    gewaehlt = list(ids) if ids is not None else sorted(_REGISTRY)
    return [hole(i)() for i in gewaehlt]


def leeren() -> None:  # pragma: no cover - nur für Tests
    _REGISTRY.clear()
