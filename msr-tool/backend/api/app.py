"""FastAPI-Anwendung des MSR-Planungstools.

Start (Entwicklung):
    DATABASE_URL="host=/var/run/postgresql dbname=msr user=postgres" \
        uvicorn api.app:app --reload
"""
from __future__ import annotations

import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from .db import close_pool, init_pool
from .routers import catalog, dokumente, projekte

FRONTEND_DIR = os.environ.get(
    "FRONTEND_DIR",
    os.path.join(os.path.dirname(__file__), "..", "..", "frontend"),
)


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

# CORS für einen separaten Frontend-Dev-Server (z. B. Vite) – im Auslieferbetrieb
# wird das Frontend same-origin unter /app bereitgestellt und braucht es nicht.
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], allow_methods=["*"], allow_headers=["*"],
)

app.include_router(catalog.router)
app.include_router(projekte.router)
app.include_router(dokumente.router)


@app.get("/health", tags=["meta"])
def health():
    return {"status": "ok"}


# Frontend (build-freie Single-Page-App) same-origin unter /app ausliefern.
if os.path.isdir(FRONTEND_DIR):
    @app.get("/", include_in_schema=False)
    def _root():
        return RedirectResponse("/app/")

    app.mount("/app", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
