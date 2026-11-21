"""Kinda Wild Films - 'He Held In A Sneeze'. Zack D. Films format: realistic 3D person, x-ray cutaways, macro, calm VO.
blender -b -P ep_sneeze.py -- outdir i0 i1      (renders frames i0..i1-1)
blender -b -P ep_sneeze.py -- --cues out.json   (timing / audio / caption data)"""
import bpy, sys, os, math, json, random
from mathutils import Vector, Euler
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
FPS = 24; DUR = 29.8
VO = [(0.15, "He held in a sneeze so hard that it ripped a hole straight through his windpipe."),
      (4.24, "He was driving when the sneeze hit, so he pinched his nose and clamped his mouth shut."),
      (8.69, "You see, a sneeze blasts air out of your lungs, and with nowhere to go, the pressure in his airway shot up to about twenty times normal."),
      (16.27, "That tore a tiny hole in his windpipe, and air leaked into his neck."),
      (20.02, "When doctors pressed on it, they could hear it crackling."),
      (23.06, "Luckily, the hole healed on its own in five weeks."),
      (26.25, "So next time, just let it out.")]
SHOTS = [(0.0, 'hook_face'), (1.9, 'macro_tear'), (4.2, 'car_side'), (6.1, 'car_pinch'), (8.7, 'xray_chest'), (11.4, 'xray_head'),
         (13.6, 'xray_pressure'), (16.2, 'macro_leak'), (20.0, 'hospital'), (22.9, 'macro_heal'), (26.2, 'car_relax'), (27.7, 'car_sneeze')]
CUES = [(0.0, 'engine', 0.6), (1.9, 'rip', 1.0), (2.4, 'thud', 0.8), (4.2, 'engine', 0.7), (5.0, 'sniff', 0.8), (6.5, 'pinch', 0.7), (7.0, 'puff', 0.6),
        (8.7, 'rush', 0.8), (11.4, 'bounce', 0.7), (13.6, 'pressure', 0.9), (16.4, 'rip', 0.9), (17.0, 'bubbles', 0.8), (20.6, 'crackle', 1.0), (21.6, 'crackle', 1.0),
        (23.3, 'heal', 0.6), (26.2, 'engine', 0.6), (27.0, 'inhale', 0.9), (28.0, 'sneeze', 1.0)]
def shot_at(t):
    cur = SHOTS[0]
    for s in SHOTS:
        if t >= s[0]: cur = s
    nxt = next((s[0] for s in SHOTS if s[0] > cur[0]), DUR)
    return cur[1], t - cur[0], nxt - cur[0]
def ease(u): u = min(1, max(0, u)); return u * u * (3 - 2 * u)
def ramp(t, a, b): return ease((t - a) / (b - a)) if b > a else float(t >= a)

def cues():
    words = []
    return dict(duration=DUR, fps=FPS, vo=VO, voice='en-US-ChristopherNeural', rate='+6%', cues=CUES, shots=SHOTS, music_gain=0.42)

if '--cues' in sys.argv:
    json.dump(cues(), open(sys.argv[-1], 'w'), indent=1); sys.exit(0)

import person as P
S = bpy.context.scene
bpy.ops.wm.read_factory_settings(use_empty=True); S = bpy.context.scene
def mat(name, col, rough=0.5, metal=0.0, emit=None, es=1.0, alpha=1.0, trans=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True; b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*col, 1); b.inputs['Roughness'].default_value = rough; b.inputs['Metallic'].default_value = metal
    if emit: b.inputs['Emission Color'].default_value = (*emit, 1); b.inputs['Emission Strength'].default_value = es
    if alpha < 1: b.inputs['Alpha'].default_value = alpha
    if trans: b.inputs['Transmission Weight'].default_value = trans
    return m
def obj_of(prim, name, mt=None, **kw):
    getattr(bpy.ops.mesh, 'primitive_' + prim + '_add')(**kw); o = bpy.context.object; o.name = name
    if mt: o.data.materials.append(mt)
    return o
def smooth(o):
    for p in o.data.polygons: p.use_smooth = True
def bevel_box(name, size, loc, mt, bev=0.02, rot=(0, 0, 0)):
    o = obj_of('cube', name, mt, size=1, location=loc, rotation=rot); o.scale = size
    m = o.modifiers.new('b', 'BEVEL'); m.width = bev; m.segments = 4; m.limit_method = 'NONE'; smooth(o)
    return o
def coll(name):
    c = bpy.data.collections.new(name); S.collection.children.link(c); return c
def into(c, objs):
    for o in objs:
        for u in list(o.users_collection): u.objects.unlink(o)
        c.objects.link(o)

# ---------------- people ----------------
import cast as C   # new cast for every story (Zack D. style); fixed seeds keep shards identical
ned = P.build_person('Ned', **C.cast({'gender': 'm', 'age': 'middle', 'race': 'caucasian', 'build': 'avg'}, 'sneeze', P.MP))
doc = P.build_person('Doc', **C.cast({'gender': 'f', 'age': 'young', 'race': 'asian', 'build': 'slim', 'hair': 'ponytail01', 'tee': 'white'}, 'sneeze-doc', P.MP))
def sit(p):
    for s in 'LR':
        p.rot(f'upperleg01.{s}', (-85, 0, 0)); p.rot(f'lowerleg01.{s}', (88, 0, 0))
P.sit = sit
sit(ned); ned.place((0, 0, 0)); bpy.context.view_layer.update()
pelvis = ned.bone_world('spine05')
# glove material on the doctor's hands (faces weighted to wrist/finger bones)
glove = mat('glove', (0.16, 0.38, 0.85), 0.35)
db = doc.body; db.data.materials.append(glove); gi = len(db.data.materials) - 1
groups = {g.index for g in db.vertex_groups if g.name.startswith(('wrist', 'finger', 'metacarpal'))}
hand_v = set()
for v in db.data.vertices:
    if sum(g.weight for g in v.groups if g.group in groups) > 0.5: hand_v.add(v.index)
for poly in db.data.polygons:
    if sum(1 for i in poly.vertices if i in hand_v) >= 3: poly.material_index = gi
doc.place((0.52, -0.08, 0.0), 90 + 25)

# ---------------- car set ----------------
C_CAR = coll('car')
seat_m = mat('seat', (0.035, 0.035, 0.04), 0.8); dash_m = mat('dash', (0.05, 0.05, 0.055), 0.55); trim_m = mat('trim', (0.18, 0.18, 0.19), 0.4)
hz = ned.bone_world('head').z; cz = ned.bone_world('spine03').z
seat = [bevel_box('seat_base', (0.55, 0.55, 0.14), (0, 0.05, pelvis.z - 0.12), seat_m, 0.05),
        bevel_box('seat_back', (0.55, 0.14, 0.75), (0, 0.32, pelvis.z + 0.32), seat_m, 0.05, (math.radians(-12), 0, 0)),
        bevel_box('headrest', (0.28, 0.12, 0.2), (0, 0.42, hz + 0.02), seat_m, 0.04)]
dash = bevel_box('dash', (2.2, 0.6, 0.35), (0.3, -0.95, cz + 0.05), dash_m, 0.08)
wheel = obj_of('torus', 'wheel', trim_m, major_radius=0.19, minor_radius=0.017, location=(0, -0.52, cz + 0.12), rotation=(math.radians(65), 0, 0)); smooth(wheel)
hub = obj_of('cylinder', 'hub', dash_m, radius=0.06, depth=0.05, location=(0, -0.55, cz + 0.11), rotation=(math.radians(65), 0, 0)); smooth(hub)
col = obj_of('cylinder', 'column', dash_m, radius=0.035, depth=0.4, location=(0, -0.7, cz + 0.02), rotation=(math.radians(65), 0, 0))
door = bevel_box('door', (0.08, 1.6, 0.6), (-0.42, -0.2, pelvis.z + 0.18), trim_m, 0.03)
sill = bevel_box('sill', (0.1, 1.6, 0.05), (-0.42, -0.2, pelvis.z + 0.49), dash_m, 0.02)
roof = bevel_box('roof', (2.0, 2.2, 0.05), (0.3, -0.1, hz + 0.27), mat('headliner', (0.55, 0.53, 0.5), 0.9), 0.02)
pil = [bevel_box('apillar', (0.07, 0.07, 0.75), (-0.42, -0.95, hz - 0.12), dash_m, 0.02, (math.radians(-35), 0, 0)),
       bevel_box('bpillar', (0.08, 0.1, 0.75), (-0.42, 0.45, hz - 0.1), dash_m, 0.02)]
# outside world: moving scenery planes (emission, defocused)
def scenery(name, loc, rot, size, seed):
    o = obj_of('plane', name, None, size=1, location=loc, rotation=rot); o.scale = (size[0], size[1], 1)
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial'); em = nt.nodes.new('ShaderNodeEmission'); em.inputs['Strength'].default_value = 1.6
    tc = nt.nodes.new('ShaderNodeTexCoord'); mp = nt.nodes.new('ShaderNodeMapping'); mp.name = 'map'
    nz = nt.nodes.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 3.0; nz.inputs['Detail'].default_value = 6
    cr = nt.nodes.new('ShaderNodeValToRGB'); cr.color_ramp.elements[0].color = (0.10, 0.22, 0.08, 1); cr.color_ramp.elements[1].color = (0.55, 0.65, 0.35, 1)
    sep = nt.nodes.new('ShaderNodeSeparateXYZ'); sky = nt.nodes.new('ShaderNodeMath'); sky.operation = 'GREATER_THAN'; sky.inputs[1].default_value = 0.55
    mix = nt.nodes.new('ShaderNodeMix'); mix.data_type = 'RGBA'; mix.inputs['B'].default_value = (0.75, 0.85, 1.0, 1)
    L = nt.links.new; L(tc.outputs['UV'], mp.inputs['Vector']); L(mp.outputs['Vector'], nz.inputs['Vector']); L(nz.outputs['Fac'], cr.inputs['Fac'])
    L(tc.outputs['UV'], sep.inputs['Vector']); L(sep.outputs['Y'], sky.inputs[0]); L(sky.outputs[0], mix.inputs['Factor']); L(cr.outputs['Color'], mix.inputs['A'])
    L(mix.outputs['Result'], em.inputs['Color']); L(em.outputs[0], out.inputs[0]); o.data.materials.append(m); return o
side_out = scenery('side_out', (-2.2, -0.2, hz - 0.2), (math.radians(90), 0, math.radians(90)), (6, 3), 1)
front_out = scenery('front_out', (0.3, -4.0, hz - 0.2), (math.radians(90), 0, 0), (8, 4), 2)
rear_out = scenery('rear_out', (0.3, 3.0, hz), (math.radians(90), 0, math.radians(180)), (8, 4), 3)
into(C_CAR, seat + [dash, wheel, hub, col, door, sill, roof] + pil + [side_out, front_out, rear_out])

# ---------------- hospital set ----------------
C_HOS = coll('hospital')
wall = obj_of('plane', 'h_wall', mat('h_wall', (0.75, 0.8, 0.82), 0.7), size=8, location=(0, 1.6, 2), rotation=(math.radians(90), 0, 0))
curtain = obj_of('plane', 'h_curtain', mat('h_curt', (0.35, 0.62, 0.62), 0.8), size=1, location=(-1.2, 0.6, 1.3), rotation=(math.radians(90), 0, math.radians(70)))
curtain.scale = (1.6, 1.4, 1); sd = curtain.modifiers.new('w', 'WAVE'); sd.height = 0.05; sd.width = 0.25; sd.narrowness = 1.2; sd.use_y = False
bed = bevel_box('h_bed', (0.9, 1.9, 0.12), (0, 0.15, pelvis.z - 0.12), mat('h_bed', (0.92, 0.93, 0.95), 0.6), 0.05)
into(C_HOS, [wall, curtain, bed])

# ---------------- x-ray organs (follow the seated pose) ----------------
C_XR = coll('xray')
def glow(name, col, es, alpha=0.6):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial'); em = nt.nodes.new('ShaderNodeEmission'); em.inputs['Color'].default_value = (*col, 1); em.inputs['Strength'].default_value = es
    tr = nt.nodes.new('ShaderNodeBsdfTransparent'); lw = nt.nodes.new('ShaderNodeLayerWeight'); lw.inputs['Blend'].default_value = 0.35
    mx = nt.nodes.new('ShaderNodeMixShader'); mth = nt.nodes.new('ShaderNodeMath'); mth.operation = 'MULTIPLY_ADD'; mth.inputs[1].default_value = 1 - alpha; mth.inputs[2].default_value = alpha
    nt.links.new(lw.outputs['Facing'], mth.inputs[0]); nt.links.new(mth.outputs[0], mx.inputs[0]); nt.links.new(tr.outputs[0], mx.inputs[1]); nt.links.new(em.outputs[0], mx.inputs[2]); nt.links.new(mx.outputs[0], out.inputs[0])
    m.blend_method = 'BLEND' if hasattr(m, 'blend_method') else None; return m, em
xray_body, _ = glow('xray_body', (0.35, 0.65, 1.0), 1.4, 0.05)
fwd = Vector((0, -1, 0))
neck_top = ned.bone_world('neck03') + fwd * 0.045 + Vector((0, 0, -0.03))
neck_bot = ned.bone_world('spine05') + Vector((0, 0, 0))   # placeholder, replaced below
chest = ned.bone_world('spine02', tail=True)
tr_top = ned.bone_world('neck02') + fwd * 0.05
tr_bot = ned.bone_world('neck01') + fwd * 0.04 + Vector((0, 0, -0.09))
def tube(name, pts, r, mt):
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = r; cu.bevel_resolution = 6
    sp = cu.splines.new('BEZIER'); sp.bezier_points.add(len(pts) - 1)
    for bp_, p in zip(sp.bezier_points, pts): bp_.co = p; bp_.handle_left_type = bp_.handle_right_type = 'AUTO'
    o = bpy.data.objects.new(name, cu); S.collection.objects.link(o); o.data.materials.append(mt); return o
trach_m, trach_em = glow('trachea', (1.0, 0.75, 0.8), 2.2, 0.5)
lung_m, lung_em = glow('lungs', (1.0, 0.35, 0.45), 1.6, 0.35)
trachea = tube('trachea', [tr_top + Vector((0, 0, 0.05)), tr_top, tr_bot], 0.011, trach_m)
lungs = []
for sx in (-1, 1):
    c = tr_bot + Vector((sx * 0.085, 0.03, -0.1))
    l = obj_of('uv_sphere', f'lung{sx}', lung_m, radius=1, location=c, segments=32, ring_count=16); l.scale = (0.065, 0.06, 0.12); smooth(l); lungs.append(l)
    lungs.append(tube(f'bronch{sx}', [tr_bot, tr_bot + Vector((sx * 0.04, 0.01, -0.03)), c + Vector((-sx * 0.02, 0, 0.04))], 0.006, trach_m))
mouth_pt = ned.bone_world('head') + fwd * 0.1 + Vector((0, 0, -0.035))
nose_pt = ned.bone_world('head') + fwd * 0.115 + Vector((0, 0, 0.0))
air_m, air_em = glow('air', (0.6, 0.95, 1.0), 6.0, 0.95)
rnd = random.Random(7); parts = []
for i in range(60):
    o = obj_of('ico_sphere', f'air{i}', air_m, radius=0.0045, subdivisions=2, location=(0, 0, 0)); smooth(o); parts.append((o, rnd.random(), rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.random()))
fcur = bpy.data.curves.new('t20', 'FONT'); fcur.body = '20x'; fcur.extrude = 0.004; fcur.size = 0.07; fcur.align_x = 'CENTER'
label = bpy.data.objects.new('label20', fcur); S.collection.objects.link(label); label.data.materials.append(glow('lab', (1, 1, 1), 4, 1.0)[0])
label.location = tr_top + Vector((-0.06, -0.06, -0.06)); label.rotation_euler = (math.radians(90), 0, 0)
into(C_XR, [trachea] + lungs + [p[0] for p in parts] + [label])

# ---------------- macro windpipe set (far away at x=30) ----------------
C_MAC = coll('macro'); M0 = Vector((30, 0, 1.0))
wall_m = mat('trach_wall', (0.85, 0.45, 0.45), 0.25); wall_m.node_tree.nodes['Principled BSDF'].inputs['Subsurface Weight'].default_value = 0.4
wall_m.node_tree.nodes['Principled BSDF'].inputs['Subsurface Radius'].default_value = (0.2, 0.05, 0.03)
ring_m = mat('cart', (0.95, 0.85, 0.8), 0.3); ring_m.node_tree.nodes['Principled BSDF'].inputs['Subsurface Weight'].default_value = 0.5
inner_m = mat('inner', (0.35, 0.05, 0.06), 0.3)
tm = bpy.data.meshes.new('m_tube'); vs = []; fs = []; NA, NL = 96, 160
for j in range(NL + 1):
    x = -1.6 + 3.2 * j / NL
    for i in range(NA):
        a = 2 * math.pi * i / NA; rr = 0.35 + 0.014 * max(0.0, math.cos(2 * math.pi * (x - 0.09) / 0.18)) ** 2; vs.append((x, rr * math.sin(a), rr * math.cos(a)))
for j in range(NL):
    for i in range(NA): fs.append((j * NA + i, j * NA + (i + 1) % NA, (j + 1) * NA + (i + 1) % NA, (j + 1) * NA + i))
tm.from_pydata(vs, [], fs); tubeo = bpy.data.objects.new('m_tube', tm); S.collection.objects.link(tubeo); tubeo.location = M0; tubeo.data.materials.append(wall_m); smooth(tubeo)
so = tubeo.modifiers.new('s', 'SOLIDIFY'); so.thickness = 0.05; tubeo.data.materials.append(inner_m); so.material_offset = 1
cutter = obj_of('uv_sphere', 'm_cut', None, radius=1, location=M0 + Vector((0, -0.36, 0.0)), segments=32, ring_count=16); cutter.display_type = 'WIRE'; cutter.hide_render = True
bo = tubeo.modifiers.new('cut', 'BOOLEAN'); bo.object = cutter; bo.operation = 'DIFFERENCE'; bo.solver = 'FAST'
ss = tubeo.modifiers.new('sub', 'SUBSURF'); ss.levels = 0; ss.render_levels = 1
rings = []
for k in range(-8, 9):
    if k == 0: continue
    r = obj_of('torus', f'm_ring{k}', ring_m, major_radius=0.36, minor_radius=0.03, location=M0 + Vector((k * 0.18 - (0.09 if k > 0 else -0.09), 0, 0)), rotation=(0, math.radians(90), 0)); smooth(r); r.hide_render = True; rings.append(r)
tissue = obj_of('plane', 'm_bg', glow('tissue', (0.55, 0.12, 0.16), 0.5, 1.0)[0], size=12, location=M0 + Vector((0, 2.5, 0)), rotation=(math.radians(90), 0, 0))
bub_m = mat('bubble', (0.95, 0.95, 1.0), 0.05, trans=1.0)
bubbles = []
for i in range(26):
    o = obj_of('uv_sphere', f'bub{i}', bub_m, radius=1, location=M0, segments=24, ring_count=12); smooth(o); bubbles.append((o, rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.random(), rnd.uniform(0.02, 0.06)))
flash = bpy.data.lights.new('flash', 'POINT'); flash.color = (1, 0.15, 0.1); flash_o = bpy.data.objects.new('flash', flash); S.collection.objects.link(flash_o); flash_o.location = M0 + Vector((0, -0.7, 0))
fc2 = bpy.data.curves.new('t5', 'FONT'); fc2.body = '5 weeks'; fc2.extrude = 0.02; fc2.size = 0.22; fc2.align_x = 'CENTER'
label5 = bpy.data.objects.new('label5', fc2); S.collection.objects.link(label5); label5.data.materials.append(glow('lab5', (1, 1, 1), 3, 1.0)[0])
label5.location = M0 + Vector((0, -0.55, 0.55)); label5.rotation_euler = (math.radians(90), 0, 0)
into(C_MAC, [tubeo, cutter] + rings + [tissue] + [b[0] for b in bubbles] + [flash_o, label5])

# ---------------- droplets for the final sneeze ----------------
C_DROP = coll('drops'); drop_m = mat('drop', (0.9, 0.95, 1.0), 0.02, trans=1.0); drops = []
for i in range(110):
    o = obj_of('ico_sphere', f'drop{i}', drop_m, radius=1, subdivisions=2, location=(0, 0, 0)); smooth(o)
    a = rnd.uniform(-0.6, 0.6); b = rnd.uniform(-0.45, 0.35); sp = rnd.uniform(1.6, 3.2); drops.append((o, Vector((math.sin(a), -math.cos(a) * math.cos(b), math.sin(b))) * sp, rnd.uniform(0.004, 0.011)))
into(C_DROP, [d[0] for d in drops])

# ---------------- lights, world, cameras ----------------
def area(name, loc, e, size, colr, tgt):
    L = bpy.data.lights.new(name, 'AREA'); L.energy = e; L.size = size; L.color = colr; o = bpy.data.objects.new(name, L); S.collection.objects.link(o); o.location = loc
    o.rotation_euler = (Vector(tgt) - o.location).to_track_quat('-Z', 'Y').to_euler(); return o
head_c = ned.bone_world('head')
L_key = area('key', (0.6, -1.6, hz + 0.5), 180, 1.6, (1, 0.96, 0.9), head_c)
L_rim = area('rim', (-1.2, 0.3, hz + 0.3), 160, 0.8, (0.45, 0.65, 1.0), head_c)
L_fill = area('fill', (1.2, -0.4, hz - 0.2), 40, 1.5, (1, 0.9, 0.8), head_c)
L_mac = area('mac_key', tuple(M0 + Vector((-1.2, -2.0, 1.4))), 500, 2.5, (1, 0.95, 0.92), M0)
L_mac2 = area('mac_rim', tuple(M0 + Vector((1.5, 0.8, 1.0))), 300, 1.5, (0.5, 0.65, 1.0), M0)
W = bpy.data.worlds.new('w'); S.world = W; W.use_nodes = True; BG = W.node_tree.nodes['Background']
cam_d = bpy.data.cameras.new('cam'); CAM = bpy.data.objects.new('cam', cam_d); S.collection.objects.link(CAM); S.camera = CAM
S.render.engine = 'CYCLES'; S.cycles.samples = int(os.environ.get('SAMPLES', '32')); S.cycles.use_denoising = True; S.cycles.max_bounces = 6
S.cycles.transparent_max_bounces = 16; S.render.use_persistent_data = True
S.render.resolution_x, S.render.resolution_y = 1080, 1920; S.render.resolution_percentage = int(os.environ.get('PCT', '100'))
S.view_settings.view_transform = 'AgX'; S.view_settings.look = 'AgX - Medium High Contrast'
S.render.fps = FPS

orig_mats = {o.name: [s.material for s in o.material_slots] for o in ned.parts if o.type == 'MESH'}
def set_xray(on):
    for o in ned.parts:
        if o.type != 'MESH': continue
        if o is ned.body:
            for i, s in enumerate(o.material_slots): s.material = xray_body if on else orig_mats[o.name][i]
        else: o.hide_render = on
def show(colls_on):
    for c in (C_CAR, C_HOS, C_XR, C_MAC, C_DROP): c.hide_render = c not in colls_on
def doc_vis(v):
    for o in doc.parts: o.hide_render = not v
def look_at(pos, tgt, lens, fstop=2.8, focus=None, roll=0.0):
    CAM.location = pos; q = (Vector(tgt) - Vector(pos)).to_track_quat('-Z', 'Y'); CAM.rotation_euler = q.to_euler()
    if roll: CAM.rotation_euler.rotate_axis('Z', math.radians(roll))
    cam_d.lens = lens; cam_d.dof.use_dof = True; cam_d.dof.aperture_fstop = fstop; cam_d.dof.focus_distance = (Vector(focus or tgt) - Vector(pos)).length
def shake(t, amp, f=9.0):
    return Vector((math.sin(t * f * 1.3) * amp, math.sin(t * f * 0.7 + 1) * amp * 0.5, math.sin(t * f + 2) * amp))

EXPR_TARGETS = {}
def face(**vals):
    want = {}
    for nm, v in vals.items():
        for path, w in P.EXPR[nm]: want[path] = max(want.get(path, 0), v * w)
    for path, k in ned.keys.items(): k.value = want.get(path, 0.0)
def arms(t, pinch, wheel=True):
    wc = wheel_center()
    ned.reach('L', wc + Vector((0.16, 0.02, 0.05)), w=1.0 if wheel else 0.0, pole=ned.bone_world('lowerarm01.L') + Vector((0.5, 0.3, -0.6)))
    tgt_wheel = wc + Vector((-0.16, 0.02, 0.05)); tgt_nose = nose_pt + Vector((0.0, -0.07, -0.035))
    ned.reach('R', tgt_wheel.lerp(tgt_nose, pinch), w=1.0, pole=Vector((-0.55, -0.3, cz - 0.5)))
    P.fingers(ned, 'R', 0.35 + 0.4 * pinch, thumb=0.6 * pinch); P.fingers(ned, 'L', 0.6, thumb=0.3)
def wheel_center(): return wheel.location.copy()

def update(t):
    name, u, L = shot_at(t)
    xr = name.startswith('xray'); mac = name.startswith('macro'); hos = name == 'hospital'
    set_xray(xr); doc_vis(hos)
    show({C_CAR, C_DROP} if name.startswith(('car', 'hook')) else {C_XR} if xr else {C_MAC} if mac else {C_HOS})
    for o in (L_key, L_rim, L_fill): o.hide_render = mac
    for o in (L_mac, L_mac2): o.hide_render = not mac
    for o in ned.parts: 
        if mac and o.type == 'MESH': o.hide_render = True
    if not mac and not xr:
        for o in ned.parts:
            if o.type == 'MESH': o.hide_render = False
    BG.inputs[0].default_value = (0.01, 0.035, 0.12, 1) if xr else (0.05, 0.02, 0.03, 1) if mac else (0.6, 0.7, 0.85, 1)
    BG.inputs[1].default_value = 1.0 if xr else 0.3 if mac else 0.25
    for sc in (side_out, front_out, rear_out):
        sc.data.materials[0].node_tree.nodes['map'].inputs['Location'].default_value[0] = t * 0.9
    wheel.rotation_euler = (math.radians(65), math.sin(t * 0.8) * 0.06, 0)
    # ---- performance by time (continuous across shots) ----
    twitch = ramp(t, 4.9, 5.4) * (1 - ramp(t, 6.3, 6.6))
    pinch = ramp(t, 6.2, 6.9) * (1 - ramp(t, 26.3, 26.9)) + (1 - ramp(t, 1.85, 1.9)) * (t < 1.9)
    puff = max(ramp(t, 6.8, 7.3) * (1 - ramp(t, 26.3, 26.8)), float(t < 1.9))
    wide = max(ramp(t, 6.9, 7.4) * (1 - ramp(t, 26.3, 26.8)), float(t < 1.9))
    inhale = ramp(t, 27.0, 27.9) * (1 - ramp(t, 28.0, 28.1))
    blast = ramp(t, 28.0, 28.08) * (1 - ramp(t, 28.5, 29.0))
    relief = ramp(t, 28.9, 29.4)
    if hos: pinch = 0; puff = 0; wide = 0.4 + 0.4 * ramp(t, 20.6, 20.8)
    face(twitch=twitch, puff=puff * (1 + 0.15 * math.sin(t * 9)), wide=wide, open=max(inhale * 0.45, blast), squint=max(inhale * 0.6, blast), smile=relief * 0.5, worry=0.6 if hos else 0)
    arms(t, pinch, wheel=not hos)
    if hos:
        ned.reach('L', Vector((0.25, -0.1, pelvis.z + 0.05)), w=0.0); ned.reach('R', Vector((-0.25, -0.1, pelvis.z + 0.05)), w=0.0)
    head_back = -inhale * 14 + blast * 22
    ned.rot('head', (head_back - 4, 0, 0)); ned.rot('neck02', (head_back * 0.5, 0, 0)); ned.rot('spine02', (blast * 10 - inhale * 4, 0, 0))
    # doctor presses his neck
    if hos:
        press = 0.5 + 0.5 * max(math.exp(-((t - 20.7) / 0.18) ** 2), math.exp(-((t - 21.7) / 0.18) ** 2))
        neck_side = ned.bone_world('neck02') + Vector((0.055, -0.035, 0))
        doc.reach('R', neck_side + Vector((0.05 * (1 - press), -0.02, 0)), w=1.0, pole=doc.bone_world('lowerarm01.R') + Vector((0, 0.4, -0.5)))
        P.fingers(doc, 'R', 0.15, thumb=0.2)
    bpy.context.view_layer.update()
    # ---- x-ray dynamics ----
    if xr:
        squeeze = 1 - 0.18 * ramp(t, 8.8, 10.5)
        for l in lungs:
            if l.name.startswith('lung'): l.scale = (0.065 * squeeze, 0.06 * squeeze, 0.12 * (0.95 + 0.05 * squeeze))
        heat = ramp(t, 13.6, 15.0); pulse = 0.5 + 0.5 * math.sin(t * 14)
        trach_em.inputs['Color'].default_value = (1.0, 0.75 * (1 - heat) + 0.15 * heat, 0.8 * (1 - heat) + 0.1 * heat, 1); trach_em.inputs['Strength'].default_value = 2.2 + heat * (4 + 3 * pulse)
        trachea.data.bevel_depth = 0.011 * (1 + 0.35 * heat * pulse)
        label.hide_render = t < 14.0; s20 = P_back(min(1, (t - 14.0) / 0.35)) if t >= 14.0 else 0; label.scale = (s20, s20, s20)
        for o, ph, ox, oy, sp in parts:
            if t < 11.4:     # flow: lungs -> up the windpipe
                s = ((t - 8.7) * (0.45 + 0.3 * sp) + ph) % 1.0; s = min(s, (t - 8.7) * 0.6 + ph * 0.3)
                p = tr_bot.lerp(tr_top, min(1, s)) if s < 1 else tr_top
                if ph < 0.4: p = (tr_bot + Vector((ox * 0.08, 0.03, -0.1))).lerp(tr_bot, min(1, s * 2)) if s < 0.5 else tr_bot.lerp(tr_top, (s - 0.5) * 2)
            else:            # trapped: crowd between throat and closed mouth, bouncing
                k = 0.5 + 0.5 * math.sin(t * (6 + 5 * sp) + ph * 9)
                base = tr_top.lerp(mouth_pt, 0.25 + 0.55 * k * (0.3 + 0.7 * (1 - heat * 0.5)))
                p = base + Vector((ox * 0.012, oy * 0.012, (sp - 0.5) * 0.03)) * (1 + heat)
            o.location = p + Vector((ox * 0.004, oy * 0.004, 0))
        air_em.inputs['Color'].default_value = (0.6 + 0.4 * heat, 0.95 * (1 - heat) + 0.3 * heat, 1.0 * (1 - heat) + 0.2 * heat, 1)
    # ---- macro dynamics ----
    if mac:
        if name == 'macro_tear': open_ = ramp(t, 2.3, 2.6)
        elif name == 'macro_leak': open_ = 1.0
        else: open_ = 1 - ramp(t, 23.4, 25.6)
        cutter.scale = (0.09 * open_ + 0.0005, 0.12, 0.05 * open_ + 0.0005)
        flash.energy = 0 if name != 'macro_tear' else 300 * math.exp(-max(0, t - 2.35) * 4) * (t > 2.3)
        for o, ox, oy, ph, r in bubbles:
            if name == 'macro_leak':
                s = max(0, (t - 16.6 - ph * 2.5)) * 0.45
                o.location = M0 + Vector((ox * 0.05 + ox * s * 0.6, -0.36 - s * 0.9, oy * 0.03 + s * (0.35 + 0.4 * oy)))
                o.scale = (r * min(1, s * 6),) * 3
            else: o.scale = (0.0001,) * 3
        label5.hide_render = not (name == 'macro_heal' and t > 23.6); k5 = P_back(min(1, max(0, (t - 23.6) / 0.35))); label5.scale = (k5, k5, k5)
    # ---- droplets ----
    for o, v, r in drops:
        dt = t - 28.05
        if dt > 0 and name == 'car_sneeze':
            p = mouth_pt + v * dt * (1 - min(dt, 0.6) * 0.5) + Vector((0, 0, -0.6 * dt * dt)); o.location = p; o.scale = (r,) * 3
        else: o.scale = (0.00001,) * 3
    # ---- cameras ----
    hc = ned.bone_world('head') + Vector((0, -0.03, 0.03))
    if name == 'hook_face':
        look_at(hc + Vector((0.16, -0.62 + 0.1 * u / L, 0.02)) + shake(t, 0.002), hc + Vector((0, 0, -0.03)), 45, 2.0)
    elif name == 'macro_tear':
        look_at(M0 + Vector((0.5 - 0.15 * u / L, -1.5 + 0.3 * u / L, 0.25)) + shake(t, 0.004 * (t > 2.3)), M0 + Vector((0, -0.35, 0)), 40, 3.5)
    elif name == 'car_side':
        look_at(Vector((0.75, -0.55, hz - 0.05)) + shake(t, 0.003), hc + Vector((0.0, 0, -0.12)) + Vector((-0.04 * u / L, 0, 0)), 30, 2.8, focus=hc)
    elif name == 'car_pinch':
        look_at(hc + Vector((0.05, -0.5 + 0.08 * u / L, 0.0)) + shake(t, 0.002), hc + Vector((0, 0, -0.05)), 40, 2.0)
    elif name == 'xray_chest':
        look_at(Vector((0.35, -1.35 + 0.15 * u / L, cz + 0.25)), tr_bot + Vector((0, 0, 0.02)), 32, 4.0)
    elif name == 'xray_head':
        look_at(tr_top + Vector((0.3, -0.5 + 0.06 * u / L, 0.06)), tr_top.lerp(mouth_pt, 0.5), 38, 4.0)
    elif name == 'xray_pressure':
        look_at(tr_top + Vector((-0.18, -0.42 + 0.06 * u / L, 0.0)) + shake(t, 0.003 * ramp(t, 14, 15)), tr_top + Vector((0, 0, -0.03)), 36, 4.0)
    elif name == 'macro_leak':
        look_at(M0 + Vector((-0.4 + 0.2 * u / L, -1.9 + 0.3 * u / L, 0.35)), M0 + Vector((0, -0.4, 0.2)), 36, 4.0)
    elif name == 'hospital':
        nk = ned.bone_world('neck02')
        look_at(nk + Vector((0.42, -0.42 + 0.04 * u / L, 0.06)), nk + Vector((0.03, -0.02, 0.0)), 42, 2.4)
    elif name == 'macro_heal':
        look_at(M0 + Vector((0.2, -1.6 + 0.2 * u / L, 0.3)), M0 + Vector((0, -0.35, 0.05)), 38, 4.0)
    elif name == 'car_relax':
        look_at(hc + Vector((-0.12, -0.75 + 0.1 * u / L, -0.02)), hc + Vector((0, 0, -0.06)), 38, 2.4)
    elif name == 'car_sneeze':
        look_at(hc + Vector((0.35, -0.8, 0.0)) + shake(t, 0.012 * math.exp(-max(0, t - 28.0) * 3) * (t > 28.0), 25), hc + Vector((0, -0.12, -0.06)), 30, 3.2, focus=hc)
def P_back(u, s=2.2): u = min(1, max(0, u)) - 1; return 1 + u * u * ((s + 1) * u + s)

if __name__ == '__main__':
    out, i0, i1 = sys.argv[-3], int(sys.argv[-2]), int(sys.argv[-1]); os.makedirs(out, exist_ok=True)
    only = os.environ.get('ONLY')
    frames = [int(x) for x in only.split(',')] if only else range(i0, i1)
    for f in frames:
        S.frame_set(f); update(f / FPS); bpy.context.view_layer.update()
        S.render.filepath = os.path.join(out, f'f{f:04d}.png'); bpy.ops.render.render(write_still=True)
