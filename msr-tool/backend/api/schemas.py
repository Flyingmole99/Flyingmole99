"""Pydantic-Schemas für Request-Bodies der API."""
from __future__ import annotations

from pydantic import BaseModel, Field


class ProjektCreate(BaseModel):
    name: str
    kunde: str | None = None
    naming_profile_id: int | None = None   # Default: erstes 'ungekuerzt'-Profil
    bac_version_id: int | None = None       # Default: neueste Version


class AnlageCreate(BaseModel):
    gewerk_kg: str = Field(examples=["420"])
    anlage_kuerzel: str = Field(examples=["VBA"])
    nummer: int = 1
    teilanlage: int | None = None


class BaugruppeCreate(BaseModel):
    """Kern des Drag & Drop: ein Aggregat-Template auf eine Anlage ziehen."""
    aggregat_template_uuid: str
    kuerzel: str | None = None              # Default: aus Template-Kennung abgeleitet
    nummer: int | None = None               # Default: nächste freie Nummer
    medium_pos: str | None = None
    position: dict | None = None            # Canvas {x, y}
