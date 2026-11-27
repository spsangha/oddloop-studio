"""Kinda Wild Films ep21 (mishap M3) - 'He Laughed So Hard He Passed Out'.  Brief: kindawild/21_laugh_faint/brief.md.
Facts: Nishida, Hirota & Tokeshi, J Med Case Reports 2008 'Laugh syncope as a rare sub-type of the situational syncopes'
(56-year-old man at a dinner: a joke, 'Ha, ha, ha' until out of breath, surroundings went dark, fell forward with his head on the
table, unresponsive for a few seconds; forced expirations with a Valsalva-type effect raise chest pressure, reduce venous return
and cardiac output, brief drop in brain blood flow; 'extremely rare'), Gaitatzis & Petzold, The Neurologist 2012, Lancet case.
Ben laughing at his desk -> chest close -> face close (eyes roll, OUT); laugh + flushed face; x-ray: lungs squeezed, slow blood
back to the heart, less blood to the brain; vision dark; he slumps forward onto the desk (D3 faint move, ~56 %); doctor (Howard);
Ben wakes up; payoff: rare, CTA; loop to the frame-0 laugh.
"""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kwkit as KW
os.environ.setdefault('KW_LIGHT', '1')
HERE = os.path.dirname(os.path.abspath(__file__))
ep = KW.Episode('ep_laughfaint', injury="passed out",
                voice_lines=[l.strip() for l in open(os.path.join(HERE, 'ep_laughfaint.txt')) if l.strip()],
                music='sneaky_snitch', gap=0.6)
ben = ep.person('Ben', 'civilian', 'eatmore-ben', gender='m', age='young', race='caucasian', hair='short02', tee='teal')
doc = ep.person('Howard', 'scientist', 'eatmore-sci', gender='m', age='old', race='caucasian', hair='short02')

FPS = 24; F = 1.0 / FPS
L = ep.line; E = ep.line_end; W = ep.word
KW.FACES.update({'out': {'blink': 1.0, 'open': 0.25}, 'woozy': {'blink': 0.55, 'worry': 0.4}, 'huh': {'x_surprise': 0.35, 'worry': 0.4},
                 'easy': {'smile': 0.6}})
ep.waive = {"HOOK inside the body": "brief: vidIQ rule 1 person -> chest cutaway -> face close; the x-ray comes later",
            "shot ": "brief: payoff/CTA shot holds over the last line + CTA",
            "HOOK cut <= 200 ms after the last word": "brief: CTA over the payoff shot, then the frame-0 loop shot"}
desk = lambda face='neutral', **k: KW.pose('sit', at='desk', face=face, **k)
HB = dict(left=KW.hand.clutch('belly'), right=KW.hand.clutch('chest'))       # holding his belly + chest (laughing); keeps the hands off the desk top
xr = lambda face='neutral', **k: KW.pose('sit', at='room.desk', face=face, **k)
LAUGH = lambda at=0.0: KW.act.breathe_hard(at=at, rate=3.2)
YL = dict(color='yellow', size=1.2); Y = 0.89
ep.label_outline = True; ep.label_maxw = 820.0; ep.label_lens_fix = True
def lab(txt, at, dur, **k): return KW.fx.label(txt, at=at, pos=(0.5, Y), dur=dur, **(k or YL))

T1 = 0.92; T2 = 1.92                                                     # hook cuts (f22, f46)
ep.duration = round(E(6) + 2.3, 4); LOOPT = ep.duration - 0.4
ep.sound(0.0, "thud", 0.6)
# ---- HOOK: Ben laughing -> chest cutaway (heaving) -> face close (eyes roll: OUT) ----------------------------------------
ep.shot(0.0, 'laugh', set='room', cast={ben: desk('laugh', act=LAUGH())},
        fx=[lab('HA HA', -1.0, 1.0 + T1 - 0.05)], cam=KW.cam.medium(ben, side=-18, push=0.10))
ep.shot(T1, 'chest', set='room', cast={ben: desk('laugh', act=LAUGH())},
        fx=[lab('NO AIR', 0.0, T2 - T1 - 0.05)], cam=KW.cam.part(ben, 'chest', dist=0.45, side=-35, push=0.12))
ep.shot(T2, 'out', set='room', cast={ben: desk('laugh', flush=0.5).then(0.15, face='out', head=(14, 0, 8), blend=0.25)},
        fx=[lab('OUT', 0.1, L(1) - T2 - 0.25, color='red', size=1.3)], cam=KW.cam.face(ben, side=-12, push=0.15))
# ---- ha ha ha until out of breath: flushed face ------------------------------------------------------------------------
ep.shot(L(1) - 0.1, 'haha', set='room', cast={ben: desk('laugh', act=LAUGH(), flush=0.15).then(1.2, flush=0.75, blend=1.0)},
        fx=[lab('HA HA HA', 0.1, W(1, 'ran') - L(1) - 0.1), lab('NO BREATH', W(1, 'ran') - L(1) + 0.05, E(1) - W(1, 'ran') + 0.3, color='red')],
        cam=KW.cam.face(ben, side=16, push=0.12))
# ---- each laugh squeezes the chest (x-ray lungs) -----------------------------------------------------------------------
ep.shot(L(2) - 0.1, 'lungs_x', set='xray', xray=ben, organs=['airway', 'lungs', 'heart'], cast={ben: xr('laugh', act=LAUGH())},
        fx=[KW.fx.flow(ben, 'air_out_mouth', at=0.0, dur=2.6, color='white', count=40, speed=1.6),
            KW.fx.pressure(ben, 'lungs', at=0.6, dur=2.0, swell=0.35), lab('SQUEEZE', W(2, 'squeezes') - L(2), 1.6)],
        cam=KW.cam.xray(ben, 'lungs', view='34', dist=0.80, push=0.25, orbit=15))
# ---- less blood back to the heart --------------------------------------------------------------------------------------
ep.shot(L(3) - 0.1, 'heart_x', set='xray', xray=ben, organs=['lungs', 'heart', 'vessels'], cast={ben: xr('laugh')},
        fx=[KW.fx.flow(ben, 'blood_heart', at=0.0, dur=3.0, color='red', count=50, speed=0.5, stop=0.6),
            KW.fx.glow(ben, 'heart', at=0.5, dur=1.8, color='blue'), lab('SLOW', W(3, 'slows') - L(3), 1.8, color='red')],
        cam=KW.cam.xray(ben, 'heart', view='34', dist=0.55, push=0.25, orbit=-15))
# ---- less blood to the brain -> vision dark -> slump onto the desk (the faint, ~56 %) ----------------------------------
ep.shot(L(4) - 0.1, 'brain_x', set='xray', xray=ben, organs=['brain', 'vessels', 'skull'], cast={ben: xr('woozy')},
        fx=[KW.fx.flow(ben, 'brain_blood', at=0.0, dur=2.0, color='red', count=40, speed=0.6, stop=0.45),
            KW.fx.glow(ben, 'brain', at=0.4, dur=1.2, color='blue'), lab('LOW BLOOD', 0.15, W(4, 'vision') - L(4) - 0.2, color='red')],
        cam=KW.cam.xray(ben, 'brain', view='34', dist=0.55, push=0.2, orbit=12))
TS = W(4, 'slumped')
ep.shot(W(4, 'vision') - 0.1, 'dark', set='room', cast={ben: desk('woozy', flush=0.3).then(0.5, face='out', head=(10, 0, 6), blend=0.4)},
        fx=[lab('DARK', 0.1, TS - W(4, 'vision') - 0.35)], cam=KW.cam.face(ben, side=-20, push=0.2))
ep.shot(TS - 0.25, 'slump', set='room',
        cast={ben: desk('out', head=(8, 0, 6), **HB).then(0.15, lean=38, head=(40, 0, 10), blend=0.45)},
        fx=[lab('FAINTED', 0.55, E(4) - TS + 0.25, color='red')], cam=KW.cam.medium(ben, side=28, push=0.06),
        sounds=[(0.55, 'thud', 0.7)])
# ---- the doctor: laugh syncope; he wakes in seconds --------------------------------------------------------------------
ep.shot(L(5) - 0.1, 'doc', set='hospital', cast={doc: KW.pose('stand', at='front', face='focus', act=KW.act.nod(at=0.5, n=1))},
        fx=[lab('SYNCOPE', W(5, 'syncope,') - L(5) - 0.1, W(5, 'he') - W(5, 'syncope,') + 0.1)], cam=KW.cam.face(doc, side=14, push=0.1))
TW = W(5, 'woke')
ep.shot(W(5, 'he') - 0.1, 'wake', set='room',
        cast={ben: desk('out', lean=38, head=(40, 0, 10), **HB).then(0.35, face='huh', lean=0, head=(0, 0, 0), blend=0.6)},
        fx=[lab('SECONDS', TW - W(5, 'he') + 0.1, E(5) - TW + 0.3)], cam=KW.cam.medium(ben, side=-24, push=0.08))
# ---- payoff: very rare; dizzy -> doctor; CTA; loop -------------------------------------------------------------------
TF = L(6)
ep.shot(TF - 0.1, 'fine', set='room', cast={ben: desk('easy', act=KW.act.nod(at=0.5, n=1))},
        fx=[lab('RARE', 0.1, W(6, 'tell') - TF),
            KW.fx.label('FAINTED?', at=E(6) - TF + 0.3, pos=(0.5, 0.30), dur=LOOPT - E(6) - 0.4, **YL),
            KW.fx.label('COMMENT BELOW', at=E(6) - TF + 0.4, pos=(0.5, 0.235), dur=LOOPT - E(6) - 0.5, color='white', size=0.5)],
        cam=KW.cam.face(ben, side=10))
ep.shot(LOOPT, 'loop', set='room', cast={ben: desk('laugh', act=LAUGH())},
        fx=[lab('HA HA', 0.0, 1.0)], cam=KW.cam.loop())
ep.mouth_fix = True; ep.eyes_fix = True; ep.relight_after_pose = True
ep.run()
