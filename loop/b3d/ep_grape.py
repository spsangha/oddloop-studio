"""Odd Loop: 'Never Microwave a Grape'. Mr. Fumble microwaves a cut grape -> plasma fireball -> boom -> sooty -> pulls out a whole bunch.
Loops: the last shot (he grins with a bunch of grapes) cuts straight back to the opening fireball.
blender -b -P ep_grape.py -- outdir i0 i1   |   blender -b -P ep_grape.py -- --cues out.json"""
import sys, os, math, random
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy, bmesh
from mathutils import Vector, Matrix, Euler
from toon import *
from humans import build_fumble, pose_fumble
from set_kitchen import build_kitchen

FPS = 30; TWOS = True
DURATION = 24.8
# narration (fixed channel voice), start times in seconds
VO = [(0.15, "This is what happens when you microwave a grape."),
      (2.8, "Cut it almost in half, and hit start."),
      (5.8, "Seconds later, a fireball of plasma. The same stuff as lightning."),
      (11.0, "The two halves squeeze the microwaves into the tiny gap where they touch, until it rips electrons off the salts in the grape."),
      (17.6, "Scientists broke a dozen microwaves figuring this out."),
      (21.0, "So, don't try this at home.")]
T_CHOP, T_IN, T_SHUT, T_START = 3.4, 4.25, 4.65, 5.0
T_SPARK, T_PLASMA, T_FLASH, T_BOOM = 6.6, 7.2, 17.15, 18.2
T_NOD, T_BUNCH = 21.4, 23.0

# microwave on the kitchen table, front (door) faces -x towards Fumble
MX0, MX1 = -1.65, -0.85; MY0, MY1 = 1.6, 2.7; MZ0, MZ1 = 1.31, 2.03
HINGE = Vector((MX0, MY1, 0)); TT = Vector((-1.25, 2.285, 1.4)); GR = 0.075
WIN = Vector((MX0 - 0.02, 2.28, 1.72))

def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def ease(u): u = clamp(u); return u * u * (3 - 2 * u)
def lin(t, a, b): return clamp((t - a) / (b - a))
def kf(t, keys):
    """piecewise eased keyframes [(t, value)], values can be floats or tuples"""
    if t <= keys[0][0]: return keys[0][1]
    for (t0, v0), (t1, v1) in zip(keys, keys[1:]):
        if t <= t1:
            u = ease((t - t0) / (t1 - t0))
            if isinstance(v0, tuple): return tuple(a + (b - a) * u for a, b in zip(v0, v1))
            return v0 + (v1 - v0) * u
    return keys[-1][1]

def in_hook(t): return t < 2.6
def story_t(t): return 9.0 if in_hook(t) else t          # the hook shows the fireball moment

# ------------------------------------------------------------------ props
def glow_mat(name, rgb, strength):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial'); mix = nt.nodes.new('ShaderNodeMixShader'); em = nt.nodes.new('ShaderNodeEmission')
    tr = nt.nodes.new('ShaderNodeBsdfTransparent'); lw = nt.nodes.new('ShaderNodeLayerWeight'); lw.inputs['Blend'].default_value = 0.55
    em.inputs['Color'].default_value = (*rgb, 1); em.inputs['Strength'].default_value = strength
    nt.links.new(lw.outputs['Facing'], mix.inputs['Fac']); nt.links.new(em.outputs[0], mix.inputs[1]); nt.links.new(tr.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs['Surface']); m.blend_method = 'BLEND'
    return m, em

def hemi(name, skin, flesh, r, sign):
    me = bpy.data.meshes.new(name); bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=32, v_segments=16, radius=r)
    res = bmesh.ops.bisect_plane(bm, geom=bm.verts[:] + bm.edges[:] + bm.faces[:], plane_co=(0, 0, 0), plane_no=(-sign, 0, 0), clear_inner=True)
    edges = [e for e in res['geom_cut'] if isinstance(e, bmesh.types.BMEdge)]
    f = bmesh.ops.edgeloop_fill(bm, edges=edges)['faces']
    for fc in bm.faces: fc.smooth = True
    for fc in f: fc.material_index = 1; fc.smooth = False
    bm.to_mesh(me); bm.free(); o = link(bpy.data.objects.new(name, me)); me.materials.append(skin); me.materials.append(flesh)
    return o

def build_grape(tag, skin, flesh):
    g = link(bpy.data.objects.new('grape_' + tag, None)); halves = []
    for k, sgn in enumerate((1, -1)):
        piv = link(bpy.data.objects.new(f'gp_{tag}{k}', None)); piv.parent = g; piv.location = (0, 0, -GR)
        h = hemi(f'gh_{tag}{k}', skin, flesh, GR, sgn); h.parent = piv; h.location = (0, 0, GR); halves.append(piv)
    br = sphere('gbridge_' + tag, skin, 1, 16); br.parent = g; br.scale = (0.02, 0.012, 0.01)
    return dict(root=g, piv=halves, bridge=br)

def set_grape(G, M, a):
    """a = opening angle: 0 whole, ~0.35 just cut, pi/2 lying open with the skin bridge between"""
    for k, sgn in enumerate((1, -1)): G['piv'][k].rotation_euler = (0, -sgn * a, 0)
    G['bridge'].location = (0, 0, -GR + GR * math.sin(a) * 0.0); G['bridge'].hide_render = a < 0.1
    G['root'].matrix_world = M @ Matrix.Translation((0, 0, GR * math.sin(a)))

def build_microwave():
    body = mat('mw_body', hexc('#E9E4D8'), 0.35, 0.4); inner = mat('mw_inner', hexc('#CFCBC2'), 0.5, 0.3); dark = mat('mw_dark', hexc('#2B2D33'), 0.25, 0.6)
    chrome = mat('mw_chrome', hexc('#C9CED6'), 0.2, 0.9); W = {}
    cx, cy = (MX0 + MX1) / 2, (MY0 + MY1) / 2; dx, dy = MX1 - MX0, MY1 - MY0; t = 0.05
    box('mw_top', body, (dx, dy, t), (cx, cy, MZ1 - t / 2), 0.015); box('mw_bot', body, (dx, dy, t), (cx, cy, MZ0 + t / 2), 0.015)
    box('mw_back', body, (t, dy, MZ1 - MZ0), (MX1 - t / 2, cy, (MZ0 + MZ1) / 2), 0.015)
    box('mw_side_far', body, (dx, t, MZ1 - MZ0), (cx, MY1 - t / 2, (MZ0 + MZ1) / 2), 0.015)
    box('mw_panel', body, (dx, 0.3, MZ1 - MZ0), (cx, MY0 + 0.15, (MZ0 + MZ1) / 2), 0.015)
    box('mw_inner_l', inner, (dx - 0.1, 0.02, MZ1 - MZ0 - 0.1), (cx, MY0 + 0.31, (MZ0 + MZ1) / 2), 0)
    box('mw_inner_r', inner, (dx - 0.1, 0.02, MZ1 - MZ0 - 0.1), (cx, MY1 - 0.06, (MZ0 + MZ1) / 2), 0)
    box('mw_inner_b', inner, (0.02, dy - 0.36, MZ1 - MZ0 - 0.1), (MX1 - 0.06, (MY0 + 0.3 + MY1) / 2, (MZ0 + MZ1) / 2), 0)
    box('mw_display', mat('mw_lcd', hexc('#7CFF9B'), 0.4, emit=2.0), (0.02, 0.2, 0.08), (MX0 - 0.005, MY0 + 0.15, 1.88), 0.005)
    for k in range(6): box('mw_btn', dark, (0.03, 0.07, 0.05), (MX0 - 0.01, MY0 + 0.1 + 0.1 * (k % 2), 1.72 - 0.08 * (k // 2)), 0.008)
    W['start_btn'] = box('mw_start', mat('mw_green', hexc('#2FBF5B'), 0.3, 0.4), (0.035, 0.18, 0.07), (MX0 - 0.012, MY0 + 0.15, 1.43), 0.01)
    plate = bpy.data.meshes.new('tt'); bm = bmesh.new(); bmesh.ops.create_cone(bm, cap_ends=True, segments=48, radius1=0.3, radius2=0.3, depth=0.015); bm.to_mesh(plate); bm.free()
    o = link(bpy.data.objects.new('turntable', plate)); plate.materials.append(mat('tt_glass', hexc('#DDE8EE'), 0.1, 0.6)); o.location = TT - Vector((0, 0, 0.01))
    # door with window opening, hinged on the far side
    piv = link(bpy.data.objects.new('mw_door', None)); piv.location = (MX0, MY1, 0); W['door'] = piv
    dw = MY1 - (MY0 + 0.3)
    for (sy, sz, y, z) in ((dw, 0.1, -dw / 2, MZ1 - 0.05), (dw, 0.13, -dw / 2, MZ0 + 0.065), (0.09, MZ1 - MZ0, -0.045, (MZ0 + MZ1) / 2), (0.12, MZ1 - MZ0, -dw + 0.06, (MZ0 + MZ1) / 2)):
        b = box('mw_door_f', body, (0.05, sy, sz), (-0.025, y, z), 0.012); b.parent = piv
    for (sy, sz, y, z) in ((dw - 0.2, 0.03, -dw / 2 + 0.005, MZ1 - 0.11), (dw - 0.2, 0.03, -dw / 2 + 0.005, MZ0 + 0.14), (0.03, MZ1 - MZ0 - 0.25, -0.1, (MZ0 + MZ1) / 2), (0.03, MZ1 - MZ0 - 0.25, -dw + 0.13, (MZ0 + MZ1) / 2)):
        b = box('mw_win_trim', dark, (0.06, sy, sz), (-0.03, y, z), 0.005); b.parent = piv
    h = box('mw_handle', chrome, (0.05, 0.03, 0.4), (-0.07, -dw + 0.06, (MZ0 + MZ1) / 2), 0.012); h.parent = piv
    W['lamp_m'] = mat('mw_lamp', hexc('#FFE3A3'), 0.5, emit=0.0)
    box('mw_lamp', W['lamp_m'], (0.3, 0.2, 0.01), ((MX0 + MX1) / 2, 2.3, MZ1 - 0.056), 0)
    L = bpy.data.lights.new('mw_light', 'POINT'); L.energy = 0; L.shadow_soft_size = 0.1; L.color = hexc('#FFD98A')
    W['light'] = link(bpy.data.objects.new('mw_light', L)); W['light'].location = ((MX0 + MX1) / 2, 2.3, 1.85)
    return W

def build_props():
    P = {}
    skin = mat('grape_skin', hexc('#A9D64B'), 0.25, 0.5, sss=0.25); flesh = mat('grape_flesh', hexc('#E3F2A8'), 0.35, 0.4, sss=0.3)
    P['grape'] = build_grape('a', skin, flesh)
    kn = link(bpy.data.objects.new('knife', None)); P['knife'] = kn
    b = box('blade', mat('steel', hexc('#D8DDE3'), 0.15, 0.95), (0.42, 0.012, 0.09), (0.3, 0, 0), 0.004); b.parent = kn
    hd = box('knife_handle', mat('knife_wood', hexc('#5A3420'), 0.5), (0.18, 0.04, 0.06), (0.0, 0, 0), 0.015); hd.parent = kn
    bunch = link(bpy.data.objects.new('bunch', None)); P['bunch'] = bunch; rnd = random.Random(4)
    for i in range(16):
        layer = i // 5; ang = i * 2.4
        rr = 0.17 - 0.035 * layer
        s = sphere(f'bg{i}', skin, 1, 24); s.parent = bunch; s.scale = (GR * 1.1,) * 3
        s.location = (rr * math.cos(ang) * 0.6, rr * math.sin(ang) * 0.6, -0.1 - 0.12 * layer - rnd.random() * 0.04)
    st = curve_line('stem', mat('stem', hexc('#6B4A22'), 0.6), [(0, 0, 0.05), (0.02, 0, -0.1), (0, 0.01, -0.3)], 0.012); st.parent = bunch
    # plasma: layered glow shells + a coloured light
    P['plasma'] = []
    for k, (col, st_) in enumerate((('#FFD9FF', 6.0), ('#E07BFF', 3.5), ('#8A4DFF', 2.2))):
        m, em = glow_mat(f'plasma{k}', hexc(col), st_); o = sphere(f'plasma{k}', m, 1, 32); P['plasma'].append((o, em, st_))
    L = bpy.data.lights.new('plasma_light', 'POINT'); L.color = hexc('#D58BFF'); L.shadow_soft_size = 0.05; P['plight'] = link(bpy.data.objects.new('plasma_light', L))
    # sparks / electrons, energy rings, hotspot
    em_c = mat('electron', hexc('#7FE7FF'), 0.3, emit=12.0)
    P['electrons'] = [sphere(f'el{i}', em_c, 1, 12) for i in range(12)]
    ring_m = mat('ring', hexc('#6FE3FF'), 0.3, emit=6.0); P['rings'] = []
    for i in range(3):
        cu = bpy.data.curves.new(f'ring{i}', 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = 0.004; sp = cu.splines.new('POLY'); sp.points.add(47)
        for j, p in enumerate(sp.points): a = j / 48 * 2 * math.pi; p.co = (math.cos(a), math.sin(a), 0, 1)
        sp.use_cyclic_u = True; o = link(bpy.data.objects.new(f'ring{i}', cu)); cu.materials.append(ring_m); P['rings'].append(o)
    hm, hem = glow_mat('hotspot', hexc('#FFFFFF'), 25.0); P['hot'] = (sphere('hotspot', hm, 1, 24), hem)
    smoke = mat('smoke', hexc('#6E6A70'), 0.9, 0.05); P['smoke'] = mball('Smoke', smoke, 0.05); P['puff'] = mball('Puff', mat('puff', hexc('#8A858C'), 0.9, 0.05), 0.03)
    return P

def build():
    clear(); s = bpy.context.scene
    s.render.engine = 'CYCLES'; s.cycles.device = 'CPU'; s.cycles.samples = int(os.environ.get('SAMPLES', 8)); s.cycles.use_denoising = True
    s.cycles.denoiser = 'OPENIMAGEDENOISE'; s.cycles.denoising_prefilter = 'FAST'; s.cycles.adaptive_threshold = 0.1; s.cycles.caustics_reflective = s.cycles.caustics_refractive = False
    s.cycles.max_bounces = 4; s.cycles.diffuse_bounces = 2; s.cycles.glossy_bounces = 1; s.cycles.transmission_bounces = 0; s.cycles.transparent_max_bounces = 8
    s.render.resolution_x, s.render.resolution_y = 1080, 1920; s.render.resolution_percentage = int(os.environ.get('PCT', 67))
    s.view_settings.view_transform = 'Standard'; s.render.image_settings.file_format = 'PNG'
    w = bpy.data.worlds.new('w'); s.world = w; w.use_nodes = True; bg = w.node_tree.nodes['Background']; bg.inputs[0].default_value = (*hexc('#FFE9C7'), 1); bg.inputs[1].default_value = 0.75
    sun = bpy.data.lights.new('sun', 'SUN'); sun.energy = 3.0; sun.angle = math.radians(6); sun.color = hexc('#FFF1D6')
    so = link(bpy.data.objects.new('sun', sun)); so.rotation_euler = (math.radians(52), 0, math.radians(-38))
    fill = bpy.data.lights.new('fill', 'AREA'); fill.energy = 450; fill.size = 6; fill.color = hexc('#CFE3FF')
    fo = link(bpy.data.objects.new('fill', fill)); fo.location = (-3, -6, 5); fo.rotation_euler = (math.radians(55), 0, math.radians(-25))
    S = build_kitchen()
    for o in bpy.data.objects:                       # this episode keeps the swinging door shut and out of the way
        if o.name.startswith(('door', 'kickplate')): pass
    S.update(build_microwave()); P = build_props(); F = build_fumble()
    cam = bpy.data.cameras.new('cam'); cam.lens = 30; cam.clip_start = 0.02; co = link(bpy.data.objects.new('cam', cam)); s.camera = co
    return s, S, P, F, co

# ------------------------------------------------------------------ acting
def fumble_pose(t):
    st = story_t(t); tt = t
    d = dict(t=tt, yaw=0.0, mood='cheeky', mouth=0.15, look=(0, 0))
    x, y = -3.05, 2.0
    if st < T_CHOP - 0.5:                                 # eyes the grape, raises the knife
        d.update(arms='swing', hand=(0.75, -0.2, 2.0 + 0.1 * math.sin(tt * 6)), mood='smug', mouth=0.3, tilt=-0.25)
    elif st < T_CHOP + 0.5:                               # CHOP
        u = lin(st, T_CHOP - 0.5, T_CHOP); dn = u ** 3
        d.update(hand=(0.8, -0.18, 2.0 - 0.6 * dn), mood='hunt' if st < T_CHOP else 'happy', mouth=0.1 if st < T_CHOP else 0.6, tilt=-0.35, pop=0.25 if st > T_CHOP else 0)
    elif st < T_IN:                                       # picks it up, steps to the open microwave, pops it in
        u = ease(lin(st, T_CHOP + 0.5, T_IN)); x = -3.05 + 0.3 * u
        d.update(hand=(0.8 - 0.1 * u, -0.15 + 0.25 * u, 1.45 + 0.3 * math.sin(u * math.pi)), lean=0.25 * u, mood='happy', mouth=0.4, tilt=-0.2)
    elif st < T_START + 0.4:                              # shuts the door, jabs START
        x = -2.75; u = lin(st, T_IN, T_SHUT)
        if st < T_SHUT: hand = (1.2, 0.1, 1.5)
        else: hand = (1.12, -0.12 - 0.06 * ease(lin(st, T_SHUT, T_START)), 1.45 + 0.04 * math.sin(lin(st, T_START - 0.15, T_START + 0.1) * math.pi))
        d.update(hand=hand, lean=0.3, mood='smug', mouth=0.3, tilt=-0.15)
    elif st < T_BOOM:                                     # leans in, nose to the window
        u = ease(lin(st, T_START + 0.4, T_START + 1.3)); x = -2.75 - 0.25 * u
        d.update(lean=0.4 * u, crouch=0.45 * u, tilt=0.3 * u, arms='hips', mood='cheeky', mouth=0.25, look=(0, 0.2))
        if st > T_SPARK: d.update(pop=min(1.0, 0.4 + 0.6 * lin(st, T_PLASMA, T_PLASMA + 0.15)) if st > T_PLASMA else 0.3, mood='shock', mouth=0.9 if st > T_PLASMA else 0.45,
                                  frazzle=0.45 * lin(st, T_PLASMA, T_PLASMA + 0.6) + 0.06 * math.sin(tt * 40) * (st > T_PLASMA), arms='hips',
                                  yaw=1.12 * ease(lin(st, T_PLASMA + 0.3, T_PLASMA + 0.55)), lean=0.4 * u * (1 - 0.6 * ease(lin(st, T_PLASMA + 0.3, T_PLASMA + 0.55))),
                                  sq=(1, 1, 1 + 0.05 * math.sin(tt * 30)) if st > T_PLASMA else (1, 1, 1))
    else:                                                 # BOOM: blown back, sooty, frazzled
        u = lin(st, T_BOOM, T_BOOM + 0.35); x = -3.0 - 0.55 * ease(u) ** 0.7
        wob = math.exp(-(st - T_BOOM) * 3) * math.sin((st - T_BOOM) * 18)
        d.update(lean=-0.35 * math.sin(u * math.pi) + 0.08 * wob, tilt=0.0, frazzle=1.0, mood='dizzy' if st < 19.6 else 'shock', mouth=0.3, blink=0.0, arms='up' if st < 18.7 else 'swing')
        if st > 19.1 and st < 19.6: d.update(mouth=0.8, sq=(1, 1, 0.93 + 0.07 * math.cos((st - 19.1) * 25)))     # cough
        if st > 20.3:                                     # turns to us
            v = ease(lin(st, 20.3, 20.9)); d['yaw'] = 1.05 * v; d['mood'] = 'shock'; d['look'] = (0, 0); d['blink'] = 1.0 if 20.5 < st < 20.62 else 0.0
        if st > T_NOD:                                    # solemn nod
            d['tilt'] = -0.18 * math.sin(lin(st, T_NOD, T_NOD + 0.9) * math.pi * 2) ** 2; d['mood'] = 'hunt'; d['mouth'] = 0.1
        if st > T_BUNCH - 0.6:                            # sly look... and the whole bunch comes out
            d['look'] = (-1 if st < T_BUNCH else 0, 0); d['mood'] = 'smug'; d['mouth'] = 0.35 + 0.35 * lin(st, T_BUNCH, T_BUNCH + 0.3)
            r = ease(lin(st, T_BUNCH - 0.1, T_BUNCH + 0.3)); d['hand2'] = (0.12 * r - 0.1 * (1 - r), 0.5 + 0.08 * r, 1.4 + 0.75 * r)
            d['tilt'] = 0.08 * math.sin(max(0, st - T_BUNCH - 0.3) * 9)
            d['brow_wiggle'] = st
    return d, x, y

def camera(co, t, hp=None):
    cam = co.data
    def look(eye, tgt, lens):
        co.location = eye; co.rotation_euler = (Vector(tgt) - Vector(eye)).to_track_quat('-Z', 'Y').to_euler(); cam.lens = lens
    sh = Vector((0, 0, 0)); st = story_t(t)
    if st > T_PLASMA and st < T_FLASH: sh += Vector((0.012 * math.sin(t * 61), 0, 0.012 * math.cos(t * 53)))
    if t > T_BOOM: k = math.exp(-(t - T_BOOM) * 5); sh += Vector((0.09 * k * math.sin(t * 70), 0, 0.07 * k * math.cos(t * 63)))
    if in_hook(t):                    # inside the microwave, fireball in front, his face in the window
        u = ease(t / 2.6); look(Vector((-1.56 + 0.03 * u, 2.0, 1.7 - 0.03 * u)) + sh * 0.4, (TT.x, TT.y, TT.z + 0.14), 22 + 6 * u)
    elif t < 5.6:                     # wide: chop, pop in, start
        look(Vector((-1.7, -2.6, 2.45)), (-2.25, 2.0, 1.7), 30)
    elif t < 10.9:                    # he leans in: mid shot, slow push
        u = ease(lin(t, 5.6, 10.9)); wv = 0.6 + 0.32 * lin(t, T_PLASMA + 0.3, T_PLASMA + 0.6); tg = hp * wv + WIN * (1 - wv)
        look(Vector((-1.05 - 0.15 * u, -0.45 + 0.45 * u, 2.15)) + sh, (tg.x, tg.y, tg.z - 0.05), 26 + 4 * u)
    elif t < T_BOOM - 0.8:            # macro inside: halves, rings, hotspot, electrons
        u = ease(lin(t, 10.9, T_BOOM - 0.8)); look(Vector((-1.52 + 0.05 * u, 2.02 + 0.03 * u, 1.62 - 0.06 * u)) + sh * 0.3, (TT.x, TT.y, TT.z + 0.06), 32 + 10 * u)
    elif t < 21.0:                    # wide: boom
        look(Vector((-1.9, -2.9, 2.5)) + sh, (-2.4, 2.0, 1.75), 28)
    else:                             # medium on sooty Fumble: nod, then the bunch
        u = ease(lin(t, 21.0, DURATION)); look(Vector((-3.35, -1.3 + 0.35 * u, 2.4)), (-3.45, 2.05, 2.15), 32 + 5 * u)

def frame(s, S, P, F, co, t):
    st = story_t(t)
    d, x, y = fumble_pose(t); d.pop('brow_wiggle', None); pose_fumble(F, x=x, **d); F.root.location.y = y
    for o in [F.root] + list(F.root.children_recursive): o.hide_render = (10.9 <= t < T_BOOM - 0.8) or in_hook(t)
    # soot after the boom
    skin = bpy.data.materials['f_skin'].node_tree.nodes['Principled BSDF']; soot = 0.0 if in_hook(t) else ease(lin(st, T_BOOM, T_BOOM + 0.08))
    skin.inputs['Base Color'].default_value = (*[a + (b - a) * soot for a, b in zip(hexc('#F1C3A0'), hexc('#3A3436'))], 1)
    # microwave door: open at the start of the chop shot, shut at T_SHUT, blown open at the boom
    if st < T_IN + 0.05: da = -1.7
    elif st < T_SHUT: da = -1.7 * (1 - ease(lin(st, T_IN + 0.05, T_SHUT)))
    elif st < T_BOOM: da = 0.008 * math.sin(t * 90) * (st > T_PLASMA)
    else: k = st - T_BOOM; da = -min(2.3, 2.3 * ease(k / 0.12)) + 0.15 * math.exp(-k * 4) * math.sin(k * 30)
    S['door'].rotation_euler = (0, 0, da)
    on = T_START < st < T_BOOM
    S['lamp_m'].node_tree.nodes['Principled BSDF'].inputs['Emission Strength'].default_value = 1.5 if on else 0.0
    S['lamp_m'].node_tree.nodes['Principled BSDF'].inputs['Emission Color'].default_value = (*hexc('#FFE3A3'), 1)
    S['light'].data.energy = 6.0 if on else 0.0
    S['start_btn'].location.x = MX0 - 0.012 + (0.012 if T_START - 0.05 < st < T_START + 0.12 else 0)
    bpy.context.view_layer.update()
    hw = [F.root.matrix_world @ F.hands_local[k] for k in range(2)]
    # grape: whole on the table -> chopped -> in hand -> open on the turntable
    G = P['grape']; table_spot = Matrix.Translation((-2.2, 1.9, 1.31 + GR))
    if st < T_CHOP: set_grape(G, table_spot, 0.0)
    elif st < T_CHOP + 0.5: set_grape(G, table_spot, 0.35 * ease(lin(st, T_CHOP, T_CHOP + 0.15)))
    elif st < T_IN:
        u = lin(st, T_CHOP + 0.5, T_CHOP + 0.7)
        set_grape(G, Matrix.Translation(table_spot.translation.lerp(hw[0] + Vector((0.04, 0, 0.05)), ease(u))) @ Euler((0, 0, 0.6)).to_matrix().to_4x4(), 0.35)
    else: set_grape(G, Matrix.Translation(TT + Vector((0, 0, GR))) @ Euler((0, 0, math.pi / 2)).to_matrix().to_4x4(), math.pi / 2 - 0.05)
    G['root'].hide_render = st > T_BOOM
    for o in G['root'].children_recursive: o.hide_render = st > T_BOOM
    # knife in hand until the grape is picked up
    kn = P['knife']; kv = st < T_CHOP + 0.55
    kn.matrix_world = Matrix.Translation(hw[0]) @ Euler((0, 0.35 + (0.5 if T_CHOP - 0.1 < st < T_CHOP + 0.3 else 0), 0.25)).to_matrix().to_4x4()
    for o in [kn] + list(kn.children): o.hide_render = not kv
    # bunch of grapes from behind his back
    bv = st > T_BUNCH - 0.1; b = P['bunch']; b.matrix_world = Matrix.Translation(hw[1] + Vector((0, 0, 0.0))) @ Euler((0, 0.0, 0.3 * math.sin(t * 7) * (st > T_BUNCH + 0.3))).to_matrix().to_4x4()
    for o in [b] + list(b.children_recursive): o.hide_render = not bv
    # plasma fireball
    pc = TT + Vector((0, 0, 0.17)); pon = lin(st, T_PLASMA, T_PLASMA + 0.25) if st < T_BOOM else 0.0
    if in_hook(t): pon = 1.0
    if T_SPARK < st < T_PLASMA: pon = 0.12 * (math.sin(t * 97) > 0.2)
    for k, (o, em, base) in enumerate(P['plasma']):
        r = (0.05 + 0.05 * k) * (0.85 + 0.18 * math.sin(t * (23 + 7 * k) + k) + 0.08 * math.sin(t * 61 + 2 * k)) * (0.4 + 0.6 * pon)
        o.location = pc + Vector((0.01 * math.sin(t * 17 + k), 0.01 * math.cos(t * 13 + k), 0.02 * k + 0.015 * math.sin(t * 9))); o.scale = (r, r, r * 1.25)
        em.inputs['Strength'].default_value = base * pon * (0.8 + 0.3 * math.sin(t * 41 + k)); o.hide_render = pon <= 0.001 or (10.9 <= t < T_BOOM - 0.8)
    P['plight'].location = pc; P['plight'].data.energy = (60 * pon * (0.8 + 0.3 * math.sin(t * 37))) if not (10.9 <= t < T_BOOM - 0.8) else 0.0
    # macro explanation: energy rings squeeze into the gap, hotspot grows, electrons fly off, white flash
    mac = 10.9 <= t < T_BOOM - 0.8; gap = TT + Vector((0, 0, GR * 1.05))
    for i, o in enumerate(P['rings']):
        ph = ((t - 11.0) * 0.6 + i / 3) % 1.0; rr = 0.32 * (1 - ph) + 0.004
        o.location = gap; o.scale = (rr, rr, rr); o.rotation_euler = (0, math.pi / 2 - 0.35, 0.55)
        o.hide_render = not (mac and 11.0 < t < 16.6)
    ho, hem = P['hot']; hs = lin(t, 12.6, 15.6)
    ho.location = gap; ho.scale = (0.006 + 0.03 * hs ** 1.5 + 0.08 * lin(t, 16.9, T_FLASH) ** 2,) * 3; hem.inputs['Strength'].default_value = 8 + 40 * hs + 200 * lin(t, 16.9, T_FLASH)
    ho.hide_render = not (mac and t > 12.0)
    rnd = random.Random(7)
    for i, o in enumerate(P['electrons']):
        a = rnd.random() * 2 * math.pi; e = rnd.random() * 1.2 + 0.2; spd = 0.25 + 0.2 * rnd.random(); t0 = 15.2 + 0.12 * i
        k = t - t0; vis = mac and k > 0
        if T_SPARK < st < T_PLASMA + 0.4 and not mac: vis = True; k = (t * 3 + i * 0.37) % 0.4; t0 = 0
        dirv = Vector((math.cos(a) * math.cos(e), math.sin(a) * math.cos(e), math.sin(e)))
        base = gap if mac else TT + Vector((0, 0, GR))
        o.location = base + dirv * (k % 0.9) * spd * (1 if mac else 0.6); o.scale = (0.006,) * 3 if mac else (0.01,) * 3; o.hide_render = not vis
    # smoke after the boom, cough puff
    sm = P['smoke']; sm.data.elements.clear(); k = st - T_BOOM
    if k > 0 and not in_hook(t):
        rnd = random.Random(3)
        for i in range(14):
            a = rnd.random() * 2 * math.pi; sp = 0.6 + rnd.random(); g = 1 - math.exp(-k * 3)
            c = Vector((MX0 - 0.15 - 0.9 * g * sp * abs(math.cos(a)), 2.2 + 0.6 * g * math.sin(a), 1.7 + 0.4 * g * sp + 0.25 * k))
            r = (0.12 + 0.2 * g) * max(0.0, 1 - k / 3.2)
            if r > 0.02: el(sm, 'BALL', c, r)
    pf = P['puff']; pf.data.elements.clear(); k = st - 19.15
    if 0 < k < 1.4 and not in_hook(t):
        bpy.context.view_layer.update(); hp = F.head.matrix_world @ Vector((0.4, 0, -0.22))
        for i in range(4): el(pf, 'BALL', hp + Vector((0.15 * k * (1 + i * 0.3), -0.25 * k * i * 0.2, 0.2 * k * i * 0.3)), (0.05 + 0.03 * i) * (1 - k / 1.4) * min(1, k * 8))
    bpy.context.view_layer.update(); camera(co, t, F.head.matrix_world.translation.copy())

def cues():
    C = [(0.0, 'plasma_buzz', 0.9), (T_CHOP, 'chop', 1.0), (T_CHOP + 0.62, 'pickup', 0.6), (T_SHUT, 'mw_door', 1.0), (T_START, 'beep', 0.9),
         (T_START + 0.12, 'hum', 1.0), (T_SPARK, 'crackle', 0.8), (T_PLASMA, 'ignite', 1.0), (T_PLASMA + 0.05, 'plasma_buzz', 1.0), (T_PLASMA + 0.1, 'horn', 0.7),
         (11.0, 'tension', 0.8), (15.2, 'zaps', 0.8), (T_FLASH - 0.1, 'swell', 0.8), (T_BOOM, 'boom', 1.0), (T_BOOM + 0.05, 'mw_door', 0.8), (T_BOOM + 0.25, 'step_cat_soft', 0.8),
         (T_BOOM + 0.5, 'step_cat_soft', 0.7), (T_BOOM + 0.9, 'stars', 0.6), (19.15, 'cough', 1.0), (20.9, 'blink', 0.7), (T_NOD + 0.2, 'nod', 0.6),
         (T_BUNCH, 'ta_da', 0.9), (T_BUNCH + 0.4, 'giggle', 0.6)]
    P = [(T_PLASMA, 'ZZZAP!', 0.5, 0.2, 140), (T_BOOM, 'BOOM!', 0.5, 0.24, 190)]
    return dict(duration=DURATION, fps=FPS, twos=TWOS, cues=sorted(C), pow=P, vo=VO, voice='en-US-ChristopherNeural', rate='+6%', hook_cut=2.6)

if __name__ == '__main__':
    if '--cues' in sys.argv:
        import json; json.dump(cues(), open(sys.argv[-1], 'w'), indent=1); sys.exit(0)
    out, i0, i1 = sys.argv[-3], int(sys.argv[-2]), int(sys.argv[-1])
    os.makedirs(out, exist_ok=True)
    s, S, P, F, co = build(); n = int(round(DURATION * FPS))
    only = os.environ.get('FRAMES')
    for i in ([int(v) for v in only.split(',')] if only else range(i0, min(i1, n))):
        if TWOS and i % 2 and not only: continue
        frame(s, S, P, F, co, i / FPS)
        s.render.filepath = os.path.join(out, f'f{i:04d}.png'); bpy.ops.render.render(write_still=True)
