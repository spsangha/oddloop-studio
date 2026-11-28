"""HK Unlocked sketch pass: ink lines + watercolour paper from our own Blender render passes.
usage: python3 ink.py <pass_dir> <frame> <out.png>   (or: ink.py <pass_dir> <f0> <f1> <out_dir>)
Lines come from object-ID, depth and normal breaks (Freestyle ran 138 s/frame here); they wobble and
'boil' every 2 frames like hand-drawn animation; fills get paper grain, pigment pooling at edges and a soft bleed."""
import sys, os, numpy as np, cv2
from scipy import ndimage as ndi

W, H = 1080, 1920
INK = np.array([13, 20, 31], np.float32)          # BGR of (0.12,0.08,0.05)
PAPER = np.array([220, 238, 246], np.float32)     # BGR of SK paper (246,238,220)
_rng = np.random.default_rng(11)

def smooth_noise(h, w, scale, seed):
    r = np.random.default_rng(seed)
    g = r.standard_normal((h // scale + 3, w // scale + 3)).astype(np.float32)
    g = cv2.resize(g, (w + 3 * scale, h + 3 * scale), interpolation=cv2.INTER_CUBIC)[:h, :w]
    return g / (g.std() + 1e-6)

# static paper texture (the sheet itself never moves)
_g1 = smooth_noise(H, W, 3, 1); _g2 = smooth_noise(H, W, 40, 2); _fib = cv2.GaussianBlur(_rng.standard_normal((H, W)).astype(np.float32), (0, 0), 0.7)
PAPER_TEX = (1 + 0.022 * _g1 + 0.008 * _g2 + 0.03 * _fib).astype(np.float32)[..., None]

def load(d, kind, f):
    return cv2.imread(os.path.join(d, f'{kind}_{f:04d}.png'), cv2.IMREAD_UNCHANGED)

def frame(d, f):
    img = load(d, 'img', f)[..., :3].astype(np.float32)
    idx = load(d, 'idx', f)[..., 0].astype(np.int32)
    dep = load(d, 'dep', f)[..., 0].astype(np.float32) / 65535 * 300 + 1e-3
    nrm = load(d, 'nrm', f)[..., ::-1].astype(np.float32) / 65535 * 2 - 1
    sky = dep >= 299
    # --- edges ---
    e = np.zeros((H, W), bool)
    ld = np.log(dep)
    for ax in (0, 1):
        a_id, b_id = idx, np.roll(idx, -1, ax)
        ide = (a_id != b_id) & (a_id != 1) & (b_id != 1)
        dz = np.abs(ld - np.roll(ld, -1, ax)) > 0.045
        dz &= ~((idx == 1) | (np.roll(idx, -1, ax) == 1))
        dz &= ~((idx == 2) & (np.roll(idx, -1, ax) == 2))      # no rings round the contact shadows on the paving
        nd = (nrm * np.roll(nrm, -1, ax)).sum(-1) < 0.80
        nd &= (idx == np.roll(idx, -1, ax)) & (idx > 2)
        e |= ide | dz | nd
    e[-1, :] = False; e[:, -1] = False
    # thickness by distance: near 2.6 px, far 1.1 px
    near = dep < 9
    e_f = e.astype(np.float32)
    thick = cv2.dilate(e_f * near, np.ones((2, 2), np.uint8))
    line = np.maximum(e_f, thick)
    line = cv2.GaussianBlur(line, (0, 0), 0.55)
    # --- boil: wobble lines with a smooth displacement field that changes every 2 frames ---
    seed = 1000 + f // 2
    dx = smooth_noise(H, W, 28, seed) * 1.1; dy = smooth_noise(H, W, 28, seed + 7) * 1.1
    gx, gy = np.meshgrid(np.arange(W, dtype=np.float32), np.arange(H, dtype=np.float32))
    line = cv2.remap(line, gx + dx, gy + dy, cv2.INTER_LINEAR)
    # broken/pressure variation along strokes
    press = 0.78 + 0.22 * np.clip(smooth_noise(H, W, 9, seed + 3), -1, 1)
    far = np.clip((dep - 25) / 60, 0, 1)
    la = np.clip(line * 1.25, 0, 1) * press * (1 - 0.6 * far)
    la[sky] *= 0.0
    la *= 1 - cv2.GaussianBlur(cv2.dilate((idx == 1).astype(np.uint8), np.ones((9, 9), np.uint8)).astype(np.float32), (0, 0), 1.5)
    # --- watercolour fill: lift toward paper, pool pigment at region edges, slight bleed ---
    col = img.copy()
    col = cv2.GaussianBlur(col, (0, 0), 0.8)
    pool = cv2.GaussianBlur(e_f, (0, 0), 2.2)
    col = col * (1 - 0.10 * np.clip(pool * 2.5, 0, 1))[..., None]
    lum = col.mean(-1, keepdims=True)
    col = col * 0.92 + PAPER * 0.08 * (0.35 + 0.65 * lum / 255)   # paper shows through the lighter washes more
    col = col + (lum - col) * 0.06                                # a touch less saturated, like wash on paper
    wash = 1 + 0.018 * smooth_noise(H, W, 60, 5)[..., None]       # static wash unevenness
    col = col * wash * PAPER_TEX
    # sky: soft wash with paper showing through
    sk = sky[..., None].astype(np.float32)
    col = col * (1 + 0.06 * sk * smooth_noise(H, W, 90, 9)[..., None])     # night sky: uneven ink-blue wash, no paper lift
    # warm bulb glow (soft, no tube look)
    bright = ((img[..., 2] > 235) & (img[..., 1] > 190) & (img[..., 0] < 200) & (idx == 1)).astype(np.float32)
    BULB = np.array([160, 217, 255], np.float32)          # #FFD9A0 in BGR
    g1 = np.clip(cv2.GaussianBlur(bright, (0, 0), 7) * 3.0, 0, 1); g2 = np.clip(cv2.GaussianBlur(bright, (0, 0), 30) * 5.0, 0, 1)
    halo = (0.6 * g1 + 0.45 * g2)[..., None]
    col = col * (1 - halo) + (col * 0.35 + BULB * 0.75) * halo                 # soft warm halo, screen-like, no tube look
    col = np.where(bright[..., None] > 0, BULB * 0.95 + col * 0.05, col)
    out = col * (1 - 0.92 * la[..., None]) + INK * 0.92 * la[..., None]
    return np.clip(out, 0, 255).astype(np.uint8)

if __name__ == '__main__':
    d = sys.argv[1]
    if len(sys.argv) == 4:
        cv2.imwrite(sys.argv[3], frame(d, int(sys.argv[2])))
    else:
        f0, f1, od = int(sys.argv[2]), int(sys.argv[3]), sys.argv[4]; os.makedirs(od, exist_ok=True)
        for f in range(f0, f1 + 1):
            if os.path.exists(os.path.join(d, f'img_{f:04d}.png')):
                cv2.imwrite(os.path.join(od, f'{f:04d}.png'), frame(d, f))
