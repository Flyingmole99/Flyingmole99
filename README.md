# Wärmebrücken-Tool für Revit (Thermal Bridge Detection)

Revit-Add-in zur **automatischen Erkennung, Markierung, Klassifizierung und
Auswertung linearer Wärmebrücken** für einen prüfbaren energetischen Nachweis.

Das Tool erzeugt **prüfbare Datenobjekte** (nicht nur grafische Markierungen)
mit Länge, Wärmebrückentyp, Psi-Wert, Quelle, Status und Excel-Export. Die
automatische Erkennung legt **keine endgültigen Nachweiswerte** fest – sie
erzeugt potenzielle Wärmebrücken mit Status *„automatisch erkannt“* bzw.
*„unklar“*. Erst nach Zuordnung von Psi-Typ/-Wert/Quelle und manueller Freigabe
(Status *„geprüft“*) geht eine Wärmebrücke in die energetische Summe ein.

---

## 1. Analyse der Anforderungen (Kurzfassung)

| Anforderung | Umsetzung |
|---|---|
| Robuste, prüfbare Datenobjekte | Shared-Parameter-Datensatz je Marker (`WB_*`) |
| Auto-Erkennung ≠ Nachweiswert | Status-Workflow: `automatisch erkannt`/`unklar` → `geprüft` |
| Auditierbarkeit | Quelle + Bibliotheksversion werden je WB gespeichert |
| Konservative Geometrie | Unsichere Geometrie → Status `unklar` + Hinweis statt falscher Wert |
| Erweiterbarkeit | Detektoren als eigene Klassen mit gemeinsamem `WbFactory` |

## 2. Architektur

```
ThermalBridgeTool/
├─ ThermalBridgeTool.csproj          # net8.0-windows (Revit 2025)
├─ ThermalBridgeTool.addin           # Add-in-Manifest
├─ Resources/PsiLibrary_Template.csv # Psi-Wert-Bibliothek (Vorlage)
└─ src/
   ├─ App.cs                         # IExternalApplication, Ribbon, Session-State
   ├─ Common/                        # Constants, UnitHelper, GeometryUtil, Logger
   ├─ Models/                        # ThermalBridge, PsiLibraryEntry, ValidationIssue, DetectionOptions
   ├─ Commands/                      # IExternalCommand je Ribbon-Schaltfläche
   ├─ Services/
   │  ├─ ParameterService.cs         # Shared-Parameter anlegen/binden
   │  ├─ EnvelopeService.cs          # Thermische-Hülle-Logik
   │  ├─ MarkerService.cs            # DirectShape-Marker erzeugen + Param-Mapping
   │  ├─ ThermalBridgeRepository.cs  # WB aus Modell lesen / löschen
   │  ├─ ThermalBridgeDetectionService.cs  # Orchestrierung
   │  ├─ DuplicateCheckService.cs    # Dublettenprüfung
   │  ├─ PsiLibraryService.cs        # CSV-Bibliothek + Zuordnung
   │  ├─ ValidationService.cs        # Plausibilitätsprüfung
   │  ├─ ExcelExportService.cs       # CSV + XLSX-Export
   │  └─ Detectors/                  # Window/Door/Plinth/FloorSlab + Helper
   └─ UI/                            # MainWindow, AssignPsiTypeWindow, ValidationResultWindow (WPF)
```

**Schichtung:** Commands (Revit-API-Kontext, Transaktionen, UI) → Services
(Fachlogik) → Models (reine Daten). Geometrie-/Einheiten-Helfer sind frei von
UI und damit unit-testbar.

## 3. Entscheidung: C#-Add-in statt Dynamo

**Empfehlung: C#-Revit-Add-in** (umgesetzt). Begründung:

- **Persistente Datenobjekte mit Shared-Parametern** und Status-Workflow sind in
  C# sauber transaktional umsetzbar; in Dynamo ist Parameter-Binding und
  Statuspflege fehleranfällig.
- **Dublettenprüfung, Validierung, Versionierung** brauchen strukturierte
  Klassen und Tests – in Dynamo schlecht wartbar.
- **Auditierbarkeit/Reproduzierbarkeit**: ein signiertes Add-in mit fester
  Bibliotheksversion ist nachvollziehbarer als ein Graph.

Dynamo eignet sich als **Prototyp** für eine einzelne Geometrieabfrage (z. B.
schnelle Sichtprüfung „welche Fenster sitzen in Außenwänden“). Für den Nachweis
ist das Add-in vorzuziehen.

## 4. Datenmodell

`ThermalBridge` (Klasse, 1:1 zu den `WB_*`-Parametern):

| Feld | Parameter | Einheit/Typ |
|---|---|---|
| Id | WB_ID | Text (deterministisch: `WB-<KAT>-<HostId>-<Kante>`) |
| Kategorie | WB_Kategorie | Text (kontrolliertes Vokabular) |
| Untertyp | WB_Untertyp | Text |
| PsiTyp | WB_Psi_Typ | Text (Bibliotheks-Code) |
| PsiWert | WB_Psi_Wert | Number, W/(m·K) |
| LaengeM | WB_Laenge | Length (intern feet, Anzeige Projektunit) |
| Verlustkoeffizient | WB_Verlustkoeffizient | Number, W/K (= Psi·Länge) |
| Quelle | WB_Quelle | Text (inkl. Bibliotheksversion) |
| Status | WB_Status | Text |
| Bauteil1Id | WB_Bauteil_1_ID | Text (ElementId-Wert) |
| Bauteil2Id | WB_Bauteil_2_ID | Text |
| Ebene | WB_Ebene | Text |
| Aussenbezug | WB_Aussenbezug | Text |
| Hinweis | WB_Hinweis | Text |

Hüllbauteile erhalten zusätzlich: `SE_Thermische_Huelle` (Ja/Nein),
`SE_Bauteil_gegen` (Text), `SE_Bauteiltyp_Energie` (Text).

**Kontrolliertes Vokabular** (zentral in `Common/Constants.cs`):

- Status: `automatisch erkannt`, `unklar`, `geprüft`, `verworfen`, `bereits vorhanden`
- Kategorie: Fensteranschluss, Außentüranschluss, Terrassentüranschluss,
  Sockel/Bodenplattenrand, Geschossdeckenanschluss (+ vorbereitet: Dach, Ecke,
  Innenwand auf Erdreich)

## 5. Revit-Parameter (Datentypen & Einheiten)

Erzeugt von `ParameterService` als **Shared Parameter** (Instanz-Binding):

| Parameter | SpecTypeId | Bindung |
|---|---|---|
| WB_ID, WB_Kategorie, WB_Untertyp, WB_Psi_Typ, WB_Quelle, WB_Status, WB_Bauteil_1_ID, WB_Bauteil_2_ID, WB_Ebene, WB_Aussenbezug, WB_Hinweis | `String.Text` | Generische Modelle |
| WB_Psi_Wert, WB_Verlustkoeffizient | `Number` | Generische Modelle |
| WB_Laenge | `Length` | Generische Modelle |
| SE_Thermische_Huelle | `Boolean.YesNo` | Wände, Decken, Fenster, Türen, Dächer |
| SE_Bauteil_gegen, SE_Bauteiltyp_Energie | `String.Text` | Wände, Decken, Fenster, Türen, Dächer |

**Einheiten:** Längen werden intern in *feet* gehalten und ausschließlich in
`Common/UnitHelper` nach Metern konvertiert (`UnitTypeId.Meters`). `WB_Psi_Wert`
und `WB_Verlustkoeffizient` sind `Number` (roher SI-Wert ohne Revit-Unit-Magie).

> Hinweis (versionsabhängig): Die ForgeTypeId-/`SpecTypeId`-API gilt für Revit
> 2022+. Für ältere Versionen müsste auf `ParameterType` umgestellt werden.

## 6. Familienstrategie „WB_Linear“ (Abschnitt K)

Geprüft wurden Option 1 (linienbasierte Generic-Model-Familie) und Option 2
(DirectShape/ModelCurve).

**Umgesetzt: DirectShape (Generic Models) mit dünnem Balken-Solid** – als
robuste, projektunabhängige Variante:

- benötigt **keine mitgelieferte `.rfa`**, funktioniert in jedem Projekt;
- in Grundriss, Schnitt und 3D sichtbar, über Kategorie/Untertyp/Status
  **filterbar** (Sichtbarkeits-/Grafikfilter auf die `WB_*`-Parameter);
- trägt alle Shared-Parameter direkt.

**Empfehlung für Produktion / Migrationspfad zu Option 1:** Eine
linienbasierte, **„work plane based“** Generic-Model-Familie `WB_Linear.rfa` mit
einem schmalen Sweep-Profil und denselben Shared-Parametern bietet bessere
grafische Kontrolle (Linienstil je Status) und einfacheres Tagging. Die
Umstellung berührt nur `MarkerService` – das Parameter-Mapping
(`WriteParameters`/`ReadBridge`) bleibt identisch. Beschreibung der Familie:

> `WB_Linear.rfa`: Vorlage *Generic Model line based / face based*. Ein
> Extrusions-/Sweep-Solid (~15–30 mm) entlang der Platzierungslinie. Shared
> Parameter `WB_*` als Instanzparameter. Unterkategorien/Linienstile je Status
> (z. B. rot = unklar, grün = geprüft) für Filter. Platzierung über
> `doc.Create.NewFamilyInstance(line, symbol, level, StructuralType.NonStructural)`.

## 7. Erkennungslogik (umgesetzt)

- **A Fenster** (`WindowBridgeDetector`): je Fenster in Hüllwand 4 WB
  (Laibung L/R = Höhe, Sturz/Brüstung = Breite). Host-Wand-ID + Fenster-ID.
- **B Türen** (`DoorBridgeDetector`): wie Fenster; Schwelle als eigener Untertyp;
  Terrassen-/Fenstertüren über Typname/Höhe getrennt klassifiziert.
- **C Sockel** (`PlinthBridgeDetector`): Außenwände der untersten Ebene,
  WB entlang Wand-Unterkante; ohne Bodenplatte gegen Erdreich → Status `unklar`.
- **D Geschossdecke** (`FloorSlabBridgeDetector`): Decke ∩ Hüllwand über
  BBox-Overlap + Höhenlage; Kontaktlinie an der Wand; konservativ als `unklar`
  markiert (Kontaktlänge = Wandachse, Näherung).
- **E Dubletten** (`DuplicateCheckService`): Signatur aus Kategorie, Untertyp,
  Bauteilpaar, gerundeter Länge und Mittelpunkt; vorhandene werden als
  „bereits vorhanden“ protokolliert, nicht überschrieben. Option „löschen & neu“.
- **G Plausibilität** (`ValidationService`): Längen-/Psi-/Quelle-/Status-Regeln,
  „geprüft ohne Pflichtwerte“, fehlender Host, fehlende Kontaktlinie, Dubletten.

## 8./9. Psi-Bibliothek & Export

- **`Resources/PsiLibrary_Template.csv`** – Spalten: `Psi_Typ_Code; Kategorie;
  Untertyp; Beschreibung; Psi_Wert; Quelle; Gueltig_fuer; Status; Version`.
  `PsiLibraryService` erkennt `;`/`,` und Dezimal-`.`/`,` automatisch.
- **Export** (`ExcelExportService`): CSV (immer) und XLSX (ClosedXML). Spalten
  inkl. `WB_Verlustkoeffizient_W_K = Psi · Länge`. **Summenzeile**
  `Summe_Waermebrueckenverlustkoeffizient_W_K` nur über **geprüfte** WB. Nicht
  geprüfte WB werden exportiert, aber als „nicht nachweiswirksam“ markiert und
  **nicht** summiert. Bibliotheksversion + Exportzeit werden mitgeschrieben.

## 10. Build & Registrierung (Revit 2025)

1. **Voraussetzungen:** Visual Studio 2022 / `dotnet` SDK 8, Revit 2025.
2. **Restore/Build:**
   ```
   dotnet build ThermalBridgeTool.csproj -c Release
   ```
   Die Revit-API kommt über die NuGet-Pakete `Nice3point.Revit.Api.RevitAPI(UI)`
   (`ExcludeAssets=runtime`, werden nicht kopiert). Alternativ direkte
   `<Reference HintPath=...>` auf `C:\Program Files\Autodesk\Revit 2025\`.
3. **Add-in registrieren:** `ThermalBridgeTool.addin` + `ThermalBridgeTool.dll`
   (+ `ClosedXML.dll`) nach
   `%AppData%\Autodesk\Revit\Addins\2025\` kopieren. Im `.addin` zeigt
   `<Assembly>` auf den DLL-Pfad (relativ neben der `.addin` oder absolut).
4. **Start:** Revit → Tab **„Wärmebrücken“** → *Hauptfenster öffnen* oder die
   Einzelschaltflächen (Parameter → Erkennen → Bibliothek → Zuordnen → Prüfen →
   Export).

> **Für Revit 2023/2024:** `TargetFramework` auf `net48`, Paketversionen auf
> `2024.*` umstellen. `ElementId.Value` (long) gibt es ab 2024; für 2023 ist
> `ElementId.IntegerValue` (int) zu verwenden.

## 11. Bekannte Grenzen & nächste Schritte

**Grenzen (Stufe 1):**

- Geometrie-Platzierung der Marker ist **bounding-box-zentriert** (Längen sind
  exakt aus Typ-/Instanzmaßen, die Lage ist Näherung). Für Maßketten/Tags ist
  die Familienvariante (Option 1) vorzuziehen.
- Geschossdecken-Kontaktlänge ist eine **Näherung** (Wandachse) → bewusst Status
  `unklar`. Präzise Kontaktlänge erfordert Solid-Solid-Verschneidung.
- „Thermische Hülle“ basiert auf `SE_*`-Parametern bzw. Fallback
  „Wandfunktion = Außen“. Schräge/gekrümmte Wände und gebogene Fensterbänder sind
  nicht vollständig abgedeckt (Warnung statt falscher Wert).
- XLSX-Export benötigt `ClosedXML`; CSV ist dependency-frei.

**Nächste Schritte (vorbereitet):**

- Detektoren für **Dachanschluss**, **Außen-/Innenecken**,
  **Innenwand auf Erdreich** (Kategorien bereits in `Constants` angelegt).
- `WB_Linear.rfa` als Loadable Family inkl. statusabhängiger Linienstile.
- Präzise Kontaktlinien über `SolidUtils`/`BooleanOperationsUtils`.
- Unit-Tests für `UnitHelper`, `GeometryUtil`, `DuplicateCheckService`,
  `PsiLibraryService`, `ValidationService` (bewusst Revit-frei gehalten).
- Schreiben/Lesen der `SE_*`-Werte über eine eigene Klassifizierungs-UI.

---

### Wichtiger fachlicher Hinweis

Die automatische Erkennung erzeugt **potenzielle** Wärmebrücken. Verantwortung
für Wärmebrückentyp, Psi-Wert, Quelle und Freigabe (Status `geprüft`) liegt beim
Energieberater/Prüfer. Nur geprüfte Wärmebrücken sind nachweiswirksam.
