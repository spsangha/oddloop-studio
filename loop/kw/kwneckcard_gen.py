"""ep19 clinic-screen cards (PIL drawing, no AI): a simple side view of the head and neck with the vertebral artery running up
the back of the neck into the base of the brain.  Facts: NBC News / Washington Post 2019 (a small tear in a vertebral artery
formed a clot that blocked blood to the brain; tPA dissolves the clot).
clot = TORN + CLOT: a tear and a dark clot in the artery, the artery above it and the back of the brain dim (no blood)
open = FLOW BACK: the clot is gone, the artery is red all the way up
    python3 kwneckcard_gen.py        -> assets/real/tex/kw_neck/{clot,open}.png  1600x1000"""
import os, math
from PIL import Image, ImageDraw, ImageFont, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', '..', 'assets', 'real', 'tex', 'kw_neck'); os.makedirs(OUT, exist_ok=True)
FB = os.path.join(HERE, '..', 'Montserrat-Black.ttf')
W, H = 1600, 1000
TXT = (240, 244, 246); YEL = (255, 214, 60); RED = (235, 60, 55); DRED = (90, 20, 24); GRN = (110, 230, 140); DIM = (95, 70, 75)
def font(s): return ImageFont.truetype(FB, s)
def path():                                        # artery: from the neck base up to the brain (face looks left)
    pts = []
    for i in range(41):
        u = i / 40; y = 930 - 520 * u
        x = 905 + 18 * math.sin(u * 7.0) + (40 * (u - 0.75) / 0.25 if u > 0.75 else 0)
        pts.append((x, y))
    return pts
def card(clot):
    im = Image.new('RGB', (W, H), (14, 24, 34)); d = ImageDraw.Draw(im)
    # head + neck silhouette (side view, face to the left)
    sil = Image.new('L', (W, H), 0); s = ImageDraw.Draw(sil)
    s.ellipse((560, 150, 1060, 600), fill=255)                                   # skull
    s.polygon([(600, 420), (560, 470), (590, 520), (570, 560), (640, 640), (720, 660), (760, 720)], fill=255)   # face / jaw
    s.polygon([(760, 560), (1010, 520), (1040, 1000), (720, 1000)], fill=255)    # neck
    sil = sil.filter(ImageFilter.GaussianBlur(4))
    im.paste((48, 62, 74), (0, 0), sil); d = ImageDraw.Draw(im)
    d.ellipse((640, 200, 1000, 470), fill=(70, 86, 100))                          # brain
    back = (860, 330, 1000, 470)
    d.ellipse(back, fill=(60, 44, 50) if clot else (150, 70, 78))                 # back of the brain (fed by this artery)
    for k in range(8): d.rectangle((900, 560 + k * 52, 960, 600 + k * 52), fill=(110, 124, 136))   # neck bones
    P = path(); cut = 22
    if clot:
        d.line(P[:cut], fill=RED, width=26, joint='curve'); d.line(P[cut:], fill=DIM, width=22, joint='curve')
        cx, cy = P[cut]; d.ellipse((cx - 34, cy - 40, cx + 34, cy + 40), fill=DRED, outline=(30, 6, 8), width=6)
        zz = [(cx - 70 + 14 * k, cy + 70 + (18 if k % 2 else -18)) for k in range(11)]
        d.line(zz, fill=YEL, width=7)
        d.text((cx - 120, cy + 120), 'TEAR', font=font(54), fill=YEL, anchor='rm')
        d.line((cx + 50, cy, cx + 180, cy - 30), fill=TXT, width=6); d.text((cx + 195, cy - 30), 'CLOT', font=font(62), fill=TXT, anchor='lm')
        d.text((1030, 260), 'NO BLOOD', font=font(54), fill=RED, anchor='lm'); d.line((1025, 280, 975, 340), fill=RED, width=6)
        foot = ('BLOCKED', RED)
    else:
        d.line(P, fill=RED, width=26, joint='curve')
        d.text((1030, 260), 'BLOOD BACK', font=font(54), fill=GRN, anchor='lm')
        foot = ('FLOW BACK', GRN)
    d.rectangle((0, 0, W - 1, 120), fill=(20, 36, 50)); d.text((W // 2, 62), 'SCAN: NECK ARTERY', font=font(78), fill=TXT, anchor='mm')
    d.text((330, 880), foot[0], font=font(84), fill=foot[1], anchor='mm')
    return im
if __name__ == '__main__':
    card(True).save(os.path.join(OUT, 'clot.png')); card(False).save(os.path.join(OUT, 'open.png')); print('cards ->', OUT)
