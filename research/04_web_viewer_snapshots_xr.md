`// VALMET × SINCE AI 2026 · RESEARCH · 04`

# 04: Web viewer, red/grey snapshots, walk mode and Quest 3

Use vanilla three.js with **Spark** (`@sparkjsdev/spark`) to render the cleaned splats on both the laptop and the Quest 3. Keep a `THREE.Points` cloud as a fallback that always works. Take each approval snapshot with a dedicated off-screen render: a fixed camera, a grey see-through room, approved objects as grey glass and the new object in solid red. Save it as a PNG through a `FormData` POST to FastAPI. Walk mode and VR share one camera rig and one 2D occupancy-grid collision function.

`2026-11-06 · npm versions checked live with npm view · Spark API checked against the 2.4.0 type definitions`

---

## 1. Recommendation

| Layer | Pick | Version (npm, 2026-11-06) | Why |
|---|---|---|---|
| Build | `vite` + `typescript` | `vite@8.3.6`, `typescript@7.0.2` | Spark itself builds with Vite 8 and TS 7 (from its devDependencies). |
| 3D | `three` + `@types/three` | `0.187.0` | Spark peer dep is `three >= 0.180.0`. Pin the exact version. |
| Splats | `@sparkjsdev/spark` | `2.4.0` | Maintained, WebXR helper (`SparkXr`), per-region recolour (`SplatEdit`), off-screen target render. |
| Fallback | `THREE.Points` + `BufferGeometry` | (core) | One draw call. Needs no extra library and still works if Spark fails on the day. |
| VR text | `troika-three-text` | `0.53.1` | SDF text, sharp in XR. Bundle the font locally (see Risks). |
| HTTPS (LAN only) | `@vitejs/plugin-basic-ssl` | `2.3.0` | Not needed if you use `adb reverse` (localhost counts as secure). |
| Desktop XR test | Meta Immersive Web Emulator (Chrome extension) or `iwer` | `iwer@2.8.0` | Lets you test VR in desktop Chrome without a headset. |
| UI shell | Plain HTML/CSS + `cyberpunk-tokens.css` | n/a | The curator panel is DOM. The canvas is plain three. |

**Vanilla three, not react-three-fiber.** For a 36 h build:

- Spark, `SparkXr`, the three.js XR examples and most StackOverflow answers are written for vanilla three. With R3F you would wrap every one of them.
- Snapshot code has to take over the renderer for one frame (swap camera, swap materials, render to a target, read pixels). This is simple imperatively and awkward inside R3F's render loop.
- `@react-three/xr@6.6.32` is good, but you would add `@react-three/fiber@9.8.2` and `@react-three/drei@10.7.9`, plus React 19, plus learning time. `sparkjsdev/spark-react-r3f` exists but is a sample, not a supported binding [UNVERIFIED].
- The Cyberpunk tokens are CSS variables. They apply to the DOM panels whatever the 3D layer is. For the 3D scene, read them once with `getComputedStyle(document.documentElement).getPropertyValue('--scene-bg')` and convert to `THREE.Color` (three parses CSS colour strings; check that `oklch()` parses in your three version, and if not, hard-code hex equivalents) [UNVERIFIED].
- If the team already lives in React, use React for the curator side panel only and mount a vanilla `Viewer` class into a `<div>`.

**Colour note.** The design system reserves alarm red (`--destructive`) for status ALERT and magenta (`--selection`) for selection. The user's non-negotiable says "new object red". Keep red **only inside snapshots**. In the live twin, use the theme's selection and status colours.

---

## 2. Options compared

### 2.1 Splat renderers

| Renderer | Package / version | WebXR on Quest 3 | Recolour / hide a subset | Formats | Status |
|---|---|---|---|---|---|
| **Spark** (World Labs) | `@sparkjsdev/spark@2.4.0` | Yes. `SparkXr` helper (VR/AR, hands, `fixedFoveation`, `frameBufferScaleFactor`). Docs: "1 million splats or less" on Quest 3; `maxStdDev: Math.sqrt(5)` for VR. | Yes. `SplatEdit` + `SplatEditSdf` (BOX, SPHERE, ELLIPSOID, CYLINDER, CAPSULE, PLANE, ALL) with `MULTIPLY`, `SET_RGB`, `ADD_RGBA`. `SplatMesh.recolor`, `SplatMesh.opacity`, `objectModifier` (Dyno GPU shader graph). | PLY (incl. compressed), SPZ, SPLAT, KSPLAT, PC-SOGS, RAD (LoD) | Active (updated 2026-10-20) |
| GaussianSplats3D (mkkellogg) | `@mkkellogg/gaussian-splats-3d@0.4.7` | `webXRMode: VR`, but users report poor Quest 3 performance (issue #65). | Opacity effects only (`enableOptionalEffects`). No region recolour. | PLY, SPLAT, KSPLAT | **README says it is no longer in active development and points to Spark.** Last publish Jan 2025. |
| three.js native `GaussianSplatMesh` | `three` r186+ (WebGPU/TSL) | Not stated | Not stated | PLY, SPLAT, SPZ, KSPLAT, glTF `KHR_gaussian_splatting` | Early. SH0 only, no LoD, WebGPU renderer path. Too new to bet on. |
| Luma web | `@lumaai/luma-web@0.2.2` | Has XR demos [UNVERIFIED] | Limited | Luma captures (URL-based) | Built for Luma-hosted captures. Not for our PLY. |
| PlayCanvas / SuperSplat | `playcanvas@2.23.3` | Yes, strong XR splat support | SuperSplat editor can select, delete and recolour | PLY, SOG, compressed PLY | Not three.js. Use **SuperSplat as an offline cleaning tool**, not as the viewer. |

Sorting cost: every splat renderer must depth-sort splats when the view changes. Spark sorts in a web worker, so a late sort shows as brief popping, not a frame drop. On Quest, keep the count low and avoid dense clusters. SplatXR (a Unity project) measured 36 fps at 200 k splats in dense indoor views. Treat **~300–500 k visible splats** as the realistic Quest target for our room, below Spark's 1 M ceiling [UNVERIFIED for our scene].

Our numbers: ~500 k usable splats after cleaning (see `00`). Also strip SH degree 3 (`f_rest_*`), or convert to SPZ, so the Quest does not download 355 MB. Do this in the offline pipeline (`01`).

### 2.2 Point-cloud fallback

| Aspect | Guidance |
|---|---|
| Geometry | One `BufferGeometry` with `position` (Float32) + `color` (Uint8 normalised). Load a raw `.bin` from `07_demo_cache`. |
| Material | `PointsMaterial({ size: 0.02, sizeAttenuation: true, vertexColors: true })`. Size is in world units when attenuated. |
| Performance | 300–500 k points is one draw call. That is easy on a laptop and should hold 72 fps on Quest 3 at small point sizes [UNVERIFIED on device]. Large points mean overdraw, which costs more than the point count. |
| Look | Points look sparse up close in VR. Use a slightly larger size in XR, or render splats. |
| Hide/recolour | Trivial. Write the `color` attribute for indices inside the object's box, then set `needsUpdate = true`. |

### 2.3 Object highlighting styles

| Style | Cost | Looks | Use for |
|---|---|---|---|
| OBB wireframe (`EdgesGeometry(BoxGeometry)` → `LineSegments`) | Tiny | Crisp, "3D framing" (criterion c1) | Every approved object, live and in snapshots |
| `Box3Helper` | Tiny | Axis-aligned only | Debug only (our boxes are oriented) |
| Translucent fill (`transparent`, `opacity 0.12–0.2`, `depthWrite:false`) | Low | Glassy | Grey "rest" objects |
| Convex hull / object mesh (from `04_mesh`, `ConvexGeometry` in addons) | Medium | Reads as the actual object | New object in red; grey glass for others |
| Outline post-pass (`OutlinePass`) | High, breaks in XR | Pretty | Laptop only, optional. Skip for 36 h. |
| Splat tint (`SplatEdit` BOX, MULTIPLY red) | Low | Object "glows" red in the scan itself | New object in snapshot + live highlight |

**Making "rest translucent grey" look good:**
- Desaturate the whole room: one `SplatEdit` with an `ALL` SDF in `SET_RGB` mode with a mid grey, plus `SplatMesh.opacity ≈ 0.35`. The scan becomes a quiet grey ghost.
- Approved objects: fill `#9aa3ad` at opacity 0.15 with `depthWrite:false`, plus edges at opacity 0.6. Lines carry the shape. The fill only adds volume.
- New object: opaque red fill (`#ff2a3d`), red edges, `renderOrder` 10. Set `depthTest:false` on the edges only, so the frame shows through pipes.
- Use a dark background (`--scene-bg`, night mode) for the snapshot. Grey on near-black reads well, and red pops.

### 2.4 Snapshot capture methods

| Method | Disturbs main view? | Perf cost | Verdict |
|---|---|---|---|
| `preserveDrawingBuffer: true` + `canvas.toBlob` | Yes (uses main camera/size) | Costs every frame, worse on Quest tiled GPU | Avoid |
| Render on main canvas then `toBlob` in the same task | Briefly. Must re-render the main view after. | None at rest | OK fallback, but size = window size |
| **`WebGLRenderTarget` + `readRenderTargetPixels` → 2D canvas → `toBlob`** | No | Only when capturing | **Use this** for meshes/points |
| **Spark `SparkRenderer({ target })` + `renderReadTarget()`** | No | Only when capturing; sorts for the snapshot camera | **Use this** when splats are shown |
| Server-side render in Python | No | Needs a renderer in the backend | Backup if the browser path fails |

---

## 3. Recipes

### 3.1 Scene, splats and a fallback

```ts
import * as THREE from 'three';
import { SparkRenderer, SplatMesh } from '@sparkjsdev/spark';

const renderer = new THREE.WebGLRenderer({ antialias: false }); // Spark: MSAA does not help splats
renderer.setPixelRatio(Math.min(devicePixelRatio, 1.5));
const scene = new THREE.Scene();
const spark = new SparkRenderer({ renderer, maxStdDev: Math.sqrt(5) });
scene.add(spark);

let room: SplatMesh | THREE.Points;
try {
  room = new SplatMesh({ url: '/cache/room.spz' });
  await (room as SplatMesh).initialized;           // check name in 2.4 typings [UNVERIFIED]
} catch {
  room = await loadPoints('/cache/room_points.bin'); // Float32 xyz + Uint8 rgb
}
scene.add(room);
```

### 3.2 Red/grey materials and the per-object group

```ts
const GREY = new THREE.Color('#9aa3ad');
const RED  = new THREE.Color('#ff2a3d');

function objectGroup(o: { center: number[]; size: number[]; quat: number[]; hull?: THREE.BufferGeometry }) {
  const g = new THREE.Group();
  g.position.fromArray(o.center); g.quaternion.fromArray(o.quat);
  const box = new THREE.BoxGeometry(...(o.size as [number, number, number]));
  const fill = new THREE.Mesh(o.hull ?? box, new THREE.MeshBasicMaterial());
  const edges = new THREE.LineSegments(new THREE.EdgesGeometry(box), new THREE.LineBasicMaterial());
  g.add(fill, edges); g.userData = { fill, edges };
  return g;
}

function styleGrey(g: THREE.Group) {
  const { fill, edges } = g.userData;
  Object.assign(fill.material, { color: GREY, transparent: true, opacity: 0.15, depthWrite: false });
  Object.assign(edges.material, { color: GREY, transparent: true, opacity: 0.6, depthTest: true });
  fill.renderOrder = 5; edges.renderOrder = 6;
}
function styleRed(g: THREE.Group) {
  const { fill, edges } = g.userData;
  Object.assign(fill.material, { color: RED, transparent: false, opacity: 1, depthWrite: true });
  Object.assign(edges.material, { color: RED, transparent: true, opacity: 1, depthTest: false });
  fill.renderOrder = 10; edges.renderOrder = 11;
}
```

### 3.3 Splat edits for the snapshot (Spark)

```ts
import { SplatEdit, SplatEditSdf, SplatEditSdfType, SplatEditRgbaBlendMode } from '@sparkjsdev/spark';

const greyAll = new SplatEdit({ rgbaBlendMode: SplatEditRgbaBlendMode.SET_RGB });
greyAll.addSdf(new SplatEditSdf({ type: SplatEditSdfType.ALL, color: new THREE.Color(0.45, 0.47, 0.5) }));

const redBox = new SplatEdit({ rgbaBlendMode: SplatEditRgbaBlendMode.SET_RGB });
const sdf = new SplatEditSdf({ type: SplatEditSdfType.BOX, color: RED });
redBox.addSdf(sdf);
// Box size comes from the SDF's Object3D scale (radius = corner rounding).
// Check whether scale means half- or full-extent [UNVERIFIED].
function aimRedBox(o: { center: number[]; size: number[]; quat: number[] }) {
  sdf.position.fromArray(o.center); sdf.quaternion.fromArray(o.quat);
  sdf.scale.fromArray(o.size).multiplyScalar(0.5);
}
// Later edits apply after earlier ones (SplatEdit.ordering), so add greyAll before redBox.
```

### 3.4 Snapshot: fixed camera, off-screen, upload

```ts
const SNAP_W = 1600, SNAP_H = 1000;
// Near-isometric: a narrow-FOV perspective camera far away. This is safer with splats than an
// OrthographicCamera, because Spark's ortho support is [UNVERIFIED].
const snapCam = new THREE.PerspectiveCamera(14, SNAP_W / SNAP_H, 0.5, 200);
snapCam.position.set(-0.4 + 30, 12, -2.2 + 30);   // room centre ≈ (-0.4, -0.2, -2.2), y-up
snapCam.lookAt(-0.4, -0.4, -2.2);
const snapSpark = new SparkRenderer({ renderer, target: { width: SNAP_W, height: SNAP_H, superXY: 2 } });

async function takeSnapshot(approvalId: string, newId: string): Promise<void> {
  // 1. style: room grey, approved grey, new one red
  for (const [id, g] of objects) id === newId ? styleRed(g) : styleGrey(g);
  scene.add(greyAll, redBox); aimRedBox(objects.get(newId)!.userData.obb);
  (room as SplatMesh).opacity = 0.35;
  scene.background = new THREE.Color('#0b0d17');
  hudGroup.visible = false;                        // hide avatar, route, labels
  // 2. render off-screen (Spark sorts for snapCam)
  await snapSpark.update({ scene, camera: snapCam });
  const px = await snapSpark.renderReadTarget({ scene, camera: snapCam }); // RGBA, rows bottom-up
  // 3. restore live styles (next animation frame redraws the main view)
  restoreLiveStyles();
  // 4. pixels -> PNG blob (flip Y)
  const c = new OffscreenCanvas(SNAP_W, SNAP_H); const ctx = c.getContext('2d')!;
  const img = ctx.createImageData(SNAP_W, SNAP_H);
  const row = SNAP_W * 4;
  for (let y = 0; y < SNAP_H; y++) img.data.set(px.subarray((SNAP_H - 1 - y) * row, (SNAP_H - y) * row), y * row);
  ctx.putImageData(img, 0, 0);
  const blob = await c.convertToBlob({ type: 'image/png' });
  // 5. upload
  const fd = new FormData();
  fd.append('file', blob, `snap_${approvalId}.png`);
  fd.append('object_id', newId);
  await fetch(`/api/approvals/${approvalId}/snapshot`, { method: 'POST', body: fd });
}
```

Points-only path (no Spark): use `new THREE.WebGLRenderTarget(W, H, { colorSpace: THREE.SRGBColorSpace })`, then `renderer.setRenderTarget(rt); renderer.render(scene, snapCam); renderer.readRenderTargetPixels(rt, 0, 0, W, H, buf); renderer.setRenderTarget(null)`, then the same flip and upload. Never take a snapshot while `renderer.xr.isPresenting`. Queue it and run it after the session ends.

FastAPI side (needs `python-multipart`):

```python
@app.post("/api/approvals/{aid}/snapshot")
async def snap(aid: str, file: UploadFile = File(...), object_id: str = Form(...)):
    path = SNAP_DIR / f"{aid:0>4}_{object_id}.png"
    path.write_bytes(await file.read()); return {"url": f"/snapshots/{path.name}"}
```

### 3.5 First-person walk with occupancy-grid collision

Use `PointerLockControls` (`three/addons/controls/PointerLockControls.js`) for mouse look and WASD for moving on the XZ plane. Load the same grid the router uses (`02_floor_grid`: origin, cell size, `Uint8Array`, 1 = blocked). Check the circle's leading edge per axis so the player slides along walls.

```ts
type Grid = { ox: number; oz: number; cell: number; w: number; h: number; data: Uint8Array };
const blocked = (g: Grid, x: number, z: number) => {
  const i = Math.floor((x - g.ox) / g.cell), j = Math.floor((z - g.oz) / g.cell);
  return i < 0 || j < 0 || i >= g.w || j >= g.h || g.data[j * g.w + i] === 1;
};
const R = 0.25; // body radius, scene units
function hits(g: Grid, x: number, z: number) {
  for (const [dx, dz] of [[R,0],[-R,0],[0,R],[0,-R],[.7*R,.7*R],[-.7*R,.7*R],[.7*R,-.7*R],[-.7*R,-.7*R]])
    if (blocked(g, x + dx, z + dz)) return true;
  return false;
}
function moveWithSlide(g: Grid, pos: THREE.Vector3, dx: number, dz: number) {
  const steps = Math.ceil(Math.hypot(dx, dz) / (g.cell * 0.5)) || 1; // sub-step: never skip a cell
  for (let s = 0; s < steps; s++) {
    const sx = dx / steps, sz = dz / steps;
    if (!hits(g, pos.x + sx, pos.z)) pos.x += sx;   // try X
    if (!hits(g, pos.x, pos.z + sz)) pos.z += sz;   // then Z → slides along walls
  }
  pos.y = FLOOR_Y + EYE_HEIGHT; // FLOOR_Y ≈ -0.9 (see 00); eye ≈ 1.0 in scene units [UNVERIFIED scale]
}
```

### 3.6 WebXR on Quest 3

```ts
import { SparkXr } from '@sparkjsdev/spark';
const rig = new THREE.Group(); rig.add(camera); scene.add(rig); // move the rig, never the XR camera
const xr = new SparkXr({
  renderer, mode: 'vr', referenceSpaceType: 'local-floor',
  fixedFoveation: 1.0, frameBufferScaleFactor: 1.0,
  onEnterXr: () => { hud.visible = false; }, onExitXr: () => { hud.visible = true; },
});
// Without Spark: renderer.xr.enabled = true; renderer.xr.setReferenceSpaceType('local-floor');
// renderer.xr.setFramebufferScaleFactor(1.0) /* before the session starts */; renderer.xr.setFoveation(1);
// document.body.append(VRButton.createButton(renderer));  // three/addons/webxr/VRButton.js

let snapReady = true;
renderer.setAnimationLoop((t, frame) => {
  const session = renderer.xr.getSession();
  if (session) for (const src of session.inputSources) {
    const ax = src.gamepad?.axes; if (!ax || ax.length < 4) continue;
    if (src.handedness === 'left') {               // smooth move, head-relative
      const fwd = new THREE.Vector3(); renderer.xr.getCamera().getWorldDirection(fwd);
      fwd.y = 0; fwd.normalize(); const right = new THREE.Vector3(-fwd.z, 0, fwd.x);
      const v = fwd.multiplyScalar(-ax[3]).add(right.multiplyScalar(ax[2])).multiplyScalar(1.4 * dt);
      moveWithSlide(grid, rig.position, v.x, v.z);  // same grid collision as desktop
    } else if (src.handedness === 'right') {        // 30° snap turn with dead-zone latch
      if (Math.abs(ax[2]) > 0.7 && snapReady) { rig.rotateY(-Math.sign(ax[2]) * Math.PI / 6); snapReady = false; }
      if (Math.abs(ax[2]) < 0.3) snapReady = true;
    }
  }
  renderer.render(scene, camera);
});
```

- In XR, the rig position is the floor point, so do not add `EYE_HEIGHT` with `local-floor`. Note also that `rotateY` turns the rig around its origin, not around the head. That is fine for a demo.
- Teleport (optional): raycast the right controller ray against a floor plane, check `!hits(grid, p.x, p.z)`, then set `rig.position` on trigger release. The three.js example `webxr_vr_teleport` uses `getOffsetReferenceSpace` instead. Either works.
- Labels: `troika-three-text` `Text` meshes (`fontSize` ≈ 0.05–0.08 m at 1–2 m, `anchorX:'center'`, a `font` URL served locally, `sync()` after changes). Make them face the camera each frame. The alternative is a `THREE.Sprite` with a `CanvasTexture` (draw text at 2× size). DOM/CSS2D labels do **not** render in immersive mode.

---

## 4. Quest 3 checklist

1. Quest in developer mode, USB-C cable, `adb devices` shows it.
2. `npm run dev -- --host` (Vite on 5173), then `adb reverse tcp:5173 tcp:5173` and `adb reverse tcp:8000 tcp:8000` for FastAPI. Open `http://localhost:5173` in **Meta Quest Browser**. Localhost is a secure context, so no certificate is needed.
3. No cable? Use `@vitejs/plugin-basic-ssl` and `https://<laptop-LAN-IP>:5173`, and accept the warning. Plain HTTP over the LAN **will not** expose WebXR. `vite-plugin-mkcert@2.1.0` gives trusted certificates, but it downloads `mkcert` on first run, so do that before Wi-Fi goes off.
4. Proxy `/api` through Vite (`server.proxy`) so the headset uses one origin and you avoid CORS.
5. Debug from the laptop: `chrome://inspect/#devices` → inspect the Quest Browser tab.
6. Desktop testing: Meta **Immersive Web Emulator** extension in Chrome, or `iwer@2.8.0` / `@iwer/devui` injected in dev builds.
7. Budget: hold 72 Hz. Splats ≤ ~500 k visible, `maxStdDev √5`, `antialias:false`, pixel ratio 1, fixed foveation 1, framebuffer scale 1.0. Raise the scale only to sharpen text if fps allows. Keep draw calls in the low hundreds (Meta: ~1,000 draw calls alone can drop you below 72 fps). Merge the OBB edges into one `LineSegments`. No shadows, no post-processing, no PBR (use `MeshBasicMaterial`).
8. Test the exact demo file on the headset by Saturday evening. Keep the `Points` fallback build one toggle away (`?mode=points`).
9. Snapshots are laptop-only. The curator runs on the laptop. XR is the walk-through.

---

## 5. Risks & gotchas

- **Garbage splats.** Two thirds of the PLY is junk (see `00`). An unclean file makes the room invisible inside a far-away cloud and kills the Quest. Load only the cleaned output from `01`.
- **Y-up.** The scan is y-up, floor ≈ y −0.9. three.js is y-up too, so do no axis swap. Check the sign of z once with a known object.
- **Splats vs transparent meshes.** Splats and translucent meshes are sorted per object, not per pixel. Expect some wrong layering. Use `depthWrite:false` on grey fills, draw them after the splats (`renderOrder`), and let edges carry the shape. GaussianSplats3D does not support transparent meshes at all.
- **Async sort for the snapshot.** A new camera needs a new sort. Always `await snapSpark.update(...)` before `renderReadTarget`. Without it you get smeared ordering. If the result still looks wrong, render twice.
- **Readback orientation and colour.** `readRenderTargetPixels` returns rows bottom-up, so flip them. Set the target `colorSpace` to sRGB or the PNG looks washed out.
- **One WebGL context.** Do not create a second `WebGLRenderer` for snapshots. Splat buffers would load twice. Reuse the same renderer with a target.
- **`preserveDrawingBuffer`** hurts every frame on Quest's tiled GPU. Don't.
- **Offline.** The demo must run with Wi-Fi off. Bundle all fonts (troika's default font is fetched from a CDN [UNVERIFIED]; pass a local `font` URL). Never use CDN import maps. `npm ci` and mkcert set-up happen while online.
- **Scale unknown.** Walking speed, eye height and body radius are in scene units. Tune them visually, since metric scale is unverified.
- **XR session edge cases.** Quest may start the session at an odd origin. Spark's own example moves a `localFrame` group to work around this on Quest 3 / Vision Pro. Recentre the rig to the start pose in `onEnterXr`.
- **Typings drift.** Spark 2.x is moving fast. Read `node_modules/@sparkjsdev/spark/dist/types/*.d.ts` rather than older blog posts. 0.1 → 2.0 had breaking changes.
- **three r186+ native splats** may tempt. They are WebGPU/TSL, SH0 only, and very new. Not for this hackathon.

---

## 6. Sources

- Spark overview and formats: https://sparkjs.dev/docs/overview/
- Spark splat editing (SplatEdit, blend modes, BOX SDF): https://sparkjs.dev/docs/splat-editing/
- Spark performance (Quest 3 "1 million splats or less", `maxStdDev √5`, `antialias:false`): https://sparkjs.dev/docs/performance/
- Spark repo and WebXR example (`SparkXr`, localFrame workaround): https://github.com/sparkjsdev/spark , https://github.com/sparkjsdev/spark/blob/main/examples/webxr/index.html
- Spark 2.4.0 package type definitions (`SparkXrOptions`, `SplatEditSdfType`, `SparkRenderer.renderReadTarget`, file types), inspected via `npm pack @sparkjsdev/spark@2.4.0`
- Spark + R3F sample: https://github.com/sparkjsdev/spark-react-r3f
- GaussianSplats3D (maintenance notice, `webXRMode`, no transparent objects): https://github.com/mkkellogg/GaussianSplats3D ; Quest perf issue: https://github.com/mkkellogg/GaussianSplats3D/issues/65
- three.js native splats in r186: https://radiancefields.com/three.js-merges-a-native-gaussian-splat-renderer-for-webgpu-in-r186
- SplatXR (200 k splat guidance, 36 fps measurement): https://radiancefields.com/splatxr-brings-interactive-gaussian-splats-to-quest-3
- three.js VRButton: https://threejs.org/docs/pages/VRButton.html
- Meta WebXR performance workflow and best practices: https://developers.meta.com/horizon/documentation/web/webxr-perf-workflow/ , https://developers.meta.com/horizon/documentation/web/webxr-perf-bp/
- Meta Quest Browser remote debugging: https://developers.meta.com/horizon/documentation/web/browser-remote-debugging/
- Meta IWSDK testing (HTTPS localhost, IWER): https://developers.meta.com/horizon/documentation/iwsdk/guides/02-testing-experience/
- `adb reverse` + localhost secure-context recipe: https://github.com/Open-Muscle/OpenMuscle-AR/wiki/Quick-Start
- WebXR text sharpness and framebuffer scale: https://discourse.threejs.org/t/vr-web-applications-font-rendering-issues-bitmap-vs-sdf/93545
- npm registry versions (checked 2026-11-06 with `npm view`): three 0.187.0, @sparkjsdev/spark 2.4.0, vite 8.3.6, typescript 7.0.2, troika-three-text 0.53.1, @react-three/fiber 9.8.2, @react-three/xr 6.6.32, @react-three/drei 10.7.9, @vitejs/plugin-basic-ssl 2.3.0, vite-plugin-mkcert 2.1.0, iwer 2.8.0, playcanvas 2.23.3, @lumaai/luma-web 0.2.2, @mkkellogg/gaussian-splats-3d 0.4.7
