# CLAUDE.md

Read [`AGENTS.md`](AGENTS.md) first — it is `pm_pack/06_AGENTS_Master_Context.md` (stack, folder tree, frozen
contracts, scan recipe, copilot contract, agent ownership rules) — then `data/scene_graph.json`, then
`pm_pack/05_Execution_Roadmap_and_Milestones.md` for the current sprint and gate.

## Git workflow

When a task is done, always finish it by:

1. **Commit** the changes on a feature branch (never directly on `main`; create a branch first if needed) with a clear message.
2. **Push** the branch to `origin`.
3. **Open a pull request** against `main` with `gh pr create`, summarizing what changed and why.

Do this without waiting to be asked. Don't merge the PR yourself unless explicitly told to.

Commit messages carry the owner prefix from `AGENTS.md` §7: `[pipe]`, `[api]`, `[web]`, `[contract]`, `[test]`, `[docs]`.
