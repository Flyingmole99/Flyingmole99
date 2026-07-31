"""Erzeugerseite: entweder pauschaler Kostenansatz oder physikalisches System."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from valeri.core.einheiten import Energieart, Energietraeger


class Erzeugertyp:
    """Kennungen der unterstützten Erzeuger (als Konstanten, nicht als Enum,
    damit eigene Typen ohne Änderung des Kerns ergänzt werden können)."""

    WAERMEPUMPE = "waermepumpe"
    KESSEL = "kessel"
    KAELTEMASCHINE = "kaeltemaschine"
    FREIE_KUEHLUNG = "freie_kuehlung"
    FERNWAERME = "fernwaerme"
    FERNKAELTE = "fernkaelte"
    DIREKTSTROM = "direktstrom"
    BHKW = "bhkw"
    KOSTENANSATZ = "kostenansatz"


class Erzeuger(BaseModel):
    """Ein Erzeuger innerhalb einer Variante.

    Die Deckung erfolgt nach ``prioritaet`` (kleiner = zuerst) bis zur
    ``nennleistung_kw``; der Rest geht an den nächsten Erzeuger. Damit lassen
    sich bivalente Anlagen (WP + Spitzenlastkessel) ohne Sonderlogik abbilden.
    """

    name: str
    typ: str
    energieart: Energieart
    prioritaet: int = 1

    #: None -> Auslegung auf die (ggf. durch Speicher gekappte) Spitzenlast
    nennleistung_kw: float | None = Field(None, gt=0)
    #: Auslegungsreserve auf die Spitzenlast (1.1 = 10 % Zuschlag)
    auslegungsfaktor: float = Field(1.0, gt=0)

    # --- Wärmepumpe / Kältemaschine
    jaz: float | None = Field(None, gt=0, description="Jahresarbeitszahl bzw. SEER")
    carnot_guetegrad: float | None = Field(
        None, gt=0, lt=1, description="Alternativ zur JAZ: COP aus Carnot-Gütegrad"
    )
    vorlauftemperatur_c: float = 45.0
    quellentemperatur_c: float = 10.0

    # --- Kessel / BHKW
    nutzungsgrad: float | None = Field(None, gt=0, le=1.2)
    stromkennzahl: float | None = Field(None, gt=0, description="BHKW: P_el / Q_th")

    # --- Netzgebundene Erzeuger
    netzverlust: float = Field(0.0, ge=0, lt=1)

    #: Endenergieträger; None -> aus Typ abgeleitet
    traeger: Energietraeger | None = None
    #: Hilfsenergie (Pumpen, Regelung) als Anteil der Nutzenergie
    hilfsstrom_anteil: float = Field(0.0, ge=0, le=0.5)

    # --- Pauschaler Kostenansatz (typ = "kostenansatz")
    kosten_eur_kwh: float | None = Field(None, ge=0)
    kosten_grundpreis_eur_a: float = 0.0
    kosten_leistungspreis_eur_kw_a: float = 0.0

    #: Verweis auf Investitionspositionen dieses Erzeugers (für Bericht)
    investitionsbezug: list[str] = Field(default_factory=list)


class Erzeugerpark(BaseModel):
    """Alle Erzeuger einer Variante."""

    erzeuger: list[Erzeuger] = Field(default_factory=list)

    def fuer(self, energieart: Energieart) -> list[Erzeuger]:
        return sorted(
            (e for e in self.erzeuger if e.energieart == energieart),
            key=lambda e: e.prioritaet,
        )


#: Vorgabe-Endenergieträger je Erzeugertyp
STANDARD_TRAEGER: dict[str, Energietraeger] = {
    Erzeugertyp.WAERMEPUMPE: Energietraeger.STROM,
    Erzeugertyp.KAELTEMASCHINE: Energietraeger.STROM,
    Erzeugertyp.FREIE_KUEHLUNG: Energietraeger.STROM,
    Erzeugertyp.DIREKTSTROM: Energietraeger.STROM,
    Erzeugertyp.KESSEL: Energietraeger.ERDGAS,
    Erzeugertyp.BHKW: Energietraeger.ERDGAS,
    Erzeugertyp.FERNWAERME: Energietraeger.FERNWAERME,
    Erzeugertyp.FERNKAELTE: Energietraeger.FERNKAELTE,
}
