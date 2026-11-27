"""ep13 clinic-screen cards (PIL, no AI): a simplified side-face tracing and the crossbite numbers
(Harari et al. Laryngoscope 2010: crossbite 49% mouth breathers vs 26% nose breathers).
card0 = normal tracing, cardA = + longer face overlay (jaw rotated down and back), cardB = crossbite bars.  1600x1000."""
import os, math
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', '..', 'assets', 'real', 'tex', 'kw_mouth'); os.makedirs(OUT, exist_ok=True)
FB = os.path.join(HERE, '..', 'Montserrat-Black.ttf'); FE = os.path.join(HERE, '..', 'Montserrat-ExtraBold.ttf')
W, H = 1600, 1000
def font(p, s): return ImageFont.truetype(p, s)
def base(title):
    im = Image.new('RGB', (W, H), (14, 24, 34)); d = ImageDraw.Draw(im)
    d.rectangle((0, 0, W - 1, 120), fill=(20, 36, 50))
    d.text((W // 2, 62), title, font=font(FB, 84), fill=(240, 244, 246), anchor='mm')
    return im
# side profile facing left, pixel coords; upper face fixed, lower face points rotate about the jaw joint J
UP = [(700, 170), (640, 230), (615, 330), (600, 410), (560, 470), (520, 545), (585, 565), (590, 600)]   # forehead -> nose -> under nose
LOW = [(565, 625), (600, 650), (590, 690), (575, 735), (590, 790), (640, 830), (720, 845), (820, 820), (900, 760)]  # lips -> chin -> under jaw
J = (930, 520)
def rot(p, a, piv=J):
    x, y = p[0] - piv[0], p[1] - piv[1]; c, s = math.cos(a), math.sin(a)
    return (piv[0] + x * c - y * s, piv[1] + x * s + y * c)
def lower(a, stretch=0):
    return [rot((x, y + stretch * max(0, (y - 600)) / 245), a) for x, y in LOW]
def smooth(P, n=10):
    P = [P[0]] + list(P) + [P[-1]]; out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for k in range(n):
            t = k / n; t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * (2 * p1[j] + (-p0[j] + p2[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t2 + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t3) for j in (0, 1)))
    return out + [P[-2]]
def tracing(im, a, col, w=10, stretch=0, only_low=False):
    d = ImageDraw.Draw(im); pts = smooth((UP[-1:] if only_low else UP) + lower(a, stretch))
    d.line(pts, fill=col, width=w, joint='curve')
    lo = lower(a, stretch); d.line([J, lo[-1], lo[-3], lo[-4]], fill=col, width=max(4, w - 4), joint='curve')   # jaw line
    d.ellipse((J[0] - 14, J[1] - 14, J[0] + 14, J[1] + 14), outline=col, width=5)
    return lo
def card0():
    im = base('FACE GROWTH'); tracing(im, 0.0, (150, 226, 212))
    d = ImageDraw.Draw(im); d.text((1120, 400), 'NOSE', font=font(FE, 60), fill=(150, 226, 212), anchor='lm')
    d.text((1120, 480), 'BREATHER', font=font(FE, 60), fill=(150, 226, 212), anchor='lm')
    return im
def cardA():
    im = card0(); d = ImageDraw.Draw(im)
    lo = tracing(im, math.radians(-9), (250, 120, 110), 10, stretch=30, only_low=True)
    a0 = LOW[5]; a1 = lo[5]
    d.line([a0, a1], fill=(250, 200, 90), width=8)
    d.polygon([a1, (a1[0] - 24, a1[1] - 22), (a1[0] + 18, a1[1] - 30)], fill=(250, 200, 90))
    d.text((1120, 640), 'MOUTH', font=font(FE, 60), fill=(250, 120, 110), anchor='lm')
    d.text((1120, 720), 'BREATHER', font=font(FE, 60), fill=(250, 120, 110), anchor='lm')
    return im
def cardB():
    im = base('CROSSBITE'); d = ImageDraw.Draw(im); x0, x1 = 110, 1490; full = x1 - x0
    for y0 in (220, 560): d.rounded_rectangle((x0, y0, x1, y0 + 180), 18, outline=(60, 84, 100), width=6)
    d.rounded_rectangle((x0, 220, x0 + int(full * 0.49), 400), 18, fill=(250, 120, 110))
    d.text((x0 + 40, 310), '49%', font=font(FB, 110), fill=(30, 12, 10), anchor='lm')
    d.text((x0 + int(full * 0.49) + 40, 310), 'MOUTH', font=font(FB, 96), fill=(250, 150, 140), anchor='lm')
    d.rounded_rectangle((x0, 560, x0 + int(full * 0.26), 740), 18, fill=(38, 190, 168))
    d.text((x0 + 40, 650), '26%', font=font(FB, 110), fill=(10, 28, 30), anchor='lm')
    d.text((x0 + int(full * 0.26) + 40, 650), 'NOSE', font=font(FB, 96), fill=(150, 226, 212), anchor='lm')
    d.text((W // 2, 880), 'HARARI ET AL. 2010', font=font(FE, 54), fill=(120, 140, 150), anchor='mm')
    return im
card0().save(os.path.join(OUT, 'card0.png')); cardA().save(os.path.join(OUT, 'cardA.png')); cardB().save(os.path.join(OUT, 'cardB.png'))
print('wrote', OUT)
