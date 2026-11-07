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
  count: number;
  start: number;
  end: number;
  bbox: BBox;
}
export interface SceneMeta {
  version: number;
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
/** true = real colours (the user's image rule since 2026-11-06 22:25); redgrey = AGENTS.md M5 recipe. */
export type Style = "true" | "redgrey";

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

interface RoleLook {
  alpha: number;
  tint?: THREE.Color;
}
type Looks = [pool: RoleLook, built: RoleLook, selected: RoleLook];

/** Opacity per role for a view state. Selection follows the user's image rule: selected 80 %, built 20 %, rest 8 %. */
export function looksFor(s: ViewState): Looks {
  const sel = s.selected > 0;
  if (s.style === "redgrey") {
    // AGENTS.md M5 snapshot recipe: new object red and opaque, other approved objects grey at 25 %, raw points hidden.
    return [{ alpha: 0 }, { alpha: 0.25, tint: GREY }, { alpha: 1, tint: RED }];
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
  vColor = mix(rgb, uTint, uTintMix);
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

export async function loadScene(): Promise<{ meta: SceneMeta; geometry: THREE.BufferGeometry }> {
  const hint = "run `uv run python scripts/export_viewer_scene.py` first";
  const metaRes = await fetch("/api/viewer/scene.json");
  if (!metaRes.ok) throw new Error(`GET /api/viewer/scene.json -> ${metaRes.status}: ${hint}`);
  const meta = (await metaRes.json()) as SceneMeta;
  const binRes = await fetch("/api/viewer/scene.bin");
  if (!binRes.ok) throw new Error(`GET /api/viewer/scene.bin -> ${binRes.status}: ${hint}`);
  return { meta, geometry: parseScene(await binRes.arrayBuffer(), meta) };
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
  private strideIndex: THREE.BufferAttribute | null = null;
  sizeScale = 1;
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
      u.uCutOn.value = s.cut ? 1 : 0;
      u.uSizeScale.value = this.sizeScale * (k > 1 ? Math.sqrt(k) * 0.85 : 1); // fill most of the gaps a stride leaves
      u.uAlpha.value = look.alpha;
      u.uTintMix.value = look.tint ? 1 : 0;
      if (look.tint) (u.uTint.value as THREE.Color).copy(look.tint);
      const opaque = look.alpha >= 0.99;
      mat.transparent = !opaque;
      mat.depthWrite = opaque;
      mat.needsUpdate = true;
      const [a, b] = this.rangeFor(role, upto, selected);
      const start = Math.ceil(a / k);
      geo.setDrawRange(start, Math.max(0, Math.ceil(b / k) - start));
      points.visible = look.alpha > 0 && b > a;
      // opaque passes first, then the faint ones, selection last so it reads on top of the haze
      points.renderOrder = (opaque ? 0 : 10) + role;
    });
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
    style: params.get("style") === "redgrey" ? "redgrey" : "true",
    selected,
    upto,
    cut: params.has("dollhouse") ? params.get("dollhouse") !== "0" : (fallback.cut ?? false),
    boxes: params.has("boxes") ? params.get("boxes") !== "0" : (fallback.boxes ?? false),
  };
}

export function writeState(params: URLSearchParams, s: ViewState, meta: SceneMeta): void {
  params.set("src", s.source);
  if (s.style === "redgrey") params.set("style", "redgrey");
  else params.delete("style");
  const sel = meta.parts[s.selected - 1];
  if (sel) params.set("part", sel.name);
  else params.delete("part");
  if (s.upto < meta.parts.length) params.set("upto", String(s.upto));
  else params.delete("upto");
  if (s.boxes) params.set("boxes", "1");
  else params.delete("boxes");
}
