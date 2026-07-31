"""Bedarfs- und Preisseite der Energie."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator

from valeri.core.einheiten import Energieart, Energietraeger


class Lastgangquelle(BaseModel):
    """Woher der Lastgang einer Energieart kommt.

    datei    – CSV/Excel-Zeitreihe (bevorzugt, echte Messwerte)
    profil   – parametrisches Ersatzprofil aus Jahressumme + Kennwerten
    konstant – Bandlast (nur für Grobabschätzungen)
    """

    art: Literal["datei", "profil", "konstant"] = "profil"
    pfad: str | None = None
    spalte: str | int | None = None
    zeitspalte: str | int | None = None
    trennzeichen: str = ";"
    dezimaltrennzeichen: str = ","
    einheit: Literal["kW", "kWh", "MW", "MWh"] = "kW"
    aufloesung_min: int = 60

    #: Parameter des Ersatzprofils (art="profil")
    profiltyp: Literal["waerme", "kaelte", "strom", "band"] = "band"
    vollbenutzungsstunden_h: float | None = None
    tagesgang_amplitude: float = Field(0.3, ge=0, le=1)
    wochenend_faktor: float = Field(0.7, gt=0, le=1)
    heizgrenze_c: float = 15.0


class Verbrauch(BaseModel):
    """Nutzenergiebedarf einer Energieart."""

    energieart: Energieart
    jahresbedarf_kwh: float = Field(..., ge=0)
    spitzenlast_kw: float | None = Field(
        None, gt=0, description="Optional; sonst aus Lastgang abgeleitet"
    )
    lastgang: Lastgangquelle = Field(default_factory=Lastgangquelle)
    gleichzeitigkeit: float = Field(1.0, gt=0, le=1)
    bemerkung: str = ""

    @model_validator(mode="after")
    def _profiltyp_ergaenzen(self) -> "Verbrauch":
        if self.lastgang.art == "profil" and self.lastgang.profiltyp == "band":
            self.lastgang.profiltyp = self.energieart.value  # type: ignore[assignment]
        return self


class Energiepreis(BaseModel):
    """Bezugspreis eines Endenergieträgers.

    Der Leistungspreis wird auf die Jahreshöchstlast des jeweiligen Trägers
    angesetzt – hier wirkt die Spitzenlastkappung durch Speicher.
    """

    traeger: Energietraeger
    arbeitspreis_eur_kwh: float = Field(..., ge=0)
    leistungspreis_eur_kw_a: float = Field(0.0, ge=0)
    grundpreis_eur_a: float = Field(0.0, ge=0)
    #: Emissionsfaktor für CO2-Bilanz und CO2-Preis (kg/kWh Endenergie)
    co2_faktor_kg_kwh: float = 0.0
    co2_preis_eur_t: float = 0.0
    #: Abweichende Preisänderungsrate; sonst aus Preisaenderung des Trägers
    preisaenderung: float | None = None
    bemerkung: str = ""


class Erloes(BaseModel):
    """Einnahmen, z. B. Stromeinspeisung, Wärmeverkauf, Förderprämien im Betrieb."""

    bezeichnung: str
    betrag_eur_a: float = 0.0
    menge_kwh_a: float = 0.0
    preis_eur_kwh: float = 0.0
    preisaenderung_art: str = "erloese"
    ab_jahr: int = 1
    bis_jahr: int | None = None

    def betrag(self) -> float:
        return self.betrag_eur_a + self.menge_kwh_a * self.preis_eur_kwh
