"""Tests der Modulmechanik – Reihenfolge, Austausch, Erweiterung.

Diese Tests sichern die eigentliche Architekturzusage ab: jedes Modul ist
unabhängig austauschbar, solange es seinen Daten-Vertrag erfüllt.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

import pytest

from valeri.core import registry
from valeri.core.kontext import Rechenkontext
from valeri.core.modul import Rechenmodul
from valeri.core.pipeline import PipelineFehler, berechne_variante, sortiere
from valeri.modelle.projekt import Projekt, Variante


class _A(Rechenmodul):
    id = "a"
    liefert = ("x",)

    def berechne(self, ctx: Rechenkontext) -> Mapping[str, Any]:
        return {"x": 1}


class _B(Rechenmodul):
    id = "b"
    benoetigt = ("x",)
    liefert = ("y",)

    def berechne(self, ctx: Rechenkontext) -> Mapping[str, Any]:
        return {"y": ctx.get("x") + 1}


class _C(Rechenmodul):
    id = "c"
    benoetigt = ("y",)
    liefert = ("z",)

    def berechne(self, ctx: Rechenkontext) -> Mapping[str, Any]:
        return {"z": ctx.get("y") * 10}


def _kontext() -> tuple[Projekt, Variante]:
    projekt = Projekt(name="T", varianten=[Variante(name="V")])
    return projekt, projekt.varianten[0]


def test_reihenfolge_folgt_den_vertraegen_nicht_der_eingabe():
    reihenfolge = [m.id for m in sortiere([_C(), _A(), _B()])]
    assert reihenfolge == ["a", "b", "c"]


def test_zyklus_wird_erkannt():
    class _Zyklus(Rechenmodul):
        id = "zyklus"
        benoetigt = ("z",)
        liefert = ("x",)

        def berechne(self, ctx):  # pragma: no cover - wird nie ausgeführt
            return {}

    with pytest.raises(PipelineFehler, match="Zyklus"):
        sortiere([_Zyklus(), _B(), _C()])


def test_doppelter_lieferant_wird_abgelehnt():
    class _Zweiter(Rechenmodul):
        id = "a2"
        liefert = ("x",)

        def berechne(self, ctx):  # pragma: no cover
            return {"x": 99}

    with pytest.raises(PipelineFehler, match="Mehrdeutigkeit"):
        sortiere([_A(), _Zweiter()])


def test_modul_austausch_aendert_nur_das_ergebnis_des_moduls():
    class _BAnders(Rechenmodul):
        id = "b"
        benoetigt = ("x",)
        liefert = ("y",)

        def berechne(self, ctx: Rechenkontext) -> Mapping[str, Any]:
            return {"y": ctx.get("x") + 100}

    projekt, variante = _kontext()
    original = berechne_variante(projekt, variante, [_A(), _B(), _C()])
    ersetzt = berechne_variante(projekt, variante, [_A(), _BAnders(), _C()])
    assert original.get("z") == 20
    assert ersetzt.get("z") == 1010  # nur über den Vertrag, ohne Änderung an _C


def test_protokoll_haelt_herkunft_jedes_wertes_fest():
    projekt, variante = _kontext()
    ctx = berechne_variante(projekt, variante, [_A(), _B()])
    quellen = {eintrag.schluessel: eintrag.modul_id for eintrag in ctx.protokoll}
    assert quellen == {"x": "a", "y": "b"}


def test_registry_verhindert_versehentliches_ueberschreiben():
    with pytest.raises(ValueError, match="bereits vergeben"):

        @registry.registriere()
        class _Doppelt(Rechenmodul):
            id = "m10_stammdaten"
            liefert = ("irgendwas",)

            def berechne(self, ctx):  # pragma: no cover
                return {}


def test_mitgelieferte_module_sind_widerspruchsfrei_sortierbar():
    module = registry.instanzen()
    reihenfolge = [m.id for m in sortiere(module)]
    assert reihenfolge.index("m30_bedarf") < reihenfolge.index("m35_speicher")
    assert reihenfolge.index("m35_speicher") < reihenfolge.index("m40_erzeuger")
    assert reihenfolge.index("m70_zahlungsreihe") < reihenfolge.index("m75_steuern")
    assert reihenfolge.index("m75_steuern") < reihenfolge.index("m80_valeri")
    assert reihenfolge[-1] == "m95_bericht"
