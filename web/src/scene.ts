/**
 * The step-by-step build as one point cloud, shared by the viewer (main.ts) and the snapshot page (capture.ts).
 *
 * Data: data/derived/viewer/scene.{bin,json}, written by scripts/export_viewer_scene.py. The pool (scan points not yet
 * claimed by a part) comes first, then every accepted part as one contiguous range in acceptance order.
 *
 * Detail levels: scene.json "lods" (scripts/lod.py) splits the same rows into additive levels, coarse to fine. The viewer
 * streams them in order and adds each as a chunk; the snapshot page loads the full scene.bin as a single chunk. Inside
 * every chunk the rows are grouped by segment (0 = pool, k = part k), so each role is still one contiguous range.
 *
 * Rendering: each chunk is drawn in up to three passes, one per role: pool, built (accepted parts up to `upto`),
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
/** One detail level (scripts/lod.py): `count` rows, `ranges[s]` = rows of segment s (0 = pool, k = part k). */
export interface LodMeta {
  level: number;
  /** voxel edge it was thinned with (scene units); null for the last level, which holds the rest */
  voxel: number | null;
  count: number;
  bin: string;
  splat: string;
  ranges: [number, number][];
  /** build "both": the two exports' own level k, merged row by row when loaded */
  sources?: { manual: LodMeta; auto: LodMeta };
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
  /** additive detail levels, coarse to fine (absent in exports older than scripts/lod.py) */
  lods?: LodMeta[];
}

/** A block of rows the cloud draws: the full scene.bin, or one detail level. */
export interface Chunk {
  geometry: THREE.BufferGeometry;
  count: number;
  /** [start, end) per segment: 0 = pool, k = part k */
  ranges: [number, number][];
  /** detail level (0 = coarsest); the full scene.bin counts as the finest */
  level: number;
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
}

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
uniform float uTintMix;
varying vec3 vColor;
void main() {
  float role = (part < 0.5 || part > uUpto + 0.5) ? 0.0 : (abs(part - uSelected) < 0.5 ? 2.0 : 1.0);
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
  vColor = mix(rgb, part > uSplit + 0.5 ? uTintAuto : uTint, uTintMix);
}`;

const fragmentShader = /* glsl */ `
uniform float uAlpha;
varying vec3 vColor;
void main() {
  vec2 c = gl_PointCoord * 2.0 - 1.0;
  if (dot(c, c) > 1.0) discard;
  gl_FragColor = vec4(vColor, uAlpha);
}`;

/** Geometry from the scene.bin layout (scene.bin itself or one lod/<k>.bin) of `n` rows. */
export function parseScene(buf: ArrayBuffer, meta: SceneMeta, n = meta.count, what = "scene.bin"): THREE.BufferGeometry {
  const expected = n * (12 + 2 + 3 + 1);
  if (buf.byteLength !== expected) {
    throw new Error(`${what} is ${buf.byteLength} bytes, scene.json says ${n} points (${expected} bytes): re-export`);
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

/** The full scene.bin as one chunk: pool, then the parts' own ranges. */
export function fullChunk(meta: SceneMeta, geometry: THREE.BufferGeometry): Chunk {
  return {
    geometry,
    count: meta.count,
    ranges: [[0, meta.pool_count], ...meta.parts.map((p) => [p.start, p.end] as [number, number])],
    level: meta.lods?.length ? meta.lods.length - 1 : 0,
  };
}

/** GET a binary file, reporting progress 0..1 when the server sends a Content-Length. */
export async function fetchBytes(url: string, hint: string, onProgress?: (f: number) => void): Promise<ArrayBuffer> {
  const res = await fetch(url);
  if (!res.ok) throw new Error(`GET ${url} -> ${res.status}: ${hint}`);
  const total = Number(res.headers.get("Content-Length")) || 0;
  if (!res.body || !total || !onProgress) return res.arrayBuffer();
  const buf = new Uint8Array(total);
  let got = 0;
  const reader = res.body.getReader();
  for (;;) {
    const { done, value } = await reader.read();
    if (done) break;
    if (got + value.length > total) throw new Error(`${url} is larger than its Content-Length`);
    buf.set(value, got);
    got += value.length;
    onProgress(got / total);
  }
  return got === total ? buf.buffer : buf.slice(0, got).buffer;
}

/**
 * Fetch `n` items in order and apply them in order, with the next download already running while the current item is
 * applied (decoded, uploaded): the network and the decoder overlap, and items still appear strictly coarse to fine.
 */
export async function streamInOrder<T>(
  n: number,
  fetchItem: (k: number) => Promise<T>,
  applyItem: (k: number, item: T) => Promise<void> | void,
): Promise<void> {
  let next = n > 0 ? fetchItem(0) : null;
  for (let k = 0; k < n; k++) {
    const item = await next!;
    next = k + 1 < n ? fetchItem(k + 1) : null;
    await applyItem(k, item);
  }
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

/** API folder of a build's viewer files (scene.json, scene.bin, scene.splat, lod/); "both" has none of its own. */
export function buildBase(build: Build): string {
  return build === "auto" ? "/api/viewer-auto" : "/api/viewer";
}

export function exportHint(build: Build): string {
  return build === "both"
    ? "run `make viewer` and `make viewer-auto` first"
    : build === "auto"
      ? "run `make viewer-auto` (scripts/export_autoscene_viewer.py) first"
      : "run `make viewer` (scripts/export_viewer_scene.py) first";
}

const BYTES_PER_POINT = 12 + 2 + 3 + 1;

interface RawScene {
  meta: SceneMeta;
  buf: ArrayBuffer;
}

/** One export's scene.json, every part tagged with its origin. */
async function fetchMeta(origin: Origin): Promise<SceneMeta> {
  const url = `${buildBase(origin)}/scene.json`;
  const res = await fetch(url);
  if (!res.ok) throw new Error(`GET ${url} -> ${res.status}: ${exportHint(origin)}`);
  const meta = (await res.json()) as SceneMeta;
  meta.parts = meta.parts.map((p) => ({ ...p, origin }));
  return meta;
}

/**
 * Rows of both builds as one block in the scene.bin layout: all `nm` manual rows, then the automatic rows after its
 * first `ap` (its pool: the same scan, already in the manual pool and parts), part ids shifted by `shift`. Used for the
 * whole scene (mergeBuilds) and for one detail level at a time (loadLevel).
 */
export function mergeRows(mBuf: ArrayBuffer, nm: number, aBuf: ArrayBuffer, na: number, ap: number, shift: number): ArrayBuffer {
  for (const [buf, count] of [[mBuf, nm], [aBuf, na]] as const) {
    const want = count * BYTES_PER_POINT;
    if (buf.byteLength !== want) {
      throw new Error(`scene.bin is ${buf.byteLength} bytes, scene.json says ${count} points (${want} bytes): re-export`);
    }
  }
  const add = na - ap;
  const n = nm + add;
  const buf = new ArrayBuffer(n * BYTES_PER_POINT);
  const xyz = new Float32Array(buf, 0, n * 3);
  xyz.set(new Float32Array(mBuf, 0, nm * 3));
  xyz.set(new Float32Array(aBuf, ap * 12, add * 3), nm * 3);
  const part = new Uint16Array(buf, n * 12, n);
  part.set(new Uint16Array(mBuf, nm * 12, nm));
  const autoPart = new Uint16Array(aBuf, na * 12 + ap * 2, add);
  for (let i = 0; i < add; i++) part[nm + i] = autoPart[i] + shift;
  const rgb = new Uint8Array(buf, n * 14, n * 3);
  rgb.set(new Uint8Array(mBuf, nm * 14, nm * 3));
  rgb.set(new Uint8Array(aBuf, na * 14 + ap * 3, add * 3), nm * 3);
  const size = new Uint8Array(buf, n * 17, n);
  size.set(new Uint8Array(mBuf, nm * 17, nm));
  size.set(new Uint8Array(aBuf, na * 17 + ap, add), nm);
  return buf;
}

/**
 * Both builds' scene.json as one: the manual parts, then the automatic ones (seq shifted by the manual part count, rows
 * after the manual rows). With detail levels in both exports, level k is level k of each, merged the same way.
 */
export function mergeMeta(m: SceneMeta, a: SceneMeta): SceneMeta {
  const shift = m.parts.length;
  if (shift + a.parts.length > 65535) throw new Error("too many parts for uint16 part ids");
  const ap = a.pool_count;
  const offset = m.count - ap;
  const bounds: BBox = {
    min: [0, 1, 2].map((k) => Math.min(m.room_bounds.min[k], a.room_bounds.min[k])) as V3,
    max: [0, 1, 2].map((k) => Math.max(m.room_bounds.max[k], a.room_bounds.max[k])) as V3,
  };
  let lods: LodMeta[] | undefined;
  if (m.lods?.length && m.lods.length === a.lods?.length) {
    lods = m.lods.map((ml, k) => {
      const al = a.lods![k];
      const pool = al.ranges[0][1];
      const off = ml.count - pool;
      return {
        ...ml,
        count: ml.count + al.count - pool,
        ranges: [...ml.ranges, ...al.ranges.slice(1).map(([x, y]) => [x + off, y + off] as [number, number])],
        sources: { manual: ml, auto: al },
      };
    });
  }
  return {
    ...m,
    build: "both",
    manual_parts: shift,
    auto_pool_count: ap,
    count: m.count + a.count - ap,
    room_bounds: bounds,
    dollhouse_cut_y: m.dollhouse_cut_y ?? a.dollhouse_cut_y,
    lods,
    parts: [
      ...m.parts.map((p) => ({ ...p, origin: "manual" as const })),
      ...a.parts.map((p) => ({ ...p, origin: "auto" as const, seq: p.seq + shift, start: p.start + offset, end: p.end + offset })),
    ],
  };
}

/**
 * Both builds as one scene: the manual export unchanged (pool + parts), then the automatic export's parts block. Points
 * of a part the two builds share are drawn twice, once per build.
 */
export function mergeBuilds(manual: RawScene, auto: RawScene): RawScene {
  const meta = mergeMeta(manual.meta, auto.meta);
  const buf = mergeRows(manual.buf, manual.meta.count, auto.buf, auto.meta.count, auto.meta.pool_count, manual.meta.parts.length);
  return { meta, buf };
}

/** scene.json only (both merged for "both"): enough to build the UI before any point arrives. */
export async function loadMeta(build: Build = "manual"): Promise<SceneMeta> {
  if (build === "both") return mergeMeta(...(await Promise.all([fetchMeta("manual"), fetchMeta("auto")])));
  return fetchMeta(build);
}

/** One detail level as a chunk; for "both" the two builds' level files, merged row by row. */
export async function loadLevel(build: Build, meta: SceneMeta, lod: LodMeta, onProgress?: (f: number) => void): Promise<Chunk> {
  let buf: ArrayBuffer;
  if (lod.sources) {
    const { manual: ml, auto: al } = lod.sources;
    const done = [0, 0];
    const total = ml.count + al.count;
    const report = (i: number, n: number) => (f: number) => {
      done[i] = f * n;
      onProgress?.((done[0] + done[1]) / total);
    };
    const [mb, ab] = await Promise.all([
      fetchBytes(`${buildBase("manual")}/${ml.bin}`, exportHint("both"), report(0, ml.count)),
      fetchBytes(`${buildBase("auto")}/${al.bin}`, exportHint("both"), report(1, al.count)),
    ]);
    buf = mergeRows(mb, ml.count, ab, al.count, al.ranges[0][1], manualCount(meta));
  } else {
    buf = await fetchBytes(`${buildBase(build)}/${lod.bin}`, exportHint(build), onProgress);
  }
  return { geometry: parseScene(buf, meta, lod.count, lod.bin), count: lod.count, ranges: lod.ranges, level: lod.level };
}

/** scene.json + the full scene.bin in one go (the snapshot page, which must draw every point). */
export async function loadScene(build: Build = "manual"): Promise<{ meta: SceneMeta; geometry: THREE.BufferGeometry }> {
  const full = async (origin: Origin): Promise<RawScene> => {
    const [meta, buf] = await Promise.all([fetchMeta(origin), fetchBytes(`${buildBase(origin)}/scene.bin`, exportHint(origin))]);
    return { meta, buf };
  };
  const raw = build === "both" ? mergeBuilds(...(await Promise.all([full("manual"), full("auto")]))) : await full(build);
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

interface Pass {
  points: THREE.Points;
  mat: THREE.ShaderMaterial;
  geo: THREE.BufferGeometry;
}

/** The point cloud as chunks (full scene or detail levels), each in three role passes, plus the part wire boxes. */
export class BuildCloud {
  readonly group = new THREE.Group();
  private draws: { chunk: Chunk; passes: Pass[] }[] = [];
  private boxes: THREE.Box3Helper[] = [];
  private halfH = 400;
  private last: ViewState | null = null;
  sizeScale = 1;
  /** false while the splat layer draws the scan instead (the part boxes stay) */
  pointsVisible = true;
  /** draw detail levels 0..maxLevel only (VR leaves out the finest levels when frames run long) */
  maxLevel = Infinity;
  readonly meta: SceneMeta;

  constructor(meta: SceneMeta, first?: Chunk) {
    this.meta = meta;
    for (const p of meta.parts) {
      const box = new THREE.Box3(new THREE.Vector3(...p.bbox.min), new THREE.Vector3(...p.bbox.max));
      const helper = new THREE.Box3Helper(box, WIRE);
      helper.renderOrder = 5;
      this.boxes.push(helper);
      this.group.add(helper);
    }
    if (first) this.addChunk(first);
  }

  /** Chunks in level order (coarse first). */
  get chunks(): Chunk[] {
    return this.draws.map((d) => d.chunk);
  }

  /** The chunks currently drawn (loaded and within maxLevel). */
  visibleChunks(): Chunk[] {
    return this.chunks.filter((c) => c.level <= this.maxLevel);
  }

  /** The Points of one role (0 pool, 1 built, 2 selected) in every chunk (tests hide the selected passes to measure them). */
  rolePasses(role: number): THREE.Points[] {
    return this.draws.map((d) => d.passes[role].points);
  }

  /** Add a chunk (a detail level that just arrived); it takes the current view state at once. */
  addChunk(chunk: Chunk): void {
    const passes: Pass[] = [];
    for (let role = 0; role < 3; role++) {
      const mat = new THREE.ShaderMaterial({
        vertexShader,
        fragmentShader,
        uniforms: {
          uRole: { value: role },
          uUpto: { value: this.meta.parts.length },
          uSelected: { value: -1 },
          uCutY: { value: this.meta.dollhouse_cut_y ?? this.meta.room_bounds.max[1] },
          uCutOn: { value: 0 },
          uHalfH: { value: this.halfH },
          uSizeScale: { value: 1 },
          uTint: { value: new THREE.Color() },
          uTintAuto: { value: new THREE.Color() },
          uSplit: { value: manualCount(this.meta) },
          uTintMix: { value: 0 },
          uAlpha: { value: 1 },
        },
      });
      // One geometry per pass over the chunk's (shared, uploaded once) attributes, so each pass draws only the range its
      // role can occur in: inside a chunk the parts are in build order, so "built" and "selected" are contiguous ranges.
      const geo = new THREE.BufferGeometry();
      for (const [name, attr] of Object.entries(chunk.geometry.attributes)) geo.setAttribute(name, attr);
      geo.boundingBox = chunk.geometry.boundingBox;
      geo.boundingSphere = chunk.geometry.boundingSphere;
      const points = new THREE.Points(geo, mat);
      points.frustumCulled = false;
      passes.push({ points, mat, geo });
      this.group.add(points);
    }
    this.draws.push({ chunk, passes });
    this.draws.sort((x, y) => x.chunk.level - y.chunk.level);
    if (this.last) this.apply(this.last);
  }

  part(seq: number): PartMeta | undefined {
    return this.meta.parts[seq - 1];
  }

  partByName(name: string): PartMeta | undefined {
    return this.meta.parts.find((p) => p.name === name);
  }

  /** drawing-buffer height in pixels; call on every resize */
  setViewportHeight(px: number): void {
    this.halfH = px / 2;
    for (const d of this.draws) for (const { mat } of d.passes) mat.uniforms.uHalfH.value = this.halfH;
  }

  setMaxLevel(level: number): void {
    this.maxLevel = level;
    if (this.last) this.apply(this.last);
  }

  /**
   * Bigger points while finer levels are missing (still streaming, or left out in VR): every level halves the voxel
   * size, so each missing level makes the spacing on a surface about twice as wide; grow the points by √2 per level.
   */
  private levelBoost(): number {
    const levels = this.meta.lods?.length ?? 1;
    const shown = this.visibleChunks();
    if (!shown.length || levels <= 1) return 1;
    const finest = Math.max(...shown.map((c) => c.level));
    return Math.SQRT2 ** Math.max(0, levels - 1 - finest);
  }

  /** [start, end) rows of a chunk a role can occur in, for the current upto/selection */
  private rangeFor(chunk: Chunk, role: number, upto: number, selected: number): [number, number] {
    const r = chunk.ranges;
    const n = this.meta.parts.length;
    if (role === 0) return [0, upto >= n ? r[0][1] : chunk.count];
    if (role === 1) return upto > 0 ? [r[1][0], r[upto][1]] : [0, 0];
    return selected > 0 ? r[selected] : [0, 0];
  }

  apply(s: ViewState): void {
    this.last = s;
    const looks = looksFor(s);
    const upto = Math.max(0, Math.min(s.upto, this.meta.parts.length));
    const selected = s.selected > 0 && s.selected <= upto ? s.selected : -1;
    const boost = this.levelBoost();
    for (const { chunk, passes } of this.draws) {
      const shown = this.pointsVisible && chunk.level <= this.maxLevel;
      passes.forEach(({ points, mat, geo }, role) => {
        const look = looks[role];
        const u = mat.uniforms;
        u.uUpto.value = upto;
        u.uSelected.value = selected;
        u.uCutOn.value = s.cut ? 1 : 0;
        u.uSizeScale.value = this.sizeScale * boost;
        u.uAlpha.value = look.alpha;
        u.uTintMix.value = look.tint ? 1 : 0;
        if (look.tint) (u.uTint.value as THREE.Color).copy(look.tint);
        if (look.tint) (u.uTintAuto.value as THREE.Color).copy(look.autoTint ?? look.tint);
        const opaque = look.alpha >= 0.99;
        mat.transparent = !opaque;
        mat.depthWrite = opaque;
        mat.needsUpdate = true;
        const [a, b] = this.rangeFor(chunk, role, upto, selected);
        geo.setDrawRange(a, Math.max(0, b - a));
        points.visible = shown && look.alpha > 0 && b > a;
        // opaque passes first, then the faint ones, selection last so it reads on top of the haze
        points.renderOrder = (opaque ? 0 : 10) + role;
      });
    }
    const showAll = s.source === "wireframe" || s.boxes;
    this.boxes.forEach((box, i) => {
      const seq = i + 1;
      const isSel = seq === selected;
      box.visible = seq <= upto && (showAll || isSel);
      (box.material as THREE.LineBasicMaterial).color.copy(isSel ? RED : WIRE);
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
): { part: PartMeta; point: THREE.Vector3; distance: number } | null {
  let best: { part: PartMeta; point: THREE.Vector3; distance: number } | null = null;
  const box = new THREE.Box3();
  const hit = new THREE.Vector3();
  for (const p of meta.parts.slice(0, upto)) {
    if (p.kind === "structure") continue;
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
}
