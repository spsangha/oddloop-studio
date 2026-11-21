"""Finish an Odd Loop 3D episode: frames (on twos) + impact words + channel bug -> video; cartoon foley + music -> audio; mux.
python post.py <frames_dir> <cues.json> <music.mp3> <out.mp4>"""
import sys, os, json, glob, subprocess, math
import numpy as np
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, os.path.join(HERE, '..'))
import loop_audio as A
FD = [os.path.join(HERE, '..', '..', 'kazoo', 'visual', 'assets', 'fonts'), os.path.join(HERE, '..')]
def ffile(n):
    for d in FD:
        if os.path.exists(os.path.join(d, n)): return os.path.join(d, n)
POW = ffile('LuckiestGuy.ttf') or ffile('Fredoka.ttf'); BUG = ffile('Fredoka.ttf')
W, H = 1080, 1920

def back_out(u, s=2.4): u = min(1, max(0, u)) - 1; return 1 + u * u * ((s + 1) * u + s)

def overlay(im, t, pows):
    d = ImageDraw.Draw(im, 'RGBA')
    for t0, txt, fx, fy, size in pows:
        if not (t0 <= t < t0 + 0.7): continue
        u = (t - t0) / 0.7; sc = back_out(min(1, u * 4)) * (1 - 0.12 * u); a = 1 if u < 0.75 else (1 - u) / 0.25
        if sc < 0.05: continue
        f = ImageFont.truetype(POW, max(8, int(size * sc)))
        d.text((fx * W, fy * H), txt, font=f, fill=(255, 214, 51, int(255 * a)), stroke_width=max(2, int(13 * sc)), stroke_fill=(33, 28, 51, int(255 * a)), anchor='mm')
    f = ImageFont.truetype(BUG, 34); d.rounded_rectangle((40, 150, 262, 206), 28, fill=(33, 28, 51, 170)); d.text((151, 178), 'ODD LOOP', font=f, fill=(255, 255, 255, 235), anchor='mm')
    return im

def audio(cj, music, out):
    SR = A.SR; dur = cj['duration']; n = int(dur * SR); fx = np.zeros(n + SR)
    FX = dict(A.FX); FX['door_bash'] = lambda: 0.55 * A.door_slam()
    gains = {'step_cat': 0.9, 'step_blob': 0.8}
    for t, name in cj['cues']:
        s = FX[name]() * gains.get(name, 1.0); i = int(t * SR); fx[i:i + len(s)] += s[:max(0, len(fx) - i)]
    fx = fx[:n]
    bed = A.music(music, 0.0, dur); bed *= 0.2 / max(1e-6, np.sqrt(np.mean(bed ** 2))) * 0.5
    mix = np.tanh((fx + bed) * 1.1) / 1.1; mix *= 0.89 / max(1e-6, np.max(np.abs(mix)))
    pcm = (np.stack([mix, mix], 1) * 32767).astype('<i2').tobytes()
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 's16le', '-ar', str(SR), '-ac', '2', '-i', '-', '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11', '-ar', str(SR), out], input=pcm, check=True)

if __name__ == '__main__':
    fdir, cjp, music, out = sys.argv[1:5]
    cj = json.load(open(cjp)); fps = cj['fps']; n = int(round(cj['duration'] * fps))
    have = sorted(glob.glob(os.path.join(fdir, 'f*.png'))); idx = {int(os.path.basename(f)[1:5]): f for f in have}
    p = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(fps), '-i', '-',
                          '-c:v', 'libx264', '-preset', 'slow', '-crf', '17', '-pix_fmt', 'yuv420p', out + '.v.mp4'], stdin=subprocess.PIPE)
    last = None
    for i in range(n):
        src = idx.get(i) or idx.get(i - 1) or last
        if src != last or i == 0:
            base = Image.open(src).convert('RGB').resize((W, H), Image.LANCZOS); last = src
        im = overlay(base.copy(), i / fps, cj['pow']); p.stdin.write(im.tobytes())
    p.stdin.close(); assert p.wait() == 0
    audio(cj, music, out + '.a.wav')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', out + '.v.mp4', '-i', out + '.a.wav', '-map', '0:v', '-map', '1:a', '-c:v', 'copy', '-c:a', 'aac', '-b:a', '256k',
                    '-shortest', '-movflags', '+faststart', out], check=True)
    os.remove(out + '.v.mp4'); os.remove(out + '.a.wav'); print('done', out, n, 'frames')
