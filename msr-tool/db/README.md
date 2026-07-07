# Datenbank – Migrationen

PostgreSQL-Schema des MSR-Planungstools. Umsetzung des ER-Modells aus
`/docs/msr-tool/ER-Modell.md`. Zwei Schemata:

- **`catalog`** – importierte, versionierte BACtwin-Stammdaten (read-mostly).
- **`project`** – projektspezifische Planungsdaten, referenziert `catalog` per UUID.

## Migrationen

Nummerierte, in **einer Transaktion** gekapselte SQL-Dateien. Anwendung strikt in
numerischer Reihenfolge, jede Datei **genau einmal**:

| Datei | Inhalt |
|-------|--------|
| `0001_catalog.sql` | Schema `catalog` + BACtwin-Stammdatentabellen |
| `0002_catalog_pflegedaten.sql` | Kabeltyp/Klemmen, Schema-Symbole, Textbausteine (nicht-BACtwin) |
| `0003_project.sql` | Schema `project` + Planungsdaten, Trigger, Audit |

## Anwenden

Voraussetzung: PostgreSQL ≥ 14 (getestet mit 16).

```bash
createdb msr
for f in db/migrations/0001_catalog.sql \
         db/migrations/0002_catalog_pflegedaten.sql \
         db/migrations/0003_project.sql; do
  psql -d msr -v ON_ERROR_STOP=1 -f "$f"
done
```

Ein dedizierter Runner (Alembic o. Ä.) ist noch nicht nötig – die Dateien laufen
mit reinem `psql`. Sobald das Backend steht, kann Alembic diese SQL-Schritte per
`op.execute()` übernehmen oder ablösen.

## Konventionen

- **Surrogatschlüssel** `bigint GENERATED ALWAYS AS IDENTITY` für projekt-/
  hilfstabellen; **UUID** als PK dort, wo BACtwin stabile UUIDs liefert
  (`dp_objekttyp`, `aggregat_template`).
- **Versionierung:** Stammdatenzeilen tragen `version_id` → `catalog.bac_version`.
  Reimport = Upsert per UUID (`INSERT … ON CONFLICT`), entfallene Zeilen werden
  `status = 'veraltet'` (Soft-Delete), nie gelöscht → Altprojekte bleiben gültig.
- **Kategorische Felder** als `text` + `CHECK` (leicht per Migration erweiterbar)
  statt `ENUM`.
- **`updated_at`** wird per Trigger `project.set_updated_at()` gepflegt.
- **Polymorphe Referenzen** (`datenpunkt.quelle_*`, `regelkreis_element.element_*`)
  haben bewusst keinen FK; Konsistenz sichert die App-Logik.

## Validierungsstand

Alle drei Migrationen wurden gegen PostgreSQL 16 angewandt und mit einem
Smoke-Test (Minimal-Gaskessel) geprüft:

- Datenpunktliste-, Kabelzuglisten- und rekursive Template-Query liefern korrekt.
- Guards feuern wie erwartet: `chk_template_dp_ref`, `chk_symbol_bezug`,
  `UNIQUE (anlage_id, bas)`, `dokument.format`-CHECK.
- `updated_at`-Trigger aktualisiert bei UPDATE.

## Offen (nächste Schritte)

- Seed der BACtwin-Bibliothek über die Import-Pipeline (`backend/import/`,
  s. `/docs/msr-tool/Import-Pipeline.md`).
- `naming_profile.segmente` mit den vier BAS-Profilen (Blatt „2 Gliederung") füllen.
- Vergabestrategie für `datenpunkt.adresse` (DDC-Kanal/BACnet-Instanz) festlegen.
