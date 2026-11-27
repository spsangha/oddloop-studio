"""ep18 clinic-screen cards (PIL drawing, no AI).  Facts: Buijze et al., PLOS ONE 2016 (3,018 adults, showers ended with
30-90 s of cold water for 30 days): sickness absence -29 % (IRR 0.71) vs control; illness days: no significant difference.
    python3 kwcoldcard_gen.py      -> assets/real/tex/kw_cold/{work,sick}.png  1600x1000"""
import os
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', '..', 'assets', 'real', 'tex', 'kw_cold'); os.makedirs(OUT, exist_ok=True)
FB = os.path.join(HERE, '..', 'Montserrat-Black.ttf'); FE = os.path.join(HERE, '..', 'Montserrat-ExtraBold.ttf')
W, H = 1600, 1000
TXT = (240, 244, 246); DIM = (130, 150, 160); YEL = (255, 214, 60); CYA = (90, 200, 240); GRY = (150, 160, 170)
def font(p, s): return ImageFont.truetype(p, s)
def bars(title, b, big, sub):
    im = Image.new('RGB', (W, H), (14, 24, 34)); d = ImageDraw.Draw(im)
    d.rectangle((0, 0, W - 1, 130), fill=(20, 36, 50)); d.text((W // 2, 66), title, font=font(FB, 84), fill=TXT, anchor='mm')
    Y1, top = 800, 250; hmax = Y1 - top
    for k, (lab, v, col) in enumerate((('WARM ONLY', 1.0, GRY), ('COLD FINISH', b, CYA))):
        x = 330 + k * 560; h = int(hmax * v)
        d.rounded_rectangle((x, Y1 - h, x + 380, Y1), 16, fill=col)
        d.text((x + 190, Y1 + 60), lab, font=font(FE, 52), fill=TXT, anchor='mm')
    d.line((240, Y1, W - 240, Y1), fill=DIM, width=6)
    d.text((330 + 560 + 190, Y1 - int(hmax * b) - 80), big, font=font(FB, 110), fill=YEL, anchor='mm')
    d.text((W // 2, 935), sub, font=font(FE, 40), fill=DIM, anchor='mm')
    return im
if __name__ == '__main__':
    bars('SICK DAYS OFF WORK', 0.71, '-29%', '3,018 PEOPLE, 30 DAYS').save(os.path.join(OUT, 'work.png'))
    bars('TIMES THEY GOT SICK', 1.0, 'SAME', 'NO REAL DIFFERENCE').save(os.path.join(OUT, 'sick.png'))
    print('cards ->', OUT)
