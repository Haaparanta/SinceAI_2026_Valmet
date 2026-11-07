"""README media: the two build videos and their GIF previews, from committed images alone (no .ply needed).

    uv run --group video python scripts/readme_media.py             # docs/media/{manual,auto}_build.{mp4,gif}
    uv run --group video python scripts/readme_media.py --gif-only  # just the GIF previews (seconds)
    make media                                                      # the same

manual_build.mp4: every step image of the Equipment Room build (images/0139 onwards; 0001-0138 belong to two archived
runs), through scripts/timelapse.py. manual_build.gif: one frame per accepted part, the "built 3D world" picture the
part's state step ends with (build/manifest.json), so the room grows part by part.
auto_build.mp4: the committed sample of the automatic build's pictures (autoscene/out/samples: close-up, room so far
and detector proof per object, in object order). auto_build.gif: the "room so far" pictures, then the finished room.
ffmpeg comes from PATH, else from the imageio-ffmpeg wheel (the `video` dependency group).
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
IMAGES = ROOT / "images"
SAMPLES = ROOT / "autoscene" / "out" / "samples"
MANIFEST = ROOT / "build" / "manifest.json"
OUT = ROOT / "docs" / "media"
FIRST_EQUIPMENT_ROOM_IMAGE = 139
ACCEPTED_PART = re.compile(r"^after (\d+) ACCEPTED \(part ")


def _timelapse():
    spec = importlib.util.spec_from_file_location("timelapse", ROOT / "scripts" / "timelapse.py")
    assert spec and spec.loader
    mod = importlib.util.module_from_spec(spec)
    sys.modules["timelapse"] = mod  # @dataclass looks its module up here
    spec.loader.exec_module(mod)
    return mod


def manual_gif_frames() -> list[Path]:
    """The last picture of the state step after each accepted part: the built room so far, one frame per part."""
    manifest = json.loads(MANIFEST.read_text())
    by_part: dict[int, Path] = {}
    for step in manifest["steps"]:
        m = ACCEPTED_PART.match(step.get("event") or "") if step.get("kind") == "state" else None
        if m and step.get("images"):
            by_part[int(m.group(1))] = ROOT / step["images"][-1]  # a later state step for the same part wins
    frames = [p for _, p in sorted(by_part.items()) if p.is_file()]
    if not frames:
        sys.exit("no state images for accepted parts in build/manifest.json")
    return frames


def auto_gif_frames() -> list[Path]:
    """The "room so far" picture (_b) of every sampled object, then the finished room."""
    frames = sorted(SAMPLES.glob("*_b.jpg")) + sorted(SAMPLES.glob("*_all_objects_textured.jpg"))
    if not frames:
        sys.exit(f"no sample pictures in {SAMPLES}")
    return frames


def write_gif(frames: list[Path], out: Path, *, seconds: float, hold_last: float, width: int, colors: int = 192) -> None:
    """One GIF from image files shown `seconds` each (the last one `hold_last`), palette-optimised by ffmpeg."""
    ffmpeg = _timelapse().ffmpeg_exe()
    out.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        lst = Path(tmp) / "frames.txt"
        lines = []
        for p in frames:
            lines.append(f"file '{p.as_posix()}'\nduration {seconds:.3f}")
        lines[-1] = f"file '{frames[-1].as_posix()}'\nduration {hold_last:.3f}"
        lines.append(f"file '{frames[-1].as_posix()}'")  # the concat demuxer needs the last file twice to honour its duration
        lst.write_text("\n".join(lines) + "\n")
        vf = (
            f"scale={width}:-2:flags=lanczos,split[a][b];"
            f"[a]palettegen=max_colors={colors}:stats_mode=diff[p];"
            "[b][p]paletteuse=dither=bayer:bayer_scale=4:diff_mode=rectangle"
        )
        cmd = [ffmpeg, "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(lst), "-vf", vf, "-loop", "0", str(out)]
        subprocess.run(cmd, check=True)
    print(f"wrote {out} ({len(frames)} frames, {out.stat().st_size / 1e6:.1f} MB)", file=sys.stderr)


def write_videos() -> None:
    tl = ROOT / "scripts" / "timelapse.py"
    # 800 px wide and 8 images per second keep the manual video (hundreds of noisy point-cloud frames) well under 20 MB
    runs = [
        [str(IMAGES), "--first", str(FIRST_EQUIPMENT_ROOM_IMAGE), "-o", str(OUT / "manual_build.mp4"),
         "--min", "60", "--max", "100", "--rate", "8", "--fps", "8", "--hold-last", "3", "--crf", "31", "--width", "800"],
        [str(SAMPLES), "--first", "1", "--last", "9999", "-o", str(OUT / "auto_build.mp4"),
         "--min", "45", "--max", "75", "--rate", "3", "--hold-last", "3", "--crf", "28", "--width", "960"],
    ]  # fmt: skip
    for args in runs:
        subprocess.run([sys.executable, str(tl), *args], check=True)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--gif-only", action="store_true", help="skip the two videos")
    ap.add_argument("--width", type=int, default=640, help="GIF width in pixels (default 640)")
    args = ap.parse_args(argv)
    OUT.mkdir(parents=True, exist_ok=True)
    write_gif(manual_gif_frames(), OUT / "manual_build.gif", seconds=0.6, hold_last=2.5, width=args.width)
    # the automatic frames are dense point clouds: a smaller, 128-colour GIF keeps the preview around 4 MB
    write_gif(auto_gif_frames(), OUT / "auto_build.gif", seconds=0.3, hold_last=2.5, width=min(args.width, 512), colors=128)
    if not args.gif_only:
        write_videos()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
