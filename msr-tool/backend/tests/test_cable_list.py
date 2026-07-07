"""Unit-Test der Feldgerät-Ableitung (rein)."""
from generators.cable_list.excel import _device_of


def test_device_of_mit_funktion():
    # Feldgerät = BAS ohne Funktionsblock (Block 7)
    assert _device_of("420_EZA01_KES01_HZ~_BRE01_#####_SB~01", "SB~01") \
        == "420_EZA01_KES01_HZ~_BRE01_#####"


def test_device_of_fallback_ohne_funktion():
    assert _device_of("420_EZA01_KES01_HZV_PPE01_MOT01_BM~01", None) \
        == "420_EZA01_KES01_HZV_PPE01_MOT01"


def test_gleiches_geraet_unterschiedliche_signale():
    # zwei Signale desselben Geräts -> gleiches Feldgerät
    d1 = _device_of("420_EZA01_KES01_HZV_VEN01_MOT01_ST~01", "ST~01")
    d2 = _device_of("420_EZA01_KES01_HZV_VEN01_MOT01_RW~01", "RW~01")
    assert d1 == d2
