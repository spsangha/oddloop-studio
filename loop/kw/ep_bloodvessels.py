"""Kinda Wild Films - 'How Long Your Blood Vessels Really Are' (myth buster).  Written only with kwkit.
Brief: kindawild/06_bloodvessels/brief.md (+ ADDENDUM A); shot rows: directions.md 1-21, re-timed to ep_bloodvessels.vo.json.
Facts: kindawild/06_bloodvessels/facts.md (S1 Poole et al. 2021 PMC7867635; S2 Poole & Musch 2023 PMC10165549;
S3 Krogh Nobel lecture 1920; S4 Wikipedia 'Blood vessel'; S5/S6 Earth circumference). Script and labels follow facts.md F1-F10.
Earth texture: NASA Blue Marble Next Generation (July 2004), public domain, credit "NASA Earth Observatory".
Voice line starts (s): L1 0.00, L2 5.09, L3 9.44, L4 14.76, L5 20.66, L6 24.78; speech ends 29.97, film 30.12 s (723 frames).
"""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kwkit as KW
# same as ep05 (lead 25 Nov B): stronger readable upper face, this episode only (cast-master defaults untouched)
KW.FACES = dict(KW.FACES)
KW.FACES.update({'worry': {'worry': min(1.0, 0.9 * 1.5), 'wide': min(1.0, 0.35 * 1.5)},
                 'focus': {'frown': min(1.0, 0.35 * 1.5), 'squint': min(1.0, 0.15 * 1.5)},
                 'relief': {'smile': 1.0, 'squint': 0.1}, 'smile': {'smile': 1.0}})

HERE = os.path.dirname(os.path.abspath(__file__))
ep = KW.Episode('ep_bloodvessels', injury="blood vessels",
                voice_lines=[l.strip() for l in open(os.path.join(HERE, 'ep_bloodvessels.txt')) if l.strip()],
                music='sneaky_snitch', gap=0.4)

# ---- cast (v1.0, ep05 faces and clothes) ---------------------------------------------------------------------
ben = ep.person('Ben', 'civilian', 'eatmore-ben', gender='m', age='young', race='caucasian', hair='short02', tee='teal')
sci = ep.person('Howard', 'scientist', 'eatmore-sci', gender='m', age='old', race='caucasian', hair='short02', clipboard=True)
art = ep.macro('artery')

L = ep.line
F = lambda n: n / 24.0                       # brief 6b local frames -> seconds
TILT = (6, -12, 0)
# seated Ben (A4): no hand given -> the kit's seated rest ('lap'): relaxed hands, palm down on mid-thigh
bed = lambda face='worry', head=TILT, **k: KW.pose('sit', at='bed_sit', face=face, head=head, look=sci, lean=4, **k)
# Howard writing at the bedside (on set in every hospital shot so look=sci has a real target; R2)
hw = lambda face='focus', **k: KW.pose('stand', at='bedside_r', left='clipboard', right='write', face=face, **k)
hstand = lambda face='focus', **k: KW.pose('stand', at='stand', left='clipboard', right='write', face=face, **k)
xr = lambda **k: KW.pose('sit', at='room.desk', **k)
XO = ['vessels', 'heart']
cells = lambda n, sp: KW.fx.particles('blood', at=0.0, speed=sp, count=n)
YL = dict(color='yellow', size=1.2)
LP = (0.5, 0.84)                             # labels: upper third (A3), centred
ep.sound(0.0, 'thud', 1.0)                   # shot 1 hook transient

# ---- L1  "Ben sits on a hospital bed as Howard tells him his blood vessels could wrap around Earth twice." -----
ep.shot(0.0, 'hos_hook', set='hospital', cast={ben: bed(), sci: hw()}, cam=KW.cam.face(ben, side=14, push=0.2))
ep.shot(0.90, 'xray_heart', set='xray', xray=ben, organs=XO, cast={ben: xr(face='worry')},
        fx=[KW.fx.flow(ben, 'blood_heart', at=0.0, color='red', count=40, speed=1.2),
            KW.fx.flow(ben, 'blood_arm_L', at=0.0, color='red', count=30, speed=1.2, sound=False),
            KW.fx.flow(ben, 'blood_arm_R', at=0.0, color='red', count=30, speed=1.2, sound=False),
            KW.fx.glow(ben, 'vessels', at=0.2, dur=0.8, color='red')],
        cam=KW.cam.xray(ben, 'heart', view='34', dist=0.62, push=0.45, orbit=25))
ep.shot(1.88, 'hos_two', set='hospital', cast={ben: bed(), sci: hw(look=ben, act=KW.act.nod(at=F(14), n=1))},
        cam=KW.cam.two_shot(ben, sci, side=12, push=0.1))
ep.shot(3.09, 'earth_claim', set='graphic', world='night',
        fx=[KW.fx.earth('wrap2', at=0.06, dur=0.86, spin=8.0, lon=10.0, lat=15.0, pulse_at=0.95),
            KW.fx.label('2X', at=4.12 - 3.09, pos=LP, **YL)],
        cam=KW.cam.prop(push=0.15, fstop=11), sounds=[(4.12 - 3.09, 'thud', 0.8)])
# ---- L2  "But that famous number came from counting tiny capillaries in guinea pig muscle." --------------------
ep.shot(L(1), 'hos_ease', set='hospital', cast={ben: bed().then(F(19), face='focus', head=(0, 0, 0)), sci: hw()},
        cam=KW.cam.face(ben, side=-16, push=0.15))
ep.shot(L(1) + 0.97, 'lab_face', set='room', cast={sci: hstand(act=KW.act.nod(at=F(15), n=1))}, cam=KW.cam.face(sci, side=18, push=0.15))
ep.shot(L(1) + 2.80, 'macro_crowd', set='macro', macro=art, fx=[cells(24, 0.6)], cam=KW.cam.macro(art, view='wide', side=0, push=0.3))
# ---- L3  "Then the old estimate applied those counts to a huge man weighing about three hundred fifteen pounds." -
ep.shot(L(2), 'lab_write', set='room', cast={sci: hstand(head=(15, 0, 0))}, cam=KW.cam.medium(sci, side=-22, height=0.1, push=0.12))
ep.shot(L(2) + 0.92, 'macro_crowd2', set='macro', macro=art, fx=[cells(24, 0.5)], cam=KW.cam.macro(art, view='wide', side=30, push=0.3))
ep.shot(L(2) + 1.98, 'room_stand', set='room', cast={ben: KW.pose('stand', at='stand', face='worry', head=TILT)},
        cam=KW.cam.wide(ben, side=30, push=0.08))
ep.shot(L(2) + 3.22, 'xray_315', set='xray', xray=ben, organs=XO, cast={ben: xr(face='calm')},
        fx=[KW.fx.glow(ben, 'vessels', at=0.1, dur=1.2, color='yellow'), KW.fx.label('315 LB', at=0.10, pos=LP, **YL)],
        cam=KW.cam.xray(ben, 'vessels', view='front', dist=0.95, push=0.15), sounds=[(0.10, 'thud', 0.8)])
# ---- L4  "Real human muscle holds far fewer capillaries, and typical bodies carry less than half that muscle." ---
ep.shot(L(3), 'macro_sparse', set='macro', macro=art, fx=[cells(6, 0.4)], cam=KW.cam.macro(art, view='wide', side=-30, push=0.25))
ep.shot(L(3) + 1.54, 'lab_nods', set='room', cast={sci: hstand(act=KW.act.nod(at=F(7), n=2))}, cam=KW.cam.face(sci, side=-14, push=0.15))
ep.shot(L(3) + 3.46, 'hos_nod', set='hospital', cast={ben: bed(face='focus', head=(0, 0, 0), act=KW.act.nod(at=F(10), n=1)), sci: hw()},
        cam=KW.cam.medium(ben, side=22, push=0.12))
ep.shot(L(3) + 4.56, 'macro_sparse2', set='macro', macro=art, fx=[cells(6, 0.4)], cam=KW.cam.macro(art, view='wide', side=15, push=0.3))
# ---- L5  "So scientists now estimate about six to twelve thousand miles." -----------------------------------------
ep.shot(L(4) + 0.19, 'hos_relief', set='hospital',
        cast={ben: bed(face='focus', head=(0, 0, 0)).then(F(12), face='relief'), sci: hw(look=ben).then(F(11), look=None, head=(18, 0, 0))},
        cam=KW.cam.two_shot(ben, sci, side=-14, push=0.1))
ep.shot(L(4) + 1.81, 'xray_miles', set='xray', xray=ben, organs=XO, cast={ben: xr(face='calm')},
        fx=[KW.fx.flow(ben, 'blood_heart', at=0.0, color='red', count=40, speed=1.0),
            KW.fx.flow(ben, 'blood_neck_r', at=0.0, color='red', count=30, speed=1.0, sound=False),
            KW.fx.flow(ben, 'blood_arm_L', at=0.0, color='red', count=24, speed=1.0, sound=False),
            KW.fx.glow(ben, 'vessels', at=0.1, color='yellow'), KW.fx.label('6-12K MI', at=0.10, pos=LP, **YL)],
        cam=KW.cam.xray(ben, 'vessels', view='34', dist=0.62, orbit=-15, push=0.15), sounds=[(0.10, 'thud', 0.7)])
# ---- L6  "That means Ben's tiniest blood vessels would stretch less than halfway around Earth, not twice." ------
ep.shot(L(5) - 0.18, 'hos_smile', set='hospital', cast={ben: bed(face='relief', head=(0, 0, 0)).then(F(14), face='smile'), sci: hw()},
        cam=KW.cam.profile(ben, 'face', push=0.15))
ep.shot(L(5) + 1.62, 'macro_mid', set='macro', macro=art, fx=[cells(14, 0.8)], cam=KW.cam.macro(art, view='wide', side=-15, push=0.3))
ep.shot(L(5) + 2.88, 'earth_payoff', set='graphic', world='night',
        fx=[KW.fx.earth('half', at=0.04, dur=0.96, spin=0.0, lon=10.0, lat=15.0, cam_raise=20.0),
            KW.fx.label('NOT 2X', at=29.11 - 27.66, pos=LP, **YL)],
        cam=KW.cam.prop(push=0.1, fstop=11, lens=70), sounds=[(29.11 - 27.66, 'thud', 0.8)])
ep.shot(L(5) + 4.62, 'hos_loop', set='hospital', cast={ben: bed(face='smile', head=(0, 0, 0)).then(F(6), face='worry', head=TILT), sci: hw()},
        cam=KW.cam.loop())

# blinks (absolute frames, brief 6b): 3 Ben f20-24; 6 Howard f22-26; 8 Howard f14-18; 10 Ben f16-20; 14 Ben f24-28;
# 16 Ben soft eye close f12-19 (relief), Howard f6-10; 18 Ben f6-10.  None in 1, 5, 13, 21.
ep.waive = {'21 shots': 'brief ep06 sec 6/P1: 21 shots, lead 24 Nov',
            'HOOK injury named in sentence 1': 'brief ep06 sec 3: script final, lead 24 Nov',
            'HOOK 8-11 words spoken in 0-3 s': 'brief ep06 sec 3: script final, lead 24 Nov'}
ep.blinks = {'Ben': [65, 290, 461, (512, 515, 518, 521), 596], 'Howard': [167, 241, 506]}
ep.run()
