# CLAUDE.md

Read [`AGENTS.md`](AGENTS.md) first — it is `pm_pack/06_AGENTS_Master_Context.md` (stack, folder tree, frozen
contracts, scan recipe, copilot contract, agent ownership rules) — then [`README.md`](README.md) "Where we are" for what
is actually built, then `pm_pack/05_Execution_Roadmap_and_Milestones.md` for the current sprint and gate.

`AGENTS.md` is the plan. Where the repo differs, the repo wins:

- The master scan is `data/raw/Equipment Room.ply`, not `Industrial Boiler Room (1).ply`.
- The current twin state is `build/manifest.json` (written by `pipeline/build.py`, one human-approved step at a time,
  images in `images/`). `data/scene_graph.json` does not exist yet.
- Set up with `make setup` (uv sync), not the `uv pip install` list in `AGENTS.md` §1.

## Dev loop

- `make help` lists every target.
- Run only the tests you touch: `make test T=parts` (file), `make test K=lamp` (name match), `make test-changed`,
  `make test-failed`. `make check` (all tests + lint + contracts + web build) must pass before a hand-off. Gate on its
  exit code; don't pipe it into `grep`.
- Never `ruff --fix` `contracts/py/a2b_contracts/models.py` or `pipeline/common/ply_io.py`: they are byte-for-byte
  copies from `AGENTS.md`.

## Git workflow

When a task is done, always finish it by:

1. **Commit** the changes on a feature branch (never directly on `main`; create a branch first if needed) with a clear message.
2. **Push** the branch to `origin`.
3. **Open a pull request** against `main` with `gh pr create`, summarizing what changed and why.

Do this without waiting to be asked. Don't merge the PR yourself unless explicitly told to.

Commit messages carry the owner prefix from `AGENTS.md` §7: `[pipe]`, `[api]`, `[web]`, `[contract]`, `[test]`, `[docs]`.
