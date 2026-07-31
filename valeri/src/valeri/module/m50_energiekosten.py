"""M50 – Energiebezugskosten im ersten Betriebsjahr.

Je Endenergieträger: Arbeitspreis * Arbeit + Leistungspreis * Jahreshöchstlast
+ Grundpreis. Der Leistungspreis ist die Stelle, an der sich eine
Spitzenlastkappung durch Speicher unmittelbar auszahlt.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from valeri.core.einheiten import Energietraeger
from valeri.core.kontext import Rechenkontext
from valeri.core.modul import Rechenmodul
from valeri.core.registry import registriere
from valeri.core.zeitreihe import Lastgang


@dataclass
class Traegerkosten:
    traeger: Energietraeger
    arbeit_kwh: float
    spitzenlast_kw: float
    arbeitskosten_eur_a: float
    leistungskosten_eur_a: float
    grundkosten_eur_a: float
    co2_menge_t_a: float
    co2_kosten_eur_a: float
    preisaenderung: float

    @property
    def summe_eur_a(self) -> float:
        return self.arbeitskosten_eur_a + self.leistungskosten_eur_a + self.grundkosten_eur_a


@registriere()
class Energiekosten(Rechenmodul):
    id = "m50_energiekosten"
    titel = "Energiebezugskosten und CO2"
    grundlage = "Arbeits-, Leistungs- und Grundpreis je Energieträger"
    benoetigt = ("erzeuger.endenergie", "erzeuger.kostenansatz_eur_a")
    liefert = (
        "energie.traegerkosten",
        "energie.kosten_eur_a",
        "energie.co2_kosten_eur_a",
        "energie.co2_t_a",
        "energie.endenergie_kwh",
    )

    def berechne(self, ctx: Rechenkontext) -> Mapping[str, Any]:
        endenergie: dict[Energietraeger, Lastgang] = ctx.get("erzeuger.endenergie")
        preisaenderung = ctx.projekt.finanzrahmen.preisaenderung
        posten: list[Traegerkosten] = []

        for traeger, lastgang in endenergie.items():
            preis = ctx.projekt.preis_fuer(ctx.variante, traeger)
            if preis is None:
                ctx.notiere(
                    f"Kein Energiepreis für {traeger.value} hinterlegt – "
                    "Kosten werden mit 0 angesetzt."
                )
                continue
            arbeit = lastgang.summe_kwh()
            spitze = lastgang.spitzenlast_kw()
            co2_t = arbeit * preis.co2_faktor_kg_kwh / 1000.0
            posten.append(
                Traegerkosten(
                    traeger=traeger,
                    arbeit_kwh=arbeit,
                    spitzenlast_kw=spitze,
                    arbeitskosten_eur_a=arbeit * preis.arbeitspreis_eur_kwh,
                    leistungskosten_eur_a=spitze * preis.leistungspreis_eur_kw_a,
                    grundkosten_eur_a=preis.grundpreis_eur_a,
                    co2_menge_t_a=co2_t,
                    co2_kosten_eur_a=co2_t * preis.co2_preis_eur_t,
                    preisaenderung=(
                        preis.preisaenderung
                        if preis.preisaenderung is not None
                        else preisaenderung.fuer(traeger.value)
                    ),
                )
            )

        kostenansatz = ctx.get("erzeuger.kostenansatz_eur_a")
        summe = sum(p.summe_eur_a for p in posten) + kostenansatz

        return {
            "energie.traegerkosten": posten,
            "energie.kosten_eur_a": summe,
            "energie.co2_kosten_eur_a": sum(p.co2_kosten_eur_a for p in posten),
            "energie.co2_t_a": sum(p.co2_menge_t_a for p in posten),
            "energie.endenergie_kwh": sum(p.arbeit_kwh for p in posten),
        }
