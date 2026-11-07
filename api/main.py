"""a2b API (FastAPI): serves the scene data and, in production, the built web viewer from one origin.

Routes: GET /api/health, GET /api/demo-mode, GET /api/scene/points, GET /api/scene/stats,
GET /api/viewer/scene.bin, GET /api/viewer/scene.json, and / (web/dist: index.html, capture.html, assets/) when built.
The routers of AGENTS.md S5 (proposals, scene graph, assets, copilot, snapshots) land with M4-M9.

    uv run uvicorn api.main:app --reload --port 8000           # local API (web dev server proxies /api to it)
    docker run -p 8080:8080 a2b                                 # production image: API + viewer on :8080

Environment (all optional):
    A2B_DATA      data folder (default: <repo>/data); the viewer files live in <A2B_DATA>/derived/viewer/
    A2B_WEB_DIST  built frontend (default: <repo>/web/dist); not mounted when missing (local dev uses Vite)
    A2B_ORIGINS   extra CORS origins, comma-separated (same-origin needs none)
    DEMO_MODE     1 = demo mode flag for the UI
"""

from __future__ import annotations

import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parents[1]
LOCAL_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:5180", "http://127.0.0.1:5180"]


def _flag(name: str) -> bool:
    return os.environ.get(name, "0").strip().lower() not in ("", "0", "false", "no")


def create_app(data_dir: Path | None = None, web_dist: Path | None = None) -> FastAPI:
    data = Path(data_dir or os.environ.get("A2B_DATA") or ROOT / "data")
    derived = data / "derived"
    viewer = derived / "viewer"
    dist = Path(web_dist or os.environ.get("A2B_WEB_DIST") or ROOT / "web" / "dist")
    demo = _flag("DEMO_MODE")
    revision = os.environ.get("K_REVISION", "local")  # set by Cloud Run

    app = FastAPI(title="a2b API", version="0.2.0", description="Approve-to-Build Twin. All metadata is SYNTHETIC.")
    extra = [o.strip() for o in os.environ.get("A2B_ORIGINS", "").split(",") if o.strip()]
    app.add_middleware(CORSMiddleware, allow_origins=LOCAL_ORIGINS + extra, allow_methods=["GET"], allow_headers=["*"])
    # JS/CSS/JSON on the fly; scene.bin is served pre-compressed below and passes through untouched
    app.add_middleware(GZipMiddleware, minimum_size=1024)

    @app.middleware("http")
    async def cache_headers(request: Request, call_next):
        response = await call_next(request)
        path = request.url.path
        if "cache-control" not in response.headers and not path.startswith("/api/"):
            if path.startswith("/assets/"):  # Vite file names carry a content hash
                response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
            elif path == "/" or path.endswith(".html"):  # pages: always revalidate, so a deploy shows at once
                response.headers["Cache-Control"] = "no-cache"
            else:  # web/public files (icons, og-image, robots.txt, sitemap.xml, manifest): unhashed names
                response.headers["Cache-Control"] = "public, max-age=3600"
        response.headers.setdefault("X-Content-Type-Options", "nosniff")
        return response

    def derived_file(name: str, media_type: str) -> FileResponse:
        path = derived / name
        if not path.exists():
            raise HTTPException(404, f"{name} missing: run `uv run python pipeline/01_clean.py` first")
        return FileResponse(path, media_type=media_type, headers={"Cache-Control": "public, max-age=3600"})

    def viewer_file(request: Request, name: str, media_type: str) -> FileResponse:
        path = viewer / name
        if not path.exists():
            raise HTTPException(404, f"viewer/{name} missing: run `make viewer`")
        # short cache + ETag revalidation: a new export shows up within a minute, unchanged files cost a 304
        headers = {"Cache-Control": "public, max-age=60", "Vary": "Accept-Encoding"}
        gz = path.with_name(name + ".gz")
        if gz.exists() and "gzip" in request.headers.get("accept-encoding", ""):
            return FileResponse(gz, media_type=media_type, headers={**headers, "Content-Encoding": "gzip"})
        return FileResponse(path, media_type=media_type, headers=headers)

    @app.get("/api/health")
    def health() -> dict:
        return {
            "ok": True,
            "demo_mode": demo,
            "revision": revision,
            "viewer_scene": (viewer / "scene.bin").exists(),
            "web": (dist / "index.html").exists(),
            "scene_points": (derived / "scene_points.bin").exists(),
        }

    @app.get("/api/demo-mode")
    def demo_mode() -> dict:
        return {"enabled": demo}

    @app.get("/api/scene/points")
    def scene_points() -> FileResponse:
        """scene_points.bin: uint32 count | float32 xyz*count | uint8 rgb*count (AGENTS.md S3)."""
        return derived_file("scene_points.bin", "application/octet-stream")

    @app.get("/api/scene/stats")
    def scene_stats() -> FileResponse:
        """clean_stats.json written by pipeline/01_clean.py (kept count, bounds, floor_y)."""
        return derived_file("clean_stats.json", "application/json")

    @app.get("/api/viewer/scene.bin")
    def viewer_scene_bin(request: Request) -> FileResponse:
        """The step-by-step build as one point cloud (layout in scripts/export_viewer_scene.py)."""
        return viewer_file(request, "scene.bin", "application/octet-stream")

    @app.get("/api/viewer/scene.json")
    def viewer_scene_json(request: Request) -> FileResponse:
        """Parts (name, kind, count, [start, end) range, bbox), room bounds and dollhouse cut for scene.bin."""
        return viewer_file(request, "scene.json", "application/json")

    # The built viewer last, so /api/* wins. html=True serves index.html for "/" and capture.html by name.
    if (dist / "index.html").exists():
        app.mount("/", StaticFiles(directory=dist, html=True), name="web")
    return app


app = create_app()
