"""Turn the numbered step images (images/NNNN_YYYYMMDD-HHMMSS.png) into one timelapse video (PRD S7).

    uv run --group video python scripts/timelapse.py                      # equipment-room images -> docs/timelapse.mp4
    uv run --group video python scripts/timelapse.py path/to/images -o out.mp4 --min 30 --max 60
    uv run --group video python scripts/timelapse.py --first 7 --last 354 --title "Boiler room" --subtitle "Day 1"
    uv run --group video python scripts/timelapse.py --plain              # just the images, no cards or effects

Default input is the equipment-room worktree's images/ (.claude/worktrees/pli-cleanup-3d-viz-1dda2f), which has
the newest step images; without that worktree it falls back to this checkout's images/.

The video: a title card over a blurred view of the finished room (fades in from black) -> every image in order with
short crossfades and a progress bar along the bottom edge -> the last image held -> an end card with the step count
and the time range (fades out to black). --plain turns all of that off.

Timing: the whole video, cards included, lasts N / --rate seconds clamped to [--min, --max]; after encoding it is
decoded back and the run fails if the length is off. Images that do not fit at --fps frames per second are thinned
out evenly (first and last always kept). Images of another size are letterboxed onto the first image's size.
ffmpeg comes from PATH, else from the imageio-ffmpeg wheel (the `video` dependency group).
"""

from __future__ import annotations

import argparse
import math
import re
import shutil
import subprocess
import sys
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = Path(__file__).resolve().parents[1]
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp"}
INDEX_RE = re.compile(r"^(\d+)")
STAMP_RE = re.compile(r"_(\d{8}-\d{6})")
# Default input: the equipment-room build worktree, which has the newest images (more than the committed images/).
EQUIPMENT_ROOM_WORKTREE = "pli-cleanup-3d-viz-1dda2f"

# Look: matches the step images (navy background, the blue STATE badge).
BG = (9, 12, 20)
ACCENT = (90, 160, 255)
TRACK = (28, 35, 51)
TEXT = (240, 243, 248)
MUTED = (150, 160, 178)
FONT_FILES = ["/System/Library/Fonts/HelveticaNeue.ttc", "DejaVuSans.ttf"]
FONT_INDEX = {"bold": 1, "light": 7, "medium": 10}  # faces inside HelveticaNeue.ttc


@dataclass(frozen=True)
class Plan:
    images: list[Path]  # images that make it into the video, in order
    frames: list[int]  # output frames per image (same length as images; the last one includes the hold)
    fps: int
    intro: int = 0  # title card frames
    outro: int = 0  # end card frames

    @property
    def total_frames(self) -> int:
        return self.intro + sum(self.frames) + self.outro

    @property
    def seconds(self) -> float:
        return self.total_frames / self.fps


@dataclass(frozen=True)
class Style:
    title: str = "Approve-to-Build Twin"
    subtitle: str = "Equipment room, built from a 3D scan one part at a time"
    xfade_s: float = 0.25  # crossfade between images (max a quarter of an image's frames)
    progress: bool = True  # progress bar along the bottom edge
    found: int = 0  # images found before thinning, for the end card


def image_index(path: Path) -> int | None:
    m = INDEX_RE.match(path.name)
    return int(m.group(1)) if m else None


def image_time(path: Path) -> datetime | None:
    m = STAMP_RE.search(path.name)
    return datetime.strptime(m.group(1), "%Y%m%d-%H%M%S") if m else None


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


def plan(
    images: list[Path],
    *,
    min_s: float,
    max_s: float,
    rate: float,
    fps: int,
    hold_last: float = 0.0,
    intro_s: float = 0.0,
    outro_s: float = 0.0,
) -> Plan:
    """Pick which images to show and for how many frames, so the whole video lasts between min_s and max_s seconds."""
    if not images:
        raise ValueError("no images to put in the video")
    if not 0 < min_s <= max_s:
        raise ValueError(f"need 0 < --min <= --max, got {min_s} and {max_s}")
    if rate <= 0 or fps <= 0:
        raise ValueError("--rate and --fps must be positive")
    if min(hold_last, intro_s, outro_s) < 0 or hold_last + intro_s + outro_s >= min_s:
        raise ValueError("--hold-last + --intro + --outro must be >= 0 and shorter than --min")

    total = min(max(len(images) / rate + intro_s + outro_s, min_s), max_s)
    # whole frames; never round up past max_s (e.g. --max 59.99 at 30 fps is 1799 frames, not 1800)
    total_frames = min(round(total * fps), math.floor(max_s * fps + 1e-9))
    hold_frames, intro, outro = (round(s * fps) for s in (hold_last, intro_s, outro_s))
    body_frames = total_frames - hold_frames - intro - outro

    # at least one frame per image: thin out evenly when there are more images than frames
    if len(images) > body_frames:
        step = (len(images) - 1) / (body_frames - 1) if body_frames > 1 else 0
        picked = sorted({round(i * step) for i in range(body_frames)})
        images = [images[i] for i in picked]

    # spread body_frames as evenly as possible (the first `extra` images get one frame more)
    base, extra = divmod(body_frames, len(images))
    frames = [base + (1 if i < extra else 0) for i in range(len(images))]
    frames[-1] += hold_frames
    return Plan(images=images, frames=frames, fps=fps, intro=intro, outro=outro)


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
    """RGB image of exactly `size`, letterboxed on the background colour when the aspect ratio differs."""
    img = img.convert("RGB")
    if img.size == size:
        return img
    scale = min(size[0] / img.width, size[1] / img.height)
    resized = img.resize((max(1, round(img.width * scale)), max(1, round(img.height * scale))), Image.LANCZOS)
    canvas = Image.new("RGB", size, BG)
    canvas.paste(resized, ((size[0] - resized.width) // 2, (size[1] - resized.height) // 2))
    return canvas


def font(face: str, px: int) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    for path in FONT_FILES:
        try:
            return ImageFont.truetype(path, px, index=FONT_INDEX[face] if path.endswith(".ttc") else 0)
        except OSError:
            continue
    return ImageFont.load_default(px)


def fmt_time(t: datetime) -> str:
    return f"{t.day} {t:%b %H:%M}"


def card(backdrop: Image.Image, lines: list[tuple[str, str, float, tuple[int, int, int]]]) -> Image.Image:
    """Centred text block over a blurred, darkened backdrop. lines: (text, face, size as share of height, colour)."""
    w, h = backdrop.size
    img = Image.blend(backdrop.filter(ImageFilter.GaussianBlur(h / 40)), Image.new("RGB", (w, h), BG), 0.62)
    draw = ImageDraw.Draw(img)
    lines = [line for line in lines if line[0]]
    fonts = [font(face, max(10, round(share * h))) for _, face, share, _ in lines]
    heights = [draw.textbbox((0, 0), text, font=f)[3] for (text, *_), f in zip(lines, fonts, strict=True)]
    gap, rule = round(h * 0.03), round(h * 0.005)
    y = (h - sum(heights) - gap * len(lines) - rule) // 2
    for i, ((text, _, _, colour), f, lh) in enumerate(zip(lines, fonts, heights, strict=True)):
        draw.text((w // 2, y), text, font=f, fill=colour, anchor="ma")
        y += lh + gap
        if i == 0:  # accent rule under the headline
            draw.rectangle([w // 2 - w // 24, y, w // 2 + w // 24, y + rule], fill=ACCENT)
            y += rule + gap
    return img


def with_progress(img: Image.Image, done: float) -> Image.Image:
    img = img.copy()
    w, h = img.size
    bar = max(3, h // 160)
    draw = ImageDraw.Draw(img)
    draw.rectangle([0, h - bar, w, h], fill=TRACK)
    draw.rectangle([0, h - bar, round(w * done), h], fill=ACCENT)
    return img


def fade(a: Image.Image, b: Image.Image, j: int, n: int) -> Image.Image:
    """Frame j (0-based) of an n-frame blend from a to b; the frame after the last one would be pure b."""
    return Image.blend(a, b, (j + 1) / (n + 1))


def frame_stream(p: Plan, size: tuple[int, int], style: Style | None) -> Iterator[Image.Image]:
    """Every output frame in order: title card, images with crossfades and progress bar, end card."""

    def load(path: Path) -> Image.Image:
        with Image.open(path) as img:
            return fit(img, size)

    if style is None:  # --plain
        for path, n in zip(p.images, p.frames, strict=True):
            img = load(path)
            yield from (img for _ in range(n))
        return

    black = Image.new("RGB", size, (0, 0, 0))
    xf = max(0, round(style.xfade_s * p.fps))
    first, last = load(p.images[0]), load(p.images[-1])

    if p.intro:
        title = card(last, [(style.title, "bold", 0.075, TEXT), (style.subtitle, "light", 0.034, MUTED)])
        fade_in, to_first = min(round(0.6 * p.fps), p.intro // 3), min(round(0.5 * p.fps), p.intro // 3)
        for j in range(p.intro):
            if j < fade_in:
                yield fade(black, title, j, fade_in)
            elif j >= p.intro - to_first:
                yield fade(title, first, j - (p.intro - to_first), to_first)
            else:
                yield title

    prev = None
    for i, (path, n) in enumerate(zip(p.images, p.frames, strict=True)):
        cur = load(path)
        k = min(xf, n // 4) if prev is not None else 0  # under 4 frames: hard cut, a blend only ghosts the text
        done = (i + 1) / len(p.images)
        for j in range(n):
            img = fade(prev, cur, j, k) if j < k else cur
            yield with_progress(img, done) if style.progress else img
        prev = cur

    if p.outro:
        final = with_progress(last, 1.0) if style.progress else last
        t0, t1 = image_time(p.images[0]), image_time(p.images[-1])
        span = f"{fmt_time(t0)}  \u2013  {fmt_time(t1)}" if t0 and t1 else ""
        steps = f"{style.found or len(p.images)} build steps"
        end = card(
            last, [(steps, "bold", 0.075, TEXT), (span, "medium", 0.032, MUTED), (style.title, "light", 0.03, MUTED)]
        )
        cross, to_black = min(round(0.6 * p.fps), p.outro // 3), min(round(0.8 * p.fps), p.outro // 3)
        for j in range(p.outro):
            if j < cross:
                yield fade(final, end, j, cross)
            elif j >= p.outro - to_black:
                yield fade(end, black, j - (p.outro - to_black), to_black)
            else:
                yield end


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


def render(p: Plan, out: Path, *, style: Style | None = None, crf: int = 26) -> None:
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
        for i, img in enumerate(frame_stream(p, size, style), 1):
            proc.stdin.write(img.tobytes())
            if i % 300 == 0 or i == p.total_frames:
                print(f"  {i}/{p.total_frames} frames", file=sys.stderr)
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
    look = ap.add_argument_group("look")
    look.add_argument("--title", default=Style.title, help=f'title card headline (default "{Style.title}")')
    look.add_argument("--subtitle", default=Style.subtitle, help="title card second line")
    look.add_argument("--intro", type=float, default=3.0, help="title card seconds, 0 = none (default 3)")
    look.add_argument("--outro", type=float, default=4.0, help="end card seconds, 0 = none (default 4)")
    look.add_argument("--xfade", type=float, default=0.25, help="crossfade between images in seconds (default 0.25)")
    look.add_argument("--no-progress", action="store_true", help="no progress bar")
    look.add_argument("--plain", action="store_true", help="images only: no cards, crossfades or progress bar")
    ap.add_argument("--dry-run", action="store_true", help="print the plan, write nothing")
    args = ap.parse_args(argv)

    if args.plain:
        args.intro = args.outro = 0.0
    if args.images is None:
        args.images = default_images()
    print(f"images from {args.images}", file=sys.stderr)
    if not args.images.is_dir():
        sys.exit(f"not a folder: {args.images}")
    images = collect(args.images, args.first, args.last)
    try:
        p = plan(
            images, min_s=args.min_s, max_s=args.max_s, rate=args.rate, fps=args.fps,
            hold_last=args.hold_last, intro_s=args.intro, outro_s=args.outro,
        )  # fmt: skip
    except ValueError as e:
        sys.exit(str(e))
    style = None if args.plain else Style(args.title, args.subtitle, args.xfade, not args.no_progress, len(images))

    shown = sum(p.frames[:-1]) / len(p.frames[:-1]) / p.fps if len(p.frames) > 1 else p.frames[0] / p.fps
    print(
        f"{len(images)} images found, {len(p.images)} used ({p.images[0].name} .. {p.images[-1].name}); "
        f"{shown:.2f} s each; title {p.intro / p.fps:.1f} s + images + end {p.outro / p.fps:.1f} s "
        f"= {p.seconds:.1f} s at {p.fps} fps -> {args.out}",
        file=sys.stderr,
    )
    if args.dry_run:
        return 0
    render(p, args.out, style=style, crf=args.crf)
    frames, decoded_s = probe(args.out)
    seconds = frames / p.fps
    print(
        f"wrote {args.out} ({args.out.stat().st_size / 1e6:.1f} MB, "
        f"{frames} frames = {seconds:.2f} s, decoder clock {decoded_s:.2f} s)",
        file=sys.stderr,
    )
    if frames != p.total_frames or not args.min_s - 1 / p.fps < seconds <= args.max_s or decoded_s > args.max_s:
        sys.exit(
            f"length check FAILED: {seconds:.2f} s, planned {p.seconds:.2f} s, allowed {args.min_s}-{args.max_s} s"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
