"""M60 – Investitionskosten zusammenstellen.

Erzeugt die Positionsliste inklusive einer eigenen Position für
Baunebenkosten/Planung, damit auch diese eine Nutzungsdauer und eine AfA
erhalten und nicht stillschweigend im Anlagenpreis verschwinden.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from valeri.core.kontext import Rechenkontext
from valeri.core.modul import Rechenmodul
from valeri.core.registry import registriere
from valeri.modelle.investition import Investitionsposition


@registriere()
class Investitionskosten(Rechenmodul):
    id = "m60_investition"
    titel = "Investitionskosten"
    grundlage = "Projektangaben, Kostengruppen"
    liefert = ("invest.positionen_roh", "invest.summe_eur")

    def berechne(self, ctx: Rechenkontext) -> Mapping[str, Any]:
        investition = ctx.variante.investition
        positionen: list[Investitionsposition] = list(investition.positionen)

        basis = sum(p.investition_eur() for p in positionen)
        if investition.nebenkosten_anteil > 0 and basis > 0:
            positionen.append(
                Investitionsposition(
                    bezeichnung=investition.nebenkosten_bezeichnung,
                    kategorie=investition.nebenkosten_kategorie or "planung.honorare",
                    einzelpreis_eur=basis * investition.nebenkosten_anteil,
                    einheit="psch",
                    ersatzinvestition=False,
                    bemerkung=(
                        f"{investition.nebenkosten_anteil:.1%} der Anlagenkosten, "
                        "automatisch ergänzt"
                    ),
                )
            )

        summe = sum(p.investition_eur() for p in positionen)
        if summe <= 0:
            ctx.notiere("Investitionssumme ist 0 – reine Betriebskostenbetrachtung.")

        return {"invest.positionen_roh": positionen, "invest.summe_eur": summe}
