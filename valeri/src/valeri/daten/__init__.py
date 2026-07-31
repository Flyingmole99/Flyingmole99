"""Stammdaten-Zugriff: VDI-2067-Kategorien und AfA-Schlüssel.

Die Kennwerte liegen bewusst als YAML neben dem Code. Wer eigene Bürowerte
pflegt, ersetzt die Datei oder lädt eine zweite über ``lade_kataloge``, ohne
eine Codezeile zu ändern.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import yaml

VDI_DATEI = Path(__file__).with_name("vdi2067_kategorien.yaml")
AFA_DATEI = Path(__file__).with_name("afa_bmf.yaml")


@dataclass(frozen=True)
class VdiKategorie:
    schluessel: str
    bezeichnung: str
    gruppe: str
    nutzungsdauer_a: float
    instandsetzung_anteil: float
    wartung_anteil: float
    bedienaufwand_h_a: float
    afa_schluessel: str | None = None
    geprueft: bool = False


@dataclass(frozen=True)
class AfaEintrag:
    schluessel: str
    bezeichnung: str
    nutzungsdauer_a: float
    methode: str = "linear"
    fundstelle: str = ""
    geprueft: bool = False


class Katalog:
    """Nachschlagewerk für Kategorien und AfA-Schlüssel."""

    def __init__(self, vdi_datei: Path = VDI_DATEI, afa_datei: Path = AFA_DATEI) -> None:
        self.vdi_version, self.kategorien = _lade_vdi(vdi_datei)
        self.afa_version, self.afa = _lade_afa(afa_datei)

    # ---------------------------------------------------------------- Zugriff

    def kategorie(self, schluessel: str) -> VdiKategorie:
        if schluessel not in self.kategorien:
            raise KeyError(
                f"Unbekannte Produktkategorie {schluessel!r}. "
                f"Verfügbar: {', '.join(sorted(self.kategorien))}"
            )
        return self.kategorien[schluessel]

    def afa_eintrag(self, schluessel: str) -> AfaEintrag:
        if schluessel not in self.afa:
            raise KeyError(
                f"Unbekannter AfA-Schlüssel {schluessel!r}. "
                f"Verfügbar: {', '.join(sorted(self.afa))}"
            )
        return self.afa[schluessel]

    def suche(self, text: str) -> list[VdiKategorie]:
        text = text.lower()
        return [
            k
            for k in self.kategorien.values()
            if text in k.schluessel.lower() or text in k.bezeichnung.lower()
        ]

    def ungeprueft(self) -> list[str]:
        return sorted(
            [k.schluessel for k in self.kategorien.values() if not k.geprueft]
            + [f"afa:{a.schluessel}" for a in self.afa.values() if not a.geprueft]
        )


def _lade_vdi(pfad: Path) -> tuple[str, dict[str, VdiKategorie]]:
    roh = yaml.safe_load(pfad.read_text(encoding="utf-8"))
    kategorien = {
        schluessel: VdiKategorie(
            schluessel=schluessel,
            bezeichnung=eintrag.get("bezeichnung", schluessel),
            gruppe=eintrag.get("gruppe", ""),
            nutzungsdauer_a=float(eintrag["nutzungsdauer_a"]),
            instandsetzung_anteil=float(eintrag.get("instandsetzung_anteil", 0.0)),
            wartung_anteil=float(eintrag.get("wartung_anteil", 0.0)),
            bedienaufwand_h_a=float(eintrag.get("bedienaufwand_h_a", 0.0)),
            afa_schluessel=eintrag.get("afa_schluessel"),
            geprueft=bool(eintrag.get("geprueft", False)),
        )
        for schluessel, eintrag in (roh.get("kategorien") or {}).items()
    }
    return roh.get("version", "?"), kategorien


def _lade_afa(pfad: Path) -> tuple[str, dict[str, AfaEintrag]]:
    roh = yaml.safe_load(pfad.read_text(encoding="utf-8"))
    eintraege = {
        schluessel: AfaEintrag(
            schluessel=schluessel,
            bezeichnung=eintrag.get("bezeichnung", schluessel),
            nutzungsdauer_a=float(eintrag["nutzungsdauer_a"]),
            methode=eintrag.get("methode", "linear"),
            fundstelle=eintrag.get("fundstelle", ""),
            geprueft=bool(eintrag.get("geprueft", False)),
        )
        for schluessel, eintrag in (roh.get("schluessel") or {}).items()
    }
    return roh.get("version", "?"), eintraege


@lru_cache(maxsize=1)
def katalog() -> Katalog:
    """Standardkatalog (zwischengespeichert)."""
    return Katalog()


def lade_kataloge(vdi_datei: str | Path, afa_datei: str | Path) -> Katalog:
    """Eigene Bürodatenbank laden."""
    return Katalog(Path(vdi_datei), Path(afa_datei))
