"""M80 – Kapitalwert nach DIN EN 17463 (VALERI).

Kapitalwert = Summe der auf den Bewertungsstichtag diskontierten
Netto-Zahlungsströme nach Steuern über den Betrachtungszeitraum.

Diskontierungssatz und bewertete Zahlungsreihe müssen zueinander passen:
  * ohne explizite Finanzierung -> Gesamtkapital-Cashflow, WACC nach Steuern
  * mit expliziter Finanzierung -> Eigenkapital-Cashflow (Zins und Tilgung
    bereits enthalten), Eigenkapitalrendite als Diskontierungssatz
Das Modul dokumentiert, welche der beiden Sichten gerechnet wurde.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from valeri.core.finanzmathematik import barwert
from valeri.core.kontext import Rechenkontext
from valeri.core.modul import Rechenmodul
from valeri.core.registry import registriere
from valeri.modelle.ergebnis import Zahlungsreihe


@registriere()
class ValeriKapitalwert(Rechenmodul):
    id = "m80_valeri"
    titel = "Kapitalwert nach DIN EN 17463 (VALERI)"
    grundlage = "DIN EN 17463 – Bewertung energiebezogener Investitionen"
    benoetigt = ("zahlung.nach_steuern", "finanz.kalkulationszins", "zeitraum.jahre")
    liefert = (
        "ergebnis.kapitalwert_eur",
        "ergebnis.cashflows",
        "ergebnis.diskontierungssatz",
        "ergebnis.valeri",
    )

    def berechne(self, ctx: Rechenkontext) -> Mapping[str, Any]:
        reihe: Zahlungsreihe = ctx.get("zahlung.nach_steuern")
        fr = ctx.projekt.finanzrahmen

        if fr.finanzierung_explizit:
            sicht = "eigenkapital"
            cashflows = reihe.reihe("cashflow_eigenkapital")
            zins = fr.eigenkapitalrendite
        else:
            sicht = "gesamtkapital"
            cashflows = reihe.reihe("cashflow_nach_steuern")
            zins = ctx.get("finanz.kalkulationszins")

        kapitalwert = barwert(cashflows, zins)

        valeri = {
            "norm": "DIN EN 17463 (VALERI)",
            "sicht": sicht,
            "diskontierungssatz": zins,
            "betrachtungszeitraum_a": ctx.get("zeitraum.jahre"),
            "kapitalwert_eur": kapitalwert,
            "barwert_investitionen_eur": barwert(reihe.reihe("investition"), zins),
            "barwert_foerderung_eur": barwert(reihe.reihe("foerderung"), zins),
            "barwert_energiekosten_eur": barwert(reihe.reihe("energiekosten"), zins),
            "barwert_wartung_instandsetzung_eur": barwert(
                reihe.reihe("wartung_instandsetzung"), zins
            ),
            "barwert_bedienung_eur": barwert(reihe.reihe("bedienung"), zins),
            "barwert_sonstige_eur": barwert(reihe.reihe("sonstige_kosten"), zins),
            "barwert_co2_eur": barwert(reihe.reihe("co2_kosten"), zins),
            "barwert_erloese_eur": barwert(reihe.reihe("erloese"), zins),
            "barwert_weitere_nutzen_eur": barwert(reihe.reihe("weitere_nutzen"), zins),
            "barwert_steuern_eur": barwert(reihe.reihe("steuer"), zins),
            "barwert_restwert_eur": barwert(reihe.reihe("restwert"), zins),
            "preisbasis": fr.preisbasis.value,
        }

        if ctx.projekt.rechenmodus.value == "vollkosten":
            ctx.notiere(
                "Vollkostenbetrachtung: Der Kapitalwert ist naturgemäß negativ; "
                "aussagekräftig ist der Vergleich mit der Referenzvariante."
            )

        return {
            "ergebnis.kapitalwert_eur": kapitalwert,
            "ergebnis.cashflows": cashflows,
            "ergebnis.diskontierungssatz": zins,
            "ergebnis.valeri": valeri,
        }
