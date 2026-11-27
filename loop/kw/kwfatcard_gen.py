"""ep12 clinic-screen card (PIL, no AI): where 10 kg of fat goes (Meerman & Brown, BMJ 2014;349:g7257, Fig 2).
card0 = frame + header only, cardA = + the two bars, cardB = + the myth row (struck out).  1600x1000 (screen 0.46 x 0.2875 m)."""
import os
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', '..', 'assets', 'real', 'tex', 'kw_fat'); os.makedirs(OUT, exist_ok=True)
FB = os.path.join(HERE, '..', 'Montserrat-Black.ttf'); FE = os.path.join(HERE, '..', 'Montserrat-ExtraBold.ttf')
W, H = 1600, 1000
def font(p, s): return ImageFont.truetype(p, s)
def base():
    im = Image.new('RGB', (W, H), (14, 24, 34)); d = ImageDraw.Draw(im)
    d.rectangle((0, 0, W - 1, 120), fill=(20, 36, 50))
    d.text((W // 2, 62), '10 KG OF FAT', font=font(FB, 84), fill=(240, 244, 246), anchor='mm')
    return im
def bars(im):
    d = ImageDraw.Draw(im); x0, x1 = 110, 1490; full = x1 - x0
    for y0 in (200, 520): d.rounded_rectangle((x0, y0, x1, y0 + 180), 18, outline=(60, 84, 100), width=6)
    # bar 1: 8.4 kg exhaled as CO2 (84 %)
    d.rounded_rectangle((x0, 200, x0 + int(full * 0.84), 380), 18, fill=(38, 190, 168))
    d.text((x0 + 40, 290), '8.4 KG', font=font(FB, 96), fill=(10, 28, 30), anchor='lm')
    d.text((x0 + int(full * 0.84) - 40, 290), 'CO2', font=font(FB, 96), fill=(10, 28, 30), anchor='rm')
    d.text((x0, 430), 'BREATHED OUT', font=font(FE, 64), fill=(150, 226, 212), anchor='lm')
    # bar 2: 1.6 kg water (16 %)
    d.rounded_rectangle((x0, 520, x0 + int(full * 0.16), 700), 18, fill=(70, 140, 235))
    d.text((x0 + int(full * 0.16) + 40, 610), '1.6 KG WATER', font=font(FB, 96), fill=(170, 205, 250), anchor='lm')
    return im
def myth(im):
    d = ImageDraw.Draw(im)
    d.text((W // 2, 870), 'ENERGY?  HEAT?', font=font(FB, 92), fill=(250, 120, 110), anchor='mm')
    bb = d.textbbox((W // 2, 870), 'ENERGY?  HEAT?', font=font(FB, 92), anchor='mm')
    d.line((bb[0] - 20, 872, bb[2] + 20, 868), fill=(250, 120, 110), width=14)
    return im
base().save(os.path.join(OUT, 'card0.png')); a = bars(base()); a.save(os.path.join(OUT, 'cardA.png')); myth(a).save(os.path.join(OUT, 'cardB.png'))
print('wrote', OUT)
