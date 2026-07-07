# Import-Pipeline: BACtwin-Workbooks → `catalog`-Datenbank

> Spezifikation des Spalten-Mappings je Blatt der drei BACtwin-Workbooks auf die
> `catalog`-Stammdatentabellen (siehe `Konzept.md` §4.1). Letzte Design-Lücke vor
> dem ersten Code.

## 1. Grundsätze

- **UUID-basiert & idempotent.** Jede Objekt-/Aggregat-Zeile trägt eine BACtwin-
  UUID → Primärschlüssel. Reimport = **Upsert** per UUID; Vokabeln ohne UUID
  werden per `(profil, block, kuerzel)` upserted.
- **Versioniert.** Jeder Lauf legt eine `bac_version` an (z. B. „AMEV 1.2",
  Dateiname, Hash, Zeitstempel); alle importierten Zeilen tragen `version_id`.
  Projekte binden an eine Version — Reimport verändert bestehende Projekte nie
  automatisch.
- **Bilingual.** Alle Blätter führen DE + EN (EN meist rechts, „ENGLISH VERSION
  (Draft)"). Import beider Sprachen in `sprache`-Spalten bzw. `_en`-Felder.
- **Kopfzeilen-Offset variiert.** Nicht jedes Blatt hat den Kopf in Zeile 0 (s.
  Spalte „Kopfzeile" unten). Der Parser bekommt Offset + Spaltenindex je Blatt
  aus einer **Mapping-Konfiguration** (kein Hardcoding im Code).
- **Quelle = normalisierte Blätter.** Import aus `10 AggregateTempl` + `8.x`, nicht
  aus der voll-gejointen `18 BACtwinTab` (mehrzeilige Gruppenköpfe). `18` dient
  nur als **Gegenprobe** (Zeilenzahl/UUID-Abgleich).

## 2. Importreihenfolge (Abhängigkeiten)

```
1. bac_version            (Lauf-Metadaten)
2. bac_gewerk             ← B1 „3 Gewerke"
3. naming_profile         ← B1 „2 Gliederung" (Blockdefinition, Stellen, Trennz.)
4. bac_vokabular          ← B1 „4 BACtwin-BAS" (Kürzel je Block)
5. Referenztabellen       ← B3 „15/16/23/24/25/26"
6. dp_objekttyp           ← B2 „8 BACtwin_Objects_DE/EN"
7. dp_objekt_property     ← B2 „8.1–8.14" (je Objekttyp)
8. aggregat_template      ← B3 „10 AggregateTempl" (Header-Zeilen)
9. aggregat_template_dp   ← B3 „10 AggregateTempl" (DP-Zeilen)
```

Fremdschlüssel: `dp_objekt_property.objekttyp_uuid → dp_objekttyp.uuid`;
`aggregat_template_dp.dp_objekttyp_uuid → dp_objekttyp.uuid` (bzw.
`referenz_template_uuid → aggregat_template.uuid` bei Unter-Aggregaten).

---

## 3. Mapping Bibliothek 1 (Adressstruktur)

### 3.1 `3 Gewerke` → `bac_gewerk`  (Kopfzeile 1)

| Quelle Spalte | Ziel | Hinweis |
|---|---|---|
| 1 `Kostengruppe (DIN 276-1)` | `kg` | z. B. 420 |
| 2 `Kürzel (VDI 3814-4.1)` | `kuerzel` | z. B. HZG |
| 3 `Z`-Spalte (1 Zeichen) | `kuerzel_1z` | Variante „gekürzt", z. B. H |
| 4 `Bezeichnung` | `bezeichnung_de` | |
| 8 / 9 / 11 (EN) | `kuerzel_en`, `kuerzel_1z_en`, `bezeichnung_en` | rechte Blockhälfte |

### 3.2 `2 Gliederung` → `naming_profile`  (Kopfzeile 3)

Definiert **nicht Vokabeln**, sondern die **Blockstruktur** je Variante
(ungekürzt/gekürzt, mit/ohne Teilanlage). Pro Block eine `segmente[]`-Zeile
(jsonb) mit: Blocknr., Bezeichnung, Stellenbereich (`Stelle`), Trennzeichen,
Pflicht/optional. Es entstehen 4 Profile (Beispiel 1–4) → daraus die
Standardprofile „BACtwin ungekürzt" / „BACtwin gekürzt".

| Quelle Spalte | Ziel (`segmente[]`-Element) |
|---|---|
| `BAS-Block` | `block` (1..8, „2.1" = Teilanlage) |
| `Bezeichnung` | `name` |
| `Stelle` | `stelle_von`, `stelle_bis` |
| `Trenn-zeichen` | `trennzeichen` (`_`, `°`, leer) |
| Spalte „(optional)" im Blocklabel | `optional` (bool) |

### 3.3 `4 BACtwin-BAS` → `bac_vokabular`  (Kopf: Blocktitel Zeile 3, Spalten Zeile 4)

Breites Blatt: je BAS-Block ein Spaltentripel (Kürzel/Bezeichnung/Description).
Der Importer iteriert die Blöcke und schreibt **eine Zeile je Kürzel** mit
`block`-Nummer:

| Block | Kürzel-Spalte | Bez.-Spalte | Desc.-Spalte |
|---|---|---|---|
| 1 Gewerk | 3 | 4 | (KG in 2) |
| 2 Anlage | 6 | 7 | 8 |
| 3 Baugruppe | 10 | 11 | 12 |
| 4 Medium/Position | 14 | 15 | 16 |
| 5 Aggregat | 18 | 19 | 20 |
| 6 Betriebsmittel | 22 | 23 | 24 |
| 7 Funktion | 26 | 27 | 28 |
| 8 Erweiterung | 30 | 31 | 32 |

Zielspalten: `block, kuerzel, bezeichnung, beschreibung, sprache, version_id`.
Leerzeilen/DIN-KG-Trennzeilen (rein numerisch) überspringen.

---

## 4. Mapping Bibliothek 2 (Datenpunkt-Objekttypen)

### 4.1 `8 BACtwin_Objects_DE` / `_EN` → `dp_objekttyp`  (Kopfzeile 0)

| Quelle Spalte | Ziel | Hinweis |
|---|---|---|
| 0 `Status` | `status` | Freigabestand |
| 1 `ObjSort + LfdNr` | `obj_sort` | Sortier-/Referenz-Code (a101 …) |
| 2 `UUID` | `uuid` | **PK** |
| 3 `Objekt-Template-Kennung` | `kennung` | z. B. `AI_MW_T_AMEV1` |
| 4 `Object_Type` | `object_type` | AI/AO/AV/BI/BO/BV/MI/MO/MV/SV/CAL/LP/NC/SCH/TL/EE/DEV |
| 5 `Kommentar` | `bezeichnung_de` (`_en` aus `8…_EN`) | |
| 6–… `GA-FL Einträge (x.y.z)` | `ga_fl(jsonb)` | Funktionsbereichs-Marker („X") → Liste |
| letzte `Letztmalige Änderung in Version` | `geaendert_version` | |

**Abgeleitete Felder (Transform, nicht in Quelle):**
- `ist_hardware` = `object_type ∈ {AI, AO, BI, BO}`.
- `ist_erweiterung` = `object_type ∈ {EE, TL}` (referenziert Basispunkt via
  BAS-Suffix `_EE`/`_TL`).

### 4.2 `8.1 AI` … `8.14 TL` → `dp_objekt_property`  (Kopfzeile 0, Property je Spalte)

Jedes Detailblatt = ein Object_Type mit den **BACnet-Property-Defaults**. Der
Importer transponiert: pro Objekttyp-Zeile × Property-Spalte → eine
`dp_objekt_property`-Zeile (oder ein jsonb-Property-Bag je Objekttyp — empfohlen
für die vielen optionalen Alarm-Properties).

Schlüsselspalten (Beispiel `8.1 AI`, 42 Spalten):

| Quelle Spalte | Ziel-Property | Für Datenpunktliste relevant |
|---|---|---|
| 2 `Objekt-Template-Kennung` | (Join → `objekttyp_uuid`) | |
| 9 `Object_Name` | `object_name_muster` | ✔ (BAS-Muster) |
| 10 `Description` | `description_muster` | ✔ |
| 16 `Units` | `units` | ✔ (°C, mbar, %) |
| 17/18 `Min_/Max_Pres_Value` | `min_pres`, `max_pres` | ✔ (Messbereich) |
| 19 `Resolution`, 20 `COV_Increment` | `resolution`, `cov` | |
| 22 `Notification_Class` | `notification_class` | ✔ (Meldeklasse) |
| 23/24/25 `Low/High_Limit`, `Deadband` | `low_limit`, `high_limit`, `deadband` | ✔ (Grenzwerte) |
| 26–36 Event-/Alarm-Properties | `event_props(jsonb)` | optional |
| 2 (Zeile „Conformance Code") | `conformance` je Property | R/W/O + AMEV-Profil |

> Die Zeilen 1–3 jedes 8.x-Blatts sind **Meta-Zeilen** (PropSort, Conformance
> Code, Grundvorgabe), keine Objektdaten → als Property-Metadaten einlesen, nicht
> als Objekt.

---

## 5. Mapping Bibliothek 3 (Aggregat-Templates + Referenztabellen)

### 5.1 `10 AggregateTempl` → `aggregat_template` + `aggregat_template_dp`  (Kopfzeile 2)

Zwei Zeilentypen im selben Blatt, unterschieden über belegte Spalten:

**A) Template-Kopfzeile** (Spalte 2 UUID **und** 4 Kennung gesetzt, 6 Ref leer)
→ `aggregat_template`:

| Quelle Spalte | Ziel |
|---|---|
| 1 `Typ` | `typ` (Aggregat/Baugruppe/Anlage) |
| 2 `UUID` | `uuid` (**PK**) |
| 3 `Gewerk` | `gewerk_kg` |
| 4 `…Template-Kennung` | `kennung` (z. B. `BGP_KES_nM_AMEV1`) |
| 5 `…Template-Bezeichnung` | `bezeichnung_de` |
| 27 `Letztmalige Änderung in Version` | `geaendert_version` |

**B) DP-/Referenz-Zeile** (Spalte 6 `Referenziertes Template` gesetzt)
→ `aggregat_template_dp` (mit `template_uuid` = zuletzt gelesene Kopf-UUID):

| Quelle Spalte | Ziel | Hinweis |
|---|---|---|
| 6 `Referenziertes Template` | `referenz_kennung` | Objekttyp-Kennung **oder** Unter-Aggregat |
| 7 `Varianten-Kennung` | `variante` | z. B. 1.1, 2.2 |
| 9/10 `Description Beispiele …` | `beschreibung` | zusammengesetzt |
| 11 `Description Länge` | `laenge` | Prüfwert |
| 12 `Object_Name Beispiel` | `object_name_beispiel` | **illustrativ**, s. §6 |
| 14–26 (BAS-Blockspalten) | `bas_block(jsonb)` | **vorzerlegte** BAS — s. u. |

**Klassifikation je Zeile (Transform):**
- `ist_unteraggregat` = `referenz_kennung` beginnt mit `AGG_`/`BGP_`/`ANL_` →
  `referenz_template_uuid` (rekursiv), sonst `dp_objekttyp_uuid` (Join über
  `dp_objekttyp.kennung`).

**BAS vorzerlegt (Spalten 14–26)** — der große Gewinn: kein String-Parsing nötig:

| Spalte | Block | Spalte | Block |
|---|---|---|---|
| 14 | Gewerk-Kennung | 21 | Aggregate-Nummer |
| 15 | Anlagen-Kennung | 22 | BM-Kennung |
| 16 | Anlagen-Nummer | 23 | BM-Nummer |
| 17 | Baugruppen-Kennung | 24 | BM-Funktions-Kennung |
| 18 | Baugruppen-Nummer | 25 | BM-Funktions-Nummer |
| 19 | Medium, Position | 26 | BM-Funktions-Erweiterung |
| 20 | Aggregate-Kennung | | |

→ `aggregat_template_dp.bas_relativ` speichert **nur Block 4–8** (Spalten 19–26,
Medium…Erweiterung). Block 1–3 (Spalten 14–18) ist der illustrative Ortsbezug und
wird **nicht** gespeichert (wird bei Instanziierung aus dem Kontext gesetzt, §6).

### 5.2 Referenztabellen → eigene `catalog`-Tabellen

| Quelle | Kopfzeile | Ziel | Schlüsselspalten |
|---|---|---|---|
| `15 Funktionsbereich` | 1 | `funktionsbereich` | Kennung(a/b/c/d), Bezeichnung, Objekttyp-Kennung |
| `16 ZuständKennung` + `17 ZuständigTab` | 1 | `zustaendigkeit` | Kennbuchstabe(B/P/U), Bereich, Ziffernblock |
| `23 MinCharStringLength` | 2 | `min_char_length` | Property, AMEV-Profil (MBE/AS-C/AS-D/MOU), Länge |
| `24 Priority_Array` | 1 | `priority_array` | Prio(1..16), Verwendung, Empfehlung |
| `25 Meldeklasse` | 1 | `meldeklasse` | Object_Identifier(NC100…), Bezeichnung, Priority, Ack_Required |
| `26 EventParameter` | 1 | `event_parameter` | Objekt_Template, Event_Algorithm, Event_Parameters |
| `27 Betreibervorgabe` | — | `betreibervorgabe` | Betreiber-Defaults (optional) |

`min_char_length` + `meldeklasse` + `priority_array` fließen später in die
Datenpunkt-Validierung und -Anreicherung ein.

---

## 6. Parsing-Regeln (die kniffligen Stellen)

1. **Relativer BAS.** Aus `10 AggregateTempl` nur Block 4–8 als `bas_relativ`
   übernehmen. Bei Instanziierung setzt `NamingEngine.compose(parentPath,
   bas_relativ)` die Block 1–3 aus Anlage/Baugruppe des Platzierungskontexts.
   → Der Beispiel-Ortsbezug im Template (`430_LTA…`, `420_EZA_BHK…`) wird
   **verworfen**, nie kopiert.
2. **Platzhalter erhalten.** `xx`/`##`/`nnn` (Nummern), `~`/`#####`/`###`
   (Kürzel-/Ebenen-Füllung), `%%` (Medium-Präfix) unverändert speichern; erst der
   Instanziierer ersetzt `xx` durch Laufnummern.
3. **Hierarchie rekursiv.** Unter-Aggregat-Zeilen (`AGG_/BGP_/ANL_`) beim
   Auflösen expandieren (Zyklusschutz per besuchter UUID-Menge). Der Kessel
   ergibt so 76 DP aus 5 Unter-Aggregaten.
4. **EE/TL anhängen.** Zeilen mit Objekttyp EE/TL an den Basispunkt gleicher BAS
   (ohne Suffix) binden → Flags `trend`/`alarm` statt Extrazeilen (konfigurierbar).
5. **SV = Container.** `SV_*`-Zeilen als Struktur-/Gruppierungsknoten importieren,
   nicht als Datenpunkt mit I/O.
6. **Leer-/Meta-Zeilen filtern.** DIN-KG-Trennzeilen (rein numerisch), leere
   Zeilen, „ENGLISH VERSION (Draft)"-Marker und die Meta-Zeilen der 8.x-Blätter
   (Zeilen 1–3) ausschließen.
7. **Object_Type-Splits.** Blätter `8.2 AO_AV`, `8.4 BO_BV`, `8.10 MO_MV`
   enthalten **zwei** Object_Types je Blatt → beim Import je Zeile am tatsächlichen
   `object_type` aus `8 …` trennen.

---

## 7. Idempotenz, Diff & Validierung

- **Upsert-Strategie:** `INSERT … ON CONFLICT (uuid) DO UPDATE`; Vokabeln
  `ON CONFLICT (profil, block, kuerzel)`. Kein Löschen — entfallene Zeilen werden
  `status='veraltet'` markiert (Soft-Delete), damit Altprojekte referenzierbar
  bleiben.
- **Diff-Report je Lauf:** neue / geänderte / veraltete UUIDs gegenüber Vorversion
  → Protokoll in `bac_version_diff`. Der Planer entscheidet pro Projekt, ob er auf
  die neue Version hebt.
- **Validierung beim Import:**
  - Referenzintegrität: jede `referenz_kennung` findet ein `dp_objekttyp` **oder**
    `aggregat_template`.
  - BAS-Länge je Datenpunkt ≤ `min_char_length`-Vorgabe (Object_Name = 64).
  - Jeder HW-Objekttyp hat Units/Messbereich, wo Property es fordert.
  - Gegenprobe der Zeilenzahl/UUID-Menge gegen `18 BACtwinTab`.

---

## 8. Implementierungsform (passt zu `backend/import/`)

```
backend/import/
├─ mapping/                # deklarative Blatt→Tabelle-Konfiguration (YAML/JSON)
│  ├─ bibliothek1.yaml     # Blatt, Kopfzeile-Offset, Spaltenindizes, Block-Tripel
│  ├─ bibliothek2.yaml
│  └─ bibliothek3.yaml
├─ readers/                # openpyxl-Leser je Blatt-Typ (breit / transponiert / 2-Zeilen-Typ)
├─ transforms/             # ist_hardware, bas_relativ, EE/TL-Bindung, Hierarchie
├─ loaders/                # Upsert je Zieltabelle (+ version_id)
├─ validate.py             # Referenz-/Längen-/Gegenprobe
└─ run_import.py           # Orchestrierung in Reihenfolge §2, ein bac_version-Lauf
```

**Kern-Idee:** Das Mapping ist **Daten (YAML), kein Code** — neue BACtwin-Version
mit verschobenen Spalten = angepasste Mapping-Datei, kein Deployment.

---

## 9. Offene Punkte für die Umsetzung

1. Property-Modell festlegen: `dp_objekt_property` **relational** vs. `jsonb`-Bag
   (Empfehlung: jsonb für die ~30 optionalen Alarm-Properties, feste Spalten für
   Units/Min/Max/NC).
2. `27 Betreibervorgabe` und `17 ZuständigTab` (374 Zeilen) fachlich einordnen —
   für MVP optional.
3. Symbol-/Textbaustein-Zuordnung je Objekttyp/Aggregat ist **nicht** in BACtwin
   → separater Pflegedatensatz (für Schema + Regelbeschreibung).
