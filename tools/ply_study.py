#!/usr/bin/env python3
"""ply_study.py - study a 3D Gaussian Splatting (3DGS) PLY and separate real splats from garbage rows.

Usage (numpy + pillow, no other dependency):
  uv run --with numpy --with pillow python -I tools/ply_study.py <scene.ply> --img <img_dir> --out <derived_dir>

Writes
  <img_dir>/stats.json              every number used in the study report
  <img_dir>/*.png                   orthographic study renders (1 px = 1 cm, upscaled 2x)
  <derived_dir>/<stem>_clean.ply    real splats only, same 59 properties, same header layout
  <derived_dir>/<stem>_clean_sh0.ply real splats, DC colour only (14 properties) - small web-viewer asset

A row counts as a *real* splat when every one of its 59 floats is finite, its quaternion has unit length
(|norm-1| < 1 %) and its colour / scale / opacity values are in a sane range. Garbage rows in this file are
uniformly random bit patterns, so they fail the unit-quaternion test with probability ~1.
"""
import sys, os, json, time, math, argparse
import numpy as np

ap = argparse.ArgumentParser()
ap.add_argument('ply')
ap.add_argument('--img', required=True)
ap.add_argument('--out', default=None, help='directory for the derived PLY files (skip export if omitted)')
ap.add_argument('--no-render', action='store_true')
args = ap.parse_args()
os.makedirs(args.img, exist_ok=True)
if args.out:
    os.makedirs(args.out, exist_ok=True)
t0 = time.time()
def log(*a):
    print(f"[{time.time()-t0:6.1f}s]", *a, flush=True)

# ------------------------------------------------------------------ header + load
with open(args.ply, 'rb') as f:
    header = b''
    while not header.endswith(b'end_header\n'):
        line = f.readline()
        if not line:
            raise SystemExit('no end_header found')
        header += line
hlen = len(header)
hl = header.decode('ascii').splitlines()
props = [l.split()[2] for l in hl if l.startswith('property')]
ptypes = [l.split()[1] for l in hl if l.startswith('property')]
n = int(next(l for l in hl if l.startswith('element vertex')).split()[2])
assert all(t == 'float' for t in ptypes), ptypes
dt = np.dtype([(p, '<f4') for p in props])
fsize = os.path.getsize(args.ply)
R = {'file': {'path': args.ply, 'bytes': fsize, 'header_bytes': hlen, 'vertices': n, 'bytes_per_vertex': dt.itemsize,
              'size_consistent': bool(hlen + n * dt.itemsize == fsize), 'props': props,
              'comments': [l for l in hl if l.startswith('comment')]}}
d = np.fromfile(args.ply, dtype=dt, count=n, offset=hlen)
log('loaded', n, 'rows x', len(props), 'floats; file size consistent =', R['file']['size_consistent'])

# ------------------------------------------------------------------ per-field NaN counts, all-finite rows
allfinite = np.ones(n, bool)
nan_counts = {}
for p in props:
    v = d[p]
    fin = np.isfinite(v)
    nan_counts[p] = int((~fin).sum())
    allfinite &= fin
R['nan_per_field'] = nan_counts
R['rows_all_fields_finite'] = int(allfinite.sum())

# ------------------------------------------------------------------ real-row detection
def f64(name):
    return np.nan_to_num(d[name].astype(np.float64), nan=0.0, posinf=1e30, neginf=-1e30)
x, y, z = f64('x'), f64('y'), f64('z')
q = np.stack([f64('rot_0'), f64('rot_1'), f64('rot_2'), f64('rot_3')], 1)
qn = np.linalg.norm(q, axis=1)
unitq = allfinite & (np.abs(qn - 1) < 0.01)
sc = np.stack([f64('scale_0'), f64('scale_1'), f64('scale_2')], 1)
dc = np.stack([f64('f_dc_0'), f64('f_dc_1'), f64('f_dc_2')], 1)
op = f64('opacity')
sane = allfinite & (np.abs(dc) < 50).all(1) & (sc < 5).all(1) & (sc > -30).all(1) & (np.abs(op) < 50)
for i in range(45):
    sane &= np.abs(f64(f'f_rest_{i}')) < 50
real = unitq & sane
garbage = ~real
R['real_rows'] = {'unit_quaternion_and_finite': int(unitq.sum()), 'sane_ranges_and_finite': int(sane.sum()),
                  'real (both)': int(real.sum()), 'garbage': int(garbage.sum()),
                  'real_fraction': float(real.mean()), 'n_over_3': n / 3}
log('real rows', real.sum(), 'garbage', garbage.sum())

# where do the real rows sit in the file?
idx = np.flatnonzero(real)
gaps = np.flatnonzero(np.diff(idx) > 1)
R['real_row_layout'] = {'first_index': int(idx[0]), 'last_index': int(idx[-1]), 'contiguous_runs': int(gaps.size + 1),
                        'longest_run': int(np.diff(np.concatenate([[-1], gaps, [idx.size - 1]])).max()),
                        'count_per_100k_block': np.bincount(idx // 100000, minlength=n // 100000 + 1).tolist(),
                        'count_by_index_mod_3': np.bincount(idx % 3, minlength=3).tolist(),
                        'count_by_index_mod_2': np.bincount(idx % 2, minlength=2).tolist()}
# are the garbage rows uniformly random bits?
u = d['x'][garbage].view(np.uint32)
expo = (u >> 23) & 0xFF
ph = np.bincount(expo, minlength=256) / u.size
R['garbage_bit_test_on_x'] = {'nan_fraction': float(np.isnan(d['x'][garbage]).mean()),
                              'nan_fraction_expected_for_uniform_bits': (2 ** 24 - 2) / 2 ** 32,
                              'sign_bit_fraction': float((u >> 31).mean()),
                              'exponent_byte_entropy_bits (max 8)': float(-(ph[ph > 0] * np.log2(ph[ph > 0])).sum()),
                              'unique_fraction': float(np.unique(u).size / u.size),
                              'real_rows_mistaken_inside_room_box_est': None}
log('layout', R['real_row_layout']['first_index'], R['real_row_layout']['last_index'], 'runs', R['real_row_layout']['contiguous_runs'])

# ------------------------------------------------------------------ geometry of the real splats
def pcts(v, ps=(0, 0.5, 1, 5, 25, 50, 75, 95, 99, 99.5, 100)):
    return {str(p): float(q_) for p, q_ in zip(ps, np.percentile(v, ps))}
xr, yr, zr = x[real], y[real], z[real]
R['real_position_pct'] = {'x': pcts(xr), 'y': pcts(yr), 'z': pcts(zr)}
core_box = {k: [float(np.percentile(v, 0.5)) - 0.1, float(np.percentile(v, 99.5)) + 0.1] for k, v in (('x', xr), ('y', yr), ('z', zr))}
R['core_box_(0.5..99.5 pct +-10cm)'] = core_box
R['core_extent'] = {k: core_box[k][1] - core_box[k][0] - 0.2 for k in 'xyz'}
incore = real & (x >= core_box['x'][0]) & (x <= core_box['x'][1]) & (y >= core_box['y'][0]) & (y <= core_box['y'][1]) & (z >= core_box['z'][0]) & (z <= core_box['z'][1])
rr = np.sqrt(x * x + y * y + z * z)
R['real_outside_core'] = {'count': int((real & ~incore).sum()), 'r_pct': pcts(rr[real & ~incore], (50, 90, 99, 100))}
R['real_centroid'] = [float(xr.mean()), float(yr.mean()), float(zr.mean())]
R['origin_relative_to_core_box'] = {k: float((0 - core_box[k][0]) / (core_box[k][1] - core_box[k][0])) for k in 'xyz'}

def peaks(v, binw=0.02, k=6):
    edges = np.arange(math.floor(v.min() / binw) * binw, v.max() + binw, binw)
    hh, _ = np.histogram(v, bins=edges)
    order = np.argsort(hh)[::-1]
    res = []
    for i in order:
        c = (edges[i] + edges[i + 1]) / 2
        if any(abs(c - r_[0]) < 0.1 for r_ in res):
            continue
        res.append([round(float(c), 3), int(hh[i]), round(float(((v > c - 0.03) & (v < c + 0.03)).sum() / v.size), 4)])
        if len(res) >= k:
            break
    return {'peakiness_max_over_median_bin': float(hh.max() / max(np.median(hh[hh > 0]), 1)), 'top_peaks_[centre,count,frac_within_3cm]': res}
R['axis_peaks_real'] = {k: peaks(v) for k, v in (('x', xr), ('y', yr), ('z', zr))}
up = max('xyz', key=lambda k: R['axis_peaks_real'][k]['peakiness_max_over_median_bin'])
R['up_axis'] = up
upv = {'x': x, 'y': y, 'z': z}[up]
ypk = sorted([p[0] for p in R['axis_peaks_real'][up]['top_peaks_[centre,count,frac_within_3cm]'][:2]])
floor_y, ceil_y = ypk[0], ypk[1]
R['floor_and_ceiling'] = {'floor': floor_y, 'ceiling': ceil_y, 'clear_height': ceil_y - floor_y,
                          'origin_height_above_floor': -floor_y}
# floor tilt: PCA of the points within +-4 cm of the floor peak
hor = [k for k in 'xyz' if k != up]
A = {'x': x, 'y': y, 'z': z}
fl = real & (np.abs(upv - floor_y) < 0.04)
P = np.stack([A['x'][fl], A['y'][fl], A['z'][fl]], 1)
P = P - P.mean(0)
w_, V = np.linalg.eigh(P.T @ P / P.shape[0])
normal = V[:, 0]
upvec = np.array([1.0 if k == up else 0.0 for k in 'xyz'])
R['floor_plane'] = {'points_used': int(fl.sum()), 'normal': [float(v) for v in normal],
                    'tilt_from_up_axis_deg': float(math.degrees(math.acos(min(1, abs(float(normal @ upvec)))))),
                    'rms_thickness_m': float(math.sqrt(max(w_[0], 0)))}
hv = np.arange(math.floor(yr.min() * 10) / 10, yr.max() + 0.1, 0.1)
hh, _ = np.histogram(upv[real], bins=hv)
R['vertical_profile_10cm'] = [[round(float(hv[i]), 2), int(hh[i])] for i in range(len(hh)) if hh[i] > 0]
below = real & (upv < floor_y - 0.10)
R['below_floor'] = {'count': int(below.sum()), 'fraction_of_real': float(below.sum() / real.sum()),
                    'depth_pct': pcts(floor_y - upv[below], (50, 90, 99))}
log('up', up, 'floor', floor_y, 'ceiling', ceil_y, 'tilt', R['floor_plane']['tilt_from_up_axis_deg'])

# yaw: rotate the horizontal plane until walls line up with the axes
a_, b_ = A[hor[0]][real], A[hor[1]][real]
rng = np.random.default_rng(0)
sel = rng.choice(a_.size, min(300000, a_.size), replace=False)
best = None
for ang in np.arange(0, 90, 0.5):
    t = math.radians(ang)
    ar = a_[sel] * math.cos(t) - b_[sel] * math.sin(t)
    br = a_[sel] * math.sin(t) + b_[sel] * math.cos(t)
    score = 0
    for v in (ar, br):
        h2, _ = np.histogram(v, bins=np.arange(v.min(), v.max() + 0.05, 0.05))
        score += np.sort(h2)[::-1][:4].sum() / v.size
    if best is None or score > best[1]:
        best = (float(ang), float(score))
yaw = best[0]
t = math.radians(yaw)
ar_full = a_ * math.cos(t) - b_ * math.sin(t)
br_full = a_ * math.sin(t) + b_ * math.cos(t)
R['yaw'] = {'horizontal_axes': hor, 'best_rotation_deg': yaw,
            'aligned_peaks': {hor[0] + "'": peaks(ar_full), hor[1] + "'": peaks(br_full)}}
log('yaw', yaw)

# ------------------------------------------------------------------ appearance of the real splats
alpha = 1 / (1 + np.exp(-op[real]))
sexp = np.exp(sc[real])
smax, smin, sgeo = sexp.max(1), sexp.min(1), np.exp(sc[real].mean(1))
R['opacity_real'] = {'alpha_pct': pcts(alpha), 'frac_alpha_lt_0.05': float((alpha < 0.05).mean()),
                     'frac_alpha_lt_0.1': float((alpha < 0.1).mean()), 'frac_alpha_gt_0.5': float((alpha > 0.5).mean()),
                     'frac_alpha_gt_0.9': float((alpha > 0.9).mean()), 'frac_alpha_lt_1_255': float((alpha < 1 / 255).mean())}
R['scale_real'] = {'smax_pct': pcts(smax), 'smin_pct': pcts(smin), 'sgeo_pct': pcts(sgeo),
                   'anisotropy_pct': pcts(smax / np.maximum(smin, 1e-12)),
                   'frac_smax_gt_0.25': float((smax > 0.25).mean()), 'frac_smax_gt_1': float((smax > 1).mean())}
qr = q[real]
R['rotation_real'] = {'file_order': [p for p in props if p.startswith('rot_')], 'norm_pct': pcts(qn[real], (0, 50, 100)),
                      'mean_abs_component_rot0..3': [float(v) for v in np.abs(qr).mean(0)],
                      'mean_component_rot0..3': [float(v) for v in qr.mean(0)]}
C0 = 0.28209479177387814
rgb = 0.5 + C0 * dc[real]
lum = 0.2126 * rgb[:, 0] + 0.7152 * rgb[:, 1] + 0.0722 * rgb[:, 2]
sat = rgb.max(1) - rgb.min(1)
qc = np.clip(np.floor(np.clip(rgb, 0, 0.999) * 4), 0, 3).astype(int)
code = qc[:, 0] * 16 + qc[:, 1] * 4 + qc[:, 2]
cnt = np.bincount(code, weights=alpha, minlength=64)
top = np.argsort(cnt)[::-1][:8]
R['colour_real'] = {'frac_any_channel_outside_0_1': float(((rgb < 0) | (rgb > 1)).any(1).mean()),
                    'mean_rgb_alpha_weighted': [float(v) for v in (rgb * alpha[:, None]).sum(0) / alpha.sum()],
                    'median_rgb': [float(v) for v in np.median(rgb, 0)], 'luminance_pct': pcts(lum), 'saturation_pct': pcts(sat),
                    'frac_sat_lt_0.1': float((sat < 0.1).mean()), 'frac_sat_gt_0.3': float((sat > 0.3).mean()),
                    'top_colour_bins_alpha_weighted': [{'rgb': [round((c // 16 + .5) / 4, 3), round(((c // 4) % 4 + .5) / 4, 3), round((c % 4 + .5) / 4, 3)],
                                                        'frac': round(float(cnt[c] / cnt.sum()), 4)} for c in top]}
rest = np.stack([d[f'f_rest_{i}'][real] for i in range(45)], 1).astype(np.float32).reshape(-1, 3, 15)
rms_k = np.sqrt((rest.astype(np.float64) ** 2).mean(axis=(0, 1)))
shift = np.abs(rest).max(axis=(1, 2)) * C0
R['sh_real'] = {'rms_dc': float(np.sqrt((dc[real] ** 2).mean())), 'rms_per_coeff_k0_14': [round(float(v), 4) for v in rms_k],
                'rms_deg1': float(np.sqrt((rms_k[0:3] ** 2).mean())), 'rms_deg2': float(np.sqrt((rms_k[3:8] ** 2).mean())),
                'rms_deg3': float(np.sqrt((rms_k[8:15] ** 2).mean())), 'frac_points_all_rest_zero': float((rest == 0).all(axis=(1, 2)).mean()),
                'max_abs_rest_times_C0_pct': pcts(shift, (50, 90, 99, 100))}
del rest
log('appearance done')

# ------------------------------------------------------------------ renders
if not args.no_render:
    from PIL import Image, ImageDraw
    def save(img, name, label, up_=2):
        im = Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8))
        im = im.resize((im.width * up_, im.height * up_), Image.NEAREST)
        dr = ImageDraw.Draw(im)
        dr.rectangle([0, 0, 8 + 6 * len(label), 16], fill=(0, 0, 0)); dr.text((4, 2), label, fill=(255, 255, 255))
        dr.rectangle([10, im.height - 14, 10 + 100 * up_, im.height - 8], fill=(255, 255, 255)); dr.text((10, im.height - 30), '1 m', fill=(255, 255, 255))
        path = os.path.join(args.img, name); im.save(path); return name
    def cmap(tt):
        an = np.array([[.19, .07, .23], [.28, .33, .75], [.1, .7, .7], [.5, .85, .2], [.95, .75, .1], [.9, .2, .1]])
        tt = np.clip(tt, 0, 1) * (len(an) - 1); i = np.clip(np.floor(tt).astype(int), 0, len(an) - 2); f = (tt - i)[:, None]
        return an[i] * (1 - f) + an[i + 1] * f
    def grid(u, v, ppm, ext):
        (umin, umax), (vmin, vmax) = ext
        W = int((umax - umin) * ppm) + 1; H = int((vmax - vmin) * ppm) + 1
        iu = ((u - umin) * ppm).astype(int); iv = H - 1 - ((v - vmin) * ppm).astype(int)
        m = (iu >= 0) & (iu < W) & (iv >= 0) & (iv < H)
        return W, H, iu, iv, m
    def ortho_last(u, v, col, order, ext, ppm=100, bg=0.08):
        W, H, iu, iv, m = grid(u, v, ppm, ext)
        o = np.argsort(order[m], kind='stable'); img = np.full((H, W, 3), bg, np.float32)
        img[iv[m][o], iu[m][o]] = col[m][o]; return img
    def ortho_avg(u, v, col, w, ext, ppm=100, bg=0.08):
        W, H, iu, iv, m = grid(u, v, ppm, ext)
        acc = np.zeros((H, W, 3)); ws = np.zeros((H, W))
        np.add.at(acc, (iv[m], iu[m]), col[m] * w[m][:, None]); np.add.at(ws, (iv[m], iu[m]), w[m])
        return np.where(ws[..., None] > 0, acc / np.maximum(ws, 1e-9)[..., None], bg).astype(np.float32)
    vis = alpha >= 0.05
    U, V, Hh = A[hor[0]][real][vis], A[hor[1]][real][vis], upv[real][vis]
    col = np.clip(rgb[vis], 0, 1); wv = alpha[vis]
    extH = (tuple(core_box[hor[0]]), tuple(core_box[hor[1]]))
    extV = (tuple(core_box[up]),)
    cut = ceil_y - 0.15
    keep = Hh <= cut
    imgs = {}
    imgs['topdown_rgb'] = save(ortho_last(U[keep], V[keep], col[keep], Hh[keep], extH), 'topdown_rgb.png',
                               f"top-down RGB | {hor[0]} right, {hor[1]} up | highest splat wins | {up} <= {cut:.2f} (ceiling removed)")
    hn = (Hh - floor_y) / (ceil_y - floor_y)
    imgs['topdown_height'] = save(ortho_last(U[keep], V[keep], cmap(hn[keep]), Hh[keep], extH), 'topdown_height.png',
                                  f"top-down height | blue = floor ({floor_y:.2f}) .. red = ceiling ({ceil_y:.2f}) | ceiling removed")
    plan = (Hh > floor_y + 0.05) & (Hh < floor_y + 1.4)
    imgs['floorplan'] = save(ortho_last(U[plan], V[plan], cmap(hn[plan]), Hh[plan], extH), 'floorplan_slice.png',
                             f"floor-plan slice | splats {floor_y+0.05:.2f} < {up} < {floor_y+1.4:.2f} | colour = height")
    imgs['topdown_xray'] = save(ortho_avg(U, V, col, wv, extH), 'topdown_xray.png', "top-down alpha-weighted average, all heights")
    ta = math.radians(yaw)
    Ua = U * math.cos(ta) - V * math.sin(ta); Va = U * math.sin(ta) + V * math.cos(ta)
    extA = ((float(Ua.min()), float(Ua.max())), (float(Va.min()), float(Va.max())))
    imgs['elev_front'] = save(ortho_avg(Ua, Hh, col, wv, (extA[0], extV[0])), 'elevation_front.png',
                              f"elevation along {hor[1]} | {hor[0]}' right (yaw {yaw:.1f} deg), {up} up | alpha-weighted average")
    imgs['elev_side'] = save(ortho_avg(Va, Hh, col, wv, (extA[1], extV[0])), 'elevation_side.png',
                             f"elevation along {hor[0]} | {hor[1]}' right (yaw {yaw:.1f} deg), {up} up | alpha-weighted average")
    bl = Hh < floor_y - 0.10
    imgs['below_floor'] = save(ortho_last(U[bl], V[bl], cmap((floor_y - Hh[bl]) / 1.0), Hh[bl], extH), 'below_floor_map.png',
                               f"splats more than 10 cm below the floor | colour = depth below floor (blue 0 .. red 1 m)")
    fin3 = np.isfinite(d['x']) & np.isfinite(d['y']) & np.isfinite(d['z'])
    for lim, name in ((50, 'garbage_map_50.png'), (5000, 'garbage_map_5000.png')):
        h2, _, _ = np.histogram2d(np.clip(np.nan_to_num(x[fin3]), -lim, lim), np.clip(np.nan_to_num(z[fin3]), -lim, lim), bins=400, range=[[-lim, lim], [-lim, lim]])
        im = np.log1p(h2.T[::-1]) / np.log1p(h2.max())
        imgs[name] = save(cmap(im.ravel()).reshape(400, 400, 3), name, f"ALL finite rows, log count, +-{lim} units, x right / z up", up_=1)
    R['renders'] = {'splats_rendered_alpha_ge_0.05': int(vis.sum()), 'ceiling_cut': cut, 'files': imgs}
    log('renders done')

# ------------------------------------------------------------------ derived PLY exports
if args.out:
    stem = os.path.splitext(os.path.basename(args.ply))[0].replace(' ', '_').replace('(', '').replace(')', '')
    sub = d[real]
    p1 = os.path.join(args.out, f'{stem}_clean.ply')
    with open(p1, 'wb') as f:
        h = header.replace(f'element vertex {n}'.encode(), f'element vertex {sub.size}'.encode())
        h = h.replace(b'end_header', b'comment real splats only (finite, unit quaternion, sane ranges) - tools/ply_study.py\nend_header')
        f.write(h); sub.tofile(f)
    keep14 = ['x', 'y', 'z', 'scale_0', 'scale_1', 'scale_2', 'rot_0', 'rot_1', 'rot_2', 'rot_3', 'f_dc_0', 'f_dc_1', 'f_dc_2', 'opacity']
    small = np.empty(sub.size, dtype=np.dtype([(p, '<f4') for p in keep14]))
    for p in keep14:
        small[p] = sub[p]
    p2 = os.path.join(args.out, f'{stem}_clean_sh0.ply')
    with open(p2, 'wb') as f:
        f.write(b'ply\nformat binary_little_endian 1.0\ncomment real splats, DC colour only (SH degree 0) - tools/ply_study.py\n')
        f.write(f'element vertex {sub.size}\n'.encode())
        for p in keep14:
            f.write(f'property float {p}\n'.encode())
        f.write(b'end_header\n'); small.tofile(f)
    R['exports'] = {'clean': {'path': p1, 'vertices': int(sub.size), 'bytes': os.path.getsize(p1)},
                    'clean_sh0': {'path': p2, 'vertices': int(sub.size), 'bytes': os.path.getsize(p2)}}
    log('exports', R['exports'])

with open(os.path.join(args.img, 'stats.json'), 'w') as f:
    json.dump(R, f, indent=1)
log('wrote', os.path.join(args.img, 'stats.json'))
