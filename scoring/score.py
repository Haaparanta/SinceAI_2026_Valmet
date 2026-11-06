#!/usr/bin/env python3
"""Self-score the build against the Valmet brief rubric.

Reads scoring/scorecard.toml (and optionally a metrics.json written by a
pipeline run), then prints the weighted total out of 100, the biggest point
gaps and the open pass/fail items. Standard library only (Python 3.11+).

    python3 scoring/score.py
    python3 scoring/score.py --metrics out/metrics.json --top 8
"""

from __future__ import annotations

import argparse
import json
import sys
import tomllib
from pathlib import Path

HERE = Path(__file__).resolve().parent
MAX = 5  # every item is scored 0..5


def item_score(item: dict, metrics: dict) -> tuple[int | None, str]:
    """Return (score 0..5, or None when not assessed yet; evidence text)."""
    if "metric" in item:
        key = item["metric"]
        value = metrics.get(key, item.get("value"))
        if value is None:
            return None, f"{key} not measured"
        down = item.get("direction") == "down"
        met = sum((value <= t) if down else (value >= t) for t in item["thresholds"])
        return met, f"{key} = {value:g}"
    score = item.get("score")
    if score is None:
        return None, "not judged yet"
    return score, item.get("evidence", "judged")


def validate(card: dict) -> list[str]:
    errors = []
    weights = 0
    for crit in card["criteria"]:
        weights += crit["weight"]
        points = sum(i["points"] for i in crit["items"])
        if points != crit["weight"]:
            errors.append(f"{crit['id']}: item points add up to {points}, weight is {crit['weight']}")
        for item in crit["items"]:
            if "metric" in item:
                t = item["thresholds"]
                if len(t) != MAX or t != sorted(t, reverse=item.get("direction") == "down"):
                    errors.append(f"{item['id']}: needs {MAX} thresholds in scoring order, got {t}")
            elif "score" in item and not 0 <= item["score"] <= MAX:
                errors.append(f"{item['id']}: score {item['score']} is outside 0..{MAX}")
    if weights != 100:
        errors.append(f"criteria weights add up to {weights}, not 100")
    return errors


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--card", type=Path, default=HERE / "scorecard.toml")
    ap.add_argument("--metrics", type=Path,
                    help="JSON object of metric values from a pipeline run; overrides `value` in the card")
    ap.add_argument("--top", type=int, default=5, help="how many point gaps to list (default 5)")
    args = ap.parse_args()

    card = tomllib.loads(args.card.read_text(encoding="utf-8"))
    metrics = json.loads(args.metrics.read_text(encoding="utf-8")) if args.metrics else {}
    if errors := validate(card):
        print(f"{args.card.name} is inconsistent:", *errors, sep="\n  ", file=sys.stderr)
        return 1

    print(f"Valmet rubric self-score · {card['updated']} · {card['stage']}\n")
    total, gaps, unassessed = 0.0, [], 0
    for crit in card["criteria"]:
        rows, got = [], 0.0
        for item in crit["items"]:
            score, evidence = item_score(item, metrics)
            pts = item["points"] * (score or 0) / MAX
            got += pts
            unassessed += score is None
            gaps.append((item["points"] - pts, item["id"], item["name"]))
            mark = "-" if score is None else f"{score}/{MAX}"
            rows.append(f"  {item['id']:<5} {item['name']:<44} {mark:>3}  "
                        f"{pts:4.1f}/{item['points']:<2}  {evidence}")
        total += got
        print(f"{crit['id']}  {crit['name']:<50} {got:5.1f} / {crit['weight']}")
        print(*rows, sep="\n", end="\n\n")

    note = f"   ({unassessed} items not assessed yet, counted as 0)" if unassessed else ""
    print(f"TOTAL {total:5.1f} / 100{note}")

    print("\nMost points still on the table:")
    for lost, item_id, name in sorted(gaps, key=lambda g: (-g[0], g[1]))[: args.top]:
        if lost > 0:
            print(f"  {lost:4.1f}  {item_id} {name}")

    checklist = card.get("checklist", [])
    still_open = [c for c in checklist if not c.get("done")]
    print(f"\nPass/fail checklist: {len(checklist) - len(still_open)}/{len(checklist)} done")
    for c in still_open:
        print(f"  [ ] {c['id']:<6} {c['name']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
