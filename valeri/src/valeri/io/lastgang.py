"""Lastgänge einlesen und – ersatzweise – synthetisieren.

Einlesen ist der Regelfall (gemessene 15-min- oder Stundenwerte). Die
Synthese liefert nur ein *Ersatzprofil* für frühe Projektphasen; sie wird im
Protokoll immer als solche gekennzeichnet, weil die Spitzenlast und damit
Leistungspreis und Speicherauslegung stark davon abhängen.
"""

from __future__ import annotations

import csv
import math
from pathlib import Path

from valeri.core.zeitreihe import Lastgang
from valeri.modelle.energie import Lastgangquelle

_EINHEIT_FAKTOR = {"kW": 1.0, "MW": 1000.0, "kWh": 1.0, "MWh": 1000.0}


def lade_csv(quelle: Lastgangquelle, bezeichnung: str = "") -> Lastgang:
    """Liest eine Zeitreihe aus einer CSV-Datei.

    Erwartet eine Spalte mit Messwerten; ``spalte`` kann Name oder Index sein.
    Werte in kWh/MWh werden über die Intervalldauer in eine mittlere Leistung
    umgerechnet.
    """
    if not quelle.pfad:
        raise ValueError("Lastgangquelle ohne Pfad")
    pfad = Path(quelle.pfad)
    if not pfad.exists():
        raise FileNotFoundError(f"Lastgangdatei nicht gefunden: {pfad}")

    werte: list[float] = []
    with pfad.open("r", encoding="utf-8-sig", newline="") as fh:
        muster = csv.reader(fh, delimiter=quelle.trennzeichen)
        zeilen = list(muster)
    if not zeilen:
        raise ValueError(f"Leere Lastgangdatei: {pfad}")

    kopf = zeilen[0]
    start = 0
    index: int
    if isinstance(quelle.spalte, str):
        if quelle.spalte not in kopf:
            raise ValueError(
                f"Spalte {quelle.spalte!r} nicht in Kopfzeile {kopf} gefunden"
            )
        index = kopf.index(quelle.spalte)
        start = 1
    elif isinstance(quelle.spalte, int):
        index = quelle.spalte
        start = 1 if not _ist_zahl(kopf[index], quelle.dezimaltrennzeichen) else 0
    else:
        index = 1 if len(kopf) > 1 else 0
        start = 1 if not _ist_zahl(kopf[index], quelle.dezimaltrennzeichen) else 0

    for zeile in zeilen[start:]:
        if not zeile or index >= len(zeile) or not zeile[index].strip():
            continue
        werte.append(_zahl(zeile[index], quelle.dezimaltrennzeichen))

    faktor = _EINHEIT_FAKTOR[quelle.einheit]
    dt_h = quelle.aufloesung_min / 60.0
    if quelle.einheit in ("kWh", "MWh"):
        # Arbeit je Intervall -> mittlere Leistung
        faktor = faktor / dt_h
    return Lastgang(
        tuple(w * faktor for w in werte),
        quelle.aufloesung_min,
        bezeichnung or pfad.stem,
        {"quelle": str(pfad), "art": "messung"},
    )


def _ist_zahl(text: str, dezimal: str) -> bool:
    try:
        _zahl(text, dezimal)
        return True
    except ValueError:
        return False


def _zahl(text: str, dezimal: str) -> float:
    text = text.strip().replace(" ", "")
    if dezimal == ",":
        text = text.replace(".", "").replace(",", ".")
    return float(text)


# ------------------------------------------------------------------ Synthese


def aussentemperatur(stunde: int, mittel_c: float = 9.5, amplitude_c: float = 9.5) -> float:
    """Grobes Jahres-/Tagesprofil der Außentemperatur (Ersatzdaten).

    Für belastbare Ergebnisse gehört hier ein Testreferenzjahr (TRY) des DWD
    hinein – die Schnittstelle ist bewusst diese eine Funktion.
    """
    tag = stunde // 24
    stunde_im_tag = stunde % 24
    jahresgang = mittel_c - amplitude_c * math.cos(2 * math.pi * (tag - 15) / 365.0)
    tagesgang = 4.0 * math.sin(2 * math.pi * (stunde_im_tag - 9) / 24.0)
    return jahresgang + tagesgang


def synthetisiere(
    quelle: Lastgangquelle, jahresarbeit_kwh: float, bezeichnung: str = ""
) -> Lastgang:
    """Erzeugt ein parametrisches Ersatzprofil mit 8760 Stundenwerten."""
    n = 8760
    roh: list[float] = []

    for stunde in range(n):
        tag = stunde // 24
        wochentag = tag % 7
        stunde_im_tag = stunde % 24
        t_aussen = aussentemperatur(stunde)
        werktag = 1.0 if wochentag < 5 else quelle.wochenend_faktor
        nutzung = 0.35 + 0.65 * _nutzungsprofil(stunde_im_tag)

        if quelle.profiltyp == "waerme":
            heizanteil = max(0.0, quelle.heizgrenze_c - t_aussen)
            grundlast = 0.15  # Trinkwarmwasser / Verteilverluste
            wert = heizanteil * (0.7 + 0.3 * nutzung) * werktag + grundlast * 8.0
        elif quelle.profiltyp == "kaelte":
            kuehlanteil = max(0.0, t_aussen - 12.0)
            grundlast = 0.25  # innere Lasten, Serverkühlung
            wert = kuehlanteil * nutzung * werktag + grundlast * 6.0
        elif quelle.profiltyp == "strom":
            wert = (0.4 + 0.6 * nutzung) * werktag
        else:  # band
            wert = 1.0
        roh.append(max(wert, 0.0))

    lastgang = Lastgang(
        tuple(roh), 60, bezeichnung, {"art": "ersatzprofil", "typ": quelle.profiltyp}
    )

    if quelle.vollbenutzungsstunden_h:
        # Profil so stauchen/spreizen, dass die Zielbenutzungsdauer erreicht wird
        lastgang = _auf_benutzungsdauer(lastgang, quelle.vollbenutzungsstunden_h)
    return lastgang.skaliert_auf(jahresarbeit_kwh)


def _nutzungsprofil(stunde_im_tag: int) -> float:
    """Tagesgang der Nutzung (0..1), Bürobetrieb als Vorgabe."""
    if 7 <= stunde_im_tag < 18:
        return 1.0
    if stunde_im_tag in (6, 18, 19):
        return 0.6
    return 0.15


def _auf_benutzungsdauer(lastgang: Lastgang, ziel_h: float, schritte: int = 60) -> Lastgang:
    """Profil über einen Exponenten auf eine Zielbenutzungsdauer bringen.

    p_neu = p_max * (p/p_max)^x – x>1 spitzt zu, x<1 glättet.
    """
    p_max = lastgang.spitzenlast_kw()
    if p_max <= 0:
        return lastgang
    unten, oben = 0.2, 6.0
    for _ in range(schritte):
        x = (unten + oben) / 2
        werte = [p_max * (w / p_max) ** x for w in lastgang.werte_kw]
        probe = lastgang.mit_werten(werte)
        if probe.benutzungsdauer_h() > ziel_h:
            unten = x  # stärker zuspitzen -> kleinere Benutzungsdauer
        else:
            oben = x
    x = (unten + oben) / 2
    return lastgang.mit_werten([p_max * (w / p_max) ** x for w in lastgang.werte_kw])
