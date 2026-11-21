"""Finish a Kinda Wild Films Short: frames (24 fps) + word-synced Zack-style captions -> video; voice + foley + ducked music -> audio; mux.
python post_kw.py <frames_dir> <cues.json> <music.mp3> <out.mp4>"""
import sys, os, json, glob, subprocess, asyncio, tempfile, time
import numpy as np
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, '..')); sys.path.insert(0, HERE)
import loop_audio as A
import fx_kw
FONT = os.path.join(HERE, '..', 'Montserrat-Black.ttf')
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
        lines.append((t0, np.frombuffer(raw, np.float32).astype(np.float64)))
        toks = text.split(); ti = 0
        for o, d, w in ws:  # restore punctuation from the script so caption groups break at commas/full stops
            key = ''.join(ch for ch in w.lower() if ch.isalnum()); lab = w
            for j in range(ti, min(ti + 4, len(toks))):
                if ''.join(ch for ch in toks[j].lower() if ch.isalnum()) == key: lab = toks[j]; ti = j + 1; break
            words.append((t0 + o, t0 + o + d, lab))
    return lines, words

def groups(words):
    """1-3 word caption groups; break after punctuation or long words."""
    out, cur = [], []
    for i, (a, b, w) in enumerate(words):
        cur.append((a, b, w))
        nxt_gap = words[i + 1][0] - b if i + 1 < len(words) else 9
        if len(cur) == 3 or w[-1:] in ',.?!' or len(''.join(x[2] for x in cur)) > 11 or nxt_gap > 0.25:
            out.append(cur); cur = []
    if cur: out.append(cur)
    res = []
    for j, g in enumerate(out):
        end = out[j + 1][0][0] if j + 1 < len(out) else g[-1][1] + 0.4
        end = min(end, g[-1][1] + 0.5)
        res.append((g[0][0], end, ' '.join(x[2] for x in g).upper().replace(',', '').replace('.', '').replace('!', '')))
    return res

def caption(im, t, caps):
    for a, b, txt in caps:
        if a <= t < b:
            u = min(1, (t - a) / 0.08); sc = 0.85 + 0.15 * u
            f = ImageFont.truetype(FONT, int(96 * sc))
            d = ImageDraw.Draw(im)
            while d.textlength(txt, font=f) > W * 0.86: f = ImageFont.truetype(FONT, f.size - 4)
            d.text((W // 2, int(H * 0.70)), txt, font=f, fill=(255, 255, 255), stroke_width=max(6, int(f.size * 0.11)), stroke_fill=(0, 0, 0), anchor='mm')
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
    lines, words = tts(cj); caps = groups(words)
    json.dump(dict(words=words, caps=caps), open(out + '.captions.json', 'w'), indent=0)
    idx = {int(os.path.basename(f)[1:5]): f for f in glob.glob(os.path.join(fdir, 'f*.png'))}
    miss = [i for i in range(n) if i not in idx]
    if len(miss) > 3: sys.exit(f'missing {len(miss)} frames, e.g. {miss[:10]}')
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(fps), '-i', '-',
                          '-c:v', 'libx264', '-preset', 'slow', '-crf', '16', '-pix_fmt', 'yuv420p', out + '.v.mp4'], stdin=subprocess.PIPE)
    last = None
    for i in range(n):
        src = idx.get(i) or last
        base = Image.open(src).convert('RGB').resize((W, H), Image.LANCZOS) if src != last else base; last = src
        p.stdin.write(caption(base.copy(), i / fps, caps).tobytes())
    p.stdin.close(); assert p.wait() == 0
    audio(cj, lines, music, out + '.a.wav')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', out + '.v.mp4', '-i', out + '.a.wav', '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '256k',
                    '-shortest', '-movflags', '+faststart', out], check=True)
    os.remove(out + '.v.mp4'); os.remove(out + '.a.wav'); print('done', out, n, 'frames', len(caps), 'captions')
