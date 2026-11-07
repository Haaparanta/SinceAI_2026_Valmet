"""api/main.py: scene files (plain and pre-gzipped), the built viewer at /, cache headers, /api wins over static."""

from __future__ import annotations

import gzip
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.main import create_app

SCENE = bytes(range(256)) * 64


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    viewer = tmp_path / "data" / "derived" / "viewer"
    viewer.mkdir(parents=True)
    (viewer / "scene.bin").write_bytes(SCENE)
    (viewer / "scene.bin.gz").write_bytes(gzip.compress(SCENE))
    (viewer / "scene.json").write_text(json.dumps({"count": 1, "parts": []}))
    dist = tmp_path / "dist"
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<!doctype html><title>viewer</title>")
    (dist / "capture.html").write_text("<!doctype html><title>snapshot</title>")
    (dist / "assets" / "main-abc123.js").write_text("console.log('x');" * 200)
    return TestClient(create_app(tmp_path / "data", dist))


def test_health_reports_scene_and_web(client: TestClient) -> None:
    body = client.get("/api/health").json()
    assert body["ok"] and body["viewer_scene"] and body["web"]


def test_scene_bin_is_served_gzipped_when_accepted(client: TestClient) -> None:
    r = client.get("/api/viewer/scene.bin", headers={"Accept-Encoding": "gzip"})
    assert r.status_code == 200
    assert r.headers["content-encoding"] == "gzip"
    assert r.content == SCENE  # httpx decodes; the bytes on the wire were the .gz file
    assert "Accept-Encoding" in r.headers["vary"]


def test_scene_bin_plain_without_gzip(client: TestClient) -> None:
    r = client.get("/api/viewer/scene.bin", headers={"Accept-Encoding": "identity"})
    assert "content-encoding" not in r.headers
    assert r.content == SCENE


def test_scene_json_and_missing_file(client: TestClient, tmp_path: Path) -> None:
    assert client.get("/api/viewer/scene.json").json()["count"] == 1
    (tmp_path / "data" / "derived" / "viewer" / "scene.json").unlink()
    assert client.get("/api/viewer/scene.json").status_code == 404


def test_viewer_pages_and_cache_headers(client: TestClient) -> None:
    index = client.get("/")
    assert "viewer" in index.text and index.headers["cache-control"] == "no-cache"
    assert "snapshot" in client.get("/capture.html").text
    asset = client.get("/assets/main-abc123.js")
    assert "immutable" in asset.headers["cache-control"]


def test_api_route_wins_over_static_and_unknown_api_is_404(client: TestClient) -> None:
    assert client.get("/api/demo-mode").json() == {"enabled": False}
    assert client.get("/api/nope").status_code == 404


def test_without_dist_only_the_api_is_served(tmp_path: Path) -> None:
    c = TestClient(create_app(tmp_path / "data", tmp_path / "no-dist"))
    assert c.get("/api/health").json()["web"] is False
    assert c.get("/").status_code == 404
