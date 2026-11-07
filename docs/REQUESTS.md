# Requests between agents

One line per request, `[from→to] what · why · evidence` (AGENTS.md §7). Strike through or delete when done.

## Open

_none_

## Done

- ~~`[test→web]` A selected part disappeared when it lay above the dollhouse cut (13 of 19 parts: ceiling, lamps,
  pipes).~~ Fixed on main in `web/src/scene.ts` (the vertex shader never cuts the selected role); kept as a regression
  test in `tests/web/viewer.test.mjs` ("a selected part stays visible when the camera frames it from above the
  dollhouse cut").
