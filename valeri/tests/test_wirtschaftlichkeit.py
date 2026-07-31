"""Integrationstests der Gesamtrechnung.

Der zentrale Test ist die Kreuzprobe: Unter vereinfachten Randbedingungen
(keine Steuern, keine Preissteigerung, keine Ersatzinvestition, kein Restwert)
müssen die Kapitalwertrechnung nach DIN EN 17463 und die Annuitätenrechnung
nach VDI 2067 dasselbe Ergebnis liefern – die Annuität ist dann exakt der mit
dem Annuitätsfaktor umgerechnete Kapitalwert.
"""

from __future__ import annotations

import pytest

from valeri import rechne
from valeri.core.einheiten import Energieart, Energietraeger
from valeri.core.finanzmathematik import annuitaetsfaktor
from valeri.core.pipeline import berechne_variante
from valeri.modelle.energie import Energiepreis, Lastgangquelle, Verbrauch
from valeri.modelle.erzeuger import Erzeuger, Erzeugerpark, Erzeugertyp
from valeri.modelle.finanzen import Finanzrahmen, Preisaenderung, Steuerparameter
from valeri.modelle.investition import Investition, Investitionsposition
from valeri.modelle.projekt import Projekt, Variante
from valeri.modelle.speicher import Speicher

KEINE_PREISAENDERUNG = Preisaenderung(
    **{feld: 0.0 for feld in Preisaenderung.model_fields}
)


def _finanzrahmen(**anpassungen) -> Finanzrahmen:
    vorgabe = dict(
        betrachtungszeitraum_a=20,
        kalkulationszins_modus="manuell",
        kalkulationszins_manuell=0.05,
        steuern=Steuerparameter(steuerneutral=True),
        preisaenderung=KEINE_PREISAENDERUNG,
    )
    vorgabe.update(anpassungen)
    return Finanzrahmen(**vorgabe)


def _variante(
    name: str = "V1",
    investition_eur: float = 200_000,
    nutzungsgrad: float = 1.0,
    **anpassungen,
) -> Variante:
    vorgabe = dict(
        name=name,
        erzeugerpark=Erzeugerpark(
            erzeuger=[
                Erzeuger(
                    name="Kessel",
                    typ=Erzeugertyp.KESSEL,
                    energieart=Energieart.WAERME,
                    nutzungsgrad=nutzungsgrad,
                )
            ]
        ),
        investition=Investition(
            positionen=[
                Investitionsposition(
                    bezeichnung="Anlage",
                    einzelpreis_eur=investition_eur,
                    nutzungsdauer_a=20,
                    afa_dauer_a=20,
                    wartung_anteil=0.01,
                    ersatzinvestition=False,
                    restwert=False,
                )
            ]
        ),
    )
    vorgabe.update(anpassungen)
    return Variante(**vorgabe)


def _projekt(varianten: list[Variante] | None = None, **anpassungen) -> Projekt:
    vorgabe = dict(
        name="Testprojekt",
        finanzrahmen=_finanzrahmen(),
        bedarf=[
            Verbrauch(
                energieart=Energieart.WAERME,
                jahresbedarf_kwh=1_000_000,
                lastgang=Lastgangquelle(art="konstant"),
            )
        ],
        energiepreise=[
            Energiepreis(traeger=Energietraeger.ERDGAS, arbeitspreis_eur_kwh=0.10)
        ],
        varianten=varianten or [_variante()],
    )
    vorgabe.update(anpassungen)
    return Projekt(**vorgabe)


# ----------------------------------------------------------------- Kreuzprobe


def test_kapitalwert_und_annuitaet_sind_konsistent():
    projekt = _projekt()
    ctx = berechne_variante(projekt, projekt.varianten[0])
    a = annuitaetsfaktor(0.05, 20)
    assert ctx.get("ergebnis.kapitalwert_eur") * a == pytest.approx(
        ctx.get("ergebnis.annuitaet_eur_a"), rel=1e-9
    )


def test_kapitalwert_entspricht_handrechnung():
    """Investition 200.000, jährlich 100.000 Energie + 2.000 Wartung, 20 a, 5 %."""
    projekt = _projekt()
    ctx = berechne_variante(projekt, projekt.varianten[0])
    rentenbarwert = (1 - 1.05**-20) / 0.05
    erwartet = -200_000 - (100_000 + 2_000) * rentenbarwert
    assert ctx.get("ergebnis.kapitalwert_eur") == pytest.approx(erwartet, rel=1e-9)


def test_nutzungsgrad_wirkt_auf_die_energiekosten():
    projekt = _projekt(varianten=[_variante(nutzungsgrad=0.8)])
    ctx = berechne_variante(projekt, projekt.varianten[0])
    assert ctx.get("energie.kosten_eur_a") == pytest.approx(1_000_000 / 0.8 * 0.10)


# ------------------------------------------------------------------- Bausteine


def test_foerderung_mindert_die_auszahlung_in_jahr_null():
    from valeri.modelle.investition import Foerderung

    variante = _variante()
    variante.investition.positionen[0].foerderung = Foerderung(anteil=0.25)
    projekt = _projekt(varianten=[variante])
    ctx = berechne_variante(projekt, variante)
    reihe = ctx.get("zahlung.nach_steuern")
    assert reihe[0].investition == pytest.approx(-200_000)
    assert reihe[0].foerderung == pytest.approx(50_000)
    assert reihe[0].cashflow_vor_steuern == pytest.approx(-150_000)


def test_ersatzinvestition_und_restwert():
    variante = _variante()
    position = variante.investition.positionen[0]
    position.nutzungsdauer_a = 15
    position.ersatzinvestition = True
    position.restwert = True
    projekt = _projekt(varianten=[variante])
    ctx = berechne_variante(projekt, variante)
    reihe = ctx.get("zahlung.nach_steuern")
    # Ersatz nach 15 Jahren, Restnutzungsdauer 10 von 15 Jahren am Ende
    assert reihe[15].investition == pytest.approx(-200_000)
    assert reihe[20].restwert == pytest.approx(200_000 * 10 / 15)


def test_steuerwirkung_verbessert_den_kapitalwert_einer_kostenvariante():
    ohne = _projekt()
    mit = _projekt(
        finanzrahmen=_finanzrahmen(
            steuern=Steuerparameter(modus="manuell", satz_manuell=0.30)
        )
    )
    kw_ohne = berechne_variante(ohne, ohne.varianten[0]).get("ergebnis.kapitalwert_eur")
    kw_mit = berechne_variante(mit, mit.varianten[0]).get("ergebnis.kapitalwert_eur")
    # Kosten mindern den steuerlichen Gewinn -> Auszahlungen wirken abgemildert
    assert kw_mit > kw_ohne


def test_abschreibung_folgt_der_steuerlichen_nutzungsdauer():
    variante = _variante()
    variante.investition.positionen[0].afa_dauer_a = 10
    projekt = _projekt(
        varianten=[variante],
        finanzrahmen=_finanzrahmen(
            steuern=Steuerparameter(modus="manuell", satz_manuell=0.30)
        ),
    )
    ctx = berechne_variante(projekt, variante)
    reihe = ctx.get("zahlung.nach_steuern")
    assert reihe[1].abschreibung == pytest.approx(-20_000)
    assert reihe[10].abschreibung == pytest.approx(-20_000)
    assert reihe[11].abschreibung == pytest.approx(0.0)


def test_speicher_senkt_die_leistungskosten():
    lastgang = Lastgangquelle(art="profil", profiltyp="waerme")
    bedarf = [
        Verbrauch(
            energieart=Energieart.WAERME, jahresbedarf_kwh=1_000_000, lastgang=lastgang
        )
    ]
    preise = [
        Energiepreis(
            traeger=Energietraeger.STROM,
            arbeitspreis_eur_kwh=0.20,
            leistungspreis_eur_kw_a=150.0,
        )
    ]
    erzeuger = Erzeugerpark(
        erzeuger=[
            Erzeuger(
                name="WP",
                typ=Erzeugertyp.WAERMEPUMPE,
                energieart=Energieart.WAERME,
                jaz=3.5,
            )
        ]
    )
    ohne = _variante(name="ohne", erzeugerpark=erzeuger)
    mit = _variante(
        name="mit",
        erzeugerpark=erzeuger,
        speicher=[
            Speicher(
                name="Puffer",
                energieart=Energieart.WAERME,
                modus="maximal",
                kapazitaet_kwh=3000,
                verlust_pro_tag=0.0,
                max_kappung_anteil=0.5,
            )
        ],
    )
    projekt = _projekt(varianten=[ohne, mit], bedarf=bedarf, energiepreise=preise)
    ergebnisse = {v.name: berechne_variante(projekt, v) for v in projekt.varianten}

    spitze_ohne = ergebnisse["ohne"].get("energie.traegerkosten")[0].spitzenlast_kw
    spitze_mit = ergebnisse["mit"].get("energie.traegerkosten")[0].spitzenlast_kw
    assert spitze_mit < spitze_ohne
    assert (
        ergebnisse["mit"].get("energie.kosten_eur_a")
        < ergebnisse["ohne"].get("energie.kosten_eur_a")
    )


def test_kostenansatz_ersetzt_die_physikalische_rechnung():
    variante = _variante(
        erzeugerpark=Erzeugerpark(
            erzeuger=[
                Erzeuger(
                    name="Contracting",
                    typ=Erzeugertyp.KOSTENANSATZ,
                    energieart=Energieart.WAERME,
                    kosten_eur_kwh=0.12,
                    kosten_grundpreis_eur_a=1_200,
                )
            ]
        )
    )
    projekt = _projekt(varianten=[variante])
    ctx = berechne_variante(projekt, variante)
    assert ctx.get("energie.kosten_eur_a") == pytest.approx(1_000_000 * 0.12 + 1_200)
    assert ctx.get("erzeuger.endenergie") == {}


# ------------------------------------------------------------------- Vergleich


def test_variantenvergleich_bildet_differenzgroessen():
    referenz = _variante(name="Referenz", investition_eur=100_000, nutzungsgrad=0.85)
    referenz.ist_referenz = True
    neu = _variante(name="Neu", investition_eur=300_000, nutzungsgrad=1.0)
    projekt = _projekt(varianten=[referenz, neu])
    ergebnis = rechne(projekt)

    zeile = next(z for z in ergebnis.vergleich.zeilen if z.variante == "Neu")
    assert zeile.mehrinvestition_eur == pytest.approx(200_000)
    assert zeile.jaehrliche_einsparung_eur == pytest.approx(
        1_000_000 / 0.85 * 0.10 - 1_000_000 * 0.10
    )
    assert zeile.kapitalwertvorteil_eur is not None
    assert zeile.interner_zinsfuss is not None


def test_bericht_wird_erzeugt():
    projekt = _projekt()
    ergebnis = rechne(projekt)
    text = ergebnis.bericht("V1")
    assert "Kapitalwert" in text
    assert "VDI 2067" in text
