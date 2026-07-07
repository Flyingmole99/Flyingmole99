"""openpyxl-Hilfen: Workbook per Glob finden, Blätter als Zeilen liefern."""
from __future__ import annotations

import glob
import os

import openpyxl
import yaml

MAPPING_DIR = os.path.join(os.path.dirname(__file__), "mapping")


def load_mapping(name: str) -> dict:
    """Lädt ein Mapping-YAML (z. B. 'bibliothek1')."""
    with open(os.path.join(MAPPING_DIR, f"{name}.yaml"), encoding="utf-8") as fh:
        return yaml.safe_load(fh)


def find_workbook(directory: str, pattern: str) -> str:
    """Findet genau eine Datei zum Glob-Muster im Verzeichnis."""
    matches = sorted(glob.glob(os.path.join(directory, pattern)))
    if not matches:
        raise FileNotFoundError(f"Keine Datei für Muster {pattern!r} in {directory}")
    return matches[0]


def sheet_rows(path: str, sheet: str) -> list[tuple]:
    """Liefert alle Zeilen eines Blatts als Liste von Werte-Tupeln."""
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    try:
        ws = wb[sheet]
        return list(ws.iter_rows(values_only=True))
    finally:
        wb.close()


def cell(row: tuple, idx) -> object:
    """Sicherer Spaltenzugriff (None bei Überlauf/None-Index)."""
    if idx is None or idx >= len(row):
        return None
    return row[idx]
