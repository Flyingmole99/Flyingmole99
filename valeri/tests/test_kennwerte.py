"""Tests der Kennwertableitung aus Produktkategorie und AfA-Tabelle."""

from __future__ import annotations

import pytest

from valeri.core.kontext import Rechenkontext
from valeri.daten import katalog
from valeri.module.m61_kennwerte import Kennwertableitung
from valeri.modelle.investition import Foerderung, Investitionsposition
from valeri.modelle.projekt import Projekt, Variante


def _kontext() -> Rechenkontext:
    projekt = Projekt(name="Test")
    variante = Variante(name="V1")
    return Rechenkontext(projekt=projekt, variante=variante)


def _rechne(positionen: list[Investitionsposition], ctx: Rechenkontext | None = None):
    ctx = ctx or _kontext()
    ctx.werte["invest.positionen_roh"] = positionen
    ergebnis = Kennwertableitung().berechne(ctx)
    return ergebnis["invest.positionen"], ctx


def test_kennwerte_kommen_aus_der_kategorie():
    kategorie = katalog().kategorie("waermeerzeuger.kessel.gas")
    positionen, _ = _rechne(
        [
            Investitionsposition(
                bezeichnung="Kessel",
                kategorie="waermeerzeuger.kessel.gas",
                einzelpreis_eur=100_000,
            )
        ]
    )
    daten = positionen[0]
    assert daten.nutzungsdauer_a == kategorie.nutzungsdauer_a
    assert daten.instandsetzung_eur_a == pytest.approx(
        100_000 * kategorie.instandsetzung_anteil
    )
    assert daten.wartung_eur_a == pytest.approx(100_000 * kategorie.wartung_anteil)
    assert daten.herkunft["nutzungsdauer_a"].startswith("vdi2067:")


def test_afa_dauer_kommt_aus_dem_verknuepften_schluessel():
    positionen, _ = _rechne(
        [
            Investitionsposition(
                bezeichnung="BHKW",
                kategorie="waermeerzeuger.bhkw",
                einzelpreis_eur=200_000,
            )
        ]
    )
    daten = positionen[0]
    assert daten.afa_dauer_a == katalog().afa_eintrag("bhkw").nutzungsdauer_a
    assert daten.herkunft["afa_dauer_a"] == "afa:bhkw"
    # technische und steuerliche Nutzungsdauer sind bewusst getrennt
    assert daten.nutzungsdauer_a != daten.afa_dauer_a


def test_manuelle_eingabe_hat_vorrang():
    positionen, _ = _rechne(
        [
            Investitionsposition(
                bezeichnung="Sonderanlage",
                kategorie="waermeerzeuger.kessel.gas",
                einzelpreis_eur=100_000,
                nutzungsdauer_a=12,
                afa_dauer_a=8,
                wartung_anteil=0.05,
            )
        ]
    )
    daten = positionen[0]
    assert daten.nutzungsdauer_a == 12
    assert daten.afa_dauer_a == 8
    assert daten.wartung_eur_a == pytest.approx(5_000)
    assert daten.herkunft["nutzungsdauer_a"] == "manuell"
    assert daten.herkunft["wartung_anteil"] == "manuell"


def test_ohne_kategorie_greifen_vorgabewerte():
    positionen, ctx = _rechne(
        [Investitionsposition(bezeichnung="Ohne", einzelpreis_eur=1000)]
    )
    daten = positionen[0]
    assert daten.herkunft["nutzungsdauer_a"] == "vorgabe"
    assert daten.wartung_eur_a == 0.0


def test_unbekannte_kategorie_meldet_hinweis():
    positionen, ctx = _rechne(
        [
            Investitionsposition(
                bezeichnung="Falsch", kategorie="gibt.es.nicht", einzelpreis_eur=1000
            )
        ]
    )
    assert any("gibt.es.nicht" in h for h in ctx.hinweise)
    assert positionen[0].nutzungsdauer_a > 0  # Berechnung läuft weiter


def test_ungeprueft_erzeugt_warnhinweis():
    _, ctx = _rechne(
        [
            Investitionsposition(
                bezeichnung="Kessel",
                kategorie="waermeerzeuger.kessel.gas",
                einzelpreis_eur=1000,
            )
        ]
    )
    assert any("Ungeprüfte Katalogwerte" in h for h in ctx.hinweise)


def test_positionsfoerderung_mit_hoechstbetrag():
    positionen, _ = _rechne(
        [
            Investitionsposition(
                bezeichnung="WP",
                kategorie="waermeerzeuger.waermepumpe.sole",
                einzelpreis_eur=300_000,
                foerderung=Foerderung(anteil=0.3, hoechstbetrag_eur=50_000),
            )
        ]
    )
    daten = positionen[0]
    assert daten.foerderung_eur == pytest.approx(50_000)
    assert daten.bemessungsgrundlage_eur == pytest.approx(250_000)


def test_gesamtfoerderung_wird_anteilig_verteilt():
    ctx = _kontext()
    ctx.variante.investition.gesamtfoerderung = Foerderung(anteil=0.2)
    positionen, _ = _rechne(
        [
            Investitionsposition(bezeichnung="A", einzelpreis_eur=100_000),
            Investitionsposition(bezeichnung="B", einzelpreis_eur=300_000),
        ],
        ctx,
    )
    assert positionen[0].foerderung_eur == pytest.approx(20_000)
    assert positionen[1].foerderung_eur == pytest.approx(60_000)
