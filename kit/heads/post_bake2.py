"""round 2 maps from the raw Lee Perry-Smith bake (build_heads.py) + MakeHuman position bake (bake_pos.py):
scan_col.jpg  - multiplicative colour detail of the real scan (blotches, capillaries, freckles, lip/eyelid colour), 0.5 = no change
scan_mask.jpg - R forehead, G eye surround, B beard/stubble zone (per-seed detail weights; women drop the stubble colour)
python3 post_bake2.py raw.npz pos.npz outdir"""
import sys, numpy as np
from PIL import Image
from scipy import ndimage as nd
z = np.load(sys.argv[1]); P = np.load(sys.argv[2]); out = sys.argv[3]
h, c = z['h'], z['c']
m = (h > 0.01) | (c.sum(0) > 0.01)
lab, n = nd.label(m); sizes = nd.sum(m, lab, range(1, n + 1)); keep = np.isin(lab, 1 + np.nonzero(sizes > 0.002 * m.size)[0])
w = nd.gaussian_filter(nd.binary_erosion(keep, iterations=6).astype(np.float32), 5)
def blur_in(a, sg, k=keep): return nd.gaussian_filter(a * k, sg) / np.maximum(nd.gaussian_filter(k.astype(np.float32), sg), 1e-4)
pp = P['p']; ez = (P['eyeL'][2] + P['eyeR'][2]) / 2; eL, eR = P['eyeL'], P['eyeR']
def ss(a, b, x): t_ = np.clip((x - a) / (b - a), 0, 1); return t_ * t_ * (3 - 2 * t_)
valid = np.abs(pp).sum(-1) > 0
rw = ss(ez - 0.165, ez - 0.115, pp[..., 2]) * valid
il, ni = nd.label(valid); zm = nd.mean(pp[..., 2], il, range(1, ni + 1)); pass   # (round 1 zeroed whole islands here, but the face shares one UV island with the body -> face lost all detail; the z fade above handles the neck)
de = np.minimum(np.linalg.norm(pp - eL, axis=-1), np.linalg.norm(pp - eR, axis=-1))
rw *= 0.5 + 0.5 * ss(0.014, 0.022, de)                       # eyeball misfit
rw *= 1 - 0.7 * ss(0.058, 0.068, np.abs(pp[..., 0])) * ss(-0.13, -0.10, pp[..., 1])   # ears
rw = nd.gaussian_filter(rw, 3)
# colour detail: local colour / broad colour, per channel (keeps the scan's mottling, drops its overall tone)
cs = np.stack([blur_in(ch, 1.2) for ch in c]); cb = np.stack([blur_in(ch, 40) for ch in c])
lr = np.log(np.maximum(cs, 1e-3) / np.maximum(cb, 1e-3))
lr = lr - np.mean(lr[:, keep], axis=1)[:, None, None]
amp = np.sqrt(blur_in((lr ** 2).mean(0), 14)); g = np.median(amp[keep]); lr *= np.minimum(1.0, 1.8 * g / (amp + 1e-6))   # misfit damping
lr *= (w * rw)[None]
C = np.clip(0.5 + lr / 1.2, 0, 1)                             # encode: ratio = exp((v-0.5)*1.2)
# region masks
front = ss(-0.05, -0.085, pp[..., 1])
fore = ss(ez + 0.012, ez + 0.035, pp[..., 2]) * (1 - ss(ez + 0.085, ez + 0.11, pp[..., 2])) * front
eye = (1 - ss(0.028, 0.05, de)) * ss(0.012, 0.018, de)
lipz = ss(0.03, 0.02, np.abs(pp[..., 0])) * ss(ez - 0.105, ez - 0.095, pp[..., 2]) * (1 - ss(ez - 0.07, ez - 0.06, pp[..., 2]))
beard = ss(ez - 0.17, ez - 0.14, pp[..., 2]) * (1 - ss(ez - 0.055, ez - 0.04, pp[..., 2])) * ss(-0.02, -0.06, pp[..., 1]) * (1 - lipz)
M = np.stack([nd.gaussian_filter(a * valid, 6) for a in (fore, eye, beard)], -1)
def save(a, name, q=92): Image.fromarray((np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8)[::-1]).save(f'{out}/{name}', quality=q)
save(np.moveaxis(C, 0, -1), 'scan_col.jpg'); save(M, 'scan_mask.jpg')
print('ok', float(np.abs(lr[:, keep]).mean()))
