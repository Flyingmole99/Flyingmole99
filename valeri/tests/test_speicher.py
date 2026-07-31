"""Tests der Spitzenlastkappung."""

from __future__ import annotations

import pytest

from valeri.core.einheiten import Energieart
from valeri.core.zeitreihe import Lastgang
from valeri.module.m35_speicher import kappe
from valeri.modelle.speicher import Speicher


def _spitzenprofil() -> Lastgang:
    """Bandlast 100 kW mit einer täglichen Spitze von 300 kW über 2 h."""
    werte = []
    for stunde in range(8760):
        werte.append(300.0 if stunde % 24 in (10, 11) else 100.0)
    return Lastgang(tuple(werte), 60, "test")


def test_ohne_kapazitaet_keine_kappung():
    lastgang = _spitzenprofil()
    speicher = Speicher(energieart=Energieart.KAELTE, modus="maximal")
    ergebnis_lastgang, ergebnis = kappe(lastgang, speicher)
    assert ergebnis.spitze_nachher_kw == pytest.approx(300.0)
    assert ergebnis_lastgang.summe_kwh() == pytest.approx(lastgang.summe_kwh())


def test_kappung_senkt_spitze_und_haelt_arbeit_naeherungsweise():
    lastgang = _spitzenprofil()
    speicher = Speicher(
        energieart=Energieart.KAELTE,
        modus="maximal",
        kapazitaet_kwh=500,
        ladeleistung_kw=100,
        entladeleistung_kw=250,
        verlust_pro_tag=0.0,
        wirkungsgrad_laden=1.0,
        wirkungsgrad_entladen=1.0,
        max_kappung_anteil=0.9,
    )
    gekappt, ergebnis = kappe(lastgang, speicher)
    assert ergebnis.spitze_nachher_kw < 300.0
    assert gekappt.spitzenlast_kw() == pytest.approx(ergebnis.spitze_nachher_kw, rel=1e-6)
    # verlustfrei: Jahresarbeit bleibt erhalten
    assert gekappt.summe_kwh() == pytest.approx(lastgang.summe_kwh(), rel=1e-3)


def test_verluste_erhoehen_die_jahresarbeit():
    lastgang = _spitzenprofil()
    speicher = Speicher(
        energieart=Energieart.WAERME,
        modus="zielspitze",
        ziel_spitzenlast_kw=250,
        kapazitaet_kwh=400,
        wirkungsgrad_laden=0.9,
        wirkungsgrad_entladen=0.9,
        verlust_pro_tag=0.05,
    )
    gekappt, ergebnis = kappe(lastgang, speicher)
    assert ergebnis.zusatzarbeit_kwh > 0
    assert gekappt.summe_kwh() > lastgang.summe_kwh()


def test_zielspitze_wird_eingehalten():
    lastgang = _spitzenprofil()
    speicher = Speicher(
        energieart=Energieart.KAELTE,
        modus="zielspitze",
        ziel_spitzenlast_kw=200,
        kapazitaet_kwh=1000,
        verlust_pro_tag=0.0,
        max_kappung_anteil=0.9,
    )
    gekappt, ergebnis = kappe(lastgang, speicher)
    assert gekappt.spitzenlast_kw() <= 200.0 + 1e-6
    assert ergebnis.hinweis == ""


def test_zu_kleiner_speicher_meldet_fehlmenge():
    lastgang = _spitzenprofil()
    speicher = Speicher(
        energieart=Energieart.KAELTE,
        modus="zielspitze",
        ziel_spitzenlast_kw=120,
        kapazitaet_kwh=50,
        max_kappung_anteil=0.9,
    )
    _, ergebnis = kappe(lastgang, speicher)
    assert "nicht durchgängig haltbar" in ergebnis.hinweis


def test_kapazitaet_auslegen_findet_ausreichende_groesse():
    lastgang = _spitzenprofil()
    speicher = Speicher(
        energieart=Energieart.KAELTE,
        modus="kapazitaet_auslegen",
        ziel_spitzenlast_kw=150,
        verlust_pro_tag=0.0,
        wirkungsgrad_laden=1.0,
        wirkungsgrad_entladen=1.0,
        max_kappung_anteil=0.9,
    )
    gekappt, ergebnis = kappe(lastgang, speicher)
    # täglich 2 h x 150 kW über der Zielspitze -> rund 300 kWh nutzbar
    assert ergebnis.kapazitaet_kwh == pytest.approx(300.0, rel=0.05)
    assert gekappt.spitzenlast_kw() <= 150.0 + 1e-6


def test_max_kappung_begrenzt_das_ergebnis():
    lastgang = _spitzenprofil()
    speicher = Speicher(
        energieart=Energieart.KAELTE,
        modus="maximal",
        kapazitaet_kwh=100_000,
        verlust_pro_tag=0.0,
        max_kappung_anteil=0.2,
    )
    _, ergebnis = kappe(lastgang, speicher)
    assert ergebnis.spitze_nachher_kw >= 300.0 * 0.8 - 1e-6
