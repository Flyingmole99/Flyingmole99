# Frontend – MSR-Planungstool

Build-freie Single-Page-App (Vanilla JS, HTML5 Drag & Drop) auf der REST-API
(`../backend/api`). Kein Node-Toolchain, keine `node_modules` – drei Dateien:

```
frontend/
├─ index.html   # Struktur (Palette, Anlage/Drop-Zone, Datenpunkttabelle)
├─ style.css    # Styling
└─ app.js       # Zustand + fetch gegen die API + Drag & Drop
```

## Nutzung

Das Backend liefert das Frontend **same-origin** unter `/app` aus (StaticFiles),
`/` leitet dorthin um. Also einfach das Backend starten:

```bash
cd ../backend
DATABASE_URL="host=/var/run/postgresql dbname=msr user=postgres" \
    uvicorn api.app:app
# Browser: http://127.0.0.1:8000/app/
```

Für einen separaten Dev-Server (z. B. Live-Reload) genügt ein statischer Server;
CORS ist im Backend offen. `FRONTEND_DIR` überschreibt den Auslieferpfad.

## Ablauf (Drag & Drop)

1. **Projekt** anlegen (Kopfzeile).
2. **Anlage** anlegen (Gewerk/Kürzel/Nummer) → BAS Block 1-2.
3. Baugruppe aus der **Palette** in die **Drop-Zone** ziehen (oder „+“) →
   Backend legt die Baugruppe an und **instanziiert die Datenpunkte**.
4. **Datenpunktliste** erscheint (Hardware/Software, Trend/Alarm); **Excel-
   Downloads** für Datenpunkt- und Kabelzugliste.

## Verifizierung

End-to-End mit Playwright/Chromium gegen das laufende Backend geprüft: Palette
lädt (58 Baugruppen), Projekt/Anlage angelegt, Gaskessel per Klick **und** per
echtem HTML5-Drag-&-Drop hinzugefügt → 45 Datenpunkte / 22 Hardware in der
Tabelle, Download-Links gesetzt.
