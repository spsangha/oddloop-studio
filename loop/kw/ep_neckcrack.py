"""Kinda Wild Films ep19 - 'He Cracked His Neck And Ended Up In Hospital'  Brief: kindawild/19_neck_crack/brief.md.
Facts: The Washington Post (via Boston.com) + NBC News, May 2019 (28-year-old man stretched his sore neck with his hand, heard a
pop; left side numb, tilting to the left; a small tear in a vertebral artery formed a clot -> stroke; 12 minutes to give tPA;
walking again within weeks; stroke neurologist: "99.9 percent of the time you pop your neck and it's fine").
Ben at home (room set), then on the clinic bed with Howard (doctor) and the scan screen, then home again for the payoff/loop.
Body changes on Ben's own mesh: a cool grey numb tint over his LEFT side (<= 28 %, lips kept natural), his head tipped hard to his
left, a red artery line + dark clot spot on the side of his neck (<= 28 %).  Scan cards: kwneckcard_gen.py (PIL, no AI).
Ladder rung 9: fingernails + knuckle creases in the close of his hand on his neck (nail tint + gloss on Ben's own mesh).
"""
import sys, os, math; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kwkit as KW
os.environ.setdefault('KW_LIGHT', '1')
HERE = os.path.dirname(os.path.abspath(__file__))
T0 = [None, 3.5, 6.45, 9.6, 12.82, 17.49, 20.76]    # pinned to the 26 Nov render so a line-1 rewrite only touches the hook shards
ep = KW.Episode('ep_neckcrack', injury="cracked his sore neck",
                voice_lines=list(zip(T0, [l.strip() for l in open(os.path.join(HERE, 'ep_neckcrack.txt')) if l.strip()])),
                music='sneaky_snitch', gap=0.6)
ep.tts_say = {6: "Weeks later, he was walking again, and a stroke doctor says ninety-nine point nine percent of neck pops are fine."}
ben = ep.person('Ben', 'civilian', 'eatmore-ben', gender='m', age='young', race='caucasian', hair='short02', tee='teal')
doc = ep.person('Howard', 'scientist', 'eatmore-sci', gender='m', age='old', race='caucasian', hair='short02')

FPS = 24; F = 1.0 / FPS
try: from mathutils import Vector as V
except ImportError: V = None
def ease(x): x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)
R = {}
OV = float(os.environ.get('KW19_OV', 0.28)); OVN = 0.45   # numb: 45 % on arms/neck, 28 % on the face            # colour overlays (<= 0.30 lead rule)
FORCE = os.environ.get('KW19_FORCE')                   # probe: force numb / artery / tilt to this value
NAIL = float(os.environ.get('KW19_NAIL', 0.22))        # rung 9: nail plate tint

KW.FACES.update({
    'stretch': {'squint': 0.55, 'x_pain': 0.25},
    'pop': {'x_surprise': 0.9, 'squint': 0.2},
    'numb': {'worry': 0.85, 'x_fear': 0.35},
    'scared': {'x_fear': 0.55, 'worry': 0.4},
    'hope': {'worry': 0.35, 'smile': 0.2},
    'easy': {'smile': 0.6},
})
ep.waive = {"1 shots;": "brief: three kit shots (home / clinic / home); the hard cuts live in ep.cam_fn",
            "3 shots;": "brief: three kit shots (home / clinic / home); the hard cuts live in ep.cam_fn",
            "last shot must use cam=KW.cam.loop()": "brief: cam_fn cuts back to the frame-0 framing for the last 9 frames (the loop)",
            "HOOK cut <= 200 ms after the last word": "brief: CTA over the payoff shot, then the frame-0 cut",
            "shot home holds": "brief: cuts inside cam_fn", "shot clinic holds": "brief: cuts inside cam_fn",
            "shot home2 holds": "brief: cuts inside cam_fn",
            "HOOK first shot": "brief: hook cuts f22 (hand on neck) and f46 (face close) live in cam_fn",
            "HOOK >= 2 cuts": "brief: hook cuts f22 and f46 live in cam_fn",
            "HOOK inside the body": "brief: vidIQ rule 1 person -> cutaway -> close-up; the scan comes later",
            "HOOK 3rd shot": "brief: third hook shot (face close) at f46 in cam_fn"}
fw = lambda i, w: int(round(ep.word(i, w) * FPS))
fl = lambda i: int(round(ep.line(i) * FPS))
fle = lambda i: int(round((ep.line(i) + ep.vo_dur[i]) * FPS))
f_last = fle(6); FN = max(f_last + 34, 700); NF = FN + 1; ep.duration = round(NF / FPS, 4)
CTA0 = FN - 44; LOOPF = FN - 9
FPOP = fw(0, 'pop.')
FH = fl(3) - 4                                      # clinic from here
FP = fl(6) - 4                                      # home again: walking (payoff), CTA, loop
FTORN = fw(4, 'torn')                               # consequence (50-60 %): the torn artery + clot
FDRUG = fw(5, 'drug.')
CUTS = [(0, 'MED0'), (22, 'HAND'), (46, 'CLOSE'), (fl(1) - 4, 'HALF'), (fl(2) - 4, 'WIDE'),
        (FH, 'TWO'), (fl(4) - 4, 'NECK'), (fw(4, 'clot') - 3, 'SCR'), (fl(5) - 4, 'FACE'), (FDRUG - 2, 'SCR'),
        (FP, 'MED1'), (LOOPF, 'MED0')]
def shot_of(f):
    cur = CUTS[0]
    for c in CUTS:
        if f >= c[0]: cur = c
    nxt = next((c[0] for c in CUTS if c[0] > cur[0]), FN + 1)
    return cur[1], (f - cur[0]) / max(1, nxt - cur[0])
def keys(f, ks):
    if f <= ks[0][0]: return ks[0][1]
    for (f0, v0), (f1, v1) in zip(ks, ks[1:]):
        if f0 <= f <= f1: return v0 + (v1 - v0) * ease((f - f0) / max(1e-6, f1 - f0))
    return ks[-1][1]
def v_numb(f):
    if f >= FP: return 0.0
    return keys(f, [(fw(1, 'numb.') - 6, 0.0), (fw(1, 'numb.') + 6, 1.0), (FDRUG, 1.0), (FP - 4, 0.45)])
def v_tilt(f): return keys(f, [(fw(2, 'tilting') - 6, 0.0), (fw(2, 'tilting') + 8, 1.0)]) if f < FH else 0.0
def v_art(f): return keys(f, [(FTORN - 4, 0.0), (FTORN + 4, 1.0)]) if FH <= f < FP else 0.0
def card_of(f): return 0 if f < fw(4, 'clot') - 3 else (1 if f < FDRUG - 2 else 2)

NECKP = 'neck_l'                                    # his left hand on the left side of his neck, head tipped to his right
STR = 'clutch_neck'                                 # kit hand pose: palm on the side of the neck
PH = (KW.pose('stand', at='stand', left=STR, face='stretch', head=(-4, 0, 14), blend=5 * F)
      .then((FPOP - 3) * F, face='pop', head=(0, 0, -4), act=KW.act.wince(at=FPOP * F), blend=3 * F)
      .then((FPOP + 12) * F, left='rest', blend=14 * F)
      .then((fl(1) - 2) * F, face='numb', head=(4, 0, 0), blend=8 * F)
      .then((fw(2, 'tilting') - 6) * F, face='scared', head=(2, 0, -18), lean=6.0, blend=12 * F))   # head tipped hard to his left (kit head tilt; - = his left)
PC = (KW.pose('sit', at='bed_sit', face='scared', blend=5 * F)
      .then((FTORN - FH) * F, face='numb', blend=8 * F)
      .then((FDRUG - FH) * F, face='hope', blend=10 * F))
PD = (KW.pose('stand', at='bedside_l', face='focus', blend=5 * F)
      .then((fl(5) - FH) * F, face={'focus': 0.8}, blend=8 * F))
PL = (KW.pose('stand', at='stand', face='easy', head=(0, 0, 0), blend=5 * F)
      .then((LOOPF - 14 - FP) * F, left=STR, face='stretch', head=(-4, 0, 14), blend=12 * F))
ep.blinks = {'Ben': [70, 150, 250, 370, 470, 560, 640], 'Howard': [300, 420, 520]}

# ------------------------------------------------------------------ clinic screen (same mount as ep14-ep18)
SCR_C = (-0.10, 0.17, 2.05); SCR_W, SCR_H = 0.46, 0.2875
def build_screen(c):
    import bpy, kwlib as L
    tex = os.path.join(HERE, '..', '..', 'assets', 'real', 'tex', 'kw_neck')
    m = bpy.data.materials.new('kw19_screen'); m.use_nodes = True; nt = m.node_tree; N = nt.nodes; N.clear(); Lk = nt.links.new
    out = N.new('ShaderNodeOutputMaterial'); em = N.new('ShaderNodeEmission'); uv = N.new('ShaderNodeTexCoord')
    def img(nm):
        n = N.new('ShaderNodeTexImage'); n.image = bpy.data.images.load(os.path.join(tex, nm + '.png'), check_existing=True)
        n.interpolation = 'Cubic'; Lk(uv.outputs['UV'], n.inputs['Vector']); return n
    iA, iB = img('clot'), img('open'); mb = N.new('ShaderNodeValue')
    x = N.new('ShaderNodeMix'); x.data_type = 'RGBA'; Lk(mb.outputs[0], x.inputs['Factor']); Lk(iA.outputs['Color'], x.inputs['A']); Lk(iB.outputs['Color'], x.inputs['B'])
    Lk(x.outputs['Result'], em.inputs['Color']); em.inputs['Strength'].default_value = float(os.environ.get('KW_SCRE', 1.4)); Lk(em.outputs[0], out.inputs[0])
    R['scr'] = mb; R['scre'] = em
    cx, cy, cz = SCR_C; tilt = math.radians(-8)
    dark = L.mat('kw19_bezel', (0.035, 0.038, 0.042), 0.35, 0.2); steel = L.mat('kw19_steel', (0.72, 0.73, 0.75), 0.3, 1.0)
    L.box('kw19_bezel', (SCR_W + 0.024, 0.03, SCR_H + 0.024), (cx, cy + 0.016, cz), dark, c, 0.008, (math.degrees(tilt), 0, 0))
    bpy.ops.mesh.primitive_plane_add(size=1.0); pl = bpy.context.active_object; pl.name = 'kw19_panel'
    for u_ in list(pl.users_collection): u_.objects.unlink(pl)
    c.objects.link(pl); pl.scale = (SCR_W, SCR_H, 1); pl.rotation_euler = (math.radians(90) + tilt, 0, 0); pl.location = (cx, cy - 0.0005, cz)
    pl.data.materials.append(m)
    for a in ('visible_diffuse', 'visible_glossy', 'visible_transmission'): setattr(pl, a, a == 'visible_glossy')
    L.cyl('kw19_boom', 0.016, 2.80 - cz, (cx, cy + 0.06, (2.80 + cz) / 2), steel, c, (0, 0, 0), 20)
    L.box('kw19_mount', (0.12, 0.04, 0.08), (cx, cy + 0.045, cz), dark, c, 0.005)
    R['scrobj'] = [o for o in c.objects if o.name.startswith('kw19_')]

# ------------------------------------------------------------------ Ben's own mesh: numb left side, artery + clot, nails
def body_keys(hg):
    """vertex colour kw19g on Ben's HG_Body: R = his left side (x > 0, lips/mouth excluded), G = artery line on the left side of
    the neck, B = clot spot on it, A = nail plates (rung 9).  Mixed into the skin base colour at <= OV (nails: NAIL + gloss)."""
    import numpy as np, bpy
    body = next(o for o in hg.meshes if o.name.startswith('HG_Body'))
    n = len(body.data.vertices); c = np.empty(n * 3); body.data.vertices.foreach_get('co', c); c = c.reshape(-1, 3)
    B2M = np.array(body.matrix_world.inverted() @ hg.rig.matrix_world)
    bone = lambda nm: B2M[:3, :3] @ np.array(hg.rig.data.bones[nm].head_local) + B2M[:3, 3]
    tail = lambda nm: B2M[:3, :3] @ np.array(hg.rig.data.bones[nm].tail_local) + B2M[:3, 3]
    E = (bone('eyeball.L') + bone('eyeball.R')) / 2
    d = c - E
    nrm = np.empty(n * 3); body.data.vertices.foreach_get('normal', nrm); nrm = nrm.reshape(-1, 3)
    left = np.clip((d[:, 0] - 0.004) / 0.018, 0, 1)                     # his left = +X (faces -Y)
    mouth = E + np.array([0.0, -0.075, -0.075])
    lips = np.exp(-np.sum((c - mouth) ** 2, axis=1) / (2 * 0.022 ** 2))
    numb = left * (1 - np.clip(lips * 1.6, 0, 1)) * np.where(d[:, 2] > -0.12, 0.62, 1.0)   # face 0.62 x 0.45 = 28 %
    # artery: a line on the left side of the neck, from above the collarbone up to below the ear
    p0 = E + np.array([0.0, 0.060, -0.215]); p1 = E + np.array([0.0, 0.055, -0.085])     # a line in the side view (y, z)
    seg = p1 - p0; seg[0] = 0; cc = c.copy(); cc[:, 0] = p0[0]
    u = np.clip(((cc - p0) @ seg) / (seg @ seg), 0, 1); q = p0 + u[:, None] * seg
    dist = np.linalg.norm(cc - q, axis=1); side = (d[:, 0] > 0.03) & (nrm[:, 0] > 0.45) & (d[:, 2] < -0.07) & (d[:, 2] > -0.24)
    art = np.exp(-dist ** 2 / (2 * 0.0065 ** 2)) * side
    pc = p0 + 0.55 * seg; clot = np.exp(-np.sum((cc - pc) ** 2, axis=1) / (2 * 0.009 ** 2)) * side
    # nails: the bone sits nearer the BACK of the fingertip than the pad, so the dorsal side = the candidate bone axis (+-x, +-z)
    # with the smallest skin distance; nail plate = skin on that side over the outer 55 % of the distal bone
    nail = np.zeros(n); names = [b.name for b in hg.rig.data.bones]
    dist_b = [nm for nm in names if nm.split('.')[0] in ('f_index', 'f_middle', 'f_ring', 'f_pinky', 'thumb') and '.03.' in nm and 'ORG' not in nm and 'DEF' not in nm]
    for nm in dist_b:
        b = hg.rig.data.bones[nm]; h, t = bone(nm), tail(nm); L_ = max(1e-6, np.linalg.norm(t - h)); ax = (t - h) / L_
        pr = (c - h) @ ax / L_; rad = (c - h) - np.outer(pr * L_, ax); rr = np.linalg.norm(rad, axis=1)
        sel = (pr > 0.2) & (pr < 1.15) & (rr < 0.014)
        if sel.sum() < 10: continue
        best = None
        for vec in (b.x_axis, b.z_axis):
            for sg in (1, -1):
                dv = B2M[:3, :3] @ (sg * np.array(vec)); dv /= max(1e-6, np.linalg.norm(dv))
                m_ = sel & ((rad @ dv) > 0.85 * rr)
                if m_.sum() < 3: continue
                md = float(rr[m_].mean())
                if best is None or md < best[0]: best = (md, dv)
        if best is None: continue
        dv = best[1]; cosv = (rad @ dv) / np.maximum(rr, 1e-6)
        w = np.clip((cosv - 0.45) / 0.3, 0, 1) * np.clip((pr - 0.42) / 0.12, 0, 1) * (pr < 1.12) * (rr < 0.013)
        nail = np.maximum(nail, w)
    print('kw19 masks numb', int((numb > 0.5).sum()), 'art', int((art > 0.3).sum()), 'clot', int((clot > 0.3).sum()),
          'nail', int((nail > 0.3).sum()), 'distal bones', dist_b[:12])
    ca = body.data.color_attributes.get('kw19g') or body.data.color_attributes.new('kw19g', 'FLOAT_COLOR', 'POINT')
    ca.data.foreach_set('color', np.stack([numb, art, clot, nail], 1).astype(np.float32).ravel())
    vn, va, vc = [], [], []
    for mt in body.data.materials:
        if not mt or not mt.use_nodes or not mt.name.startswith('.Human'): continue
        N = mt.node_tree.nodes; Lk = mt.node_tree.links.new
        bs = next(q_ for q_ in N if q_.bl_idname == 'ShaderNodeBsdfPrincipled'); bc = bs.inputs['Base Color']
        if not bc.is_linked: continue
        at = N.new('ShaderNodeAttribute'); at.attribute_name = 'kw19g'; sp = N.new('ShaderNodeSeparateColor'); Lk(at.outputs['Color'], sp.inputs[0])
        cur = bc.links[0].from_socket
        def mix(fac_sock, col, lst=None, const=None):
            nonlocal cur
            m1 = N.new('ShaderNodeMath'); m1.operation = 'MULTIPLY'; Lk(fac_sock, m1.inputs[0])
            if lst is not None: a = N.new('ShaderNodeValue'); a.outputs[0].default_value = 0.0; lst.append(a); Lk(a.outputs[0], m1.inputs[1])
            else: m1.inputs[1].default_value = const
            mx = N.new('ShaderNodeMix'); mx.data_type = 'RGBA'; Lk(m1.outputs[0], mx.inputs['Factor']); Lk(cur, mx.inputs['A'])
            mx.inputs['B'].default_value = col; cur = mx.outputs['Result']
        mix(sp.outputs[0], (0.42, 0.50, 0.68, 1.0), vn)                  # numb: cool grey
        mix(sp.outputs[1], (0.70, 0.05, 0.06, 1.0), va)                  # artery: red line
        mix(sp.outputs[2], (0.22, 0.02, 0.04, 1.0), vc)                  # clot: dark spot
        mix(at.outputs['Alpha'], (0.93, 0.82, 0.80, 1.0), const=NAIL)    # nail plate: paler pink
        Lk(cur, bc)
        ri = bs.inputs['Roughness']; mr = N.new('ShaderNodeMath'); mr.operation = 'MULTIPLY'
        if ri.is_linked: Lk(ri.links[0].from_socket, mr.inputs[0])
        else: mr.inputs[0].default_value = ri.default_value
        inv = N.new('ShaderNodeMath'); inv.operation = 'MULTIPLY_ADD'; Lk(at.outputs['Alpha'], inv.inputs[0]); inv.inputs[1].default_value = -0.6; inv.inputs[2].default_value = 1.0
        Lk(inv.outputs[0], mr.inputs[1]); Lk(mr.outputs[0], ri)              # nails 60 % glossier
    R['ov'] = (vn, va, vc); print('kw19 overlay nodes', len(vn)); R['body'] = body

def build(rt):
    import bpy
    c = bpy.data.collections.get('kw_ep19') or bpy.data.collections.new('kw_ep19')
    if c.name not in bpy.context.scene.collection.children: bpy.context.scene.collection.children.link(c)
    import kwlook as Q_; Q_.LOOP_T = FN / FPS
    build_screen(c); body_keys(rt.actors[ben].p.hg)
ep.build_hook = build

def eyes(rt, who):
    rg = rt.actors[who].p.hg.rig; W_ = rg.matrix_world
    EL = W_ @ rg.pose.bones['eyeball.L'].head; ER = W_ @ rg.pose.bones['eyeball.R'].head; return EL, ER, (EL + ER) / 2

def frame_hook(rt, t):
    import bpy, kwlook as Q_
    Q_.LOOP_T = FN / FPS
    f = t * FPS; hb = rt.actors[ben].p.hg
    fv = float(FORCE) if FORCE is not None else None
    nv = fv if fv is not None else v_numb(f); av = fv if fv is not None else v_art(f)
    if f >= LOOPF: nv = av = 0.0
    vn, va, vc = R['ov']
    for n_ in vn: n_.outputs[0].default_value = OVN * nv
    for n_ in va: n_.outputs[0].default_value = OV * av
    for n_ in vc: n_.outputs[0].default_value = 0.30 * av
    clinic = FH <= f < FP
    R['scr'].outputs[0].default_value = 1.0 if card_of(f) >= 2 else 0.0
    R['scre'].inputs['Strength'].default_value = float(os.environ.get('KW_SCRE', 1.4)) if (clinic and card_of(f) >= 1) else 0.03
    for o in R['scrobj']: o.hide_render = not clinic
    bpy.context.view_layer.update()
    if clinic:
        _, _, EB = eyes(rt, ben); _, _, ED = eyes(rt, doc)
        rt.eyes_at(rt.actors[doc], EB)
        if f < fl(4) - 6: rt.eyes_at(rt.actors[ben], ED)
    sh_ = rt.ep.shot_at(t); rt.FX.update(sh_, t - sh_.t, t)
ep.frame_hook = frame_hook


def look(tg, dirv, dist, lens, fst=8.0, foc=None):
    dv = V(dirv).normalized(); return tg + dv * dist, tg, V((0, 0, 1)), lens, fst, (foc if foc is not None else tg)
def cam_fn(rt, t):
    import bpy
    f = t * FPS; bpy.context.view_layer.update(); shot, u = shot_of(f)
    _, _, EB = eyes(rt, ben)
    push = lambda a, b: a * (b / a) ** ease(u)
    if shot in ('MED0', 'MED1'):
        tg = EB + V((0.0, 0.0, -0.20)); d_ = push(1.30, 1.18) if shot == 'MED0' and f < LOOPF else (push(1.25, 1.12) if shot == 'MED1' else 1.30)
        return look(tg, (-0.55, -1.0, 0.05), d_, 50.0, 8.0, EB)
    if shot == 'HAND':                                             # his right hand on his neck (nails + knuckles, rung 9)
        tg = EB + V((0.07, 0.0, -0.12)); return look(tg, (1.0, -0.60, 0.10), push(0.80, 0.70), 85.0, 11.0, tg)
    if shot == 'CLOSE':
        tg = EB + V((0, 0, -0.05)); return look(tg, (-0.30, -1.0, 0.02), push(0.55, 0.46), 85.0, 11.0, EB)
    if shot == 'HALF':                                             # front: the numb grey creeps over his left side
        tg = EB + V((0.10, 0.0, -0.26)); return look(tg, (0.35, -1.0, 0.04), push(1.25, 1.12), 50.0, 8.0, EB)
    if shot == 'WIDE':                                             # upper body: head tipped hard to his left
        tg = EB + V((0.0, 0.0, -0.28)); return look(tg, (0.10, -1.0, 0.04), push(1.60, 1.42), 50.0, 8.0, EB)
    _, _, ED = eyes(rt, doc)
    if shot == 'TWO':
        mid = EB.lerp(ED, 0.5) + V((0, 0, -0.15)); bm = (ED - EB); bm.z = 0; bm.normalize(); side = V((0, 0, 1)).cross(bm).normalized()
        if side.y > 0: side = -side
        return look(mid, side * 1.0 + V((0, 0, 0.08)), push(1.80, 1.62), 50.0, 8.0, mid)
    if shot == 'NECK':                                             # the left side of his neck: artery line + clot
        tg = EB + V((0.05, 0.05, -0.14)); return look(tg, (1.0, -0.05, 0.08), push(0.55, 0.48), 70.0, 11.0, tg)
    if shot == 'FACE':
        tg = EB + V((0, 0, -0.04)); return look(tg, (-0.45, -1.0, 0.02), push(0.55, 0.46), 85.0, 11.0, EB)
    tg = V(SCR_C) + V((0, 0, -0.15))                                 # SCR: screen + Ben below it
    return look(tg, (0.06, -1.0, 0.25), push(1.55, 1.45), 50.0, 8.0, V(SCR_C))
ep.cam_fn = cam_fn

YL = dict(color='yellow', size=1.2); Y = 0.89
ep.label_outline = True; ep.label_maxw = 820.0; ep.label_lens_fix = True
def lab(txt, f0, f1, **k): return KW.fx.label(txt, at=f0 * F, pos=(0.5, Y), dur=(f1 - f0) * F, **(k or YL))
wd = fw
labels = [KW.fx.label('CRACKED', at=-1.0, pos=(0.5, Y), dur=1.0 + (FPOP - 2) * F, **YL),
          lab('POP', FPOP, fl(1) - 6),
          lab('NUMB', wd(1, 'numb.'), fl(2) - 6),
          lab('TILTING', wd(2, 'tilting'), fl(3) - 6),
          lab('STROKE', wd(3, 'stroke.'), fl(4) - 6),
          lab('TORN', FTORN, wd(4, 'clot') - 1),
          lab('CLOT', wd(4, 'clot'), fl(5) - 6),
          lab('12 MIN', wd(5, 'twelve'), FDRUG - 1),
          lab('DRUG', FDRUG, fl(6) - 6),
          lab('WALKING', wd(6, 'walking'), CTA0 - 2),
          KW.fx.label('CRACK IT?', at=CTA0 * F, pos=(0.5, 0.30), dur=(LOOPF - 1 - CTA0) * F, **YL),
          KW.fx.label('COMMENT BELOW', at=(CTA0 + 3) * F, pos=(0.5, 0.235), dur=(LOOPF - 4 - CTA0) * F, color='white', size=0.5),
          KW.fx.label('CRACKED', at=LOOPF * F, pos=(0.5, Y), dur=2.0, **YL)]
labels[-1].o['nopop'] = True
fxs = [KW.fx.crackle(ben.part(NECKP), times=(FPOP * F,))]
ep.sound(0.0, 'thud', 0.6)
for f_ in (wd(1, 'numb.'), wd(2, 'tilting'), wd(3, 'stroke.'), FTORN, FDRUG): ep.sound(f_ * F, 'thud', 0.45)
ep.mouth_fix = True; ep.eyes_fix = True; ep.relight_after_pose = True
def part(a, b):           # labels are shot-local: split them by start and shift
    out = []
    for lb in labels:
        at = lb.o.get('at', 0)
        if a * F - 1e-6 <= at < b * F - 1e-6 or (a == 0 and at < 0): lb.o['at'] = at - a * F if a else at; out.append(lb)
    return out
LH, LC, LP = part(0, FH), part(FH, FP), part(FP, FN + 99)
ep.shot(0.0, 'home', set='room', cast={ben: PH}, fx=LH + fxs, cam=KW.cam.face(ben))
ep.shot(FH * F, 'clinic', set='hospital', cast={ben: PC, doc: PD}, fx=LC, cam=KW.cam.face(ben))
ep.shot(FP * F, 'home2', set='room', cast={ben: PL}, fx=LP, cam=KW.cam.face(ben))
ep.run()
