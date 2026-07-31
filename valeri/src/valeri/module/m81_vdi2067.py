"""M81 – Annuitätenmethode nach VDI 2067 Blatt 1 (Gegenprobe zum Kapitalwert).

Kostengruppen:
  A_N,K  kapitalgebunden  (Investition, Ersatzbeschaffungen, Restwert)
  A_N,V  bedarfsgebunden  (Energiebezug)
  A_N,B  betriebsgebunden (Bedienen, Wartung, Instandsetzung)
  A_N,S  sonstige         (Versicherung, Verwaltung, ...)
  A_N,E  Erlöse
  A_N = A_N,E - (A_N,K + A_N,V + A_N,B + A_N,S)

Anders als die VALERI-Rechnung ist die Annuitätenmethode nach VDI 2067 eine
Betrachtung *vor* Steuern. Beide Ergebnisse stehen daher bewusst nebeneinander.
"""

from __future__ import annotations

import math
from collections.abc import Mapping
from typing import Any

from valeri.core.finanzmathematik import annuitaetsfaktor, barwertfaktor
from valeri.core.kontext import Rechenkontext
from valeri.core.modul import Rechenmodul
from valeri.core.registry import registriere
from valeri.modelle.investition import Positionsdaten


@registriere()
class Vdi2067Annuitaet(Rechenmodul):
    id = "m81_vdi2067"
    titel = "Annuität nach VDI 2067 Blatt 1"
    grundlage = "VDI 2067 Blatt 1 – Annuitätenmethode"
    benoetigt = (
        "zeitraum.jahre",
        "finanz.kalkulationszins",
        "invest.positionen",
        "energie.traegerkosten",
        "erzeuger.kostenansatz_eur_a",
        "betrieb.instandsetzung_eur_a",
        "betrieb.wartung_eur_a",
        "betrieb.bedienung_eur_a",
        "betrieb.sonstige_eur_a",
    )
    liefert = ("ergebnis.annuitaet_eur_a", "ergebnis.vdi2067")

    def berechne(self, ctx: Rechenkontext) -> Mapping[str, Any]:
        jahre: int = ctx.get("zeitraum.jahre")
        zins: float = ctx.get("finanz.kalkulationszins")
        pa = ctx.projekt.finanzrahmen.preisaenderung
        a = annuitaetsfaktor(zins, jahre)
        q = 1.0 + zins

        # --- A_N,K kapitalgebunden
        kapital_barwert = 0.0
        restwert_barwert = 0.0
        for daten in ctx.get("invest.positionen"):
            position = daten.position
            nd = daten.nutzungsdauer_a
            a0 = daten.investition_eur - daten.foerderung_eur
            r = 1.0 + pa.investition
            anzahl_ersatz = (
                max(0, math.ceil(jahre / nd) - 1)
                if (position.ersatzinvestition and nd > 0)
                else 0
            )
            barwert_position = a0
            for n in range(1, anzahl_ersatz + 1):
                barwert_position += a0 * r ** (n * nd) / q ** (n * nd)
            kapital_barwert += barwert_position

            if position.restwert and nd > 0:
                restnutzungsdauer = (anzahl_ersatz + 1) * nd - jahre
                if restnutzungsdauer > 0:
                    restwert = (
                        a0
                        * r ** (anzahl_ersatz * nd)
                        * (restnutzungsdauer / nd)
                        / q**jahre
                    )
                    restwert_barwert += restwert

        a_nk = (kapital_barwert - restwert_barwert) * a

        # --- A_N,V bedarfsgebunden
        a_nv = 0.0
        for posten in ctx.get("energie.traegerkosten"):
            a_nv += posten.summe_eur_a * a * barwertfaktor(zins, posten.preisaenderung, jahre)
        a_nv += (
            ctx.get("erzeuger.kostenansatz_eur_a")
            * a
            * barwertfaktor(zins, pa.allgemein, jahre)
        )

        # --- A_N,B betriebsgebunden
        b_wartung = barwertfaktor(zins, pa.wartung_instandsetzung, jahre)
        b_personal = barwertfaktor(zins, pa.personal, jahre)
        a_nb = (
            ctx.get("betrieb.wartung_eur_a") + ctx.get("betrieb.instandsetzung_eur_a")
        ) * a * b_wartung + ctx.get("betrieb.bedienung_eur_a") * a * b_personal

        # --- A_N,S sonstige
        a_ns = ctx.get("betrieb.sonstige_eur_a") * a * barwertfaktor(zins, pa.sonstige, jahre)

        # --- A_N,E Erlöse und weitere Nutzen
        b_erloese = barwertfaktor(zins, pa.erloese, jahre)
        a_ne = (
            sum(e.betrag() for e in ctx.variante.erloese)
            + sum(e.betrag() for e in ctx.variante.weitere_nutzen)
        ) * a * b_erloese

        annuitaet = a_ne - (a_nk + a_nv + a_nb + a_ns)

        vdi = {
            "norm": "VDI 2067 Blatt 1 (vor Steuern)",
            "annuitaetsfaktor": a,
            "kalkulationszins": zins,
            "a_nk_kapitalgebunden_eur_a": a_nk,
            "a_nv_bedarfsgebunden_eur_a": a_nv,
            "a_nb_betriebsgebunden_eur_a": a_nb,
            "a_ns_sonstige_eur_a": a_ns,
            "a_ne_erloese_eur_a": a_ne,
            "annuitaet_eur_a": annuitaet,
            "jahreskosten_eur_a": -(a_nk + a_nv + a_nb + a_ns),
        }
        return {"ergebnis.annuitaet_eur_a": annuitaet, "ergebnis.vdi2067": vdi}
