/**
 * First-person walk mode for the screen: the VR walk-through (xr.ts) without a headset, on desktop and phone.
 *
 * - You stand ON the floor at eye height (1.65 m): the camera y never changes while walking, movement is horizontal.
 * - Walls: the walkable area is the room bounds minus a 0.25 m margin (the same margin as keepHeadInRoom in xr.ts).
 * - Parts: the walker is a vertical cylinder of radius 0.30 m from the floor to just over the eyes. Every built part that
 *   reaches into that height band blocks (pipes up by the ceiling and the structure never do), resolved per axis so you
 *   slide along a pump instead of sticking to it. What blocks is the part's POINTS, not its box: an occupancy grid over
 *   the floor (occupancy.ts) marks the cells the loaded points fall in, grown by the walker's radius, so a sprawling
 *   cluster box with pipes along its edges can be walked through where there is nothing. Until the first detail level is
 *   in, the boxes grown by the radius stand in. A part that appears around you (the build slider) never traps you:
 *   standing inside something, every step is allowed until you are clear again.
 * - Gaze: a ray from the eye through the screen centre; the nearest built part within 12 m gets a cyan box (red when it
 *   is the selected one) and the HUD (#aim, drawn by main.ts) shows its name, kind, point count and distance. Click, tap
 *   or Enter selects it. The aim stays box-based: a box is what you can point at, the points are what you bump into.
 * - Keys: W A S D / arrows walk, Q E snap-turn 30°, Shift runs; the mouse looks (pointer lock on click, else a drag).
 *   Touch: the thumb stick (#joystick) walks, a one-finger drag on the room looks, a tap selects.
 */
import * as THREE from "three";
import { Occupancy } from "./occupancy";
import { pickPart, type Chunk, type PartMeta, type SceneMeta } from "./scene";
import { biggestEquipment, chooseSpawn } from "./spawn";

export interface WalkHooks {
  /** called once the camera stands in the room / is back on its orbit */
  onEnter(): void;
  onExit(): void;
  /** click, tap or Enter on the aimed part: select it, or clear the selection if it already is (as in VR) */
  select(seq: number): void;
  /** the camera or the aim changed: redraw */
  onChange(): void;
}

export interface WalkOptions {
  metresPerUnit: number;
  /** parts 1..upto are built: they block and can be aimed at */
  upto: () => number;
  /** the selected part's seq, 0 for none (colours the highlight) */
  selected: () => number;
  /** whether a built part is drawn (build "both": cloud.visibleIn) */
  visible: (p: PartMeta) => boolean;
  /** face this part on entry (the selected one); falls back to the biggest equipment, then the room centre */
  focus?: () => PartMeta | undefined;
  /** the loaded detail levels (cloud.chunks): their points build the occupancy grid; without it the boxes block */
  chunks?: () => Chunk[];
}

export interface Aimed {
  part: PartMeta;
  /** scene units from the eye to the part's box */
  distance: number;
  point: THREE.Vector3;
}

const WALK_MPS = 1.4; // as in VR (xr.ts)
const RUN = 2; // with Shift
const TURN = Math.PI / 6; // Q / E snap turn
const MAX_PITCH = THREE.MathUtils.degToRad(80);
const MOUSE_RAD_PER_PX = 0.0025;
const TOUCH_RAD_PER_PX = 0.005;
const WALL_MARGIN_M = 0.25;
const HEAD_ROOM_M = 0.15; // the walker's top is this much over the eyes
const STEP_OVER_M = 0.1; // anything ending lower than this over the floor is walked over
const CELL_U = 0.05; // occupancy grid cell (scene units)
const GAZE_M = 12;
const DEADZONE = 0.18;
const STICK_TRAVEL_PX = 36; // (120 px ring - 48 px knob) / 2
const TAP_MS = 500;
const TAP_PX = 8;
const CYAN = 0x00e5ff;
const RED = 0xff2d55;
const KEYS = new Set(["w", "a", "s", "d", "q", "e", "arrowup", "arrowdown", "arrowleft", "arrowright", "enter"]);
/** input types that do not take typing: the keys stay the walk's after a click on the build slider */
const NOT_TYPING = new Set(["range", "checkbox", "radio", "button", "submit", "reset", "color", "file"]);

const keyName = (e: KeyboardEvent): string => e.key.toLowerCase();
const clamp = THREE.MathUtils.clamp;

interface Saved {
  pos: THREE.Vector3;
  quat: THREE.Quaternion;
  fov: number;
  near: number;
  order: THREE.EulerOrder;
}

interface Press {
  id: number;
  type: string;
  x: number;
  y: number;
  /** last position, for drag deltas */
  lx: number;
  ly: number;
  t: number;
  /** farthest the pointer went from where it came down (px) */
  moved: number;
}

export class WalkMode {
  /** the highlight lives here; main.ts adds the group to the scene */
  readonly group = new THREE.Group();
  readonly highlight: THREE.Box3Helper;
  active = false;
  readonly eyeHeightM = 1.65;
  readonly radiusM = 0.3;
  /** camera y while walking: floor + eye height, never anything else */
  readonly eyeY: number;
  /** rotation about +y (left is positive) and about the local x; roll is always 0 */
  yaw = 0;
  pitch = 0;
  /** what the screen centre points at, within 12 m; null for nothing */
  aimed: Aimed | null = null;
  /** the walker's eye: the camera position itself */
  readonly position: THREE.Vector3;
  /** the walkable area: the room minus the wall margin */
  readonly bounds: { minX: number; maxX: number; minZ: number; maxZ: number };
  /** where the loaded points of the obstacles are (rebuildOccupancy); null until there is a chunk to build it from */
  occupancy: Occupancy | null = null;

  private readonly camera: THREE.PerspectiveCamera;
  private readonly canvas: HTMLCanvasElement;
  private readonly meta: SceneMeta;
  private readonly hooks: WalkHooks;
  private readonly opts: WalkOptions;
  private readonly mpu: number;
  private readonly coarse: boolean;
  private saved: Saved | null = null;
  private readonly held = new Set<string>();
  private locked = false;
  private press: Press | null = null;
  /** thumb stick, normalised: x right, y down (screen) */
  private stick = { x: 0, y: 0 };
  private aimKey = "";
  /** what the grid was last built from (chunks and obstacles): the same again is not rebuilt */
  private occKey = "";
  private readonly ray = new THREE.Ray();

  constructor(camera: THREE.PerspectiveCamera, canvas: HTMLCanvasElement, meta: SceneMeta, hooks: WalkHooks, opts: WalkOptions) {
    this.camera = camera;
    this.canvas = canvas;
    this.meta = meta;
    this.hooks = hooks;
    this.opts = opts;
    this.mpu = opts.metresPerUnit;
    this.position = camera.position;
    this.eyeY = meta.floor_y + this.eyeHeightM / this.mpu;
    const b = meta.room_bounds;
    const m = WALL_MARGIN_M / this.mpu;
    this.bounds = { minX: b.min[0] + m, maxX: b.max[0] - m, minZ: b.min[2] + m, maxZ: b.max[2] - m };
    this.coarse = matchMedia("(pointer: coarse)").matches;
    this.highlight = new THREE.Box3Helper(new THREE.Box3(), new THREE.Color(CYAN));
    this.highlight.visible = false;
    this.highlight.renderOrder = 25;
    this.group.add(this.highlight);
    this.bindKeys();
    this.bindPointer();
    this.bindJoystick();
    document.addEventListener("pointerlockchange", () => (this.locked = document.pointerLockElement === this.canvas));
    document.addEventListener("pointerlockerror", () => (this.locked = false));
    window.addEventListener("blur", () => this.held.clear());
  }

  /** Save the orbit camera, stand on open floor at eye height facing the focus, take over the keys and the pointer. */
  enter(): void {
    if (this.active) return;
    const c = this.camera;
    this.saved = { pos: c.position.clone(), quat: c.quaternion.clone(), fov: c.fov, near: c.near, order: c.rotation.order };
    this.rebuildOccupancy(); // the spawn nudge and the first steps collide with the points, not the boxes
    const focus = this.opts.focus?.();
    const spawn = chooseSpawn(this.meta, this.mpu, focus);
    this.clearSpot(spawn.pos);
    c.position.set(spawn.pos.x, this.eyeY, spawn.pos.z);
    c.fov = 70;
    c.updateProjectionMatrix();
    this.active = true;
    // face the selected part, else the biggest equipment, else the room centre, from where you actually stand
    this.yaw = spawn.yaw; // what lookAt keeps when the target is right here
    const target = focus ?? biggestEquipment(this.meta);
    if (target) {
      const b = target.bbox;
      this.lookAt((b.min[0] + b.max[0]) / 2, (b.min[1] + b.max[1]) / 2, (b.min[2] + b.max[2]) / 2);
    } else {
      const b = this.meta.room_bounds;
      this.lookAt((b.min[0] + b.max[0]) / 2, this.eyeY, (b.min[2] + b.max[2]) / 2);
    }
    // the Walk button (or the filter box) must not keep the keys: they walk now
    const el = document.activeElement;
    if (el instanceof HTMLElement && el !== document.body) el.blur();
    this.hooks.onEnter();
    this.hooks.onChange();
  }

  /** Back to the orbit camera exactly as it was. */
  exit(): void {
    if (!this.active) return;
    if (document.pointerLockElement === this.canvas) document.exitPointerLock();
    this.held.clear();
    this.press = null;
    this.setStick(0, 0);
    const c = this.camera;
    const s = this.saved;
    if (s) {
      c.position.copy(s.pos);
      c.rotation.order = s.order; // before the quaternion: changing the order re-reads the Euler angles
      c.quaternion.copy(s.quat);
      c.fov = s.fov;
      c.near = s.near;
      c.updateProjectionMatrix();
    }
    this.saved = null;
    this.aimed = null;
    this.aimKey = "";
    this.highlight.visible = false;
    this.active = false;
    this.hooks.onExit();
    this.hooks.onChange();
  }

  /** Per frame while active: held keys and the thumb stick walk, then the gaze is refreshed. */
  update(dt: number): void {
    if (!this.active) return;
    const h = this.held;
    let f = (h.has("w") || h.has("arrowup") ? 1 : 0) - (h.has("s") || h.has("arrowdown") ? 1 : 0);
    let s = (h.has("d") || h.has("arrowright") ? 1 : 0) - (h.has("a") || h.has("arrowleft") ? 1 : 0);
    f -= this.stick.y;
    s += this.stick.x;
    const mag = Math.hypot(f, s);
    if (mag > 1e-6 && dt > 0) {
      const k = (mag > 1 ? 1 / mag : 1) * WALK_MPS * (h.has("shift") ? RUN : 1) * dt;
      this.moveBy(f * k, s * k);
    } else this.updateAim(true); // the build slider or a selection may have changed what is in front
  }

  /**
   * Whether a key event is the walk's (main.ts leaves those alone while walking): W A S D, arrows, Q E, Enter. Not with
   * a modifier, not while typing (the filter box), not while a dialog (the lightbox) has the keys, and Enter only when
   * nothing focused takes it itself (a button, a parts-list row).
   */
  handlesKey(e: KeyboardEvent): boolean {
    if (!this.active || e.metaKey || e.ctrlKey || e.altKey) return false;
    if (document.querySelector('[aria-modal="true"]:not([hidden]), dialog[open]')) return false;
    const t = e.target;
    if (typingIn(t)) return false;
    const k = keyName(e);
    if (k === "enter" && t !== document.body && t !== this.canvas && t !== document.documentElement) return false;
    return KEYS.has(k);
  }

  /** Set the view direction (pitch clamped to ±80°). */
  setLook(yaw: number, pitch: number): void {
    this.yaw = Math.atan2(Math.sin(yaw), Math.cos(yaw));
    this.pitch = clamp(pitch, -MAX_PITCH, MAX_PITCH);
    this.camera.rotation.set(this.pitch, this.yaw, 0, "YXZ");
    this.updateAim(false);
    this.hooks.onChange();
  }

  /** Turn the view towards a world point (the yaw stays when the point is right here). */
  lookAt(x: number, y: number, z: number): void {
    const p = this.camera.position;
    const dx = x - p.x;
    const dy = y - p.y;
    const dz = z - p.z;
    const flat = Math.hypot(dx, dz);
    this.setLook(flat > 1e-6 ? Math.atan2(-dx, -dz) : this.yaw, Math.atan2(dy, flat));
  }

  /** The look direction, a unit vector. */
  forward(out: THREE.Vector3): THREE.Vector3 {
    const c = Math.cos(this.pitch);
    return out.set(-Math.sin(this.yaw) * c, Math.sin(this.pitch), -Math.cos(this.yaw) * c);
  }

  /** Teleport: stand at (x, floor, z) with no collision check (a bad spot is walked out of anyway). */
  setPosition(x: number, z: number): void {
    this.camera.position.set(x, this.eyeY, z);
    this.updateAim(false);
    this.hooks.onChange();
  }

  /**
   * Walk, in metres, relative to the look direction (forward = where you look, strafe = to your right), stopping at
   * the parts and the walls. Sub-steps no longer than the walker's radius: an obstacle grown by the radius is at least
   * two radii wide, so no step can jump through one. Returns whether the position changed.
   */
  moveBy(forwardM: number, strafeM: number): boolean {
    const sy = Math.sin(this.yaw);
    const cy = Math.cos(this.yaw);
    const dx = (-sy * forwardM + cy * strafeM) / this.mpu;
    const dz = (-cy * forwardM - sy * strafeM) / this.mpu;
    const len = Math.hypot(dx, dz);
    if (len < 1e-9) return false;
    const blocked = this.collider();
    const r = this.radiusM / this.mpu;
    const b = this.bounds;
    const p = this.camera.position;
    let x = p.x;
    let z = p.z;
    const n = Math.max(1, Math.ceil(len / r));
    const sx = dx / n;
    const sz = dz / n;
    for (let i = 0; i < n; i++) {
      // already inside something (a part the build slider put around you): any step is allowed, you can always get out
      const inside = blocked(x, z);
      const x0 = x;
      const z0 = z;
      const nx = clamp(x + sx, b.minX, b.maxX);
      if (inside || !blocked(nx, z)) x = nx;
      const nz = clamp(z + sz, b.minZ, b.maxZ);
      if (inside || !blocked(x, nz)) z = nz;
      if (x === x0 && z === z0) break; // stuck against something: the next sub-steps would be too
    }
    x = clamp(x, b.minX, b.maxX);
    z = clamp(z, b.minZ, b.maxZ);
    if (x === p.x && z === p.z) return false;
    p.set(x, this.eyeY, z);
    this.updateAim(false);
    this.hooks.onChange();
    return true;
  }

  /** The built, drawn parts that block walking: everything but structure that reaches into the walker's height band. */
  obstacles(): PartMeta[] {
    const upto = this.opts.upto();
    const top = this.eyeY + HEAD_ROOM_M / this.mpu;
    const low = this.meta.floor_y + STEP_OVER_M / this.mpu;
    return this.meta.parts.filter((p) => {
      const b = p.bbox;
      return p.seq <= upto && p.kind !== "structure" && b.min[1] < top && b.max[1] > low && this.opts.visible(p);
    });
  }

  /**
   * Whether a walker standing at (x, z) is in something: the occupancy grid once it is built (true outside the grid),
   * else the obstacle boxes grown by the walker's radius.
   */
  blockedAt(x: number, z: number): boolean {
    return this.collider()(x, z);
  }

  /**
   * Rebuild the occupancy grid from the loaded detail levels (opts.chunks) and the obstacles of the moment: main.ts
   * calls this when a level arrives and when the build (upto) or the shown build changes, enter() does too. Without a
   * chunk there is no grid and the boxes block. The same chunks and obstacles as last time are not rebuilt.
   */
  rebuildOccupancy(): void {
    const chunks = this.opts.chunks?.() ?? [];
    if (!chunks.length) {
      this.occupancy = null;
      this.occKey = "";
      return;
    }
    const obs = this.obstacles();
    const key = `${chunks.map((c) => `${c.level}:${c.count}`).join(",")}|${obs.map((p) => p.seq).join(",")}`;
    if (key === this.occKey && this.occupancy?.built) return;
    const mask = new Uint8Array(this.meta.parts.length + 1); // by seq: one lookup per segment, never per point
    for (const p of obs) mask[p.seq] = 1;
    const occ = this.occupancy ?? new Occupancy(this.meta, CELL_U);
    occ.rebuild(
      chunks,
      (seq) => mask[seq] === 1,
      this.meta.floor_y + STEP_OVER_M / this.mpu,
      this.eyeY + HEAD_ROOM_M / this.mpu,
      this.radiusM / this.mpu,
    );
    this.occupancy = occ;
    this.occKey = key;
  }

  /** The HUD lines for the aimed part: label; kind · points · distance (· detector confidence); hint. Empty for none. */
  aimText(): string[] {
    const a = this.aimed;
    if (!a) return [];
    const p = a.part;
    let info = `${p.kind} · ${p.count.toLocaleString("en-US")} pts · ${(a.distance * this.mpu).toFixed(1)} m`;
    if (p.source) info += ` · ${p.source}${p.confidence !== undefined ? ` ${Math.round(p.confidence * 100)} %` : ""}`;
    const act = this.coarse ? "tap" : "click";
    const hint = this.opts.selected() === p.seq ? `SELECTED · ${act} · clear` : `${act} · select`;
    return [p.label, info, hint];
  }

  /** blockedAt as a predicate with the box list gathered once, for the many calls of a move or a spawn search. */
  private collider(): (x: number, z: number) => boolean {
    const occ = this.occupancy;
    if (occ?.built) return (x, z) => occ.blocked(x, z);
    const obs = this.obstacles();
    const r = this.radiusM / this.mpu;
    return (x, z) => obs.some((o) => overlaps(o, x, z, r));
  }

  /** The nearest built part on the ray through the screen centre, and its highlight box. */
  private updateAim(notify: boolean): void {
    this.ray.origin.copy(this.camera.position);
    this.forward(this.ray.direction);
    const hit = pickPart(this.ray, this.meta, this.opts.upto(), undefined, this.opts.visible);
    const aimed = hit && hit.distance <= GAZE_M / this.mpu ? hit : null;
    this.aimed = aimed;
    this.highlight.visible = !!aimed;
    let key = "";
    if (aimed) {
      const p = aimed.part;
      const selected = this.opts.selected() === p.seq;
      this.highlight.box.min.set(...p.bbox.min);
      this.highlight.box.max.set(...p.bbox.max);
      (this.highlight.material as THREE.LineBasicMaterial).color.setHex(selected ? RED : CYAN);
      key = `${p.seq}|${(aimed.distance * this.mpu).toFixed(1)}|${selected}`;
    }
    if (key === this.aimKey) return;
    this.aimKey = key;
    if (notify) this.hooks.onChange();
  }

  private selectAimed(): void {
    if (!this.aimed) return;
    this.hooks.select(this.aimed.part.seq);
    this.updateAim(true); // the highlight turns red (or cyan again) at once, not a frame later
  }

  private turnBy(dxPx: number, dyPx: number, radPerPx: number): void {
    if (!dxPx && !dyPx) return;
    this.setLook(this.yaw - dxPx * radPerPx, this.pitch - dyPx * radPerPx);
  }

  /**
   * If the spawn point is blocked, move it to the nearest spot inside the walkable area that is not: the nearest free
   * occupancy cell when the grid is built, else the nearest free spot of a 24 x 24, then a 96 x 96 grid 0.6 m in from
   * the walls. Never spawn blocked; only a room with no free spot at all leaves the point where it is (the escape rule
   * in moveBy still lets you walk out).
   */
  private clearSpot(pos: THREE.Vector3): void {
    const blocked = this.collider();
    if (!blocked(pos.x, pos.z)) return;
    const wb = this.bounds;
    const best = { x: pos.x, z: pos.z, d: Infinity };
    const consider = (x: number, z: number): void => {
      if (x < wb.minX || x > wb.maxX || z < wb.minZ || z > wb.maxZ) return;
      const d = Math.hypot(x - pos.x, z - pos.z);
      if (d >= best.d || blocked(x, z)) return;
      best.x = x;
      best.z = z;
      best.d = d;
    };
    const occ = this.occupancy;
    if (occ?.built) {
      for (let i = 0; i < occ.nx; i++) {
        for (let j = 0; j < occ.nz; j++) consider(occ.originX + (i + 0.5) * occ.cell, occ.originZ + (j + 0.5) * occ.cell);
      }
    } else {
      const b = this.meta.room_bounds;
      const margin = 0.6 / this.mpu;
      for (const steps of [24, 96]) {
        for (let i = 0; i <= steps; i++) {
          for (let j = 0; j <= steps; j++) {
            consider(
              b.min[0] + margin + ((b.max[0] - b.min[0] - 2 * margin) * i) / steps,
              b.min[2] + margin + ((b.max[2] - b.min[2] - 2 * margin) * j) / steps,
            );
          }
        }
        if (best.d < Infinity) break;
      }
    }
    pos.x = best.x;
    pos.z = best.z;
  }

  private bindKeys(): void {
    window.addEventListener("keydown", (e) => {
      // running is not a key of its own (handlesKey leaves a bare Shift to the page): noted from any key event
      if (e.shiftKey) this.held.add("shift");
      else this.held.delete("shift");
      if (!this.handlesKey(e)) return;
      e.preventDefault();
      const k = keyName(e);
      if (k === "enter") {
        if (!e.repeat) this.selectAimed();
      } else if (k === "q" || k === "e") {
        if (!e.repeat) this.setLook(this.yaw + (k === "q" ? TURN : -TURN), this.pitch);
      } else this.held.add(k);
    });
    // always: a key let go over an input must not stay held
    window.addEventListener("keyup", (e) => this.held.delete(keyName(e)));
  }

  /**
   * Mouse: a click takes pointer lock and then the mouse looks around; without the lock (refused, or a phone) a drag
   * looks. A click while locked, or a tap on a touch screen, selects the aimed part. Pointers are tracked by id, so a
   * second finger does nothing.
   */
  private bindPointer(): void {
    const c = this.canvas;
    c.addEventListener("pointerdown", (e) => {
      if (!this.active || this.press || (e.pointerType === "mouse" && e.button !== 0)) return;
      this.press = { id: e.pointerId, type: e.pointerType, x: e.clientX, y: e.clientY, lx: e.clientX, ly: e.clientY, t: performance.now(), moved: 0 };
      try {
        c.setPointerCapture(e.pointerId);
      } catch {
        // synthetic events have no pointer to capture
      }
    });
    c.addEventListener("pointermove", (e) => {
      if (!this.active) return;
      const p = this.press;
      if (this.locked) {
        if (e.pointerType !== "mouse") return;
        this.turnBy(e.movementX, e.movementY, MOUSE_RAD_PER_PX);
        if (p) p.moved += Math.hypot(e.movementX, e.movementY);
        return;
      }
      if (!p || e.pointerId !== p.id) return;
      const dx = e.clientX - p.lx;
      const dy = e.clientY - p.ly;
      p.lx = e.clientX;
      p.ly = e.clientY;
      p.moved = Math.max(p.moved, Math.hypot(e.clientX - p.x, e.clientY - p.y));
      this.turnBy(dx, dy, e.pointerType === "mouse" ? MOUSE_RAD_PER_PX : TOUCH_RAD_PER_PX);
    });
    const up = (e: PointerEvent): void => {
      const p = this.press;
      if (!p || e.pointerId !== p.id) return;
      this.press = null;
      if (!this.active || performance.now() - p.t >= TAP_MS || p.moved >= TAP_PX) return;
      // a mouse click without the lock only asks for it (the mouse should look, not select, from the first click on)
      if (p.type === "mouse" && !this.coarse && !this.locked) this.requestLock();
      else this.selectAimed();
    };
    c.addEventListener("pointerup", up);
    c.addEventListener("pointercancel", () => (this.press = null));
  }

  private requestLock(): void {
    try {
      const p: unknown = this.canvas.requestPointerLock();
      if (p instanceof Promise) p.catch(() => undefined); // refused: dragging still looks around
    } catch {
      // no pointer lock here (an old browser): dragging still looks around
    }
  }

  /** The phone's thumb stick: the knob follows the finger inside the ring; its offset is the walking speed. */
  private bindJoystick(): void {
    const stick = document.querySelector<HTMLElement>("#joystick");
    const knob = stick?.querySelector<HTMLElement>(".knob");
    if (!stick || !knob) return;
    let id: number | null = null;
    let cx = 0;
    let cy = 0;
    const move = (e: PointerEvent): void => {
      if (id === null || e.pointerId !== id) return;
      let dx = e.clientX - cx;
      let dy = e.clientY - cy;
      const m = Math.hypot(dx, dy);
      if (m > STICK_TRAVEL_PX) {
        dx *= STICK_TRAVEL_PX / m;
        dy *= STICK_TRAVEL_PX / m;
      }
      knob.style.transform = `translate(${dx.toFixed(1)}px, ${dy.toFixed(1)}px)`;
      this.setStick(dx / STICK_TRAVEL_PX, dy / STICK_TRAVEL_PX);
    };
    const end = (e: PointerEvent): void => {
      if (id === null || e.pointerId !== id) return;
      id = null;
      knob.style.transform = "";
      this.setStick(0, 0);
    };
    stick.addEventListener("pointerdown", (e) => {
      if (!this.active || id !== null) return;
      e.preventDefault();
      id = e.pointerId;
      const r = stick.getBoundingClientRect();
      cx = r.left + r.width / 2;
      cy = r.top + r.height / 2;
      try {
        stick.setPointerCapture(e.pointerId);
      } catch {
        // synthetic events have no pointer to capture
      }
      move(e);
    });
    stick.addEventListener("pointermove", move);
    stick.addEventListener("pointerup", end);
    stick.addEventListener("pointercancel", end);
    window.addEventListener("pointerup", end); // the finger came up elsewhere
  }

  /** Thumb stick offset (-1..1 each way) with the VR dead zone, so a resting thumb does not creep. */
  private setStick(x: number, y: number): void {
    const mag = Math.hypot(x, y);
    if (mag < DEADZONE) {
      this.stick.x = this.stick.y = 0;
      return;
    }
    const k = (Math.min(mag, 1) - DEADZONE) / (1 - DEADZONE) / mag;
    this.stick.x = x * k;
    this.stick.y = y * k;
  }
}

/** Whether a key event's target takes typing (the filter box, a text area, editable text): its keys are its own. */
function typingIn(t: EventTarget | null): boolean {
  if (t instanceof HTMLTextAreaElement) return true;
  if (t instanceof HTMLInputElement) return !NOT_TYPING.has(t.type);
  return t instanceof HTMLElement && t.isContentEditable;
}

/** Whether a walker of radius r at (x, z) overlaps the part's box in plan (the box grown by r on every side). */
function overlaps(p: PartMeta, x: number, z: number, r: number): boolean {
  const b = p.bbox;
  return x > b.min[0] - r && x < b.max[0] + r && z > b.min[2] - r && z < b.max[2] + r;
}
