import type React from "react";
import type { TimedScene } from "../data";
import { Generic } from "./Generic";
import { Cut } from "./Cut";
import { Outro } from "./Outro";

export type SceneProps = { scene: TimedScene };
/** scene.kind → component; anything unknown renders the Generic layout */
const registry: Record<string, React.FC<SceneProps>> = { cut: Cut, outro: Outro, generic: Generic };

export function sceneComponent(s: TimedScene): React.FC<SceneProps> {
  return registry[s.kind ?? ""] ?? registry[s.id] ?? Generic;
}
