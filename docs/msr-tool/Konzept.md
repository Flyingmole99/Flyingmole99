# MSR-Planungstool – Konzept (Struktur, Datenbanken, Workflow)

> Status: Entwurf / Diskussionsgrundlage. **Noch kein Code.**
> Ziel: Anlagen aufbauen, Baugruppen/Regelorgane/Betriebsmittel per Drag & Drop
> zuordnen, zu Regelkreisen gruppieren und daraus automatisch
> **Datenpunktlisten, Regelschemen, Kabelzuglisten und Regelbeschreibungen**
> erzeugen. Bezeichnung nach **BACtwin (AMEV 1.2)**-Standard.

Bestätigte Rahmenbedingungen:
- **Plattform:** Web-App, mehrbenutzerfähig (zentrale DB, Browser-Client).
- **Exporte:** Excel (Datenpunkt-/Kabelzugliste), Word/PDF (Regelbeschreibung),
  SVG + DXF (Regelschema).
- **Bezeichnung:** BACtwin-Bibliothek (3 Referenz-Workbooks liegen vor und werden
  als Stammdaten importiert).

---

## 0. Leitgedanke: BACtwin *ist* die Bauteilbibliothek

Die zentrale Erkenntnis aus den drei BACtwin-Dateien: Der Standard liefert nicht
nur ein Namensschema, sondern eine **vollständige, vorlagengetriebene
Bauteilbibliothek**. Das Tool muss Bezeichnungen und Datenpunkte daher nicht
erfinden — es **importiert BACtwin als Stammdaten** und wird zum
**Zusammenstellungs-/Instanziierungswerkzeug** darüber.

Drei aufeinander aufbauende Ebenen aus den Dateien:

| Ebene | BACtwin-Quelle | Rolle im Tool |
|-------|----------------|---------------|
| **1. Adressstruktur (BAS/UAK)** | Bibliothek 1, Blatt „2 Gliederung" + „4 BACtwin-BAS" | Bezeichnungsschlüssel (8 Blöcke) + Kürzelvokabular |
| **2. Datenpunkt-Objekttypen** | Bibliothek 2, Blätter „8 / 8.1–8.14" | BACnet-Objektvorlagen (AI/AO/BI/BO/…) je Datenpunkt |
| **3. Aggregat-Templates** | Bibliothek 3, Blätter „10 AggregateTempl" / „18 BACtwinTab" | Baugruppen/Aggregate mit fertiger Datenpunktliste |

**Folge für die Automatik:** Eine Baugruppe auf die Anlage ziehen = ein
Aggregat-Template instanziieren. Jedes im Template referenzierte Datenpunkt-Objekt
wird sofort zu einem konkreten Datenpunkt mit vollständiger BAS-Adresse. Die
**Datenpunktliste ist damit nativ** — sie entsteht als Nebenprodukt der Zuordnung,
nicht durch nachgelagerte Logik.

---

## 1. Der BACtwin-Adressschlüssel (BAS/UAK)

8 Blöcke, Trennzeichen `_` (Ausnahme: `°` vor Teilanlage), Varianten
*ungekürzt* / *gekürzt* (einstellige Nummern, einstelliges Gewerk):

| # | Block | Inhalt | Beispiel | Vokabular (Quelle) |
|---|-------|--------|----------|--------------------|
| 1 | **Gewerk** | KG nach DIN 276 oder 1 Zeichen | `420` / `H` | 12 Gewerke (Bibl. 1, „3 Gewerke") |
| 2 | **Anlage** | Kürzel + Nr. | `VBA01` | 84 Kürzel |
| 2.1 | *Teilanlage (opt.)* | Nummer | `00` | — |
| 3 | **Baugruppe** | Kürzel + Nr. | `STH01` | 302 Kürzel |
| 4 | **Medium/Position** | Kürzel | `HZV` | 256 Kürzel |
| 5 | **Aggregat** | Kürzel + Nr. | `EF~01` | 248 Kürzel |
| 6 | **Betriebsmittel** | Kürzel + Nr. | `T~~01` | 309 Kürzel |
| 7 | **BM-Funktion** | Kürzel + Nr. | `MW~01` | 196 Kürzel |
| 8 | *Erweiterung (opt.)* | `EE`/`TL`/`ZP` | `TL` | 3 (Meldung/Aufz./Zeitplan) |

Vollbeispiel (ungekürzt): `420_VBA01_STH01_HZV_EF~01_T~~01_MW~01`
Mit Erweiterung: `…_MW~01_TL` · Mit Teilanlage: `420_VBA01°00_STH01_…`

Besonderheiten, die die Engine kennen muss:
- Platzhalterzeichen im Kürzel: `~` (Freistelle), `#####` (nicht belegtes
  Aggregat), `%%` (Medium-Präfix), `xx`/`nnn` (Nummern-Platzhalter).
- Feste Stellenpositionen je Variante (Blatt „2 Gliederung" definiert Stelle
  1–43); Prüfung gegen **MinCharStringLength** (Bibl. 3, Blatt 23).
- Laufnummern werden je Kontext (Anlage/Baugruppe/Aggregat) atomar vergeben.
- Bilinguales Vokabular (DE/EN) ist vorhanden → Sprache als Profileigenschaft.

### `NamingEngine`
Eigener Dienst: nimmt ein Objekt + seinen Elternpfad, liest die Kürzel aus den
Vokabeltabellen und setzt den Schlüssel gemäß Profil (Variante, Sprache,
Trennzeichen) zusammen. Ergebnis wird am Objekt gespeichert **und** bleibt über
einen Regel-Snapshot reproduzierbar. Andere Standards (VDI 3814, RDS-CX) wären
weitere Profile — die App-Logik bleibt gleich.

---

## 2. Import der BACtwin-Bibliothek (Seed-Pipeline)

Einmaliger/aktualisierbarer Import der drei Workbooks in die `catalog`-Tabellen.
Jeder Import ist **versioniert** (BACtwin-Version, z. B. „AMEV 1.2"), damit
Projekte an einen Bibliotheksstand gebunden bleiben.

| Workbook | Blätter | Ziel-Tabellen |
|----------|---------|---------------|
| Bibliothek 1 | `3 Gewerke`, `4 BACtwin-BAS` | `bac_gewerk`, `bac_vokabular` (je Block), `naming_profile` |
| Bibliothek 2 | `8 …`, `8.1–8.14` | `dp_objekttyp`, `dp_objekt_property` |
| Bibliothek 3 | `10 AggregateTempl`, `18 BACtwinTab` | `aggregat_template`, `aggregat_template_dp` |
| Bibliothek 3 | `15/16/17/24/25/26` u. a. | `funktionsbereich`, `zustaendigkeit`, `priority_array`, `meldeklasse`, `event_parameter` |

Jede Zeile trägt bereits eine **UUID** (BACtwin) → stabiler Primärschlüssel für
Nachimporte/Diffs. Der Importer meldet Abweichungen zum Vorstand (neue/geänderte
Templates), ohne bestehende Projekte automatisch zu verändern.

---

## 3. Fachliches Domänenmodell

```
Projekt
└─ Anlage                 (BAS Block 1–2, z.B. 420_VBA01)
   └─ Baugruppe           = instanziiertes Aggregat-Template (Block 3)
      ├─ Regelorgan       (Aggregat/BM, aktives Stellglied)
      └─ Betriebsmittel   (BM, Sensorik)          (Block 4–6)
         └─ Datenpunkt    = instanziiertes DP-Objekt (Block 7–8)

Regelkreis                (quer über Baugruppen gruppierbar, m:n)
   └─ Rolle je Element: Istwert | Sollwert | Stellglied | Meldung | Führung
```

- **Baugruppe** entsteht durch Ziehen eines `aggregat_template`; ihre Datenpunkte
  werden aus `aggregat_template_dp` materialisiert.
- **Regelorgan/Betriebsmittel** sind die Aggregat-/BM-Ebenen desselben Templates
  bzw. einzeln zuziehbare Aggregat-Templates (Fühler, 3-Wegeventil …).
- **Regelkreis** ist das gruppierende Objekt; die Rollen liefern die Struktur für
  Regelschema **und** Regelbeschreibung.

---

## 4. Datenbankstruktur

PostgreSQL, zwei Schemata: `catalog` (importierte BACtwin-Stammdaten, versioniert)
und `project` (Projektdaten).

### 4.1 `catalog` (aus BACtwin importiert)

| Tabelle | Zweck / Schlüsselspalten |
|---------|--------------------------|
| `bac_version` | Importstand. `id, bezeichnung, quelle, importiert_am` |
| `bac_gewerk` | DIN-276-Gewerke. `kg, kuerzel, kuerzel_1z, bezeichnung` |
| `bac_vokabular` | Kürzel je BAS-Block. `block(1–8), kuerzel, bezeichnung, beschreibung, sprache, version_id` |
| `naming_profile` | BAS-Profil. `id, name, variante, trennzeichen, segmente(jsonb)` |
| `dp_objekttyp` | BACnet-Objektvorlage. `uuid, kennung, object_type, bezeichnung, version_id` |
| `dp_objekt_property` | BACnet-Properties je Objekttyp. `objekttyp_uuid, property, units, min/max_pres, conformance, priority` |
| `aggregat_template` | Baugruppen/Aggregate. `uuid, typ, gewerk, kennung, bezeichnung, referenz_template` |
| `aggregat_template_dp` | DP-Zeilen je Template. `template_uuid, dp_objekttyp_uuid, bas_funktion, bas_muster, reihenfolge` |
| `funktionsbereich`, `zustaendigkeit`, `meldeklasse`, `priority_array`, `event_parameter` | Ergänzende BACtwin-Tabellen |

### 4.2 `project`

| Tabelle | Zweck / Schlüsselspalten |
|---------|--------------------------|
| `projekt` | `id, name, kunde, naming_profile_id, bac_version_id, status` |
| `anlage` | `id, projekt_id, gewerk_kg, anlage_kuerzel, nummer, teilanlage, bas` |
| `baugruppe` | Instanz. `id, anlage_id, aggregat_template_uuid, kuerzel, nummer, medium_pos, position(jsonb), bas` |
| `betriebsmittel` | `id, baugruppe_id, aggregat_template_uuid, kuerzel, nummer, bas` |
| `datenpunkt` | Materialisiert. `id, quelle_ref, dp_objekttyp_uuid, bas_funktion, bas(voll), adresse, units, prio` |
| `regelkreis` | `id, anlage_id, art, bezeichnung, bas` |
| `regelkreis_element` | m:n. `regelkreis_id, element_typ, element_id, rolle` |
| `kabel` | Für Kabelzugliste. `id, betriebsmittel_id, von, nach, kabeltyp, adern, querschnitt, laenge` |
| `dokument` | Exporte. `id, projekt_id, art, format, pfad, quelle_hash, erzeugt_am` |
| `audit_log` | `id, entity, entity_id, aktion, benutzer, zeit, diff(jsonb)` |

**Grundsatz:** `datenpunkt` ist eine **materialisierte** Instanz aus
`aggregat_template_dp` (+ projektindividuelle Adresse). Projekte bleiben stabil,
auch wenn ein neuer BACtwin-Stand importiert wird; „Bibliotheks-Update
übernehmen" ist ein bewusster, diff-basierter Schritt.

---

## 5. Repository-/Projektstruktur

```
msr-tool/
├─ docs/                         # dieses Konzept, ADRs, BACtwin-Mapping
├─ db/
│  ├─ migrations/                # catalog + project
│  └─ seed/                      # Ergebnis der Import-Pipeline (BACtwin)
├─ backend/
│  ├─ import/                    # BACtwin-Workbook-Importer (Bibl. 1–3)
│  ├─ domain/                    # Anlage, Baugruppe, Regelkreis, Datenpunkt
│  ├─ naming/                    # NamingEngine (BAS/UAK, Profile)
│  ├─ catalog/                   # Zugriff auf importierte Stammdaten
│  ├─ generators/                # ← Automatik (neutrales Zwischenmodell)
│  │  ├─ datapoint_list/         # → xlsx/csv
│  │  ├─ cable_list/             # → xlsx
│  │  ├─ control_scheme/         # → svg/dxf
│  │  └─ control_description/    # → docx/pdf
│  ├─ export/                    # Renderer (xlsx/docx/svg/dxf), austauschbar
│  └─ api/                       # REST/GraphQL
├─ frontend/
│  ├─ palette/                   # Katalog-Baugruppen (aus aggregat_template) zum Ziehen
│  ├─ canvas/                    # Anlagenbaum + Drag & Drop
│  ├─ inspector/                 # Eigenschaften/BAS-Kennung eines Objekts
│  └─ regelkreis/               # Gruppieren + Rollen zuweisen
└─ shared/                       # DTOs FE↔BE
```

---

## 6. Automatische Generierung

| Dokument | Quelle | Ableitung |
|----------|--------|-----------|
| **Datenpunktliste** | `datenpunkt` der Anlage | Direkt aus instanziierten Aggregat-Templates; Spalten = BACnet-Properties (Object_Name=BAS, Units, Min/Max, Conformance, Priority) → **quasi native BACtwin-Liste**. |
| **Kabelzugliste** | `kabel` + Betriebsmittel-Topologie | Pro Feldgerät Kabel Gerät→Schaltschrank/DDC; Kabeltyp/Querschnitt aus Vorlage; Länge optional. |
| **Regelschema** | `regelkreis` + Symbolbibliothek | Regelkreis-Elemente nach Rolle als Symbole platziert, über Medium/Anschlüsse verbunden → Graph → SVG/DXF. |
| **Regelbeschreibung** | `regelkreis.art` + Textbausteine | Passender Baustein, Platzhalter (Sollwerte, BAS-Kennungen, Gerätebezeichnungen) gefüllt → Fließtext. |

Jeder Generator schreibt zuerst ein neutrales Zwischenmodell; Renderer gießen es
ins Format. Jeder Export speichert `quelle_hash` → veraltete Exporte werden
erkannt und markiert (Konsistenzgarantie).

---

## 7. Workflow (Benutzer)

1. **Projekt anlegen** → BACtwin-Version + Profil (Variante/Sprache) wählen.
2. **Anlage anlegen** → Gewerk + Anlagenkürzel; BAS Block 1–2 vergeben.
3. **Baugruppen per Drag & Drop** aus der Palette (= Aggregat-Templates) auf die
   Anlage ziehen. Datenpunkte kommen automatisch aus dem Template mit.
4. **Regelorgane & Betriebsmittel** zuordnen (Fühler, 3-Wegeventil …).
5. **BAS-Kennung** wird live vergeben; im Inspector übersteuerbar
   (mit Kollisions- und Längenprüfung gegen MinCharStringLength).
6. **Regelkreise bilden**: Elemente markieren → gruppieren, Art wählen, Rollen
   zuweisen (Istwert/Sollwert/Stellglied/Meldung).
7. **Validierung**: fehlende Rollen, offene Anschlüsse, doppelte/zu lange BAS,
   Datenpunkte ohne Adresse.
8. **Generieren**: vier Dokumente auf Knopfdruck; Vorschau; Export.
9. **Versionieren/Freigeben**: Stand einfrieren; Exporte an `quelle_hash` binden.

---

## 8. Technologie-Stack (Vorschlag)

| Schicht | Vorschlag | Begründung |
|---------|-----------|------------|
| DB | PostgreSQL (jsonb für Segmente/Properties) | relational + flexibel |
| Backend | Python (FastAPI) | reiche Libs: openpyxl (BACtwin-Import), xlsx/docx, ezdxf |
| Import | openpyxl | liest die BACtwin-Workbooks direkt |
| Frontend | React + SVG/Canvas-DnD | performantes Drag & Drop + Schema-Rendering |
| Export | openpyxl/xlsxwriter, python-docx, svg + ezdxf (DXF) | formatstabil |

---

## 9. Nächste Schritte

1. **Import-Pipeline** für die 3 Workbooks spezifizieren (Spalten-Mapping je Blatt
   → `catalog`-Tabellen). Grundlage liegt vor (Blattstruktur ist analysiert).
2. **Ein Aggregat-Template durchspielen** (z. B. Gaskessel/`AGG_…`): welche
   Datenpunkte, welche BAS-Kennungen, welche Klemmen → Referenz für Kabelliste.
3. **ER-Diagramm** finalisieren, dann Migrationen für `catalog` + `project`.
4. **Symbolbibliothek + Textbausteine** je Regelkreis-Art definieren (die einzigen
   Inhalte, die BACtwin *nicht* liefert — für Schema und Regelbeschreibung).
```
