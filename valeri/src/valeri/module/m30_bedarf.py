"""M30 – Nutzenergiebedarf je Energieart als Lastgang.

Ergebnis ist für jede Energieart (Wärme, Kälte, Strom) ein Lastgang in kW.
Quelle ist entweder eine eingelesene Zeitreihe oder ein Ersatzprofil.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from valeri.core.einheiten import Energieart
from valeri.core.kontext import Rechenkontext
from valeri.core.modul import Rechenmodul
from valeri.core.registry import registriere
from valeri.core.zeitreihe import Lastgang
from valeri.io.lastgang import lade_csv, synthetisiere


@registriere()
class Bedarf(Rechenmodul):
    id = "m30_bedarf"
    titel = "Nutzenergiebedarf und Lastgänge"
    grundlage = "Messwerte bzw. Ersatzprofil"
    liefert = ("bedarf.nutzenergie", "bedarf.jahresarbeit_kwh", "bedarf.spitzenlast_kw")

    def berechne(self, ctx: Rechenkontext) -> Mapping[str, Any]:
        lastgaenge: dict[Energieart, Lastgang] = {}

        for verbrauch in ctx.projekt.bedarf_fuer(ctx.variante):
            if verbrauch.jahresbedarf_kwh <= 0:
                continue
            quelle = verbrauch.lastgang
            name = f"{verbrauch.energieart.value}"

            if quelle.art == "datei":
                lastgang = lade_csv(quelle, name)
                gemessen = lastgang.summe_kwh()
                if abs(gemessen - verbrauch.jahresbedarf_kwh) / max(gemessen, 1.0) > 0.02:
                    ctx.notiere(
                        f"{name}: Jahressumme des Lastgangs ({gemessen:,.0f} kWh) weicht "
                        f"von der Vorgabe ({verbrauch.jahresbedarf_kwh:,.0f} kWh) ab – "
                        "Profil wurde auf die Vorgabe skaliert."
                    )
                lastgang = lastgang.skaliert_auf(verbrauch.jahresbedarf_kwh)
            elif quelle.art == "konstant":
                lastgang = Lastgang.konstant(
                    verbrauch.jahresbedarf_kwh / 8760.0, 60, name
                )
                ctx.notiere(f"{name}: Bandlast angesetzt – keine Spitzenlastaussage.")
            else:
                lastgang = synthetisiere(quelle, verbrauch.jahresbedarf_kwh, name)
                ctx.notiere(
                    f"{name}: Ersatzprofil verwendet. Spitzenlast und damit "
                    "Leistungspreis/Speicherauslegung sind vorläufig."
                )

            if verbrauch.spitzenlast_kw:
                # gemessene/vorgegebene Spitzenlast hat Vorrang vor der Profilform
                lastgang = _auf_spitzenlast(lastgang, verbrauch.spitzenlast_kw)
            if verbrauch.gleichzeitigkeit < 1.0:
                lastgang = lastgang.skaliert(verbrauch.gleichzeitigkeit)

            lastgaenge[verbrauch.energieart] = lastgang

        if not lastgaenge:
            ctx.notiere("Kein Bedarf vorhanden – Energiekosten werden zu 0 gerechnet.")

        return {
            "bedarf.nutzenergie": lastgaenge,
            "bedarf.jahresarbeit_kwh": {a: lg.summe_kwh() for a, lg in lastgaenge.items()},
            "bedarf.spitzenlast_kw": {
                a: lg.spitzenlast_kw() for a, lg in lastgaenge.items()
            },
        }


def _auf_spitzenlast(lastgang: Lastgang, ziel_kw: float) -> Lastgang:
    """Profil so verformen, dass Jahresarbeit erhalten bleibt und die
    Spitzenlast dem vorgegebenen Wert entspricht."""
    arbeit = lastgang.summe_kwh()
    p_max = lastgang.spitzenlast_kw()
    if p_max <= 0:
        return lastgang
    unten, oben = 0.1, 8.0
    for _ in range(80):
        x = (unten + oben) / 2
        werte = [p_max * (w / p_max) ** x for w in lastgang.werte_kw]
        probe = lastgang.mit_werten(werte).skaliert_auf(arbeit)
        if probe.spitzenlast_kw() > ziel_kw:
            oben = x
        else:
            unten = x
    x = (unten + oben) / 2
    werte = [p_max * (w / p_max) ** x for w in lastgang.werte_kw]
    return lastgang.mit_werten(werte).skaliert_auf(arbeit)
