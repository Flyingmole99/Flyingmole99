"""M40 – Erzeugung: Nutzenergie -> Endenergie je Energieträger.

Zwei Wege, wie vom Anwender gefordert:
  1. Erzeugersystem hinterlegen (Wärmepumpe, Kessel, Kältemaschine, ...):
     Der Lastgang wird nach Priorität auf die Erzeuger aufgeteilt und über
     Arbeitszahl bzw. Nutzungsgrad in Endenergie umgerechnet.
  2. Kostenansatz hinterlegen (typ = "kostenansatz"): Es wird nicht
     physikalisch gerechnet, sondern direkt mit EUR/kWh Nutzenergie.

Neue Erzeugertypen werden in ``UMRECHNUNG`` ergänzt – ohne Eingriff in die
Modullogik.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Any

from valeri.core.einheiten import Energieart, Energietraeger
from valeri.core.kontext import Rechenkontext
from valeri.core.modul import Rechenmodul
from valeri.core.registry import registriere
from valeri.core.zeitreihe import Lastgang
from valeri.modelle.erzeuger import STANDARD_TRAEGER, Erzeuger, Erzeugertyp


@dataclass
class Erzeugerauslegung:
    name: str
    typ: str
    energieart: Energieart
    nennleistung_kw: float
    deckung_kwh: float
    deckungsanteil: float
    endenergie_kwh: float
    arbeitszahl: float
    traeger: Energietraeger | None
    volllaststunden_h: float
    hinweis: str = ""


@registriere()
class Erzeugung(Rechenmodul):
    id = "m40_erzeuger"
    titel = "Erzeugersysteme und Endenergiebedarf"
    grundlage = "Arbeitszahl/Nutzungsgrad je Erzeuger, Deckung nach Priorität"
    benoetigt = ("speicher.nutzenergie",)
    liefert = (
        "erzeuger.endenergie",
        "erzeuger.auslegung",
        "erzeuger.kostenansatz_eur_a",
    )

    def berechne(self, ctx: Rechenkontext) -> Mapping[str, Any]:
        nutzenergie: dict[Energieart, Lastgang] = ctx.get("speicher.nutzenergie")
        endenergie: dict[Energietraeger, Lastgang] = {}
        auslegungen: list[Erzeugerauslegung] = []
        kostenansatz_eur_a = 0.0

        for energieart, lastgang in nutzenergie.items():
            park = ctx.variante.erzeugerpark.fuer(energieart)
            if not park:
                ctx.notiere(
                    f"Kein Erzeuger für {energieart.value} hinterlegt – "
                    "Bedarf bleibt unversorgt."
                )
                continue

            rest = lastgang
            gesamt_kwh = lastgang.summe_kwh()

            for i, erzeuger in enumerate(park):
                letzter = i == len(park) - 1
                nennleistung = _nennleistung(erzeuger, rest, letzter)
                gedeckt, rest = rest.begrenzt_auf(nennleistung)

                if erzeuger.typ == Erzeugertyp.KOSTENANSATZ:
                    betrag = (
                        gedeckt.summe_kwh() * (erzeuger.kosten_eur_kwh or 0.0)
                        + erzeuger.kosten_grundpreis_eur_a
                        + erzeuger.kosten_leistungspreis_eur_kw_a
                        * gedeckt.spitzenlast_kw()
                    )
                    kostenansatz_eur_a += betrag
                    auslegungen.append(
                        _auslegung(erzeuger, gedeckt, gesamt_kwh, nennleistung, 1.0, None)
                    )
                    continue

                traeger = erzeuger.traeger or STANDARD_TRAEGER.get(erzeuger.typ)
                if traeger is None:
                    raise ValueError(
                        f"Erzeuger {erzeuger.name!r}: Endenergieträger nicht bestimmbar"
                    )
                umrechnung = UMRECHNUNG.get(erzeuger.typ, _umrechnung_direkt)
                endlastgang, arbeitszahl = umrechnung(erzeuger, gedeckt)

                endenergie[traeger] = (
                    endlastgang if traeger not in endenergie
                    else endenergie[traeger].plus(endlastgang)
                )

                if erzeuger.hilfsstrom_anteil > 0:
                    hilfs = gedeckt.skaliert(erzeuger.hilfsstrom_anteil)
                    endenergie[Energietraeger.STROM] = (
                        hilfs
                        if Energietraeger.STROM not in endenergie
                        else endenergie[Energietraeger.STROM].plus(hilfs)
                    )

                auslegungen.append(
                    _auslegung(
                        erzeuger, gedeckt, gesamt_kwh, nennleistung, arbeitszahl, traeger
                    )
                )

            if rest.summe_kwh() > 1.0:
                ctx.notiere(
                    f"{energieart.value}: {rest.summe_kwh():,.0f} kWh bleiben ungedeckt "
                    f"(Spitze {rest.spitzenlast_kw():,.1f} kW). Erzeugerleistung prüfen."
                )

        return {
            "erzeuger.endenergie": endenergie,
            "erzeuger.auslegung": auslegungen,
            "erzeuger.kostenansatz_eur_a": kostenansatz_eur_a,
        }


# --------------------------------------------------------------- Umrechnungen


def _umrechnung_waermepumpe(erzeuger: Erzeuger, nutz: Lastgang) -> tuple[Lastgang, float]:
    """Strombedarf einer Wärmepumpe/Kältemaschine über JAZ oder Carnot-Gütegrad."""
    if erzeuger.jaz:
        return nutz.skaliert(1.0 / erzeuger.jaz), erzeuger.jaz
    if erzeuger.carnot_guetegrad:
        t_vl = erzeuger.vorlauftemperatur_c + 273.15
        t_q = erzeuger.quellentemperatur_c + 273.15
        if t_vl <= t_q:
            raise ValueError(f"{erzeuger.name}: Vorlauf <= Quelle, COP nicht bestimmbar")
        cop = erzeuger.carnot_guetegrad * t_vl / (t_vl - t_q)
        return nutz.skaliert(1.0 / cop), cop
    raise ValueError(f"{erzeuger.name}: weder jaz noch carnot_guetegrad gesetzt")


def _umrechnung_kaeltemaschine(erzeuger: Erzeuger, nutz: Lastgang) -> tuple[Lastgang, float]:
    if erzeuger.jaz:
        return nutz.skaliert(1.0 / erzeuger.jaz), erzeuger.jaz
    if erzeuger.carnot_guetegrad:
        t_kalt = erzeuger.vorlauftemperatur_c + 273.15
        t_warm = erzeuger.quellentemperatur_c + 273.15
        if t_warm <= t_kalt:
            raise ValueError(f"{erzeuger.name}: Rückkühl- <= Kaltwassertemperatur")
        eer = erzeuger.carnot_guetegrad * t_kalt / (t_warm - t_kalt)
        return nutz.skaliert(1.0 / eer), eer
    raise ValueError(f"{erzeuger.name}: weder jaz (SEER) noch carnot_guetegrad gesetzt")


def _umrechnung_kessel(erzeuger: Erzeuger, nutz: Lastgang) -> tuple[Lastgang, float]:
    wirkungsgrad = erzeuger.nutzungsgrad or 0.92
    return nutz.skaliert(1.0 / wirkungsgrad), wirkungsgrad


def _umrechnung_netz(erzeuger: Erzeuger, nutz: Lastgang) -> tuple[Lastgang, float]:
    faktor = 1.0 / (1.0 - erzeuger.netzverlust)
    return nutz.skaliert(faktor), 1.0 / faktor


def _umrechnung_direkt(erzeuger: Erzeuger, nutz: Lastgang) -> tuple[Lastgang, float]:
    return nutz, 1.0


#: Erweiterungspunkt für eigene Erzeugertypen
UMRECHNUNG: dict[str, Callable[[Erzeuger, Lastgang], tuple[Lastgang, float]]] = {
    Erzeugertyp.WAERMEPUMPE: _umrechnung_waermepumpe,
    Erzeugertyp.KAELTEMASCHINE: _umrechnung_kaeltemaschine,
    Erzeugertyp.FREIE_KUEHLUNG: _umrechnung_kaeltemaschine,
    Erzeugertyp.KESSEL: _umrechnung_kessel,
    Erzeugertyp.BHKW: _umrechnung_kessel,
    Erzeugertyp.FERNWAERME: _umrechnung_netz,
    Erzeugertyp.FERNKAELTE: _umrechnung_netz,
    Erzeugertyp.DIREKTSTROM: _umrechnung_direkt,
}


def _nennleistung(erzeuger: Erzeuger, rest: Lastgang, letzter: bool) -> float:
    if erzeuger.nennleistung_kw:
        return erzeuger.nennleistung_kw
    if letzter:
        return rest.spitzenlast_kw() * erzeuger.auslegungsfaktor
    return rest.spitzenlast_kw() * erzeuger.auslegungsfaktor


def _auslegung(
    erzeuger: Erzeuger,
    gedeckt: Lastgang,
    gesamt_kwh: float,
    nennleistung: float,
    arbeitszahl: float,
    traeger: Energietraeger | None,
) -> Erzeugerauslegung:
    deckung = gedeckt.summe_kwh()
    endenergie = deckung / arbeitszahl if arbeitszahl > 0 else 0.0
    return Erzeugerauslegung(
        name=erzeuger.name,
        typ=erzeuger.typ,
        energieart=erzeuger.energieart,
        nennleistung_kw=nennleistung,
        deckung_kwh=deckung,
        deckungsanteil=deckung / gesamt_kwh if gesamt_kwh > 0 else 0.0,
        endenergie_kwh=endenergie,
        arbeitszahl=arbeitszahl,
        traeger=traeger,
        volllaststunden_h=deckung / nennleistung if nennleistung > 0 else 0.0,
    )
