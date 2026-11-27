"""ep14 clinic-screen cards (PIL, no AI).  Facts: ASU Embryo Project, Lydia Fairchild case (2002).
card0 = three DNA tests, empty result column; cardA = same with NO MATCH x3 (revealed top-down); cardB = baby test NO MATCH;
cardC = body outline: hair/cheek/skin/blood = DNA 1 (blue), cervix swab = DNA 2 matching the kids (orange).  1600x1000."""
import os
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', '..', 'assets', 'real', 'tex', 'kw_dna'); os.makedirs(OUT, exist_ok=True)
FB = os.path.join(HERE, '..', 'Montserrat-Black.ttf'); FE = os.path.join(HERE, '..', 'Montserrat-ExtraBold.ttf')
W, H = 1600, 1000
BLUE = (90, 170, 255); ORANGE = (255, 150, 60); RED = (250, 90, 80); TXT = (240, 244, 246); DIM = (120, 140, 150)
def font(p, s): return ImageFont.truetype(p, s)
def base(title):
    im = Image.new('RGB', (W, H), (14, 24, 34)); d = ImageDraw.Draw(im)
    d.rectangle((0, 0, W - 1, 120), fill=(20, 36, 50))
    d.text((W // 2, 62), title, font=font(FB, 84), fill=TXT, anchor='mm')
    return im
ROWS = (270, 520, 770)
def card0(res=False):
    im = base('DNA TEST: MOTHER?'); d = ImageDraw.Draw(im)
    for i, y in enumerate(ROWS):
        d.rounded_rectangle((90, y - 95, W - 90, y + 95), 18, outline=(60, 84, 100), width=6)
        d.text((150, y), f'TEST {i + 1}', font=font(FE, 80), fill=TXT, anchor='lm')
        if res: d.text((W - 150, y), 'NO MATCH', font=font(FB, 104), fill=RED, anchor='rm')
    return im
def cardB():
    im = base('NEW BABY: MOTHER?'); d = ImageDraw.Draw(im)
    d.rounded_rectangle((90, 300, W - 90, 640), 24, outline=RED, width=10)
    d.text((W // 2, 470), 'NO MATCH', font=font(FB, 190), fill=RED, anchor='mm')
    d.text((W // 2, 800), 'COURT OFFICER AT THE BIRTH', font=font(FE, 60), fill=DIM, anchor='mm')
    return im
def cardC():
    im = base('TWO DNA SETS'); d = ImageDraw.Draw(im)
    cx = 470; col = (150, 170, 185); w = 12
    R_ = [(30, 300), (34, 335), (150, 360), (185, 395), (215, 640), (175, 652), (140, 430), (128, 600), (118, 960), (40, 960), (14, 700)]
    poly = [(cx + x, y) for x, y in R_] + [(cx - x, y) for x, y in reversed(R_)]
    d.polygon(poly, fill=(40, 58, 72), outline=col); d.line(poly + [poly[0]], fill=col, width=8, joint='curve')
    d.ellipse((cx - 68, 165, cx + 68, 310), fill=(40, 58, 72), outline=col, width=8)
    def dot(p, c, r=26): d.ellipse((p[0] - r, p[1] - r, p[0] + r, p[1] + r), fill=c)
    for p in ((cx, 172), (cx + 38, 255), (cx - 168, 470), (cx + 196, 646)): dot(p, BLUE)          # hair, cheek, skin, blood
    dot((cx, 640), ORANGE, 34)                                                                     # cervix swab
    x = 860
    d.text((x, 300), 'HAIR  CHEEK', font=font(FE, 58), fill=BLUE, anchor='lm')
    d.text((x, 375), 'SKIN  BLOOD', font=font(FE, 58), fill=BLUE, anchor='lm')
    d.text((x, 460), 'DNA 1', font=font(FB, 96), fill=BLUE, anchor='lm')
    d.text((x, 640), 'CERVIX', font=font(FE, 58), fill=ORANGE, anchor='lm')
    d.text((x, 725), 'DNA 2', font=font(FB, 96), fill=ORANGE, anchor='lm')
    d.text((x, 820), '= HER KIDS', font=font(FE, 64), fill=ORANGE, anchor='lm')
    return im
card0().save(os.path.join(OUT, 'card0.png')); card0(True).save(os.path.join(OUT, 'cardA.png'))
cardB().save(os.path.join(OUT, 'cardB.png')); cardC().save(os.path.join(OUT, 'cardC.png'))
print('wrote', OUT)
