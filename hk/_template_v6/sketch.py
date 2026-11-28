#!/usr/bin/env python3
"""SKETCH world, picture side (looks_v6_brief section 9.2): free photo -> ink lines + flat watercolour wash + draw order.

    layers = make_layers(photo_path, crop, out_w, out_h, near=None, cache_dir=None)
      ink    float32 (h, w)   0..1 ink coverage (1 = black line)
      wash   uint8  (h, w, 4) RGBA wash, alpha 0 where the paper stays bare
      order  float32 (h, w)   0..1 time at which the pen reaches each pixel (only meaningful where ink > 0)

Ink: 3 edge-preserving passes, difference of Gaussians (sigma 1.2 / 1.92) with a soft threshold on a 1600 px wide copy,
specks < 12 px dropped, lines outside the hand-drawn `near` polygon 65 % lighter.
Wash: 10 flat colour areas (k-means), saturation raised, brightest ~18 % left as bare paper, darkest no darker than 35 %
grey-equivalent, blurred and shifted 4 px against the lines, edge pooling, paper grain on top.
"""
import os, hashlib
import numpy as np
import cv2

PAPER = (246, 238, 220)


def _load(photo, crop):
    im = cv2.imread(photo, cv2.IMREAD_COLOR)
    if crop: x0, y0, x1, y1 = map(int, crop); im = im[y0:y1, x0:x1]
    return im


def ink_layer(bgr, near=None, quiet=None):
    w0 = 1600; h0 = int(round(bgr.shape[0] * w0 / bgr.shape[1]))
    im = cv2.resize(bgr, (w0, h0), interpolation=cv2.INTER_AREA)
    lab_ = cv2.cvtColor(im, cv2.COLOR_BGR2LAB); lab_[..., 0] = cv2.createCLAHE(4.0, (6, 6)).apply(lab_[..., 0]); im = cv2.cvtColor(lab_, cv2.COLOR_LAB2BGR)
    im = cv2.medianBlur(im, 5)
    for _ in range(3): im = cv2.bilateralFilter(im, 9, 40, 7)                 # edge-preserving smoothing, 3 passes
    g = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
    g = g.astype(np.float32) / 255.0                                            # haze handled by the CLAHE above
    d = cv2.GaussianBlur(g, (0, 0), 1.2) - cv2.GaussianBlur(g, (0, 0), 1.92)
    # soft threshold: only the dark side of a real edge becomes ink (flat areas stay paper)
    eps, sc = 0.007, 0.026
    ink = np.clip((-d - eps) / sc, 0, 1) ** 0.8
    m = (ink > 0.25).astype(np.uint8)                                          # drop specks under 12 px
    n, lab, st, _ = cv2.connectedComponentsWithStats(m, connectivity=8)
    keep = np.zeros(n, bool); keep[1:] = np.maximum(st[1:, cv2.CC_STAT_WIDTH], st[1:, cv2.CC_STAT_HEIGHT]) >= 12
    dil = cv2.dilate((keep[lab]).astype(np.uint8), np.ones((3, 3), np.uint8))
    ink = ink * dil
    if near:                                                                    # far background lighter
        msk = np.zeros((h0, w0), np.uint8)
        cv2.fillPoly(msk, [np.array([[x * w0, y * h0] for x, y in poly], np.int32) for poly in near], 1)
        msk = cv2.GaussianBlur(msk.astype(np.float32), (0, 0), 14)
        ink = ink * (0.35 + 0.65 * msk)
    if quiet:                                                                   # water / fine texture: keep only long lines, lighter
        q = np.zeros((h0, w0), np.uint8)
        cv2.fillPoly(q, [np.array([[x * w0, y * h0] for x, y in poly], np.int32) for poly in quiet], 1)
        m2 = (ink > 0.25).astype(np.uint8); n2, lab2, st2, _ = cv2.connectedComponentsWithStats(m2, connectivity=8)
        long_ = np.zeros(n2, bool); long_[1:] = np.maximum(st2[1:, cv2.CC_STAT_WIDTH], st2[1:, cv2.CC_STAT_HEIGHT]) >= 60
        kill = cv2.dilate(((~long_[lab2]) & (m2 > 0) & (q > 0)).astype(np.uint8), np.ones((3, 3), np.uint8))
        qs = cv2.GaussianBlur(q.astype(np.float32), (0, 0), 10)
        ink = ink * (1 - kill) * (1 - 0.45 * qs)
    return ink, im


def wash_layer(sm_bgr, out_w, out_h, k=10, seed=7, near=None, warm=False):
    small = cv2.resize(sm_bgr, (480, int(480 * sm_bgr.shape[0] / sm_bgr.shape[1])), interpolation=cv2.INTER_AREA)
    small = cv2.pyrMeanShiftFiltering(small, 14, 40)
    lab = cv2.cvtColor(small, cv2.COLOR_BGR2LAB).reshape(-1, 3).astype(np.float32)
    cv2.setRNGSeed(seed)
    _, lbl, cen = cv2.kmeans(lab, k, None, (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 30, 0.5), 3, cv2.KMEANS_PP_CENTERS)
    lbl = lbl.reshape(small.shape[:2])
    for i in range(k):                                                          # merge near-identical colours (no banding in skies)
        for j in range(i):
            if np.linalg.norm(cen[i] - cen[j]) < 20 and (lbl == j).any(): lbl[lbl == i] = j; break
    lbl = cv2.medianBlur(lbl.astype(np.uint8), 7)
    # palette: raise saturation, lift darks (ink carries the darks)
    cen_bgr = cv2.cvtColor(cen.reshape(1, -1, 3).astype(np.uint8), cv2.COLOR_LAB2BGR).reshape(-1, 3)
    hsv = cv2.cvtColor(cen_bgr.reshape(1, -1, 3), cv2.COLOR_BGR2HSV).reshape(-1, 3).astype(np.float32)
    hsv[:, 1] = np.clip(hsv[:, 1] * 2.4 + 34, 0, 255)
    hsv[:, 2] = np.clip(120 + hsv[:, 2] * 0.55, 0, 255)                         # value >= 120/255: never darker than the 35 % rule allows
    pal = cv2.cvtColor(hsv.reshape(1, -1, 3).astype(np.uint8), cv2.COLOR_HSV2BGR).reshape(-1, 3).astype(np.float32)
    # bare paper: the brightest clusters covering ~18 % of the area
    Lc = cen[:, 0]; order = np.argsort(-Lc); share = np.bincount(lbl.ravel(), minlength=k) / lbl.size
    bare = np.zeros(k, bool); acc = 0.0
    for i in order:
        if acc >= 0.15: break
        bare[i] = True; acc += share[i]
    up = cv2.resize(lbl, (out_w, out_h), interpolation=cv2.INTER_NEAREST)
    up = cv2.medianBlur(up, 9)
    col = pal[up]                                                               # BGR float
    al = np.where(bare[up], 0.0, 0.78).astype(np.float32)
    if warm:                                                                    # opt-in: warm bright clusters (sand) get a light wash, not bare paper
        wb = bare & (cen[:, 2] > 136)
        al = np.where(wb[up], 0.5, al).astype(np.float32)
    # edge pooling (darker rim where two colours meet), then soften like wet paint
    edge = cv2.Canny(up * 20, 1, 1).astype(np.float32) / 255.0
    edge = cv2.GaussianBlur(cv2.dilate(edge, np.ones((3, 3), np.uint8)), (0, 0), 1.6)
    col = col * (1 - 0.06 * np.clip(edge * 3, 0, 1))[..., None]
    rng = np.random.default_rng(seed)
    blot = cv2.GaussianBlur(rng.random((out_h // 8 + 1, out_w // 8 + 1)).astype(np.float32), (0, 0), 2)
    blot = cv2.resize(blot, (out_w, out_h)); blot = (blot - blot.mean()) / (blot.std() + 1e-6)
    al = al * np.clip(1 + 0.12 * blot, 0.6, 1.2)
    if near:                                                                    # background washes paler so the subject reads first
        msk = np.zeros((out_h, out_w), np.uint8)
        cv2.fillPoly(msk, [np.array([[x * out_w, y * out_h] for x, y in poly], np.int32) for poly in near], 1)
        msk = cv2.GaussianBlur(msk.astype(np.float32), (0, 0), 12); al = al * (0.5 + 0.5 * msk)
        col = col * (0.75 + 0.25 * msk[..., None]) + 255 * (0.25 - 0.25 * msk[..., None])
    col = cv2.GaussianBlur(col, (0, 0), 2.2); al = cv2.GaussianBlur(al, (0, 0), 2.6)
    M = np.float32([[1, 0, 4], [0, 1, -3]])                                    # shifted against the lines
    col = cv2.warpAffine(col, M, (out_w, out_h), borderMode=cv2.BORDER_REPLICATE)
    al = cv2.warpAffine(al, M, (out_w, out_h), borderMode=cv2.BORDER_CONSTANT, borderValue=0)
    rgb = col[..., ::-1]
    return np.dstack([np.clip(rgb, 0, 255), np.clip(al * 255, 0, 255)]).astype(np.uint8)


def draw_order(ink, seed=3, start=(0.6, 0.6), subject=None):
    """pen order: the subject first (lines nearest `start`, crop-normalised), then outwards; each line traced along its length"""
    h, w = ink.shape; m = (ink > 0.2).astype(np.uint8)
    n, lab, st, cen = cv2.connectedComponentsWithStats(m, connectivity=8)
    rng = np.random.default_rng(seed)
    key = np.zeros(n, np.float32)
    key[1:] = np.hypot(cen[1:, 0] / w - start[0], (cen[1:, 1] / h - start[1]) * 0.8) + rng.normal(0, 0.03, n - 1)
    if subject:                                                                 # lines of the subject box are all drawn before anything else
        sx0, sy0, sx1, sy1 = subject; cx_, cy_ = cen[1:, 0] / w, cen[1:, 1] / h
        key[1:] += np.where((cx_ >= sx0) & (cx_ <= sx1) & (cy_ >= sy0) & (cy_ <= sy1), 0.0, 10.0)
    rk = np.zeros(n, np.float32); rk[1:] = np.argsort(np.argsort(key[1:])) / max(1, n - 2)
    yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)
    span = np.zeros(n, np.float32); span[1:] = 0.9 / max(1, n - 1) * 6
    x0 = st[:, cv2.CC_STAT_LEFT].astype(np.float32); ww = np.maximum(1, st[:, cv2.CC_STAT_WIDTH]).astype(np.float32)
    within = (xx - x0[lab]) / ww[lab]
    o = rk[lab] * 0.94 + within * span[lab]
    o = np.where(m > 0, o, cv2.dilate(o * m, np.ones((5, 5), np.uint8)))
    return np.clip(o, 0, 1).astype(np.float32)


def make_layers(photo, crop, out_w, out_h, near=None, quiet=None, cache_dir=None, start=(0.6, 0.6), subject=None, warm=False):
    key = hashlib.md5(repr((os.path.basename(photo), crop, out_w, out_h, near, quiet, tuple(start), subject, 'v5') + (('warm',) if warm else ())).encode()).hexdigest()[:12]
    cf = cache_dir and os.path.join(cache_dir, f'sketch_{key}.npz')
    if cf and os.path.exists(cf):
        z = np.load(cf); return z['ink'], z['wash'], z['order']
    bgr = _load(photo, crop)
    ink, sm = ink_layer(bgr, near, quiet)
    ink = cv2.resize(ink, (out_w, out_h), interpolation=cv2.INTER_AREA)
    ink = (np.clip(ink * 1.3, 0, 1) ** 0.7).astype(np.float32)            # keep lines dark after the downscale
    wash = wash_layer(sm, out_w, out_h, near=near, warm=warm)
    order = draw_order(ink, start=start, subject=subject)
    if cf: os.makedirs(cache_dir, exist_ok=True); np.savez_compressed(cf, ink=ink, wash=wash, order=order)
    return ink, wash, order


if __name__ == '__main__':                                                      # quick look: python3 sketch.py photo out.jpg x0 y0 x1 y1
    import sys
    from PIL import Image
    ph, out = sys.argv[1], sys.argv[2]; crop = list(map(int, sys.argv[3:7])) if len(sys.argv) > 6 else None
    import json
    ex = json.loads(sys.argv[7]) if len(sys.argv) > 7 else {}
    ink, wash, order = make_layers(ph, crop, 1000, 840, ex.get('near'), ex.get('quiet'))
    paper = np.ones((840, 1000, 3), np.float32) * np.array(PAPER, np.float32)
    a = wash[..., 3:4] / 255.0; pw = paper * (1 - a) + wash[..., :3] * a
    pw = pw * (1 - ink[..., None] * 0.9) + np.array((28, 26, 30)) * ink[..., None] * 0.9
    Image.fromarray(np.hstack([paper * (1 - ink[..., None] * 0.9), pw]).clip(0, 255).astype(np.uint8)).save(out, quality=90)
