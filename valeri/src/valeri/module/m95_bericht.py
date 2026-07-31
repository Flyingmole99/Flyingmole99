"""M95 – Textbericht einer Variante.

Der Bericht enthält bewusst auch Herkunft und Prüfstand der Kennwerte:
DIN EN 17463 verlangt, dass Eingangsgrößen, Annahmen und Rechenweg
nachvollziehbar dokumentiert sind.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from valeri.core.kontext import Rechenkontext
from valeri.core.modul import Rechenmodul
from valeri.core.registry import registriere


def _de(wert: float, nachkomma: int = 0, breite: int = 0) -> str:
    """Zahl in deutscher Schreibweise (Tausenderpunkt, Dezimalkomma)."""
    text = f"{wert:,.{nachkomma}f}"
    text = text.replace(",", "\x00").replace(".", ",").replace("\x00", ".")
    return f"{text:>{breite}}" if breite else text


def _eur(wert: float) -> str:
    return f"{_de(wert, 0, 14)} EUR"


@registriere()
class Bericht(Rechenmodul):
    id = "m95_bericht"
    titel = "Ergebnisbericht"
    grundlage = "DIN EN 17463 (Dokumentationsanforderungen)"
    benoetigt = ("ergebnis.kennzahlen", "ergebnis.valeri", "ergebnis.vdi2067")
    liefert = ("ergebnis.bericht",)

    def berechne(self, ctx: Rechenkontext) -> Mapping[str, Any]:
        kennzahlen = ctx.get("ergebnis.kennzahlen")
        valeri = ctx.get("ergebnis.valeri")
        vdi = ctx.get("ergebnis.vdi2067")
        zeilen: list[str] = []

        zeilen.append(f"Projekt : {ctx.projekt.name}")
        zeilen.append(f"Variante: {ctx.variante.name}")
        if ctx.variante.beschreibung:
            zeilen.append(f"          {ctx.variante.beschreibung}")
        zeilen.append("")

        zeilen.append("Randdaten")
        herleitung = ctx.get_oder("finanz.herleitung", {})
        zeilen.append(f"  Betrachtungszeitraum      {ctx.get('zeitraum.jahre')} a")
        zeilen.append(f"  Steuersatz                {herleitung.get('steuersatz', 0):.2%}")
        zeilen.append(
            f"  Eigenkapital              {herleitung.get('eigenkapitalquote', 0):.0%} "
            f"zu {herleitung.get('eigenkapitalrendite', 0):.2%}"
        )
        zeilen.append(f"  Fremdkapitalzins          {herleitung.get('fremdkapitalzins', 0):.2%}")
        zeilen.append(f"  Diskontierungssatz        {valeri['diskontierungssatz']:.2%}"
                      f"  ({valeri['sicht']})")
        zeilen.append("")

        zeilen.append("Energie")
        for art, menge in ctx.get_oder("bedarf.jahresarbeit_kwh", {}).items():
            spitze = ctx.get_oder("bedarf.spitzenlast_kw", {}).get(art, 0.0)
            zeilen.append(
                f"  Nutzenergie {art.value:<8} {_de(menge, 0, 12)} kWh/a   "
                f"Spitze {_de(spitze, 1, 8)} kW"
            )
        for ergebnis in ctx.get_oder("speicher.ergebnisse", []):
            zeilen.append(
                f"  Speicher {ergebnis.name:<14} Spitze {_de(ergebnis.spitze_vorher_kw, 1)}"
                f" -> {_de(ergebnis.spitze_nachher_kw, 1)} kW "
                f"({ergebnis.kappung_anteil:.1%}), "
                f"{_de(ergebnis.vollzyklen)} Vollzyklen/a"
            )
        for auslegung in ctx.get_oder("erzeuger.auslegung", []):
            zeilen.append(
                f"  Erzeuger {auslegung.name:<14} {_de(auslegung.nennleistung_kw, 1, 8)} kW, "
                f"Deckung {auslegung.deckungsanteil:>4.0%}, "
                f"AZ {_de(auslegung.arbeitszahl, 2)}, "
                f"{_de(auslegung.volllaststunden_h, 0, 6)} h/a"
            )
        zeilen.append(f"  Energiekosten Jahr 1      {_eur(ctx.get('energie.kosten_eur_a'))}/a")
        zeilen.append("")

        zeilen.append("Kosten")
        zeilen.append(f"  Investition (Jahr 0)      {_eur(ctx.get('invest.summe_eur'))}")
        zeilen.append(f"  davon Förderung           {_eur(ctx.get('invest.foerderung_eur'))}")
        zeilen.append(
            f"  Wartung/Instandsetzung    "
            f"{_eur(ctx.get('betrieb.wartung_eur_a') + ctx.get('betrieb.instandsetzung_eur_a'))}/a"
        )
        zeilen.append(f"  Bedienung                 {_eur(ctx.get('betrieb.bedienung_eur_a'))}/a")
        zeilen.append(f"  Sonstige                  {_eur(ctx.get('betrieb.sonstige_eur_a'))}/a")
        zeilen.append("")

        zeilen.append("Ergebnis DIN EN 17463 (VALERI)")
        zeilen.append(f"  Kapitalwert               {_eur(kennzahlen.kapitalwert_eur)}")
        if kennzahlen.interner_zinsfuss is not None:
            zeilen.append(f"  Interner Zinsfuß          {kennzahlen.interner_zinsfuss:.2%}")
        if kennzahlen.amortisation_dynamisch_a is not None:
            zeilen.append(
                f"  Amortisation (dynamisch)  {kennzahlen.amortisation_dynamisch_a:.1f} a"
            )
        zeilen.append("")

        zeilen.append("Ergebnis VDI 2067 (vor Steuern)")
        zeilen.append(f"  A_N,K kapitalgebunden     {_eur(-vdi['a_nk_kapitalgebunden_eur_a'])}/a")
        zeilen.append(f"  A_N,V bedarfsgebunden     {_eur(-vdi['a_nv_bedarfsgebunden_eur_a'])}/a")
        zeilen.append(f"  A_N,B betriebsgebunden    {_eur(-vdi['a_nb_betriebsgebunden_eur_a'])}/a")
        zeilen.append(f"  A_N,S sonstige            {_eur(-vdi['a_ns_sonstige_eur_a'])}/a")
        zeilen.append(f"  A_N,E Erlöse              {_eur(vdi['a_ne_erloese_eur_a'])}/a")
        zeilen.append(f"  Annuität                  {_eur(vdi['annuitaet_eur_a'])}/a")
        if kennzahlen.waermegestehungskosten_eur_kwh:
            zeilen.append(
                f"  Wärmegestehungskosten     "
                f"{kennzahlen.waermegestehungskosten_eur_kwh * 100:.2f} ct/kWh"
            )
        if kennzahlen.kaeltegestehungskosten_eur_kwh:
            zeilen.append(
                f"  Kältegestehungskosten     "
                f"{kennzahlen.kaeltegestehungskosten_eur_kwh * 100:.2f} ct/kWh"
            )
        zeilen.append("")

        if ctx.hinweise:
            zeilen.append("Hinweise")
            zeilen.extend(f"  - {h}" for h in ctx.hinweise)

        return {"ergebnis.bericht": "\n".join(zeilen)}
