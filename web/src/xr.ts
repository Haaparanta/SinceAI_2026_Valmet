/**
 * WebXR walk-through of the build for Meta Quest 3 (AGENTS.md S3, research/04 §3.6 and §4).
 *
 * - `local-floor` reference space; the camera lives in a rig placed on the scan floor (floor_y), so the headset floor
 *   is the room floor. You start where the desktop camera was looking, facing the same way.
 * - Left stick: walk (head-relative, clamped to the room). Right stick left/right: 30° snap turn around the head.
 * - Trigger: select the part the controller ray points at (box pick; walls/floor/ceiling only when nothing else is hit).
 *   Trigger on the selected part again clears it.
 * - A: next source (Scan / Model / Overlay / Wireframe). B: clear selection.
 * - X / Y: replay the build one part back / forward. Left stick press: cutaway on/off.
 * - A small panel on the left controller shows the mode, build step and selection (DOM HUDs do not render in VR).
 *
 * Budget (research/04 §4.7): pixel ratio 1, foveation 1, framebuffer scale 1, at most `xrpool` scan points (default
 * 300 k; the parts are always drawn in full), point size x `xrsize` (default 0.8). URL: ?xrpool=200000&xrsize=0.7.
 * Units: scene units are taken as metres; ?xrscale=<scene units per metre> rescales the room around you.
 * Dev only: ?xremu=1 installs Meta's emulated Quest 3 (iwer) so the session can be tested on a laptop.
 */
import * as THREE from "three";
import { SOURCES, type BuildCloud, type SceneMeta, type ViewState } from "./scene";

const MOVE_SPEED = 1.4; // m/s
const SNAP = Math.PI / 6;
const RAY_LENGTH = 6;
const Y = new THREE.Vector3(0, 1, 0);

export interface XRHost {
  renderer: THREE.WebGLRenderer;
  camera: THREE.PerspectiveCamera;
  /** the camera's parent; moved for locomotion (never move the XR camera itself) */
  rig: THREE.Group;
  cloud: BuildCloud;
  meta: SceneMeta;
  getState(): ViewState;
  setState(patch: Partial<ViewState>): void;
  /** where the desktop view was looking: the XR start point and direction */
  startPose(): { target: THREE.Vector3; forward: THREE.Vector3 };
  toggleCut(): void;
  onStart(): void;
  onEnd(): void;
}

interface Hand {
  controller: THREE.Group;
  ray: THREE.Line;
  handedness?: XRHandedness;
  gamepad?: Gamepad;
  pressed: boolean[];
  snapReady: boolean;
}

export type XRStatus = { ok: true } | { ok: false; reason: string };

/** Installs the emulated Quest 3 when ?xremu is set (dev builds only; tree-shaken from production). */
async function maybeEmulate(): Promise<void> {
  if (!import.meta.env.DEV || !new URLSearchParams(location.search).has("xremu")) return;
  const { XRDevice, metaQuest3 } = await import("iwer");
  const device = new XRDevice(metaQuest3);
  device.installRuntime({ forceInstall: true });
  Object.assign(window, { __xrdevice: device });
}

export async function xrStatus(): Promise<XRStatus> {
  await maybeEmulate();
  if (!window.isSecureContext) {
    return { ok: false, reason: "WebXR needs a secure page: open via https:// (npm run dev:quest) or localhost (adb reverse)" };
  }
  if (!navigator.xr) return { ok: false, reason: "this browser has no WebXR (use Meta Quest Browser)" };
  try {
    if (await navigator.xr.isSessionSupported("immersive-vr")) return { ok: true };
  } catch {
    /* fall through */
  }
  return { ok: false, reason: "no VR headset available to this browser" };
}

export class XRWalk {
  private host: XRHost;
  private hands: Hand[] = [];
  private raycaster = new THREE.Raycaster();
  private panel: THREE.Mesh<THREE.PlaneGeometry, THREE.MeshBasicMaterial>;
  private panelCtx: CanvasRenderingContext2D;
  private hovered = 0;
  private saved?: { position: THREE.Vector3; quaternion: THREE.Quaternion; sizeScale: number; poolBudget: number };
  private readonly params = new URLSearchParams(location.search);
  readonly poolBudget = Number(this.params.get("xrpool") ?? 300_000);
  readonly sizeScale = Number(this.params.get("xrsize") ?? 0.8);
  readonly unitsPerMetre = Number(this.params.get("xrscale") ?? 1);

  constructor(host: XRHost) {
    this.host = host;
    const { renderer, rig } = host;
    renderer.xr.enabled = true;
    renderer.xr.setReferenceSpaceType("local-floor");
    renderer.xr.setFramebufferScaleFactor(1);
    renderer.xr.setFoveation(1);

    for (let i = 0; i < 2; i++) {
      const controller = renderer.xr.getController(i);
      const geom = new THREE.BufferGeometry().setFromPoints([new THREE.Vector3(0, 0, 0), new THREE.Vector3(0, 0, -1)]);
      const ray = new THREE.Line(geom, new THREE.LineBasicMaterial({ color: 0x9de2f0, transparent: true, opacity: 0.8 }));
      ray.scale.z = RAY_LENGTH;
      controller.add(ray);
      const hand: Hand = { controller, ray, pressed: [], snapReady: true };
      controller.addEventListener("connected", (e) => {
        const src = (e as unknown as { data: XRInputSource }).data;
        hand.handedness = src.handedness;
        hand.gamepad = src.gamepad ?? undefined;
        ray.visible = src.targetRayMode === "tracked-pointer";
        if (src.handedness === "left") controller.add(this.panel);
      });
      controller.addEventListener("disconnected", () => {
        hand.handedness = undefined;
        hand.gamepad = undefined;
      });
      controller.addEventListener("select", () => this.pick(hand));
      rig.add(controller);
      this.hands.push(hand);
    }

    // wrist panel: a canvas texture on the left controller
    const canvas = document.createElement("canvas");
    canvas.width = 512;
    canvas.height = 256;
    this.panelCtx = canvas.getContext("2d")!;
    const tex = new THREE.CanvasTexture(canvas);
    tex.colorSpace = THREE.SRGBColorSpace;
    this.panel = new THREE.Mesh(
      new THREE.PlaneGeometry(0.16, 0.08),
      new THREE.MeshBasicMaterial({ map: tex, transparent: true, depthTest: false }),
    );
    this.panel.position.set(0, 0.06, -0.02);
    this.panel.rotation.x = -Math.PI / 4;
    this.panel.renderOrder = 100;

    renderer.xr.addEventListener("sessionstart", () => this.onStart());
    renderer.xr.addEventListener("sessionend", () => this.onEnd());
  }

  async enter(): Promise<void> {
    const session = await navigator.xr!.requestSession("immersive-vr", {
      optionalFeatures: ["local-floor", "bounded-floor", "hand-tracking", "layers"],
    });
    await this.host.renderer.xr.setSession(session);
  }

  get presenting(): boolean {
    return this.host.renderer.xr.isPresenting;
  }

  private onStart(): void {
    const { camera, rig, cloud, meta, renderer } = this.host;
    this.saved = {
      position: camera.position.clone(),
      quaternion: camera.quaternion.clone(),
      sizeScale: cloud.sizeScale,
      poolBudget: cloud.poolBudget,
    };
    // Stand on the scan floor under the point the desktop view was looking at, facing the same way.
    const { target, forward } = this.host.startPose();
    const b = meta.room_bounds;
    rig.position.set(
      THREE.MathUtils.clamp(target.x, b.min[0] + 0.3, b.max[0] - 0.3),
      meta.floor_y,
      THREE.MathUtils.clamp(target.z, b.min[2] + 0.3, b.max[2] - 0.3),
    );
    rig.rotation.set(0, Math.atan2(-forward.x, -forward.z), 0);
    rig.scale.setScalar(this.unitsPerMetre);
    camera.position.set(0, 0, 0);
    camera.quaternion.identity();
    cloud.sizeScale = this.sizeScale;
    cloud.poolBudget = this.poolBudget;
    // point size needs the per-eye height in pixels: the XR layer's height (eyes sit side by side or in an array)
    const layer = renderer.xr.getBaseLayer() as (XRWebGLLayer & { textureHeight?: number }) | null;
    const eyeHeight = layer?.textureHeight ?? layer?.framebufferHeight ?? renderer.getDrawingBufferSize(new THREE.Vector2()).y;
    cloud.setViewportHeight(eyeHeight);
    this.host.onStart();
    this.refreshPanel();
  }

  private onEnd(): void {
    const { camera, rig, cloud } = this.host;
    rig.position.set(0, 0, 0);
    rig.rotation.set(0, 0, 0);
    rig.scale.setScalar(1);
    if (this.saved) {
      camera.position.copy(this.saved.position);
      camera.quaternion.copy(this.saved.quaternion);
      cloud.sizeScale = this.saved.sizeScale;
      cloud.poolBudget = this.saved.poolBudget;
    }
    this.host.onEnd();
  }

  /**
   * Head pose in world space. three copies the XR pose into our camera, whose parent is the rig, so its world matrix
   * includes the locomotion. (Do not call getWorldDirection() on renderer.xr.getCamera(): that recomputes the XR
   * camera's matrix without the rig.)
   */
  private head(): { position: THREE.Vector3; forward: THREE.Vector3 } {
    const cam = this.host.camera;
    cam.updateWorldMatrix(true, false);
    return {
      position: new THREE.Vector3().setFromMatrixPosition(cam.matrixWorld),
      forward: new THREE.Vector3(0, 0, -1).transformDirection(cam.matrixWorld),
    };
  }

  /** Per-frame input while presenting. */
  update(dt: number): void {
    for (const hand of this.hands) {
      const pad = hand.gamepad;
      if (!pad || !hand.handedness) continue;
      const [, , sx = 0, sy = 0] = pad.axes;
      if (hand.handedness === "left") {
        if (Math.hypot(sx, sy) > 0.15) this.move(sx, sy, dt);
      } else if (hand.handedness === "right") {
        if (Math.abs(sx) > 0.7 && hand.snapReady) {
          this.turn(-Math.sign(sx) * SNAP);
          hand.snapReady = false;
        }
        if (Math.abs(sx) < 0.3) hand.snapReady = true;
      }
      this.buttons(hand, pad);
    }
    this.hover();
  }

  private move(sx: number, sy: number, dt: number): void {
    const { rig, meta } = this.host;
    const { position: head, forward } = this.head();
    const fwd = forward.setY(0);
    if (fwd.lengthSq() < 1e-6) return;
    fwd.normalize();
    const right = new THREE.Vector3(-fwd.z, 0, fwd.x);
    const step = fwd.multiplyScalar(-sy).add(right.multiplyScalar(sx)).multiplyScalar(MOVE_SPEED * this.unitsPerMetre * dt);
    // keep the head inside the room (no collision grid yet: walls and objects can be walked through)
    const b = meta.room_bounds;
    const nx = head.x + step.x;
    const nz = head.z + step.z;
    if (nx > b.min[0] && nx < b.max[0]) rig.position.x += step.x;
    if (nz > b.min[2] && nz < b.max[2]) rig.position.z += step.z;
  }

  /** Rotate the rig about the vertical axis through the head, so the user turns in place. */
  private turn(angle: number): void {
    const { rig } = this.host;
    const head = this.head().position;
    const offset = rig.position.clone().sub(head).applyAxisAngle(Y, angle);
    rig.position.copy(head).add(offset);
    rig.rotateY(angle);
  }

  private buttons(hand: Hand, pad: Gamepad): void {
    const edge = (i: number): boolean => {
      const down = !!pad.buttons[i]?.pressed;
      const was = hand.pressed[i] ?? false;
      hand.pressed[i] = down;
      return down && !was;
    };
    const { setState, getState, meta } = this.host;
    const s = getState();
    if (hand.handedness === "right") {
      if (edge(4)) setState({ source: SOURCES[(SOURCES.indexOf(s.source) + 1) % SOURCES.length] }); // A
      if (edge(5)) setState({ selected: 0 }); // B
    } else {
      if (edge(4)) setState({ upto: Math.max(0, s.upto - 1) }); // X
      if (edge(5)) setState({ upto: Math.min(meta.parts.length, s.upto + 1) }); // Y
      if (edge(3)) this.host.toggleCut(); // stick press
    }
    this.refreshPanel();
  }

  /** The part a controller ray points at: nearest entry into a built part's box; structure parts only as a fallback. */
  private hit(hand: Hand): { seq: number; dist: number } | undefined {
    const { cloud, getState, meta } = this.host;
    this.raycaster.setFromXRController(hand.controller as unknown as THREE.XRTargetRaySpace);
    const ray = this.raycaster.ray;
    const upto = getState().upto;
    let best: { seq: number; dist: number; structure: boolean } | undefined;
    const p = new THREE.Vector3();
    cloud.partBoxes.forEach((box, i) => {
      if (i + 1 > upto || box.containsPoint(ray.origin) || !ray.intersectBox(box, p)) return;
      const dist = p.distanceTo(ray.origin);
      const structure = meta.parts[i].kind === "structure";
      if (!best || (best.structure && !structure) || (best.structure === structure && dist < best.dist)) {
        best = { seq: i + 1, dist, structure };
      }
    });
    return best;
  }

  private hover(): void {
    let hovered = 0;
    for (const hand of this.hands) {
      if (!hand.handedness || !hand.ray.visible) continue;
      const h = this.hit(hand);
      // the ray is a child of the (scaled) rig: convert the world distance back to rig units
      hand.ray.scale.z = (h ? h.dist : RAY_LENGTH) / this.unitsPerMetre;
      (hand.ray.material as THREE.LineBasicMaterial).color.set(h ? 0xff2d55 : 0x9de2f0);
      if (hand.handedness === "right" && h) hovered = h.seq;
    }
    if (hovered !== this.hovered) {
      this.hovered = hovered;
      this.refreshPanel();
    }
  }

  private pick(hand: Hand): void {
    const h = this.hit(hand);
    const s = this.host.getState();
    if (!h) return;
    this.host.setState({ selected: h.seq === s.selected ? 0 : h.seq });
    this.refreshPanel();
  }

  private lastPanel = "";
  refreshPanel(): void {
    if (!this.presenting) return;
    const { meta, cloud } = this.host;
    const s = this.host.getState();
    const sel = meta.parts[s.selected - 1];
    const hov = meta.parts[this.hovered - 1];
    const lines = [
      `${s.source.toUpperCase()} · ${s.style === "redgrey" ? "RED/GREY" : "TRUE COLOUR"}`,
      `built ${s.upto}/${meta.parts.length}${s.upto ? ` · ${meta.parts[s.upto - 1].label}` : ""}`,
      sel ? `selected: ${sel.label} (${sel.count.toLocaleString("en-US")})` : "trigger: select a part",
      hov && hov !== sel ? `pointing at: ${hov.label}` : `${(cloud.drawnCount() / 1000).toFixed(0)} k points drawn`,
      "A mode · B clear · X/Y build · stick: walk/turn",
    ];
    const key = lines.join("|");
    if (key === this.lastPanel) return;
    this.lastPanel = key;
    const ctx = this.panelCtx;
    ctx.clearRect(0, 0, 512, 256);
    ctx.fillStyle = "rgba(11,13,20,0.88)";
    ctx.beginPath();
    ctx.roundRect(4, 4, 504, 248, 18);
    ctx.fill();
    ctx.strokeStyle = sel ? "#ff2d55" : "#00e5ff";
    ctx.lineWidth = 4;
    ctx.stroke();
    lines.forEach((t, i) => {
      ctx.fillStyle = i === 0 ? "#00e5ff" : i === 4 ? "#9aa0b4" : "#e6e8f0";
      ctx.font = `${i === 0 ? 600 : 400} ${i === 4 ? 22 : 28}px ui-monospace, Menlo, monospace`;
      ctx.fillText(t, 22, 50 + i * 46, 468);
    });
    this.panel.material.map!.needsUpdate = true;
  }
}
