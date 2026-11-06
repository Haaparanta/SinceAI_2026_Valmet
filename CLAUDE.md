# CLAUDE.md

## Git workflow

When a task is done, always finish it by:

1. **Commit** the changes on a feature branch (never directly on `main`; create a branch first if needed) with a clear message.
2. **Push** the branch to `origin`.
3. **Open a pull request** against `main` with `gh pr create`, summarizing what changed and why.

Do this without waiting to be asked. Don't merge the PR yourself unless explicitly told to.
