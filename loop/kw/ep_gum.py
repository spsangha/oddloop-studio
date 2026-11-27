"""Kinda Wild Films ep20 - 'What Happens If You Swallow Gum?'  Brief: kindawild/20_gum/brief.md.
Facts: Cleveland Clinic 'What Happens if You Swallow Gum?' (gum base isn't digested; out in the stool ~40 hours later; a piece
every day / several at once can block the intestines), Mayo Clinic 'Swallowing gum: Is it harmful?' (the 7-year story isn't true;
moves intact through the digestive system), Live Science (Duke gastroenterologist: no enzymes for it; found gum on colonoscopy,
probably swallowed within the last 24 hours), KidsHealth (peristalsis moves it along).
Ben at his desk chewing, swallows (throat bulge), x-ray glass body: the gum (orange) goes down, sits whole in the stomach, is
squeezed through the gut and out; the doctor; blocked gut (bunching + swollen belly) for lots of gum; payoff one piece fine.
Ladder rung 9 (nails / knuckles, carried from ep19): close of his hand bringing the gum to his mouth is NOT used here (no hand near
the lens); rung 9 stays OWED.
"""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kwkit as KW
os.environ.setdefault('KW_LIGHT', '1')
HERE = os.path.dirname(os.path.abspath(__file__))
ep = KW.Episode('ep_gum', injury="swallowed it",
                voice_lines=[l.strip() for l in open(os.path.join(HERE, 'ep_gum.txt')) if l.strip()],
                music='sneaky_snitch', gap=0.6)
ben = ep.person('Ben', 'civilian', 'eatmore-ben', gender='m', age='young', race='caucasian', hair='short02', tee='teal')
doc = ep.person('Howard', 'scientist', 'eatmore-sci', gender='m', age='old', race='caucasian', hair='short02')
gut = ep.macro('intestine')

FPS = 24; F = 1.0 / FPS
L = ep.line; E = ep.line_end; W = ep.word
KW.FACES.update({'oops': {'x_surprise': 0.85}, 'huh': {'x_surprise': 0.35, 'worry': 0.4}, 'easy': {'smile': 0.6},
                 'ache': {'x_pain': 0.6, 'worry': 0.4}})
ep.waive = {"HOOK inside the body": "brief: vidIQ rule 1 person -> throat cutaway -> face close; the x-ray comes at 3 s",
            "shot ": "brief: payoff/CTA shot holds over the last line + CTA",
            "HOOK cut <= 200 ms after the last word": "brief: CTA over the payoff shot, then the frame-0 loop shot"}
desk = lambda face='neutral', **k: KW.pose('sit', at='desk', face=face, **k)
xr = lambda face='neutral', **k: KW.pose('sit', at='room.desk', face=face, **k)
XO = ['esophagus', 'stomach', 'intestines']
YL = dict(color='yellow', size=1.2); Y = 0.89
ep.label_outline = True; ep.label_maxw = 820.0; ep.label_lens_fix = True
def lab(txt, at, dur, **k): return KW.fx.label(txt, at=at, pos=(0.5, Y), dur=dur, **(k or YL))

T1 = 0.92; T2 = 1.92                                                     # hook cuts (f22, f46)
TG = W(0, 'swallowed')
ep.duration = round(E(6) + 2.3, 4); LOOPT = ep.duration - 0.4                                                   # the gulp
ep.sound(0.0, 'thud', 0.6)
# ---- HOOK: Ben chewing -> throat cutaway (the gulp) -> face close (oops) -------------------------------------------
ep.shot(0.0, 'chew', set='room', cast={ben: desk('neutral', act=KW.act.chew(at=0.0, until=0.9, rate=1.8))},
        fx=[lab('GUM', -1.0, 1.0 + T1 - 0.05)], cam=KW.cam.medium(ben, side=-18, push=0.10))
ep.shot(T1, 'gulp', set='room', cast={ben: desk('neutral', head=(-8, 0, 0), act=KW.act.swallow(at=max(0.05, TG - T1)))},
        fx=[lab('GULP', 0.0, T2 - T1 - 0.05)], cam=KW.cam.part(ben, 'throat', dist=0.34, side=-60, push=0.12),
        sounds=[(max(0.05, TG - T1), 'thud', 0.5)])
ep.shot(T2, 'oops', set='room', cast={ben: desk('oops')}, fx=[lab('OOPS', 0.0, L(1) - T2 - 0.2)], cam=KW.cam.face(ben, side=-12, push=0.15))
# ---- myth: 7 years in the stomach? (x-ray: the gum sits in the stomach) -------------------------------------------
ep.shot(L(1) - 0.1, 'myth_x', set='xray', xray=ben, organs=XO, cast={ben: xr('huh')},
        fx=[KW.fx.flow(ben, 'food_down', at=0.0, dur=1.4, color='orange', count=3, speed=0.8, stop=0.97),
            lab('7 YEARS?', W(1, 'seven') - L(1) + 0.1, 2.0)],
        cam=KW.cam.xray(ben, 'stomach', view='34', dist=0.62, push=0.30, orbit=20))
ep.shot(L(2) - 0.1, 'nope', set='room', cast={ben: desk('huh', act=KW.act.shake_head(at=0.1, n=2))},
        fx=[lab('NOPE', 0.1, W(2, 'your') - L(2) - 0.1)], cam=KW.cam.face(ben, side=16, push=0.12))
ep.shot(W(2, 'your') - 0.1, 'whole_x', set='xray', xray=ben, organs=XO, cast={ben: xr('huh')},
        fx=[KW.fx.glow(ben, 'stomach', at=0.2, dur=1.2, color='yellow'), KW.fx.pressure(ben, 'stomach', at=1.8, dur=1.6, swell=0.35), lab('UNDIGESTED', 0.15, E(2) - W(2, 'your') - 0.05, size=1.05, color='yellow')],
        cam=KW.cam.xray(ben, 'stomach', view='front', dist=0.48, push=0.15))
# ---- the gut squeezes it along (rung: visible change every 3-4 s) ---------------------------------------------------
ep.shot(L(3) - 0.1, 'squeeze_x', set='xray', xray=ben, organs=XO, cast={ben: xr('neutral')},
        fx=[KW.fx.pressure(ben, 'intestines', at=0.3, dur=2.4, swell=0.35), lab('SQUEEZE', W(3, 'squeezes') - L(3) + 0.05, 2.0)],
        cam=KW.cam.xray(ben, 'intestines', view='34', dist=0.66, push=0.25, orbit=-20))
ep.shot(W(3, 'stomach') - 0.1, 'macro_in', set='macro', macro=gut, fx=[KW.fx.particles('food', at=0.0, speed=0.8, count=20)],
        cam=KW.cam.macro(gut, view='inside', push=0.3))
# ---- 40 hours, out whole (visible consequence ~50 %) -----------------------------------------------------------------
ep.shot(L(4) - 0.1, 'hours', set='room', cast={ben: desk('huh', swell={'belly': 0.5})},
        fx=[KW.fx.counter(0, 40, unit=' HOURS', at=0.1, dur=1.2, pos=(0.5, Y), size=1.1)], cam=KW.cam.medium(ben, side=22, push=0.10))
ep.shot(W(4, 'comes') - 0.1, 'out_x', set='xray', xray=ben, organs=XO, cast={ben: xr('easy')},
        fx=[KW.fx.glow(ben, 'intestines', at=0.1, dur=0.9, color='green'), lab('OUT WHOLE', 0.1, E(4) - W(4, 'comes') + 0.3)],
        cam=KW.cam.xray(ben, 'intestines', view='front', dist=0.60, push=0.15))
# ---- the doctor + colonoscopy (scan) ----------------------------------------------------------------------------------
ep.shot(L(5) - 0.1, 'doc', set='hospital', cast={doc: KW.pose('stand', at='front', face='focus', act=KW.act.nod(at=0.4, n=1))},
        fx=[lab('DOCTOR', 0.1, W(5, 'colonoscopy,') - L(5) - 0.1)], cam=KW.cam.face(doc, side=14, push=0.12))
ep.shot(W(5, 'colonoscopy,') - 0.1, 'scope', set='macro', macro=gut, fx=[KW.fx.particles('food', at=0.0, speed=0.5, count=8),
        lab('1 DAY OLD', W(5, 'likely') - W(5, 'colonoscopy,') + 0.1, E(5) - W(5, 'likely') + 0.2)],
        cam=KW.cam.macro(gut, view='inside', push=0.25))
# ---- lots of gum can block the gut ---------------------------------------------------------------------------------
ep.shot(L(6) - 0.1, 'block_x', set='xray', xray=ben, organs=XO, cast={ben: xr('ache')},
        fx=[KW.fx.flow(ben, 'food_down', at=0.0, dur=2.0, color='orange', count=30, speed=1.0, stop=0.85),
            KW.fx.pressure(ben, 'intestines', at=0.6, dur=2.0, swell=0.6), KW.fx.glow(ben, 'intestines', at=W(6, 'lots') - L(6) + 1.05, dur=1.6, color='red'), lab('LOTS', W(6, 'lots') - L(6) + 0.05, 1.0),
            lab('BLOCKED', W(6, 'lots') - L(6) + 1.05, W(6, 'block') + 0.15 - W(6, 'lots') - 1.05, color='red', size=1.2)],
        cam=KW.cam.xray(ben, 'intestines', view='34', dist=0.70, push=0.25, orbit=15))
ep.shot(W(6, 'block') + 0.3, 'ache', set='room', cast={ben: desk('ache', swell={'belly': 1.0}, left=KW.hand.clutch('belly'))},
        cam=KW.cam.medium(ben, side=-26, push=0.12))
# ---- payoff: one piece is fine, CTA, loop ------------------------------------------------------------------------------
TF = W(6, 'one')
ep.shot(TF - 0.1, 'fine', set='room', cast={ben: desk('easy', act=KW.act.nod(at=0.5, n=1))},
        fx=[lab('FINE', 0.1, E(6) - TF + 0.1),
            KW.fx.label('SWALLOWED?', at=E(6) - TF + 0.3, pos=(0.5, 0.30), dur=LOOPT - E(6) - 0.4, **YL),
            KW.fx.label('COMMENT BELOW', at=E(6) - TF + 0.4, pos=(0.5, 0.235), dur=LOOPT - E(6) - 0.5, color='white', size=0.5)],
        cam=KW.cam.face(ben, side=10))
ep.shot(LOOPT, 'loop', set='room', cast={ben: desk('neutral', act=KW.act.chew(at=0.0, until=0.4, rate=1.8))},
        fx=[lab('GUM', 0.0, 1.0)], cam=KW.cam.loop())
ep.mouth_fix = True; ep.eyes_fix = True; ep.relight_after_pose = True
ep.run()
