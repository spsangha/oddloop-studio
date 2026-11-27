"""Kinda Wild Films ep15 - 'He Sees Every Face Turn Into A Demon'  Brief: kindawild/15_face_demon/brief.md.
Facts: Mello, Stehr, Bujarski, Duchaine, The Lancet 2024;403:1176 (Dartmouth, prosopometamorphopsia) + NBC News 22 Mar 2024.
Ben (patient) on the clinic bed, Maya standing at the bedside.  What Ben sees: Maya's face stretches (ears, nose, mouth pulled
back, outer eyes and brows up, chin longer) with deep grooves on forehead, cheeks and chin (shape keys on her own mesh + a soft
groove shade at most 25 %; lips keep their colour).  The clinic screen shows her photo (normal), the edited photo (matching what
he sees) and an MRI slice with the small bright cyst.  No gore: stretched features only.
"""
import sys, os, math; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kwkit as KW
os.environ.setdefault('KW_LIGHT', '1')
HERE = os.path.dirname(os.path.abspath(__file__))
ep = KW.Episode('ep_facedemon', injury="turned into a demon",
                voice_lines=[l.strip() for l in open(os.path.join(HERE, 'ep_facedemon.txt')) if l.strip()],
                music='sneaky_snitch', gap=0.6)
ben = ep.person('Ben', 'civilian', 'eatmore-ben', gender='m', age='young', race='caucasian', hair='short02', tee='teal')
maya = ep.person('Maya', 'civilian', 'cast-maya', gender='f', age='young', race='hispanic', hair='short02', tee='red')

FPS = 24; F = 1.0 / FPS
try: from mathutils import Vector as V
except ImportError: V = None
def ease(x): x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)
R = {}
AMT = float(os.environ.get('KW15_AMT', 1.25))         # overall stretch scale
GSH = float(os.environ.get('KW15_GSH', 0.30))        # groove shade (<= 0.30, lead rule)
DEMON_ALL = os.environ.get('KW15_DEMON')             # probe: force every demon key to this value

ep.waive = {"1 shots;": "brief: one kit shot; the hard cuts (medium -> POV -> close ...) live in ep.cam_fn",
            "last shot must use cam=KW.cam.loop()": "brief: cam_fn cuts back to the frame-0 framing for the last 9 frames (the loop)",
            "HOOK cut <= 200 ms after the last word": "brief: CTA over the payoff shot, then the frame-0 cut",
            "shot face holds": "brief: cuts every 1.1-4 s inside cam_fn"}
fw = lambda i, w: int(round(ep.word(i, w) * FPS))
fl = lambda i: int(round(ep.line(i) * FPS))
fle = lambda i: int(round((ep.line(i) + ep.vo_dur[i]) * FPS))
f_last = fle(6); FN = max(f_last + 30, 680); NF = FN + 1; ep.duration = round(NF / FPS, 4)
CTA0 = FN - 40
FL = fw(3, 'fine.')                                   # consequence: Ben flinches when he looks back from the screen
CUTS = [(0, 'MED0'), (26, 'POV'), (55, 'CLOSE'), (fl(1) - 4, 'MFACE'), (fl(2) - 4, 'TWO'), (fl(3) - 4, 'SCR'), (FL - 2, 'FLINCH'),
        (fl(4) - 4, 'SCR'), (fl(5) - 4, 'SCR'), (fl(6) - 4, 'MFACE7'), (fw(6, 'person') - 3, 'BFACE'), (FN - 9, 'MED0')]
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
LOOP = lambda f: f >= FN - 9
OFF = CTA0 - 8                                        # every distortion gone before the CTA (her face is off screen there anyway)
def ramp(f, f0, n=8, peak=1.0): return 0.0 if (LOOP(f) or f >= OFF) else keys(f, [(f0 - 1, 0.0), (f0 + n, peak)])
# what Ben sees: the hook POV already stretched (0.65), then each feature grows on its word; a stronger second wave on line 2
W1 = fl(1)
def v_ear(f): return max(ramp(f, 26, 10, 0.85), ramp(f, fw(1, 'Ears,'), 8))
def v_nose(f): return max(ramp(f, 26, 10, 0.85), ramp(f, fw(1, 'noses'), 8))
def v_mouth(f): return max(ramp(f, 26, 10, 0.85), ramp(f, fw(1, 'mouths'), 8))
def v_groove(f): return max(ramp(f, 30, 10, 0.5), ramp(f, fw(1, 'grooves'), 10))
def v_eye(f): return max(ramp(f, 26, 10, 0.7), ramp(f, fw(2, 'knew'), 10))
def v_chin(f): return max(ramp(f, 30, 10, 0.4), ramp(f, fw(1, 'chins.'), 8))
DEMON = (('kw15_ear', v_ear), ('kw15_nose', v_nose), ('kw15_mouth', v_mouth), ('kw15_eye', v_eye), ('kw15_chin', v_chin))

# Ben: worried at frame 0 and at the loop; fear on the hook, a flinch when he looks back from the screen
PB = (KW.pose('sit', at='bed_sit', face={'worry': 0.5}, blend=5 * F)
      .then(14 * F, face={'fear': 0.75}, blend=6 * F)
      .then((fl(2) - 4) * F, face={'worry': 0.6}, blend=6 * F)
      .then((FL - 2) * F, face={'fear': 0.9}, act=KW.act.flinch(at=FL * F), blend=4 * F)
      .then((fl(4) - 4) * F, face={'worry': 0.5}, blend=6 * F)
      .then((fl(6) - 4) * F, face={'fear': 0.6}, blend=6 * F)
      .then((CTA0 - 6) * F, face={'worry': 0.5}, blend=6 * F)
      .then((FN - 9) * F, face={'worry': 0.5}, blend=0.01))
PM = (KW.pose('stand', at='front', face='calm', blend=5 * F)
      .then((fl(1) - 4) * F, face={'smile': 0.35}, blend=6 * F)
      .then((CTA0 - 8) * F, face='calm', blend=6 * F))
ep.blinks = {'Ben': [96, 190, 300, 420, 560, 640], 'Maya': [70, 230, 350, 480, 600]}

SCR_C = (-0.10, 0.17, 2.05); SCR_W, SCR_H = 0.46, 0.2875
def build_screen(c):
    import bpy, kwlib as L
    tex = os.path.join(HERE, '..', '..', 'assets', 'real', 'tex', 'kw_pmo')
    m = bpy.data.materials.new('kw15_screen'); m.use_nodes = True; nt = m.node_tree; N = nt.nodes; N.clear(); Lk = nt.links.new
    out = N.new('ShaderNodeOutputMaterial'); em = N.new('ShaderNodeEmission'); uv = N.new('ShaderNodeTexCoord')
    def img(nm):
        n = N.new('ShaderNodeTexImage'); n.image = bpy.data.images.load(os.path.join(tex, nm + '.png'), check_existing=True)
        n.interpolation = 'Cubic'; Lk(uv.outputs['UV'], n.inputs['Vector']); return n
    i0, iA, iB = img('photo'), img('edited'), img('mri')
    su = N.new('ShaderNodeSeparateXYZ'); Lk(uv.outputs['UV'], su.inputs[0])
    rev = N.new('ShaderNodeValue'); mb = N.new('ShaderNodeValue')
    gt = N.new('ShaderNodeMath'); gt.operation = 'LESS_THAN'; Lk(su.outputs['X'], gt.inputs[0]); Lk(rev.outputs[0], gt.inputs[1])   # left-to-right edit wipe
    def mix(fac, a, b):
        x = N.new('ShaderNodeMix'); x.data_type = 'RGBA'; Lk(fac, x.inputs['Factor']); Lk(a, x.inputs['A']); Lk(b, x.inputs['B']); return x.outputs['Result']
    col = mix(mb.outputs[0], mix(gt.outputs[0], i0.outputs['Color'], iA.outputs['Color']), iB.outputs['Color'])
    Lk(col, em.inputs['Color']); em.inputs['Strength'].default_value = float(os.environ.get('KW_SCRE', 1.4)); Lk(em.outputs[0], out.inputs[0])
    R['scr'] = (rev, mb)
    cx, cy, cz = SCR_C; tilt = math.radians(-8)
    dark = L.mat('kw15_bezel', (0.035, 0.038, 0.042), 0.35, 0.2); steel = L.mat('kw15_steel', (0.72, 0.73, 0.75), 0.3, 1.0)
    L.box('kw15_bezel', (SCR_W + 0.024, 0.03, SCR_H + 0.024), (cx, cy + 0.016, cz), dark, c, 0.008, (math.degrees(tilt), 0, 0))
    bpy.ops.mesh.primitive_plane_add(size=1.0); pl = bpy.context.active_object; pl.name = 'kw15_panel'
    for u_ in list(pl.users_collection): u_.objects.unlink(pl)
    c.objects.link(pl); pl.scale = (SCR_W, SCR_H, 1); pl.rotation_euler = (math.radians(90) + tilt, 0, 0); pl.location = (cx, cy - 0.0005, cz)
    pl.data.materials.append(m)
    for a in ('visible_diffuse', 'visible_glossy', 'visible_transmission'): setattr(pl, a, a == 'visible_glossy')
    L.cyl('kw15_boom', 0.016, 2.80 - cz, (cx, cy + 0.06, (2.80 + cz) / 2), steel, c, (0, 0, 0), 20)
    L.box('kw15_mount', (0.12, 0.04, 0.08), (cx, cy + 0.045, cz), dark, c, 0.005)

def rest_local(o):
    """rest-pose LOCAL coords including the active HG shape keys -> (basis co, mixed co)"""
    import numpy as np
    n = len(o.data.vertices); kb = o.data.shape_keys.key_blocks if o.data.shape_keys else None
    co = np.empty(n * 3)
    if kb: kb[0].data.foreach_get('co', co)
    else: o.data.vertices.foreach_get('co', co)
    co = co.reshape(-1, 3); mix = co.copy()
    if kb:
        tmp = np.empty(n * 3); ref = np.empty(n * 3)
        for k in kb[1:]:
            if k.mute or abs(k.value) < 1e-6 or k.name.startswith('kw15'): continue
            k.data.foreach_get('co', tmp); k.relative_key.data.foreach_get('co', ref)
            mix += k.value * (tmp - ref).reshape(-1, 3)
    return co, mix

def demon_keys(hg):
    """kw15_* shape keys on Maya's HG_Body (body-local space, she faces -Y, her left = +X): what the patient described
    (Lancet 2024: 'severely stretched features of the face, with deep grooves on the forehead, cheeks, and chin'; NBC: 'ears,
    noses and mouths were stretched back').  The eyeballs, teeth and lashes are separate, so the eye corners move at most 3 mm."""
    import numpy as np
    body = next(o for o in hg.meshes if o.name.startswith('HG_Body'))
    co, c = rest_local(body); n = len(c)
    B2M = np.array(body.matrix_world.inverted() @ hg.rig.matrix_world)
    bone = lambda nm: B2M[:3, :3] @ np.array(hg.rig.data.bones[nm].head_local) + B2M[:3, 3]
    eL, eR = bone('eyeball.L'), bone('eyeball.R'); E = (eL + eR) / 2; iod = float(np.linalg.norm(eL - eR))
    m = (np.abs(c[:, 0] - E[0]) < 0.008) & (c[:, 2] < E[2] - 0.01) & (c[:, 2] > E[2] - 0.07) & (np.abs(c[:, 1] - E[1]) < 0.15)
    tip = c[m][np.argmin(c[m][:, 1])]
    x = c[:, 0] - E[0]; ax = np.abs(x); sx = np.sign(x); z = c[:, 2]
    front = np.clip((E[1] + 0.03 - c[:, 1]) / 0.02, 0, 1)                 # front half of the head only
    g = lambda p, s: np.exp(-np.sum((c - p) ** 2, axis=1) / (2 * s * s))
    hm = (np.abs(z - E[2]) < 0.035) & (np.abs(c[:, 1] - E[1]) < 0.15)
    D = {}
    # ears: pulled back and up into a point
    d = np.zeros((n, 3))
    for s in (-1, 1):
        sm = hm & (s * x > 0)
        if not sm.any(): continue
        ep_ = c[sm][np.argmax(s * x[sm])]; w = g(ep_ + np.array([0, 0.005, 0.012]), 0.020)
        d[:, 1] += 0.020 * w; d[:, 2] += 0.014 * w * np.clip((z - ep_[2] + 0.01) / 0.03, 0, 1.5); d[:, 0] += s * 0.006 * w
    D['kw15_ear'] = d
    # nose: wings stretched sideways and back, tip a little longer
    d = np.zeros((n, 3)); w = g(tip + np.array([0, 0.012, 0.004]), 0.016) * front
    d[:, 0] += sx * 0.010 * w * np.clip(ax / 0.012, 0, 1); d[:, 1] += 0.006 * w; d[:, 2] -= 0.006 * g(tip, 0.008)
    D['kw15_nose'] = d
    # mouth: corners pulled far back and out (a stretched grin), lips keep their shape and colour
    d = np.zeros((n, 3))
    for s in (-1, 1):
        mc = tip + np.array([s * 0.024, 0.016, -0.034]); w = g(mc, 0.016) * front
        d[:, 0] += s * 0.016 * w; d[:, 1] += 0.018 * w; d[:, 2] += 0.006 * w
    D['kw15_mouth'] = d
    # outer eyes and brows: pulled up and back toward the temples (eye corners <= 3 mm: the eyeball is a separate mesh)
    d = np.zeros((n, 3))
    for s in (-1, 1):
        bc = E + np.array([s * 0.62 * iod, 0.006, 0.026]); w = g(bc, 0.019) * front
        d[:, 2] += 0.020 * w; d[:, 1] += 0.006 * w; d[:, 0] += s * 0.006 * w
        tc = E + np.array([s * 0.80 * iod, 0.012, 0.004]); w2 = g(tc, 0.010) * front
        d[:, 2] += 0.003 * w2; d[:, 1] += 0.003 * w2
    D['kw15_eye'] = d
    # chin: longer and narrower
    d = np.zeros((n, 3)); w = np.clip((tip[2] - 0.050 - z) / 0.03, 0, 1) * np.clip((z - (tip[2] - 0.12)) / 0.02, 0, 1) * np.exp(-(x / 0.035) ** 2) * front
    d[:, 2] -= 0.016 * w; d[:, 1] -= 0.004 * w
    D['kw15_chin'] = d
    # grooves: thin dents along the skin normal + a soft shade (vertex attribute kw15g, max GSH)
    nrm = np.empty(n * 3); body.data.vertices.foreach_get('normal', nrm); nrm = nrm.reshape(-1, 3)
    def seg(a, b, s):
        a = np.array(a); b = np.array(b); ab = b - a; t = np.clip(((c - a) @ ab) / (ab @ ab), 0, 1)
        return np.exp(-np.sum((c - (a + t[:, None] * ab)) ** 2, axis=1) / (2 * s * s))
    gr = np.zeros(n)
    for k in range(3):                                                    # three forehead lines
        zz = E[2] + 0.032 + k * 0.013; gr = np.maximum(gr, np.exp(-((z - zz) / 0.0030) ** 2) * np.clip((0.045 - ax) / 0.012, 0, 1))
    for s in (-1, 1):
        gr = np.maximum(gr, seg(tip + np.array([s * 0.017, 0.010, 0.004]), tip + np.array([s * 0.031, 0.014, -0.040]), 0.0032))   # nose-to-mouth
        gr = np.maximum(gr, seg(E + np.array([s * 0.035, 0.0, -0.022]), tip + np.array([s * 0.048, 0.018, -0.030]), 0.0030))     # cheek
        gr = np.maximum(gr, seg(tip + np.array([s * 0.007, 0.0, -0.058]), tip + np.array([s * 0.010, 0.006, -0.080]), 0.0028))    # chin
    gr = np.maximum(gr, seg(tip + np.array([-0.012, 0.006, -0.052]), tip + np.array([0.012, 0.006, -0.052]), 0.0028))
    gr *= front * (np.abs(c[:, 1] - E[1]) < 0.12)
    D['kw15_groove'] = -0.0036 * gr[:, None] * nrm
    for k_ in D: D[k_] = D[k_] * AMT
    if body.data.shape_keys is None: body.shape_key_add(name='Basis', from_mix=False)
    for nm, d in D.items():
        k = body.shape_key_add(name=nm, from_mix=False); k.slider_max = 1.5; k.value = 0.0
        k.data.foreach_set('co', (co + d).ravel())
    ca = body.data.color_attributes.get('kw15g') or body.data.color_attributes.new('kw15g', 'FLOAT_COLOR', 'POINT')
    ca.data.foreach_set('color', np.stack([gr, gr, gr, np.ones(n)], 1).astype(np.float32).ravel())
    vals = []
    for mt in body.data.materials:
        if not mt or not mt.use_nodes or not mt.name.startswith('.Human'): continue
        N = mt.node_tree.nodes; Lk = mt.node_tree.links.new
        bs = next(x for x in N if x.bl_idname == 'ShaderNodeBsdfPrincipled'); bc = bs.inputs['Base Color']
        if not bc.is_linked: continue
        at = N.new('ShaderNodeAttribute'); at.attribute_name = 'kw15g'; v = N.new('ShaderNodeValue'); v.outputs[0].default_value = 0.0; vals.append(v)
        mu = N.new('ShaderNodeMath'); mu.operation = 'MULTIPLY'; Lk(at.outputs['Fac'], mu.inputs[0]); Lk(v.outputs[0], mu.inputs[1])
        mx = N.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'; Lk(mu.outputs[0], mx.inputs['Factor'])
        src = bc.links[0].from_socket; Lk(src, mx.inputs['A']); mx.inputs['B'].default_value = (0.45, 0.36, 0.33, 1.0); Lk(mx.outputs['Result'], bc)
    R['gshade'] = vals
    mx_ = {k_: round(float(np.linalg.norm(d, axis=1).max()) * 1000, 1) for k_, d in D.items()}
    print('ep15 demon keys (max mm)', mx_, 'groove verts', int((gr > 0.5).sum()), 'iod', round(iod, 4), flush=True)
    hg.keys = [o.data.shape_keys.key_blocks for o in hg.meshes if o.data.shape_keys]

def set_key(hg, name, v):
    for o in hg.meshes:
        kb = o.data.shape_keys.key_blocks if o.data.shape_keys else None
        k = kb.get(name) if kb else None
        if k is not None: k.value = v

def build(rt):
    import bpy
    c = bpy.data.collections.get('kw_ep15') or bpy.data.collections.new('kw_ep15')
    if c.name not in bpy.context.scene.collection.children: bpy.context.scene.collection.children.link(c)
    import kwlook as Q_; Q_.LOOP_T = FN / FPS
    build_screen(c); demon_keys(rt.actors[maya].p.hg)
ep.build_hook = build

def eyes(rt, who):
    rg = rt.actors[who].p.hg.rig; W_ = rg.matrix_world
    EL = W_ @ rg.pose.bones['eyeball.L'].head; ER = W_ @ rg.pose.bones['eyeball.R'].head; return EL, ER, (EL + ER) / 2

def frame_hook(rt, t):
    import bpy, kwlook as Q_
    Q_.LOOP_T = FN / FPS
    f = t * FPS; hm = rt.actors[maya].p.hg
    for nm, fn in DEMON: set_key(hm, nm, float(DEMON_ALL) if DEMON_ALL is not None else fn(f))
    gv = float(DEMON_ALL) if DEMON_ALL is not None else v_groove(f)
    set_key(hm, 'kw15_groove', gv)
    for n_ in R.get('gshade', []): n_.outputs[0].default_value = GSH * gv
    _, _, EB = eyes(rt, ben); _, _, EM = eyes(rt, maya)
    sh, _ = shot_of(f)
    rt.eyes_at(rt.actors[ben], EM)
    rt.eyes_at(rt.actors[maya], EB)
    rev, mb = R['scr']
    f4, f5 = fl(4) - 4, fl(5) - 4
    rev.outputs[0].default_value = 0.0 if f < fw(4, 'edited') else ease((f - fw(4, 'edited')) / 22)
    mb.outputs[0].default_value = 1.0 if (f5 <= f < FN - 9) else 0.0
    bpy.context.view_layer.update(); sh_ = rt.ep.shot_at(t); rt.FX.update(sh_, t - sh_.t, t)
ep.frame_hook = frame_hook

def look(tg, dirv, dist, lens, fst=8.0, foc=None):
    dv = V(dirv).normalized(); return tg + dv * dist, tg, V((0, 0, 1)), lens, fst, (foc if foc is not None else tg)
def cam_fn(rt, t):
    import bpy
    f = t * FPS; bpy.context.view_layer.update(); shot, u = shot_of(f)
    _, _, EB = eyes(rt, ben); _, _, EM = eyes(rt, maya)
    push = lambda a, b: a * (b / a) ** ease(u)
    bm = (EM - EB); bm.z = 0; bm.normalize(); side = bm.cross(V((0, 0, 1))).normalized()     # side = Ben's right of his look line
    if shot == 'MED0':
        tg = EB + V((0.0, 0.0, -0.20)); return look(tg, (-0.75, -1.0, 0.05), push(1.30, 1.18) if f < FN - 9 else 1.30, 50.0, 8.0, EB)
    if shot == 'CLOSE':
        tg = EB + V((0, 0, -0.01)); return look(tg, (-0.25, -1.0, 0.02), push(0.40, 0.34), 85.0, 11.0, EB)
    if shot == 'POV':        # over Ben's right shoulder onto Maya's face
        P = EB - bm * 0.30 + side * 0.16 + V((0, 0, 0.04)); tg = EM + V((0, 0, -0.03))
        return P, tg, V((0, 0, 1)), 60.0, 4.0, EM
    if shot in ('MFACE', 'MFACE7'):
        d = (EB - EM); d.z = 0; d.normalize(); tg = EM + V((0, 0, -0.035))
        a, b = (0.52, 0.42) if shot == 'MFACE' else (0.48, 0.40)
        return look(tg, d + side * 0.25 + V((0, 0, 0.02)), push(a, b), 85.0, 11.0, EM)
    if shot == 'TWO':
        mid = EB.lerp(EM, 0.5) + V((0, 0, -0.12))      # from Ben's right (-X): the open side of the room
        return look(mid, (-1.0, -0.45, 0.08), push(1.25, 1.15), 30.0, 8.0, mid)    # curtain at x -1.4
    if shot == 'FLINCH':
        tg = EB + V((0, 0, -0.05)); return look(tg, (-0.35, -1.0, 0.02), push(0.70, 0.60), 85.0, 11.0, EB)
    if shot == 'BFACE':
        tg = EB + V((0, 0, -0.05)); return look(tg, (-0.45, -1.0, 0.02), push(0.80, 0.70), 85.0, 11.0, EB)
    tg = V(SCR_C) + V((0, 0, -0.06))
    return look(tg, (0.06, -1.0, 0.25), push(1.30, 1.20), 50.0, 8.0, V(SCR_C))
ep.cam_fn = cam_fn

YL = dict(color='yellow', size=1.2); Y = 0.89
ep.label_outline = True; ep.label_maxw = 820.0; ep.label_lens_fix = True
def lab(txt, f0, f1, **k): return KW.fx.label(txt, at=f0 * F, pos=(0.5, Y), dur=(f1 - f0) * F, **(k or YL))
wd = lambda i, w: fw(i, w)
labels = [KW.fx.label('EVERY FACE', at=-1.0, pos=(0.5, Y), dur=1.0 + (wd(0, 'demon.') - 2) * F, **YL),
          lab('DEMON', wd(0, 'demon.'), fl(1) - 6),
          lab('EARS', wd(1, 'Ears,'), wd(1, 'noses') - 1),
          lab('NOSES', wd(1, 'noses'), wd(1, 'mouths') - 1),
          lab('MOUTHS', wd(1, 'mouths'), wd(1, 'grooves') - 1),
          lab('GROOVES', wd(1, 'grooves'), fl(2) - 6),
          lab('NORMAL', wd(2, 'Houses'), wd(2, 'knew') - 1),
          lab('KNEW THEM', wd(2, 'knew'), fl(3) - 6),
          lab('ON SCREEN', wd(3, 'screen,'), FL - 2),
          lab('FINE', FL - 1, fl(4) - 6),
          lab('PHOTO', wd(4, 'photographed'), wd(4, 'edited') - 1),
          lab('EDITED', wd(4, 'edited'), fl(5) - 6),
          lab('MRI', wd(5, 'MRI'), wd(5, 'cyst') - 1),
          lab('CYST', wd(5, 'cyst'), fl(6) - 6),
          lab('PMO', wd(6, 'prosopometamorphopsia,'), wd(6, 'person') - 3),
          lab('IN PERSON', wd(6, 'person') - 2, CTA0 - 2),
          KW.fx.label('SCARED?', at=CTA0 * F, pos=(0.5, 0.30), dur=(FN - 10 - CTA0) * F, **YL),
          KW.fx.label('COMMENT BELOW', at=(CTA0 + 3) * F, pos=(0.5, 0.235), dur=(FN - 13 - CTA0) * F, color='white', size=0.5),
          KW.fx.label('EVERY FACE', at=(FN - 9) * F, pos=(0.5, Y), dur=2.0, **YL)]
labels[-1].o['nopop'] = True
ep.sound(0.0, 'thud', 0.6)
for f_ in (26, 55, wd(1, 'Ears,'), FL, wd(5, 'cyst'), wd(6, 'prosopometamorphopsia,')): ep.sound(f_ * F, 'thud', 0.45)
ep.mouth_fix = True; ep.eyes_fix = True; ep.relight_after_pose = True
ep.shot(0.0, 'face', set='hospital', cast={ben: PB, maya: PM}, fx=labels, cam=KW.cam.face(ben))
ep.run()
