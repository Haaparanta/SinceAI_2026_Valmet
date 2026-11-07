"""M6 (first half) - builder-pack xlsx -> JSON dump + AssetRecord merge.

    uv run python pipeline/05_bind_metadata.py --dump [--in XLSX] [--out data/derived]

Writes
  data/derived/xlsx/<Sheet>.json   all 16 sheets, one file each: {"sheet", "kind", "columns", "row_count", "rows"}.
                                   Excel dates -> ISO 8601 strings; the pack has no formulas (plain values only).
  data/derived/xlsx/_manifest.json sheet names, row counts, columns.
  data/derived/assets.json         one validated AssetRecord (AGENTS.md S4.1) per Asset_Master row merged with
                                   Current_State, its Telemetry_Sample_3d rows, Alarms_Events, Maintenance_History,
                                   Knowledge_Docs (class core doc + DOC-FIELD-SAFETY + DOC-RAG-GUIDE + DOC-3D-MAPPING,
                                   plus its RAG_Corpus_Index asset-card entry) and Data_Quality.
Status mapping [HYPOTHESIS]: healthy -> OK, watch -> WATCH, degraded -> WATCH, attention_required -> ALERT.
object_id / anchor stay null until the curator binds the asset (second half of M6, not implemented yet).
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
from collections import defaultdict
from datetime import date, datetime, time
from pathlib import Path
from typing import Any

import orjson
from a2b_contracts.models import (
    AssetRecord,
    CurrentState,
    DataQualityRow,
    EventRow,
    TelemetryRow,
    WorkOrderRow,
)
from openpyxl import load_workbook
from openpyxl.utils.datetime import from_excel
from pydantic import TypeAdapter, ValidationError

log = logging.getLogger("05_bind_metadata")
ROOT = Path(__file__).resolve().parents[1]
DEFAULT_IN = ROOT / "data" / "raw" / "Valmet_SinceAI_2026_Synthetic_Industrial_Metaverse_Builder_Pack (1) (2) (1).xlsx"
DEFAULT_OUT = ROOT / "data" / "derived"
EXPECTED_SHEETS = 16
STATUS_MAP = {"healthy": "OK", "watch": "WATCH", "degraded": "WATCH", "attention_required": "ALERT"}
GLOBAL_DOCS = ("DOC-FIELD-SAFETY", "DOC-RAG-GUIDE", "DOC-3D-MAPPING")
SAMPLE_TARGETS = {"ASSET-017": "P-005", "ASSET-024": "M-006", "ASSET-014": "P-002"}
DATE_COLUMN = re.compile(r"(^|_)(date|at|timestamp|updated)$")

ASSET_MASTER_FIELDS = (
    "asset_id", "tag", "asset_class", "area_id", "area_name", "process_context", "criticality",
    "installation_date", "last_service_date", "service_interval_days", "connectivity_profile",
)
CURRENT_STATE_FIELDS = tuple(CurrentState.model_fields)
TELEMETRY_FIELDS = tuple(TelemetryRow.model_fields)
EVENT_FIELDS = tuple(EventRow.model_fields)
WORK_ORDER_FIELDS = tuple(WorkOrderRow.model_fields)
DATA_QUALITY_FIELDS = tuple(DataQualityRow.model_fields)


def json_value(column: str, value: Any) -> Any:
    """Cell -> JSON-safe value. datetime/date/time -> ISO 8601; Excel serial numbers in date-like columns -> ISO 8601."""
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, (date, time)):
        return value.isoformat()
    if isinstance(value, (int, float)) and not isinstance(value, bool) and DATE_COLUMN.search(column or ""):
        return from_excel(value).isoformat()
    if isinstance(value, str):
        return value.strip()
    return value


def _trim(row: list[Any]) -> list[Any]:
    while row and row[-1] is None:
        row = row[:-1]
    return row


def read_sheet(ws) -> dict[str, Any]:
    """A sheet whose first row is all strings is a table (rows -> dicts); otherwise free-form (rows -> lists)."""
    rows = [_trim(list(r)) for r in ws.iter_rows(values_only=True)]
    rows = [r for r in rows if r]
    if not rows:
        return {"sheet": ws.title, "kind": "empty", "columns": [], "row_count": 0, "rows": []}
    header = rows[0]
    if len(header) >= 2 and all(isinstance(c, str) and c.strip() for c in header):
        columns = [c.strip() for c in header]
        recs = [
            {col: json_value(col, r[i] if i < len(r) else None) for i, col in enumerate(columns)} for r in rows[1:]
        ]
        return {"sheet": ws.title, "kind": "table", "columns": columns, "row_count": len(recs), "rows": recs}
    recs = [[json_value("", c) for c in r] for r in rows]
    return {"sheet": ws.title, "kind": "freeform", "columns": [], "row_count": len(recs), "rows": recs}


def dump_sheets(xlsx: Path, out_dir: Path) -> dict[str, dict[str, Any]]:
    wb = load_workbook(xlsx, read_only=True, data_only=True)
    if len(wb.sheetnames) != EXPECTED_SHEETS:
        log.warning("expected %d sheets, found %d: %s", EXPECTED_SHEETS, len(wb.sheetnames), wb.sheetnames)
    out_dir.mkdir(parents=True, exist_ok=True)
    sheets: dict[str, dict[str, Any]] = {}
    for ws in wb.worksheets:
        sheet = read_sheet(ws)
        sheets[ws.title] = sheet
        (out_dir / f"{ws.title}.json").write_bytes(orjson.dumps(sheet, option=orjson.OPT_INDENT_2))
        log.info("sheet %-26s %-8s %5d rows  %2d cols", ws.title, sheet["kind"], sheet["row_count"], len(sheet["columns"]))
    manifest = {
        "source_file": xlsx.name,
        "generated_at": datetime.now().isoformat(timespec="seconds"),
        "sheets": [
            {"sheet": s["sheet"], "kind": s["kind"], "row_count": s["row_count"], "columns": s["columns"]}
            for s in sheets.values()
        ],
    }
    (out_dir / "_manifest.json").write_bytes(orjson.dumps(manifest, option=orjson.OPT_INDENT_2))
    return sheets


def _pick(row: dict[str, Any], fields: tuple[str, ...]) -> dict[str, Any]:
    return {k: row.get(k) for k in fields}


def _group(rows: list[dict[str, Any]], key: str) -> dict[str, list[dict[str, Any]]]:
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for r in rows:
        groups[r[key]].append(r)
    return groups


def build_assets(sheets: dict[str, dict[str, Any]]) -> list[dict[str, Any]]:
    rows = {name: s["rows"] for name, s in sheets.items()}
    current = {r["asset_id"]: r for r in rows["Current_State"]}
    telemetry = _group(rows["Telemetry_Sample_3d"], "asset_id")
    events = _group(rows["Alarms_Events"], "asset_id")
    work_orders = _group(rows["Maintenance_History"], "asset_id")
    quality = _group(rows["Data_Quality"], "asset_id")
    docs = {r["doc_id"]: r for r in rows["Knowledge_Docs"]}
    rag_by_doc = {r["doc_id"]: r for r in rows["RAG_Corpus_Index"]}
    rag_by_asset = _group(rows["RAG_Corpus_Index"], "asset_id")

    assets: list[dict[str, Any]] = []
    for am in rows["Asset_Master"]:
        asset_id, asset_class = am["asset_id"], am["asset_class"]
        state = current.get(asset_id)
        if state is None:
            raise SystemExit(f"{asset_id}: no Current_State row")
        documents = []
        for doc_id in (f"DOC-{asset_class}-CORE", *GLOBAL_DOCS):
            doc = docs.get(doc_id)
            if doc is None:
                raise SystemExit(f"{asset_id}: Knowledge_Docs has no {doc_id}")
            documents.append({
                "doc_id": doc_id,
                "title": doc["title"],
                "scope": doc["scope"],
                "document_role": rag_by_doc.get(doc_id, {}).get("document_role") or "knowledge_doc",
                "content": doc["content"],
            })
        for r in rag_by_asset.get(asset_id, []):  # the asset card is only indexed; its .md is not in the pack
            documents.append({
                "doc_id": r["doc_id"], "title": r["file_name"], "scope": r["scope"],
                "document_role": r["document_role"], "content": None,
            })
        assets.append({
            **_pick(am, ASSET_MASTER_FIELDS),
            "current_state": _pick(state, CURRENT_STATE_FIELDS),
            "status": STATUS_MAP[state["condition_state"]],
            "telemetry_window": [
                _pick(r, TELEMETRY_FIELDS) for r in sorted(telemetry.get(asset_id, []), key=lambda r: r["timestamp"])
            ],
            "events": [_pick(r, EVENT_FIELDS) for r in sorted(events.get(asset_id, []), key=lambda r: r["timestamp"])],
            "maintenance_history": [
                _pick(r, WORK_ORDER_FIELDS) for r in sorted(work_orders.get(asset_id, []), key=lambda r: r["opened_at"])
            ],
            "documents": documents,
            "data_quality": [_pick(r, DATA_QUALITY_FIELDS) for r in quality.get(asset_id, [])],
            "object_id": None,
            "anchor": None,
        })
    return assets


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dump", action="store_true", help="xlsx -> data/derived/xlsx/*.json + assets.json")
    ap.add_argument("--in", dest="inp", type=Path, default=DEFAULT_IN, help="builder-pack xlsx")
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT, help="output folder (default: data/derived)")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s %(levelname)s %(message)s")

    if not args.dump:
        log.error("only --dump is implemented (M6 first half); Scene_Anchors rewrite/binding comes with the curator")
        return 2
    if not args.inp.exists():
        log.error("xlsx not found: %s", args.inp)
        return 2

    sheets = dump_sheets(args.inp, args.out / "xlsx")
    assets = build_assets(sheets)
    adapter = TypeAdapter(list[AssetRecord])
    try:
        records = adapter.validate_python(assets)
    except ValidationError as e:
        log.error("AssetRecord validation failed:\n%s", e)
        return 1
    (args.out / "assets.json").write_bytes(adapter.dump_json(records, indent=2))

    by_status: dict[str, int] = defaultdict(int)
    for rec in records:
        by_status[rec.status] += 1
    log.info(
        "assets.json: %d AssetRecords validated; status %s; telemetry rows %d; events %d; work orders %d; dq %d",
        len(records), dict(by_status), sum(len(r.telemetry_window) for r in records),
        sum(len(r.events) for r in records), sum(len(r.maintenance_history) for r in records),
        sum(len(r.data_quality) for r in records),
    )
    for rec in records:
        if rec.asset_id in SAMPLE_TARGETS:
            cs = rec.current_state
            log.info(
                "target %s %s %s: %s / %s / health %.0f / %s -> status %s (%d telemetry, %d events, %d WOs, %d docs, %d dq)",
                rec.asset_id, rec.tag, rec.asset_class, cs.condition_state, cs.issue_code, cs.health_score, cs.urgency,
                rec.status, len(rec.telemetry_window), len(rec.events), len(rec.maintenance_history),
                len(rec.documents), len(rec.data_quality),
            )
    return 0


if __name__ == "__main__":
    sys.exit(main())
