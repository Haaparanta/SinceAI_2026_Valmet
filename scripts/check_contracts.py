"""Export JSON Schema from the pydantic contracts and check the TypeScript twin has the same field names.

    uv run python scripts/check_contracts.py          # (re)write contracts/json-schema/<Model>.json
    uv run python scripts/check_contracts.py --check  # exit 1 if a schema file is stale or contracts/ts/index.ts drifts

Shared surface rule (AGENTS.md S7): a contract change needs docs/CONTRACT_CHANGES.md + both the py and ts edit.
"""

from __future__ import annotations

import argparse
import inspect
import re
import sys
from pathlib import Path

import orjson
from a2b_contracts import models
from pydantic import BaseModel

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_DIR = ROOT / "contracts" / "json-schema"
TS_FILE = ROOT / "contracts" / "ts" / "index.ts"


def pydantic_models() -> dict[str, type[BaseModel]]:
    out: dict[str, type[BaseModel]] = {}
    for name, obj in vars(models).items():
        if inspect.isclass(obj) and issubclass(obj, BaseModel) and obj not in (BaseModel, models.Strict):
            out[name] = obj
    return out


def ts_interfaces(src: str) -> dict[str, set[str]]:
    """export interface Name { a: T; b?: T; } -> {Name: {a, b}} (the contracts have no nested braces)."""
    out: dict[str, set[str]] = {}
    for m in re.finditer(r"export interface (\w+)\s*\{(.*?)\}", src, re.DOTALL):
        body = re.sub(r"//[^\n]*", "", m.group(2))
        out[m.group(1)] = set(re.findall(r"(?:^|[;{\s])(\w+)\??\s*:", body))
    return out


def schema_bytes(model: type[BaseModel]) -> bytes:
    return orjson.dumps(model.model_json_schema(), option=orjson.OPT_INDENT_2 | orjson.OPT_SORT_KEYS) + b"\n"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", action="store_true", help="verify instead of write")
    args = ap.parse_args(argv)

    py = pydantic_models()
    ts = ts_interfaces(TS_FILE.read_text())
    problems: list[str] = []

    for name, model in py.items():
        if name not in ts:
            problems.append(f"{name}: missing in {TS_FILE.relative_to(ROOT)}")
            continue
        py_fields, ts_fields = set(model.model_fields), ts[name]
        if py_fields != ts_fields:
            only_py, only_ts = sorted(py_fields - ts_fields), sorted(ts_fields - py_fields)
            problems.append(f"{name}: field drift  only-in-py={only_py}  only-in-ts={only_ts}")
    for name in sorted(set(ts) - set(py)):
        problems.append(f"{name}: TypeScript interface without a pydantic model")

    SCHEMA_DIR.mkdir(parents=True, exist_ok=True)
    stale: list[str] = []
    for name, model in py.items():
        target = SCHEMA_DIR / f"{name}.json"
        data = schema_bytes(model)
        if args.check:
            if not target.exists() or target.read_bytes() != data:
                stale.append(target.name)
        else:
            target.write_bytes(data)

    if args.check:
        for s in stale:
            problems.append(f"contracts/json-schema/{s} is stale: run `uv run python scripts/check_contracts.py`")
        if problems:
            print("CONTRACT CHECK FAILED", file=sys.stderr)
            for p in problems:
                print(" -", p, file=sys.stderr)
            return 1
        print(f"contracts OK: {len(py)} models == {len(ts)} TypeScript interfaces, {len(py)} schemas up to date")
        return 0

    for p in problems:
        print("WARNING:", p, file=sys.stderr)
    print(f"wrote {len(py)} schemas to {SCHEMA_DIR.relative_to(ROOT)}/")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
