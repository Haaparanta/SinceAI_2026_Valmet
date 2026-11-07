import React from "react";
import { AbsoluteFill, OffthreadVideo, Sequence, interpolate, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import type { SceneProps } from "./index";
import { C, FONT, FPS } from "../theme";
import { Chip, Mono, Reveal, Spotlight, ease } from "../ui";

/** One stretch of the screen recording: starts `in` seconds into it; `dur` seconds (the last shot fills the scene). */
type Shot = { in: number; dur?: number; rate?: number };
type ZoomSpec = { at: number; scale: number; x: number; y: number; dur?: number; until?: number };
type SpotSpec = { x: number; y: number; w: number; h: number; label?: string; at?: number; until?: number; labelBelow?: boolean };
type ChipSpec = { color: "cyan" | "amber" | "magenta" | "green"; text: string; at?: number };
type Props = {
  shots: Shot[];
  headline?: string[];
  sub?: string;
  brand?: boolean;
  chips?: ChipSpec[];
  spot?: SpotSpec;
  zoom?: ZoomSpec;
  dim?: number;
  values?: string[];
  headAt?: { x: number; y: number };
};

/** The cropped, 30 fps proxy of the recording (tools/assets.mjs copies it into public/recordings/). */
const SRC = "recordings/screen_crop.mp4";
const COLORS: Record<ChipSpec["color"], string> = { cyan: C.cyan, amber: C.amber, magenta: C.magenta, green: C.green };
const clamp = { extrapolateLeft: "clamp" as const, extrapolateRight: "clamp" as const };

function zoomState(frame: number, zoom?: ZoomSpec): { s: number; ox: number; oy: number } {
  if (!zoom) return { s: 1, ox: 0, oy: 0 };
  const at = zoom.at * FPS;
  const dur = (zoom.dur ?? 0.8) * FPS;
  const pIn = interpolate(frame, [at, at + dur], [0, 1], { ...clamp, easing: ease });
  const pOut = zoom.until == null ? 1 : interpolate(frame, [zoom.until * FPS, zoom.until * FPS + dur], [1, 0], { ...clamp, easing: ease });
  const p = Math.min(pIn, pOut);
  const s = 1 + (zoom.scale - 1) * p;
  const vw = 1920 / s;
  const vh = 1080 / s;
  const cx = 960 + (zoom.x - 960) * p;
  const cy = 540 + (zoom.y - 540) * p;
  const ox = Math.min(Math.max(cx - vw / 2, 0), 1920 - vw);
  const oy = Math.min(Math.max(cy - vh / 2, 0), 1080 - vh);
  return { s, ox, oy };
}

/** Overlays fade out over the last 10 frames of the scene so hard cuts stay clean. */
function useOverlayOpacity(): number {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  return interpolate(frame, [durationInFrames - 10, durationInFrames - 1], [1, 0], clamp);
}

export const Cut: React.FC<SceneProps> = ({ scene }) => {
  const p = (scene.props ?? {}) as Props;
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const { s, ox, oy } = zoomState(frame, p.zoom);
  const fade = useOverlayOpacity();

  // shot ranges in frames
  const starts: number[] = [];
  const lens: number[] = [];
  let at = 0;
  p.shots.forEach((shot, i) => {
    const last = i === p.shots.length - 1;
    const len = last || shot.dur == null ? Math.max(1, durationInFrames - at) : Math.round(shot.dur * FPS);
    starts.push(at);
    lens.push(len);
    at += len;
  });

  const headSize = p.brand ? 76 : p.headline && p.headline.join(" ").length > 28 ? 46 : 54;
  return (
    <AbsoluteFill style={{ background: C.bg, overflow: "hidden" }}>
      <div style={{ position: "absolute", left: 0, top: 0, width: 1920, height: 1080, transform: `scale(${s}) translate(${-ox}px, ${-oy}px)`, transformOrigin: "0 0" }}>
        {p.shots.map((shot, i) => (
          <Sequence key={i} from={starts[i]} durationInFrames={lens[i]} name={`shot ${i} @${shot.in}s`}>
            <OffthreadVideo src={staticFile(SRC)} startFrom={Math.round(shot.in * FPS)} playbackRate={shot.rate ?? 1} muted style={{ width: 1920, height: 1080 }} />
          </Sequence>
        ))}
      </div>
      {p.dim ? <AbsoluteFill style={{ background: `rgba(11, 13, 20, ${p.dim})` }} /> : null}

      {/* spotlight and zoom work in recording coordinates: move them with the zoom */}
      {p.spot ? (
        <div style={{ position: "absolute", left: 0, top: 0, width: 1920, height: 1080, transform: `scale(${s}) translate(${-ox}px, ${-oy}px)`, transformOrigin: "0 0", opacity: fade, pointerEvents: "none" }}>
          <Spotlight x={p.spot.x} y={p.spot.y} w={p.spot.w} h={p.spot.h} label={p.spot.label} labelBelow={p.spot.labelBelow} at={Math.round((p.spot.at ?? 0.4) * FPS)} until={p.spot.until != null ? Math.round(p.spot.until * FPS) : durationInFrames - 8} />
        </div>
      ) : null}

      <AbsoluteFill style={{ opacity: fade, pointerEvents: "none" }}>
        {p.headline || p.brand ? (
          <div style={{ position: "absolute", left: p.headAt?.x ?? 36, top: p.headAt?.y ?? 100, maxWidth: 1100 }}>
            {p.brand ? (
              <Reveal at={6}>
                <Mono size={24} style={{ marginBottom: 14, letterSpacing: 3 }}>SINCE AI 2026 × VALMET</Mono>
              </Reveal>
            ) : null}
            {p.headline ? (
              <Reveal at={p.brand ? 12 : 8}>
                <div style={{ display: "inline-block", padding: p.brand ? "18px 28px" : "12px 22px", borderRadius: 16, background: "rgba(8, 10, 18, 0.72)", border: `1px solid ${C.line}`, backdropFilter: "blur(8px)", boxShadow: "0 10px 40px rgba(0,0,0,0.45)" }}>
                  {p.headline.map((line, i) => (
                    <div key={i} style={{ fontFamily: FONT.display, fontSize: headSize, fontWeight: 700, lineHeight: 1.1, letterSpacing: -1, color: i === 0 ? C.fg : C.cyan }}>{line}</div>
                  ))}
                </div>
              </Reveal>
            ) : null}
            {p.brand ? (
              <Reveal at={46}>
                <div style={{ marginTop: 18, fontFamily: FONT.display, fontSize: 34, fontWeight: 600, color: C.fg }}>
                  <span style={{ color: C.cyan, fontFamily: FONT.mono }}>a2b</span> · Approve-to-Build Twin
                </div>
              </Reveal>
            ) : null}
            {p.sub ? (
              <Reveal at={30}>
                <Mono size={24} color={C.muted} style={{ marginTop: 14 }}>{p.sub}</Mono>
              </Reveal>
            ) : null}
            {p.chips ? (
              <div style={{ display: "flex", flexDirection: "column", gap: 12, marginTop: 18, alignItems: "flex-start" }}>
                {p.chips.map((c, i) => (
                  <Reveal key={i} at={Math.round((c.at ?? 1 + i) * FPS)} dy={18}>
                    <Chip color={COLORS[c.color]} size={28}>{c.text}</Chip>
                  </Reveal>
                ))}
              </div>
            ) : null}
          </div>
        ) : null}

        {p.values ? (
          <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
            <div style={{ display: "flex", flexDirection: "column", gap: 28, marginTop: -60 }}>
              {p.values.map((v, i) => (
                <Reveal key={i} at={Math.round((0.5 + i * 1.7) * FPS)} dy={24}>
                  <div style={{ display: "flex", alignItems: "center", gap: 26 }}>
                    <div style={{ width: 54, height: 54, borderRadius: 999, background: `${C.cyan}22`, border: `2px solid ${C.cyan}`, display: "flex", alignItems: "center", justifyContent: "center", boxShadow: `0 0 24px ${C.cyan}55` }}>
                      <svg width="30" height="30" viewBox="0 0 24 24"><path d="M5 12.5l4.5 4.5L19 7.5" fill="none" stroke={C.cyan} strokeWidth="3" strokeLinecap="round" strokeLinejoin="round" /></svg>
                    </div>
                    <div style={{ fontFamily: FONT.display, fontSize: 64, fontWeight: 700, letterSpacing: -1, color: C.fg, textShadow: "0 4px 30px rgba(0,0,0,0.8)" }}>{v}</div>
                  </div>
                </Reveal>
              ))}
              <Reveal at={Math.round((0.5 + p.values.length * 1.7 + 1.2) * FPS)} dy={16}>
                <div style={{ marginTop: 18, fontFamily: FONT.mono, fontSize: 44, color: C.cyan, letterSpacing: 2, textShadow: `0 0 30px ${C.cyan}66` }}>twinbuild.click</div>
              </Reveal>
            </div>
          </AbsoluteFill>
        ) : null}
      </AbsoluteFill>
    </AbsoluteFill>
  );
};
