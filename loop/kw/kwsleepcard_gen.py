"""ep17 clinic-screen cards (PIL drawing, no AI).
Facts: Dawson & Reid, Nature 1997;388:235 (40 people, 28 h awake; hand-eye tracking task; 17 h = 0.05 % BAC, 24 h = ~0.10 %);
Sundelin et al., Sleep 2013;36:1355 (faces after sleep loss rated more fatigued and more sad).
test17 / test24 = a tracking test: the target line and his (wobblier) trace + the alcohol equivalent
chart  = relative performance falling with hours awake (10-26 h), the 0.05 % and 0.10 % levels marked
faces  = the same face rested / after no sleep (two stills of the episode itself) -> 'RATED SADDER'
    python3 kwsleepcard_gen.py [rested.png tired.png]       -> assets/real/tex/kw_sleep/*.png  1600x1000"""
import os, sys, math, random
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', '..', 'assets', 'real', 'tex', 'kw_sleep'); os.makedirs(OUT, exist_ok=True)
FB = os.path.join(HERE, '..', 'Montserrat-Black.ttf'); FE = os.path.join(HERE, '..', 'Montserrat-ExtraBold.ttf')
W, H = 1600, 1000
TXT = (240, 244, 246); DIM = (120, 140, 150); YEL = (255, 214, 60); RED = (250, 90, 80); CYA = (90, 210, 240)
def font(p, s): return ImageFont.truetype(p, s)
def base(title, col=TXT):
    im = Image.new('RGB', (W, H), (14, 24, 34)); d = ImageDraw.Draw(im)
    d.rectangle((0, 0, W - 1, 120), fill=(20, 36, 50)); d.text((W // 2, 62), title, font=font(FB, 80), fill=col, anchor='mm')
    return im, d
def test(hours, bac, wob):
    im, d = base(f'{hours} HOURS AWAKE')
    x0, x1, yc = 120, W - 120, 470; rnd = random.Random(hours)
    d.rectangle((x0 - 20, 180, x1 + 20, 760), outline=(50, 74, 90), width=4)
    tgt = [(x, yc + 170 * math.sin((x - x0) / 150.0)) for x in range(x0, x1, 6)]
    d.line(tgt, fill=CYA, width=12)
    ph = 0.0; tr = []
    for x, y in tgt:
        ph += rnd.uniform(-1, 1) * 0.35; tr.append((x, y + wob * (55 * math.sin((x - x0) / 47.0 + ph) + rnd.uniform(-12, 12)) + wob * 40))
    d.line(tr, fill=RED, width=9)
    d.text((x0, 210), 'TARGET', font=font(FE, 44), fill=CYA, anchor='lm'); d.text((x0 + 260, 210), 'HIS HAND', font=font(FE, 44), fill=RED, anchor='lm')
    d.text((W // 2, 870), f'= {bac} BLOOD ALCOHOL', font=font(FB, 92), fill=YEL, anchor='mm')
    return im
def chart():
    im, d = base('40 PEOPLE, 28 HOURS AWAKE')
    X0, X1, Y0, Y1 = 220, 1480, 220, 820
    d.line((X0, Y0, X0, Y1, X1, Y1), fill=DIM, width=6)
    hx = lambda h: X0 + (h - 10) / 16 * (X1 - X0)
    py = lambda p: Y1 - (p - 0.86) / 0.16 * (Y1 - Y0)      # relative performance 0.86 .. 1.02
    pts = [(hx(h), py(1.0 - 0.0074 * max(0, h - 10))) for h in range(10, 27)]
    d.line(pts, fill=RED, width=12)
    for h, lab in ((17, '0.05%'), (24, '0.10%')):
        x, y = hx(h), py(1.0 - 0.0074 * (h - 10)); d.line((x, y, x, Y1), fill=YEL, width=5); d.ellipse((x - 16, y - 16, x + 16, y + 16), fill=YEL)
        d.text((x, y - 50), lab, font=font(FB, 58), fill=YEL, anchor='mm'); d.text((x, Y1 + 50), f'{h} h', font=font(FE, 46), fill=TXT, anchor='mm')
    d.text((X0 - 30, Y0 + 10), 'HAND-EYE SCORE', font=font(FE, 40), fill=DIM, anchor='lm')
    d.text(((X0 + X1) // 2, Y1 + 120), 'HOURS AWAKE', font=font(FE, 40), fill=DIM, anchor='mm')
    return im
def faces(a, b):
    im, d = base('STRANGERS RATED THEM')
    for k, (p, lab, col) in enumerate(((a, 'SLEPT', TXT), (b, 'SADDER', RED))):
        box = (110 + k * 720, 160, 110 + k * 720 + 660, 820)
        if p and os.path.exists(p):
            s = Image.open(p).convert('RGB'); w, h = s.size; cw = w; ch = cw; cx, cy = w // 2, int(h * 0.42)
            s = s.crop((cx - cw // 2, max(0, cy - ch // 2), cx + cw // 2, max(0, cy - ch // 2) + ch)).resize((box[2] - box[0], box[3] - box[1]), Image.LANCZOS)
            im.paste(s, box[:2])
        else: d.rectangle(box, fill=(70, 80, 90))
        d.rectangle(box, outline=(60, 84, 100), width=8); d.text(((box[0] + box[2]) // 2, 880), lab, font=font(FB, 70), fill=col, anchor='mm')
    d.text((110 + 720 + 330, 945), 'NO SLEEP', font=font(FE, 40), fill=DIM, anchor='mm'); d.text((110 + 330, 945), '8 HOURS', font=font(FE, 40), fill=DIM, anchor='mm')
    return im
if __name__ == '__main__':
    a = sys.argv[1] if len(sys.argv) > 1 else None; b = sys.argv[2] if len(sys.argv) > 2 else None
    test(17, '0.05%', 0.55).save(os.path.join(OUT, 'test17.png')); test(24, '0.10%', 1.0).save(os.path.join(OUT, 'test24.png'))
    chart().save(os.path.join(OUT, 'chart.png')); faces(a, b).save(os.path.join(OUT, 'faces.png')); print('cards ->', OUT)
