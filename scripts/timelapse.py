"""Turn the numbered step images (images/NNNN_YYYYMMDD-HHMMSS.png) into one timelapse video (PRD S7).

    uv run --group video python scripts/timelapse.py                      # equipment-room images -> docs/timelapse.mp4
    uv run --group video python scripts/timelapse.py path/to/images -o out.mp4 --min 30 --max 60
    uv run --group video python scripts/timelapse.py --first 7 --last 354 --hold-last 3

Default input is the equipment-room worktree's images/ (.claude/worktrees/pli-cleanup-3d-viz-1dda2f), which has
the newest step images; without that worktree it falls back to this checkout's images/.

Timing: every image is shown the same time; the total is N / --rate seconds, clamped to [--min, --max].
More images than fit at --fps frames per second are thinned out evenly (first and last always kept).
Images of another size are letterboxed onto the first image's size. ffmpeg comes from PATH, else from the
imageio-ffmpeg wheel (the `video` dependency group), so no Homebrew install is needed.
"""

from __future__ import annotations

import argparse
import math
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}
INDEX_RE = re.compile(r"^(\d+)")
# Default input: the equipment-room build worktree, which has the newest images (more than the committed images/).
EQUIPMENT_ROOM_WORKTREE = "pli-cleanup-3d-viz-1dda2f"


@dataclass(frozen=True)
class Plan:
    images: list[Path]  # images that make it into the video, in order
    frames: list[int]  # output frames per image (same length as images)
    fps: int

    @property
    def seconds(self) -> float:
        return sum(self.frames) / self.fps


def image_index(path: Path) -> int | None:
    m = INDEX_RE.match(path.name)
    return int(m.group(1)) if m else None


def default_images() -> Path:
    """The equipment-room worktree's images/ when it exists on this machine, else this checkout's images/."""
    try:
        git_dir = subprocess.run(
            ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
            cwd=ROOT, capture_output=True, text=True, check=True,
        ).stdout.strip()  # fmt: skip
    except (OSError, subprocess.CalledProcessError):
        return ROOT / "images"
    candidate = Path(git_dir).parent / ".claude" / "worktrees" / EQUIPMENT_ROOM_WORKTREE / "images"
    return candidate if candidate.is_dir() else ROOT / "images"


def collect(folder: Path, first: int | None = None, last: int | None = None) -> list[Path]:
    """Image files in name order (NNNN_ prefix sorts numerically), optionally limited to an index range."""
    files = sorted(p for p in folder.iterdir() if p.is_file() and p.suffix.lower() in IMAGE_EXTS)
    out = []
    for p in files:
        idx = image_index(p)
        if first is not None and (idx is None or idx < first):
            continue
        if last is not None and (idx is None or idx > last):
            continue
        out.append(p)
    return out


def plan(images: list[Path], *, min_s: float, max_s: float, rate: float, fps: int, hold_last: float = 0.0) -> Plan:
    """Pick which images to show and for how many frames, so the video lasts between min_s and max_s seconds."""
    if not images:
        raise ValueError("no images to put in the video")
    if not 0 < min_s <= max_s:
        raise ValueError(f"need 0 < --min <= --max, got {min_s} and {max_s}")
    if rate <= 0 or fps <= 0:
        raise ValueError("--rate and --fps must be positive")
    if not 0 <= hold_last < min_s:
        raise ValueError("--hold-last must be between 0 and --min")

    total = min(max(len(images) / rate, min_s), max_s)
    # whole frames; never round up past max_s (e.g. --max 59.99 at 30 fps is 1799 frames, not 1800)
    total_frames = min(round(total * fps), math.floor(max_s * fps + 1e-9))
    hold_frames = round(hold_last * fps)
    body_frames = total_frames - hold_frames

    # at least one frame per image: thin out evenly when there are more images than frames
    if len(images) > body_frames:
        step = (len(images) - 1) / (body_frames - 1) if body_frames > 1 else 0
        picked = sorted({round(i * step) for i in range(body_frames)})
        images = [images[i] for i in picked]

    # spread body_frames as evenly as possible (the first `extra` images get one frame more)
    base, extra = divmod(body_frames, len(images))
    frames = [base + (1 if i < extra else 0) for i in range(len(images))]
    frames[-1] += hold_frames
    return Plan(images=images, frames=frames, fps=fps)


def ffmpeg_exe() -> str:
    exe = shutil.which("ffmpeg")
    if exe:
        return exe
    try:
        import imageio_ffmpeg
    except ImportError:
        sys.exit("ffmpeg not found: run with `uv run --group video ...` (imageio-ffmpeg) or `brew install ffmpeg`")
    return imageio_ffmpeg.get_ffmpeg_exe()


def fit(img: Image.Image, size: tuple[int, int]) -> Image.Image:
    """RGB image of exactly `size`, letterboxed on black when the aspect ratio differs."""
    img = img.convert("RGB")
    if img.size == size:
        return img
    scale = min(size[0] / img.width, size[1] / img.height)
    resized = img.resize((max(1, round(img.width * scale)), max(1, round(img.height * scale))), Image.LANCZOS)
    canvas = Image.new("RGB", size)
    canvas.paste(resized, ((size[0] - resized.width) // 2, (size[1] - resized.height) // 2))
    return canvas


def probe(path: Path) -> tuple[int, float]:
    """(frames, seconds) of an encoded video, by decoding it: the real length, not the planned one."""
    r = subprocess.run(
        [ffmpeg_exe(), "-hide_banner", "-i", str(path), "-map", "0:v:0", "-f", "null", "-"],
        check=False, capture_output=True, text=True,
    )  # fmt: skip
    frames = re.findall(r"frame=\s*(\d+)", r.stderr)
    times = re.findall(r"time=(\d+):(\d+):([\d.]+)", r.stderr)
    if r.returncode != 0 or not frames or not times:
        raise RuntimeError(f"could not read back {path}: {r.stderr[-300:]}")
    h, m, sec = times[-1]
    return int(frames[-1]), int(h) * 3600 + int(m) * 60 + float(sec)


def render(p: Plan, out: Path, *, crf: int = 26) -> None:
    with Image.open(p.images[0]) as first:
        w, h = first.size
    size = (w - w % 2, h - h % 2)  # yuv420p needs even dimensions
    out.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        ffmpeg_exe(), "-y", "-loglevel", "error",
        "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{size[0]}x{size[1]}", "-r", str(p.fps), "-i", "-",
        "-c:v", "libx264", "-preset", "medium", "-crf", str(crf), "-pix_fmt", "yuv420p",
        "-movflags", "+faststart", str(out),
    ]  # fmt: skip
    proc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    assert proc.stdin is not None
    try:
        for i, (path, n) in enumerate(zip(p.images, p.frames, strict=True), 1):
            with Image.open(path) as img:
                raw = fit(img, size).tobytes()
            for _ in range(n):
                proc.stdin.write(raw)
            if i % 50 == 0 or i == len(p.images):
                print(f"  {i}/{len(p.images)} images", file=sys.stderr)
    finally:
        proc.stdin.close()
        code = proc.wait()
    if code != 0:
        sys.exit(f"ffmpeg failed with exit code {code}")


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument(
        "images", nargs="?", type=Path,
        help=f"folder of images (default: the {EQUIPMENT_ROOM_WORKTREE} worktree's images/ if present, else images/)",
    )  # fmt: skip
    ap.add_argument("-o", "--out", type=Path, default=ROOT / "docs" / "timelapse.mp4", help="output .mp4")
    ap.add_argument("--min", dest="min_s", type=float, default=30.0, help="shortest video in seconds (default 30)")
    ap.add_argument("--max", dest="max_s", type=float, default=60.0, help="longest video in seconds (default 60)")
    ap.add_argument("--rate", type=float, default=6.0, help="preferred images per second before clamping (default 6)")
    ap.add_argument("--fps", type=int, default=30, help="video frame rate (default 30)")
    ap.add_argument("--hold-last", type=float, default=2.0, help="extra seconds on the last image (default 2)")
    ap.add_argument("--first", type=int, help="first image index to include (NNNN prefix)")
    ap.add_argument("--last", type=int, help="last image index to include (NNNN prefix)")
    ap.add_argument("--crf", type=int, default=26, help="x264 quality, lower is better (default 26)")
    ap.add_argument("--dry-run", action="store_true", help="print the plan, write nothing")
    args = ap.parse_args(argv)

    if args.images is None:
        args.images = default_images()
    print(f"images from {args.images}", file=sys.stderr)
    if not args.images.is_dir():
        sys.exit(f"not a folder: {args.images}")
    images = collect(args.images, args.first, args.last)
    try:
        p = plan(images, min_s=args.min_s, max_s=args.max_s, rate=args.rate, fps=args.fps, hold_last=args.hold_last)
    except ValueError as e:
        sys.exit(str(e))

    shown = sum(p.frames[:-1]) / len(p.frames[:-1]) / p.fps if len(p.frames) > 1 else p.seconds
    print(
        f"{len(images)} images found, {len(p.images)} used ({p.images[0].name} .. {p.images[-1].name}); "
        f"{shown:.2f} s each, video {p.seconds:.1f} s at {p.fps} fps -> {args.out}",
        file=sys.stderr,
    )
    if args.dry_run:
        return 0
    render(p, args.out, crf=args.crf)
    frames, decoded_s = probe(args.out)
    seconds = frames / p.fps
    print(
        f"wrote {args.out} ({args.out.stat().st_size / 1e6:.1f} MB, {frames} frames = {seconds:.2f} s, decoder clock {decoded_s:.2f} s)",
        file=sys.stderr,
    )
    if frames != sum(p.frames) or not args.min_s - 1 / p.fps < seconds <= args.max_s or decoded_s > args.max_s:
        sys.exit(
            f"length check FAILED: {seconds:.2f} s, planned {p.seconds:.2f} s, allowed {args.min_s}-{args.max_s} s"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
