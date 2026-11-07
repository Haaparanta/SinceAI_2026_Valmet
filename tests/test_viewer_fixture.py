"""scripts/make_viewer_fixture.py: the synthetic viewer scene matches the layout web/src/scene.ts parses."""

import subprocess
import sys
from pathlib import Path

import numpy as np
import orjson

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "scripts" / "make_viewer_fixture.py"
MANIFEST = orjson.loads((ROOT / "build" / "manifest.json").read_bytes())


def run(out: Path, *extra: str) -> subprocess.CompletedProcess:
    return subprocess.run([sys.executable, str(SCRIPT), "--out", str(out), *extra],
                          check=False, capture_output=True, text=True)


def test_fixture_layout_matches_scene_json(tmp_path: Path) -> None:
    assert run(tmp_path, "--pool", "500", "--part-max", "200").returncode == 0
    meta = orjson.loads((tmp_path / "scene.json").read_bytes())
    blob = (tmp_path / "scene.bin").read_bytes()
    n = meta["count"]
    assert meta["fixture"] is True
    assert len(blob) == n * (12 + 2 + 3 + 1)                       # the check in parseScene()
    assert [p["name"] for p in meta["parts"]] == [p["name"] for p in MANIFEST["parts"]]

    xyz = np.frombuffer(blob, "<f4", n * 3).reshape(n, 3)
    part = np.frombuffer(blob, "<u2", n, offset=n * 12)
    assert (part[: meta["pool_count"]] == 0).all()
    start = meta["pool_count"]
    for p in meta["parts"]:                                         # contiguous, in order, inside the manifest bbox
        assert p["start"] == start and (part[p["start"]:p["end"]] == p["seq"]).all()
        box = xyz[p["start"]:p["end"]]
        assert (box >= np.array(p["bbox"]["min"], "f4")).all() and (box <= np.array(p["bbox"]["max"], "f4")).all()
        start = p["end"]
    assert start == n


def test_fixture_never_replaces_a_real_export(tmp_path: Path) -> None:
    (tmp_path / "scene.json").write_bytes(orjson.dumps({"version": 1, "parts": []}))
    res = run(tmp_path)
    assert res.returncode == 1 and "real export" in res.stderr
    assert not (tmp_path / "scene.bin").exists()
    assert run(tmp_path, "--force", "--pool", "10", "--part-max", "60").returncode == 0
    assert run(tmp_path, "--pool", "10", "--part-max", "60").returncode == 0  # a fixture may replace a fixture
