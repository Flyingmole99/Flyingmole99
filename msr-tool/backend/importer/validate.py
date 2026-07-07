"""Import-Validierung: Referenzintegrität und Kennzahlen."""
from __future__ import annotations


def report(cur) -> dict:
    def scalar(sql, *args):
        cur.execute(sql, args)
        return cur.fetchone()[0]

    counts = {
        "bac_gewerk": scalar("SELECT count(*) FROM catalog.bac_gewerk"),
        "bac_vokabular": scalar("SELECT count(*) FROM catalog.bac_vokabular"),
        "dp_objekttyp": scalar("SELECT count(*) FROM catalog.dp_objekttyp"),
        "dp_objekt_property": scalar("SELECT count(*) FROM catalog.dp_objekt_property"),
        "aggregat_template": scalar("SELECT count(*) FROM catalog.aggregat_template"),
        "aggregat_template_dp": scalar("SELECT count(*) FROM catalog.aggregat_template_dp"),
        "meldeklasse": scalar("SELECT count(*) FROM catalog.meldeklasse"),
        "priority_array": scalar("SELECT count(*) FROM catalog.priority_array"),
    }
    unresolved = scalar("""
        SELECT count(*) FROM catalog.aggregat_template_dp
        WHERE dp_objekttyp_uuid IS NULL AND referenz_template_uuid IS NULL
    """)
    hardware = scalar("SELECT count(*) FROM catalog.dp_objekttyp WHERE ist_hardware")
    return {"counts": counts, "unresolved_refs": unresolved, "hardware_objekttypen": hardware}


def resolve_template(cur, kennung: str) -> tuple[int, int]:
    """Expandiert ein Template rekursiv zu allen Datenpunkten.

    Rückgabe: (gesamt_datenpunkte, davon_hardware).
    """
    cur.execute("""
        WITH RECURSIVE expand AS (
            SELECT dp.id, dp.dp_objekttyp_uuid, dp.referenz_template_uuid
            FROM catalog.aggregat_template t
            JOIN catalog.aggregat_template_dp dp ON dp.template_uuid = t.uuid
            WHERE t.kennung = %s
          UNION ALL
            SELECT child.id, child.dp_objekttyp_uuid, child.referenz_template_uuid
            FROM expand e
            JOIN catalog.aggregat_template_dp child
              ON child.template_uuid = e.referenz_template_uuid
            WHERE e.referenz_template_uuid IS NOT NULL
        )
        SELECT
            count(*) FILTER (WHERE dp_objekttyp_uuid IS NOT NULL) AS dp_gesamt,
            count(*) FILTER (WHERE dp_objekttyp_uuid IS NOT NULL AND o.ist_hardware) AS hardware
        FROM expand
        LEFT JOIN catalog.dp_objekttyp o ON o.uuid = expand.dp_objekttyp_uuid
    """, (kennung,))
    row = cur.fetchone()
    return int(row[0]), int(row[1] or 0)
