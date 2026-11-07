"""a2b API (FastAPI) - scaffold.

Routes now: GET /api/health, GET /api/demo-mode, GET /api/scene/points, GET /api/scene/stats,
GET /api/viewer/scene.{bin,splat,json} (the step-by-step build), GET /api/viewer-auto/scene.{bin,splat,json} (the
automatic build), GET /api/images/{name} (the numbered step images; also the automatic build's object pictures),
GET /api/compare.json (manual vs automatic build, scripts/compare_builds.py).
The routers of AGENTS.md S5 (proposals, scene graph, assets, copilot, snapshots) land with M4-M9.

    uv run uvicorn api.main:app --reload --port 8000
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
DERIVED = DATA / "derived"
IMAGES = ROOT / "images"
AUTOSCENE_IMAGES = ROOT / "autoscene" / "out" / "images"
# NNNN_YYYYMMDD-HHMMSS[_tag].png, the image-name rule of pipeline/stepbuild/state.py (no path parts, so no traversal)
IMAGE_NAME = re.compile(r"^\d{4,}_\d{8}-\d{6}(?:_[\w-]+)?\.png$")
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


def _viewer_file(name: str, media_type: str, folder: str = "viewer") -> FileResponse:
    path = DERIVED / folder / name
    script = "export_viewer_scene.py" if folder == "viewer" else "export_autoscene_viewer.py"
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"{folder}/{name} missing: run `uv run python scripts/{script}`")
    return FileResponse(path, media_type=media_type, headers={"Cache-Control": "no-cache"})


@app.get("/api/viewer/scene.bin")
def viewer_scene_bin() -> FileResponse:
    """The step-by-step build as one point cloud (layout in scripts/export_viewer_scene.py)."""
    return _viewer_file("scene.bin", "application/octet-stream")


@app.get("/api/viewer/scene.splat")
def viewer_scene_splat() -> FileResponse:
    """The same rows as Gaussian splats (.splat layout) for the viewer's Splats mode."""
    return _viewer_file("scene.splat", "application/octet-stream")


@app.get("/api/viewer/scene.json")
def viewer_scene_json() -> FileResponse:
    """Parts (name, kind, count, [start, end) range, bbox), room bounds and dollhouse cut for scene.bin."""
    return _viewer_file("scene.json", "application/json")


@app.get("/api/viewer-auto/scene.bin")
def viewer_auto_scene_bin() -> FileResponse:
    """The automatic build (autoscene) as one point cloud, same layout (scripts/export_autoscene_viewer.py)."""
    return _viewer_file("scene.bin", "application/octet-stream", "viewer_auto")


@app.get("/api/viewer-auto/scene.splat")
def viewer_auto_scene_splat() -> FileResponse:
    """The automatic build as Gaussian splats (.splat layout) for the viewer's Splats mode."""
    return _viewer_file("scene.splat", "application/octet-stream", "viewer_auto")


@app.get("/api/viewer-auto/scene.json")
def viewer_auto_scene_json() -> FileResponse:
    """Objects of the automatic build (name, label, kind, source, confidence, range, bbox, obb)."""
    return _viewer_file("scene.json", "application/json", "viewer_auto")


@app.get("/api/compare.json")
def compare_builds() -> FileResponse:
    """Manual vs automatic build, part by part (scripts/compare_builds.py): the viewer's comparison in ?scene=both."""
    path = DERIVED / "compare.json"
    if not path.exists():
        raise HTTPException(status_code=404, detail="compare.json missing: run `uv run python scripts/compare_builds.py`")
    return FileResponse(path, media_type="application/json", headers={"Cache-Control": "no-cache"})


@app.get("/api/images/{name}")
def step_image(name: str) -> FileResponse:
    """One numbered build-step image (the viewer's info card shows the images a part was accepted with): from
    images/ (the manual build), else from autoscene/out/images/ (the automatic build's object pictures)."""
    if not IMAGE_NAME.match(name):
        raise HTTPException(status_code=404, detail=f"no step image {name!r}")
    for folder in (IMAGES, AUTOSCENE_IMAGES):
        path = folder / name
        if path.is_file():
            return FileResponse(path, media_type="image/png", headers={"Cache-Control": "public, max-age=86400"})
    raise HTTPException(status_code=404, detail=f"no step image {name!r}")


@app.get("/api/scene/stats")
def scene_stats() -> FileResponse:
    """clean_stats.json written by pipeline/01_clean.py (kept count, bounds, floor_y)."""
    return _derived_file("clean_stats.json", "application/json")
