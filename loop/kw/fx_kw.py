"""Realistic synthesised foley for Kinda Wild Films (no samples, no whooshes)."""
import os, sys
import numpy as np
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'b3d'))
from loop_audio import T, env, lp, noise, bp, SR
import fx_extra
rng = np.random.default_rng(23)

def _fade(s, a=0.02, b=0.1):
    n = len(s); x = np.arange(n) / SR; return s * np.minimum(1, x / a) * np.clip((x[-1] - x) / b, 0, 1)

def engine(d=1.9):  # low cabin rumble, no pitch sweeps
    x = T(d); f = 38 + 1.5 * np.sin(2 * np.pi * 0.7 * x)
    ph = 2 * np.pi * np.cumsum(f) / SR
    s = 0.5 * np.sin(ph) + 0.3 * np.sin(2 * ph) + 0.25 * lp(noise(len(x)), 90)
    return 0.22 * _fade(s, 0.25, 0.3)
def rip():  # wet tissue tear
    x = T(0.45); n = noise(len(x)); g = (rng.random(len(x)) < 0.08) * 1.0
    s = bp(n * lp(g, 30) * 6, 600, 4000) * env(x, 0.005, 0.18)
    return 0.6 * s / max(1e-6, np.max(np.abs(s)))
def thud():
    x = T(0.5); return 0.8 * (np.sin(2 * np.pi * 62 * x) * env(x, 0.002, 0.12) + 0.2 * lp(noise(len(x)), 30) * env(x, 0.001, 0.04))
def sniff():
    x = T(0.5); s = bp(noise(len(x)), 1500, 6000) * env(x, 0.12, 0.15)
    return 0.35 * s / max(1e-6, np.max(np.abs(s)))
def pinch():  # soft skin squeeze
    x = T(0.2); s = bp(noise(len(x)), 300, 2000) * env(x, 0.003, 0.04); return 0.4 * s / max(1e-6, np.max(np.abs(s)))
def puff():  # cheeks filling: muffled low pressure
    x = T(0.8); s = lp(noise(len(x)), 120) * env(x, 0.15, 0.3) + 0.3 * np.sin(2 * np.pi * 90 * x) * env(x, 0.1, 0.25)
    return 0.5 * s / max(1e-6, np.max(np.abs(s)))
def rush(d=2.0):  # airflow through a pipe (steady, low, not a whoosh sweep)
    x = T(d); s = bp(noise(len(x)), 150, 900) * (0.6 + 0.4 * np.sin(2 * np.pi * 1.3 * x) ** 2)
    return 0.28 * _fade(s / max(1e-6, np.max(np.abs(s))), 0.3, 0.5)
def bounce():  # air hitting a closed wall
    x = T(0.6); return 0.55 * (np.sin(2 * np.pi * 75 * x) * env(x, 0.003, 0.15) + 0.15 * bp(noise(len(x)), 200, 800) * env(x, 0.002, 0.08))
def pressure(d=2.6):  # rising strained creak + low tone
    x = T(d); f = 55 + 25 * x / d
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) * (x / d) + 0.25 * bp(noise(len(x)), 300, 1200) * (x / d) ** 2
    return 0.35 * _fade(s, 0.2, 0.15)
def bubbles(d=2.4):
    out = np.zeros(int(d * SR))
    for _ in range(int(d * 9)):
        f = rng.uniform(500, 1400); n = int(0.06 * SR); xx = np.arange(n) / SR
        b = np.sin(2 * np.pi * (f + 3000 * xx) * xx) * np.exp(-xx / 0.015)
        i = rng.integers(0, len(out) - n); out[i:i + n] += 0.22 * b
    return out
def crackle(): return 1.3 * fx_extra.crackle(0.7)
def heal():  # gentle sparkle-free warm tone
    x = T(1.6); s = (np.sin(2 * np.pi * 220 * x) + 0.5 * np.sin(2 * np.pi * 330 * x)) * env(x, 0.4, 0.6)
    return 0.12 * s
def inhale():
    x = T(1.0); s = bp(noise(len(x)), 800, 5000) * (x / 1.0) ** 1.5 * np.clip((1.0 - x) / 0.08, 0, 1)
    return 0.4 * s / max(1e-6, np.max(np.abs(s)))
def sneeze():  # "choo": vocal-ish noise burst
    x = T(0.6); s = bp(noise(len(x)), 1200, 7000) * env(x, 0.004, 0.12) + 0.4 * np.sin(2 * np.pi * 180 * x) * env(x, 0.004, 0.08)
    return 0.8 * s / max(1e-6, np.max(np.abs(s)))

def tick():  # soft dry suture tick: ~40 ms band-passed click, no ring
    x = T(0.045); s = bp(noise(len(x)), 1800, 5200) * env(x, 0.0015, 0.012) + 0.25 * np.sin(2 * np.pi * 2400 * x) * env(x, 0.001, 0.006)
    return 0.8 * s / max(1e-6, np.max(np.abs(s)))
FX = dict(tick=tick, engine=engine, rip=rip, thud=thud, sniff=sniff, pinch=pinch, puff=puff, rush=rush, bounce=bounce, pressure=pressure,
          bubbles=bubbles, crackle=crackle, heal=heal, inhale=inhale, sneeze=sneeze)
