/**
 * Proximity display: how far the selected part is from its neighbours (axis-aligned bbox gaps, scene units), drawn as
 * dashed leader lines with distance labels. The lines are plain three.js objects, so they also show in VR.
 */
import * as THREE from "three";
import { CSS2DObject } from "three/addons/renderers/CSS2DRenderer.js";
import type { PartMeta, SceneMeta } from "./scene";

export interface Neighbour {
  part: PartMeta;
  /** gap between the two boxes, scene units (0 = touching or overlapping) */
  gap: number;
  /** closest point on the selected box and on the neighbour's box */
  a: THREE.Vector3;
  b: THREE.Vector3;
}

/** Floor and ceiling touch everything; leave them out of "what is near this" (by name or label: "001_floor_1"). */
const IGNORE = new Set(["floor", "ceiling"]);

/** Closest points between two boxes, axis by axis (exact for axis-aligned boxes). */
function closest(a: PartMeta["bbox"], b: PartMeta["bbox"]): [THREE.Vector3, THREE.Vector3] {
  const pa = new THREE.Vector3();
  const pb = new THREE.Vector3();
  for (let k = 0; k < 3; k++) {
    let va: number;
    let vb: number;
    if (a.max[k] < b.min[k]) [va, vb] = [a.max[k], b.min[k]];
    else if (b.max[k] < a.min[k]) [va, vb] = [a.min[k], b.max[k]];
    else va = vb = (Math.max(a.min[k], b.min[k]) + Math.min(a.max[k], b.max[k])) / 2;
    pa.setComponent(k, va);
    pb.setComponent(k, vb);
  }
  return [pa, pb];
}

/** The built parts nearest to `sel`, closest first; `keep` narrows the candidates (e.g. to the same build). */
export function neighbours(meta: SceneMeta, sel: PartMeta, upto: number, k = 5, keep?: (p: PartMeta) => boolean): Neighbour[] {
  const out: Neighbour[] = [];
  for (const p of meta.parts.slice(0, upto)) {
    if (p.seq === sel.seq || IGNORE.has(p.name) || IGNORE.has(p.label.toLowerCase()) || (keep && !keep(p))) continue;
    const [a, b] = closest(sel.bbox, p.bbox);
    out.push({ part: p, gap: a.distanceTo(b), a, b });
  }
  return out.sort((x, y) => x.gap - y.gap).slice(0, k);
}

/** "0.42 u ≈ 0.48 m", or "touching" */
export function fmtGap(u: number, mpu: number): string {
  if (u < 0.005) return "touching";
  return `${u.toFixed(2)} u ≈ ${(u * mpu).toFixed(2)} m`;
}

/** Leader lines + labels from the selected part to its nearest neighbours. */
export class ProximityView {
  readonly group = new THREE.Group();
  private readonly mat = new THREE.LineDashedMaterial({
    color: 0xffc94d,
    dashSize: 0.06,
    gapSize: 0.04,
    transparent: true,
    opacity: 0.95,
    depthTest: false,
  });
  private readonly dotMat = new THREE.MeshBasicMaterial({ color: 0xffc94d, depthTest: false });
  private readonly dotGeo = new THREE.SphereGeometry(0.025, 12, 8);

  constructor() {
    this.group.renderOrder = 40;
  }

  show(list: Neighbour[], mpu: number, count = 3): void {
    this.clear();
    for (const n of list.slice(0, count)) {
      const mid = n.a.clone().add(n.b).multiplyScalar(0.5);
      if (n.gap >= 0.005) {
        const line = new THREE.Line(new THREE.BufferGeometry().setFromPoints([n.a, n.b]), this.mat);
        line.computeLineDistances();
        line.renderOrder = 40;
        this.group.add(line);
        for (const p of [n.a, n.b]) {
          const dot = new THREE.Mesh(this.dotGeo, this.dotMat);
          dot.position.copy(p);
          dot.renderOrder = 41;
          this.group.add(dot);
        }
      }
      const el = document.createElement("div");
      el.className = "tag tag-gap";
      el.innerHTML = `<b></b><span></span>`;
      el.querySelector("b")!.textContent = n.part.label;
      el.querySelector("span")!.textContent = fmtGap(n.gap, mpu);
      const tag = new CSS2DObject(el);
      tag.position.copy(mid);
      this.group.add(tag);
    }
  }

  clear(): void {
    for (const ch of [...this.group.children]) {
      this.group.remove(ch);
      if (ch instanceof THREE.Line) ch.geometry.dispose();
      if (ch instanceof CSS2DObject) ch.element.remove();
    }
  }
}
