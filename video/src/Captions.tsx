import React from "react";
import { AbsoluteFill, useCurrentFrame } from "remotion";
import { type TimedScene, type Word } from "./data";
import { C, FONT, FPS } from "./theme";

type Page = { start: number; end: number; words: Word[] };

/** Group the words of one clip into caption pages: at most ~44 characters per line, two lines, broken at sentence ends and pauses. */
export function pages(words: Word[]): Page[] {
  const out: Page[] = [];
  let cur: Word[] = [];
  let len = 0;
  const flush = () => {
    if (!cur.length) return;
    out.push({ start: cur[0].start, end: cur[cur.length - 1].end, words: cur });
    cur = [];
    len = 0;
  };
  for (let i = 0; i < words.length; i++) {
    const w = words[i];
    const prev = words[i - 1];
    const gap = prev ? w.start - prev.end : 0;
    const endsSentence = prev ? /[.!?]$/.test(prev.text) : false;
    const tooLong = len + w.text.length + 1 > 84;
    if (cur.length && (tooLong || gap > 0.7 || (endsSentence && len > 36))) flush();
    cur.push(w);
    len += w.text.length + 1;
  }
  flush();
  // a page stays until the next page starts (no flicker between pages), but never longer than 1.2 s after its last word
  for (let i = 0; i < out.length; i++) {
    const next = out[i + 1];
    out[i].end = Math.min(next ? next.start - 0.04 : out[i].end + 1.2, out[i].end + 1.2);
  }
  return out;
}

/** Split a page's words into two balanced lines. */
function lines(words: Word[]): Word[][] {
  const text = words.map((w) => w.text).join(" ");
  if (text.length <= 44) return [words];
  let best = 1;
  let bestDiff = Infinity;
  for (let k = 1; k < words.length; k++) {
    const a = words.slice(0, k).map((w) => w.text).join(" ").length;
    const b = words.slice(k).map((w) => w.text).join(" ").length;
    const diff = Math.abs(a - b);
    if (diff < bestDiff) {
      bestDiff = diff;
      best = k;
    }
  }
  return [words.slice(0, best), words.slice(best)];
}

export const Captions: React.FC<{ scenes: TimedScene[] }> = ({ scenes }) => {
  const frame = useCurrentFrame();
  const scene = scenes.find((s) => frame >= s.from && frame < s.from + s.frames);
  if (!scene?.narration_clip) return null;
  const t = (frame - scene.from) / FPS - scene.lead; // seconds into the clip
  const page = pages(scene.narration_clip.words).find((p) => t >= p.start - 0.05 && t < p.end);
  if (!page) return null;
  const rows = lines(page.words);
  return (
    <AbsoluteFill style={{ justifyContent: "flex-end", alignItems: "center", pointerEvents: "none" }}>
      <div
        style={{
          marginBottom: 46,
          padding: "14px 30px",
          borderRadius: 14,
          background: "rgba(8, 10, 18, 0.78)",
          border: `1px solid ${C.line}`,
          boxShadow: "0 8px 32px rgba(0,0,0,0.45)",
          backdropFilter: "blur(6px)",
          fontFamily: FONT.display,
          fontSize: 38,
          lineHeight: 1.25,
          fontWeight: 600,
          color: C.fg,
          textAlign: "center",
          maxWidth: 1000,
        }}
      >
        {rows.map((row, i) => (
          <div key={i}>
            {row.map((w, j) => {
              const active = t >= w.start && t < w.end + 0.06;
              return (
                <span key={j} style={{ color: active ? C.cyan : C.fg, transition: "color 80ms" }}>
                  {w.text}
                  {j < row.length - 1 ? " " : ""}
                </span>
              );
            })}
          </div>
        ))}
      </div>
    </AbsoluteFill>
  );
};
