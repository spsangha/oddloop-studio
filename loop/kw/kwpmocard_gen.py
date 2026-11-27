"""ep15 clinic-screen cards (PIL, no AI).  Facts: Mello et al., The Lancet 2024;403:1176.
photo  = Maya's face as a photo on the screen (looks normal to the patient)       <- a still of the episode itself (KW15_DEMON=0)
edited = the same photo edited to match what he sees in person                    <- the same still with the stretch keys on
mri    = a simple coronal MRI-style slice (T2: fluid bright) with the ~1 cm round cyst on top of the left hippocampus head.
    python3 kwpmocard_gen.py [photo_still.png edited_still.png]      (no stills -> grey placeholders)   1600x1000."""
import os, sys, math, random
from PIL import Image, ImageDraw, ImageFont, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(HERE, '..', '..', 'assets', 'real', 'tex', 'kw_pmo'); os.makedirs(OUT, exist_ok=True)
FB = os.path.join(HERE, '..', 'Montserrat-Black.ttf'); FE = os.path.join(HERE, '..', 'Montserrat-ExtraBold.ttf')
W, H = 1600, 1000
TXT = (240, 244, 246); DIM = (120, 140, 150); YEL = (255, 214, 60); RED = (250, 90, 80)
def font(p, s): return ImageFont.truetype(p, s)
def base(title, col=TXT):
    im = Image.new('RGB', (W, H), (14, 24, 34)); d = ImageDraw.Draw(im)
    d.rectangle((0, 0, W - 1, 120), fill=(20, 36, 50)); d.text((W // 2, 62), title, font=font(FB, 84), fill=col, anchor='mm')
    return im
def face_card(still, title, col):
    im = base(title, col); d = ImageDraw.Draw(im)
    box = (W // 2 - 400, 150, W // 2 + 400, 970)
    if still and os.path.exists(still):
        s = Image.open(still).convert('RGB'); w, h = s.size
        cw = int(w * 0.80); ch = int(cw * (box[3] - box[1]) / (box[2] - box[0])); cx, cy = w // 2, int(h * 0.42)
        s = s.crop((cx - cw // 2, max(0, cy - ch // 2), cx + cw // 2, max(0, cy - ch // 2) + ch)).resize((box[2] - box[0], box[3] - box[1]), Image.LANCZOS)
        im.paste(s, box[:2])
    else: d.rectangle(box, fill=(70, 80, 90))
    d.rectangle(box, outline=(60, 84, 100), width=8)
    return im
def mri():
    im = base('MRI'); rnd = random.Random(7)
    sl = Image.new('L', (900, 820), 0); d = ImageDraw.Draw(sl); cx, cy = 450, 420
    d.ellipse((cx - 330, cy - 370, cx + 330, cy + 350), fill=70)                  # scalp / skull
    d.ellipse((cx - 305, cy - 345, cx + 305, cy + 325), fill=18)
    d.ellipse((cx - 290, cy - 330, cx + 290, cy + 300), fill=120)                 # brain
    for _ in range(260):                                                          # sulci (fluid = bright on T2)
        a = rnd.uniform(0, 2 * math.pi); r = rnd.uniform(0.55, 0.98); x = cx + 285 * r * math.cos(a); y = cy - 15 + 310 * r * math.sin(a)
        L_ = rnd.uniform(14, 34); b = a + math.pi / 2 + rnd.uniform(-0.5, 0.5)
        d.line((x, y, x + L_ * math.cos(b), y + L_ * math.sin(b)), fill=rnd.randint(150, 185), width=3)
    d.line((cx, cy - 330, cx, cy + 60), fill=175, width=5)                         # midline fissure
    for s in (-1, 1):                                                             # lateral ventricles
        d.polygon([(cx + s * 8, cy - 130), (cx + s * 70, cy - 105), (cx + s * 60, cy - 70), (cx + s * 8, cy - 80)], fill=210)
        d.ellipse((cx + s * 150 - 55, cy + 95, cx + s * 150 + 55, cy + 150), fill=95)          # hippocampi (grey)
    d.rectangle((cx - 60, cy + 210, cx + 60, cy + 300), fill=105)                  # brainstem
    sl = sl.filter(ImageFilter.GaussianBlur(2.2))
    d = ImageDraw.Draw(sl); hx, hy = cx + 150, cy + 82                             # patient's LEFT = image right (radiology)
    d.ellipse((hx - 22, hy - 22, hx + 22, hy + 22), fill=250)                     # the ~1 cm cyst, T2 bright, on top of the left hippocampus
    sl = sl.filter(ImageFilter.GaussianBlur(1.0))
    im.paste(Image.merge('RGB', (sl, sl, sl)), (W // 2 - 450, 150))
    d = ImageDraw.Draw(im); X, Y = W // 2 - 450 + hx, 150 + hy
    d.ellipse((X - 52, Y - 52, X + 52, Y + 52), outline=YEL, width=9)
    d.line((X + 50, Y - 40, X + 210, Y - 170), fill=YEL, width=9)
    d.text((X + 225, Y - 190), 'CYST', font=font(FB, 80), fill=YEL, anchor='lm')
    d.text((W // 2 + 470, 930), 'L', font=font(FE, 60), fill=DIM, anchor='mm')
    return im
if __name__ == '__main__':
    a = sys.argv[1] if len(sys.argv) > 1 else None; b = sys.argv[2] if len(sys.argv) > 2 else None
    face_card(a, 'PHOTO: LOOKS FINE', TXT).save(os.path.join(OUT, 'photo.png'))
    face_card(b, 'EDITED TO MATCH', YEL).save(os.path.join(OUT, 'edited.png'))
    mri().save(os.path.join(OUT, 'mri.png'))
    print('cards ->', OUT)
