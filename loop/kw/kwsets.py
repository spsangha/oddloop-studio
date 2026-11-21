"""kwsets - extra story sets for kwkit: 'room' (home office + kitchen corner), 'street' (sidewalk, road, park strip), 'studio' (stool).
Built around a reference person seated at the set's main seat (like sets_kw).  All models CC0 from Poly Haven (assets/real/CREDITS.md).
build(kind, S, ref_person, K) -> object with .coll .lights and optional .update(t)."""
import bpy, math, os
from mathutils import Vector as V, Matrix
import kwlib as L
HERE = os.path.dirname(os.path.abspath(__file__))
A = os.environ.get('KW_ASSETS', os.path.normpath(os.path.join(HERE, '..', '..', 'assets', 'real')))
class Set: pass

def _tex(K, name, folder, scale, tint=None, nor=1.0, fallback=(0.6, 0.6, 0.6)):
    try:
        if K: return K.tex(name, folder, scale, tint=tint, nor=nor)
    except Exception as e: print('tex failed', folder, e)
    return L.mat(name, fallback, 0.6)

def gltf_fit(c, model, loc, rz=0.0, dim=None):
    """import a Poly Haven glTF, optionally scale so that its ('x'|'y'|'z', metres) dimension matches, bottom at loc.z"""
    import kw_realism as R
    p = os.path.join(A, 'models', model, f'{model}_1k.gltf')
    if not os.path.exists(p): print('missing model', p); return []
    objs = R.import_gltf(p, collection=c); bpy.context.view_layer.update()
    roots = [o for o in objs if o.parent is None or o.parent not in objs]
    pts = [o.matrix_world @ V(b) for o in objs if o.type == 'MESH' for b in o.bound_box]
    if not pts: return objs
    mn = V((min(p.x for p in pts), min(p.y for p in pts), min(p.z for p in pts))); mx = V((max(p.x for p in pts), max(p.y for p in pts), max(p.z for p in pts)))
    s = 1.0
    if dim: ax = 'xyz'.index(dim[0]); s = dim[1] / max(1e-6, (mx - mn)[ax])
    ctr = V(((mn.x + mx.x) / 2, (mn.y + mx.y) / 2, mn.z))
    T = Matrix.Translation(V(loc)) @ Matrix.Rotation(math.radians(rz), 4, 'Z') @ Matrix.Scale(s, 4) @ Matrix.Translation(-ctr)
    for o in roots: o.matrix_world = T @ o.matrix_world
    return objs

def _area(c, name, loc, e, size, col, tgt, sy=None):
    Ld = bpy.data.lights.new(name, 'AREA'); Ld.energy = e; Ld.size = size; Ld.color = col
    if sy: Ld.shape = 'RECTANGLE'; Ld.size_y = sy
    o = bpy.data.objects.new(name, Ld); c.objects.link(o); o.location = loc
    o.rotation_euler = (V(tgt) - V(loc)).to_track_quat('-Z', 'Y').to_euler(); return o

def wood(name, base=(0.42, 0.24, 0.12), scale=6.0, planks=True):
    """procedural varnished wood (planks along X)"""
    m = L.mat(name, base, 0.35, coat=0.25); nt = m.node_tree; b = nt.nodes['Principled BSDF']
    tc = nt.nodes.new('ShaderNodeTexCoord'); mp = nt.nodes.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (0.25 * scale, 4.0 * scale, 1)
    nt.links.new(tc.outputs['Object'], mp.inputs['Vector'])
    wv = nt.nodes.new('ShaderNodeTexWave'); wv.inputs['Scale'].default_value = 1.2; wv.inputs['Distortion'].default_value = 6; wv.inputs['Detail'].default_value = 3
    nt.links.new(mp.outputs['Vector'], wv.inputs['Vector'])
    cr = nt.nodes.new('ShaderNodeValToRGB'); cr.color_ramp.elements[0].color = (*[x * 0.55 for x in base], 1); cr.color_ramp.elements[1].color = (*[min(1, x * 1.35) for x in base], 1)
    nt.links.new(wv.outputs['Fac'], cr.inputs['Fac'])
    if planks:
        br = nt.nodes.new('ShaderNodeTexBrick'); br.inputs['Scale'].default_value = 1.0; br.offset = 0.5
        br.inputs['Mortar Size'].default_value = 0.004; br.inputs['Brick Width'].default_value = 1.6; br.inputs['Row Height'].default_value = 0.16
        mp2 = nt.nodes.new('ShaderNodeMapping'); nt.links.new(tc.outputs['Object'], mp2.inputs['Vector']); nt.links.new(mp2.outputs['Vector'], br.inputs['Vector'])
        nt.links.new(cr.outputs['Color'], br.inputs['Color1']); nt.links.new(cr.outputs['Color'], br.inputs['Color2'])
        br.inputs['Mortar'].default_value = (*[x * 0.3 for x in base], 1)
        nt.links.new(br.outputs['Color'], b.inputs['Base Color'])
        bp = nt.nodes.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.3; nt.links.new(br.outputs['Fac'], bp.inputs['Height']); nt.links.new(bp.outputs['Normal'], b.inputs['Normal'])
    else: nt.links.new(cr.outputs['Color'], b.inputs['Base Color'])
    return m

def sky_window_mat(name):
    """bright daylight seen through a window (emissive vertical gradient: warm haze to blue sky)"""
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial'); em = nt.nodes.new('ShaderNodeEmission'); tc = nt.nodes.new('ShaderNodeTexCoord'); sep = nt.nodes.new('ShaderNodeSeparateXYZ')
    nt.links.new(tc.outputs['Generated'], sep.inputs[0]); cr = nt.nodes.new('ShaderNodeValToRGB')
    cr.color_ramp.elements[0].position = 0.0; cr.color_ramp.elements[0].color = (0.95, 0.85, 0.7, 1); cr.color_ramp.elements[1].position = 0.9; cr.color_ramp.elements[1].color = (0.25, 0.55, 1.0, 1)
    nt.links.new(sep.outputs['Z'], cr.inputs['Fac']); nt.links.new(cr.outputs['Color'], em.inputs['Color']); em.inputs['Strength'].default_value = 2.2
    lp = nt.nodes.new('ShaderNodeLightPath'); mx = nt.nodes.new('ShaderNodeMixShader'); tr = nt.nodes.new('ShaderNodeBsdfTransparent')
    nt.links.new(lp.outputs['Is Camera Ray'], mx.inputs[0]); nt.links.new(em.outputs[0], mx.inputs[2])
    em2 = nt.nodes.new('ShaderNodeEmission'); em2.inputs['Strength'].default_value = 1.0; nt.links.new(cr.outputs['Color'], em2.inputs['Color']); nt.links.new(em2.outputs[0], mx.inputs[1])
    nt.links.new(mx.outputs[0], out.inputs[0]); return m

def build(kind, S, ref, K):
    bpy.context.view_layer.update()
    return {'room': room, 'street': street, 'studio': studio}[kind](S, ref, K)

# ------------------------------------------------------------------ room: home office with a kitchen corner
def room(S, ref, K):
    c = L.coll('kw_room'); s = Set(); s.coll = c
    P = ref.bone_world('spine05'); H = ref.bone_world('head').z; seat = P.z - 0.075
    YW, XW, XR, ZC = 1.45, -2.2, 2.2, 2.65      # back wall (behind the desk chair), left/right walls, ceiling
    wall = _tex(K, 'kw_r_wall', 'white_plaster_02', 0.9, tint=(1.0, 0.86, 0.66), nor=0.5, fallback=(0.85, 0.75, 0.6))
    wall2 = _tex(K, 'kw_r_wall2', 'white_plaster_02', 0.9, tint=(0.55, 0.78, 0.86), nor=0.5, fallback=(0.5, 0.7, 0.8))
    floor = wood('kw_r_floor', (0.45, 0.27, 0.14), 1.0)
    white = L.mat('kw_r_white', (0.85, 0.85, 0.82), 0.35)
    L.box('r_floor', (8, 8, 0.05), (0, 0, -0.025), floor, c, 0)
    L.box('r_ceiling', (8, 8, 0.05), (0, 0, ZC + 0.025), L.mat('kw_r_ceil', (0.9, 0.9, 0.88), 0.9), c, 0)
    L.box('r_wall_back', (8, 0.1, ZC), (0, YW + 0.05, ZC / 2), wall, c, 0)
    L.box('r_wall_left', (0.1, 8, ZC), (XW - 0.05, 0, ZC / 2), wall2, c, 0)
    L.box('r_wall_right', (0.1, 8, ZC), (XR + 0.05, 0, ZC / 2), wall2, c, 0)
    L.box('r_wall_front', (8, 0.1, ZC), (0, -4.0, ZC / 2), wall, c, 0)
    L.box('r_skirt', (8, 0.02, 0.09), (0, YW - 0.005, 0.045), white, c, 0.004)
    # window in the back wall (left of the person) with daylight behind
    wx, wz, ww, wh = -1.05, 1.55, 1.1, 1.15
    fr = L.mat('kw_r_frame', (0.95, 0.95, 0.93), 0.3)
    L.box('r_win_sky', (ww + 0.3, 0.02, wh + 0.3), (wx, YW + 0.2, wz), sky_window_mat('kw_r_sky'), c, 0)
    for nm, sz, lc in (('r_win_t', (ww + 0.1, 0.12, 0.06), (wx, YW, wz + wh / 2)), ('r_win_b', (ww + 0.2, 0.2, 0.06), (wx, YW - 0.04, wz - wh / 2)),
                       ('r_win_l', (0.06, 0.12, wh), (wx - ww / 2, YW, wz)), ('r_win_r', (0.06, 0.12, wh), (wx + ww / 2, YW, wz)), ('r_win_m', (0.04, 0.08, wh), (wx, YW, wz))):
        L.box(nm, sz, lc, fr, c, 0.008)
    # cut the wall: hide the wall behind the window with a boolean
    cut = L.box('r_win_cut', (ww, 0.4, wh), (wx, YW + 0.05, wz), None, c, 0); cut.hide_render = True; cut.display_type = 'WIRE'
    bw = bpy.data.objects['r_wall_back']; bo = bw.modifiers.new('win', 'BOOLEAN'); bo.object = cut; bo.operation = 'DIFFERENCE'; bo.solver = 'EXACT'
    # desk in front of the person, chair under them
    desk_y = -0.55
    gltf_fit(c, 'WoodenTable_01', (0.0, desk_y, 0.0), 0, ('z', seat + 0.27))
    gltf_fit(c, 'dining_chair_02', (0.0, 0.08, 0.0), 0, ('z', seat + 0.43))
    top = seat + 0.27
    # laptop + mug + papers + tissue box on the desk (simple bevelled shapes)
    dark = L.mat('kw_r_laptop', (0.08, 0.085, 0.09), 0.3, 0.6); scr = (K._screen('kw_r_screen', 'map') if K and hasattr(K, '_screen') else L.emis('kw_r_screen', (0.2, 0.5, 1.0), 1.5)[0])
    L.box('r_laptop_base', (0.34, 0.24, 0.018), (0.34, desk_y - 0.05, top + 0.009), dark, c, 0.006, (0, 0, 20))
    lid = L.box('r_laptop_lid', (0.34, 0.012, 0.23), (0.30, desk_y - 0.16, top + 0.125), dark, c, 0.006, (-12, 0, 20))
    L.box('r_laptop_scr', (0.31, 0.002, 0.2), (0.302, desk_y - 0.152, top + 0.127), scr, c, 0, (-12, 0, 20))
    mug = L.cyl('r_mug', 0.045, 0.1, (-0.38, desk_y + 0.02, top + 0.05), L.mat('kw_r_mug', (0.85, 0.15, 0.1), 0.25, coat=0.6), c)
    L.box('r_paper', (0.21, 0.297, 0.004), (-0.1, desk_y - 0.12, top + 0.003), L.mat('kw_r_paper', (0.95, 0.95, 0.93), 0.8), c, 0, (0, 0, -8))
    tb = L.box('r_tissuebox', (0.24, 0.12, 0.1), (-0.48, desk_y - 0.2, top + 0.05), L.mat('kw_r_tbox', (0.25, 0.65, 0.85), 0.4), c, 0.01, (0, 0, 15))
    t_ = L.ico('r_tissue_pop', 0.04, (-0.48, desk_y - 0.2, top + 0.11), L.mat('kw_r_tissue', (0.97, 0.97, 0.98), 0.85, sss=0.2), c, 2); t_.scale = (1.2, 0.6, 0.9)
    # shelf with books on the right wall area of the back wall, plant, clock
    shelf_m = wood('kw_r_shelf', (0.55, 0.35, 0.2), 3.0, planks=False)
    for k, z in enumerate((1.25, 1.65)):
        L.box(f'r_shelf{k}', (0.9, 0.22, 0.03), (1.15, YW - 0.11, z), shelf_m, c, 0.005)
        x = 0.75
        for j in range(9):
            col = [(0.8, 0.15, 0.1), (0.1, 0.35, 0.75), (0.95, 0.7, 0.1), (0.15, 0.55, 0.3), (0.9, 0.9, 0.85), (0.5, 0.2, 0.6)][(j + 2 * k) % 6]
            h = 0.18 + 0.06 * ((j * 7 + k) % 3) / 2; wdt = 0.035 + 0.01 * (j % 3)
            L.box(f'r_book{k}{j}', (wdt, 0.16, h), (x, YW - 0.12, z + 0.015 + h / 2), L.mat(f'kw_r_book{k}{j}', col, 0.5), c, 0.003); x += wdt + 0.006
    gltf_fit(c, 'potted_plant_02', (1.75, YW - 0.35, 0), 30, ('z', 1.05))
    gltf_fit(c, 'wall_clock', (0.15, YW - 0.02, 2.05), 0, None)
    # kitchen corner on the left wall: counter + stove + apple
    cm = L.mat('kw_r_cab', (0.92, 0.9, 0.86), 0.4); ctop = L.mat('kw_r_ctop', (0.2, 0.22, 0.24), 0.25, coat=0.4)
    L.box('r_cab', (0.62, 1.6, 0.86), (XW + 0.31, 0.2, 0.43), cm, c, 0.01)
    L.box('r_ctop', (0.66, 1.64, 0.04), (XW + 0.33, 0.2, 0.88), ctop, c, 0.006)
    gltf_fit(c, 'electric_stove', (XW + 0.34, -0.95, 0), 90, ('z', 0.92))
    gltf_fit(c, 'food_apple_01', (XW + 0.4, 0.5, 0.9), 0, ('z', 0.08))
    gltf_fit(c, 'food_apple_01', (XW + 0.47, 0.6, 0.9), 50, ('z', 0.075))
    L.box('r_upper', (0.35, 1.6, 0.7), (XW + 0.18, 0.2, 1.85), cm, c, 0.01)
    # rug + ceiling lamp
    L.box('r_rug', (1.8, 1.3, 0.01), (0.1, -0.2, 0.005), _tex(K, 'kw_r_rug', 'Fabric030', 2.0, tint=(0.6, 0.25, 0.2), fallback=(0.6, 0.25, 0.2)), c, 0.004)
    gltf_fit(c, 'modern_ceiling_lamp_01', (0.0, -0.3, ZC), 0, None)
    s.lights = [_area(c, 'r_window_light', (wx, YW - 0.1, wz), 260, 1.2, (1.0, 0.93, 0.82), (0.2, -0.6, H - 0.2), 1.2),
                _area(c, 'r_key', (0.95, -1.55, 2.1), 170, 1.3, (1.0, 0.88, 0.74), (0, 0, H - 0.1)),
                _area(c, 'r_rim', (-1.2, 1.0, 2.0), 120, 0.8, (0.6, 0.8, 1.0), (0, 0, H - 0.1)),
                _area(c, 'r_fill', (-0.2, -2.2, 1.1), 40, 1.6, (1.0, 0.95, 0.9), (0, 0, H - 0.2))]
    s.desk_top = top; s.desk_y = desk_y
    return s

# ------------------------------------------------------------------ street: sidewalk + road + park strip
def street(S, ref, K):
    c = L.coll('kw_street'); s = Set(); s.coll = c
    P = ref.bone_world('spine05'); seat = P.z - 0.075; by = ref.rig.location.y
    asphalt = _tex(K, 'kw_s_asphalt', 'asphalt_02', 3.0, fallback=(0.12, 0.12, 0.13))
    paving = _tex(K, 'kw_s_paving', 'Tiles043', 1 / 0.9, tint=(0.75, 0.74, 0.7), nor=0.8, fallback=(0.6, 0.6, 0.58))
    grass = _tex(K, 'kw_s_grass', 'leafy_grass', 1.5, fallback=(0.2, 0.45, 0.12))
    kerb = L.mat('kw_s_kerb', (0.62, 0.62, 0.6), 0.7)
    L.box('s_road', (60, 8, 0.05), (0, -5.6, -0.145), asphalt, c, 0)
    L.box('s_kerb', (60, 0.18, 0.14), (0, -1.52, -0.05), kerb, c, 0.01)
    L.box('s_walk', (60, 2.9, 0.06), (0, -0.05, -0.03), paving, c, 0)
    L.box('s_grass', (60, 12, 0.05), (0, 7.4, -0.03), grass, c, 0)
    line = L.mat('kw_s_line', (0.95, 0.85, 0.2), 0.5)
    for k in range(-8, 9): L.box(f's_line{k}', (1.6, 0.12, 0.005), (k * 3.2, -5.6, -0.118), line, c, 0)
    gltf_fit(c, 'painted_wooden_bench', (0.0, by + 0.12, 0.0), 180, ('z', None) if False else None)
    bpy.context.view_layer.update()
    gltf_fit(c, 'street_lamp_01', (-1.6, 1.25, 0), 0, ('z', 4.2))
    gltf_fit(c, 'metal_trash_can', (1.05, 1.2, 0), 0, ('z', 0.9))
    gltf_fit(c, 'fire_hydrant', (2.4, -1.15, 0), 20, ('z', 0.75))
    for k, (x, y, sc) in enumerate(((-3.0, 2.2, 1.0), (-1.0, 2.6, 1.3), (1.9, 2.3, 1.1), (3.4, 2.8, 1.4), (-4.4, 3.0, 1.2))):
        gltf_fit(c, 'shrub_04', (x, y, 0), k * 70, ('z', 0.9 * sc))
    for k in range(10): gltf_fit(c, 'grass_medium_02', (-4.5 + k, 1.6 + 0.3 * (k % 3), 0), k * 37, ('z', 0.25))
    s.lights = [_area(c, 's_sun_key', (2.5, -3.0, 3.6), 900, 2.5, (1.0, 0.92, 0.8), (0, 0, 1.2)), _area(c, 's_fill', (-2.0, -2.5, 1.5), 120, 2.5, (0.8, 0.9, 1.0), (0, 0, 1.2))]
    sun = bpy.data.lights.new('s_sun', 'SUN'); sun.energy = 3.0; sun.angle = math.radians(3); sun.color = (1.0, 0.95, 0.85)
    so = bpy.data.objects.new('s_sun', sun); c.objects.link(so); so.rotation_euler = (math.radians(50), 0, math.radians(35)); s.lights.append(so)
    return s

# ------------------------------------------------------------------ studio: gradient world (from Episode), a stool for centre_sit
def studio(S, ref, K):
    c = L.coll('kw_studio'); s = Set(); s.coll = c
    P = ref.bone_world('spine05'); seat = P.z - 0.075; x, y = ref.rig.location.x, ref.rig.location.y
    m = L.mat('kw_st_stool', (0.9, 0.25, 0.1), 0.3, coat=0.6); st = L.mat('kw_st_steel', (0.8, 0.8, 0.82), 0.25, 1.0)
    L.cyl('st_seat', 0.2, 0.05, (x, y + 0.05, seat - 0.025), m, c, verts=40)
    L.cyl('st_post', 0.025, seat - 0.05, (x, y + 0.05, (seat - 0.05) / 2), st, c)
    L.cyl('st_foot', 0.22, 0.02, (x, y + 0.05, 0.01), st, c)
    s.lights = []
    return s
