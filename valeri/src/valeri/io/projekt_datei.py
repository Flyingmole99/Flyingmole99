"""Projektdateien laden und speichern (YAML/JSON)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import yaml

from valeri.modelle.projekt import Projekt


def lade_projekt(pfad: str | Path) -> Projekt:
    pfad = Path(pfad)
    roh = _lade_roh(pfad)
    return Projekt.model_validate(roh)


def speichere_projekt(projekt: Projekt, pfad: str | Path) -> Path:
    pfad = Path(pfad)
    daten = projekt.model_dump(mode="json", exclude_defaults=False)
    if pfad.suffix.lower() in (".yaml", ".yml"):
        pfad.write_text(
            yaml.safe_dump(daten, allow_unicode=True, sort_keys=False), encoding="utf-8"
        )
    else:
        pfad.write_text(
            json.dumps(daten, indent=2, ensure_ascii=False), encoding="utf-8"
        )
    return pfad


def _lade_roh(pfad: Path) -> dict[str, Any]:
    text = pfad.read_text(encoding="utf-8")
    if pfad.suffix.lower() in (".yaml", ".yml"):
        return yaml.safe_load(text)
    return json.loads(text)
