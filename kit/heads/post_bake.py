"""raw scan bakes (build_heads.py) -> assets/heads/scan_height.jpg, scan_spec.jpg, scan_red.jpg (MakeHuman UV, 2048 px)"""
import sys, numpy as np
from PIL import Image
from scipy import ndimage as nd
z = np.load(sys.argv[1]); out = sys.argv[2]; P = np.load(sys.argv[3]) if len(sys.argv) > 3 else None
h, s, c = z['h'], z['s'], z['c']
m = (h > 0.01) | (c.sum(0) > 0.01)
lab, n = nd.label(m); sizes = nd.sum(m, lab, range(1, n + 1)); keep = np.isin(lab, 1 + np.nonzero(sizes > 0.002 * m.size)[0])
w = nd.gaussian_filter(nd.binary_erosion(keep, iterations=6).astype(np.float32), 5)   # feather island edges (no seams)
def blur_in(a, sg):  # mask-normalised blur so the black background does not bleed in
    return nd.gaussian_filter(a * keep, sg) / np.maximum(nd.gaussian_filter(keep.astype(np.float32), sg), 1e-4)
b4 = blur_in(h, 3.5); hp = ((h - b4) + 0.35 * (b4 - blur_in(h, 14))) * w                                                    # pores, lip lines, creases (mid/high frequency)
lr = np.sqrt(blur_in(hp * hp, 12)); g = np.median(lr[keep]); hp = hp * np.minimum(1.0, 1.6 * g / (lr + 1e-6)) ** 1.5   # damp misfit rings (eyes, ears, lip outline)
hp = hp / (np.percentile(np.abs(hp[keep]), 99.5) + 1e-6) * 0.5
if P is not None:   # region weights from the MakeHuman position bake: no creases down the neck, quieter eyelids and ears
    pp = P['p']; ez = (P['eyeL'][2] + P['eyeR'][2]) / 2; ey = P['eyeL'][1]
    def ss(a, b, x): t_ = np.clip((x - a) / (b - a), 0, 1); return t_ * t_ * (3 - 2 * t_)
    rw = ss(ez - 0.165, ez - 0.115, pp[..., 2])
    il, ni = nd.label(np.abs(pp).sum(-1) > 0)
    zm = nd.mean(pp[..., 2], il, range(1, ni + 1)); pass   # (round 1 zeroed whole islands here, but the face shares one UV island with the body -> face lost all detail; the z fade above handles the neck)   # the whole neck UV island
    de = np.minimum(np.linalg.norm(pp - P['eyeL'], axis=-1), np.linalg.norm(pp - P['eyeR'], axis=-1))
    rw *= 0.35 + 0.65 * ss(0.016, 0.026, de)
    rw *= 1 - 0.6 * ss(0.058, 0.068, np.abs(pp[..., 0])) * ss(ey - 0.01, ey + 0.02, pp[..., 1])
    hp = hp * nd.gaussian_filter(rw, 2)
H = np.clip(0.5 + hp, 0, 1)
sp = blur_in(s, 14); mu = sp[keep].mean(); S = np.clip(0.5 + (sp - mu) / (7 * sp[keep].std() + 1e-6), 0, 1) * w + 0.5 * (1 - w)
cs = np.stack([blur_in(ch, 4) for ch in c]); red = cs[0] - 0.5 * (cs[1] + cs[2]); lum = cs.mean(0) + 1e-3
rr = red / lum; rr = rr - blur_in(rr, 60) * 0.6                                   # keep local red zones, flatten the overall tint
lo, hi = np.percentile(rr[keep], 40), np.percentile(rr[keep], 99)
Rd = np.clip((rr - lo) / (hi - lo), 0, 1) * w
def save(a, name, q=90): Image.fromarray((np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8)[::-1]).save(f'{out}/{name}', quality=q)
save(H, 'scan_height.jpg', 92); save(S, 'scan_spec.jpg'); save(Rd, 'scan_red.jpg')
print('ok', keep.mean())
