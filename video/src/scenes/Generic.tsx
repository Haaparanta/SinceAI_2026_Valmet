import React from "react";
import { AbsoluteFill } from "remotion";
import type { SceneProps } from "./index";
import { Backdrop, FadeOut, Headline, KenBurns, Media, Mono, Reveal, Sub, asset } from "../ui";
import { C } from "../theme";

/** Fallback layout: the first asset as backdrop, the on-screen lines revealed one by one. */
export const Generic: React.FC<SceneProps> = ({ scene }) => {
  const bg = scene.assets.find((a) => /\.(png|jpe?g|gif|mp4|webm)$/i.test(a));
  const [head, ...rest] = scene.on_screen_text;
  return (
    <FadeOut>
      <Backdrop>
        {bg ? (/\.(png|jpe?g)$/i.test(bg) ? <KenBurns src={asset(bg)} opacity={0.35} /> : <AbsoluteFill style={{ opacity: 0.35 }}><Media src={bg} /></AbsoluteFill>) : null}
        <AbsoluteFill style={{ padding: "120px 140px", justifyContent: "center" }}>
          <Reveal at={4}>
            <Mono style={{ marginBottom: 24 }}>{scene.title.toUpperCase()}</Mono>
          </Reveal>
          <Reveal at={8}>
            <Headline style={{ maxWidth: 1400 }}>{head}</Headline>
          </Reveal>
          {rest.map((line, i) => (
            <Reveal key={i} at={24 + i * 14}>
              <Sub style={{ marginTop: i === 0 ? 36 : 14, color: i === 0 ? C.fg : C.muted }}>{line}</Sub>
            </Reveal>
          ))}
        </AbsoluteFill>
      </Backdrop>
    </FadeOut>
  );
};
