# valeri

Modulares Werkzeug für Wirtschaftlichkeitsberechnungen gebäudetechnischer
Energieversorgungsanlagen nach **DIN EN 17463 (VALERI)** mit Gegenprobe nach
**VDI 2067 Blatt 1**.

VALERI steht für *Valuation of Energy Related Investments* und beschreibt die
Bewertung energiebezogener Investitionen über die Kapitalwertmethode nach
Steuern. VDI 2067 liefert die Annuitätenmethode sowie die Kennwerte für
Nutzungsdauer, Wartung und Instandsetzung; die steuerlichen Nutzungsdauern
kommen aus der AfA-Tabelle des BMF.

## Schnellstart

```bash
pip install -e .[dev]

valeri rechnen beispiele/beispiel_wp_vs_kessel.yaml   # Bericht + Vergleich
valeri module                                          # Module und ihre Verträge
valeri katalog waermepumpe                             # Kennwertkatalog durchsuchen
valeri sensitivitaet beispiele/beispiel_wp_vs_kessel.yaml --variante Gaskessel
```

Ausgabe (gekürzt):

```
Variante                     Kapitalwert    Annuität/a   Investition   Δ Kapitalwert     IRR  Amort.
----------------------------------------------------------------------------------------------------
Gaskessel (Ref)               -2.496.827      -275.204       341.550               -       -       -
Waermepumpe + Speicher        -2.581.686      -283.136     1.062.600         -84.859    3.1%       -
```

Als Bibliothek:

```python
from valeri import lade_projekt, rechne

projekt = lade_projekt("beispiele/beispiel_wp_vs_kessel.yaml")
ergebnis = rechne(projekt)

print(ergebnis.bericht("Gaskessel"))
print(ergebnis.vergleich.als_text())
print(ergebnis.varianten["Gaskessel"].get("ergebnis.kennzahlen"))
```

## Architektur

Jede fachliche Funktion ist genau ein Modul. Module kennen einander nicht — sie
deklarieren nur, welche Schlüssel sie aus dem Rechenkontext **benötigen** und
welche sie **liefern**. Die Ausführungsreihenfolge wird daraus topologisch
abgeleitet, nicht fest verdrahtet.

```
Projekt (YAML)
   |
   v
m10 Stammdaten ──> m20 Finanzrahmen ──────────────────────────┐
   |                    (Steuersatz, WACC, Preispfade)         |
   v                                                           |
m30 Bedarf  ──> m35 Speicher ──> m40 Erzeuger ──> m50 Energiekosten
 (Lastgang)   (Spitzenlast-      (WP/Kessel/KKM      (Arbeit, Leistung,
              kappung)            oder Kostenansatz)   Grundpreis, CO2)
                                                               |
m60 Investition ──> m61 Kennwerte ──> m62 Betriebskosten ──────┤
                    (VDI 2067 / AfA)                           |
                                                               v
                                        m70 Zahlungsreihe ──> m75 Steuern
                                                               |
                                        ┌──────────────────────┴─────────┐
                                        v                                v
                              m80 VALERI (Kapitalwert)      m81 VDI 2067 (Annuität)
                                        └──────────────┬─────────────────┘
                                                       v
                                     m85 Kennzahlen ──> m95 Bericht
```

```
src/valeri/
├── core/          Modul-Vertrag, Registry, Pipeline, Zeitreihe, Finanzmathematik
├── modelle/       Pydantic-Datenmodelle = die Verträge zwischen den Modulen
├── module/        je Datei eine fachliche Funktion (m10 … m95) + Vergleich
├── daten/         Kennwertkataloge als YAML (VDI 2067, AfA) + Zugriffsschicht
├── io/            Lastgang-Import (CSV), Projektdateien
└── cli.py
```

### Modul ergänzen

```python
from valeri.core.modul import Rechenmodul
from valeri.core.registry import registriere

@registriere()
class Eigenstrom(Rechenmodul):
    id = "m45_eigenstrom"
    titel = "PV-Eigenverbrauch"
    grundlage = "Bilanzierung im Stundenraster"
    benoetigt = ("erzeuger.endenergie",)
    liefert = ("eigenstrom.quote", "eigenstrom.erloes_eur_a")

    def berechne(self, ctx):
        ...
        return {"eigenstrom.quote": quote, "eigenstrom.erloes_eur_a": erloes}
```

Import in `valeri/module/__init__.py` eintragen — fertig. Die Pipeline hängt das
Modul selbständig an der richtigen Stelle ein.

### Modul ersetzen

Gleiche `id`, gleiche `liefert`-Menge, `@registriere(ersetzt=True)`. Kein
anderes Modul muss angefasst werden. Ein Test in `tests/test_pipeline.py` sichert
genau diese Zusage ab.

## Fachliche Bausteine

**Randdaten** — Betrachtungszeitraum, Eigenkapitalquote und -rendite,
Fremdkapitalzins und -laufzeit, Ertragsteuersatz (automatisch aus KSt + SolZ +
GewSt oder manuell), Preisänderungsraten je Kostenart, nominale oder reale
Betrachtung. Der Kalkulationszins ist standardmäßig der WACC nach Steuern.

**Verbrauch und Lastgang** — je Energieart (Wärme, Kälte, Strom) wahlweise
eingelesene Zeitreihe (CSV, 15 min oder 1 h), parametrisches Ersatzprofil oder
Bandlast. Ersatzprofile werden als solche gekennzeichnet, weil Spitzenlast,
Leistungspreis und Speicherauslegung unmittelbar davon abhängen.

**Erzeugung** — entweder ein Erzeugersystem (Wärmepumpe über JAZ oder
Carnot-Gütegrad, Kessel über Nutzungsgrad, Kältemaschine über SEER, Fernwärme,
BHKW) mit Deckung nach Priorität — damit sind bivalente Anlagen ohne Sonderlogik
abbildbar — oder ein pauschaler Kostenansatz in EUR/kWh.

**Speicher** — Simulation der Spitzenlastkappung im Lastgangraster mit Lade- und
Entladeleistung, Wirkungsgraden und Selbstentladung. Drei Betriebsarten:
kleinstmögliche Spitze bei gegebener Kapazität, Kappung auf eine Zielspitze,
oder Auslegung der kleinsten Kapazität für eine Zielspitze.

**Investition und Kennwerte** — die Produktkategorie einer Position steuert
technische Nutzungsdauer, Instandsetzung, Wartung und Bedienaufwand (VDI 2067),
der AfA-Schlüssel die steuerliche Nutzungsdauer (BMF). Beide sind bewusst
getrennt: die technische Nutzungsdauer bestimmt Ersatzinvestition und Restwert,
die steuerliche nur die Abschreibung. Jeder Wert ist einzeln überschreibbar und
trägt seine Herkunft (`manuell`, `vdi2067:…`, `afa:…`, `vorgabe`) im Protokoll.

**Ergebnis** — Kapitalwert nach DIN EN 17463, Annuität nach VDI 2067 mit
Aufteilung in kapital-, bedarfs-, betriebsgebundene und sonstige Kosten,
interner Zinsfuß, statische und dynamische Amortisation, Gestehungskosten,
Variantenvergleich mit Differenzgrößen und CO2-Vermeidungskosten sowie
Sensitivitätsanalyse.

## Kennwertkataloge

`src/valeri/daten/vdi2067_kategorien.yaml` und `afa_bmf.yaml` enthalten einen
**Startdatensatz mit Richtwerten**, keinen Normauszug. VDI 2067 ist
urheberrechtlich geschützt, und die steuerliche Einordnung (Betriebsvorrichtung
oder Gebäudebestandteil) entscheidet oft stärker über die AfA-Dauer als die
Produktkategorie. Alle Einträge tragen deshalb `geprueft: false`; solange das so
ist, weist jede Berechnung im Protokoll darauf hin.

Eigene Bürowerte:

```python
from valeri.daten import lade_kataloge
from valeri.module.m61_kennwerte import Kennwertableitung

modul = Kennwertableitung(lade_kataloge("buero_vdi.yaml", "buero_afa.yaml"))
```

## Bewusste Vereinfachungen

* Restwert am Ende des Betrachtungszeitraums als Buchwertabgang, nicht besteuert.
* AfA linear und ganzjährig ab dem Folgejahr der Investition — keine pro rata
  temporis, keine degressive AfA, keine Sonderabschreibung.
* Gewerbesteuerliche Hinzurechnung von Schuldentgelten nur optional und
  vereinfacht.
* Nettobetrachtung ohne Umsatzsteuer (Vorsteuerabzug unterstellt).
* Außentemperatur der Ersatzprofile aus Sinusnäherung statt Testreferenzjahr.
* Fremdkapital wirkt standardmäßig über den WACC; die explizite
  Finanzierungsrechnung (`finanzierung_explizit: true`) wechselt auf die
  Eigenkapitalsicht und diskontiert dann mit der Eigenkapitalrendite.

Diese Punkte sind in den Modul-Docstrings und im Berechnungsprotokoll benannt.
Sie sind der erste Ort, an dem das Werkzeug zu erweitern ist, sobald ein
Projekt genauer werden muss.

## Tests

```bash
python -m pytest -q
```

Der wichtigste Test ist die Kreuzprobe: ohne Steuern, ohne Preissteigerung, ohne
Ersatzinvestition und ohne Restwert muss die Annuität nach VDI 2067 exakt dem
mit dem Annuitätsfaktor umgerechneten Kapitalwert nach DIN EN 17463 entsprechen.
Ein zweiter Test prüft den Kapitalwert gegen eine von Hand nachvollziehbare
Rechnung.

## Haftungsausschluss

Das Werkzeug unterstützt die Erstellung von Wirtschaftlichkeitsberechnungen,
ersetzt aber weder den Blick in die Normen noch die steuerliche Beratung.
Insbesondere die AfA-Einordnung und die Frage der Betriebsvorrichtung sind im
Einzelfall zu klären.
