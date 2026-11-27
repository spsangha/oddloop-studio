"""ep16 clinic-screen cards (PIL drawing, no AI): a simple side-view X-ray of one jaw joint (TMJ), face to the left.
Facts: Thangarajah et al., J Med Case Reports 2010;4:263 ("bilateral anterior dislocations": the condyle moves forward past
the articular eminence, the bump in front of the socket).
out = LOCKED: the jaw's ball (condyle) sits in front of the bump, the socket is empty (yellow ring)
in  = BACK IN: the condyle sits in its socket again
    python3 kwjawcard_gen.py        -> assets/real/tex/kw_tmj/{out,in}.png  1600x1000"""
import os, math, random
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', '..', 'assets', 'real', 'tex', 'kw_tmj'); os.makedirs(OUT, exist_ok=True)
FB = os.path.join(HERE, '..', 'Montserrat-Black.ttf'); FE = os.path.join(HERE, '..', 'Montserrat-ExtraBold.ttf')
W, H = 1600, 1000; PW, PH = 1300, 800; PX, PY = (W - PW) // 2, 150
TXT = (240, 244, 246); DIM = (120, 140, 150); YEL = (255, 214, 60); RED = (250, 90, 80); GRN = (110, 230, 140)
def font(p, s): return ImageFont.truetype(p, s)
FOSSA = (760, 330)                                # socket centre (panel px)
def under(x):                                     # underside of the skull base: bump (eminence) in front, socket behind it
    return 330 + 80 * math.exp(-((x - 520) / 85) ** 2) + 60 * math.exp(-((x - 900) / 45) ** 2) - 45 * math.exp(-((x - 760) / 75) ** 2)
def skull():
    m = Image.new('L', (PW, PH), 0); d = ImageDraw.Draw(m)
    d.polygon([(0, 0), (PW, 0)] + [(x, under(x)) for x in range(PW, -1, -10)], fill=190)
    d.ellipse((1010 - 55, 310 - 55, 1010 + 55, 310 + 55), fill=0)            # ear canal (dark)
    d.ellipse((1010 - 75, 310 - 75, 1010 + 75, 310 + 75), outline=230, width=10)
    for k in range(6): d.line((80 + k * 110, 60, 160 + k * 110, 200), fill=215, width=6)   # bone texture
    return m
def jaw(dx, dy, rot):
    m = Image.new('L', (PW, PH), 0); d = ImageDraw.Draw(m); cx, cy = FOSSA
    d.ellipse((cx - 72, cy - 34, cx + 72, cy + 50), fill=225)                # condyle (the ball)
    d.polygon([(cx - 50, cy + 20), (cx + 50, cy + 20), (cx + 42, cy + 120), (cx + 70, cy + 420), (cx + 80, cy + 700),
               (cx - 150, cy + 700), (cx - 120, cy + 420), (cx - 45, cy + 120)], fill=200)      # neck + ramus, down off the panel
    m = m.rotate(rot, center=(cx, cy), resample=Image.BICUBIC)
    o = Image.new('L', (PW, PH), 0); o.paste(m, (dx, dy)); return o
def card(locked):
    im = Image.new('RGB', (W, H), (14, 24, 34)); d = ImageDraw.Draw(im)
    d.rectangle((0, 0, W - 1, 120), fill=(20, 36, 50)); d.text((W // 2, 62), 'X-RAY: JAW JOINT', font=font(FB, 80), fill=TXT, anchor='mm')
    dx, dy, rot = (-330, 70, 14) if locked else (0, 0, 0)
    pan = ImageChops.lighter(skull(), jaw(dx, dy, rot))
    rnd = random.Random(3); nz = Image.effect_noise((PW, PH), 22).filter(ImageFilter.GaussianBlur(1))
    pan = ImageChops.add(pan.filter(ImageFilter.GaussianBlur(3.5)), ImageChops.multiply(nz, Image.new('L', (PW, PH), 60)))
    pan = ImageChops.lighter(pan, Image.new('L', (PW, PH), 22))
    im.paste(Image.merge('RGB', (pan, pan, pan)), (PX, PY)); d = ImageDraw.Draw(im)
    d.rectangle((PX, PY, PX + PW, PY + PH), outline=(60, 84, 100), width=6)
    fx, fy = PX + FOSSA[0], PY + FOSSA[1]
    if locked:
        d.ellipse((fx - 95, fy - 70, fx + 95, fy + 80), outline=YEL, width=9)
        d.text((fx + 120, fy + 150), 'EMPTY SOCKET', font=font(FB, 54), fill=YEL, anchor='lm')
        d.line((fx + 60, fy + 70, fx + 115, fy + 140), fill=YEL, width=8)
        bx, by = fx - 330, fy + 70                                            # where the ball ended up
        d.line((fx - 110, fy - 110, bx + 40, by - 150), fill=RED, width=14)
        d.polygon([(bx + 10, by - 150), (bx + 70, by - 185), (bx + 62, by - 112)], fill=RED)
        d.text((W // 2, PY + PH - 60), 'OUT OF SOCKET', font=font(FB, 76), fill=RED, anchor='mm')
    else:
        d.ellipse((fx - 95, fy - 70, fx + 95, fy + 80), outline=GRN, width=9)
        d.text((W // 2, PY + PH - 60), 'BACK IN', font=font(FB, 76), fill=GRN, anchor='mm')
    d.text((PX + 40, PY + 40), 'FRONT', font=font(FE, 40), fill=DIM, anchor='lm')
    return im
if __name__ == '__main__':
    card(True).save(os.path.join(OUT, 'out.png')); card(False).save(os.path.join(OUT, 'in.png')); print('cards ->', OUT)
