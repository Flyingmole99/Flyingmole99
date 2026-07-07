"""CLI-Orchestrierung des BACtwin-Imports.

Beispiel:
    python -m importer.run_import \
        --dir /pfad/zu/workbooks \
        --dsn "host=/var/run/postgresql dbname=msr user=postgres" \
        --version "AMEV 1.2"
"""
from __future__ import annotations

import argparse
import hashlib
import os

import psycopg2

from . import loaders, parsers, validate
from .workbook import find_workbook, load_mapping


def _hash(path: str) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 16), b""):
            h.update(chunk)
    return h.hexdigest()


def run(directory: str, dsn: str, version_bez: str) -> dict:
    m1 = load_mapping("bibliothek1")
    m2 = load_mapping("bibliothek2")
    m3 = load_mapping("bibliothek3")

    wb1 = find_workbook(directory, m1["workbook_glob"])
    wb2 = find_workbook(directory, m2["workbook_glob"])
    wb3 = find_workbook(directory, m3["workbook_glob"])

    s1, s2, s3 = m1["sheets"], m2["sheets"], m3["sheets"]

    # --- Parsen (ohne DB) ---
    gewerke = parsers.parse_gewerke(wb1, s1["gewerke"])
    vokabular = parsers.parse_vokabular(wb1, s1["vokabular"])
    meldeklasse = parsers.parse_meldeklasse(wb3, s3["meldeklasse"])
    prio = parsers.parse_priority_array(wb3, s3["priority_array"])
    objekttypen = parsers.parse_objekttypen(wb2, s2["objekttypen_de"], s2["objekttypen_en"])
    mk_ids = {r["object_identifier"] for r in meldeklasse}
    properties = parsers.parse_properties(wb2, s2["properties"], mk_ids)
    templates, template_dp, dropped = parsers.parse_aggregate(wb3, s3["aggregate"])

    # --- Laden (eine Transaktion) ---
    conn = psycopg2.connect(dsn)
    conn.set_client_encoding("UTF8")
    try:
        with conn, conn.cursor() as cur:
            version_id = loaders.insert_version(
                cur, version_bez, os.path.basename(wb1), _hash(wb1))
            loaders.load_gewerke(cur, gewerke, version_id)
            loaders.load_vokabular(cur, vokabular, version_id)
            loaders.load_naming_profiles(cur, m1["naming_profiles"])
            loaders.load_meldeklasse(cur, meldeklasse, version_id)
            loaders.load_priority_array(cur, prio)
            loaders.load_objekttypen(cur, objekttypen, version_id)
            loaders.load_properties(cur, properties)
            loaders.load_aggregat_templates(cur, templates, version_id)
            loaders.load_template_dp(cur, template_dp)
            loaders.resolve_refs(cur)

        with conn.cursor() as cur:
            rep = validate.report(cur)
    finally:
        conn.close()

    rep["parsed"] = {
        "gewerke": len(gewerke), "vokabular": len(vokabular),
        "objekttypen": len(objekttypen), "properties": len(properties),
        "templates": len(templates), "template_dp": len(template_dp),
        "dropped_dubletten": len(dropped),
    }
    return rep


def main() -> None:
    ap = argparse.ArgumentParser(description="BACtwin-Bibliothek importieren")
    ap.add_argument("--dir", required=True, help="Verzeichnis mit den 3 Workbooks")
    ap.add_argument("--dsn", default=os.environ.get("DATABASE_URL", ""),
                    help="psycopg2-DSN (oder Env DATABASE_URL)")
    ap.add_argument("--version", default="AMEV 1.2", help="Versionsbezeichnung")
    args = ap.parse_args()

    rep = run(args.dir, args.dsn, args.version)
    print("== Import abgeschlossen ==")
    for k, v in rep["parsed"].items():
        print(f"  geparst  {k:16} {v}")
    for k, v in rep["counts"].items():
        print(f"  geladen  {k:20} {v}")
    print(f"  Hardware-Objekttypen: {rep['hardware_objekttypen']}")
    print(f"  unaufgelöste Referenzen: {rep['unresolved_refs']}")


if __name__ == "__main__":
    main()
