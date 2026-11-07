/**
 * Gaussian splat view of the build (Spark, @sparkjsdev/spark): the same rows as the point cloud, drawn as real splats.
 *
 * Data: data/derived/viewer/scene.splat (scripts/export_viewer_scene.py), 32 bytes per splat, row i = row i of
 * scene.bin. The file is cut into one SplatMesh for the pool and one per part, so the Scan / Model / Overlay / Wireframe
 * looks, build replay and selection work exactly as for the points: each mesh gets the opacity and tint of its role.
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
import { buildBase, looksFor, type Build, type SceneMeta, type ViewState } from "./scene";

const BYTES = 32;
const WHITE = new THREE.Color(1, 1, 1);

export class SplatLayer {
  readonly group = new THREE.Group();
  /** [pool, part 1, …, part n] */
  private meshes: SplatMesh[] = [];
  private cuts: SplatEdit[] = [];
  private spark: SparkRenderer | null = null;
  private readonly meta: SceneMeta;
  private readonly url: string;
  private readonly script: string;
  ready = false;

  constructor(meta: SceneMeta, build: Build = "manual") {
    this.meta = meta;
    this.url = `${buildBase(build)}/scene.splat`;
    this.script = build === "auto" ? "make viewer-auto" : "make viewer";
    this.group.visible = false;
  }

  /** Download scene.splat (with progress 0..1) and build the meshes. Resolves once every mesh is decoded. */
  async load(
    renderer: THREE.WebGLRenderer,
    scene: THREE.Scene,
    onDirty: () => void,
    onProgress: (f: number) => void,
  ): Promise<void> {
    const res = await fetch(this.url);
    if (!res.ok) throw new Error(`GET ${this.url} -> ${res.status}: run \`${this.script}\` (it writes scene.splat)`);
    const total = Number(res.headers.get("Content-Length")) || this.meta.count * BYTES;
    const buf = new Uint8Array(total);
    let got = 0;
    const reader = res.body!.getReader();
    for (;;) {
      const { done, value } = await reader.read();
      if (done) break;
      if (got + value.length > buf.length) throw new Error("scene.splat is larger than its Content-Length");
      buf.set(value, got);
      got += value.length;
      onProgress(got / total);
    }
    if (got !== this.meta.count * BYTES) {
      throw new Error(`scene.splat has ${got} bytes, scene.json says ${this.meta.count} splats: re-run \`${this.script}\``);
    }

    this.spark = new SparkRenderer({ renderer, covSplats: true, onDirty });
    scene.add(this.spark);

    const ranges: [number, number][] = [[0, this.meta.pool_count], ...this.meta.parts.map((p) => [p.start, p.end] as [number, number])];
    // the cut: a half-space above the dollhouse height, alpha multiplied by 0
    const cutY = this.meta.dollhouse_cut_y ?? this.meta.room_bounds.max[1];
    this.meshes = ranges.map(([a, b]) => {
      // each mesh gets its own copy: the decoder may take ownership of (transfer) the bytes it is given
      const mesh = new SplatMesh({ fileBytes: buf.slice(a * BYTES, b * BYTES), fileType: SplatFileType.SPLAT });
      this.group.add(mesh);
      const edit = new SplatEdit({ rgbaBlendMode: SplatEditRgbaBlendMode.MULTIPLY, softEdge: 0.01 });
      const plane = new SplatEditSdf({ type: SplatEditSdfType.PLANE, opacity: 0 });
      plane.position.set(0, cutY, 0);
      plane.quaternion.setFromUnitVectors(new THREE.Vector3(0, 0, 1), new THREE.Vector3(0, -1, 0));
      edit.addSdf(plane);
      this.cuts.push(edit);
      return mesh;
    });
    await Promise.all(this.meshes.map((m) => m.initialized));
    this.ready = true;
  }

  /** Same roles as the point shader: pool (and parts after `upto`), built, selected. */
  apply(s: ViewState): void {
    if (!this.ready) return;
    const looks = looksFor(s);
    const n = this.meta.parts.length;
    const upto = Math.max(0, Math.min(s.upto, n));
    const sel = s.selected > 0 && s.selected <= upto ? s.selected : -1;
    this.meshes.forEach((mesh, i) => {
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

  /** In VR: cut each splat at √5 standard deviations instead of 3 (about 40 % fewer pixels, little visible change). */
  setXr(on: boolean): void {
    if (this.spark) this.spark.maxStdDev = on ? Math.sqrt(5) : 3;
  }

  show(on: boolean): void {
    this.group.visible = on;
    if (this.spark) this.spark.visible = on;
  }
}
