"""scripts/make_viewer_fixture.py: the synthetic viewer scenes match the layout web/src/scene.ts parses."""

import subprocess
import sys
from pathlib import Path

import numpy as np
import orjson
import pytest

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "make_viewer_fixture.py"
MANIFEST = orjson.loads((ROOT / "build" / "manifest.json").read_bytes())
AUTOSCENE = orjson.loads((ROOT / "autoscene" / "out" / "scene.json").read_bytes())


def run(out: Path, *extra: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT), "--out", str(out), "--pool", "500", "--part-max", "200", *extra],
                          check=False, capture_output=True, text=True)


@pytest.mark.parametrize(("build", "folder", "names"), [
    ("manual", "viewer", [p["name"] for p in MANIFEST["parts"]]),
    ("auto", "viewer_auto", [o["name"] for o in AUTOSCENE["objects"]]),
])
def test_fixture_layout_matches_scene_json(tmp_path: Path, build: str, folder: str, names: list[str]) -> None:
    assert run(tmp_path, "--build", build).returncode == 0
    out = tmp_path / folder
    meta = orjson.loads((out / "scene.json").read_bytes())
    blob = (out / "scene.bin").read_bytes()
    n = meta["count"]
    assert meta["fixture"] is True
    assert len(blob) == n * (12 + 2 + 3 + 1)                       # the check in parseScene()
    assert len((out / "scene.splat").read_bytes()) == n * 32        # Splats mode: one row per point
    assert [p["name"] for p in meta["parts"]] == names
    assert (meta.get("build") == "autoscene") == (build == "auto")

    xyz = np.frombuffer(blob, "<f4", n * 3).reshape(n, 3)
    part = np.frombuffer(blob, "<u2", n, offset=n * 12)
    splat_xyz = np.frombuffer((out / "scene.splat").read_bytes(), np.uint8).reshape(n, 32)[:, :12].copy().view("<f4")
    assert np.array_equal(splat_xyz, xyz)                           # row i of scene.splat = row i of scene.bin
    assert (part[: meta["pool_count"]] == 0).all()
    start = meta["pool_count"]
    for p in meta["parts"]:                                         # contiguous, in order, inside the bbox
        assert p["start"] == start and (part[p["start"]:p["end"]] == p["seq"]).all()
        box = xyz[p["start"]:p["end"]]
        assert (box >= np.array(p["bbox"]["min"], "f4")).all() and (box <= np.array(p["bbox"]["max"], "f4")).all()
        start = p["end"]
    assert start == n


def test_fixture_never_replaces_a_real_export(tmp_path: Path) -> None:
    (tmp_path / "viewer").mkdir()
    (tmp_path / "viewer" / "scene.json").write_bytes(orjson.dumps({"version": 1, "parts": []}))
    res = run(tmp_path)
    assert res.returncode == 1 and "real export" in res.stderr
    assert not (tmp_path / "viewer" / "scene.bin").exists()
    assert (tmp_path / "viewer_auto" / "scene.bin").exists()       # the other build is still written
    assert run(tmp_path, "--build", "manual", "--force").returncode == 0
    assert run(tmp_path, "--build", "manual").returncode == 0      # a fixture may replace a fixture


def test_missing_only_leaves_existing_exports_alone(tmp_path: Path) -> None:
    (tmp_path / "viewer").mkdir()
    real = orjson.dumps({"version": 1, "parts": []})
    (tmp_path / "viewer" / "scene.json").write_bytes(real)
    res = run(tmp_path, "--missing-only")
    assert res.returncode == 0, res.stderr
    assert (tmp_path / "viewer" / "scene.json").read_bytes() == real
    assert (tmp_path / "viewer_auto" / "scene.json").exists()
