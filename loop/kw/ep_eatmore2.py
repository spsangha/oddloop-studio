"""Kinda Wild Films ep08 - 'They Ate 500 More Calories A Day'.  Brief: kindawild/08_eatmore_v2/brief.md (+ lead answers 25 Nov).
ONE unbroken shot: Ben bites a burger, lowers it to tray A, tray B slides in, bites vanish, bars, +500 A DAY, +2 / -2 LB, back to the bite.
Voice line starts (s): L0 0.00, L1 5.04, L2 10.53, L3 15.71, L4 21.53, L5 26.15; speech ends 29.98, film 30.13 s (723 frames, fN = 722).
All times below are frames (/ F -> seconds).  The burger path is ep.burger_track (heads_hg: grip where='track').
"""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kwkit as KW
os.environ.setdefault('KW_LIGHT', '1')
HERE = os.path.dirname(os.path.abspath(__file__))
ep = KW.Episode('ep_eatmore2', injury="ate meals like this",
                voice_lines=[l.strip() for l in open(os.path.join(HERE, 'ep_eatmore2.txt')) if l.strip()],
                music='sneaky_snitch', gap=0.9)
ep.waive = {"1 shots;": "brief s6: ONE unbroken shot (lead ruling: no cuts)",
            "last shot must use cam=KW.cam.loop()": "brief s6: the camera path itself returns to the frame-0 view at fN (the loop)",
            "HOOK foley transient": "lead ruling 2: the f5 bite is silent",
            "HOOK cut <= 200 ms after the last word": "lead CHECK 1 ruling fix 4: the return starts later so both LB labels are gone before his head enters; the tail is music",
            "shot bite holds": "brief s6: ONE unbroken shot; a visible change every <= 2.2 s comes from the food, labels and camera",
            "HOOK 8-11 words": "brief s3: script.txt is final (changing words is a STOP rule)",
            "HOOK inside the body": "brief s0: real-scene food experiment, no xray/macro shot"}
ben = ep.person('Ben', 'civilian', 'eatmore-ben', gender='m', age='young', race='caucasian', hair='short02', tee='teal')

W = ep.word; L = ep.line
FPS = 24; F = 1.0 / FPS
RET = int(os.environ.get('KW_RET', 13))                   # CHECK 2 fix 4: the return starts RET frames later (fN moves with it); voice unchanged
ep.duration = round(ep.duration + RET / FPS, 4)
NF = int(round(ep.duration * FPS)); FN = NF - 1          # last frame = frame 0 again
fw = lambda i, w: int(round(W(i, w) * FPS))               # word -> frame
f_four, f_two1, f_meals, f_two2 = fw(0, 'four'), fw(1, 2), fw(1, 'meals'), fw(1, 8)
f_same, f_much, f_wanted, f_ate, f_five = fw(2, 'same'), fw(2, 'much'), fw(2, 'wanted'), fw(3, 'ate'), fw(3, 'five')
f_gained, f_lost, f_avg5 = fw(4, 'gained'), fw(5, 'lost'), fw(5, 'average')
f_L3, f_L4, f_L5 = int(round(L(3) * FPS)), int(round(L(4) * FPS)), int(round(L(5) * FPS))
f_L3end = int(round((L(3) + ep.vo_dur[3]) * FPS))

# ---- layout (world m; Ben at the studio centre_sit (60, 0), facing -Y; +X = his left = the viewer's right) -----------------
TZ = 0.75                                  # table top
YE = -0.20                                 # table edge in front of him
TA = (60.0, -0.555)                        # tray A centre (short side toward the camera: rz 90 -> 35 cm across, 45 deep)
TB = (60.38, -0.555)                       # tray B centre, 3 cm gap (both bars fit the two-tray view)
TRAY_FLOOR = TZ + 0.003
PLACE = (59.92, -0.47, TRAY_FLOOR, float(os.environ.get('KW_PRZ', 140.0)))  # burger: left quarter of tray A, bite toward the camera's right (natural yaw of the bite)
REST = {'R': (59.875, -0.245, TZ + 0.011), 'L': (60.125, -0.245, TZ + 0.011)}   # palms down in front of tray A

# ---- burger (brief s5 + ruling 6: 4.2 cm cutters, centre 5.1 cm out = 2.5 cm deep, overlapping ~1 cm side by side) -----------
ep.grip_kw = {'burger': dict(bites=[(0.0, 0.93), (36.6, 0.93), (73.2, 0.93)], bite_r=0.021, bite_side=270.0, cheese_at=45.0,
                             droop2=True, sym=True, proud=0.005, nseeds=18,
                             lettuce=((0.10, 0.42, 0.03), (0.26, 0.58, 0.07)))}

# ---- the race (ruling 7): span ate->five < 40 frames -> both start at W(3,'ate'); A every 4 frames, B 3 even pieces -----------
A0 = f_five - 36                           # 10 pieces of tray A, 4 frames apart, the last on W(3,'five')
A_T = [A0 + 4 * k for k in range(10)]
B_T = [A0, (A0 + f_five) // 2, f_five]
A_KIND = ['fry', 'fry', 'bite', 'fry', 'fry', 'fry', 'bite', 'fry', 'fry', 'fry']

def steps(times, v0, dur=3):
    """keys for a counter that steps +1 at each frame in `times` (eased over `dur` frames)"""
    ks = [(0.0, v0)]; v = v0
    for t in times: ks += [(t * F, v), ((t + dur) * F, v + 1)]; v += 1
    return ks

fry_t = [f_much] + [t for t, k in zip(A_T, A_KIND) if k == 'fry']
bite_t = [t for t, k in zip(A_T, A_KIND) if k == 'bite']
# ---- burger track (frames) ------------------------------------------------------------------------------------------------
SPIN0, SPIN1, SWAP = FN - 38, FN - 26, int(os.environ.get('KW_SWAP', FN - 49))   # KW_SWAP: dev override for the arc-hidden test
TK = [(0, dict(w=0.0, pull=0.0, down=0.0, lvl=0.0, spin=0.0, g=1.0, gt=1.0, lift=0.0, r=0.0, tap=0.0, dxL=0.0, dxR=0.0, gone=0.0, rr=0.0, ox=0.0, rf=0.0)),
      (1, dict(gone=0.0)), (6, dict(gone=1.0)),                                      # bite 1: the cutter grows inside the mouth
      (5, dict(pull=0.0, down=0.0)), (12, dict(pull=0.05, down=0.02, lvl=0.7, w=0.0)),  # pull away 5 cm, down 2 cm
      (22, dict(lvl=1.0)), (44, dict(w=1.0)),                                         # lowered onto tray A
      (106, dict(tap=0.0)), (109, dict(tap=1.0)), (113, dict(tap=0.0)),              # right index taps once
      (f_two2, dict(dxL=0.0)), (f_two2 + 8, dict(dxL=-0.02)), (f_two2 + 20, dict(dxL=-0.012)),   # the hand by tray B shifts away
      (bite_t[0], dict(gone=1.0)), (bite_t[0] + 3, dict(gone=2.0)), (bite_t[1], dict(gone=2.0)), (bite_t[1] + 3, dict(gone=3.0)),
      (FN - 38, dict(w=1.0, spin=0.0, pull=0.05, down=0.02, lvl=1.0)),
      (SPIN1, dict(spin=180.0)), (FN - 14, dict(w=0.0, lvl=0.0)), (FN - 2, dict(pull=0.0, down=0.0))]
# hands (CHECK 2 fix 1), own channels: release = thumbs out f48-52, fingers soft f50-56, palm turns down to a hover just over
# the bun top 3 cm out on its own side f50-58, lift 2 cm f56-60, low own-side path to rest f58-76 (palm lands), fingers settle
# by f79; pick-up = the same mirrored (fingers soft, low path to the hover, palm turns in, thumbs under first, fingers close)
CHAN = dict(g=[(0, 1.0), (50, 1.0), (56, 0.0), (FN - 44, 0.0), (FN - 38, 1.0)],
            gt=[(0, 1.0), (48, 1.0), (52, 0.0), (FN - 46, 0.0), (FN - 43, 1.0)],
            rr=[(0, 0.0), (50, 0.0), (58, 1.0), (FN - 51, 1.0), (FN - 46, 0.0)],
            ox=[(0, 0.0), (50, 0.0), (56, 0.03), (FN - 50, 0.03), (FN - 46, 0.0)],
            lift=[(0, 0.0), (56, 0.0), (60, 1.0), (70, 1.0), (76, 0.0), (FN - 58, 0.0), (FN - 55, 1.0), (FN - 52, 1.0), (FN - 48, 0.0)],
            r=[(0, 0.0), (58, 0.0), (76, 1.0), (FN - 58, 1.0), (FN - 50, 0.0)],
            rf=[(0, 0.0), (76, 0.0), (79, 1.0), (FN - 58, 1.0), (FN - 55, 0.0)])
ep.burger_track = dict(keys=TK, place=PLACE, rest=REST, swap=SWAP, chan=CHAN)
TRK = KW.hand.grip('grip_burger', where='track')

# ---- Ben: one seated pose with keys (head / lean / face); chew act f12 -> before the hands move ----------------------------------
CHEW = KW.act.chew(at=12 * F, until=(FN - 70) * F, rate=1.5, gap=7.0, swallow=100 * F)
P0 = KW.pose('sit', at='centre_sit', left=TRK, right=TRK, face={'bite': 1.0}, head=(12, 0, 0), look='held', act=CHEW, lean=0.0, blend=5 * F)
P = (P0.then(0, blend=5 * F, face={'bite': 0.55}, head=(15, 0, 0), acts=[])
       .then(5 * F, blend=4 * F, face={'smile': 0.2}, head=(13, 0, 0), acts=[])
       .then(12 * F, blend=32 * F, head=(30, 0, 0), lean=12.0, acts=[])
       .then((FN - 46) * F, blend=32 * F, head=(12, 0, 0), lean=0.0, acts=[])
       .then((FN - 14) * F, blend=12 * F, face={'bite': 1.0}, acts=[]))
ep.blinks = {'Ben': [20, FN - 40]}

# ---- props ----------------------------------------------------------------------------------------------------------------
I = KW.fx.item
tbl = I('bench', (60.2, YE - 0.8, 0.0), style='table', top=(1.6, 1.6), h=TZ, soft=True, wood=(0.27, 0.155, 0.075))
ta = I('tray', (TA[0], TA[1], TZ), rz=90, style='meal', color=(0.34, 0.34, 0.34), ao=True)
tb = I('tray', (TB[0], TB[1], TZ), rz=90, style='meal', color=(0.20, 0.30, 0.42), ao=True,
       keys=[(0.0, {'dx': 0.9}), (f_two2 * F, {'dx': 0.9}), ((f_two2 + 14) * F, {'dx': -0.003}), ((f_two2 + 18) * F, {'dx': 0.0})])
fries = I('fries', (TA[0] + 0.085 - TA[0], -0.66 - TA[1], 0.0), rz=-10, on=ta, count=15,
          keys=[(t_, {'gone': v_}) for t_, v_ in steps(fry_t, 0)])
props = [tbl, ta, tb, fries,
         I('ketchup', (0.09, 0.09, 0.0), on=ta),
         I('cup', (-0.085, -0.12, 0.0), on=ta),
         I('salmon', (-0.085, 0.05, 0.0), rz=90, on=tb, size=(0.16, 0.07, 0.025), brown=True, lemon=True,
           keys=[(t_, {'gone': v_}) for t_, v_ in steps([f_wanted, B_T[2]], 0)]),
         I('sweet_potato', (0.072, 0.06, 0.0), rz=-20, on=tb, keys=[(t_, {'gone': v_}) for t_, v_ in steps([B_T[1]], 0)]),
         I('beans', (-0.02, -0.14, 0.0), rz=8, on=tb, keys=[(t_, {'gone': v_}) for t_, v_ in steps([B_T[0]], 0)]),
         I('fork', (0.145, -0.10, 0.0), rz=92, on=tb)]
# bars (beat 13-16, 19): beside each tray's outer long edge; 1/16 notches over 4 frames; bracket on W(3,'five'); fade at L4
XA, XB = TA[0] - 0.175 - 0.026, TB[0] + 0.175 + 0.026
bar_vis = [(0.0, {'alpha': 0.0}), ((f_much - 3) * F, {'alpha': 0.0}), (f_much * F, {'alpha': 1.0}), (f_L4 * F, {'alpha': 1.0}), ((f_L4 + 8) * F, {'alpha': 0.0})]
barA = I('bar', (XA, TA[1], TZ), bracket=(XB - XA, 12, 10),
         keys=bar_vis + [(t_, {'fill': v_}) for t_, v_ in steps([f_much] + A_T, 1, dur=4)] + [(f_five * F, {'br': 0.0}), ((f_five + 6) * F, {'br': 1.0})])
barB = I('bar', (XB, TB[1], TZ), keys=bar_vis + [(t_, {'fill': v_}) for t_, v_ in steps([f_wanted] + B_T, 6, dur=4)])
props += [barA, barB]

# ---- labels (FIX_H: screen-fixed, yellow, upper third) + sounds ------------------------------------------------------------
YL = dict(color='yellow', size=1.2); Y = 0.84
off2 = f_same - 6
labels = [KW.fx.label('4 WEEKS', at=f_four * F, pos=(0.5, Y), dur=1.07, **YL),
          KW.fx.label('2 WEEKS', at=f_two1 * F, pos=(0.5, Y), dur=(off2 - f_two1) * F,
                      keys=[(f_meals * F, {'pos': (0.5, Y), 'width': 960}), ((f_two2 + 14) * F, {'pos': (0.27, Y), 'width': 440})], **YL),
          KW.fx.label('2 WEEKS', at=(f_two2 + 15) * F, pos=(0.73, Y), dur=(off2 - f_two2 - 15) * F, keys=[(0.0, {'width': 440})], **YL),
          KW.fx.label('SAME CALORIES', at=f_same * F, pos=(0.5, Y), dur=20 * F, **YL),          # CHECK 2 fix 2 (was '=')
          KW.fx.label('+500 A DAY', at=f_five * F, pos=(0.5, Y), dur=(f_L3end + 6 - f_five) * F, **YL),
          KW.fx.label('+2 LB', at=f_gained * F, pos=(0.27, Y), dur=(f_avg5 - 4 - f_gained) * F, keys=[(0.0, {'width': 440})], **YL),
          KW.fx.label('\u22122 LB', at=f_lost * F, pos=(0.73, Y), dur=(f_avg5 - 4 - f_lost) * F, keys=[(0.0, {'width': 440})], **YL)]
for f_, g_ in ((f_four, 0.5), (f_two1, 0.5), (f_two2 + 15, 0.5), (f_same, 0.5), (f_five, 0.6), (f_gained, 0.5), (f_lost, 0.5)):
    ep.sound(f_ * F, 'thud', g_)
ep.sound(44 * F, 'thud', 0.28); ep.sound((f_two2 + 14) * F, 'thud', 0.26)          # ruling 2: the two taps, under the label thuds
ep.sound(f_much * F, 'tick', 0.4); ep.sound(f_wanted * F, 'tick', 0.3)
for t_ in A_T: ep.sound(t_ * F, 'tick', 0.35)
for t_ in B_T: ep.sound(t_ * F + 0.02, 'tick', 0.3)

# ---- camera: one path (frame-0 face view -> TRAY VIEW -> two trays -> push -> lean A -> lean B -> back to frame 0) ----------------
# frame-0 view = the approved bite still (cast/v11/burger_bite.jpg: KW.cam.face(side=38, lens 85, dist 1.4, aim (0,-0.05,-0.04)) on the
# standing harness): the same camera-to-lips offset, re-measured on the seated rig (the face preset takes a standing eye height)
LIP0 = (59.997, -0.159, 1.292)                        # V11DBG lip world at f0 (seated, lean 0)
C_T = (LIP0[0] + 0.0026, LIP0[1] + 0.028, LIP0[2] + 0.009); C0 = ((C_T[0] + 0.8598, C_T[1] - 1.1058, C_T[2] + 0.041), C_T, 85.0)
def view(cx, cy, d, el=50.0, lens=50.0, push=0.0):
    import math
    d = d * (1 - push); e = math.radians(el)
    return ((cx, cy - math.cos(e) * d, TZ + math.sin(e) * d), (cx, cy, TZ), lens)
V1 = view(TA[0], TA[1], 1.26)                       # TRAY VIEW: tray A at ~80 % of the width
V2 = view((TA[0] + TB[0]) / 2, TA[1], 2.30)         # both trays
V3 = view((TA[0] + TB[0]) / 2, TA[1], 2.30, push=0.03)
VA = view(TA[0] + 0.07, TA[1], 2.30, push=0.07)
VB = view(TB[0] - 0.07, TA[1], 2.30, push=0.07)
CAM = KW.cam.path([(0.0, *C0), (6 * F, *C0), (78 * F, *V1), (f_meals * F, *V1), ((f_two2 + 14) * F, *V2), (f_L3 * F, *V2), (f_L4 * F, *V3),
                   ((f_L4 + 30) * F, *VA), (f_L5 * F, *VA), ((f_L5 + 36) * F, *VB), ((FN - 40) * F, *VB), ((FN - 12) * F, *C0), (FN * F + 1.0, *C0)], fstop=5.6)

ep.label_lens_fix = True; ep.relight_after_pose = True   # kwrun: key/rim/fill placed again after posing (opt-in; old episodes render as before)
ep.exposure_keys = [(6 * F, 0.0), (78 * F, -0.7), ((FN - 40) * F, -0.7), ((FN - 12) * F, 0.0)]   # tray views sit 1 m under the head key light
ep.shot(0.0, 'bite', set='studio', world='sky', cast={ben: P}, fx=props + labels, cam=CAM)
ep.run()
