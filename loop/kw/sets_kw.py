"""Kinda Wild Films - reusable story sets (car interior on a moving road, hospital exam bay), worlds, skin, render finish.
Blender 4.2 / Cycles. All assets CC0 (Poly Haven, ambientCG) in os.environ['KW_ASSETS'] or <repo>/assets/real.

    import sets_kw as K
    car = K.build_car(S, ned)      # .coll  .wheel (steer with car.steer(rad) or wheel.rotation_euler[2])  .update(t)  .belt  .lights
    hos = K.build_hospital(S, ned) # .coll  .lights
    K.set_world(S, 'car' | 'hospital' | 'studio')   # cached worlds, cheap every frame
    K.finish(S, samples)           # AgX Punchy + OIDN/adaptive + bloom/vignette compositor
    K.skin(person); K.flush(person, v)   # tanned pore-detailed SSS skin; v 0..1 reddens skin (one node value)
Coordinates: driver seated at origin facing -Y, Z up, metres. Driver door is at -X, passenger seat at x=+0.75.
Each set carries its own lights inside its collection (hidden with the collection).
"""
import bpy, os, math, sys
from mathutils import Vector, Matrix
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
import kw_realism as R
import kwlook as Q

A = os.environ.get('KW_ASSETS', os.path.normpath(os.path.join(HERE, '..', '..', 'assets', 'real')))
def ap(*p): return os.path.join(A, *p)

# ------------------------------------------------------------------ small helpers
def _coll(S, name):
    c = bpy.data.collections.get(name) or bpy.data.collections.new(name)
    if c.name not in S.collection.children: S.collection.children.link(c)
    return c
def _link(c, o):
    for u in list(o.users_collection): u.objects.unlink(o)
    c.objects.link(o); return o
def _smooth(o):
    if o.type == 'MESH':
        for p in o.data.polygons: p.use_smooth = True
def mat(name, col, rough=0.5, metal=0.0, emit=None, es=1.0, coat=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True; b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*col, 1); b.inputs['Roughness'].default_value = rough; b.inputs['Metallic'].default_value = metal
    if coat: b.inputs['Coat Weight'].default_value = coat; b.inputs['Coat Roughness'].default_value = 0.03
    if emit: b.inputs['Emission Color'].default_value = (*emit, 1); b.inputs['Emission Strength'].default_value = es
    return m
def tex(name, folder, scale, tint=None, rough_mul=1.0, nor=1.0):
    return R.pbr_dir(name, ap('tex', folder), scale=scale, tint=tint, rough_mul=rough_mul, nor_strength=nor)
class _B:   # builds bevelled boxes into a collection
    def __init__(s, c): s.c = c
    def box(s, name, size, loc, m, bev=0.01, rot=(0, 0, 0), seg=2):
        me = bpy.data.meshes.new(name); import bmesh; bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0); bm.to_mesh(me); bm.free()
        o = bpy.data.objects.new(name, me); s.c.objects.link(o); o.location = loc; o.rotation_euler = [math.radians(a) for a in rot]; o.scale = size
        if bev:
            md = o.modifiers.new('bev', 'BEVEL'); md.width = bev; md.segments = seg; md.limit_method = 'ANGLE'; md.use_clamp_overlap = True
            md.affect = 'EDGES'; md.harden_normals = True
            # bevel width is in object space before scale: apply scale so widths are metres
            me.transform(Matrix.Diagonal((*size, 1))); o.scale = (1, 1, 1)
        _smooth(o); o.data.materials.append(m)
        return o
    def cyl(s, name, r, depth, loc, m, rot=(0, 0, 0), verts=32):
        bpy.ops.mesh.primitive_cylinder_add(radius=r, depth=depth, location=loc, rotation=[math.radians(a) for a in rot], vertices=verts)
        o = bpy.context.object; o.name = name; _link(s.c, o); o.data.materials.append(m); _smooth(o); return o
    def plane(s, name, size, loc, m, rot=(0, 0, 0)):
        bpy.ops.mesh.primitive_plane_add(size=1, location=loc, rotation=[math.radians(a) for a in rot])
        o = bpy.context.object; o.name = name; o.scale = (size[0], size[1], 1); _link(s.c, o); o.data.materials.append(m); return o
def _area(c, name, loc, e, size, col, tgt, shape='SQUARE', sy=None):
    L = bpy.data.lights.new(name, 'AREA'); L.energy = e; L.size = size; L.color = col
    if sy: L.shape = 'RECTANGLE'; L.size_y = sy
    o = bpy.data.objects.new(name, L); c.objects.link(o); o.location = loc
    o.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat('-Z', 'Y').to_euler(); return o
def _gltf(c, model, loc=(0, 0, 0), rz=0.0, scale=1.0, hide=()):
    objs = R.import_gltf(ap('models', model, f'{model}_1k.gltf'), collection=c)
    T = Matrix.Translation(loc) @ Matrix.Rotation(math.radians(rz), 4, 'Z') @ Matrix.Scale(scale, 4)
    for o in objs:
        if o.parent is None or o.parent not in objs: o.matrix_world = T @ o.matrix_world
    for o in objs:
        if any(h in o.name for h in hide): o.hide_render = True; o.hide_viewport = True
    return objs
def _glass(name, tint=(0.85, 0.92, 0.95)):
    """Thin architectural glass: Fresnel reflection + straight-through transparency (no refraction offset, cheap)."""
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear(); L = nt.links.new
    out = nt.nodes.new('ShaderNodeOutputMaterial'); tr = nt.nodes.new('ShaderNodeBsdfTransparent'); tr.inputs[0].default_value = (*tint, 1)
    gl = nt.nodes.new('ShaderNodeBsdfGlossy'); gl.inputs['Roughness'].default_value = 0.02
    fr = nt.nodes.new('ShaderNodeLayerWeight'); fr.inputs['Blend'].default_value = 0.12
    mx = nt.nodes.new('ShaderNodeMixShader'); L(fr.outputs['Fresnel'], mx.inputs[0]); L(tr.outputs[0], mx.inputs[1]); L(gl.outputs[0], mx.inputs[2])
    lp = nt.nodes.new('ShaderNodeLightPath'); m2 = nt.nodes.new('ShaderNodeMixShader')   # shadows pass straight through
    L(lp.outputs['Is Shadow Ray'], m2.inputs[0]); L(mx.outputs[0], m2.inputs[1]); L(tr.outputs[0], m2.inputs[2]); L(m2.outputs[0], out.inputs[0])
    return m
def _screen(name, kind='map'):
    """Emissive display with a cheap procedural picture (no text, no logos)."""
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear(); L = nt.links.new
    out = nt.nodes.new('ShaderNodeOutputMaterial'); em = nt.nodes.new('ShaderNodeEmission'); tc = nt.nodes.new('ShaderNodeTexCoord')
    if kind == 'map':     # navigation: dark blue-grey blocks with a bright route line
        vo = nt.nodes.new('ShaderNodeTexVoronoi'); vo.inputs['Scale'].default_value = 9; vo.feature = 'DISTANCE_TO_EDGE'
        L(tc.outputs['Generated'], vo.inputs['Vector'])
        cr = nt.nodes.new('ShaderNodeValToRGB'); cr.color_ramp.elements[0].position = 0.0; cr.color_ramp.elements[0].color = (0.45, 0.5, 0.55, 1)
        cr.color_ramp.elements[1].position = 0.06; cr.color_ramp.elements[1].color = (0.05, 0.08, 0.13, 1); L(vo.outputs['Distance'], cr.inputs[0])
        sep = nt.nodes.new('ShaderNodeSeparateXYZ'); L(tc.outputs['Generated'], sep.inputs[0])
        d = nt.nodes.new('ShaderNodeMath'); d.operation = 'SUBTRACT'; L(sep.outputs['X'], d.inputs[0]); d.inputs[1].default_value = 0.5
        a = nt.nodes.new('ShaderNodeMath'); a.operation = 'ABSOLUTE'; L(d.outputs[0], a.inputs[0])
        rt = nt.nodes.new('ShaderNodeMath'); rt.operation = 'LESS_THAN'; rt.inputs[1].default_value = 0.03; L(a.outputs[0], rt.inputs[0])
        mx = nt.nodes.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.inputs['B'].default_value = (0.1, 0.55, 1.0, 1)
        L(rt.outputs[0], mx.inputs['Factor']); L(cr.outputs['Color'], mx.inputs['A']); L(mx.outputs['Result'], em.inputs['Color']); em.inputs['Strength'].default_value = 1.6
    else:                 # patient monitor: black with green / cyan / yellow waveform bands
        sep = nt.nodes.new('ShaderNodeSeparateXYZ'); L(tc.outputs['Generated'], sep.inputs[0])
        cols = [(0.1, 1.0, 0.25), (0.1, 0.85, 1.0), (1.0, 0.85, 0.1)]; prev = None
        for i, colr in enumerate(cols):
            w = nt.nodes.new('ShaderNodeMath'); w.operation = 'MULTIPLY'; w.inputs[1].default_value = 30 + 9 * i; L(sep.outputs['X'], w.inputs[0])
            sn = nt.nodes.new('ShaderNodeMath'); sn.operation = 'SINE'; L(w.outputs[0], sn.inputs[0])
            pw = nt.nodes.new('ShaderNodeMath'); pw.operation = 'POWER'; pw.inputs[1].default_value = 9.0; L(sn.outputs[0], pw.inputs[0])
            yy = nt.nodes.new('ShaderNodeMath'); yy.operation = 'MULTIPLY_ADD'; yy.inputs[1].default_value = 0.14; yy.inputs[2].default_value = 0.72 - 0.27 * i; L(pw.outputs[0], yy.inputs[0])
            df = nt.nodes.new('ShaderNodeMath'); df.operation = 'SUBTRACT'; L(sep.outputs['Y'], df.inputs[0]); L(yy.outputs[0], df.inputs[1])
            ab = nt.nodes.new('ShaderNodeMath'); ab.operation = 'ABSOLUTE'; L(df.outputs[0], ab.inputs[0])
            ln = nt.nodes.new('ShaderNodeMath'); ln.operation = 'LESS_THAN'; ln.inputs[1].default_value = 0.012; L(ab.outputs[0], ln.inputs[0])
            mx = nt.nodes.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.inputs['B'].default_value = (*colr, 1); L(ln.outputs[0], mx.inputs['Factor'])
            if prev is None: mx.inputs['A'].default_value = (0.004, 0.01, 0.012, 1)
            else: L(prev, mx.inputs['A'])
            prev = mx.outputs['Result']
        L(prev, em.inputs['Color']); em.inputs['Strength'].default_value = 2.2
    L(em.outputs[0], out.inputs[0]); return m

# ------------------------------------------------------------------ worlds
WORLDS = {  # kind -> (lighting HDR, strength, z-rotation deg, camera-ray background image or colour, camera strength)
    'car':      ('park_parking_1k.hdr', 1.5, 0.0, (0.16, 0.55, 0.92), 1.0),   # round 3: sky-blue behind the car windows (was the parking photo)
    'hospital': ('hospital_room_2_1k.hdr', 0.45, 0.0, None, 0.45),
    'studio':   ('studio_small_08_1k.hdr', 0.6, 0.0, (0.01, 0.035, 0.12), 1.0),
}
def _world(kind):
    nm = f'kw_{kind}'
    if nm in bpy.data.worlds: return bpy.data.worlds[nm]
    hdr, st, rot, cam, cst = WORLDS[kind]
    w = bpy.data.worlds.new(nm); w.use_nodes = True; nt = w.node_tree; nt.nodes.clear(); L = nt.links.new
    tc = nt.nodes.new('ShaderNodeTexCoord'); mp = nt.nodes.new('ShaderNodeMapping'); mp.inputs['Rotation'].default_value[2] = math.radians(rot)
    L(tc.outputs['Generated'], mp.inputs['Vector'])
    env = nt.nodes.new('ShaderNodeTexEnvironment'); env.image = bpy.data.images.load(ap('hdri', hdr), check_existing=True); L(mp.outputs[0], env.inputs['Vector'])
    bg = nt.nodes.new('ShaderNodeBackground'); bg.name = 'light'; bg.inputs['Strength'].default_value = st; L(env.outputs['Color'], bg.inputs['Color'])
    bg2 = nt.nodes.new('ShaderNodeBackground'); bg2.name = 'camera'; bg2.inputs['Strength'].default_value = cst
    if isinstance(cam, str):
        e2 = nt.nodes.new('ShaderNodeTexEnvironment'); e2.image = bpy.data.images.load(ap('hdri', cam), check_existing=True); L(mp.outputs[0], e2.inputs['Vector'])
        L(e2.outputs['Color'], bg2.inputs['Color'])
    elif cam is None: L(env.outputs['Color'], bg2.inputs['Color'])
    else: bg2.inputs['Color'].default_value = (*cam, 1)
    if kind == 'car' and Q.enabled('CABIN'):
        # A pale horizon and a richer zenith, both cyan. HDR illumination stays independent.
        sep = nt.nodes.new('ShaderNodeSeparateXYZ'); L(tc.outputs['Generated'], sep.inputs[0])
        ramp = nt.nodes.new('ShaderNodeValToRGB')
        ramp.color_ramp.elements[0].position = 0.0
        ramp.color_ramp.elements[0].color = (0.35, 0.74, 0.96, 1)
        ramp.color_ramp.elements[1].position = 0.53
        ramp.color_ramp.elements[1].color = (0.07, 0.41, 0.85, 1)
        L(sep.outputs['Z'], ramp.inputs[0]); L(ramp.outputs[0], bg2.inputs['Color'])
    lp = nt.nodes.new('ShaderNodeLightPath'); mx = nt.nodes.new('ShaderNodeMixShader'); out = nt.nodes.new('ShaderNodeOutputWorld')
    L(lp.outputs['Is Camera Ray'], mx.inputs[0]); L(bg.outputs[0], mx.inputs[1]); L(bg2.outputs[0], mx.inputs[2]); L(mx.outputs[0], out.inputs['Surface'])
    return w
def set_world(S, kind):
    w = _world(kind)
    if S.world is not w: S.world = w
    return w

def finish(S, samples=32):
    R.render_look(S, samples=samples, look='AgX - Punchy')
    R.compositor_finish(S, glare=True, vignette=0.18, glare_threshold=1.0, glare_mix=-0.85)

# ------------------------------------------------------------------ skin
def _skin_nodes(p):
    for o in p.parts:
        if o is p.body and o.active_material and o.active_material.node_tree:
            return o.active_material, o.active_material.node_tree
    return None, None
TAN = (0.62, 0.34, 0.2); RED = (0.75, 0.07, 0.05)
def _skin_group(p):
    m, nt = _skin_nodes(p)
    if not nt: return None
    return next((n for n in nt.nodes if n.type == 'GROUP' and 'colorMixIn' in n.inputs), None)
def skin(p, tan=TAN, amount=0.3, pores=0.3, rough=0.44):
    """Warm/tanned, healthy skin with visible pores + Random-Walk-Skin SSS. Uses the MPFB ENHANCED_SSS group inputs
    (colorMixIn / colorMixInStrength / Pore strength / SSS ...); falls back to the Principled BSDF otherwise."""
    m, nt = _skin_nodes(p)
    if not nt: return
    g = _skin_group(p)
    if g:
        g.inputs['colorMixIn'].default_value = (*tan, 1); g.inputs['colorMixInStrength'].default_value = amount
        for k, v in {'Roughness': rough, 'Pore strength': pores, 'SSS strength': 0.3, 'SSS radius scale': 0.1, 'Contrast': 0.08,
                     'Clearcoat': 0.1, 'Clearcoat Roughness': 0.4}.items():
            if k in g.inputs: g.inputs[k].default_value = v
        g['kw_tan'] = list(tan); g['kw_amt'] = amount
        trees = [g.node_tree] if g.node_tree else []
    else:
        trees = [nt]
    for t in trees:
        for n in t.nodes:
            if n.type == 'BSDF_PRINCIPLED': n.subsurface_method = 'RANDOM_WALK_SKIN'
def flush(p, v):
    """v 0..1: skin goes red (holding the sneeze). Changes two group input values only."""
    try:   # KW_HEADS=scan skin reads its own per-person flush value (heads_kw)
        import heads_kw as _HK
        if _HK.on(): _HK.flush(p, v)
    except Exception as e: print('scan flush skipped', repr(e))
    g = _skin_group(p)
    if not g: return
    v = max(0.0, min(1.0, v)); tan = g.get('kw_tan', TAN); amt = g.get('kw_amt', 0.3)
    g.inputs['colorMixIn'].default_value = (*[tan[i] + (RED[i] - tan[i]) * v for i in range(3)], 1)
    g.inputs['colorMixInStrength'].default_value = amt + (0.7 - amt) * v

# ------------------------------------------------------------------ car
class Car: pass
SPEED = 13.0      # m/s (about 47 km/h)
PERIOD = 24.0     # everything outside repeats every 24 m, so the loop is seamless
def build_car(S, ned, paint=(0.02, 0.1, 0.5)):
    c = _coll(S, 'kw_car'); B = _B(c); car = Car(); car.coll = c
    bpy.context.view_layer.update()
    P = ned.bone_world('spine05').z; H = ned.bone_world('head').z; Cz = ned.bone_world('spine03').z
    BL = H - 0.45                     # beltline (top of doors / dash)
    RF = H + 0.26                     # headliner height
    XL, XR = -0.50, 1.22              # inner door planes (driver at x=0, passenger at x=0.75)
    XC = (XL + XR) / 2; W = XR - XL
    YF, YB = -0.98, 1.62              # windscreen base, rear window base
    # materials
    seat_m = tex('kw_seat', 'Fabric030', 6.0, tint=(0.16, 0.16, 0.17), nor=0.8)
    bol_m = tex('kw_seat_bolster', 'Fabric030', 9.0, tint=(0.07, 0.07, 0.075), nor=1.0)
    dash_m = tex('kw_dash', 'Plastic012A', 5.0, tint=(0.11, 0.11, 0.115), nor=0.6)
    trim_m = tex('kw_trim', 'Plastic012A', 5.0, tint=(0.42, 0.40, 0.38), nor=0.5)
    head_m = tex('kw_headliner', 'Fabric036', 5.0, tint=(0.62, 0.6, 0.56), nor=0.4)
    carpet = tex('kw_carpet', 'Fabric030', 10.0, tint=(0.05, 0.05, 0.05), nor=1.0)
    paint_m = mat('kw_paint', paint, 0.3, 0.35, coat=0.8)
    black = mat('kw_black', (0.012, 0.012, 0.014), 0.45); chrome = mat('kw_chrome', (0.9, 0.9, 0.92), 0.08, 1.0)
    glass = _glass('kw_glass'); mirror = mat('kw_mirror', (0.95, 0.95, 0.95), 0.0, 1.0)
    leather = mat('kw_wheel_leather', (0.02, 0.02, 0.022), 0.5)
    look = Q.enabled('CABIN')
    if look:
        seat_m = tex('kw_seat_tailored', 'Fabric030', 11, tint=(0.43, 0.23, 0.13), nor=1.2)
        bol_m = Q.texture(mat('kw_cabin_leather', (0.12, 0.047, 0.025), 0.42, coat=0.13),
                          (0.09, 0.031, 0.014), (0.28, 0.115, 0.049), 125, rough=(0.39, 0.56), bump=(0.26, 0.0015))
        trim_m = tex('kw_cabin_trim', 'Plastic012A', 9, tint=(0.16, 0.21, 0.27), nor=0.85)
        dash_m = tex('kw_cabin_dash', 'Plastic012A', 8, tint=(0.06, 0.08, 0.105), nor=0.9)
        head_m = tex('kw_cabin_liner', 'Fabric036', 10, tint=(0.33, 0.36, 0.40), nor=0.65)
        leather = Q.texture(leather, (0.010, 0.014, 0.022), (0.043, 0.052, 0.066), 138, rough=(0.38, 0.58), bump=(0.28, 0.0011))
        thread = mat('kw_contrast_thread', (0.26, 0.125, 0.07), 0.83)
        piping = mat('kw_seat_piping', (0.045, 0.016, 0.010), 0.45)
        satin = mat('kw_satin_alloy', (0.28, 0.38, 0.45), 0.30, 0.70)
        ember = mat('kw_cabin_amber', (0.53, 0.15, 0.018), 0.52, emit=(0.65, 0.18, 0.02), es=0.42)
    # ---------- seats
    for sx, nm in ((0.0, 'drv'), (0.75, 'pas')):
        B.box(f'seat_{nm}_base', (0.5, 0.54, 0.13), (sx, 0.04, P - 0.13), seat_m, 0.04, (4, 0, 0), 3)
        for bx in (-1, 1):
            B.box(f'seat_{nm}_bolster{bx}', (0.08, 0.52, 0.12), (sx + bx * 0.24, 0.04, P - 0.07), bol_m, 0.035, (4, 0, 0), 3)
            B.box(f'seat_{nm}_side{bx}', (0.09, 0.15, 0.62), (sx + bx * 0.235, 0.31, P + 0.31), bol_m, 0.035, (-12, 0, 0), 3)
        B.box(f'seat_{nm}_back', (0.42, 0.13, 0.66), (sx, 0.34, P + 0.31), seat_m, 0.04, (-12, 0, 0), 3)
        B.box(f'seat_{nm}_head', (0.27, 0.1, 0.19), (sx, 0.45, H + 0.0), bol_m, 0.045, (-8, 0, 0), 3)
        for px in (-0.07, 0.07): B.cyl(f'seat_{nm}_post', 0.007, 0.12, (sx + px, 0.44, H - 0.14), chrome, (-10, 0, 0), 12)
        B.box(f'seat_{nm}_rail', (0.4, 0.6, 0.06), (sx, 0.05, P - 0.24), black, 0.01)
        if look: Q.cabin_seat(B, sx, nm, P, H, piping, thread)
    # back bench
    B.box('rear_base', (W - 0.12, 0.5, 0.14), (XC, 1.05, P - 0.11), seat_m, 0.04, (4, 0, 0), 3)
    B.box('rear_back', (W - 0.12, 0.14, 0.6), (XC, 1.36, P + 0.25), seat_m, 0.04, (-16, 0, 0), 3)
    for hx in (0.0, 0.75): B.box('rear_head', (0.25, 0.09, 0.15), (hx, 1.43, H - 0.06), bol_m, 0.04, (-14, 0, 0), 3)
    B.box('parcel_shelf', (W, 0.3, 0.03), (XC, 1.55, H - 0.25), dash_m, 0.008)
    # ---------- floor, roof, pillars, doors
    B.box('floor', (W + 0.1, 3.2, 0.05), (XC, 0.2, -0.04), carpet, 0.0)
    B.box('console', (0.24, 0.9, 0.3), (0.375, -0.35, P - 0.15), dash_m, 0.03, (0, 0, 0), 3)
    B.box('console_lid', (0.22, 0.32, 0.05), (0.375, 0.0, P + 0.02), bol_m, 0.02, (0, 0, 0), 3)
    B.cyl('gear_knob', 0.025, 0.12, (0.375, -0.45, P + 0.06), leather, (0, 0, 0), 16)
    B.box('headliner', (W + 0.12, 2.1, 0.04), (XC, 0.58, RF), head_m, 0.015)
    B.box('roof_skin', (W + 0.28, 2.12, 0.05), (XC, 0.58, RF + 0.06), paint_m, 0.03, (0, 0, 0), 3)
    for side, x in (('L', XL - 0.04), ('R', XR + 0.04)):
        # A pillar (windscreen to roof), B pillar, C pillar
        a0 = Vector((x, YF, BL + 0.02)); a1 = Vector((x, -0.47, RF)); mid = (a0 + a1) / 2; ln = (a1 - a0).length; ang = math.degrees(math.atan2(a1.y - a0.y, a1.z - a0.z))
        B.box(f'apillar_{side}', (0.09, 0.08, ln), tuple(mid), paint_m, 0.02, (-ang, 0, 0), 3)
        B.box(f'apillar_trim_{side}', (0.07, 0.07, ln), tuple(mid + Vector((0.025 if side == 'L' else -0.025, 0.02, -0.01))), trim_m, 0.02, (-ang, 0, 0), 3)
        B.box(f'bpillar_{side}', (0.09, 0.11, RF - BL), (x, 0.56, (RF + BL) / 2), trim_m, 0.02, (0, 0, 0), 3)
        c0 = Vector((x, 1.38, RF)); c1 = Vector((x, YB + 0.05, BL)); mid = (c0 + c1) / 2; ln = (c1 - c0).length; ang = math.degrees(math.atan2(c1.y - c0.y, c0.z - c1.z))
        B.box(f'cpillar_{side}', (0.09, 0.22, ln), tuple(mid), trim_m, 0.02, (ang, 0, 0), 3)
        # doors: trim panel inside, painted skin outside, armrest, handle, window channel
        sgn = 1 if side == 'L' else -1
        B.box(f'door_{side}', (0.07, 2.55, BL - 0.1), (x, 0.3, (BL + 0.1) / 2), trim_m, 0.015)
        B.box(f'door_skin_{side}', (0.03, 2.62, BL - 0.0), (x - sgn * 0.05, 0.3, BL / 2), paint_m, 0.012)
        B.box(f'door_cap_{side}', (0.1, 2.55, 0.035), (x, 0.3, BL), dash_m, 0.012)
        B.box(f'armrest_{side}', (0.09, 0.42, 0.05), (x + sgn * 0.06, -0.05, P + 0.15), bol_m, 0.02, (0, 0, 0), 3)
        B.box(f'pocket_{side}', (0.05, 0.6, 0.1), (x + sgn * 0.04, -0.35, 0.18), dash_m, 0.015)
        B.box(f'handle_{side}', (0.02, 0.1, 0.02), (x + sgn * 0.045, -0.32, P + 0.3), chrome, 0.006)
        B.box(f'seal_{side}', (0.02, 2.55, 0.015), (x + sgn * 0.035, 0.3, BL + 0.025), black, 0.004)
        if look: Q.cabin_door(B, side, x, sgn, P, BL, dash_m, bol_m, satin, ember, thread)
        # door mirror outside, ahead of the A pillar base
        B.box(f'mirror_arm_{side}', (0.12, 0.05, 0.04), (x - sgn * 0.08, YF + 0.12, BL + 0.05), black, 0.01)
        mh = B.box(f'mirror_house_{side}', (0.08, 0.13, 0.11), (x - sgn * 0.17, YF + 0.14, BL + 0.08), paint_m, 0.03, (0, 0, -sgn * 8), 3)
        B.box(f'mirror_glass_{side}', (0.005, 0.12, 0.09), (x - sgn * 0.17, YF + 0.205, BL + 0.08), mirror, 0.0, (0, 0, 90 - sgn * 8))
    # ---------- windscreen, rear window
    g0 = Vector((XC, YF, BL + 0.02)); g1 = Vector((XC, -0.47, RF)); mid = (g0 + g1) / 2; ln = (g1 - g0).length; ang = math.degrees(math.atan2(g1.y - g0.y, g1.z - g0.z))
    ws = B.plane('windscreen', (W + 0.1, ln), tuple(mid), glass, (-ang, 0, 0))
    ws_frame = B.box('windscreen_frame_top', (W + 0.2, 0.06, 0.04), (XC, -0.48, RF - 0.01), black, 0.01)
    r0 = Vector((XC, YB, BL + 0.02)); r1 = Vector((XC, 1.38, RF)); mid = (r0 + r1) / 2; ln = (r1 - r0).length; ang = math.degrees(math.atan2(r1.y - r0.y, r0.z - r1.z))
    B.plane('rear_window', (W + 0.05, ln), tuple(mid), glass, (ang, 0, 0))
    # ---------- dashboard
    B.box('dash_top', (W + 0.1, 0.55, 0.1), (XC, YF + 0.22, BL - 0.0), dash_m, 0.04, (-6, 0, 0), 3)
    B.box('dash_face', (W, 0.12, 0.34), (XC, YF + 0.47, BL - 0.2), dash_m, 0.04, (12, 0, 0), 3)
    B.box('dash_trim', (W - 0.05, 0.03, 0.035), (XC, YF + 0.535, BL - 0.1), trim_m, 0.008, (12, 0, 0))
    if look:
        B.box('kw_dash_inlay', (W - 0.10, 0.018, 0.010), (XC, YF + 0.556, BL - 0.106), satin, 0.004, (12, 0, 0))
        B.box('kw_dash_ambient', (W - 0.11, 0.012, 0.004), (XC, YF + 0.565, BL - 0.118), ember, 0.002, (12, 0, 0))
    B.box('glovebox', (0.48, 0.03, 0.17), (0.78, YF + 0.53, BL - 0.27), dash_m, 0.01, (12, 0, 0))
    B.box('binnacle', (0.42, 0.24, 0.1), (0.0, YF + 0.33, BL + 0.07), dash_m, 0.04, (8, 0, 0), 3)
    clu = B.box('cluster', (0.36, 0.01, 0.12), (0.0, YF + 0.44, BL + 0.04), _screen('kw_cluster', 'map'), 0.0, (100, 0, 0))
    for dx in (-0.09, 0.09):
        rg = bpy.data.objects.new('dial', None)
        bpy.ops.mesh.primitive_torus_add(major_radius=0.045, minor_radius=0.004, location=(dx, YF + 0.436, BL + 0.045), rotation=(math.radians(100), 0, 0))
        d = bpy.context.object; d.name = 'dial_ring'; _link(c, d); d.data.materials.append(mat('kw_dial', (1, 1, 1), 0.3, emit=(1.0, 0.45, 0.1), es=4.0))
    scr = B.box('centre_screen', (0.26, 0.012, 0.16), (XC, YF + 0.48, BL + 0.07), black, 0.006, (-12, 0, 0))
    B.box('centre_screen_img', (0.245, 0.002, 0.145), (XC, YF + 0.487 + 0.0, BL + 0.07 - 0.0015), _screen('kw_nav', 'map'), 0.0, (-12, 0, 0))
    for vx in (XC - 0.13, XC + 0.13, -0.3, 1.05):   # air vents: frame + slats
        B.box('vent', (0.13, 0.03, 0.06), (vx, YF + 0.53, BL - 0.07), black, 0.01, (12, 0, 0))
        for k in range(3): B.box('vent_slat', (0.12, 0.012, 0.005), (vx, YF + 0.545, BL - 0.087 + 0.017 * k), chrome if k == 1 else dash_m, 0.0, (12, 0, 0))
    # steering wheel (local Z = steering axis). Steer: car.steer(rad) or car.wheel.rotation_euler[2] = rad
    wc = Vector((0, -0.52, Cz + 0.12))
    wheel = bpy.data.objects.new('wheel', None); c.objects.link(wheel); wheel.location = wc; wheel.rotation_mode = 'ZYX'; wheel.rotation_euler = (math.radians(65), 0, 0)
    wheel.empty_display_size = 0.2
    bpy.ops.mesh.primitive_torus_add(major_radius=0.19, minor_radius=0.017, major_segments=64, minor_segments=16); rim = bpy.context.object; rim.name = 'wheel_rim'
    _link(c, rim); rim.data.materials.append(leather); _smooth(rim); rim.parent = wheel
    hub = B.cyl('wheel_hub', 0.065, 0.06, (0, 0, -0.01), black, (0, 0, 0), 32); hub.parent = wheel
    logo_free = B.cyl('wheel_badge', 0.03, 0.065, (0, 0, -0.005), chrome, (0, 0, 0), 24); logo_free.parent = wheel
    for k, a in enumerate((90, 210, 330)):
        sp = B.box('wheel_spoke', (0.13, 0.035, 0.015), (math.cos(math.radians(a)) * 0.11, math.sin(math.radians(a)) * 0.11, -0.012), black, 0.006, (0, 0, a))
        sp.parent = wheel
    B.cyl('column', 0.04, 0.32, tuple(wc + Vector((0, -0.17, -0.08))), black, (65, 0, 0))
    B.box('column_shroud', (0.11, 0.2, 0.09), tuple(wc + Vector((0, -0.2, -0.11))), dash_m, 0.03, (-25, 0, 0), 3)
    car.wheel = wheel
    def steer(a): wheel.rotation_euler = (math.radians(65), 0, a)
    car.steer = steer
    # rear-view mirror
    B.box('rvm_stem', (0.02, 0.02, 0.07), (XC, -0.5, RF - 0.04), black, 0.005)
    B.box('rvm_house', (0.24, 0.045, 0.07), (XC, -0.52, RF - 0.1), black, 0.018, (0, 0, -8), 3)
    B.box('rvm_glass', (0.22, 0.003, 0.055), (XC, -0.497, RF - 0.1), mirror, 0.0, (0, 0, -8))
    # sun visors
    for vx in (0.0, 0.75): B.box('visor', (0.36, 0.17, 0.025), (vx, -0.38, RF - 0.03), head_m, 0.01, (8, 0, 0), 3)
    if look:
        B.box('kw_overhead_console', (0.22, 0.20, 0.032), (XC, -0.23, RF - 0.029), dash_m, 0.011)
        lamp = mat('kw_cabin_dome_diffuser', (0.45, 0.52, 0.52), 0.35)
        for inc in (-0.073, 0.073):
            B.box('kw_overhead_diffuser', (0.042, 0.059, 0.004), (XC + inc, -0.24, RF - 0.047), lamp, 0.006)
    # ---------- exterior: hood, fenders, wipers, cowl
    hood_z0 = BL - 0.05
    B.box('cowl', (W + 0.2, 0.14, 0.04), (XC, YF - 0.05, hood_z0), black, 0.012)
    B.box('hood', (W + 0.22, 1.35, 0.07), (XC, YF - 0.8, hood_z0 - 0.08), paint_m, 0.05, (-5, 0, 0), 4)
    for sx in (XL - 0.08, XR + 0.08): B.box('fender', (0.18, 1.35, 0.3), (sx, YF - 0.8, hood_z0 - 0.25), paint_m, 0.06, (-5, 0, 0), 4)
    B.box('bumper', (W + 0.3, 0.2, 0.32), (XC, YF - 1.5, hood_z0 - 0.38), paint_m, 0.08, (0, 0, 0), 4)
    for wx in (XC - 0.38, XC + 0.35):
        wp = B.box('wiper', (0.62, 0.015, 0.012), (wx, YF + 0.02, BL + 0.03), black, 0.004, (-30, 0, 9))
        B.cyl('wiper_pivot', 0.012, 0.03, (wx - 0.3, YF - 0.02, BL + 0.01), black, (0, 0, 0), 12)
    B.box('trunk', (W + 0.2, 0.6, 0.08), (XC, YB + 0.35, BL - 0.06), paint_m, 0.04, (3, 0, 0), 3)
    for ox in (XL - 0.08, XR + 0.08): B.box('rear_quarter', (0.16, 1.0, 0.5), (ox, YB + 0.05, BL - 0.3), paint_m, 0.05, (0, 0, 0), 3)
    # ---------- seat belt (driver): strap laid on the torso by ray casting onto the body/tee, parented to spine02
    car.belt = None
    try: car.belt = _belt(S, ned, c, mat('kw_belt', (0.03, 0.03, 0.035), 0.6), BL, XL)
    except Exception as e: print('belt skipped:', e)
    # ---------- outside moving world
    road_z = -0.34
    mover = bpy.data.objects.new('kw_road_mover', None); c.objects.link(mover)
    Bm = _B(c)
    span = (-150.0, 60.0); Lr = span[1] - span[0]; yc = (span[0] + span[1]) / 2
    road = Bm.plane('road', (8.0, Lr), (-1.2, yc, road_z), tex('kw_asphalt', 'asphalt_02', 1 / 2.4, tint=(0.75, 0.75, 0.75), nor=0.8))
    lane_m = mat('kw_lane', (0.85, 0.85, 0.8), 0.6)
    for lx in (2.15, -4.6):  # solid edge lines
        Bm.plane('edge_line', (0.12, Lr), (lx, yc, road_z + 0.004), lane_m)
    dash = Bm.plane('centre_dash', (0.12, 4.0), (-1.2, span[0] + 2.0, road_z + 0.004), lane_m)
    ar = dash.modifiers.new('arr', 'ARRAY'); ar.use_relative_offset = False; ar.use_constant_offset = True; ar.constant_offset_displace = (0, 12.0 / 4.0, 0); ar.count = int(Lr / 12)
    # array offset is in local units and the plane is scaled by 4 in Y -> 3.0 local = 12 m
    grass_m = tex('kw_grass', 'leafy_grass', 1 / 2.0, tint=(0.8, 0.9, 0.7), nor=1.0)
    Bm.plane('verge_L', (40.0, Lr), (2.8 + 20.0, yc, road_z - 0.03), grass_m)
    Bm.plane('verge_R', (40.0, Lr), (-5.2 - 20.0, yc, road_z - 0.03), grass_m)
    Bm.box('kerb_L', (0.15, Lr, 0.12), (2.45, yc, road_z + 0.03), tex('kw_kerb', 'white_plaster_02', 1.0, tint=(0.6, 0.6, 0.58)), 0.02)
    # roadside props: one 24 m bay built from models, then linked copies along the road
    bay = []; roots = []
    def keep(objs):
        bay.extend([o for o in objs if o.type == 'MESH' and not o.hide_render]); roots.extend([o for o in objs if o.parent is None]); return objs
    keep(_gltf(c, 'shrub_04', (5.0, 0.0, road_z), 20, 1.1))
    keep(_gltf(c, 'shrub_04', (7.5, 9.0, road_z), 140, 1.5))
    keep(_gltf(c, 'shrub_04', (-7.0, 15.0, road_z), 70, 1.4))
    keep(_gltf(c, 'fire_hydrant', (3.1, 6.0, road_z), 90, 1.0, hide=('aged',)))
    keep(_gltf(c, 'metal_trash_can', (3.3, 17.0, road_z), 0, 1.0, hide=('rust',)))
    for k in range(4): keep(_gltf(c, 'concrete_road_barrier', (-5.7, 3.0 + k * 6.0, road_z), 90, 1.0))
    for gx, gy in ((3.4, 2.0), (4.2, 12.0), (3.6, 20.0), (-6.2, 6.0), (-6.4, 19.0), (6.0, 14.0)):
        keep(_gltf(c, 'grass_medium_02', (gx, gy, road_z - 0.02), gx * 37 % 360, 1.6))
    pole_m = mat('kw_pole', (0.35, 0.36, 0.37), 0.4, 0.8)
    for py, px in ((10.0, 3.0), (22.0, -6.4)):   # simple street light poles
        sgn = -1 if px > 0 else 1
        p1 = Bm.cyl('pole', 0.07, 7.5, (px, py, road_z + 3.75), pole_m, (0, 0, 0), 16); p2 = Bm.cyl('pole_arm', 0.045, 1.8, (px + sgn * 0.85, py, road_z + 7.45), pole_m, (0, 90, 0), 12)
        p3 = Bm.box('pole_head', (0.6, 0.22, 0.1), (px + sgn * 1.7, py, road_z + 7.42), pole_m, 0.03)
        bay += [p1, p2, p3]; roots += [p1, p2, p3]
    bpy.context.view_layer.update()
    wm = {o: o.matrix_world.copy() for o in bay}
    for o in [road, dash] + [o for o in c.objects if o.name.split('.')[0] in ('edge_line', 'verge_L', 'verge_R', 'kerb_L')] + roots:
        if o.parent is None: o.parent = mover        # mover is at identity here, so no inverse needed
    copies = []
    for k in range(int(span[0] // PERIOD), int(span[1] // PERIOD) + 1):
        if k == 0: continue
        for o in bay:
            d = o.copy(); c.objects.link(d); d.parent = mover; d.matrix_parent_inverse = Matrix.Identity(4)
            d.matrix_basis = Matrix.Translation((0, k * PERIOD, 0)) @ wm[o]; copies.append(d)
    car.mover = mover; car.road_z = road_z
    def update(t):
        mover.location.y = (SPEED * t) % PERIOD
    car.update = update
    # ---------- lights carried by the set: soft window light from the front + cool sky rim from the driver window
    car.lights = [_area(c, 'car_key', (0.55, -1.5, H + 0.45), 230, 1.6, (1.0, 0.93, 0.85), (0, 0, H - 0.05)),
                  _area(c, 'car_rim', (-1.1, 0.35, H + 0.25), 70, 0.9, (0.65, 0.8, 1.0), (0, 0, H - 0.05)),
                  _area(c, 'car_fill', (1.0, -0.2, H - 0.1), 40, 1.0, (1.0, 0.9, 0.8), (0, 0, H - 0.1))]
    if look:
        key, rim, fill = car.lights
        key.data.size = 1.25; key.data.energy = 252; key.data.color = (1.0, 0.93, 0.84)
        rim.data.energy = 103; rim.data.color = (0.65, 0.83, 1.0)
        fill.data.energy = 23; fill.data.color = (0.91, 0.98, 1.0)
    if Q.enabled('PEOPLE2'):
        key, rim, fill = car.lights
        key.location = (.97, -1.47, H + .55)
        key.rotation_euler = (Vector((0, 0, H - .05)) - key.location).to_track_quat('-Z', 'Y').to_euler()
        key.data.size, key.data.energy, key.data.color = 1.30, 272, (1., .96, .90)
        rim.data.energy, fill.data.energy = 66, 16
    car.H, car.BL, car.RF = H, BL, RF
    return car

def _belt(S, ned, c, m, BL, XL):
    """Belt from the B-pillar over the driver's right shoulder (door side, -X) down to the left hip. Each point is projected
    onto the front of the tee/body with ray casts so it lies on the clothes, then pushed out 6 mm."""
    dg = bpy.context.evaluated_depsgraph_get()
    targets = [o for o in ned.parts if o.type == 'MESH' and ('casualsuit' in o.name or o is ned.body)]
    sh = ned.bone_world('clavicle.R', tail=True) if 'clavicle.R' in ned.rig.pose.bones else ned.bone_world('shoulder01.R')
    hip = ned.bone_world('spine05') + Vector((0.17, 0, 0.04))
    def cast(p):   # nearest front surface of tee/body along +Y, ignoring the car and the arms' far side
        best = None
        for o in targets:
            ev = o.evaluated_get(dg); mi = ev.matrix_world.inverted()
            org = mi @ Vector((p.x, -0.9, p.z)); d = (mi.to_3x3() @ Vector((0, 1, 0))).normalized()
            ok, loc, nor, idx = ev.ray_cast(org, d)
            if ok:
                w = ev.matrix_world @ loc
                if abs(w.y - p.y) < 0.35 and (best is None or w.y < best.y): best = w
        return best
    pts = []
    for i in range(13):
        u = i / 12.0; p = sh.lerp(hip, u) + Vector((0, 0, 0.02 * math.sin(math.pi * u)))
        hit = cast(p)
        if hit is not None: pts.append(hit + Vector((0, -0.008, 0)))
    if len(pts) < 6: raise RuntimeError('belt: body not found by rays')
    top = pts[0] + Vector((0, 0.0, 0.06)); anchor = Vector((XL + 0.04, 0.55, BL + 0.42))
    pts = [anchor, anchor.lerp(top, 0.5) + Vector((0, 0.0, 0.02)), top] + pts[1:]
    cu = bpy.data.curves.new('belt', 'CURVE'); cu.dimensions = '3D'; cu.extrude = 0.024; cu.twist_mode = 'MINIMUM'
    sp = cu.splines.new('POLY'); sp.points.add(len(pts) - 1)
    for p_, v in zip(sp.points, pts): p_.co = (*v, 1)
    sp.use_smooth = True
    o = bpy.data.objects.new('belt', cu); c.objects.link(o); o.data.materials.append(m)
    # parent to spine02 so it follows the torso lean
    mw = o.matrix_world.copy(); o.parent = ned.rig; o.parent_type = 'BONE'; o.parent_bone = 'spine02'
    bpy.context.view_layer.update(); o.matrix_world = mw
    buckle = _B(c).box('belt_buckle', (0.04, 0.05, 0.07), tuple(ned.bone_world('spine05') + Vector((0.27, 0.08, 0.0))), mat('kw_buckle', (0.02, 0.02, 0.02), 0.4), 0.01)
    return o

# ------------------------------------------------------------------ hospital
class Hos: pass
def build_hospital(S, ned, wall_col=(0.12, 0.60, 0.86)):   # Zack look: bright sky-blue walls (was dark teal 0.013, 0.147, 0.262)
    c = _coll(S, 'kw_hospital'); B = _B(c); h = Hos(); h.coll = c
    bpy.context.view_layer.update()
    P = ned.bone_world('spine05').z; H = ned.bone_world('head').z
    YW, XW, ZC = 1.55, -1.85, 2.75          # back wall, left wall, ceiling
    wall_m = mat('kw_h_wall', wall_col, 0.9)   # Zack look round 2: flat sky-blue, no plaster texture
    low_m = mat('kw_h_wall_low', (0.06, 0.40, 0.66), 0.9)
    floor_m = tex('kw_h_floor', 'Tiles043', 1 / 1.2, tint=(0.82, 0.85, 0.86), nor=0.7)
    sheet_m = tex('kw_h_sheet', 'Fabric036', 3.0, tint=(0.92, 0.93, 0.94), nor=0.8)
    mattress_m = mat('kw_h_mattress', (0.03, 0.12, 0.18), 0.45, coat=0.3)
    steel = mat('kw_h_steel', (0.75, 0.76, 0.78), 0.25, 1.0); white = mat('kw_h_white', (0.8, 0.8, 0.78), 0.4)
    ceil_m = mat('kw_h_ceiling', (0.30, 0.72, 0.90), 0.9)   # Zack look round 2: no white ceiling band
    curt_m = tex('kw_h_curtain', 'Fabric036', 2.0, tint=(0.62, 0.82, 0.8), nor=1.0)
    # room shell
    B.box('h_floor', (8, 8, 0.05), (0, 0, -0.025), floor_m, 0.0)
    B.box('h_wall_back', (8, 0.1, 1.85), (0, YW + 0.05, 0.9 + 1.85 / 2), wall_m, 0.0)
    B.box('h_wall_back_low', (8, 0.1, 0.9), (0, YW + 0.05, 0.45), low_m, 0.0)
    B.box('h_wall_left', (0.1, 8, 1.85), (XW - 0.05, 0, 0.9 + 1.85 / 2), wall_m, 0.0)
    B.box('h_wall_left_low', (0.1, 8, 0.9), (XW - 0.05, 0, 0.45), low_m, 0.0)
    B.box('h_rail_back', (8, 0.04, 0.07), (0, YW - 0.01, 0.92), white, 0.01)
    B.box('h_rail_left', (0.04, 8, 0.07), (XW + 0.01, 0, 0.92), white, 0.01)
    B.box('h_skirt_back', (8, 0.02, 0.1), (0, YW - 0.005, 0.05), white, 0.004)
    B.box('h_ceiling', (8, 8, 0.05), (0, 0, ZC), ceil_m, 0.0)
    B.box('h_ceiling_panel', (1.2, 0.6, 0.02), (-0.6, 0.4, ZC - 0.03), mat('kw_h_panel', (1, 1, 1), 0.5, emit=(1.0, 0.97, 0.92), es=6.0), 0.0)
    # exam bed (he sits on the long front edge; bed runs along X away from the doctor)
    top = P - 0.075; bx0, bx1, by0, by1 = -1.55, 0.3, -0.12, 0.62
    bxc, byc = (bx0 + bx1) / 2, (by0 + by1) / 2
    B.box('h_bed_mattress', (bx1 - bx0, by1 - by0, 0.1), (bxc, byc, top - 0.05), mattress_m, 0.03, (0, 0, 0), 3)
    B.box('h_bed_sheet', (bx1 - bx0 - 0.25, by1 - by0 + 0.01, 0.012), (bxc - 0.05, byc, top + 0.002), sheet_m, 0.004)
    B.box('h_bed_pillow', (0.3, 0.55, 0.1), (bx0 + 0.2, byc, top + 0.05), sheet_m, 0.04, (0, -8, 0), 3)
    B.box('h_bed_base', (bx1 - bx0 - 0.1, by1 - by0 - 0.1, top - 0.2), (bxc, byc + 0.03, (top - 0.1) / 2), white, 0.02, (0, 0, 0), 3)
    B.box('h_bed_drawer', (0.5, 0.01, 0.12), (bxc - 0.35, by0 + 0.035, (top - 0.1) * 0.6), steel, 0.004)
    # curtain on a ceiling track behind-left of him
    B.cyl('h_track', 0.012, 3.0, (XW + 0.45, 0.0, ZC - 0.25), steel, (90, 0, 0), 12)
    bpy.ops.mesh.primitive_plane_add(size=1, location=(XW + 0.45, -0.2, (ZC - 0.27) / 2 + 0.05), rotation=(math.radians(90), 0, math.radians(90)))
    cu = bpy.context.object; cu.name = 'h_curtain'; _link(c, cu); cu.scale = (2.0, ZC - 0.35, 1)
    bpy.ops.object.select_all(action='DESELECT'); cu.select_set(True); bpy.context.view_layer.objects.active = cu
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    md = cu.modifiers.new('sub', 'SUBSURF'); md.subdivision_type = 'SIMPLE'; md.levels = 5; md.render_levels = 5
    wv = cu.modifiers.new('folds', 'WAVE'); wv.use_x = False; wv.use_y = True; wv.height = 0.05; wv.width = 0.2; wv.narrowness = 1.0; wv.speed = 0
    wv.use_normal = True; wv.use_normal_x = wv.use_normal_y = wv.use_normal_z = True
    so = cu.modifiers.new('thick', 'SOLIDIFY'); so.thickness = 0.006
    cu.data.materials.append(curt_m); _smooth(cu)
    # monitor cart with a lit screen
    mx_, my_ = -1.3, 1.1
    B.cyl('h_cart_pole', 0.022, 1.2, (mx_, my_, 0.62), steel, (0, 0, 0), 16)
    for k in range(5):
        a = math.radians(72 * k); B.box('h_cart_leg', (0.3, 0.03, 0.02), (mx_ + math.cos(a) * 0.15, my_ + math.sin(a) * 0.15, 0.06), steel, 0.006, (0, 0, math.degrees(a)))
    B.box('h_monitor', (0.42, 0.1, 0.32), (mx_, my_ - 0.02, 1.38), mat('kw_h_monitor', (0.75, 0.77, 0.78), 0.4), 0.025, (6, 0, 18), 3)
    B.box('h_monitor_screen', (0.36, 0.005, 0.24), (mx_ - 0.016, my_ - 0.072, 1.385), _screen('kw_h_vitals', 'vitals'), 0.0, (6, 0, 18))
    B.box('h_cart_basket', (0.3, 0.2, 0.08), (mx_, my_, 0.95), steel, 0.01)
    # Poly Haven props (CC0)
    _gltf(c, 'wall_clock', (0.55, YW - 0.03, 2.1), 0, 1.0)
    _gltf(c, 'potted_plant_02', (1.25, YW - 0.35, 0.0), 30, 1.15)
    _gltf(c, 'side_table_01', (0.75, YW - 0.35, 0.0), 0, 1.0)
    _gltf(c, 'wheelchair_01', (XW + 0.45, -1.15, 0.0), 75, 1.0)
    _gltf(c, 'modern_ceiling_lamp_01', (0.35, 0.25, ZC - 0.02), 0, 1.0)
    # wall details: hand sanitiser box, glove box shelf, poster frame with soft gradient (no text)
    B.box('h_dispenser', (0.12, 0.08, 0.22), (1.6, YW - 0.04, 1.3), white, 0.015, (0, 0, 0), 3)
    B.box('h_shelf', (0.6, 0.18, 0.025), (-1.35, YW - 0.09, 1.55), white, 0.005)
    for k, colr in enumerate(((0.1, 0.35, 0.8), (0.75, 0.2, 0.55), (0.9, 0.85, 0.85))):
        B.box('h_glovebox', (0.15, 0.09, 0.08), (-1.55 + k * 0.17, YW - 0.1, 1.605), mat(f'kw_h_gb{k}', colr, 0.6), 0.004)
    frame = B.box('h_frame', (0.55, 0.025, 0.7), (-0.05, YW - 0.015, 1.75), mat('kw_h_framewood', (0.5, 0.36, 0.22), 0.5), 0.008)
    B.box('h_frame_img', (0.48, 0.005, 0.62), (-0.05, YW - 0.03, 1.75), mat('kw_h_chart', (0.75, 0.82, 0.86), 0.7), 0.0)
    if Q.enabled('DRESSING'):
        # Coherent clinical headwall: satin extrusion, instrument sockets and a folded lower sheet.
        fascia = mat('kw_h_headwall', (0.53, 0.70, 0.73), 0.42)
        socket = mat('kw_h_socket', (0.095, 0.20, 0.24), 0.50)
        ring = mat('kw_h_medical_blue', (0.05, 0.32, 0.56), 0.35, 0.16)
        B.box('h_headwall', (1.77, 0.048, 0.13), (-0.58, YW - 0.027, 1.12), fascia, 0.012)
        B.box('h_headwall_shadow_line', (1.74, 0.011, 0.012), (-0.58, YW - 0.053, 1.08), socket, 0.005)
        for x_ in (-1.29, -1.17, 0.03, 0.16):
            B.cyl('h_service_ring', 0.025, 0.012, (x_, YW - 0.058, 1.131), ring, (90, 0, 0), 16)
            B.cyl('h_service_port', 0.014, 0.013, (x_, YW - 0.065, 1.131), socket, (90, 0, 0), 12)
        blanket = tex('kw_h_blanket', 'Fabric036', 9, tint=(0.25, 0.57, 0.63), nor=1.1)
        B.box('h_bed_blanket_fold', (0.43, by1 - by0 + 0.018, 0.023), (-0.36, byc, top + 0.014), blanket, 0.008)
        B.box('h_bed_blanket_drop', (0.43, 0.018, 0.11), (-0.36, by0 - 0.014, top - 0.036), blanket, 0.008, (-6, 0, 0))
        frame.data.materials[0] = ring
        # Mark the chart as a designed prop, not a blank block. Lines are intentionally non-readable.
        for k, x_ in enumerate((-0.192, -0.03, 0.124)):
            B.box('h_chart_bar', (0.062, 0.002, 0.07 + k * 0.034), (x_, YW - 0.034, 1.74), ring, 0)
        for z in (1.55, 1.576, 1.887):
            B.box('h_chart_rule', (0.36, 0.002, 0.004), (-0.045, YW - 0.034, z), ring, 0)
    # lights: warm key front-right, cool rim back-left, ceiling bounce
    h.lights = [_area(c, 'h_key', (1.25, -1.45, 2.25), 160, 1.3, (1.0, 0.86, 0.72), (0, 0, H - 0.1)),
                _area(c, 'h_rim', (-1.2, 1.1, 2.1), 110, 0.8, (0.55, 0.75, 1.0), (0, 0, H - 0.1)),
                _area(c, 'h_fill', (0.2, -1.8, 1.0), 30, 1.5, (1.0, 0.95, 0.9), (0, 0, H - 0.2))]
    if Q.enabled('DRESSING'):
        h.lights[0].data.color = (1.0, 0.94, 0.85); h.lights[0].data.energy = 185
    if Q.enabled('PEOPLE2'):
        key, rim, fill = h.lights
        key.data.size, key.data.energy, key.data.color = 1.18, 218, (1., .96, .91)
        rim.data.energy, fill.data.energy = 72, 15
    return h
