"""M61 – Kennwertableitung aus Produktkategorie und AfA-Tabelle.

Für jede Investitionsposition werden abgeleitet:
  * technische Nutzungsdauer, Instandsetzung, Wartung, Bedienaufwand
    -> Produktkategorie in Anlehnung an VDI 2067 Blatt 1
  * steuerliche Nutzungsdauer (AfA)
    -> AfA-Schlüssel in Anlehnung an die AfA-Tabelle des BMF

Manuelle Eingaben an der Position haben immer Vorrang. Jeder Wert wird mit
seiner Herkunft protokolliert; ungeprüfte Katalogwerte erzeugen einen Hinweis.
"""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from valeri.core.kontext import Rechenkontext
from valeri.core.modul import Rechenmodul
from valeri.core.registry import registriere
from valeri.daten import Katalog, katalog
from valeri.modelle.investition import Investitionsposition, Positionsdaten

#: Rückfallwerte, wenn weder Kategorie noch manuelle Eingabe vorliegen
VORGABE_NUTZUNGSDAUER_A = 20.0
VORGABE_AFA_A = 20.0


@registriere()
class Kennwertableitung(Rechenmodul):
    id = "m61_kennwerte"
    titel = "Nutzungsdauern, Wartung und Instandhaltung ableiten"
    grundlage = "VDI 2067 Blatt 1 (Kategoriekatalog) / AfA-Tabelle BMF"
    benoetigt = ("invest.positionen_roh",)
    liefert = ("invest.positionen", "invest.foerderung_eur", "invest.katalogstand")

    #: austauschbar: eigener Katalog per Konstruktor
    def __init__(self, eigener_katalog: Katalog | None = None) -> None:
        self._katalog = eigener_katalog or katalog()

    def berechne(self, ctx: Rechenkontext) -> Mapping[str, Any]:
        positionen: list[Investitionsposition] = ctx.get("invest.positionen_roh")
        aufbereitet: list[Positionsdaten] = []
        ungeprueft: set[str] = set()

        gesamtfoerderung = ctx.variante.investition.gesamtfoerderung
        summe_invest = sum(p.investition_eur() for p in positionen)

        for position in positionen:
            daten = self._ableiten(position, ctx)

            # Förderung: positionsbezogen, sonst anteilig aus der Gesamtförderung
            if position.foerderung:
                daten.foerderung_eur = position.foerderung.hoehe(daten.investition_eur)
                daten.herkunft["foerderung"] = "position"
            elif gesamtfoerderung and summe_invest > 0:
                anteil = daten.investition_eur / summe_invest
                daten.foerderung_eur = gesamtfoerderung.hoehe(summe_invest) * anteil
                daten.herkunft["foerderung"] = "gesamtfoerderung (anteilig)"

            if position.kategorie and not self._ist_geprueft(position.kategorie):
                ungeprueft.add(position.kategorie)
            aufbereitet.append(daten)

        if ungeprueft:
            ctx.notiere(
                "Ungeprüfte Katalogwerte verwendet: "
                + ", ".join(sorted(ungeprueft))
                + ". Vor Verwendung im Nachweis gegen VDI 2067 bzw. AfA-Tabelle prüfen."
            )

        return {
            "invest.positionen": aufbereitet,
            "invest.foerderung_eur": sum(p.foerderung_eur for p in aufbereitet),
            "invest.katalogstand": {
                "vdi2067": self._katalog.vdi_version,
                "afa": self._katalog.afa_version,
            },
        }

    # ------------------------------------------------------------------ intern

    def _ableiten(
        self, position: Investitionsposition, ctx: Rechenkontext
    ) -> Positionsdaten:
        investition = position.investition_eur()
        herkunft: dict[str, str] = {}
        kategorie = None

        if position.kategorie:
            try:
                kategorie = self._katalog.kategorie(position.kategorie)
            except KeyError as fehler:
                ctx.notiere(str(fehler))

        def waehle(manuell: float | None, aus_katalog: float | None, feld: str) -> float:
            if manuell is not None:
                herkunft[feld] = "manuell"
                return manuell
            if aus_katalog is not None and kategorie is not None:
                herkunft[feld] = f"vdi2067:{kategorie.schluessel}"
                return aus_katalog
            herkunft[feld] = "vorgabe"
            return 0.0

        nutzungsdauer = (
            position.nutzungsdauer_a
            if position.nutzungsdauer_a is not None
            else (kategorie.nutzungsdauer_a if kategorie else VORGABE_NUTZUNGSDAUER_A)
        )
        herkunft["nutzungsdauer_a"] = (
            "manuell"
            if position.nutzungsdauer_a is not None
            else (f"vdi2067:{kategorie.schluessel}" if kategorie else "vorgabe")
        )

        instand_anteil = waehle(
            position.instandsetzung_anteil,
            kategorie.instandsetzung_anteil if kategorie else None,
            "instandsetzung_anteil",
        )
        wartung_anteil = waehle(
            position.wartung_anteil,
            kategorie.wartung_anteil if kategorie else None,
            "wartung_anteil",
        )
        bedienung = waehle(
            position.bedienaufwand_h_a,
            kategorie.bedienaufwand_h_a if kategorie else None,
            "bedienaufwand_h_a",
        )
        afa_dauer, afa_herkunft = self._afa(position, kategorie, ctx)
        herkunft["afa_dauer_a"] = afa_herkunft

        return Positionsdaten(
            position=position,
            investition_eur=investition,
            nutzungsdauer_a=nutzungsdauer,
            afa_dauer_a=afa_dauer,
            instandsetzung_eur_a=investition * instand_anteil,
            wartung_eur_a=investition * wartung_anteil,
            bedienaufwand_h_a=bedienung,
            herkunft=herkunft,
        )

    def _afa(self, position, kategorie, ctx: Rechenkontext) -> tuple[float, str]:
        if position.afa_dauer_a is not None:
            return position.afa_dauer_a, "manuell"
        schluessel = position.afa_schluessel or (
            kategorie.afa_schluessel if kategorie else None
        )
        if schluessel:
            try:
                eintrag = self._katalog.afa_eintrag(schluessel)
                return eintrag.nutzungsdauer_a, f"afa:{schluessel}"
            except KeyError as fehler:
                ctx.notiere(str(fehler))
        return VORGABE_AFA_A, "vorgabe"

    def _ist_geprueft(self, kategorie: str) -> bool:
        try:
            eintrag = self._katalog.kategorie(kategorie)
        except KeyError:
            return True  # Fehler wurde bereits gemeldet
        if not eintrag.geprueft:
            return False
        if eintrag.afa_schluessel:
            try:
                return self._katalog.afa_eintrag(eintrag.afa_schluessel).geprueft
            except KeyError:
                return False
        return True
