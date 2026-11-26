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
         'paperclip', 'pea', 'ball', 'bulb', 'bench', 'sweet_potato', 'beans', 'ketchup', 'fork', 'bar',
         'kidney_dish', 'sprout', 'lens_arm', 'xray_screen', 'scope', 'peas')
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
    if o.get('kw_off', False) != h: o['kw_off'] = h      # read by kwfx for hand-carried items (their visibility follows the root)


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


def tray(c, K=None, style='meal', w=None, d=None, h=None, r=None, color=None, liner=None, ao=False, **_):
    """meal tray 45x35 cm, rim 1.5 cm, corner r 3 cm, matte plastic (color) | clinic tray 30x20x2 cm brushed steel, rolled rim.
    liner: None | 'paper' | 'cloth' (Fabric030) lying inside.  Point 'floor' = top of the tray floor (place food there)."""
    P = TRAY[style]; w = w or P['w']; d = d or P['d']; h = h or P['h']; r = r or P['r']; col = color or P['col']
    pr = Prop('tray_' + style, c)
    m = plastic('kwp_tray_' + style, col, 0.5) if P['mat'] == 'plastic' else brushed('kwp_tray_steel')
    if ao: m = m.copy(); m.name = f'kwp_tray_{style}_{len(bpy.data.materials)}'; _contact_ao(m, 0.02, 0.5)
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
def burger(c, K=None, width=0.11, height=0.06, bite_side=225.0, cheese_at=None, bites=None, bite_r=0.021, sym=False, droop2=False, lettuce=None,
           proud=0.0, nseeds=46, **_):
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
    if proud:      # ep08: patty proud of the bun front and back (x stays at the bun edge: the palms sit there)
        pat.scale = ((width / 2 + 0.001) / (width * 0.49), (width / 2 + proud) / (width * 0.49), 1.0)
    ss = pat.modifiers.new('s', 'SUBSURF'); ss.levels = ss.render_levels = 2; _noise_disp(pat, 0.0025, 0.012, 'kwp_patty_n'); z += hp
    # cheese: square slice rotated 45, corners droop (one more), lettuce frill under it
    N = 16; s = width * 0.42; vs = []; fs = []
    for j in range(N + 1):
        for i in range(N + 1):
            x = -s + 2 * s * i / N; y = -s + 2 * s * j / N; rr = math.hypot(x, y); dz = -max(0.0, rr - width * 0.48) * 0.5
            if x > s * 0.55 and y > s * 0.55: dz -= ((x - s * 0.55) + (y - s * 0.55)) * 0.55     # the drooping corner
            if droop2 and x < -s * 0.55 and y < -s * 0.55: dz -= ((-x - s * 0.55) + (-y - s * 0.55)) * 0.55     # ep08: the opposite corner too (180-deg symmetric)
            vs.append((x, y, dz))
    for j in range(N):
        for i in range(N): fs.append((j * (N + 1) + i, j * (N + 1) + i + 1, (j + 1) * (N + 1) + i + 1, (j + 1) * (N + 1) + i))
    ch = _mesh('kwp_cheese', vs, fs, L.mat('kwp_cheese_m', (0.95, 0.55, 0.06), 0.35, sss=0.2, coat=0.2))
    ch.rotation_euler = (0, 0, math.radians(bite_side + 20 if cheese_at is None else cheese_at - 45))   # drooping corner ~65 deg round from the bitten side (or at cheese_at deg from +X)
    ch.location = (0, 0, z + hc * 0.5); so = ch.modifiers.new('t', 'SOLIDIFY'); so.thickness = hc
    z += hc
    lv = []; lf = []; NA, NR = 96, 4
    for j in range(NR + 1):
        rr = width * (0.40 + 0.17 * j / NR)
        for i in range(NA):
            a = 2 * math.pi * i / NA; wv = (math.sin(a * 14) * 0.6 + math.sin(a * 8 + 1) * 0.4) if sym else (math.sin(a * 13) * 0.6 + math.sin(a * 7 + 1) * 0.4)
            lv.append((rr * math.cos(a) * (1 + 0.04 * wv * j / NR), rr * math.sin(a) * (1 + 0.04 * wv * j / NR), 0.0025 * wv * (j / NR) - 0.006 * (j / NR) ** 2))
    for j in range(NR):
        for i in range(NA): lf.append((j * NA + i, j * NA + (i + 1) % NA, (j + 1) * NA + (i + 1) % NA, (j + 1) * NA + i))
    lc0, lc1 = lettuce or ((0.25, 0.6, 0.1), (0.55, 0.8, 0.25))
    let = _mesh('kwp_lettuce', lv, lf, two_tone('kwp_lettuce_m' + ('_g' if lettuce else ''), lc0, lc1, 60, 0.45, sss=0.2, bump=0.3))
    let.location = (0, 0, z - hc - 0.0005); so = let.modifiers.new('t', 'SOLIDIFY'); so.thickness = 0.0008
    z += hl
    top.scale = (sx, sx, kz); top.location = (0, 0, z - zt * kz)
    # sesame seeds on the crown (ray cast down onto the evaluated crown)
    bpy.context.view_layer.update(); seed_m = L.mat('kwp_sesame', (0.93, 0.85, 0.62), 0.5); rnd = random.Random(11)
    dg = bpy.context.evaluated_depsgraph_get(); Mi = top.matrix_world.inverted(); seeds = []
    if sym:      # ep08: whole-burger 180-deg symmetry (the return turns it in the hands; last frame = frame 0)
        for o in (bun, top, pat):
            mm = o.modifiers.new('sym', 'MIRROR'); mm.use_axis = (True, True, False); mm.use_bisect_axis = (True, True, False); mm.use_clip = True
        bpy.context.view_layer.update(); dg = bpy.context.evaluated_depsgraph_get()
    seedpts = []
    for k in range(nseeds):
        a = rnd.uniform(0, 2 * math.pi); rr = width * 0.40 * math.sqrt(rnd.random()); seedpts.append((a, rr))
        if sym: seedpts.append((a + math.pi, rr))
    for a, rr in seedpts:
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
    R = width / 2; cuts = []
    if bites is not None:
        # ep08: crescent bites (bite_r) side by side along one arc; every part gets its own cutter carrying its own cut-face
        # material (TRANSFER), so the cut shows bun crumb / lettuce / cheese / patty layers, never a flat grey face
        cutm = {id(bun): crumb, id(top): crumb, id(pat): patty_m, id(ch): ch.data.materials[0], id(let): let.data.materials[0]}
        for k, (da, fr) in enumerate(bites):
            a = math.radians(bite_side + da); mods = []; cus = []
            for o in parts:
                cu = L.cyl(f'kwp_bite{k}_{o.name}', bite_r, height * 3, (R * fr * math.cos(a), R * fr * math.sin(a), height / 2), cutm[id(o)], None, verts=40)
                pr.add(cu); md = _bool_cut([o], cu, f'bite{k}')[0]
                try: md.material_mode = 'TRANSFER'
                except Exception: pass
                mods.append(md); cus.append(cu)
            cuts.append((mods, cus, cu.location.copy()))
        sxy = [(sd, sd.location.copy()) for sd in seeds]     # seed positions at build = prop-local (root at the origin)
        def _s(eaten=0.0, gone=None, **_):
            g = gone if gone is not None else eaten * len(cuts) / 0.96
            act = []
            for k, (mods, cus, ctr) in enumerate(cuts):
                pk = max(0.0, min(1.0, g - k)); pk = pk * pk * (3 - 2 * pk)
                for md in mods: md.show_render = md.show_viewport = pk > 1e-3
                for cu in cus: cu.scale = (max(pk, 1e-3), max(pk, 1e-3), 1.0)
                if pk > 1e-3: act.append((ctr, bite_r * pk + 0.001))
            for sd, q in sxy: _show(sd, not any(math.hypot(q.x - c_.x, q.y - c_.y) < bite_r + 0.002 for _m, _c, c_ in cuts))   # ep08: no seeds on any bite area, ever (the whole-bun swap changes no seed)
        pr._set = _s; _s(0.0); return pr
    rb = 0.0185
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
    _fadeable(fm)
    def _s(eaten=0.0, gone=None, **_):
        if gone is None:
            gone = int(round(eaten * count))
            for k, i in enumerate(order): _show(sticks[i], k >= gone)
            return
        for k, i in enumerate(order): _fade_piece(sticks[i], gone - k)
    pr._set = _s; return pr


def salmon(c, K=None, size=(0.12, 0.06, 0.025), brown=False, lemon=False, **_):
    """salmon fillet 12 x 6 x 2.5 cm: orange-pink, pale fat lines, glossy top; eaten 0..1 = forkfuls from the +X end"""
    pr = Prop('salmon', c); lx, ly, lz = size; NU, NV = 32, 10; vs = []; fs = []
    for j in range(NV + 1):
        v = j / NV; sc = 1 - (0.12 if brown else 0.38) * v ** 2.2  # domed: the outline pulls in toward the top (ep08 fillet: flat-topped slab)
        for i in range(NU):
            a = 2 * math.pi * i / NU; ca, sa = math.cos(a), math.sin(a)
            if brown: ca, sa = math.copysign(abs(ca) ** 0.45, ca), math.copysign(abs(sa) ** 0.45, sa)   # boxy outline (superellipse), a cut fillet
            u = ca; x = lx / 2 * u * sc
            y = ly / 2 * sa * sc * (1 - (0.15 if brown else 0.35) * max(0.0, u) ** 2)      # tail end (+X) narrower
            hz = lz * (1 - 0.45 * max(0.0, u) ** 2)                         # and thinner
            vs.append((x, y, hz * math.sin(v * math.pi / 2)))
    for j in range(NV):
        for i in range(NU): fs.append((j * NU + i, j * NU + (i + 1) % NU, (j + 1) * NU + (i + 1) % NU, (j + 1) * NU + i))
    fs.append(tuple(reversed(range(NU)))); fs.append(tuple(range(NV * NU, (NV + 1) * NU)))
    m = L.mat('kwp_salmon', (0.87, 0.23, 0.10) if brown else (0.85, 0.30, 0.16), 0.42 if brown else 0.35, coat=0.08 if brown else 0.45, sss=0.05 if brown else 0.15); nt, N, Lk, b = _nodes(m)
    tc = N.new('ShaderNodeTexCoord'); wv = N.new('ShaderNodeTexWave'); wv.inputs['Scale'].default_value = 9.0; wv.inputs['Distortion'].default_value = 2.0
    mp = N.new('ShaderNodeMapping'); mp.inputs['Rotation'].default_value = (0, 0, 0.6); mp.inputs['Scale'].default_value = (14, 14, 14); Lk(tc.outputs['Object'], mp.inputs['Vector']); Lk(mp.outputs[0], wv.inputs['Vector'])
    cr = N.new('ShaderNodeValToRGB'); cr.color_ramp.elements[0].position = 0.93 if brown else 0.86; cr.color_ramp.elements[0].color = ((0.98, 0.33, 0.07, 1) if brown else (0.85, 0.30, 0.16, 1)); cr.color_ramp.elements[1].position = 0.975 if brown else 0.95; cr.color_ramp.elements[1].color = (0.98, 0.72, 0.58, 1)
    Lk(wv.outputs['Fac'], cr.inputs['Fac']); Lk(cr.outputs['Color'], b.inputs['Base Color'])
    o = _mesh('kwp_salmon', vs, fs, m); ss = o.modifiers.new('s', 'SUBSURF'); ss.levels = ss.render_levels = 1
    _noise_disp(o, 0.0012, 0.01, 'kwp_salmon_n'); pr.add(o)
    if brown:      # ep08 (CHECK 2 fix 3): clear salmon orange-pink (#F0845C) with 4 thin pale diagonal fat lines across the top
        so_ = N.new('ShaderNodeSeparateXYZ'); Lk(tc.outputs['Object'], so_.inputs[0])
        d1 = N.new('ShaderNodeMath'); d1.operation = 'MULTIPLY_ADD'; Lk(so_.outputs['X'], d1.inputs[0]); d1.inputs[1].default_value = 0.8; Lk(so_.outputs['Y'], d1.inputs[2])
        d2 = N.new('ShaderNodeMath'); d2.operation = 'MULTIPLY'; Lk(d1.outputs[0], d2.inputs[0]); d2.inputs[1].default_value = 1.0 / 0.034   # a line every 3.4 cm
        fr = N.new('ShaderNodeMath'); fr.operation = 'PINGPONG'; Lk(d2.outputs[0], fr.inputs[0]); fr.inputs[1].default_value = 0.5
        ln = N.new('ShaderNodeMapRange'); ln.inputs[1].default_value = 0.035; ln.inputs[2].default_value = 0.075; ln.inputs[3].default_value = 1.0; ln.inputs[4].default_value = 0.0; Lk(fr.outputs[0], ln.inputs['Value'])
        mx = N.new('ShaderNodeMix'); mx.data_type = 'RGBA'; Lk(ln.outputs[0], mx.inputs['Factor']); mx.inputs[6].default_value = (0.87, 0.23, 0.10, 1); mx.inputs[7].default_value = (0.96, 0.66, 0.52, 1)
        Lk(mx.outputs[2], b.inputs['Base Color'])
    rnd = random.Random(8); cuts = []
    for k in range(6):
        x = lx / 2 + 0.006 - k * lx * 0.15; cu = L.sphere(f'kwp_fork{k}', 0.016 + 0.003 * rnd.random(), (x, rnd.uniform(-0.01, 0.01), lz * 1.05), None, None, 20, 10)
        cu.scale = (0.9, 1.6, 1.0); pr.add(cu); cuts.append(_bool_cut([o], cu, f'fork{k}'))
    if lemon:
        _lemon(pr, (-lx * 0.18, ly * 0.05, lz * 0.98))
    sc0 = [cu.scale.copy() for cu in [m_.object for m_s in cuts for m_ in m_s]]
    def _s(eaten=0.0, gone=None, **_):
        for k, mods in enumerate(cuts):
            if gone is None: pk = 1.0 if eaten >= 0.05 + 0.15 * k else 0.0
            else: pk = max(0.0, min(1.0, gone - k)); pk = pk * pk * (3 - 2 * pk)
            for md in mods: md.show_render = md.show_viewport = pk > 1e-3; md.object.scale = sc0[k] * max(pk, 1e-3)
        _show(o, (eaten if gone is None else 0.0) < 0.96)
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
def bench(c, K=None, top=(1.2, 0.6), h=0.9, style='grey', floor=True, soft=False, wood=None, **_):
    """plain demo bench: top 120 x 60 cm at 90 cm, matte light grey, 1 cm rounded edge, slight grain (style='grey');
    style='table': varnished wood (ep08 dining table, use h=0.75).  floor=True adds a shadow-catcher floor (no floating legs).
    Point 'top' = centre of the top surface."""
    pr = Prop('bench_' + style, c); w, d = top; tt = 0.035
    if style == 'table':
        import kwsets; m = kwsets.wood('kwp_table', wood or (0.5, 0.31, 0.16), 6.0, planks=True, contrast=(0.82, 1.12) if soft else None); legm = m
        if soft: _contact_ao(m, 0.035, 0.45)
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


# ===================================================================================== ep08: fades, new food, bars
def _contact_ao(m, dist=0.03, dark=0.5):
    """contact shadow: base colour darkened by Cycles AO within `dist` (a soft dark line where things meet the surface)"""
    nt = m.node_tree; N = nt.nodes; b = N['Principled BSDF']; sock = b.inputs['Base Color']
    ao = N.new('ShaderNodeAmbientOcclusion'); ao.inputs['Distance'].default_value = dist; ao.samples = 8
    mr = N.new('ShaderNodeMapRange'); mr.inputs[3].default_value = dark; mr.inputs[4].default_value = 1.0; nt.links.new(ao.outputs['AO'], mr.inputs['Value'])
    mul = N.new('ShaderNodeMix'); mul.data_type = 'RGBA'; mul.blend_type = 'MULTIPLY'; mul.inputs['Factor'].default_value = 1.0
    if sock.links: nt.links.new(sock.links[0].from_socket, mul.inputs[6])
    else: mul.inputs[6].default_value = sock.default_value
    nt.links.new(mr.outputs[0], mul.inputs[7]); nt.links.new(mul.outputs[2], sock); return m


def _fadeable(m):
    """mix the material toward transparent by the object's colour alpha (obj.color[3]): per-piece 3-frame fade-outs"""
    if m.get('kw_fade'): return m
    nt = m.node_tree; N = nt.nodes; out = next(n for n in N if n.type == 'OUTPUT_MATERIAL'); src = out.inputs['Surface'].links[0].from_socket
    oi = N.new('ShaderNodeObjectInfo'); tr = N.new('ShaderNodeBsdfTransparent'); mx = N.new('ShaderNodeMixShader')
    nt.links.new(oi.outputs['Alpha'], mx.inputs[0]); nt.links.new(tr.outputs[0], mx.inputs[1]); nt.links.new(src, mx.inputs[2]); nt.links.new(mx.outputs[0], out.inputs['Surface'])
    m['kw_fade'] = 1; return m


def _fade_piece(o, p):
    """p = 0 (whole) .. 1 (gone): 3-frame fade with a 10 % shrink (never a hard pop)"""
    p = max(0.0, min(1.0, p)); e = p * p * (3 - 2 * p)
    if 's0' not in o: o['s0'] = tuple(o.scale)
    s0 = o['s0']; k = 1.0 - 0.1 * e; o.scale = (s0[0] * k, s0[1] * k, s0[2] * k)
    o.color = (1.0, 1.0, 1.0, 1.0 - e); _show(o, p < 0.999)


def _lemon(pr, loc):
    """lemon wedge ~6 cm lying on its peel: pale yellow flesh face up, bright peel"""
    peel = L.mat('kwp_lemon_peel', (0.95, 0.78, 0.08), 0.4, coat=0.3); flesh = two_tone('kwp_lemon', (0.98, 0.9, 0.45), (0.92, 0.82, 0.3), 90, 0.35, sss=0.3, bump=0.2)
    NU = 16; vs = []; fs = []; ln, r = 0.06, 0.016
    for i in range(NU + 1):
        u = i / NU; x = ln * (u - 0.5); rr = r * math.sin(math.pi * u) ** 0.7 + 0.001
        for j in range(9):
            a = math.pi * (j / 8); vs.append((x, rr * math.cos(a), rr * math.sin(a) * 0.9))
    for i in range(NU):
        for j in range(8): fs.append((i * 9 + j, (i + 1) * 9 + j, (i + 1) * 9 + j + 1, i * 9 + j + 1))
    o = _mesh('kwp_lemon', vs, fs, peel); fl = []
    for i in range(NU): fl.append((i * 9, i * 9 + 8, (i + 1) * 9 + 8, (i + 1) * 9))
    o.data.materials.append(flesh); bm = bmesh.new(); bm.from_mesh(o.data); bm.verts.ensure_lookup_table()
    for f in fl:
        try: nf = bm.faces.new([bm.verts[k] for k in f]); nf.material_index = 1
        except ValueError: pass
    bm.to_mesh(o.data); bm.free()
    o.rotation_euler = (math.radians(180), 0, math.radians(25)); o.location = (loc[0], loc[1], loc[2] + r * 0.9); pr.add(o); return o


def sweet_potato(c, K=None, length=0.14, **_):
    """baked sweet potato 14 cm: brown wrinkled skin, split open along the top showing bright orange flesh; gone = forkful notches"""
    pr = Prop('sweet_potato', c); rnd = random.Random(41); NU, NV = 40, 20; vs = []; fs = []; R0 = 0.03
    skin = two_tone('kwp_spot_skin', (0.20, 0.055, 0.025), (0.27, 0.075, 0.035), 40, 0.6, bump=0.5)     # #8A4B32 (ep08 CHECK 2 fix 3)
    for j in range(NV + 1):
        v = j / NV; x = length * (v - 0.5); prof = math.sin(math.pi * (0.04 + 0.92 * v)) ** 0.75
        for i in range(NU):
            a = 2 * math.pi * i / NU; w = 1 + 0.05 * math.sin(3 * a + 5 * v) + 0.04 * math.sin(7 * v + 2 * a)
            vs.append((x, R0 * prof * w * math.cos(a), R0 * 0.85 * prof * w * math.sin(a) + R0 * 0.8 * prof))
    for j in range(NV):
        for i in range(NU): fs.append((j * NU + i, j * NU + (i + 1) % NU, (j + 1) * NU + (i + 1) % NU, (j + 1) * NU + i))
    o = _mesh('kwp_spot', vs, fs, skin); ss = o.modifiers.new('s', 'SUBSURF'); ss.levels = ss.render_levels = 1; pr.add(o)
    flesh = two_tone('kwp_spot_flesh', (0.85, 0.20, 0.008), (0.89, 0.26, 0.015), 60, 0.5, bump=0.3)   # #F28C28
    # the split: a groove box cut along the top, the flesh mound fills it and bulges out
    gv = L.cyl('kwp_spot_split', 1, 1, (0, 0, 0), None, None, verts=24); gv.scale = (0.045, 0.010, 0.03); gv.location = (0, 0, 0.048 + 0.015 - 0.007)    # narrow 9 x 2 cm slit (ep08 lead spec)
    pr.add(gv); _bool_cut([o], gv, 'split')[0].show_render = True; o.modifiers['split'].show_viewport = True
    fm = L.sphere('kwp_spot_mash', 1, (0, 0, 0.046 - 0.012), flesh, None, 32, 16); fm.scale = (0.044, 0.0098, 0.012); _noise_disp(fm, 0.001, 0.008, 'kwp_spot_n')   # flesh top ~2 mm below the skin edge; pr.add(fm)
    cuts = []
    for k in range(4):
        x = length * 0.22 - k * length * 0.11; cu = L.sphere(f'kwp_spotfork{k}', 1, (x, 0.004 * (-1) ** k, R0 * 1.75), None, None, 20, 10); cu.scale = (0.015, 0.012, 0.014)
        pr.add(cu); cuts.append(_bool_cut([fm, o], cu, f'spf{k}'))
    sc0 = [m_[0].object.scale.copy() for m_ in cuts]
    def _s(gone=0.0, **_):
        for k, mods in enumerate(cuts):
            pk = max(0.0, min(1.0, gone - k)); pk = pk * pk * (3 - 2 * pk)
            for md in mods: md.show_render = md.show_viewport = pk > 1e-3
            mods[0].object.scale = sc0[k] * max(pk, 1e-3)
    pr._set = _s; _s(0.0); return pr


def beans(c, K=None, count=14, **_):
    """a heap of green beans 10-12 cm, saturated glossy green; gone = pairs of beans faded out (top first)"""
    pr = Prop('beans', c); rnd = random.Random(51); items = []
    m = _fadeable(two_tone('kwp_bean', (0.10, 0.42, 0.04), (0.18, 0.55, 0.06), 70, 0.32, coat=0.35, sss=0.1, bump=0.15))
    for k in range(count):
        ln = rnd.uniform(0.10, 0.12); bend = rnd.uniform(-0.012, 0.012); pts = []
        for i in range(7):
            u = i / 6; pts.append((ln * (u - 0.5), bend * math.sin(math.pi * u), 0.0))
        o = L.tube(f'kwp_bean{k}', pts, 0.0042, m, None, 4, radii=[0.45, 0.9, 1, 1, 1, 0.9, 0.4])
        layer = k // 5; o.location = (rnd.uniform(-0.012, 0.012), -0.022 + 0.011 * (k % 5) + rnd.uniform(-0.003, 0.003), 0.0042 + 0.0075 * layer)
        o.rotation_euler = (0, rnd.uniform(-0.05, 0.05), math.radians(rnd.uniform(-14, 14))); items.append(pr.add(o))
    order = list(reversed(items))
    def _s(gone=0.0, **_):
        for k, o in enumerate(order): _fade_piece(o, gone - k // 2)
    pr._set = _s; _s(0.0); return pr


def ketchup(c, K=None, d=0.05, **_):
    """5 cm white pleated paper cup with a glossy red fill"""
    pr = Prop('ketchup', c); n = 48; h = 0.03
    ring = lambda r, f: [(r * (1 + f * math.cos(16 * 2 * math.pi * i / n)) * math.cos(2 * math.pi * i / n), r * (1 + f * math.cos(16 * 2 * math.pi * i / n)) * math.sin(2 * math.pi * i / n)) for i in range(n)]
    pm = L.mat('kwp_kcup', (0.93, 0.93, 0.9), 0.75, sss=0.05)
    cu = pr.add(loft('kwp_kcup', [(ring(d * 0.38, 0.012), 0.0), (ring(d / 2, 0.02), h)], pm)); so = cu.modifiers.new('t', 'SOLIDIFY'); so.thickness = 0.0005
    fill = pr.add(L.cyl('kwp_kfill', d * 0.47, 0.004, (0, 0, h - 0.005), L.mat('kwp_ketchup', (0.55, 0.02, 0.01), 0.12, coat=0.8), None, verts=40))
    sp = pr.add(L.sphere('kwp_kdome', 1, (0, 0, h - 0.003), fill.data.materials[0], None, 24, 8)); sp.scale = (d * 0.46, d * 0.46, 0.003)
    return pr


def fork(c, K=None, length=0.19, **_):
    """steel table fork lying flat (handle toward -X)"""
    pr = Prop('fork', c); m = brushed('kwp_fork', (0.8, 0.81, 0.83), 0.22)
    h = pr.add(_box('kwp_fork_handle', (0.12, 0.014, 0.003), (-0.035, 0, 0.004), m, None, 0.0012)); h.rotation_euler = (0, math.radians(-3), 0)
    pr.add(_box('kwp_fork_neck', (0.03, 0.008, 0.0025), (0.04, 0, 0.007), m, None, 0.001))
    pr.add(_box('kwp_fork_head', (0.02, 0.024, 0.002), (0.062, 0, 0.0085), m, None, 0.0008))
    for k in range(4):
        pr.add(_box(f'kwp_fork_tine{k}', (0.028, 0.0032, 0.0018), (0.084, -0.0105 + 0.007 * k, 0.0095), m, None, 0.0006))
    return pr


def bar(c, K=None, w=0.04, h=0.34, notches=16, color=(1.0, 0.82, 0.02), bracket=None, **_):
    """ep08: plain upright bar frame standing on the table (a drawing of 'more', never a number): thin dark outline,
    yellow fill from the bottom.  fill = notches filled (float; one notch = h / notches); alpha 0..1 fades the whole bar.
    bracket = (dx, n_hi, n_lo): yellow bracket from this bar's top at n_hi notches toward the other bar dx metres away
    along +X (its top at n_lo): a line from each bar top to the middle joined by a vertical stroke; br 0..1 draws it."""
    pr = Prop('bar', c); t = 0.003; dpt = 0.012
    dk = _fadeable(L.mat('kwp_bar_frame', (0.04, 0.04, 0.05), 0.5)); fm = _fadeable(L.mat('kwp_bar_fill', color, 0.45, emit=color, es=0.35))
    bk = _fadeable(L.mat('kwp_bar_back', (0.5, 0.52, 0.55), 0.7))
    for nm, sz, lc in (('l', (t, dpt, h), (-w / 2 + t / 2, 0, h / 2)), ('r', (t, dpt, h), (w / 2 - t / 2, 0, h / 2)),
                       ('t', (w, dpt, t), (0, 0, h - t / 2)), ('b', (w, dpt, t), (0, 0, t / 2))):
        pr.add(_box('kwp_bar_' + nm, sz, lc, dk, None, 0.0008))
    pr.add(_box('kwp_bar_back', (w - 2 * t, 0.002, h - 2 * t), (0, dpt / 2 - 0.001, h / 2), bk, None, 0))
    fl = pr.add(_box('kwp_bar_fill', (w - 2 * t - 0.001, dpt - 0.002, 1.0), (0, 0, 0), fm, None, 0)); fl.location = (0, 0, t)
    hin = h - 2 * t; segs = []
    if bracket:
        dx, nh, nl = bracket; zh = t + hin * nh / notches; zl = t + hin * nl / notches; xm = dx / 2; bt = 0.004
        for nm, (x0, z0, x1, z1) in (('a', (w / 2 + 0.01, zh, xm, zh)), ('v', (xm, zh, xm, zl)), ('b', (dx - w / 2 - 0.01, zl, xm, zl))):
            o = pr.add(_box('kwp_brk_' + nm, (1.0, 0.004, 1.0), (0, 0, 0), fm, None, 0)); segs.append((o, V((x0, 0, z0)), V((x1, 0, z1)), bt))
    def _s(fill=0.0, alpha=1.0, br=0.0, **_):
        z = max(1e-4, hin * min(notches, max(0.0, fill)) / notches); fl.scale = (1, 1, z); fl.location = (0, 0, t + z / 2)
        for o in pr.objs:
            o.color = (1, 1, 1, alpha); _show(o, alpha > 0.01 and (o is not fl or fill > 1e-3))
        for k_, (o, a, b, th) in enumerate(segs):       # drawn in order: both horizontals together, then the vertical
            pk = max(0.0, min(1.0, br * 2 if k_ != 1 else br * 2 - 1)); e = b if pk >= 1 else a.lerp(b, pk)
            d = e - a; L_ = max(1e-4, d.length); o.location = (a + e) / 2
            o.scale = (L_ + (th if pk > 0 else 0), 1, th) if abs(d.z) < 1e-6 else (th, 1, L_ + th)
            _show(o, alpha > 0.01 and pk > 1e-3)
    pr._set = _s; _s(0.0); return pr

# ===================================================================================== ep09 pea lung (kidney dish, sprout, lens arm, X-ray screen, scope, peas)
def _hexlin(h):
    """sRGB hex -> linear rgb"""
    c = [int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)


def kidney_dish(c, K=None, w=0.25, d=0.12, h=0.03, gauze=True, **_):
    """brushed-steel kidney dish w x d x h (concave side toward +Y) with a folded 8 x 8 cm gauze square on its floor.
    Point 'gauze' = centre of the gauze top."""
    pr = Prop('kidney_dish', c); n = 72
    def outline(s):
        pts = []
        for i in range(n):
            a = 2 * math.pi * i / n; ca, sa = math.cos(a), math.sin(a)
            y = 0.5 * d * sa - 0.30 * d * math.exp(-(ca / 0.45) ** 2) * max(0.0, sa)
            pts.append((s * 0.5 * w * ca, s * (y + 0.06 * d)))
        return pts
    st = brushed('kwp_kd_steel', (0.62, 0.63, 0.65), 0.42)
    o = pr.add(loft('kwp_kd', [(outline(0.80), 0.0015), (outline(0.90), 0.010), (outline(0.97), 0.022), (outline(1.0), h)], st))
    sd = o.modifiers.new('sd', 'SOLIDIFY'); sd.thickness = 0.0012; sd.offset = 1.0
    top = [(x, y, h) for x, y in outline(1.0)]
    pr.add(ring_tube('kwp_kd_rim', top, 0.0022, st)); _contact_ao(st, 0.02, 0.6)
    pr.pts['gauze'] = (0, 0, 0.0015)
    if gauze:
        gm = L.mat('kwp_gauze', (0.56, 0.56, 0.535), 0.85, sss=0.02); nt, N, Lk, b = _nodes(gm)
        tc = N.new('ShaderNodeTexCoord'); ws = []
        for ax in ('X', 'Y'):
            wv = N.new('ShaderNodeTexWave'); wv.wave_type = 'BANDS'; wv.bands_direction = ax; wv.inputs['Scale'].default_value = 1.6; wv.inputs['Distortion'].default_value = 0.4
            mp = N.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (110, 110, 110); Lk(tc.outputs['Object'], mp.inputs['Vector']); Lk(mp.outputs[0], wv.inputs['Vector']); ws.append(wv)
        mx = N.new('ShaderNodeMath'); mx.operation = 'MULTIPLY'; Lk(ws[0].outputs['Fac'], mx.inputs[0]); Lk(ws[1].outputs['Fac'], mx.inputs[1])
        bp = N.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.35; bp.inputs['Distance'].default_value = 0.0003; Lk(mx.outputs[0], bp.inputs['Height']); Lk(bp.outputs['Normal'], b.inputs['Normal'])
        rnd = random.Random(9); G_ = 28; vs = []; fs = []
        for j in range(G_ + 1):
            for i in range(G_ + 1):
                x = -0.04 + 0.08 * i / G_; y = -0.04 + 0.08 * j / G_
                z = 0.0006 * math.sin(x * 90 + 1.0) * math.sin(y * 70) + rnd.uniform(-0.00015, 0.00015)
                if x > 0.025: z += 0.0018 * min(1.0, (x - 0.025) / 0.012)        # a soft folded edge on one side
                vs.append((x, y, z))
        for j in range(G_):
            for i in range(G_): fs.append((j * (G_ + 1) + i, j * (G_ + 1) + i + 1, (j + 1) * (G_ + 1) + i + 1, (j + 1) * (G_ + 1) + i))
        g = pr.add(_mesh('kwp_gauze', vs, fs, gm)); g.location.z = 0.0036      # ep09 CHECK 2: 2.1 mm let the dish floor poke through (grey flakes)
        sg = g.modifiers.new('sd', 'SOLIDIFY'); sg.thickness = 0.0015; sg.offset = -1.0
        pr.pts['gauze'] = (0, 0, 0.0036 + 0.0006)
    return pr


def sprout(c, K=None, scale=1.0, **_):
    """sprouted pea lying on its side, total ~13 mm: seed 7 mm split along its top (two halves gaping a little, paler inside),
    a cream root tip 4 mm out of the -X end, a pale green shoot 5 mm out of the +X end with two tiny folded leaves.
    Point 'mid' = centre of the seed."""
    pr = Prop('sprout', c); mm = 0.001 * scale; r = 3.5 * mm
    seed = two_tone('kwp_sp_seed', _hexlin('9DB86A'), tuple(0.82 * x for x in _hexlin('9DB86A')), 900 / scale, 0.5, coat=0.05, sss=0.08, bump=0.9)
    inner = two_tone('kwp_sp_inner', _hexlin('EADFA0'), _hexlin('D8CC80'), 1400 / scale, 0.55, sss=0.1, bump=0.1)
    for sg in (1, -1):
        bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=40, v_segments=20, radius=1.0)
        res = bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=(0, 0, 0), plane_no=(0, sg, 0), clear_outer=True)
        cut = [e for e in res['geom_cut'] if isinstance(e, bmesh.types.BMEdge)]; nf = bmesh.ops.holes_fill(bm, edges=cut, sides=0)['faces']
        me = bpy.data.meshes.new(f'kwp_sp_half{sg}'); bm.to_mesh(me); bm.free()
        me.materials.append(seed); me.materials.append(inner)
        for p_ in me.polygons: p_.use_smooth = True
        o = bpy.data.objects.new(me.name, me); bpy.context.scene.collection.objects.link(o)
        for p_ in o.data.polygons:
            if abs(p_.normal.y) > 0.98 and abs(p_.center.y) < 0.02: p_.material_index = 1; p_.use_smooth = False
        o.scale = (r, 0.92 * r, 0.82 * r)
        # hinge on the bottom line: each half leans out 7 deg about X -> a V split along the top
        o.rotation_euler = (math.radians(-17 * sg), 0, 0); o.location = (0, sg * 0.45 * mm, 0.82 * r)
        pr.add(o)
    rm = L.mat('kwp_sp_root', (0.62, 0.55, 0.36), 0.5, sss=0.15)
    pr.add(L.tube('kwp_sp_root', [V((-2.6 * mm, 0.1 * mm, 1.6 * mm)), V((-4.3 * mm, 0.35 * mm, 0.95 * mm)), V((-6.0 * mm, 0.75 * mm, 0.62 * mm)), V((-7.6 * mm, 1.15 * mm, 0.5 * mm))],
                  0.75 * mm, rm, None, 4, radii=[1.0, 0.9, 0.7, 0.35]))
    sh = L.mat('kwp_sp_shoot', _hexlin('A9CF78'), 0.5, sss=0.15)
    S = [V((2.4 * mm, -0.1 * mm, 4.0 * mm)), V((3.9 * mm, -0.3 * mm, 5.0 * mm)), V((5.1 * mm, -0.55 * mm, 4.6 * mm)), V((5.6 * mm, -0.7 * mm, 3.7 * mm))]
    pr.add(L.tube('kwp_sp_shoot', S, 0.45 * mm, sh, None, 4, radii=[1.0, 0.95, 0.9, 0.8]))
    lm = two_tone('kwp_sp_leaf', _hexlin('8FC45A'), tuple(0.85 * x for x in _hexlin('8FC45A')), 2500 / scale, 0.5, sss=0.2, bump=0.1)
    for sg in (1, -1):
        lf = pr.add(L.sphere(f'kwp_sp_leaf{sg}', 1.0, (5.75 * mm, (-0.7 + sg * 0.45) * mm, 3.2 * mm), lm, None, 16, 8))
        lf.scale = (2.1 * mm, 0.95 * mm, 0.32 * mm); lf.rotation_euler = (math.radians(sg * 55), math.radians(70), 0)
    pr.pts['mid'] = (0, 0, 0.82 * r)
    return pr


def _lens_mat(name, power, th=0.003):
    """thin glass disc that refracts like a converging lens: the surface normal tilts with the radius (power = 1/R per face, 1/m)"""
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; N = nt.nodes; Lk = nt.links.new; N.clear()
    # Refraction BSDF (no reflection): a glass BSDF mirrored the lamp twice (front + back face) = a see-through double square
    out = N.new('ShaderNodeOutputMaterial'); gl = N.new('ShaderNodeBsdfRefraction'); gl.inputs['IOR'].default_value = 1.5; gl.inputs['Roughness'].default_value = 0.0
    gl.inputs['Color'].default_value = (0.985, 0.99, 0.99, 1)
    tc = N.new('ShaderNodeTexCoord'); sp = N.new('ShaderNodeSeparateXYZ'); Lk(tc.outputs['Object'], sp.inputs[0])
    def M(op, a, b=None):
        q = N.new('ShaderNodeMath'); q.operation = op
        for i_, v in enumerate((a, b)):
            if v is None: continue
            if isinstance(v, (int, float)): q.inputs[i_].default_value = v
            else: Lk(v, q.inputs[i_])
        return q.outputs[0]
    cb = N.new('ShaderNodeCombineXYZ'); Lk(M('MULTIPLY', sp.outputs['X'], power), cb.inputs['X']); Lk(M('MULTIPLY', sp.outputs['Y'], power), cb.inputs['Y'])
    Lk(M('SIGN', sp.outputs['Z']), cb.inputs['Z'])
    vt = N.new('ShaderNodeVectorTransform'); vt.vector_type = 'NORMAL'; vt.convert_from = 'OBJECT'; vt.convert_to = 'WORLD'; Lk(cb.outputs[0], vt.inputs[0])
    geo = N.new('ShaderNodeNewGeometry')
    fl = N.new('ShaderNodeVectorMath'); fl.operation = 'SCALE'; Lk(vt.outputs[0], fl.inputs[0])
    Lk(M('SUBTRACT', 1.0, M('MULTIPLY', geo.outputs['Backfacing'], 2.0)), fl.inputs['Scale'])     # Cycles: the normal must face the ray side
    nm = N.new('ShaderNodeVectorMath'); nm.operation = 'NORMALIZE'; Lk(fl.outputs[0], nm.inputs[0])
    face = M('GREATER_THAN', M('ABSOLUTE', sp.outputs['Z']), th * 0.37)
    mx = N.new('ShaderNodeMix'); mx.data_type = 'VECTOR'; Lk(face, mx.inputs['Factor']); Lk(geo.outputs['Normal'], mx.inputs[4]); Lk(nm.outputs[0], mx.inputs[5])
    Lk(mx.outputs[1], gl.inputs['Normal']); Lk(gl.outputs[0], out.inputs[0])
    return m


def lens_arm(c, K=None, lens=(-0.30, -0.31, 0.058), off=(0.048, 0.0, 0.0), r=0.045, lt=25.0, power=12.3, post=0.16, l1=0.22, l2=0.24,
             rim=0.0013, rim_z=1.6, th=0.003, rim_col=(0.025, 0.025, 0.027), **_):
    """magnifier on a two-joint black arm; the root is the clamp on the table edge.  lens = lens centre (root local) when
    slide=0 (centred over the dish); slide=1 moves it by `off`.  The glass is a thin disc whose normals bend the view like
    a converging lens (power ~ 1/R per face), tilted `lt` deg toward -Y (NB fx.item's own tilt turns the root).  Lens casts no shadow."""
    pr = Prop('lens_arm', c); blk = L.mat('kwp_la_black', (0.025, 0.025, 0.027), 0.35, coat=0.2)
    pr.add(_box('kwp_la_clamp', (0.05, 0.06, 0.045), (0, 0, 0.0225), blk, None, 0.004))
    pr.add(_box('kwp_la_jaw', (0.05, 0.012, 0.05), (0, 0.035, -0.012), blk, None, 0.003))
    pr.add(L.cyl('kwp_la_post', 0.007, post, (0, 0, 0.045 + post / 2), blk, None, verts=20))
    J1 = V((0, 0, 0.045 + post)); pr.add(L.sphere('kwp_la_j1', 0.011, J1, blk, None, 20, 10))
    seg1 = pr.add(L.cyl('kwp_la_s1', 0.0055, 1.0, (0, 0, 0), blk, None, verts=16)); seg2 = pr.add(L.cyl('kwp_la_s2', 0.0048, 1.0, (0, 0, 0), blk, None, verts=16))
    j2 = pr.add(L.sphere('kwp_la_j2', 0.0095, (0, 0, 0), blk, None, 20, 10))
    head = bpy.data.objects.new('kwp_la_head', None); c.objects.link(head); head.parent = pr.root; pr.objs.append(head)
    ring = pr.add(L.prim('torus', 'kwp_la_ring', blk, None, major_radius=r + rim * 0.77, minor_radius=rim, major_segments=128, minor_segments=12)); L.smooth(ring)
    ring.scale = (1, 1, rim_z); ring.parent = head
    if tuple(rim_col) != (0.025, 0.025, 0.027): ring.data.materials[0] = L.mat('kwp_la_rim', tuple(rim_col), 0.38, metal=0.6)
    gm = _lens_mat('kwp_la_glass', power, th)
    gl = pr.add(L.cyl('kwp_la_glass', r, th, (0, 0, 0), gm, None, verts=160)); gl.parent = head
    gl.visible_shadow = False
    stub = pr.add(L.cyl('kwp_la_stub', 0.004, 0.03, (r + 0.015, 0, 0), blk, None, rot=(0, 90, 0), verts=12)); stub.parent = head
    def place_seg(o, a, b):
        d_ = b - a; o.location = (a + b) / 2; o.rotation_mode = 'QUATERNION'; o.rotation_quaternion = V((0, 0, 1)).rotation_difference(d_.normalized()); o.scale = (1, 1, d_.length)
    def _s(slide=0.0, **_):
        Lc = V(lens) + V(off) * slide
        to_clamp = V((-Lc.x, -Lc.y, 0)).normalized()                      # the arm leaves the ring toward the clamp side
        yaw = math.atan2(to_clamp.y, to_clamp.x)
        # head frame: disc tilted toward -Y (camera) by `tilt`; stub along the clamp direction in the disc plane
        Rt = Matrix.Rotation(math.radians(lt), 3, 'X')
        xs = (Rt.inverted() @ V((to_clamp.x, to_clamp.y, 0))); xs.z = 0; xs.normalize(); a_ = math.atan2(xs.y, xs.x)
        head.matrix_basis = (Matrix.Translation(Lc) @ Rt.to_4x4() @ Matrix.Rotation(a_, 4, 'Z'))
        A = head.matrix_basis @ V((r + 0.03, 0, 0))
        dv = A - J1; dist = min(dv.length, l1 + l2 - 1e-4); dn = dv.normalized()
        a1 = (l1 * l1 - l2 * l2 + dist * dist) / (2 * dist); hh = math.sqrt(max(0.0, l1 * l1 - a1 * a1))
        up = V((0, 0, 1)); pp = (up - dn * up.dot(dn)).normalized(); E = J1 + dn * a1 + pp * hh
        place_seg(seg1, J1, E); place_seg(seg2, E, A); j2.location = E
    pr._set = _s; _s(0.0)
    pr.pts['lens'] = tuple(lens)
    return pr


def _xray_pixels(Wp=1024, Hp=658, spot=(0.33, 0.36), spot_r=0.029):
    """chest X-ray drawn by us: R = grey film, G = dotted path parameter (0 none, 0.02..1 along it), B = ring angle parameter"""
    import numpy as np
    asp = Wp / Hp; u = (np.arange(Wp) + 0.5) / Wp; v = (np.arange(Hp) + 0.5) / Hp; U, Vv = np.meshgrid(u, v); X = (U - 0.5) * asp; Y = Vv
    rng = np.random.default_rng(4)
    def ell(cx, cy, rx, ry, soft=0.04):
        q = ((U - cx) * asp / (rx * asp)) ** 2 + ((Vv - cy) / ry) ** 2
        return np.clip((1.0 - q) / soft, 0, 1)
    def sm(a, n=3):
        k = np.ones(n) / n
        a = np.apply_along_axis(lambda m: np.convolve(m, k, 'same'), 0, a); return np.apply_along_axis(lambda m: np.convolve(m, k, 'same'), 1, a)
    g = np.full((Hp, Wp), 0.018)
    torso = np.maximum(ell(0.5, 0.36, 0.40, 0.62, 0.08), np.clip(1 - np.abs(U - 0.5) / 0.07, 0, 1) * (Vv > 0.85))
    g = g + 0.20 * torso
    lungR = ell(0.345, 0.50, 0.125, 0.31, 0.10); lungL = ell(0.655, 0.50, 0.118, 0.29, 0.10)
    lungs = np.maximum(lungR, lungL)
    nz = sm(rng.normal(0, 1, (Hp, Wp)), 9) * 0.5
    g = g * (1 - 0.62 * lungs) + lungs * (0.02 * nz)
    heart = ell(0.565, 0.31, 0.11, 0.13, 0.25); g = g + 0.10 * heart * lungL + 0.05 * heart
    spine = np.clip(1 - np.abs(U - 0.5) / 0.028, 0, 1) * torso; g = g + 0.07 * spine * (0.85 + 0.15 * np.sin(Vv * 140))
    for i in range(9):            # ribs: arcs from the spine outward and down, both sides
        v0 = 0.84 - i * 0.068
        for s in (-1, 1):
            t = np.clip((U - 0.5) * s / 0.34, 0, 1.2)
            vr = v0 - 0.11 * t ** 1.5 + 0.035 * np.sin(np.pi * np.clip(t, 0, 1))
            band = np.exp(-((Vv - vr) / 0.0085) ** 2) * (t > 0.06) * (t < 1.02) * torso
            g = g + 0.10 * band
    for s in (-1, 1):              # clavicles
        t = np.clip((U - 0.5) * s / 0.3, 0, 1); vc = 0.86 + 0.03 * t - 0.02 * t * t
        g = g + 0.12 * np.exp(-((Vv - vc) / 0.011) ** 2) * (t > 0.08) * (t < 0.95)
    wp = np.clip(1 - np.abs(U - 0.5) / 0.016, 0, 1) * (Vv > 0.56) * torso; g = g * (1 - 0.55 * wp)
    for s in (-1, 1):              # main bronchi
        a = np.array([0.5, 0.56]); b = np.array([0.5 + s * 0.085, 0.47]); P = np.stack([U, Vv], -1); ab = b - a
        tt = np.clip(((P - a) @ ab) / (ab @ ab), 0, 1); dd = np.linalg.norm(P - (a + tt[..., None] * ab), axis=-1)
        g = g * (1 - 0.45 * np.clip(1 - dd / 0.012, 0, 1))
    g = sm(g, 3) + rng.normal(0, 0.006, (Hp, Wp))
    # the dark spot itself is drawn by the shader (it pulses); a faint halo here so it sits in the film
    sx, sy = spot; dsp = np.sqrt(((U - sx) * asp) ** 2 + (Vv - sy) ** 2); g = g * (1 - 0.15 * np.clip(1 - dsp / (spot_r * 1.6), 0, 1))
    # dotted path: mouth (top centre) -> windpipe -> right bronchus (viewer's left) -> down to the spot edge
    ctrl = [(0.5, 1.02), (0.5, 0.80), (0.5, 0.58), (0.455, 0.52), (0.40, 0.47), (0.36, 0.43), (sx + 0.006, sy + spot_r * 1.9)]
    pts = []
    for (x0, y0), (x1, y1) in zip(ctrl, ctrl[1:]):
        for k in range(40): f = k / 40; pts.append((x0 + (x1 - x0) * f, y0 + (y1 - y0) * f))
    pts.append(ctrl[-1]); pts = np.array(pts); seg = np.linalg.norm(np.diff(pts * [asp, 1], axis=0), axis=1); s_ = np.concatenate([[0], np.cumsum(seg)]); L_ = s_[-1]
    G = np.zeros((Hp, Wp)); step = 0.032; nd = int(L_ / step)
    for k in range(nd + 1):
        sk = min(L_, k * step + 0.01); j = np.searchsorted(s_, sk); j = max(1, min(len(pts) - 1, j)); f = (sk - s_[j - 1]) / max(1e-9, seg[j - 1])
        cx, cy = pts[j - 1] + (pts[j] - pts[j - 1]) * f
        dd = np.sqrt(((U - cx) * asp) ** 2 + (Vv - cy) ** 2); G = np.where(dd < 0.0095, max(0.02, sk / L_), G)
    ra = np.where(np.abs(dsp - spot_r * 1.75) < 0.0042, (np.arctan2((U - sx) * asp, Vv - sy) % (2 * np.pi)) / (2 * np.pi) + 0.002, 0.0)
    img = np.stack([np.clip(g, 0, 1), G, ra, np.ones_like(g)], -1).astype(np.float32)
    return img, asp


def xray_screen(c, K=None, width=0.45, spot=(0.33, 0.36), **_):
    """the ep02 CT monitor body (gfx_kw.ScanMonitor) on its stand, standing on z=0, with OUR chest X-ray on its screen and
    no text: controls power (backlight 0..1), ring (yellow ring drawn 0..1 round the spot), path (dotted mouth->lung path
    0..1), pulse (spot scale, 1 = normal).  Point 'spot' = the spot on the screen (world, for labels / looks)."""
    import gfx_kw as G
    pr = Prop('xray_screen', c); mon = G.ScanMonitor(V((0, 0, 0)), c, width=width); mon.root.parent = pr.root; mon.root.location = (0, 0, 0.681 * width)
    for o in list(mon._ui_objs) + [mon._marker]: o.hide_render = True; o.hide_viewport = True
    Wp, Hp = 1024, 658; img, asp = _xray_pixels(Wp, Hp, spot)
    im = bpy.data.images.new('kwp_xray', Wp, Hp, float_buffer=True, alpha=True); im.colorspace_settings.name = 'Non-Color'; im.pixels.foreach_set(img.ravel())
    try: im.pack()
    except Exception: pass
    m = bpy.data.materials.new('kwp_xray_screen'); m.use_nodes = True; nt = m.node_tree; N = nt.nodes; Lk = nt.links.new; N.clear()
    out = N.new('ShaderNodeOutputMaterial'); em = N.new('ShaderNodeEmission'); tc = N.new('ShaderNodeTexCoord')
    sp = N.new('ShaderNodeSeparateXYZ'); Lk(tc.outputs['Generated'], sp.inputs[0])
    uv = N.new('ShaderNodeCombineXYZ'); Lk(sp.outputs['X'], uv.inputs['X']); Lk(sp.outputs['Z'], uv.inputs['Y'])
    tx = N.new('ShaderNodeTexImage'); tx.image = im; tx.interpolation = 'Linear'; tx.extension = 'EXTEND'; Lk(uv.outputs[0], tx.inputs['Vector'])
    rgb = N.new('ShaderNodeSeparateColor'); Lk(tx.outputs['Color'], rgb.inputs[0])
    vals = {}
    for nm_, dv in (('power', 0.0), ('ring', 0.0), ('path', 0.0), ('pulse', 1.0)):
        vn = N.new('ShaderNodeValue'); vn.outputs[0].default_value = dv; vn.label = nm_; vals[nm_] = vn
    def M(op, a, b=None):
        q = N.new('ShaderNodeMath'); q.operation = op
        for i_, v in enumerate((a, b)):
            if v is None: continue
            if isinstance(v, (int, float)): q.inputs[i_].default_value = v
            else: Lk(v, q.inputs[i_])
        return q.outputs[0]
    du = M('MULTIPLY', M('SUBTRACT', sp.outputs['X'], spot[0]), asp); dv_ = M('SUBTRACT', sp.outputs['Z'], spot[1])
    dist = M('SQRT', M('ADD', M('MULTIPLY', du, du), M('MULTIPLY', dv_, dv_)))
    rr = M('MULTIPLY', vals['pulse'].outputs[0], 0.029)
    mr = N.new('ShaderNodeMapRange'); mr.interpolation_type = 'SMOOTHSTEP'; Lk(dist, mr.inputs['Value']); Lk(M('MULTIPLY', rr, 0.55), mr.inputs['From Min']); Lk(rr, mr.inputs['From Max'])
    spotm = M('SUBTRACT', 1.0, mr.outputs['Result'])
    grey = M('MULTIPLY', rgb.outputs['Red'], M('SUBTRACT', 1.0, M('MULTIPLY', spotm, 0.85)))
    pon = M('MULTIPLY', M('GREATER_THAN', rgb.outputs['Green'], 0.001), M('LESS_THAN', rgb.outputs['Green'], M('ADD', vals['path'].outputs[0], 0.0001)))
    pon = M('MULTIPLY', pon, M('GREATER_THAN', vals['path'].outputs[0], 0.001))
    ron = M('MULTIPLY', M('GREATER_THAN', rgb.outputs['Blue'], 0.001), M('LESS_THAN', rgb.outputs['Blue'], M('ADD', vals['ring'].outputs[0], 0.0001)))
    ron = M('MULTIPLY', ron, M('GREATER_THAN', vals['ring'].outputs[0], 0.001))
    yel = M('MAXIMUM', pon, ron)
    gc = N.new('ShaderNodeCombineColor'); Lk(M('MULTIPLY', grey, 0.92), gc.inputs['Red']); Lk(M('MULTIPLY', grey, 0.97), gc.inputs['Green']); Lk(grey, gc.inputs['Blue'])
    mx = N.new('ShaderNodeMix'); mx.data_type = 'RGBA'; Lk(yel, mx.inputs['Factor']); Lk(gc.outputs[0], mx.inputs[6]); mx.inputs[7].default_value = (1.0, 0.72, 0.02, 1)
    Lk(mx.outputs[2], em.inputs['Color']); Lk(M('MULTIPLY', vals['power'].outputs[0], 1.6), em.inputs['Strength'])
    Lk(em.outputs[0], out.inputs[0])
    mon.screen.data.materials.clear(); mon.screen.data.materials.append(m)
    pr.objs += [o for o in mon.root.children_recursive]
    sw, sh = mon._screen_dims
    pr.pts['spot'] = (0 + (spot[0] - 0.5) * sw, -0.091 * width - 0.003, 0.681 * width + mon._sz + (spot[1] - 0.5) * sh)
    pr.pts['top_mid'] = (0, -0.091 * width - 0.003, 0.681 * width + mon._sz + 0.5 * sh)
    def _s(power=0.0, ring=0.0, path=0.0, pulse=1.0, **_):
        vals['power'].outputs[0].default_value = power; vals['ring'].outputs[0].default_value = ring
        vals['path'].outputs[0].default_value = path; vals['pulse'].outputs[0].default_value = pulse
    pr._set = _s; _s(); return pr


def scope(c, K=None, handle=0.12, hr=0.0085, tube_r=0.003, coil=(0.0, 0.10), **_):
    """flexible endoscope: grey handle `handle` long along +X (axis hr above the origin, the grip point 2 cm in front of its
    middle), black 6 mm tube.  The tube is rebuilt every frame by post(): a 14 cm tip section out of the handle front
    (lying on the table when lift=0, curving up toward the user when lift=1) and a cord from the handle back end to a
    coil lying on the table (coil = its centre in the handle's table frame, set once by place_table)."""
    pr = Prop('scope', c); gm = plastic('kwp_sc_grey', (0.30, 0.31, 0.33), 0.45, 0.5, 0.2); bk = L.mat('kwp_sc_black', (0.018, 0.018, 0.02), 0.4, coat=0.25)
    pr.add(L.cyl('kwp_sc_handle', hr, handle, (0, 0, hr), gm, None, rot=(0, 90, 0), verts=24))
    pr.add(L.cyl('kwp_sc_cap', hr * 0.8, 0.012, (-handle / 2 - 0.006, 0, hr), bk, None, rot=(0, 90, 0), verts=20))
    pr.add(L.cyl('kwp_sc_nose', hr * 0.55, 0.018, (handle / 2 + 0.009, 0, hr), bk, None, rot=(0, 90, 0), verts=20))
    lev = pr.add(_box('kwp_sc_lever', (0.012, 0.006, 0.01), (-0.02, 0, 2 * hr + 0.003), bk, None, 0.002))
    NP = 90
    cu = bpy.data.curves.new('kwp_sc_tube', 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = tube_r; cu.bevel_resolution = 4; cu.use_fill_caps = True
    spl = cu.splines.new('POLY'); spl.points.add(NP - 1)
    tube = bpy.data.objects.new('kwp_sc_tube', cu); c.objects.link(tube); tube.data.materials.append(bk); pr.objs.append(tube)
    state = {'T': None, 'lift': 0.0}; pr.state = state; pr.held = False
    def _cat(P, n):
        out = []
        for i in range(len(P) - 1):
            p0 = P[max(0, i - 1)]; p1 = P[i]; p2 = P[i + 1]; p3 = P[min(len(P) - 1, i + 2)]
            for k in range(n):
                t = k / n; t2 = t * t; t3 = t2 * t
                out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
        out.append(P[-1]); return out
    def _resample(P, n):
        d = [0.0]
        for a, b in zip(P, P[1:]): d.append(d[-1] + (b - a).length)
        out = []; j = 0
        for k in range(n):
            s = d[-1] * k / (n - 1)
            while j < len(d) - 2 and d[j + 1] < s: j += 1
            f = (s - d[j]) / max(1e-9, d[j + 1] - d[j]); out.append(P[j].lerp(P[j + 1], f))
        return out
    def post(lift=0.0, look=None):
        """rebuild the tube in world space from the current handle placement"""
        M = pr.root.matrix_world; X = (M.to_3x3() @ V((1, 0, 0))).normalized(); A0 = M @ V((handle / 2 + 0.018, 0, hr)); B0 = M @ V((-handle / 2 - 0.012, 0, hr))
        T = state['T'] or M; Tz = T.translation.z; Xt = (T.to_3x3() @ V((1, 0, 0))).normalized(); Yt = (T.to_3x3() @ V((0, 1, 0))).normalized(); Yt.z = 0; Yt.normalize(); Xt.z = 0; Xt.normalize()
        Cc = T @ V((coil[0], coil[1], 0)); Cc.z = Tz + tube_r
        # tip section 14 cm: on the table it lies straight on along X then bends a little; lifted it curves up toward the face
        if look is not None: up = (V(look) - A0).normalized()
        else: up = V((0, 0, 1))
        dflat = [A0 + X * 0.05, A0 + X * 0.10 + Yt * 0.012, A0 + X * 0.14 + Yt * 0.03]
        for p_ in dflat: p_.z = Tz + tube_r
        dlift = [A0 + X * 0.045 + up * 0.012, A0 + X * 0.07 + up * 0.055, A0 + X * 0.06 + up * 0.10]
        tip = [a.lerp(b, lift) for a, b in zip(dflat, dlift)]
        # cord: from the back end, down to the table and round the coil (1.4 turns, r 5 cm)
        cord = [B0 - X * 0.03]; drop = B0 - X * 0.07; drop.z = max(Tz + tube_r, drop.z - 0.10 * lift); cord.append(drop)
        e0 = Cc + (B0 - Cc).normalized() * 0.055; e0.z = Tz + tube_r; cord.append(e0)
        a0 = math.atan2((e0 - Cc).y, (e0 - Cc).x)
        for k in range(1, 15):
            a = a0 + k * 2 * math.pi * 1.4 / 14; rr = 0.055 - 0.012 * k / 14
            cord.append(V((Cc.x + rr * math.cos(a), Cc.y + rr * math.sin(a), Tz + tube_r + (0.0055 if k > 10 else 0.0))))
        P = list(reversed(tip)) + [A0] + [B0] + cord
        # (the tube runs THROUGH the handle between A0 and B0: hidden inside it)
        P = _resample(_cat(P, 6), NP)
        for q, p_ in zip(spl.points, P): q.co = (p_.x, p_.y, p_.z, 1)
    def place_table(T):
        state['T'] = T.copy(); pr.root.matrix_world = T; bpy.context.view_layer.update(); post(0.0)
    def _s(lift=0.0, **_): state['lift'] = lift
    pr._set = _s
    pr.post = post; pr.place_table = place_table; pr.pts['tip'] = (handle / 2 + 0.07, 0, hr + 0.1)
    return pr


def peas(c, K=None, count=40, plate_r=0.105, heap_r=0.042, heap_h=0.016, **_):
    """white plate with a small heap of ~40 bright green peas (7-8 mm, a little uneven)"""
    pr = Prop('peas', c); pm = L.mat('kwp_plate', (0.70, 0.70, 0.68), 0.22, coat=0.3)
    prof = [(0.0, 0.0), (plate_r * 0.62, 0.0), (plate_r * 0.70, 0.004), (plate_r * 0.98, 0.016), (plate_r, 0.0185)]
    loops = []
    for rr, z in prof[1:]:
        loops.append(([(rr * math.cos(2 * math.pi * i / 64), rr * math.sin(2 * math.pi * i / 64)) for i in range(64)], z))
    o = pr.add(loft('kwp_plate', loops, pm, cap_bottom=True)); sd = o.modifiers.new('sd', 'SOLIDIFY'); sd.thickness = 0.003; sd.offset = 1.0; _contact_ao(pm, 0.02, 0.6)
    gm = two_tone('kwp_peas', _hexlin('6DB33F'), tuple(0.78 * x for x in _hexlin('6DB33F')), 700, 0.32, coat=0.35, sss=0.05, bump=0.12)
    rnd = random.Random(17); placed = []
    tries = 0
    while len(placed) < count and tries < 400 * count:
        tries += 1; rr = rnd.uniform(0.0036, 0.0041); a = rnd.uniform(0, 2 * math.pi); d_ = heap_r * math.sqrt(rnd.random()); x, y = d_ * math.cos(a), d_ * math.sin(a)
        z = 0.0035 + rr
        for (px, py, pz, pr_) in placed:          # stack: rest on the highest pea it overlaps
            h2 = (rr + pr_) ** 2 - (x - px) ** 2 - (y - py) ** 2
            if h2 > 0: z = max(z, pz + math.sqrt(h2))
        if z > 0.0035 + rr + heap_h * (1 - (d_ / (heap_r + 0.003)) ** 2) + 0.002: continue
        placed.append((x, y, z, rr))
    print('KW peas placed', len(placed), 'of', count)
    for i, (x, y, z, rr) in enumerate(placed):
        s = pr.add(L.sphere(f'kwp_pea{i}', rr, (x, y, z), gm, None, 16, 8)); s.scale = (1, 1, rnd.uniform(0.92, 1.0))
    return pr


def make(kind, c, K=None, **params):
    if kind not in KINDS: raise ValueError(f'item kind {kind!r}: one of {", ".join(KINDS)}')
    return globals()[kind](c, K, **params)
