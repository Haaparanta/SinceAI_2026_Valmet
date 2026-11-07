/**
 * Gaussian splat view of the build (Spark, @sparkjsdev/spark): the same rows as the point cloud, drawn as real splats.
 *
 * Data: the detail levels lod/<k>.splat (scripts/lod.py), streamed coarse to fine, or the single scene.splat of older
 * exports; 32 bytes per splat. Every level keeps the segment order (0 = pool, k = part k), so the splats of one segment
 * are one range per level. Each segment is one SplatMesh: when a level arrives, every segment that gained splats is
 * rebuilt from all its levels so far and swapped in once decoded (no gap on screen). The Scan / Model / Overlay /
 * Wireframe looks, build replay and selection work as for the points: each mesh gets the opacity and tint of its role.
 * Spark sorts all meshes together, so the parts blend correctly with the rest of the room.
 *
 * Dollhouse cut: a SplatEdit plane on every mesh but the selected one zeroes the splats above the cut height.
 * VR: the XR rig is scaled (metres per unit), and Spark's default path drops camera scale, so the renderer uses
 * covariance splats, whose render-to-view transform keeps it.
 */
import * as THREE from "three";
import {
  SparkRenderer,
  SplatEdit,
  SplatEditRgbaBlendMode,
  SplatEditSdf,
  SplatEditSdfType,
  SplatFileType,
  SplatMesh,
} from "@sparkjsdev/spark";
import { buildBase, exportHint, fetchBytes, looksFor, type Build, type SceneMeta, type ViewState } from "./scene";

const BYTES = 32;
const WHITE = new THREE.Color(1, 1, 1);

export class SplatLayer {
  readonly group = new THREE.Group();
  /** per segment: [pool, part 1, …, part n]; undefined until the segment has splats */
  private meshes: (SplatMesh | undefined)[] = [];
  /** per segment: the byte blocks received so far, one per level */
  private pieces: Uint8Array[][] = [];
  private cuts: SplatEdit[] = [];
  private spark: SparkRenderer | null = null;
  /** set by load(): Spark joins the scene only once the first level is decoded (an empty one blanks the canvas) */
  private attach: (() => void) | null = null;
  private last: ViewState | null = null;
  private readonly meta: SceneMeta;
  private readonly build: Build;
  ready = false;
  /** splats loaded so far */
  count = 0;

  constructor(meta: SceneMeta, build: Build = "manual") {
    this.meta = meta;
    this.build = build;
    this.group.visible = false;
    const segments = meta.parts.length + 1;
    const cutY = meta.dollhouse_cut_y ?? meta.room_bounds.max[1];
    for (let s = 0; s < segments; s++) {
      this.pieces.push([]);
      this.meshes.push(undefined);
      // the cut: a half-space above the dollhouse height, alpha multiplied by 0
      const edit = new SplatEdit({ rgbaBlendMode: SplatEditRgbaBlendMode.MULTIPLY, softEdge: 0.01 });
      const plane = new SplatEditSdf({ type: SplatEditSdfType.PLANE, opacity: 0 });
      plane.position.set(0, cutY, 0);
      plane.quaternion.setFromUnitVectors(new THREE.Vector3(0, 0, 1), new THREE.Vector3(0, -1, 0));
      edit.addSdf(plane);
      this.cuts.push(edit);
    }
  }

  /**
   * Stream the splat levels 0..maxLevel in order (progress 0..1 over all of them); `onLevel` runs after each level is
   * on screen. Exports without detail levels load scene.splat in one step.
   */
  async load(
    renderer: THREE.WebGLRenderer,
    scene: THREE.Scene,
    onDirty: () => void,
    onProgress: (f: number) => void,
    maxLevel = Infinity,
    onLevel: (level: number) => void = () => {},
  ): Promise<void> {
    this.attach = () => {
      this.spark = new SparkRenderer({ renderer, covSplats: true, onDirty });
      this.spark.visible = this.group.visible;
      scene.add(this.spark);
    };
    const base = buildBase(this.build);
    const hint = `${exportHint(this.build)} (it writes the splat files)`;
    const lods = this.meta.lods?.filter((l) => l.level <= maxLevel) ?? [];
    if (!lods.length) {
      const buf = await fetchBytes(`${base}/scene.splat`, hint, onProgress);
      const ranges: [number, number][] = [[0, this.meta.pool_count], ...this.meta.parts.map((p) => [p.start, p.end] as [number, number])];
      await this.addLevel(buf, this.meta.count, ranges, "scene.splat");
      onDirty();
      onLevel(0);
      return;
    }
    const total = lods.reduce((a, l) => a + l.count, 0);
    let before = 0;
    for (const lod of lods) {
      const buf = await fetchBytes(`${base}/${lod.splat}`, hint, (f) => onProgress((before + f * lod.count) / total));
      before += lod.count;
      await this.addLevel(buf, lod.count, lod.ranges, lod.splat);
      onDirty();
      onLevel(lod.level);
    }
  }

  /** Append one level's splats to their segments, rebuild those meshes, and swap them in once decoded. */
  private async addLevel(buf: ArrayBuffer, count: number, ranges: [number, number][], what: string): Promise<void> {
    if (buf.byteLength !== count * BYTES) {
      throw new Error(`${what} has ${buf.byteLength} bytes, scene.json says ${count} splats: re-export`);
    }
    const changed: number[] = [];
    ranges.forEach(([a, b], s) => {
      if (b <= a || s >= this.pieces.length) return;
      this.pieces[s].push(new Uint8Array(buf.slice(a * BYTES, b * BYTES)));
      changed.push(s);
    });
    const fresh = changed.map((s) => {
      const blocks = this.pieces[s];
      const bytes = new Uint8Array(blocks.reduce((n, p) => n + p.length, 0));
      let at = 0;
      for (const p of blocks) {
        bytes.set(p, at);
        at += p.length;
      }
      // a fresh copy per mesh: the decoder may take ownership of (transfer) the bytes it is given
      return new SplatMesh({ fileBytes: bytes, fileType: SplatFileType.SPLAT });
    });
    await Promise.all(fresh.map((m) => m.initialized));
    if (!this.spark) this.attach?.();
    changed.forEach((s, i) => {
      const old = this.meshes[s];
      if (old) {
        if (this.cuts[s].parent === old) old.remove(this.cuts[s]);
        this.group.remove(old);
        old.dispose();
      }
      this.meshes[s] = fresh[i];
      this.group.add(fresh[i]);
    });
    this.count += count;
    this.ready = true;
    if (this.last) this.apply(this.last);
  }

  /** Same roles as the point shader: pool (and parts after `upto`), built, selected. */
  apply(s: ViewState): void {
    this.last = s;
    if (!this.ready) return;
    const looks = looksFor(s);
    const n = this.meta.parts.length;
    const upto = Math.max(0, Math.min(s.upto, n));
    const sel = s.selected > 0 && s.selected <= upto ? s.selected : -1;
    this.meshes.forEach((mesh, i) => {
      if (!mesh) return;
      const role = i === 0 || i > upto ? 0 : i === sel ? 2 : 1;
      const look = looks[role];
      mesh.opacity = look.alpha;
      mesh.visible = look.alpha > 0;
      mesh.recolor.copy(look.tint ?? WHITE); // multiplies: red / grey for the snapshot style
      const cut = this.cuts[i];
      const wantCut = s.cut && role < 2;
      if (wantCut && cut.parent !== mesh) mesh.add(cut);
      else if (!wantCut && cut.parent === mesh) mesh.remove(cut);
    });
  }

  /** True once Spark has sorted and draws splats (it draws nothing before its first sort). */
  get drawing(): boolean {
    return (this.spark?.activeSplats ?? 0) > 0;
  }

  /** In VR: cut each splat at √5 standard deviations instead of 3 (about 40 % fewer pixels, little visible change). */
  setXr(on: boolean): void {
    if (this.spark) this.spark.maxStdDev = on ? Math.sqrt(5) : 3;
  }

  show(on: boolean): void {
    this.group.visible = on;
    if (this.spark) this.spark.visible = on;
  }
}
