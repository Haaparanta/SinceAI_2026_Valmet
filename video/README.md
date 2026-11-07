# video/ — the two-minute demo video

The hackathon demo video of the Approve-to-Build Twin: Vesa's screen recording of [twinbuild.click](https://twinbuild.click),
cut to under two minutes, narrated by an ElevenLabs voice, with burned-in captions and a few animated overlays.
Composed with [Remotion](https://www.remotion.dev) (React); everything is driven by `storyboard.json`.

```
storyboard.json          the cut: one scene per narration beat (which seconds of the recording, overlays, zooms, the words)
facts.md                 every number the narration and the submission text may use, with its source
tools/narrate.mjs        narration clips + word timings: ElevenLabs (with-timestamps API) or the macOS `say` stand-in
tools/assets.mjs         copies the storyboard's repo assets and the recording proxy into public/
tools/srt.mjs            out/a2b_demo.srt + .vtt from the same word timings as the burned-in captions
tools/transcribe.py      Whisper transcript of the raw recording's audio (what was said while recording)
tools/record.mjs …       (probe.mjs, shots.mjs) Playwright helpers for scripted recordings of the live viewer
src/                     the Remotion composition: Demo.tsx (timeline + audio), Captions.tsx, scenes/Cut.tsx (recording + overlays), scenes/Outro.tsx
public/narration/        the generated clips and manifest.json (committed, so a re-render needs no API key)
recordings/              the raw recording and its proxies (gitignored: 300 MB+)
out/                     renders (gitignored)
```

## Re-render

```bash
cd video && npm install
# 1. the recording: put the screen capture at recordings/user/screen.mp4 (2880x1800, 60 fps), then make the cropped proxy
FF=../.venv/lib/python3.12/site-packages/imageio_ffmpeg/binaries/ffmpeg-macos-aarch64-v9.0   # or any ffmpeg
$FF -i recordings/user/screen.mp4 -vf "crop=2880:1620:0:180,scale=2560:1440,fps=30" -c:v libx264 -crf 17 -pix_fmt yuv420p -an recordings/screen_crop.mp4
# 2. narration (skips clips whose text, voice and speed have not changed)
echo 'ELEVENLABS_API_KEY=sk_…' > .env            # gitignored; without it, --say uses the macOS voice as a stand-in
node tools/narrate.mjs --voice Daniel --speed 1.06
# 3. assets, captions, render
node tools/assets.mjs
node tools/srt.mjs
npx remotion render src/index.ts Demo out/a2b_demo.mp4 --codec h264 --crf 19
npx remotion studio src/index.ts                   # live preview while editing storyboard.json or the components
```

`make demo-video` from the repo root runs steps 2–3.

## How the cut works

Each scene in `storyboard.json` has a `kind` (`cut` = the recording with overlays, `outro` = the end card) and `props`:

- `shots`: `[{ "in": 58.2, "dur": 3.4, "rate": 2 }, …]` seconds into the recording; the last shot fills the scene.
- `headline`, `sub`, `brand`, `chips`, `values`, `dim`: the on-screen text for people watching without sound.
- `spot`: a glowing box in recording coordinates (1920×1080), `zoom`: a push-in keyframe, both timed in seconds.

A scene lasts `max(duration_s, narration + lead + tail)`, so changing the words re-times the cut automatically;
`tools/srt.mjs` and `Captions.tsx` page the words the same way.
