#!/usr/bin/env python3
"""Contact sheets for the human look-through (template v5).

  python3 sheets.py <reel_folder>
writes contact_sheet_1s.jpg   (every whole second, 0 .. end)
       contact_sheet_0-3s.jpg (0, 0.5, 1, 1.5, 2, 2.5, 3 s at larger size, with the safe zone and UI floor outlined)
"""
import json, os, subprocess, sys
from PIL import Image, ImageDraw, ImageFont

D = os.path.abspath(sys.argv[1]); job = json.load(open(f'{D}/job.json')); mp4 = f"{D}/{job['out']}"
dur = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', mp4], capture_output=True, text=True).stdout)
FONT = '/usr/local/share/fonts/asi-document/Montserrat-Bold.ttf'
try: lab = ImageFont.truetype(FONT, 22)
except OSError: lab = ImageFont.load_default()


def grab(t, w):
    h = w * 16 // 9
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-threads', '1', '-ss', f'{t:.3f}', '-i', mp4, '-frames:v', '1', '-vf', f'scale={w}:{h}',
                          '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], capture_output=True).stdout
    return Image.frombytes('RGB', (w, h), raw)


def sheet(ts, w, cols, out, guides=False):
    h = w * 16 // 9; rows = (len(ts) + cols - 1) // cols; pad = 34
    S = Image.new('RGB', (cols * (w + 8) + 8, rows * (h + pad + 8) + 8), (24, 26, 30)); d = ImageDraw.Draw(S)
    k = w / 1080
    for i, t in enumerate(ts):
        im = grab(min(t, dur - 0.04), w); x = 8 + (i % cols) * (w + 8); y = 8 + (i // cols) * (h + pad + 8)
        if guides:
            g = ImageDraw.Draw(im)
            g.rectangle([70 * k, 270 * k, 900 * k, 1230 * k], outline=(0, 255, 140))
            g.line([0, 1420 * k, w, 1420 * k], fill=(255, 60, 60))
        S.paste(im, (x, y + pad)); d.text((x + 4, y + 6), f'{t:.1f} s', font=lab, fill=(235, 235, 235))
    S.save(f'{D}/{out}', quality=88); print('wrote', out)


sheet([float(s) for s in range(0, int(dur) + 1)], 216, 8, 'contact_sheet_1s.jpg')
sheet([0, 0.5, 1, 1.5, 2, 2.5, 3], 300, 7, 'contact_sheet_0-3s.jpg', guides=True)
