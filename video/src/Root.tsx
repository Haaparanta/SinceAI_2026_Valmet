import React from "react";
import { Composition } from "remotion";
import { Demo } from "./Demo";
import { timeline } from "./data";
import { FPS, H, W } from "./theme";

export const Root: React.FC = () => {
  const { total } = timeline();
  return <Composition id="Demo" component={Demo} durationInFrames={Math.max(total, FPS)} fps={FPS} width={W} height={H} />;
};
