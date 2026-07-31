"""M85 – Abgeleitete Kennzahlen.

Interner Zinsfuß, Amortisationszeiten, Kapitalwertrate und Gestehungskosten.
Kennzahlen, die einen Vergleichsfall brauchen (CO2-Vermeidungskosten,
Mehrinvestition, Einsparung), entstehen erst im Variantenvergleich.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from valeri.core.einheiten import Energieart
from valeri.core.finanzmathematik import amortisationszeit, interner_zinsfuss
from valeri.core.kontext import Rechenkontext
from valeri.core.modul import Rechenmodul
from valeri.core.registry import registriere
from valeri.modelle.ergebnis import Kennzahlen


@registriere()
class Kennzahlenmodul(Rechenmodul):
    id = "m85_kennzahlen"
    titel = "Kennzahlen"
    grundlage = "Kapitalwertrechnung, VDI 2067"
    benoetigt = (
        "ergebnis.cashflows",
        "ergebnis.kapitalwert_eur",
        "ergebnis.diskontierungssatz",
        "ergebnis.annuitaet_eur_a",
        "ergebnis.vdi2067",
        "bedarf.jahresarbeit_kwh",
        "invest.summe_eur",
        "energie.co2_t_a",
    )
    liefert = ("ergebnis.kennzahlen",)

    def berechne(self, ctx: Rechenkontext) -> Mapping[str, Any]:
        cashflows: list[float] = ctx.get("ergebnis.cashflows")
        zins: float = ctx.get("ergebnis.diskontierungssatz")
        investition: float = ctx.get("invest.summe_eur")
        jahresarbeit: dict[Energieart, float] = ctx.get("bedarf.jahresarbeit_kwh")
        vdi = ctx.get("ergebnis.vdi2067")

        kennzahlen = Kennzahlen(
            kapitalwert_eur=ctx.get("ergebnis.kapitalwert_eur"),
            kalkulationszins=zins,
            annuitaet_eur_a=ctx.get("ergebnis.annuitaet_eur_a"),
            interner_zinsfuss=interner_zinsfuss(cashflows),
            amortisation_statisch_a=amortisationszeit(cashflows, 0.0),
            amortisation_dynamisch_a=amortisationszeit(cashflows, zins),
            kapitalwertrate=(
                ctx.get("ergebnis.kapitalwert_eur") / investition if investition > 0 else None
            ),
        )

        # Gestehungskosten: Jahreskosten (VDI 2067, vor Steuern) je Nutzenergie
        jahreskosten = -vdi["jahreskosten_eur_a"]
        arten = {a: menge for a, menge in jahresarbeit.items() if menge > 0}
        if len(arten) == 1:
            art, menge = next(iter(arten.items()))
            wert = jahreskosten / menge
            if art is Energieart.WAERME:
                kennzahlen.waermegestehungskosten_eur_kwh = wert
            elif art is Energieart.KAELTE:
                kennzahlen.kaeltegestehungskosten_eur_kwh = wert
        elif len(arten) > 1:
            ctx.notiere(
                "Mehrere Nutzenergiearten in einer Variante – Gestehungskosten "
                "je Art erfordern eine Kostenaufteilung (nicht automatisch möglich)."
            )

        if kennzahlen.interner_zinsfuss is None:
            ctx.notiere(
                "Kein interner Zinsfuß bestimmbar (kein Vorzeichenwechsel der "
                "Zahlungsreihe) – bei Vollkostenbetrachtungen der Normalfall."
            )

        return {"ergebnis.kennzahlen": kennzahlen}
