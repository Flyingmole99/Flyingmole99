"""M20 – Kapitalkosten, Steuersatz und Preispfade.

Hier entsteht der Diskontierungssatz der Kapitalwertrechnung. DIN EN 17463
verlangt, dass er begründet und dokumentiert wird; deshalb liefert das Modul
neben dem Zahlenwert immer auch seine Herleitung.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from valeri.core.finanzmathematik import wacc
from valeri.core.kontext import Rechenkontext
from valeri.core.modul import Rechenmodul
from valeri.core.registry import registriere


@registriere()
class Finanzrahmenmodul(Rechenmodul):
    id = "m20_finanzrahmen"
    titel = "Kapitalkosten, Steuern, Preisentwicklung"
    grundlage = "DIN EN 17463 (Kapitalwertmethode, WACC nach Steuern)"
    liefert = (
        "finanz.steuersatz",
        "finanz.kalkulationszins",
        "finanz.wacc",
        "finanz.herleitung",
    )

    def berechne(self, ctx: Rechenkontext) -> Mapping[str, Any]:
        fr = ctx.projekt.finanzrahmen
        steuersatz = fr.steuersatz()
        kapitalkosten = wacc(
            fr.eigenkapitalquote,
            fr.eigenkapitalrendite,
            fr.fremdkapitalzins,
            steuersatz,
        )
        zins = fr.kalkulationszins()

        herleitung = {
            "steuersatz_modus": fr.steuern.modus,
            "steuersatz": steuersatz,
            "eigenkapitalquote": fr.eigenkapitalquote,
            "eigenkapitalrendite": fr.eigenkapitalrendite,
            "fremdkapitalzins": fr.fremdkapitalzins,
            "fremdkapitalzins_nach_steuern": fr.fremdkapitalzins * (1 - steuersatz),
            "wacc_nach_steuern": kapitalkosten,
            "kalkulationszins_modus": fr.kalkulationszins_modus,
            "kalkulationszins": zins,
            "preisbasis": fr.preisbasis.value,
            "formel": "WACC = q_EK*r_EK + (1-q_EK)*r_FK*(1-s)",
        }

        if fr.steuern.steuerneutral:
            ctx.notiere("Steuerneutrale Betrachtung – keine Ertragsteuerwirkung.")
        if fr.eigenkapitalquote == 1.0 and fr.fremdkapitalzins > 0:
            ctx.notiere("100 % Eigenkapital: Fremdkapitalzins ohne Wirkung.")
        if zins <= 0:
            ctx.notiere(
                "Kalkulationszins <= 0 – Ergebnis reagiert extrem empfindlich, "
                "Sensitivitätsrechnung erforderlich."
            )

        return {
            "finanz.steuersatz": steuersatz,
            "finanz.kalkulationszins": zins,
            "finanz.wacc": kapitalkosten,
            "finanz.herleitung": herleitung,
        }
