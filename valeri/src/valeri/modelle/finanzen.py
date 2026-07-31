"""Finanzieller Rahmen: Kapitalkosten, Steuern, Preisentwicklung."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from valeri.core.einheiten import Preisbasis
from valeri.core.finanzmathematik import wacc


class Steuerparameter(BaseModel):
    """Ertragsteuerliche Randdaten.

    ``modus="auto"`` leitet den Ertragsteuersatz einer Kapitalgesellschaft aus
    Körperschaftsteuer + Solidaritätszuschlag + Gewerbesteuer ab.
    ``modus="manuell"`` verwendet ausschließlich ``satz_manuell``.
    """

    modus: Literal["auto", "manuell"] = "auto"
    koerperschaftsteuer: float = Field(0.15, ge=0, le=1)
    solidaritaetszuschlag: float = Field(0.055, ge=0, le=1)
    gewerbesteuer_messzahl: float = Field(0.035, ge=0, le=1)
    gewerbesteuer_hebesatz: float = Field(4.00, ge=0, description="400 % = 4.00")
    satz_manuell: float | None = Field(None, ge=0, le=1)

    #: Gewerbesteuerliche Hinzurechnung von 25 % der Schuldentgelte (§ 8 Nr. 1a GewStG)
    zins_hinzurechnung: bool = False
    hinzurechnung_freibetrag_eur: float = 200_000.0

    #: True  = negative Bemessungsgrundlagen werden vorgetragen
    #: False = sofortige Verrechnung mit übrigen Erträgen des Unternehmens
    #:         (Regelfall bei Vollkostenbetrachtungen eines laufenden Betriebs)
    verlustvortrag: bool = False

    #: Steuerliche Wirkung vollständig ausblenden (z. B. Kommune, Eigenbetrieb)
    steuerneutral: bool = False

    def effektiver_satz(self) -> float:
        if self.steuerneutral:
            return 0.0
        if self.modus == "manuell":
            if self.satz_manuell is None:
                raise ValueError("modus='manuell' erfordert satz_manuell")
            return self.satz_manuell
        kst = self.koerperschaftsteuer * (1.0 + self.solidaritaetszuschlag)
        gewst = self.gewerbesteuer_messzahl * self.gewerbesteuer_hebesatz
        return kst + gewst


class Preisaenderung(BaseModel):
    """Jährliche Preisänderungsraten je Kostenart (nominal, VDI 2067 Blatt 1).

    Die Werte sind Vorgaben und *müssen* projektbezogen belegt werden –
    DIN EN 17463 verlangt die Dokumentation der unterstellten Preispfade.
    """

    allgemein: float = 0.02
    strom: float = 0.03
    erdgas: float = 0.03
    heizoel: float = 0.03
    pellets: float = 0.02
    fernwaerme: float = 0.03
    fernkaelte: float = 0.03
    wasserstoff: float = 0.03
    investition: float = 0.02
    wartung_instandsetzung: float = 0.02
    personal: float = 0.025
    sonstige: float = 0.02
    erloese: float = 0.02
    co2_preis: float = 0.08

    def fuer(self, kostenart: str) -> float:
        return getattr(self, kostenart, self.allgemein)


class Finanzrahmen(BaseModel):
    """Randdaten der Basisvariante: Zeitraum, Kapitalkosten, Steuern, Preispfade."""

    betrachtungszeitraum_a: int = Field(20, gt=0, le=80)
    basisjahr: int = 2026

    eigenkapitalquote: float = Field(0.30, ge=0, le=1)
    eigenkapitalrendite: float = Field(0.08, ge=0)
    fremdkapitalzins: float = Field(0.045, ge=0)
    fremdkapital_laufzeit_a: int = Field(15, gt=0)

    kalkulationszins_modus: Literal["wacc", "manuell"] = "wacc"
    kalkulationszins_manuell: float | None = None

    preisbasis: Preisbasis = Preisbasis.NOMINAL
    steuern: Steuerparameter = Field(default_factory=Steuerparameter)
    preisaenderung: Preisaenderung = Field(default_factory=Preisaenderung)

    #: Fremdkapital tatsächlich als Zahlungsreihe abbilden (VOFI-nah) statt
    #: ausschließlich über den WACC im Diskontierungssatz.
    finanzierung_explizit: bool = False

    def steuersatz(self) -> float:
        return self.steuern.effektiver_satz()

    def kalkulationszins(self) -> float:
        if self.kalkulationszins_modus == "manuell":
            if self.kalkulationszins_manuell is None:
                raise ValueError("kalkulationszins_modus='manuell' erfordert einen Wert")
            return self.kalkulationszins_manuell
        zins = wacc(
            self.eigenkapitalquote,
            self.eigenkapitalrendite,
            self.fremdkapitalzins,
            self.steuersatz(),
        )
        if self.preisbasis is Preisbasis.REAL:
            zins = (1.0 + zins) / (1.0 + self.preisaenderung.allgemein) - 1.0
        return zins
