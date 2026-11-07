# Requests between agents

One line per request, `[from→to] what · why · evidence` (AGENTS.md §7). Strike through or delete when done.

## Open

- `[test→web]` **A selected part disappears when it lies above the dollhouse cut.** `select()` in `web/src/main.ts` frames
  the part from `dir (0.9, 0.8, 1.1)`, which puts the camera above the room (e.g. y 5.6 u vs room top 1.29 u for
  `pipe_1`); `autoCut()` then turns the cutaway on and hides everything above `dollhouse_cut_y` (0.543 u), the selected
  part included, so only its wire box is left. In the current build that is 13 of 19 parts: ceiling, both lamps and
  10 of the 12 pipes. Suggested fix: never cut the selected part (e.g. skip the cut test for role 2 in the vertex
  shader), or switch the auto-cut off while a part above the cut is selected. Test: `make test-web`, the `todo` test
  "a selected part stays visible when the camera frames it from above the dollhouse cut" (drop its `todo` once fixed).
