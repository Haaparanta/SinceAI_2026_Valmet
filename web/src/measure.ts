/**
 * Measure tool: click two points on the scan, read the distance (scene units and an approximate metre value).
 *
 * Picking runs on the CPU over the points that are actually drawn: the same role / replay / dollhouse-cut rules as the
 * point shader, and only roles whose current opacity is above zero. The nearest point within a few pixels of the ray wins.
 * One pass over 1.6 M points takes a few tens of milliseconds, fine for a click.
 */
import * as THREE from "three";
import { CSS2DObject } from "three/addons/renderers/CSS2DRenderer.js";
import { looksFor, type BuildCloud, type ViewState } from "./scene";

/**
 * The drawn point nearest to the viewer within `pxTol` pixels of the ray. `radPerPx` is the camera's vertical field of
 * view divided by the viewport height in pixels.
 */
export function pickPoint(
  cloud: BuildCloud,
  state: ViewState,
  ray: THREE.Ray,
  radPerPx: number,
  pxTol = 5,
): THREE.Vector3 | null {
  const pos = cloud.geometry.getAttribute("position").array as Float32Array;
  const part = cloud.geometry.getAttribute("part").array as Uint16Array;
  const looks = looksFor(state);
  const upto = Math.max(0, Math.min(state.upto, cloud.meta.parts.length));
  const sel = state.selected > 0 && state.selected <= upto ? state.selected : -1;
  const cutY = state.cut ? (cloud.meta.dollhouse_cut_y ?? Infinity) : Infinity;
  const { x: ox, y: oy, z: oz } = ray.origin;
  const { x: dx, y: dy, z: dz } = ray.direction;
  const tol = Math.tan(radPerPx * pxTol);
  const tol2 = tol * tol;
  let bestT = Infinity;
  let best = -1;
  const n = cloud.meta.count;
  for (let i = 0; i < n; i++) {
    const p = part[i];
    const role = p === 0 || p > upto ? 0 : p === sel ? 2 : 1;
    if (looks[role].alpha <= 0) continue;
    const y = pos[i * 3 + 1];
    if (role < 2 && y > cutY) continue;
    const vx = pos[i * 3] - ox;
    const vy = y - oy;
    const vz = pos[i * 3 + 2] - oz;
    const t = vx * dx + vy * dy + vz * dz;
    if (t <= 0 || t >= bestT) continue;
    const perp2 = vx * vx + vy * vy + vz * vz - t * t;
    if (perp2 <= tol2 * t * t) {
      bestT = t;
      best = i;
    }
  }
  return best < 0 ? null : new THREE.Vector3(pos[best * 3], pos[best * 3 + 1], pos[best * 3 + 2]);
}

/** The measured segment: two end dots, a line on top of everything, and a label at the middle. */
export class MeasureView {
  readonly group = new THREE.Group();
  readonly points: THREE.Vector3[] = [];
  private readonly mat = new THREE.LineBasicMaterial({ color: 0x00e5ff, depthTest: false, transparent: true });
  private readonly dotMat = new THREE.MeshBasicMaterial({ color: 0x00e5ff, depthTest: false });
  private readonly dotGeo = new THREE.SphereGeometry(0.02, 12, 8);
  private readonly mpu: number;

  constructor(metresPerUnit: number) {
    this.mpu = metresPerUnit;
  }

  /** Add a point; a third click starts a new measurement. Returns the distance once two points are set. */
  add(p: THREE.Vector3): number | null {
    if (this.points.length >= 2) this.clear();
    this.points.push(p.clone());
    this.redraw();
    return this.points.length === 2 ? this.points[0].distanceTo(this.points[1]) : null;
  }

  clear(): void {
    this.points.length = 0;
    this.redraw();
  }

  private redraw(): void {
    for (const ch of [...this.group.children]) {
      this.group.remove(ch);
      if (ch instanceof THREE.Line) ch.geometry.dispose();
      if (ch instanceof CSS2DObject) ch.element.remove();
    }
    for (const p of this.points) {
      const dot = new THREE.Mesh(this.dotGeo, this.dotMat);
      dot.position.copy(p);
      dot.renderOrder = 51;
      this.group.add(dot);
    }
    if (this.points.length < 2) return;
    const [a, b] = this.points;
    const line = new THREE.Line(new THREE.BufferGeometry().setFromPoints([a, b]), this.mat);
    line.renderOrder = 50;
    this.group.add(line);
    const d = a.distanceTo(b);
    const el = document.createElement("div");
    el.className = "tag tag-measure";
    el.innerHTML = `<b></b><span></span>`;
    el.querySelector("b")!.textContent = `${d.toFixed(3)} u ≈ ${(d * this.mpu).toFixed(2)} m`;
    el.querySelector("span")!.textContent =
      `Δx ${Math.abs(b.x - a.x).toFixed(2)} · Δy ${Math.abs(b.y - a.y).toFixed(2)} · Δz ${Math.abs(b.z - a.z).toFixed(2)} u`;
    const tag = new CSS2DObject(el);
    tag.position.copy(a).add(b).multiplyScalar(0.5);
    this.group.add(tag);
  }
}
