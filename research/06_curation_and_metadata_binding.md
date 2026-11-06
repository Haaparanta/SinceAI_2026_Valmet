`// VALMET × SINCE AI 2026 · RESEARCH · 06`

# 06: The one-by-one curator, the scene graph and xlsx binding

The offline pipeline proposes objects. A human reviews them one at a time in `/curate` with the keyboard, and every approval is written to an append-only event log. A single `scene_graph.json` is built from that log. Binding to `Asset_Master` is procedural: a class-masked Hungarian assignment on the placeholder `Scene_Anchors`, after a 2D similarity alignment. The faulty target `P-005` is pinned by hand first. The human can override every binding. The result feeds navigation, proximity and the copilot, and exports cheaply to glTF `extras`. USD is a stretch goal.

`2026-11-06 · INPUTS: 00_context, Builder Pack xlsx (Scene_Anchors, Asset_Master, Knowledge_Docs/DOC-3D-MAPPING) · DEPENDS ON: 02 (proposals), 03 (nav grid), 04 (snapshots)`

---

## 1. Recommendation

1. **Event log first, JSON second.** `data/curation/events.jsonl` is the source of truth: one line per decision, never edited. `scene_graph.json` is a projection that is rebuilt after each event and written atomically. Undo appends a `revert` event. This gives us the audit trail ("who approved what, when") for free. That trail is our trust story.
2. **Keyboard-only curator, one object at a time.** Fly the camera to the proposal, isolate it (red, everything else grey), and give it one key per decision. Target **≤ 5 s per decision**, so 150 proposals take about 12 minutes.
3. **Order the queue by "value × confidence".** Large, high-confidence objects come first, so scene density grows fast. Low-confidence and tiny proposals come last, where they can be skipped in bulk if time runs out. Never auto-accept: the user requires one-by-one approval.
4. **Bind in two stages.** (a) The human pins `P-005` to a pump-like, reachable object near the end of a good route. (b) A class-masked Hungarian assignment (`scipy.optimize.linear_sum_assignment`) binds the other 29 assets to approved objects, using anchor coordinates aligned to the scan. Each binding is shown as a *suggestion*, and the human confirms it or presses `B` to override.
5. **Never write the source xlsx.** Write `data/derived/scene_anchors_mapped.csv` (and optionally an `.xlsx` copy) with `mapping_status=human_approved`, real scene coordinates and a new `scene_path`.
6. **Export glTF with `extras`** (three.js puts them in `userData` automatically). Add a USDA export with `usd-core` only if there is time. Mention IFC only in the slides.

Pitch line: *"The AI proposes, the engineer approves. Nothing enters the twin, and no identity is assigned, without a logged human decision."* This matches the brief's own contract in `DOC-3D-MAPPING`: "Never silently guess identity". It also matches the human-oversight idea in EU AI Act Art. 14, which stresses guarding against over-reliance on model output ([AI Act Art. 14](https://www.artificialintelligenceact.eu/article/14/)). We are not claiming legal compliance, only following the same principle.

---

## 2. Lessons from annotation tools

| Tool | Relevant pattern | Take for us |
|---|---|---|
| **CVAT 3D** | Cuboids in a point cloud with top/side/front views. Single-key draw (`N`) and frame stepping (`F`/`D`). Separate *Review* mode for validation ([3D annotation](https://docs.cvat.ai/docs/annotation/manual-annotation/modes/3d-object-annotation/), [editor shortcuts, mirror](https://www.mintlify.com/cvat-ai/cvat/annotation/editor-overview)) | Show three orthographic mini-views next to the 3D view. Use single-letter keys. |
| **Label Studio** | Review stream with **Accept / Fix & Accept / Reject**. Predictions imported as pre-annotations. Configurable task ordering and sampling ([review](https://docs.humansignal.com/guide/quality), [predictions](https://labelstud.io/guide/predictions)) | Copy this decision set exactly. Approve, Relabel+Approve, Reject, Skip. |
| **Segments.ai** | Model-assisted labeling: upload model predictions, then humans correct them. **`q` snaps a cuboid to the points inside it.** "Merged point cloud" mode for static scenes ([MAL](https://segments.ai/data-labeling/model-assisted-labeling/), [cuboid UI](https://docs.segments.ai/how-to-annotate/label-3d-point-clouds/3d-point-cloud-cuboid-interface), [hotkeys](https://docs.segments.ai/how-to-annotate/customize-hotkeys)) | Add a `T` "tighten" key that refits the OBB to its member points on the server. Our scene is static, like their merged mode. |
| **Supervisely** | "Smart tool": lasso a region and a model fits a cuboid. Configurable hotkey map ([3D episodes](https://docs.supervisely.com/labeling/labeling-toolbox/3d-point-cloud-episodes-2), [product](https://supervisely.com/lidar-3d-cloud/)) | Later: "lasso-add" for objects the pipeline missed. Out of scope for v1. |
| **BasicAI / Xtreme1** | One-click detection pre-labels, then a quick object review. Xtreme1 lets you plug in your own model ([BasicAI](https://www.basic.ai/basicai-data-annotation-platform/3d-lidar-point-cloud-annotation-tool), [Xtreme1](https://docs.xtreme1.io/xtreme1-docs)) | Pre-labels plus a fast review list is now the industry default. Our offline pipeline plays the "model" role. |
| **Scale / Labelbox** | Model-assisted labeling with confidence tiers (auto-accept, spot-check, review) ([Labelbox](https://labelbox.com/blog/use-automation-to-reduce-your-labeling-time-and-spend/)) | We keep tiers for *ordering* only, not for auto-accept. |
| **MATLAB Lidar Labeler** | Run the automation algorithm, then **accept or reject** the generated labels ([MathWorks](https://es.mathworks.com/help/lidar/ug/automate-labeling-in-lidar-labeler.html)) | The same "algorithm proposes, human accepts" framing, from a mainstream engineering tool. |
| **Rerun / Foxglove** | Viewers, not curators. Rerun `Boxes3D` takes centers, half-sizes, xyzw quaternions and `class_ids` ([Rerun Boxes3D](https://rerun.io/docs/reference/types/archetypes/boxes3d)) | Log proposals and approvals to an `.rrd` file for debugging and slides. Do not build the curator on top of it. |

**Measured speedups from pre-labelling.** None of these numbers is 3D-cuboid specific:
- 2D boxes: pre-labels from a detector cut annotation time by **about 60 %**, mostly on objects the pre-label already got right (BDD, cited in [DeepBbox](https://arxiv.org/pdf/1909.05620)).
- Industrial segmentation: **73–84 % time saved (mean 78 %)** with DL pre-annotation ([arXiv 2606.19934](https://arxiv.org/pdf/2606.19934)).
- 3D boxes with a pre-trained detector and click-based correction: **3.7 s per object**, reported as 30× faster than manual cuboids ([arXiv 1807.06072](https://ar5iv.arxiv.org/html/1807.06072)).
- A LiDAR one-click tool: a **6.2×** reduction overall ([arXiv 1908.08926](https://arxiv.org/pdf/1908.08926)).

So "seconds per object with pre-labels, versus a minute or more by hand" is a defensible pitch claim. Our own number should come from timing our curator log (see §3).

**Ordering.** Active-learning work says uncertainty sampling is the cheapest first strategy, and that it works best combined with diversity ([Munro, HITL ML](https://livebook.manning.com/book/human-in-the-loop-machine-learning/part-2), [survey](https://ar5iv.labs.arxiv.org/html/2405.00334)). We have no model to retrain during the hackathon, so ordering is about *demo value*, not learning efficiency.

---

## 3. Curator UX spec (`/curate`)

**Layout.** On the left, the three.js viewport: the current proposal in red, approved objects in grey wireframe, the rest of the cloud at about 15 % opacity. On the right, a card with proposal id, class guess, confidence, point count, OBB size, the suggested asset binding with its score, and a row of three orthographic thumbnails. At the bottom: a progress bar, a decisions-per-minute counter and the last 5 decisions.

**Keys.** Every key works without the mouse. Mouse orbit stays available.

| Key | Action | Event written |
|---|---|---|
| `A` / `Enter` | Approve as shown | `approve` (then snapshot) |
| `X` | Reject (false positive or junk) | `reject` |
| `S` / `Space` | Skip, re-queue at the end | `skip` |
| `1`–`9` | Relabel to class *n* in a fixed palette (valve, pump, motor, transmitter, sensor, pipe, tank, panel, other), then approve | `approve` with `label_override` |
| `M` | Merge with the nearest approved object (highlighted in yellow while `M` is held). Confirm with `Enter` | `merge` (union of point indices, OBB refit) |
| `T` | Tighten: server refits the OBB to the member points (Segments.ai `q` idea) | `edit_obb` |
| `B` | Binding picker: type-ahead on tag (`P-0…`), `Enter` to bind, `Esc` to keep the suggestion | `bind` with `source=human` |
| `U` | Unbind (object stays, no asset identity) | `unbind` |
| `Z` | Undo the last decision | `revert` (target = event id) |
| `F` | Refocus camera on the proposal | none |
| `←` / `→` | Previous / next proposal without deciding | none |
| `?` | Shortcut overlay | none |

**Rules.**
- One proposal on screen at a time (non-negotiable #1). Nothing is batch-approved.
- Every key gives visible feedback within 100 ms: an optimistic UI update, then the server confirms. If the server rejects, roll the UI back with a toast.
- Prefetch the next 3 proposals (point subsets + thumbnails) so the camera fly-to is instant.
- The snapshot (red new object, grey others; see 04) runs in the background after `approve`. It must not block the next decision.

**Queue order.** Score each proposal as `priority = confidence × log(1 + point_count) × class_weight`, with `class_weight = 2` for classes present in `Asset_Master` (valve, pump, motor, transmitter, sensor) and 1 for others. Work in three tiers. First the top tier (high confidence, large objects): this builds visible density for criterion c1 fast. Then the middle tier. Then the "uncertain" tier (confidence < 0.4, or under 200 points). Hold back very near duplicates (centroid distance under 0.15 units to an approved object) and show them right after their twin with a "merge?" hint.

**Throughput target.** ≤ 5 s median per decision, ≥ 12 decisions/minute. With about 150 proposals, a full pass takes about 12–15 minutes. That is short enough to redo after a pipeline change on Saturday night. Log `decided_at - shown_at` per event, so we can put *our* measured seconds-per-object on a slide.

**Demo plan.** Curate most of the scene before the demo, and keep the log as evidence. Approve the last 3–5 objects live, including one relabel, one reject and one undo, then show the snapshot appear.

---

## 4. Scene-graph schema

**Event (one line in `events.jsonl`):**

```json
{"event_id":"ev-000231","ts":"2026-11-07T21:14:03.512Z","actor":"vesa","session":"cur-02",
 "type":"approve","proposal_id":"prop-0087","label_override":"PROCESS_PUMP",
 "shown_at":"2026-11-07T21:13:59.901Z","client_version":"curate@0.3.1"}
```

Event types: `approve`, `reject`, `skip`, `merge`, `edit_obb`, `bind`, `unbind`, `revert`, `pin_target`.

**Materialised `scene_graph.json` (one object shown):**

```json
{
  "schema": "valmet-twin/scene-graph@1",
  "frame": {"up": "y", "units": "scene_units", "metric_scale": null, "floor_y": -0.9,
            "source": "Industrial Boiler Room (1).ply", "clean_bbox": [[-4.7,-1.5,-4.4],[3.9,1.1,0.0]]},
  "built_from": {"events": "events.jsonl", "last_event_id": "ev-000231", "n_events": 231},
  "objects": [{
    "object_id": "obj-0042",
    "class": "PROCESS_PUMP",
    "label": "Pump P-005",
    "obb": {"center": [1.92, -0.71, -3.10], "size": [0.52, 0.38, 0.30],
            "rotation_xyzw": [0.0, 0.2588, 0.0, 0.9659]},
    "geometry": {"point_indices_ref": "points/obj-0042.u32.bin", "n_points": 4813,
                 "mesh_ref": "meshes/obj-0042.glb"},
    "provenance": {"proposal_ids": ["prop-0087", "prop-0091"], "algorithm": "03_propose:dbscan+clip@a1f3c",
                   "proposal_confidence": 0.71, "class_source": "human_relabel"},
    "approval": {"decision": "approve", "by": "vesa", "at": "2026-11-07T21:14:03.512Z",
                 "event_ids": ["ev-000231", "ev-000240"], "seconds_to_decide": 3.6},
    "binding": {"asset_id": "ASSET-017", "tag": "P-005", "scene_anchor_id": "ANCHOR-017",
                "source": "human_pin", "score": 1.0, "suggested_asset_id": "ASSET-016",
                "event_id": "ev-000245"},
    "nav": {"approach_cell": [41, 12], "reachable": true},
    "snapshot": "snapshots/0042.png"
  }],
  "rejected_proposals": ["prop-0003", "prop-0011"],
  "unbound_assets": ["ASSET-029"]
}
```

**Design notes.**
- **Quaternions in xyzw order.** Rerun and three.js (`Quaternion(x,y,z,w)`) use this order. Note that `scipy.spatial.transform.Rotation.as_quat()` is xyzw by default, while glTF stores `rotation` as `[x,y,z,w]` and USD `GfQuatf` is `(w, x, y, z)`. Convert explicitly at every boundary.
- **Point indices are stored out-of-line** as little-endian `uint32` binary files, indexing into the *cleaned* point array. Also record the cleaning hash in `frame`, so the indices fail loudly if the cleaning step changes.
- **Merged objects** keep all `proposal_ids`. Their indices are the union, and the OBB is refit with PCA on the server.
- **Append-only log vs mutable JSON.** The log is the audit record and the undo stack, and can be replayed. The JSON is a fast read model for the viewer, nav and copilot. This is the event-sourcing pattern without a framework. Rebuilding the projection from ≤ 1,000 events takes milliseconds.
- **Atomic write.** Write to a temp file in the same directory, `flush()` + `os.fsync()`, then `os.replace()`. This is atomic only on the same filesystem ([pattern](https://dev.to/constanta/crash-safe-json-at-scale-atomic-writes-recovery-without-a-db-3aic)). Atomic replace does not serialise writers, so wrap the whole read-modify-write in a lock.
- **Locking in FastAPI.** Run one uvicorn worker. Wrap the handler in a module-level `asyncio.Lock`, plus a `filelock.FileLock("data/curation/.lock")` in case a CLI script (for example `05_bind_metadata`) writes at the same time. Append to `events.jsonl` with `open(..., "a")` and one `write()` of a single line ending in `\n`, then fsync. [UNVERIFIED: single-line appends under ~4 KB are not interleaved on macOS APFS. The lock makes this moot anyway.]
- **Undo.** `revert` names an `event_id`. The projector skips reverted events. Undoing a `merge` restores both source objects. Undoing an `approve` removes the object and queues its snapshot for regeneration (or marks the snapshot as superseded).
- **IDs.** `object_id` is stable and assigned at the first approval. It is never reused, even after a revert, so snapshots and logs stay unambiguous.

**Consumers.**
- Nav (03) reads OBBs as obstacles and `nav.approach_cell` as goal cells.
- Proximity reads centers and OBBs for k-nearest and distance-to-box queries.
- The copilot (05) gets `binding.asset_id` and then joins to `Current_State`, `Telemetry` and `Knowledge_Docs`. It must cite `binding.source` and `approval.by`, so it can say "identity confirmed by a human on …" versus "suggested".

---

## 5. Binding algorithm (`05_bind_metadata`)

**What the xlsx gives us** (read-only, measured):
- 30 assets: 12 CONTROL_VALVE, 6 PROCESS_PUMP, 6 ELECTRIC_MOTOR, 3 PRESSURE_TRANSMITTER, 3 VIBRATION_SENSOR.
- `Scene_Anchors` is a synthetic grid. x is 0 to 30.4 and y is 0 to 15.5 (5 rows of about 6–7 assets, z-up, z from 0.47 to 2.15). Default bbox sizes are per class: valve 1.0×0.8×1.3, pump 1.8×1.0×1.1, and so on.
- `area_id` is scattered across the grid, so areas carry no spatial meaning.
- `P-005` sits at (4.36, 10.17, 1.57), in the left part of row 3.
- Every row says `mapping_status=placeholder_until_valmet_scene_received`, `mapping_confidence=0.65`, and "Remap to real scene path and bounds when Valmet splat arrives."
- **Useful coincidence:** the anchor footprint (about 30.7 × 15.9, aspect 1.93) has almost the same aspect ratio as the cleaned room floor (8.6 × 4.4 scene units, aspect 1.95).

**Steps.**
1. **Align frames.** Map anchor `(x, y, z)` (z-up) to scan `(x', z', y')` (y-up) with a 2D similarity: uniform scale `s ≈ 8.6/30.7 ≈ 0.28`, plus a translation to the clean bbox. Try the four axis flips and keep the one whose aligned anchors land closest to approved objects of the same class. Height: `y' = floor_y + s·z`. This is honest "procedural" placement. Say so in the README.
2. **Pin the target first.** In the curator, the human presses `P` on the chosen object (`pin_target` event). The object should be:
   - pump-like: approved with class PROCESS_PUMP, a squat OBB, on or near the floor;
   - reachable: its approach cell is on the 03 nav grid, within about 0.5 units of an OBB face;
   - at the end of a good route: from the spawn point, the path is in the top third of lengths among candidates, and it passes at least 4 other bound assets within the proximity radius, so the proximity display has something to show.

   Have 02/03 output a ranked shortlist of 3 candidates, so the pin takes one keystroke.
3. **Class-masked Hungarian for the other 29.** Cost `C[i,j] = ‖anchor_i − object_j‖₂ (aligned, scene units)`, plus `λ·|log(vol_i/vol_j)|`, with `+∞` (use `1e6`) when classes are incompatible. Compatibility: exact match. If there are not enough objects of a class, relax with a penalty: pump ↔ motor (pumps sit on motors), transmitter ↔ sensor ↔ valve (small inline devices). Solve with `scipy.optimize.linear_sum_assignment`, which accepts rectangular matrices and leaves extra rows unassigned ([SciPy docs](https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.linear_sum_assignment.html)). Drop pairs with cost ≥ 1e6, and list those assets as `unbound_assets`. Do not force them.
4. **Greedy fallback.** If scipy is unavailable or there are fewer than 3 objects of a class, use class-matched greedy assignment: sort all (anchor, object) pairs by cost and take the cheapest unused pairs. This is good enough with 30 assets.
5. **Score.** `binding_score = exp(-cost/σ)` in 0–1. Show it on the curator card and in the twin. Mark bindings as `source=procedural` until confirmed.
6. **Human confirmation pass.** After the main curation, `/curate?mode=bind` walks the 30 assets one by one: `A` accepts the suggestion, `B` overrides, `U` leaves the asset unplaced. Each accept is a `bind` event with `source=human_confirmed`.
7. **Write `scene_anchors_mapped.csv`.** Use the same columns as `Scene_Anchors`, with:
   - `x/y/z_local_m` set to the scene-unit OBB center (rename the header to `_scene` or add a `units` column, since the scale is unverified);
   - `bbox_*` from the OBB size;
   - `scene_path=/BoilerRoom/<CLASS>/<tag>`;
   - `mapping_status=human_approved` (or `procedural_suggested`);
   - `identity_methods="procedural class+position match; human approval in curator"`;
   - `mapping_confidence=min(proposal_confidence, binding_score)`, set to 1.0 for the human pin;
   - a new `approval_event_id` column.

   Also emit `.xlsx` via openpyxl to a *new* file in `data/derived/`.

**Why Hungarian over pure greedy:** it is one line of code, globally optimal, and easy to explain on a slide ("optimal assignment, not random"). The class mask is what keeps it honest.

---

## 6. Export options

| Format | What to write | Effort | Value |
|---|---|---|---|
| `scene_graph.json` (native) | Section 4 | done | Source for nav, proximity, copilot |
| **glTF/GLB + `extras`** | One node per object (OBB as a scaled unit cube or the mesh), with `extras = {object_id, class, asset_id, tag, confidence, approval}`. three.js `GLTFLoader` copies node `extras` into `object.userData`. Keep extras as objects, not primitives ([three.js GLTFLoader](https://threejs.org/docs/pages/GLTFLoader), [loader issue](https://lightrun.com/answers/mrdoob-three-js-gltfloader-primitive-type-extras)) | **Low** (pygltflib or trimesh) | Opens in any viewer. Same file feeds the Quest build |
| glTF + `KHR_xmp_json_ld` | Standardised descriptive metadata packets per node ([spec](https://github.com/KhronosGroup/glTF/blob/main/extensions/2.0/Khronos/KHR_xmp_json_ld/README.md)) | Medium | Good slide talking point. `extras` is enough at runtime |
| **OpenUSD (`.usda`)** | `pip install usd-core`. An `Xform` per object with a scaled `Cube`. Labels via `SemanticsLabelsAPI:class` → `semantics:labels:class = ["PROCESS_PUMP"]` (OpenUSD ≥ 24.11) ([NVIDIA semantic labels](https://docs.omniverse.nvidia.com/kit/docs/asset-requirements/latest/capabilities/semantic_labels/capability-semantic_labels.html)). Asset metadata in `customData` | Medium (about 2 h) | The xlsx START_HERE names OpenUSD/Omniverse. Strong interoperability story. [UNVERIFIED: the `usd-core` wheel registers `SemanticsLabelsAPI`. If it does not, author the `semantics:labels:class` token[] attribute directly] |
| Rerun `.rrd` | `rr.log("objects", rr.Boxes3D(centers, half_sizes, quaternions, class_ids))` plus the points ([Rerun](https://rerun.io/docs/reference/types/archetypes/boxes3d)) | Low | Debugging and slide visuals. Not the product |
| IFC4 | `ifcopenshell`: `IfcPump`/`IfcValve`/`IfcBuildingElementProxy` plus `pset.add_pset` with asset props ([OSArch](https://community.osarch.org/discussion/comment/16222/)) | High (placement, geometry, units) | Mention as a future BIM/CMMS path only |
| 3D scene-graph papers (Hydra, Rosinol) | Layers: mesh → objects → places → rooms, with edges ([Hydra](https://arxiv.org/pdf/2201.13360), [RSS'22](https://roboticsproceedings.org/rss18/p050.html)) | Low (just naming) | Our graph is a two-layer version (objects + nav places). Optional `edges: [{"a","b","rel":"near"}]` from proximity. Cite it as the academic frame |

---

## 7. Risks and gotchas

- **Class supply mismatch.** The scan may show 2 pumps and 30 valve-like blobs, while the xlsx wants 6 pumps and 12 valves. Allow relaxed classes with a penalty, and allow `unbound_assets`. Show the counts honestly ("27 of 30 assets bound").
- **The P-005 story depends on 03.** If the pinned object becomes unreachable after a grid change, the demo breaks. Re-validate reachability when the projection is rebuilt, and flag a broken pin in the curator.
- **Frame and scale confusion.** The anchors are z-up and in metres, the scan is y-up and in unknown units. Do the conversion in exactly one function, with a unit test on `P-005`.
- **Quaternion order.** USD is `(w, x, y, z)`; three.js, glTF and Rerun are `xyzw`. A wrong order gives silently rotated boxes.
- **Point indices drift** if `01_clean` is re-run with other thresholds. Store the clean hash, and refuse to load mismatched indices.
- **Lost updates** if two tabs or a script write at once. Use one worker plus the lock. Show a single "curator session active" banner.
- **Undo of merge and bind chains.** Reverting an approve must cascade to its bind. Keep the projector pure (log in, JSON out) and test it with a 10-event fixture.
- **Snapshot backlog.** Rendering each snapshot synchronously would kill throughput. Queue the snapshots, and number them by `object_id`.
- **Automation bias in our own UI.** A green "suggested binding" invites blind `A` presses. Show the score, and colour low scores amber. This is exactly the over-reliance risk Art. 14 names ([AI Act Art. 14](https://www.artificialintelligenceact.eu/article/14/)).
- **Do not overwrite source data.** The repo says `Source-Data-Do-Not_change`. Write all derived files to `data/derived/`.
- **Keyboard focus.** The three.js canvas and text inputs steal keys. Bind keys on `window`, and ignore them while the `B` picker input has focus.

---

## 8. Sources

- CVAT 3D object annotation: https://docs.cvat.ai/docs/annotation/manual-annotation/modes/3d-object-annotation/
- CVAT editor shortcuts (unofficial mirror): https://www.mintlify.com/cvat-ai/cvat/annotation/editor-overview
- Label Studio review/quality: https://docs.humansignal.com/guide/quality
- Label Studio predictions: https://labelstud.io/guide/predictions
- Segments.ai model-assisted labeling: https://segments.ai/data-labeling/model-assisted-labeling/
- Segments.ai cuboid interface: https://docs.segments.ai/how-to-annotate/label-3d-point-clouds/3d-point-cloud-cuboid-interface
- Segments.ai hotkeys: https://docs.segments.ai/how-to-annotate/customize-hotkeys
- Supervisely 3D episodes: https://docs.supervisely.com/labeling/labeling-toolbox/3d-point-cloud-episodes-2
- Supervisely 3D toolbox: https://supervisely.com/lidar-3d-cloud/
- BasicAI 3D tool: https://www.basic.ai/basicai-data-annotation-platform/3d-lidar-point-cloud-annotation-tool
- Xtreme1 docs: https://docs.xtreme1.io/xtreme1-docs
- Labelbox automation: https://labelbox.com/blog/use-automation-to-reduce-your-labeling-time-and-spend/
- MathWorks Lidar Labeler automation: https://es.mathworks.com/help/lidar/ug/automate-labeling-in-lidar-labeler.html
- DeepBbox (cites BDD 60 % pre-label saving): https://arxiv.org/pdf/1909.05620
- Industrial segmentation pre-annotation (78 %): https://arxiv.org/pdf/2606.19934
- Pre-trained 3D detector for fast GT (3.7 s/object): https://ar5iv.arxiv.org/html/1807.06072
- LiDAR one-click tool (6.2×): https://arxiv.org/pdf/1908.08926
- Munro, Human-in-the-Loop ML: https://livebook.manning.com/book/human-in-the-loop-machine-learning/part-2
- Deep active learning survey: https://ar5iv.labs.arxiv.org/html/2405.00334
- EU AI Act Art. 14: https://www.artificialintelligenceact.eu/article/14/
- Rerun Boxes3D: https://rerun.io/docs/reference/types/archetypes/boxes3d
- three.js GLTFLoader: https://threejs.org/docs/pages/GLTFLoader
- GLTFLoader primitive extras issue: https://lightrun.com/answers/mrdoob-three-js-gltfloader-primitive-type-extras
- KHR_xmp_json_ld: https://github.com/KhronosGroup/glTF/blob/main/extensions/2.0/Khronos/KHR_xmp_json_ld/README.md
- NVIDIA / OpenUSD semantic labels: https://docs.omniverse.nvidia.com/kit/docs/asset-requirements/latest/capabilities/semantic_labels/capability-semantic_labels.html
- Hydra 3D scene graphs: https://arxiv.org/pdf/2201.13360 · https://roboticsproceedings.org/rss18/p050.html
- SciPy linear_sum_assignment: https://docs.scipy.org/doc/scipy/reference/generated/scipy.optimize.linear_sum_assignment.html
- Atomic JSON writes: https://dev.to/constanta/crash-safe-json-at-scale-atomic-writes-recovery-without-a-db-3aic
- ifcopenshell psets (OSArch): https://community.osarch.org/discussion/comment/16222/
- Builder Pack xlsx: `Scene_Anchors`, `Asset_Master`, `Knowledge_Docs/DOC-3D-MAPPING`, `START_HERE` (read-only, measured 2026-11-06)
