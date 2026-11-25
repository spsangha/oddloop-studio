# Kinda Wild Films — kwkit API (appendix to kit/kw_card.md)

```python
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kwkit as KW
```

## 1 Episode
`ep = KW.Episode(name, voice_lines=[...], injury='words in line 1', music='sneaky_snitch', gap=0.32)`
- `gap`: pause between lines (0.3-0.45). Raise it (or add words) if check says duration < 26 s.
- `ep.line(i)` start second of sentence i (0-based); `ep.line_end(i)` its end; `ep.word(i, 'cracked')` start of one
  word — put cuts and impacts ON the words. `ep.duration`.
- `ep.sound(t, 'thud', 1.0)` extra sound at absolute time t. `ep.run()` — last line of the file.

## 2 People
`mia = ep.person('Mia', job, seed, gender='f'|'m', age='young'|'middle'|'old', race='caucasian'|'african'|'asian', hair=..., tee='red', tan=0.3, clipboard=True, mask=True, gloves=True)`
- jobs: doctor nurse surgeon police paramedic firefighter patient chef 'construction worker' business pilot scientist civilian
- seed: any string; same seed = same face. `mia.part('neck_l', (0, -0.05, 0.03))` = point on her (their-left, forward, up m).
- Scan heads (DEFAULT ON since 2026-11-23; env `KW_HEADS=legacy` restores the old heads; defaults live in heads_kw.DEFAULT and cast._scan): scan mode gives every person a light-stage scan face shape (ICT-FaceKit, picked by seed), scan skin detail,
  strand hair, brows and beard, scan iris; same API, expressions, x-ray and seeds. `KW_SCAN_HAIR=0` keeps card hair, `KW_SCAN_BROWS=0` card brows/beard;
  `KW_SCAN_LONGHAIR=1` strand long/bob hair (about +90% frame time); knobs `KW_HEADS_GAIN` (1.4) `KW_SCAN_SSS` (0; >0 costs ~+50%) `KW_SCAN_COL` `KW_SCAN_BUMP`. Credit Lee Perry-Smith (assets/LICENCES.md). Code: loop/kw/heads_kw.py.
- PARTS: nose mouth chin forehead head_top eye_l eye_r cheek_l cheek_r ear_l ear_r neck_l neck_r throat chest chest_l chest_r belly shoulder_l shoulder_r wrist_l wrist_r back knee_l knee_r

## 3 Shots
`ep.shot(t, 'unique_name', set=..., cast={person: pose}, cam=KW.cam.*, fx=[KW.fx.*], sounds=[(local_t, 'name', gain)], world=None, xray=person, organs=[...], macro=handle)`
- sets: car hospital room street studio xray macro graphic.  x-ray: `set='xray', xray=mia, organs=['sinus','eyes']` and
  put mia in cast. macro: `bone = ep.macro('bone')` then `set='macro', macro=bone`. graphic: a prop fx + `cam=KW.cam.prop()`.
- ORGANS: airway lungs esophagus stomach heart brain intestines sinus eyes skull vessels kidneys bladder liver
- MACRO kinds: windpipe esophagus artery vein intestine stomach bone nerve sinus
- SPOTS — car: driver passenger | hospital: bed_sit bed_lie bedside_l bedside_r behind front lie_side lie_far |
  room: desk stand stand_l stand_r counter coworker | street: walk stand stand_l stand_r bench ground | studio: centre centre_l centre_r centre_sit

## 4 Poses
`KW.pose(base, at='spot', left=hand, right=hand, face='pain', head=(nod,turn,tilt), look=person, lean=10, act=KW.act.*, flush=0.6, swell={'eye_l': 1.0})`
- base: stand sit drive lie walk.  `.then(local_t, face='worry', swell={...})` blends to a change inside the shot.
- faces: neutral calm strain puffed shock pain worry relief smile sleep talk disgust focus scream nausea sniff blow
  (mix: `'pain+worry'` or `{'pain': 0.6, 'worry': 0.4}`)
- swell keys: neck eye_l eye_r cheek_l cheek_r lips belly
- e.g. `KW.pose('drive', right='pinch_nose', left='wheel', face='strain', flush=0.5)`

## 5 Hands
- strings: rest lap wheel pinch_nose cover_mouth cover_nose tissue_nose wave point_fwd clipboard write hips to_mouth phone_ear, `touch_<PART>`, `clutch_<chest|belly|neck|head|throat|forehead|eye_l|...>`
- `KW.hand.touch(person, 'neck_l', shape='press2', pulses=[0.4, 0.9])` (doctor presses), `KW.hand.press(person, part)`,
  `KW.hand.clutch('chest')`, `KW.hand.point(mia.part('eye_l'))`, `KW.hand.hold('cup', where='mouth')`
- shapes: relaxed open fist pinch point press2 hold cup claw.  props: tissue cup apple pill phone pen spoon bottle can earbud swab pepper

## 6 Acts (body actions, `at` = local time of the key moment)
`sneeze(at, big, spray)` `cough(at, n, gap)` `blow_nose(at, dur, hard)` `swallow` `eat(bites)` `drink(dur)` `wince(hard)` `nod(n)` `shake_head(n)` `gasp` `breathe_hard(rate)` `look_around` `flinch` `yawn` `sniff` `scratch` — e.g. `act=KW.act.blow_nose(at=0.0, dur=1.6, hard=1.3)`

## 7 Cameras (options: push, orbit, side, height, shake, hits=[t], lens, dist, fstop, follow)
`face(p)` `medium(p)` `wide(p)` `two_shot(a, b)` `over_shoulder(a, b)` `profile(p, part)` `low_hero(p)` `top_down(p)` `part(p, 'eye_l')`
`plunge(p, into='nose')` (fly into the body; next shot x-ray/macro) `xray(p, organ, view='34'|'front'|'profile'|'back34')`
`macro(m, view='hole'|'wide'|'inside'|'object')` `prop()` `at(pos, look)` `bench('wide'|'close', at=(x, y), top=0.9, width=, h=, look=)` (table-top items) `loop()` (LAST shot only).
e.g. `cam=KW.cam.face(mia, push=0.12, side=14, shake=0.4)` — keep `push` 0.06-0.2 so every shot moves.

## 8 Effects (`at` = local seconds)
- x-ray: `flow(person, path, color, count, speed, stop)` paths: air_out_nose air_out_mouth air_in nose_to_sinus sinus_to_eye food_down blood_heart brain_blood;
  `pressure(person, organ, dur, swell)` `glow(person, organ, color)` `seal(person)` `swell_air(person, 'eye_l', shrink_at=)` `crack_line(person, 'eye_l')`
- macro: `tear(at)` `crack(at)` `leak(at, rate, kind='bubbles'|'blood'|'fluid')` `particles(kind)` `block(obj)` `heal(at, dur)`
- graphics: `label('20x', pos=(0.5,0.74), color='yellow')` (1-3 words) `gauge(to=0.97, low='NORMAL\nBLOW', high='')` (dial text: low = green label, high = red full-scale label, '' hides it; default prints NORMAL SNEEZE / 20x) `arrow(...)` `bracket(...)`
  `calendar(weeks=3)` `scan('head'|'neck'|'chest'|'belly', heal=False)` `skin_block(press_at=)` `crackle(near=anchor, times=[...])`
- table-top (kwprops, any set, best `set='studio', world='sky'`, no cast = own 3-light prop rig):
  `item(kind, pos, rz, tilt, keys=[(t, {control: v})], on=other_item, light=0.45, **params)` kinds: tray(style='meal'|'clinic', liner='paper'|'cloth', color) burger fries salmon wedges salad (eaten 0..1) cup(lid, straw) penlight(on) tweezers probe magnifier paperclip pea(sprout) ball(squash) bulb bench(style='grey'|'table', top=(w, d), h)
  `counter(v0, v1, unit, at, dur, pos, size, color, decimals, sign)` `beam(origin=(pen, 'tip'), target, at, fade, width, color, strength, sweep=(target2, t0, t1))` `flow_path(points, at, color, size, count, speed, spread)`
- e.g. `fx=[KW.fx.crack(at=0.15), KW.fx.leak(at=0.45, rate=0.8)]`

## 9 Sounds
bounce bubbles crackle engine heal inhale pinch pressure puff rip rush sneeze sniff thud (acts and fx add their own).
Frame-0 transient: thud / pinch / bounce / rip / crackle / sneeze.

## Round 4 picture switches

Enabled by default; set a variable to `0` to isolate or revert that class of changes. Set, camera, act, spot, effect and pose names are unchanged.

- `KW_CABIN_R4`: Layered cabin materials, padded panels, upholstery seams, sky gradient and a more directional car key/rim. Wheel and seat marks are unchanged.
- `KW_DRESSING_R4`: Dressed kitchen and clinic, with physical set backgrounds on medium/two/over-shoulder shots. Close views retain the Round 3 sky card where applicable. Existing `KW_BACKDROP=0` and `ROOM_WINDOW=1` still work.
- `KW_ACTING_R4`: Adds irregular breathing and blinks, lateral weight shifts, delayed shoulder and elbow recoil, non-contact finger flex, modest walking arm swing, and steering-wheel hand tracking. Hand contacts still use the authored IK solver; the slushie hold solves to its straw tip rather than the cup body.
- `KW_MOCAP_R4`: Opt out of all trimmed CMU torso tracks while retaining the rest of the acting pass. No root, fingers or full limbs come from the capture. See `assets/LICENCES.md`.
- `KW_CAMERA_R4`: Softens push/orbit timing, replaces jitter with gentler drift and damped impacts, and shortens a wide room dolly only when its camera would cross a set wall.
- `KW_XRAY_R4`: Clearer contour shell, differentiated tissue and skull response, sparse cerebral branches and a physical anatomy key.
- `KW_MACRO_R4`: Layered macro tissue and vessel finish, plus a slight diagonal framing bias on tube wides. Existing effect anchors and explicit f-stops are preserved.
- `KW_SCAN2_R4`: Near-black default X-ray environment (an explicit `world=` still wins), narrower cyan body edge, folded cortex, and contextual cervical/thorax bones. Requires `KW_XRAY_R4`; public organs, anchors and FX are unchanged.
- `KW_MACRO2_R4`: Tube-based macros gain additional tissue depths, branching capillaries and fine outer-wall fibres outside the animated cut. Default macro framing gets a grid-free dark tissue gradient; an explicit `world=` still wins. Requires `KW_MACRO_R4`.
- `KW_PEOPLE2_R4`: More off-axis, lower-fill people lighting and a restrained existing rim. No additional frontal catchlight and no material changes to heads.
- `KW_PATH2_R4`: Shorter diffuse/glossy paths and adaptive sampling for room and hospital shots. Keeps refractive caustics enabled for eyes.
- `KW_CONTACT2_R4`: Add bounded torso-only capture for seated/standing clutch and authored lean/examiner touch. `=0` retains the earlier drink/eat tracks and restores procedural clutch/lean. Existing contact IK remains in charge.

## Hook template values that pass the gate (from ep_blownose)
- shot 1 `KW.cam.face(p, push=0.12, side=14, dist=0.7, shake=0.4)`; shot 2 at 1.0 s `KW.cam.xray(p, organ, view='34', push=0.55, orbit=30, dist=0.62)`
  (a small push fails 9a: x-ray frames at 1 s and 2 s look the same); shot 3 at 2.2 s `KW.cam.macro(m, view='wide', push=0.3, hits=[0.15])`.

## Cast v1.1 (KW_CAST=v1.1, HG cast; default cast stays v1.0)
- new faces: `surprise fear disgust pain wince laugh` (also `shock`=surprise, `scream`=fear + 26 mm jaw, `nausea`=0.6 disgust + pressed lips).
  Strength works at 1.0 and 0.6: `face={'fear': 0.6}`. Laugh adds head back ~4° and 3 shoulder bounces; `KW.act.wince(at)` runs in 4 / hold 6 / out 8 frames, left eye stronger.
- named jaw openings (front-teeth gap): `speak` 8 mm, `spoon` 20 mm, `bite` 32 mm (+ lips apart); per-character table in heads_hg.JAW_TAB.
- `look='camera'` aims head and eyes at the lens.
- grips (the item follows the hand): `KW.hand.grip('grip_cup')`, `grip('grip_tool', 'tweezers'|'penlight')`, `grip('grip_pinch', 'pea'|'paperclip')`,
  `grip('grip_burger')` given to BOTH hands (hold at the chest; `grip('grip_burger', where='mouth')` on both hands + `face={'bite': 1}`, `look='held'` = the bite).
  Cup, tool and pinch are hand-authored finger tables (heads_hg.AUTH); the burger fingers are closed on the real bun by the finger solver
  `heads_hg.close_hand` (each finger curls its 3 joints together in 2 deg steps until the pad is 0-2 mm from the prop; human joint limits FINGER_ROM).
  `look='held'` = head dips toward the held item, eyes on it.  A hand resting on the belly: `KW.hand.clutch('belly')` on a SEATED pose (rest_belly was removed).
