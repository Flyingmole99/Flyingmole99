"""Tests der finanzmathematischen Grundfunktionen."""

from __future__ import annotations

import math

import pytest

from valeri.core.finanzmathematik import (
    amortisationszeit,
    annuitaetendarlehen,
    annuitaetsfaktor,
    barwert,
    barwertfaktor,
    interner_zinsfuss,
    real_aus_nominal,
    wacc,
)


def test_barwert_einzelzahlung():
    assert barwert([0, 110], 0.10) == pytest.approx(100.0)


def test_annuitaetsfaktor_verteilt_barwert_gleichmaessig():
    zins, jahre = 0.05, 10
    a = annuitaetsfaktor(zins, jahre)
    rate = 1000 * a
    assert barwert([0] + [rate] * jahre, zins) == pytest.approx(1000.0)


def test_annuitaetsfaktor_ohne_zins():
    assert annuitaetsfaktor(0.0, 20) == pytest.approx(1 / 20)


def test_barwertfaktor_ohne_preisaenderung_entspricht_rentenbarwert():
    zins, jahre = 0.04, 15
    erwartet = (1 - (1 + zins) ** -jahre) / zins
    assert barwertfaktor(zins, 0.0, jahre) == pytest.approx(erwartet)


def test_barwertfaktor_sonderfall_zins_gleich_preisaenderung():
    assert barwertfaktor(0.03, 0.03, 10) == pytest.approx(10 / 1.03)


def test_barwertfaktor_ist_kehrwert_konsistent_zum_annuitaetsfaktor():
    """b * a == 1, wenn keine Preisänderung wirkt."""
    zins, jahre = 0.06, 25
    assert barwertfaktor(zins, 0.0, jahre) * annuitaetsfaktor(zins, jahre) == pytest.approx(1.0)


def test_interner_zinsfuss_trifft_bekannten_wert():
    # -1000 heute, 10 Jahre je 150 -> IRR rund 8,14 %
    zahlungen = [-1000.0] + [150.0] * 10
    irr = interner_zinsfuss(zahlungen)
    assert irr is not None
    assert barwert(zahlungen, irr) == pytest.approx(0.0, abs=1e-4)


def test_interner_zinsfuss_ohne_vorzeichenwechsel_ist_none():
    assert interner_zinsfuss([-100.0, -50.0, -50.0]) is None


def test_amortisation_statisch_und_dynamisch():
    zahlungen = [-1000.0] + [250.0] * 10
    statisch = amortisationszeit(zahlungen, 0.0)
    dynamisch = amortisationszeit(zahlungen, 0.05)
    assert statisch == pytest.approx(4.0)
    assert dynamisch is not None and dynamisch > statisch


def test_amortisation_nicht_erreicht():
    assert amortisationszeit([-1000.0, 10.0, 10.0], 0.05) is None


def test_wacc_beruecksichtigt_steuervorteil_des_fremdkapitals():
    ohne_steuer = wacc(0.3, 0.08, 0.045, 0.0)
    mit_steuer = wacc(0.3, 0.08, 0.045, 0.30)
    assert ohne_steuer == pytest.approx(0.3 * 0.08 + 0.7 * 0.045)
    assert mit_steuer < ohne_steuer


def test_wacc_lehnt_unplausible_quote_ab():
    with pytest.raises(ValueError):
        wacc(1.4, 0.08, 0.045, 0.3)


def test_real_aus_nominal():
    assert real_aus_nominal(0.05, 0.02) == pytest.approx(1.05 / 1.02 - 1)


def test_annuitaetendarlehen_tilgt_vollstaendig():
    plan = annuitaetendarlehen(100_000, 0.04, 10, 10)
    assert plan[-1][2] == pytest.approx(0.0, abs=1e-6)
    raten = [zins + tilgung for zins, tilgung, _ in plan]
    assert all(math.isclose(raten[0], r, rel_tol=1e-9) for r in raten)


def test_annuitaetendarlehen_endet_mit_laufzeit():
    plan = annuitaetendarlehen(50_000, 0.03, 5, 8)
    assert all(z == 0 and t == 0 for z, t, _ in plan[5:])
