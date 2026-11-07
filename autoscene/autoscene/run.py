"""autoscene command line: run the stages, each cached under out/.

    uv run python -m autoscene.run all [--ply FILE] [--force]
    uv run python -m autoscene.run clean|views|detect|lift|cluster|relabel|rebuild|pictures
"""

from __future__ import annotations

import argparse
import logging
import time
from pathlib import Path

import numpy as np

from autoscene import DATA, OUT

log = logging.getLogger("autoscene")
DEFAULT_PLY = DATA / "raw" / "Equipment Room.ply"
STAGES = ("clean", "views", "detect", "lift", "cluster", "relabel", "rebuild", "pictures")


def stage_clean(sc, args):
    from autoscene import scene as S
    S.clean(sc)
    S.structure(sc)
    S.save_state(sc, OUT / "state.npz")
    import orjson
    (OUT / "scene_info.json").write_bytes(orjson.dumps(sc.info, option=orjson.OPT_INDENT_2))


def stage_views(sc, args):
    from autoscene import views as V
    views = V.camera_set(sc)
    V.render_views(sc, views, OUT / "views")


def stage_detect(sc, args):
    from autoscene import detect2d as D
    from autoscene import views as V
    views = V.load_views(OUT / "views")
    det = D.Detector().load()
    exclude = (sc.structure == 1) | (sc.structure == 2)        # floor and ceiling never belong to an object
    dets = []
    seen = np.zeros(sc.n, dtype=bool)                          # splats visible in at least one view
    t0 = time.time()
    for i, v in enumerate(views):
        V.load_view_data(v, OUT / "views")
        seen[v.ids[v.ids >= 0]] = True
        found = det.detect(v.image, i)
        for d in found:
            d.splat_ids = D.mask_to_splats(d.mask, v.ids, v.depth, exclude)
            d.mask = None
        dets += [d for d in found if len(d.splat_ids) >= 30]
        v.image = v.ids = v.depth = None
        if i % 10 == 0 or i == len(views) - 1:
            log.info("detected %d/%d views, %d masks (%.0f s)", i + 1, len(views), len(dets), time.time() - t0)
    D.save_detections(dets, OUT / "detections.npz")
    np.save(OUT / "seen.npy", seen)
    log.info("%s of %s kept splats were visible in some view", f"{int(seen[sc.keep].sum()):,}", f"{int(sc.keep.sum()):,}")


def stage_lift(sc, args):
    from scipy import sparse

    from autoscene import detect2d as D
    from autoscene import lift as L
    dets = D.load_detections(OUT / "detections.npz")
    seen = np.load(OUT / "seen.npy")
    vis_path = OUT / "visibility.npz"
    if vis_path.exists():
        vis = sparse.load_npz(vis_path)
    else:
        vis = L.visibility(OUT / "views", sc.n)
        sparse.save_npz(vis_path, vis)
    instances = L.lift(sc, dets, seen=seen, vis=vis)
    L.save_instances(instances, OUT / "instances.npz")


def stage_cluster(sc, args):
    from autoscene import cluster as C
    from autoscene import lift as L
    instances = L.load_instances(OUT / "instances.npz")
    instances = C.add_clusters(sc, instances)
    L.save_instances(instances, OUT / "instances_all.npz")


def stage_relabel(sc, args):
    from autoscene import lift as L
    from autoscene import relabel as RL
    instances = L.load_instances(OUT / "instances_all.npz")
    instances = RL.relabel(sc, instances)
    L.save_instances(instances, OUT / "instances_named.npz")


def stage_rebuild(sc, args):
    from autoscene import lift as L
    from autoscene import rebuild as B
    src = OUT / "instances_named.npz"
    if not src.exists():
        src = OUT / "instances_all.npz"
    instances = L.load_instances(src)
    B.rebuild(sc, instances, OUT)


def stage_pictures(sc, args):
    """`--workers N` renders the objects in N processes (shards), then assembles the final pictures."""
    import subprocess
    import sys

    from autoscene import pictures as P
    if args.shard:
        i, n = (int(v) for v in args.shard.split("/"))
        P.pictures(sc, OUT, limit=args.limit, shard=(i, n), image_base=args.image_base)
        return
    for old in list((OUT / "images").glob("*.png")) + list(OUT.glob("images_manifest*.json")):
        old.unlink()
    base = 1
    if args.workers > 1:
        procs = [subprocess.Popen([sys.executable, "-m", "autoscene.run", "pictures", "--ply", str(args.ply),
                                   "--shard", f"{i}/{args.workers}", "--image-base", str(base), "--limit", str(args.limit)])
                 for i in range(args.workers)]
        for p in procs:
            p.wait()
    else:
        P.pictures(sc, OUT, limit=args.limit, shard=(0, 1), image_base=base)
    P.finish(sc, OUT)


def main(argv=None) -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("stage", choices=("all", *STAGES))
    ap.add_argument("--ply", type=Path, default=DEFAULT_PLY)
    ap.add_argument("--from", dest="from_stage", choices=STAGES, help="with `all`: start at this stage")
    ap.add_argument("--limit", type=int, default=0, help="pictures: only the first N objects")
    ap.add_argument("--workers", type=int, default=3, help="pictures: parallel processes")
    ap.add_argument("--shard", default="", help="pictures (internal): i/n")
    ap.add_argument("--image-base", type=int, default=0, help="pictures (internal): first image number")
    args = ap.parse_args(argv)
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(name)s: %(message)s", datefmt="%H:%M:%S")
    from autoscene import scene as S
    sc = S.load(args.ply)
    stages = list(STAGES) if args.stage == "all" else [args.stage]
    if args.stage == "all" and args.from_stage:
        stages = stages[stages.index(args.from_stage):]
    if stages[0] != "clean":
        S.load_state(sc, OUT / "state.npz")
    for name in stages:
        t = time.time()
        log.info("=== stage %s", name)
        globals()[f"stage_{name}"](sc, args)
        log.info("=== stage %s done in %.0f s", name, time.time() - t)


if __name__ == "__main__":
    main()
