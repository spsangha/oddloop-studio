"""Expression / swell / flush / nurse-hair contact test for the heads (not an episode). One shot per 0.5 s; frame = 12*i + 9.
KW_NOCHECK=1 ONLY=... PCT=35 SAMPLES=12 [KW_HEADS=scan] blender -b -P kit/heads/expr.py -- OUT 0 1"""
import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'loop', 'kw'))
import kwkit as KW
FACES = 'neutral calm strain puffed shock pain worry relief smile sleep talk disgust focus scream nausea sniff blow'.split() + ['pain+worry']
SW = [{'neck': 1.0}, {'eye_l': 1.0, 'eye_r': 1.0}, {'cheek_l': 1.0, 'cheek_r': 1.0}, {'lips': 1.0}]
ep = KW.Episode('heads_expr', injury='none', voice_lines=['A long test of every face, every swell and the flush on one scan head, then a nurse.'] * 3, music='sneaky_snitch', gap=0.4)
ben = ep.person('Ben', 'civilian', 'eatmore-ben', gender='m', age='young', race='caucasian', hair='short02', tee='teal')
nur = ep.person('Nia', 'nurse', 'lineup-5', gender='f', age='young', race='african')
shots = [(f, {}, 0.0) for f in FACES] + [('calm', s, 0.0) for s in SW] + [('strain', {}, 0.9)]
for i, (f, sw, fl) in enumerate(shots):
    ep.shot(i * 0.5, f'e{i}_{f}', set='studio', cast={ben: KW.pose('stand', at='studio.centre', face=f, swell=sw, flush=fl)}, cam=KW.cam.face(ben, side=15, push=0.0, lens=45, fstop=11))
i = len(shots)
ep.shot(i * 0.5, 'nurse', set='studio', cast={nur: KW.pose('stand', at='studio.centre', face='calm')}, cam=KW.cam.face(nur, side=25, push=0.0, lens=40, fstop=11))
ep.run()
