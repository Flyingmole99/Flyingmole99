"""Materialisierung: expandiert ein Aggregat-Template rekursiv und schreibt die
Datenpunkte einer Baugruppe nach project.datenpunkt.

Folding-Policy v1 (siehe /docs/msr-tool/Beispiel-Gaskessel.md §3):
- Struktur-Container (object_type = 'SV') sind keine Datenpunkte -> übersprungen.
- Trend-Objekte (object_type = 'TL') werden auf den Basispunkt gefaltet
  (trend=true), Suffix '_TL' identifiziert den Basispunkt eindeutig.
- Ereignis-Objekte (object_type = 'EE') werden gefaltet (alarm=true), sofern ein
  Basispunkt mit gleichem BAS ohne '_EE' existiert; sonst als eigener Datenpunkt.
- Alle übrigen Objekte (AI/AO/BI/BO/AV/BV/MI/MO/MV/…) -> eigener Datenpunkt.
"""
from __future__ import annotations

from psycopg2.extras import execute_values

from naming.engine import NamingEngine

_EXPAND = """
WITH RECURSIVE expand AS (
    SELECT dp.id, dp.template_uuid, dp.referenz_template_uuid, dp.dp_objekttyp_uuid,
           dp.bas_relativ, dp.reihenfolge, 0 AS tiefe
    FROM catalog.aggregat_template t
    JOIN catalog.aggregat_template_dp dp ON dp.template_uuid = t.uuid
    WHERE t.uuid = %s
  UNION ALL
    SELECT c.id, c.template_uuid, c.referenz_template_uuid, c.dp_objekttyp_uuid,
           c.bas_relativ, c.reihenfolge, e.tiefe + 1
    FROM expand e
    JOIN catalog.aggregat_template_dp c ON c.template_uuid = e.referenz_template_uuid
    WHERE e.referenz_template_uuid IS NOT NULL
)
SELECT e.bas_relativ, o.uuid, o.object_type, o.ist_hardware,
       p.units, p.min_pres, p.max_pres
FROM expand e
JOIN catalog.dp_objekttyp o ON o.uuid = e.dp_objekttyp_uuid
LEFT JOIN catalog.dp_objekt_property p ON p.objekttyp_uuid = o.uuid
WHERE e.dp_objekttyp_uuid IS NOT NULL
ORDER BY e.tiefe, e.reihenfolge
"""


def instantiate_baugruppe(cur, baugruppe_id: int, variante: str = "ungekuerzt") -> dict:
    """Erzeugt die Datenpunkte einer Baugruppe neu (idempotent) und liefert Kennzahlen."""
    cur.execute("""
        SELECT b.anlage_id, b.aggregat_template_uuid, b.bas
        FROM project.baugruppe b WHERE b.id = %s
    """, (baugruppe_id,))
    row = cur.fetchone()
    if row is None:
        raise ValueError(f"Baugruppe {baugruppe_id} nicht gefunden")
    anlage_id, template_uuid, baugruppe_bas = row

    cur.execute(_EXPAND, (template_uuid,))
    objects = cur.fetchall()

    engine = NamingEngine(variante=variante)

    containers, trends, events, base = [], [], [], []
    seen_base_bas: set[str] = set()
    duplikate = 0
    for bas_rel, uuid, otype, is_hw, units, mn, mx in objects:
        bas = engine.datapoint_bas(baugruppe_bas, bas_rel)
        rec = {
            "bas": bas, "uuid": uuid, "otype": otype, "is_hw": is_hw,
            "units": units, "min": mn, "max": mx,
            "funktion": engine.funktion(bas_rel),
            "trend": False, "alarm": False,
        }
        if otype == "SV":
            containers.append(rec)
        elif otype == "TL":
            trends.append(rec)
        elif otype == "EE":
            events.append(rec)
        elif bas in seen_base_bas:
            # gleicher BAS über verschiedene Objekttypen = alternative Variante
            # (z. B. BI_HD vs. MI_HD); erste gewinnt, BAS bleibt eindeutig.
            duplikate += 1
        else:
            seen_base_bas.add(bas)
            base.append(rec)

    by_bas = {b["bas"]: b for b in base}

    for t in trends:
        base_bas = t["bas"][:-3] if t["bas"].endswith("_TL") else None
        if base_bas in by_bas:
            by_bas[base_bas]["trend"] = True
        else:
            base.append(t)  # kein Basispunkt -> als eigener Punkt behalten
    for e in events:
        base_bas = e["bas"][:-3] if e["bas"].endswith("_EE") else None
        if base_bas in by_bas:
            by_bas[base_bas]["alarm"] = True
        else:
            base.append(e)

    # Sicherheitsnetz: endgültige BAS-Eindeutigkeit (auch über angehängte Objekte)
    unique_base, seen = [], set()
    for b in base:
        if b["bas"] in seen:
            duplikate += 1
            continue
        seen.add(b["bas"])
        unique_base.append(b)
    base = unique_base

    # idempotent: bestehende Datenpunkte dieser Baugruppe ersetzen
    cur.execute(
        "DELETE FROM project.datenpunkt WHERE quelle_typ='baugruppe' AND quelle_id=%s",
        (baugruppe_id,),
    )
    execute_values(cur, """
        INSERT INTO project.datenpunkt
            (anlage_id, quelle_typ, quelle_id, dp_objekttyp_uuid, bas_funktion,
             bas, units, min_pres, max_pres, trend, alarm)
        VALUES %s
    """, [(anlage_id, "baugruppe", baugruppe_id, b["uuid"], b["funktion"],
           b["bas"], b["units"], b["min"], b["max"], b["trend"], b["alarm"])
          for b in base])

    return {
        "objekte_gesamt": len(objects),
        "container_uebersprungen": len(containers),
        "varianten_dubletten": duplikate,
        "datenpunkte": len(base),
        "hardware": sum(1 for b in base if b["is_hw"]),
        "trend": sum(1 for b in base if b["trend"]),
        "alarm": sum(1 for b in base if b["alarm"]),
    }
