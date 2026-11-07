"""Copy a committed sample of the pictures to out/samples/ as JPEGs (the full out/images/ PNG set is gitignored,
~190 MB). The contact sheet is shrunk and the flipbook re-encoded small.

    uv run python scripts_samples.py [--objects 30] [--every 12]
"""

from __future__ import annotations

import argparse
import shutil
from pathlib import Path

import numpy as np
import orjson
from PIL import Image

ROOT = Path(__file__).resolve().parent
OUT = ROOT / "out"


def jpeg(src: Path, dst: Path, quality: int = 85, max_w: int = 1280) -> None:
    im = Image.open(src).convert("RGB")
    if im.width > max_w:
        im = im.resize((max_w, int(im.height * max_w / im.width)), Image.LANCZOS)
    im.save(dst, quality=quality, optimize=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--objects", type=int, default=30)
    ap.add_argument("--every", type=int, default=12)
    args = ap.parse_args()
    samples = OUT / "samples"
    if samples.exists():
        shutil.rmtree(samples)                      # pictures of an older run never linger
    samples.mkdir()
    manifest = orjson.loads((OUT / "images_manifest.json").read_bytes())
    chosen = manifest[: args.objects] + manifest[args.objects::args.every]
    n = 0
    for m in chosen:
        for rel in m["images"].values():
            jpeg(OUT / rel, samples / (Path(rel).stem + ".jpg"))
            n += 1
    for p in sorted((OUT / "images").glob("*_all_objects_*.png")):
        jpeg(p, samples / (p.stem + ".jpg"), quality=90)
        n += 1
    if (OUT / "contact_sheet.png").exists():
        jpeg(OUT / "contact_sheet.png", samples / "contact_sheet.jpg", quality=80, max_w=1920)
        n += 1
    try:
        import imageio.v2 as iio
        with iio.get_writer(samples / "flipbook.mp4", fps=6, codec="libx264", quality=5, macro_block_size=8) as w:
            for m in manifest:
                im = Image.open(OUT / m["images"]["outside"]).convert("RGB").resize((640, 400), Image.LANCZOS)
                w.append_data(np.asarray(im))
        n += 1
    except ImportError:
        pass
    (samples / "README.md").write_text(
        f"Sample of the autoscene pictures: {len(chosen)} of {len(manifest)} objects (the first {args.objects} and every "
        f"{args.every}th after that), as JPEG. The full PNG set (3 per object) is produced by "
        "`uv run python -m autoscene.run pictures` into out/images/ (gitignored).\n")
    print(f"{n} files in {samples} for {len(chosen)} of {len(manifest)} objects")


if __name__ == "__main__":
    main()
