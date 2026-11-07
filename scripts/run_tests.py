"""Run only the tests you need (faster dev loop); `make check` still runs everything.

    uv run python scripts/run_tests.py                     # all tests
    uv run python scripts/run_tests.py parts cleaning      # tests/test_parts.py + tests/test_cleaning.py
    uv run python scripts/run_tests.py parts::test_lamp_takes_the_largest_white_cluster_up_high
    uv run python scripts/run_tests.py lamp                # not a file name -> tests whose name contains "lamp"
                                                           # (with file names too, it narrows inside those files)
    uv run python scripts/run_tests.py --list              # what can be picked
    uv run python scripts/run_tests.py --pick              # numbered menu
    uv run python scripts/run_tests.py --changed           # tests related to files changed vs origin/main (+ uncommitted)
    uv run python scripts/run_tests.py --failed            # only the tests that failed last run
    uv run python scripts/run_tests.py parts -- -x -vv     # anything after -- goes straight to pytest

Same via make: `make test T="parts cleaning"`, `make test K=lamp`, `make test-list`, `make test-pick`,
`make test-changed`, `make test-failed`.
"""

from __future__ import annotations

import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TESTS = ROOT / "tests"
TEST_DEF = re.compile(r"^def (test_\w+)", re.MULTILINE)


def test_files() -> list[Path]:
    return sorted(TESTS.glob("test_*.py"))


def short(path: Path) -> str:
    return path.stem.removeprefix("test_")


def resolve_file(name: str) -> str | None:
    """`parts`, `test_parts`, `test_parts.py` or `tests/test_parts.py` -> 'tests/test_parts.py'."""
    for cand in (Path(name), ROOT / name, TESTS / name, TESTS / f"{name}.py", TESTS / f"test_{name}.py",
                 TESTS / f"test_{name.removesuffix('.py')}.py"):
        if cand.is_file():
            return str(cand.resolve().relative_to(ROOT))
    return None


def build_selection(names: list[str], keyword: str | None) -> tuple[list[str], list[str]]:
    """Split the names into pytest paths (files / file::test) and -k keywords."""
    paths: list[str] = []
    keywords: list[str] = [keyword] if keyword else []
    for name in names:
        file_part, sep, rest = name.partition("::")
        found = resolve_file(file_part)
        if found:
            paths.append(found + sep + rest)
        elif sep:
            sys.exit(f"no test file matches {file_part!r}; see `make test-list`")
        else:
            keywords.append(name)
    return paths, keywords


def list_tests() -> None:
    for f in test_files():
        names = TEST_DEF.findall(f.read_text())
        print(f"{short(f):<14} {len(names):>2} tests   {f.relative_to(ROOT)}")
        for n in names:
            print(f"    {n}")


def pick() -> list[str]:
    files = test_files()
    for i, f in enumerate(files, 1):
        print(f"  {i:>2}  {short(f):<14} {len(TEST_DEF.findall(f.read_text()))} tests")
    try:
        answer = input("Numbers or names to run (e.g. `1 3` or `parts`), Enter = all: ").strip()
    except EOFError:
        answer = ""
    picked: list[str] = []
    for tok in answer.replace(",", " ").split():
        if tok.isdigit():
            if not 1 <= int(tok) <= len(files):
                sys.exit(f"{tok} is not in the list (1-{len(files)})")
            picked.append(str(files[int(tok) - 1].relative_to(ROOT)))
        else:
            picked.append(tok)
    return picked


def git_lines(*args: str) -> list[str]:
    out = subprocess.run(["git", *args], check=False, cwd=ROOT, capture_output=True, text=True)
    return [line for line in out.stdout.splitlines() if line.strip()] if out.returncode == 0 else []


def changed_tests() -> list[str] | None:
    """Test files that changed, plus test files that mention the name of a changed .py module.
    Returns None when nothing Python changed."""
    base = "origin/main" if git_lines("rev-parse", "--verify", "-q", "origin/main") else "main"
    changed = set(git_lines("diff", "--name-only", f"{base}...HEAD"))
    changed |= set(git_lines("diff", "--name-only", "HEAD"))
    changed |= set(git_lines("ls-files", "--others", "--exclude-standard"))
    py = sorted(p for p in changed if p.endswith(".py") and (ROOT / p).is_file())
    if not py:
        return None
    selected = {p for p in py if p.startswith("tests/test_")}
    stems = {Path(p).stem for p in py if not p.startswith("tests/")} - {"__init__"}
    for f in test_files():
        text = f.read_text()
        if any(re.search(rf"\b{re.escape(s)}\b", text) for s in stems):
            selected.add(str(f.relative_to(ROOT)))
    print("changed .py: " + ", ".join(py))
    return sorted(selected)


def main() -> int:
    argv = sys.argv[1:]
    passthrough: list[str] = []
    if "--" in argv:
        i = argv.index("--")
        argv, passthrough = argv[:i], argv[i + 1:]

    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("names", nargs="*", help="test file short names (parts), file::test, or name keywords (lamp)")
    ap.add_argument("-k", dest="keyword", help="pytest -k expression")
    ap.add_argument("--list", action="store_true", help="list test files and test names, run nothing")
    ap.add_argument("--pick", action="store_true", help="choose test files from a numbered menu")
    ap.add_argument("--changed", action="store_true", help="only tests related to changed files")
    ap.add_argument("--failed", action="store_true", help="only tests that failed last run (pytest --lf)")
    args = ap.parse_args(argv)

    if args.list:
        list_tests()
        return 0

    names = list(args.names)
    if args.pick:
        names += pick()
    if args.changed:
        found = changed_tests()
        if not found:
            print("no tests related to the changed files; `make test` runs them all")
            return 0
        names += found

    paths, keywords = build_selection(names, args.keyword)
    cmd = [sys.executable, "-m", "pytest", "-q", *paths]
    if keywords:
        cmd += ["-k", " or ".join(f"({k})" for k in keywords)]
    if args.failed:
        cmd += ["--lf", "--lfnf=none"]
    cmd += passthrough
    print("$ pytest " + " ".join(cmd[3:]), flush=True)
    rc = subprocess.call(cmd, cwd=ROOT)
    if rc == 5:  # pytest: no tests collected
        if args.failed:
            print("nothing failed last run")
            return 0
        print("no tests matched; see `make test-list`")
    return rc


if __name__ == "__main__":
    sys.exit(main())
