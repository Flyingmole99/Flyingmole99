"""M10 – Stammdaten und Plausibilitätsprüfung der Basisvariante."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from valeri.core.kontext import Rechenkontext
from valeri.core.modul import Rechenmodul
from valeri.core.registry import registriere


@registriere()
class Stammdaten(Rechenmodul):
    id = "m10_stammdaten"
    titel = "Stammdaten und Betrachtungszeitraum"
    grundlage = "DIN EN 17463, Abschnitt Eingangsgrößen"
    liefert = ("zeitraum.jahre", "zeitraum.basisjahr", "stammdaten.pruefung")

    def berechne(self, ctx: Rechenkontext) -> Mapping[str, Any]:
        fr = ctx.projekt.finanzrahmen
        pruefung: list[str] = []

        if not ctx.projekt.bedarf and not ctx.variante.bedarf_ueberschreibung:
            pruefung.append("Kein Energiebedarf hinterlegt.")
        if not ctx.variante.investition.positionen:
            pruefung.append("Keine Investitionspositionen hinterlegt.")

        # Betrachtungszeitraum gegen die längste Nutzungsdauer spiegeln
        if fr.betrachtungszeitraum_a < 10:
            pruefung.append(
                f"Betrachtungszeitraum {fr.betrachtungszeitraum_a} a ist kurz; "
                "DIN EN 17463 stellt auf die Nutzungsdauer der Investition ab."
            )
        if fr.fremdkapital_laufzeit_a > fr.betrachtungszeitraum_a:
            pruefung.append(
                "Fremdkapitallaufzeit ist länger als der Betrachtungszeitraum – "
                "Restschuld am Ende beachten."
            )
        for hinweis in pruefung:
            ctx.notiere(hinweis)

        return {
            "zeitraum.jahre": fr.betrachtungszeitraum_a,
            "zeitraum.basisjahr": fr.basisjahr,
            "stammdaten.pruefung": pruefung,
        }
