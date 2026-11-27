"""Kinda Wild Films ep16 - 'He Yawned So Hard His Jaw Locked Open'  Brief: kindawild/16_yawn_jaw/brief.md.
Facts: Thangarajah et al., J Med Case Reports 2010;4:263 (29-year-old man, bilateral TMJ dislocation after a yawn) +
Cleveland Clinic 'Dislocated Jaw' (fist under the chin when you yawn).
Ben (patient) on the clinic bed, Howard (doctor, lab coat) at the bedside.  Body changes on Ben's own mesh: jaw locked wide
and pushed forward, a drool strand from the lower lip, dents in front of both ears (where the joint left its socket, soft red
<= 25 %), clenched chewing muscles (small bulge + soft red <= 25 %).  The clinic screen shows a simple side-view X-ray drawing
of the joint: out of its socket, then back in (kwjawcard_gen.py).  Ladder rung 2: teeth, dark inside and tongue on the open mouth.
"""
import sys, os, math; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kwkit as KW
os.environ.setdefault('KW_LIGHT', '1')
HERE = os.path.dirname(os.path.abspath(__file__))
ep = KW.Episode('ep_yawnjaw', injury="jaw locked",
                voice_lines=[l.strip() for l in open(os.path.join(HERE, 'ep_yawnjaw.txt')) if l.strip()],
                music='sneaky_snitch', gap=0.6)
ep.tts_say = {3: "In the E.R., doctors sedated him and pushed twice, but it wouldn't budge."}
ben = ep.person('Ben', 'civilian', 'eatmore-ben', gender='m', age='young', race='caucasian', hair='short02', tee='teal')
doc = ep.person('Howard', 'scientist', 'eatmore-sci', gender='m', age='old', race='caucasian', hair='short02')

FPS = 24; F = 1.0 / FPS
try: from mathutils import Vector as V
except ImportError: V = None
def ease(x): x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)
R = {}
GLOW = float(os.environ.get('KW16_GLOW', 0.28))       # red on dents / chewing muscles (<= 0.30, lead rule)
FORCE = os.environ.get('KW16_FORCE')                  # probe: force dents/drool/clench to this value

# faces: the locked jaw = widest calibrated gap + jaw pushed forward (an ARKit key added to the HG face table in Blender)
KW.FACES.update({
    'yawn': {'x_gap': 30.0, 'x_lips': 0.5, 'squint': 0.7, 'worry': 0.2},
    'locked': {'x_gap': 33.0, 'x_lips': 0.6, 'x_fwd': 1.0, 'worry': 0.8, 'wide': 0.4},
    'lockpain': {'x_gap': 33.0, 'x_lips': 0.6, 'x_fwd': 1.0, 'x_pain': 0.6},
    'locksleep': {'x_gap': 33.0, 'x_lips': 0.5, 'x_fwd': 1.0, 'blink': 1.0},
    'closesleep': {'blink': 1.0},
})
try:
    import bpy  # noqa: F401  (Blender only)
    import heads_hg as HH
    HH.ARK['x_fwd'] = {'jawForward': 0.9}
    HH.ARK_NAMES = sorted({k for d in HH.ARK.values() for k in d})
except ImportError:
    pass

ep.waive = {"1 shots;": "brief: one kit shot; the hard cuts (medium -> side -> close ...) live in ep.cam_fn",
            "last shot must use cam=KW.cam.loop()": "brief: cam_fn cuts back to the frame-0 framing for the last 9 frames (the loop)",
            "HOOK cut <= 200 ms after the last word": "brief: CTA over the payoff shot, then the frame-0 cut",
            "shot face holds": "brief: cuts every 1.1-4 s inside cam_fn"}
fw = lambda i, w: int(round(ep.word(i, w) * FPS))
fl = lambda i: int(round(ep.line(i) * FPS))
fle = lambda i: int(round((ep.line(i) + ep.vo_dur[i]) * FPS))
f_last = fle(6); FN = max(f_last + 30, 680); NF = FN + 1; ep.duration = round(NF / FPS, 4)
CTA0 = FN - 40
FLK = fw(0, 'locked')                     # the lock
FPU1, FPU2 = fw(3, 'pushed'), fw(3, 'twice,')     # consequence (50-60 %): two pushes fail
FCL = fw(4, 'clenched.')
FBK = fw(5, 'jaw')                        # under anaesthesia the jaw slides back in
FFI = fw(6, 'fist')
CUTS = [(0, 'MED0'), (22, 'SIDE'), (46, 'CLOSE'), (fw(1, 'drooling,') - 3, 'MOUTH'), (fw(1, 'spots') - 3, 'SIDE2'),
        (fl(2) - 4, 'SCR'), (fl(3) - 4, 'TWO'), (fl(4) - 4, 'PAIN'), (fl(5) - 4, 'SLEEP'), (fw(5, 'back') - 1, 'SCR2'),
        (fl(6) - 4, 'MED1'), (FN - 9, 'MED0')]
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
# body-change curves (0..1)
def v_drool(f): return keys(f, [(fw(1, 'drooling,') - 2, 0.0), (fw(1, 'drooling,') + 14, 1.0), (FBK, 1.0), (FBK + 8, 0.0)])
def v_dent(f): return keys(f, [(fw(1, 'ears') - 4, 0.0), (fw(1, 'ears') + 6, 1.0), (FBK, 1.0), (FBK + 10, 0.0)])
def v_clench(f): return keys(f, [(FCL - 4, 0.0), (FCL + 6, 1.0), (fl(5) + 8, 1.0), (fl(5) + 30, 0.0)])

# Ben: calm at frame 0 and the loop; yawn -> locked -> pain on the pushes -> asleep, jaw back -> fist under the chin
PB = (KW.pose('sit', at='bed_sit', face={'worry': 0.25}, blend=5 * F)
      .then(2 * F, face='yawn', head=(-8, 0, 0), blend=24 * F)
      .then((FLK - 3) * F, face='locked', head=(0, 0, 0), blend=5 * F)
      .then((FPU1 - 2) * F, face='lockpain', act=KW.act.wince(at=FPU1 * F), blend=3 * F)
      .then((FPU1 + 5) * F, face='locked', blend=4 * F)
      .then((FPU2 - 2) * F, face='lockpain', act=KW.act.wince(at=FPU2 * F), blend=3 * F)
      .then((FPU2 + 8) * F, face='locked', blend=5 * F)
      .then((FCL - 4) * F, face='lockpain', blend=6 * F)
      .then((fl(5) - 4) * F, face='locksleep', head=(6, 0, 0), blend=6 * F)
      .then(FBK * F, face='closesleep', blend=10 * F)
      .then((fl(6) - 4) * F, face={'relief': 0.5}, head=(0, 0, 0), blend=6 * F)
      .then((FFI - 10) * F, right=KW.hand.touch(ben, 'throat', shape='fist'), face={'smile': 0.3}, blend=10 * F)
      .then((FN - 22) * F, right='rest', face={'worry': 0.25}, blend=12 * F))
PD = (KW.pose('stand', at='bedside_l', face='focus', blend=5 * F)
      .then((fl(3) - 2) * F, right=KW.hand.touch(ben, 'chin', shape='open', pulses=((FPU1 - fl(3) + 2) * F, (FPU2 - fl(3) + 2) * F)),
            face={'focus': 0.8}, blend=8 * F)
      .then((fl(4) + 6) * F, right='rest', face={'worry': 0.5}, blend=10 * F)
      .then((FFI - 10) * F, face='calm', blend=8 * F))
ep.blinks = {'Ben': [100, 190, 296, 400, 600], 'Howard': [120, 260, 380, 520, 640]}

# ------------------------------------------------------------------ screen (same mount as ep14/ep15)
SCR_C = (-0.10, 0.17, 2.05); SCR_W, SCR_H = 0.46, 0.2875
def build_screen(c):
    import bpy, kwlib as L
    tex = os.path.join(HERE, '..', '..', 'assets', 'real', 'tex', 'kw_tmj')
    m = bpy.data.materials.new('kw16_screen'); m.use_nodes = True; nt = m.node_tree; N = nt.nodes; N.clear(); Lk = nt.links.new
    out = N.new('ShaderNodeOutputMaterial'); em = N.new('ShaderNodeEmission'); uv = N.new('ShaderNodeTexCoord')
    def img(nm):
        n = N.new('ShaderNodeTexImage'); n.image = bpy.data.images.load(os.path.join(tex, nm + '.png'), check_existing=True)
        n.interpolation = 'Cubic'; Lk(uv.outputs['UV'], n.inputs['Vector']); return n
    iA, iB = img('out'), img('in'); mb = N.new('ShaderNodeValue')
    x = N.new('ShaderNodeMix'); x.data_type = 'RGBA'; Lk(mb.outputs[0], x.inputs['Factor']); Lk(iA.outputs['Color'], x.inputs['A']); Lk(iB.outputs['Color'], x.inputs['B'])
    Lk(x.outputs['Result'], em.inputs['Color']); em.inputs['Strength'].default_value = float(os.environ.get('KW_SCRE', 1.4)); Lk(em.outputs[0], out.inputs[0])
    R['scr'] = mb; R['scre'] = em
    cx, cy, cz = SCR_C; tilt = math.radians(-8)
    dark = L.mat('kw16_bezel', (0.035, 0.038, 0.042), 0.35, 0.2); steel = L.mat('kw16_steel', (0.72, 0.73, 0.75), 0.3, 1.0)
    L.box('kw16_bezel', (SCR_W + 0.024, 0.03, SCR_H + 0.024), (cx, cy + 0.016, cz), dark, c, 0.008, (math.degrees(tilt), 0, 0))
    bpy.ops.mesh.primitive_plane_add(size=1.0); pl = bpy.context.active_object; pl.name = 'kw16_panel'
    for u_ in list(pl.users_collection): u_.objects.unlink(pl)
    c.objects.link(pl); pl.scale = (SCR_W, SCR_H, 1); pl.rotation_euler = (math.radians(90) + tilt, 0, 0); pl.location = (cx, cy - 0.0005, cz)
    pl.data.materials.append(m)
    for a in ('visible_diffuse', 'visible_glossy', 'visible_transmission'): setattr(pl, a, a == 'visible_glossy')
    L.cyl('kw16_boom', 0.016, 2.80 - cz, (cx, cy + 0.06, (2.80 + cz) / 2), steel, c, (0, 0, 0), 20)
    L.box('kw16_mount', (0.12, 0.04, 0.08), (cx, cy + 0.045, cz), dark, c, 0.005)

# ------------------------------------------------------------------ Ben's own mesh: dents, chewing muscles, drool anchor
def rest_local(o):
    import numpy as np
    n = len(o.data.vertices); kb = o.data.shape_keys.key_blocks if o.data.shape_keys else None
    co = np.empty(n * 3)
    if kb: kb[0].data.foreach_get('co', co)
    else: o.data.vertices.foreach_get('co', co)
    co = co.reshape(-1, 3); mix = co.copy()
    if kb:
        tmp = np.empty(n * 3); ref = np.empty(n * 3)
        for k in kb[1:]:
            if k.mute or abs(k.value) < 1e-6 or k.name.startswith('kw16'): continue
            k.data.foreach_get('co', tmp); k.relative_key.data.foreach_get('co', ref)
            mix += k.value * (tmp - ref).reshape(-1, 3)
    return co, mix

def body_keys(hg):
    """kw16_dent (3 mm hollows in front of both ears, where the joint ball left its socket) and kw16_clench (1.5 mm bulge of the
    chewing muscles) on Ben's HG_Body, + vertex colour kw16g (R = dents, G = muscles) for a soft red at most GLOW."""
    import numpy as np, bpy
    body = next(o for o in hg.meshes if o.name.startswith('HG_Body'))
    co, c = rest_local(body); n = len(c)
    B2M = np.array(body.matrix_world.inverted() @ hg.rig.matrix_world)
    bone = lambda nm: B2M[:3, :3] @ np.array(hg.rig.data.bones[nm].head_local) + B2M[:3, 3]
    eL, eR = bone('eyeball.L'), bone('eyeball.R'); E = (eL + eR) / 2
    x = c[:, 0] - E[0]; z = c[:, 2]; y = c[:, 1]
    nrm = np.empty(n * 3); body.data.vertices.foreach_get('normal', nrm); nrm = nrm.reshape(-1, 3)
    g = lambda p, s: np.exp(-np.sum((c - p) ** 2, axis=1) / (2 * s * s))
    dent = np.zeros(n); mus = np.zeros(n); P = {}
    for s in (-1, 1):
        def lateral(zc, y0, y1):
            m = (np.abs(z - zc) < 0.006) & (y > y0) & (y < y1) & (s * x > 0.03)
            return c[m][np.argmax(s * x[m])] if m.any() else None
        tp = lateral(E[2] - 0.030, E[1] + 0.055, E[1] + 0.072)            # skin just in front of the ear, joint level
        if tp is not None: dent = np.maximum(dent, g(tp, 0.010)); P['dent%+d' % s] = tp
        mp = lateral(E[2] - 0.062, E[1] + 0.035, E[1] + 0.055)            # masseter over the jaw angle
        if mp is not None: mus = np.maximum(mus, g(mp, 0.014)); P['mus%+d' % s] = mp
    print('kw16 body points', {k: [round(float(v_), 3) for v_ in p] for k, p in P.items()}, 'dent verts', int((dent > 0.3).sum()), 'mus', int((mus > 0.3).sum()))
    if body.data.shape_keys is None: body.shape_key_add(name='Basis', from_mix=False)
    for nm, d in (('kw16_dent', -0.0050 * dent[:, None] * nrm), ('kw16_clench', 0.0030 * mus[:, None] * nrm)):
        k = body.shape_key_add(name=nm, from_mix=False); k.slider_max = 1.5; k.value = 0.0; k.data.foreach_set('co', (co + d).ravel())
    ca = body.data.color_attributes.get('kw16g') or body.data.color_attributes.new('kw16g', 'FLOAT_COLOR', 'POINT')
    ca.data.foreach_set('color', np.stack([dent, mus, np.zeros(n), np.ones(n)], 1).astype(np.float32).ravel())
    vd, vm = [], []
    for mt in body.data.materials:
        if not mt or not mt.use_nodes or not mt.name.startswith('.Human'): continue
        N = mt.node_tree.nodes; Lk = mt.node_tree.links.new
        bs = next(q for q in N if q.bl_idname == 'ShaderNodeBsdfPrincipled'); bc = bs.inputs['Base Color']
        if not bc.is_linked: continue
        at = N.new('ShaderNodeAttribute'); at.attribute_name = 'kw16g'; sp = N.new('ShaderNodeSeparateColor'); Lk(at.outputs['Color'], sp.inputs[0])
        a = N.new('ShaderNodeValue'); b = N.new('ShaderNodeValue'); a.outputs[0].default_value = 0.0; b.outputs[0].default_value = 0.0; vd.append(a); vm.append(b)
        m1 = N.new('ShaderNodeMath'); m1.operation = 'MULTIPLY'; Lk(sp.outputs[0], m1.inputs[0]); Lk(a.outputs[0], m1.inputs[1])
        m2 = N.new('ShaderNodeMath'); m2.operation = 'MULTIPLY'; Lk(sp.outputs[1], m2.inputs[0]); Lk(b.outputs[0], m2.inputs[1])
        mx_ = N.new('ShaderNodeMath'); mx_.operation = 'MAXIMUM'; Lk(m1.outputs[0], mx_.inputs[0]); Lk(m2.outputs[0], mx_.inputs[1])
        mx = N.new('ShaderNodeMix'); mx.data_type = 'RGBA'; Lk(mx_.outputs[0], mx.inputs['Factor'])
        src = bc.links[0].from_socket; Lk(src, mx.inputs['A']); mx.inputs['B'].default_value = (0.72, 0.10, 0.08, 1.0); Lk(mx.outputs['Result'], bc)
    R['glow'] = (vd, vm); print('kw16 glow nodes', len(vd))
    # drool anchor: the lower-lip vertex nearest the mouth corner on the camera's side (Ben's right = -X), front-most
    m = (np.abs(x + 0.020) < 0.006) & (z < E[2] - 0.075) & (z > E[2] - 0.095) & (y < E[1] - 0.005)
    if m.any():
        cand = np.where(m)[0]; R['lip'] = int(cand[np.argmin(y[cand] + 2.0 * np.abs(z[cand] - (E[2] - 0.088)))])
        print('kw16 lip vertex', R['lip'], 'rel eyes', np.round(c[R['lip']] - E, 4).tolist())
    R['body'] = body

def build_drool(c):
    import bpy, bmesh
    me = bpy.data.meshes.new('kw16_drool'); bm = bmesh.new()
    ring = 10; segs = 14
    for i in range(segs + 1):
        u = i / segs; r = 0.0011 * (1.0 - 0.45 * u)
        for k in range(ring):
            a = 2 * math.pi * k / ring; bm.verts.new((r * math.cos(a), r * math.sin(a), -u))
    bm.verts.ensure_lookup_table()
    for i in range(segs):
        for k in range(ring):
            a, b = i * ring + k, i * ring + (k + 1) % ring
            bm.faces.new((bm.verts[a], bm.verts[b], bm.verts[b + ring], bm.verts[a + ring]))
    bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new('kw16_drool', me); c.objects.link(ob)
    for p in me.polygons: p.use_smooth = True
    bpy.ops.mesh.primitive_uv_sphere_add(radius=0.0024, segments=16, ring_count=10); dr = bpy.context.active_object; dr.name = 'kw16_drop'
    for u_ in list(dr.users_collection): u_.objects.unlink(dr)
    c.objects.link(dr); bpy.ops.object.shade_smooth()
    mt = bpy.data.materials.new('kw16_saliva'); mt.use_nodes = True; bs = mt.node_tree.nodes['Principled BSDF']
    bs.inputs['Base Color'].default_value = (0.92, 0.94, 0.95, 1); bs.inputs['Roughness'].default_value = 0.04
    bs.inputs['IOR'].default_value = 1.34
    for nm in ('Transmission Weight', 'Transmission'):
        if nm in bs.inputs: bs.inputs[nm].default_value = 0.92; break
    ob.data.materials.append(mt); dr.data.materials.append(mt)
    R['drool'] = (ob, dr)

def build(rt):
    import bpy
    c = bpy.data.collections.get('kw_ep16') or bpy.data.collections.new('kw_ep16')
    if c.name not in bpy.context.scene.collection.children: bpy.context.scene.collection.children.link(c)
    import kwlook as Q_; Q_.LOOP_T = FN / FPS
    build_screen(c); body_keys(rt.actors[ben].p.hg); build_drool(c)
ep.build_hook = build

def eyes(rt, who):
    rg = rt.actors[who].p.hg.rig; W_ = rg.matrix_world
    EL = W_ @ rg.pose.bones['eyeball.L'].head; ER = W_ @ rg.pose.bones['eyeball.R'].head; return EL, ER, (EL + ER) / 2

def set_key(hg, name, v):
    for o in hg.meshes:
        kb = o.data.shape_keys.key_blocks if o.data.shape_keys else None
        k = kb.get(name) if kb else None
        if k is not None: k.value = v

def lip_world(rt):
    import bpy
    body = R['body']; dg = bpy.context.evaluated_depsgraph_get(); ev = body.evaluated_get(dg)
    return ev.matrix_world @ ev.data.vertices[R['lip']].co

def frame_hook(rt, t):
    import bpy, kwlook as Q_
    Q_.LOOP_T = FN / FPS
    f = t * FPS; hb = rt.actors[ben].p.hg
    fv = float(FORCE) if FORCE is not None else None
    dv = fv if fv is not None else v_dent(f); cv = fv if fv is not None else v_clench(f); rv = fv if fv is not None else v_drool(f)
    if f >= FN - 9: dv = cv = rv = 0.0
    set_key(hb, 'kw16_dent', dv); set_key(hb, 'kw16_clench', cv)
    vd, vm = R['glow']
    for n_ in vd: n_.outputs[0].default_value = GLOW * dv
    for n_ in vm: n_.outputs[0].default_value = GLOW * cv
    _, _, EB = eyes(rt, ben); _, _, ED = eyes(rt, doc)
    sh, _ = shot_of(f)
    if fl(3) - 6 <= f < fl(4) + 10: rt.eyes_at(rt.actors[ben], ED)
    rt.eyes_at(rt.actors[doc], EB)
    R['scr'].outputs[0].default_value = 1.0 if f >= fl(3) else 0.0
    R['scre'].inputs['Strength'].default_value = float(os.environ.get('KW_SCRE', 1.4)) if (fl(2) - 4 <= f < FN - 9) else 0.03     # screen off until the X-ray
    bpy.context.view_layer.update()
    ob, dr = R['drool']
    vis = rv > 0.02 and 'lip' in R
    ob.hide_render = dr.hide_render = not vis; ob.hide_viewport = dr.hide_viewport = not vis
    if vis:
        P = lip_world(rt) + V((0, -0.0008, 0.0)); Lg = 0.008 + 0.055 * rv + 0.004 * math.sin(f * 0.21)
        ob.location = P; ob.rotation_euler = (0, 0, 0); ob.scale = (1, 1, Lg)
        dr.location = P + V((0, 0, -Lg)); dr.scale = (1, 1, 1.25)
    sh_ = rt.ep.shot_at(t); rt.FX.update(sh_, t - sh_.t, t)
ep.frame_hook = frame_hook

def look(tg, dirv, dist, lens, fst=8.0, foc=None):
    dv = V(dirv).normalized(); return tg + dv * dist, tg, V((0, 0, 1)), lens, fst, (foc if foc is not None else tg)
def cam_fn(rt, t):
    import bpy
    f = t * FPS; bpy.context.view_layer.update(); shot, u = shot_of(f)
    _, _, EB = eyes(rt, ben); _, _, ED = eyes(rt, doc)
    push = lambda a, b: a * (b / a) ** ease(u)
    if shot in ('MED0', 'MED1'):
        tg = EB + V((0.0, 0.0, -0.20)); d_ = push(1.30, 1.18) if shot == 'MED0' and f < FN - 9 else (push(1.25, 1.12) if shot == 'MED1' else 1.30)
        return look(tg, (-0.75, -1.0, 0.05), d_, 50.0, 8.0, EB)
    if shot == 'SIDE':                                             # Ben's right profile: the locked jaw
        tg = EB + V((-0.05, 0.015, -0.055)); return look(tg, (-1.0, -0.12, 0.05), push(0.66, 0.56), 85.0, 11.0, tg)
    if shot == 'SIDE2':                                            # profile with the ear in frame: the dent in front of it
        tg = EB + V((-0.05, 0.022, -0.045)); return look(tg, (-1.0, -0.10, 0.05), push(0.74, 0.66), 70.0, 11.0, tg)
    if shot == 'CLOSE':
        tg = EB + V((0, 0, -0.05)); return look(tg, (-0.25, -1.0, 0.02), push(0.55, 0.46), 85.0, 11.0, EB)
    if shot == 'MOUTH':                                            # 3/4 low on the lower lip: the drool
        tg = EB + V((-0.015, -0.03, -0.10)); return look(tg, (-0.55, -1.0, -0.05), push(0.42, 0.36), 85.0, 11.0, tg)
    if shot == 'TWO':
        mid = EB.lerp(ED, 0.5) + V((0, 0, -0.15)); bm = (ED - EB); bm.z = 0; bm.normalize(); side = V((0, 0, 1)).cross(bm).normalized()
        if side.y > 0: side = -side
        return look(mid, side * 1.0 + V((0, 0, 0.08)), push(1.80, 1.62), 50.0, 8.0, mid)
    if shot == 'PAIN':                                             # 3/4: the chewing muscle over the jaw angle
        tg = EB + V((-0.01, 0.0, -0.06)); return look(tg, (-0.85, -1.0, 0.02), push(0.62, 0.52), 85.0, 11.0, EB)
    if shot == 'SLEEP':
        tg = EB + V((0, 0, -0.06)); return look(tg, (-0.45, -1.0, 0.02), push(0.60, 0.50), 85.0, 11.0, EB)
    tg = V(SCR_C) + V((0, 0, -0.15))                                 # SCR / SCR2: screen + Ben below it, label clear above
    return look(tg, (0.06, -1.0, 0.25), push(1.55, 1.45), 50.0, 8.0, V(SCR_C))
ep.cam_fn = cam_fn

YL = dict(color='yellow', size=1.2); Y = 0.89
ep.label_outline = True; ep.label_maxw = 820.0; ep.label_lens_fix = True
def lab(txt, f0, f1, **k): return KW.fx.label(txt, at=f0 * F, pos=(0.5, Y), dur=(f1 - f0) * F, **(k or YL))
wd = fw
labels = [KW.fx.label('YAWN', at=-1.0, pos=(0.5, Y), dur=1.0 + (FLK - 2) * F, **YL),
          lab('LOCKED', FLK, fl(1) - 6),
          lab('STUCK', fl(1), wd(1, 'drooling,') - 1),
          lab('DROOLING', wd(1, 'drooling,'), wd(1, 'ears') - 1),
          lab('DENTS', wd(1, 'ears'), fl(2) - 6),
          lab('X-RAY', fl(2), wd(2, 'out') - 1),
          lab('OUT', wd(2, 'out'), fl(3) - 6),
          lab('ER', wd(3, 'ER,'), FPU1 - 1),
          lab('PUSH', FPU1, FPU2 - 1),
          lab('TWICE', FPU2, fl(4) - 6),
          lab('CLENCHED', FCL, fl(5) - 6),
          lab('ASLEEP', wd(5, 'anesthesia,'), FBK - 1),
          lab('BACK IN', FBK, fl(6) - 6),
          lab('FIST', FFI, CTA0 - 2),
          KW.fx.label('JAW CLICK?', at=CTA0 * F, pos=(0.5, 0.30), dur=(FN - 10 - CTA0) * F, **YL),
          KW.fx.label('COMMENT BELOW', at=(CTA0 + 3) * F, pos=(0.5, 0.235), dur=(FN - 13 - CTA0) * F, color='white', size=0.5),
          KW.fx.label('YAWN', at=(FN - 9) * F, pos=(0.5, Y), dur=2.0, **YL)]
labels[-1].o['nopop'] = True
ep.sound(0.0, 'thud', 0.6)
for f_ in (FLK, wd(1, 'ears'), wd(2, 'out'), FPU1, FPU2, FBK): ep.sound(f_ * F, 'thud', 0.45)
ep.mouth_fix = True; ep.eyes_fix = True; ep.relight_after_pose = True
ep.shot(0.0, 'face', set='hospital', cast={ben: PB, doc: PD}, fx=labels, cam=KW.cam.face(ben))
ep.run()
