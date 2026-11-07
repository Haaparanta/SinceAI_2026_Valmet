"""The viewer's info card: scene.json carries each part's step images, and GET /api/images/{name} serves only those."""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import pytest
from fastapi import HTTPException

ROOT = Path(__file__).parents[1]
_spec = importlib.util.spec_from_file_location("export_viewer_scene", ROOT / "scripts" / "export_viewer_scene.py")
assert _spec and _spec.loader
export = importlib.util.module_from_spec(_spec)
sys.modules["export_viewer_scene"] = export
_spec.loader.exec_module(export)

from api import main as api


def test_step_info_keeps_image_names_and_time() -> None:
    step = {"index": 447, "images": ["images/0447_20261107-004957.png", "images/0448_20261107-004957.png"],
            "created_at": "2026-11-07T00:49:57+02:00"}
    assert export.step_info(step) == {
        "images": ["0447_20261107-004957.png", "0448_20261107-004957.png"],
        "accepted_at": "2026-11-07T00:49:57+02:00",
    }
    assert export.step_info(None) == {}
    assert export.step_info({"index": 1}) == {"images": []}


@pytest.mark.parametrize("name", ["0447_20261107-004957.png", "0001_20261106-120000_close-up.png"])
def test_image_name_rule_accepts_step_images(name: str) -> None:
    assert api.IMAGE_NAME.match(name)


@pytest.mark.parametrize("name", ["../README.md", "0447.png", "x_20261107-004957.png", "0447_20261107-004957.png/..",
                                  "0447_20261107-004957.jpg"])
def test_image_name_rule_rejects_anything_else(name: str) -> None:
    assert not api.IMAGE_NAME.match(name)


def test_step_image_serves_a_committed_image_and_404s_otherwise() -> None:
    first = sorted(p.name for p in (ROOT / "images").glob("*.png"))
    if not first:
        pytest.skip("no step images in images/")
    assert Path(api.step_image(first[0]).path) == ROOT / "images" / first[0]
    with pytest.raises(HTTPException) as e:
        api.step_image("9999_20000101-000000.png")
    assert e.value.status_code == 404
