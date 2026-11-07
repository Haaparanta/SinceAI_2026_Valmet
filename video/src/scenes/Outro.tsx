import React from "react";
import { AbsoluteFill } from "remotion";
import type { SceneProps } from "./index";
import { Backdrop, Chip, Headline, Mono, Reveal, Sub } from "../ui";
import { C, FONT } from "../theme";

const BUILT_WITH = ["Python", "numba", "YOLOE-26", "three.js", "Spark splats", "FastAPI", "Cloud Run"];

export const Outro: React.FC<SceneProps> = () => (
  <Backdrop>
    <AbsoluteFill style={{ justifyContent: "center", alignItems: "center", textAlign: "center" }}>
      <Reveal at={2}>
        <Mono size={26} style={{ letterSpacing: 4, marginBottom: 22 }}>SINCE AI 2026 × VALMET</Mono>
      </Reveal>
      <Reveal at={6}>
        <Headline size={96}>Approve-to-Build Twin</Headline>
      </Reveal>
      <Reveal at={14}>
        <Sub size={38} style={{ marginTop: 18 }}>A scanned plant room that knows what it contains.</Sub>
      </Reveal>
      <Reveal at={22}>
        <div style={{ marginTop: 44, fontFamily: FONT.mono, fontSize: 64, color: C.cyan, letterSpacing: 2, textShadow: `0 0 40px ${C.cyan}66` }}>twinbuild.click</div>
      </Reveal>
      <Reveal at={32}>
        <div style={{ display: "flex", gap: 14, marginTop: 44, flexWrap: "wrap", justifyContent: "center", maxWidth: 1300 }}>
          {BUILT_WITH.map((b, i) => (
            <Chip key={b} color={i % 2 ? C.amber : C.cyan} size={24}>{b}</Chip>
          ))}
        </div>
      </Reveal>
      <Reveal at={40}>
        <Mono size={24} color={C.muted} style={{ marginTop: 40 }}>github.com/Haaparanta/SinceAI_2026_Valmet</Mono>
      </Reveal>
    </AbsoluteFill>
  </Backdrop>
);
