import React from "react";
import { AbsoluteFill, Audio, Sequence, staticFile } from "remotion";
import { loadFont as loadDisplay } from "@remotion/google-fonts/SpaceGrotesk";
import { loadFont as loadMono } from "@remotion/google-fonts/JetBrainsMono";
import { Captions } from "./Captions";
import { timeline } from "./data";
import { sceneComponent } from "./scenes";
import { C, FPS } from "./theme";

loadDisplay("normal", { weights: ["500", "600", "700"], subsets: ["latin"] });
loadMono("normal", { weights: ["500", "700"], subsets: ["latin"] });

export const Demo: React.FC = () => {
  const { scenes } = timeline();
  return (
    <AbsoluteFill style={{ background: C.bg, color: C.fg }}>
      {scenes.map((s) => {
        const Comp = sceneComponent(s);
        return (
          <Sequence key={s.id} from={s.from} durationInFrames={s.frames} name={s.id}>
            <Comp scene={s} />
            {s.narration_clip ? (
              <Sequence from={Math.round(s.lead * FPS)} name={`${s.id} voice`}>
                <Audio src={staticFile(s.narration_clip.file)} volume={1.7} />
              </Sequence>
            ) : null}
          </Sequence>
        );
      })}
      <Captions scenes={scenes} />
    </AbsoluteFill>
  );
};
