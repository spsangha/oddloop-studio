"""Kinda Wild Films ep22 - 'Every Shower Gives Her Hives'  Brief: kindawild/22_water_allergy/brief.md.
Facts: DermNet 'Aquagenic urticaria' (< 100 cases reported; any water temperature, salt or pH, sweat and tears; water reacts with
unknown components in the skin -> histamine from mast cells; 1-3 mm weals with red flares on the trunk and upper arms within 20-30
min; rarely wheezing; weals fade in 30-120 min; daily non-sedating antihistamine), Cleveland Clinic 'Rare allergies' (fewer than
100 cases; regardless of water temperature or source; freshwater, saltwater, sweat and tears), Allergy & Asthma Network.
Maya (generic adult) under a tiled shower in her tee (studio set, chest-up), then on the clinic bed with the doctor + screen.
Body changes on Maya's own mesh: wet skin, hives on her forearm (hook), a tear runs down her cheek and raises a welt (face overlay
<= 30 %, lips natural), the hives spread over her arms, neck and upper chest (~55 %), then fade in the clinic.
"""
import sys, os, math; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kwkit as KW
os.environ.setdefault('KW_LIGHT', '1')
os.environ.setdefault('KW_NAILS', '1')                 # ladder rung 9 (nails + knuckle creases) proven on this Short
HERE = os.path.dirname(os.path.abspath(__file__))
ep = KW.Episode('ep_waterallergy', injury="hives",
                voice_lines=[l.strip() for l in open(os.path.join(HERE, 'ep_waterallergy.txt')) if l.strip()],
                music='sneaky_snitch', gap=0.6)
maya = ep.person('Maya', 'civilian', 'cast-maya', gender='f', age='young', race='hispanic', hair='short02', tee='red')
doc = ep.person('Howard', 'scientist', 'eatmore-sci', gender='m', age='old', race='caucasian', hair='short02')

FPS = 24; F = 1.0 / FPS
try: from mathutils import Vector as V
except ImportError: V = None
def ease(x): x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)
def lerp(a, b, u): return a + (b - a) * u
R = {}
OV = float(os.environ.get('KW22_OV', 0.30))            # hive redness (<= 0.30 lead rule on faces; lips excluded)
FORCE = os.environ.get('KW22_FORCE')

KW.FACES.update({
    'warm': {'smile': 0.3, 'blink': 0.4},
    'itch': {'x_wince': 0.55, 'worry': 0.4},
    'oops': {'x_surprise': 0.75},
    'sad': {'worry': 0.8, 'frown': 0.3, 'blink': 0.25},
    'huh': {'x_surprise': 0.35, 'worry': 0.35},
    'calm2': {'smile': 0.25},
    'easy': {'smile': 0.55},
})
ep.waive = {"1 shots;": "brief: three kit shots (shower / clinic / loop); the hard cuts live in ep.cam_fn",
            "3 shots;": "brief: three kit shots (shower / clinic / loop); the hard cuts live in ep.cam_fn",
            "last shot must use cam=KW.cam.loop()": "brief: cam_fn cuts back to the frame-0 framing for the last 15 frames (the loop)",
            "HOOK cut <= 200 ms after the last word": "brief: CTA over the payoff shot, then the frame-0 cut",
            "shot shower holds": "brief: cuts inside cam_fn", "shot clinic holds": "brief: cuts inside cam_fn",
            "HOOK first shot": "brief: hook cuts f22 (shower head) and f46 (forearm close) live in cam_fn",
            "HOOK >= 2 cuts": "brief: hook cuts f22 and f46 live in cam_fn",
            "HOOK inside the body": "brief: vidIQ rule 1 person -> cutaway -> close-up; no xray in this story",
            "HOOK 3rd shot": "brief: third hook shot (forearm close) at f46 in cam_fn"}
fw = lambda i, w: int(round(ep.word(i, w) * FPS))
fl = lambda i: int(round(ep.line(i) * FPS))
fle = lambda i: int(round((ep.line(i) + ep.vo_dur[i]) * FPS))
f_last = fle(6); FN = max(f_last + 36, 700); NF = FN + 1; ep.duration = round(NF / FPS, 4)
CTA0 = FN - 46; LOOPF = FN - 15
FCL = fl(5) - 4                                     # clinic from here
TT0 = fw(2, 'tears') - 6; TT1 = TT0 + 30            # the tear runs down her cheek
FSP = fw(4, 'spread') - 2                           # hives spread (visible consequence)
CUTS = [(0, 'MED0'), (22, 'HEAD'), (46, 'ARM'), (fl(1) - 4, 'FACE'), (fw(1, 'rain') - 3, 'SIDE'),
        (fl(2) - 4, 'CLOSE'), (fl(3) - 4, 'ARM'), (fl(4) - 4, 'MED1'), (FSP + 10, 'CHEST'), (FCL, 'BED'),
        (fw(5, 'welts') - 3, 'BFACE'), (fl(6) - 4, 'SCR'), (CTA0 - 4, 'BFACE'), (LOOPF, 'MED0')]
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
FADE = [(FCL, 1.0), (fw(5, 'fade') + 4, 0.75), (fw(5, 'two') + 30, 0.25)]
def v_arm(f):                                       # forearm hives (hook), stay
    if f >= LOOPF: return 0.0
    return keys(f, [(30, 0.0), (58, 1.0)] + FADE)
def v_spread(f):                                    # arms, neck, upper chest
    if f >= LOOPF: return 0.0
    return keys(f, [(FSP, 0.0), (FSP + 26, 1.0)] + FADE)
def v_cheek(f):
    if f >= LOOPF: return 0.0
    return keys(f, [(TT0 + 14, 0.0), (TT1 + 6, 1.0)] + FADE)
def pulse(f): return 0.85 + 0.15 * math.sin(2 * math.pi * f / 20.0) if fl(3) - 4 <= f < fl(4) - 4 else 1.0   # histamine line: flare throbs

ARMUP = KW.hand.inspect(dist=0.30, offset=(0.10, -0.20))
PS = (KW.pose('stand', at='centre', face='warm', head=(-6, 0, 0), blend=5 * F)
      .then(26 * F, face='oops', left=ARMUP, head=(10, 0, 0), look=None, blend=8 * F)
      .then((fl(1) - 6) * F, face='itch', left=None, head=(-2, 0, 0), blend=8 * F)
      .then((fl(2) - 6) * F, face='sad', head=(0, 0, -4), blend=10 * F)
      .then((fl(3) - 6) * F, face='itch', left=ARMUP, head=(10, 0, 0), blend=8 * F)
      .then((fl(4) - 6) * F, face='itch', left=None, head=(-2, 0, 0), blend=8 * F))
PC = (KW.pose('sit', at='bed_sit', face='itch', blend=5 * F)
      .then((fw(5, 'welts') - FCL - 2) * F, face='calm2', blend=10 * F)
      .then((fl(6) - FCL - 2) * F, face='huh', head=(0, 0, 6), blend=8 * F)
      .then((CTA0 - FCL - 4) * F, face='easy', head=(0, 0, 0), blend=8 * F))
PD = KW.pose('stand', at='bedside_l', face='focus', act=KW.act.nod(at=1.0, n=1), blend=5 * F)
PL = KW.pose('stand', at='centre', face='warm', head=(-6, 0, 0), blend=1 * F)
ep.blinks = {'Maya': [44, fl(1) - 4, fl(2) - 4, fl(3) - 4, fl(4) - 4, FCL + 2, fl(6) - 4]}

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
    back = tile_mat('kw22_tile_back', ('X', 'Z')); side = tile_mat('kw22_tile_side', ('Y', 'Z')); flo = tile_mat('kw22_tile_floor', ('X', 'Y'), (0.30, 0.34, 0.37), 0.10)
    L.box('kw22_back', (2 * W_ + 0.1, 0.05, HT), (SX, YB + 0.025, HT / 2), back, c, 0.0)
    L.box('kw22_left', (0.05, YB - YF, HT), (SX + W_ + 0.025, (YB + YF) / 2, HT / 2), side, c, 0.0)
    L.box('kw22_right', (0.05, YB - YF, HT), (SX - W_ - 0.025, (YB + YF) / 2, HT / 2), side, c, 0.0)
    L.box('kw22_floor', (2 * W_ + 0.1, YB - YF, 0.02), (SX, (YB + YF) / 2, 0.01), flo, c, 0.0)
    L.box('kw22_ceil', (2 * W_ + 0.1, YB - YF, 0.04), (SX, (YB + YF) / 2, HT + 0.02), back, c, 0.0)
    chrome = L.mat('kw22_chrome', (0.85, 0.86, 0.88), 0.08, 1.0)
    HZ = EB.z + 0.40; HY = by + 0.20; R['shead'] = V((SX + 0.0, HY, HZ - 0.02))
    L.cyl('kw22_arm', 0.012, YB - HY, (SX, (YB + HY) / 2, HZ + 0.04), chrome, c, (90, 0, 0), 20)
    L.cyl('kw22_neck', 0.012, 0.06, (SX, HY, HZ + 0.01), chrome, c, (0, 0, 0), 20)
    L.cyl('kw22_head', 0.085, 0.025, (SX, HY, HZ - 0.02), chrome, c, (-12, 0, 0), 48)
    L.cyl('kw22_valve', 0.04, 0.03, (SX + 0.30, YB - 0.01, EB.z - 0.45), chrome, c, (90, 0, 0), 32)
    L.box('kw22_lever', (0.012, 0.02, 0.09), (SX + 0.30, YB - 0.04, EB.z - 0.42), chrome, c, 0.004)
    wl = bpy.data.lights.new('kw22_key', 'AREA'); wl.energy = float(os.environ.get('KW22_KEY', 45)); wl.size = 0.8; wl.color = (0.93, 0.97, 1.0)
    lo = bpy.data.objects.new('kw22_key', wl); c.objects.link(lo); lo.location = (SX - 0.25, by - 0.55, HZ + 0.15); lo.rotation_euler = (math.radians(40), 0, math.radians(-20))
    R['lights'] = [lo]
    # water: thin streaks from the head, a cone towards the back of his head and shoulders
    import random, bmesh
    rnd = random.Random(22); mt = bpy.data.materials.new('kw22_water'); mt.use_nodes = True; bs = mt.node_tree.nodes['Principled BSDF']
    bs.inputs['Base Color'].default_value = (0.92, 0.96, 1.0, 1); bs.inputs['Roughness'].default_value = 0.05; bs.inputs['IOR'].default_value = 1.33
    for nm in ('Transmission Weight', 'Transmission'):
        if nm in bs.inputs: bs.inputs[nm].default_value = 0.35; break
    bs.inputs['Alpha'].default_value = 0.9
    me = bpy.data.meshes.new('kw22_streak'); bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=True, segments=6, radius1=0.0017, radius2=0.0017, depth=1.0); bm.to_mesh(me); bm.free()
    me.materials.append(mt); S = []
    for i in range(int(os.environ.get('KW22_NW', 240))):
        a = rnd.uniform(0, 2 * math.pi); r = 0.075 * math.sqrt(rnd.random())
        p0 = R['shead'] + V((r * math.cos(a), r * math.sin(a), -0.015))
        d = V((r * math.cos(a) * 2.2, r * math.sin(a) * 2.2 - 0.09, -1.0)).normalized()
        ob = bpy.data.objects.new('kw22_w%03d' % i, me); c.objects.link(ob); ob.visible_shadow = False
        S.append((ob, p0, d, rnd.uniform(0, 3.0), rnd.uniform(0.06, 0.12)))
    R['water'] = S


# ------------------------------------------------------------------ screen (clinic, same mount as ep14-18)
SCR_C = (-0.10, 0.17, 2.05); SCR_W, SCR_H = 0.46, 0.2875
CARDS = ('cases', 'pills')
def card_of(f): return 1 if f >= fw(6, 'antihistamines') - 4 else 0
def build_screen(c):
    import bpy, kwlib as L
    tex = os.path.join(HERE, '..', '..', 'assets', 'real', 'tex', 'kw_water')
    m = bpy.data.materials.new('kw22_screen'); m.use_nodes = True; nt = m.node_tree; N = nt.nodes; N.clear(); Lk = nt.links.new
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
    dark = L.mat('kw22_bezel', (0.035, 0.038, 0.042), 0.35, 0.2); steel = L.mat('kw22_steel', (0.72, 0.73, 0.75), 0.3, 1.0)
    L.box('kw22_bezel', (SCR_W + 0.024, 0.03, SCR_H + 0.024), (cx, cy + 0.016, cz), dark, c, 0.008, (math.degrees(tilt), 0, 0))
    bpy.ops.mesh.primitive_plane_add(size=1.0); pl = bpy.context.active_object; pl.name = 'kw22_panel'
    for u_ in list(pl.users_collection): u_.objects.unlink(pl)
    c.objects.link(pl); pl.scale = (SCR_W, SCR_H, 1); pl.rotation_euler = (math.radians(90) + tilt, 0, 0); pl.location = (cx, cy - 0.0005, cz)
    pl.data.materials.append(m)
    for a in ('visible_diffuse', 'visible_glossy', 'visible_transmission'): setattr(pl, a, a == 'visible_glossy')
    L.cyl('kw22_boom', 0.016, 2.80 - cz, (cx, cy + 0.06, (2.80 + cz) / 2), steel, c, (0, 0, 0), 20)
    L.box('kw22_mount', (0.12, 0.04, 0.08), (cx, cy + 0.045, cz), dark, c, 0.005)


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
            if k.mute or abs(k.value) < 1e-6 or k.name.startswith('kw22'): continue
            k.data.foreach_get('co', tmp); k.relative_key.data.foreach_get('co', ref)
            mix += k.value * (tmp - ref).reshape(-1, 3)
    return co, mix


# ------------------------------------------------------------------ Maya's own mesh: hives (forearm / spread / cheek), wet skin, the tear
def body_keys(hg):
    import numpy as np, bpy
    body = next(o for o in hg.meshes if o.name.startswith('HG_Body'))
    co, c = rest_local(body); n = len(c)
    B2M = np.array(body.matrix_world.inverted() @ hg.rig.matrix_world)
    bone = lambda nm: B2M[:3, :3] @ np.array(hg.rig.data.bones[nm].head_local) + B2M[:3, 3]
    EL_, ER_ = bone('eyeball.L'), bone('eyeball.R'); E = (EL_ + ER_) / 2
    EC = EL_ if EL_[0] < ER_[0] else ER_            # the eye on the camera side (cameras sit at -x)
    d = c - E
    def grp(keys_):
        gi = {g.index for g in body.vertex_groups if any(k in g.name.lower() for k in keys_)}; w = np.zeros(n)
        for v in body.data.vertices:
            for g in v.groups:
                if g.group in gi: w[v.index] += g.weight
        return np.clip(w, 0, 1), len(gi)
    fore, nf = grp(('lowerarm',)); upper, nu = grp(('upperarm',))
    neck = np.clip((-d[:, 2] - 0.13) / 0.03, 0, 1) * np.clip((d[:, 2] + 0.40) / 0.04, 0, 1) * (np.abs(d[:, 0]) < 0.17)
    spread = np.clip(fore + upper + neck, 0, 1)
    fy = c[(np.abs(c[:, 0] - EC[0]) < 0.01) & (np.abs(d[:, 2] + 0.035) < 0.006)][:, 1]
    fy = fy.min() if len(fy) else EC[1] - 0.02
    cheek = np.exp(-((c[:, 0] - EC[0]) ** 2 + (d[:, 2] + 0.036) ** 2) / (2 * 0.011 ** 2)) * (c[:, 1] < fy + 0.012)
    lip = np.exp(-((d[:, 0]) ** 2) / (2 * 0.03 ** 2) - ((d[:, 2] + 0.085) ** 2) / (2 * 0.015 ** 2))
    cheek = np.clip(cheek - 2 * lip, 0, 1)
    # tear path: front-most cheek vertices under the inner half of the eye, top to bottom
    path = []
    for zo in np.linspace(-0.012, -0.055, 10):
        m = (np.abs(c[:, 0] - (EC[0] + 0.006 * np.sign(E[0] - EC[0]))) < 0.004) & (np.abs(d[:, 2] - zo) < 0.003)
        idx = np.nonzero(m)[0]
        if len(idx): path.append(int(idx[np.argmin(c[idx, 1])]))
    R['tpath'] = path
    print('kw22 groups fore', nf, 'upper', nu, 'verts fore', int((fore > 0.3).sum()), 'spread', int((spread > 0.3).sum()), 'cheek', int((cheek > 0.3).sum()), 'tear path', len(path))
    ca = body.data.color_attributes.get('kw22h') or body.data.color_attributes.new('kw22h', 'FLOAT_COLOR', 'POINT')
    ca.data.foreach_set('color', np.stack([fore, spread, cheek, np.ones(n)], 1).astype(np.float32).ravel())
    va, vs, vc, vw = [], [], [], []
    for mt in body.data.materials:
        if not mt or not mt.use_nodes or not mt.name.startswith('.Human'): continue
        N = mt.node_tree.nodes; Lk = mt.node_tree.links.new
        bs = next(q for q in N if q.bl_idname == 'ShaderNodeBsdfPrincipled'); bc = bs.inputs['Base Color']
        if not bc.is_linked: continue
        at = N.new('ShaderNodeAttribute'); at.attribute_name = 'kw22h'; sp = N.new('ShaderNodeSeparateColor'); Lk(at.outputs['Color'], sp.inputs[0])
        acc = None
        for ch_, lst in ((0, va), (1, vs), (2, vc)):
            a = N.new('ShaderNodeValue'); a.outputs[0].default_value = 0.0; lst.append(a)
            m1 = N.new('ShaderNodeMath'); m1.operation = 'MULTIPLY'; Lk(sp.outputs[ch_], m1.inputs[0]); Lk(a.outputs[0], m1.inputs[1])
            if acc is None: acc = m1.outputs[0]
            else:
                mm = N.new('ShaderNodeMath'); mm.operation = 'MAXIMUM'; Lk(acc, mm.inputs[0]); Lk(m1.outputs[0], mm.inputs[1]); acc = mm.outputs[0]
        tc = N.new('ShaderNodeTexCoord'); vo = N.new('ShaderNodeTexVoronoi'); vo.inputs['Scale'].default_value = float(os.environ.get('KW22_SCALE', 170.0))
        Lk(tc.outputs['Object'], vo.inputs['Vector'])
        sm = N.new('ShaderNodeMapRange'); Lk(vo.outputs['Distance'], sm.inputs[0]); sm.inputs[1].default_value = 0.42; sm.inputs[2].default_value = 0.05
        sm.inputs[3].default_value = 0.0; sm.inputs[4].default_value = 1.0; sm.interpolation_type = 'SMOOTHSTEP'      # 1 at the wheal centre
        wm = N.new('ShaderNodeMath'); wm.operation = 'MULTIPLY'; Lk(sm.outputs[0], wm.inputs[0]); Lk(acc, wm.inputs[1])
        fm = N.new('ShaderNodeMath'); fm.operation = 'MULTIPLY'; fm.inputs[1].default_value = OV; Lk(acc, fm.inputs[0])
        cur = bc.links[0].from_socket
        mx = N.new('ShaderNodeMix'); mx.data_type = 'RGBA'; Lk(fm.outputs[0], mx.inputs['Factor']); Lk(cur, mx.inputs['A'])
        mx.inputs['B'].default_value = (0.72, 0.12, 0.10, 1.0); cur = mx.outputs['Result']                 # red flare
        wf = N.new('ShaderNodeMath'); wf.operation = 'MULTIPLY'; wf.inputs[1].default_value = 0.35; Lk(wm.outputs[0], wf.inputs[0])
        mx2 = N.new('ShaderNodeMix'); mx2.data_type = 'RGBA'; Lk(wf.outputs[0], mx2.inputs['Factor']); Lk(cur, mx2.inputs['A'])
        mx2.inputs['B'].default_value = (0.95, 0.74, 0.68, 1.0); Lk(mx2.outputs['Result'], bc)                 # pale raised wheal centre
        bp = N.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = float(os.environ.get('KW22_BUMP', 0.8)); bp.inputs['Distance'].default_value = 0.0015
        Lk(wm.outputs[0], bp.inputs['Height']); ni = bs.inputs['Normal']
        if ni.is_linked: Lk(ni.links[0].from_socket, bp.inputs['Normal'])
        Lk(bp.outputs['Normal'], ni)
        ri = bs.inputs['Roughness']; w = N.new('ShaderNodeValue'); w.outputs[0].default_value = 1.0; vw.append(w)
        mr = N.new('ShaderNodeMath'); mr.operation = 'MULTIPLY'; Lk(w.outputs[0], mr.inputs[1])
        if ri.is_linked: Lk(ri.links[0].from_socket, mr.inputs[0])
        else: mr.inputs[0].default_value = ri.default_value
        Lk(mr.outputs[0], ri)
    R['ov'] = (va, vs, vc, vw); print('kw22 overlay nodes', len(va)); R['body'] = body

def build_tear(c):
    import bpy, bmesh
    me = bpy.data.meshes.new('kw22_tear'); bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=16, v_segments=10, radius=0.0026); bm.to_mesh(me); bm.free()
    mt = bpy.data.materials.get('kw22_water'); me.materials.append(mt)
    ob = bpy.data.objects.new('kw22_tear', me); c.objects.link(ob); ob.scale = (1.0, 0.7, 1.5); ob.hide_render = True; R['tear'] = ob
    tr = []
    for i in range(6):                              # the wet trail it leaves
        o2 = bpy.data.objects.new('kw22_trail%d' % i, me); c.objects.link(o2); o2.scale = (0.55, 0.35, 1.2); o2.hide_render = True; tr.append(o2)
    R['trail'] = tr

def place_tear(f):
    import bpy
    ob = R['tear']; tr = R['trail']; path = R['tpath']
    show = TT0 <= f <= TT1 + 40 and in_shower(f) and f < LOOPF and len(path) >= 2
    if not show:
        ob.hide_render = True
        for o in tr: o.hide_render = True
        return
    body = R['body']; dg = bpy.context.evaluated_depsgraph_get(); ev = body.evaluated_get(dg); me = ev.to_mesh(); Mw = ev.matrix_world
    P = [Mw @ me.vertices[i].co for i in path]; Nn = [(Mw.to_3x3() @ me.vertices[i].normal).normalized() for i in path]
    ev.to_mesh_clear()
    def at(s):
        s = max(0.0, min(1.0, s)) * (len(P) - 1); i = min(int(s), len(P) - 2); u = s - i
        return P[i].lerp(P[i + 1], u) + Nn[i].lerp(Nn[i + 1], u) * 0.0022
    s = ease((f - TT0) / max(1, TT1 - TT0)); ob.location = at(s); ob.hide_render = f > TT1 + 8
    for k, o in enumerate(tr):
        sk = s * (k + 0.5) / len(tr); o.location = at(sk); o.hide_render = s <= 0.05

def eyes(rt, who):
    rg = rt.actors[who].p.hg.rig; W_ = rg.matrix_world
    EL = W_ @ rg.pose.bones['eyeball.L'].head; ER = W_ @ rg.pose.bones['eyeball.R'].head; return EL, ER, (EL + ER) / 2

def set_key(hg, name, v):
    for o in hg.meshes:
        kb = o.data.shape_keys.key_blocks if o.data.shape_keys else None
        k = kb.get(name) if kb else None
        if k is not None: k.value = v

def look(tg, dirv, dist, lens, fst=8.0, foc=None):
    dv = V(dirv).normalized(); return tg + dv * dist, tg, V((0, 0, 1)), lens, fst, (foc if foc is not None else tg)

def build(rt):
    import bpy
    c = bpy.data.collections.get('kw_ep22') or bpy.data.collections.new('kw_ep22')
    if c.name not in bpy.context.scene.collection.children: bpy.context.scene.collection.children.link(c)
    import kwlook as Q_; Q_.LOOP_T = FN / FPS
    hg = rt.actors[maya].p.hg; W_ = hg.rig.matrix_world
    EB = (W_ @ hg.rig.data.bones['eyeball.L'].head_local + W_ @ hg.rig.data.bones['eyeball.R'].head_local) / 2
    if abs(EB.x - SX) > 2.0: EB = V((SX, 0.0, 1.55))
    R['EB0'] = EB.copy(); print('kw22 eyes at build', tuple(round(v, 3) for v in EB))
    build_shower(c, EB); build_screen(c); body_keys(hg); build_tear(c)
ep.build_hook = build

def frame_hook(rt, t):
    import bpy, kwlook as Q_
    Q_.LOOP_T = FN / FPS
    f = t * FPS; sh = in_shower(f)
    fv = float(FORCE) if FORCE is not None else None
    va, vs, vc, vw = R['ov']; p = pulse(f)
    for n_ in va: n_.outputs[0].default_value = (fv if fv is not None else v_arm(f)) * p
    for n_ in vs: n_.outputs[0].default_value = (fv if fv is not None else v_spread(f)) * p
    for n_ in vc: n_.outputs[0].default_value = fv if fv is not None else v_cheek(f)
    for n_ in vw: n_.outputs[0].default_value = 0.55 if sh else 1.0
    k = card_of(f)
    for i, v in enumerate(R['scr']): v.outputs[0].default_value = 1.0 if k >= i + 1 else 0.0
    R['scre'].inputs['Strength'].default_value = float(os.environ.get('KW_SCRE', 1.4)) if not sh else 0.0
    for lo in R['lights']: lo.hide_render = not sh
    bpy.context.view_layer.update()
    _, _, EB = eyes(rt, maya)
    top = EB.z + 0.11
    for ob, p0, d, off, ln in R['water']:
        if not sh: ob.hide_render = True; continue
        s = (f * 0.13 + off) % 3.0; pp = p0 + d * s
        rel = pp - EB; inside = (rel.x / 0.25) ** 2 + ((rel.y - 0.03) / 0.17) ** 2 < 1.0 and pp.z < top
        hid = pp.z < 0.02 or inside or (f < 4 and s > 1.2)
        ob.hide_render = hid
        if not hid:
            ob.location = pp - d * (ln / 2); ob.rotation_euler = d.to_track_quat('Z', 'Y').to_euler(); ob.scale = (1, 1, ln)
    place_tear(f)
    sh_ = rt.ep.shot_at(t); rt.FX.update(sh_, t - sh_.t, t)
ep.frame_hook = frame_hook

def arm_pt(rt):
    rg = rt.actors[maya].p.hg.rig; W_ = rg.matrix_world; b = rg.pose.bones['lowerarm01.L']
    return W_ @ ((b.head + b.tail) / 2)
def cam_fn(rt, t):
    import bpy
    f = t * FPS; bpy.context.view_layer.update(); shot, u = shot_of(f)
    _, _, EB = eyes(rt, maya)
    push = lambda a, b: a * (b / a) ** ease(u)
    if shot in ('MED0', 'MED1'):                                    # chest-up in the shower
        tg = EB + V((0.0, 0.0, -0.14)); d_ = push(1.05, 0.95) if shot == 'MED0' and f < LOOPF else (push(1.0, 0.9) if shot == 'MED1' else 1.05)
        return look(tg, (-0.45, -1.0, 0.10), d_, 50.0, 8.0, EB)
    if shot == 'HEAD':                                             # cutaway: the shower head, water pouring
        tg = R['shead'] + V((0, -0.04, -0.10)); return look(tg, (-1.0, -0.55, -0.05), push(0.62, 0.54), 50.0, 8.0, tg)
    if shot == 'ARM':                                              # close: hives on her raised forearm
        tg = arm_pt(rt); return look(tg, (-0.35, -1.0, 0.25), push(0.42, 0.36), 70.0, 9.0, tg)
    if shot == 'CLOSE':                                            # the tear on her cheek
        tg = EB + V((0, 0, -0.04)); return look(tg, (-0.30, -1.0, 0.02), push(0.50, 0.42), 85.0, 11.0, EB + V((0, 0, -0.03)))
    if shot == 'FACE':
        tg = EB + V((0, 0, -0.04)); return look(tg, (-0.55, -1.0, 0.02), push(0.50, 0.43), 85.0, 11.0, EB)
    if shot == 'SIDE':
        tg = EB + V((0, 0.02, -0.08)); return look(tg, (-1.0, -0.35, 0.08), push(0.78, 0.70), 70.0, 9.0, EB)
    if shot == 'CHEST':                                            # neck, upper chest and arms covered in hives
        tg = EB + V((0.0, -0.02, -0.22)); return look(tg, (-0.30, -1.0, 0.06), push(0.95, 0.82), 50.0, 8.0, tg)
    if shot in ('BED', 'BFACE'):
        tg = EB + V((0.0, 0.0, -0.20)) if shot == 'BED' else EB + V((0, 0, -0.06))
        return look(tg, (-0.75, -1.0, 0.05), push(1.25, 1.12) if shot == 'BED' else push(0.62, 0.55), 50.0, 8.0, EB)
    tg = V(SCR_C) + V((0, 0, -0.15))                                 # SCR: screen + Maya below it
    return look(tg, (0.06, -1.0, 0.25), push(1.55, 1.45), 50.0, 8.0, V(SCR_C))
ep.cam_fn = cam_fn

YL = dict(color='yellow', size=1.2); Y = 0.89
ep.label_outline = True; ep.label_maxw = 820.0; ep.label_lens_fix = True
def lab(txt, f0, f1, **k): return KW.fx.label(txt, at=f0 * F, pos=(0.5, Y), dur=(f1 - f0) * F, **(k or YL))
wd = fw
labels = [KW.fx.label('WATER', at=-1.0, pos=(0.5, Y), dur=1.0 + 44 * F, **YL),
          lab('HIVES', 46, fl(1) - 6, color='red'),
          lab('CHLORINE?', fl(1) - 2, wd(1, 'plain') - 1),
          lab('ANY WATER', wd(1, 'plain'), fl(2) - 6),
          lab('SWEAT', wd(2, 'sweat'), wd(2, 'tears') - 1),
          lab('TEARS', wd(2, 'tears'), fl(3) - 6, color='red'),
          lab('HISTAMINE', wd(3, 'histamine.') - 4, fl(4) - 6),
          lab('30 MIN', fl(4) - 2, FSP + 8),
          lab('SPREADING', FSP + 10, FCL - 2, color='red'),
          lab('RARELY', wd(5, 'rarely') - 2, wd(5, 'welts') - 1),
          lab('2 HOURS', wd(5, 'two'), fl(6) - 6),
          lab('RARE', fl(6) - 2, wd(6, 'antihistamines') - 2),
          lab('PILLS HELP', wd(6, 'antihistamines'), CTA0 - 2),
          KW.fx.label('ITCHY?', at=CTA0 * F, pos=(0.5, 0.30), dur=(LOOPF - 1 - CTA0) * F, **YL),
          KW.fx.label('COMMENT BELOW', at=(CTA0 + 3) * F, pos=(0.5, 0.235), dur=(LOOPF - 4 - CTA0) * F, color='white', size=0.5),
          KW.fx.label('WATER', at=(LOOPF) * F, pos=(0.5, Y), dur=2.0, **YL)]
labels[-1].o['nopop'] = True
ep.sound(0.0, 'thud', 0.6)
for f_ in (46, wd(2, 'tears'), FSP, fl(6)): ep.sound(f_ * F, 'thud', 0.45)
ep.mouth_fix = True; ep.eyes_fix = True; ep.relight_after_pose = True
def part(a, b):           # labels are shot-local: split them by start and shift
    out = []
    for lb in labels:
        at = lb.o.get('at', 0)
        if a * F - 1e-6 <= at < b * F - 1e-6 or (a == 0 and at < 0): lb.o['at'] = at - a * F if a else at; out.append(lb)
    return out
LS, LC, LL = part(0, FCL), part(FCL, LOOPF), part(LOOPF, FN + 99)
ep.shot(0.0, 'shower', set='studio', cast={maya: PS}, fx=LS, cam=KW.cam.face(maya))
ep.shot(FCL * F, 'clinic', set='hospital', cast={maya: PC, doc: PD}, fx=LC, cam=KW.cam.face(maya))
ep.shot((LOOPF) * F, 'loop', set='studio', cast={maya: PL}, fx=LL, cam=KW.cam.face(maya))
ep.run()
