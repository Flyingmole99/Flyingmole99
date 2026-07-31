"""Investitionskosten, Nutzungsdauern und betriebsgebundene Kosten.

Kernidee: Der Anwender ordnet einer Position nur eine *Produktkategorie* zu.
Daraus werden abgeleitet
  * technische Nutzungsdauer, Instandsetzung, Wartung, Bedienaufwand -> VDI 2067
  * steuerliche Nutzungsdauer (AfA)                                  -> AfA-Tabelle BMF
Jeder abgeleitete Wert lässt sich feldweise überschreiben; gesetzte Werte
haben immer Vorrang und werden im Protokoll als "manuell" gekennzeichnet.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field


class Foerderung(BaseModel):
    """Zuschuss zu einer Investition."""

    bezeichnung: str = "Förderung"
    anteil: float = Field(0.0, ge=0, le=1)
    betrag_eur: float = Field(0.0, ge=0)
    hoechstbetrag_eur: float | None = None
    #: ertragswirksam = mindert die AfA-Bemessungsgrundlage (Regelfall)
    behandlung: Literal["minderung_afa", "ertrag_sofort"] = "minderung_afa"

    def hoehe(self, investition_eur: float) -> float:
        betrag = self.betrag_eur + self.anteil * investition_eur
        if self.hoechstbetrag_eur is not None:
            betrag = min(betrag, self.hoechstbetrag_eur)
        return min(betrag, investition_eur)


class Investitionsposition(BaseModel):
    """Eine Anlagenkomponente mit ihren Kosten- und Dauerkennwerten."""

    bezeichnung: str
    #: Schlüssel in daten/vdi2067_kategorien.yaml
    kategorie: str | None = None
    #: Schlüssel in daten/afa_bmf.yaml; None -> Vorgabe aus der Kategorie
    afa_schluessel: str | None = None

    menge: float = Field(1.0, gt=0)
    einzelpreis_eur: float = Field(..., ge=0)
    einheit: str = "Stk"

    # --- Überschreibungen (None = automatisch ableiten)
    nutzungsdauer_a: float | None = Field(None, gt=0, description="technisch, VDI 2067")
    afa_dauer_a: float | None = Field(None, gt=0, description="steuerlich, AfA-Tabelle")
    instandsetzung_anteil: float | None = Field(
        None, ge=0, description="Anteil der Investition je Jahr"
    )
    wartung_anteil: float | None = Field(None, ge=0)
    bedienaufwand_h_a: float | None = Field(None, ge=0)

    # --- Sonstiges
    foerderung: Foerderung | None = None
    ersatzinvestition: bool = True
    restwert: bool = True
    #: Jahr der Erstinvestition (0 = Projektstart, >0 = spätere Maßnahme)
    investitionsjahr: int = 0
    aktivierungspflichtig: bool = True
    bemerkung: str = ""

    def investition_eur(self) -> float:
        return self.menge * self.einzelpreis_eur


class Investition(BaseModel):
    """Investitionsblock einer Variante."""

    positionen: list[Investitionsposition] = Field(default_factory=list)
    #: Baunebenkosten als Anteil der Summe der Positionen (Planung, Honorare)
    nebenkosten_anteil: float = Field(0.0, ge=0, le=1)
    nebenkosten_bezeichnung: str = "Planung/Baunebenkosten"
    #: Nebenkosten folgen der AfA/Nutzungsdauer dieser Kategorie
    nebenkosten_kategorie: str | None = None
    gesamtfoerderung: Foerderung | None = None

    def summe_eur(self) -> float:
        basis = sum(p.investition_eur() for p in self.positionen)
        return basis * (1.0 + self.nebenkosten_anteil)


class Positionsdaten(BaseModel):
    """Ergebnis der Kennwertableitung – Vertrag zwischen m61 und den Folgemodulen.

    ``herkunft`` dokumentiert je Kennwert, ob er manuell gesetzt ("manuell"),
    aus der Produktkategorie ("vdi2067:<schluessel>") oder aus der AfA-Tabelle
    ("afa:<schluessel>") stammt. DIN EN 17463 verlangt genau diese
    Nachvollziehbarkeit der Eingangsgrößen.
    """

    position: Investitionsposition
    investition_eur: float
    foerderung_eur: float = 0.0
    nutzungsdauer_a: float = 20.0
    afa_dauer_a: float = 20.0
    instandsetzung_eur_a: float = 0.0
    wartung_eur_a: float = 0.0
    bedienaufwand_h_a: float = 0.0
    herkunft: dict[str, str] = Field(default_factory=dict)

    @property
    def bemessungsgrundlage_eur(self) -> float:
        """Aktivierungsfähiger Betrag nach Abzug ertragsmindernder Zuschüsse."""
        return max(0.0, self.investition_eur - self.foerderung_eur)


class Betriebsparameter(BaseModel):
    """Betriebsgebundene Randdaten, die nicht an einer Position hängen."""

    stundensatz_eur_h: float = Field(65.0, ge=0)
    sonstige_kosten_eur_a: float = Field(0.0, ge=0)
    versicherung_anteil_investition: float = Field(0.0, ge=0)
    verwaltung_eur_a: float = Field(0.0, ge=0)
    bemerkung: str = ""
