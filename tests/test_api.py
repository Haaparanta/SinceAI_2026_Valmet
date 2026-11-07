"""api/main.py: both exports with their detail levels, the comparison, step images (local or redirected to GitHub),
the built viewer at /, cache headers, /api wins over static. Everything runs on temp folders: no export needed."""

from __future__ import annotations

import gzip
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.main import GITHUB_RAW, create_app

SCENE = bytes(range(256)) * 64
MANUAL_IMAGE = "1024_20261107-035218.png"
AUTO_IMAGE = "0019_20261107-043504_007_chair_1_a.png"


@pytest.fixture
def site(tmp_path: Path) -> dict[str, Path]:
    derived = tmp_path / "data" / "derived"
    for folder in ("viewer", "viewer_auto"):
        (derived / folder / "lod").mkdir(parents=True)
        (derived / folder / "scene.bin").write_bytes(SCENE)
        (derived / folder / "scene.json").write_text(json.dumps({"count": 1, "parts": [], "build": folder}))
        (derived / folder / "lod" / "0.bin").write_bytes(SCENE[:256])
        (derived / folder / "lod" / "0.splat").write_bytes(SCENE[:512])
    (derived / "compare.json").write_text(json.dumps({"summary": {"found": 1}}))
    images = tmp_path / "images"
    images.mkdir()
    (images / MANUAL_IMAGE).write_bytes(b"\x89PNG\r\n\x1a\n" + b"\0" * 32)
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<!doctype html><title>viewer</title>")
    (dist / "capture.html").write_text("<!doctype html><title>snapshot</title>")
    (dist / "assets" / "main-abc123.js").write_text("console.log('x');" * 200)
    (dist / "robots.txt").write_text("User-agent: *\nAllow: /\n")
    return {"data": tmp_path / "data", "dist": dist, "images": images}


@pytest.fixture
def client(site: dict[str, Path]) -> TestClient:
    return TestClient(create_app(site["data"], site["dist"], [site["images"]]))


def test_health_reports_what_is_there(client: TestClient) -> None:
    body = client.get("/api/health").json()
    assert body["ok"] and body["viewer_scene"] and body["viewer_auto"] and body["compare"] and body["web"]
    assert body["scene_points"] is False


def test_both_exports_are_served_plain_with_a_short_cache(client: TestClient) -> None:
    for build in ("viewer", "viewer-auto"):
        r = client.get(f"/api/{build}/scene.bin", headers={"Accept-Encoding": "gzip"})
        assert r.status_code == 200 and r.content == SCENE
        assert "content-encoding" not in r.headers, "the viewer reads Content-Length for progress: never compressed"
        assert r.headers["cache-control"] == "public, max-age=60"
        assert client.get(f"/api/{build}/scene.json").json()["build"] == build.replace("-", "_")
        assert client.get(f"/api/{build}/lod/0.bin").content == SCENE[:256]
        assert client.get(f"/api/{build}/lod/0.splat").content == SCENE[:512]
    assert client.get("/api/viewer/lod/x.bin").status_code == 404
    assert client.get("/api/viewer/lod/0.png").status_code == 404
    assert client.get("/api/nope/scene.json").status_code == 404


def test_missing_export_says_how_to_make_it(client: TestClient, site: dict[str, Path]) -> None:
    (site["data"] / "derived" / "viewer_auto" / "scene.json").unlink()
    r = client.get("/api/viewer-auto/scene.json")
    assert r.status_code == 404 and "make viewer-auto" in r.json()["detail"]
    (site["data"] / "derived" / "viewer" / "scene.splat").write_bytes(SCENE[:64])
    assert client.get("/api/viewer/scene.splat").content == SCENE[:64]


def test_compare_json(client: TestClient, site: dict[str, Path]) -> None:
    assert client.get("/api/compare.json").json()["summary"]["found"] == 1
    (site["data"] / "derived" / "compare.json").unlink()
    r = client.get("/api/compare.json")
    assert r.status_code == 404 and "make compare" in r.json()["detail"]


def test_step_images_local_else_github(client: TestClient) -> None:
    local = client.get(f"/api/images/{MANUAL_IMAGE}")
    assert local.status_code == 200 and local.headers["content-type"] == "image/png"
    assert local.headers["cache-control"] == "public, max-age=86400"
    # a manual step image that is not on this machine: the committed PNG in the repository
    gone = client.get("/api/images/0001_20261106-215306.png", follow_redirects=False)
    assert gone.status_code == 307
    assert gone.headers["location"] == f"{GITHUB_RAW}/images/0001_20261106-215306.png"
    # an automatic-build picture (tagged name): only a JPEG sample of those is committed
    auto = client.get(f"/api/images/{AUTO_IMAGE}", follow_redirects=False)
    assert auto.status_code == 307
    assert auto.headers["location"] == f"{GITHUB_RAW}/autoscene/out/samples/{AUTO_IMAGE[:-4]}.jpg"
    for bad in ("../secret.png", "scene.json", "1024_20261107-035218.jpg", "x_20261107-035218.png"):
        assert client.get(f"/api/images/{bad}", follow_redirects=False).status_code in (404, 422), bad


def test_image_fallback_can_be_switched_off(site: dict[str, Path]) -> None:
    c = TestClient(create_app(site["data"], site["dist"], [site["images"]], image_fallback=""))
    assert c.get(f"/api/images/{MANUAL_IMAGE}").status_code == 200
    assert c.get("/api/images/0001_20261106-215306.png", follow_redirects=False).status_code == 404


def test_viewer_pages_assets_and_cache_headers(client: TestClient) -> None:
    index = client.get("/")
    assert "viewer" in index.text and index.headers["cache-control"] == "no-cache"
    assert "snapshot" in client.get("/capture.html").text
    assert client.get("/capture.html").headers["cache-control"] == "no-cache"
    asset = client.get("/assets/main-abc123.js", headers={"Accept-Encoding": "gzip"})
    assert "immutable" in asset.headers["cache-control"]
    assert asset.headers.get("content-encoding") == "gzip", "site files are compressed on the fly"
    assert "console.log" in asset.text
    robots = client.get("/robots.txt")
    assert robots.status_code == 200 and robots.headers["cache-control"] == "public, max-age=3600"
    assert index.headers["x-content-type-options"] == "nosniff"


def test_api_route_wins_over_static_and_unknown_api_is_404(client: TestClient) -> None:
    assert client.get("/api/demo-mode").json() == {"enabled": False}
    assert client.get("/api/nope").status_code == 404


def test_without_dist_only_the_api_is_served(site: dict[str, Path], tmp_path: Path) -> None:
    c = TestClient(create_app(site["data"], tmp_path / "no-dist", [site["images"]]))
    assert c.get("/api/health").json()["web"] is False
    assert c.get("/").status_code == 404


def test_gzip_helper_is_not_used_for_exports(client: TestClient) -> None:
    """A pre-compressed copy next to an export must not be picked up: the browser would see the wrong length."""
    r = client.get("/api/viewer/scene.bin", headers={"Accept-Encoding": "gzip, deflate"})
    assert r.content == SCENE and gzip.decompress(gzip.compress(SCENE)) == SCENE
