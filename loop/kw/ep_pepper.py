"""Kinda Wild Films - 'He Ate The Hottest Pepper On Earth'.  Written only with kwkit.
Case: 34-year-old man ate one Carolina Reaper at a hot pepper contest -> dry heaves, neck/occipital pain becoming holocephalic,
brief thunderclap headaches over the next few days; CT angiography: multifocal narrowing of brain arteries (vasospasm, RCVS);
supportive care, no further headaches; repeat CTA 5 weeks later showed the narrowing resolved.
Sources (opened): https://pmc.ncbi.nlm.nih.gov/articles/PMC5893965/   https://www.bbc.com/news/health-43699484
Line sources: 1-4 BMJ 'symptoms began with dry heaves ... ate one Carolina Reaper ... intense neck and occipital head pain
that became holocephalic ... During the next few days ... brief intense thunderclap headaches lasting seconds';
5 'CT angiography ... multifocal luminal narrowing ... consistent with vasospasm'; 6 'symptoms improved with supportive care,
he had no further thunderclap headaches'; 7 'repeat CT angiography 5 weeks later demonstrated resolution of luminal narrowing'.
No scan() monitor: its 'head' art shows a skull crack, which this case did not have.
"""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kwkit as KW

ep = KW.Episode('ep_pepper', injury="squeezed the arteries", voice_lines=[
    "The world's hottest pepper squeezed the arteries in his brain.",
    "He ate a whole Carolina Reaper at a chili contest and started dry heaving.",
    "Then intense pain spread from his neck through his entire head.",
    "Over the next few days, sudden thunderclap headaches hit him for seconds at a time.",
    "A hospital scan showed several arteries in his brain had narrowed in tight spasms.",
    "He got supportive care, and the headaches stopped.",
    "Five weeks later, a second scan showed every artery had opened back up.",
], music='sneaky_snitch', gap=0.4)

# ---- cast ---------------------------------------------------------------------------------------------------
leo = ep.person('Leo', 'civilian', 'pepper-leo', gender='m', age='young', race='asian', hair='short02', tee='red')
doc = ep.person('Dr Grant', 'doctor', 'pepper-doc', gender='f', age='middle', race='caucasian', hair='long01', clipboard=True)
art = ep.macro('artery')

L = ep.line; E = ep.line_end
bite = lambda at=0.0, **k: KW.pose('stand', at='counter', right=KW.hand.hold('pepper', where='mouth'), face='pain', act=KW.act.eat(at=at, bites=1), flush=0.8, **k)
xr = lambda **k: KW.pose('stand', at='room.counter', **k)
ep.sound(0.0, 'thud', 1.0)                    # hook: a real transient on frame 0 (never a whoosh)

# ---- HOOK 0-3 s: mid-bite -> inside the head (x-ray, blood to the brain bunches up) -> the artery squeezes ---------------
ep.shot(0.0, 'room_bite', set='room', cast={leo: bite(at=0.3)}, cam=KW.cam.face(leo, push=0.2, side=14, dist=0.7, shake=0.5, orbit=10))
ep.shot(1.0, 'xray_brain', set='xray', xray=leo, organs=['brain', 'vessels', 'skull'], cast={leo: xr(face='pain')},
        fx=[KW.fx.flow(leo, 'brain_blood', at=0.0, color='red', count=70, speed=1.4, stop=0.6), KW.fx.glow(leo, 'vessels', at=0.2, dur=0.8, color='red')],
        cam=KW.cam.xray(leo, 'brain', view='34', push=0.55, orbit=30, dist=0.62))
ep.shot(2.2, 'macro_squeeze', set='macro', macro=art, fx=[KW.fx.particles('blood', at=0.0, speed=0.4, count=20), KW.fx.label('SPASM', at=0.15, pos=(0.5, 0.62), color='yellow')],
        cam=KW.cam.macro(art, view='wide', push=0.3, hits=[0.15]))
# ---- 2: the contest, dry heaving ---------------------------------------------------------------------------------
ep.shot(L(1) + 0.1, 'room_medium', set='room', cast={leo: bite(at=0.1)}, cam=KW.cam.medium(leo, side=28, height=0.12, push=0.1, shake=0.5))
ep.shot(L(1) + 1.8, 'room_heave', set='room',
        cast={leo: KW.pose('stand', at='counter', left=KW.hand.clutch('belly'), right='cover_mouth', face='nausea', lean=18, act=KW.act.cough(at=0.1, n=3, gap=0.4))},
        cam=KW.cam.wide(leo, side=38, push=0.08, shake=0.4))
ep.shot(L(1) + 3.0, 'room_heave_face', set='room',
        cast={leo: KW.pose('stand', at='counter', left=KW.hand.clutch('belly'), right='cover_mouth', face='nausea', lean=18, act=KW.act.cough(at=0.0, n=2, gap=0.35))},
        cam=KW.cam.face(leo, side=-16, push=0.15, shake=0.5))
# ---- 3: pain spreads from the neck through the head --------------------------------------------------------------
ep.shot(L(2) - 0.1, 'room_neck', set='room', cast={leo: KW.pose('stand', at='counter', left=KW.hand.clutch('neck_l'), right=KW.hand.clutch('head_top'), face='pain', act=KW.act.wince(at=0.3, hard=1.2))},
        cam=KW.cam.face(leo, side=-20, push=0.15, shake=0.5))
ep.shot(L(2) + 1.6, 'xray_spread', set='xray', xray=leo, organs=['brain', 'vessels', 'skull'], cast={leo: xr(face='pain')},
        fx=[KW.fx.glow(leo, 'brain', at=0.0, dur=1.2, color='red')],
        cam=KW.cam.xray(leo, 'brain', view='back34', push=0.15))
# ---- 4: thunderclap headaches over the next few days (re-hook) -----------------------------------------------------
ep.shot(L(3) - 0.1, 'room_clap1', set='room', cast={leo: KW.pose('sit', at='desk', left=KW.hand.clutch('forehead'), right=KW.hand.clutch('head_top'), face='scream', act=KW.act.flinch(at=0.4))},
        cam=KW.cam.face(leo, side=18, push=0.18, shake=0.8, hits=[0.4]), sounds=[(0.4, 'thud', 1.0)])
ep.shot(L(3) + 1.9, 'xray_clap', set='xray', xray=leo, organs=['brain', 'vessels', 'skull'], cast={leo: xr(face='pain')},
        fx=[KW.fx.pressure(leo, 'vessels', at=0.0, dur=1.6, swell=0.3), KW.fx.label('THUNDERCLAP', at=0.2, pos=(0.5, 0.78), color='red')],
        cam=KW.cam.xray(leo, 'vessels', view='front', push=0.15, dist=0.5, hits=[0.2]))
ep.shot(L(3) + 3.4, 'room_clap2', set='room', cast={leo: KW.pose('sit', at='desk', left=KW.hand.clutch('forehead'), right=KW.hand.clutch('head_top'), face='pain', act=KW.act.flinch(at=0.15))},
        cam=KW.cam.medium(leo, side=-24, push=0.12, shake=0.7, hits=[0.15]), sounds=[(0.15, 'thud', 0.9)])
# ---- 5: hospital, the scan shows narrowed arteries ----------------------------------------------------------------
ep.shot(L(4) - 0.1, 'hos_exam', set='hospital',
        cast={leo: KW.pose('sit', at='bed_sit', face='worry', look=doc),
              doc: KW.pose('stand', at='bedside_l', left='clipboard', right=KW.hand.point(leo.part('head_top')), face='focus', look=leo)},
        cam=KW.cam.two_shot(leo, doc, side=-10, push=0.08))
ep.shot(L(4) + 1.5, 'macro_narrow', set='macro', macro=art, fx=[KW.fx.particles('blood', at=0.0, speed=0.3, count=20), KW.fx.label('NARROWED', at=0.1, pos=(0.5, 0.62), color='yellow')],
        cam=KW.cam.macro(art, view='wide', push=0.25))
ep.shot(L(4) + 3.3, 'xray_narrow', set='xray', xray=leo, organs=['brain', 'vessels', 'skull'], cast={leo: xr(face='worry')},
        fx=[KW.fx.flow(leo, 'brain_blood', at=0.0, color='red', count=70, speed=0.8, stop=0.55)], cam=KW.cam.xray(leo, 'vessels', view='profile', push=0.15))
# ---- 6: supportive care, headaches stop ---------------------------------------------------------------------------
ep.shot(L(5) - 0.1, 'hos_care', set='hospital',
        cast={leo: KW.pose('sit', at='bed_sit', face='calm', look=doc),
              doc: KW.pose('stand', at='bedside_l', left='clipboard', right='write', face='focus', look=leo)},
        cam=KW.cam.two_shot(leo, doc, side=14, push=0.08))
ep.shot(L(5) + 1.3, 'hos_relief', set='hospital', cast={leo: KW.pose('sit', at='bed_sit', face='relief')}, cam=KW.cam.face(leo, side=-25, push=0.15))
# ---- 7: five weeks later the arteries are open again, loop back to the bite ---------------------------------------
ep.shot(L(6) - 0.1, 'calendar', set='graphic', world='hospital', fx=[KW.fx.calendar(weeks=5, at=0.05, dur=0.6)], cam=KW.cam.prop())
ep.shot(L(6) + 1.1, 'xray_open', set='xray', xray=leo, organs=['brain', 'vessels', 'skull'], cast={leo: xr(face='calm')},
        fx=[KW.fx.flow(leo, 'brain_blood', at=0.0, color='red', count=70, speed=1.2)], cam=KW.cam.xray(leo, 'vessels', view='34', dist=0.5, orbit=-12))
ep.shot(L(6) + 2.4, 'room_loop', set='room',
        cast={leo: KW.pose('stand', at='counter', right=KW.hand.hold('pepper', where='mouth'), face='calm').then(0.3, face='pain', flush=0.8, act=KW.act.eat(at=0.3, bites=1))},
        cam=KW.cam.loop())

ep.run()
