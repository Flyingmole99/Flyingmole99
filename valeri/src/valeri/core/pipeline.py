"""Pipeline – bringt Module anhand ihrer Datenabhängigkeiten in Reihenfolge.

Die Reihenfolge wird *nicht* fest verdrahtet, sondern aus ``benoetigt`` /
``liefert`` topologisch abgeleitet. Ein neues Modul einhängen heißt daher:
registrieren, Verträge deklarieren – fertig.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from valeri.core.kontext import Rechenkontext
from valeri.core.modul import Rechenmodul
from valeri.core import registry
from valeri.modelle.projekt import Projekt, Variante


class PipelineFehler(RuntimeError):
    pass


def sortiere(module: Sequence[Rechenmodul]) -> list[Rechenmodul]:
    """Topologische Sortierung über die gelieferten/benötigten Schlüssel."""
    erzeuger: dict[str, Rechenmodul] = {}
    for m in module:
        for schluessel in m.liefert:
            if schluessel in erzeuger:
                raise PipelineFehler(
                    f"Schlüssel {schluessel!r} wird von {erzeuger[schluessel].id!r} "
                    f"und {m.id!r} geliefert – Mehrdeutigkeit."
                )
            erzeuger[schluessel] = m

    offen = list(module)
    erledigt: list[Rechenmodul] = []
    vorhanden: set[str] = set()

    while offen:
        bereit = [
            m
            for m in offen
            if all(
                b in vorhanden or b not in erzeuger  # extern gesetzte Werte zulassen
                for b in m.benoetigt
            )
        ]
        if not bereit:
            blockiert = {
                m.id: [b for b in m.benoetigt if b not in vorhanden] for m in offen
            }
            raise PipelineFehler(f"Zyklus oder fehlende Lieferanten: {blockiert}")
        # stabile Reihenfolge: nach id, damit Läufe reproduzierbar sind
        bereit.sort(key=lambda m: m.id)
        for m in bereit:
            erledigt.append(m)
            vorhanden.update(m.liefert)
            offen.remove(m)
    return erledigt


def berechne_variante(
    projekt: Projekt,
    variante: Variante,
    module: Iterable[Rechenmodul] | None = None,
) -> Rechenkontext:
    """Führt alle Module für genau eine Variante aus."""
    module = list(module) if module is not None else registry.instanzen()
    ctx = Rechenkontext(projekt=projekt, variante=variante)

    for modul in sortiere(module):
        if modul.optional and not modul.ist_anwendbar(ctx):
            continue
        fehlend = [b for b in modul.benoetigt if not ctx.hat(b)]
        if fehlend:
            if modul.optional:
                continue
            raise PipelineFehler(
                f"Modul {modul.id!r} benötigt {fehlend}, was nicht vorliegt."
            )
        ctx.betrete_modul(modul.id, modul.version, modul.grundlage)
        try:
            ergebnis = modul.berechne(ctx)
        finally:
            ctx.verlasse_modul()
        for schluessel, wert in dict(ergebnis).items():
            ctx.betrete_modul(modul.id, modul.version, modul.grundlage)
            ctx.setze(schluessel, wert)
            ctx.verlasse_modul()
    return ctx


def berechne_projekt(
    projekt: Projekt, module: Iterable[Rechenmodul] | None = None
) -> dict[str, Rechenkontext]:
    """Rechnet alle Varianten eines Projekts."""
    module = list(module) if module is not None else registry.instanzen()
    return {v.name: berechne_variante(projekt, v, module) for v in projekt.varianten}
