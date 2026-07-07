"""DB-Loader: Upsert je Zieltabelle (psycopg2). Idempotent über die Naturschlüssel."""
from __future__ import annotations

import json

from psycopg2.extras import Json, execute_values


def _upsert(cur, sql: str, rows: list[tuple]):
    if rows:
        execute_values(cur, sql, rows)


def insert_version(cur, bezeichnung: str, quelle_datei: str, hash_: str) -> int:
    cur.execute(
        """INSERT INTO catalog.bac_version(bezeichnung, quelle_datei, hash)
           VALUES (%s, %s, %s)
           ON CONFLICT (bezeichnung) DO UPDATE SET importiert_am = now()
           RETURNING id""",
        (bezeichnung, quelle_datei, hash_),
    )
    return cur.fetchone()[0]


def load_gewerke(cur, rows: list[dict], version_id: int):
    _upsert(cur, """
        INSERT INTO catalog.bac_gewerk
            (kg, kuerzel, kuerzel_1z, bezeichnung_de, bezeichnung_en, version_id)
        VALUES %s
        ON CONFLICT (kg) DO UPDATE SET
            kuerzel=EXCLUDED.kuerzel, kuerzel_1z=EXCLUDED.kuerzel_1z,
            bezeichnung_de=EXCLUDED.bezeichnung_de, bezeichnung_en=EXCLUDED.bezeichnung_en,
            version_id=EXCLUDED.version_id, status='aktiv'
    """, [(r["kg"], r["kuerzel"], r["kuerzel_1z"], r["bezeichnung_de"],
           r["bezeichnung_en"], version_id) for r in rows])


def load_vokabular(cur, rows: list[dict], version_id: int):
    _upsert(cur, """
        INSERT INTO catalog.bac_vokabular
            (block, kuerzel, bezeichnung, beschreibung, sprache, version_id)
        VALUES %s
        ON CONFLICT (block, kuerzel, sprache) DO UPDATE SET
            bezeichnung=EXCLUDED.bezeichnung, beschreibung=EXCLUDED.beschreibung,
            version_id=EXCLUDED.version_id, status='aktiv'
    """, [(r["block"], r["kuerzel"], r["bezeichnung"], r["beschreibung"], "de",
           version_id) for r in rows])


def load_naming_profiles(cur, profiles: list[dict]):
    for p in profiles:
        cur.execute("""
            INSERT INTO catalog.naming_profile
                (name, variante, sprache, trennzeichen_default, segmente)
            VALUES (%s, %s, %s, %s, %s)
            ON CONFLICT (name) DO UPDATE SET
                variante=EXCLUDED.variante, trennzeichen_default=EXCLUDED.trennzeichen_default,
                segmente=EXCLUDED.segmente
        """, (p["name"], p["variante"], p.get("sprache", "de"),
              p.get("trennzeichen_default", "_"), Json(p["segmente"])))


def load_meldeklasse(cur, rows: list[dict], version_id: int):
    _upsert(cur, """
        INSERT INTO catalog.meldeklasse
            (object_identifier, bezeichnung_de, bezeichnung_en, priority, ack_required, version_id)
        VALUES %s
        ON CONFLICT (object_identifier) DO UPDATE SET
            bezeichnung_de=EXCLUDED.bezeichnung_de, priority=EXCLUDED.priority,
            ack_required=EXCLUDED.ack_required, version_id=EXCLUDED.version_id
    """, [(r["object_identifier"], r["bezeichnung_de"], r["bezeichnung_en"],
           r["priority"], r["ack_required"], version_id) for r in rows])


def load_priority_array(cur, rows: list[dict]):
    _upsert(cur, """
        INSERT INTO catalog.priority_array (prio, verwendung, empfehlung, beschreibung)
        VALUES %s
        ON CONFLICT (prio) DO UPDATE SET
            verwendung=EXCLUDED.verwendung, empfehlung=EXCLUDED.empfehlung,
            beschreibung=EXCLUDED.beschreibung
    """, [(r["prio"], r["verwendung"], r["empfehlung"], r["beschreibung"]) for r in rows])


def load_objekttypen(cur, rows: list[dict], version_id: int):
    _upsert(cur, """
        INSERT INTO catalog.dp_objekttyp
            (uuid, obj_sort, kennung, object_type, bezeichnung_de, bezeichnung_en,
             ist_hardware, ist_erweiterung, version_id)
        VALUES %s
        ON CONFLICT (uuid) DO UPDATE SET
            obj_sort=EXCLUDED.obj_sort, kennung=EXCLUDED.kennung,
            object_type=EXCLUDED.object_type, bezeichnung_de=EXCLUDED.bezeichnung_de,
            bezeichnung_en=EXCLUDED.bezeichnung_en, ist_hardware=EXCLUDED.ist_hardware,
            ist_erweiterung=EXCLUDED.ist_erweiterung, version_id=EXCLUDED.version_id,
            status='aktiv'
    """, [(r["uuid"], r["obj_sort"], r["kennung"], r["object_type"],
           r["bezeichnung_de"], r["bezeichnung_en"], r["ist_hardware"],
           r["ist_erweiterung"], version_id) for r in rows])


def load_properties(cur, rows: list[dict]):
    """Join per kennung -> objekttyp_uuid; upsert 1:1 je Objekttyp."""
    _upsert(cur, """
        INSERT INTO catalog.dp_objekt_property
            (objekttyp_uuid, object_name_muster, description_muster, units,
             min_pres, max_pres, notification_class, low_limit, high_limit, deadband)
        SELECT o.uuid, v.object_name_muster, v.description_muster, v.units,
               v.min_pres::numeric, v.max_pres::numeric, v.notification_class,
               v.low_limit::numeric, v.high_limit::numeric, v.deadband::numeric
        FROM (VALUES %s) AS v(kennung, object_name_muster, description_muster, units,
             min_pres, max_pres, notification_class, low_limit, high_limit, deadband)
        JOIN catalog.dp_objekttyp o ON o.kennung = v.kennung
        ON CONFLICT (objekttyp_uuid) DO UPDATE SET
            object_name_muster=EXCLUDED.object_name_muster, units=EXCLUDED.units,
            min_pres=EXCLUDED.min_pres, max_pres=EXCLUDED.max_pres,
            notification_class=EXCLUDED.notification_class,
            low_limit=EXCLUDED.low_limit, high_limit=EXCLUDED.high_limit,
            deadband=EXCLUDED.deadband
    """, [(r["kennung"], r["object_name_muster"], r["description_muster"], r["units"],
           r["min_pres"], r["max_pres"], r["notification_class"], r["low_limit"],
           r["high_limit"], r["deadband"]) for r in rows])


def load_aggregat_templates(cur, rows: list[dict], version_id: int):
    _upsert(cur, """
        INSERT INTO catalog.aggregat_template
            (uuid, typ, gewerk_kg, kennung, bezeichnung_de, version_id)
        VALUES %s
        ON CONFLICT (uuid) DO UPDATE SET
            typ=EXCLUDED.typ, gewerk_kg=EXCLUDED.gewerk_kg, kennung=EXCLUDED.kennung,
            bezeichnung_de=EXCLUDED.bezeichnung_de, version_id=EXCLUDED.version_id,
            status='aktiv'
    """, [(r["uuid"], r["typ"], r["gewerk_kg"], r["kennung"],
           r["bezeichnung_de"], version_id) for r in rows])


def load_template_dp(cur, rows: list[dict]):
    """Rohladung (referenz_kennung + Flags + bas_relativ). FKs füllt resolve_refs()."""
    # Vorher die DP-Zeilen der neu importierten Templates leeren (voller Ersatz),
    # damit ein Reimport keine Dubletten erzeugt.
    template_uuids = list({r["template_uuid"] for r in rows})
    if template_uuids:
        cur.execute(
            "DELETE FROM catalog.aggregat_template_dp WHERE template_uuid = ANY(%s::uuid[])",
            (template_uuids,),
        )
    _upsert(cur, """
        INSERT INTO catalog.aggregat_template_dp
            (template_uuid, reihenfolge, referenz_kennung, ist_unteraggregat,
             variante, beschreibung, bas_relativ, object_name_beispiel)
        VALUES %s
    """, [(r["template_uuid"], r["reihenfolge"], r["referenz_kennung"],
           r["ist_unteraggregat"], r["variante"], r["beschreibung"],
           Json(r["bas_relativ"]), r["object_name_beispiel"]) for r in rows])


def resolve_refs(cur) -> None:
    """Löst referenz_kennung -> dp_objekttyp_uuid bzw. referenz_template_uuid auf."""
    cur.execute("""
        UPDATE catalog.aggregat_template_dp dp
        SET referenz_template_uuid = t.uuid, dp_objekttyp_uuid = NULL
        FROM catalog.aggregat_template t
        WHERE dp.ist_unteraggregat AND t.kennung = dp.referenz_kennung
    """)
    cur.execute("""
        UPDATE catalog.aggregat_template_dp dp
        SET dp_objekttyp_uuid = o.uuid, referenz_template_uuid = NULL
        FROM catalog.dp_objekttyp o
        WHERE NOT dp.ist_unteraggregat AND o.kennung = dp.referenz_kennung
    """)
    # Fallback: Referenz ohne Versionssuffix (ref = "..._AMEV1", Objekt = "..._AMEV1.2").
    # Greift nur, wenn GENAU EIN Objekttyp mit diesem Präfix vor dem ersten Punkt
    # existiert (Eindeutigkeit), sonst bleibt die Referenz unaufgelöst (Validierung).
    cur.execute("""
        WITH cand AS (
            SELECT dp.id AS dp_id, o.uuid AS o_uuid,
                   count(*) OVER (PARTITION BY dp.id) AS n
            FROM catalog.aggregat_template_dp dp
            JOIN catalog.dp_objekttyp o
              ON split_part(o.kennung, '.', 1) = dp.referenz_kennung
            WHERE NOT dp.ist_unteraggregat
              AND dp.dp_objekttyp_uuid IS NULL
              AND dp.referenz_template_uuid IS NULL
        )
        UPDATE catalog.aggregat_template_dp dp
        SET dp_objekttyp_uuid = cand.o_uuid
        FROM cand
        WHERE dp.id = cand.dp_id AND cand.n = 1
    """)
