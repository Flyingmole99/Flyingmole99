"""Ergebnisstrukturen: Zahlungsreihe und Kennzahlen."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Jahreszahlung:
    """Alle Zahlungsströme eines Jahres (Vorzeichen: Auszahlung negativ)."""

    jahr: int
    investition: float = 0.0
    foerderung: float = 0.0
    restwert: float = 0.0
    energiekosten: float = 0.0
    wartung_instandsetzung: float = 0.0
    bedienung: float = 0.0
    sonstige_kosten: float = 0.0
    co2_kosten: float = 0.0
    erloese: float = 0.0
    weitere_nutzen: float = 0.0

    # Finanzierung / Steuern (nachgelagert befüllt)
    fk_auszahlung: float = 0.0
    fk_zins: float = 0.0
    fk_tilgung: float = 0.0
    abschreibung: float = 0.0
    steuer: float = 0.0

    @property
    def betriebsergebnis(self) -> float:
        """Zahlungswirksames Ergebnis vor Investition, Zinsen und Steuern."""
        return (
            self.energiekosten
            + self.wartung_instandsetzung
            + self.bedienung
            + self.sonstige_kosten
            + self.co2_kosten
            + self.erloese
            + self.weitere_nutzen
        )

    @property
    def cashflow_vor_steuern(self) -> float:
        return (
            self.betriebsergebnis
            + self.investition
            + self.foerderung
            + self.restwert
        )

    @property
    def steuerbemessung(self) -> float:
        """Ertragsteuerliche Bemessungsgrundlage (ohne Investitionsauszahlung)."""
        return self.betriebsergebnis + self.abschreibung + self.fk_zins

    @property
    def cashflow_nach_steuern(self) -> float:
        return self.cashflow_vor_steuern + self.steuer

    @property
    def cashflow_eigenkapital(self) -> float:
        """Sicht des Eigenkapitalgebers (nur bei expliziter Finanzierung)."""
        return (
            self.cashflow_nach_steuern
            + self.fk_auszahlung
            + self.fk_zins
            + self.fk_tilgung
        )


@dataclass
class Zahlungsreihe:
    """Zahlungsreihe über den Betrachtungszeitraum, Jahr 0 .. T."""

    jahre: list[Jahreszahlung] = field(default_factory=list)

    def __len__(self) -> int:
        return len(self.jahre)

    def __getitem__(self, jahr: int) -> Jahreszahlung:
        return self.jahre[jahr]

    def reihe(self, attribut: str = "cashflow_nach_steuern") -> list[float]:
        return [getattr(j, attribut) for j in self.jahre]

    def summe(self, attribut: str) -> float:
        return sum(getattr(j, attribut) for j in self.jahre)


@dataclass
class Kennzahlen:
    """Ergebnisgrößen der Wirtschaftlichkeitsbetrachtung."""

    kapitalwert_eur: float = 0.0
    kalkulationszins: float = 0.0
    annuitaet_eur_a: float = 0.0
    interner_zinsfuss: float | None = None
    amortisation_statisch_a: float | None = None
    amortisation_dynamisch_a: float | None = None
    kapitalwertrate: float | None = None
    waermegestehungskosten_eur_kwh: float | None = None
    kaeltegestehungskosten_eur_kwh: float | None = None
    co2_vermeidungskosten_eur_t: float | None = None
