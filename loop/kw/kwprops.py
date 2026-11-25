"""kwprops - reusable table-top props for kwkit (slate batch 1).  Every prop is built at the origin, lying or standing on
the plane z=0 (so its root sits ON a surface), real sizes in metres, and returns a Prop:  .root (empty), .objs,
.set(**controls) for its animated controls, .point(name) for a named world point (e.g. the penlight tip).

    make(kind, coll, K=None, **params) -> Prop          kinds: see KINDS (kwkit.ITEMS lists the same names)

Controls (all 0..1 unless said):  burger/fries/salmon/wedges/salad eaten | penlight on | pea sprout | ball squash.
Poly Haven (CC0, assets/real/models): hamburger_buns (bun), magnifying_glass_01, metal_stool_01 (kwsets clinic stool).
"""
import bpy, bmesh, math, random, os
from mathutils import Vector as V, Matrix
import kwlib as L

KINDS = ('tray', 'burger', 'fries', 'salmon', 'wedges', 'salad', 'cup', 'penlight', 'tweezers', 'probe', 'magnifier',
         'paperclip', 'pea', 'ball', 'bulb', 'bench')
HERE = os.path.dirname(os.path.abspath(__file__))


# ===================================================================================== helpers
class Prop:
    def __init__(self, name, coll):
        self.name = name; self.coll = coll
        self.root = bpy.data.objects.new('kwp_' + name, None); coll.objects.link(self.root); self.root.empty_display_size = 0.05
        self.objs = []; self.pts = {}; self._set = None
    def add(self, o):
        for u in list(o.users_collection): u.objects.unlink(o)
        self.coll.objects.link(o)
        if o.parent is None: o.parent = self.root
        self.objs.append(o); return o
    def set(self, **kw):
        if self._set: self._set(**kw)
    def point(self, name):
        return self.root.matrix_world @ V(self.pts.get(name, (0, 0, 0)))


def _mesh(name, verts, faces, mt=None, smooth=True):
    me = bpy.data.meshes.new(name); me.from_pydata([tuple(v) for v in verts], [], faces); me.update()
    o = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(o)
    if mt: o.data.materials.append(mt)
    if smooth: L.smooth(o)
    return o


def rrect(w, d, r, n=6):
    """rounded rectangle outline (CCW), 4*n points"""
    r = min(r, w / 2 - 1e-4, d / 2 - 1e-4); pts = []
    for cx, cy, a0 in ((w / 2 - r, d / 2 - r, 0), (-w / 2 + r, d / 2 - r, 90), (-w / 2 + r, -d / 2 + r, 180), (w / 2 - r, -d / 2 + r, 270)):
        for k in range(n):
            a = math.radians(a0 + 90 * k / (n - 1)); pts.append((cx + r * math.cos(a), cy + r * math.sin(a)))
    return pts


def loft(name, loops, mt=None, cap_bottom=True, cap_top=False):
    """skin between closed loops [(pts2d, z), ...] of equal length"""
    vs = []; fs = []; n = len(loops[0][0])
    for pts, z in loops: vs += [(x, y, z) for x, y in pts]
    for j in range(len(loops) - 1):
        for i in range(n): fs.append((j * n + i, j * n + (i + 1) % n, (j + 1) * n + (i + 1) % n, (j + 1) * n + i))
    if cap_bottom: fs.append(tuple(reversed(range(n))))
    if cap_top: fs.append(tuple(range((len(loops) - 1) * n, len(loops) * n)))
    return _mesh(name, vs, fs, mt)


def ring_tube(name, pts3d, r, mt=None, res=4):
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = r; cu.bevel_resolution = res
    sp = cu.splines.new('POLY'); sp.points.add(len(pts3d) - 1); sp.use_cyclic_u = True
    for p_, q in zip(sp.points, pts3d): p_.co = (*q, 1)
    o = bpy.data.objects.new(name, cu); bpy.context.scene.collection.objects.link(o)
    if mt: o.data.materials.append(mt)
    return o


def _nodes(m): nt = m.node_tree; return nt, nt.nodes, nt.links.new, nt.nodes['Principled BSDF']


def plastic(name, col, rough=0.5, scuff=1.0, sheen=0.25):
    """matte plastic: soft sheen, fine directional scuffs in roughness + a faint colour mottle"""
    m = L.mat(name, col, rough, coat=sheen); nt, N, Lk, b = _nodes(m)
    tc = N.new('ShaderNodeTexCoord'); mp = N.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (60, 2.5, 60); Lk(tc.outputs['Object'], mp.inputs['Vector'])
    sc = N.new('ShaderNodeTexNoise'); sc.inputs['Scale'].default_value = 9.0; sc.inputs['Detail'].default_value = 8; Lk(mp.outputs[0], sc.inputs['Vector'])
    cr = N.new('ShaderNodeValToRGB'); cr.color_ramp.elements[0].position = 0.55; cr.color_ramp.elements[1].position = 0.75; Lk(sc.outputs['Fac'], cr.inputs['Fac'])
    mr = N.new('ShaderNodeMapRange'); mr.inputs[3].default_value = rough; mr.inputs[4].default_value = min(1.0, rough + 0.3 * scuff); Lk(cr.outputs['Color'], mr.inputs['Value']); Lk(mr.outputs[0], b.inputs['Roughness'])
    mo = N.new('ShaderNodeTexNoise'); mo.inputs['Scale'].default_value = 30.0; Lk(tc.outputs['Object'], mo.inputs['Vector'])
    mx = N.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.inputs['Factor'].default_value = 0.06
    mx.inputs[6].default_value = (*col, 1); Lk(mo.outputs['Color'], mx.inputs[7]); Lk(mx.outputs[2], b.inputs['Base Color'])
    bp = N.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.08 * scuff; bp.inputs['Distance'].default_value = 0.0005; Lk(cr.outputs['Color'], bp.inputs['Height']); Lk(bp.outputs['Normal'], b.inputs['Normal'])
    return m


def brushed(name, col=(0.78, 0.79, 0.8), rough=0.28):
    """brushed steel: streaks along local X in roughness and a faint bump"""
    m = L.mat(name, col, rough, 1.0); nt, N, Lk, b = _nodes(m)
    tc = N.new('ShaderNodeTexCoord'); mp = N.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (3, 400, 400); Lk(tc.outputs['Object'], mp.inputs['Vector'])
    nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 4.0; nz.inputs['Detail'].default_value = 6; Lk(mp.outputs[0], nz.inputs['Vector'])
    mr = N.new('ShaderNodeMapRange'); mr.inputs[3].default_value = rough - 0.08; mr.inputs[4].default_value = rough + 0.12; Lk(nz.outputs['Fac'], mr.inputs['Value']); Lk(mr.outputs[0], b.inputs['Roughness'])
    bp = N.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.05; bp.inputs['Distance'].default_value = 0.0002; Lk(nz.outputs['Fac'], bp.inputs['Height']); Lk(bp.outputs['Normal'], b.inputs['Normal'])
    return m


def two_tone(name, c0, c1, scale=20.0, rough=0.5, coat=0.0, sss=0.0, bump=0.2, axis_ramp=None, ramp_cols=None):
    """noise mix of two colours (food); axis_ramp=('Z', a, b) darkens along a Generated axis (fry tips)"""
    m = L.mat(name, c0, rough, coat=coat, sss=sss); nt, N, Lk, b = _nodes(m)
    tc = N.new('ShaderNodeTexCoord'); nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = scale; nz.inputs['Detail'].default_value = 6
    Lk(tc.outputs['Object'], nz.inputs['Vector'])
    cr = N.new('ShaderNodeValToRGB'); cr.color_ramp.elements[0].color = (*c0, 1); cr.color_ramp.elements[1].color = (*c1, 1)
    cr.color_ramp.elements[0].position = 0.35; cr.color_ramp.elements[1].position = 0.7; Lk(nz.outputs['Fac'], cr.inputs['Fac'])
    out = cr.outputs['Color']
    if axis_ramp:
        sep = N.new('ShaderNodeSeparateXYZ'); Lk(tc.outputs['Generated'], sep.inputs[0])
        r2 = N.new('ShaderNodeMapRange'); r2.inputs[1].default_value = axis_ramp[1]; r2.inputs[2].default_value = axis_ramp[2]; Lk(sep.outputs[axis_ramp[0]], r2.inputs['Value'])
        mx = N.new('ShaderNodeMix'); mx.data_type = 'RGBA'; Lk(r2.outputs[0], mx.inputs['Factor']); Lk(out, mx.inputs[6]); mx.inputs[7].default_value = (*ramp_cols, 1); out = mx.outputs[2]
    Lk(out, b.inputs['Base Color'])
    if bump:
        bp = N.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = bump; bp.inputs['Distance'].default_value = 0.001; Lk(nz.outputs['Fac'], bp.inputs['Height']); Lk(bp.outputs['Normal'], b.inputs['Normal'])
    return m


def _box(name, size, loc, mt, c=None, bev=0.0, rot=(0, 0, 0)):
    """box with its scale applied so the bevel width is in metres"""
    o = L.prim('cube', name, mt, c, size=1, location=(0, 0, 0)); o.scale = size
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active = o
    bpy.ops.object.transform_apply(location=False, rotation=False, scale=True)
    o.location = loc; o.rotation_euler = [math.radians(a) for a in rot]
    if bev:
        m = o.modifiers.new('b', 'BEVEL'); m.width = bev; m.segments = 3; m.limit_method = 'NONE'; L.smooth(o)
    return o


def _ground(objs, z0=0.0):
    """lift objects together so their lowest evaluated point sits at z0"""
    bpy.context.view_layer.update(); dg = bpy.context.evaluated_depsgraph_get(); mn = 1e9
    for o in objs:
        oe = o.evaluated_get(dg); mn = min(mn, min((oe.matrix_world @ V(b)).z for b in oe.bound_box))
    for o in objs: o.location.z += z0 - mn


def _bool_cut(objs, cutter, name):
    mods = []
    for o in objs:
        md = o.modifiers.new(name, 'BOOLEAN'); md.operation = 'DIFFERENCE'; md.solver = 'EXACT'; md.object = cutter
        md.show_viewport = md.show_render = False; mods.append(md)
    cutter.hide_render = True; cutter.hide_viewport = True; cutter.display_type = 'WIRE'
    return mods


def _show(o, on):
    h = not on
    if o.hide_render != h: o.hide_render = h


def _noise_disp(o, strength, scale, name='kwp_disp'):
    tx = bpy.data.textures.new(name, 'CLOUDS'); tx.noise_scale = scale
    md = o.modifiers.new('disp', 'DISPLACE'); md.texture = tx; md.strength = strength; md.texture_coords = 'LOCAL'; md.mid_level = 0.5
    return md


def _gltf(model):
    import kw_realism as R
    p = os.path.join(HERE, '..', '..', 'assets', 'real', 'models', model, f'{model}_1k.gltf')
    objs = R.import_gltf(os.path.normpath(p)); bpy.context.view_layer.update(); return objs


def _bisect_keep(o, z, keep_above, cap_mat):
    """cut a mesh object at local height z, keep one side, fill the cut with cap_mat (bread crumb)"""
    bm = bmesh.new(); bm.from_mesh(o.data)
    geom = bm.verts[:] + bm.edges[:] + bm.faces[:]
    res = bmesh.ops.bisect_plane(bm, geom=geom, plane_co=(0, 0, z), plane_no=(0, 0, 1), clear_outer=not keep_above, clear_inner=keep_above)
    cut = [e for e in res['geom_cut'] if isinstance(e, bmesh.types.BMEdge)]
    nf = bmesh.ops.holes_fill(bm, edges=cut, sides=0)['faces'] if cut else []
    o.data.materials.append(cap_mat); mi = len(o.data.materials) - 1
    for f in nf: f.material_index = mi; f.smooth = False
    bm.to_mesh(o.data); bm.free(); o.data.update()


# ===================================================================================== A1 tray
TRAY = {'meal': dict(w=0.45, d=0.35, h=0.015, r=0.03, mat='plastic', col=(0.30, 0.28, 0.26)),
        'clinic': dict(w=0.30, d=0.20, h=0.02, r=0.02, mat='steel', col=(0.78, 0.79, 0.8))}


def tray(c, K=None, style='meal', w=None, d=None, h=None, r=None, color=None, liner=None, **_):
    """meal tray 45x35 cm, rim 1.5 cm, corner r 3 cm, matte plastic (color) | clinic tray 30x20x2 cm brushed steel, rolled rim.
    liner: None | 'paper' | 'cloth' (Fabric030) lying inside.  Point 'floor' = top of the tray floor (place food there)."""
    P = TRAY[style]; w = w or P['w']; d = d or P['d']; h = h or P['h']; r = r or P['r']; col = color or P['col']
    pr = Prop('tray_' + style, c)
    m = plastic('kwp_tray_' + style, col, 0.5) if P['mat'] == 'plastic' else brushed('kwp_tray_steel')
    t = 0.003 if style == 'meal' else 0.0009; flare = 0.008 if style == 'meal' else 0.012; n = 7
    bot = rrect(w - 2 * flare, d - 2 * flare, r - flare * 0.5, n); top = rrect(w, d, r, n)
    body = pr.add(loft('kwp_tray_body', [(bot, 0.0), (top, h)], m))
    so = body.modifiers.new('t', 'SOLIDIFY'); so.thickness = t; so.offset = -1.0     # inward/up: the floor must not sit coplanar with the table
    bv = body.modifiers.new('b', 'BEVEL'); bv.width = 0.0012; bv.segments = 2; bv.limit_method = 'ANGLE'
    rim_r = 0.004 if style == 'meal' else 0.0022
    rim = pr.add(ring_tube('kwp_tray_rim', [(x, y, h - rim_r * 0.4) for x, y in rrect(w + rim_r * 0.6, d + rim_r * 0.6, r, n)], rim_r, m))
    pr.pts['floor'] = (0, 0, t + 0.0003)
    if liner:
        lw, ld = w - 2 * flare - 0.03, d - 2 * flare - 0.03
        bpy.ops.mesh.primitive_grid_add(x_subdivisions=40, y_subdivisions=32, size=1.0); g = bpy.context.object; g.name = 'kwp_liner'
        g.scale = (lw, ld, 1); g.location = (0, 0, t + 0.0012); bpy.ops.object.transform_apply(location=False, scale=True)
        _noise_disp(g, 0.0025, 0.05, 'kwp_liner_n')
        if liner == 'cloth':
            lm = None
            try:
                if K: lm = K.tex('kwp_cloth', 'Fabric030', 6.0, tint=(0.75, 0.82, 0.9))
            except Exception as e: print('cloth tex failed', e)
            lm = lm or L.bumpy(L.mat('kwp_cloth', (0.75, 0.82, 0.9), 0.9), 300, 0.2, dist=0.0005)
        else:
            lm = L.bumpy(L.mat('kwp_paper', (0.93, 0.91, 0.86), 0.85, sss=0.05), 400.0, 0.08, 3.0, dist=0.0003)
        g.data.materials.append(lm); L.smooth(g); pr.add(g); pr.pts['floor'] = (0, 0, t + 0.0015)
    return pr


# ===================================================================================== A2 food
def burger(c, K=None, width=0.11, height=0.06, bite_side=225.0, **_):
    """cheeseburger 11 x 6 cm: Poly Haven bun (cut in two), rough patty, cheese with one drooping corner, lettuce frill,
    sesame seeds.  eaten 0..1: round 3.5 cm bites from one side (bite_side, deg from +X; 225 = front-left), gone at 0.96."""
    pr = Prop('burger', c)
    crumb = L.bumpy(L.mat('kwp_crumb', (0.86, 0.72, 0.5), 0.8), 600, 0.25, dist=0.0006)
    objs = _gltf('hamburger_buns'); bun = next(o for o in objs if o.name.startswith('hamburger_buns_01'))
    for o in objs:
        if o is not bun: bpy.data.objects.remove(o, do_unlink=True)
    bun.parent = None; bun.matrix_world = Matrix.Identity(4)
    bun.data = bun.data.copy()
    sx = width / 0.104; zb, zt = 0.016, 0.03            # bottom heel / crown cut heights on the 6.3 cm bun
    top = bun.copy(); top.data = bun.data.copy(); bpy.context.scene.collection.objects.link(top)
    _bisect_keep(bun, zb, False, crumb); _bisect_keep(top, zt, True, crumb)
    hp, hc, hl = 0.012, 0.003, 0.004
    kz = (height - hp - hc - hl) / ((0.063 - zt) + zb)     # squeeze the bread so the stack is `height`
    bun.scale = (sx, sx, kz); bun.location = (0, 0, 0)
    z = zb * kz
    patty_m = two_tone('kwp_patty', (0.16, 0.07, 0.035), (0.05, 0.022, 0.012), 90, 0.55, bump=0.6)
    pat = L.cyl('kwp_patty', width * 0.5 * 0.98, hp, (0, 0, z + hp / 2), patty_m, None, verts=48)
    ss = pat.modifiers.new('s', 'SUBSURF'); ss.levels = ss.render_levels = 2; _noise_disp(pat, 0.0025, 0.012, 'kwp_patty_n'); z += hp
    # cheese: square slice rotated 45, corners droop (one more), lettuce frill under it
    N = 16; s = width * 0.42; vs = []; fs = []
    for j in range(N + 1):
        for i in range(N + 1):
            x = -s + 2 * s * i / N; y = -s + 2 * s * j / N; rr = math.hypot(x, y); dz = -max(0.0, rr - width * 0.48) * 0.5
            if x > s * 0.55 and y > s * 0.55: dz -= ((x - s * 0.55) + (y - s * 0.55)) * 0.55     # the drooping corner
            vs.append((x, y, dz))
    for j in range(N):
        for i in range(N): fs.append((j * (N + 1) + i, j * (N + 1) + i + 1, (j + 1) * (N + 1) + i + 1, (j + 1) * (N + 1) + i))
    ch = _mesh('kwp_cheese', vs, fs, L.mat('kwp_cheese_m', (0.95, 0.55, 0.06), 0.35, sss=0.2, coat=0.2))
    ch.rotation_euler = (0, 0, math.radians(bite_side + 20))   # drooping corner ~65 deg round from the bitten side; ch.location = (0, 0, z + hc * 0.5); so = ch.modifiers.new('t', 'SOLIDIFY'); so.thickness = hc
    z += hc
    lv = []; lf = []; NA, NR = 96, 4
    for j in range(NR + 1):
        rr = width * (0.40 + 0.17 * j / NR)
        for i in range(NA):
            a = 2 * math.pi * i / NA; wv = math.sin(a * 13) * 0.6 + math.sin(a * 7 + 1) * 0.4
            lv.append((rr * math.cos(a) * (1 + 0.04 * wv * j / NR), rr * math.sin(a) * (1 + 0.04 * wv * j / NR), 0.0025 * wv * (j / NR) - 0.006 * (j / NR) ** 2))
    for j in range(NR):
        for i in range(NA): lf.append((j * NA + i, j * NA + (i + 1) % NA, (j + 1) * NA + (i + 1) % NA, (j + 1) * NA + i))
    let = _mesh('kwp_lettuce', lv, lf, two_tone('kwp_lettuce_m', (0.25, 0.6, 0.1), (0.55, 0.8, 0.25), 60, 0.45, sss=0.2, bump=0.3))
    let.location = (0, 0, z - hc - 0.0005); so = let.modifiers.new('t', 'SOLIDIFY'); so.thickness = 0.0008
    z += hl
    top.scale = (sx, sx, kz); top.location = (0, 0, z - zt * kz)
    # sesame seeds on the crown (ray cast down onto the evaluated crown)
    bpy.context.view_layer.update(); seed_m = L.mat('kwp_sesame', (0.93, 0.85, 0.62), 0.5); rnd = random.Random(11)
    dg = bpy.context.evaluated_depsgraph_get(); Mi = top.matrix_world.inverted(); seeds = []
    for k in range(46):
        a = rnd.uniform(0, 2 * math.pi); rr = width * 0.40 * math.sqrt(rnd.random())
        p0 = V((rr * math.cos(a), rr * math.sin(a), 0.2))
        hit, loc, nor, idx = top.evaluated_get(dg).ray_cast(Mi @ p0, (Mi.to_3x3() @ V((0, 0, -1))).normalized())
        if not hit: continue
        w_ = top.matrix_world @ loc; nw = (top.matrix_world.to_3x3().inverted().transposed() @ nor).normalized()
        sd = L.sphere('kwp_seed', 1, w_ + nw * 0.0004, seed_m, None, 8, 4); sd.scale = (0.0018, 0.0009, 0.0006)
        sd.rotation_euler = nw.to_track_quat('Z', 'Y').to_euler(); sd.rotation_euler.rotate_axis('Z', rnd.uniform(0, 6.3)); seeds.append(sd)
    parts = [bun, pat, ch, let, top]
    for o in parts + seeds: pr.add(o)
    for o in seeds: o.parent = top; o.matrix_parent_inverse = top.matrix_world.inverted()
    # bites: (angle offset deg, centre distance as a fraction of the radius)
    R = width / 2; rb = 0.0185; cuts = []
    for k, (da, fr) in enumerate(((0, 1.14), (-30, 1.08), (30, 1.08), (0, 0.78), (-28, 0.62), (28, 0.62), (0, 0.36), (-35, 0.2), (35, 0.2))):
        a = math.radians(bite_side + da); cu = L.cyl(f'kwp_bite{k}', rb + 0.002 * (k % 2), height * 3, (R * fr * math.cos(a), R * fr * math.sin(a), height / 2), None, None, verts=28)
        pr.add(cu); cuts.append(_bool_cut(parts, cu, f'bite{k}'))
    TH = [0.05 + 0.1 * k for k in range(len(cuts))]
    def _s(eaten=0.0, **_):
        for th, mods in zip(TH, cuts):
            for md in mods: on = eaten >= th; md.show_render = md.show_viewport = on
        for o in parts + seeds: _show(o, eaten < 0.96)
    pr._set = _s; _s(0.0); return pr


def fries(c, K=None, count=14, sleeve=True, **_):
    """fries: `count` sticks 7-9 cm, golden with darker tips, standing in a red paper sleeve; eaten 0..1 removes them one by one"""
    pr = Prop('fries', c); rnd = random.Random(4)
    fm = two_tone('kwp_fry', (0.93, 0.68, 0.26), (0.86, 0.55, 0.16), 140, 0.5, bump=0.25, axis_ramp=('Z', 0.8, 1.0), ramp_cols=(0.55, 0.28, 0.07))
    sw, sd_, sh = 0.085, 0.035, 0.075
    if sleeve:
        pm = two_tone('kwp_sleeve', (0.75, 0.05, 0.04), (0.68, 0.04, 0.035), 50, 0.6, bump=0.05)
        bot = rrect(sw * 0.72, sd_ * 0.7, 0.008, 5); top = rrect(sw, sd_, 0.012, 5)
        sl = pr.add(loft('kwp_sleeve', [(bot, 0.0), (top, sh)], pm)); so = sl.modifiers.new('t', 'SOLIDIFY'); so.thickness = 0.0007
    sticks = []
    for i in range(count):
        ln = rnd.uniform(0.07, 0.09); x = (i % 7 - 3) / 3 * sw * 0.36 + rnd.uniform(-0.003, 0.003); y = (i // 7 - 0.5) * sd_ * 0.45
        b = _box(f'kwp_fry{i}', (0.0085, 0.0085, ln), (x, y, ln / 2 + 0.01), fm, None, 0.0015)
        b.rotation_euler = (rnd.uniform(-0.18, 0.18), rnd.uniform(-0.25, 0.25) + x * 3.0, rnd.uniform(0, 3.14)); sticks.append(pr.add(b))
    order = sorted(range(count), key=lambda i: -sticks[i].location.z - sticks[i].dimensions.z * 0.5 + rnd.uniform(0, 0.01))
    def _s(eaten=0.0, **_):
        gone = int(round(eaten * count))
        for k, i in enumerate(order): _show(sticks[i], k >= gone)
    pr._set = _s; return pr


def salmon(c, K=None, size=(0.12, 0.06, 0.025), **_):
    """salmon fillet 12 x 6 x 2.5 cm: orange-pink, pale fat lines, glossy top; eaten 0..1 = forkfuls from the +X end"""
    pr = Prop('salmon', c); lx, ly, lz = size; NU, NV = 32, 10; vs = []; fs = []
    for j in range(NV + 1):
        v = j / NV; sc = 1 - 0.38 * v ** 2.2                      # domed: the outline pulls in toward the top
        for i in range(NU):
            a = 2 * math.pi * i / NU; u = math.cos(a); x = lx / 2 * u * sc
            y = ly / 2 * math.sin(a) * sc * (1 - 0.35 * max(0.0, u) ** 2)      # tail end (+X) narrower
            hz = lz * (1 - 0.45 * max(0.0, u) ** 2)                         # and thinner
            vs.append((x, y, hz * math.sin(v * math.pi / 2)))
    for j in range(NV):
        for i in range(NU): fs.append((j * NU + i, j * NU + (i + 1) % NU, (j + 1) * NU + (i + 1) % NU, (j + 1) * NU + i))
    fs.append(tuple(reversed(range(NU)))); fs.append(tuple(range(NV * NU, (NV + 1) * NU)))
    m = L.mat('kwp_salmon', (0.85, 0.30, 0.16), 0.3, coat=0.45, sss=0.15); nt, N, Lk, b = _nodes(m)
    tc = N.new('ShaderNodeTexCoord'); wv = N.new('ShaderNodeTexWave'); wv.inputs['Scale'].default_value = 9.0; wv.inputs['Distortion'].default_value = 2.0
    mp = N.new('ShaderNodeMapping'); mp.inputs['Rotation'].default_value = (0, 0, 0.6); mp.inputs['Scale'].default_value = (14, 14, 14); Lk(tc.outputs['Object'], mp.inputs['Vector']); Lk(mp.outputs[0], wv.inputs['Vector'])
    cr = N.new('ShaderNodeValToRGB'); cr.color_ramp.elements[0].position = 0.86; cr.color_ramp.elements[0].color = (0.85, 0.30, 0.16, 1); cr.color_ramp.elements[1].position = 0.95; cr.color_ramp.elements[1].color = (0.98, 0.72, 0.58, 1)
    Lk(wv.outputs['Fac'], cr.inputs['Fac']); Lk(cr.outputs['Color'], b.inputs['Base Color'])
    o = _mesh('kwp_salmon', vs, fs, m); ss = o.modifiers.new('s', 'SUBSURF'); ss.levels = ss.render_levels = 1
    _noise_disp(o, 0.0012, 0.01, 'kwp_salmon_n'); pr.add(o)
    rnd = random.Random(8); cuts = []
    for k in range(6):
        x = lx / 2 + 0.006 - k * lx * 0.15; cu = L.sphere(f'kwp_fork{k}', 0.016 + 0.003 * rnd.random(), (x, rnd.uniform(-0.01, 0.01), lz * 1.05), None, None, 20, 10)
        cu.scale = (0.9, 1.6, 1.0); pr.add(cu); cuts.append(_bool_cut([o], cu, f'fork{k}'))
    def _s(eaten=0.0, **_):
        for k, mods in enumerate(cuts):
            for md in mods: on = eaten >= 0.05 + 0.15 * k; md.show_render = md.show_viewport = on
        _show(o, eaten < 0.96)
    pr._set = _s; _s(0.0); return pr


def wedges(c, K=None, count=5, **_):
    """sweet potato wedges (count, ~7 cm): orange flesh, darker skin on the curved back; eaten 0..1 removes them one by one"""
    pr = Prop('wedges', c); rnd = random.Random(21)
    flesh = two_tone('kwp_wedge', (0.95, 0.42, 0.06), (0.85, 0.32, 0.04), 70, 0.45, coat=0.25, bump=0.35)
    skin = two_tone('kwp_wedge_skin', (0.35, 0.10, 0.05), (0.5, 0.18, 0.08), 50, 0.6, bump=0.4)
    items = []
    for k in range(count):
        ln = rnd.uniform(0.065, 0.078); R = rnd.uniform(0.017, 0.021); NA, NL = 8, 10; vs = []; fs = []
        for j in range(NL + 1):
            v = j / NL; tp = math.sin(math.pi * (0.08 + 0.84 * v)) ** 0.6
            vs.append((ln * (v - 0.5), 0, 0))
            for i in range(NA + 1):
                a = math.radians(-35 + 70 * i / NA); vs.append((ln * (v - 0.5), R * tp * math.sin(a), R * tp * math.cos(a)))
        st = NA + 2; mats = []
        for j in range(NL):
            b0, b1 = j * st, (j + 1) * st
            for i in range(NA): fs.append((b0 + 1 + i, b1 + 1 + i, b1 + 2 + i, b0 + 2 + i)); mats.append(1)
            fs.append((b0, b1, b1 + 1, b0 + 1)); mats.append(0); fs.append((b0, b0 + st - 1, b1 + st - 1, b1)); mats.append(0)
        o = _mesh(f'kwp_wedge{k}', vs, fs, flesh); o.data.materials.append(skin)
        for p_, mi in zip(o.data.polygons, mats): p_.material_index = mi
        o.rotation_euler = (math.radians(rnd.uniform(140, 175)), 0, math.radians(-30 + 15 * k + rnd.uniform(-8, 8)))
        o.location = (-0.03 + 0.016 * k, rnd.uniform(-0.012, 0.012) + 0.004 * k, R * 0.75)
        ss = o.modifiers.new('s', 'SUBSURF'); ss.levels = ss.render_levels = 1; items.append(pr.add(o)); _ground([o])
    def _s(eaten=0.0, **_):
        gone = int(round(eaten * count))
        for k, o in enumerate(reversed(items)): _show(o, k >= gone)
    pr._set = _s; return pr


def salad(c, K=None, count=8, **_):
    """a small pile of green salad leaves (count, 4-6 cm); eaten 0..1 removes them one by one (top first)"""
    pr = Prop('salad', c); rnd = random.Random(31); items = []
    m = two_tone('kwp_leaf', (0.18, 0.5, 0.08), (0.45, 0.75, 0.2), 45, 0.45, sss=0.25, bump=0.4)
    for k in range(count):
        ln = rnd.uniform(0.04, 0.06); wd = ln * 0.6; NU, NV = 10, 6; vs = []; fs = []
        for j in range(NV + 1):
            for i in range(NU + 1):
                u = i / NU; v = j / NV * 2 - 1; half = math.sin(math.pi * u) ** 0.8 * wd / 2
                x = ln * (u - 0.5); y = v * half; z = 0.012 * (abs(v) ** 1.6) * math.sin(math.pi * u) + 0.002 * math.sin(i * 2.1 + j * 1.7) * abs(v)
                vs.append((x, y, z))
        for j in range(NV):
            for i in range(NU): fs.append((j * (NU + 1) + i, j * (NU + 1) + i + 1, (j + 1) * (NU + 1) + i + 1, (j + 1) * (NU + 1) + i))
        o = _mesh(f'kwp_leaf{k}', vs, fs, m); so = o.modifiers.new('t', 'SOLIDIFY'); so.thickness = 0.0007
        o.rotation_euler = (rnd.uniform(-0.4, 0.4), rnd.uniform(-0.4, 0.4), rnd.uniform(0, 6.28))
        o.location = (rnd.uniform(-0.02, 0.02), rnd.uniform(-0.015, 0.015), 0.003 + 0.0045 * k); items.append(pr.add(o))
    _ground(items)
    def _s(eaten=0.0, **_):
        gone = int(round(eaten * count))
        for k, o in enumerate(reversed(items)): _show(o, k >= gone)
    pr._set = _s; return pr


# ===================================================================================== A3 cup
def cup(c, K=None, height=0.1, r_top=0.04, r_bottom=0.031, lid=True, straw=True, color=(0.95, 0.95, 0.92), **_):
    """the kit's held cup (white, 4 cm radius, 10 cm) as a table item: slightly tapered wall, flat lid with a sip hole,
    optional red straw"""
    pr = Prop('cup', c); n = 40
    ring = lambda r: [(r * math.cos(2 * math.pi * i / n), r * math.sin(2 * math.pi * i / n)) for i in range(n)]
    m = plastic('kwp_cup', color, 0.45, 0.6, 0.35)
    body = pr.add(loft('kwp_cup', [(ring(r_bottom), 0.0), (ring(r_top), height)], m)); so = body.modifiers.new('t', 'SOLIDIFY'); so.thickness = 0.0006
    rim = pr.add(ring_tube('kwp_cup_rim', [(x, y, height) for x, y in ring(r_top + 0.0005)], 0.0015, m))
    if lid:
        lm = plastic('kwp_lid', (0.97, 0.97, 0.97), 0.3, 0.4, 0.5)
        ld = pr.add(L.cyl('kwp_lid', r_top + 0.002, 0.004, (0, 0, height + 0.002), lm, None, verts=48))
        bv = ld.modifiers.new('b', 'BEVEL'); bv.width = 0.0015; bv.segments = 3
        hole = pr.add(L.sphere('kwp_siphole', 1, (r_top * 0.6, 0, height + 0.0041), L.mat('kwp_hole', (0.03, 0.03, 0.03), 0.6), None, 16, 6))
        hole.scale = (0.0035, 0.007, 0.0004)
        pr.pts['hole'] = (r_top * 0.6, 0, height + 0.004)
    if straw:
        sm = L.mat('kwp_straw', (0.85, 0.06, 0.05), 0.3, coat=0.4)
        st = pr.add(L.cyl('kwp_straw', 0.0032, 0.2, (-r_top * 0.25, 0, height + 0.02), sm, None, rot=(0, -8, 0), verts=12))
    return pr


# ===================================================================================== B4 tools
def penlight(c, K=None, length=0.13, **_):
    """penlight 13 cm lying along X: brushed body, pocket clip, black end cap, lens tip at +X that switches on (on 0..1).
    Point 'tip' = lens centre, 'aim' = 1 m along the beam (pairs with fx.beam)."""
    pr = Prop('penlight', c); r = 0.0065; st = brushed('kwp_pen_steel', (0.7, 0.72, 0.75), 0.3)
    body = pr.add(L.cyl('kwp_pen_body', r, length * 0.86, (-length * 0.07, 0, r), st, None, rot=(0, 90, 0), verts=24))
    head = pr.add(L.cyl('kwp_pen_head', r * 1.12, length * 0.14, (length * 0.43, 0, r), st, None, rot=(0, 90, 0), verts=24))
    cap = pr.add(L.cyl('kwp_pen_cap', r * 1.02, 0.012, (-length * 0.5 + 0.006, 0, r), L.mat('kwp_pen_black', (0.02, 0.02, 0.025), 0.35), None, rot=(0, 90, 0), verts=24))
    clip = pr.add(_box('kwp_pen_clip', (length * 0.42, 0.0035, 0.0012), (-length * 0.22, 0, 2 * r + 0.0012), st, None, 0.0005))
    lm, em = L.emis('kwp_pen_lens', (1.0, 0.95, 0.82), 0.0)
    lens = pr.add(L.cyl('kwp_pen_lens', r * 0.85, 0.0015, (length * 0.5 + 0.0006, 0, r), lm, None, rot=(0, 90, 0), verts=24))
    pr.pts['tip'] = (length * 0.5 + 0.002, 0, r); pr.pts['aim'] = (length * 0.5 + 1.0, 0, r)
    def _s(on=0.0, **_): em.inputs['Strength'].default_value = 40.0 * on
    pr._set = _s; return pr


def tweezers(c, K=None, length=0.12, **_):
    """tweezers 12 cm lying flat along X: two thin sprung steel arms joined at -X, tips meeting at +X"""
    pr = Prop('tweezers', c); st = brushed('kwp_tw_steel', (0.8, 0.81, 0.83), 0.22)
    for sgn in (1, -1):
        pts = [V((-length / 2, 0.0, 0.0012)), V((-length / 2 + 0.02, sgn * 0.004, 0.0012)), V((0.0, sgn * 0.0065, 0.0012)), V((length / 2 - 0.012, sgn * 0.0018, 0.0012)), V((length / 2, sgn * 0.0003, 0.0012))]
        a = pr.add(L.tube(f'kwp_tw_arm{sgn}', pts, 0.0011, st, None, 3, radii=[1.6, 1.8, 2.2, 1.2, 0.5])); a.scale = (1, 1, 0.45)
    return pr


def probe(c, K=None, length=0.14, **_):
    """blunt probe 14 cm lying along X: knurled handle, thin shaft, ball tip"""
    pr = Prop('probe', c); st = brushed('kwp_pr_steel', (0.78, 0.79, 0.8), 0.25)
    hm = L.bumpy(L.mat('kwp_pr_knurl', (0.7, 0.71, 0.73), 0.4, 1.0), 900, 0.5, dist=0.0003)
    hl = length * 0.62; r = 0.004
    pr.add(L.cyl('kwp_pr_handle', r, hl, (-length / 2 + hl / 2, 0, r), hm, None, rot=(0, 90, 0), verts=20))
    sl = length - hl - 0.003
    pr.add(L.cyl('kwp_pr_shaft', 0.0011, sl, (-length / 2 + hl + sl / 2, 0, r), st, None, rot=(0, 90, 0), verts=12))
    pr.add(L.sphere('kwp_pr_tip', 0.0022, (length / 2 - 0.002, 0, r), st, None, 16, 8)); pr.pts['tip'] = (length / 2, 0, r)
    return pr


def magnifier(c, K=None, length=0.2, **_):
    """Poly Haven magnifying_glass_01 scaled to `length`, lying flat; its lens is replaced by a real convex glass lens
    (refraction magnifies what is under it - no fake inset)."""
    pr = Prop('magnifier', c); objs = _gltf('magnifying_glass_01')
    o = next(x for x in objs if x.type == 'MESH')
    for x in objs:
        if x is not o: bpy.data.objects.remove(x, do_unlink=True)
    o.parent = None; o.matrix_world = Matrix.Identity(4)
    for sl in o.material_slots:
        if sl.material and 'lense' in sl.material.name:
            m = sl.material.copy(); sl.material = m; nt = m.node_tree; nt.nodes.clear()
            out = nt.nodes.new('ShaderNodeOutputMaterial'); tr = nt.nodes.new('ShaderNodeBsdfTransparent'); nt.links.new(tr.outputs[0], out.inputs[0])
    s = length / 0.272
    # model: ring centre near z=0.205 (handle down to z=0); rotate -90 about X: local +Z -> +Y (ring away, handle toward camera)
    o.matrix_world = Matrix.Rotation(math.radians(-90), 4, 'X') @ Matrix.Scale(s, 4)
    bpy.context.view_layer.update()
    pts = [o.matrix_world @ V(b) for b in o.bound_box]; mnz = min(p.z for p in pts); o.location.z -= mnz
    pr.add(o); bpy.context.view_layer.update()
    lens_y = 0.205 * s; zc = 0.013 * s
    gm = L.mat('kwp_lens', (1, 1, 1), 0.0, trans=1.0); L.bsdf(gm).inputs['IOR'].default_value = 1.52
    ln = pr.add(L.sphere('kwp_lens', 1, (0, lens_y, zc), gm, None, 48, 24)); ln.scale = (0.052 * s, 0.052 * s, 0.009 * s)
    pr.pts['lens'] = (0, lens_y, zc)
    return pr


# ===================================================================================== B5 hand items
def paperclip(c, K=None, length=0.033, color=(0.85, 0.05, 0.04), **_):
    """red paperclip 3.3 cm, 1 mm wire, proper double loop, lying flat"""
    pr = Prop('paperclip', c); s = length / 0.0335; mm = 0.001 * s; pts = []
    def arc(cx, cy, r, a0, a1, n=10):
        for k in range(n + 1): a = math.radians(a0 + (a1 - a0) * k / n); pts.append(V((cx + r * math.cos(a), cy + r * math.sin(a), 0)))
    pts.append(V((8, -2.5, 0))); arc(27.5, 0, 2.5, -90, 90); pts.append(V((4, 2.5, 0))); arc(4, -1, 3.5, 90, 270); pts.append(V((29, -4.5, 0)))
    arc(29, 0, 4.5, -90, 90); pts.append(V((12, 4.5, 0)))
    P = [V(((p.x - 16.75) * mm, p.y * mm, 0.0005 * s)) for p in pts]
    cu = bpy.data.curves.new('kwp_clip', 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = 0.0005 * s; cu.bevel_resolution = 4; cu.use_fill_caps = True
    sp = cu.splines.new('POLY'); sp.points.add(len(P) - 1)
    for q, p in zip(sp.points, P): q.co = (*p, 1)
    o = bpy.data.objects.new('kwp_clip', cu); bpy.context.scene.collection.objects.link(o)
    o.data.materials.append(L.mat('kwp_clip_m', color, 0.3, coat=0.6)); pr.add(o)
    return pr


def pea(c, K=None, d=0.008, **_):
    """pea 8 mm with a sprout: sprout 0..1 grows a green stem to 3 cm (full at 0.75); two leaves unfold from 0.45 to 1"""
    pr = Prop('pea', c); r = d / 2
    pr.add(L.sphere('kwp_pea', r, (0, 0, r), two_tone('kwp_pea_m', (0.32, 0.62, 0.12), (0.42, 0.72, 0.2), 300, 0.35, coat=0.3, bump=0.1), None, 24, 12))
    stm = L.mat('kwp_sprout', (0.55, 0.78, 0.3), 0.5, sss=0.3)
    pts = [V((0.001, 0, d * 0.9)), V((0.003, 0.0, d + 0.006)), V((0.001, 0.0, d + 0.016)), V((-0.002, 0.0, d + 0.024)), V((0.0, 0.0, d + 0.03))]
    st = pr.add(L.tube('kwp_sprout', pts, 0.0007, stm, None, 3)); st.data.bevel_factor_mapping_end = 'SPLINE'; st.data.bevel_factor_end = 0.0
    lm = two_tone('kwp_sleaf', (0.3, 0.65, 0.12), (0.5, 0.8, 0.2), 200, 0.45, sss=0.3, bump=0.1)
    leaves = []
    for sgn in (1, -1):
        lf = pr.add(L.sphere(f'kwp_sleaf{sgn}', 1, (sgn * 0.0035, 0, d + 0.03), lm, None, 12, 6)); lf.scale = (1e-5,) * 3; lf.rotation_euler = (0, sgn * 0.5, 0); leaves.append(lf)
    def _s(sprout=0.0, **_):
        st.data.bevel_factor_end = max(1e-4, min(1.0, sprout / 0.75)); _show(st, sprout > 0.01); k = max(0.0, min(1.0, (sprout - 0.45) / 0.55))
        for lf in leaves: lf.scale = (0.004 * k + 1e-5, 0.0022 * k + 1e-5, 0.0006 * k + 1e-5); _show(lf, k > 0)
    pr._set = _s; _s(0.0); return pr


def ball(c, K=None, d=0.06, color=(0.05, 0.45, 0.8), **_):
    """therapy ball 6 cm, soft rubber; squash 0..1 flattens it on the surface (volume kept)"""
    pr = Prop('ball', c); r = d / 2
    m = L.bumpy(L.mat('kwp_ball', color, 0.55, sss=0.05, coat=0.15), 700, 0.25, dist=0.0003)
    b = pr.add(L.sphere('kwp_ball', r, (0, 0, r), m, None, 40, 20))
    def _s(squash=0.0, **_):
        kz = 1 - 0.45 * squash; kx = 1 / math.sqrt(kz); b.scale = (kx, kx, kz); b.location = (0, 0, r * kz)
    pr._set = _s; return pr


def bulb(c, K=None, length=0.09, color=(0.07, 0.07, 0.075), **_):
    """rubber pressure bulb 9 cm lying along X, valve at -X, short tube from the narrow end"""
    pr = Prop('bulb', c); m = L.bumpy(L.mat('kwp_bulb', color, 0.5, coat=0.2), 500, 0.2, dist=0.0003); R = 0.028
    NU, NV = 32, 20; vs = []; fs = []
    for j in range(NV + 1):
        v = j / NV; x = -length / 2 + length * v; rr = R * math.sin(math.pi * v) ** 0.75 * (1 - 0.35 * v) + 0.005
        for i in range(NU): a = 2 * math.pi * i / NU; vs.append((x, rr * math.cos(a), rr * math.sin(a)))
    for j in range(NV):
        for i in range(NU): fs.append((j * NU + i, j * NU + (i + 1) % NU, (j + 1) * NU + (i + 1) % NU, (j + 1) * NU + i))
    o = pr.add(_mesh('kwp_bulb', vs, fs, m)); o.location.z = R + 0.0005
    st = brushed('kwp_bulb_valve', (0.75, 0.76, 0.78), 0.3)
    pr.add(L.cyl('kwp_bulb_valve', 0.006, 0.012, (-length / 2 - 0.004, 0, R + 0.0005), st, None, rot=(0, 90, 0), verts=16))
    tm = L.mat('kwp_bulb_tube', (0.08, 0.08, 0.085), 0.45)
    pts = [V((length / 2, 0, R)), V((length / 2 + 0.02, 0.002, R - 0.004)), V((length / 2 + 0.04, 0.008, 0.008)), V((length / 2 + 0.06, 0.012, 0.004))]
    pr.add(L.tube('kwp_bulb_tube', pts, 0.0035, tm, None, 4))
    return pr


# ===================================================================================== B3 bench / tabletop
def bench(c, K=None, top=(1.2, 0.6), h=0.9, style='grey', floor=True, **_):
    """plain demo bench: top 120 x 60 cm at 90 cm, matte light grey, 1 cm rounded edge, slight grain (style='grey');
    style='table': varnished wood (ep08 dining table, use h=0.75).  floor=True adds a shadow-catcher floor (no floating legs).
    Point 'top' = centre of the top surface."""
    pr = Prop('bench_' + style, c); w, d = top; tt = 0.035
    if style == 'table':
        import kwsets; m = kwsets.wood('kwp_table', (0.5, 0.31, 0.16), 6.0, planks=True); legm = m
    else:
        m = L.mat('kwp_bench', (0.48, 0.49, 0.5), 0.7); nt, N, Lk, b = _nodes(m)
        tc = N.new('ShaderNodeTexCoord'); mp = N.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (4, 60, 60); Lk(tc.outputs['Object'], mp.inputs['Vector'])
        nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 6.0; nz.inputs['Detail'].default_value = 8; Lk(mp.outputs[0], nz.inputs['Vector'])
        mx = N.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.inputs['Factor'].default_value = 0.08; mx.inputs[6].default_value = (0.48, 0.49, 0.5, 1); Lk(nz.outputs['Color'], mx.inputs[7]); Lk(mx.outputs[2], b.inputs['Base Color'])
        bp = N.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.06; bp.inputs['Distance'].default_value = 0.0004; Lk(nz.outputs['Fac'], bp.inputs['Height']); Lk(bp.outputs['Normal'], b.inputs['Normal'])
        legm = L.mat('kwp_bench_leg', (0.25, 0.26, 0.28), 0.4, 0.8)
    pr.add(_box('kwp_bench_top', (w, d, tt), (0, 0, h - tt / 2), m, None, 0.01))
    for sx in (-1, 1):
        for sy in (-1, 1):
            pr.add(_box('kwp_bench_leg', (0.04, 0.04, h - tt), (sx * (w / 2 - 0.06), sy * (d / 2 - 0.06), (h - tt) / 2), legm, None, 0.004))
    if floor:
        fl = pr.add(_box('kwp_floor_catcher', (8, 8, 0.01), (0, 0, -0.005), L.mat('kwp_floor', (0.5, 0.5, 0.5), 0.8), None, 0)); fl.is_shadow_catcher = True
    pr.pts['top'] = (0, 0, h)
    return pr


def make(kind, c, K=None, **params):
    if kind not in KINDS: raise ValueError(f'item kind {kind!r}: one of {", ".join(KINDS)}')
    return globals()[kind](c, K, **params)
