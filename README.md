# SinceAI_2026_Valmet
## autoscene: automatic object detection and room rebuild

[`autoscene/`](autoscene/README.md) turns the splat scan into a room of named, framed objects with no human in
the loop: a numba Gaussian-splat rasteriser renders 197 views with an ID buffer, YOLOE-26 finds objects in them,
the masks are lifted to 3D by view-consensus merging, the ceiling pipe network is split into runs by local
direction, and every object gets its own PLY, an oriented box, a row in `out/scene.json` and three pictures
(textured close-up, room-so-far from outside, detector proof). Plan and research: [`autoscene/PLAN.md`](autoscene/PLAN.md).

```bash
cd autoscene && uv sync && uv run python -m autoscene.run all
```
