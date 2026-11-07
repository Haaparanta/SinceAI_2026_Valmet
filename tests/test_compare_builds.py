"""scripts/compare_builds.py: manual vs automatic build from boxes; GET /api/compare.json serves the result."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import orjson
import pytest
from fastapi import HTTPException

ROOT = Path(__file__).resolve().parents[1]
_spec = importlib.util.spec_from_file_location("compare_builds", ROOT / "scripts" / "compare_builds.py")
assert _spec and _spec.loader
cb = importlib.util.module_from_spec(_spec)
sys.modules["compare_builds"] = cb
_spec.loader.exec_module(cb)

from api import main as api


def box(lo: list[float], hi: list[float]) -> dict:
    return {"min": lo, "max": hi}


def part(name: str, b: dict, kind: str = "equipment") -> dict:
    return {"name": name, "label": name.title(), "kind": kind, "bbox": b}


def obj(name: str, b: dict, source: str = "yoloe", label: str = "thing") -> dict:
    return {"name": name, "label": label, "source": source, "aabb": b}


def run(parts: list[dict], objects: list[dict]) -> dict:
    return cb.compare({"parts": parts}, {"objects": objects})


def test_each_status() -> None:
    parts = [
        part("tank", box([0, 0, 0], [1, 1, 1])),                       # one object, nearly the same box
        part("pipe", box([0, 3, 0], [4, 3.2, 0.2]), "pipe"),           # cut into 3 pieces along x
        part("cart", box([6, 0, 0], [7, 1, 1])),                       # one small object in a corner
        part("lamp", box([10, 2, 10], [10.3, 2.3, 10.3])),             # nothing there
    ]
    objects = [
        obj("a_tank", box([0.02, 0, 0], [1, 1, 0.98])),
        obj("b_pipe", box([0, 3, 0], [1.3, 3.2, 0.2]), "cluster", "pipe"),
        obj("c_pipe", box([1.4, 3, 0], [2.6, 3.2, 0.2]), "cluster", "pipe"),
        obj("d_pipe", box([2.7, 3, 0], [4, 3.2, 0.2]), "cluster", "pipe"),
        obj("e_box", box([6, 0, 0], [6.6, 0.6, 0.6])),
        obj("f_far", box([20, 0, 0], [21, 1, 1])),
    ]
    c = run(parts, objects)
    rows = {r["name"]: r for r in c["manual"]}
    assert rows["tank"]["status"] == "matched" and rows["tank"]["best"]["name"] == "a_tank"
    assert rows["pipe"]["status"] == "split"
    assert sorted(rows["pipe"]["fragments"]) == ["b_pipe", "c_pipe", "d_pipe"]
    assert rows["pipe"]["fragment_labels"] == {"pipe": 3}
    assert 0.85 < rows["pipe"]["coverage"] <= 1.0                     # the gaps between pieces are not covered
    assert rows["cart"]["status"] == "partial" and rows["cart"]["fragments"] == ["e_box"]
    assert rows["lamp"]["status"] == "missed" and rows["lamp"]["best"] is None and rows["lamp"]["fragments"] == []
    assert rows["lamp"]["nearest"]["gap"] > 0

    autos = {a["name"]: a["in"] for a in c["auto"]}
    assert autos == {"a_tank": "tank", "b_pipe": "pipe", "c_pipe": "pipe", "d_pipe": "pipe", "e_box": "cart",
                     "f_far": None}
    s = c["summary"]
    assert s["status"] == {"matched": 1, "split": 1, "partial": 1, "missed": 1}
    assert s["found"] == 3 and s["auto_only"] == 1 and s["auto_only_by_label"] == {"thing": 1}
    # missed parts count as 0 in the mean, they are not skipped
    best = [rows[n]["best"]["iou"] if rows[n]["best"] else 0.0 for n in ("tank", "pipe", "cart", "lamp")]
    assert s["mean_best_iou"] == pytest.approx(sum(best) / 4, abs=1e-3)


def test_structures_and_objects_are_not_pieces_of_each_other() -> None:
    floor = part("floor", box([-5, -1.2, -5], [5, -1.1, 5]), "structure")
    c = run([floor], [obj("pipe_on_floor", box([0, -1.2, 0], [2, -1.1, 0.2]), "cluster"),
                      obj("auto_floor", box([-5, -1.21, -5], [5, -1.12, 5]), "structure", "floor")])
    row = c["manual"][0]
    assert row["fragments"] == ["auto_floor"] and row["status"] == "matched"
    assert {a["name"]: a["in"] for a in c["auto"]} == {"pipe_on_floor": None, "auto_floor": "floor"}


def test_an_object_belongs_to_the_smallest_part_it_is_inside() -> None:
    big = part("pump", box([0, 0, 0], [2, 2, 2]))
    small = part("valve", box([0.5, 0.5, 0.5], [0.8, 0.8, 0.8]))
    c = run([big, small], [obj("v", box([0.55, 0.55, 0.55], [0.75, 0.75, 0.75]))])
    assert c["auto"][0]["in"] == "valve"


def test_thin_slabs_a_few_cm_apart_still_overlap() -> None:
    a = cb.as_box(box([0, 1.40, 0], [5, 1.40, 5]))                    # zero-thickness boxes
    b = cb.as_box(box([0, 1.41, 0], [5, 1.41, 5]))
    assert cb.iou(a, b) > 0.5


def test_real_builds() -> None:
    manual = orjson.loads((ROOT / "build" / "manifest.json").read_bytes())
    auto = orjson.loads((ROOT / "autoscene" / "out" / "scene.json").read_bytes())
    c = cb.compare(manual, auto)
    rows = {r["name"]: r for r in c["manual"]}
    assert [r["name"] for r in c["manual"]] == [p["name"] for p in manual["parts"]]
    assert [a["name"] for a in c["auto"]] == [o["name"] for o in auto["objects"]]
    assert sum(c["summary"]["status"].values()) == len(manual["parts"])
    assert rows["floor"]["status"] == "matched" and rows["floor"]["best"]["label"] == "floor"
    assert rows["pipe_1"]["status"] == "split" and len(rows["pipe_1"]["fragments"]) >= 2
    # the two builds took different ceiling layers: the comparison must say so, not invent a match
    assert rows["ceiling"]["status"] == "missed" and rows["ceiling"]["nearest"]["label"] == "ceiling"


def test_cli_writes_json_and_report(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    out, rep = tmp_path / "compare.json", tmp_path / "report.md"
    monkeypatch.setattr(sys, "argv", ["compare_builds.py", "--out", str(out), "--report", str(rep)])
    assert cb.main() == 0
    c = orjson.loads(out.read_bytes())
    text = rep.read_text()
    assert f"{c['summary']['found']} of {c['inputs']['manual_parts']}" in text
    assert "| Pipe 1 | pipe | split |" in text


def test_api_serves_compare_json(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(api, "DERIVED", tmp_path)
    with pytest.raises(HTTPException) as e:
        api.compare_builds()
    assert e.value.status_code == 404 and "compare_builds.py" in e.value.detail
    (tmp_path / "compare.json").write_bytes(b"{}")
    assert Path(api.compare_builds().path) == tmp_path / "compare.json"
