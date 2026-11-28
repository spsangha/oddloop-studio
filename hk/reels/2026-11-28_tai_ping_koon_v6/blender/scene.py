# Tai Ping Koon 太平館 - set swapped into the Temple Street plate engine (HK Unlocked, Blender 4.2), warm daylight
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
# SET: S1 old shopfront + SINCE 1860 stamp (x 0) · S2 Swiss wings, sweet/Swiss (x 20) · S3 roast pigeon (x 40) · S4 giant soufflé (x 60)
# plate frames 0..542 at 30 fps = video time: S1 0-188, S2 189-313, S3 314-413, S4 414-542
# =====================================================================================
sc.frame_end = 542
H90 = math.radians(90)
WHITE = toon('white', hx('f4f1ea'), lit=0.35); CREAM = toon('cream', hx('e8dfcf'))
WOOD = toon('wood', hx('5a3a24')); DKGREEN = toon('dkgreen', hx('2f4a3a')); RED = toon('tpkred', hx('a3282a'), lit=0.05)
GOLD = toon('gold', hx('e2b54a'), lit=0.3); DARK = toon('dark', hx('2a2626')); BRASS = toon('brass', hx('c79a45'))
CLOTH = toon('cloth', hx('f6f2e8'), lit=0.4, mottle=0.04); TXT_W = toon('txtw', hx('ffffff'), lit=0.6); TXT_K = toon('txtk', hx('2a2626'))
GLASS = toon('glass', hx('8aa1a8')); TILE = toon('tile', hx('d8cbb2'), mottle=0.05)
def floor(name, cx, w_=14, d_=12, col='cbbfa9'):
    boxes_obj(name, [(cx, -2.0, -0.05, w_, d_, 0.1, 0)], [toon('floor' + col, hx(col), mottle=0.05)], coll=GROUND)
def kv(ob, path, keys, interp='BEZIER'):
    for f, v in keys:
        setattr(ob, path, v); ob.keyframe_insert(path, frame=f)
    for fc in ob.animation_data.action.fcurves:
        for kp in fc.keyframe_points: kp.interpolation = interp
def bowtie(pname, s=1.0):
    root = bpy.data.objects[pname]
    for sx in (-1, 1):
        prim('cone', f'{pname}_bow{sx}', (sx * 0.028 * s, 0.112 * s, 1.405 * s), (0.022 * s, 0.01 * s, 0.03 * s), DARK, rot=(0, sx * H90, 0), seg=4, parent=root)
    prim('sph', f'{pname}_knot', (0, 0.118 * s, 1.405 * s), (0.012 * s, 0.01 * s, 0.012 * s), DARK, parent=root, seg=6)
def steam(prefix, x, y, z, n=6, spread=0.12, rise=0.45, rate=0.011, size=0.035, f0=0):
    """steam puffs: small soft blobs that rise, drift and shrink in a loop (no ink lines)"""
    m = toon('steam', hx('fbf8f2'), lit=0.7, mottle=0.02)
    for k in range(n):
        ph = k / n; dx = (k % 3 - 1) * spread * 0.5
        p = prim('sph', f'{prefix}{k}', (x + dx, y, z), (size, size, size), m, coll=NOINK, seg=8)
        u = f'(((frame-{f0})*{rate}+{ph:.3f})%1.0)'
        drv(p, 'location', 2, f'{z}+{rise}*{u}')
        drv(p, 'location', 0, f'{x + dx}+0.04*sin(frame*0.07+{k})*{u}')
        for i in range(3): drv(p, 'scale', i, f'{size}*(0.5+1.6*{u})*(1-{u})*(1 if frame>={f0} else 0)')
def shine(name, parent, loc, sc_, axis_len, speed=0.05, ph=0.0):
    """a glossy highlight that slides along the glaze"""
    m = toon('shine', hx('fff6e0'), lit=1.0, mottle=0.0)
    s_ = prim('sph', name, loc, sc_, m, coll=NOINK, seg=8, parent=parent)
    drv(s_, 'location', 0, f'{loc[0]}+{axis_len}*sin(frame*{speed}+{ph})')
    return s_
def bubble(name, loc, body, f_on, f_off, size=0.11, w=0.5, h=0.22):
    B = empty(name, loc)
    prim('cyl', name + '_disc', (0, 0, 0), (w, h, 0.012), toon('bubble', hx('fffdf6'), lit=0.6), rot=(H90, 0, 0), seg=24, parent=B)
    prim('cone', name + '_tail', (-w * 0.45, 0, -h * 0.95), (0.05, 0.012, 0.09), toon('bubble', hx('fffdf6'), lit=0.6), rot=(0, -0.5, 0), seg=3, parent=B)
    text(name + '_t', body, (0, -0.02, 0), size, TXT_K).parent = B
    kv(B, 'scale', [(0, (0.001,) * 3), (f_on, (0.001,) * 3), (f_on + 5, (1.15,) * 3), (f_on + 9, (1.0,) * 3), (f_off, (1.0,) * 3), (f_off + 4, (0.001,) * 3)])
    return B

# ---------------- S1: the old Tai Ping Koon shopfront + SINCE 1860 stamp ----------------
floor('floor1', 0, 16, 14, 'b9b0a2')
boxes_obj('bldg', [(0, 0.6, 6.0, 7.0, 0.3, 12.0, 0)], [toon('bldg', hx('e3d2b4'))])
boxes_obj('bldg_win', [(x_, 0.43, z_, 1.0, 0.06, 1.1, 0) for x_ in (-2.2, 0, 2.2) for z_ in (5.6, 7.6, 9.6)], [GLASS])
boxes_obj('front', [(-2.6, 0.0, 1.5, 0.5, 0.4, 3.0, 0), (2.6, 0.0, 1.5, 0.5, 0.4, 3.0, 0), (0, 0.0, 3.25, 5.7, 0.4, 0.5, 0)], [WOOD])
boxes_obj('front_low', [(-1.55, -0.02, 0.45, 1.6, 0.36, 0.9, 0), (1.55, -0.02, 0.45, 1.6, 0.36, 0.9, 0)], [DKGREEN])
boxes_obj('front_glass', [(-1.55, 0.05, 1.85, 1.6, 0.05, 1.9, 0), (1.55, 0.05, 1.85, 1.6, 0.05, 1.9, 0)], [toon('glasswarm', hx('e9c98a'), lit=0.4)])
boxes_obj('front_mull', [(x_, -0.02, 1.85, 0.06, 0.08, 1.9, 0) for x_ in (-1.55, 1.55)] + [(x_, -0.02, 1.85, 1.6, 0.08, 0.06, 0) for x_ in (-1.55, 1.55)], [WOOD])
boxes_obj('door', [(0, 0.1, 1.3, 1.3, 0.05, 2.6, 0)], [toon('doorin', hx('6b4a2e'))])
boxes_obj('door_frame', [(-0.68, -0.02, 1.3, 0.08, 0.1, 2.6, 0), (0.68, -0.02, 1.3, 0.08, 0.1, 2.6, 0), (0, -0.02, 2.62, 1.44, 0.1, 0.08, 0)], [BRASS])
# the big red signboard with gold characters
boxes_obj('sign', [(0, -0.3, 4.15, 3.3, 0.14, 1.15, 0)], [RED])
boxes_obj('sign_rim', [(0, -0.37, 4.15, 3.4, 0.02, 1.25, 0)], [GOLD])
boxes_obj('sign_in', [(0, -0.39, 4.15, 3.15, 0.02, 1.05, 0)], [RED])
text('sign_zh', '太平館', (0, -0.41, 4.28), 0.7, GOLD)
text('sign_en', 'TAI PING KOON RESTAURANT', (0, -0.41, 3.77), 0.15, GOLD)
for i, (x_, z_) in enumerate(((-1.55, 2.95), (1.55, 2.95))):
    text(f'win_txt{i}', ['西餐', '餐廳'][i], (x_, 0.0, z_ - 0.25), 0.22, toon('wintxt', hx('f6efe0'), lit=0.5))
# old wall lamps either side of the door
for s_ in (-1, 1):
    prim('sph', f'lamp{s_}', (s_ * 0.95, -0.3, 2.35), (0.1, 0.1, 0.14), toon('lamp', hx('ffe2a8'), lit=0.7), seg=10)
    prim('box', f'lampb{s_}', (s_ * 0.95, -0.2, 2.2), (0.03, 0.1, 0.03), BRASS)
# the waiter in a white jacket and black bow tie at the door, holding a covered plate
wt = person('waiter0', hx('f4f1ea'), hx('2c2c30'), walk=False, hair='short', top='shirt', face=True, shadow=True)
wt.location = (0.0, -3.0, 0); wt.rotation_euler = (0, 0, math.pi)
bowtie('waiter0')
for nm, rot in (('waiter0_sh1', (0.95, 0, -0.25)), ('waiter0_el1', (0.85, 0, 0))):
    o_ = bpy.data.objects[nm]; o_.animation_data_clear(); o_.rotation_euler = rot
drv(wt, 'location', 2, '0.004*sin(frame*0.12)')
# SINCE 1860 stamp: thumps on low on the right, well inside the frame (in front of the walkers)
st = empty('stamp', (0.85, -2.2, 0.6))
prim('cyl', 'stamp_disc', (0, 0, 0), (0.95, 0.95, 0.04), toon('stampred', hx('c8302a'), lit=0.05), rot=(H90, 0, 0), seg=32).parent = st
prim('cyl', 'stamp_ring', (0, -0.03, 0), (0.82, 0.82, 0.01), toon('stampring', hx('f6efe0'), lit=0.5), rot=(H90, 0, 0), seg=32).parent = st
prim('cyl', 'stamp_in', (0, -0.05, 0), (0.76, 0.76, 0.01), toon('stampred', hx('c8302a'), lit=0.05), rot=(H90, 0, 0), seg=32).parent = st
text('stamp_en', 'SINCE', (0, -0.08, 0.36), 0.22, TXT_W).parent = st
text('stamp_num', '1860', (0, -0.08, 0.02), 0.46, TXT_W).parent = st
text('stamp_zh', '創於廣州', (0, -0.08, -0.38), 0.22, TXT_W).parent = st
kv(st, 'scale', [(0, (0.001, 0.001, 0.001)), (16, (0.001, 0.001, 0.001)), (22, (0.7, 0.7, 0.7)), (27, (0.58, 0.58, 0.58)), (31, (0.62, 0.62, 0.62)), (188, (0.62, 0.62, 0.62))])
kv(st, 'rotation_euler', [(16, (0, 0.5, 0)), (24, (0, -0.12, 0)), (31, (0, -0.12, 0))])
WALK = [(-4.2, -1.3, 1, 1.15, 0.0), (4.0, -1.7, -1, 1.25, 1.1), (-6.4, -1.5, 1, 1.3, 2.0), (1.4, -1.0, 1, 0.9, 0.5)]
for i, (x0, y0, d_, sp, ph) in enumerate(WALK):
    rr = random.Random(300 + i)
    p = person(f'w{i}', rr.choice(P['cloth']), rr.choice(P['pants']), scale=rr.uniform(0.93, 1.04), speed=sp, phase=ph, face=False, rr=rr)
    p.location = (x0, y0, 0); p.rotation_euler = (0, 0, -d_ * H90)
    drv(p, 'location', 0, f'{x0}+{d_ * sp:.2f}*frame/30')

def table(prefix, cx, w_=2.4, d_=1.3):
    boxes_obj(prefix + '_table', [(cx, 0.3, 0.72, w_, d_, 0.06, 0), (cx, 0.3 - d_ / 2 - 0.01, 0.55, w_, 0.02, 0.36, 0)], [CLOTH, CLOTH])
    boxes_obj(prefix + '_wall', [(cx, 2.4, 2.0, 7.0, 0.2, 4.0, 0), (cx, 2.28, 0.6, 7.0, 0.05, 1.2, 1), (cx, 2.27, 1.22, 7.0, 0.04, 0.05, 2)],
              [toon('wallcream', hx('efe3c8')), WOOD, BRASS])
    floor(prefix + '_floor', cx, 8, 10, 'c9b28e')
def plate(name, loc, rx=0.32, ry=0.22):
    P_ = empty(name, loc)
    prim('cyl', name + '_disc', (0, 0, 0), (rx, ry, 0.01), WHITE, seg=28, parent=P_)
    prim('cyl', name + '_rim', (0, 0, 0.012), (rx * 0.97, ry * 0.97, 0.002), toon('platerim', hx('d6b25a'), lit=0.3), seg=28, parent=P_)
    prim('cyl', name + '_in', (0, 0, 0.016), (rx * 0.9, ry * 0.9, 0.002), WHITE, seg=28, parent=P_)
    return P_

# ---------------- S2: Swiss wings, glossy dark sweet-soy glaze; "Sweet!" ... "Swiss?" (x 20) ----------------
QX = 20.0
table('q', QX)
GLAZE = toon('glaze', hx('6a2f16'), lit=0.08); GLAZE2 = toon('glaze2', hx('8a4120'), lit=0.1)
PW = plate('wingplate', (QX, 0.35, 0.76), 0.36, 0.24)
for k in range(6):
    a = -0.5 + (k % 3) * 0.5; row = k // 3
    W = empty(f'wing{k}', (-0.17 + (k % 3) * 0.17, -0.06 + row * 0.12, 0.05), parent=PW); W.rotation_euler = (0, 0, a); W.scale = (1.3, 1.3, 1.45)
    prim('sph', f'wing{k}_a', (-0.04, 0, 0), (0.07, 0.035, 0.03), GLAZE, seg=10, parent=W)
    prim('sph', f'wing{k}_b', (0.05, 0.0, 0.004), (0.055, 0.03, 0.026), GLAZE2, seg=10, parent=W, rot=(0, 0, 0.4))
    shine(f'wing{k}_sh', W, (0.0, -0.01, 0.028), (0.026, 0.008, 0.005), 0.035, speed=0.06, ph=k * 0.9)
prim('sph', 'lettuce', (QX + 0.24, 0.42, 0.79), (0.07, 0.05, 0.02), toon('lettuce', hx('7aa64a')), seg=8)
prim('cyl', 'saucebowl', (QX - 0.55, 0.15, 0.78), (0.07, 0.07, 0.03), WHITE, seg=14)
prim('cyl', 'sauce', (QX - 0.55, 0.15, 0.805), (0.06, 0.06, 0.004), GLAZE, seg=14)
steam('wst', QX, 0.4, 0.86, n=12, spread=0.3, rise=0.35, rate=0.012, size=0.016)
gu = person('guest', hx('3f5f8f'), hx('34374a'), walk=False, sit=True, hair='short', top='jacket', face=True, shadow=False)
gu.location = (QX - 0.5, 1.1, 0); gu.rotation_euler = (0, 0, math.pi + 0.35)
wq = person('waiter1', hx('f4f1ea'), hx('2c2c30'), walk=False, hair='short', top='shirt', face=True, shadow=False)
wq.location = (QX + 0.55, 1.15, 0); wq.rotation_euler = (0, 0, math.pi - 0.35)
bowtie('waiter1')
bubble('b_sweet', (QX - 0.48, 0.9, 1.84), 'Sweet!', 236, 313, size=0.12, w=0.34, h=0.15)
bubble('b_swiss', (QX + 0.5, 0.9, 1.95), 'Swiss?', 284, 313, size=0.12, w=0.34, h=0.15)
# head turns: the guest nods at "sweet", the waiter tilts his head at "Swiss"
kv(bpy.data.objects['guest_hd'], 'rotation_euler', [(189, (0, 0, 0)), (236, (0, 0, 0)), (242, (0.18, 0, 0)), (250, (0, 0, 0)), (313, (0, 0, 0))])
kv(bpy.data.objects['waiter1_hd'], 'rotation_euler', [(189, (0, 0, 0)), (284, (0, 0, 0)), (292, (0, 0.22, 0)), (313, (0, 0.22, 0))])

# ---------------- S3: roast pigeon, still made the original way, steaming (x 40) ----------------
SX = 40.0
table('s', SX)
SKIN = toon('pigeon', hx('9c4a22'), lit=0.08); SKIN2 = toon('pigeon2', hx('b8642e'), lit=0.12)
PP = plate('pigplate', (SX, 0.35, 0.76), 0.34, 0.23)
PG = empty('pigeon', (0.0, 0.0, 0.08), parent=PP)
prim('sph', 'pig_body', (0, 0, 0), (0.15, 0.1, 0.075), SKIN, seg=14, parent=PG)
prim('sph', 'pig_breast', (0.05, -0.02, 0.02), (0.1, 0.075, 0.06), SKIN2, seg=12, parent=PG)
prim('sph', 'pig_head', (0.19, -0.01, 0.03), (0.045, 0.04, 0.04), SKIN, seg=10, parent=PG)
prim('cone', 'pig_beak', (0.24, -0.01, 0.025), (0.02, 0.012, 0.014), toon('beak', hx('6a3018')), rot=(0, H90, 0), seg=6, parent=PG)
for s_ in (-1, 1):
    prim('cyl', f'pig_leg{s_}', (-0.12, s_ * 0.05, -0.02), (0.014, 0.014, 0.05), SKIN2, rot=(0, -1.2, 0), seg=6, parent=PG)
    prim('sph', f'pig_wing{s_}', (-0.02, s_ * 0.085, 0.01), (0.09, 0.025, 0.05), SKIN, seg=10, parent=PG)
shine('pig_sh', PG, (0.02, -0.06, 0.06), (0.04, 0.012, 0.01), 0.06, speed=0.05)
shine('pig_sh2', PG, (0.0, 0.03, 0.074), (0.035, 0.01, 0.006), 0.05, speed=0.045, ph=2.0)
for k in range(4):     # lemon wedge + prawn crackers round the plate
    prim('sph', f'cracker{k}', (SX - 0.24 + k * 0.05, 0.22 + (k % 2) * 0.06, 0.785), (0.05, 0.04, 0.008), toon('cracker', hx('f6ecd2'), lit=0.3), seg=8)
prim('sph', 'lemon', (SX + 0.24, 0.27, 0.79), (0.05, 0.03, 0.025), toon('lemon', hx('f0d24a'), lit=0.2), seg=8)
prim('cyl', 'saltdish', (SX + 0.5, 0.05, 0.775), (0.05, 0.05, 0.015), WHITE, seg=12)
steam('pst', SX, 0.35, 0.92, n=12, spread=0.25, rise=0.45, rate=0.013, size=0.017, f0=330)
# the plate is set down: it comes in from above-right on a waiter's hand, then the hand leaves
kv(PP, 'location', [(314, (SX + 0.9, 0.2, 1.15)), (322, (SX + 0.9, 0.2, 1.15)), (338, (SX + 0.03, 0.33, 0.78)), (344, (SX, 0.35, 0.76)), (413, (SX, 0.35, 0.76))])
HD = empty('hand', (SX + 1.3, 0.25, 1.15))
prim('cyl', 'sleeve', (0.45, 0, 0), (0.06, 0.06, 0.35), CLOTH, rot=(0, H90, 0), seg=10, parent=HD)
prim('sph', 'palm', (0.05, 0, -0.02), (0.06, 0.05, 0.03), toon('skin0', SKINS[0]), seg=10, parent=HD)
kv(HD, 'location', [(314, (SX + 1.25, 0.2, 1.1)), (322, (SX + 1.25, 0.2, 1.1)), (338, (SX + 0.4, 0.33, 0.74)), (348, (SX + 0.42, 0.33, 0.74)), (366, (SX + 2.2, 0.2, 1.0)), (413, (SX + 2.2, 0.2, 1.0))])

# ---------------- S4: the giant soufflé rising out of its dish (x 60) ----------------
UX = 60.0
table('u', UX)
DISH = toon('dish', hx('f2ede2'), lit=0.4)
prim('cyl', 'souf_dish', (UX, 0.35, 0.86), (0.27, 0.27, 0.11), DISH, seg=28)
prim('cyl', 'souf_dishrim', (UX, 0.35, 0.97), (0.285, 0.285, 0.012), toon('dishrim', hx('d6b25a'), lit=0.3), seg=28)
prim('cyl', 'souf_under', (UX, 0.35, 0.755), (0.4, 0.3, 0.01), WHITE, seg=28)
SF = empty('souffle', (UX, 0.35, 0.95))
prim('sph', 'souf_dome', (0, 0, 0.0), (0.3, 0.3, 0.5), toon('souffle', hx('e9b665'), lit=0.2, mottle=0.12), seg=24, parent=SF)
prim('sph', 'souf_crown', (0, -0.02, 0.38), (0.16, 0.16, 0.12), toon('souffle2', hx('d49a4a'), lit=0.15, mottle=0.12), seg=16, parent=SF)
for k in range(14):     # icing-sugar dust on the top
    a = k * 2.39; r_ = 0.04 + 0.11 * ((k * 37) % 10) / 10
    prim('ico', f'sugar{k}', (r_ * math.cos(a), r_ * math.sin(a), 0.47 - r_ * 0.4), (0.012, 0.012, 0.006), toon('sugar', hx('fffaf0'), lit=0.8), parent=SF)
# rises out of the dish from L5 (f414) to "giant" (f433) and keeps breathing
kv(SF, 'scale', [(414, (0.92, 0.92, 0.05)), (418, (0.92, 0.92, 0.05)), (440, (1.0, 1.0, 1.06)), (448, (1.0, 1.0, 0.98)), (455, (1.0, 1.0, 1.0)), (542, (1.0, 1.0, 1.0))])
drv(bpy.data.objects['souf_crown'], 'location', 2, '0.38+0.008*sin(frame*0.2)')
steam('ust', UX, 0.35, 1.45, n=12, spread=0.3, rise=0.4, rate=0.012, size=0.02, f0=440)
for s_ in (-1, 1):
    prim('box', f'spoon{s_}', (UX + s_ * 0.55, 0.05, 0.765), (0.02, 0.12, 0.006), toon('silver', hx('cfd3d8'), lit=0.3), rot=(0, 0, s_ * 0.2))
for s_ in (-1, 1):
    cu_ = person(f'diner{s_}', [hx('b9473f'), hx('4d7a5a')][s_ > 0], hx('34374a'), walk=False, sit=True, face=True, shadow=False)
    cu_.location = (UX + s_ * 0.55, 1.1, 0); cu_.rotation_euler = (0, 0, math.pi - s_ * 0.5)
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


C1 = cam("S1", [(0, (0.0, -6.0, 3.5), (0, 0, 1.5)), (188, (0.0, -5.85, 3.47), (0, 0, 1.5))], lens=26)
C2 = cam("S2", [(189, (QX - 0.1, -1.4, 1.55), (QX, 0.5, 1.0)), (313, (QX - 0.05, -1.15, 1.5), (QX, 0.5, 1.0))], lens=28)
C3 = cam("S3", [(314, (SX - 0.1, -0.95, 1.5), (SX, 0.4, 0.85)), (413, (SX, -0.7, 1.35), (SX, 0.38, 0.82))], lens=32)
C4 = cam("S4", [(414, (UX - 0.05, -1.4, 1.35), (UX, 0.35, 1.05)), (542, (UX, -1.15, 1.32), (UX, 0.35, 1.08))], lens=28)
for f, c in ((0, C1), (189, C2), (314, C3), (414, C4)):
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
# ---- framing check printed in the log: screen position of the key items per shot (the stamp edges must stay inside x 60-1020) ----
from bpy_extras.object_utils import world_to_camera_view
for f, cn, names in ((40, 'S1', ['sign', 'sign_zh', 'stamp', 'waiter0_head', 'door']),
                     (250, 'S2', ['wingplate', 'wing1_a', 'guest_head', 'waiter1_head', 'b_sweet']),
                     (300, 'S2', ['b_swiss', 'b_sweet', 'wingplate']),
                     (380, 'S3', ['pig_body', 'pig_head', 'pigplate', 'lemon']),
                     (500, 'S4', ['souf_dome', 'souf_crown', 'souf_dish', 'diner-1_head', 'diner1_head'])):
    sc.frame_set(f); cobj = bpy.data.objects[cn]
    for nm in names:
        ob = bpy.data.objects[nm]; v = world_to_camera_view(sc, cobj, ob.matrix_world.translation)
        print(f'FRAME {f} {cn} {nm:12s} x={v.x * 1080:6.0f} y={(1 - v.y) * 1920:6.0f} d={v.z:5.2f}')
for sf in (22, 31, 120):
  sc.frame_set(sf); stp = bpy.data.objects['stamp']; cobj = bpy.data.objects['S1']
  for dx, dz in ((-0.95, 0), (0.95, 0), (0, 0.95), (0, -0.95)):
    p = stp.matrix_world @ Vector((dx, 0, dz)); v = world_to_camera_view(sc, cobj, p)
    print(f'STAMP f{sf} edge x={v.x * 1080:6.0f} y={(1 - v.y) * 1920:6.0f}')
if 0: stp = bpy.data.objects['stamp']; cobj = bpy.data.objects['S1']
for dx, dz in ((-0.95, 0), (0.95, 0), (0, 0.95), (0, -0.95)):
    p = stp.matrix_world @ Vector((dx, 0, dz)); v = world_to_camera_view(sc, cobj, p)
    print(f'STAMP edge x={v.x * 1080:6.0f} y={(1 - v.y) * 1920:6.0f}')
