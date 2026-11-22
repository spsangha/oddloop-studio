"""Kinda Wild Films - 'Why Brain Freeze Hurts Your Forehead' (explainer).  Written only with kwkit.
Sources (opened 2026-11-22):
  Johns Hopkins https://www.hopkinsmedicine.org/health/conditions-and-diseases/how-to-ease-brain-freeze
  Cleveland Clinic https://my.clevelandclinic.org/health/diseases/21478-brain-freeze
Line sources: 1 CC 'a brief but intense pain in the front part of your head'; 2 JH 'drink a large quantity of very cold ...
liquid, you drop the temperature of the palate (the roof of your mouth)'; 3 JH 'The blood vessels automatically constrict -
it's a survival reflex to maintain your body's core temperature'; 4 JH 'After the squeeze ... the blood vessels open up -
quickly'; 5 JH 'This rebound dilation sends a pain signal ... through ... the trigeminal nerve, whose upper branch extends into
the midface and forehead'; 6 JH 'referred pain ... the palate ... but the sensation is experienced higher up in the head';
7 JH/CC 'press your tongue ... against the roof of your mouth' (CC: 'to transfer warmth'; 'lasts only a few seconds').
"""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kwkit as KW

ep = KW.Episode('ep_brainfreeze', injury="forehead burn", voice_lines=[
    "One gulp of icy slushie made his forehead burn with pain.",
    "He gulped a huge mouthful, and the freezing slush chilled the roof of his mouth.",
    "Tiny blood vessels there squeezed tight to protect his body's heat.",
    "Then they suddenly burst wide open again.",
    "That rebound sent a pain signal through the trigeminal nerve, which reaches up into the forehead.",
    "The pain hit his forehead, but it started in his mouth.",
    "He pressed his warm tongue to the roof of his mouth, and the ache faded.",
], music='sneaky_snitch', gap=0.4)

# ---- cast ---------------------------------------------------------------------------------------------------
sam = ep.person('Sam', 'civilian', 'freeze-sam', gender='m', age='young', race='african', hair='short02', tee='orange')
art = ep.macro('artery')
nrv = ep.macro('nerve')

L = ep.line; E = ep.line_end
sip = lambda at=0.0, face='pain', **k: KW.pose('drive', at='driver', right=KW.hand.hold('slushie', where='mouth'), left='wheel',
                                               face=face, act=KW.act.drink(at=at, dur=0.8), **k)
xr = lambda **k: KW.pose('sit', at='room.desk', **k)
ep.sound(0.0, 'thud', 1.0)                    # hook: a real transient on frame 0 (never a whoosh)

# ---- HOOK 0-3 s: mid-gulp, hand on forehead -> inside the head -> the palate artery clamps ------------------------
ep.shot(0.0, 'car_gulp', set='car', cast={sam: sip(at=0.0, flush=0.6)}, cam=KW.cam.face(sam, push=0.2, side=14, dist=0.7, shake=0.5, orbit=10))
ep.shot(1.0, 'xray_head', set='xray', xray=sam, organs=['brain', 'vessels', 'skull'], cast={sam: xr(face='pain')},
        fx=[KW.fx.flow(sam, 'brain_blood', at=0.0, color='blue', count=60, speed=1.2, stop=0.6), KW.fx.glow(sam, 'vessels', at=0.2, dur=0.8, color='blue')],
        cam=KW.cam.xray(sam, 'brain', view='34', push=0.55, orbit=30, dist=0.62))
ep.shot(2.2, 'macro_cold', set='macro', macro=art, fx=[KW.fx.particles('blood', at=0.0, speed=0.3, count=20), KW.fx.label('FROZEN', at=0.15, pos=(0.5, 0.62), color='yellow')],
        cam=KW.cam.macro(art, view='wide', push=0.3, hits=[0.15]))
# ---- 2: the gulp chills the palate ----------------------------------------------------------------------------
ep.shot(L(1) + 0.1, 'car_medium', set='car', cast={sam: KW.pose('drive', at='driver', right=KW.hand.hold('slushie', where='mouth'), left='wheel', face='focus', act=KW.act.drink(at=0.1, dur=1.4))},
        cam=KW.cam.medium(sam, side=28, height=0.12, push=0.1))
ep.shot(L(1) + 1.9, 'xray_mouth', set='xray', xray=sam, organs=['vessels', 'skull', 'airway'], cast={sam: xr(face='strain')},
        fx=[KW.fx.flow(sam, 'food_down', at=0.0, color='blue', count=50, speed=0.8), KW.fx.label('ICE COLD', at=0.2, pos=(0.5, 0.62), color='yellow')],
        cam=KW.cam.xray(sam, 'vessels', view='profile', push=0.15, dist=0.5))
ep.shot(L(1) + 3.3, 'car_chill', set='car', cast={sam: KW.pose('drive', at='driver', right=KW.hand.hold('slushie', where='mouth'), left='wheel', face='shock')},
        cam=KW.cam.face(sam, side=10, push=0.15, shake=0.3))
# ---- 3: vessels squeeze ----------------------------------------------------------------------------------------
ep.shot(L(2) - 0.1, 'macro_squeeze', set='macro', macro=art, fx=[KW.fx.particles('blood', at=0.0, speed=0.2, count=15), KW.fx.label('SQUEEZE', at=0.1, pos=(0.5, 0.62), color='yellow')],
        cam=KW.cam.macro(art, view='wide', push=0.25))
ep.shot(L(2) + 1.6, 'car_wince', set='car', cast={sam: KW.pose('drive', at='driver', right=KW.hand.clutch('forehead'), left='wheel', face='pain', act=KW.act.wince(at=0.2, hard=1.0))},
        cam=KW.cam.face(sam, side=-18, push=0.15, shake=0.5))
# ---- 4: rebound, vessels burst open (re-hook) ---------------------------------------------------------------------
ep.shot(L(3) - 0.1, 'xray_rebound', set='xray', xray=sam, organs=['brain', 'vessels', 'skull'], cast={sam: xr(face='pain')},
        fx=[KW.fx.pressure(sam, 'vessels', at=0.1, dur=1.4, swell=0.35), KW.fx.label('WIDE OPEN', at=0.25, pos=(0.5, 0.78), color='red')],
        cam=KW.cam.xray(sam, 'vessels', view='front', push=0.18, dist=0.5, hits=[0.25]), sounds=[(0.25, 'thud', 0.9)])
ep.shot(L(3) + 1.5, 'macro_open', set='macro', macro=art, fx=[KW.fx.particles('blood', at=0.0, speed=0.8, count=20)],
        cam=KW.cam.macro(art, view='wide', push=0.3, hits=[0.1]), sounds=[(0.1, 'rush', 0.8)])
# ---- 5: the trigeminal nerve carries it up to the forehead --------------------------------------------------------
ep.shot(L(4) - 0.1, 'macro_nerve', set='macro', macro=nrv, fx=[KW.fx.label('NERVE', at=0.15, pos=(0.5, 0.62), color='yellow')],
        cam=KW.cam.macro(nrv, view='wide', push=0.3, hits=[0.15]))
ep.shot(L(4) + 1.8, 'xray_nerve', set='xray', xray=sam, organs=['brain', 'vessels', 'skull'], cast={sam: xr(face='pain')},
        fx=[KW.fx.glow(sam, 'brain', at=0.0, dur=1.4, color='red')],
        cam=KW.cam.xray(sam, 'brain', view='34', push=0.2, orbit=-15))
ep.shot(L(4) + 3.6, 'car_forehead', set='car', cast={sam: KW.pose('drive', at='driver', left=KW.hand.clutch('forehead'), right=KW.hand.clutch('head_top'), face='scream', act=KW.act.flinch(at=0.2))},
        cam=KW.cam.face(sam, side=18, push=0.18, shake=0.7, hits=[0.2]), sounds=[(0.2, 'thud', 0.8)])
# ---- 6: forehead pain, mouth problem ---------------------------------------------------------------------------
ep.shot(L(5) - 0.1, 'xray_refer', set='xray', xray=sam, organs=['brain', 'vessels', 'skull'], cast={sam: xr(face='pain')},
        fx=[KW.fx.glow(sam, 'skull', at=0.0, dur=0.8, color='red'), KW.fx.glow(sam, 'vessels', at=0.8, dur=0.8, color='blue')],
        cam=KW.cam.xray(sam, 'skull', view='profile', push=0.15))
ep.shot(L(5) + 1.5, 'car_worry', set='car', cast={sam: KW.pose('drive', at='driver', left=KW.hand.clutch('forehead'), right='wheel', face='worry')},
        cam=KW.cam.medium(sam, side=-24, push=0.12))
# ---- 7: warm tongue on the palate, ache fades, loop back to the gulp ---------------------------------------------
ep.shot(L(6) - 0.1, 'car_tongue', set='car', cast={sam: KW.pose('drive', at='driver', right='to_mouth', left='wheel', face='strain').then(0.9, face='relief')},
        cam=KW.cam.face(sam, side=-14, push=0.15))
ep.shot(L(6) + 1.3, 'xray_warm', set='xray', xray=sam, organs=['brain', 'vessels', 'skull'], cast={sam: xr(face='calm')},
        fx=[KW.fx.flow(sam, 'brain_blood', at=0.0, color='red', count=60, speed=0.9)], cam=KW.cam.xray(sam, 'vessels', view='34', dist=0.5, orbit=-12))
ep.shot(L(6) + 2.6, 'car_loop', set='car',
        cast={sam: KW.pose('drive', at='driver', right=KW.hand.hold('slushie', where='mouth'), left='wheel', face='calm').then(0.3, face='pain', act=KW.act.drink(at=0.3, dur=0.6))},
        cam=KW.cam.loop())

ep.run()
