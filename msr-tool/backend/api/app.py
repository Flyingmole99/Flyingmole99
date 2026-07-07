"""FastAPI-Anwendung des MSR-Planungstools.

Start (Entwicklung):
    DATABASE_URL="host=/var/run/postgresql dbname=msr user=postgres" \
        uvicorn api.app:app --reload
"""
from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import FastAPI

from .db import close_pool, init_pool
from .routers import catalog, dokumente, projekte


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_pool()
    yield
    close_pool()


app = FastAPI(
    title="MSR-Planungstool API",
    version="0.1.0",
    summary="Anlagen aufbauen, Baugruppen per Drag & Drop zuordnen, "
            "Datenpunkt-/Kabellisten generieren (BACtwin).",
    lifespan=lifespan,
)

app.include_router(catalog.router)
app.include_router(projekte.router)
app.include_router(dokumente.router)


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}
