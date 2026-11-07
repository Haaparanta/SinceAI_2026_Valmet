/**
 * WebXR walk-through for Meta Quest 3 (AGENTS.md S3): stand in the scanned room at real-world scale.
 *
 * - Room-scale: the session uses a `local-floor` reference space, so the headset's real height and every physical step
 *   carry straight into the room. One metre walked is one metre in the scan (scene units scaled by metres-per-unit).
 * - Spawn: on an open patch of floor away from equipment, facing the selected part (or the biggest piece of equipment).
 * - Left stick: smooth walk where you look. Right stick: 30° snap turn around your head.
 * - Trigger (or pinch with hand tracking): teleport arc to the floor.
 * - Point at equipment or a pipe: its box lights up and a label floats at the spot. Squeeze (grip): select / deselect it.
 * - A / X: cycle Scan, Model, Overlay. B / Y: part boxes on/off. Left stick click: back to the spawn point.
 * - Right stick click: switch between the point cloud and Gaussian splats.
 *
 * Nothing here downloads at runtime (no controller-profile CDN): controllers are drawn as simple rays, hands as spheres,
 * so the demo also runs with Wi-Fi off.
 */
import * as THREE from "three";
import { XRHandModelFactory } from "three/addons/webxr/XRHandModelFactory.js";
import { pickPart, type PartMeta, type SceneMeta } from "./scene";

export interface XrHooks {
  /** called when the session starts / ends (after the rig is placed / restored) */
  onStart(): void;
  onEnd(): void;
  /** A / X button */
  cycleSource(): void;
  /** B / Y button */
  toggleBoxes(): void;
  /** right stick click: points <-> Gaussian splats */
  toggleRender(): void;
  /** squeeze while pointing at a part: select it, or clear the selection if it already is */
  select(seq: number): void;
  /** two short lines for the wrist panel: what is on screen */
  status(): [string, string];
}

export interface XrOptions {
  metresPerUnit: number;
  /** look at this part on entry (the selected one); falls back to the biggest equipment */
  focus?: () => PartMeta | undefined;
  /** parts 1..upto are built (pointable); defaults to all */
  upto?: () => number;
}

const UP = new THREE.Vector3(0, 1, 0);
const WALK_MPS = 1.4; // comfortable walking speed, metres per second
const TURN = Math.PI / 6; // snap-turn step
const DEADZONE = 0.18;
const HEAD_CLEARANCE_M = 2.0; // anything lower than this over the floor is an obstacle for the spawn point
const CYAN = 0x00e5ff;
const RED = 0xff2d55;
const RAY_IDLE_M = 1.5; // pointer length when it hits nothing

interface Pad {
  source: XRInputSource;
  pressed: boolean[];
  turnLatch: boolean;
}

/** Whether this browser can open an immersive VR session at all (false on http:// over the LAN, see README). */
export async function vrSupported(): Promise<boolean> {
  try {
    return (await navigator.xr?.isSessionSupported("immersive-vr")) ?? false;
  } catch {
    return false;
  }
}

export class XrWalk {
  readonly rig = new THREE.Group();
  presenting = false;
  private readonly renderer: THREE.WebGLRenderer;
  private readonly camera: THREE.PerspectiveCamera;
  private readonly meta: SceneMeta;
  private readonly hooks: XrHooks;
  private readonly opts: XrOptions;
  private readonly mpu: number;
  private readonly floorY: number;
  private saved: { pos: THREE.Vector3; quat: THREE.Quaternion; fov: number; near: number; far: number } | null = null;
  private spawn = { pos: new THREE.Vector3(), yaw: 0 };
  private pads = new Map<XRInputSource, Pad>();
  private aiming: THREE.XRTargetRaySpace | null = null;
  private arc: THREE.Line;
  private arcPos: Float32Array;
  private marker: THREE.Group;
  private target = new THREE.Vector3();
  private targetOk = false;
  private panel: THREE.Mesh;
  private panelCtx: CanvasRenderingContext2D;
  private panelTex: THREE.CanvasTexture;
  private panelText = "";
  private eyeHeightPx = 0;
  private controllers: { space: THREE.XRTargetRaySpace; source: XRInputSource | null; hover: PartMeta | null }[] = [];
  private hoverBox: THREE.Box3Helper;
  private label: THREE.Mesh;
  private labelCtx: CanvasRenderingContext2D;
  private labelTex: THREE.CanvasTexture;
  private labelText = "";

  constructor(
    renderer: THREE.WebGLRenderer,
    scene: THREE.Scene,
    camera: THREE.PerspectiveCamera,
    meta: SceneMeta,
    hooks: XrHooks,
    opts: XrOptions,
  ) {
    this.renderer = renderer;
    this.camera = camera;
    this.meta = meta;
    this.hooks = hooks;
    this.opts = opts;
    this.mpu = opts.metresPerUnit;
    this.floorY = meta.floor_y;

    renderer.xr.enabled = true;
    renderer.xr.setReferenceSpaceType("local-floor");
    renderer.xr.setFoveation(1); // fixed foveation: the periphery is drawn at lower resolution, a large win on Quest
    scene.add(this.rig);
    this.rig.add(camera);

    // teleport arc + landing ring (world units: these live in the scene, not the rig)
    const N = 40;
    this.arcPos = new Float32Array(N * 3);
    const arcGeo = new THREE.BufferGeometry();
    arcGeo.setAttribute("position", new THREE.BufferAttribute(this.arcPos, 3));
    this.arc = new THREE.Line(arcGeo, new THREE.LineBasicMaterial({ color: CYAN, transparent: true, opacity: 0.9 }));
    this.arc.frustumCulled = false;
    this.arc.visible = false;
    this.arc.renderOrder = 20;
    scene.add(this.arc);
    this.marker = this.makeMarker();
    scene.add(this.marker);

    // wrist panel (rig-local, so in metres)
    const canvas = document.createElement("canvas");
    canvas.width = 768;
    canvas.height = 288;
    this.panelCtx = canvas.getContext("2d")!;
    this.panelTex = new THREE.CanvasTexture(canvas);
    this.panelTex.colorSpace = THREE.SRGBColorSpace;
    this.panel = new THREE.Mesh(
      new THREE.PlaneGeometry(0.2, 0.075),
      new THREE.MeshBasicMaterial({ map: this.panelTex, transparent: true, depthTest: false }),
    );
    this.panel.renderOrder = 30;
    this.panel.position.set(0, 0.07, 0.03);
    this.panel.rotation.x = -0.75;

    // pointed-at part: highlight box + floating label (world units, scaled per frame by distance)
    this.hoverBox = new THREE.Box3Helper(new THREE.Box3(), new THREE.Color(CYAN));
    this.hoverBox.visible = false;
    this.hoverBox.renderOrder = 25;
    scene.add(this.hoverBox);
    const lc = document.createElement("canvas");
    lc.width = 768;
    lc.height = 240;
    this.labelCtx = lc.getContext("2d")!;
    this.labelTex = new THREE.CanvasTexture(lc);
    this.labelTex.colorSpace = THREE.SRGBColorSpace;
    this.label = new THREE.Mesh(
      new THREE.PlaneGeometry(1, 240 / 768),
      new THREE.MeshBasicMaterial({ map: this.labelTex, transparent: true, depthTest: false }),
    );
    this.label.renderOrder = 31;
    this.label.visible = false;
    scene.add(this.label);

    const hands = new XRHandModelFactory();
    for (let i = 0; i < 2; i++) {
      const c = renderer.xr.getController(i);
      const slot = { space: c, source: null as XRInputSource | null, hover: null as PartMeta | null };
      this.controllers.push(slot);
      c.add(this.makePointer());
      c.addEventListener("connected", (e) => {
        const src = (e as unknown as { data: XRInputSource }).data;
        slot.source = src;
        c.children[0].visible = !src.hand; // hands show the sphere model instead of a stick
        if (src.handedness === "left") c.add(this.panel);
      });
      c.addEventListener("disconnected", () => {
        slot.source = null;
        slot.hover = null;
        if (this.panel.parent === c) c.remove(this.panel);
        if (this.aiming === c) this.endAim(false);
      });
      c.addEventListener("squeezestart", () => slot.hover && this.hooks.select(slot.hover.seq));
      c.addEventListener("selectstart", () => (this.aiming = c));
      c.addEventListener("selectend", () => this.aiming === c && this.endAim(true));
      this.rig.add(c);
      const hand = renderer.xr.getHand(i);
      hand.add(hands.createHandModel(hand, "spheres"));
      this.rig.add(hand);
    }

    renderer.xr.addEventListener("sessionstart", () => this.start());
    renderer.xr.addEventListener("sessionend", () => this.end());
  }

  /** Toggle an immersive session (the Enter VR button). */
  async toggle(): Promise<void> {
    const current = this.renderer.xr.getSession();
    if (current) {
      await current.end();
      return;
    }
    const session = await navigator.xr!.requestSession("immersive-vr", {
      requiredFeatures: ["local-floor"],
      optionalFeatures: ["bounded-floor", "hand-tracking"],
    });
    await this.renderer.xr.setSession(session);
  }

  private start(): void {
    this.saved = {
      pos: this.camera.position.clone(),
      quat: this.camera.quaternion.clone(),
      fov: this.camera.fov,
      near: this.camera.near,
      far: this.camera.far,
    };
    this.presenting = true;
    this.eyeHeightPx = 0;
    this.camera.near = 0.05; // metres: the camera is rig-local in XR
    this.camera.far = 100;
    this.chooseSpawn();
    this.goToSpawn();
    this.hooks.onStart();
  }

  private end(): void {
    this.presenting = false;
    this.endAim(false);
    this.pads.clear();
    this.hoverBox.visible = this.label.visible = false;
    this.rig.position.set(0, 0, 0);
    this.rig.rotation.set(0, 0, 0);
    this.rig.scale.setScalar(1);
    this.rig.updateMatrixWorld(true);
    if (this.saved) {
      this.camera.position.copy(this.saved.pos);
      this.camera.quaternion.copy(this.saved.quat);
      this.camera.scale.setScalar(1);
      this.camera.fov = this.saved.fov;
      this.camera.near = this.saved.near;
      this.camera.far = this.saved.far;
      this.camera.zoom = 1;
      this.camera.updateProjectionMatrix();
    }
    this.hooks.onEnd();
  }

  /** Open floor, away from anything below head height, not hugging a wall; prefers the middle of the room. */
  private chooseSpawn(): void {
    const b = this.meta.room_bounds;
    const head = this.floorY + HEAD_CLEARANCE_M / this.mpu;
    const obstacles = this.meta.parts.filter((p) => p.kind !== "structure" && p.bbox.min[1] < head);
    const cx = (b.min[0] + b.max[0]) / 2;
    const cz = (b.min[2] + b.max[2]) / 2;
    const margin = 0.6 / this.mpu;
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
        const score = Math.min(clear, 1.5 / this.mpu) - 0.2 * Math.hypot(x - cx, z - cz);
        if (score > best.score) best = { x, z, score };
      }
    }
    const focus = this.opts.focus?.() ?? this.biggestEquipment();
    const fx = focus ? (focus.bbox.min[0] + focus.bbox.max[0]) / 2 : cx;
    const fz = focus ? (focus.bbox.min[2] + focus.bbox.max[2]) / 2 : b.min[2];
    const dx = fx - best.x;
    const dz = fz - best.z;
    this.spawn.pos.set(best.x, this.floorY, best.z);
    // rig yaw so that the headset's initial forward (-z) looks at the focus
    this.spawn.yaw = Math.hypot(dx, dz) > 1e-3 ? Math.atan2(-dx, -dz) : 0;
  }

  private biggestEquipment(): PartMeta | undefined {
    let best: PartMeta | undefined;
    for (const p of this.meta.parts) if (p.kind === "equipment" && (!best || p.count > best.count)) best = p;
    return best;
  }

  private goToSpawn(): void {
    this.rig.position.copy(this.spawn.pos);
    this.rig.rotation.set(0, this.spawn.yaw, 0);
    this.rig.scale.setScalar(1 / this.mpu); // rig-local units are metres, the room is in scene units
    this.rig.updateMatrixWorld(true);
  }

  private headWorld(out: THREE.Vector3): THREE.Vector3 {
    return out.setFromMatrixPosition(this.renderer.xr.getCamera().matrixWorld);
  }

  /** Per frame while presenting: thumbsticks, buttons, teleport aim, panel, point size. */
  update(dt: number): void {
    if (!this.presenting) return;
    const session = this.renderer.xr.getSession();
    if (!session) return;
    const seen = new Set<XRInputSource>();
    for (const source of session.inputSources) {
      seen.add(source);
      const gp = source.gamepad;
      if (!gp) continue;
      let pad = this.pads.get(source);
      if (!pad) {
        pad = { source, pressed: [], turnLatch: false };
        this.pads.set(source, pad);
      }
      const ax = gp.axes.length >= 4 ? [gp.axes[2], gp.axes[3]] : [gp.axes[0] ?? 0, gp.axes[1] ?? 0];
      const edge = (i: number): boolean => {
        const now = !!gp.buttons[i]?.pressed;
        const was = !!pad!.pressed[i];
        pad!.pressed[i] = now;
        return now && !was;
      };
      if (source.handedness === "left") {
        this.walk(ax[0], ax[1], dt);
        if (edge(3)) this.goToSpawn();
      } else if (source.handedness === "right") {
        if (edge(3)) this.hooks.toggleRender();
        if (Math.abs(ax[0]) > 0.7 && !pad.turnLatch) {
          this.turn(-Math.sign(ax[0]) * TURN);
          pad.turnLatch = true;
        } else if (Math.abs(ax[0]) < 0.3) pad.turnLatch = false;
      }
      if (edge(4)) this.hooks.cycleSource();
      if (edge(5)) this.hooks.toggleBoxes();
    }
    for (const s of [...this.pads.keys()]) if (!seen.has(s)) this.pads.delete(s);
    this.updateAim();
    this.updateHover();
    this.drawPanel();
  }

  /** Eye-buffer height in pixels for the point-size shader (0 until the first XR frame). */
  eyeHeight(): number {
    const cams = this.renderer.xr.getCamera().cameras;
    const h = cams.length ? cams[0].viewport.w : 0;
    if (h > 0) this.eyeHeightPx = h;
    return this.eyeHeightPx;
  }

  private walk(x: number, y: number, dt: number): void {
    const mag = Math.hypot(x, y);
    if (mag < DEADZONE) return;
    const k = ((mag - DEADZONE) / (1 - DEADZONE)) * (1 / mag);
    // read matrixWorld directly: getWorldDirection() would rebuild the XR camera's matrix without the rig
    const fwd = new THREE.Vector3(0, 0, -1).transformDirection(this.renderer.xr.getCamera().matrixWorld);
    fwd.y = 0;
    if (fwd.lengthSq() < 1e-6) return;
    fwd.normalize();
    const right = new THREE.Vector3().crossVectors(fwd, UP);
    const step = (WALK_MPS / this.mpu) * dt;
    const move = fwd.multiplyScalar(-y * k * step).addScaledVector(right, x * k * step);
    this.rig.position.add(move);
    this.keepHeadInRoom();
  }

  private turn(angle: number): void {
    const head = this.headWorld(new THREE.Vector3());
    this.rig.position.sub(head).applyAxisAngle(UP, angle).add(head);
    this.rig.rotation.y += angle;
    this.rig.updateMatrixWorld(true);
  }

  /** Stick walking and teleports stop at the walls (your real legs can still take you anywhere). */
  private keepHeadInRoom(): void {
    this.rig.updateMatrixWorld(true);
    const head = this.headWorld(new THREE.Vector3());
    const b = this.meta.room_bounds;
    const m = 0.25 / this.mpu;
    const x = THREE.MathUtils.clamp(head.x, b.min[0] + m, b.max[0] - m);
    const z = THREE.MathUtils.clamp(head.z, b.min[2] + m, b.max[2] - m);
    this.rig.position.x += x - head.x;
    this.rig.position.z += z - head.z;
    this.rig.updateMatrixWorld(true);
  }

  private updateAim(): void {
    const c = this.aiming;
    this.arc.visible = this.marker.visible = false;
    this.targetOk = false;
    if (!c) return;
    const o = new THREE.Vector3().setFromMatrixPosition(c.matrixWorld);
    const dir = new THREE.Vector3(0, 0, -1).transformDirection(c.matrixWorld);
    const v = dir.multiplyScalar(7 / this.mpu); // launch speed, m/s -> u/s
    const g = 9.8 / this.mpu;
    const h = o.y - this.floorY;
    const t = (v.y + Math.sqrt(Math.max(0, v.y * v.y + 2 * g * h))) / g;
    const n = this.arcPos.length / 3;
    for (let i = 0; i < n; i++) {
      const s = (t * i) / (n - 1);
      this.arcPos[i * 3] = o.x + v.x * s;
      this.arcPos[i * 3 + 1] = o.y + v.y * s - 0.5 * g * s * s;
      this.arcPos[i * 3 + 2] = o.z + v.z * s;
    }
    this.arc.geometry.attributes.position.needsUpdate = true;
    this.target.set(o.x + v.x * t, this.floorY, o.z + v.z * t);
    const b = this.meta.room_bounds;
    const m = 0.25 / this.mpu;
    this.targetOk =
      this.target.x > b.min[0] + m && this.target.x < b.max[0] - m && this.target.z > b.min[2] + m && this.target.z < b.max[2] - m;
    const colour = this.targetOk ? CYAN : RED;
    (this.arc.material as THREE.LineBasicMaterial).color.setHex(colour);
    this.marker.position.copy(this.target).setY(this.floorY + 0.01);
    this.marker.scale.setScalar(1 / this.mpu);
    for (const ch of this.marker.children) ((ch as THREE.Mesh).material as THREE.MeshBasicMaterial).color.setHex(colour);
    this.arc.visible = true;
    this.marker.visible = true;
  }

  /** Each controller ray picks the nearest built part; the right hand's pick wins for the highlight and label. */
  private updateHover(): void {
    const upto = this.opts.upto?.() ?? this.meta.parts.length;
    const ray = new THREE.Ray();
    let shown: { part: PartMeta; point: THREE.Vector3; distance: number } | null = null;
    let shownRight = false;
    for (const slot of this.controllers) {
      const c = slot.space;
      const pointer = c.children[0];
      slot.hover = null;
      if (!slot.source || this.aiming === c) {
        this.setPointer(pointer, RAY_IDLE_M, false);
        continue;
      }
      ray.origin.setFromMatrixPosition(c.matrixWorld);
      ray.direction.set(0, 0, -1).transformDirection(c.matrixWorld);
      const hit = pickPart(ray, this.meta, upto);
      const maxU = 12 / this.mpu; // only within a dozen metres
      if (hit && hit.distance < maxU) {
        slot.hover = hit.part;
        this.setPointer(pointer, hit.distance * this.mpu, true);
        const right = slot.source.handedness === "right";
        if (!shown || (right && !shownRight)) {
          shown = hit;
          shownRight = right;
        }
      } else this.setPointer(pointer, RAY_IDLE_M, false);
    }
    this.hoverBox.visible = this.label.visible = !!shown;
    if (!shown) return;
    const p = shown.part;
    this.hoverBox.box.min.set(...p.bbox.min);
    this.hoverBox.box.max.set(...p.bbox.max);
    (this.hoverBox.material as THREE.LineBasicMaterial).color.setHex(this.opts.focus?.()?.seq === p.seq ? RED : CYAN);
    // label just above the pointed-at spot, turned to face you, sized to stay readable with distance
    const head = this.headWorld(new THREE.Vector3());
    const metres = shown.distance * this.mpu;
    const width = THREE.MathUtils.clamp(metres * 0.3, 0.3, 1.8) / this.mpu; // ~17° wide at any distance
    this.label.scale.setScalar(width);
    this.label.position.copy(shown.point).addScaledVector(UP, 0.09 / this.mpu + width * 0.2);
    this.label.lookAt(head.x, this.label.position.y, head.z);
    this.drawLabel(p);
  }

  private setPointer(pointer: THREE.Object3D, metres: number, hit: boolean): void {
    const [ray, tip] = pointer.children;
    ray.scale.z = metres / 0.12;
    tip.position.z = -metres;
    tip.visible = hit;
    ((ray as THREE.Line).material as THREE.LineBasicMaterial).opacity = hit ? 1 : 0.35;
  }

  private drawLabel(p: PartMeta): void {
    const selected = this.opts.focus?.()?.seq === p.seq;
    const text = `${p.seq}|${selected}`;
    if (text === this.labelText) return;
    this.labelText = text;
    const ctx = this.labelCtx;
    const { width: W, height: H } = ctx.canvas;
    ctx.clearRect(0, 0, W, H);
    ctx.fillStyle = "rgba(14, 18, 32, 0.9)";
    ctx.strokeStyle = selected ? "#ff2d55" : "rgba(0, 229, 255, 0.8)";
    ctx.lineWidth = 5;
    ctx.beginPath();
    ctx.roundRect(4, 4, W - 8, H - 8, 32);
    ctx.fill();
    ctx.stroke();
    ctx.fillStyle = "#e6e8f0";
    ctx.font = "600 64px system-ui, sans-serif";
    ctx.fillText(p.label, 40, 92);
    ctx.fillStyle = "#9aa0b4";
    ctx.font = "34px ui-monospace, monospace";
    ctx.fillText(`${p.kind} · ${p.count.toLocaleString("en-US")} pts`, 40, 148);
    ctx.fillStyle = selected ? "#ff2d55" : "#00e5ff";
    ctx.font = "600 30px system-ui, sans-serif";
    ctx.fillText(selected ? "SELECTED · squeeze to clear" : "squeeze to select", 40, 202);
    this.labelTex.needsUpdate = true;
  }

  private endAim(go: boolean): void {
    if (go && this.targetOk) {
      const head = this.headWorld(new THREE.Vector3());
      this.rig.position.x += this.target.x - head.x;
      this.rig.position.z += this.target.z - head.z;
      this.rig.updateMatrixWorld(true);
    }
    this.aiming = null;
    this.arc.visible = this.marker.visible = false;
  }

  private drawPanel(): void {
    if (!this.panel.parent) return;
    const [a, b] = this.hooks.status();
    const text = `${a}\n${b}`;
    if (text === this.panelText) return;
    this.panelText = text;
    const ctx = this.panelCtx;
    const { width: W, height: H } = ctx.canvas;
    ctx.clearRect(0, 0, W, H);
    ctx.fillStyle = "rgba(14, 18, 32, 0.88)";
    ctx.strokeStyle = "rgba(0, 229, 255, 0.7)";
    ctx.lineWidth = 4;
    ctx.beginPath();
    ctx.roundRect(4, 4, W - 8, H - 8, 28);
    ctx.fill();
    ctx.stroke();
    ctx.fillStyle = "#00e5ff";
    ctx.font = "600 30px ui-monospace, monospace";
    ctx.fillText("a2b · EQUIPMENT ROOM", 36, 62);
    ctx.fillStyle = "#e6e8f0";
    ctx.font = "600 52px system-ui, sans-serif";
    ctx.fillText(a, 36, 136);
    ctx.fillStyle = "#9aa0b4";
    ctx.font = "30px system-ui, sans-serif";
    ctx.fillText(b, 36, 192);
    ctx.fillText("trigger teleport · grip select · A/X view · R-click splats", 36, 246);
    this.panelTex.needsUpdate = true;
  }

  private makePointer(): THREE.Group {
    const g = new THREE.Group();
    const ray = new THREE.Line(
      new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(0, 0, 0), new THREE.Vector3(0, 0, -0.12)]),
      new THREE.LineBasicMaterial({ color: CYAN, transparent: true, opacity: 0.35 }),
    );
    const tip = new THREE.Mesh(new THREE.SphereGeometry(0.006, 12, 8), new THREE.MeshBasicMaterial({ color: CYAN }));
    tip.position.z = -0.12;
    const body = new THREE.Mesh(
      new THREE.CylinderGeometry(0.012, 0.016, 0.09, 16).rotateX(Math.PI / 2).translate(0, 0, 0.045),
      new THREE.MeshBasicMaterial({ color: 0x2a3350 }),
    );
    g.add(ray, tip, body);
    return g;
  }

  private makeMarker(): THREE.Group {
    const g = new THREE.Group();
    const mat = () => new THREE.MeshBasicMaterial({ color: CYAN, transparent: true, opacity: 0.85, side: THREE.DoubleSide });
    const ring = new THREE.Mesh(new THREE.RingGeometry(0.22, 0.27, 48).rotateX(-Math.PI / 2), mat());
    const dot = new THREE.Mesh(new THREE.CircleGeometry(0.05, 24).rotateX(-Math.PI / 2), mat());
    g.add(ring, dot);
    g.visible = false;
    g.renderOrder = 21;
    return g;
  }
}
