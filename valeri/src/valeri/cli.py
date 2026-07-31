"""Kommandozeile.

    valeri rechnen projekt.yaml [--variante NAME] [--json ergebnis.json]
    valeri katalog [suchbegriff]
    valeri module
    valeri sensitivitaet projekt.yaml --variante NAME
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from valeri import rechne
from valeri.core import registry
from valeri.core.pipeline import sortiere
from valeri.daten import katalog
from valeri.io import lade_projekt
from valeri.module.vergleich import (
    sensitivitaet,
    sensitivitaet_energiepreis,
    sensitivitaet_investition,
    sensitivitaet_zins,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="valeri",
        description="Wirtschaftlichkeitsberechnung nach DIN EN 17463 und VDI 2067",
    )
    unter = parser.add_subparsers(dest="befehl", required=True)

    p_rechnen = unter.add_parser("rechnen", help="Projekt berechnen")
    p_rechnen.add_argument("projekt", type=Path)
    p_rechnen.add_argument("--variante", help="nur diese Variante ausgeben")
    p_rechnen.add_argument("--json", type=Path, help="Kennzahlen als JSON speichern")

    p_katalog = unter.add_parser("katalog", help="Produktkategorien und AfA-Schlüssel")
    p_katalog.add_argument("suche", nargs="?", default="")

    unter.add_parser("module", help="registrierte Rechenmodule und ihre Verträge")

    p_sens = unter.add_parser("sensitivitaet", help="Sensitivitätsanalyse")
    p_sens.add_argument("projekt", type=Path)
    p_sens.add_argument("--variante", required=True)

    args = parser.parse_args(argv)

    if args.befehl == "rechnen":
        return _rechnen(args)
    if args.befehl == "katalog":
        return _katalog(args)
    if args.befehl == "module":
        return _module()
    if args.befehl == "sensitivitaet":
        return _sensitivitaet(args)
    return 1


def _rechnen(args) -> int:
    projekt = lade_projekt(args.projekt)
    ergebnis = rechne(projekt)

    if args.variante:
        if args.variante not in ergebnis.varianten:
            print(f"Unbekannte Variante: {args.variante}", file=sys.stderr)
            return 2
        print(ergebnis.bericht(args.variante))
    else:
        print(ergebnis.gesamtbericht())

    if args.json:
        daten = {
            name: {
                "kennzahlen": vars(ctx.get("ergebnis.kennzahlen")),
                "valeri": ctx.get("ergebnis.valeri"),
                "vdi2067": ctx.get("ergebnis.vdi2067"),
                "hinweise": ctx.hinweise,
            }
            for name, ctx in ergebnis.varianten.items()
        }
        args.json.write_text(
            json.dumps(daten, indent=2, ensure_ascii=False, default=str), encoding="utf-8"
        )
        print(f"\nKennzahlen gespeichert: {args.json}")
    return 0


def _katalog(args) -> int:
    k = katalog()
    print(f"VDI-2067-Kategorien (Katalogstand {k.vdi_version})")
    treffer = k.suche(args.suche) if args.suche else list(k.kategorien.values())
    for kategorie in sorted(treffer, key=lambda x: x.schluessel):
        marke = " " if kategorie.geprueft else "!"
        print(
            f" {marke} {kategorie.schluessel:<38} ND {kategorie.nutzungsdauer_a:>4.0f} a  "
            f"Inst {kategorie.instandsetzung_anteil:>6.2%}  "
            f"Wart {kategorie.wartung_anteil:>6.2%}  "
            f"Bed {kategorie.bedienaufwand_h_a:>4.0f} h/a  "
            f"-> afa:{kategorie.afa_schluessel}"
        )
    print(f"\nAfA-Schlüssel (Katalogstand {k.afa_version})")
    for eintrag in sorted(k.afa.values(), key=lambda x: x.schluessel):
        marke = " " if eintrag.geprueft else "!"
        print(f" {marke} {eintrag.schluessel:<24} {eintrag.nutzungsdauer_a:>4.0f} a  "
              f"{eintrag.fundstelle}")
    print("\n! = Katalogwert noch nicht gegen Norm bzw. AfA-Tabelle geprüft")
    return 0


def _module() -> int:
    module = registry.instanzen()
    print("Ausführungsreihenfolge (aus den Daten-Verträgen abgeleitet):\n")
    for i, modul in enumerate(sortiere(module), start=1):
        print(f"{i:>2}. {modul.id:<20} {modul.titel}")
        print(f"    Grundlage : {modul.grundlage}")
        print(f"    benötigt  : {', '.join(modul.benoetigt) or '-'}")
        print(f"    liefert   : {', '.join(modul.liefert) or '-'}")
    return 0


def _sensitivitaet(args) -> int:
    projekt = lade_projekt(args.projekt)
    punkte = sensitivitaet(
        projekt,
        args.variante,
        {
            "Energiepreis": sensitivitaet_energiepreis,
            "Investition": sensitivitaet_investition,
            "Kapitalkosten": sensitivitaet_zins,
        },
    )
    print(f"Sensitivität – Variante {args.variante}\n")
    print(f"{'Parameter':<16}{'Faktor':>10}{'Kapitalwert':>18}")
    for punkt in punkte:
        betrag = _de(punkt.kapitalwert_eur)
        print(f"{punkt.parameter:<16}{punkt.faktor:>10.2f}{betrag:>18}")
    return 0


def _de(wert: float, nachkomma: int = 0) -> str:
    text = f"{wert:,.{nachkomma}f}"
    return text.replace(",", "\x00").replace(".", ",").replace("\x00", ".")


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
