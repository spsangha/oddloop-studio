"""Kinda Wild Films ep18 - 'What Cold Showers For 30 Days Do To Your Body'  Brief: kindawild/18_cold_shower/brief.md.
Facts: Buijze et al., PLOS ONE 2016 (3,018 adults, showers ended cold 30-90 s for 30 days: sickness absence -29 %, illness days
not different, more perceived energy) + Tipton, Eglin & Golden, J Physiol 1998 (cold shock gasp / hyperventilation / tachycardia
shrink after a few dips) + Shattock & Tipton, J Physiol 2012 (cold shock: gasp, hyperventilation, tachycardia, vasoconstriction).
Ben under a tiled shower (studio set, shirt off, framed chest-up), then on the clinic bed in his tee for the trial screen.
Body changes on Ben's own mesh: wet skin, gasp, fast chest breathing (shape key), a racing heart pulse on the chest (red <= 28 %),
pale hands (<= 28 %); by day 30 slow breathing, calm face, hands back to normal.  Ladder rung 8: breathing (chest rise).
"""
import sys, os, math; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kwkit as KW
os.environ.setdefault('KW_LIGHT', '1')
HERE = os.path.dirname(os.path.abspath(__file__))
ep = KW.Episode('ep_coldshower', injury="cold shower",
                voice_lines=[l.strip() for l in open(os.path.join(HERE, 'ep_coldshower.txt')) if l.strip()],
                music='sneaky_snitch', gap=0.6)
ep.tts_say = {3: "In a Dutch trial, three thousand people ended their showers cold for 30 days."}
ben = ep.person('Ben', 'civilian', 'eatmore-ben', gender='m', age='young', race='caucasian', hair='short02', tee='teal')

FPS = 24; F = 1.0 / FPS
try: from mathutils import Vector as V
except ImportError: V = None
def ease(x): x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)
def lerp(a, b, u): return a + (b - a) * u
R = {}
OV = float(os.environ.get('KW18_OV', 0.28))            # colour overlays (<= 0.30 lead rule)
FORCE = os.environ.get('KW18_FORCE')

KW.FACES.update({
    'warm': {'smile': 0.3, 'blink': 0.55},
    'shock': {'x_fear': 0.55, 'squint': 0.35},
    'gasp': {'x_surprise': 1.0},
    'pant': {'x_gap': 9.0, 'worry': 0.7, 'squint': 0.2},
    'shock2': {'x_gap': 5.0, 'worry': 0.45},
    'calmw': {'smile': 0.35, 'blink': 0.25},
    'easy': {'smile': 0.55},
    'huh': {'x_surprise': 0.35, 'worry': 0.35},
})
ep.waive = {"1 shots;": "brief: three kit shots (shower / clinic / loop); the hard cuts live in ep.cam_fn",
            "3 shots;": "brief: three kit shots (shower / clinic / loop); the hard cuts live in ep.cam_fn",
            "last shot must use cam=KW.cam.loop()": "brief: cam_fn cuts back to the frame-0 framing for the last 9 frames (the loop)",
            "HOOK cut <= 200 ms after the last word": "brief: CTA over the payoff shot, then the frame-0 cut",
            "shot face holds": "brief: cuts every 1.1-4 s inside cam_fn", "shot shower holds": "brief: cuts inside cam_fn",
            "shot clinic holds": "brief: cuts inside cam_fn",
            "HOOK first shot": "brief: hook cuts f22 (shower head) and f46 (close) live in cam_fn",
            "HOOK >= 2 cuts": "brief: hook cuts f22 and f46 live in cam_fn",
            "HOOK inside the body": "brief: vidIQ rule 1 person -> cutaway -> close-up; no xray in this story",
            "HOOK 3rd shot": "brief: third hook shot (close) at f46 in cam_fn"}
fw = lambda i, w: int(round(ep.word(i, w) * FPS))
fl = lambda i: int(round(ep.line(i) * FPS))
fle = lambda i: int(round((ep.line(i) + ep.vo_dur[i]) * FPS))
f_last = fle(6); FN = max(f_last + 36, 700); NF = FN + 1; ep.duration = round(NF / FPS, 4)
CTA0 = FN - 46; LOOPF = FN - 15
FCL = fl(5) - 4                                     # clinic from here (tee on)
F30 = fw(3, '30 days')                              # day 30: calm under the cold water (visible consequence ~56 %)
CUTS = [(0, 'MED0'), (22, 'HEAD'), (46, 'CLOSE'), (fl(1) - 4, 'FACE'), (fw(1, 'breathing') - 3, 'CHEST'),
        (fw(2, 'squeeze') - 4, 'HANDS'), (fl(3) - 4, 'MED1'), (fw(3, 'three') - 3, 'SIDE'), (F30 - 4, 'CLOSE'),
        (fl(4) - 4, 'FACE'), (fw(4, 'calm') - 4, 'CHEST'), (FCL, 'SCR'), (fw(5, 'fewer') - 2, 'BED'), (fl(6) - 4, 'SCR'),
        (CTA0 - 4, 'BFACE'), (LOOPF, 'MED0')]
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
def in_shower(f): return f < FCL or f >= LOOPF
def v_shock(f):                                     # cold-shock level 0..1
    if not in_shower(f) or f >= LOOPF: return 0.0
    return keys(f, [(6, 0.0), (50, 1.0), (fw(3, 'three') - 3, 1.0), (fw(3, 'three') + 6, 0.55), (F30 - 4, 0.45), (F30 + 6, 0.0)])
def v_heart(f): return keys(f, [(fw(2, 'heart') - 2, 0.0), (fw(2, 'heart') + 6, 1.0)]) if in_shower(f) and f < LOOPF else 0.0
def v_pale(f): return keys(f, [(fw(2, 'squeeze') - 2, 0.0), (fw(2, 'pale.') + 4, 1.0)]) * min(1.0, v_shock(f) / 0.5)
def phase(f, lo, hi):                               # integrated cycles: period lerp(lo, hi, shock) frames
    s = 0.0
    for k in range(int(f)): s += 1.0 / lerp(lo, hi, v_shock(k))
    return s
def breath(f):
    sh = v_shock(f); ph = phase(f, 92.0, 28.0)
    return lerp(0.30, 1.0, sh) * 0.5 * (1 - math.cos(2 * math.pi * ph))
def beat(f):
    ph = phase(f, 21.0, 9.6) % 1.0; return math.exp(-ph * 7.0) + 0.45 * math.exp(-max(0.0, ph - 0.22) * 9.0) * (ph > 0.22)

PS = (KW.pose('stand', at='centre', face='warm', head=(-6, 0, 0), blend=5 * F)
      .then(6 * F, face='shock', head=(4, 0, 0), act=KW.act.wince(at=12 * F), blend=6 * F)
      .then((fw(1, 'gasp,') - 5) * F, face='gasp', head=(-5, 0, 0), blend=5 * F)
      .then((fw(1, 'gasp,') + 14) * F, face='pant', head=(2, 0, 0), blend=8 * F)
      .then((fl(3) - 6) * F, face='shock2', blend=12 * F)
      .then((F30 - 4) * F, face='calmw', head=(-4, 0, 0), blend=8 * F)
      .then((fw(4, 'calm') - 2) * F, face='easy', blend=8 * F))
PC = (KW.pose('sit', at='bed_sit', face='calm', blend=5 * F)
      .then((fw(5, 'energetic') - FCL - 2) * F, face={'smile': 0.7}, blend=8 * F)
      .then((fl(6) - FCL - 2) * F, face='huh', head=(0, 0, 6), blend=8 * F))
PL = KW.pose('stand', at='centre', face='warm', head=(-6, 0, 0), blend=1 * F)
ep.blinks = {'Ben': [44, fl(1) - 4, fw(2, 'squeeze') - 4, fl(3) - 4, F30 - 3, fl(4) - 4, FCL + 2, fl(6) - 4]}

# ------------------------------------------------------------------ the shower (studio set, x = 60)
SX = 60.0
def tile_mat(name, axes, col=(0.50, 0.58, 0.63), size=0.15):
    import bpy
    m = bpy.data.materials.new(name); m.use_nodes = True; N = m.node_tree.nodes; Lk = m.node_tree.links.new
    bs = N['Principled BSDF']; bs.inputs['Roughness'].default_value = 0.12
    gm = N.new('ShaderNodeNewGeometry'); sp = N.new('ShaderNodeSeparateXYZ'); Lk(gm.outputs['Position'], sp.inputs[0])
    cb = N.new('ShaderNodeCombineXYZ'); Lk(sp.outputs[axes[0]], cb.inputs[0]); Lk(sp.outputs[axes[1]], cb.inputs[1])
    br = N.new('ShaderNodeTexBrick'); br.offset = 0.0; Lk(cb.outputs[0], br.inputs['Vector'])
    br.inputs['Scale'].default_value = 1.0; br.inputs['Brick Width'].default_value = size; br.inputs['Row Height'].default_value = size
    br.inputs['Mortar Size'].default_value = 0.0035; br.inputs['Mortar Smooth'].default_value = 0.2
    br.inputs['Color1'].default_value = (*col, 1); br.inputs['Color2'].default_value = (col[0] * 0.95, col[1] * 0.95, col[2] * 0.96, 1)
    br.inputs['Mortar'].default_value = (0.50, 0.53, 0.55, 1); Lk(br.outputs['Color'], bs.inputs['Base Color'])
    rm = N.new('ShaderNodeMapRange'); Lk(br.outputs['Fac'], rm.inputs[0]); rm.inputs[3].default_value = 0.12; rm.inputs[4].default_value = 0.6
    Lk(rm.outputs[0], bs.inputs['Roughness'])
    return m
def build_shower(c, EB):
    import bpy, kwlib as L
    for o in bpy.data.objects:
        if o.name.startswith('st_'): o.hide_render = True; o.hide_viewport = True
    by = EB.y; W_, YB, YF, HT = 0.95, by + 0.50, by - 1.0, 2.5
    back = tile_mat('kw18_tile_back', ('X', 'Z')); side = tile_mat('kw18_tile_side', ('Y', 'Z')); flo = tile_mat('kw18_tile_floor', ('X', 'Y'), (0.30, 0.34, 0.37), 0.10)
    L.box('kw18_back', (2 * W_ + 0.1, 0.05, HT), (SX, YB + 0.025, HT / 2), back, c, 0.0)
    L.box('kw18_left', (0.05, YB - YF, HT), (SX + W_ + 0.025, (YB + YF) / 2, HT / 2), side, c, 0.0)
    L.box('kw18_right', (0.05, YB - YF, HT), (SX - W_ - 0.025, (YB + YF) / 2, HT / 2), side, c, 0.0)
    L.box('kw18_floor', (2 * W_ + 0.1, YB - YF, 0.02), (SX, (YB + YF) / 2, 0.01), flo, c, 0.0)
    L.box('kw18_ceil', (2 * W_ + 0.1, YB - YF, 0.04), (SX, (YB + YF) / 2, HT + 0.02), back, c, 0.0)
    chrome = L.mat('kw18_chrome', (0.85, 0.86, 0.88), 0.08, 1.0)
    HZ = EB.z + 0.40; HY = by + 0.20; R['shead'] = V((SX + 0.0, HY, HZ - 0.02))
    L.cyl('kw18_arm', 0.012, YB - HY, (SX, (YB + HY) / 2, HZ + 0.04), chrome, c, (90, 0, 0), 20)
    L.cyl('kw18_neck', 0.012, 0.06, (SX, HY, HZ + 0.01), chrome, c, (0, 0, 0), 20)
    L.cyl('kw18_head', 0.085, 0.025, (SX, HY, HZ - 0.02), chrome, c, (-12, 0, 0), 48)
    L.cyl('kw18_valve', 0.04, 0.03, (SX + 0.30, YB - 0.01, EB.z - 0.45), chrome, c, (90, 0, 0), 32)
    L.box('kw18_lever', (0.012, 0.02, 0.09), (SX + 0.30, YB - 0.04, EB.z - 0.42), chrome, c, 0.004)
    wl = bpy.data.lights.new('kw18_key', 'AREA'); wl.energy = float(os.environ.get('KW18_KEY', 45)); wl.size = 0.8; wl.color = (0.93, 0.97, 1.0)
    lo = bpy.data.objects.new('kw18_key', wl); c.objects.link(lo); lo.location = (SX - 0.25, by - 0.55, HZ + 0.15); lo.rotation_euler = (math.radians(40), 0, math.radians(-20))
    R['lights'] = [lo]
    # water: thin streaks from the head, a cone towards the back of his head and shoulders
    import random, bmesh
    rnd = random.Random(18); mt = bpy.data.materials.new('kw18_water'); mt.use_nodes = True; bs = mt.node_tree.nodes['Principled BSDF']
    bs.inputs['Base Color'].default_value = (0.92, 0.96, 1.0, 1); bs.inputs['Roughness'].default_value = 0.05; bs.inputs['IOR'].default_value = 1.33
    for nm in ('Transmission Weight', 'Transmission'):
        if nm in bs.inputs: bs.inputs[nm].default_value = 0.35; break
    bs.inputs['Alpha'].default_value = 0.9
    me = bpy.data.meshes.new('kw18_streak'); bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=True, segments=6, radius1=0.0017, radius2=0.0017, depth=1.0); bm.to_mesh(me); bm.free()
    me.materials.append(mt); S = []
    for i in range(int(os.environ.get('KW18_NW', 240))):
        a = rnd.uniform(0, 2 * math.pi); r = 0.075 * math.sqrt(rnd.random())
        p0 = R['shead'] + V((r * math.cos(a), r * math.sin(a), -0.015))
        d = V((r * math.cos(a) * 2.2, r * math.sin(a) * 2.2 - 0.09, -1.0)).normalized()
        ob = bpy.data.objects.new('kw18_w%03d' % i, me); c.objects.link(ob); ob.visible_shadow = False
        S.append((ob, p0, d, rnd.uniform(0, 3.0), rnd.uniform(0.06, 0.12)))
    R['water'] = S

# ------------------------------------------------------------------ screen (clinic, same mount as ep14-17)
SCR_C = (-0.10, 0.17, 2.05); SCR_W, SCR_H = 0.46, 0.2875
CARDS = ('work', 'sick')
def card_of(f): return 1 if f >= fl(6) - 4 else 0
def build_screen(c):
    import bpy, kwlib as L
    tex = os.path.join(HERE, '..', '..', 'assets', 'real', 'tex', 'kw_cold')
    m = bpy.data.materials.new('kw18_screen'); m.use_nodes = True; nt = m.node_tree; N = nt.nodes; N.clear(); Lk = nt.links.new
    out = N.new('ShaderNodeOutputMaterial'); em = N.new('ShaderNodeEmission'); uv = N.new('ShaderNodeTexCoord')
    def img(nm):
        n = N.new('ShaderNodeTexImage'); n.image = bpy.data.images.load(os.path.join(tex, nm + '.png'), check_existing=True)
        n.interpolation = 'Cubic'; Lk(uv.outputs['UV'], n.inputs['Vector']); return n
    ims = [img(nm) for nm in CARDS]; prev = ims[0].outputs['Color']; R['scr'] = []
    for im in ims[1:]:
        v = N.new('ShaderNodeValue'); x = N.new('ShaderNodeMix'); x.data_type = 'RGBA'
        Lk(v.outputs[0], x.inputs['Factor']); Lk(prev, x.inputs['A']); Lk(im.outputs['Color'], x.inputs['B']); prev = x.outputs['Result']; R['scr'].append(v)
    Lk(prev, em.inputs['Color']); em.inputs['Strength'].default_value = float(os.environ.get('KW_SCRE', 1.4)); Lk(em.outputs[0], out.inputs[0])
    R['scre'] = em
    cx, cy, cz = SCR_C; tilt = math.radians(-8)
    dark = L.mat('kw18_bezel', (0.035, 0.038, 0.042), 0.35, 0.2); steel = L.mat('kw18_steel', (0.72, 0.73, 0.75), 0.3, 1.0)
    L.box('kw18_bezel', (SCR_W + 0.024, 0.03, SCR_H + 0.024), (cx, cy + 0.016, cz), dark, c, 0.008, (math.degrees(tilt), 0, 0))
    bpy.ops.mesh.primitive_plane_add(size=1.0); pl = bpy.context.active_object; pl.name = 'kw18_panel'
    for u_ in list(pl.users_collection): u_.objects.unlink(pl)
    c.objects.link(pl); pl.scale = (SCR_W, SCR_H, 1); pl.rotation_euler = (math.radians(90) + tilt, 0, 0); pl.location = (cx, cy - 0.0005, cz)
    pl.data.materials.append(m)
    for a in ('visible_diffuse', 'visible_glossy', 'visible_transmission'): setattr(pl, a, a == 'visible_glossy')
    L.cyl('kw18_boom', 0.016, 2.80 - cz, (cx, cy + 0.06, (2.80 + cz) / 2), steel, c, (0, 0, 0), 20)
    L.box('kw18_mount', (0.12, 0.04, 0.08), (cx, cy + 0.045, cz), dark, c, 0.005)


def strip_shirt(pp, on):
    """shower: tee off (body masks off); clinic: tee on."""
    hg = pp.hg
    if 'shirt' not in R:
        R['shirt'] = [o for o in pp.parts if o.name.startswith('HG_TSHIRT') or 'tee print' in o.name]
        for o in R['shirt']: pp.parts.remove(o)
        R['masks'] = [m for m in hg.body.modifiers if m.type == 'MASK' and m.name in ('kw_hide', 'mask_torso', 'mask_arms_short')]
        for m in R['masks']:
            if m in hg.xray_mods: hg.xray_mods.remove(m)
    for o in R['shirt']: o.hide_render = not on; o.hide_viewport = not on
    for m in R['masks']: m.show_render = on; m.show_viewport = on


# ------------------------------------------------------------------ Ben's own mesh: breathing chest, heart pulse, pale hands, wet skin
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
            if k.mute or abs(k.value) < 1e-6 or k.name.startswith('kw18'): continue
            k.data.foreach_get('co', tmp); k.relative_key.data.foreach_get('co', ref)
            mix += k.value * (tmp - ref).reshape(-1, 3)
    return co, mix

def body_keys(hg):
    import numpy as np, bpy
    body = next(o for o in hg.meshes if o.name.startswith('HG_Body'))
    co, c = rest_local(body); n = len(c)
    B2M = np.array(body.matrix_world.inverted() @ hg.rig.matrix_world)
    bone = lambda nm: B2M[:3, :3] @ np.array(hg.rig.data.bones[nm].head_local) + B2M[:3, 3]
    E = (bone('eyeball.L') + bone('eyeball.R')) / 2
    nrm = np.empty(n * 3); body.data.vertices.foreach_get('normal', nrm); nrm = nrm.reshape(-1, 3)
    d = c - E
    m = (np.abs(d[:, 0]) < 0.02) & (np.abs(d[:, 2] + 0.33) < 0.02)
    cy = c[m][:, 1].min() if m.any() else E[1]
    ch = np.exp(-(d[:, 0] ** 2) / (2 * 0.10 ** 2) - ((d[:, 2] + 0.33) ** 2) / (2 * 0.08 ** 2)) * (c[:, 1] < cy + 0.08) * (np.abs(d[:, 0]) < 0.2)
    hp = np.array([E[0] + 0.045, cy, E[2] - 0.34])
    heart = np.exp(-np.sum((c - hp) ** 2, axis=1) / (2 * 0.05 ** 2))
    gi = {g.index for g in body.vertex_groups if any(k in g.name.lower() for k in ('hand', 'thumb', 'f_', 'palm', 'finger'))}
    hand = np.zeros(n)
    for v in body.data.vertices:
        for g in v.groups:
            if g.group in gi: hand[v.index] += g.weight
    hand = np.clip(hand + np.clip((-d[:, 2] - 0.20) / 0.06, 0, 1), 0, 1)   # pale: hands + all skin below the neck (face/lips stay natural)
    print('kw18 chest y', round(float(cy - E[1]), 3), 'chest verts', int((ch > 0.3).sum()), 'heart', int((heart > 0.3).sum()), 'hand', int((hand > 0.3).sum()), 'groups', len(gi))
    if body.data.shape_keys is None: body.shape_key_add(name='Basis', from_mix=False)
    k = body.shape_key_add(name='kw18_breath', from_mix=False); k.slider_max = 1.5; k.value = 0.0
    k.data.foreach_set('co', (co + ch[:, None] * (0.008 * nrm + np.array([0, 0, 0.004]))).ravel())
    ca = body.data.color_attributes.get('kw18g') or body.data.color_attributes.new('kw18g', 'FLOAT_COLOR', 'POINT')
    ca.data.foreach_set('color', np.stack([heart, hand, np.zeros(n), np.ones(n)], 1).astype(np.float32).ravel())
    vh, vp, vw = [], [], []
    for mt in body.data.materials:
        if not mt or not mt.use_nodes or not mt.name.startswith('.Human'): continue
        N = mt.node_tree.nodes; Lk = mt.node_tree.links.new
        bs = next(q for q in N if q.bl_idname == 'ShaderNodeBsdfPrincipled'); bc = bs.inputs['Base Color']
        if not bc.is_linked: continue
        at = N.new('ShaderNodeAttribute'); at.attribute_name = 'kw18g'; sp = N.new('ShaderNodeSeparateColor'); Lk(at.outputs['Color'], sp.inputs[0])
        cur = bc.links[0].from_socket
        for ch_, col, lst in ((1, (0.78, 0.79, 0.84, 1.0), vp), (0, (0.62, 0.03, 0.05, 1.0), vh)):
            a = N.new('ShaderNodeValue'); a.outputs[0].default_value = 0.0; lst.append(a)
            m1 = N.new('ShaderNodeMath'); m1.operation = 'MULTIPLY'; Lk(sp.outputs[ch_], m1.inputs[0]); Lk(a.outputs[0], m1.inputs[1])
            mx = N.new('ShaderNodeMix'); mx.data_type = 'RGBA'; Lk(m1.outputs[0], mx.inputs['Factor']); Lk(cur, mx.inputs['A'])
            mx.inputs['B'].default_value = col; cur = mx.outputs['Result']
        Lk(cur, bc)
        ri = bs.inputs['Roughness']; w = N.new('ShaderNodeValue'); w.outputs[0].default_value = 1.0; vw.append(w)
        mr = N.new('ShaderNodeMath'); mr.operation = 'MULTIPLY'; Lk(w.outputs[0], mr.inputs[1])
        if ri.is_linked: Lk(ri.links[0].from_socket, mr.inputs[0])
        else: mr.inputs[0].default_value = ri.default_value
        Lk(mr.outputs[0], ri)
    R['ov'] = (vh, vp, vw); print('kw18 overlay nodes', len(vh)); R['body'] = body

def eyes(rt, who):
    rg = rt.actors[who].p.hg.rig; W_ = rg.matrix_world
    EL = W_ @ rg.pose.bones['eyeball.L'].head; ER = W_ @ rg.pose.bones['eyeball.R'].head; return EL, ER, (EL + ER) / 2

def build(rt):
    import bpy
    c = bpy.data.collections.get('kw_ep18') or bpy.data.collections.new('kw_ep18')
    if c.name not in bpy.context.scene.collection.children: bpy.context.scene.collection.children.link(c)
    import kwlook as Q_; Q_.LOOP_T = FN / FPS
    hg = rt.actors[ben].p.hg; W_ = hg.rig.matrix_world
    EB = (W_ @ hg.rig.data.bones['eyeball.L'].head_local + W_ @ hg.rig.data.bones['eyeball.R'].head_local) / 2
    if abs(EB.x - SX) > 2.0: EB = V((SX, 0.0, 1.62))
    R['EB0'] = EB.copy(); print('kw18 eyes at build', tuple(round(v, 3) for v in EB))
    build_shower(c, EB); build_screen(c); body_keys(hg); strip_shirt(rt.actors[ben].p, False)
ep.build_hook = build

def set_key(hg, name, v):
    for o in hg.meshes:
        kb = o.data.shape_keys.key_blocks if o.data.shape_keys else None
        k = kb.get(name) if kb else None
        if k is not None: k.value = v

def frame_hook(rt, t):
    import bpy, kwlook as Q_
    Q_.LOOP_T = FN / FPS
    f = t * FPS; hb = rt.actors[ben].p.hg; sh = in_shower(f)
    strip_shirt(rt.actors[ben].p, not sh)
    fv = float(FORCE) if FORCE is not None else None
    set_key(hb, 'kw18_breath', breath(f) if sh else 0.25 * 0.5 * (1 - math.cos(2 * math.pi * f / 92.0)))
    vh, vp, vw = R['ov']
    hv = (fv if fv is not None else v_heart(f)) * (0.35 + 0.65 * max(v_shock(f), 0.0)) * (0.55 + 0.45 * beat(f))
    pv = fv if fv is not None else v_pale(f)
    for n_ in vh: n_.outputs[0].default_value = OV * hv
    for n_ in vp: n_.outputs[0].default_value = OV * pv
    for n_ in vw: n_.outputs[0].default_value = 0.55 if sh else 1.0
    k = card_of(f)
    for i, v in enumerate(R['scr']): v.outputs[0].default_value = 1.0 if k >= i + 1 else 0.0
    R['scre'].inputs['Strength'].default_value = float(os.environ.get('KW_SCRE', 1.4)) if not sh else 0.0
    for lo in R['lights']: lo.hide_render = not sh
    bpy.context.view_layer.update()
    _, _, EB = eyes(rt, ben)
    top = EB.z + 0.11
    for ob, p0, d, off, ln in R['water']:
        if not sh: ob.hide_render = True; continue
        s = (f * 0.13 + off) % 3.0; p = p0 + d * s
        rel = p - EB; inside = (rel.x / 0.25) ** 2 + ((rel.y - 0.03) / 0.17) ** 2 < 1.0 and p.z < top
        hid = p.z < 0.02 or inside or (f < 4 and s > 1.2)
        ob.hide_render = hid
        if not hid:
            ob.location = p - d * (ln / 2); ob.rotation_euler = d.to_track_quat('Z', 'Y').to_euler(); ob.scale = (1, 1, ln)
    sh_ = rt.ep.shot_at(t); rt.FX.update(sh_, t - sh_.t, t)
ep.frame_hook = frame_hook

def look(tg, dirv, dist, lens, fst=8.0, foc=None):
    dv = V(dirv).normalized(); return tg + dv * dist, tg, V((0, 0, 1)), lens, fst, (foc if foc is not None else tg)
def cam_fn(rt, t):
    import bpy
    f = t * FPS; bpy.context.view_layer.update(); shot, u = shot_of(f)
    _, _, EB = eyes(rt, ben)
    push = lambda a, b: a * (b / a) ** ease(u)
    if shot in ('MED0', 'MED1'):                                    # chest-up in the shower (jeans never in frame)
        tg = EB + V((0.0, 0.0, -0.14)); d_ = push(1.05, 0.95) if shot == 'MED0' and f < LOOPF else (push(1.0, 0.9) if shot == 'MED1' else 1.05)
        return look(tg, (-0.45, -1.0, 0.10), d_, 50.0, 8.0, EB)
    if shot == 'HEAD':                                             # cutaway: the shower head, cold water pouring
        tg = R['shead'] + V((0, -0.04, -0.10)); return look(tg, (-1.0, -0.55, -0.05), push(0.62, 0.54), 50.0, 8.0, tg)
    if shot == 'CLOSE':
        tg = EB + V((0, 0, -0.05)); return look(tg, (-0.25, -1.0, 0.02), push(0.55, 0.46), 85.0, 11.0, EB)
    if shot == 'FACE':
        tg = EB + V((0, 0, -0.04)); return look(tg, (-0.55, -1.0, 0.02), push(0.50, 0.43), 85.0, 11.0, EB)
    if shot == 'SIDE':                                             # profile under the spray
        tg = EB + V((0, 0.02, -0.08)); return look(tg, (-1.0, -0.35, 0.08), push(0.78, 0.70), 70.0, 9.0, EB)
    if shot == 'CHEST':                                            # chest: breathing + heart pulse (+ hand)
        tg = EB + V((0.02, -0.02, -0.20)); return look(tg, (-0.35, -1.0, 0.06), push(0.95, 0.85), 50.0, 8.0, tg)
    if shot == 'HANDS':                                            # other-side torso: skin goes pale/cool
        tg = EB + V((0.0, -0.02, -0.24)); return look(tg, (0.35, -1.0, 0.06), push(0.95, 0.85), 50.0, 8.0, tg)
    if shot in ('BED', 'BFACE'):
        tg = EB + V((0.0, 0.0, -0.20)); return look(tg, (-0.75, -1.0, 0.05), push(1.25, 1.12), 50.0, 8.0, EB)
    tg = V(SCR_C) + V((0, 0, -0.15))                                 # SCR: screen + Ben below it
    return look(tg, (0.06, -1.0, 0.25), push(1.55, 1.45), 50.0, 8.0, V(SCR_C))
ep.cam_fn = cam_fn

YL = dict(color='yellow', size=1.2); Y = 0.89
ep.label_outline = True; ep.label_maxw = 820.0; ep.label_lens_fix = True
def lab(txt, f0, f1, **k): return KW.fx.label(txt, at=f0 * F, pos=(0.5, Y), dur=(f1 - f0) * F, **(k or YL))
wd = fw
labels = [KW.fx.label('COLD', at=-1.0, pos=(0.5, Y), dur=1.0 + (fl(1) - 6) * F, **YL),
          lab('GASP', wd(1, 'gasp,'), wd(1, 'breathing') - 1),
          lab('BREATHING', wd(1, 'breathing'), fl(2) - 6),
          lab('RACING', wd(2, 'races,'), wd(2, 'squeeze') - 1),
          lab('SQUEEZE', wd(2, 'squeeze'), wd(2, 'pale.') - 1),
          lab('PALE', wd(2, 'pale.'), fl(3) - 6),
          lab('TRIAL', wd(3, 'trial,'), wd(3, 'three') - 1),
          lab('3,000', wd(3, 'three'), F30 - 1),
          lab('DAY 30', F30, fl(4) - 6),
          lab('CALM', wd(4, 'calm'), fl(5) - 6),
          lab('ENERGY', wd(5, 'energetic'), wd(5, 'fewer') - 1),
          lab('-29%', wd(5, 'fewer'), fl(6) - 6),
          lab('SAME', wd(6, 'sick'), CTA0 - 2),
          KW.fx.label('TRY IT?', at=CTA0 * F, pos=(0.5, 0.30), dur=(LOOPF - 1 - CTA0) * F, **YL),
          KW.fx.label('COMMENT BELOW', at=(CTA0 + 3) * F, pos=(0.5, 0.235), dur=(LOOPF - 4 - CTA0) * F, color='white', size=0.5),
          KW.fx.label('COLD', at=(LOOPF) * F, pos=(0.5, Y), dur=2.0, **YL)]
labels[-1].o['nopop'] = True
ep.sound(0.0, 'thud', 0.6)
for f_ in (wd(1, 'gasp,'), wd(2, 'races,'), F30, fl(6)): ep.sound(f_ * F, 'thud', 0.45)
ep.mouth_fix = True; ep.eyes_fix = True; ep.relight_after_pose = True
def part(a, b):           # labels are shot-local: split them by start and shift
    out = []
    for lb in labels:
        at = lb.o.get('at', 0)
        if a * F - 1e-6 <= at < b * F - 1e-6 or (a == 0 and at < 0): lb.o['at'] = at - a * F if a else at; out.append(lb)
    return out
LS, LC, LL = part(0, FCL), part(FCL, LOOPF), part(LOOPF, FN + 99)
ep.shot(0.0, 'shower', set='studio', cast={ben: PS}, fx=LS, cam=KW.cam.face(ben))
ep.shot(FCL * F, 'clinic', set='hospital', cast={ben: PC}, fx=LC, cam=KW.cam.face(ben))
ep.shot((LOOPF) * F, 'loop', set='studio', cast={ben: PL}, fx=LL, cam=KW.cam.face(ben))
ep.run()
