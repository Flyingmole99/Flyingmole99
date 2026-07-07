"""Unit-Tests der NamingEngine (rein, ohne DB)."""
from naming.engine import NamingEngine


def test_brenner_schaltbefehl():
    eng = NamingEngine()
    bas = eng.datapoint_bas("420_EZA01_KES01", {
        "medium": "HZ~", "agg_kennung": "BRE", "agg_nr": "xx",
        "bm_kennung": "#####", "bm_nr": "##", "fn_kennung": "SB~", "fn_nr": "01",
    })
    # Block 1-3 aus Kontext, xx->01, Füll-Kürzel bleibt, Nummern-Füller entfällt
    assert bas == "420_EZA01_KES01_HZ~_BRE01_#####_SB~01"


def test_ortsbezug_wird_aus_kontext_gesetzt():
    """Selbst wenn das relative Muster aus einem Unter-Aggregat stammt (Pumpe),
    zählt nur der Baugruppen-Kontext – kein '430_LTA…'-Präfix."""
    eng = NamingEngine()
    bas = eng.datapoint_bas("420_EZA01_KES01", {
        "medium": "HZV", "agg_kennung": "PPE", "agg_nr": "xx",
        "bm_kennung": "MOT", "bm_nr": "xx", "fn_kennung": "SB~", "fn_nr": "01",
    })
    assert bas == "420_EZA01_KES01_HZV_PPE01_MOT01_SB~01"


def test_erweiterung_wird_angehaengt():
    eng = NamingEngine()
    bas = eng.datapoint_bas("420_EZA01_KES01", {
        "medium": "HZ~", "agg_kennung": "BRE", "agg_nr": "xx",
        "bm_kennung": "#####", "fn_kennung": "BM~", "fn_nr": "01",
        "erweiterung": "TL",
    })
    assert bas.endswith("_BM~01_TL")


def test_gekuerzt_einstellige_nummer():
    eng = NamingEngine(variante="gekuerzt")
    bas = eng.datapoint_bas("H_VBA1_KES1", {
        "medium": "HZ~", "agg_kennung": "BRE", "agg_nr": "xx",
        "fn_kennung": "SB~", "fn_nr": "1",
    })
    assert "_BRE1_" in bas


def test_konkrete_nummer_bleibt():
    eng = NamingEngine()
    bas = eng.datapoint_bas("420_EZA01_KES01", {
        "medium": "HZ~", "agg_kennung": "WMZ", "agg_nr": "02",
        "fn_kennung": "MW~", "fn_nr": "01",
    })
    assert "_WMZ02_" in bas
