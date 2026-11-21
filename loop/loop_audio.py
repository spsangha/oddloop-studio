"""Odd Loop sound: cartoon effects made from oscillators and noise (no samples, no whoosh) over a Kevin MacLeod bed.
python loop_audio.py <episode_dir> <music.mp3> <out.wav>   (episode ep.py exposes CUES [(t, name)] and DURATION; optional MUSIC_START)"""
import sys, os, math, subprocess, importlib.util
import numpy as np

SR = 48000
rng = np.random.default_rng(7)

def T(d): return np.arange(int(d * SR)) / SR
def env(x, a, d): return (1 - np.exp(-x / a)) * np.exp(-x / d)
def sweep(x, f0, f1, curve=1.0):
    u = (x / x[-1]) ** curve; f = f0 + (f1 - f0) * u
    return np.sin(2 * np.pi * np.cumsum(f) / SR)
def lp(sig, k=12): return np.convolve(sig, np.ones(k) / k, mode='same')
def noise(n): return rng.normal(0, 1, n)

def patter():
    x = T(0.05); f = rng.uniform(170, 240)
    return 0.35 * (np.sin(2 * np.pi * f * x) * env(x, .001, .018) + 0.4 * lp(noise(len(x)), 6) * env(x, .0005, .008))
def skid():
    x = T(0.42); vib = 1 + 0.03 * np.sin(2 * np.pi * 30 * x)
    s = sweep(x, 1500, 950) * vib * env(x, .01, .25)
    return 0.32 * (s + 0.25 * lp(noise(len(x)), 4) * env(x, .005, .12))
def button():
    x = T(0.25)
    return 0.8 * (np.sin(2 * np.pi * 110 * x) * env(x, .001, .06) + 0.5 * np.sin(2 * np.pi * 620 * x) * env(x, .0005, .012))
def slide(up=True):
    x = T(0.5); f0, f1 = (300, 1300) if up else (1300, 260)
    s = sweep(x, f0, f1, 0.8) * (1 + 0.04 * np.sin(2 * np.pi * 7 * x))
    a = np.minimum(1, x / 0.03) * np.minimum(1, (x[-1] - x) / 0.08)
    wub = np.sin(2 * np.pi * 70 * x) * (0.5 + 0.5 * np.sin(2 * np.pi * 11 * x)) * env(x, .01, .3)
    return 0.28 * s * a + 0.35 * wub
def splat():
    x = T(0.45); n = lp(noise(len(x)), 18)
    return 0.9 * (n * env(x, .002, .09) + 0.9 * np.sin(2 * np.pi * 62 * x) * env(x, .002, .14) + 0.3 * sweep(x, 400, 80) * env(x, .002, .05))
def land():
    x = T(0.25)
    return 0.7 * (np.sin(2 * np.pi * 85 * x) * env(x, .002, .07) + 0.25 * lp(noise(len(x)), 10) * env(x, .001, .03))
def stars():
    out = np.zeros(int(0.9 * SR))
    for k, (t0, f) in enumerate(((0, 2800), (0.16, 3300), (0.42, 2800), (0.58, 3300))):
        x = T(0.1); c = np.sin(2 * np.pi * np.cumsum(f * (1 + 0.25 * np.sin(2 * np.pi * 40 * x))) / SR) * env(x, .004, .04)
        i = int(t0 * SR); out[i:i + len(c)] += 0.16 * c
    return out
def gulp():
    x = T(0.22); return 0.45 * sweep(x, 420, 140) * env(x, .005, .07)
def boing():
    x = T(0.7); f = 160 * (1 + 0.35 * np.sin(2 * np.pi * 16 * x) * np.exp(-4 * x))
    return 0.5 * np.sin(2 * np.pi * np.cumsum(f) / SR) * env(x, .003, .25)

# ---- foley: every footfall, every prop (added so each action on screen has its own sound)
def bp(sig, lo, hi):
    F = np.fft.rfft(sig); f = np.fft.rfftfreq(len(sig), 1 / SR); F[(f < lo) | (f > hi)] = 0; return np.fft.irfft(F, len(sig))
def pluck(f, d=0.28, bright=0.5):
    n = int(SR / f); buf = rng.uniform(-1, 1, n); out = np.zeros(int(d * SR))
    for i in range(len(out)):
        out[i] = buf[i % n]; buf[i % n] = 0.996 * (bright * buf[i % n] + (1 - bright) * buf[(i + 1) % n])
    return out
_bs = [0]
def step_blob():                       # squishy rubber "pit" - alternates feet
    _bs[0] ^= 1; x = T(0.07); f0 = 1050 if _bs[0] else 900
    return 0.30 * sweep(x, f0, f0 * 0.62) * env(x, .001, .022) + 0.18 * lp(noise(len(x)), 5) * env(x, .0005, .006)
def step_cat(soft=False):             # heavy padded clomp
    x = T(0.16); f = rng.uniform(78, 96)
    s = np.sin(2 * np.pi * np.cumsum(f * (1 + 0.6 * np.exp(-x / 0.01))) / SR) * env(x, .0015, .05) + 0.35 * lp(noise(len(x)), 14) * env(x, .001, .015)
    return (0.38 if soft else 0.75) * s
_tt = [0]
def tiptoe():                          # sneaking pizzicato, one note per step, climbing
    notes = [196, 220, 247, 262, 294, 330, 349, 392]; f = notes[_tt[0] % len(notes)]; _tt[0] += 1
    return 0.55 * pluck(f, 0.3, 0.55)
def horn():                            # ah-OO-gah when the eyes pop out
    x = T(0.62); f = np.interp(x, [0, .08, .3, .45, .62], [240, 260, 420, 300, 260])
    ph = np.cumsum(f) / SR; saw = 2 * (ph % 1) - 1
    a = np.minimum(1, x / 0.02) * np.minimum(1, (x[-1] - x) / 0.06)
    return 0.32 * lp(np.tanh(2.5 * saw), 4) * a
def giggle():                          # cheeky little "hee-hee-hee"
    out = np.zeros(int(0.42 * SR))
    for k in range(3):
        x = T(0.1); f = (900 + 140 * k) * (1 + 0.12 * np.sin(2 * np.pi * 28 * x))
        c = np.sin(2 * np.pi * np.cumsum(f) / SR) + 0.3 * np.sin(4 * np.pi * np.cumsum(f) / SR)
        i = int(k * 0.13 * SR); out[i:i + len(x)] += 0.22 * c * env(x, .006, .035)
    return out
def bloop():                           # water lifting off: rising bubbles
    out = np.zeros(int(0.5 * SR))
    for k, t0 in enumerate((0, 0.09, 0.2, 0.28)):
        x = T(0.07); c = sweep(x, 350 + 120 * k, 1100 + 200 * k, 0.6) * env(x, .002, .025); i = int(t0 * SR); out[i:i + len(c)] += 0.3 * c
    return out
def water():                           # splash plus drips
    x = T(0.6); s = 0.6 * bp(noise(len(x)), 500, 5000) * env(x, .003, .09)
    for t0, f in ((0.18, 1400), (0.31, 1700), (0.45, 1200)):
        y = T(0.05); c = sweep(y, f, f * 1.8) * env(y, .001, .015); i = int(t0 * SR); s[i:i + len(c)] += 0.25 * c
    return 0.7 * s
def door_slam():
    x = T(0.6); body = np.sin(2 * np.pi * 70 * x) * env(x, .001, .12) + 0.6 * np.sin(2 * np.pi * 131 * x) * env(x, .001, .07)
    crack = bp(noise(len(x)), 300, 6000) * env(x, .0005, .02); rattle = bp(noise(len(x)), 2000, 7000) * env(x, .05, .12) * (0.5 + 0.5 * np.sign(np.sin(2 * np.pi * 34 * x)))
    return 0.9 * (body + 0.7 * crack + 0.15 * rattle)
def door_creak():
    x = T(0.9); f = 180 + 90 * np.sin(2 * np.pi * 0.9 * x); pulses = (np.sin(2 * np.pi * np.cumsum(f) / SR) > 0.92).astype(float)
    return 0.5 * bp(pulses - pulses.mean(), 400, 4000) * np.minimum(1, x / 0.05) * np.minimum(1, (x[-1] - x) / 0.1)
def knock():
    out = np.zeros(int(0.5 * SR))
    for t0 in (0, 0.16, 0.32):
        x = T(0.08); c = np.sin(2 * np.pi * 190 * x) * env(x, .0005, .018) + 0.4 * bp(noise(len(x)), 800, 4000) * env(x, .0003, .006); i = int(t0 * SR); out[i:i + len(c)] += 0.6 * c
    return out

FX = dict(patter=patter, skid=skid, button=button, flip=lambda: slide(True), flip_back=lambda: slide(False), splat=splat, land=land,
          stars=stars, gulp=gulp, boing=boing,
          step_blob=step_blob, step_cat=step_cat, step_cat_soft=lambda: step_cat(True), tiptoe=tiptoe, horn=horn, giggle=giggle,
          bloop=bloop, water=water, door_slam=door_slam, door_creak=door_creak, knock=knock)

def load(ep_dir):
    sys.path.insert(0, os.path.abspath(ep_dir))
    spec = importlib.util.spec_from_file_location('ep', os.path.join(ep_dir, 'ep.py'))
    m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m); return m

def music(path, start, dur):
    raw = subprocess.run(['ffmpeg', '-v', 'error', '-ss', str(start), '-t', str(dur + 0.1), '-i', path, '-f', 'f32le', '-ac', '1', '-ar', str(SR), '-'],
                         capture_output=True, check=True).stdout
    m = np.frombuffer(raw, np.float32).astype(np.float64)[:int(dur * SR)]
    m = np.pad(m, (0, int(dur * SR) - len(m)))
    fade = int(0.04 * SR); m[:fade] *= np.linspace(0, 1, fade); m[-fade:] *= np.linspace(1, 0, fade)
    return m

if __name__ == '__main__':
    ep_dir, mpath, out = sys.argv[1:4]
    m = load(ep_dir); dur = float(m.DURATION); n = int(dur * SR)
    fx = np.zeros(n + SR)
    for t, name in sorted(m.CUES):
        s = FX[name](); i = int(t * SR); fx[i:i + len(s)] += s[:max(0, len(fx) - i)]
    fx = fx[:n]
    bed = music(mpath, getattr(m, 'MUSIC_START', 0.0), dur)
    bed *= 0.20 / max(1e-6, np.sqrt(np.mean(bed ** 2))) * 0.55     # bed well under the effects
    mix = fx + bed
    mix = np.tanh(mix * 1.1) / 1.1                                  # soft limiter
    mix *= 0.89 / max(1e-6, np.max(np.abs(mix)))
    st = np.stack([mix, mix], 1)
    pcm = (st * 32767).astype('<i2').tobytes()
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 's16le', '-ar', str(SR), '-ac', '2', '-i', '-', '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11', '-ar', str(SR), out], input=pcm, check=True)
    print('audio', out, round(dur, 2), 's', len(m.CUES), 'cues')
