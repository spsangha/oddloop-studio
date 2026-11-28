#!/usr/bin/env python3
"""looks review sheet: python3 looksheet.py out.jpg look old.png still1.png ... (tiles 540 px, labelled look + time; last tile OLD | NEW)"""
import sys, re
from PIL import Image, ImageDraw, ImageFont
out, look, old = sys.argv[1], sys.argv[2], sys.argv[3]; fs = sys.argv[4:]
f = ImageFont.truetype('/usr/local/share/fonts/asi-document/Montserrat-Bold.ttf', 24)
tiles = [(Image.open(p).convert('RGB').resize((540, 960), Image.LANCZOS), f"{look}  {float(re.search(r't([\d.]+)\.png', p).group(1)):.1f} s") for p in fs]
on = Image.new('RGB', (540, 960), (24, 26, 30)); a = Image.open(old).convert('RGB').resize((266, 473), Image.LANCZOS); b = Image.open(fs[0]).convert('RGB').resize((266, 473), Image.LANCZOS)
on.paste(a, (2, 240)); on.paste(b, (272, 240)); d = ImageDraw.Draw(on)
d.text((10, 200), 'OLD  (v5, 0.0 s)', font=f, fill=(235, 235, 235)); d.text((280, 200), f'NEW  ({look}, 0.0 s)', font=f, fill=(255, 200, 61))
tiles.append((on, 'OLD | NEW'))
cols = 4; rows = (len(tiles) + cols - 1) // cols
S = Image.new('RGB', (cols * 548 + 8, rows * (960 + 42) + 8), (24, 26, 30)); D = ImageDraw.Draw(S)
for i, (im, lab) in enumerate(tiles):
    x = 8 + (i % cols) * 548; y = 8 + (i // cols) * 1002; S.paste(im, (x, y + 34)); D.text((x + 4, y + 4), lab, font=f, fill=(235, 235, 235))
S.save(out, quality=88); print('wrote', out, S.size)
