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
vec3 srgbToLinear(vec3 c) {
  return mix(c / 12.92, pow((c + 0.055) / 1.055, vec3(2.4)), step(0.04045, c));
}
void main() {
  float role = (part < 0.5 || part > uUpto + 0.5) ? 0.0 : (abs(part - uSelected) < 0.5 ? 2.0 : 1.0);
  if (abs(role - uRole) > 0.5 || (uCutOn > 0.5 && position.y > uCutY)) {
    gl_Position = vec4(2.0, 2.0, 2.0, 1.0);
    gl_PointSize = 0.0;
    return;
  }
  vec4 mv = modelViewMatrix * vec4(position, 1.0);
  gl_Position = projectionMatrix * mv;
  bool ortho = projectionMatrix[3][3] > 0.5;
  float pxPerUnit = projectionMatrix[1][1] * uHalfH / (ortho ? 1.0 : max(-mv.z, 0.001));
  gl_PointSize = clamp(psize * 0.001 * uSizeScale * pxPerUnit, 1.0, 48.0);
  // Work in linear colour (uTint is a linear THREE.Color) and let three convert to the output colour space: the default
  // framebuffer and the WebXR layer both expect that, so the headset shows the same colours as the laptop.
  vColor = mix(srgbToLinear(rgb), uTint, uTintMix);
}`;

const fragmentShader = /* glsl */ `
uniform float uAlpha;
varying vec3 vColor;
void main() {
  vec2 c = gl_PointCoord * 2.0 - 1.0;
  if (dot(c, c) > 1.0) discard;
  gl_FragColor = vec4(vColor, uAlpha);
  #include <colorspace_fragment>
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
 * The point cloud in three role passes plus the part wire boxes, driven by a ViewState.
 * Each pass is drawn only over the ranges where its role can occur: pool = the (shuffled) pool block, capped by
 * `poolBudget`, plus the parts block (parts after `upto` count as pool); built = the parts block up to `upto`;
 * selected = that part's own range.
 */
export class BuildCloud {
  readonly group = new THREE.Group();
  private passes: { objects: THREE.Points[]; mat: THREE.ShaderMaterial; role: number }[] = [];
  private boxes: THREE.Box3Helper[] = [];
  /** world-space boxes of the parts, index = seq - 1 (for controller ray picking) */
  readonly partBoxes: THREE.Box3[] = [];
  sizeScale = 1;
  /** draw at most this many pool points (the pool block is shuffled, so a prefix is a fair sample) */
  poolBudget = Infinity;
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
      // Points objects share the geometry but each keeps its own draw range (THREE.Points uses geometry.drawRange,
      // so every object gets a lightweight geometry clone that shares the attribute buffers).
      const objects = (role === 0 ? [0, 1] : [0]).map(() => {
        const g = new THREE.BufferGeometry();
        for (const [name, attr] of Object.entries(geometry.attributes)) g.setAttribute(name, attr);
        g.boundingBox = geometry.boundingBox;
        g.boundingSphere = geometry.boundingSphere;
        const points = new THREE.Points(g, mat);
        points.frustumCulled = false;
        this.group.add(points);
        return points;
      });
      this.passes.push({ objects, mat, role });
    }
    for (const p of meta.parts) {
      const box = new THREE.Box3(new THREE.Vector3(...p.bbox.min), new THREE.Vector3(...p.bbox.max));
      this.partBoxes.push(box);
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

  /** points drawn per pass for a state (for the HUD and the XR budget) */
  drawnCount(): number {
    let n = 0;
    for (const { objects } of this.passes) for (const o of objects) if (o.visible) n += o.geometry.drawRange.count;
    return n;
  }

  apply(s: ViewState): void {
    const looks = looksFor(s);
    const upto = Math.max(0, Math.min(s.upto, this.meta.parts.length));
    const selected = s.selected > 0 && s.selected <= upto ? s.selected : -1;
    const { pool_count: poolEnd, count } = this.meta;
    const builtEnd = upto > 0 ? this.meta.parts[upto - 1].end : poolEnd;
    const selPart = selected > 0 ? this.meta.parts[selected - 1] : undefined;
    const ranges: [number, number][][] = [
      [
        [0, Math.min(poolEnd, this.poolBudget)],
        [builtEnd, count], // parts after `upto` are still scan
      ],
      [[poolEnd, builtEnd]],
      [selPart ? [selPart.start, selPart.end] : [0, 0]],
    ];
    this.passes.forEach(({ objects, mat, role }) => {
      const look = looks[role];
      objects.forEach((o, i) => {
        const [a, b] = ranges[role][i];
        o.geometry.setDrawRange(a, Math.max(0, b - a));
      });
      const u = mat.uniforms;
      u.uUpto.value = upto;
      u.uSelected.value = selected;
      u.uCutOn.value = s.cut ? 1 : 0;
      u.uSizeScale.value = this.sizeScale;
      u.uAlpha.value = look.alpha;
      u.uTintMix.value = look.tint ? 1 : 0;
      if (look.tint) (u.uTint.value as THREE.Color).copy(look.tint);
      const opaque = look.alpha >= 0.99;
      mat.transparent = !opaque;
      mat.depthWrite = opaque;
      mat.needsUpdate = true;
      for (const o of objects) {
        o.visible = look.alpha > 0 && o.geometry.drawRange.count > 0;
        // opaque passes first, then the faint ones, selection last so it reads on top of the haze
        o.renderOrder = (opaque ? 0 : 10) + role;
      }
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
