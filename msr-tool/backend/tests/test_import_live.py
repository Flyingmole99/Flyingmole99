"""Live-Integrationstest des vollständigen Imports.

Läuft nur, wenn beide Umgebungsvariablen gesetzt sind:
    BACTWIN_DIR   Verzeichnis mit den drei Bibliotheks-Workbooks
    DATABASE_URL  psycopg2-DSN einer Datenbank mit angewandten Migrationen

Prüft, dass der importierte Gaskessel BGP_KES_nM_AMEV1 rekursiv zu den
erwarteten 76 Datenpunkten (22 Hardware) expandiert.
"""
import os

import pytest

BACTWIN_DIR = os.environ.get("BACTWIN_DIR")
DATABASE_URL = os.environ.get("DATABASE_URL")

pytestmark = pytest.mark.skipif(
    not (BACTWIN_DIR and DATABASE_URL),
    reason="BACTWIN_DIR und DATABASE_URL erforderlich",
)


def test_import_gaskessel():
    import psycopg2

    from importer import validate
    from importer.run_import import run

    rep = run(BACTWIN_DIR, DATABASE_URL, "AMEV 1.2 (test)")

    # Grundmengen plausibel
    assert rep["counts"]["dp_objekttyp"] > 300
    assert rep["counts"]["aggregat_template"] > 100
    assert rep["unresolved_refs"] == 0

    # Gaskessel rekursiv auflösen
    conn = psycopg2.connect(DATABASE_URL)
    try:
        with conn.cursor() as cur:
            gesamt, hardware = validate.resolve_template(cur, "BGP_KES_nM_AMEV1")
    finally:
        conn.close()

    assert gesamt == 76, f"erwartet 76 Datenpunkte, erhalten {gesamt}"
    assert hardware == 22, f"erwartet 22 Hardware-I/O, erhalten {hardware}"
