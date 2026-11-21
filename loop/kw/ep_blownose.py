"""Kinda Wild Films - 'She Blew Her Nose Too Hard' (sequel to the sneeze episode).  Written only with kwkit.
Case: 36-year-old UK woman, nose blowing -> left lamina papyracea (medial orbital wall) fracture + orbital/eyelid
emphysema, no surgery, resolved in 3 weeks.  https://pmc.ncbi.nlm.nih.gov/articles/PMC6040533/
https://www.livescience.com/63012-nose-blowing-eye-socket-fracture.html
"""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kwkit as KW

ep = KW.Episode('ep_blownose', injury="cracked the bone", voice_lines=[
    "Blowing her nose too hard cracked the bone beside her eye.",
    "She was at work, so she pressed a tissue to her face and blew as hard as she could.",
    "The blast forced air up into the hollow sinus right beside her left eye.",
    "That pressure snapped the paper-thin inner wall of her eye socket.",
    "Air rushed through the crack and puffed her eyelid swollen shut.",
    "A hospital scan showed the broken bone and tiny air pockets around her eye.",
    "Three weeks later, the trapped air was gone, without any surgery.",
], music='sneaky_snitch', gap=0.4)

# ---- cast ---------------------------------------------------------------------------------------------------
mia = ep.person('Mia', 'business', 'blownose-mia', gender='f', age='young', race='caucasian', hair='long01')
doc = ep.person('Dr Hale', 'doctor', 'blownose-doc', gender='m', age='middle', race='african', hair='short02', clipboard=True)
bone = ep.macro('bone')                       # the thin eye-socket wall, seen from inside the eye socket

L = ep.line; E = ep.line_end
blow = lambda at=0.0, hard=1.3, **k: KW.pose('sit', at='desk', left='tissue_nose', right='tissue_nose', face='strain', act=KW.act.blow_nose(at=at, dur=1.6, hard=hard), flush=0.7, **k)
xr = lambda **k: KW.pose('sit', at='room.desk', **k)
ep.sound(0.0, 'thud', 1.0)                    # hook: a real transient on frame 0 (never a whoosh)

# ---- HOOK 0-3 s: face mid-blow -> inside (x-ray, air into the sinus) -> the bone cracks ---------------------------
ep.shot(0.0, 'room_face', set='room', cast={mia: blow(at=0.0)}, cam=KW.cam.face(mia, push=0.12, side=14, dist=0.7, shake=0.4))
ep.shot(1.0, 'xray_front', set='xray', xray=mia, organs=['airway', 'sinus', 'skull', 'eyes'], cast={mia: xr(face='strain')},
        fx=[KW.fx.flow(mia, 'nose_to_sinus', at=0.0, color='green', count=60, speed=1.6), KW.fx.pressure(mia, 'sinus', at=0.1, dur=1.0, swell=0.6)],
        cam=KW.cam.xray(mia, 'sinus', view='34', push=0.55, orbit=30, dist=0.62))
ep.shot(2.2, 'macro_crack', set='macro', macro=bone, fx=[KW.fx.crack(at=0.15), KW.fx.leak(at=0.45, rate=0.8)],
        cam=KW.cam.macro(bone, view='wide', push=0.3, hits=[0.15]))
# ---- 2: context - at work, blowing as hard as she can --------------------------------------------------------------
ep.shot(3.0, 'room_medium', set='room', cast={mia: blow(at=0.1)}, cam=KW.cam.medium(mia, side=28, height=0.12, push=0.1, shake=0.5))
ep.shot(L(1) + 1.6, 'room_wide', set='room',
        cast={mia: blow(at=0.0, hard=1.0)},
        cam=KW.cam.wide(mia, side=38, push=0.06))
ep.shot(L(1) + 3.3, 'plunge_nose', set='room', cast={mia: blow(at=0.0)}, cam=KW.cam.plunge(mia, into='nose'))
# ---- 3: air shoots up into the sinus -------------------------------------------------------------------------------
ep.shot(L(2) + 0.1, 'xray_profile', set='xray', xray=mia, organs=['airway', 'sinus', 'skull', 'eyes'], cast={mia: xr(face='strain')},
        fx=[KW.fx.flow(mia, 'nose_to_sinus', at=0.1, color='green', count=60, speed=1.2)],
        cam=KW.cam.xray(mia, 'sinus', view='profile', push=0.12))
ep.shot(L(2) + 2.0, 'xray_sinus', set='xray', xray=mia, organs=['airway', 'sinus', 'skull', 'eyes'], cast={mia: xr(face='strain')},
        fx=[KW.fx.flow(mia, 'nose_to_sinus', at=0.0, color='green', count=60, stop=0.97, heat=0.6),
            KW.fx.pressure(mia, 'sinus', at=0.1, dur=1.4, swell=0.5), KW.fx.gauge(to=0.97, at=0.2, dur=1.3, pos=(0.74, 0.3))],
        cam=KW.cam.xray(mia, 'sinus', view='front', push=0.15, dist=0.5))
# ---- 4: the paper-thin wall snaps (re-hook) -------------------------------------------------------------------------
ep.shot(L(3) - 0.1, 'macro_strain', set='macro', macro=bone,
        fx=[KW.fx.crack(at=0.7), KW.fx.label('THIN WALL', at=0.1, pos=(0.5, 0.74), color='yellow')],
        cam=KW.cam.macro(bone, view='wide', hits=[0.7]))
ep.shot(L(3) + 1.6, 'xray_crack', set='xray', xray=mia, organs=['sinus', 'skull', 'eyes'], cast={mia: xr(face='pain')},
        fx=[KW.fx.crack_line(mia, 'eye_l', at=0.1), KW.fx.glow(mia, 'sinus', at=0.0, dur=0.8, color='red')],
        cam=KW.cam.xray(mia, 'eyes', view='front', dist=0.38, push=0.1))
# ---- 5: air under the eyelid, the eye puffs shut ----------------------------------------------------------------
ep.shot(L(4) - 0.1, 'macro_leak', set='macro', macro=bone, fx=[KW.fx.leak(at=0.0, rate=1.4)], cam=KW.cam.macro(bone, view='wide', push=0.25))
ep.shot(L(4) + 1.3, 'room_swollen', set='room',
        cast={mia: KW.pose('sit', at='desk', face='worry', swell={'eye_l': 0.25}, left=KW.hand.touch(mia, 'cheek_l', shape='press2')).then(0.3, swell={'eye_l': 1.0})},
        cam=KW.cam.face(mia, side=-20, push=0.15))
# ---- 6: hospital scan --------------------------------------------------------------------------------------------
ep.shot(L(5) - 0.1, 'hos_exam', set='hospital',
        cast={mia: KW.pose('sit', at='bed_sit', face='worry', swell={'eye_l': 1.0}, look=doc),
              doc: KW.pose('stand', at='bedside_l', left='clipboard', right=KW.hand.point(mia.part('eye_l')), face='focus', look=mia)},
        cam=KW.cam.two_shot(mia, doc, side=-10, push=0.08))
ep.shot(L(5) + 1.4, 'scan', set='graphic', world='hospital', fx=[KW.fx.scan('head', heal=False)], cam=KW.cam.prop(push=0.2))
ep.shot(L(5) + 3.0, 'hos_eye', set='hospital',
        cast={mia: KW.pose('sit', at='bed_sit', face='worry', swell={'eye_l': 1.0}),
              doc: KW.pose('stand', at='bedside_l', left='clipboard', right='write', face='focus', look=mia)},
        cam=KW.cam.face(mia, side=-25, push=0.15))
# ---- 7: healed in three weeks, loop back to the desk (last frame = frame 0) --------------------------------------
ep.shot(L(6) - 0.1, 'calendar', set='graphic', world='hospital', fx=[KW.fx.calendar(weeks=3, at=0.05, dur=0.6)], cam=KW.cam.prop())
ep.shot(L(6) + 1.1, 'xray_heal', set='xray', xray=mia, organs=['sinus', 'skull', 'eyes'], cast={mia: xr(face='calm')},
        fx=[KW.fx.swell_air(mia, 'eye_l', at=-2.0, dur=0.1, shrink_at=0.1)], cam=KW.cam.xray(mia, 'eyes', view='34', dist=0.42, orbit=-12))
ep.shot(L(6) + 2.2, 'room_loop', set='room',
        cast={mia: KW.pose('sit', at='desk', face='relief', left='tissue_nose', right='tissue_nose').then(0.2, face='strain', flush=0.7, act=KW.act.blow_nose(at=0.3, dur=1.0, hard=1.3))},
        cam=KW.cam.loop())

ep.run()
