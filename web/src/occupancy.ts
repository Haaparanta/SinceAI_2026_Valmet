/**
 * Where the first-person walk (walk.ts) can stand: a 2D occupancy grid over the room floor, built from the POINTS of the
 * built parts rather than their boxes. The automatic build's 348 obstacle boxes cover the whole floor between them (the
 * box-based free fraction is 0), so box collision leaves nowhere to walk; a part's points lie only where its surfaces
 * are, so the floor between the pipes stays open.
 *
 * rebuild() marks every cell that holds a point of an obstacle part (the caller says which seqs block: built, shown, not
 * structure) inside the walker's height band [floor + step-over, eye + head room], then grows the marks by the walker's
 * radius plus the grid's own rounding (makeDisc) with a precomputed disc of cell offsets, so the walker's centre never
 * comes closer than the radius to a point. blocked(x, z) is then one array lookup, so collision costs nothing per
 * sub-step. Typed arrays and nothing allocated per point: the fixtures rebuild in 2-11 ms, 1.5 M rows in about 18 ms
 * (node, V8), well inside the 100 ms budget; a rebuild happens when a detail level arrives or the built set changes,
 * never per frame. Note that the synthetic fixtures fill every box with uniform random points, so there the point grid
 * equals the box grid (the automatic fixture stays mostly full); the open floor between real parts shows only on a real
 * export.
 */
import type { Chunk, SceneMeta } from "./scene";

/** Default cell edge, scene units (about 6 cm): collision rounds to a cell, well under the walker's 30 cm radius. */
export const CELL_U = 0.05;
/** Coarser alternative: rebuilds faster (a 49-offset disc instead of 137) but grows the parts by 0.14 u (16 cm) more. */
export const COARSE_CELL_U = 0.1;

export class Occupancy {
  /** cell edge, scene units */
  readonly cell: number;
  /** cells along x and z: the grid covers meta.room_bounds from (originX, originZ) */
  readonly nx: number;
  readonly nz: number;
  readonly originX: number;
  readonly originZ: number;
  /** row-major (iz * nx + ix): 1 where an in-band point of an obstacle part fell */
  readonly occupied: Uint8Array;
  /** occupied grown by the walker's radius: 1 where a walker centred in the cell overlaps a part */
  readonly blockedCells: Uint8Array;
  /** true once rebuild() has seen a chunk; until then the walk falls back to its box test */
  built = false;

  /** (di, dj) pairs with hypot(di, dj) * cell <= radius, and the same as dj * nx + di for cells away from the border */
  private disc = new Int32Array(0);
  private discLinear = new Int32Array(0);
  /** max |di|, |dj| of the disc, in cells */
  private discReach = 0;
  /** the radius the disc was made for (scene units); -1 for none yet */
  private discRadius = -1;

  constructor(meta: SceneMeta, cell = CELL_U) {
    if (!(cell > 0)) throw new Error(`occupancy cell must be positive, got ${cell}`);
    const b = meta.room_bounds;
    this.cell = cell;
    this.originX = b.min[0];
    this.originZ = b.min[2];
    this.nx = Math.max(1, Math.ceil((b.max[0] - b.min[0]) / cell));
    this.nz = Math.max(1, Math.ceil((b.max[2] - b.min[2]) / cell));
    this.occupied = new Uint8Array(this.nx * this.nz);
    this.blockedCells = new Uint8Array(this.nx * this.nz);
  }

  /**
   * Mark the cells under the obstacle parts' points with y in [yMin, yMax] (the walker's height band), then grow them by
   * radiusU (plus the grid's rounding, see makeDisc). `chunks` are the loaded detail levels (cloud.chunks): in each,
   * segment 0 is the pool and never blocks and segment k holds part k. Returns how many obstacle points marked a cell (in
   * the band and inside the room).
   */
  rebuild(chunks: Chunk[], isObstacle: (seq: number) => boolean, yMin: number, yMax: number, radiusU: number): number {
    const { nx, nz, originX, originZ, occupied } = this;
    const inv = 1 / this.cell;
    occupied.fill(0);
    let used = 0;
    for (const chunk of chunks) {
      const attr = chunk.geometry.getAttribute("position");
      if (!attr) continue;
      // parseScene's planar Float32Array (xyz per row); an interleaved attribute carries its own stride and offset
      const pos = attr.array;
      const stride = "isInterleavedBufferAttribute" in attr ? attr.data.stride : attr.itemSize;
      const base = "isInterleavedBufferAttribute" in attr ? attr.offset : 0;
      const ranges = chunk.ranges;
      for (let seq = 1; seq < ranges.length; seq++) {
        if (!isObstacle(seq)) continue;
        const end = Math.min(ranges[seq][1], attr.count);
        for (let i = ranges[seq][0]; i < end; i++) {
          const k = base + i * stride;
          const y = pos[k + 1];
          if (y < yMin || y > yMax) continue;
          const fx = (pos[k] - originX) * inv;
          const fz = (pos[k + 2] - originZ) * inv;
          if (fx < 0 || fx >= nx || fz < 0 || fz >= nz) continue;
          occupied[(fz | 0) * nx + (fx | 0)] = 1;
          used++;
        }
      }
    }
    this.dilate(radiusU);
    this.built = chunks.length > 0;
    return used;
  }

  /** Whether a walker centred at (x, z) overlaps a part; true outside the grid (outside the room). */
  blocked(x: number, z: number): boolean {
    const fx = (x - this.originX) / this.cell;
    const fz = (z - this.originZ) / this.cell;
    if (!(fx >= 0 && fx < this.nx && fz >= 0 && fz < this.nz)) return true; // NaN counts as outside
    return this.blockedCells[(fz | 0) * this.nx + (fx | 0)] === 1;
  }

  /** Share of the room's cells a walker can stand in, 0..1 (a walkability check: tests and the real export). */
  freeFraction(): number {
    const b = this.blockedCells;
    let free = 0;
    for (let i = 0; i < b.length; i++) if (!b[i]) free++;
    return b.length ? free / b.length : 0;
  }

  /** blockedCells = occupied grown by the disc (remade when the radius changes). */
  private dilate(radiusU: number): void {
    if (radiusU !== this.discRadius) this.makeDisc(radiusU);
    const { nx, nz, occupied, blockedCells, disc, discLinear } = this;
    const reach = this.discReach;
    blockedCells.fill(0);
    for (let iz = 0; iz < nz; iz++) {
      const row = iz * nx;
      const innerRow = iz >= reach && iz < nz - reach;
      for (let ix = 0; ix < nx; ix++) {
        const k = row + ix;
        if (!occupied[k]) continue;
        if (innerRow && ix >= reach && ix < nx - reach) {
          // away from the border every offset lands inside the grid: no bounds checks
          for (let d = 0; d < discLinear.length; d++) blockedCells[k + discLinear[d]] = 1;
        } else {
          for (let d = 0; d < disc.length; d += 2) {
            const jx = ix + disc[d];
            const jz = iz + disc[d + 1];
            if (jx >= 0 && jx < nx && jz >= 0 && jz < nz) blockedCells[jz * nx + jx] = 1;
          }
        }
      }
    }
  }

  /**
   * The cell offsets within the walker's radius of a cell, plus the grid's rounding: a point marks the cell it fell in
   * and the walker is tested by the cell it stands in, so a walker in a free cell can be up to cell * sqrt(2) closer to
   * a point than the two cell centres are (both at the far corners, on a diagonal). Growing by that much more keeps the
   * walker's centre at least the radius from every point; the band around a part gets about 1.4 cells wider on each
   * side (137 offsets at cell 0.05 u and radius 0.26 u, 49 at 0.10 u).
   */
  private makeDisc(radiusU: number): void {
    const r = (radiusU > 0 ? radiusU : 0) + this.cell * Math.SQRT2; // a bad radius still blocks the cell's neighbours
    const reach = Math.floor(r / this.cell);
    const offs: number[] = [];
    for (let dj = -reach; dj <= reach; dj++) {
      for (let di = -reach; di <= reach; di++) if (Math.hypot(di, dj) * this.cell <= r) offs.push(di, dj);
    }
    this.disc = Int32Array.from(offs);
    this.discLinear = new Int32Array(offs.length / 2);
    for (let d = 0; d < offs.length; d += 2) this.discLinear[d / 2] = offs[d + 1] * this.nx + offs[d];
    this.discReach = reach;
    this.discRadius = radiusU;
  }
}
