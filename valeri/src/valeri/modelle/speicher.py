"""Speicher zur Spitzenlastkappung."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from valeri.core.einheiten import Energieart


class Speicher(BaseModel):
    """Energiespeicher, der auf den Nutzenergie-Lastgang wirkt.

    Modi:
      ``maximal``    – kleinstmögliche Spitzenlast bei gegebener Kapazität
      ``zielspitze`` – Kappung auf einen vorgegebenen Leistungswert
      ``kapazitaet_auslegen`` – kleinste Kapazität für eine Zielspitze
    """

    name: str = "Speicher"
    energieart: Energieart
    modus: Literal["maximal", "zielspitze", "kapazitaet_auslegen"] = "maximal"

    kapazitaet_kwh: float | None = Field(None, gt=0)
    nutzbarer_anteil: float = Field(1.0, gt=0, le=1)
    ladeleistung_kw: float | None = Field(None, gt=0)
    entladeleistung_kw: float | None = Field(None, gt=0)

    wirkungsgrad_laden: float = Field(0.98, gt=0, le=1)
    wirkungsgrad_entladen: float = Field(0.98, gt=0, le=1)
    #: Selbstentladung/Wärmeverlust je Tag, bezogen auf den Ladezustand
    verlust_pro_tag: float = Field(0.02, ge=0, lt=1)

    ziel_spitzenlast_kw: float | None = Field(None, gt=0)
    max_kappung_anteil: float = Field(
        0.9, gt=0, le=1, description="Untergrenze der Kappung als Anteil der Spitze"
    )
    ladezustand_start: float = Field(1.0, ge=0, le=1)

    #: Verweis auf die zugehörige Investitionsposition (für Bericht/Zuordnung)
    investitionsbezug: list[str] = Field(default_factory=list)

    def kapazitaet_nutzbar_kwh(self) -> float:
        if self.kapazitaet_kwh is None:
            return 0.0
        return self.kapazitaet_kwh * self.nutzbarer_anteil
