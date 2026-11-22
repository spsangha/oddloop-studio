"""Head close-up test (not an episode): tight face shots for skin/eye work. Frames 6, 18, 30, 42 (+12 each).
ONLY=6,18,30,42 PCT=50 SAMPLES=16 [KW_HEADS=scan] blender -b -P kit/heads/closeup.py -- OUT 0 1"""
import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'loop', 'kw'))
import kwkit as KW
CAST = [('m', 'young', 'caucasian', 'eatmore-ben', 'short02'), ('f', 'young', 'african', 'lineup-5', None),
        ('m', 'old', 'asian', 'lineup-4', None), ('f', 'young', 'asian', 'lineup-1', None)]
ep = KW.Episode('heads_closeup', injury='none', voice_lines=['Four faces, very close, for a skin test.'], music='sneaky_snitch', gap=0.4)
P = [ep.person(f'P{i}', 'civilian', s, gender=g, age=a, race=r, **({'hair': h} if h else {})) for i, (g, a, r, s, h) in enumerate(CAST)]
for i, p in enumerate(P):
    ep.shot(i * 0.5, f'face{i}', set='studio', cast={p: KW.pose('stand', at='studio.centre', face='calm')}, cam=KW.cam.face(p, side=15, push=0.0, lens=55, fstop=16))
ep.run()
