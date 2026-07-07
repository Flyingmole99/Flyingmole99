# MSR-Planungstool – Konzept (Struktur, Datenbanken, Workflow)

> Status: Entwurf / Diskussionsgrundlage. **Noch kein Code.**
> Ziel: Anlagen aufbauen, Baugruppen/Regelorgane/Betriebsmittel per Drag & Drop
> zuordnen, zu Regelkreisen gruppieren und daraus automatisch
> **Datenpunktlisten, Regelschemen, Kabelzuglisten und Regelbeschreibungen**
> erzeugen. Bezeichnung nach **BACtwin**-Standard.

---

## 0. Getroffene Annahmen (bitte bestätigen/korrigieren)

Diese drei Punkte prägen die Architektur. Ich habe pragmatische Defaults gewählt
und den Entwurf so gebaut, dass ein Wechsel jeweils nur ein Modul betrifft:

| # | Thema | Angenommener Default | Warum austauschbar |
|---|-------|----------------------|--------------------|
| A | **BACtwin-Bezeichnung** | Generisches, konfigurierbares Segment-Schema (`NamingEngine`), das dem BACtwin-AKS nachgebildet ist. Exakte Kürzellisten/Trennzeichen später einpflegbar. | Bezeichnungslogik ist als eigener Dienst gekapselt; Rest der App kennt nur „gib mir den Schlüssel für Objekt X". |
| B | **Zielplattform** | **Web-App, mehrbenutzerfähig** (zentrale PostgreSQL, Browser-Client). | Datenmodell & Generatoren sind plattformunabhängig; ein Desktop-/SQLite-Betrieb ist derselbe Kern mit anderem Deployment. |
| C | **Exportformate** | Excel (`.xlsx`) für Datenpunkt-/Kabelzugliste, Word/PDF für Regelbeschreibung, **SVG + DXF** für Regelschema. | Generatoren schreiben in ein neutrales Zwischenmodell; Renderer sind austauschbar. |

> **BACtwin-Hinweis:** BACtwin ist mir nicht als vollständig offengelegter,
> feldscharfer Standard sicher genug bekannt, um Kürzellisten fest zu
> verdrahten. Deshalb ist die Bezeichnung **datengetrieben** (Regeln +
> Kürzeltabellen in der DB), nicht hart codiert. Du kannst die BACtwin-Regeln
> pflegen, ohne die Anwendung anzufassen.

---

## 1. Fachliches Domänenmodell

Kern-Erkenntnis: **Automatische Listen/Schemen entstehen nur, wenn jeder
Bauteil-Typ aus einem Katalog kommt, der seine Datenpunkte, Klemmen und
Textbausteine als Vorlage mitbringt.** Der Planer instanziiert Typen; die
Generatoren lesen die Vorlagen aus.

### 1.1 Objekthierarchie (Projektseite)

```
Projekt
└─ Anlage                 (z.B. Heizzentrale, RLT 01)
   └─ Baugruppe           (Gaskessel, Wärmepumpe, Lüftungsanlage …)  ← Aggregat
      ├─ Regelorgan       (Pumpe, Stellantrieb, Mischer …)
      └─ Betriebsmittel   (Temperaturfühler, Druckfühler, 3-Wegeventil …)

Regelkreis                (quer über Baugruppen gruppierbar)
   └─ referenziert Betriebsmittel + Regelorgane (m:n)
```

- **Projekt**: Klammer für mehrere Anlagen, Rechte, Versionsstände.
- **Anlage**: bekommt eine BACtwin-Anlagenkennung.
- **Baugruppe (Aggregat)**: funktionale Einheit; trägt selbst schon Standard-
  Datenpunkte (z.B. Kessel: Vorlauf-/Rücklauffühler, Brenner-Freigabe, Störung).
- **Regelorgan**: aktives Stellglied (hat i.d.R. AO/BO-Datenpunkte + Rückmeldung).
- **Betriebsmittel**: Feldgerät/Sensorik (hat i.d.R. AI/BI-Datenpunkte).
- **Regelkreis**: **das gruppierende Objekt** für den gemeinsamen Regelkreis.
  Er verknüpft Führungsgröße (z.B. Fühler), Stellglied (z.B. Ventil) und
  Regelfunktion (z.B. „Konstantregelung Vorlauf 60 °C") → Grundlage für
  Regelschema **und** Regelbeschreibung.

### 1.2 Katalog / Typenbibliothek (Stammdaten, wiederverwendbar)

Jeder Typ ist eine Vorlage mit angehängten „Baukasten"-Elementen:

```
BauteilTyp  (Kategorie: Baugruppe | Regelorgan | Betriebsmittel)
├─ DatenpunktVorlagen[]   → DP-Name-Kürzel, Signalart (AI/AO/BI/BO), Einheit,
│                            Messbereich, Default-Adresse-Regel, GA-Funktion
├─ KlemmenVorlagen[]      → Klemme, Adernzahl, Kabeltyp-Empfehlung, Querschnitt
├─ AnschlussPunkte[]      → für Schema-Symbol (Ein-/Ausgänge, Medium)
├─ SchemaSymbol           → SVG-Symbol-Referenz (Bibliothekssymbol)
└─ TextbausteinRegel      → Vorlage für Regelbeschreibung (mit Platzhaltern)
```

Damit ist die Generierung **deterministisch**: Anlage + zugeordnete Typen +
Regelkreis-Zuordnung ⇒ alle vier Dokumente ohne manuelle Nacharbeit.

---

## 2. BACtwin-Bezeichnung (`NamingEngine`)

Bezeichnung wird zentral erzeugt, nicht an jeder Stelle „von Hand". Die Engine
setzt aus **konfigurierbaren Segmenten** einen Schlüssel zusammen:

```
[Standort] [Gebäude] [Gewerk/Anlagenart] [AnlagenNr] [Aggregat] [BM-Typ] [Laufnr] [Funktion/DP]
```

- Jedes Segment kommt aus einer **Kürzeltabelle** (`bac_abkuerzung`) mit
  Gültigkeit/Version → BACtwin-Kürzel pflegbar ohne Deployment.
- Trennzeichen, Feldreihenfolge, Pflicht/Optional pro Segment als **Profil**
  (`naming_profile`) hinterlegt → „BACtwin" ist ein Profil, andere Kunden-
  standards (DIN 6779, VDI 3814, RDS-CX) sind weitere Profile.
- Laufnummern werden pro Kontext atomar vergeben (Kollisionsfreiheit).
- Ergebnis wird am Objekt gespeichert **und** ist reproduzierbar (Regel-Snapshot),
  damit spätere Kürzeländerungen historische Pläne nicht still verändern.

> Sobald du mir die genaue BACtwin-Feldstruktur + Kürzelliste gibst, wird daraus
> ein Seed-Datensatz für `naming_profile` + `bac_abkuerzung` — keine
> Code-Änderung.

---

## 3. Datenbankstruktur

Zwei logische Bereiche (in PostgreSQL als Schemata `catalog` und `project`):

### 3.1 Stammdaten `catalog` (versioniert, projektübergreifend)

| Tabelle | Zweck / Schlüsselspalten |
|---------|--------------------------|
| `bauteil_typ` | Typkatalog. `id, kategorie, bezeichnung, hersteller, medium, version` |
| `dp_vorlage` | Datenpunkt-Vorlagen je Typ. `typ_id, dp_kuerzel, signalart, einheit, messbereich, ga_funktion` |
| `klemmen_vorlage` | Klemmen/Verdrahtung je Typ. `typ_id, klemme, adern, kabeltyp_id, querschnitt` |
| `kabeltyp` | Kabelstammdaten. `id, bezeichnung, aufbau, querschnitt, schirm` |
| `schema_symbol` | SVG-Symbolbibliothek. `id, typ_id, svg_ref, anschlusspunkte(jsonb)` |
| `textbaustein` | Regelbeschreibungs-Vorlagen mit Platzhaltern. `id, regelkreis_art, text_md` |
| `naming_profile` | Bezeichnungsprofile (BACtwin …). `id, name, segmente(jsonb)` |
| `bac_abkuerzung` | Kürzeltabellen je Profil/Segment. `profile_id, segment, langtext, kuerzel, gueltig_ab` |

### 3.2 Projektdaten `project`

| Tabelle | Zweck / Schlüsselspalten |
|---------|--------------------------|
| `projekt` | `id, name, kunde, naming_profile_id, status, version` |
| `anlage` | `id, projekt_id, art, bac_kennung, parent(optional)` |
| `baugruppe` | Instanz eines `bauteil_typ`. `id, anlage_id, typ_id, bac_kennung, position(jsonb)` |
| `regelorgan` | `id, baugruppe_id, typ_id, bac_kennung` |
| `betriebsmittel` | `id, baugruppe_id, typ_id, bac_kennung` |
| `datenpunkt` | Materialisierte DP-Instanz. `id, quelle_ref, dp_kuerzel, signalart, adresse, bac_kennung` |
| `regelkreis` | Gruppierung. `id, anlage_id, art, bezeichnung, bac_kennung` |
| `regelkreis_element` | m:n Regelkreis ↔ (Betriebsmittel/Regelorgan). `regelkreis_id, element_typ, element_id, rolle` |
| `dokument` | Generierte Artefakte. `id, projekt_id, art, format, pfad, erzeugt_am, quelle_hash` |
| `audit_log` | Änderungshistorie. `id, entity, entity_id, aktion, benutzer, zeit, diff(jsonb)` |

**Grundsatz:** `datenpunkt` ist eine **materialisierte** Kopie aus `dp_vorlage`
(mit projektindividueller Adresse). So bleiben Projekte stabil, auch wenn der
Katalog sich weiterentwickelt. Ein „Katalog-Update übernehmen"-Vorgang ist
bewusst explizit.

---

## 4. Projekt-/Dateistruktur (Repository)

Getrennt nach Frontend, Backend-Kern und Generatoren, damit die Generatoren
auch headless (CLI/Batch) laufen können.

```
msr-tool/
├─ docs/                         # Konzept, ADRs, BACtwin-Mapping
├─ db/
│  ├─ migrations/                # SQL-Migrationsschritte (catalog + project)
│  └─ seed/                      # Kürzellisten, Beispiel-Typenkatalog
├─ backend/
│  ├─ domain/                    # Entities: Anlage, Baugruppe, Regelkreis …
│  ├─ naming/                    # NamingEngine (BACtwin-Profil)
│  ├─ catalog/                   # Zugriff Typenbibliothek
│  ├─ generators/                # ← Kern der Automatik
│  │  ├─ datapoint_list/         # → xlsx/csv
│  │  ├─ cable_list/             # → xlsx
│  │  ├─ control_scheme/         # → svg/dxf
│  │  └─ control_description/    # → docx/pdf (aus Textbausteinen)
│  ├─ api/                       # REST/GraphQL: Projekte, Zuordnung, Export
│  └─ export/                    # Renderer (xlsx/docx/svg/dxf) austauschbar
├─ frontend/
│  ├─ canvas/                    # Drag-&-Drop-Arbeitsfläche (Anlagenbaum + Palette)
│  ├─ palette/                   # Katalog-Bauteile zum Ziehen
│  ├─ inspector/                 # Eigenschaften/Bezeichnung eines Objekts
│  └─ regelkreis/                # Gruppieren zu Regelkreisen
└─ shared/                       # DTOs/Schema zwischen FE und BE
```

Neutrales Zwischenmodell: Jeder Generator erzeugt zuerst ein **strukturiertes
Zwischenobjekt** (z.B. „DataPointTable", „SchemeGraph"), das dann ein Renderer
in xlsx/docx/svg/dxf gießt. Vorteil: neues Format = neuer Renderer, nicht neuer
Generator.

---

## 5. Automatische Generierung – Ableitungslogik

| Dokument | Quelle | Ableitung |
|----------|--------|-----------|
| **Datenpunktliste** | Alle `datenpunkt` der Anlage | Aus `dp_vorlage` jedes zugeordneten Typs materialisiert; Adresse/BAC-Kennung ergänzt; Gruppierung nach Baugruppe/Regelkreis. |
| **Kabelzugliste** | `klemmen_vorlage` + Topologie | Pro Feldgerät → Kabel von Gerät zu Schaltschrank/DDC; Kabeltyp/Querschnitt aus Vorlage; Länge optional aus Position/Manuell. |
| **Regelschema** | `regelkreis` + `schema_symbol` | Regelkreis-Elemente werden als Symbole platziert und über ihre Anschlusspunkte/Medium verbunden → Graph → SVG/DXF. |
| **Regelbeschreibung** | `regelkreis.art` + `textbaustein` | Passenden Textbaustein wählen, Platzhalter (Sollwerte, Gerätekennungen, BAC-Kennung) füllen → Fließtext. |

Jeder Export speichert einen `quelle_hash` (Hash aus relevanten Objekten). Ändert
sich nichts, wird nicht neu erzeugt; ändert sich etwas, wird der Nutzer auf
veraltete Exporte hingewiesen (Konsistenz-Garantie).

---

## 6. Workflow (Benutzer)

1. **Projekt anlegen** → Namensprofil „BACtwin" wählen.
2. **Anlage(n) anlegen** → BAC-Anlagenkennung wird vorgeschlagen.
3. **Baugruppen per Drag & Drop** aus der Katalog-Palette auf die Anlage ziehen
   (Gaskessel, Wärmepumpe, Lüftung …). Standard-Datenpunkte kommen automatisch mit.
4. **Regelorgane & Betriebsmittel** auf die jeweilige Baugruppe ziehen
   (Fühler, 3-Wegeventil …).
5. **Bezeichnung**: `NamingEngine` vergibt BAC-Kennungen live; Planer kann
   Segmente/Laufnummer im Inspector übersteuern (mit Kollisionsprüfung).
6. **Regelkreise bilden**: Elemente markieren → „zu Regelkreis gruppieren",
   Art wählen (z.B. Konstant-/Folgeregelung), Rollen zuweisen (Istwert/Sollwert/
   Stellglied).
7. **Validierung**: fehlende Rollen, offene Anschlüsse, doppelte Kennungen,
   Datenpunkte ohne Adresse → Prüfliste.
8. **Generieren**: Datenpunktliste, Kabelzugliste, Regelschema, Regelbeschreibung
   auf Knopfdruck; Vorschau; Export im gewählten Format.
9. **Versionieren/Freigeben**: Projektstand einfrieren; Exporte werden mit
   `quelle_hash` an den Stand gebunden.

---

## 7. Empfohlener Technologie-Stack (Vorschlag, offen)

| Schicht | Vorschlag | Begründung |
|---------|-----------|------------|
| DB | PostgreSQL (jsonb für flexible Segmente/Positionen) | relational + flexibel; für Desktop-Variante SQLite-kompatibel gehalten |
| Backend | Python (FastAPI) **oder** .NET | reiche Bibliotheken für xlsx/docx/svg; .NET falls Nähe zum bestehenden Revit-Ökosystem gewünscht |
| Frontend | Web (React + Canvas/SVG-DnD-Bibliothek) | performantes Drag & Drop, Schema-Rendering im Browser |
| Export | openpyxl/xlsxwriter, python-docx, svg→dxf via ezdxf | bewährt, formatstabil |

---

## 8. Nächste Schritte

1. Die drei Annahmen aus **Abschnitt 0** bestätigen/ändern.
2. **BACtwin-Feldstruktur + Kürzelliste** liefern → Seed für `naming_profile`/`bac_abkuerzung`.
3. Einen **Beispiel-Bauteiltyp** vollständig durchdefinieren (z.B. Gaskessel mit
   allen Datenpunkten/Klemmen) als Referenz für den Katalog.
4. Datenmodell als ER-Diagramm final abstimmen, dann Migrationen anlegen.
```
