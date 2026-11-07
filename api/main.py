"""a2b API (FastAPI): the scene data for the web viewer and, in production, the built viewer itself from one origin.

Routes: GET /api/health, GET /api/demo-mode, GET /api/scene/points, GET /api/scene/stats,
GET /api/viewer/scene.{bin,splat,json} and GET /api/viewer/lod/{k}.{bin,splat} (the step-by-step build),
the same under /api/viewer-auto/ (the automatic build), GET /api/compare.json (scripts/compare_builds.py),
GET /api/images/{name} (the numbered step images and the automatic build's object pictures; a picture that is not on
this machine sends the browser to the public copy in the GitHub repository), and / (web/dist: index.html,
capture.html, assets/ and the web/public files) once the viewer has been built.
The routers of AGENTS.md S5 (proposals, scene graph, assets, copilot, snapshots) land with M4-M9.

    uv run uvicorn api.main:app --reload --port 8000     # local API (the Vite dev server proxies /api to it)
    docker run -p 8080:8080 a2b:local                     # production image: API + viewer on :8080 (docs/DEPLOY.md)

Environment (all optional):
    A2B_DATA            data folder (default <repo>/data); the exports live in <A2B_DATA>/derived/{viewer,viewer_auto}
    A2B_WEB_DIST        built frontend (default <repo>/web/dist); not mounted when missing (local dev uses Vite)
    A2B_IMAGES          folders holding the step images, ":"-separated (default <repo>/images:<repo>/autoscene/out/images)
    A2B_IMAGE_FALLBACK  base URL for step images that are not in those folders (default: this repository on
                        raw.githubusercontent.com; empty string = no redirect, plain 404)
    A2B_ORIGINS         extra CORS origins, comma-separated (same-origin needs none)
    DEMO_MODE           1 = demo mode flag for the UI
"""

from __future__ import annotations

import os
import re
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.responses import FileResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parents[1]
LOCAL_ORIGINS = ["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost:5180", "http://127.0.0.1:5180"]
# NNNN_YYYYMMDD-HHMMSS[_tag].png, the image-name rule of pipeline/stepbuild/state.py (no path parts, so no traversal);
# the automatic build's pictures carry a tag (…_007_chair_1_a.png), the manual build's step images none
IMAGE_NAME = re.compile(r"^\d{4,}_\d{8}-\d{6}(_[\w-]+)?\.png$")
# detail levels written by scripts/lod.py: lod/<k>.bin and lod/<k>.splat
LOD_NAME = re.compile(r"^\d{1,2}\.(bin|splat)$")
# the step images are in git (images/) and a sample of the automatic pictures as JPEG (autoscene/out/samples/), so a
# deployment that does not carry them can point the browser there
GITHUB_RAW = "https://raw.githubusercontent.com/Haaparanta/SinceAI_2026_Valmet/main"
# URL folder -> (export folder under data/derived, how to make it)
BUILDS = {
    "viewer": ("viewer", "run `make viewer` (scripts/export_viewer_scene.py)"),
    "viewer-auto": ("viewer_auto", "run `make viewer-auto` (scripts/export_autoscene_viewer.py)"),
}


def _flag(name: str) -> bool:
    return os.environ.get(name, "0").strip().lower() not in ("", "0", "false", "no")


def create_app(
    data_dir: Path | None = None,
    web_dist: Path | None = None,
    image_dirs: list[Path] | None = None,
    image_fallback: str | None = None,
) -> FastAPI:
    data = Path(data_dir or os.environ.get("A2B_DATA") or ROOT / "data")
    derived = data / "derived"
    dist = Path(web_dist or os.environ.get("A2B_WEB_DIST") or ROOT / "web" / "dist")
    if image_dirs is None:
        env_dirs = os.environ.get("A2B_IMAGES")
        image_dirs = [Path(p) for p in env_dirs.split(":") if p] if env_dirs else [ROOT / "images", ROOT / "autoscene" / "out" / "images"]
    fallback = (os.environ.get("A2B_IMAGE_FALLBACK", GITHUB_RAW) if image_fallback is None else image_fallback).rstrip("/")
    demo = _flag("DEMO_MODE")
    revision = os.environ.get("K_REVISION", "local")  # set by Cloud Run

    app = FastAPI(title="a2b API", version="0.3.0", description="Approve-to-Build Twin. All metadata is SYNTHETIC.")
    extra = [o.strip() for o in os.environ.get("A2B_ORIGINS", "").split(",") if o.strip()]
    app.add_middleware(CORSMiddleware, allow_origins=LOCAL_ORIGINS + extra, allow_methods=["GET"], allow_headers=["*"])

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

    def export_file(build: str, name: str, media_type: str) -> FileResponse:
        """A file of one build's export. Short cache + ETag: a new export shows within a minute, unchanged files cost
        a 304. Never pre-compressed: the viewer reads Content-Length to show download progress."""
        if build not in BUILDS:
            raise HTTPException(404, f"no build {build!r}: viewer or viewer-auto")
        folder, hint = BUILDS[build]
        path = derived / folder / name
        if not path.exists():
            raise HTTPException(404, f"{folder}/{name} missing: {hint}")
        return FileResponse(path, media_type=media_type, headers={"Cache-Control": "public, max-age=60"})

    @app.get("/api/health")
    def health() -> dict:
        return {
            "ok": True,
            "demo_mode": demo,
            "revision": revision,
            "viewer_scene": (derived / "viewer" / "scene.json").exists(),
            "viewer_auto": (derived / "viewer_auto" / "scene.json").exists(),
            "compare": (derived / "compare.json").exists(),
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

    @app.get("/api/compare.json")
    def compare_builds() -> FileResponse:
        """Manual vs automatic build, part by part (scripts/compare_builds.py): the viewer's comparison in ?scene=both."""
        path = derived / "compare.json"
        if not path.exists():
            raise HTTPException(404, "compare.json missing: run `make compare` (scripts/compare_builds.py)")
        return FileResponse(path, media_type="application/json", headers={"Cache-Control": "public, max-age=60"})

    @app.get("/api/images/{name}")
    def step_image(name: str):
        """One numbered build-step image (the viewer's part card shows the images a part was accepted with): from
        images/ (the manual build), else autoscene/out/images/ (the automatic build's object pictures), else the
        public copy in the GitHub repository (the manual images as they are, the automatic ones as the JPEG sample)."""
        m = IMAGE_NAME.match(name)
        if not m:
            raise HTTPException(404, f"no step image {name!r}")
        for folder in image_dirs:
            path = folder / name
            if path.is_file():
                return FileResponse(path, media_type="image/png", headers={"Cache-Control": "public, max-age=86400"})
        if not fallback:
            raise HTTPException(404, f"no step image {name!r}")
        url = f"{fallback}/autoscene/out/samples/{name[:-4]}.jpg" if m.group(1) else f"{fallback}/images/{name}"
        return RedirectResponse(url, status_code=307, headers={"Cache-Control": "public, max-age=3600"})

    @app.get("/api/{build}/scene.bin")
    def export_scene_bin(build: str) -> FileResponse:
        """The build as one point cloud: float32 xyz | uint16 part | uint8 rgb | uint8 size_mm (scripts/export_*.py)."""
        return export_file(build, "scene.bin", "application/octet-stream")

    @app.get("/api/{build}/scene.splat")
    def export_scene_splat(build: str) -> FileResponse:
        """The same rows as Gaussian splats (.splat layout) for the viewer's Splats mode (exports without lod/)."""
        return export_file(build, "scene.splat", "application/octet-stream")

    @app.get("/api/{build}/scene.json")
    def export_scene_json(build: str) -> FileResponse:
        """Parts (name, kind, count, [start, end) range, bbox), room bounds, dollhouse cut and the detail levels."""
        return export_file(build, "scene.json", "application/json")

    @app.get("/api/{build}/lod/{name}")
    def export_lod(build: str, name: str) -> FileResponse:
        """One detail level (scripts/lod.py), streamed by the viewer coarse to fine."""
        if not LOD_NAME.match(name):
            raise HTTPException(404, f"no detail level {name!r}")
        return export_file(build, f"lod/{name}", "application/octet-stream")

    # The built viewer last, so /api/* wins. html=True serves index.html for "/" and capture.html by name. Its own
    # gzip: JS, CSS and HTML shrink 3-4x on the fly, while the API's binaries above pass through untouched.
    if (dist / "index.html").exists():
        site = FastAPI(openapi_url=None, docs_url=None, redoc_url=None)
        site.add_middleware(GZipMiddleware, minimum_size=1024)
        site.mount("/", StaticFiles(directory=dist, html=True), name="web")
        app.mount("/", site)
    return app


app = create_app()
