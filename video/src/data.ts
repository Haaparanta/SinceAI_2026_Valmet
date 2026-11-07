import storyboard from "../storyboard.json";
import manifest from "../public/narration/manifest.json";
import { FPS } from "./theme";

export type Word = { text: string; start: number; end: number };
export type Scene = {
  id: string;
  title: string;
  kind?: string;
  start_s: number;
  duration_s: number;
  visual: string;
  assets: string[];
  on_screen_text: string[];
  animation: string;
  narration: string;
  /** scene-specific knobs (set in storyboard.json) */
  props?: Record<string, unknown>;
};
export type Narration = { file: string; duration: number; text: string; words: Word[] };
export type TimedScene = Scene & { index: number; from: number; frames: number; lead: number; narration_clip?: Narration };

/** Default silence after the narration before the next scene, and before it starts (seconds); props.lead / props.tail override. */
const TAIL_S = 0.7;
const LEAD_S = 0.3;

const clips = (manifest as { scenes: Record<string, Narration> }).scenes;

export function timeline(): { scenes: TimedScene[]; total: number } {
  let from = 0;
  const scenes = (storyboard as { scenes: Scene[] }).scenes.map((s, index) => {
    const clip = clips[s.id];
    const lead = typeof s.props?.lead === "number" ? (s.props.lead as number) : LEAD_S;
    const tail = typeof s.props?.tail === "number" ? (s.props.tail as number) : TAIL_S;
    const seconds = Math.max(s.duration_s, clip ? clip.duration + lead + tail : 0);
    const frames = Math.round(seconds * FPS);
    const t: TimedScene = { ...s, index, from, frames, lead, narration_clip: clip };
    from += frames;
    return t;
  });
  return { scenes, total: from };
}

export const story = storyboard as { title: string; scenes: Scene[] };
