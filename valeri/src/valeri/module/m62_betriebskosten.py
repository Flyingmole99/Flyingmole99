"""M62 – Betriebsgebundene Kosten des ersten Betriebsjahres.

Wartung und Instandsetzung stammen aus den Positionskennwerten (Anteil der
Investition je Jahr), der Bedienaufwand wird über den Stundensatz bewertet.
Versicherung und Verwaltung kommen aus den Betriebsparametern.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from valeri.core.kontext import Rechenkontext
from valeri.core.modul import Rechenmodul
from valeri.core.registry import registriere
from valeri.modelle.investition import Positionsdaten


@registriere()
class Betriebskosten(Rechenmodul):
    id = "m62_betriebskosten"
    titel = "Wartung, Instandsetzung, Bedienung"
    grundlage = "VDI 2067 Blatt 1 (betriebsgebundene Kosten)"
    benoetigt = ("invest.positionen", "invest.summe_eur")
    liefert = (
        "betrieb.instandsetzung_eur_a",
        "betrieb.wartung_eur_a",
        "betrieb.bedienung_eur_a",
        "betrieb.sonstige_eur_a",
        "betrieb.aufstellung",
    )

    def berechne(self, ctx: Rechenkontext) -> Mapping[str, Any]:
        positionen: list[Positionsdaten] = ctx.get("invest.positionen")
        parameter = ctx.variante.betrieb

        instandsetzung = sum(p.instandsetzung_eur_a for p in positionen)
        wartung = sum(p.wartung_eur_a for p in positionen)
        stunden = sum(p.bedienaufwand_h_a for p in positionen)
        bedienung = stunden * parameter.stundensatz_eur_h

        investitionssumme = ctx.get("invest.summe_eur")
        sonstige = (
            parameter.sonstige_kosten_eur_a
            + parameter.verwaltung_eur_a
            + parameter.versicherung_anteil_investition * investitionssumme
        )

        aufstellung = [
            {
                "bezeichnung": p.position.bezeichnung,
                "investition_eur": p.investition_eur,
                "instandsetzung_eur_a": p.instandsetzung_eur_a,
                "wartung_eur_a": p.wartung_eur_a,
                "bedienaufwand_h_a": p.bedienaufwand_h_a,
                "nutzungsdauer_a": p.nutzungsdauer_a,
                "afa_dauer_a": p.afa_dauer_a,
                "herkunft": p.herkunft,
            }
            for p in positionen
        ]

        if instandsetzung + wartung == 0 and positionen:
            ctx.notiere(
                "Keine Wartungs-/Instandsetzungskennwerte abgeleitet – "
                "Produktkategorie zuordnen oder Werte manuell setzen."
            )

        return {
            "betrieb.instandsetzung_eur_a": instandsetzung,
            "betrieb.wartung_eur_a": wartung,
            "betrieb.bedienung_eur_a": bedienung,
            "betrieb.sonstige_eur_a": sonstige,
            "betrieb.aufstellung": aufstellung,
        }
