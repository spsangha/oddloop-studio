"""Kinda Wild Films - 'How Stitches Work' (test harness; full brief pending)."""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kwkit as KW
os.environ.setdefault('KW_LIGHT', '1')      # light-render settings on the studio set (approved for the full render)
ep = KW.Episode('ep_stitches', injury="cut", voice_lines=[
    "Ben cuts his leg and the doctor closes the cut with stitches.",
    "The stitches pull the two edges of the skin together.",
    "Then the body sends blood and builds new tissue across the gap.",
    "Tiny new vessels grow into the wound to feed it.",
    "After about a week or two the stitches come out.",
    "What stays is a thin pink scar that slowly fades.",
], music='sneaky_snitch', gap=0.4)
ben = ep.person('Ben', 'civilian', 'eatmore-ben', gender='m', age='young', race='caucasian', hair='short02', tee='teal')
GLIDE = [(0.0, 0.38), (1.3, 0.27), (4.9, 0.16), (7.8, 0.12), (9.8, 0.08), (11.4, 0.06), (21.2, 0.05), (23.3, 0.18), (25.3, 0.38), (26.8, 0.35), (29.0, 0.38)]
CAMO = dict(glide=GLIDE, yaw=(-10.0, 10.0, 29.0), slide=(11.4, 21.2, 0.02), lens=50, cap_bone='lowerleg01.L', cap_dz=0.02)
# CHECK 1 stills (Addendum B): (name, film time, wound state)
CK = [('f0_wide', 0.0, dict(open=1.0)),
      ('t12_stage2', 12.0, dict(open=1.0, stitches=10.0, line=1.0, red=1.0, cells=1.0, specks=0.5)),
      ('t17_stage3', 17.0, dict(open=1.0, stitches=10.0, line=1.0, red=1.0, collagen=1.0)),
      ('t20_stage4', 20.0, dict(open=1.0, stitches=10.0, line=1.0, red=1.0, collagen=1.0, vessels=1.0))]
for i_, (nm, T, st) in enumerate(CK):
    c = dict(CAMO); c['at'] = T - 4 / 24
    ep.shot(float(i_), nm, set='studio', world='sky', cast={ben: KW.pose('stand', at='centre')}, fx=[KW.fx.wound(ben, [(0.0, st)], side='L')],
            cam=KW.cam.part(ben, 'calf_l', **c))
ep.run()
