"""Projekt- und Variantenmodell – die vollständige Eingabe des Werkzeugs."""

from __future__ import annotations

from pydantic import BaseModel, Field

from valeri.core.einheiten import Energieart, Energietraeger, Rechenmodus
from valeri.modelle.energie import Energiepreis, Erloes, Verbrauch
from valeri.modelle.erzeuger import Erzeugerpark
from valeri.modelle.finanzen import Finanzrahmen
from valeri.modelle.investition import Betriebsparameter, Investition
from valeri.modelle.speicher import Speicher


class Variante(BaseModel):
    """Eine zu bewertende technische Lösung.

    Der Bedarf (Nutzenergie) kommt in der Regel aus dem Projekt und ist für
    alle Varianten gleich; eine Variante darf ihn gezielt überschreiben
    (z. B. Effizienzmaßnahme mit geringerem Wärmebedarf).
    """

    name: str
    beschreibung: str = ""
    ist_referenz: bool = False

    bedarf_ueberschreibung: list[Verbrauch] = Field(default_factory=list)
    erzeugerpark: Erzeugerpark = Field(default_factory=Erzeugerpark)
    speicher: list[Speicher] = Field(default_factory=list)
    investition: Investition = Field(default_factory=Investition)
    betrieb: Betriebsparameter = Field(default_factory=Betriebsparameter)
    energiepreise: list[Energiepreis] = Field(default_factory=list)
    erloese: list[Erloes] = Field(default_factory=list)

    #: Nicht-energetische Nutzen (DIN EN 17463: "non-energy benefits"),
    #: z. B. geringere Ausfallzeiten, Qualitätsgewinne, Instandhaltungsvorteile
    weitere_nutzen: list[Erloes] = Field(default_factory=list)


class Projekt(BaseModel):
    """Wurzelobjekt der Berechnung."""

    name: str
    beschreibung: str = ""
    bearbeiter: str = ""
    stand: str = ""

    finanzrahmen: Finanzrahmen = Field(default_factory=Finanzrahmen)
    rechenmodus: Rechenmodus = Rechenmodus.VOLLKOSTEN
    bedarf: list[Verbrauch] = Field(default_factory=list)
    energiepreise: list[Energiepreis] = Field(default_factory=list)
    varianten: list[Variante] = Field(default_factory=list)

    def referenzvariante(self) -> Variante | None:
        for v in self.varianten:
            if v.ist_referenz:
                return v
        return None

    def bedarf_fuer(self, variante: Variante) -> list[Verbrauch]:
        """Projektbedarf, überlagert von den Überschreibungen der Variante."""
        zusammen: dict[Energieart, Verbrauch] = {v.energieart: v for v in self.bedarf}
        for v in variante.bedarf_ueberschreibung:
            zusammen[v.energieart] = v
        return list(zusammen.values())

    def preis_fuer(self, variante: Variante, traeger: Energietraeger) -> Energiepreis | None:
        for p in variante.energiepreise:
            if p.traeger == traeger:
                return p
        for p in self.energiepreise:
            if p.traeger == traeger:
                return p
        return None
