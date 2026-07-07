"""Katalog-Endpunkte (read-only) – u. a. die Drag-&-Drop-Palette."""
from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from ..db import get_cursor

router = APIRouter(prefix="/catalog", tags=["catalog"])


@router.get("/versions")
def versions(cur=Depends(get_cursor)):
    cur.execute("SELECT id, bezeichnung, importiert_am FROM catalog.bac_version ORDER BY id DESC")
    return [{"id": i, "bezeichnung": b, "importiert_am": t} for i, b, t in cur.fetchall()]


@router.get("/naming-profiles")
def naming_profiles(cur=Depends(get_cursor)):
    cur.execute("SELECT id, name, variante, sprache FROM catalog.naming_profile ORDER BY id")
    return [{"id": i, "name": n, "variante": v, "sprache": s} for i, n, v, s in cur.fetchall()]


@router.get("/gewerke")
def gewerke(cur=Depends(get_cursor)):
    cur.execute("""SELECT kg, kuerzel, kuerzel_1z, bezeichnung_de
                   FROM catalog.bac_gewerk WHERE status='aktiv' ORDER BY kg""")
    return [{"kg": kg, "kuerzel": k, "kuerzel_1z": k1, "bezeichnung": b}
            for kg, k, k1, b in cur.fetchall()]


@router.get("/aggregate-templates")
def aggregate_templates(
    typ: str | None = Query(None, description="Aggregat | Baugruppe | Anlage"),
    gewerk: str | None = Query(None),
    q: str | None = Query(None, description="Suche in Kennung/Bezeichnung"),
    limit: int = Query(200, le=1000),
    cur=Depends(get_cursor),
):
    """Palette der ziehbaren Bauteile."""
    sql = ["SELECT uuid, typ, gewerk_kg, kennung, bezeichnung_de",
           "FROM catalog.aggregat_template WHERE status='aktiv'"]
    args: list = []
    if typ:
        sql.append("AND typ = %s"); args.append(typ)
    if gewerk:
        sql.append("AND gewerk_kg = %s"); args.append(gewerk)
    if q:
        sql.append("AND (kennung ILIKE %s OR bezeichnung_de ILIKE %s)")
        args += [f"%{q}%", f"%{q}%"]
    sql.append("ORDER BY kennung LIMIT %s"); args.append(limit)
    cur.execute(" ".join(sql), args)
    return [{"uuid": str(u), "typ": t, "gewerk_kg": g, "kennung": k, "bezeichnung": b}
            for u, t, g, k, b in cur.fetchall()]
