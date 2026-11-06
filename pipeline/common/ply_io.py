# pipeline/common/ply_io.py
import numpy as np

SH_C0 = 0.28209479

def read_header(path: str) -> tuple[int, int, list[str]]:
    with open(path, "rb") as f:
        header = b""
        while not header.endswith(b"end_header\n"):
            header += f.readline()
    lines = header.decode().splitlines()
    n = int(next(l for l in lines if l.startswith("element vertex")).split()[-1])
    names = [l.split()[-1] for l in lines if l.startswith("property")]
    return n, len(header), names

def load_gaussians(path: str) -> np.ndarray:
    n, offset, names = read_header(path)
    dt = np.dtype([(name, "<f4") for name in names])          # 59 fields, 236 bytes
    return np.fromfile(path, dtype=dt, count=n, offset=offset)  # ~2 s

def clean_mask(g: np.ndarray, room_limit: float = 20.0, min_opacity: float = 0.05,
               max_scale: float = 2.0) -> np.ndarray:         # thresholds [HYPOTHESIS]
    xyz = np.stack([g["x"], g["y"], g["z"]], 1)
    finite = np.isfinite(xyz).all(1)
    in_room = (np.abs(xyz) < room_limit).all(1)
    not_origin = (np.abs(xyz) > 1e-3).any(1)
    opacity = 1.0 / (1.0 + np.exp(-np.clip(g["opacity"], -30, 30)))
    scale = np.exp(np.clip(np.stack([g["scale_0"], g["scale_1"], g["scale_2"]], 1), -30, 30))
    return finite & in_room & not_origin & (opacity >= min_opacity) & (scale.max(1) < max_scale)

def rgb_from_dc(g: np.ndarray) -> np.ndarray:
    dc = np.stack([g["f_dc_0"], g["f_dc_1"], g["f_dc_2"]], 1)
    return np.clip(0.5 + SH_C0 * dc, 0.0, 1.0)
