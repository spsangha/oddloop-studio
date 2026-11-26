"""Kinda Wild Films ep09 - 'A Pea Sprouted Inside His Lung'.  Brief: kindawild/09_pea_lung/brief.md (+ lead rulings 26 Nov).
ONE unbroken shot: the sprout under the lens -> wide (Howard, X-ray screen) -> 75 -> CANCER? -> NEGATIVE -> scope + surprise ->
1/2 INCH -> WRONG WAY -> tray of peas, HE ATE THEM -> back to the sprout under the lens (last frame = frame 0).
Voice line starts (frames): L0 0, L1 90, L2 210, L3 311, L4 397, L5 507, L6 617; speech ends f738.
The scope path is ep.tool_track (heads_hg: grip_tool scope where='track').
"""
import sys, os, math; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kwkit as KW
os.environ.setdefault('KW_LIGHT', '1')
HERE = os.path.dirname(os.path.abspath(__file__))
ep = KW.Episode('ep_pealung', injury="pea plant growing inside a man's lung",
                voice_lines=[l.strip() for l in open(os.path.join(HERE, 'ep_pealung.txt')) if l.strip()],
                music='sneaky_snitch', gap=0.9)
ep.waive = {"1 shots;": "brief s6: ONE unbroken shot (no cuts)",
            "last shot must use cam=KW.cam.loop()": "brief s6: the camera path itself returns to the frame-0 view at fN (the loop)",
            "HOOK foley transient": "brief s6 phase A: no sound at f0 (waiver as ep08)",
            "HOOK cut <= 200 ms after the last word": "brief 6b.9: the return starts after all labels are gone; the tail is music",
            "HOOK 8-11 words": "brief s3: script.txt is final (changing words is a STOP rule)",
            "voice line 7 must be exactly one sentence": "brief s3: script.txt is final (L6 is two short sentences in one line)",
            "shot pea holds": "brief s6: ONE unbroken shot; a visible change every <= 2.2 s comes from the lens, screen, labels and camera",
            "HOOK inside the body": "brief s5: real-scene props; the X-ray is on a screen, never on a person"}
how = ep.person('Howard', 'scientist', 'eatmore-sci', gender='m', age='old', race='caucasian', hair='short02')

FPS = 24; F = 1.0 / FPS
fw = lambda i, w: int(round(ep.word(i, w) * FPS))
fl = lambda i: int(round(ep.line(i) * FPS))
fle = lambda i: int(round((ep.line(i) + ep.vo_dur[i]) * FPS))
f_75, f_cancer, f_two, f_biop, f_neg = fw(1, 'seventyfive'), fw(2, 'cancer'), fw(3, 'Two'), fw(3, 'biopsies'), fw(3, 'negative')
f_sprouting, f_pea, f_half, f_wrong, f_laughed, f_ate = fw(4, 'sprouting'), fw(4, 'pea'), fw(4, 'half'), fw(5, 'wrong'), fw(6, 'laughed'), fw(6, 'ate')
f_L1, f_L2, f_L4, f_L5, f_L6 = fl(1), fl(2), fl(4), fl(5), fl(6)
f_L4e, f_L6e = fle(4), fle(6)
OFF_ATE = f_ate + 24                       # HE ATE THEM off (1 s)
RET0 = max(OFF_ATE + 8, f_L6e + 6)         # return starts (6b.9)
RET = 26                                   # camera return, frames (24-30)
FN = RET0 + RET; NF = FN + 1
ep.duration = round(NF / FPS, 4)

# ---- layout (world m; Howard standing at studio 'centre' (60, 0), facing -Y; +X = his left = the viewer's right) -----------
TZ = 0.86                                  # table top (upper thigh of a standing man)
YE = -0.18                                 # table edge in front of him
DISH = (60.0, -0.54)                       # CHECK 2: 9 cm further out (camera >= 40 cm from his arms in the close views)
SPR = (DISH[0], DISH[1], TZ + 0.0042)      # sprout base (on the gauze, raised 1.5 mm in CHECK 2)
SPR_MID = (SPR[0], SPR[1], SPR[2] + 0.0029)
SCR = (59.53, -0.28, 20.0)                 # screen (x, y, rz): back-left of the dish, turned toward the camera
TRAY = (60.37, -0.53)
SC_T = (59.73, -0.39, TZ, 195.0)           # scope handle on the table (Howard's right hand side), tip pointing out-left
REST = {'R': (59.83, -0.245, TZ + 0.011), 'L': (60.17, -0.245, TZ + 0.011)}
EYE = (59.97, -0.07, 1.62)

# lens: centred on the view ray 5.5 cm above the sprout, tilted 25 deg toward the camera; slide=1 -> 4.9 cm to the right
EL0 = math.radians(60.0)
RAY = (0.0, -math.cos(EL0), math.sin(EL0))
LU = float(os.environ.get('KW_LU', 0.06))          # lens centre height above the sprout along the view ray
LENS_C = tuple(SPR_MID[i] + LU * RAY[i] for i in range(3))
CLAMP = (60.45, YE, TZ)

# ---- props ----------------------------------------------------------------------------------------------------------------
I = KW.fx.item
tbl = I('bench', (60.2, YE - 0.8, 0.0), style='table', top=(1.6, 1.6), h=TZ, soft=True, wood=(0.27, 0.155, 0.075))
dish = I('kidney_dish', (DISH[0], DISH[1], TZ), rz=0)
spr = I('sprout', (0, 0, 0), rz=25, on=dish, point='gauze')
LS = int(os.environ.get('KW_LS', 16))
LOFF = float(os.environ.get('KW_LOFF', 0.056))      # CHECK-2 FIX 1: at f0 only the lens edge shows, in the right quarter
lens = I('lens_arm', CLAMP, rz=0, lens=tuple(LENS_C[i] - CLAMP[i] for i in range(3)), off=(LOFF, 0.0, 0.0), lt=30.0,
         power=float(os.environ.get('KW_LP', 10.3)), post=0.16, l1=0.30, l2=0.31,
         rim=0.0007, rim_z=1.0, th=0.001, rim_col=(0.10, 0.10, 0.105),
         keys=[(0.0, {'slide': 1.0}), (20 * F, {'slide': 0.0}), ((FN - LS) * F, {'slide': 0.0}), (FN * F, {'slide': 1.0})])
f_path = f_wrong
scr = I('xray_screen', (SCR[0], SCR[1], TZ), rz=SCR[2], width=0.44,
        keys=[(0.0, {'power': 0.0, 'ring': 0.0, 'path': 0.0, 'pulse': 1.0}), (f_L2 * F, {'power': 0.0}), ((f_L2 + 8) * F, {'power': 1.0}),
              ((f_cancer - 23) * F, {'ring': 0.0}), ((f_cancer - 7) * F, {'ring': 1.0}),
              (f_path * F, {'path': 0.0}), ((f_path + 18) * F, {'path': 1.0}),
              ((f_path + 18) * F, {'pulse': 1.0}), ((f_path + 23) * F, {'pulse': 1.15}), ((f_path + 28) * F, {'pulse': 1.0})])
f_tray = f_L6 + 4
tray = I('tray', (TRAY[0], TRAY[1], TZ), rz=90, style='meal', color=(0.20, 0.30, 0.42), ao=True,
         keys=[(0.0, {'dx': 0.9}), (f_tray * F, {'dx': 0.9}), ((f_tray + 14) * F, {'dx': -0.003}), ((f_tray + 18) * F, {'dx': 0.0})])
peas = I('peas', (0.0, 0.0, 0.0), on=tray, count=80, heap_r=0.045, heap_h=0.02)    # FIX 5: ~80 peas, heap 9 cm
props = [tbl, dish, spr, lens, scr, tray, peas]

# ---- Howard: standing, hands palm down on the table; the right hand picks up the scope (ep.tool_track) ----------------------
f_reach = f_L4 - 5                         # reach 10, grip 4 (thumb last), lift 12
f_sprouting_ = fw(4, 'sprouting'); B_ = f_sprouting_ + 15  # CHECK 2 FIX 3: the scope goes down during the camera arc (was L4 end)
CHAN = dict(reach=[(0, 0.0), (f_reach, 0.0), (f_reach + 10, 1.0), (B_ + 22, 1.0), (B_ + 32, 0.0)],
            g=[(0, 0.0), (f_reach + 9, 0.0), (f_reach + 12, 1.0), (B_ + 20, 1.0), (B_ + 23, 0.0)],
            gt=[(0, 0.0), (f_reach + 11, 0.0), (f_reach + 14, 1.0), (B_ + 19, 1.0), (B_ + 22, 0.0)],
            lift=[(0, 0.0), (f_reach + 14, 0.0), (f_reach + 26, 1.0), (B_ + 7, 1.0), (B_ + 19, 0.0)])
TIP_LOOK = (59.90, -0.46, 1.50)
ep.tool_track = dict(table=SC_T, rest=REST, chan=CHAN, look=EYE, lift_up=(0.0, -0.06, 0.16))
TRK = KW.hand.grip('grip_tool', item='scope', where='track')
LK_DISH = (DISH[0], DISH[1], TZ); LK_SCR = (SCR[0] + 0.02, SCR[1], TZ + 0.42)
P = KW.pose('stand', at='centre', left=TRK, right=TRK, face='focus', look=LK_DISH, lean=12.0, blend=5 * F)
P = (P.then((f_L2 + 2) * F, blend=10 * F, look=LK_SCR)
      .then((f_reach - 2) * F, blend=8 * F, look=(SC_T[0], SC_T[1], TZ))
      .then((f_reach + 18) * F, blend=10 * F, look=TIP_LOOK, lean=5.0)
      .then(f_sprouting * F, blend=6 * F, face={'surprise': 1.0, 'spoon': 1.0})
      .then((B_ + 7) * F, blend=10 * F, face='focus', look=LK_DISH, lean=12.0)
      .then((f_wrong - 2) * F, blend=10 * F, look=LK_SCR)
      .then((f_tray + 6) * F, blend=10 * F, look=(TRAY[0], TRAY[1], TZ))
      .then(f_laughed * F, blend=6 * F, face={'focus': 0.5, 'smile': 0.4})
      .then((RET0 - 8) * F, blend=8 * F, face='focus', look=LK_DISH))
ep.blinks = {'Howard': [130, 205, 300, 380, 500, 590, 660, 740]}

# ---- camera (one path) -----------------------------------------------------------------------------------------------------
def close(d, lens=85.0, el=60.0, at=SPR_MID):
    e = math.radians(el); return ((at[0], at[1] - math.cos(e) * d, at[2] + math.sin(e) * d), at, lens)
def wide(cx, cy, cz, d, el=14.0, lens=50.0, push=0.0, yaw=0.0):
    d = d * (1 - push); e = math.radians(el); a = math.radians(yaw)
    return ((cx + math.sin(a) * math.cos(e) * d, cy - math.cos(a) * math.cos(e) * d, cz + math.sin(e) * d), (cx, cy, cz), lens)
D0 = float(os.environ.get('KW_D0', 0.16))
AIM0 = (SPR_MID[0] + 0.10 * D0 * 20.25 / 85.0, SPR_MID[1], SPR_MID[2])     # FIX 1: the sprout sits a little left of centre
C0 = close(D0, at=AIM0); C0p = close(D0 * 0.97, at=AIM0)
WC = float(os.environ.get('KW_WC', 59.83)); WZ = float(os.environ.get('KW_WZ', 1.41)); WD = float(os.environ.get('KW_WD', 2.57))
VW = wide(WC, -0.30, WZ, WD)
VS = wide(WC - 0.03, -0.30, WZ, WD, push=0.06, yaw=-3.0)
VD_D = float(os.environ.get('KW_VD', 0.245))
VD = close(VD_D, lens=80.0, el=58.0)                      # FIX 4: the 1/2 INCH close (sprout >= 420 px through the lens)
VS2 = wide(59.62, -0.30, WZ - 0.05, WD * 0.80)
VE = wide(60.05, -0.35, WZ - 0.02, WD * 1.02)
VM = wide(60.22, -0.38, 1.335, 1.85)                        # FIX 5: lean toward the tray on 'meals' (plate >= 300 px)
FACE = ((59.993, -1.191, 1.169), (59.990, -0.115, 1.467), 75.0)   # FIX 3: medium close, eyes upper third (world; was cam.face side 15 dist 1.1, which follows his gaze down)
PB = wide(59.97, -0.45, 1.20, 2.5, el=25.0, lens=40.0)    # pull back (via key, world: a face preset follows his gaze down under the table)
D1 = close(1.25, lens=65.0, el=66.0)                         # high in front of the dish (via key): the coat stays at the top edge
R1 = close(1.25, lens=65.0, el=66.0, at=AIM0)
R0 = ((60.05, -2.30, 2.00), (60.05, -0.50, 0.95), 40.0)    # return via key: far and high, already looking down at the table                # return via key
f_scope, f_meals = fw(4, 'scope'), fw(6, 'meals')
f_fc = f_sprouting - 2; f_hold = f_sprouting + 20; f_arc = f_hold + 30     # face from f_fc, surprise held to f_hold, arc to f_arc
KEYS = [(0.0, *C0), (70 * F, *C0p), (120 * F, *VW), (f_L2 * F, *VW), ((f_L2 + 16) * F, *VS),
        (f_scope * F, *VS), (f_fc * F, *FACE), (f_hold * F, *FACE), ((f_hold + 10) * F, *PB), ((f_hold + 20) * F, *D1), (f_arc * F, *VD),
        (f_wrong * F, *VD), ((f_wrong + 16) * F, *VS2), (f_L6 * F, *VS2), (f_meals * F, *VE), ((f_meals + 16) * F, *VM),
        (RET0 * F, *VM), ((RET0 + 7) * F, *R0), ((RET0 + 15) * F, *R1), (FN * F, *C0), (FN * F + 1.0, *C0)]
CAM = KW.cam.path(KEYS, fstop=64.0, via=(8, 9, 17, 18))

if os.environ.get('KW_FACECAM'):      # dev only (step-4 face still): a face view instead of the path
    CAM = KW.cam.face(how, side=float(os.environ['KW_FACECAM']), lens=85, dist=1.1, push=0.0)

# ---- labels + sounds -----------------------------------------------------------------------------------------------------
YL = dict(color='yellow', size=1.2); Y = 0.84
labels = [KW.fx.label('75', at=f_75 * F, pos=(0.5, Y), dur=1.3, **YL),
          KW.fx.label('CANCER?', at=f_cancer * F, pos=(0.5, Y), dur=(f_two - 6 - f_cancer) * F, **YL),
          KW.fx.label('NEGATIVE', at=f_neg * F, pos=(0.625, Y), dur=(f_L4 - 6 - f_neg) * F, keys=[(0.0, {'width': 600})], **YL),
          KW.fx.label('1/2 INCH', at=(f_arc - 3) * F, pos=(0.5, Y), dur=(f_L4e + 20 - f_arc + 3) * F, keys=[(0.0, {'width': 700.0})], **YL),   # seen through the lens glass (x1.27): 700 px -> ~890 px on screen,
          KW.fx.label('WRONG WAY', at=f_wrong * F, pos=(0.5, Y), dur=(f_L6 - 6 - f_wrong) * F, **YL),
          KW.fx.label('HE ATE THEM', at=f_ate * F, pos=(0.5, Y), dur=(OFF_ATE - f_ate) * F, **YL)]
if hasattr(KW.fx, 'mark'):
    labels += [KW.fx.mark('tick', at=f_two * F, pos=(0.11, Y), px=96, dur=(f_L4 - 6 - f_two) * F),
               KW.fx.mark('tick', at=f_biop * F, pos=(0.225, Y), px=96, dur=(f_L4 - 6 - f_biop) * F),
               KW.fx.mark('ruler', at=(f_arc - 2) * F, pos=tuple(float(x) for x in os.environ.get('KW_RULER', '0.521,0.443').split(',')),
                          px=float(os.environ.get('KW_RULER_PX', 374)), rot=float(os.environ.get('KW_RULER_ROT', 22.9)), dur=(f_L4e + 20 - f_arc + 2) * F)]
for f_ in (f_75, f_cancer, f_neg, f_half, f_wrong, f_ate): ep.sound(f_ * F, 'thud', 0.5)
for f_ in (f_two, f_biop): ep.sound(f_ * F, 'tick', 0.35)
ep.sound((f_reach + 14) * F, 'thud', 0.3)                    # tap: the scope leaves the table
ep.sound((f_tray + 14) * F, 'thud', 0.3)                     # tap: the tray settles

ep.label_lens_fix = True; ep.relight_after_pose = True
ep.mouth_fix = True                                          # N6 (opt-in): inner mouth material + a little light (heads_hg)
EXP = float(os.environ.get('KW_EXP0', -1.0))
ep.exposure_keys = [(0.0, EXP), (70 * F, EXP), (120 * F, 0.0), ((FN - RET) * F, 0.0), (FN * F, EXP)]
ep.shot(0.0, 'pea', set='studio', world='sky', cast={how: P}, fx=props + labels, cam=CAM)
ep.run()
