# DQ + Sushi Zanmai firsts - set swapped into the Temple Street plate engine (HK Unlocked, Blender 4.2), warm mall daylight
# run: blender -b -y --factory-startup -P scene.py -- <out.blend>
import bpy, bmesh, math, random, sys
from mathutils import Vector

R = random.Random(7)
FPS = 30
ZH_FONT = '/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc'

bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.fps = FPS; sc.frame_start = 0; sc.frame_end = 23 * FPS
sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = 1080, 1920, 100
sc.render.engine = 'CYCLES'
sc.cycles.device = 'CPU'; sc.cycles.samples = 6; sc.cycles.use_denoising = False
sc.cycles.max_bounces = 0; sc.cycles.diffuse_bounces = 0; sc.cycles.glossy_bounces = 0
sc.cycles.transmission_bounces = 0; sc.cycles.transparent_max_bounces = 8
sc.cycles.pixel_filter_width = 1.2
sc.view_settings.view_transform = 'Standard'; sc.view_settings.look = 'None'
sc.render.film_transparent = False

INK = bpy.data.collections.new('Ink'); sc.collection.children.link(INK)
NOINK = bpy.data.collections.new('NoInk'); sc.collection.children.link(NOINK)

# ---------------- world: warm mall daylight backdrop ----------------
w = bpy.data.worlds.new('day'); sc.world = w; w.use_nodes = True
bgn = w.node_tree.nodes['Background']; bgn.inputs['Color'].default_value = (0.93, 0.90, 0.84, 1); bgn.inputs['Strength'].default_value = 1.0
# ---------------- materials ----------------
LIGHT = Vector((0.45, -0.55, 0.70)).normalized()
BULB = (1.0, 0.851, 0.627)          # #FFD9A0 warm bare bulb
_mats = {}
POOL_IMG = bpy.data.images.new('pools', 880, 1540, alpha=False, float_buffer=True)   # baked at the end, looked up by every toon + ground material
def pool_lookup(n, g):
    mp = n.nodes.new('ShaderNodeMapping'); mp.vector_type = 'POINT'
    mp.inputs['Location'].default_value = (44.0 / 88.0, 24.0 / 154.0, 0)
    mp.inputs['Scale'].default_value = (1 / 88.0, 1 / 154.0, 1)
    im = n.nodes.new('ShaderNodeTexImage'); im.image = POOL_IMG; im.interpolation = 'Linear'; im.extension = 'EXTEND'
    n.links.new(g.outputs['Position'], mp.inputs['Vector']); n.links.new(mp.outputs['Vector'], im.inputs['Vector'])
    return im.outputs['Color']

def night_tint(n, lit):
    """day: even warm mall light (no night blues, no neon)"""
    rgb = n.nodes.new('ShaderNodeRGB')
    rgb.outputs[0].default_value = tuple(c + (1 - c) * lit for c in (1.03, 1.0, 0.93)) + (1,)
    return rgb.outputs[0]
def toon(name, col, bands=(0.66, 0.84, 1.0), warm=0.0, mottle=0.07, lit=0.0):
    """flat watercolour-like fill: 3 constant bands from a fixed light direction, mottled, tinted for night"""
    if name in _mats: return _mats[name]
    mt = bpy.data.materials.new(name); mt.use_nodes = True; n = mt.node_tree; n.nodes.clear()
    g = n.nodes.new('ShaderNodeNewGeometry'); dv = n.nodes.new('ShaderNodeVectorMath'); dv.operation = 'DOT_PRODUCT'
    dv.inputs[1].default_value = LIGHT
    nz = n.nodes.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 1.6; nz.inputs['Detail'].default_value = 3
    tco = n.nodes.new('ShaderNodeTexCoord')
    sub = n.nodes.new('ShaderNodeMath'); sub.operation = 'SUBTRACT'; sub.inputs[1].default_value = 0.5
    mul = n.nodes.new('ShaderNodeMath'); mul.operation = 'MULTIPLY'; mul.inputs[1].default_value = mottle * 2
    add = n.nodes.new('ShaderNodeMath'); add.operation = 'ADD'
    ramp = n.nodes.new('ShaderNodeValToRGB'); r = ramp.color_ramp; r.interpolation = 'CONSTANT'
    def c(k): return tuple(min(1, col[i] * k + warm * (0.06, 0.03, -0.02)[i]) for i in range(3)) + (1,)
    r.elements[0].position = 0.0; r.elements[0].color = c(bands[0])
    r.elements[1].position = 0.18; r.elements[1].color = c(bands[1])
    r.elements.new(0.52).color = c(bands[2])
    mx = n.nodes.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'; mx.inputs['Factor'].default_value = 1.0
    em = n.nodes.new('ShaderNodeEmission'); o = n.nodes.new('ShaderNodeOutputMaterial')
    n.links.new(g.outputs['Normal'], dv.inputs[0]); n.links.new(tco.outputs['Object'], nz.inputs['Vector'])
    n.links.new(nz.outputs['Fac'], sub.inputs[0]); n.links.new(sub.outputs[0], mul.inputs[0])
    n.links.new(dv.outputs['Value'], add.inputs[0]); n.links.new(mul.outputs[0], add.inputs[1])
    n.links.new(add.outputs[0], ramp.inputs['Fac'])
    n.links.new(ramp.outputs['Color'], mx.inputs['A']); n.links.new(night_tint(n, lit), mx.inputs['B'])
    n.links.new(mx.outputs['Result'], em.inputs['Color'])
    n.links.new(em.outputs[0], o.inputs['Surface'])
    _mats[name] = mt; return mt

def glow(name, col, strength=1.0, alpha=1.0):
    if name in _mats: return _mats[name]
    mt = bpy.data.materials.new(name); mt.use_nodes = True; n = mt.node_tree; n.nodes.clear()
    em = n.nodes.new('ShaderNodeEmission'); em.name = 'Emission'; em.inputs['Color'].default_value = tuple(col) + (1,)
    em.inputs['Strength'].default_value = strength
    o = n.nodes.new('ShaderNodeOutputMaterial')
    if alpha < 1:
        tr = n.nodes.new('ShaderNodeBsdfTransparent'); mx = n.nodes.new('ShaderNodeMixShader'); mx.name = 'Mix'
        mx.inputs[0].default_value = alpha
        n.links.new(tr.outputs[0], mx.inputs[1]); n.links.new(em.outputs[0], mx.inputs[2]); n.links.new(mx.outputs[0], o.inputs['Surface'])
        mt.blend_method = 'BLEND'
    else:
        n.links.new(em.outputs[0], o.inputs['Surface'])
    _mats[name] = mt; return mt

def wash(name, col, alpha):
    """ink-wash steam: emission mixed with transparency, per-object fade via object colour alpha (driven)"""
    if name in _mats: return _mats[name]
    mt = bpy.data.materials.new(name); mt.use_nodes = True; n = mt.node_tree; n.nodes.clear()
    em = n.nodes.new('ShaderNodeEmission'); em.inputs['Color'].default_value = tuple(col) + (1,)
    tr = n.nodes.new('ShaderNodeBsdfTransparent'); mx = n.nodes.new('ShaderNodeMixShader')
    oi = n.nodes.new('ShaderNodeObjectInfo'); ml = n.nodes.new('ShaderNodeMath'); ml.operation = 'MULTIPLY'; ml.inputs[1].default_value = alpha
    # soften toward the strip's side edges (uv x 0..1)
    uv = n.nodes.new('ShaderNodeUVMap'); sp = n.nodes.new('ShaderNodeSeparateXYZ')
    s1 = n.nodes.new('ShaderNodeMath'); s1.operation = 'PINGPONG'; s1.inputs[1].default_value = 0.5
    s2 = n.nodes.new('ShaderNodeMath'); s2.operation = 'MULTIPLY'; s2.inputs[1].default_value = 2.0
    s3 = n.nodes.new('ShaderNodeMath'); s3.operation = 'MULTIPLY'
    o = n.nodes.new('ShaderNodeOutputMaterial')
    n.links.new(uv.outputs['UV'], sp.inputs[0]); n.links.new(sp.outputs['X'], s1.inputs[0]); n.links.new(s1.outputs[0], s2.inputs[0])
    n.links.new(oi.outputs['Alpha'], ml.inputs[0]); n.links.new(ml.outputs[0], s3.inputs[0]); n.links.new(s2.outputs[0], s3.inputs[1])
    # and fade toward both ends of the strip (uv y 0..1), so no hard cut-offs
    t1 = n.nodes.new('ShaderNodeMath'); t1.operation = 'PINGPONG'; t1.inputs[1].default_value = 0.5
    t2 = n.nodes.new('ShaderNodeMath'); t2.operation = 'MULTIPLY'; t2.inputs[1].default_value = 2.0
    t3 = n.nodes.new('ShaderNodeMath'); t3.operation = 'POWER'; t3.inputs[1].default_value = 0.8
    t4 = n.nodes.new('ShaderNodeMath'); t4.operation = 'MULTIPLY'
    n.links.new(sp.outputs['Y'], t1.inputs[0]); n.links.new(t1.outputs[0], t2.inputs[0]); n.links.new(t2.outputs[0], t3.inputs[0])
    n.links.new(s3.outputs[0], t4.inputs[0]); n.links.new(t3.outputs[0], t4.inputs[1])
    n.links.new(t4.outputs[0], mx.inputs[0]); n.links.new(tr.outputs[0], mx.inputs[1]); n.links.new(em.outputs[0], mx.inputs[2])
    n.links.new(mx.outputs[0], o.inputs['Surface']); mt.blend_method = 'BLEND'
    _mats[name] = mt; return mt
def hx(s): return tuple(int(s[i:i + 2], 16) / 255 for i in (0, 2, 4))
P = dict(
    wall=[hx('d9c3a0'), hx('c9b59a'), hx('e2cfae'), hx('b9a48c'), hx('d6b79a'), hx('a8b4a6'), hx('c4a28a')],
    win=hx('4a4660'), winlit=hx('f2c879'), slab=hx('ece2cc'), ac=hx('e8e4da'), road=hx('6f6a72'), walk=hx('a39a8e'),
    red=hx('c8443a'), green=hx('4f8f62'), blue=hx('3f6fa8'), yellow=hx('e8b64a'), pole=hx('5a4a3c'), table=hx('8a6244'),
    goods=[hx('d65a4a'), hx('e3b04b'), hx('5b8fc4'), hx('7aa66a'), hx('e7e0cf'), hx('b07ab0')],
    skin=hx('d8b090'), hair=hx('2e2a2a'),
    cloth=[hx('3f5f8f'), hx('b9473f'), hx('e2d6b8'), hx('4d7a5a'), hx('7b6a9a'), hx('d9a441'), hx('5d5d66'), hx('c9826a'), hx('2f4858')],
    pants=[hx('34374a'), hx('4b4038'), hx('5a6472'), hx('2c2c30')],
    roofgreen=hx('3f7a5c'), roofgold=hx('d9a441'), templered=hx('a8352d'), stone=hx('bfb3a2'),
    steel=hx('b7bcc2'), curry=hx('d99a2b'), clay=hx('9a5a3a'), ember=hx('ff8a3a'), stage=hx('9e2a2a'),
    board=[hx('f1e3c0'), hx('c8443a'), hx('2f5d8a'), hx('e8b64a'), hx('3f7a5c')],
)

# ---------------- mesh helpers ----------------
def boxes_obj(name, boxes, mats, coll=INK, loc=(0, 0, 0)):
    """one object from many boxes: (cx,cy,cz, sx,sy,sz, mat_index[, rot_z])"""
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    for b in boxes:
        cx, cy, cz, sx, sy, sz, mi = b[:7]; rz = b[7] if len(b) > 7 else 0
        res = bmesh.ops.create_cube(bm, size=1.0)
        vs = res['verts']
        for v in vs:
            x, y, z = v.co.x * sx, v.co.y * sy, v.co.z * sz
            if rz: x, y = x * math.cos(rz) - y * math.sin(rz), x * math.sin(rz) + y * math.cos(rz)
            v.co = Vector((x + cx, y + cy, z + cz))
        fs = {f for v in vs for f in v.link_faces}
        for f in fs: f.material_index = mi
    bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); ob.location = loc
    for mt in mats: me.materials.append(mt)
    coll.objects.link(ob); return ob

def prim(kind, name, loc, scale, mat, coll=INK, rot=(0, 0, 0), seg=10, parent=None):
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    if kind == 'cyl': bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=1, radius2=1, depth=2)
    elif kind == 'cone': bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=1, radius2=0.0001, depth=2)
    elif kind == 'torso': bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=0.8, radius2=1, depth=2)
    elif kind == 'frustum': bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=1, radius2=0.6, depth=2)
    elif kind == 'sph': bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=max(4, seg // 2 + 1), radius=1)
    elif kind == 'ico': bmesh.ops.create_icosphere(bm, subdivisions=1, radius=1)
    elif kind == 'box': bmesh.ops.create_cube(bm, size=2)
    elif kind == 'plane':
        bmesh.ops.create_grid(bm, x_segments=1, y_segments=1, size=1)
    bm.to_mesh(me); bm.free()
    for p in me.polygons: p.use_smooth = kind in ('sph', 'cyl', 'frustum', 'cone', 'torso')
    ob = bpy.data.objects.new(name, me); ob.location = loc; ob.scale = scale; ob.rotation_euler = rot
    me.materials.append(mat); coll.objects.link(ob)
    if parent: ob.parent = parent
    return ob

def empty(name, loc=(0, 0, 0), parent=None, coll=INK):
    ob = bpy.data.objects.new(name, None); ob.location = loc; coll.objects.link(ob)
    if parent: ob.parent = parent
    return ob

def drv(ob, path, idx, expr):
    fc = ob.driver_add(path, idx) if idx is not None else ob.driver_add(path)
    fc.driver.type = 'SCRIPTED'; fc.driver.expression = expr
    return fc

def text(name, body, loc, size, mat, rot=(math.radians(90), 0, 0), coll=INK):
    cu = bpy.data.curves.new(name, 'FONT'); cu.body = body; cu.size = size
    cu.font = FONT; cu.align_x = 'CENTER'; cu.align_y = 'CENTER'
    ob = bpy.data.objects.new(name, cu); ob.location = loc; ob.rotation_euler = rot
    cu.materials.append(mat); coll.objects.link(ob); return ob

FONT = bpy.data.fonts.load(ZH_FONT)


GROUND = bpy.data.collections.new('Ground'); sc.collection.children.link(GROUND)
def contact_shadow(name, parent, rx=0.42, ry=0.32, z=0.012, loc=(0, 0, 0)):
    return prim('cyl', name, (loc[0], loc[1], z), (rx, ry, 0.002), toon('shadow', hx('b8ad9c'), mottle=0.02), coll=GROUND, seg=16, parent=parent)
# ---------------- people: real proportions (head ~1/7.5 of height), necks, shoulders, hair, varied clothes ----------------
HAIRS = ['short', 'short', 'pony', 'cap', 'long', 'short', 'bun']
TOPS = ['tee', 'tee', 'jacket', 'shirt', 'tee', 'jacket']
SKINS = [hx('d8b090'), hx('c99a78'), hx('e0bc9c'), hx('b98a68')]
FACE_INK = None
def ik2(Y, Z, l1, l2):
    """2-bone planar IK in the (forward Y, up Z) plane from the shoulder; returns (upper angle, forearm relative angle)
    where angle 0 = hanging straight down and positive = swung forward/up."""
    d = min(math.hypot(Y, Z), l1 + l2 - 1e-4)
    a_t = math.atan2(Y, -Z)                          # angle of target from 'down'
    c = (l1 * l1 + d * d - l2 * l2) / (2 * l1 * d); b = math.acos(max(-1, min(1, c)))
    a1 = a_t - b                                       # elbow stays low/behind, like a real reach
    c2 = (l1 * l1 + l2 * l2 - d * d) / (2 * l1 * l2); e = math.pi - math.acos(max(-1, min(1, c2)))
    return a1, e

def person(name, cloth, pants, scale=1.0, walk=True, speed=1.25, phase=0.0, sit=False, coll=INK, hair=None, top=None,
           face=False, bag=None, pause=0.0, skin=None, rr=None, seat=0.45, shadow=True):
    global FACE_INK
    rr = rr or random.Random(sum(ord(c_) * (k_ + 1) for k_, c_ in enumerate(name)))
    hair = hair or rr.choice(HAIRS); top = top or rr.choice(TOPS)
    if bag is None: bag = rr.choice([None, None, 'strap', 'back'])
    root = empty(name)
    s = scale
    sk = toon(f'skin{SKINS.index(skin) if skin in SKINS else 0}', skin or rr.choice(SKINS))
    hr = toon('hair', P['hair']); ct = toon(f'c_{cloth}', cloth); pt = toon(f'p_{pants}', pants)
    dk = toon(f'cd_{cloth}', tuple(c_ * 0.62 for c_ in cloth))
    # torso (wider at the shoulders), pelvis, neck, head
    prim('torso', name + '_torso', (0, 0, 1.17 * s), (0.18 * s, 0.105 * s, 0.25 * s), ct, parent=root, seg=10)
    prim('sph', name + '_shl', (0, 0, 1.385 * s), (0.2 * s, 0.11 * s, 0.05 * s), ct, parent=root, seg=10)
    prim('frustum', name + '_pelvis', (0, 0, 0.95 * s), (0.155 * s, 0.1 * s, 0.07 * s), pt, parent=root, seg=10, rot=(math.pi, 0, 0))
    prim('cyl', name + '_neck', (0, 0, 1.45 * s), (0.045 * s, 0.045 * s, 0.05 * s), sk, parent=root, seg=8)
    hd = empty(name + '_hd', (0, 0, 1.49 * s), parent=root)
    prim('sph', name + '_head', (0, 0.008 * s, 0.1 * s), (0.088 * s, 0.098 * s, 0.112 * s), sk, parent=hd, seg=12)
    if hair in ('short', 'pony', 'long', 'bun'):
        prim('sph', name + '_hair', (0, -0.012 * s, 0.135 * s), (0.094 * s, 0.1 * s, 0.09 * s), hr, parent=hd, seg=12)
    if hair == 'pony':
        prim('sph', name + '_pony', (0, -0.11 * s, 0.09 * s), (0.035 * s, 0.05 * s, 0.09 * s), hr, parent=hd, seg=8, rot=(0.5, 0, 0))
    if hair == 'bun':
        prim('sph', name + '_bun', (0, -0.08 * s, 0.2 * s), (0.045 * s, 0.045 * s, 0.045 * s), hr, parent=hd, seg=8)
    if hair == 'long':
        prim('box', name + '_long', (0, -0.06 * s, 0.0), (0.09 * s, 0.04 * s, 0.12 * s), hr, parent=hd)
    if hair == 'cap':
        cc = toon(f'cap{rr.randrange(3)}', [hx('c8443a'), hx('2f4858'), hx('e9e4d8')][rr.randrange(3)])
        prim('sph', name + '_cap', (0, -0.005 * s, 0.14 * s), (0.096 * s, 0.103 * s, 0.075 * s), cc, parent=hd, seg=12)
        prim('box', name + '_brim', (0, 0.1 * s, 0.135 * s), (0.07 * s, 0.05 * s, 0.008 * s), cc, parent=hd)
    if face:
        if FACE_INK is None: FACE_INK = glow('faceink', (0.16, 0.10, 0.07))
        for sd_ in (-1, 1):
            prim('box', name + f'_eye{sd_}', (sd_ * 0.032 * s, 0.1 * s, 0.115 * s), (0.016 * s, 0.006 * s, 0.004 * s), FACE_INK, parent=hd)
        prim('box', name + '_nose', (0.006 * s, 0.108 * s, 0.085 * s), (0.004 * s, 0.006 * s, 0.022 * s), FACE_INK, parent=hd)
        prim('box', name + '_mouth', (0, 0.098 * s, 0.045 * s), (0.018 * s, 0.006 * s, 0.003 * s), FACE_INK, parent=hd)
    if top == 'jacket':     # open front: darker lapel strip + zip line
        prim('box', name + '_zip', (0, 0.1 * s, 1.17 * s), (0.035 * s, 0.012 * s, 0.24 * s), toon('tee0', hx('e9e4d8')), parent=root)
    if top == 'shirt':
        prim('box', name + '_collar', (0, 0.075 * s, 1.41 * s), (0.07 * s, 0.03 * s, 0.025 * s), dk, parent=root)
    if bag == 'strap':
        st = toon('strap', hx('3a2a22'))
        prim('box', name + '_strap', (0, 0.108 * s, 1.2 * s), (0.016 * s, 0.006 * s, 0.27 * s), st, parent=root, rot=(0, 0.75, 0))
        prim('box', name + '_bag', (-0.19 * s, 0.03 * s, 0.98 * s), (0.04 * s, 0.11 * s, 0.09 * s), st, parent=root)
    if bag == 'back':
        prim('box', name + '_pack', (0, -0.15 * s, 1.18 * s), (0.13 * s, 0.06 * s, 0.17 * s), toon(f'pack{rr.randrange(3)}', [hx('2f4858'), hx('4d7a5a'), hx('3a3a40')][rr.randrange(3)]), parent=root)
    hips, arms = [], []
    arm_lo = sk if top == 'tee' else ct
    for sd_ in (-1, 1):
        hip = empty(name + f'_hip{sd_}', (sd_ * 0.085 * s, 0, 0.93 * s), parent=root)
        prim('cyl', name + f'_thigh{sd_}', (0, 0, -0.215 * s), (0.062 * s, 0.066 * s, 0.215 * s), pt, parent=hip, seg=8)
        kn = empty(name + f'_kn{sd_}', (0, 0, -0.44 * s), parent=hip)
        prim('cyl', name + f'_shin{sd_}', (0, 0, -0.2 * s), (0.048 * s, 0.05 * s, 0.21 * s), pt, parent=kn, seg=8)
        prim('box', name + f'_shoe{sd_}', (0, 0.045 * s, -0.43 * s), (0.048 * s, 0.11 * s, 0.032 * s), toon('shoe', hx('2a2626')), parent=kn)
        sh = empty(name + f'_sh{sd_}', (sd_ * 0.205 * s, 0, 1.38 * s), parent=root)
        prim('cyl', name + f'_arm{sd_}', (0, 0, -0.14 * s), (0.045 * s, 0.045 * s, 0.145 * s), ct, parent=sh, seg=8)
        el = empty(name + f'_el{sd_}', (0, 0, -0.29 * s), parent=sh)
        prim('cyl', name + f'_fore{sd_}', (0, 0, -0.125 * s), (0.036 * s, 0.036 * s, 0.13 * s), arm_lo, parent=el, seg=8)
        prim('sph', name + f'_hand{sd_}', (0, 0.008 * s, -0.29 * s), (0.032 * s, 0.045 * s, 0.06 * s), sk, parent=el, seg=8)
        hips.append((hip, kn, sd_)); arms.append((sh, el, sd_))
    if walk:
        w = 2 * math.pi * speed / (1.45 * s)            # gait cycle = 2 steps of ~0.72 m
        if pause > 0:   # stop-and-go browsing walk: speed factor 1 + a*cos(Ωt), gait phase integrates it
            Om = 2 * math.pi / rr.uniform(5, 9); ph2 = rr.uniform(0, 6)
            T = f'(frame/30+{pause:.2f}*sin(frame/30*{Om:.3f}+{ph2:.2f})/{Om:.3f})'
            amp = f'(0.25+0.75*(1+{pause:.2f}*cos(frame/30*{Om:.3f}+{ph2:.2f}))/{1 + pause:.2f})'
        else:
            T = '(frame/30)'; amp = '1'
        for hip, kn, sd_ in hips:
            p = f'({w:.3f}*{T}+{phase + (0 if sd_ < 0 else math.pi):.3f})'
            drv(hip, 'rotation_euler', 0, f'{amp}*0.40*sin({p})')
            drv(kn, 'rotation_euler', 0, f'-{amp}*(0.08+0.62*max(0,cos({p})))')
        for sh, el, sd_ in arms:
            p = f'({w:.3f}*{T}+{phase + (0 if sd_ < 0 else math.pi):.3f})'
            drv(sh, 'rotation_euler', 0, f'-{amp}*0.34*sin({p})')
            drv(sh, 'rotation_euler', 1, f'{-sd_ * 0.06:.3f}')
            drv(el, 'rotation_euler', 0, f'0.22+{amp}*0.18*max(0,-sin({p}))')
        drv(root, 'location', 2, f'{amp}*0.03*abs(sin({w:.3f}*{T}+{phase:.3f}))')
        drv(hd, 'rotation_euler', 0, f'0.05*sin(2*{w:.3f}*{T}+{phase + 0.6:.3f})')
        root['T'] = T     # walkers reuse the same time warp for their position
    else:
        for sh, el, sd_ in arms:
            sh.rotation_euler = (0.05, -sd_ * 0.06, 0); el.rotation_euler = (0.25, 0, 0)
        drv(hd, 'rotation_euler', 2, f'0.25*sin(frame*0.03+{phase:.2f})')
    if sit:
        for hip, kn, sd_ in hips:
            hip.rotation_euler = (1.5, 0, 0); kn.rotation_euler = (-1.5, 0, 0)
        root.location.z = seat + 0.07 * s - 0.93 * s
    if shadow and not sit:
        contact_shadow(name + '_shd', root, rx=0.32 * s, ry=0.26 * s, z=0.014)
    return root


# =====================================================================================
# SET: plates S1 two shopfronts (x 0) · S2 Dairy Queen counter (x 20) · S3 Sushi Zanmai counter (x 40)
# plate frames 0..555 at 30 fps: S1 0-80, S2 81-302, S3 303-555
# =====================================================================================
sc.frame_end = 555
H90 = math.radians(90)
WHITE = toon('white', hx('f4f1ea'), lit=0.35); CREAM = toon('cream', hx('e8dfcf'))
DQRED = toon('dqred', hx('d3202e'), lit=0.1); DQBLUE = toon('dqblue', hx('1f4f9e'))
WOOD = toon('wood', hx('6a4128')); HINOKI = toon('hinoki', hx('dcbd8c'), mottle=0.1)
NAVY = toon('navy', hx('22386a')); STEEL = toon('steel', hx('c3c8ce')); DARK = toon('dark', hx('2a2626'))
TXT_W = toon('txtw', hx('ffffff'), lit=0.6); TXT_R = toon('txtr', hx('c81e28'), lit=0.1); TXT_K = toon('txtk', hx('2a2626'))

def floor(name, cx, w_=14, d_=12):
    boxes_obj(name, [(cx, -2.0, -0.05, w_, d_, 0.1, 0)], [toon('floor', hx('cbbfa9'), mottle=0.05)], coll=GROUND)
def kv(ob, path, keys, interp='BEZIER'):
    for f, v in keys:
        setattr(ob, path, v); ob.keyframe_insert(path, frame=f)
    for fc in ob.animation_data.action.fcurves:
        for kp in fc.keyframe_points: kp.interpolation = interp

# ---------------- S1: two shopfronts side by side + FIRST IN HK stamp ----------------
floor('floor1', 0, 16, 14)
boxes_obj('mallwall', [(0, 0.6, 5.5, 9.0, 0.3, 11.0, 0)], [toon('mallwall', hx('e6d3b3'))])
boxes_obj('mallbands', [(0, 0.42, 3.55, 9.0, 0.08, 0.12, 0), (0, 0.42, 6.4, 9.0, 0.08, 0.12, 0), (0, 0.42, 9.2, 9.0, 0.08, 0.12, 0)], [toon('mallband', hx('c9b79a'))])
# Dairy Queen (left)
DX = -1.45
boxes_obj('dq_front', [(DX - 1.2, 0.0, 1.5, 0.14, 0.4, 3.0, 0), (DX + 1.2, 0.0, 1.5, 0.14, 0.4, 3.0, 0),
                       (DX, 0.0, 3.05, 2.54, 0.4, 0.8, 0)], [WHITE])
boxes_obj('dq_back', [(DX, 0.42, 1.3, 2.3, 0.05, 2.6, 0)], [DQRED])
boxes_obj('dq_counter', [(DX, -0.05, 0.5, 2.2, 0.5, 1.0, 0), (DX, -0.31, 0.62, 2.2, 0.02, 0.16, 1)], [WHITE, DQRED])
for i, c_ in enumerate(['f2c879', 'f4f1ea', 'f2c879']):
    prim('box', f'dq_menu{i}', (DX - 0.7 + i * 0.7, 0.38, 2.0), (0.3, 0.02, 0.22), toon(f'menu{i}', hx(c_), lit=0.3))
sg = prim('cyl', 'dq_sign', (DX, -0.25, 3.15), (1.0, 0.58, 0.05), DQRED, rot=(H90, 0, 0), seg=28)
prim('cyl', 'dq_signrim', (DX, -0.23, 3.15), (1.07, 0.65, 0.04), TXT_W, rot=(H90, 0, 0), seg=28)
text('dq_txt', 'DQ', (DX, -0.31, 3.15), 0.8, TXT_W)
boxes_obj('dq_band', [(DX, -0.32, 2.42, 2.5, 0.06, 0.22, 0)], [DQBLUE])
text('dq_txt2', 'DAIRY QUEEN', (DX, -0.36, 2.42), 0.17, TXT_W)
for i in range(3):     # cups on the counter
    prim('frustum', f'dq_cupc{i}', (DX - 0.5 + i * 0.5, -0.1, 1.09), (0.07, 0.07, 0.09), WHITE, rot=(math.pi, 0, 0), seg=12)
    prim('sph', f'dq_cupt{i}', (DX - 0.5 + i * 0.5, -0.1, 1.19), (0.07, 0.07, 0.035), toon('icecream', hx('f3e6cf')), seg=12)
# Sushi Zanmai (right)
ZX = 1.45
boxes_obj('zm_front', [(ZX - 1.2, 0.0, 1.5, 0.16, 0.4, 3.0, 0), (ZX + 1.2, 0.0, 1.5, 0.16, 0.4, 3.0, 0),
                       (ZX, 0.0, 3.05, 2.56, 0.4, 0.8, 0)], [WOOD])
boxes_obj('zm_back', [(ZX, 0.42, 1.3, 2.3, 0.05, 2.6, 0)], [CREAM])
boxes_obj('zm_counter', [(ZX, 0.0, 0.5, 2.2, 0.5, 1.0, 0), (ZX, 0.0, 1.03, 2.3, 0.6, 0.06, 0)], [WOOD, HINOKI])
boxes_obj('zm_board', [(ZX, -0.23, 3.1, 2.36, 0.06, 0.62, 0)], [toon('zmboard', hx('f6f1e4'), lit=0.4)])
text('zm_txt', 'すしざんまい', (ZX, -0.27, 3.18), 0.36, TXT_R)
text('zm_txt2', 'SUSHI ZANMAI', (ZX, -0.27, 2.92), 0.14, TXT_K)
for i in range(3):     # noren curtain, swaying in the doorway breeze
    nr = prim('box', f'zm_noren{i}', (0, 0, -0.32), (0.35, 0.012, 0.32), NAVY)
    pv = empty(f'zm_nor_pv{i}', (ZX - 0.74 + i * 0.74, -0.24, 2.66)); nr.parent = pv
    drv(pv, 'rotation_euler', 0, f'0.10*sin(frame*0.09+{i * 1.3:.1f})+0.04*sin(frame*0.23+{i:.1f})')
    if i == 1:
        tx = text('zm_norentxt', 'すし', (0, -0.016, -0.3), 0.2, TXT_W); tx.parent = pv
for s_ in (-1, 1):
    prim('sph', f'zm_lant{s_}', (ZX + s_ * 1.4, -0.4, 2.45), (0.14, 0.14, 0.2), TXT_R, seg=12)
prim('sph', 'chef0_tray', (ZX + 0.6, -0.05, 1.08), (0.14, 0.1, 0.02), toon('platew', hx('f4f1ea')), seg=12)
c0 = person('chef0', hx('f4f1ea'), hx('34374a'), walk=False, hair='short', top='shirt', face=True, shadow=False)
c0.location = (ZX - 0.3, 0.25, 0); c0.rotation_euler = (0, 0, math.pi)
s0 = person('srv0', hx('d3202e'), hx('34374a'), walk=False, hair='cap', top='tee', face=True, shadow=False)
s0.location = (DX + 0.4, 0.25, 0); s0.rotation_euler = (0, 0, math.pi)
# FIRST IN HK stamp: thumps on at frame 18-30 over the mall wall between the two signs
st = empty('stamp', (1.95, -0.6, 5.9))
prim('cyl', 'stamp_disc', (0, 0, 0), (0.95, 0.95, 0.04), toon('stampred', hx('c8302a'), lit=0.05), rot=(H90, 0, 0), seg=32).parent = st
prim('cyl', 'stamp_ring', (0, -0.03, 0), (0.82, 0.82, 0.01), toon('stampring', hx('f6efe0'), lit=0.5), rot=(H90, 0, 0), seg=32).parent = st
prim('cyl', 'stamp_in', (0, -0.05, 0), (0.76, 0.76, 0.01), toon('stampred', hx('c8302a'), lit=0.05), rot=(H90, 0, 0), seg=32).parent = st
text('stamp_en', 'FIRST IN HK', (0, -0.08, 0.2), 0.24, TXT_W).parent = st
text('stamp_zh', '香港首間', (0, -0.08, -0.17), 0.36, TXT_W).parent = st
kv(st, 'scale', [(0, (0.001, 0.001, 0.001)), (16, (0.001, 0.001, 0.001)), (22, (0.75, 0.75, 0.75)), (27, (0.57, 0.57, 0.57)), (31, (0.6, 0.6, 0.6))])
kv(st, 'rotation_euler', [(16, (0, 0.5, 0)), (24, (0, -0.12, 0)), (31, (0, -0.12, 0))])
# shoppers crossing in front of the shops
WALK = [(-4.2, -1.6, 1, 1.15, 0.0), (4.0, -2.2, -1, 1.25, 1.1), (-5.0, -2.8, 1, 1.3, 2.0), (0.6, -1.3, 1, 1.0, 0.5)]
for i, (x0, y0, d_, sp, ph) in enumerate(WALK):
    rr = random.Random(300 + i)
    p = person(f'w{i}', rr.choice(P['cloth']), rr.choice(P['pants']), scale=rr.uniform(0.93, 1.04), speed=sp, phase=ph, face=False, rr=rr)
    p.location = (x0, y0, 0); p.rotation_euler = (0, 0, -d_ * H90)
    drv(p, 'location', 0, f'{x0}+{d_ * sp:.2f}*frame/30')

# ---------------- S2: Dairy Queen counter, the Blizzard flipped upside down (x 20) ----------------
QX = 20.0
floor('floor2', QX, 8, 10)
boxes_obj('q_wall', [(QX, 2.0, 2.0, 6.0, 0.2, 4.0, 0), (QX, 1.88, 0.55, 6.0, 0.05, 0.25, 1)], [DQRED, WHITE])
for i, (c_, en) in enumerate([('f2c879', 'BLIZZARD'), ('f4f1ea', 'DQ'), ('9fc5e8', 'SHAKES')]):
    prim('box', f'q_menu{i}', (QX - 0.85 + i * 0.85, 1.86, 2.1), (0.36, 0.02, 0.26), toon(f'qmenu{i}', hx(c_), lit=0.3))
    text(f'q_menut{i}', en, (QX - 0.85 + i * 0.85, 1.83, 2.22), 0.1, TXT_R if i != 1 else DQRED)
    for k in range(3):
        prim('box', f'q_menul{i}{k}', (QX - 0.85 + i * 0.85, 1.83, 2.06 - k * 0.08), (0.25, 0.005, 0.012), TXT_K)
boxes_obj('q_counter', [(QX, 0.35, 0.5, 3.6, 0.7, 1.0, 0), (QX, 0.35, 1.02, 3.7, 0.75, 0.04, 1), (QX, -0.01, 0.75, 3.6, 0.02, 0.18, 2)],
          [WHITE, toon('qtop', hx('e8e2d8')), DQRED])
srv = person('srv', hx('d3202e'), hx('34374a'), walk=False, hair='cap', top='tee', face=True, shadow=False, scale=1.0)
srv.location = (QX + 0.55, 1.05, 0); srv.rotation_euler = (0, 0, math.pi)
prim('box', 'q_till', (QX - 1.0, 0.5, 1.15), (0.18, 0.15, 0.1), DARK)
# the hand holding the Blizzard: pivot on the forearm axis (x), the wrist rolls the cup over
G = empty('cupG', (QX, 0.25, 1.165))
cup = empty('cup', (0, 0, 0), parent=G)
prim('frustum', 'cup_body', (0, 0, 0), (0.085, 0.085, 0.125), WHITE, rot=(math.pi, 0, 0), seg=16, parent=cup)
prim('cyl', 'cup_band', (0, 0, -0.01), (0.083, 0.083, 0.03), DQRED, seg=16, parent=cup)
prim('cyl', 'cup_band2', (0, 0, 0.035), (0.087, 0.087, 0.012), DQBLUE, seg=16, parent=cup)
text('cup_dq', 'DQ', (0, -0.089, -0.012), 0.045, TXT_W).parent = cup
prim('sph', 'cup_top', (0, 0, 0.125), (0.085, 0.085, 0.045), toon('icecream', hx('f3e6cf')), seg=14, parent=cup)
for k in range(9):
    a = k * 2.4; r_ = 0.025 + 0.05 * ((k * 37) % 10) / 10
    prim('ico', f'crumb{k}', (r_ * math.cos(a), r_ * math.sin(a), 0.16 - r_ * 0.35), (0.011, 0.011, 0.008), toon('cookie', hx('4a3428')), parent=cup)
prim('box', 'spoon', (0.02, 0.0, 0.19), (0.012, 0.004, 0.11), DQRED, rot=(0, 0.25, 0), parent=cup)
prim('sph', 'hand', (0.1, 0.0, 0.0), (0.05, 0.045, 0.065), toon('skin0', SKINS[0]), seg=10, parent=cup)
for k in range(3):
    prim('cyl', f'finger{k}', (0.065, -0.04, 0.03 - k * 0.032), (0.016, 0.016, 0.03), toon('skin0', SKINS[0]), rot=(0, H90, 0), seg=8, parent=cup)
prim('cyl', 'forearm', (0.4, 0.0, 0.0), (0.042, 0.042, 0.3), toon('skin0', SKINS[0]), rot=(0, H90, 0), seg=10, parent=G)
prim('cyl', 'cuff', (0.68, 0.0, 0.0), (0.055, 0.055, 0.08), DQRED, rot=(0, H90, 0), seg=10, parent=G)
# lift from the counter while L2 plays, then the famous flip on "Upside Down" (f182) and hold: nothing falls
kv(G, 'location', [(81, (QX, 0.25, 1.165)), (110, (QX, 0.25, 1.165)), (140, (QX, 0.12, 1.38)), (300, (QX, 0.1, 1.4))])
kv(G, 'rotation_euler', [(81, (0, 0, 0)), (176, (0, 0, 0)), (196, (math.pi * 1.04, 0, 0)), (204, (math.pi * 0.98, 0, 0)), (212, (math.pi, 0, 0)), (302, (math.pi, 0, 0))])
# a customer's shoulder at the left edge
cu = person('cust', hx('3f5f8f'), hx('34374a'), walk=False, hair='pony', top='jacket', shadow=False)
cu.location = (QX - 0.8, -0.35, 0); cu.rotation_euler = (0, 0, 0.3)

# ---------------- S3: Sushi Zanmai counter, chef slices bluefin, 3-piece plate slides in (x 40) ----------------
SX = 40.0
floor('floor3', SX, 8, 10)
boxes_obj('s_wall', [(SX, 2.1, 2.0, 6.0, 0.2, 4.0, 0), (SX, 1.98, 2.9, 6.0, 0.05, 0.5, 1)], [CREAM, WOOD])
text('s_walltxt', 'すしざんまい', (SX, 1.94, 2.9), 0.26, toon('txtcream', hx('f6efe0'), lit=0.4))
boxes_obj('s_counter', [(SX, 0.35, 0.5, 3.6, 0.7, 1.0, 0), (SX, 0.35, 1.02, 3.7, 0.8, 0.04, 1)], [WOOD, HINOKI])
boxes_obj('s_board', [(SX, 0.62, 1.065, 1.6, 0.42, 0.05, 0)], [toon('board', hx('efe3c6'))])
chef = person('chef', hx('f4f1ea'), hx('34374a'), walk=False, hair='short', top='shirt', face=True, shadow=False)
chef.location = (SX + 0.2, 1.3, 0); chef.rotation_euler = (0, 0, math.pi)
hd = bpy.data.objects['chef_hd']
prim('cyl', 'chef_hat', (0, 0, 0.25), (0.095, 0.1, 0.06), WHITE, parent=hd, seg=12)
prim('box', 'chef_band', (0, 0, 0.185), (0.097, 0.102, 0.015), NAVY, parent=hd)
# the tuna on the board (head to the right), with a red block of loin at the cut end
TU = empty('tuna', (SX - 0.55, 0.62, 1.2))
prim('sph', 'tuna_back', (0, 0, 0.02), (0.55, 0.17, 0.15), toon('tunaback', hx('2b3a58')), seg=16, parent=TU)
prim('sph', 'tuna_belly', (0, -0.005, -0.04), (0.53, 0.16, 0.12), toon('tunabelly', hx('cfd3da'), lit=0.2), seg=16, parent=TU)
prim('cone', 'tuna_tail', (-0.62, 0, 0), (0.1, 0.06, 0.12), toon('tunaback', hx('2b3a58')), rot=(0, -H90, 0), parent=TU)
prim('box', 'tuna_fin', (-0.76, 0, 0), (0.03, 0.02, 0.16), toon('tunaback', hx('2b3a58')), rot=(0, 0.2, 0), parent=TU)
prim('cone', 'tuna_dorsal', (-0.1, 0, 0.16), (0.07, 0.015, 0.07), toon('fin', hx('d9b13a')), parent=TU)
prim('sph', 'tuna_eye', (0.43, -0.12, 0.04), (0.03, 0.01, 0.03), DARK, parent=TU)
prim('box', 'loin_red', (SX + 0.12, 0.62, 1.14), (0.16, 0.12, 0.05), toon('akami', hx('b52a37'), lit=0.05))
prim('box', 'loin_pink', (SX + 0.12, 0.62, 1.2), (0.16, 0.12, 0.018), toon('otoro', hx('efb3ab'), lit=0.15))
# chef's right arm saws the knife (parented to the forearm), slices appear on the board
sh = bpy.data.objects['chef_sh-1']; el = bpy.data.objects['chef_el-1']
for o_ in (sh, el): o_.animation_data_clear()
drv(sh, 'rotation_euler', 0, '1.2+0.08*sin(frame*0.33)'); drv(sh, 'rotation_euler', 1, '0.0'); el.rotation_euler = (0.55, 0, 0)
sh2 = bpy.data.objects['chef_sh1']; el2 = bpy.data.objects['chef_el1']
for o_ in (sh2, el2): o_.animation_data_clear()
sh2.rotation_euler = (0.9, 0, -0.3); el2.rotation_euler = (0.7, 0, 0)
kn = empty('knife', (SX + 0.1, 0.66, 1.27))
drv(kn, 'location', 0, f'{SX + 0.1}+0.06*sin(frame*0.33)'); drv(kn, 'location', 2, '1.25+0.025*cos(frame*0.33)')
kn.rotation_euler = (0, 0.12, 0)
prim('box', 'knife_blade', (0.0, 0, 0), (0.24, 0.006, 0.028), STEEL, parent=kn)
prim('box', 'knife_handle', (0.31, 0, 0.005), (0.08, 0.014, 0.016), WOOD, parent=kn)
for k, f in enumerate((340, 370, 400)):
    sl = prim('box', f'slice{k}', (SX + 0.4 + k * 0.1, 0.5, 1.1), (0.045, 0.09, 0.012), toon('chutoro', hx('e0707a'), lit=0.1), rot=(0, 0, 0.15))
    kv(sl, 'scale', [(303, (0.001, 0.001, 0.001)), (f, (0.001, 0.001, 0.001)), (f + 6, (0.045, 0.09, 0.012))])
# the plate of 3 (otoro, chutoro, akami) slides along the counter to the front on "Dine in" (L5 ~ f428)
PL = empty('plate', (SX + 2.4, 0.1, 1.045))
prim('cyl', 'plate_disc', (0, 0, 0), (0.24, 0.13, 0.012), toon('plateblk', hx('2e2b2b')), seg=24, parent=PL)
for k, (nm, c_) in enumerate([('otoro', 'efb3ab'), ('chutoro', 'e0707a'), ('akami', 'b52a37')]):
    x_ = -0.14 + k * 0.14
    prim('box', f'rice{k}', (x_, 0, 0.032), (0.05, 0.028, 0.022), WHITE, parent=PL)
    prim('box', f'neta{k}', (x_, 0, 0.058), (0.058, 0.032, 0.01), toon(f'neta_{nm}', hx(c_), lit=0.1), rot=(0, 0.06, 0), parent=PL)
prim('box', 'ginger', (0.2, 0.04, 0.02), (0.025, 0.02, 0.012), toon('ginger', hx('f2c6b0')), parent=PL)
kv(PL, 'location', [(303, (SX + 2.4, 0.1, 1.045)), (424, (SX + 2.4, 0.1, 1.045)), (448, (SX + 0.28, 0.1, 1.045)), (456, (SX + 0.22, 0.1, 1.045)), (555, (SX + 0.22, 0.1, 1.045))])
cu2 = person('cust2', hx('4d7a5a'), hx('34374a'), walk=False, hair='short', top='tee', shadow=False)
cu2.location = (SX - 0.95, -0.3, 0); cu2.rotation_euler = (0, 0, 0.35)
def cam(name, keys, lens=24):
    cd = bpy.data.cameras.new(name); cd.lens = lens; cd.sensor_width = 36; cd.clip_end = 400
    c = bpy.data.objects.new(name, cd); sc.collection.objects.link(c)
    tgt = bpy.data.objects.new(name + '_tgt', None); sc.collection.objects.link(tgt)
    con = c.constraints.new('TRACK_TO'); con.target = tgt; con.track_axis = 'TRACK_NEGATIVE_Z'; con.up_axis = 'UP_Y'
    for f, pos, look in keys:
        c.location = pos; c.keyframe_insert('location', frame=f)
        tgt.location = look; tgt.keyframe_insert('location', frame=f)
    for ob in (c, tgt):
        for fcu in ob.animation_data.action.fcurves:
            for kp in fcu.keyframe_points: kp.interpolation = 'LINEAR'
    return c


C1 = cam('S1', [(0, (0.0, -7.9, 3.0), (0, 0, 4.3)), (80, (0.0, -7.3, 3.0), (0, 0, 4.25))], lens=28)
C2 = cam('S2', [(81, (QX - 0.1, -1.6, 1.62), (QX + 0.08, 0.4, 1.3)), (150, (QX - 0.05, -1.05, 1.6), (QX + 0.08, 0.15, 1.36)), (302, (QX, -0.85, 1.58), (QX + 0.08, 0.1, 1.38))], lens=32)
C3 = cam('S3', [(303, (SX - 0.1, -1.45, 1.72), (SX + 0.05, 0.7, 1.28)), (420, (SX - 0.05, -1.3, 1.68), (SX + 0.1, 0.6, 1.22)),
                (460, (SX + 0.1, -1.0, 1.45), (SX + 0.2, 0.2, 1.08)), (555, (SX + 0.15, -0.85, 1.42), (SX + 0.2, 0.2, 1.08))], lens=32)
for f, c in ((0, C1), (81, C2), (303, C3)):
    mk = sc.timeline_markers.new(c.name, frame=f); mk.camera = c
sc.camera = C1
# ---------------- passes for our own ink pass (Freestyle is 138 s/frame on this box) ----------------
sc.render.use_freestyle = False
vl = sc.view_layers[0]; vl.use_pass_z = True; vl.use_pass_normal = True; vl.use_pass_object_index = True
k = 3
for ob in bpy.data.objects:
    if ob.type in ('MESH', 'FONT'):
        cn = [c_.name for c_ in ob.users_collection]
        if 'NoInk' in cn: ob.pass_index = 1
        elif 'Ground' in cn: ob.pass_index = 2          # road, pavements and contact shadows share one id: no lines between them
        else: ob.pass_index = k; k += 1
for ob in bpy.data.objects:           # face details / highlights share their parent's id, so no ink ring round them
    if 'same_idx' in ob and ob['same_idx'] in bpy.data.objects:
        ob.pass_index = bpy.data.objects[ob['same_idx']].pass_index
print('INDEXED', k)
sc.use_nodes = True; ct = sc.node_tree; ct.nodes.clear()
rl = ct.nodes.new('CompositorNodeRLayers'); comp = ct.nodes.new('CompositorNodeComposite')
ct.links.new(rl.outputs['Image'], comp.inputs['Image'])
fo = ct.nodes.new('CompositorNodeOutputFile'); fo.base_path = '//pass/'
fo.format.file_format = 'PNG'; fo.format.color_depth = '16'; fo.format.color_mode = 'RGB'
fo.format.color_management = 'OVERRIDE'; fo.format.view_settings.view_transform = 'Raw'
fo.file_slots.clear()
for nm in ('nrm_', 'dep_', 'idx_'): fo.file_slots.new(nm)
a1 = ct.nodes.new('CompositorNodeMixRGB'); a1.blend_type = 'ADD'; a1.inputs[0].default_value = 1; a1.inputs[2].default_value = (1, 1, 1, 1)
a2 = ct.nodes.new('CompositorNodeMixRGB'); a2.blend_type = 'MULTIPLY'; a2.inputs[0].default_value = 1; a2.inputs[2].default_value = (0.5, 0.5, 0.5, 1)
ct.links.new(rl.outputs['Normal'], a1.inputs[1]); ct.links.new(a1.outputs[0], a2.inputs[1]); ct.links.new(a2.outputs[0], fo.inputs['nrm_'])
dd = ct.nodes.new('CompositorNodeMath'); dd.operation = 'DIVIDE'; dd.inputs[1].default_value = 300; dd.use_clamp = True
ct.links.new(rl.outputs['Depth'], dd.inputs[0]); ct.links.new(dd.outputs[0], fo.inputs['dep_'])
di = ct.nodes.new('CompositorNodeMath'); di.operation = 'DIVIDE'; di.inputs[1].default_value = 65535
ct.links.new(rl.outputs['IndexOB'], di.inputs[0]); ct.links.new(di.outputs[0], fo.inputs['idx_'])
sc.render.image_settings.file_format = 'PNG'; sc.render.image_settings.color_depth = '8'
sc.render.filepath = '//pass/img_'

out = sys.argv[sys.argv.index('--') + 1]
bpy.ops.wm.save_as_mainfile(filepath=out)
print('SAVED', out, len(bpy.data.objects), 'objects')
# ---- framing check printed in the log: screen position of the key items per shot ----
from bpy_extras.object_utils import world_to_camera_view
for f, cn, names in ((25, 'S1', ['dq_sign', 'zm_board', 'stamp', 'dq_counter', 'zm_noren1', 'chef0_head', 'srv0_head']),
                     (150, 'S2', ['cup_body', 'hand', 'forearm', 'cuff', 'srv_head', 'q_menu1', 'cust_head']),
                     (250, 'S2', ['cup_body', 'cup_top', 'hand']),
                     (360, 'S3', ['tuna_back', 'loin_red', 'knife_blade', 'chef_head', 'chef_hat', 'slice0']),
                     (500, 'S3', ['plate_disc', 'neta0', 'neta2', 'tuna_back', 'cust2_head'])):
    sc.frame_set(f); cobj = bpy.data.objects[cn]
    for nm in names:
        ob = bpy.data.objects[nm]; v = world_to_camera_view(sc, cobj, ob.matrix_world.translation)
        print(f'FRAME {f} {cn} {nm:12s} x={v.x * 1080:6.0f} y={(1 - v.y) * 1920:6.0f} d={v.z:5.2f}')
