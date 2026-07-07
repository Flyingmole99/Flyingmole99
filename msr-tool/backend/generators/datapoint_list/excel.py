"""Generator: Datenpunktliste einer Anlage als Excel (.xlsx)."""
from __future__ import annotations

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill

_QUERY = """
SELECT d.bas, o.object_type, o.kennung, o.bezeichnung_de,
       d.units, d.min_pres, d.max_pres, o.ist_hardware, d.trend, d.alarm, d.adresse
FROM project.datenpunkt d
JOIN catalog.dp_objekttyp o ON o.uuid = d.dp_objekttyp_uuid
WHERE d.anlage_id = %s
ORDER BY d.bas
"""

_HEADERS = [
    ("Datenpunkt (BAS)", 42), ("Objekttyp", 10), ("Objekt-Kennung", 22),
    ("Beschreibung", 34), ("Einheit", 9), ("Min", 8), ("Max", 8),
    ("Art", 10), ("Trend", 7), ("Alarm", 7), ("Adresse", 14),
]


def export_datapoint_list(cur, anlage_id: int, path: str) -> int:
    """Schreibt die Datenpunktliste der Anlage nach `path`. Rückgabe: Zeilenzahl."""
    cur.execute("SELECT bas FROM project.anlage WHERE id = %s", (anlage_id,))
    row = cur.fetchone()
    anlage_bas = row[0] if row else str(anlage_id)

    cur.execute(_QUERY, (anlage_id,))
    rows = cur.fetchall()

    wb = Workbook()
    ws = wb.active
    ws.title = "Datenpunktliste"

    header_fill = PatternFill("solid", fgColor="1F4E78")
    header_font = Font(bold=True, color="FFFFFF")
    for col, (title, width) in enumerate(_HEADERS, start=1):
        c = ws.cell(row=1, column=col, value=title)
        c.fill = header_fill
        c.font = header_font
        c.alignment = Alignment(vertical="center", wrap_text=True)
        ws.column_dimensions[c.column_letter].width = width

    for r, (bas, otype, kennung, bez, units, mn, mx, is_hw, trend, alarm, adr) in enumerate(rows, start=2):
        ws.cell(row=r, column=1, value=bas)
        ws.cell(row=r, column=2, value=otype)
        ws.cell(row=r, column=3, value=kennung)
        ws.cell(row=r, column=4, value=bez)
        ws.cell(row=r, column=5, value=units)
        ws.cell(row=r, column=6, value=float(mn) if mn is not None else None)
        ws.cell(row=r, column=7, value=float(mx) if mx is not None else None)
        ws.cell(row=r, column=8, value="Hardware" if is_hw else "Software")
        ws.cell(row=r, column=9, value="X" if trend else "")
        ws.cell(row=r, column=10, value="X" if alarm else "")
        ws.cell(row=r, column=11, value=adr)

    ws.freeze_panes = "A2"
    ws.auto_filter.ref = f"A1:{ws.cell(row=1, column=len(_HEADERS)).column_letter}{len(rows) + 1}"

    # Kopfzeile mit Anlagenbezug als Blattname-Zusatz (Titelzeile im Dokument-Namen)
    wb.properties.title = f"Datenpunktliste {anlage_bas}"
    wb.save(path)
    return len(rows)
