"""Unit-Tests der reinen Transformationen (keine DB/Dateien nötig)."""
from importer import transforms as T


def test_ist_hardware():
    assert T.ist_hardware("AI") and T.ist_hardware("bo")
    assert not T.ist_hardware("AV")
    assert not T.ist_hardware(None)


def test_ist_erweiterung():
    assert T.ist_erweiterung("EE") and T.ist_erweiterung("TL")
    assert not T.ist_erweiterung("BI")


def test_ist_unteraggregat():
    assert T.ist_unteraggregat("AGG_BRE_nM_AMEV1")
    assert T.ist_unteraggregat("BGP_KES_nM_AMEV1")
    assert not T.ist_unteraggregat("AI_MW_T_AMEV1")
    assert not T.ist_unteraggregat(None)


def test_to_number():
    assert T.to_number("120") == 120.0
    assert T.to_number("-20,5") == -20.5   # deutsches Dezimalkomma
    assert T.to_number("[Description]") is None
    assert T.to_number(None) is None


def test_normalize_notification_class():
    assert T.normalize_notification_class("200") == "NC200"
    assert T.normalize_notification_class("NC100") == "NC100"
    assert T.normalize_notification_class("100,101") == "NC100"
    assert T.normalize_notification_class("") is None
    assert T.normalize_notification_class("foo") is None


def test_is_data_kennung():
    assert T.is_data_kennung("AI_MW_T_AMEV1")
    assert not T.is_data_kennung("PropSort")
    assert not T.is_data_kennung(None)


def test_bas_relativ_nur_gesetzte_felder():
    row = {19: "HZV", 20: "BRE", 21: "xx", 24: "MW~", 25: "01", 26: None}
    blocks = {"medium": 19, "agg_kennung": 20, "agg_nr": 21,
              "fn_kennung": 24, "fn_nr": 25, "erweiterung": 26}
    out = T.bas_relativ(lambda i: row.get(i), blocks)
    assert out == {"medium": "HZV", "agg_kennung": "BRE", "agg_nr": "xx",
                   "fn_kennung": "MW~", "fn_nr": "01"}
    assert "erweiterung" not in out   # None-Werte werden ausgelassen
