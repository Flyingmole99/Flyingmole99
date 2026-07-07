# Backend – Importer, Instanziierung & Generatoren

Datenfluss: **BACtwin-Workbooks → `catalog` (Import) → `project` (Instanziierung)
→ Dokumente (Generatoren)**. Siehe `../db/` und `/docs/msr-tool/`.

## Module

| Modul | Aufgabe |
|-------|---------|
| `importer/` | liest die 3 Workbooks in `catalog` (s. u.) |
| `naming/` | `NamingEngine` – komponiert den vollständigen BAS-Schlüssel eines Datenpunkts (Block 1-3 aus Kontext, Block 4-8 aus dem relativen Template-Muster) |
| `domain/` | `instantiate_baugruppe` – expandiert ein Aggregat-Template rekursiv und materialisiert die Datenpunkte einer Baugruppe nach `project.datenpunkt` |
| `generators/datapoint_list/` | Datenpunktliste einer Anlage als Excel (`.xlsx`) |

### Instanziierung (Folding-Policy v1)

`instantiate_baugruppe` expandiert das Template rekursiv und faltet gemäß
`/docs/msr-tool/Beispiel-Gaskessel.md` §3:

- `SV` (Structured-View-Container) → übersprungen (kein Datenpunkt).
- `TL` (Trend) → auf den Basispunkt gefaltet (`trend=true`, Suffix `_TL`).
- `EE` (Ereignis) → gefaltet (`alarm=true`), falls Basispunkt existiert; sonst
  eigener Datenpunkt.
- Gleicher BAS über verschiedene Objekttypen (`BI_HD`/`MI_HD` = alternative
  Varianten) → erste gewinnt, BAS bleibt eindeutig (BACnet-Object_Name).

**Verifiziert:** Der Gaskessel `BGP_KES_nM_AMEV1` ergibt aus 76 Objekten
**45 Datenpunkte** (6 Container, 4 Varianten-Dubletten, 17 Trend gefaltet,
4 Alarm), davon **22 Hardware-I/O** – mit vollständig komponierten, je Anlage
eindeutigen BAS-Bezeichnungen.

## Importer

Liest die drei BACtwin-Bibliotheks-Workbooks in das `catalog`-Schema
(siehe `/docs/msr-tool/Import-Pipeline.md`).

> Das Verzeichnis heißt `importer/` (nicht `import/` wie im Doku-Entwurf), weil
> `import` in Python ein reserviertes Wort ist.

## Aufbau

```
backend/
├─ requirements.txt
├─ importer/
│  ├─ mapping/               # deklarative Spalten-Mappings (YAML, "Daten statt Code")
│  │  ├─ bibliothek1.yaml    #   Gewerke, BAS-Vokabular, Namensprofile
│  │  ├─ bibliothek2.yaml    #   Objekttypen + BACnet-Properties
│  │  └─ bibliothek3.yaml    #   Aggregat-Templates, Meldeklasse, Priority-Array
│  ├─ workbook.py            # openpyxl-/YAML-Helfer
│  ├─ transforms.py          # reine Transformationen (ist_hardware, bas_relativ, …)
│  ├─ parsers.py             # Blatt -> Domänen-Dicts
│  ├─ loaders.py             # Upsert je Zieltabelle (psycopg2) + Referenzauflösung
│  ├─ validate.py            # Kennzahlen + rekursive Template-Auflösung
│  └─ run_import.py          # CLI-Orchestrierung
└─ tests/
   ├─ test_transforms.py     # Unit-Tests (ohne DB/Dateien)
   └─ test_import_live.py    # Integrationstest (nur mit BACTWIN_DIR + DATABASE_URL)
```

## Installation

```bash
pip install -r requirements.txt
```

## Ausführen

Voraussetzung: eine PostgreSQL-DB mit angewandten Migrationen (`../db/`).

```bash
python -m importer.run_import \
    --dir  /pfad/zu/den/3/workbooks \
    --dsn  "host=/var/run/postgresql dbname=msr user=postgres" \
    --version "AMEV 1.2"
```

Der Import ist **idempotent** (Upsert je Naturschlüssel/UUID) und läuft in einer
Transaktion. Am Ende wird ein Kennzahlen-Report ausgegeben.

## Tests

```bash
cd backend
python -m pytest                      # nur Unit-Tests
BACTWIN_DIR=/pfad/wb DATABASE_URL="host=… dbname=msr user=postgres" \
  python -m pytest                    # inkl. Live-Integrationstest
```

## Validierungsstand (gegen die echten Bibliotheken, PostgreSQL 16)

| Kennzahl | Wert |
|----------|------|
| Gewerke | 12 |
| BAS-Vokabular (Kürzel) | 1093 |
| Objekttypen | 336 (davon 109 Hardware) |
| Objekt-Properties | 336 |
| Aggregat-Templates | 183 (6 Dubletten dedupliziert) |
| Template-Zeilen | 1639 |
| **Unaufgelöste Referenzen** | **0** |

**Akzeptanztest:** Der Gaskessel `BGP_KES_nM_AMEV1` expandiert rekursiv auf
**76 Datenpunkte / 22 Hardware-I/O** – exakt die im Referenzbeispiel
(`/docs/msr-tool/Beispiel-Gaskessel.md`) manuell ermittelten Werte.

### Bekannte Datenquirks (vom Importer robust behandelt)

- **6 doppelte Template-Kennungen** (Redefinitionen mit zweiter UUID): erste
  gewinnt, DP-Zeilen der Dublette werden übersprungen.
- **Referenz ohne Versionssuffix** (`ref = "…_AMEV1"`, Objekt = `"…_AMEV1.2"`):
  eindeutiger Fallback über das Präfix vor dem ersten Punkt löst auf; nur bei
  Eindeutigkeit, sonst bleibt die Referenz offen und die Validierung meldet sie.

## Noch nicht importiert (nächste Ausbaustufe)

`funktionsbereich`, `zustaendigkeit`, `min_char_length`, `event_parameter`,
`betreibervorgabe` – Mapping ist in der Import-Pipeline dokumentiert, aber für den
Gaskessel-Pfad nicht erforderlich.
