"""Finish a Kinda Wild Films Short: frames (24 fps) + word-synced Zack-style captions -> video; voice + foley + ducked music -> audio; mux.
python post_kw.py <frames_dir> <cues.json> <music.mp3> <out.mp4>"""
import sys, os, json, glob, subprocess, asyncio, tempfile, time
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, '..')); sys.path.insert(0, HERE)
import loop_audio as A
import fx_kw
FONT = os.path.join(HERE, '..', 'Montserrat-ExtraBold.ttf')
W, H = 1080, 1920; SR = A.SR

def tts(cj):
    """Same channel voice every time. Returns per-line audio + absolute word timings."""
    import edge_tts
    lines, words = [], []
    for k, (t0, text) in enumerate(cj['vo']):
        mp = os.path.join(tempfile.gettempdir(), f'kw{k}.mp3')
        for i in range(8):
            try:
                c = edge_tts.Communicate(text, cj['voice'], rate=cj.get('rate', '+0%'), boundary='WordBoundary'); ws = []
                async def go():
                    with open(mp, 'wb') as f:
                        async for ch in c.stream():
                            if ch['type'] == 'audio': f.write(ch['data'])
                            elif ch['type'] == 'WordBoundary': ws.append((ch['offset'] / 1e7, ch['duration'] / 1e7, ch['text']))
                asyncio.run(go())
                if os.path.getsize(mp) > 2000 and ws: break
            except Exception as e: print('tts retry', k, type(e).__name__, flush=True)
            time.sleep(4 * (i + 1))
        else: sys.exit('voice service gave no audio')
        raw = subprocess.run(['ffmpeg', '-v', 'error', '-i', mp, '-af', 'highpass=f=70,acompressor=threshold=-18dB:ratio=3:attack=5:release=80',
                              '-f', 'f32le', '-ac', '1', '-ar', str(SR), '-'], capture_output=True, check=True).stdout
        v = np.frombuffer(raw, np.float32).astype(np.float64); shift = 0.0
        if cj.get('vo_trim'):   # hook rule: t0 is the AUDIBLE onset of the line (the TTS lead-in silence is cut, 12 ms kept)
            on = int(np.argmax(np.abs(v) > 0.03 * max(1e-6, np.max(np.abs(v))))); cut = max(0, on - int(0.012 * SR)); v = v[cut:]; shift = cut / SR
        lines.append((t0, v))
        toks = text.split(); ti = 0
        for o, d, w in ws:  # restore punctuation from the script so caption groups break at commas/full stops
            key = ''.join(ch for ch in w.lower() if ch.isalnum()); lab = w
            for j in range(ti, min(ti + 4, len(toks))):
                if ''.join(ch for ch in toks[j].lower() if ch.isalnum()) == key: lab = toks[j]; ti = j + 1; break
            words.append((max(0.0, t0 + o - shift), t0 + o + d - shift, lab))
    return lines, words

def groups(words, lead0=False):
    """1-4 word caption groups; break after punctuation or long words. lead0: the first caption is already on frame 0."""
    out, cur = [], []
    for i, (a, b, w) in enumerate(words):
        cur.append((a, b, w))
        nxt_gap = words[i + 1][0] - b if i + 1 < len(words) else 9
        if len(cur) == 4 or w[-1:] in ',.?!' or len(''.join(x[2] for x in cur)) > 15 or nxt_gap > 0.25:
            out.append(cur); cur = []
    if cur: out.append(cur)
    res = []
    for j, g in enumerate(out):
        end = out[j + 1][0][0] if j + 1 < len(out) else g[-1][1] + 0.4
        end = min(end, g[-1][1] + 0.5)
        res.append((g[0][0], end, ' '.join(x[2] for x in g).replace(',', '').replace('.', '').replace('!', '')))
    if lead0 and res and res[0][0] < 0.3: res[0] = (0.0,) + res[0][1:]
    return res

def grade(im):
    """Zack D. look: punchy contrast, rich saturation, warm skin, cyan-leaning blues."""
    a = np.asarray(im).astype(np.float32) / 255.0
    lum = a @ np.array([0.299, 0.587, 0.114], np.float32)
    a = lum[..., None] + (a - lum[..., None]) * 1.18                     # saturation
    a = np.clip(a, 0, 1)
    a = 0.5 + (a - 0.5) * 1.06; a = np.clip(a, 0, 1)                     # contrast
    a = a ** np.array([0.98, 1.0, 1.03], np.float32)                       # slight warm overall
    mid = 4 * lum * (1 - lum)                                              # warm midtones (skin), cool/cyan highlights in blues
    a[..., 0] += 0.025 * mid; a[..., 2] -= 0.02 * mid
    blue = np.clip((a[..., 2] - a[..., 0]) * 2.0, 0, 1)
    a[..., 1] += 0.06 * blue; a[..., 0] -= 0.03 * blue
    sh = np.clip(1 - lum * 3, 0, 1); a -= 0.04 * sh[..., None]             # deeper shadows
    h, w = lum.shape; yy, xx = np.mgrid[0:h, 0:w].astype(np.float32)      # soft vignette here (the Blender ellipse-mask one rendered as a sharp oval)
    r = np.sqrt(((xx + 0.5) / w - 0.5) ** 2 / 0.25 + ((yy + 0.5) / h - 0.5) ** 2 / 0.25)
    a *= (1 - 0.15 * np.clip((r - 0.55) / 0.6, 0, 1) ** 2)[..., None]
    return Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))

def caption(im, t, caps, y=0.78):
    for a, b, txt in caps:
        if a <= t < b:
            f = ImageFont.truetype(FONT, 70); d = ImageDraw.Draw(im)
            while d.textlength(txt, font=f) > W * 0.84: f = ImageFont.truetype(FONT, f.size - 3)
            pos = (W // 2, int(H * y))         # cues 'cap_y' (fraction from the top); hook gate wants 0.66-0.72 (28-34% up from the bottom)
            sh = Image.new('L', im.size, 0); ImageDraw.Draw(sh).text((pos[0] + 3, pos[1] + 5), txt, font=f, fill=200, anchor='mm', stroke_width=4, stroke_fill=200)
            sh = sh.filter(ImageFilter.GaussianBlur(7)); im.paste((0, 0, 0), (0, 0), sh)
            d.text(pos, txt, font=f, fill=(255, 255, 255), stroke_width=3, stroke_fill=(0, 0, 0), anchor='mm')
            break
    return im

def audio(cj, lines, music, out):
    dur = cj['duration']; n = int(dur * SR); fx = np.zeros(n + 10 * SR); vo = np.zeros(n + 10 * SR)
    for t, name, g in cj['cues']:
        s = fx_kw.FX[name]() * g; i = int(t * SR); fx[i:i + len(s)] += s
    for t0, v in lines: i = int(t0 * SR); vo[i:i + len(v)] += v
    fx, vo = fx[:n], vo[:n]
    vo = vo / max(1e-6, np.sqrt(np.mean(vo[np.abs(vo) > 1e-4] ** 2))) * 0.17
    bed = A.music(music, 0.0, dur); bed *= 0.2 / max(1e-6, np.sqrt(np.mean(bed ** 2))) * cj.get('music_gain', 0.42)
    e = np.convolve(np.abs(vo), np.ones(SR // 10) / (SR // 10), mode='same'); k = np.clip(e / 0.04, 0, 1)
    tail = int(1.2 * SR); bed[-tail:] *= np.linspace(1, 0, tail)
    mix = vo + fx * (1 - 0.3 * k) + bed * (1 - 0.5 * k)
    mix = np.tanh(mix * 1.1) / 1.1; mix *= 0.89 / max(1e-6, np.max(np.abs(mix)))
    pcm = (np.stack([mix, mix], 1) * 32767).astype('<i2').tobytes()
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 's16le', '-ar', str(SR), '-ac', '2', '-i', '-', '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11', '-ar', str(SR), out], input=pcm, check=True)

if __name__ == '__main__':
    fdir, cjp, music, out = sys.argv[1:5]
    cj = json.load(open(cjp)); fps = cj['fps']; n = int(round(cj['duration'] * fps))
    lines, words = tts(cj); caps = groups(words, cj.get('cap_lead0', False))
    json.dump(dict(words=words, caps=caps), open(out + '.captions.json', 'w'), indent=0)
    idx = {int(os.path.basename(f)[1:5]): f for f in glob.glob(os.path.join(fdir, 'f*.png'))}
    miss = [i for i in range(n) if i not in idx]
    if len(miss) > 3: sys.exit(f'missing {len(miss)} frames, e.g. {miss[:10]}')
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(fps), '-i', '-',
                          '-c:v', 'libx264', '-preset', 'slow', '-crf', '16', '-pix_fmt', 'yuv420p', out + '.v.mp4'], stdin=subprocess.PIPE)
    last = None
    for i in range(n):
        src = idx.get(i) or last
        base = grade(Image.open(src).convert('RGB').resize((W, H), Image.LANCZOS)) if src != last else base; last = src
        p.stdin.write(caption(base.copy(), i / fps, caps, cj.get('cap_y', 0.78)).tobytes())
    p.stdin.close(); assert p.wait() == 0
    audio(cj, lines, music, out + '.a.wav')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', out + '.v.mp4', '-i', out + '.a.wav', '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '256k',
                    '-shortest', '-movflags', '+faststart', out], check=True)
    os.remove(out + '.v.mp4'); os.remove(out + '.a.wav'); print('done', out, n, 'frames', len(caps), 'captions')
