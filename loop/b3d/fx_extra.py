"""Extra foley for Odd Loop 3D episodes (synthesised, no samples, no whooshes)."""
import numpy as np
import loop_audio as A
from loop_audio import T, env, sweep, lp, noise, bp, pluck, SR
rng = np.random.default_rng(11)
def _fade(s, a=0.01, b=0.08):
    n = len(s); x = np.arange(n) / SR; return s * np.minimum(1, x / a) * np.minimum(1, (x[-1] - x) / b + 1e-9)
def chop():
    x = T(0.3); return 0.9 * (np.sin(2 * np.pi * 140 * x) * env(x, .001, .05) + 0.6 * bp(noise(len(x)), 1500, 6000) * env(x, .0005, .012))
def pickup(): return 0.35 * pluck(880, 0.2, 0.6)
def mw_door():
    x = T(0.35); return 0.8 * (np.sin(2 * np.pi * 95 * x) * env(x, .002, .07) + 0.5 * bp(noise(len(x)), 1200, 5000) * env(x, .0005, .01))
def beep():
    x = T(0.2); return 0.25 * np.sin(2 * np.pi * 1900 * x) * np.minimum(1, x / 0.005) * np.minimum(1, (0.2 - x) / 0.01)
def hum(d=13.0):
    x = T(d); s = 0.5 * np.sin(2 * np.pi * 120 * x) + 0.25 * np.sin(2 * np.pi * 240 * x) + 0.12 * np.sin(2 * np.pi * 360 * x) + 0.03 * lp(noise(len(x)), 40)
    return 0.12 * _fade(s, 0.15, 0.05)
def crackle(d=0.6):
    out = np.zeros(int(d * SR))
    for _ in range(int(d * 40)):
        i = rng.integers(0, len(out) - 400); c = bp(noise(300), 2000, 9000) * np.exp(-np.arange(300) / 40); out[i:i + 300] += 0.35 * c
    return out
def buzz(d=3.6):
    x = T(d); saw = 2 * ((x * 98) % 1) - 1; am = 0.7 + 0.3 * np.sin(2 * np.pi * 7.3 * x) * np.sin(2 * np.pi * 1.1 * x)
    s = 0.22 * lp(saw, 6) * am + 0.5 * crackle(d)[:len(x)]
    return _fade(s, 0.02, 0.15)
def ignite():
    x = T(0.9); return 0.9 * (sweep(x, 90, 40) * env(x, .004, .3) + 0.4 * lp(noise(len(x)), 30) * env(x, .002, .15)) + 0.6 * np.pad(crackle(0.5), (0, int(0.4 * SR)))[:len(x)]
def tension(d=6.0):
    x = T(d); f = 180 * (1 + 1.4 * (x / d) ** 1.5); s = np.sin(2 * np.pi * np.cumsum(f) / SR) * (0.6 + 0.4 * np.sin(2 * np.pi * 6 * x))
    return 0.07 * _fade(s, 0.4, 0.2)
def zaps(d=1.6):
    out = np.zeros(int(d * SR))
    for k in range(9):
        x = T(0.07); c = sweep(x, 3200, 900) * env(x, .001, .03); i = int(k * d / 9 * SR); out[i:i + len(c)] += 0.25 * c
    return out
def swell():
    x = T(0.9); return 0.12 * sweep(x, 300, 1400, 1.4) * np.minimum(1, x / 0.6)
def boom():
    x = T(1.6); low = sweep(x, 75, 28) * env(x, .003, .55); rumble = lp(noise(len(x)), 60) * env(x, .002, .5); crack = bp(noise(len(x)), 600, 5000) * env(x, .0005, .04)
    return 1.2 * low + 0.9 * rumble + 0.5 * crack
def cough():
    out = np.zeros(int(0.7 * SR))
    for t0, a in ((0, 1), (0.26, 0.8)):
        x = T(0.18); c = bp(noise(len(x)), 300, 2400) * env(x, .004, .05) * a; i = int(t0 * SR); out[i:i + len(c)] += 0.6 * c
    return out
def blink(): return 0.18 * pluck(1760, 0.12, 0.8)
def nod():
    out = np.zeros(int(0.8 * SR))
    for t0 in (0, 0.42): c = 0.3 * pluck(330, 0.18, 0.4); i = int(t0 * SR); out[i:i + len(c)] += c
    return out
def ta_da():
    out = np.zeros(int(1.1 * SR))
    for k, f in enumerate((523, 659, 784, 1047)): c = 0.22 * pluck(f, 0.6, 0.6); i = int(k * 0.07 * SR); out[i:i + len(c)] += c
    return out
FX = dict(A.FX); FX.update(chop=chop, pickup=pickup, mw_door=mw_door, beep=beep, hum=hum, crackle=crackle, plasma_buzz=buzz, ignite=ignite,
                          tension=tension, zaps=zaps, swell=swell, boom=boom, cough=cough, blink=blink, nod=nod, ta_da=ta_da,
                          door_bash=lambda: 0.55 * A.door_slam())
