"""Dokument-Endpunkte: Datenpunktliste / Kabelzugliste als Excel-Download."""
from __future__ import annotations

import io

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from generators.cable_list.excel import export_cable_list
from generators.datapoint_list.excel import export_datapoint_list

from ..db import get_cursor

router = APIRouter(prefix="/anlagen/{anlage_id}/dokumente", tags=["dokumente"])

_XLSX = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"


def _anlage_bas(cur, anlage_id: int) -> str:
    cur.execute("SELECT bas FROM project.anlage WHERE id=%s", (anlage_id,))
    row = cur.fetchone()
    if row is None:
        raise HTTPException(404, "Anlage nicht gefunden")
    return row[0]


def _stream(buf: io.BytesIO, filename: str) -> StreamingResponse:
    buf.seek(0)
    return StreamingResponse(
        buf, media_type=_XLSX,
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@router.get("/datenpunktliste")
def datenpunktliste(anlage_id: int, cur=Depends(get_cursor)):
    bas = _anlage_bas(cur, anlage_id)
    buf = io.BytesIO()
    export_datapoint_list(cur, anlage_id, buf)
    return _stream(buf, f"Datenpunktliste_{bas}.xlsx")


@router.get("/kabelzugliste")
def kabelzugliste(anlage_id: int, cur=Depends(get_cursor)):
    bas = _anlage_bas(cur, anlage_id)
    buf = io.BytesIO()
    export_cable_list(cur, anlage_id, buf)
    return _stream(buf, f"Kabelzugliste_{bas}.xlsx")
