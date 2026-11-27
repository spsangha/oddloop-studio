"""Kinda Wild Films ep14 - 'Why Her Own DNA Said She Wasn't The Mother'  Brief: kindawild/14_dna_mother/brief.md.
Facts: ASU Embryo Project (Lydia Fairchild, 2002), National Geographic (Ed Yong), Yu et al. NEJM 2002.  Maya (cast v1.2) on the
clinic bed.  Body changes: pregnant belly (kit swell 'belly' = kw_bloat on body + clothes) then flat at the birth; blue DNA glow
on hair, cheek, forearm skin and hand veins (vertex masks + emission); chimera patchwork of blue / orange cells on all skin.
No child or baby is shown: the screen carries text and a body outline only.
"""
import sys, os, math; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kwkit as KW
os.environ.setdefault('KW_LIGHT', '1')
HERE = os.path.dirname(os.path.abspath(__file__))
ep = KW.Episode('ep_dnamother', injury="her own kids",
                voice_lines=[l.strip() for l in open(os.path.join(HERE, 'ep_dnamother.txt')) if l.strip()],
                music='sneaky_snitch', gap=0.7)
maya = ep.person('Maya', 'civilian', 'cast-maya', gender='f', age='young', race='hispanic', hair='short02', tee='red')

FPS = 24; F = 1.0 / FPS
try: from mathutils import Vector as V
except ImportError: V = None
def ease(x): x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)
R = {}
BLUE = (0.0, 0.16, 1.0, 1.0); ORANGE = (1.0, 0.33, 0.04, 1.0)
GLOW = float(os.environ.get('KW14_GLOW', 1.2)); MOS = float(os.environ.get('KW14_MOS', 0.12)); MOST = float(os.environ.get('KW14_MOST', 0.30))
CELL = float(os.environ.get('KW14_CELL', 40.0))

ep.waive = {"1 shots;": "brief: one kit shot; the hard cuts (medium -> screen -> close ...) live in ep.cam_fn",
            "last shot must use cam=KW.cam.loop()": "brief: cam_fn cuts back to the frame-0 framing for the last 9 frames (the loop)",
            "HOOK cut <= 200 ms after the last word": "brief: CTA over the payoff shot, then the frame-0 cut",
            "shot face holds": "brief: cuts every 1.1-4 s inside cam_fn",
            "script has 8 sentences": "lead GO on the 8-line draft (27 Nov); each line is one beat of the true case"}
fw = lambda i, w: int(round(ep.word(i, w) * FPS))
fl = lambda i: int(round(ep.line(i) * FPS))
fle = lambda i: int(round((ep.line(i) + ep.vo_dur[i]) * FPS))
f_last = fle(7); FN = max(f_last + 30, 680); NF = FN + 1; ep.duration = round(NF / FPS, 4)
CTA0 = FN - 40
CUTS = [(0, 'MED0'), (26, 'SCR'), (55, 'CLOSE'), (fl(1) - 4, 'FRONT1'), (fl(2) - 4, 'SIDE2'), (fl(3) - 4, 'SCR2'), (fw(3, 'match') - 3, 'FRONT3'),
        (fl(4) - 4, 'GLOW'), (fl(5) - 4, 'SCR3'), (fl(6) - 4, 'MOSA'), (fl(7) - 4, 'FACE7'), (FN - 9, 'MED0')]
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
G_OFF = fl(6) - 4                                     # glows off at the MOSA cut
def on_at(f, f0, n=6): return 0.0 if (LOOP(f) or f >= G_OFF) else keys(f, [(f0 - 1, 0.0), (f0 + n, 1.0)])
B0 = fl(2) - 4; B1 = fw(2, 'birth')
def v_hair(f): return on_at(f, fw(4, 'hair,'))
def v_cheek(f): return on_at(f, fw(4, 'cheek,'))
def v_skin(f): return on_at(f, fw(4, 'skin'))
def v_blood(f): return on_at(f, fw(4, 'blood'))
def v_preg(f): return 0.0 if LOOP(f) else keys(f, [(B0, 0.0), (B1 - 8, 1.0), (B1 + 2, 1.0), (B1 + 12, 0.0)])
def v_mos(f): return 0.0 if LOOP(f) else keys(f, [(fw(6, 'chimera,') - 2, 0.0), (fw(6, 'chimera,') + 14, 1.0)])

# pose timeline (local time = global, one kit shot at 0): belly grows into line 3, flat at "birth"; faces ease over 6 frames
B0 = fl(2) - 4; B1 = fw(2, 'birth')
P = (KW.pose('sit', at='bed_sit', face={'worry': 0.45}, blend=5 * F)
     .then(fl(1) * F, face='worry', blend=6 * F)
     .then(B0 * F, face={'worry': 0.4}, blend=6 * F)
     .then((fw(3, 'match') - 2) * F, face={'worry': 0.75}, flush=float(os.environ.get('KW14_FLUSH', 1.0)), blend=8 * F)
     .then((fl(4) - 4) * F, face='calm', flush=0.0, blend=6 * F)
     .then(fw(6, 'chimera,') * F, face={'surprise': 0.6}, blend=6 * F)
     .then((fw(7, 'dismissed') - 2) * F, face='relief', blend=6 * F)
     .then((FN - 9) * F, face={'worry': 0.45}, blend=0.01))
ep.blinks = {'Maya': [44, 150, 236, 330, 420, 520, 600, 660]}

SCR_C = (-0.10, 0.17, 2.05); SCR_W, SCR_H = 0.46, 0.2875
def build_screen(c):
    import bpy, kwlib as L
    tex = os.path.join(HERE, '..', '..', 'assets', 'real', 'tex', 'kw_dna')
    m = bpy.data.materials.new('kw14_screen'); m.use_nodes = True; nt = m.node_tree; N = nt.nodes; N.clear(); Lk = nt.links.new
    out = N.new('ShaderNodeOutputMaterial'); em = N.new('ShaderNodeEmission'); uv = N.new('ShaderNodeTexCoord')
    def img(nm):
        n = N.new('ShaderNodeTexImage'); n.image = bpy.data.images.load(os.path.join(tex, nm + '.png'), check_existing=True)
        n.interpolation = 'Cubic'; Lk(uv.outputs['UV'], n.inputs['Vector']); return n
    i0, iA, iB, iC = img('card0'), img('cardA'), img('cardB'), img('cardC')
    su = N.new('ShaderNodeSeparateXYZ'); Lk(uv.outputs['UV'], su.inputs[0])
    rev = N.new('ShaderNodeValue'); mb = N.new('ShaderNodeValue'); mc = N.new('ShaderNodeValue')
    inv = N.new('ShaderNodeMath'); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1.0; Lk(rev.outputs[0], inv.inputs[1])
    gt = N.new('ShaderNodeMath'); gt.operation = 'GREATER_THAN'; Lk(su.outputs['Y'], gt.inputs[0]); Lk(inv.outputs[0], gt.inputs[1])   # top-down reveal
    def mix(fac, a, b):
        x = N.new('ShaderNodeMix'); x.data_type = 'RGBA'; Lk(fac, x.inputs['Factor']); Lk(a, x.inputs['A']); Lk(b, x.inputs['B']); return x.outputs['Result']
    col = mix(mc.outputs[0], mix(mb.outputs[0], mix(gt.outputs[0], i0.outputs['Color'], iA.outputs['Color']), iB.outputs['Color']), iC.outputs['Color'])
    Lk(col, em.inputs['Color']); em.inputs['Strength'].default_value = float(os.environ.get('KW_SCRE', 1.4)); Lk(em.outputs[0], out.inputs[0])
    R['scr'] = (rev, mb, mc)
    cx, cy, cz = SCR_C; tilt = math.radians(-8)
    dark = L.mat('kw14_bezel', (0.035, 0.038, 0.042), 0.35, 0.2); steel = L.mat('kw14_steel', (0.72, 0.73, 0.75), 0.3, 1.0)
    L.box('kw14_bezel', (SCR_W + 0.024, 0.03, SCR_H + 0.024), (cx, cy + 0.016, cz), dark, c, 0.008, (math.degrees(tilt), 0, 0))
    bpy.ops.mesh.primitive_plane_add(size=1.0); pl = bpy.context.active_object; pl.name = 'kw14_panel'
    for u_ in list(pl.users_collection): u_.objects.unlink(pl)
    c.objects.link(pl); pl.scale = (SCR_W, SCR_H, 1); pl.rotation_euler = (math.radians(90) + tilt, 0, 0); pl.location = (cx, cy - 0.0005, cz)
    pl.data.materials.append(m)
    for a in ('visible_diffuse', 'visible_glossy', 'visible_transmission'): setattr(pl, a, a == 'visible_glossy')
    L.cyl('kw14_boom', 0.016, 2.80 - cz, (cx, cy + 0.06, (2.80 + cz) / 2), steel, c, (0, 0, 0), 20)
    L.box('kw14_mount', (0.12, 0.04, 0.08), (cx, cy + 0.045, cz), dark, c, 0.005)

def seg_dist(P_, a, b):
    import numpy as np
    ab = b - a; t = np.clip(((P_ - a) @ ab) / max(1e-9, ab @ ab), 0, 1)
    return np.linalg.norm(P_ - (a + t[:, None] * ab), axis=1), t

def rest_world(o):
    """rest-pose world coords including the active HG shape keys (height/body keys), -> (basis co, world co, inv 3x3)"""
    import numpy as np
    n = len(o.data.vertices); kb = o.data.shape_keys.key_blocks if o.data.shape_keys else None
    co = np.empty(n * 3)
    if kb: kb[0].data.foreach_get('co', co)
    else: o.data.vertices.foreach_get('co', co)
    co = co.reshape(-1, 3); mix = co.copy()
    if kb:
        tmp = np.empty(n * 3); ref = np.empty(n * 3)
        for k in kb[1:]:
            if k.mute or abs(k.value) < 1e-6 or k.name.startswith('kw14'): continue
            k.data.foreach_get('co', tmp); k.relative_key.data.foreach_get('co', ref)
            mix += k.value * (tmp - ref).reshape(-1, 3)
    W = np.array(o.matrix_world); return co, mix @ W[:3, :3].T + W[:3, 3], np.linalg.inv(W[:3, :3])

def belly_key(hg):
    """kw14_preg: pregnant belly, the same world-space field on body, tee and jeans (rest pose, Maya faces -Y)."""
    import numpy as np
    rig = hg.rig; RW = np.array(rig.matrix_world); bn = rig.data.bones
    wp = lambda v: RW[:3, :3] @ np.array(v) + RW[:3, 3]
    hz = wp(bn['thigh.L'].head_local)[2]; sp = wp(bn['spine.001'].head_local)
    cz = hz + float(os.environ.get('KW14_BZ', 0.13)); A = float(os.environ.get('KW14_BA', 0.10))
    body = next(o for o in hg.meshes if o.name.startswith('HG_Body')); _, bw, _ = rest_world(body)
    band = (np.abs(bw[:, 2] - cz) < 0.02) & (np.abs(bw[:, 0] - sp[0]) < 0.05); yf = bw[band, 1].min(); cy = yf + 0.10
    out = {}
    for o in hg.meshes:
        if not (o.name.startswith('HG_Body') or 'SHIRT' in o.name.upper() or 'JEANS' in o.name.upper()): continue
        co, cw, Wi = rest_world(o); x = cw[:, 0] - sp[0]; y = cw[:, 1]; z = cw[:, 2]
        g = np.exp(-(x / 0.115) ** 2 - ((z - cz) / np.where(z < cz, 0.10, 0.15)) ** 2)
        g *= np.clip((cy - y) / 0.07, 0, 1) * np.clip((z - (hz - 0.01)) / 0.05, 0, 1)
        d = np.zeros_like(cw); d[:, 1] = -A * g; d[:, 0] = A * 0.30 * g * np.clip(x / 0.10, -1, 1); d[:, 2] = -A * 0.15 * g
        if o.data.shape_keys is None: o.shape_key_add(name='Basis', from_mix=False)
        k = o.shape_key_add(name='kw14_preg', from_mix=False); k.slider_max = 1.5; k.value = 0.0
        k.data.foreach_set('co', (co + d @ Wi.T).ravel()); out[o.name] = int((g > 0.05).sum())
    print('ep14 belly', out, 'cz', round(cz, 3), 'front y', round(yf, 3), flush=True)
    hg.keys = [o.data.shape_keys.key_blocks for o in hg.meshes if o.data.shape_keys]

def set_key(hg, name, v):
    for o in hg.meshes:
        kb = o.data.shape_keys.key_blocks if o.data.shape_keys else None
        k = kb.get(name) if kb else None
        if k is not None: k.value = v

def build_glow(hg):
    """vertex masks on HG_Body (rest pose, world space): R cheeks, G left forearm (skin), B left wrist + back of hand (blood
    veins).  Emission on the skin material: masks x values, vein lines from a noise texture, chimera cells from a Voronoi
    texture on the undeformed (Generated) coordinates.  Hair materials get an emission mix."""
    import bpy, numpy as np
    rig = hg.rig; RW = np.array(rig.matrix_world); bn = rig.data.bones
    wp = lambda v: RW[:3, :3] @ np.array(v) + RW[:3, 3]
    E = (wp(bn['eyeball.L'].head_local) + wp(bn['eyeball.R'].head_local)) / 2
    body = next(o for o in hg.meshes if o.name.startswith('HG_Body'))
    co, cw, _ = rest_world(body); n = len(cw)
    # cheeks: both sides, below the eyes, front of the face
    ch = np.zeros(n)
    for sx in (-1, 1):
        c0 = E + np.array([sx * 0.040, -0.010, -0.040]); d = np.linalg.norm((cw - c0) * np.array([1.0, 0.7, 1.0]), axis=1)
        ch = np.maximum(ch, np.clip((0.034 - d) / 0.016, 0, 1))
    ch *= (cw[:, 1] < E[1] + 0.02)
    fa, fb = wp(bn['forearm.L'].head_local), wp(bn['forearm.L'].tail_local)
    ha = wp(bn['hand.L'].head_local); hb = wp(bn['hand.L'].tail_local)
    d1, t1 = seg_dist(cw, fa, fb); arm = np.clip((0.060 - d1) / 0.015, 0, 1) * np.clip((0.70 - t1) / 0.12, 0, 1) * np.clip((t1 - 0.10) / 0.1, 0, 1)
    d2, t2 = seg_dist(cw, fb + (fa - fb) * 0.25, hb); hand = np.clip((0.055 - d2) / 0.015, 0, 1)
    sm = lambda x: x * x * (3 - 2 * x)
    col = np.stack([sm(ch), sm(arm), sm(hand), np.ones(n)], 1).astype(np.float32)
    ca = body.data.color_attributes.get('kw14m') or body.data.color_attributes.new('kw14m', 'FLOAT_COLOR', 'POINT')
    ca.data.foreach_set('color', col.ravel())
    lo, hi = co.min(0), co.max(0); dims = hi - lo
    print('ep14 masks: cheek', int((ch > 0.5).sum()), 'arm', int((arm > 0.5).sum()), 'hand', int((hand > 0.5).sum()), 'dims', dims.round(3), flush=True)
    vals = {}
    for m in body.data.materials:
        if not m or not m.use_nodes: continue
        nt = m.node_tree; N = nt.nodes; Lk = nt.links.new
        if m.name.startswith('.Human'):
            bs = next(x for x in N if x.bl_idname == 'ShaderNodeBsdfPrincipled')
            def val(k):
                if k not in vals: v = N.new('ShaderNodeValue'); v.outputs[0].default_value = 0.0; vals[k] = [v]
                else: v = N.new('ShaderNodeValue'); vals[k].append(v)
                return v.outputs[0]
            def math_(op, a, b):
                x = N.new('ShaderNodeMath'); x.operation = op
                for i, s in enumerate((a, b)):
                    if isinstance(s, (int, float)): x.inputs[i].default_value = s
                    else: Lk(s, x.inputs[i])
                return x.outputs[0]
            at = N.new('ShaderNodeAttribute'); at.attribute_name = 'kw14m'
            sp = N.new('ShaderNodeSeparateColor'); Lk(at.outputs['Color'], sp.inputs[0])
            tc = N.new('ShaderNodeTexCoord'); mp = N.new('ShaderNodeMapping'); Lk(tc.outputs['Generated'], mp.inputs['Vector'])
            mp.inputs['Scale'].default_value = tuple(float(x) for x in dims)
            nz = N.new('ShaderNodeTexNoise'); Lk(mp.outputs['Vector'], nz.inputs['Vector']); nz.inputs['Scale'].default_value = 60.0; nz.inputs['Detail'].default_value = 3.0
            vein = N.new('ShaderNodeMapRange'); Lk(math_('ABSOLUTE', math_('SUBTRACT', nz.outputs['Fac'], 0.5), 0), vein.inputs['Value'])
            vein.inputs['From Min'].default_value = 0.0; vein.inputs['From Max'].default_value = 0.035; vein.inputs['To Min'].default_value = 1.0; vein.inputs['To Max'].default_value = 0.15
            glow = math_('ADD', math_('ADD', math_('MULTIPLY', sp.outputs['Red'], val('cheek')), math_('MULTIPLY', sp.outputs['Green'], val('skin'))),
                         math_('MULTIPLY', math_('MULTIPLY', sp.outputs['Blue'], vein.outputs['Result']), val('blood')))
            vo = N.new('ShaderNodeTexVoronoi'); Lk(mp.outputs['Vector'], vo.inputs['Vector']); vo.inputs['Scale'].default_value = CELL
            cs = N.new('ShaderNodeSeparateColor'); Lk(vo.outputs['Color'], cs.inputs[0])
            cell = math_('GREATER_THAN', cs.outputs['Red'], 0.5)
            cc = N.new('ShaderNodeMix'); cc.data_type = 'RGBA'; Lk(cell, cc.inputs['Factor']); cc.inputs['A'].default_value = BLUE; cc.inputs['B'].default_value = ORANGE
            mos = val('mos')
            ec = N.new('ShaderNodeMix'); ec.data_type = 'RGBA'; Lk(mos, ec.inputs['Factor']); ec.inputs['A'].default_value = BLUE; Lk(cc.outputs['Result'], ec.inputs['B'])
            Lk(ec.outputs['Result'], bs.inputs['Emission Color'])
            Lk(math_('ADD', math_('MULTIPLY', glow, GLOW), math_('MULTIPLY', mos, MOS)), bs.inputs['Emission Strength'])
            bc = bs.inputs['Base Color']
            if bc.is_linked:
                src = bc.links[0].from_socket; tm = N.new('ShaderNodeMix'); tm.data_type = 'RGBA'
                Lk(math_('MULTIPLY', mos, MOST), tm.inputs['Factor']); Lk(src, tm.inputs['A']); Lk(cc.outputs['Result'], tm.inputs['B']); Lk(tm.outputs['Result'], bc)
    hair_mats = [m for m in body.data.materials if m and m.name.startswith('.HG_Hair_Head')]
    for o in bpy.data.objects:
        if o.type == 'MESH' and 'hair' in o.name.lower() and o.name.startswith(hg.rig.name.split('.')[0]):
            hair_mats += [m for m in o.data.materials if m]
    for o in bpy.data.objects:
        if o.type == 'MESH' and o.name.startswith('Maya') and 'hair' in o.name.lower(): hair_mats += [m for m in o.data.materials if m and m not in hair_mats]
    for m in hair_mats:
        if not m.use_nodes: continue
        nt = m.node_tree; N = nt.nodes; Lk = nt.links.new
        out = next((x for x in N if x.bl_idname == 'ShaderNodeOutputMaterial' and x.is_active_output), None) or next(x for x in N if x.bl_idname == 'ShaderNodeOutputMaterial')
        if not out.inputs['Surface'].is_linked: continue
        src = out.inputs['Surface'].links[0].from_socket
        em = N.new('ShaderNodeEmission'); em.inputs['Color'].default_value = BLUE; em.inputs['Strength'].default_value = float(os.environ.get('KW14_HGLOW', 1.0))
        mx = N.new('ShaderNodeMixShader'); v = N.new('ShaderNodeValue'); v.outputs[0].default_value = 0.0; vals.setdefault('hair', []).append(v)
        mf = N.new('ShaderNodeMath'); mf.operation = 'MULTIPLY'; mf.inputs[1].default_value = 0.75; Lk(v.outputs[0], mf.inputs[0]); Lk(mf.outputs[0], mx.inputs[0]); Lk(src, mx.inputs[1]); Lk(em.outputs[0], mx.inputs[2]); Lk(mx.outputs[0], out.inputs['Surface'])
    print('ep14 glow materials', {k: len(v) for k, v in vals.items()}, [m.name for m in hair_mats], flush=True)
    R['vals'] = vals

def build(rt):
    import bpy
    c = bpy.data.collections.get('kw_ep14') or bpy.data.collections.new('kw_ep14')
    if c.name not in bpy.context.scene.collection.children: bpy.context.scene.collection.children.link(c)
    import kwlook as Q_; Q_.LOOP_T = FN / FPS
    build_screen(c); belly_key(rt.actors[maya].p.hg); build_glow(rt.actors[maya].p.hg)
ep.build_hook = build

def eyes(rt):
    rg = rt.actors[maya].p.hg.rig; W_ = rg.matrix_world
    EL = W_ @ rg.pose.bones['eyeball.L'].head; ER = W_ @ rg.pose.bones['eyeball.R'].head; return EL, ER, (EL + ER) / 2
def bone_w(rt, nm):
    rg = rt.actors[maya].p.hg.rig; return rg.matrix_world @ rg.pose.bones[nm].head

def frame_hook(rt, t):
    import bpy, kwlook as Q_
    Q_.LOOP_T = FN / FPS
    f = t * FPS; ra = rt.actors[maya]
    set_key(ra.p.hg, 'kw14_preg', v_preg(f))
    EL, ER, Em = eyes(rt); rt.eyes_at(ra, Em + V((0.10, -0.60, 0.015)))
    for k, fn in (('hair', v_hair), ('cheek', v_cheek), ('skin', v_skin), ('blood', v_blood), ('mos', v_mos)):
        for n_ in R['vals'].get(k, []): n_.outputs[0].default_value = fn(f)
    rev, mb, mc = R['scr']
    rev.outputs[0].default_value = 0.0 if f < 30 else ease((f - 30) / 20)
    mb.outputs[0].default_value = 1.0 if (fl(3) - 4 <= f < FN - 9) else 0.0
    mc.outputs[0].default_value = 1.0 if (fl(5) - 4 <= f < FN - 9) else 0.0
    bpy.context.view_layer.update(); sh_ = rt.ep.shot_at(t); rt.FX.update(sh_, t - sh_.t, t)
ep.frame_hook = frame_hook

def look(tg, dirv, dist, lens, fst=8.0, foc=None):
    dv = V(dirv).normalized(); return tg + dv * dist, tg, V((0, 0, 1)), lens, fst, (foc if foc is not None else tg)
def cam_fn(rt, t):
    import bpy
    f = t * FPS; bpy.context.view_layer.update(); shot, u = shot_of(f)
    EL, ER, Em = eyes(rt)
    push = lambda a, b: a * (b / a) ** ease(u)
    if shot == 'MED0':
        tg = Em + V((0.0, 0.0, -0.22)); return look(tg, (0.55, -1.0, 0.05), 1.30, 50.0, 8.0, Em)
    if shot == 'CLOSE':
        tg = Em + V((0, 0, -0.03)); return look(tg, (0.35, -1.0, 0.02), push(0.50, 0.44), 85.0, 11.0, Em)
    if shot == 'FRONT3':
        tg = Em + V((0, 0, -0.06)); return look(tg, (-0.20, -1.0, 0.02), push(0.62, 0.56), 85.0, 11.0, Em)
    if shot == 'FRONT1':
        tg = Em + V((0, 0, -0.05)); return look(tg, (0.10, -1.0, 0.02), push(0.66, 0.58), 85.0, 11.0, Em)
    if shot == 'SIDE2':
        tg = Em + V((0.0, -0.06, -0.36)); return look(tg, (1.0, -0.35, 0.05), push(1.75, 1.60), 50.0, 8.0, Em + V((0, -0.05, -0.40)))
    if shot == 'GLOW':
        hd = bone_w(rt, 'hand.L'); tg = Em.lerp(hd, 0.40)
        return look(tg, (0.75, -1.0, 0.10), push(1.45, 1.30), 50.0, 8.0, Em.lerp(hd, 0.3))
    if shot == 'MOSA':
        tg = Em + V((0, 0, -0.20)); return look(tg, (0.45, -1.0, 0.05), push(1.20, 0.95), 50.0, 8.0, Em)
    if shot == 'FACE7':
        tg = Em + V((0, 0, -0.06)); return look(tg, (0.30, -1.0, 0.02), push(0.80, 0.70), 85.0, 11.0, Em)
    tg = V(SCR_C) + V((0, 0, -0.06))
    return look(tg, (0.06, -1.0, 0.25), push(1.30, 1.20), 50.0, 8.0, V(SCR_C))
ep.cam_fn = cam_fn

YL = dict(color='yellow', size=1.2); Y = 0.89
ep.label_outline = True; ep.label_maxw = 820.0; ep.label_lens_fix = True
def lab(txt, f0, f1, **k): return KW.fx.label(txt, at=f0 * F, pos=(0.5, Y), dur=(f1 - f0) * F, **(k or YL))
wd = lambda i, w: fw(i, w)
labels = [KW.fx.label('NO MATCH', at=-1.0, pos=(0.5, Y), dur=1.0 + (fl(1) - 6) * F, **YL),
          lab('FRAUD', wd(1, 'fraud.'), fl(2) - 6),
          lab('PREGNANT', wd(2, 'Pregnant'), wd(2, 'birth') - 2),
          lab('WATCHED', wd(2, 'officer'), fl(3) - 6),
          lab('NO MATCH', wd(3, 'match'), fl(4) - 6),
          lab('HAIR', wd(4, 'hair,'), wd(4, 'cheek,') - 1),
          lab('CHEEK', wd(4, 'cheek,'), wd(4, 'skin') - 1),
          lab('SKIN', wd(4, 'skin'), wd(4, 'blood') - 1),
          lab('BLOOD', wd(4, 'blood'), wd(4, 'one') - 1),
          lab('ONE DNA', wd(4, 'one'), fl(5) - 6),
          lab('2ND DNA', wd(5, 'second'), fl(6) - 6),
          lab('CHIMERA', wd(6, 'chimera,'), fl(7) - 6),
          lab('DISMISSED', wd(7, 'dismissed'), CTA0 - 2),
          KW.fx.label('SHOCKED?', at=CTA0 * F, pos=(0.5, 0.30), dur=(FN - 10 - CTA0) * F, **YL),
          KW.fx.label('COMMENT BELOW', at=(CTA0 + 3) * F, pos=(0.5, 0.235), dur=(FN - 13 - CTA0) * F, color='white', size=0.5),
          KW.fx.label('NO MATCH', at=(FN - 9) * F, pos=(0.5, Y), dur=2.0, **YL)]
labels[-1].o['nopop'] = True
ep.sound(0.0, 'thud', 0.6)
for f_ in (26, 55, wd(1, 'fraud.'), wd(3, 'match'), wd(5, 'second'), wd(6, 'chimera,')): ep.sound(f_ * F, 'thud', 0.45)
ep.mouth_fix = True; ep.eyes_fix = True; ep.relight_after_pose = True
ep.shot(0.0, 'face', set='hospital', cast={maya: P}, fx=labels, cam=KW.cam.face(maya))
ep.run()
