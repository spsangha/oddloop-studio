"""ep11: the RETINA SCAN screen plate, drawn procedurally (no photo, no AI image).

    PYTHONPATH=<PIL> python3 kwretina_gen.py   -> assets/real/tex/kw_retina/{scan,mask,erg}.png

scan.png : the static screen (white UI frame, RETINA SCAN title, KINDA WILD corner, a clean stylised fundus, the signal panel)
mask.png : R = vessel mask, G = distance from the optic disc (0..1, for the 1.1 Hz pulse that travels out along the vessels)
erg.png  : R = the ERG wave line, G = the flat baseline line, B = the flash tick.  The shader reveals R left -> right after the
           flash and keeps G where the wave has not been drawn yet.
"""
import os, math, random
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', '..', 'assets', 'real', 'tex', 'kw_retina')
W, H = 1600, 1000
S = 2                                    # supersample
FONT = os.path.join(HERE, '..', 'Montserrat-Black.ttf')
FC, FR = (430, 575), 330                 # fundus centre, radius
DISC = (FC[0] - 150, FC[1] - 8)          # optic disc
PANEL = (860, 250, 1520, 860)            # signal panel
BASE_Y = 640
ERG_X0, ERG_X1 = 890, 1490
FLASH_T = 0.08


def erg_value(t):
    """clean ERG-style wave (px up from the baseline): a-wave dip, b-wave peak with three small oscillatory ripples, slow return"""
    if t < FLASH_T: return 0.0
    x = t - FLASH_T
    a = -62.0 * math.exp(-((x - 0.055) / 0.024) ** 2)
    b = 205.0 * (1 - math.exp(-max(0.0, x - 0.05) / 0.045)) * math.exp(-max(0.0, x - 0.05) / 0.16)
    op = 13.0 * math.sin((x - 0.06) * 2 * math.pi / 0.032) * math.exp(-((x - 0.13) / 0.035) ** 2) if x > 0.06 else 0.0
    under = -14.0 * math.exp(-((x - 0.62) / 0.12) ** 2)
    return a + b + op + under


def fundus(img, mask_r):
    rnd = random.Random(11)
    yy, xx = np.mgrid[0:H * S, 0:W * S].astype(np.float32) / S
    r = np.hypot(xx - FC[0], yy - FC[1]) / FR
    inside = r < 1.0
    # base: warm orange-red, darker toward the rim, soft low-frequency mottling (choroid), darker macula
    t = np.clip(r, 0, 1)
    base = np.stack([212 - 95 * t ** 1.6, 84 - 50 * t ** 1.6, 42 - 24 * t ** 1.6], -1)
    n = np.zeros_like(r)
    for k, (fx, fy, ph) in enumerate(((0.011, 0.013, 0.3), (0.023, 0.019, 1.7), (0.041, 0.037, 2.9))):
        n += np.sin(xx * fx + ph) * np.sin(yy * fy + 2 * ph) / (k + 1)
    base += n[..., None] * np.array([7, 3, 2])
    mac = np.exp(-(((xx - FC[0] - 45) ** 2 + (yy - FC[1] - 5) ** 2) / (2 * 62.0 ** 2)))
    base *= (1 - 0.30 * mac)[..., None]
    fov = np.exp(-(((xx - FC[0] - 45) ** 2 + (yy - FC[1] - 5) ** 2) / (2 * 10.0 ** 2)))
    base += fov[..., None] * np.array([30, 18, 8])
    # optic disc: pale yellow-pink with a bright cup
    rd = np.hypot(xx - DISC[0], yy - DISC[1])
    disc = np.clip((46 - rd) / 6.0, 0, 1)
    cup = np.clip((20 - rd) / 6.0, 0, 1)
    base = base * (1 - disc[..., None]) + np.array([244, 196, 140]) * disc[..., None]
    base = base * (1 - cup[..., None]) + np.array([255, 236, 196]) * cup[..., None]
    rim = np.clip((r - 0.97) / 0.03, 0, 1)
    base *= (1 - 0.85 * rim)[..., None]
    a = (np.clip((1.0 - r) * FR * S, 0, 1))
    # vessels: veins (dark, wide) then arteries (lighter, thinner) branching from the disc
    lay = Image.new('RGBA', (W * S, H * S), (0, 0, 0, 0)); dl = ImageDraw.Draw(lay)
    msk = Image.new('L', (W * S, H * S), 0); dm = ImageDraw.Draw(msk)
    def branch(x, y, ang, w, length, col, depth, curv=0.0):
        pts = [(x, y)]; cur = ang
        steps = int(length / 9)
        for i in range(steps):
            cur += rnd.uniform(-0.06, 0.06) + curv
            x += math.cos(cur) * 9; y += math.sin(cur) * 9
            if math.hypot(x - FC[0], y - FC[1]) > FR * 0.985: break
            pts.append((x, y))
            if depth < 3 and i > 4 and rnd.random() < 0.075:
                branch(x, y, cur + rnd.choice((-1, 1)) * rnd.uniform(0.45, 0.9), w * 0.62, length * 0.55, col, depth + 1, curv * 0.5)
        for i in range(len(pts) - 1):
            ww = max(1.2, w * (1 - 0.55 * i / max(1, len(pts))))
            seg = [(pts[i][0] * S, pts[i][1] * S), (pts[i + 1][0] * S, pts[i + 1][1] * S)]
            dl.line(seg, fill=col, width=int(ww * S)); dm.line(seg, fill=255, width=int(ww * S))
            r_ = ww * S / 2
            dl.ellipse([seg[1][0] - r_, seg[1][1] - r_, seg[1][0] + r_, seg[1][1] + r_], fill=col)
            dm.ellipse([seg[1][0] - r_, seg[1][1] - r_, seg[1][0] + r_, seg[1][1] + r_], fill=255)
    # arcades curve around the macula (temporal = toward +x), nasal branches fan out to -x
    for col, w, off in (((112, 18, 26, 255), 12.0, 0.10), ((222, 64, 44, 255), 8.5, -0.10)):
        for ang, curve_len, cv in ((-1.05 + off, 470, 0.024), (1.05 - off, 470, -0.024), (-2.35 + off, 240, 0.0), (2.35 - off, 240, 0.0), (-1.75, 200, 0.0), (1.8, 190, 0.0)):
            branch(DISC[0], DISC[1], ang, w, curve_len, col, 0, cv)
    lay = lay.filter(ImageFilter.GaussianBlur(0.6 * S))
    lv = np.asarray(lay).astype(np.float32) / 255.0
    base = base * (1 - lv[..., 3:4]) + lv[..., :3] * 255 * lv[..., 3:4]
    out = np.asarray(img).astype(np.float32).copy()
    out = out * (1 - a[..., None]) + base * a[..., None]
    mk = np.asarray(msk.filter(ImageFilter.GaussianBlur(0.8 * S))).astype(np.float32) / 255.0 * a
    dist = np.clip(np.hypot(xx - DISC[0], yy - DISC[1]) / (FR * 1.6), 0, 1)
    return out, mk, dist


def main():
    os.makedirs(OUT, exist_ok=True)
    img = Image.new('RGB', (W * S, H * S), (9, 17, 30)); d = ImageDraw.Draw(img)
    # soft vertical gradient background
    g = np.linspace(0, 1, H * S)[:, None, None]
    bg = np.array([9, 17, 30]) * (1 - g) + np.array([4, 9, 18]) * g
    img = Image.fromarray(np.broadcast_to(bg, (H * S, W * S, 3)).astype(np.uint8)); d = ImageDraw.Draw(img)
    # white UI frame
    d.rounded_rectangle([22 * S, 22 * S, (W - 22) * S, (H - 22) * S], radius=34 * S, outline=(238, 242, 246), width=10 * S)
    f_t = ImageFont.truetype(FONT, 66 * S); f_s = ImageFont.truetype(FONT, 34 * S); f_c = ImageFont.truetype(FONT, 30 * S)
    d.text((72 * S, 52 * S), 'RETINA SCAN', font=f_t, fill=(246, 248, 250))
    d.text((1300 * S, 74 * S), 'LEFT EYE', font=f_s, fill=(150, 170, 190))
    d.line([(60 * S, 160 * S), ((W - 60) * S, 160 * S)], fill=(238, 242, 246), width=4 * S)
    # signal panel
    x0, y0, x1, y1 = PANEL
    d.rounded_rectangle([x0 * S, y0 * S, x1 * S, y1 * S], radius=18 * S, outline=(70, 92, 118), width=3 * S)
    d.text(((x0 + 26) * S, (y0 + 20) * S), 'RETINA SIGNAL', font=f_s, fill=(150, 170, 190))
    for k in range(1, 6):     # faint grid
        yk = y0 + 90 + k * 85
        d.line([((x0 + 20) * S, yk * S), ((x1 - 20) * S, yk * S)], fill=(22, 36, 54), width=2 * S)
    d.text((1268 * S, 918 * S), 'KINDA WILD', font=f_c, fill=(214, 222, 230))
    arr, vmask, dist = fundus(img, None)
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    # erg layers
    erg = Image.new('RGB', (W * S, H * S), (0, 0, 0)); de = ImageDraw.Draw(erg)
    pts = [((ERG_X0 + (ERG_X1 - ERG_X0) * t) * S, (BASE_Y - erg_value(t)) * S) for t in np.linspace(0, 1, 900)]
    wave = Image.new('L', (W * S, H * S), 0); ImageDraw.Draw(wave).line(pts, fill=255, width=7 * S, joint='curve')
    basel = Image.new('L', (W * S, H * S), 0); ImageDraw.Draw(basel).line([(ERG_X0 * S, BASE_Y * S), (ERG_X1 * S, BASE_Y * S)], fill=255, width=5 * S)
    fx_ = (ERG_X0 + (ERG_X1 - ERG_X0) * FLASH_T) * S
    tick = Image.new('L', (W * S, H * S), 0); ImageDraw.Draw(tick).polygon([(fx_ - 16 * S, 330 * S), (fx_ + 16 * S, 330 * S), (fx_, 356 * S)], fill=255)
    ImageDraw.Draw(tick).line([(fx_, 362 * S), (fx_, 840 * S)], fill=110, width=2 * S)
    erg = Image.merge('RGB', (wave, basel, tick))
    msk = Image.fromarray(np.stack([np.clip(vmask * 255, 0, 255), np.clip(dist * 255, 0, 255), np.zeros_like(dist)], -1).astype(np.uint8))
    for im, nm in ((img, 'scan'), (msk, 'mask'), (erg, 'erg')):
        im.resize((W, H), Image.LANCZOS).save(os.path.join(OUT, nm + '.png'), optimize=True)
    print('wrote', OUT)


if __name__ == '__main__':
    main()
