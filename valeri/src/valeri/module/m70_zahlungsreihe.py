"""M70 – Zahlungsreihe über den Betrachtungszeitraum (vor Steuern).

Erzeugt Jahr 0 bis T mit
  * Erst- und Ersatzinvestitionen (technische Nutzungsdauer, preisgesteigert)
  * Restwert am Ende des Betrachtungszeitraums (linear)
  * Energie-, Wartungs-, Instandsetzungs-, Bedien- und sonstigen Kosten
    mit kostenartenspezifischen Preisänderungsraten
  * Erlösen und nicht-energetischen Nutzen (DIN EN 17463)
  * Abschreibung und – optional – explizitem Fremdkapitaldienst

Vorzeichen: Auszahlungen negativ, Einzahlungen positiv.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from valeri.core.finanzmathematik import annuitaetendarlehen
from valeri.core.kontext import Rechenkontext
from valeri.core.modul import Rechenmodul
from valeri.core.registry import registriere
from valeri.modelle.energie import Erloes
from valeri.modelle.ergebnis import Jahreszahlung, Zahlungsreihe
from valeri.modelle.investition import Positionsdaten


@registriere()
class Zahlungsreihenmodul(Rechenmodul):
    id = "m70_zahlungsreihe"
    titel = "Zahlungsreihe vor Steuern"
    grundlage = "DIN EN 17463 (Zahlungsstromermittlung), VDI 2067 (Ersatz/Restwert)"
    benoetigt = (
        "zeitraum.jahre",
        "invest.positionen",
        "energie.traegerkosten",
        "energie.kosten_eur_a",
        "energie.co2_kosten_eur_a",
        "erzeuger.kostenansatz_eur_a",
        "betrieb.instandsetzung_eur_a",
        "betrieb.wartung_eur_a",
        "betrieb.bedienung_eur_a",
        "betrieb.sonstige_eur_a",
    )
    liefert = ("zahlung.vor_steuern", "zahlung.investitionsplan")

    def berechne(self, ctx: Rechenkontext) -> Mapping[str, Any]:
        jahre: int = ctx.get("zeitraum.jahre")
        fr = ctx.projekt.finanzrahmen
        pa = fr.preisaenderung
        reihe = Zahlungsreihe([Jahreszahlung(jahr=j) for j in range(jahre + 1)])

        investitionsplan = self._investitionen(ctx, reihe, jahre)
        self._betriebszahlungen(ctx, reihe, jahre)
        self._erloese(ctx, reihe, jahre)
        self._abschreibung(reihe, investitionsplan, jahre)
        if fr.finanzierung_explizit:
            self._finanzierung(ctx, reihe, jahre)

        return {"zahlung.vor_steuern": reihe, "zahlung.investitionsplan": investitionsplan}

    # -------------------------------------------------------------- Investition

    def _investitionen(
        self, ctx: Rechenkontext, reihe: Zahlungsreihe, jahre: int
    ) -> list[dict[str, Any]]:
        """Erst- und Ersatzinvestitionen einplanen, Restwert am Ende gutschreiben."""
        pa = ctx.projekt.finanzrahmen.preisaenderung
        positionen: list[Positionsdaten] = ctx.get("invest.positionen")
        plan: list[dict[str, Any]] = []

        for daten in positionen:
            position = daten.position
            nd = daten.nutzungsdauer_a
            start = position.investitionsjahr
            if start > jahre:
                continue

            zeitpunkte = [start]
            if position.ersatzinvestition and nd > 0:
                k = 1
                while start + k * nd < jahre:
                    zeitpunkte.append(int(round(start + k * nd)))
                    k += 1

            for zeitpunkt in zeitpunkte:
                faktor = (1.0 + pa.investition) ** zeitpunkt
                betrag = daten.investition_eur * faktor
                foerderung = daten.foerderung_eur * faktor
                reihe[zeitpunkt].investition -= betrag
                behandlung = (
                    position.foerderung.behandlung if position.foerderung else "minderung_afa"
                )
                if foerderung:
                    if behandlung == "ertrag_sofort":
                        reihe[zeitpunkt].erloese += foerderung
                    else:
                        reihe[zeitpunkt].foerderung += foerderung
                plan.append(
                    {
                        "bezeichnung": position.bezeichnung,
                        "jahr": zeitpunkt,
                        "investition_eur": betrag,
                        "foerderung_eur": foerderung,
                        "afa_basis_eur": max(
                            0.0,
                            betrag - (foerderung if behandlung == "minderung_afa" else 0.0),
                        ),
                        "afa_dauer_a": daten.afa_dauer_a,
                        "nutzungsdauer_a": nd,
                        "ersatz": zeitpunkt != start,
                    }
                )

            # Restwert der zuletzt getätigten Investition
            if position.restwert and nd > 0:
                letzte = zeitpunkte[-1]
                restnutzungsdauer = nd - (jahre - letzte)
                if restnutzungsdauer > 0:
                    betrag = daten.investition_eur * (1.0 + pa.investition) ** letzte
                    reihe[jahre].restwert += betrag * restnutzungsdauer / nd

        return plan

    # ------------------------------------------------------------ Betriebsjahre

    def _betriebszahlungen(
        self, ctx: Rechenkontext, reihe: Zahlungsreihe, jahre: int
    ) -> None:
        pa = ctx.projekt.finanzrahmen.preisaenderung
        traegerkosten = ctx.get("energie.traegerkosten")
        kostenansatz = ctx.get("erzeuger.kostenansatz_eur_a")
        co2 = ctx.get("energie.co2_kosten_eur_a")
        wartung_instand = ctx.get("betrieb.wartung_eur_a") + ctx.get(
            "betrieb.instandsetzung_eur_a"
        )
        bedienung = ctx.get("betrieb.bedienung_eur_a")
        sonstige = ctx.get("betrieb.sonstige_eur_a")

        for jahr in range(1, jahre + 1):
            zahlung = reihe[jahr]
            for posten in traegerkosten:
                zahlung.energiekosten -= posten.summe_eur_a * (
                    1.0 + posten.preisaenderung
                ) ** (jahr - 1)
            zahlung.energiekosten -= kostenansatz * (1.0 + pa.allgemein) ** (jahr - 1)
            zahlung.co2_kosten -= co2 * (1.0 + pa.co2_preis) ** (jahr - 1)
            zahlung.wartung_instandsetzung -= wartung_instand * (
                1.0 + pa.wartung_instandsetzung
            ) ** (jahr - 1)
            zahlung.bedienung -= bedienung * (1.0 + pa.personal) ** (jahr - 1)
            zahlung.sonstige_kosten -= sonstige * (1.0 + pa.sonstige) ** (jahr - 1)

    def _erloese(self, ctx: Rechenkontext, reihe: Zahlungsreihe, jahre: int) -> None:
        pa = ctx.projekt.finanzrahmen.preisaenderung

        def eintragen(posten: list[Erloes], feld: str) -> None:
            for erloes in posten:
                rate = pa.fuer(erloes.preisaenderung_art)
                bis = erloes.bis_jahr or jahre
                for jahr in range(max(1, erloes.ab_jahr), min(jahre, bis) + 1):
                    wert = erloes.betrag() * (1.0 + rate) ** (jahr - 1)
                    setattr(reihe[jahr], feld, getattr(reihe[jahr], feld) + wert)

        eintragen(ctx.variante.erloese, "erloese")
        eintragen(ctx.variante.weitere_nutzen, "weitere_nutzen")

    # ------------------------------------------------------- AfA & Finanzierung

    def _abschreibung(
        self, reihe: Zahlungsreihe, plan: list[dict[str, Any]], jahre: int
    ) -> None:
        """Lineare AfA ab dem Jahr nach der Investition (vereinfachend ganzjährig)."""
        for eintrag in plan:
            dauer = max(1, int(round(eintrag["afa_dauer_a"])))
            jahresbetrag = eintrag["afa_basis_eur"] / dauer
            start = eintrag["jahr"] + 1
            for jahr in range(start, min(start + dauer, jahre + 1)):
                reihe[jahr].abschreibung -= jahresbetrag

    def _finanzierung(self, ctx: Rechenkontext, reihe: Zahlungsreihe, jahre: int) -> None:
        fr = ctx.projekt.finanzrahmen
        eigenmittel_frei = 1.0 - fr.eigenkapitalquote
        darlehen = -(reihe[0].investition + reihe[0].foerderung) * eigenmittel_frei
        if darlehen <= 0:
            return
        reihe[0].fk_auszahlung += darlehen
        plan = annuitaetendarlehen(
            darlehen, fr.fremdkapitalzins, fr.fremdkapital_laufzeit_a, jahre
        )
        for jahr, (zins, tilgung, _rest) in enumerate(plan, start=1):
            reihe[jahr].fk_zins -= zins
            reihe[jahr].fk_tilgung -= tilgung
        restschuld = plan[-1][2] if plan else 0.0
        if restschuld > 1e-6:
            reihe[jahre].fk_tilgung -= restschuld
            ctx.notiere(
                f"Restschuld von {restschuld:,.0f} EUR am Ende des "
                "Betrachtungszeitraums als Tilgung angesetzt."
            )
