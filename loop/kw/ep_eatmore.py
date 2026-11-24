"""Kinda Wild Films - 'How Food Companies Make You Eat More' (explainer).  Written only with kwkit.
Sources (opened 2026-11-22):
  NPR / Here & Now, Michael Moss interview https://www.npr.org/sections/thesalt/2015/12/16/459981099/how-the-food-industry-helps-engineer-our-cravings
  NIH Research Matters https://www.nih.gov/news-events/nih-research-matters/eating-highly-processed-foods-linked-weight-gain
Line sources: 1 NPR 'so perfectly engineered to get us to not just like them but to want more and more of them';
2 NPR 'it's Howard who coined the expression "bliss point" to capture that perfect amount of sweetness';
3 NPR 'a new soda flavor ... no less than 59 variations of sweetness ... subjected those to 3,000 taste tests';
4 NPR 'the perfect amount of sweetness - not too little, not too much - is at the very top of the curve';
5 NIH 'On the ultra-processed diet, people ate about 500 calories more per day' (20 healthy adults);
6 NIH 'People also ate faster on the ultra-processed diet and gained 2 pounds on average' / 'two weeks on both of the diets';
7 restates the title (payoff).
"""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kwkit as KW
# lead 25 Nov (B), this episode only: stronger readable upper face (cast-master defaults untouched)
KW.FACES = dict(KW.FACES)
KW.FACES.update({'worry': {'worry': min(1.0, 0.9 * 1.5), 'wide': min(1.0, 0.35 * 1.5)},
                 'focus': {'frown': min(1.0, 0.35 * 1.5), 'squint': min(1.0, 0.15 * 1.5)},
                 'relief': {'smile': 1.0, 'squint': 0.1}, 'smile': {'smile': 1.0}})

ep = KW.Episode('ep_eatmore', injury="wanting more", voice_lines=[
    "Food companies tune every snack so your brain keeps wanting more.",
    "Scientist Howard Moskowitz named the target the bliss point, the exact sweetness people like most.",
    "For one soda, he mixed fifty nine versions and ran three thousand taste tests.",
    "The winner sat at the very top, not too sweet, not too plain.",
    "In an NIH study, adults on ultra processed food ate about five hundred more calories a day.",
    "They ate faster too, and gained about two pounds in two weeks.",
    "That is how food companies make you eat more.",
], music='sneaky_snitch', gap=0.4)

# ---- cast ---------------------------------------------------------------------------------------------------
ben = ep.person('Ben', 'civilian', 'eatmore-ben', gender='m', age='young', race='caucasian', hair='short02', tee='teal')
sci = ep.person('Howard', 'scientist', 'eatmore-sci', gender='m', age='old', race='caucasian', hair='short02', clipboard=True)
nrv = ep.macro('nerve')
sto = ep.macro('stomach')

L = ep.line; E = ep.line_end
sip = lambda at=0.0, face='smile', dur=0.8, **k: KW.pose('stand', at='counter', right=KW.hand.hold('can', where='mouth'), face=face,
                                                         act=KW.act.drink(at=at, dur=dur), **k)
xr = lambda **k: KW.pose('sit', at='room.desk', **k)
ep.sound(0.0, 'thud', 1.0)                    # hook: a real transient on frame 0 (never a whoosh)

# ---- HOOK 0-3 s: one sip -> inside the head, the brain lights up -> the craving signal -------------------------
ep.shot(0.0, 'room_sip', set='room', cast={ben: sip(at=0.0)}, cam=KW.cam.face(ben, push=0.2, side=14, dist=0.7, shake=0.4, orbit=10))
ep.shot(1.0, 'xray_brain', set='xray', xray=ben, organs=['brain', 'skull', 'esophagus'], cast={ben: xr(face='smile')},
        fx=[KW.fx.flow(ben, 'food_down', at=0.0, color='yellow', count=60, speed=1.2), KW.fx.glow(ben, 'brain', at=0.2, dur=0.8, color='yellow')],
        cam=KW.cam.xray(ben, 'brain', view='34', push=0.55, orbit=30, dist=0.62))
ep.shot(2.2, 'macro_more', set='macro', macro=nrv, fx=[KW.fx.label('MORE', at=0.15, pos=(0.5, 0.62), color='red')],
        cam=KW.cam.macro(nrv, view='wide', push=0.3, hits=[0.15]))
# ---- 2: the scientist and the bliss point --------------------------------------------------------------------
ep.shot(L(1) + 0.1, 'lab_sci', set='room', cast={sci: KW.pose('stand', at='stand', left='clipboard', right='write', face='focus', act=KW.act.nod(at=0.6, n=1))},
        cam=KW.cam.medium(sci, side=-30, height=0.1, push=0.12))   # C2: the paper faces his right (normal -0.75 x): from side=24 the board was edge-on
ep.shot(L(1) + 1.9, 'room_like', set='room', cast={ben: sip(at=0.1, dur=1.2)}, cam=KW.cam.face(ben, side=18, push=0.15))   # ruling k: mirrored to the free side, the raised can hid both eyes from side=-18
ep.shot(L(1) + 3.6, 'macro_bliss', set='macro', macro=nrv, fx=[KW.fx.label('BLISS', at=0.1, pos=(0.5, 0.62), color='red')],
        cam=KW.cam.macro(nrv, view='wide', push=0.25, hits=[0.1]), sounds=[(0.1, 'thud', 0.8)])
# ---- 3: fifty nine versions, three thousand taste tests ---------------------------------------------------------
ep.shot(L(2) - 0.1, 'room_mix', set='room', cast={ben: sip(at=0.2, face='focus', dur=1.2)},
        cam=KW.cam.medium(ben, side=26, height=0.12, push=0.1))
ep.shot(L(2) + 1.7, 'room_taste', set='room', cast={ben: sip(at=0.1, face='focus', dur=1.2)}, cam=KW.cam.profile(ben, 'mouth', push=0.15))
ep.shot(L(2) + 3.3, 'lab_note', set='room', cast={sci: KW.pose('stand', at='stand', left='clipboard', right='write', face='smile', act=KW.act.nod(at=0.3, n=2))},
        cam=KW.cam.face(sci, side=16, push=0.15))
# ---- 4: the top of the curve (re-hook) --------------------------------------------------------------------------
ep.shot(L(3) - 0.1, 'xray_peak', set='xray', xray=ben, organs=['brain', 'skull'], cast={ben: xr(face='smile')},
        fx=[KW.fx.pressure(ben, 'brain', at=0.1, dur=1.4, swell=0.2), KW.fx.glow(ben, 'brain', at=0.1, dur=1.2, color='yellow')],
        cam=KW.cam.xray(ben, 'brain', view='front', push=0.18, dist=0.5, hits=[0.25]), sounds=[(0.25, 'thud', 0.8)])
ep.shot(L(3) + 1.9, 'room_peak', set='room', cast={ben: sip(at=0.0, dur=0.9).then(1.0, face='relief')}, cam=KW.cam.face(ben, side=12, push=0.18, hits=[1.0]))   # addendum I R2
# ---- 5: the NIH study: about 500 more calories a day ------------------------------------------------------------
ep.shot(L(4) - 0.1, 'hos_study', set='hospital',
        cast={ben: KW.pose('sit', at='bed_sit', right=KW.hand.hold('spoon', where='mouth'), face='calm', act=KW.act.eat(at=7 / 24, bites=1, beats=(19, 6, 4, 16), chew=(31, 39), drop=0.37)),     # R3: lift f447-466, in -472, out -476, one chew f478-486
              sci: KW.pose('stand', at='bedside_r', left='clipboard', right='write', face='focus', look=ben)},
        cam=KW.cam.two_shot(ben, sci, side=12, push=0.1))
ep.shot(L(4) + 1.9, 'xray_stomach', set='xray', xray=ben, organs=['esophagus', 'stomach', 'intestines'], cast={ben: xr(face='calm')},
        fx=[KW.fx.flow(ben, 'food_down', at=0.0, color='yellow', count=70, speed=1.0), KW.fx.pressure(ben, 'stomach', at=0.3, dur=1.4, swell=0.3)],
        cam=KW.cam.xray(ben, 'stomach', view='front', push=0.3))
ep.shot(L(4) + 3.7, 'macro_500', set='macro', macro=sto, fx=[KW.fx.particles('food', at=0.0, speed=0.6, count=14), KW.fx.label('+500', at=0.15, pos=(0.5, 0.62), color='blue', size=1.3)],
        cam=KW.cam.macro(sto, view='wide', push=0.3, hits=[0.15]), sounds=[(0.15, 'thud', 0.8)])
# ---- 6: ate faster, two pounds in two weeks ----------------------------------------------------------------------
ep.shot(L(5) - 0.1, 'hos_fast', set='hospital', cast={ben: KW.pose('sit', at='bed_sit', right=KW.hand.hold('spoon', where='mouth'), face='focus', lean=8, act=KW.act.eat(at=2 / 24, bites=2, beats=(7, 3, 2, 6), drop=0.20, nod=3, trunk=1, gaze='hold'))},     # R3/R4: two 18-frame bites f576-594-611, bent ~8 deg
        cam=KW.cam.face(ben, side=-18, push=0.15, shake=0.3))
ep.shot(L(5) + 1.5, 'calendar', set='graphic', world='hospital', fx=[KW.fx.calendar(weeks=2, at=0.05, dur=0.6)], cam=KW.cam.prop())
ep.shot(L(5) + 2.9, 'hos_belly', set='hospital', cast={ben: KW.pose('sit', at='bed_sit', left=KW.hand.clutch('belly'), face='worry', head=(14, 0, 0)).then(0.3, swell={'belly': 0.8})},
        cam=KW.cam.medium(ben, side=22, push=0.12))
# ---- 7: payoff, loop back to the sip ----------------------------------------------------------------------------
ep.shot(L(6) - 0.1, 'room_can', set='room', cast={ben: KW.pose('stand', at='counter', right=KW.hand.hold('can', where='mouth'), face='worry', head=(6, -12, 0)).then(0.6, face='calm')},
        cam=KW.cam.face(ben, side=14, push=0.15))   # ruling k: mirrored to the free side, the index tip and can bottom covered the nose from side=-14 (elbow already out 25-27 deg)
ep.shot(L(6) + 1.4, 'room_loop', set='room',
        cast={ben: KW.pose('stand', at='counter', right=KW.hand.hold('can', where='mouth'), face='calm').then(0.3, face='smile')},   # R8: no sip, still M1 hold, calm->smile from 0.3 s
        cam=KW.cam.loop())

# blinks keyed to the frame timeline (addendum G, R7); shot 11 soft eye close f416-423, open f424-427
ep.blinks = {'Ben': [258, 660, 695, (416, 420, 423, 427)], 'Howard': [125, 334]}
ep.run()
