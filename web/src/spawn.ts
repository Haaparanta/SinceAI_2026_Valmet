/**
 * Where a walk-through starts, shared by VR (xr.ts) and the first-person walk mode (walk.ts): an open patch of floor
 * away from equipment, not hugging a wall, preferring the middle of the room, facing the part that matters.
 */
import * as THREE from "three";
import type { PartMeta, SceneMeta } from "./scene";

const HEAD_CLEARANCE_M = 2.0; // anything lower than this over the floor is an obstacle for the spawn point

export interface Spawn {
  /** on the floor (y = floor_y) */
  pos: THREE.Vector3;
  /** rotation about +y such that forward (-z) looks at the focus */
  yaw: number;
}

/** The equipment part with the most points: what to face when nothing is selected. */
export function biggestEquipment(meta: SceneMeta): PartMeta | undefined {
  let best: PartMeta | undefined;
  for (const p of meta.parts) if (p.kind === "equipment" && (!best || p.count > best.count)) best = p;
  return best;
}

/**
 * Open floor, away from anything below head height, not hugging a wall; prefers the middle of the room. A 24 x 24 grid
 * over the room (0.6 m in from the walls), scored by clearance from the parts (capped at 1.5 m) minus a pull towards
 * the centre. Faces `focus`, else the biggest equipment, else the room centre (yaw 0 when standing right there).
 */
export function chooseSpawn(meta: SceneMeta, mpu: number, focus?: PartMeta): Spawn {
  const b = meta.room_bounds;
  const head = meta.floor_y + HEAD_CLEARANCE_M / mpu;
  const obstacles = meta.parts.filter((p) => p.kind !== "structure" && p.bbox.min[1] < head);
  const cx = (b.min[0] + b.max[0]) / 2;
  const cz = (b.min[2] + b.max[2]) / 2;
  const margin = 0.6 / mpu;
  let best = { x: cx, z: cz, score: -Infinity };
  const steps = 24;
  for (let i = 0; i <= steps; i++) {
    for (let j = 0; j <= steps; j++) {
      const x = b.min[0] + margin + ((b.max[0] - b.min[0] - 2 * margin) * i) / steps;
      const z = b.min[2] + margin + ((b.max[2] - b.min[2] - 2 * margin) * j) / steps;
      let clear = Infinity;
      for (const p of obstacles) {
        const dx = Math.max(p.bbox.min[0] - x, 0, x - p.bbox.max[0]);
        const dz = Math.max(p.bbox.min[2] - z, 0, z - p.bbox.max[2]);
        clear = Math.min(clear, Math.hypot(dx, dz));
      }
      const score = Math.min(clear, 1.5 / mpu) - 0.2 * Math.hypot(x - cx, z - cz);
      if (score > best.score) best = { x, z, score };
    }
  }
  const target = focus ?? biggestEquipment(meta);
  const fx = target ? (target.bbox.min[0] + target.bbox.max[0]) / 2 : cx;
  const fz = target ? (target.bbox.min[2] + target.bbox.max[2]) / 2 : cz;
  const dx = fx - best.x;
  const dz = fz - best.z;
  return {
    pos: new THREE.Vector3(best.x, meta.floor_y, best.z),
    yaw: Math.hypot(dx, dz) > 1e-3 ? Math.atan2(-dx, -dz) : 0,
  };
}
