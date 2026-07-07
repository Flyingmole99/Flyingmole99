# Referenzbeispiel: Generischer Gaskessel (BACtwin)

> Durchgerechnetes Aggregat-Template als Referenz für alle vier Generatoren.
> Grundlage: `BGP_KES_nM_AMEV1` aus BACtwin-Bibliothek 3, Blatt „10 AggregateTempl".

## 1. Gewähltes Template

**`BGP_KES_nM_AMEV1`** — „Kessel mit modulierendem Brenner, Pumpe und
Rücklaufanhebung (z. B. Gas)". `BGP` = Baugruppe. Das ist der generischste
Kessel-Eintrag der Bibliothek (Alternativen: `AGG_BRE_*` nur Brenner,
`ANL_2KES_*` Kesselverbund).

Das Template ist **hierarchisch**: Die Baugruppe referenziert Unter-Aggregate,
die jeweils eigene Datenpunkte mitbringen:

```
BGP_KES_nM_AMEV1  (Kessel-Baugruppe)
├─ SV_BGP                 Struktur-Container der Baugruppe
├─ Sicherheitskette       STW, STB, SDB, WMS   (4 × BI, direkt an der Baugruppe)
├─ AGG_BRE_nM_AMEV1       Brenner modulierend  (20 DP)
├─ AGG_PPE_E1_AMEV1       Pumpe einstufig      (10 DP)
├─ AGG_VEN_ST_AMEV1       Ventil stetig (Rücklaufanhebung / 3-Wege) (9 DP)
├─ AGG_GMZ_H_AMEV1        Gasmengenzähler      (15 DP)
└─ AGG_WMZ_H_AMEV1        Wärmemengenzähler    (17 DP)
```

**Ergebnis der Instanziierung: 76 Datenpunkte** — davon **22 Hardware-I/O**
(6 AI, 12 BI, 2 AO, 2 BO) und 54 Software-/Trend-/Meldeobjekte
(AV/BV/MV/MI/SV/EE/TL). Diese 76 Zeilen entstehen **automatisch**, sobald der
Planer die Kessel-Baugruppe auf die Anlage zieht.

---

## 2. Aufgelöste Datenpunktliste

Legende: **HW** = physische Hardware-I/O (Klemme + Kabel nötig) · sw =
Software-/virtuelles Objekt (kein Feldkabel). `xx` = Laufnummer, `~`/`#####` =
Platzhalter, werden bei Instanziierung aufgelöst.

#### Kessel (Baugruppe)

| # | Objekttyp | I/O | Beschreibung | BAS-Muster (Object_Name) | Einheit |
|---|-----------|-----|--------------|--------------------------|---------|
| 1 | SV | sw |  | `420_EZAxx_KESxx_###_#####_#####_SV~01` |  |
| 2 | BI | **HW** | Sicherheitstemperaturwächter Temperatur schaltend hoch Störmeldung | `420_EZAxx_KESxx_HZ~_STWxx_TSHxx_SM~01` |  |
| 3 | BI | **HW** | Sicherheitstemperaturbegrenzer Temperatur schaltend hoch Alarmmeldung | `420_EZAxx_KESxx_HZ~_STBxx_TSHxx_AM~01` |  |
| 4 | BI | **HW** | Sicherheitsdruckbegrenzer Druck schaltend hoch Alarmmeldung | `420_EZAxx_KESxx_HZ~_SDBxx_PSHxx_AM~01` |  |
| 5 | BI | **HW** | Wassermangelsicherung Füllstand schaltend niedrig Alarmmeldung | `420_EZAxx_KESxx_HZ~_WMSxx_LSLxx_AM~01` |  |

#### Brenner

| # | Objekttyp | I/O | Beschreibung | BAS-Muster (Object_Name) | Einheit |
|---|-----------|-----|--------------|--------------------------|---------|
| 1 | SV | sw | Brenner | `420_EZAxx_KESxx_HZ~_BRExx_#####_SV~01` |  |
| 2 | BO | **HW** | Brenner Schaltbefehl | `420_EZAxx_KESxx_HZ~_BRExx_#####_SB~01` |  |
| 3 | EE | sw | Brenner Ausführkontrolle | `420_EZAxx_KESxx_HZ~_BRExx_#####_AK~01_EE` |  |
| 4 | BI | **HW** | Brenner Betriebsmeldung | `420_EZAxx_KESxx_HZ~_BRExx_#####_BM~01` |  |
| 5 | BI | **HW** | Brenner Störmeldung | `420_EZAxx_KESxx_HZ~_BRExx_#####_SM~01` |  |
| 6 | TL | sw | Brenner Betriebsmeldung Datenaufzeichung | `420_EZAxx_KESxx_HZ~_BRExx_#####_BM~01_TL` |  |
| 7 | AO | **HW** | Brenner Stellsignal | `420_EZAxx_KESxx_HZ~_BRExx_#####_ST~01` | % |
| 8 | AI | **HW** | Brenner Rückführwert | `420_EZAxx_KESxx_HZ~_BRExx_#####_RW~01` | % |
| 9 | TL | sw | Brenner Rückführwert Datenaufzeichung | `420_EZAxx_KESxx_HZ~_BRExx_#####_RW~01_TL` |  |
| 10 | EE | sw | Brenner Abweichung | `420_EZAxx_KESxx_HZ~_BRExx_#####_ABW01_EE` |  |
| 11 | AV | sw | Brenner Betriebsstunden Zählwert | `420_EZAxx_KESxx_HZ~_BRExx_#####_BZ~01` |  |
| 12 | AV | sw | Brenner Zähler Starts Zählwert | `420_EZAxx_KESxx_HZ~_BRExx_ZSTxx_ZW~01` |  |
| 13 | EE | sw | Brenner Bedieneinheit Hand schalten | `420_EZAxx_KESxx_HZ~_BRExx_UBExx_HDB01_EE` |  |
| 14 | EE | sw | Brenner Bedieneinheit Hand stellen | `420_EZAxx_KESxx_HZ~_BRExx_UBExx_HDG01_EE` |  |
| 15 | BI | **HW** | Brenner LVB Hand schalten | `420_EZAxx_KESxx_HZ~_BRExx_LVBxx_HDB01` |  |
| 16 | BI | **HW** | Brenner LVB Hand stellen | `420_EZAxx_KESxx_HZ~_BRExx_LVBxx_HDG01` |  |
| 17 | MI | sw | Brenner LVB Hand schalten | `420_EZAxx_KESxx_HZ~_BRExx_LVBxx_HDB01` |  |
| 18 | MI | sw | Brenner LVB Hand stellen | `420_EZAxx_KESxx_HZ~_BRExx_LVBxx_HDG01` |  |
| 19 | EE | sw | Brenner LVB Hand schalten | `420_EZAxx_KESxx_HZ~_BRExx_LVBxx_HDB01_EE` |  |
| 20 | EE | sw | Brenner LVB Hand stellen | `420_EZAxx_KESxx_HZ~_BRExx_LVBxx_HDG01_EE` |  |

#### Pumpe

| # | Objekttyp | I/O | Beschreibung | BAS-Muster (Object_Name) | Einheit |
|---|-----------|-----|--------------|--------------------------|---------|
| 1 | SV | sw | Pumpe | `430_LTAxx_ERHxx_HZV_PPExx_#####_SV~01` |  |
| 2 | BO | **HW** | Pumpe Schaltbefehl | `430_LTAxx_ERHxx_HZV_PPExx_MOTxx_SB~01` |  |
| 3 | EE | sw | Pumpe Ausführkontrolle | `430_LTAxx_ERHxx_HZV_PPExx_MOTxx_AK~01_EE` |  |
| 4 | BI | **HW** | Pumpe Betriebsmeldung | `430_LTAxx_ERHxx_HZV_PPExx_MOTxx_BM~01` |  |
| 5 | TL | sw | Pumpe Betriebsmeldung Datenaufzeichung | `430_LTAxx_ERHxx_HZV_PPExx_MOTxx_BM~01_TL` |  |
| 6 | BI | **HW** | Pumpe Störmeldung | `430_LTAxx_ERHxx_HZV_PPExx_MOTxx_SM~01` |  |
| 7 | EE | sw | Pumpe Bedieneinheit Hand schalten | `430_LTAxx_ERHxx_HZV_PPExx_UBExx_HDB01_EE` |  |
| 8 | BI | **HW** | Pumpe LVB Hand schalten | `430_LTAxx_ERHxx_HZV_PPExx_LVBxx_HDB01` |  |
| 9 | MI | sw | Pumpe LVB Hand schalten | `430_LTAxx_ERHxx_HZV_PPExx_LVBxx_HDB01` |  |
| 10 | EE | sw | Pumpe LVB Hand schalten | `430_LTAxx_ERHxx_HZV_PPExx_LVBxx_HDB01_EE` |  |

#### Ventil

| # | Objekttyp | I/O | Beschreibung | BAS-Muster (Object_Name) | Einheit |
|---|-----------|-----|--------------|--------------------------|---------|
| 1 | SV | sw | Ventil | `430_LTAxx_ERHxx_HZV_VENxx_#####_SV~01` |  |
| 2 | AO | **HW** | Ventil Stellsignal | `430_LTAxx_ERHxx_HZV_VENxx_MOTxx_ST~01` | % |
| 3 | EE | sw | Ventil Abweichung | `430_LTAxx_ERHxx_HZV_VENxx_MOTxx_ABW01_EE` |  |
| 4 | AI | **HW** | Ventil Rückführwert | `430_LTAxx_ERHxx_HZV_VENxx_MOTxx_RW~01` | % |
| 5 | EE | sw | Ventil Bedieneinheit Hand stellen | `430_LTAxx_ERHxx_HZV_VENxx_UBExx_HDG01_EE` |  |
| 6 | TL | sw | Ventil Rückführwert Datenaufzeichung | `430_LTAxx_ERHxx_HZV_VENxx_MOTxx_RW~01_TL` |  |
| 7 | BI | **HW** | Ventil LVB Hand stellen | `430_LTAxx_ERHxx_HZV_VENxx_LVBxx_HDG01` |  |
| 8 | MI | sw | Ventil LVB Hand stellen | `430_LTAxx_ERHxx_HZV_VENxx_LVBxx_HDG01` |  |
| 9 | EE | sw | Ventil LVB Hand stellen | `430_LTAxx_ERHxx_HZV_VENxx_LVBxx_HDG01_EE` |  |

#### Gasmengenzähler

| # | Objekttyp | I/O | Beschreibung | BAS-Muster (Object_Name) | Einheit |
|---|-----------|-----|--------------|--------------------------|---------|
| 1 | SV | sw | Gasmengenzähler | `420_EZAxx_BHKxx_GC~_GMZxx_#####_SV~01` |  |
| 2 | BV | sw | Gasmengenzähler Zähler Störmeldung | `420_EZAxx_BHKxx_GC~_GMZxx_ZAExx_SM~01` |  |
| 3 | AV | sw | Gasmengenzähler Zähler Seriennummer | `420_EZAxx_BHKxx_GC~_GMZxx_ZAExx_SN~01` |  |
| 4 | AV | sw | Gasmengenzähler Energiemenge Zählwert | `420_EZAxx_BHKxx_GC~_GMZxx_H~~xx_ZW~01` |  |
| 5 | AV | sw | Gasmengenzähler Leistung Messwert | `420_EZAxx_BHKxx_GC~_GMZxx_J~~xx_MW~01` |  |
| 6 | AV | sw | Gasmengenzähler Menge Zählwert | `420_EZAxx_BHKxx_GC~_GMZxx_F~~xx_ZW~01` |  |
| 7 | AV | sw | Gasmengenzähler Menge Messwert | `420_EZAxx_BHKxx_GC~_GMZxx_F~~xx_MW~01` |  |
| 8 | AI | **HW** | Gasmengenzähler Temperatur Messwert | `420_EZAxx_BHKxx_GC~_GMZxx_T~~xx_MW~01` | °C |
| 9 | AI | **HW** | Gasmengenzähler Druck Messwert | `420_EZAxx_BHKxx_GC~_GMZxx_P~~xx_MW~01` | mbar |
| 10 | TL | sw | Gasmengenzähler Energiemenge Zählwert Datenaufzeichung | `420_EZAxx_BHKxx_GC~_GMZxx_H~~xx_ZW~01_TL` |  |
| 11 | TL | sw | Gasmengenzähler Leistung Messwert Datenaufzeichung | `420_EZAxx_BHKxx_GC~_GMZxx_J~~xx_MW~01_TL` |  |
| 12 | TL | sw | Gasmengenzähler Menge Zählwert Datenaufzeichung | `420_EZAxx_BHKxx_GC~_GMZxx_F~~xx_ZW~01_TL` |  |
| 13 | TL | sw | Gasmengenzähler Menge Messwert Datenaufzeichung | `420_EZAxx_BHKxx_GC~_GMZxx_F~~xx_MW~01_TL` |  |
| 14 | TL | sw | Gasmengenzähler Temperatur Messwert Datenaufzeichung | `420_EZAxx_BHKxx_GC~_GMZxx_T~~xx_MW~01_TL` |  |
| 15 | TL | sw | Gasmengenzähler Druck Messwert Datenaufzeichung | `420_EZAxx_BHKxx_GC~_GMZxx_P~~xx_MW~01_TL` |  |

#### Wärmemengenzähler

| # | Objekttyp | I/O | Beschreibung | BAS-Muster (Object_Name) | Einheit |
|---|-----------|-----|--------------|--------------------------|---------|
| 1 | SV | sw | Wärmemengenzähler | `420_NZAxx_FWUxx_HW~_WMZxx_#####_SV~01` |  |
| 2 | BV | sw | Wärmemengenzähler Zähler Störmeldung | `420_NZAxx_FWUxx_HW~_WMZxx_ZAExx_SM~01` |  |
| 3 | AV | sw | Wärmemengenzähler Zähler Seriennummer | `420_NZAxx_FWUxx_HW~_WMZxx_ZAExx_SN~01` |  |
| 4 | AV | sw | Wärmemengenzähler Energiemenge Zählwert | `420_NZAxx_FWUxx_HW~_WMZxx_H~~xx_ZW~01` |  |
| 5 | AV | sw | Wärmemengenzähler Leistung Messwert | `420_NZAxx_FWUxx_HW~_WMZxx_J~~xx_MW~01` |  |
| 6 | AV | sw | Wärmemengenzähler Menge Zählwert | `420_NZAxx_FWUxx_HW~_WMZxx_F~~xx_ZW~01` |  |
| 7 | AV | sw | Wärmemengenzähler Menge Messwert | `420_NZAxx_FWUxx_HW~_WMZxx_F~~xx_MW~01` |  |
| 8 | AI | **HW** | Wärmemengenzähler Temperatur Messwert | `420_NZAxx_FWUxx_HWR_WMZxx_T~~xx_MW~01` | °C |
| 9 | AI | **HW** | Wärmemengenzähler Temperatur Messwert | `420_NZAxx_FWUxx_HWV_WMZxx_T~~xx_MW~01` | °C |
| 10 | AV | sw | Wärmemengenzähler Temperaturdifferenz Messwert berechnet | `420_NZAxx_FWUxx_HW~_WMZxx_TD~xx_MWC01` |  |
| 11 | TL | sw | Wärmemengenzähler Energiemenge Zählwert Datenaufzeichung | `420_NZAxx_FWUxx_HW~_WMZxx_H~~xx_ZW~01_TL` |  |
| 12 | TL | sw | Wärmemengenzähler Leistung Messwert Datenaufzeichung | `420_NZAxx_FWUxx_HW~_WMZxx_J~~xx_MW~01_TL` |  |
| 13 | TL | sw | Wärmemengenzähler Menge Zählwert Datenaufzeichung | `420_NZAxx_FWUxx_HW~_WMZxx_F~~xx_ZW~01_TL` |  |
| 14 | TL | sw | Wärmemengenzähler Menge Messwert Datenaufzeichung | `420_NZAxx_FWUxx_HW~_WMZxx_F~~xx_MW~01_TL` |  |
| 15 | TL | sw | Wärmemengenzähler Temperatur Messwert Datenaufzeichung | `420_NZAxx_FWUxx_HWR_WMZxx_T~~xx_MW~01_TL` |  |
| 16 | TL | sw | Wärmemengenzähler Temperatur Messwert Datenaufzeichung | `420_NZAxx_FWUxx_HWV_WMZxx_T~~xx_MW~01_TL` |  |
| 17 | TL | sw | Wärmemengenzähler Temperaturdifferenz Messwert berechnet Datenaufzeichung | `420_NZAxx_FWUxx_HW~_WMZxx_TD~xx_MWC01_TL` |  |

---

## 3. Abgeleitete Kompositionsregeln (wichtig für die Engine)

Das Beispiel deckt die Regeln auf, die die `NamingEngine` und der Instanziierer
beherrschen müssen:

1. **Ortsbezug wird beim Einbau umgeschrieben.** Die Unter-Aggregate tragen im
   Template ihren *eigenen* Beispiel-Präfix — Pumpe/Ventil zeigen
   `430_LTAxx_ERHxx…`, Gaszähler `420_EZAxx_BHKxx…`, Wärmezähler
   `420_NZAxx_FWUxx…`. Im Kessel müssen **Block 1–3 (Gewerk/Anlage/Baugruppe)
   auf den Kessel-Kontext `420_EZAxx_KESxx…` überschrieben** werden; nur
   Block 4–8 (Medium, Aggregat, BM, Funktion, Erweiterung) stammen aus dem
   Template. → Templates speichern die Adresse **relativ**, der Beispiel-Präfix
   ist nur illustrativ.

2. **Platzhalter → Laufnummern.** `xx` wird pro Kontext hochgezählt
   (`KES01`, `BRE01`, `PPE01` …), `~`/`#####`/`###` markieren unbelegte
   Kürzel-/Ebenenstellen und bleiben als Füllzeichen erhalten.

3. **Hardware ≠ Software.** Nur `AI/AO/BI/BO` sind physische I/O und gehen in die
   **Kabelzugliste** + Klemmenplan. `SV` ist ein reiner Struktur-Container
   (BACnet Structured View), `AV/BV/MV/MI` sind berechnete/virtuelle Werte,
   `EE`/`TL` sind an einen Basis-Datenpunkt **angehängte** Objekte
   (referenzierte Meldung bzw. Datenaufzeichnung). → Die Generatoren brauchen ein
   Feld `ist_hardware` je Objekttyp.

4. **`EE`/`TL` sind Attribute, keine eigenständigen Punkte.** Sie referenzieren
   den Basispunkt (gleicher BAS + Suffix `_EE`/`_TL`). In der Datenpunktliste als
   Zusatzspalte („Trend ja/nein", „Alarm ja/nein") darstellbar statt als
   Extrazeilen — konfigurierbar.

5. **Sicherheitskette ist verdrahtungsrelevant.** STW/STB/SDB/WMS
   (Sicherheitstemperaturwächter/-begrenzer, Druckbegrenzer,
   Wassermangelsicherung) sind hartverdrahtete BI und müssen im Schema als
   Verriegelung des Brenners erscheinen.

---

## 4. Ableitung der vier Dokumente aus diesem Beispiel

| Dokument | Aus diesem Kessel |
|----------|-------------------|
| **Datenpunktliste** | Die 76 Zeilen oben, angereichert um BACnet-Properties je Objekttyp (Units: °C/mbar/%, Min/Max_Pres_Value, Priority-Array, Conformance) aus Bibliothek 2. |
| **Kabelzugliste** | Die **22 HW-I/O**, gruppiert je Feldgerät: Brenner (BO+BI+BI+AO+AI+2 BI), Pumpe (BO+2 BI+BI), Ventil/3-Wege (AO+AI+BI), Sicherheitskette (4 BI), Gaszähler (2 AI), Wärmezähler (2 AI). Je Gerät → Kabel Feld↔Schaltschrank; Kabeltyp/Adern/Querschnitt aus Betriebsmittel-Vorlage. |
| **Regelschema** | Regelkreis „Kesselvorlauf-Temperaturregelung": Führung = Vorlauffühler (WMZ-T Vorlauf), Stellglied = Brenner (Stellsignal `ST~`), Verriegelung = Sicherheitskette; Rücklaufanhebung = 3-Wege-Ventil + Pumpe. Symbole aus eigener Bibliothek. |
| **Regelbeschreibung** | Textbaustein „Kessel modulierend mit Rücklaufanhebung": Brenner moduliert auf Vorlauf-Sollwert, Freigabe über Sicherheitskette, Pumpe bei Wärmeanforderung, 3-Wege hält Mindest-Rücklauftemperatur. Platzhalter mit BAS-Kennungen + Sollwerten gefüllt. |

---

## 5. Rückwirkung auf das Datenmodell (Konzept.md)

Dieses Beispiel bestätigt und präzisiert:

- `aggregat_template` braucht **Selbstreferenz** (`referenz_template`) für die
  Hierarchie Baugruppe → Aggregat → Objekt (rekursive Auflösung).
- `dp_objekttyp` braucht Flag **`ist_hardware`** (AI/AO/BI/BO = true) und
  **`ist_erweiterung`** (EE/TL, referenziert Basispunkt).
- `aggregat_template_dp.bas_muster` speichert die **relative** Adresse (Block
  4–8); Block 1–3 kommt bei Instanziierung aus dem Platzierungskontext →
  `NamingEngine.compose(parentPath, relPattern)`.
- `datenpunkt` erhält Spalten für die BACnet-Properties (Units, Min/Max, Prio),
  die aus `dp_objekt_property` gezogen werden.
- Kabelzugliste braucht je HW-Datenpunkt eine Zuordnung Feldgerät →
  Schaltschrank/DDC; das Feldgerät ist die Aggregat-/BM-Ebene über dem Punkt.
