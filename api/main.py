"""a2b API (FastAPI) - scaffold.

Routes now: GET /api/health, GET /api/demo-mode, GET /api/scene/points, GET /api/scene/stats.
The routers of AGENTS.md S5 (proposals, scene graph, assets, copilot, snapshots) land with M4-M9.

    uv run uvicorn api.main:app --reload --port 8000
"""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DERIVED = DATA / "derived"
DEMO_MODE = os.environ.get("DEMO_MODE", "0").strip().lower() not in ("", "0", "false", "no")

app = FastAPI(title="a2b API", version="0.1.0", description="Approve-to-Build Twin. All metadata is SYNTHETIC.")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


def _derived_file(name: str, media_type: str) -> FileResponse:
    path = DERIVED / name
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"{name} missing: run `uv run python pipeline/01_clean.py` first")
    return FileResponse(path, media_type=media_type, headers={"Cache-Control": "public, max-age=3600"})


@app.get("/api/health")
def health() -> dict:
    return {"ok": True, "demo_mode": DEMO_MODE, "scene_points": (DERIVED / "scene_points.bin").exists()}


@app.get("/api/demo-mode")
def demo_mode() -> dict:
    return {"enabled": DEMO_MODE}


@app.get("/api/scene/points")
def scene_points() -> FileResponse:
    """scene_points.bin: uint32 count | float32 xyz*count | uint8 rgb*count (AGENTS.md S3)."""
    return _derived_file("scene_points.bin", "application/octet-stream")


@app.get("/api/scene/stats")
def scene_stats() -> FileResponse:
    """clean_stats.json written by pipeline/01_clean.py (kept count, bounds, floor_y)."""
    return _derived_file("clean_stats.json", "application/json")
