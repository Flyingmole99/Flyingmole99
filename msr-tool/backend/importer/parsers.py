"""Parser je Blatt-Typ: liefern Domänen-Dicts, bereit für die Loader."""
from __future__ import annotations

from . import transforms as T
from .workbook import cell, sheet_rows


def parse_gewerke(path: str, spec: dict) -> list[dict]:
    rows = sheet_rows(path, spec["name"])
    c = spec["cols"]
    out = []
    for row in rows[spec["data_start"]:]:
        kg = T.clean(cell(row, c["kg"]))
        kuerzel = T.clean(cell(row, c["kuerzel"]))
        if not kg or not kuerzel or not kg.isdigit():
            continue
        out.append({
            "kg": kg,
            "kuerzel": kuerzel,
            "kuerzel_1z": T.clean(cell(row, c["kuerzel_1z"])),
            "bezeichnung_de": T.clean(cell(row, c["bezeichnung_de"])),
            "kuerzel_en": T.clean(cell(row, c["kuerzel_en"])),
            "kuerzel_1z_en": T.clean(cell(row, c["kuerzel_1z_en"])),
            "bezeichnung_en": T.clean(cell(row, c["bezeichnung_en"])),
        })
    return out


def parse_vokabular(path: str, spec: dict) -> list[dict]:
    rows = sheet_rows(path, spec["name"])
    out = []
    seen = set()
    for row in rows[spec["data_start"]:]:
        for block_str, (k_col, b_col, d_col) in spec["blocks"].items():
            block = int(block_str)
            kuerzel = T.clean(cell(row, k_col))
            if not kuerzel or kuerzel.isdigit():
                continue
            # zu lange Zellen sind i. d. R. Überschriften/Beschreibungen, kein Kürzel
            if len(kuerzel) > 6:
                continue
            key = (block, kuerzel)
            if key in seen:
                continue
            seen.add(key)
            out.append({
                "block": block,
                "kuerzel": kuerzel,
                "bezeichnung": T.clean(cell(row, b_col)),
                "beschreibung": T.clean(cell(row, d_col)) if d_col is not None else None,
            })
    return out


def parse_objekttypen(path: str, spec_de: dict, spec_en: dict) -> list[dict]:
    rows_de = sheet_rows(path, spec_de["name"])
    rows_en = sheet_rows(path, spec_en["name"])
    cde, cen = spec_de["cols"], spec_en["cols"]

    en_by_uuid = {}
    for row in rows_en[spec_en["data_start"]:]:
        u = T.clean(cell(row, cen["uuid"]))
        if u:
            en_by_uuid[u] = T.clean(cell(row, cen["bezeichnung"]))

    out = []
    for row in rows_de[spec_de["data_start"]:]:
        uuid = T.clean(cell(row, cde["uuid"]))
        kennung = T.clean(cell(row, cde["kennung"]))
        object_type = T.clean(cell(row, cde["object_type"]))
        if not uuid or not kennung or not object_type:
            continue
        out.append({
            "uuid": uuid,
            "obj_sort": T.clean(cell(row, cde["obj_sort"])),
            "kennung": kennung,
            "object_type": object_type,
            "bezeichnung_de": T.clean(cell(row, cde["bezeichnung"])),
            "bezeichnung_en": en_by_uuid.get(uuid),
            "ist_hardware": T.ist_hardware(object_type),
            "ist_erweiterung": T.ist_erweiterung(object_type),
        })
    return out


def parse_properties(path: str, spec: dict, meldeklasse_ids: set[str]) -> list[dict]:
    """Liest die 8.x-Detailblätter; Spalten per Header-Name. Eine Zeile je Kennung
    (erste Fundstelle gewinnt), damit die 1:1-Property-Tabelle eindeutig bleibt."""
    by_name = spec["by_name"]
    numeric = set(spec["numeric"])
    kennung_col = spec["kennung_col"]
    header_row = spec["header_row"]

    result: dict[str, dict] = {}
    for sheet in spec["names"]:
        rows = sheet_rows(path, sheet)
        if not rows:
            continue
        header = {T.clean(v): i for i, v in enumerate(rows[header_row]) if T.clean(v)}
        idx = {field: header.get(col) for field, col in by_name.items()}
        for row in rows[header_row + 1:]:
            kennung = T.clean(cell(row, kennung_col))
            if not T.is_data_kennung(kennung) or kennung in result:
                continue
            rec = {"kennung": kennung}
            for field, col in idx.items():
                if col is None:
                    rec[field] = None
                    continue
                raw = cell(row, col)
                if field in numeric:
                    rec[field] = T.to_number(raw)
                elif field == "notification_class":
                    nc = T.normalize_notification_class(raw)
                    rec[field] = nc if nc in meldeklasse_ids else None
                else:
                    rec[field] = T.clean(raw)
            result[kennung] = rec
    return list(result.values())


def parse_meldeklasse(path: str, spec: dict) -> list[dict]:
    rows = sheet_rows(path, spec["name"])
    c = spec["cols"]
    out = []
    for row in rows[spec["data_start"]:]:
        oid = T.clean(cell(row, c["object_identifier"]))
        if not oid:
            continue
        out.append({
            "object_identifier": oid,
            "bezeichnung_de": T.clean(cell(row, c["bezeichnung_de"])) or oid,
            "bezeichnung_en": T.clean(cell(row, c["bezeichnung_en"])),
            "priority": T.clean(cell(row, c["priority"])),
            "ack_required": T.clean(cell(row, c["ack_required"])),
        })
    return out


def parse_priority_array(path: str, spec: dict) -> list[dict]:
    rows = sheet_rows(path, spec["name"])
    c = spec["cols"]
    out = []
    seen = set()
    for row in rows[spec["data_start"]:]:
        p = T.clean(cell(row, c["prio"]))
        if not p or not p.isdigit():
            continue
        prio = int(p)
        if prio in seen or not (1 <= prio <= 16):
            continue
        seen.add(prio)
        out.append({
            "prio": prio,
            "verwendung": T.clean(cell(row, c["verwendung"])),
            "empfehlung": T.clean(cell(row, c["empfehlung"])),
            "beschreibung": T.clean(cell(row, c["beschreibung"])),
        })
    return out


def parse_aggregate(path: str, spec: dict) -> tuple[list[dict], list[dict], list[dict]]:
    """Trennt Kopfzeilen (Templates) von DP-/Referenz-Zeilen anhand belegter Spalten.

    Kennungen sind eindeutig (Referenzauflösung erfolgt darüber). Taucht eine
    Kennung mit zweiter UUID auf (Redefinition), gewinnt die erste; die DP-Zeilen
    der Dublette werden übersprungen. Rückgabe: (templates, dp_rows, dropped)."""
    rows = sheet_rows(path, spec["name"])
    c = spec["cols"]
    blocks = spec["bas_blocks"]

    templates: list[dict] = []
    dp_rows: list[dict] = []
    dropped: list[dict] = []
    seen_kennung: dict[str, str] = {}
    current_uuid: str | None = None
    skip_current = False

    for row in rows[spec["data_start"]:]:
        uuid = T.clean(cell(row, c["uuid"]))
        kennung = T.clean(cell(row, c["kennung"]))
        ref = T.clean(cell(row, c["ref"]))

        if uuid and kennung and not ref:
            # Template-Kopfzeile
            if kennung in seen_kennung:
                skip_current = True
                dropped.append({"kennung": kennung, "uuid": uuid})
                continue
            seen_kennung[kennung] = uuid
            skip_current = False
            current_uuid = uuid
            templates.append({
                "uuid": uuid,
                "typ": T.clean(cell(row, c["typ"])) or "Aggregat",
                "gewerk_kg": T.clean(cell(row, c["gewerk"])),
                "kennung": kennung,
                "bezeichnung_de": T.clean(cell(row, c["bezeichnung"])),
            })
        elif ref and current_uuid and not skip_current:
            # DP- oder Unter-Aggregat-Zeile
            desc = " ".join(filter(None, [
                T.clean(cell(row, c["desc1"])), T.clean(cell(row, c["desc2"]))]))
            dp_rows.append({
                "template_uuid": current_uuid,
                "reihenfolge": len(dp_rows),
                "referenz_kennung": ref,
                "ist_unteraggregat": T.ist_unteraggregat(ref),
                "variante": T.clean(cell(row, c["variante"])),
                "beschreibung": desc or None,
                "bas_relativ": T.bas_relativ(lambda i: cell(row, i), blocks),
                "object_name_beispiel": T.clean(cell(row, c["object_name_bsp"])),
            })
    return templates, dp_rows, dropped
