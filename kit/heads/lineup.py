"""Head test lineup (not an episode): 8 cast members, one face close-up each in the studio set.
ONLY=6,18,30,42,54,66,78,90 PCT=35 SAMPLES=12 [KW_HEADS=scan] blender -b -P kit/heads/lineup.py -- OUT 0 1"""
import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'loop', 'kw'))
import kwkit as KW
CAST = [('m', 'young', 'caucasian'), ('f', 'young', 'asian'), ('m', 'middle', 'african'), ('f', 'middle', 'caucasian'),
        ('m', 'old', 'asian'), ('f', 'young', 'african'), ('m', 'middle', 'caucasian'), ('f', 'old', 'caucasian')]
ep = KW.Episode('heads_lineup', injury='none', voice_lines=['Eight faces, one after another, for a head test.'] , music='sneaky_snitch', gap=0.4)
P = [ep.person(f'P{i}', 'civilian', f'lineup-{i}', gender=g, age=a, race=r) for i, (g, a, r) in enumerate(CAST)]
for i, p in enumerate(P):
    ep.shot(i * 0.5, f'face{i}', set='studio', cast={p: KW.pose('stand', at='studio.centre', face='calm')}, cam=KW.cam.face(p, side=12, push=0.0))
ep.run()
