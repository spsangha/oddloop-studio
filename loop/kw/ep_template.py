"""Kinda Wild Films - EPISODE TEMPLATE.  Copy to ep_<slug>.py, fill every <<...>>, delete nothing structural.
Case: <<one line: who, what happened, outcome>>.  Sources (2, opened):  <<url 1>>  <<url 2>>
Rules (ep.check enforces them; python3 kwkit.py --check ep_<slug>.py):
  * 3-6 sentences (7 max), 68-92 words (Zack: 69-92 words, 3-6 sentences), third person past tense, no filler opening ("Imagine", "Did you know", "This is").
  * Sentence 1 = one run-on of 18-24 words with a comma (8-13 still passes), shots timed with ep.word(0, 'word'), and NAMES THE INJURY within 12 words; `injury=` is that exact phrase from sentence 1.
  * Shots: first shot <= 1.0 s, an inside-body shot (set='xray' or 'macro') at 1.0 s, a third shot by 2.2-2.4 s,
    no shot longer than 2.2 s, the last shot uses KW.cam.loop() so the Short loops back to frame 0.
  * A physical sound on frame 0 (thud, pinch, puff, pop ...). NEVER a whoosh / swoosh / riser (owner ban).
  * Names for sets, poses, faces, hands, organs, fx, sounds: see kit/kw_card.md (API). Unknown names raise an error.
Worked example: ep_blownose.py (same structure).  Run order: kwvo.py -> kwkit.py --check -> test frames -> kwhook.py gate.
"""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kwkit as KW

ep = KW.Episode('ep_<<slug>>', injury="<<injury phrase from sentence 1>>", voice_lines=[
    "<<1. Hook: action + injury, 8-13 words, e.g. 'Blowing her nose too hard cracked the bone beside her eye.'>>",
    "<<2. Where / what she was doing (the showable action).>>",
    "<<3. Mechanism step 1 (inside the body).>>",
    "<<4. Mechanism step 2 - the break / tear (re-hook).>>",
    "<<5. What it did to the body (the visible symptom).>>",
    "<<6. Hospital: how doctors found it.>>",
    "<<7. Outcome: how it healed / how long.>>",
], music='sneaky_snitch', gap=0.4)

# ---- cast (costumes: see card; keep the same seed string so the face never changes between episodes) ------------------
hero = ep.person('<<Name>>', '<<business|casual|sport|...>>', '<<slug>>-hero', gender='f', age='young', race='caucasian', hair='long01')
doc = ep.person('Dr <<Name>>', 'doctor', '<<slug>>-doc', gender='m', age='middle', race='african', clipboard=True)
tube = ep.macro('<<windpipe|esophagus|artery|vein|intestine|stomach|bone|nerve|sinus>>')

L = ep.line; E = ep.line_end          # L(n) = start time of sentence n (0-based), E(n) = its end
act = lambda at=0.0, **k: KW.pose('sit', at='desk', face='strain', **k)     # <<the hook performance; reuse it in the loop shot>>
xr = lambda **k: KW.pose('sit', at='room.desk', **k)
ep.sound(0.0, '<<thud|pinch|puff|pop>>', 1.0)                                 # hook: physical transient on frame 0

# ---- HOOK 0-3 s: person mid-action -> inside the body at 1.0 s -> the injury happens by 2.2 s ------------------------
ep.shot(0.0, 'hook_face', set='<<room|car|hospital|...>>', cast={hero: act(at=0.0)}, cam=KW.cam.face(hero, push=0.12, side=14, dist=0.7, shake=0.4))
ep.shot(1.0, 'hook_xray', set='xray', xray=hero, organs=['<<organ>>', 'skull'], cast={hero: xr(face='strain')},
        fx=[KW.fx.pressure(hero, '<<organ>>', at=0.1, dur=1.0, swell=0.6)],
        cam=KW.cam.xray(hero, '<<organ>>', view='34', push=0.55, orbit=30, dist=0.62))   # big push/orbit: the gate wants visible change 1->2 s
ep.shot(2.2, 'hook_macro', set='macro', macro=tube, fx=[KW.fx.crack(at=0.15)],      # or KW.fx.tear(at=...) for soft tissue
        cam=KW.cam.macro(tube, view='wide', push=0.3, hits=[0.15]))
# ---- sentence 2: context (where / what) -----------------------------------------------------------------------------
ep.shot(3.0, 'ctx_medium', set='<<room>>', cast={hero: act(at=0.1)}, cam=KW.cam.medium(hero, side=28, height=0.12, push=0.1, shake=0.5))
ep.shot(L(1) + 1.6, 'ctx_wide', set='<<room>>', cast={hero: act(at=0.0)}, cam=KW.cam.wide(hero, side=38, push=0.06))
ep.shot(L(1) + 3.3, 'plunge', set='<<room>>', cast={hero: act()}, cam=KW.cam.plunge(hero, into='<<nose|mouth|ear_l|eye_l|neck_l|chest|belly>>'))
# ---- sentence 3-4: mechanism + the break (re-hook) ------------------------------------------------------------------
ep.shot(L(2) + 0.1, 'mech_xray', set='xray', xray=hero, organs=['<<organ>>', 'skull'], cast={hero: xr(face='strain')},
        fx=[KW.fx.pressure(hero, '<<organ>>', at=0.1, dur=1.4, swell=0.5)], cam=KW.cam.xray(hero, '<<organ>>', view='profile', push=0.12))
ep.shot(L(2) + 2.0, 'mech_gauge', set='xray', xray=hero, organs=['<<organ>>'], cast={hero: xr(face='strain')},
        fx=[KW.fx.gauge(to=0.97, at=0.2, dur=1.3, pos=(0.74, 0.3))], cam=KW.cam.xray(hero, '<<organ>>', view='front', push=0.15, dist=0.5))
ep.shot(L(3) - 0.1, 'break_macro', set='macro', macro=tube, fx=[KW.fx.crack(at=0.7), KW.fx.label('<<2-WORD LABEL>>', at=0.1, pos=(0.5, 0.74), color='yellow')],
        cam=KW.cam.macro(tube, view='wide', hits=[0.7]))
ep.shot(L(3) + 1.6, 'break_xray', set='xray', xray=hero, organs=['<<organ>>', 'skull'], cast={hero: xr(face='pain')},
        fx=[KW.fx.glow(hero, '<<organ>>', at=0.0, dur=0.8, color='red')], cam=KW.cam.xray(hero, '<<organ>>', view='front', dist=0.38, push=0.1))
# ---- sentence 5: the symptom ----------------------------------------------------------------------------------------
ep.shot(L(4) - 0.1, 'symptom_macro', set='macro', macro=tube, fx=[KW.fx.leak(at=0.0, rate=1.4)], cam=KW.cam.macro(tube, view='object', push=0.1))
ep.shot(L(4) + 1.3, 'symptom_face', set='<<room>>', cast={hero: KW.pose('sit', at='desk', face='worry')}, cam=KW.cam.face(hero, side=-20, push=0.15))
# ---- sentence 6: hospital -------------------------------------------------------------------------------------------
ep.shot(L(5) - 0.1, 'hos_exam', set='hospital',
        cast={hero: KW.pose('sit', at='bed_sit', face='worry', look=doc),
              doc: KW.pose('stand', at='bedside_l', left='clipboard', right='write', face='focus', look=hero)},
        cam=KW.cam.two_shot(hero, doc, side=-10, push=0.08))
ep.shot(L(5) + 1.4, 'scan', set='graphic', world='hospital', fx=[KW.fx.scan('<<head|neck|chest|belly>>', heal=False)], cam=KW.cam.prop(push=0.2))
ep.shot(L(5) + 3.0, 'hos_part', set='hospital', cast={hero: KW.pose('sit', at='bed_sit', face='worry')},
        cam=KW.cam.part(hero, '<<eye_l|neck_l|belly|wrist_r ...>>', dist=0.34, side=-10, push=0.12))
# ---- sentence 7: outcome + LOOP (last shot ends exactly on frame 0) -------------------------------------------------
ep.shot(L(6) - 0.1, 'calendar', set='graphic', world='hospital', fx=[KW.fx.calendar(weeks=<<N>>, at=0.1, dur=0.9)], cam=KW.cam.prop())
ep.shot(L(6) + 1.1, 'heal_xray', set='xray', xray=hero, organs=['<<organ>>', 'skull'], cast={hero: xr(face='calm')},
        cam=KW.cam.xray(hero, '<<organ>>', view='34', dist=0.42, orbit=-12))
ep.shot(L(6) + 2.2, 'loop', set='<<room>>', cast={hero: KW.pose('sit', at='desk', face='relief').then(0.2, face='strain')}, cam=KW.cam.loop())

ep.run()
