/**
 * The step-by-step build as one point cloud, shared by the viewer (main.ts) and the snapshot page (capture.ts).
 *
 * Data: data/derived/viewer/scene.{bin,json}, written by scripts/export_viewer_scene.py. The pool (scan points not yet
 * claimed by a part) comes first, then every accepted part as one contiguous range in acceptance order.
 *
 * Rendering: the same geometry is drawn in up to three passes, one per role: pool, built (accepted parts up to `upto`),
 * selected (one part). Each pass has its own opacity and tint, so the Scan / Model / Overlay / Wireframe sources (after
 * the 3D Model Anything viewer, MIT, Wes Bos) and both snapshot styles come from one shader. A part after `upto` counts
 * as pool: scrubbing `upto` replays the build.
 *
 * Builds: the manual step-by-step build (default), the automatic one (?scene=auto, scripts/export_autoscene_viewer.py) or
 * both at once (?scene=both): the manual export as is (its pool is the whole kept scan) followed by the automatic
 * objects, so parts 1..manual_parts are manual and the rest automatic. Every part carries its `origin`.
 */
import * as THREE from "three";

export type V3 = [number, number, number];
export interface BBox {
  min: V3;
  max: V3;
}
export interface PartMeta {
  seq: number;
  step: number;
  name: string;
  label: string;
  kind: string;
  /** automatic build only: structure | yoloe | cluster, and the detector's confidence */
  source?: string;
  confidence?: number;
  count: number;
  start: number;
  end: number;
  bbox: BBox;
  /** the step images the part was accepted with (file names in images/, served at /api/images/<name>) */
  images?: string[];
  /** ISO time of the acceptance step */
  accepted_at?: string;
  /** which build the part comes from (set by loadScene) */
  origin?: Origin;
}
export interface SceneMeta {
  version: number;
  /** "autoscene" for the automatic build, "both" for the two merged (loadScene); absent for the manual one */
  build?: string;
  /** build "both": parts 1..manual_parts are the manual build, the rest the automatic one */
  manual_parts?: number;
  /** build "both": rows of the automatic export's pool that were dropped (its scene.splat skips the same rows) */
  auto_pool_count?: number;
  exported_at: string;
  source: { file: string; header_rows: number; real_rows: number };
  frame: string;
  units: string;
  count: number;
  pool_count: number;
  pool_total: number;
  removed_count: number;
  room_bounds: BBox;
  floor_y: number;
  dollhouse_cut_y: number | null;
  parts: PartMeta[];
}

export type Source = "scan" | "model" | "overlay" | "wireframe";
export const SOURCES: Source[] = ["scan", "model", "overlay", "wireframe"];
/**
 * true = real colours (the user's image rule since 2026-11-06 22:25); redgrey = AGENTS.md M5 recipe;
 * origin = built parts tinted by the build they come from (manual cyan, automatic amber), selected red.
 */
export type Style = "true" | "redgrey" | "origin";
export const STYLES: Style[] = ["true", "redgrey", "origin"];
export type Origin = "manual" | "auto";

export interface ViewState {
  source: Source;
  style: Style;
  /** part seq (1-based) or 0 for none */
  selected: number;
  /** show parts 1..upto as built; later parts count as pool */
  upto: number;
  /** hide points above the dollhouse cut height */
  cut: boolean;
  /** draw a wire box around every built part (always on in wireframe) */
  boxes: boolean;
  /** build "both": which builds to draw (a hidden manual build falls back to plain scan, a hidden automatic one vanishes) */
  show: Show;
}
export type Show = "both" | "manual" | "auto";

const RED = new THREE.Color(0xff2d55);
const GREY = new THREE.Color(0x9aa0a6);
const WIRE = new THREE.Color(0x9de2f0);
/** "By origin" colours (also the list tags in style.css: keep in sync) */
export const ORIGIN_COLOUR: Record<Origin, string> = { manual: "#00e5ff", auto: "#ffb020" };
const MANUAL_TINT = new THREE.Color(ORIGIN_COLOUR.manual);
const AUTO_TINT = new THREE.Color(ORIGIN_COLOUR.auto);

interface RoleLook {
  alpha: number;
  tint?: THREE.Color;
  /** tint for automatic parts when it differs from `tint` (style "origin") */
  autoTint?: THREE.Color;
}
type Looks = [pool: RoleLook, built: RoleLook, selected: RoleLook];

/** Opacity per role for a view state. Selection follows the user's image rule: selected 80 %, built 20 %, rest 8 %. */
export function looksFor(s: ViewState): Looks {
  const sel = s.selected > 0;
  if (s.style === "redgrey") {
    // AGENTS.md M5 snapshot recipe: new object red and opaque, other approved objects grey at 25 %, raw points hidden.
    return [{ alpha: 0 }, { alpha: 0.25, tint: GREY }, { alpha: 1, tint: RED }];
  }
  if (s.style === "origin") {
    return [{ alpha: sel ? 0.05 : 0.1 }, { alpha: sel ? 0.3 : 1, tint: MANUAL_TINT, autoTint: AUTO_TINT }, { alpha: 1, tint: RED }];
  }
  switch (s.source) {
    case "scan":
      return [{ alpha: 1 }, { alpha: 1 }, { alpha: 1 }];
    case "model":
      return sel ? [{ alpha: 0 }, { alpha: 0.2 }, { alpha: 1 }] : [{ alpha: 0 }, { alpha: 1 }, { alpha: 1 }];
    case "overlay":
      return sel ? [{ alpha: 0.08 }, { alpha: 0.2 }, { alpha: 0.8 }] : [{ alpha: 0.12 }, { alpha: 1 }, { alpha: 1 }];
    case "wireframe":
      return [{ alpha: 0.04 }, { alpha: 0.3 }, { alpha: 0.7 }];
  }
}

const vertexShader = /* glsl */ `
attribute float part;
attribute vec3 rgb;
attribute float psize;
uniform float uRole;
uniform float uUpto;
uniform float uSelected;
uniform float uCutY;
uniform float uCutOn;
uniform float uHalfH;
uniform float uSizeScale;
uniform vec3 uTint;
uniform vec3 uTintAuto;
uniform float uSplit;
uniform float uHideManual;
uniform float uHideAuto;
uniform float uTintMix;
varying vec3 vColor;
void main() {
  bool isAuto = part > uSplit + 0.5;
  // a hidden automatic build vanishes (its rows repeat scan points); a hidden manual build is plain scan again
  if (isAuto && uHideAuto > 0.5) {
    gl_Position = vec4(2.0, 2.0, 2.0, 1.0);
    gl_PointSize = 0.0;
    return;
  }
  bool hidden = !isAuto && part > 0.5 && uHideManual > 0.5;
  float role = (part < 0.5 || part > uUpto + 0.5 || hidden) ? 0.0 : (abs(part - uSelected) < 0.5 ? 2.0 : 1.0);
  // the dollhouse cut never hides the selected part (a lamp or a pipe up by the ceiling stays visible)
  if (abs(role - uRole) > 0.5 || (uCutOn > 0.5 && role < 1.5 && position.y > uCutY)) {
    gl_Position = vec4(2.0, 2.0, 2.0, 1.0);
    gl_PointSize = 0.0;
    return;
  }
  vec4 mv = modelViewMatrix * vec4(position, 1.0);
  gl_Position = projectionMatrix * mv;
  bool ortho = projectionMatrix[3][3] > 0.5;
  float pxPerUnit = projectionMatrix[1][1] * uHalfH / (ortho ? 1.0 : max(-mv.z, 0.001));
  gl_PointSize = clamp(psize * 0.001 * uSizeScale * pxPerUnit, 1.0, 48.0);
  vColor = mix(rgb, isAuto ? uTintAuto : uTint, uTintMix);
}`;

const fragmentShader = /* glsl */ `
uniform float uAlpha;
varying vec3 vColor;
void main() {
  vec2 c = gl_PointCoord * 2.0 - 1.0;
  if (dot(c, c) > 1.0) discard;
  gl_FragColor = vec4(vColor, uAlpha);
}`;

export function parseScene(buf: ArrayBuffer, meta: SceneMeta): THREE.BufferGeometry {
  const n = meta.count;
  const expected = n * (12 + 2 + 3 + 1);
  if (buf.byteLength !== expected) {
    throw new Error(`scene.bin is ${buf.byteLength} bytes, scene.json says ${n} points (${expected} bytes): re-export`);
  }
  const g = new THREE.BufferGeometry();
  g.setAttribute("position", new THREE.BufferAttribute(new Float32Array(buf, 0, n * 3), 3));
  g.setAttribute("part", new THREE.BufferAttribute(new Uint16Array(buf, n * 12, n), 1));
  g.setAttribute("rgb", new THREE.BufferAttribute(new Uint8Array(buf, n * 14, n * 3), 3, true));
  g.setAttribute("psize", new THREE.BufferAttribute(new Uint8Array(buf, n * 17, n), 1));
  const b = meta.room_bounds;
  g.boundingBox = new THREE.Box3(new THREE.Vector3(...b.min), new THREE.Vector3(...b.max));
  g.boundingSphere = g.boundingBox.getBoundingSphere(new THREE.Sphere());
  return g;
}

/** Which build to show: the manual step-by-step build (default), the automatic one (?scene=auto) or both (?scene=both). */
export type Build = "manual" | "auto" | "both";
export const BUILDS: Build[] = ["manual", "auto", "both"];
export function buildFromUrl(params: URLSearchParams): Build {
  const b = params.get("scene");
  return b === "auto" || b === "both" ? b : "manual";
}

/** Number of manual parts at the start of meta.parts (the rest are automatic). */
export function manualCount(meta: SceneMeta): number {
  return meta.manual_parts ?? (meta.build === "autoscene" ? 0 : meta.parts.length);
}

const EXPORTS: Record<Origin, { base: string; script: string }> = {
  manual: { base: buildBase("manual"), script: "export_viewer_scene.py" },
  auto: { base: buildBase("auto"), script: "export_autoscene_viewer.py" },
};
const BYTES_PER_POINT = 12 + 2 + 3 + 1;

interface RawScene {
  meta: SceneMeta;
  buf: ArrayBuffer;
}

async function fetchExport(origin: Origin): Promise<RawScene> {
  const { base, script } = EXPORTS[origin];
  const hint = `run \`uv run python scripts/${script}\` first`;
  const [metaRes, binRes] = await Promise.all([fetch(`${base}/scene.json`), fetch(`${base}/scene.bin`)]);
  if (!metaRes.ok) throw new Error(`GET ${base}/scene.json -> ${metaRes.status}: ${hint}`);
  if (!binRes.ok) throw new Error(`GET ${base}/scene.bin -> ${binRes.status}: ${hint}`);
  const meta = (await metaRes.json()) as SceneMeta;
  meta.parts = meta.parts.map((p) => ({ ...p, origin }));
  return { meta, buf: await binRes.arrayBuffer() };
}

/**
 * Both builds as one scene: the manual export unchanged (pool + parts), then the automatic export's parts block (its pool
 * is dropped: it is the same scan, already in the manual pool and parts). Automatic part ids shift by the manual part
 * count; points of a part the two builds share are drawn twice, once per build.
 */
export function mergeBuilds(manual: RawScene, auto: RawScene): RawScene {
  for (const r of [manual, auto]) {
    const want = r.meta.count * BYTES_PER_POINT;
    if (r.buf.byteLength !== want) {
      throw new Error(`scene.bin is ${r.buf.byteLength} bytes, scene.json says ${r.meta.count} points (${want} bytes): re-export`);
    }
  }
  const nm = manual.meta.count;
  const na = auto.meta.count;
  const ap = auto.meta.pool_count;
  const add = na - ap;
  const n = nm + add;
  const shift = manual.meta.parts.length;
  if (shift + auto.meta.parts.length > 65535) throw new Error("too many parts for uint16 part ids");

  const buf = new ArrayBuffer(n * BYTES_PER_POINT);
  new Float32Array(buf, 0, n * 3).set(new Float32Array(manual.buf, 0, nm * 3));
  new Float32Array(buf, 0, n * 3).set(new Float32Array(auto.buf, ap * 12, add * 3), nm * 3);
  const part = new Uint16Array(buf, n * 12, n);
  part.set(new Uint16Array(manual.buf, nm * 12, nm));
  const autoPart = new Uint16Array(auto.buf, na * 12 + ap * 2, add);
  for (let i = 0; i < add; i++) part[nm + i] = autoPart[i] + shift;
  const bytes = (src: RawScene, count: number, at: number, skip: number, width: number) =>
    new Uint8Array(src.buf, count * at + skip * width, (src === manual ? nm : add) * width);
  const rgb = new Uint8Array(buf, n * 14, n * 3);
  rgb.set(bytes(manual, nm, 14, 0, 3));
  rgb.set(bytes(auto, na, 14, ap, 3), nm * 3);
  const size = new Uint8Array(buf, n * 17, n);
  size.set(bytes(manual, nm, 17, 0, 1));
  size.set(bytes(auto, na, 17, ap, 1), nm);

  const m = manual.meta;
  const a = auto.meta;
  const offset = nm - ap;
  const bounds: BBox = {
    min: [0, 1, 2].map((k) => Math.min(m.room_bounds.min[k], a.room_bounds.min[k])) as V3,
    max: [0, 1, 2].map((k) => Math.max(m.room_bounds.max[k], a.room_bounds.max[k])) as V3,
  };
  const meta: SceneMeta = {
    ...m,
    build: "both",
    manual_parts: shift,
    auto_pool_count: ap,
    count: n,
    room_bounds: bounds,
    dollhouse_cut_y: m.dollhouse_cut_y ?? a.dollhouse_cut_y,
    parts: [
      ...m.parts.map((p) => ({ ...p, origin: "manual" as const })),
      ...a.parts.map((p) => ({ ...p, origin: "auto" as const, seq: p.seq + shift, start: p.start + offset, end: p.end + offset })),
    ],
  };
  return { meta, buf };
}

/** API folder of a build's viewer files (scene.json, scene.bin, scene.splat); "both" has none of its own (see mergeBuilds). */
export function buildBase(build: Build): string {
  return build === "auto" ? "/api/viewer-auto" : "/api/viewer";
}

export async function loadScene(build: Build = "manual"): Promise<{ meta: SceneMeta; geometry: THREE.BufferGeometry }> {
  const raw =
    build === "both"
      ? mergeBuilds(...(await Promise.all([fetchExport("manual"), fetchExport("auto")])))
      : await fetchExport(build);
  return { meta: raw.meta, geometry: parseScene(raw.buf, raw.meta) };
}

/** Axis-aligned box overlap (intersection over union), 0..1. */
export function iou(a: BBox, b: BBox): number {
  let inter = 1;
  for (let k = 0; k < 3; k++) inter *= Math.max(0, Math.min(a.max[k], b.max[k]) - Math.max(a.min[k], b.min[k]));
  const vol = (x: BBox) => (x.max[0] - x.min[0]) * (x.max[1] - x.min[1]) * (x.max[2] - x.min[2]);
  const union = vol(a) + vol(b) - inter;
  return union > 0 ? inter / union : 0;
}

/** Build "both": the part from the other build whose box overlaps `sel` most (IoU >= minIou), among parts 1..upto. */
export function counterpart(meta: SceneMeta, sel: PartMeta, upto: number, minIou = 0.1): { part: PartMeta; iou: number } | null {
  if (meta.build !== "both" || !sel.origin) return null;
  let best: { part: PartMeta; iou: number } | null = null;
  for (const p of meta.parts.slice(0, upto)) {
    if (p.origin === sel.origin) continue;
    const v = iou(sel.bbox, p.bbox);
    if (v >= minIou && (!best || v > best.iou)) best = { part: p, iou: v };
  }
  return best;
}

/**
 * Metric scale guess for WebXR, where one physical metre walked must be one metre in the room. The scan is in scene units
 * and its metric scale is unverified (research/00, AGENTS.md §3). In the Equipment Room the pallet jack is 1.05 u tall at
 * the handle and 0.47 u wide (a real one: about 1.2 m and 0.55 m), and floor-to-ceiling is 2.6 u (about 3 m), so
 * 1 u is about 1.15 m [HYPOTHESIS]. Override with ?mpu=<metres per unit>.
 */
export const METRES_PER_UNIT_GUESS = 1.15;

/** The point cloud in three passes plus the part wire boxes, driven by a ViewState. */
export class BuildCloud {
  readonly group = new THREE.Group();
  private passes: { points: THREE.Points; mat: THREE.ShaderMaterial; geo: THREE.BufferGeometry }[] = [];
  private boxes: THREE.Box3Helper[] = [];
  private stride = 1;
  /** part seqs whose wire boxes are drawn amber (e.g. the automatic pieces of the selected manual part) */
  private highlight = new Set<number>();
  private strideIndex: THREE.BufferAttribute | null = null;
  sizeScale = 1;
  /** false while the splat layer draws the scan instead (the part boxes stay) */
  pointsVisible = true;
  readonly meta: SceneMeta;
  readonly geometry: THREE.BufferGeometry;

  constructor(meta: SceneMeta, geometry: THREE.BufferGeometry) {
    this.meta = meta;
    this.geometry = geometry;
    for (let role = 0; role < 3; role++) {
      const mat = new THREE.ShaderMaterial({
        vertexShader,
        fragmentShader,
        uniforms: {
          uRole: { value: role },
          uUpto: { value: meta.parts.length },
          uSelected: { value: -1 },
          uCutY: { value: meta.dollhouse_cut_y ?? meta.room_bounds.max[1] },
          uCutOn: { value: 0 },
          uHalfH: { value: 400 },
          uSizeScale: { value: 1 },
          uTint: { value: new THREE.Color() },
          uTintAuto: { value: new THREE.Color() },
          uSplit: { value: manualCount(meta) },
          uHideManual: { value: 0 },
          uHideAuto: { value: 0 },
          uTintMix: { value: 0 },
          uAlpha: { value: 1 },
        },
      });
      // One geometry per pass over the same (shared, uploaded once) attributes, so each pass can draw only the range
      // its role can occur in: the parts block is in acceptance order, so "built" and "selected" are contiguous ranges.
      const geo = new THREE.BufferGeometry();
      for (const [name, attr] of Object.entries(geometry.attributes)) geo.setAttribute(name, attr);
      geo.boundingBox = geometry.boundingBox;
      geo.boundingSphere = geometry.boundingSphere;
      const points = new THREE.Points(geo, mat);
      points.frustumCulled = false;
      points.renderOrder = role;
      this.passes.push({ points, mat, geo });
      this.group.add(points);
    }
    for (const p of meta.parts) {
      const box = new THREE.Box3(new THREE.Vector3(...p.bbox.min), new THREE.Vector3(...p.bbox.max));
      const helper = new THREE.Box3Helper(box, WIRE);
      helper.renderOrder = 5;
      this.boxes.push(helper);
      this.group.add(helper);
    }
  }

  part(seq: number): PartMeta | undefined {
    return this.meta.parts[seq - 1];
  }

  partByName(name: string): PartMeta | undefined {
    return this.meta.parts.find((p) => p.name === name);
  }

  setHighlight(seqs: Iterable<number>): void {
    this.highlight = new Set(seqs);
  }

  /** whether a part is drawn as a built part under `show` (build "both") */
  visibleIn(seq: number, show: Show): boolean {
    if (show === "both") return true;
    const auto = seq > manualCount(this.meta);
    return show === "auto" ? auto : !auto;
  }

  /** drawing-buffer height in pixels; call on every resize */
  setViewportHeight(px: number): void {
    for (const { mat } of this.passes) mat.uniforms.uHalfH.value = px / 2;
  }

  /**
   * Draw every k-th point only (k = 1: all). Used in VR, where the headset renders the cloud twice per frame at 72 Hz.
   * Point order is pool then parts, so a uniform stride thins every part evenly.
   */
  setStride(k: number): void {
    k = Math.max(1, Math.floor(k));
    if (k === this.stride) return;
    this.stride = k;
    this.strideIndex = null;
    if (k > 1) {
      const n = Math.ceil(this.meta.count / k);
      const idx = new Uint32Array(n);
      for (let i = 0; i < n; i++) idx[i] = i * k;
      this.strideIndex = new THREE.BufferAttribute(idx, 1);
    }
    for (const { geo } of this.passes) geo.setIndex(this.strideIndex);
  }

  /** [start, end) point range a role can occur in, for the current upto/selection */
  private rangeFor(role: number, upto: number, selected: number): [number, number] {
    const parts = this.meta.parts;
    if (role === 0) return [0, upto >= parts.length ? this.meta.pool_count : this.meta.count];
    if (role === 1) return upto > 0 ? [parts[0].start, parts[upto - 1].end] : [0, 0];
    const sel = parts[selected - 1];
    return sel ? [sel.start, sel.end] : [0, 0];
  }

  apply(s: ViewState): void {
    const looks = looksFor(s);
    const upto = Math.max(0, Math.min(s.upto, this.meta.parts.length));
    const selected = s.selected > 0 && s.selected <= upto ? s.selected : -1;
    const k = this.stride;
    this.passes.forEach(({ points, mat, geo }, role) => {
      const look = looks[role];
      const u = mat.uniforms;
      u.uUpto.value = upto;
      u.uSelected.value = selected;
      u.uHideManual.value = s.show === "auto" ? 1 : 0;
      u.uHideAuto.value = s.show === "manual" ? 1 : 0;
      u.uCutOn.value = s.cut ? 1 : 0;
      u.uSizeScale.value = this.sizeScale * (k > 1 ? Math.sqrt(k) * 0.85 : 1); // fill most of the gaps a stride leaves
      u.uAlpha.value = look.alpha;
      u.uTintMix.value = look.tint ? 1 : 0;
      if (look.tint) (u.uTint.value as THREE.Color).copy(look.tint);
      if (look.tint) (u.uTintAuto.value as THREE.Color).copy(look.autoTint ?? look.tint);
      const opaque = look.alpha >= 0.99;
      mat.transparent = !opaque;
      mat.depthWrite = opaque;
      mat.needsUpdate = true;
      const [a, b] = this.rangeFor(role, upto, selected);
      const start = Math.ceil(a / k);
      geo.setDrawRange(start, Math.max(0, Math.ceil(b / k) - start));
      points.visible = this.pointsVisible && look.alpha > 0 && b > a;
      // opaque passes first, then the faint ones, selection last so it reads on top of the haze
      points.renderOrder = (opaque ? 0 : 10) + role;
    });
    const showAll = s.source === "wireframe" || s.boxes;
    this.boxes.forEach((box, i) => {
      const seq = i + 1;
      const isSel = seq === selected;
      const lit = this.highlight.has(seq);
      box.visible = seq <= upto && (isSel || lit || (showAll && this.visibleIn(seq, s.show)));
      (box.material as THREE.LineBasicMaterial).color.copy(isSel ? RED : lit ? AUTO_TINT : WIRE);
    });
  }
}

/**
 * The built part a ray points at: nearest bbox entry among parts 1..upto. Structures (floor, walls, ceiling) are skipped
 * so that pointing at empty space never selects the floor; boxes the ray starts inside are skipped too (standing inside
 * a pipe run's bbox in VR). With `cutY`, parts entirely above the dollhouse cut are not pickable.
 */
export function pickPart(
  ray: THREE.Ray,
  meta: SceneMeta,
  upto: number,
  cutY?: number,
  keep?: (p: PartMeta) => boolean,
): { part: PartMeta; point: THREE.Vector3; distance: number } | null {
  let best: { part: PartMeta; point: THREE.Vector3; distance: number } | null = null;
  const box = new THREE.Box3();
  const hit = new THREE.Vector3();
  for (const p of meta.parts.slice(0, upto)) {
    if (p.kind === "structure" || (keep && !keep(p))) continue;
    if (cutY !== undefined && p.bbox.min[1] > cutY) continue;
    box.min.set(...p.bbox.min);
    box.max.set(...p.bbox.max);
    if (box.containsPoint(ray.origin) || !ray.intersectBox(box, hit)) continue;
    const distance = hit.distanceTo(ray.origin);
    if (!best || distance < best.distance) best = { part: p, point: hit.clone(), distance };
  }
  return best;
}

export function roomBox(meta: SceneMeta): THREE.Box3 {
  return new THREE.Box3(new THREE.Vector3(...meta.room_bounds.min), new THREE.Vector3(...meta.room_bounds.max));
}

export function partBox(p: PartMeta): THREE.Box3 {
  return new THREE.Box3(new THREE.Vector3(...p.bbox.min), new THREE.Vector3(...p.bbox.max));
}

/** Camera position/target that frames a box from a direction (outside, looking in), for a vertical fov in degrees. */
export function frameBox(box: THREE.Box3, dir: THREE.Vector3, fovDeg: number, aspect: number, fill = 0.7) {
  const center = box.getCenter(new THREE.Vector3());
  const radius = Math.max(box.getSize(new THREE.Vector3()).length() / 2, 0.05);
  const fov = THREE.MathUtils.degToRad(fovDeg);
  const fit = Math.min(fov, 2 * Math.atan(Math.tan(fov / 2) * aspect));
  // radius / sin(fit/2) puts the bounding sphere edge-to-edge; a box shows at roughly 40 % of that, so scale by 0.4/fill
  const dist = ((radius / Math.sin(fit / 2)) * 0.4) / fill;
  return { position: center.clone().addScaledVector(dir.clone().normalize(), dist), target: center };
}

/** URL <-> ViewState (shared by the viewer and capture.html, so a viewer link reproduces as a snapshot). */
export function readState(params: URLSearchParams, meta: SceneMeta, fallback: Partial<ViewState> = {}): ViewState {
  const src = params.get("src") as Source | null;
  const partParam = params.get("part");
  let selected = 0;
  if (partParam) {
    const byName = meta.parts.find((p) => p.name === partParam);
    selected = byName ? byName.seq : Number(partParam) || 0;
  }
  const uptoParam = params.get("upto");
  let upto = meta.parts.length;
  if (uptoParam) {
    const byName = meta.parts.find((p) => p.name === uptoParam);
    upto = byName ? byName.seq : Math.max(0, Number(uptoParam));
  }
  return {
    source: src && SOURCES.includes(src) ? src : (fallback.source ?? "overlay"),
    style: STYLES.includes(params.get("style") as Style) ? (params.get("style") as Style) : (fallback.style ?? defaultStyle(meta)),
    selected,
    upto,
    cut: params.has("dollhouse") ? params.get("dollhouse") !== "0" : (fallback.cut ?? false),
    boxes: params.has("boxes") ? params.get("boxes") !== "0" : (fallback.boxes ?? false),
    show: meta.build === "both" && (params.get("show") === "manual" || params.get("show") === "auto") ? (params.get("show") as Show) : "both",
  };
}

/** The style a build opens with when the URL names none: both builds at once are told apart by colour. */
export function defaultStyle(meta: SceneMeta): Style {
  return meta.build === "both" ? "origin" : "true";
}

export function writeState(params: URLSearchParams, s: ViewState, meta: SceneMeta): void {
  params.set("src", s.source);
  if (s.style !== defaultStyle(meta)) params.set("style", s.style);
  else params.delete("style");
  const sel = meta.parts[s.selected - 1];
  if (sel) params.set("part", sel.name);
  else params.delete("part");
  if (s.upto < meta.parts.length) params.set("upto", String(s.upto));
  else params.delete("upto");
  if (s.boxes) params.set("boxes", "1");
  else params.delete("boxes");
  if (s.show !== "both") params.set("show", s.show);
  else params.delete("show");
}

/** scripts/compare_builds.py: manual vs automatic build (GET /api/compare.json). */
export type MatchStatus = "matched" | "split" | "partial" | "missed";
export interface CompareManual {
  name: string;
  label: string;
  kind: string;
  status: MatchStatus;
  best: { name: string; label: string; iou: number } | null;
  /** automatic objects lying at least half inside this part, largest first */
  fragments: string[];
  fragment_labels: Record<string, number>;
  /** share of the part's box covered by its fragments */
  coverage: number;
  nearest: { name: string; label: string; gap: number; dy: number } | null;
}
export interface CompareAuto {
  name: string;
  label: string;
  source: string;
  /** the manual part it lies inside, or null: only the automatic build has it */
  in: string | null;
}
export interface Compare {
  summary: {
    status: Record<MatchStatus, number>;
    found: number;
    found_share: number;
    mean_best_iou: number;
    auto_inside_manual: number;
    auto_only: number;
    auto_only_by_label: Record<string, number>;
  };
  manual: CompareManual[];
  auto: CompareAuto[];
}

/** The comparison, or null when it has not been generated (the viewer then falls back to box IoU on the fly). */
export async function loadCompare(): Promise<Compare | null> {
  try {
    const res = await fetch("/api/compare.json");
    return res.ok ? ((await res.json()) as Compare) : null;
  } catch {
    return null;
  }
}
