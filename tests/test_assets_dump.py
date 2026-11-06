"""M6 first half: data/derived/assets.json from pipeline/05_bind_metadata.py --dump validates as AssetRecord[]."""

import json
from pathlib import Path

import pytest
from a2b_contracts.models import AssetRecord
from pydantic import TypeAdapter

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "data" / "derived" / "assets.json"
XLSX_DIR = ROOT / "data" / "derived" / "xlsx"
STATUS_MAP = {"healthy": "OK", "watch": "WATCH", "degraded": "WATCH", "attention_required": "ALERT"}
SAMPLE_TARGETS = {"ASSET-017": ("P-005", "FOULING"), "ASSET-024": ("M-006", "OVERHEATING"), "ASSET-014": ("P-002", "CAVITATION_RISK")}

pytestmark = pytest.mark.skipif(
    not ASSETS.exists(), reason="run `uv run python pipeline/05_bind_metadata.py --dump` first"
)


@pytest.fixture(scope="module")
def records() -> list[AssetRecord]:
    return TypeAdapter(list[AssetRecord]).validate_json(ASSETS.read_bytes())


def test_all_16_sheets_dumped() -> None:
    manifest = json.loads((XLSX_DIR / "_manifest.json").read_text())
    assert len(manifest["sheets"]) == 16
    for s in manifest["sheets"]:
        assert (XLSX_DIR / f"{s['sheet']}.json").exists()


def test_30_assets_with_mapped_status(records: list[AssetRecord]) -> None:
    assert len(records) == 30
    assert len({r.asset_id for r in records}) == 30
    for r in records:
        assert r.status == STATUS_MAP[r.current_state.condition_state]
        assert r.object_id is None and r.anchor is None  # unbound until the curator run


def test_sample_targets_are_alert(records: list[AssetRecord]) -> None:
    by_id = {r.asset_id: r for r in records}
    for asset_id, (tag, issue) in SAMPLE_TARGETS.items():
        r = by_id[asset_id]
        assert (r.tag, r.status, r.current_state.issue_code) == (tag, "ALERT", issue)


def test_windows_and_documents_are_merged(records: list[AssetRecord]) -> None:
    for r in records:
        assert len(r.telemetry_window) >= 100, r.asset_id
        assert all(a.timestamp <= b.timestamp for a, b in zip(r.telemetry_window, r.telemetry_window[1:]))
        doc_ids = [d.doc_id for d in r.documents]
        assert f"DOC-{r.asset_class}-CORE" in doc_ids
        assert {"DOC-FIELD-SAFETY", "DOC-RAG-GUIDE", "DOC-3D-MAPPING"} <= set(doc_ids)
        assert all(d.content for d in r.documents if d.doc_id.endswith("-CORE") or d.scope == "ALL")
