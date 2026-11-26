"""Kinda Wild Films ep10 - 'What Your Body Does To A Splinter'.  Brief: kindawild/10_splinter/brief.md (+ lead rulings 26 Nov).
ONE unbroken shot: fingertip macro (splinter) -> Ben chest-up -> red + swollen -> push through the skin into a local
cut-away block -> white cells -> pus -> pushed out -> rewind -> walled off -> rise out to Ben, tweezers, same angle -> fingertip (loop).
The fingertip, splinter, block, cells, pus and capsule are kwfinger.Fingertip; the camera is ep.cam_fn (keys in the pad frame
of the left index fingertip, or in the world), the right hand is ep.hand_fn (the tweezers pull along the splinter axis).
"""
import sys, os, math; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kwkit as KW
os.environ.setdefault('KW_LIGHT', '1')
HERE = os.path.dirname(os.path.abspath(__file__))
ep = KW.Episode('ep_splinter', injury="a splinter",
                voice_lines=[l.strip() for l in open(os.path.join(HERE, 'ep_splinter.txt')) if l.strip()],
                music='sneaky_snitch', gap=1.4)
ep.waive = {"1 shots;": "brief s6: ONE unbroken shot (no cuts)",
            "last shot must use cam=KW.cam.loop()": "brief s6: the camera path itself returns to the frame-0 view at fN (the loop)",
            "HOOK cut <= 200 ms after the last word": "brief 6b.8 + lead: 1.1 s loop return carrying the end CTA, then the frame-0 title",
            "HOOK 8-11 words": "brief s3: script.txt is final",
            "shot finger holds": "brief s6: ONE unbroken shot; a visible change every <= 2.2 s comes from the finger, cells and camera",
            "HOOK inside the body": "brief s5: the cut-away is a local skin block after 3.0 s (D5)"}
ben = ep.person('Ben', 'civilian', 'eatmore-ben', gender='m', age='young', race='caucasian', hair='short02', tee='teal')

FPS = 24; F = 1.0 / FPS
fw = lambda i, w: int(round(ep.word(i, w) * FPS))
fl = lambda i: int(round(ep.line(i) * FPS))
fle = lambda i: int(round((ep.line(i) + ep.vo_dur[i]) * FPS))
f_leave, f_red, f_swollen, f_white, f_pus, f_push, f_out = fw(0, 'leave'), fw(1, 'red'), fw(1, 'swollen'), fw(2, 'White'), fw(3, 'pus'), fw(4, 'push'), fw(4, 'out')
f_walls, f_lump, f_same = fw(5, 'walls'), fw(5, 'lump'), fw(6, 'same')
f_L0e, f_L1, f_L2, f_L3, f_L4, f_L5, f_L6, f_L6e = fle(0), fl(1), fl(2), fl(3), fl(4), fl(5), fl(6), fle(6)

# ---- timeline (frames) ---------------------------------------------------------------------------------------------------
BEND = 24                                   # 6b.1 finger bend f0-24
B0 = f_leave; B1 = B0 + 34                  # glide back to Ben
C0 = f_L1 + 22; C1 = f_red - 6              # glide back to the fingertip
DV0 = f_white - 15; DV1 = f_white - 1       # the push through the surface (15 frames)
VAN0 = DV0 + 3; VAN1 = VAN0 + 6             # near skin fades over 6 frames while moving
RW0 = f_L5; RW1 = RW0 + 10                  # the rewind
CAP0 = f_walls; CAP1 = CAP0 + 24
RS0 = f_lump - 8; RS1 = RS0 + 34            # rise out through the surface to Ben
RVAN0 = RS0 + 6; RVAN1 = RVAN0 + 6
TW0 = f_L6 + 2; TW1 = TW0 + 16              # right hand rises from below the frame with the tweezers
PUSH0 = TW1; PUSH1 = PUSH0 + 13             # eased push into the pull close (lead CHECK 1 #5)
GR0 = PUSH1 + 1; GR1 = GR0 + 4              # jaws + grip close at full size (thumb last)
PL0 = max(f_same, GR1 + 1); PL1 = PL0 + 16                # the pull along the axis
OFF_SAME = max(f_L6e + 4, PL1 + 20)
RET0 = OFF_SAME - 4; RET = 22; FN = RET0 + RET; NF = FN + 1
ep.duration = round(NF / FPS, 4)
CTA0 = FN - 40                               # the CTA: ~1.25 s, off 10 frames before the loop point
UNPULL0 = RET0; UNPULL1 = RET0 + 8         # the loop: a quick reverse of the pull, the hand drops away

def ease(x): x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)
def ramp(f, a, b): return ease((f - a) / max(1e-6, b - a))
def keys(f, ks):
    """[(frame, value), ...] eased"""
    if f <= ks[0][0]: return ks[0][1]
    for (f0, v0), (f1, v1) in zip(ks, ks[1:]):
        if f0 <= f <= f1: return v0 + (v1 - v0) * ease((f - f0) / max(1e-6, f1 - f0))
    return ks[-1][1]

# ---- Ben -----------------------------------------------------------------------------------------------------------------
TIP_W = tuple(float(x) for x in os.environ.get('KW_TIPW', '60.04,-0.47,1.62').split(','))     # fingertip, world (measured)
INS = KW.hand.inspect('index', dist=float(os.environ.get('KW_INSD', 0.34)), offset=(0.05, -0.10))
P = KW.pose('stand', at='centre', left=INS, right=KW.hand.fn('tweezers'), face='focus', look=TIP_W, blend=5 * F)
P = (P.then((f_leave - 4) * F, blend=8 * F, face={'focus': 0.6, 'wince': 0.4})
      .then((B1 + 14) * F, blend=12 * F, face='focus')
      .then((PL1 + 2) * F, blend=10 * F, face={'focus': 0.5, 'smile': 0.3})
      .then((RET0 + 6) * F, blend=12 * F, face='focus'))
ep.blinks = {'Ben': [70, 150, 236, 320, 405, 490, 575, 642]}       # every 3-4 s, none in the last 12 frames

ft = None          # kwfinger.Fingertip (built in build_hook)
TW = {}

def build(rt):
    global ft
    import kwfinger, kwprops, bpy
    ra = rt.actors[ben]; ft = kwfinger.Fingertip(rt, ra, side='L', finger='index', shape='inspect')
    c = bpy.data.collections.get('kw_finger')
    tw = kwprops.tweezers(c); tw.set(gap=0.0025); TW['p'] = tw
    hg = ra.p.hg
    import heads_hg
    Pl_, Rr_ = heads_hg._tool_Pl(hg, rt, ra, 'R', 'g_tweezers'); TW['Pl'] = Pl_ @ Rr_.inverted() @ Matrix.Translation((TW_BACK, 0, 0))   # item root = wrist @ Pl @ Rr^-1; held TW_BACK further back (tips clear of the fingers)
    rt.set_shape(ra.p, 'L', 'inspect'); bpy.context.view_layer.update(); TW['rel'] = rt.wmat(ra.p, 'wrist.L').inverted() @ ft.frame()   # fingertip frame in the left wrist
    rt.reset(ra.p); bpy.context.view_layer.update()
    if os.environ.get('KW_PROBE'):
        print('PROBE built')
        pp = ra.p
        for sd in 'LR':
            for sh in ('open', 'fist'):
                rt.set_shape(pp, sd, sh); bpy.context.view_layer.update(); Mi = rt.wmat(pp, f'wrist.{sd}').inverted()
                tip = Mi @ rt.bw(pp, f'finger3-3.{sd}', True); print('PROBE cal', sd, sh, 'tip local', tuple(round(x, 3) for x in tip), 'dot pn', round(tip.dot(V(ra.hand[sd]['pnorm'])), 3), 'pn', tuple(round(x, 2) for x in ra.hand[sd]['pnorm']), 'fd', tuple(round(x, 2) for x in ra.hand[sd]['fdir']))
ep.build_hook = build

# ---- right hand + tweezers ------------------------------------------------------------------------------------------------
from mathutils import Vector as V, Matrix, Quaternion
TW_GAP_OPEN, TW_GAP_HOLD = 0.0024, 0.00104       # tip-centre half-gaps: open / closed on the 1 mm width (tip radius 0.55 mm)
TW_HAND = V(tuple(float(x) for x in os.environ.get('KW_TWDIR', '-0.25,-0.65,0.70').split(',')))   # pad-local direction tips -> hand
TW_INSET = 0.0014
TW_POLE = tuple(float(x) for x in os.environ.get('KW_TWPOLE', '0.40,0.35,0.05').split(','))
TW_BACK = float(os.environ.get('KW_TWBACK', 0.04))     # the pinch sits 8 cm behind the tips (the kit tool grip holds 4 cm)

def pull_m(f):
    """metres the splinter is drawn out along its axis by the tweezers"""
    if f < PL0: return 0.0
    if f <= PL1: return ease((f - PL0) / (PL1 - PL0)) * (ft.Lin + 0.003)
    if f < UNPULL0: return ft.Lin + 0.003
    return (1 - ease((f - UNPULL0) / (UNPULL1 - UNPULL0))) * (ft.Lin + 0.003)

def tw_target(f, Fm=None):
    """tweezers root, world: tips at the grip point on the stub, pinching across the splinter's width"""
    Fm = ft.frame() if Fm is None else Fm; out = pull_m(f)
    G = ft.splinter_M(out) @ V((TW_INSET, 0, 0))
    X = -TW_HAND.normalized(); Y = V((0, 1, 0)); Y = (Y - X * Y.dot(X)).normalized(); Z = X.cross(Y)
    R = Matrix((X, Y, Z)).transposed()
    M = R.to_4x4(); M.translation = G - R @ V((0.06, 0.0, 0.0012))
    return Fm @ M

def tw_state(f):
    """0 = at rest by his side .. 1 = at the splinter"""
    if f < TW0 or f > UNPULL1 + 10: return 0.0
    if f <= TW1: return ease((f - TW0) / (TW1 - TW0))
    if f <= UNPULL1 + 2: return 1.0
    return 1.0 - ease((f - UNPULL1 - 2) / 8)

def grip(f):
    g = keys(f, [(0, 0.0), (GR0, 0.0), (GR0 + 3, 1.0), (UNPULL1, 1.0), (UNPULL1 + 3, 0.0)])
    gt = keys(f, [(0, 0.0), (GR0 + 1, 0.0), (GR1, 1.0), (UNPULL1, 1.0), (UNPULL1 + 3, 0.0)])
    return g, gt

def hand_fn(rt, ra, side, h, u, t):
    f = t * FPS; s = tw_state(f)
    if side != 'R' or s <= 0.0 or ft is None: return None
    rest = rt.hand_goal(ra, side, KW.Hand('rest'), u, t)
    gL = rt.hand_goal(ra, 'L', INS, u, t); DL, tL, sL, RL, _ = gL; tlL = ra.hand['L'][sL][tL]
    Fp_ = Matrix.Translation(DL - RL @ tlL) @ RL.to_4x4() @ TW['rel']        # the left fingertip frame this frame (L is solved after R's goal)
    tl = ra.hand[side]['hold']['palm']; W = tw_target(f, Fp_) @ TW['Pl'].inverted()
    Dr, _, _, Rr, poler = rest; Wr = Matrix.Translation(Dr - Rr @ ra.hand[side]['palm' if False else 'relaxed']['palm']) @ Rr.to_4x4()
    via = W.translation + V((0.0, -0.06, -0.26))     # under the target, in front of the belly: the hand rises from below (lead CHECK 1 #4)
    pos = (1 - s) ** 2 * Wr.translation + 2 * (1 - s) * s * via + s * s * W.translation
    q0_, q1_ = Wr.to_quaternion(), W.to_quaternion()
    if q0_.dot(q1_) < 0: q1_.negate()
    q = q0_.slerp(q1_, s); Wb = Matrix.Translation(pos) @ q.to_matrix().to_4x4()
    R3 = ra.p.rig.matrix_world.to_3x3().normalized(); Up = R3 @ V((0, 0, 1)); sh = rt.bw(ra.p, 'upperarm01.R'); out_ = R3 @ V((-1, 0, 0)); Fp = R3 @ V((0, -1, 0))
    po_ = TW_POLE; pole = sh + out_ * po_[0] - Up * po_[1] + Fp * po_[2]     # elbow out to the side, not low: wrist flex stays natural
    return Wb @ tl, 'palm', 'hold', Wb.to_3x3(), poler.lerp(pole, min(1.0, 1.8 * s))
ep.hand_fn = hand_fn

def pose_hook(rt, t):
    import heads_hg
    f = t * FPS; p = rt.actors[ben].p
    # 6b.1: the index bends 6 deg at the last joint and back over f0-24 (and again into the loop end, so fN = f0)
    b = 6.0 * math.sin(math.pi * f / BEND) if f < BEND else 0.0
    e = p.pb('finger2-3.L').rotation_euler; e.x += math.radians(b)
    # right hand: the tweezers grip (AUTH g_tweezers table, thumb last), relaxed hold otherwise
    g, gt = grip(f); s = tw_state(f)
    if s <= 0.0: return
    tab = heads_hg.AUTH['g_tweezers']
    for k in range(1, 6):
        (ga, gz) = tab[k]; w_ = (0.86 + 0.14 * (gt if k == 1 else g))
        for jj in (1, 2, 3):
            pb = p.pb(f'finger{k}-{jj}.R'); e = pb.rotation_euler
            e.x = math.radians(ga[jj - 1] * w_); e.y = 0.0; e.z = math.radians(gz if jj == 1 else 0.0) * w_
ep.pose_hook = pose_hook

# ---- the fingertip states ---------------------------------------------------------------------------------------------
TICKS = []
def state(f):
    v = {}
    v['red'] = keys(f, [(0, 0.0), (f_red, 0.0), (f_red + 18, 1.0), (f_L3, 1.0), (f_L3 + 30, 0.5), (CAP0, 0.5), (CAP1 + 10, 0.0)])
    if f < BEND: v['red'] = max(v['red'], 0.22 * math.sin(math.pi * f / BEND))     # opening rule (1): the press flushes the skin at f0
    v['swell'] = keys(f, [(0, 0.0), (f_swollen, 0.0), (f_swollen + 22, 1.0), (CAP0, 1.0), (CAP1, 0.0)])
    v['dome'] = keys(f, [(0, 0.0), (f_pus + 12, 0.0), (f_pus + 50, 1.0), (f_push + 18, 1.0), (f_out + 22, 0.0), (RW0, 0.0), (RW0 + 3, 0.6), (RW1, 0.0)])
    v['pocket'] = keys(f, [(0, 0.0), (f_pus + 8, 0.0), (f_pus + 48, 1.0), (f_push + 16, 1.0), (f_out + 20, 0.0), (RW0, 0.0), (RW0 + 3, 0.6), (RW1, 0.0)])
    v['pus'] = keys(f, [(0, 0.0), (f_pus, 0.0), (f_pus + 34, 1.0)])
    v['sheath_fade'] = keys(f, [(0, 1.0), (RW0, 1.0), (RW1, 0.0)])
    v['lump'] = keys(f, [(0, 0.0), (CAP0 + 12, 0.0), (f_lump + 6, 1.0), (RET0, 1.0), (FN - 4, 0.0)])
    v['capsule'] = keys(f, [(0, 0.0), (CAP0, 0.0), (CAP1, 1.0)])
    # the push out (E) and the rewind (F)
    po = keys(f, [(0, 0.0), (f_push, 0.0), (f_push + 34, 1.0), (RW0, 1.0), (RW1, 0.0)])
    v['out'] = po
    v['cells'] = (f - f_white) / FPS if DV0 <= f < RS1 else -1.0
    v['vanish'] = keys(f, [(0, 0.0), (VAN0, 0.0), (VAN1, 1.0), (RVAN0, 1.0), (RVAN1, 0.0)])
    v['cut'] = 1.0 if VAN0 <= f < RVAN1 else 0.0
    v['ridges'] = 1.0
    return v

def frame_hook(rt, t):
    import bpy
    f = t * FPS; ra = rt.actors[ben]; p = ra.p
    rt.CAM.data.clip_start = 0.002 if DV0 + 6 <= f <= RS0 + 16 else 0.01     # labels ride at 8 mm inside the cut-away
    rt.CAM.data.dof.use_dof = not (DV0 + 6 <= f <= RS0 + 16)     # f/64 still blurred the near labels; the cut-away reads flat anyway
    gl_ = 3.0 if (f < B0 or f > FN - 14) else 0.0       # the opening / loop macro is dim (exposure -0.6): labels glow a little there
    for m_ in bpy.data.materials:
        if m_.name.startswith('KW label') and m_.node_tree:
            b_ = next((n for n in m_.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)
            if b_ is not None:
                b_.inputs['Emission Color'].default_value = b_.inputs['Base Color'].default_value; b_.inputs['Emission Strength'].default_value = gl_
    v = state(f)
    out_t = pull_m(f)
    if out_t > 0: v['out'] = out_t / (ft.Lin + 0.0015)
    ft.set(**v)
    # tweezers: in the hand (wrist @ Pl) while moving, on the splinter end while gripping
    tw = TW['p']; s = tw_state(f); Mh = rt.wmat(p, 'wrist.R') @ TW['Pl']
    if s >= 1.0 or (GR0 - 2 <= f <= UNPULL1 + 1):
        Mt = tw_target(f)
        k = min(1.0, (f - (TW1 - 2)) / 2.0) if f < TW1 else 1.0
        if k < 1.0:
            q = Mh.to_quaternion().slerp(Mt.to_quaternion(), k); Mt = Matrix.Translation(Mh.translation.lerp(Mt.translation, k)) @ q.to_matrix().to_4x4()
    else: Mt = Mh
    tw.root.matrix_world = Mt
    g, gt = grip(f); tw.set(gap=TW_GAP_OPEN + (TW_GAP_HOLD - TW_GAP_OPEN) * min(g, gt))
    # eyes converge on the fingertip (N5)
    tip = ft.frame() @ V((0.002, 0, 0.002))
    rt.eyes_at(ra, tip)
    # inside the skin: Ben is hidden (the near skin has faded out; the block fills the frame)
    inside = v['vanish'] >= 0.999
    if 'hide' not in TW:
        hr = ft.rig; obs = list({o for o in list(getattr(p.hg, 'meshes', [])) + [o for o in bpy.data.objects if o.type == 'MESH' and (o.parent in (hr, p.rig) or o in p.parts)] if o is not ft.splinter and o.name not in ft.c.objects})
        TW['hide'] = [(o, o.hide_render) for o in obs]
    for o, h0 in TW['hide']: o.hide_render = True if inside else h0
    tw.root.hide_render = inside
    for o in tw.objs: o.hide_render = inside
    ft.splinter.hide_render = False
    if os.environ.get('KW_LBOX'): _lbox(rt, f, p)
    if os.environ.get('KW_PROBE'):
        R3 = p.rig.matrix_world.to_3x3(); Mw = rt.wmat(p, 'wrist.L'); info = ra.hand['L']
        print('PROBE L fdir', tuple(round(x, 2) for x in (Mw.to_3x3() @ V(info['fdir'])).normalized()), 'pnorm', tuple(round(x, 2) for x in (Mw.to_3x3() @ V(info['pnorm'])).normalized()),
              'idx', tuple(round(x, 2) for x in (rt.bw(p, 'finger2-3.L', True) - rt.bw(p, 'finger2-1.L')).normalized()), 'wristL', tuple(round(x, 3) for x in Mw.translation))
        hgr = ft.rig; HW = hgr.matrix_world; pnw = (Mw.to_3x3() @ V(info['pnorm'])).normalized(); fdw = (Mw.to_3x3() @ V(info['fdir'])).normalized()
        for nm in ('finger2-1.L', 'finger2-2.L', 'finger2-3.L', 'finger3-2.L', 'finger3-3.L'):
            b_ = p.pb(nm); d_ = (rt.bw(p, nm, True) - rt.bw(p, nm)).normalized(); print('PROBE MH', nm, 'dot pn', round(d_.dot(pnw), 2), 'dot fd', round(d_.dot(fdw), 2), 'rot', tuple(round(math.degrees(x), 1) for x in b_.rotation_euler))
        for nm in ('f_index.01.L', 'f_index.02.L', 'f_index.03.L', 'f_middle.03.L'):
            b_ = hgr.pose.bones.get(nm)
            if b_ is None: continue
            d_ = (HW @ b_.tail - HW @ b_.head).normalized(); print('PROBE HG', nm, 'dot pn', round(d_.dot(pnw), 2), 'dot fd', round(d_.dot(fdw), 2))
        Fm = ft.frame(); print('PROBE f', int(f), 'frame', [tuple(round(x, 4) for x in r) for r in Fm], 'eyes', tuple(round(x, 4) for x in (rt.bw(p, 'eye.L') + rt.bw(p, 'eye.R')) / 2),
                               'head', tuple(round(x, 4) for x in rt.bw(p, 'head')), 'tw', tuple(round(x, 4) for x in Mt.translation), 'wristR err mm', round((Mh.translation - Mt.translation).length * 1000, 1))
ep.frame_hook = frame_hook

def _lbox(rt, f, p):
    """dev check (KW_LBOX=1, NORENDER): every visible label's screen box at 1080 x 1920, margins, occlusion along camera rays,
    wood points inside the box; right wrist twist/flex vs the forearm (HG rig)"""
    import bpy
    from bpy_extras.object_utils import world_to_camera_view as w2c
    bpy.context.view_layer.update()
    sc = bpy.context.scene; cam = rt.CAM; dg = bpy.context.evaluated_depsgraph_get(); P0 = cam.matrix_world.translation
    wood = []
    if not ft.splinter.hide_render:
        Mw = ft.splinter.matrix_world; vs = ft.splinter.data.vertices
        for i in range(0, len(vs), max(1, len(vs) // 80)):
            q = w2c(sc, cam, Mw @ vs[i].co)
            if q.z > 0: wood.append((q.x * 1080, (1 - q.y) * 1920))
    for fx_, it in rt.FX.items.items():
        if getattr(fx_, 'kind', None) != 'label' or not it or it.get('label') is None: continue
        lab = it['label']; ob = lab.object
        if ob.hide_render or ob.scale[0] < 0.5: continue
        M = ob.matrix_world; pts = [M @ V(c) for c in ob.bound_box]
        for o_, _l in getattr(lab, 'extras', ()): pts += [o_.matrix_world @ V(c) for c in o_.bound_box]
        sp = [w2c(sc, cam, q) for q in pts]; xs = [q.x * 1080 for q in sp]; ys = [(1 - q.y) * 1920 for q in sp]
        x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
        mine = {ob.name} | {o_.name for o_, _l in getattr(lab, 'extras', ())}
        occ = 0; n = 0; hn_ = ''
        for i in range(9):
            for j in range(3):
                tgt = M @ V((ob.bound_box[0][0] + (ob.bound_box[6][0] - ob.bound_box[0][0]) * (i + 0.5) / 9, (ob.bound_box[0][1] + ob.bound_box[6][1]) / 2 + (ob.bound_box[6][1] - ob.bound_box[0][1]) * (j - 1) * 0.3, ob.bound_box[6][2]))
                d = tgt - P0; L_ = d.length; hit, loc, nrm, idx, hob, mx = sc.ray_cast(dg, P0, d.normalized(), distance=L_ * 0.97)
                n += 1
                if hit and hob.name not in mine:
                    occ += 1; hn_ = hob.name
        wd = sum(1 for (wx, wy) in wood if x0 - 8 <= wx <= x1 + 8 and y0 - 8 <= wy <= y1 + 8)
        print('LBOX f%d %-22s x %4.0f-%4.0f y %4.0f-%4.0f w %4.0f margins %3.0f/%3.0f occ %d/%d %s wood %d sc %.3f' % (f, fx_.o['text'], x0, x1, y0, y1, x1 - x0, x0, 1080 - x1, occ, n, hn_, wd, ob.scale[0]), flush=True)
    if TW0 <= f <= PUSH1 + 4:
        hg = ft.rig; HW = hg.matrix_world
        fa = next((b for b in ('forearm.R', 'lowerarm.R', 'DEF-forearm.R') if b in hg.pose.bones), None); hd = next((b for b in ('hand.R', 'DEF-hand.R') if b in hg.pose.bones), None)
        if fa and hd:
            Rf = (HW @ hg.pose.bones[fa].matrix).to_3x3().normalized(); Rh = (HW @ hg.pose.bones[hd].matrix).to_3x3().normalized()
            Rrel = Rf.inverted() @ Rh; q = Rrel.to_quaternion(); tw = 2 * math.degrees(math.atan2(q.y, q.w)); yv = Rrel @ V((0, 1, 0)); flex = math.degrees(math.acos(max(-1, min(1, yv.y))))
            wr = HW @ hg.pose.bones[hd].head; qq = w2c(sc, cam, wr)
            print('TWIST f%d twist %.0f flex %.0f wristR screen (%.0f, %.0f) z %.2f' % (f, tw, flex, qq.x * 1080, (1 - qq.y) * 1920, qq.z), flush=True)

# ---- camera: keys in the pad frame ('p', live with the finger) or the world ('w') -------------------------------------------
FREF = None
def _fref():
    m = os.environ.get('KW_FREF')
    if m: v_ = [float(x) for x in m.split(',')]; return Matrix([v_[0:4], v_[4:8], v_[8:12], v_[12:16]])
    return None
FREF = _fref()
def P_(x, y, z): return V((x, y, z))
a30 = math.radians(30)
D0 = float(os.environ.get('KW_D0', 0.074))               # frame width 15 mm at 100 mm
T0 = P_(0.0016, 0.00145, -0.0005)
def macro(d, tgt=T0, el=a30, yaw=0.0):
    dirv = V((math.sin(yaw), math.sin(el), math.cos(el))).normalized(); return tgt + dirv * d
M0 = ('p', macro(D0), T0, 100.0, 'x')
M0b = ('p', macro(D0 * 0.97), T0, 100.0, 'x')
SIDE = ('p', P_(-0.03, 0.32, 0.06), P_(0.04, 0.0, 0.12), 60.0, 'w')
BEN = ('w', None, None, 50.0, 'w')                         # world, set from FREF below
M1 = ('p', macro(D0 * 1.05), T0, 100.0, 'x')
M1b = ('p', macro(D0 * 0.92), T0, 100.0, 'x')
# the dive / inside / rise: one parametric view (angle off the pad normal toward +c, distance, lens, target; up = the finger axis X
# all the way, so there is no roll): the camera always stays on the pad side (z > 0), outside the finger; the near skin fades out
TI = P_(0.0045, 0.0, -0.0027)                 # centre of the cut face (splinter + dermis + fat), frame ~9.5 x 17 mm
TE0, TE1 = P_(0.0025, 0.0, -0.0024), P_(-0.0010, 0.0, -0.0019)
DI = 0.0165
def _pk(th, d, lens, tgt): return (th, d, lens, tgt)
PK = [(DV0, _pk(30.0, D0 * 0.92, 100.0, T0)), (DV1, _pk(65.0, DI, 35.0, TI)), (f_white + 6, _pk(65.0, DI, 35.0, TI)), (f_L3 - 10, _pk(56.0, DI, 35.0, TI)),
      (f_push - 6, _pk(57.0, DI, 35.0, TE0)), (f_out + 8, _pk(57.0, DI * 1.06, 35.0, TE1)), (RW1 + 4, _pk(60.0, DI, 35.0, TI)), (RS0, _pk(60.0, DI, 35.0, TI)),
      (RS0 + 16, _pk(30.0, D0 * 0.92, 100.0, T0))]
def _pview(f):
    k1 = next((i for i, k in enumerate(PK) if k[0] >= f), len(PK) - 1); k0 = max(0, k1 - 1)
    (fa, A), (fb, B) = PK[k0], PK[k1]; x = ease((f - fa) / max(1e-6, fb - fa)) if fb > fa else 0.0
    th = math.radians(A[0] + (B[0] - A[0]) * x); d = A[1] * (B[1] / A[1]) ** x; lens = A[2] * (B[2] / A[2]) ** x; tgt = A[3].lerp(B[3], x)
    return tgt + V((0.0, math.sin(th), math.cos(th))) * d, tgt, lens
SIDEF = ('w', None, None, 45.0, 'w')

def _key_world(k, Fm):
    sp, pos, tgt, lens, upk = k
    if sp == 'w':
        return V(pos), V(tgt), lens, V((0, 0, 1))
    Fx = Fm if sp == 'p' else FREF
    up = {'x': Fx.to_3x3() @ V((1, 0, 0)), 'z': Fx.to_3x3() @ V((0, 0, 1)), 'w': V((0, 0, 1))}[upk]
    return Fx @ pos, Fx @ tgt, lens, up.normalized()

def _wv(name, d):
    return tuple(float(x) for x in os.environ.get(name, d).split(','))
def _cam_keys():
    # world keys (measured on the probe: fingertip ~(60.037,-0.468,1.613), eyes (59.98,-0.155,1.692); Ben faces -Y, his left = +X)
    W_ = lambda pos, tgt, lens: ('w', _wv(*pos), _wv(*tgt), lens, 'w')
    BEN_ = W_(('KW_BENP', '60.30,-1.00,1.68'), ('KW_BENT', '60.01,-0.30,1.60'), 50.0)
    BENb = ('w', tuple(V(BEN_[1]) + (V(BEN_[2]) - V(BEN_[1])) * 0.03), BEN_[2], 50.0, 'w')
    SIDE = W_(('KW_SIDEP', '60.22,-0.66,1.72'), ('KW_SIDET', '60.03,-0.42,1.64'), 70.0)
    SIDE_R = W_(('KW_SIDERP', '60.20,-0.68,1.71'), ('KW_SIDERT', '60.03,-0.43,1.63'), 70.0)
    SF = W_(('KW_SFP', '60.55,-1.04,1.92'), ('KW_SFT', '60.00,-0.25,1.67'), 38.0)
    SFb = ('w', tuple(V(SF[1]) + (V(SF[2]) - V(SF[1])) * 0.15), SF[2], 45.0, 'w')
    TWC = ('p', macro(0.16), T0, 70.0, 'x')     # the pull: pad-locked, on the side away from the tweezer hand
    RETW = W_(('KW_RETP', '60.12,-0.66,1.71'), ('KW_RETT', '60.04,-0.47,1.62'), 85.0)
    # (frame, key, via)
    return [(0, M0, 0), (B0 - 4, M0b, 0), (B0 + 14, SIDE, 1), (B1, BEN_, 0), (C0 - 2, BENb, 0), (C0 + 16, SIDE_R, 1), (C1 + 6, M1, 0),
            (DV0, M1b, 0), (RS0 + 16, M1b, 0), (RS1, SF, 0), (PUSH0, SF, 0),
            (PUSH1, TWC, 0), (RET0, TWC, 0), (FN, M0, 0)]

def cam_fn(rt, t):
    import bpy
    f = t * FPS; bpy.context.view_layer.update(); Fm = ft.frame()
    Fc = Fm
    if f < BEND or f > FN - 1:     # opening rule (1): the camera holds still while the fingertip presses (the bend reads)
        b_ = 6.0 * math.sin(math.pi * f / BEND) if f < BEND else 0.0
        rg_ = rt.actors[ben].p.rig; Jm = rg_.matrix_world @ rg_.pose.bones['finger2-3.L'].matrix
        Fc = Jm @ Matrix.Rotation(math.radians(-b_), 4, 'X') @ Jm.inverted() @ Fm
    if DV0 <= f <= RS0 + 16:
        pl, tl, lens = _pview(f); up = (Fm.to_3x3() @ V((1, 0, 0))).normalized()
        return Fm @ pl, Fm @ tl, up, lens, 64.0, Fm @ tl
    ks = getattr(rt, '_ep10_keys', None)
    if ks is None: ks = rt._ep10_keys = _cam_keys()
    fr = [k[0] for k in ks]
    k1 = next((i for i, x in enumerate(fr) if x >= f), len(ks) - 1); k0 = max(0, k1 - 1)
    if f <= fr[0]: k0 = k1 = 0
    a_, b_ = k0, k1
    while a_ > 0 and ks[a_][2]: a_ -= 1
    while b_ < len(ks) - 1 and ks[b_][2]: b_ += 1
    T0_, T1_ = fr[a_], fr[b_]
    xx = ease((f - T0_) / max(1e-6, T1_ - T0_)) if b_ != a_ else 0.0; tt = T0_ + xx * (T1_ - T0_)
    i_ = a_
    while i_ < b_ - 1 and fr[i_ + 1] <= tt: i_ += 1
    s_ = min(1.0, max(0.0, (tt - fr[i_]) / max(1e-6, fr[min(b_, i_ + 1)] - fr[i_])))
    Q = [_key_world(ks[min(b_, max(a_, j))][1], Fc) for j in (i_ - 1, i_, i_ + 1, i_ + 2)]
    def cr(p0, p1, p2, p3, u):
        u2, u3 = u * u, u * u * u
        return 0.5 * ((2 * p1) + (-p0 + p2) * u + (2 * p0 - 5 * p1 + 4 * p2 - p3) * u2 + (-p0 + 3 * p1 - 3 * p2 + p3) * u3)
    if b_ - a_ <= 1:
        A_, B_ = Q[1], Q[2]; pos = A_[0].lerp(B_[0], s_); tgt = A_[1].lerp(B_[1], s_)
    else:
        pos = cr(*[q[0] for q in Q], s_); tgt = cr(*[q[1] for q in Q], s_)
    if PUSH0 < f < PUSH1:     # the push bows away from the tweezer hand (his right, -X) and below it: nothing nears the lens
        pos = pos + V(_wv('KW_PUSHOFF', '0.30,-0.10,-0.15')) * math.sin(math.pi * s_)
    lens = Q[1][2] + (Q[2][2] - Q[1][2]) * s_
    up = Q[1][3].lerp(Q[2][3], s_).normalized()
    d_ = (tgt - pos).length
    fstop = 64.0 if d_ < 0.3 else 8.0
    if PUSH0 <= f <= FN - 12 and d_ < 0.3: fstop = 220.0     # the pull close: deep focus so the near labels (10 cm) stay sharp
    return pos, tgt, up, lens, fstop, tgt
ep.cam_fn = cam_fn

# ---- labels + sounds ---------------------------------------------------------------------------------------------------
YL = dict(color='yellow', size=1.2); Y = 0.86
CUTK = lambda w: [(0.0, {'pos': (0.31, Y), 'width': w})]     # lead CHECK 1 #1: inside the cut-away the labels sit over the fat layer, clear of the wood
ep.label_outline = True                                        # lead CHECK 1 #2: dark outline + soft drop shadow on every label
labels = [KW.fx.label('RED + SWOLLEN', at=f_red * F, pos=(0.5, Y), dur=(DV0 - 4 - f_red) * F, **YL),
          KW.fx.label('WHITE BLOOD CELLS', at=f_white * F, pos=(0.5, Y), dur=(f_L3 - 8 - f_white) * F, keys=CUTK(520), **YL),
          KW.fx.label('PUS', at=f_pus * F, pos=(0.5, Y), dur=(f_L4 - 8 - f_pus) * F, keys=CUTK(420), **YL),
          KW.fx.label('PUSHED OUT', at=f_out * F, pos=(0.5, Y), dur=(f_L5 - 4 - f_out) * F, keys=CUTK(520), **YL),
          KW.fx.label('WALLED OFF', at=f_walls * F, pos=(0.5, Y), dur=(RS0 + 4 - f_walls) * F, keys=CUTK(520), **YL),
          KW.fx.label('SAME ANGLE', at=f_same * F, pos=(0.5, Y), dur=(RET0 - f_same) * F, keys=[(0.0, {'width': 760})], **YL),
          KW.fx.label('WHAT YOUR BODY DOES', at=-1.0, pos=(0.5, Y), dur=1.0 + (B0 - 2) * F, **YL),     # opening rule (3): the title promise on frame 0
          KW.fx.label('PULL IT OUT OR WAIT?', at=CTA0 * F, pos=(0.5, 0.62), dur=(FN - 10 - CTA0) * F, color='white', size=0.9),     # lead: end CTA, caption style
          KW.fx.label('COMMENT BELOW', at=(CTA0 + 3) * F, pos=(0.5, 0.575), dur=(FN - 13 - CTA0) * F, color='white', size=0.125),
          KW.fx.label('WHAT YOUR BODY DOES', at=(FN - 9) * F, pos=(0.5, Y), dur=2.0, **YL)]                  # ... and back on for the loop (fN = f0)
labels[-1].o['nopop'] = True     # final_scan: the pop overshoot took this wide word to 40 px margins at f703; eased in, it stays 860 px
ep.sound(0.0, 'thud', 0.8)
ep.sound(f_red * F, 'thud', 0.6)
for f_ in (f_pus, f_out, f_walls, f_same): ep.sound(f_ * F, 'thud', 0.5)
ep.sound(GR1 * F, 'thud', 0.3)                                # tap: the tweezers close
TICK_F = [int(os.environ.get('KW_TICK%d' % i, d)) for i, d in enumerate((f_white + 20, f_white + 38, f_white + 57))]
for f_ in TICK_F: ep.sound(f_ * F, 'tick', 0.3)

MX = float(os.environ.get('KW_MEXP', -0.6)); MXI = float(os.environ.get('KW_IEXP', -1.6))   # inside: the block lights sit 5 cm away       # the macro is lit ~0.6 stop hotter than the Ben views (same studio rig, 7 cm away)
ep.exposure_keys = [(f_ * F, v_) for f_, v_ in ((0, MX), (B0 - 4, MX), (B1, 0.0), (C0, 0.0), (C1 + 6, MX), (DV0 + 4, MX), (DV1, MXI),
                                                 (RS0, MXI), (RS0 + 16, MX), (RS1, 0.0), (RET0, 0.0), (FN, MX))]
ep.label_dk = lambda f: 0.012 if DV0 + 6 <= f <= RS0 + 16 else (0.10 if PUSH1 - 4 <= f <= FN - 12 else None)     # labels in front of the cut-away tissue
ep.label_maxw = 880.0   # lead CHECK 1 #3: >= 67 px margins each side incl. the 6 px outline
ep.label_lens_fix = True; ep.relight_after_pose = True
ep.mouth_fix = True
ep.eyes_fix = True                                             # N6 (opt-in): wet catch-light, iris depth, lower-lid line (heads_hg)
ep.shot(0.0, 'finger', set='studio', world='sky', cast={ben: P}, fx=labels, cam=KW.cam.face(ben))
ep.run()
