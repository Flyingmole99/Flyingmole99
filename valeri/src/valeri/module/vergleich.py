"""Variantenvergleich und Sensitivität – arbeiten über mehrere Rechenkontexte.

Bewusst keine Pipeline-Module: sie brauchen die Ergebnisse *aller* Varianten
und stehen damit eine Ebene über der Einzelberechnung.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable

from valeri.core.finanzmathematik import (
    amortisationszeit,
    annuitaetsfaktor,
    barwert,
    interner_zinsfuss,
)
from valeri.core.kontext import Rechenkontext
from valeri.core.pipeline import berechne_projekt
from valeri.modelle.projekt import Projekt


def _de(wert: float, nachkomma: int = 0) -> str:
    """Zahl in deutscher Schreibweise."""
    text = f"{wert:,.{nachkomma}f}"
    return text.replace(",", "\x00").replace(".", ",").replace("\x00", ".")


@dataclass
class Vergleichszeile:
    variante: str
    kapitalwert_eur: float
    annuitaet_eur_a: float
    investition_eur: float
    energiekosten_eur_a: float
    co2_t_a: float
    ist_referenz: bool = False

    # Differenzgrößen gegenüber der Referenz
    mehrinvestition_eur: float | None = None
    kapitalwertvorteil_eur: float | None = None
    jaehrliche_einsparung_eur: float | None = None
    interner_zinsfuss: float | None = None
    amortisation_dynamisch_a: float | None = None
    co2_einsparung_t_a: float | None = None
    co2_vermeidungskosten_eur_t: float | None = None


@dataclass
class Vergleich:
    zeilen: list[Vergleichszeile] = field(default_factory=list)
    referenz: str | None = None
    hinweise: list[str] = field(default_factory=list)

    def bestes(self) -> Vergleichszeile | None:
        return max(self.zeilen, key=lambda z: z.kapitalwert_eur, default=None)

    def als_text(self) -> str:
        kopf = (
            f"{'Variante':<24}{'Kapitalwert':>16}{'Annuität/a':>14}"
            f"{'Investition':>14}{'Δ Kapitalwert':>16}{'IRR':>8}{'Amort.':>8}"
        )
        zeilen = [kopf, "-" * len(kopf)]
        for z in sorted(self.zeilen, key=lambda z: -z.kapitalwert_eur):
            irr = f"{z.interner_zinsfuss:.1%}" if z.interner_zinsfuss is not None else "-"
            amort = (
                f"{z.amortisation_dynamisch_a:.1f} a"
                if z.amortisation_dynamisch_a is not None
                else "-"
            )
            delta = (
                _de(z.kapitalwertvorteil_eur)
                if z.kapitalwertvorteil_eur is not None
                else "-"
            )
            marke = " (Ref)" if z.ist_referenz else ""
            zeilen.append(
                f"{z.variante + marke:<24}{_de(z.kapitalwert_eur):>16}"
                f"{_de(z.annuitaet_eur_a):>14}{_de(z.investition_eur):>14}"
                f"{delta:>16}{irr:>8}{amort:>8}"
            )
        if self.hinweise:
            zeilen.append("")
            zeilen.extend(f"- {h}" for h in self.hinweise)
        return "\n".join(zeilen)


def vergleiche(
    projekt: Projekt, ergebnisse: dict[str, Rechenkontext]
) -> Vergleich:
    """Stellt die Varianten gegenüber und bildet Differenzgrößen zur Referenz."""
    referenz = projekt.referenzvariante()
    referenzname = referenz.name if referenz else None
    vergleich = Vergleich(referenz=referenzname)

    zeilen: dict[str, Vergleichszeile] = {}
    for name, ctx in ergebnisse.items():
        kennzahlen = ctx.get("ergebnis.kennzahlen")
        zeilen[name] = Vergleichszeile(
            variante=name,
            kapitalwert_eur=kennzahlen.kapitalwert_eur,
            annuitaet_eur_a=kennzahlen.annuitaet_eur_a,
            investition_eur=ctx.get("invest.summe_eur"),
            energiekosten_eur_a=ctx.get("energie.kosten_eur_a"),
            co2_t_a=ctx.get("energie.co2_t_a"),
            ist_referenz=name == referenzname,
        )

    if referenzname is None:
        vergleich.hinweise.append(
            "Keine Referenzvariante gesetzt – es werden nur absolute Werte gezeigt. "
            "Für Maßnahmenbewertung nach DIN EN 17463 eine Variante mit "
            "ist_referenz: true kennzeichnen."
        )
        vergleich.zeilen = list(zeilen.values())
        return vergleich

    ref_ctx = ergebnisse[referenzname]
    ref_zeile = zeilen[referenzname]
    zins = ref_ctx.get("ergebnis.diskontierungssatz")
    ref_cashflows = ref_ctx.get("ergebnis.cashflows")

    for name, zeile in zeilen.items():
        if name == referenzname:
            vergleich.zeilen.append(zeile)
            continue
        ctx = ergebnisse[name]
        differenz = [
            a - b for a, b in zip(ctx.get("ergebnis.cashflows"), ref_cashflows)
        ]
        zeile.mehrinvestition_eur = zeile.investition_eur - ref_zeile.investition_eur
        zeile.kapitalwertvorteil_eur = barwert(differenz, zins)
        zeile.jaehrliche_einsparung_eur = (
            ref_zeile.energiekosten_eur_a - zeile.energiekosten_eur_a
        )
        zeile.interner_zinsfuss = interner_zinsfuss(differenz)
        zeile.amortisation_dynamisch_a = amortisationszeit(differenz, zins)
        zeile.co2_einsparung_t_a = ref_zeile.co2_t_a - zeile.co2_t_a
        if zeile.co2_einsparung_t_a and abs(zeile.co2_einsparung_t_a) > 1e-9:
            # negativer Kapitalwertvorteil = Mehrkosten je vermiedener Tonne
            jahre = ctx.get("zeitraum.jahre")
            mehrkosten_a = -zeile.kapitalwertvorteil_eur * annuitaetsfaktor(zins, jahre)
            zeile.co2_vermeidungskosten_eur_t = mehrkosten_a / zeile.co2_einsparung_t_a
        vergleich.zeilen.append(zeile)

    return vergleich


# ------------------------------------------------------------------ Sensitivität


@dataclass
class Sensitivitaetspunkt:
    parameter: str
    faktor: float
    kapitalwert_eur: float


def sensitivitaet(
    projekt: Projekt,
    variante_name: str,
    parameter: dict[str, Callable[[Projekt, float], Projekt]],
    faktoren: tuple[float, ...] = (0.8, 0.9, 1.0, 1.1, 1.2),
) -> list[Sensitivitaetspunkt]:
    """Sensitivitätsanalyse – von DIN EN 17463 für unsichere Eingangsgrößen gefordert.

    ``parameter`` bildet einen Namen auf eine Funktion ab, die eine veränderte
    Projektkopie liefert. Beispiel siehe ``sensitivitaet_energiepreis``.
    """
    punkte: list[Sensitivitaetspunkt] = []
    for name, aendere in parameter.items():
        for faktor in faktoren:
            variiert = aendere(projekt, faktor)
            ergebnisse = berechne_projekt(variiert)
            ctx = ergebnisse[variante_name]
            punkte.append(
                Sensitivitaetspunkt(name, faktor, ctx.get("ergebnis.kapitalwert_eur"))
            )
    return punkte


def sensitivitaet_energiepreis(projekt: Projekt, faktor: float) -> Projekt:
    """Beispiel-Variator: alle Arbeitspreise skalieren."""
    kopie = projekt.model_copy(deep=True)
    for preis in kopie.energiepreise:
        preis.arbeitspreis_eur_kwh *= faktor
    for variante in kopie.varianten:
        for preis in variante.energiepreise:
            preis.arbeitspreis_eur_kwh *= faktor
    return kopie


def sensitivitaet_investition(projekt: Projekt, faktor: float) -> Projekt:
    kopie = projekt.model_copy(deep=True)
    for variante in kopie.varianten:
        for position in variante.investition.positionen:
            position.einzelpreis_eur *= faktor
    return kopie


def sensitivitaet_zins(projekt: Projekt, faktor: float) -> Projekt:
    kopie = projekt.model_copy(deep=True)
    kopie.finanzrahmen.eigenkapitalrendite *= faktor
    kopie.finanzrahmen.fremdkapitalzins *= faktor
    if kopie.finanzrahmen.kalkulationszins_manuell is not None:
        kopie.finanzrahmen.kalkulationszins_manuell *= faktor
    return kopie
