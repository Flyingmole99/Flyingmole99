"""M75 – Ertragsteuerwirkung.

Bemessungsgrundlage je Jahr = zahlungswirksames Betriebsergebnis
+ Abschreibung + Fremdkapitalzinsen. Die Investitionsauszahlung selbst wirkt
ausschließlich über die AfA.

Zwei Betriebsarten:
  verlustvortrag = False  negative Bemessungsgrundlagen führen sofort zu einer
                          Steuerminderung (Verrechnung mit übrigen Erträgen des
                          Unternehmens) – Regelfall bei Vollkostenvergleichen
  verlustvortrag = True   Verluste werden vorgetragen und erst mit späteren
                          positiven Bemessungsgrundlagen verrechnet

Vereinfachung (bewusst und dokumentiert): Der Restwert am Ende des
Betrachtungszeitraums wird als Buchwertabgang behandelt und nicht besteuert.
Weicht die steuerliche von der technischen Nutzungsdauer stark ab, ist der
Effekt gesondert zu würdigen.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from valeri.core.kontext import Rechenkontext
from valeri.core.modul import Rechenmodul
from valeri.core.registry import registriere
from valeri.modelle.ergebnis import Zahlungsreihe


@registriere()
class Steuern(Rechenmodul):
    id = "m75_steuern"
    titel = "Ertragsteuern"
    grundlage = "KSt + SolZ + GewSt bzw. manueller Satz"
    benoetigt = ("zahlung.vor_steuern", "finanz.steuersatz")
    liefert = ("zahlung.nach_steuern", "steuer.uebersicht")

    def berechne(self, ctx: Rechenkontext) -> Mapping[str, Any]:
        reihe: Zahlungsreihe = ctx.get("zahlung.vor_steuern")
        satz: float = ctx.get("finanz.steuersatz")
        parameter = ctx.projekt.finanzrahmen.steuern

        vortrag = 0.0
        uebersicht: list[dict[str, float]] = []

        for zahlung in reihe.jahre:
            bemessung = zahlung.steuerbemessung
            if parameter.zins_hinzurechnung and zahlung.fk_zins < 0:
                zinsen = -zahlung.fk_zins
                hinzurechnung = max(0.0, zinsen - parameter.hinzurechnung_freibetrag_eur) * 0.25
                # nur der gewerbesteuerliche Teil des Mischsatzes ist betroffen
                gewst_satz = (
                    parameter.gewerbesteuer_messzahl * parameter.gewerbesteuer_hebesatz
                )
                bemessung += hinzurechnung * (gewst_satz / satz if satz > 0 else 0.0)

            if parameter.verlustvortrag:
                bemessung += vortrag
                if bemessung < 0:
                    vortrag = bemessung
                    bemessung = 0.0
                else:
                    vortrag = 0.0

            zahlung.steuer = -satz * bemessung
            uebersicht.append(
                {
                    "jahr": zahlung.jahr,
                    "bemessungsgrundlage_eur": bemessung,
                    "steuer_eur": zahlung.steuer,
                    "verlustvortrag_eur": vortrag,
                }
            )

        if parameter.verlustvortrag and vortrag < 0:
            ctx.notiere(
                f"Verlustvortrag von {-vortrag:,.0f} EUR verfällt am Ende des "
                "Betrachtungszeitraums."
            )
        if satz == 0:
            ctx.notiere("Steuersatz 0 – Ergebnis entspricht der Vorsteuerbetrachtung.")

        return {"zahlung.nach_steuern": reihe, "steuer.uebersicht": uebersicht}
