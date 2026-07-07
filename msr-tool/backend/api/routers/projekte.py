"""Projekt-/Anlage-/Baugruppe-Endpunkte inkl. Drag-&-Drop-Instanziierung."""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from domain.instantiate import instantiate_baugruppe
from naming.engine import NamingEngine, default_baugruppe_kuerzel

from ..db import get_cursor
from ..schemas import AnlageCreate, BaugruppeCreate, ProjektCreate

router = APIRouter(tags=["projekte"])


def _variante(cur, projekt_id: int) -> str:
    cur.execute("""SELECT p.variante FROM catalog.naming_profile p
                   JOIN project.projekt pr ON pr.naming_profile_id = p.id
                   WHERE pr.id = %s""", (projekt_id,))
    row = cur.fetchone()
    return row[0] if row else "ungekuerzt"


# ---------------------------------------------------------------- Projekte
@router.post("/projekte", status_code=201)
def create_projekt(body: ProjektCreate, cur=Depends(get_cursor)):
    profile_id = body.naming_profile_id
    if profile_id is None:
        cur.execute("SELECT id FROM catalog.naming_profile WHERE variante='ungekuerzt' ORDER BY id LIMIT 1")
        row = cur.fetchone()
        if row is None:
            raise HTTPException(400, "Kein Namensprofil vorhanden – Katalog importieren")
        profile_id = row[0]
    version_id = body.bac_version_id
    if version_id is None:
        cur.execute("SELECT id FROM catalog.bac_version ORDER BY id DESC LIMIT 1")
        row = cur.fetchone()
        if row is None:
            raise HTTPException(400, "Keine BACtwin-Version vorhanden – Katalog importieren")
        version_id = row[0]
    cur.execute("""INSERT INTO project.projekt(name, kunde, naming_profile_id, bac_version_id)
                   VALUES (%s,%s,%s,%s) RETURNING id, status""",
                (body.name, body.kunde, profile_id, version_id))
    pid, status = cur.fetchone()
    return {"id": pid, "name": body.name, "status": status,
            "naming_profile_id": profile_id, "bac_version_id": version_id}


@router.get("/projekte")
def list_projekte(cur=Depends(get_cursor)):
    cur.execute("SELECT id, name, kunde, status FROM project.projekt ORDER BY id DESC")
    return [{"id": i, "name": n, "kunde": k, "status": s} for i, n, k, s in cur.fetchall()]


@router.get("/projekte/{projekt_id}")
def get_projekt(projekt_id: int, cur=Depends(get_cursor)):
    cur.execute("SELECT id, name, kunde, status FROM project.projekt WHERE id=%s", (projekt_id,))
    row = cur.fetchone()
    if row is None:
        raise HTTPException(404, "Projekt nicht gefunden")
    cur.execute("SELECT id, bas, gewerk_kg, anlage_kuerzel, nummer FROM project.anlage WHERE projekt_id=%s ORDER BY id",
                (projekt_id,))
    anlagen = [{"id": i, "bas": b, "gewerk_kg": g, "kuerzel": k, "nummer": n}
               for i, b, g, k, n in cur.fetchall()]
    return {"id": row[0], "name": row[1], "kunde": row[2], "status": row[3], "anlagen": anlagen}


# ---------------------------------------------------------------- Anlagen
@router.post("/projekte/{projekt_id}/anlagen", status_code=201)
def create_anlage(projekt_id: int, body: AnlageCreate, cur=Depends(get_cursor)):
    variante = _variante(cur, projekt_id)
    eng = NamingEngine(variante=variante)
    bas = eng.anlage_bas(body.gewerk_kg, body.anlage_kuerzel, body.nummer, body.teilanlage)
    try:
        cur.execute("""INSERT INTO project.anlage(projekt_id, gewerk_kg, anlage_kuerzel, nummer, teilanlage, bas)
                       VALUES (%s,%s,%s,%s,%s,%s) RETURNING id""",
                    (projekt_id, body.gewerk_kg, body.anlage_kuerzel, body.nummer, body.teilanlage, bas))
    except Exception as exc:  # z. B. UNIQUE (projekt_id, bas)
        raise HTTPException(409, f"Anlage {bas} existiert bereits") from exc
    return {"id": cur.fetchone()[0], "bas": bas}


@router.get("/anlagen/{anlage_id}")
def get_anlage(anlage_id: int, cur=Depends(get_cursor)):
    cur.execute("SELECT id, projekt_id, bas FROM project.anlage WHERE id=%s", (anlage_id,))
    row = cur.fetchone()
    if row is None:
        raise HTTPException(404, "Anlage nicht gefunden")
    cur.execute("""SELECT b.id, b.bas, b.kuerzel, b.nummer, t.kennung, t.bezeichnung_de,
                          (SELECT count(*) FROM project.datenpunkt d
                             WHERE d.quelle_typ='baugruppe' AND d.quelle_id=b.id) AS dp
                   FROM project.baugruppe b
                   JOIN catalog.aggregat_template t ON t.uuid=b.aggregat_template_uuid
                   WHERE b.anlage_id=%s ORDER BY b.id""", (anlage_id,))
    bg = [{"id": i, "bas": b, "kuerzel": k, "nummer": n, "template": ken,
           "bezeichnung": bez, "datenpunkte": dp} for i, b, k, n, ken, bez, dp in cur.fetchall()]
    return {"id": row[0], "projekt_id": row[1], "bas": row[2], "baugruppen": bg}


# ---------------------------------------------------------------- Baugruppen (Drag & Drop)
@router.post("/anlagen/{anlage_id}/baugruppen", status_code=201)
def add_baugruppe(anlage_id: int, body: BaugruppeCreate, cur=Depends(get_cursor)):
    cur.execute("SELECT projekt_id, bas FROM project.anlage WHERE id=%s", (anlage_id,))
    row = cur.fetchone()
    if row is None:
        raise HTTPException(404, "Anlage nicht gefunden")
    projekt_id, anlage_bas = row

    cur.execute("SELECT kennung, typ FROM catalog.aggregat_template WHERE uuid=%s",
                (body.aggregat_template_uuid,))
    tmpl = cur.fetchone()
    if tmpl is None:
        raise HTTPException(404, "Aggregat-Template nicht gefunden")
    kennung = tmpl[0]

    variante = _variante(cur, projekt_id)
    eng = NamingEngine(variante=variante)
    kuerzel = body.kuerzel or default_baugruppe_kuerzel(kennung)
    nummer = body.nummer
    if nummer is None:
        cur.execute("""SELECT COALESCE(max(nummer),0)+1 FROM project.baugruppe
                       WHERE anlage_id=%s AND kuerzel=%s""", (anlage_id, kuerzel))
        nummer = cur.fetchone()[0]
    bas = eng.baugruppe_bas(anlage_bas, kuerzel, nummer)

    try:
        cur.execute("""INSERT INTO project.baugruppe
                          (anlage_id, aggregat_template_uuid, kuerzel, nummer, medium_pos, position, bas)
                       VALUES (%s,%s,%s,%s,%s,%s,%s) RETURNING id""",
                    (anlage_id, body.aggregat_template_uuid, kuerzel, nummer,
                     body.medium_pos, _json(body.position), bas))
    except Exception as exc:
        raise HTTPException(409, f"Baugruppe {bas} existiert bereits") from exc
    baugruppe_id = cur.fetchone()[0]

    stats = instantiate_baugruppe(cur, baugruppe_id, variante=variante)
    return {"id": baugruppe_id, "bas": bas, "kuerzel": kuerzel, "nummer": nummer,
            "template": kennung, "instanziierung": stats}


@router.delete("/baugruppen/{baugruppe_id}", status_code=204)
def delete_baugruppe(baugruppe_id: int, cur=Depends(get_cursor)):
    cur.execute("DELETE FROM project.baugruppe WHERE id=%s", (baugruppe_id,))
    if cur.rowcount == 0:
        raise HTTPException(404, "Baugruppe nicht gefunden")


@router.get("/anlagen/{anlage_id}/datenpunkte")
def list_datenpunkte(anlage_id: int, cur=Depends(get_cursor)):
    cur.execute("""SELECT d.bas, o.object_type, o.bezeichnung_de, d.units,
                          o.ist_hardware, d.trend, d.alarm
                   FROM project.datenpunkt d
                   JOIN catalog.dp_objekttyp o ON o.uuid=d.dp_objekttyp_uuid
                   WHERE d.anlage_id=%s ORDER BY d.bas""", (anlage_id,))
    return [{"bas": b, "object_type": ot, "bezeichnung": bez, "units": u,
             "hardware": hw, "trend": tr, "alarm": al}
            for b, ot, bez, u, hw, tr, al in cur.fetchall()]


def _json(value):
    from psycopg2.extras import Json
    return Json(value) if value is not None else None
