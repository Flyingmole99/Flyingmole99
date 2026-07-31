"""M35 – Speicher zur Spitzenlastkappung.

Der Speicher wirkt auf den Nutzenergie-Lastgang *vor* der Erzeugung. Dadurch
sinkt die erforderliche Erzeugerleistung (Investition) und – über den
Leistungspreis – die Energiebezugskosten. Genau diese beiden Effekte sind der
wirtschaftliche Hebel der Spitzenlastkappung.

Simulation je Zeitschritt:
  Last > Zielleistung -> Speicher entlädt (begrenzt durch Entladeleistung/SoC)
  Last < Zielleistung -> Speicher lädt   (begrenzt durch Ladeleistung/Kapazität)
Verluste werden über Lade-/Entladewirkungsgrad und Selbstentladung erfasst.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from valeri.core.einheiten import Energieart
from valeri.core.kontext import Rechenkontext
from valeri.core.modul import Rechenmodul
from valeri.core.registry import registriere
from valeri.core.zeitreihe import Lastgang
from valeri.modelle.speicher import Speicher


@dataclass
class Speicherergebnis:
    name: str
    energieart: Energieart
    kapazitaet_kwh: float
    spitze_vorher_kw: float
    spitze_nachher_kw: float
    kappung_kw: float
    kappung_anteil: float
    zusatzarbeit_kwh: float
    entladene_arbeit_kwh: float
    vollzyklen: float
    hinweis: str = ""


@registriere()
class Speichermodul(Rechenmodul):
    id = "m35_speicher"
    titel = "Speicher / Spitzenlastkappung"
    grundlage = "Lastgangsimulation mit Leistungs- und Kapazitätsgrenzen"
    benoetigt = ("bedarf.nutzenergie",)
    liefert = ("speicher.nutzenergie", "speicher.ergebnisse")

    def berechne(self, ctx: Rechenkontext) -> Mapping[str, Any]:
        lastgaenge: dict[Energieart, Lastgang] = dict(ctx.get("bedarf.nutzenergie"))
        ergebnisse: list[Speicherergebnis] = []

        for speicher in ctx.variante.speicher:
            if speicher.energieart not in lastgaenge:
                ctx.notiere(
                    f"Speicher {speicher.name!r}: kein Bedarf für "
                    f"{speicher.energieart.value} – übersprungen."
                )
                continue
            vorher = lastgaenge[speicher.energieart]
            nachher, ergebnis = kappe(vorher, speicher)
            lastgaenge[speicher.energieart] = nachher
            ergebnisse.append(ergebnis)
            if ergebnis.hinweis:
                ctx.notiere(f"Speicher {speicher.name!r}: {ergebnis.hinweis}")

        return {"speicher.nutzenergie": lastgaenge, "speicher.ergebnisse": ergebnisse}


# --------------------------------------------------------------------- Kernlogik


def kappe(lastgang: Lastgang, speicher: Speicher) -> tuple[Lastgang, Speicherergebnis]:
    """Wendet einen Speicher auf einen Lastgang an."""
    spitze = lastgang.spitzenlast_kw()

    if speicher.modus == "kapazitaet_auslegen":
        ziel = speicher.ziel_spitzenlast_kw or spitze
        kapazitaet = _kapazitaet_fuer_ziel(lastgang, speicher, ziel)
        speicher = speicher.model_copy(update={"kapazitaet_kwh": kapazitaet})
        ziel_kw = ziel
    elif speicher.modus == "zielspitze":
        ziel_kw = speicher.ziel_spitzenlast_kw or spitze
    else:  # "maximal"
        ziel_kw = _minimale_spitze(lastgang, speicher)

    untergrenze = spitze * (1.0 - speicher.max_kappung_anteil)
    ziel_kw = max(ziel_kw, untergrenze)

    profil, fehlmenge = _simuliere(lastgang, speicher, ziel_kw)
    hinweis = ""
    if fehlmenge > 1e-6:
        hinweis = (
            f"Zielspitze {ziel_kw:,.1f} kW nicht durchgängig haltbar "
            f"(Fehlmenge {fehlmenge:,.0f} kWh) – Kapazität oder Entladeleistung prüfen."
        )

    erreicht = profil.spitzenlast_kw()
    zusatz = profil.summe_kwh() - lastgang.summe_kwh()
    entladen = sum(
        max(0.0, a - b) for a, b in zip(lastgang.werte_kw, profil.werte_kw)
    ) * lastgang.dt_h
    kapazitaet = speicher.kapazitaet_nutzbar_kwh()

    ergebnis = Speicherergebnis(
        name=speicher.name,
        energieart=speicher.energieart,
        kapazitaet_kwh=speicher.kapazitaet_kwh or 0.0,
        spitze_vorher_kw=spitze,
        spitze_nachher_kw=erreicht,
        kappung_kw=spitze - erreicht,
        kappung_anteil=(spitze - erreicht) / spitze if spitze > 0 else 0.0,
        zusatzarbeit_kwh=zusatz,
        entladene_arbeit_kwh=entladen,
        vollzyklen=entladen / kapazitaet if kapazitaet > 0 else 0.0,
        hinweis=hinweis,
    )
    return profil, ergebnis


def _simuliere(
    lastgang: Lastgang, speicher: Speicher, ziel_kw: float
) -> tuple[Lastgang, float]:
    """Ein Simulationslauf. Rückgabe: (gekappter Lastgang, nicht gedeckte Arbeit)."""
    dt = lastgang.dt_h
    kapazitaet = speicher.kapazitaet_nutzbar_kwh()
    p_laden = speicher.ladeleistung_kw or float("inf")
    p_entladen = speicher.entladeleistung_kw or float("inf")
    eta_l = speicher.wirkungsgrad_laden
    eta_e = speicher.wirkungsgrad_entladen
    verlust = speicher.verlust_pro_tag * dt / 24.0

    soc = kapazitaet * speicher.ladezustand_start
    ergebnis: list[float] = []
    fehlmenge = 0.0

    for last in lastgang.werte_kw:
        if last > ziel_kw:
            bedarf_kwh = (last - ziel_kw) * dt
            moeglich = min(bedarf_kwh, p_entladen * dt, soc * eta_e)
            soc -= moeglich / eta_e if eta_e > 0 else 0.0
            rest_kw = last - moeglich / dt
            fehlmenge += max(0.0, rest_kw - ziel_kw) * dt
            ergebnis.append(rest_kw)
        else:
            spielraum_kw = min(ziel_kw - last, p_laden)
            aufnahme = min(spielraum_kw * dt * eta_l, kapazitaet - soc)
            soc += aufnahme
            ergebnis.append(last + (aufnahme / eta_l) / dt if eta_l > 0 else last)
        soc = max(0.0, soc * (1.0 - verlust))

    return lastgang.mit_werten(ergebnis), fehlmenge


def _minimale_spitze(lastgang: Lastgang, speicher: Speicher, schritte: int = 40) -> float:
    """Kleinste haltbare Zielspitze bei gegebener Kapazität (Bisektion)."""
    unten = 0.0
    oben = lastgang.spitzenlast_kw()
    if speicher.kapazitaet_nutzbar_kwh() <= 0:
        return oben
    for _ in range(schritte):
        mitte = (unten + oben) / 2.0
        _, fehlmenge = _simuliere(lastgang, speicher, mitte)
        if fehlmenge > 1e-6:
            unten = mitte
        else:
            oben = mitte
    return oben


def _kapazitaet_fuer_ziel(
    lastgang: Lastgang, speicher: Speicher, ziel_kw: float, schritte: int = 30
) -> float:
    """Kleinste Kapazität, mit der die Zielspitze eingehalten wird."""
    unten = 0.0
    # Obergrenze (brutto): gesamte Arbeit oberhalb der Zielspitze
    arbeit_oberhalb = sum(max(0.0, w - ziel_kw) for w in lastgang.werte_kw) * lastgang.dt_h
    oben = max(arbeit_oberhalb, 1.0) / max(speicher.nutzbarer_anteil, 1e-9)
    for _ in range(schritte):
        mitte = (unten + oben) / 2.0
        probe = speicher.model_copy(update={"kapazitaet_kwh": mitte})
        _, fehlmenge = _simuliere(lastgang, probe, ziel_kw)
        if fehlmenge > 1e-6:
            unten = mitte
        else:
            oben = mitte
    return oben
