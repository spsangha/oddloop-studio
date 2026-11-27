"""ep22 clinic-screen cards (PIL drawing, no AI).  Facts: DermNet 'Aquagenic urticaria' (fewer than 100 cases reported;
main treatment a daily non-sedating antihistamine), Cleveland Clinic 'Rare allergies' (fewer than 100 cases).
    python3 kwwatercard_gen.py      -> assets/real/tex/kw_water/{cases,pills}.png  1600x1000"""
import os
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', '..', 'assets', 'real', 'tex', 'kw_water'); os.makedirs(OUT, exist_ok=True)
FB = os.path.join(HERE, '..', 'Montserrat-Black.ttf'); FE = os.path.join(HERE, '..', 'Montserrat-ExtraBold.ttf')
W, H = 1600, 1000
TXT = (240, 244, 246); DIM = (130, 150, 160); YEL = (255, 214, 60); CYA = (90, 200, 240)
def font(p, s): return ImageFont.truetype(p, s)
def base(title):
    im = Image.new('RGB', (W, H), (14, 24, 34)); d = ImageDraw.Draw(im)
    d.rectangle((0, 0, W - 1, 130), fill=(20, 36, 50)); d.text((W // 2, 66), title, font=font(FB, 84), fill=TXT, anchor='mm'); return im, d
def cases():
    im, d = base('WATER ALLERGY')
    for i in range(100):                       # 100 dots, the reported cases fill fewer than all of them
        x = 300 + (i % 20) * 50; y = 230 + (i // 20) * 62
        d.ellipse((x - 17, y - 17, x + 17, y + 17), fill=CYA if i < 77 else (40, 56, 70))
    d.text((W // 2, 640), '<100 CASES', font=font(FB, 150), fill=YEL, anchor='mm')
    d.text((W // 2, 790), 'EVER REPORTED', font=font(FE, 64), fill=TXT, anchor='mm')
    d.text((W // 2, 925), 'DERMNET / CLEVELAND CLINIC', font=font(FE, 38), fill=DIM, anchor='mm'); return im
def pills():
    im, d = base('TREATMENT')
    for k in range(3):
        x = 470 + k * 330; y = 400
        d.rounded_rectangle((x - 120, y - 52, x + 120, y + 52), 52, fill=(235, 238, 242))
        d.rounded_rectangle((x, y - 52, x + 120, y + 52), 52, fill=CYA); d.rectangle((x, y - 52, x + 52, y + 52), fill=CYA)
    d.text((W // 2, 640), 'ANTIHISTAMINE', font=font(FB, 130), fill=YEL, anchor='mm')
    d.text((W // 2, 790), 'ONE A DAY', font=font(FE, 64), fill=TXT, anchor='mm')
    d.text((W // 2, 925), 'ASK A DOCTOR', font=font(FE, 38), fill=DIM, anchor='mm'); return im
if __name__ == '__main__':
    cases().save(os.path.join(OUT, 'cases.png')); pills().save(os.path.join(OUT, 'pills.png')); print('cards ->', OUT)
