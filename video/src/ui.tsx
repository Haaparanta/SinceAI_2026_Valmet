import React from "react";
import { AbsoluteFill, Easing, Img, OffthreadVideo, interpolate, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { Gif } from "@remotion/gif";
import { C, FONT } from "./theme";

export const ease = Easing.bezier(0.2, 0.8, 0.2, 1);
export const asset = (repoPath: string): string => staticFile(`assets/${repoPath}`);

/** 0 → 1 over [at, at + dur] frames of the current sequence, eased and clamped. */
export function useProgress(at: number, dur: number): number {
  const frame = useCurrentFrame();
  return interpolate(frame, [at, at + dur], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: ease });
}

/** Fades the children in (and up) `at` frames into the sequence. */
export const Reveal: React.FC<{ at?: number; dur?: number; dy?: number; style?: React.CSSProperties; children: React.ReactNode }> = ({ at = 0, dur = 16, dy = 28, style, children }) => {
  const p = useProgress(at, dur);
  return <div style={{ opacity: p, transform: `translateY(${(1 - p) * dy}px)`, ...style }}>{children}</div>;
};

/** Fades the children out over the last `dur` frames of the sequence. */
export const FadeOut: React.FC<{ dur?: number; children: React.ReactNode }> = ({ dur = 12, children }) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const o = interpolate(frame, [durationInFrames - dur, durationInFrames - 1], [1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  return <AbsoluteFill style={{ opacity: o }}>{children}</AbsoluteFill>;
};

export const Headline: React.FC<{ size?: number; color?: string; weight?: number; style?: React.CSSProperties; children: React.ReactNode }> = ({ size = 88, color = C.fg, weight = 700, style, children }) => (
  <div style={{ fontFamily: FONT.display, fontSize: size, fontWeight: weight, lineHeight: 1.06, letterSpacing: -1.5, color, ...style }}>{children}</div>
);

export const Sub: React.FC<{ size?: number; color?: string; style?: React.CSSProperties; children: React.ReactNode }> = ({ size = 40, color = C.muted, style, children }) => (
  <div style={{ fontFamily: FONT.display, fontSize: size, fontWeight: 500, lineHeight: 1.3, color, ...style }}>{children}</div>
);

export const Mono: React.FC<{ size?: number; color?: string; style?: React.CSSProperties; children: React.ReactNode }> = ({ size = 26, color = C.cyan, style, children }) => (
  <div style={{ fontFamily: FONT.mono, fontSize: size, letterSpacing: 1, color, ...style }}>{children}</div>
);

/** A small label with a coloured dot, as in the viewer's build panel. */
export const Chip: React.FC<{ color?: string; size?: number; style?: React.CSSProperties; children: React.ReactNode }> = ({ color = C.cyan, size = 26, style, children }) => (
  <span style={{ display: "inline-flex", alignItems: "center", gap: 12, padding: "8px 18px", borderRadius: 999, border: `1px solid ${color}55`, background: `${color}14`, fontFamily: FONT.mono, fontSize: size, color, ...style }}>
    <span style={{ width: size * 0.42, height: size * 0.42, borderRadius: 999, background: color, boxShadow: `0 0 12px ${color}` }} />
    {children}
  </span>
);

/** Counts from 0 to `to`, formatted with thousands separators. */
export const Counter: React.FC<{ to: number; at?: number; dur?: number; size?: number; color?: string; prefix?: string; suffix?: string; style?: React.CSSProperties }> = ({ to, at = 0, dur = 40, size = 150, color = C.cyan, prefix = "", suffix = "", style }) => {
  const p = useProgress(at, dur);
  const n = Math.round(to * p);
  return (
    <div style={{ fontFamily: FONT.display, fontSize: size, fontWeight: 700, letterSpacing: -3, lineHeight: 1, color, fontVariantNumeric: "tabular-nums", ...style }}>
      {prefix}
      {n.toLocaleString("en-US")}
      {suffix}
    </div>
  );
};

/** Slow zoom and drift over a still image, over the whole sequence. */
export const KenBurns: React.FC<{ src: string; from?: number; to?: number; dx?: number; dy?: number; opacity?: number; style?: React.CSSProperties; fit?: "cover" | "contain" }> = ({ src, from = 1.0, to = 1.12, dx = 0, dy = 0, opacity = 1, style, fit = "cover" }) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();
  const p = interpolate(frame, [0, durationInFrames], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const s = from + (to - from) * p;
  return (
    <AbsoluteFill style={{ overflow: "hidden", ...style }}>
      <Img src={src} style={{ width: "100%", height: "100%", objectFit: fit, opacity, transform: `scale(${s}) translate(${dx * p}px, ${dy * p}px)` }} />
    </AbsoluteFill>
  );
};

/** The dark grid-and-vignette backdrop of the title scenes. */
export const Backdrop: React.FC<{ children?: React.ReactNode }> = ({ children }) => (
  <AbsoluteFill style={{ background: `radial-gradient(1200px 700px at 30% 20%, #151a2e 0%, ${C.bg} 60%)` }}>
    <AbsoluteFill
      style={{
        backgroundImage: `linear-gradient(${C.line} 1px, transparent 1px), linear-gradient(90deg, ${C.line} 1px, transparent 1px)`,
        backgroundSize: "96px 96px",
        opacity: 0.35,
        maskImage: "radial-gradient(900px 600px at 50% 40%, black 30%, transparent 100%)",
      }}
    />
    {children}
  </AbsoluteFill>
);

/** A framed "window" around a picture or clip, with a mono title bar. */
export const Frame: React.FC<{ title?: string; width: number; height: number; style?: React.CSSProperties; children: React.ReactNode; accent?: string }> = ({ title, width, height, style, children, accent = C.cyan }) => (
  <div style={{ width, display: "flex", flexDirection: "column", borderRadius: 16, overflow: "hidden", border: `1px solid ${accent}44`, boxShadow: `0 20px 60px rgba(0,0,0,0.55), 0 0 0 1px rgba(255,255,255,0.03)`, background: C.panel, ...style }}>
    {title ? (
      <div style={{ height: 44, display: "flex", alignItems: "center", gap: 10, padding: "0 16px", background: "#0e1120", borderBottom: `1px solid ${accent}33`, fontFamily: FONT.mono, fontSize: 20, color: accent, letterSpacing: 1 }}>
        <span style={{ width: 10, height: 10, borderRadius: 99, background: accent, boxShadow: `0 0 10px ${accent}` }} />
        {title}
      </div>
    ) : null}
    <div style={{ width, height, position: "relative", overflow: "hidden", background: "#000" }}>{children}</div>
  </div>
);

/** A still, a GIF or an MP4 from the repo, filling its box. */
export const Media: React.FC<{ src: string; fit?: "cover" | "contain"; startFrom?: number; muted?: boolean; playbackRate?: number; style?: React.CSSProperties }> = ({ src, fit = "cover", startFrom = 0, playbackRate = 1, style }) => {
  const url = asset(src);
  const common: React.CSSProperties = { width: "100%", height: "100%", objectFit: fit, ...style };
  if (/\.(mp4|webm|mov)$/i.test(src)) return <OffthreadVideo src={url} startFrom={startFrom} playbackRate={playbackRate} muted style={common} />;
  if (/\.gif$/i.test(src)) return <Gif src={url} fit={fit} width={1920} height={1080} style={common} />;
  return <Img src={url} style={common} />;
};

export type Zoom = { at: number; dur?: number; scale: number; x: number; y: number };
/**
 * The screen recording with zoom keyframes: each keyframe zooms (scale) on a point (x, y in 1920×1080 pixels of the
 * recording) `at` frames into the sequence, easing over `dur` frames; the picture holds until the next keyframe.
 */
export const ZoomVideo: React.FC<{ src: string; startFrom?: number; zooms?: Zoom[]; playbackRate?: number }> = ({ src, startFrom = 0, zooms = [], playbackRate = 1 }) => {
  const frame = useCurrentFrame();
  const keys = [{ at: -1, dur: 1, scale: 1, x: 960, y: 540 }, ...zooms].sort((a, b) => a.at - b.at);
  let cur = keys[0];
  let next: Zoom | undefined;
  for (let i = 0; i < keys.length; i++) {
    if (frame >= keys[i].at) {
      cur = keys[i];
      next = undefined;
    } else {
      next = keys[i];
      break;
    }
  }
  // ease from the previous key to the current one
  const prev = keys[Math.max(0, keys.indexOf(cur) - 1)];
  const p = interpolate(frame, [cur.at, cur.at + (cur.dur ?? 20)], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: ease });
  const s = prev.scale + (cur.scale - prev.scale) * p;
  const cx = prev.x + (cur.x - prev.x) * p;
  const cy = prev.y + (cur.y - prev.y) * p;
  void next;
  // keep the zoom window inside the picture
  const vw = 1920 / s;
  const vh = 1080 / s;
  const ox = Math.min(Math.max(cx - vw / 2, 0), 1920 - vw);
  const oy = Math.min(Math.max(cy - vh / 2, 0), 1080 - vh);
  return (
    <AbsoluteFill style={{ overflow: "hidden", background: "#000" }}>
      <div style={{ position: "absolute", left: 0, top: 0, width: 1920, height: 1080, transform: `scale(${s}) translate(${-ox}px, ${-oy}px)`, transformOrigin: "0 0" }}>
        <OffthreadVideo src={src} startFrom={startFrom} playbackRate={playbackRate} muted style={{ width: 1920, height: 1080 }} />
      </div>
    </AbsoluteFill>
  );
};

/** A glowing rectangle that draws attention to a region of the screen (recording coordinates, before any zoom). */
export const Spotlight: React.FC<{ x: number; y: number; w: number; h: number; at?: number; until?: number; color?: string; label?: string; labelBelow?: boolean }> = ({ x, y, w, h, at = 0, until = 1e9, color = C.cyan, label, labelBelow = false }) => {
  const frame = useCurrentFrame();
  const p = interpolate(frame, [at, at + 12, until - 10, until], [0, 1, 1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  if (p <= 0) return null;
  return (
    <div style={{ position: "absolute", left: x, top: y, width: w, height: h, border: `3px solid ${color}`, borderRadius: 12, boxShadow: `0 0 0 4px ${color}33, 0 0 30px ${color}66`, opacity: p, pointerEvents: "none" }}>
      {label ? (
        <div style={{ position: "absolute", left: -3, top: labelBelow ? h + 10 : -46, padding: "6px 14px", borderRadius: 8, background: color, color: "#0b0d14", fontFamily: FONT.mono, fontSize: 24, fontWeight: 700, whiteSpace: "nowrap" }}>{label}</div>
      ) : null}
    </div>
  );
};

/** Side label in the corner: what the user is doing / what the pipeline did. */
export const Callout: React.FC<{ at?: number; until?: number; x?: number; y?: number; color?: string; title: string; text?: string; width?: number }> = ({ at = 0, until = 1e9, x = 60, y = 120, color = C.cyan, title, text, width = 560 }) => {
  const frame = useCurrentFrame();
  const p = interpolate(frame, [at, at + 14, until - 10, until], [0, 1, 1, 0], { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: ease });
  if (p <= 0) return null;
  return (
    <div style={{ position: "absolute", left: x, top: y, width, opacity: p, transform: `translateY(${(1 - p) * 16}px)`, padding: "18px 24px", borderRadius: 14, background: "rgba(10, 12, 22, 0.86)", border: `1px solid ${color}66`, boxShadow: `0 10px 40px rgba(0,0,0,0.5)`, backdropFilter: "blur(8px)" }}>
      <div style={{ fontFamily: FONT.mono, fontSize: 22, letterSpacing: 2, color, marginBottom: text ? 8 : 0 }}>{title}</div>
      {text ? <div style={{ fontFamily: FONT.display, fontSize: 30, fontWeight: 600, color: C.fg, lineHeight: 1.25 }}>{text}</div> : null}
    </div>
  );
};
