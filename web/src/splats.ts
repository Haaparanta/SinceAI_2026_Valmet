/**
 * Gaussian splat view of the build (Spark, @sparkjsdev/spark): the same rows as the point cloud, drawn as real splats.
 *
 * Data: the detail levels lod/<k>.splat (scripts/lod.py), streamed coarse to fine, or the single scene.splat of older
 * exports; 32 bytes per splat. Build "both" joins the two builds' files the way scene.ts mergeRows joins the points:
 * every manual row, then the automatic rows after its pool. Every level keeps the segment order (0 = pool, k = part k), so the splats of one segment
 * are one range per level. Each level file is decoded once (one PackedSplats, in row order); each segment's slice of it
 * is then appended to that segment's own PackedSplats (a copy of packed words, no second decode), and the segment's
 * SplatMesh, created the first time the segment gets splats, re-accumulates. The Scan / Model / Overlay /
 * Wireframe looks, build replay and selection work as for the points: each mesh gets the opacity and tint of its role.
 * Spark sorts all meshes together, so the parts blend correctly with the rest of the room.
 *
 * Dollhouse cut: a SplatEdit plane on every mesh but the selected one zeroes the splats above the cut height.
 * VR: the XR rig is scaled (metres per unit), and Spark's default path drops camera scale, so the renderer uses
 * covariance splats, whose render-to-view transform keeps it.
 */
import * as THREE from "three";
import {
  PackedSplats,
  SparkRenderer,
  SplatEdit,
  SplatEditRgbaBlendMode,
  SplatEditSdf,
  SplatEditSdfType,
  SplatFileType,
  SplatMesh,
} from "@sparkjsdev/spark";
import {
  buildBase,
  exportHint,
  fetchBytes,
  looksFor,
  streamInOrder,
  manualCount,
  type Build,
  type LodMeta,
  type SceneMeta,
  type ViewState,
} from "./scene";

const BYTES = 32;
const WHITE = new THREE.Color(1, 1, 1);

export class SplatLayer {
  readonly group = new THREE.Group();
  /** per segment: [pool, part 1, …, part n]; undefined until the segment has splats */
  private meshes: (SplatMesh | undefined)[] = [];
  /** per segment: its splats so far (all levels received), shared with its mesh */
  private packed: (PackedSplats | undefined)[] = [];
  private cuts: SplatEdit[] = [];
  private spark: SparkRenderer | null = null;
  /** set by load(): Spark joins the scene only once the first level is decoded (an empty one blanks the canvas) */
  private attach: (() => void) | null = null;
  private last: ViewState | null = null;
  private readonly meta: SceneMeta;
  private readonly build: Build;
  /** true from the first level on (splats can be drawn); `complete` once every level asked for is in */
  ready = false;
  complete = false;
  /** splats loaded so far */
  count = 0;

  constructor(meta: SceneMeta, build: Build = "manual") {
    this.meta = meta;
    this.build = build;
    this.group.visible = false;
    const segments = meta.parts.length + 1;
    const cutY = meta.dollhouse_cut_y ?? meta.room_bounds.max[1];
    for (let s = 0; s < segments; s++) {
      this.packed.push(undefined);
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
    const lods = this.meta.lods?.filter((l) => l.level <= maxLevel) ?? [];
    if (!lods.length) {
      const both = this.build === "both";
      const buf = await this.fetchJoined(
        both ? "manual" : this.build,
        "scene.splat",
        both ? "scene.splat" : null,
        this.meta.auto_pool_count ?? 0,
        onProgress,
      );
      const ranges: [number, number][] = [[0, this.meta.pool_count], ...this.meta.parts.map((p) => [p.start, p.end] as [number, number])];
      await this.addLevel(buf, this.meta.count, ranges, "scene.splat");
      this.complete = true;
      onDirty();
      onLevel(0);
      return;
    }
    const total = lods.reduce((a, l) => a + l.count, 0);
    let done = 0;
    await streamInOrder(
      lods.length,
      // level 0 streams with progress; later levels prefetch while the previous one decodes
      (k) => this.fetchLevel(lods[k], k === 0 ? (f) => onProgress((f * lods[0].count) / total) : undefined),
      async (k, buf) => {
        const lod = lods[k];
        await this.addLevel(buf, lod.count, lod.ranges, lod.splat);
        done += lod.count;
        if (k === lods.length - 1) this.complete = true;
        onProgress(done / total);
        onDirty();
        onLevel(lod.level);
      },
    );
  }

  /** One level's splat bytes; for "both" the two builds' level files joined (manual rows, then automatic after its pool). */
  private fetchLevel(lod: LodMeta, onProgress?: (f: number) => void): Promise<ArrayBuffer> {
    if (!lod.sources) return this.fetchJoined(this.build === "auto" ? "auto" : "manual", lod.splat, null, 0, onProgress);
    const { manual, auto } = lod.sources;
    return this.fetchJoined("manual", manual.splat, auto.splat, auto.ranges[0][1], onProgress);
  }

  /** GET `first` from a build (and, for "both", `second` from the automatic build, from row `skip` on) as one buffer. */
  private async fetchJoined(
    build: "manual" | "auto",
    first: string,
    second: string | null,
    skip: number,
    onProgress?: (f: number) => void,
  ): Promise<ArrayBuffer> {
    const hint = `${exportHint(this.build)} (it writes the splat files)`;
    const got = [0, 0];
    const report = (i: number) =>
      onProgress &&
      ((f: number) => {
        got[i] = f;
        onProgress(second ? (got[0] + got[1]) / 2 : got[0]);
      });
    const [a, b] = await Promise.all([
      fetchBytes(`${buildBase(build)}/${first}`, hint, report(0)),
      second ? fetchBytes(`${buildBase("auto")}/${second}`, hint, report(1)) : Promise.resolve(null),
    ]);
    if (!b) return a;
    if (b.byteLength < skip * BYTES) throw new Error(`${second} has fewer than its ${skip} pool rows: re-export`);
    const out = new Uint8Array(a.byteLength + b.byteLength - skip * BYTES);
    out.set(new Uint8Array(a), 0);
    out.set(new Uint8Array(b, skip * BYTES), a.byteLength);
    return out.buffer;
  }

  /** Decode one level once, append each segment's slice to that segment's splats, and add meshes for new segments. */
  private async addLevel(buf: ArrayBuffer, count: number, ranges: [number, number][], what: string): Promise<void> {
    if (buf.byteLength !== count * BYTES) {
      throw new Error(`${what} has ${buf.byteLength} bytes, scene.json says ${count} splats: re-export`);
    }
    const level = new PackedSplats({ fileBytes: buf, fileType: SplatFileType.SPLAT });
    await level.initialized;
    const words = level.packedArray;
    if (!words || level.numSplats !== count) {
      throw new Error(`${what}: decoded ${level.numSplats} splats, scene.json says ${count}: re-export`);
    }
    const fresh: [number, SplatMesh][] = [];
    ranges.forEach(([a, b], s) => {
      if (b <= a || s >= this.packed.length) return;
      const n = b - a;
      let seg = this.packed[s];
      const at = seg?.numSplats ?? 0;
      if (!seg) seg = this.packed[s] = new PackedSplats({ splatEncoding: level.splatEncoding });
      seg.ensureSplats(at + n).set(words.subarray(a * 4, b * 4), at * 4); // 4 packed words per splat
      seg.numSplats = at + n;
      seg.needsUpdate = true;
      const mesh = this.meshes[s];
      if (mesh) {
        mesh.updateGenerator();
        mesh.updateVersion();
      } else fresh.push([s, new SplatMesh({ packedSplats: seg })]);
    });
    level.dispose();
    await Promise.all(fresh.map(([, m]) => m.initialized));
    if (!this.spark) this.attach?.();
    for (const [s, mesh] of fresh) {
      this.meshes[s] = mesh;
      this.group.add(mesh);
    }
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
    const split = manualCount(this.meta);
    this.meshes.forEach((mesh, i) => {
      if (!mesh) return;
      const auto = i > split;
      // same rule as the point shader: a hidden automatic build vanishes, a hidden manual build is plain scan again
      const gone = auto && s.show === "manual";
      const asScan = !auto && i > 0 && s.show === "auto";
      const role = i === 0 || i > upto || asScan ? 0 : i === sel ? 2 : 1;
      const look = looks[role];
      mesh.opacity = look.alpha;
      mesh.visible = look.alpha > 0 && !gone;
      // multiplies: red / grey for the snapshot style, cyan / amber by origin
      mesh.recolor.copy((i > split && look.autoTint) || look.tint || WHITE);
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
