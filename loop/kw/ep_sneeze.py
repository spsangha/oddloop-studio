"""Kinda Wild Films - 'He Held In A Sneeze' (v2). Zack D. Films format: realistic 3D people, real sets, glossy anatomy, 3D graphics, calm VO.
blender -b -P ep_sneeze.py -- outdir i0 i1      (renders frames i0..i1-1)
blender -b -P ep_sneeze.py -- --cues out.json   (timing / audio / caption data)"""
import bpy, sys, os, math, json, random
from mathutils import Vector, Euler
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)
FPS = 24; DUR = 26.4
VO = [(0.15, "He pinched his nose and shut his mouth to stop a sneeze while he was driving."),
      (4.30, "But with no way out, the air built up pressure in his throat."),
      (7.85, "It could have reached twenty times the pressure of a normal sneeze, enough to tear a two-millimeter hole in his windpipe."),
      (13.80, "Both sides of his neck swelled up, and when doctors pressed on it, they heard it crackle."),
      (18.60, "Air had leaked through the hole and gotten trapped under his skin."),
      (21.80, "Five weeks later, a scan showed the hole had closed.")]
SHOTS = [(0.0, 'car_pinch'), (1.6, 'car_cheeks'), (2.9, 'car_hood'), (4.3, 'car_plunge'), (5.0, 'xray_profile'), (6.4, 'xray_throat'), (7.85, 'xray_gauge'),
         (9.45, 'normal_sneeze'), (11.0, 'macro_tear'), (11.9, 'macro_hole'), (13.8, 'car_neck'), (15.8, 'hos_wide'), (17.2, 'hos_press'),
         (18.6, 'macro_leak'), (20.1, 'skin_block'), (21.8, 'calendar'), (23.1, 'scan'), (24.7, 'car_sneeze')]
T_TEAR = 11.45; T_NS = 9.95; T_END = 25.45; PRESS = (17.55, 18.05)
CUES = [(0.0, 'engine', 0.6), (0.0, 'inhale', 0.5), (0.5, 'pinch', 0.9), (1.5, 'puff', 0.8), (2.9, 'engine', 0.7), (4.3, 'pressure', 0.5),
        (5.0, 'rush', 0.8), (5.6, 'bounce', 0.8), (6.0, 'bounce', 0.6), (6.4, 'pressure', 0.9), (8.7, 'thud', 0.9),
        (9.45, 'inhale', 0.5), (T_NS, 'sneeze', 0.9), (11.0, 'pressure', 0.6), (T_TEAR, 'rip', 1.0), (T_TEAR + 0.05, 'thud', 0.7), (12.3, 'bounce', 0.4),
        (13.8, 'engine', 0.4), (14.3, 'puff', 0.7), (PRESS[0], 'crackle', 1.0), (PRESS[1], 'crackle', 1.0), (18.7, 'bubbles', 0.8),
        (20.3, 'bubbles', 0.6), (21.1, 'crackle', 0.8), (21.95, 'pinch', 0.5), (22.2, 'pinch', 0.5), (22.45, 'pinch', 0.5), (22.7, 'pinch', 0.5),
        (23.7, 'heal', 0.7), (24.7, 'engine', 0.5), (24.75, 'inhale', 0.9), (T_END, 'sneeze', 1.0), (T_END + 0.3, 'bounce', 0.5)]
def shot_at(t):
    cur = SHOTS[0]
    for s in SHOTS:
        if t >= s[0]: cur = s
    nxt = next((s[0] for s in SHOTS if s[0] > cur[0]), DUR)
    return cur[1], t - cur[0], nxt - cur[0]
def ease(u): u = min(1, max(0, u)); return u * u * (3 - 2 * u)
def ramp(t, a, b): return ease((t - a) / (b - a)) if b > a else float(t >= a)
def P_back(u, s=2.2): u = min(1, max(0, u)) - 1; return 1 + u * u * ((s + 1) * u + s)
def bump(t, c, w): return math.exp(-((t - c) / w) ** 2)

def cues():
    return dict(duration=DUR, fps=FPS, vo=VO, voice='en-US-ChristopherNeural', rate='+6%', cues=CUES, shots=SHOTS, music_gain=0.42)

if '--cues' in sys.argv:
    json.dump(cues(), open(sys.argv[-1], 'w'), indent=1); sys.exit(0)

import person as P
bpy.ops.wm.read_factory_settings(use_empty=True); S = bpy.context.scene
K = G = None
if not os.environ.get('NOSETS'):
    try: import sets_kw as K
    except Exception as e: print('sets_kw unavailable:', repr(e))
if not os.environ.get('NOGFX'):
    try: import gfx_kw as G
    except Exception as e: print('gfx_kw unavailable:', repr(e))
FONT = bpy.data.fonts.load(os.path.join(HERE, '..', 'Montserrat-Black.ttf'))

def mat(name, col, rough=0.5, metal=0.0, emit=None, es=1.0, alpha=1.0, trans=0.0, sss=0.0, coat=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True; b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*col, 1); b.inputs['Roughness'].default_value = rough; b.inputs['Metallic'].default_value = metal
    if emit: b.inputs['Emission Color'].default_value = (*emit, 1); b.inputs['Emission Strength'].default_value = es
    if alpha < 1: b.inputs['Alpha'].default_value = alpha
    if trans: b.inputs['Transmission Weight'].default_value = trans
    if sss: b.inputs['Subsurface Weight'].default_value = sss; b.inputs['Subsurface Radius'].default_value = (0.2, 0.05, 0.03)
    if coat: b.inputs['Coat Weight'].default_value = coat; b.inputs['Coat Roughness'].default_value = 0.1
    return m
def bumpy(m, scale=40.0, strength=0.3, detail=4.0, dist=0.02):
    """procedural wet-tissue bump"""
    nt = m.node_tree; b = nt.nodes['Principled BSDF']; nz = nt.nodes.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = scale; nz.inputs['Detail'].default_value = detail
    bp_ = nt.nodes.new('ShaderNodeBump'); bp_.inputs['Strength'].default_value = strength; bp_.inputs['Distance'].default_value = dist
    nt.links.new(nz.outputs['Fac'], bp_.inputs['Height']); nt.links.new(bp_.outputs['Normal'], b.inputs['Normal']); return m
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
def tube(name, pts, r, mt, res=6):
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = r; cu.bevel_resolution = res; cu.use_fill_caps = True
    sp = cu.splines.new('BEZIER'); sp.bezier_points.add(len(pts) - 1)
    for bp_, p in zip(sp.bezier_points, pts): bp_.co = p; bp_.handle_left_type = bp_.handle_right_type = 'AUTO'
    o = bpy.data.objects.new(name, cu); S.collection.objects.link(o); o.data.materials.append(mt); return o
def glow(name, col, es, alpha=0.6, blend=0.35):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial'); em = nt.nodes.new('ShaderNodeEmission'); em.inputs['Color'].default_value = (*col, 1); em.inputs['Strength'].default_value = es
    tr = nt.nodes.new('ShaderNodeBsdfTransparent'); lw = nt.nodes.new('ShaderNodeLayerWeight'); lw.inputs['Blend'].default_value = blend
    mx = nt.nodes.new('ShaderNodeMixShader'); mth = nt.nodes.new('ShaderNodeMath'); mth.operation = 'MULTIPLY_ADD'; mth.inputs[1].default_value = 1 - alpha; mth.inputs[2].default_value = alpha
    nt.links.new(lw.outputs['Facing'], mth.inputs[0]); nt.links.new(mth.outputs[0], mx.inputs[0]); nt.links.new(tr.outputs[0], mx.inputs[1]); nt.links.new(em.outputs[0], mx.inputs[2]); nt.links.new(mx.outputs[0], out.inputs[0])
    return m, em
def text3d(name, body, size, col, es=0.0, extrude=0.18):
    fc = bpy.data.curves.new(name, 'FONT'); fc.body = body; fc.font = FONT; fc.size = size; fc.extrude = size * extrude; fc.bevel_depth = size * 0.035; fc.bevel_resolution = 3
    fc.align_x = 'CENTER'; fc.align_y = 'CENTER'
    o = bpy.data.objects.new(name, fc); S.collection.objects.link(o); o.rotation_euler = (math.radians(90), 0, 0)
    o.data.materials.append(mat(name + '_m', col, 0.18, emit=col if es else None, es=es, coat=1.0)); return o

# ---------------- people ----------------
import cast as C   # new cast for every story (Zack D. style); fixed seeds keep shards identical
ned = P.build_person('Ned', **C.cast({'gender': 'm', 'age': 'middle', 'race': 'caucasian', 'build': 'avg', 'tee': 'red'}, 'sneeze', P.MP))
try: import wardrobe_kw as Wd     # uniforms by job: Wd.person(name, job, seed, **role)
except Exception as e: Wd = None; print('wardrobe unavailable', repr(e))
if Wd:
    doc = Wd.person('Doc', 'doctor', 'sneeze-doc', gender='f', age='young', race='asian', build='slim', hair='ponytail01')
    nurse = Wd.person('Nurse', 'nurse', 'sneeze-nurse', gender='m', age='young', race='african', build='avg', clipboard=True)
else:
    doc = P.build_person('Doc', **C.cast({'gender': 'f', 'age': 'young', 'race': 'asian', 'build': 'slim', 'hair': 'ponytail01', 'tee': 'white'}, 'sneeze-doc', P.MP)); nurse = None
ns = P.build_person('Nia', **C.cast({'gender': 'f', 'age': 'young', 'race': 'african', 'build': 'avg', 'hair': 'afro01', 'tee': 'mustard'}, 'sneeze-nia', P.MP))
PEOPLE = tuple(p for p in (ned, doc, ns, nurse) if p)
def sit(p):
    for s in 'LR':
        p.rot(f'upperleg01.{s}', (-85, 0, 0)); p.rot(f'lowerleg01.{s}', (88, 0, 0))
P.sit = sit
sit(ned); ned.place((0, 0, 0)); bpy.context.view_layer.update()
pelvis = ned.bone_world('spine05')
if not Wd:   # blue exam gloves on the doctor's hands (faces weighted to wrist/finger bones)
    glove = mat('glove', (0.1, 0.32, 0.85), 0.3, coat=0.3)
    db = doc.body; db.data.materials.append(glove); gi = len(db.data.materials) - 1
    groups = {g.index for g in db.vertex_groups if g.name.startswith(('wrist', 'finger', 'metacarpal'))}
    hand_v = set()
    for v in db.data.vertices:
        if sum(g.weight for g in v.groups if g.group in groups) > 0.5: hand_v.add(v.index)
    for poly in db.data.polygons:
        if sum(1 for i in poly.vertices if i in hand_v) >= 3: poly.material_index = gi
# he sits on a high exam bed (hips at standing height), so the standing staff are lifted to keep real proportions
bpy.context.view_layer.update(); NED_HEAD_Z = ned.bone_world('head').z
def stand_z(p, above): return NED_HEAD_Z + above - (p.bone_world('head').z - p.rig.location.z)
DOC_AT = Vector((0.47, -0.27, stand_z(doc, 0.07))); doc.place(DOC_AT, -119)       # faces his left neck
if nurse: NURSE_AT = Vector((0.36, 0.62, stand_z(nurse, 0.12))); nurse.place(NURSE_AT, 12)
print('heights', NED_HEAD_Z, DOC_AT, nurse and NURSE_AT)
NS0 = Vector((60, 0, 0)); ns.place(NS0); bpy.context.view_layer.update(); NS_HEAD = ns.bone_world('head') + Vector((0, -0.03, 0.03)); NS_SH = {s_: ns.bone_world(f'upperarm01.{s_}') for s_ in 'LR'}
if K and hasattr(K, 'skin'):
    for p in PEOPLE:   # warmer, more saturated skin on pale faces; dark skin keeps its own colour
        try: K.skin(p, amount=0.5 if p is ned else 0.3 if p is doc else 0.1)
        except Exception as e: print('skin failed', repr(e))
def flush(v):
    if K and hasattr(K, 'flush'):
        try: K.flush(ned, v)
        except Exception as e: print('flush failed', repr(e))

hz = ned.bone_world('head').z; cz = ned.bone_world('spine03').z
fwd = Vector((0, -1, 0))
head_b = ned.bone_world('head')
mouth_pt = head_b + fwd * 0.1 + Vector((0, 0, -0.035))
nose_pt = head_b + fwd * 0.115 + Vector((0, 0, 0.0))

# ---------------- car + hospital sets ----------------
if K:
    car = K.build_car(S, ned); C_CAR = car.coll; wheel = car.wheel
    hos = K.build_hospital(S, ned); C_HOS = hos.coll
else:   # plain fallback sets
    car = hos = None; C_CAR = coll('car'); C_HOS = coll('hospital')
    seat_m = mat('seat', (0.035, 0.035, 0.04), 0.8); dash_m = mat('dash', (0.05, 0.05, 0.055), 0.55); trim_m = mat('trim', (0.12, 0.1, 0.09), 0.4)
    wheel = obj_of('torus', 'wheel', trim_m, major_radius=0.19, minor_radius=0.017, location=(0, -0.52, cz + 0.12), rotation=(math.radians(65), 0, 0)); smooth(wheel)
    into(C_CAR, [bevel_box('seat_base', (0.55, 0.55, 0.14), (0, 0.05, pelvis.z - 0.12), seat_m, 0.05),
                 bevel_box('seat_back', (0.55, 0.14, 0.75), (0, 0.32, pelvis.z + 0.32), seat_m, 0.05, (math.radians(-12), 0, 0)),
                 bevel_box('headrest', (0.28, 0.12, 0.2), (0, 0.42, hz + 0.02), seat_m, 0.04),
                 bevel_box('dash', (2.2, 0.6, 0.35), (0.3, -0.95, cz + 0.05), dash_m, 0.08), wheel,
                 bevel_box('roof', (2.0, 2.2, 0.05), (0.3, -0.1, hz + 0.27), mat('headliner', (0.42, 0.36, 0.3), 0.9), 0.02)])
    into(C_HOS, [obj_of('plane', 'h_wall', mat('h_wall', (0.03, 0.2, 0.3), 0.7), size=8, location=(0, 1.6, 2), rotation=(math.radians(90), 0, 0)),
                 bevel_box('h_bed', (0.9, 1.9, 0.12), (0, 0.15, pelvis.z - 0.12), mat('h_bed', (0.92, 0.93, 0.95), 0.6), 0.05)])

# ---------------- x-ray anatomy (follows the seated pose) ----------------
C_XR = coll('xray')
xray_body, _ = glow('xray_body', (0.15, 0.75, 1.0), 2.2, 0.03, 0.42)
tr_top = ned.bone_world('neck02') + fwd * 0.05
tr_bot = ned.bone_world('neck01') + fwd * 0.04 + Vector((0, 0, -0.09))
ph = head_b + fwd * 0.035 + Vector((0, 0, -0.05))                    # back of the throat
nb = head_b + fwd * 0.045 + Vector((0, 0, 0.005))                    # back of the nasal cavity
nostril = nose_pt + Vector((0, 0.012, -0.012)); lips = mouth_pt + Vector((0, 0.012, 0))
air_wall = mat('airway', (0.95, 0.42, 0.45), 0.22, emit=(0.9, 0.25, 0.3), es=0.6, sss=0.3, coat=0.5)
ring_x = mat('ring_x', (0.98, 0.93, 0.85), 0.3, emit=(1, 0.9, 0.8), es=0.5)
lung_m = bumpy(mat('lungs', (1.0, 0.36, 0.22), 0.3, emit=(1.0, 0.25, 0.1), es=0.7, sss=0.3, coat=0.4), 55, 0.5)
trachea = tube('trachea', [tr_bot, tr_top, ph], 0.0105, air_wall)
oral = tube('oral', [ph, ph.lerp(lips, 0.5) + Vector((0, 0, 0.004)), lips], 0.0105, air_wall)
nasal = tube('nasal', [ph, nb, nb.lerp(nostril, 0.55) + Vector((0, 0, 0.012)), nostril], 0.0065, air_wall)
xr_objs = [trachea, oral, nasal]
for k in range(7):
    c = tr_bot.lerp(tr_top, 0.08 + k * 0.13); d = (tr_top - tr_bot).normalized()
    r = obj_of('torus', f'xring{k}', ring_x, major_radius=0.0115, minor_radius=0.0022, location=c, major_segments=24, minor_segments=8)
    r.rotation_euler = d.to_track_quat('Z', 'Y').to_euler(); smooth(r); xr_objs.append(r)
lung_c = []
for sx in (-1, 1):
    c = tr_bot + Vector((sx * 0.082, 0.03, -0.105)); lung_c.append(c)
    l = obj_of('uv_sphere', f'lung{sx}', lung_m, radius=1, location=c, segments=48, ring_count=24); l.scale = (0.062, 0.06, 0.125); smooth(l)
    tx = bpy.data.textures.new(f'lt{sx}', 'CLOUDS'); tx.noise_scale = 0.9; dm = l.modifiers.new('d', 'DISPLACE'); dm.texture = tx; dm.strength = 0.22; dm.texture_coords = 'GLOBAL'
    xr_objs.append(l)
    xr_objs.append(tube(f'bronch{sx}', [tr_bot, tr_bot + Vector((sx * 0.035, 0.01, -0.03)), c + Vector((-sx * 0.015, -0.02, 0.05))], 0.0065, air_wall))
    for j, (dz, dx) in enumerate(((0.02, 0.02), (-0.03, 0.01), (-0.07, 0.025))):
        xr_objs.append(tube(f'br{sx}{j}', [c + Vector((-sx * 0.015, -0.02, 0.05)), c + Vector((sx * dx, -0.045, dz))], 0.003, air_wall))
air_m, air_em = glow('air', (0.55, 1.0, 0.05), 9.0, 0.97)
rnd = random.Random(7); parts = []
for i in range(90):
    o = obj_of('ico_sphere', f'air{i}', air_m, radius=0.0042, subdivisions=2, location=(0, 0, 0)); smooth(o)
    parts.append((o, rnd.random(), rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.random(), rnd.random() < 0.4, rnd.choice((0, 1))))
seal_m, seal_em = glow('seal', (1.0, 0.05, 0.02), 10.0, 1.0)
seals = []
for pt, r in ((nostril + fwd * 0.008, 0.012), (lips + fwd * 0.008, 0.017)):
    s_ = obj_of('torus', 'seal', seal_m, major_radius=r, minor_radius=r * 0.22, location=pt, rotation=(math.radians(90), 0, 0)); smooth(s_); seals.append(s_)
    for a in (45, -45):
        seals.append(bevel_box('sealx', (r * 1.5, r * 0.3, r * 0.3), pt, seal_m, 0.001, (0, math.radians(a), 0)))
seal_base = [tuple(s_.scale) for s_ in seals]
G0 = tr_top + Vector((0.17, -0.12, -0.1))                           # pressure gauge beside the throat
if G:
    gauge = G.Gauge(G0, C_XR, radius=0.06)
    lab20 = G.Label3D('20x', G0 + Vector((0.0, -0.02, 0.105)), C_XR, size=0.06, color=(1.0, 0.06, 0.04))
else:
    gauge = None; lab20 = text3d('label20', '20x', 0.06, (1.0, 0.06, 0.04), 1.5); lab20.location = G0 + Vector((0.0, -0.02, 0.105)); xr_objs.append(lab20)
into(C_XR, xr_objs + [p[0] for p in parts] + seals)

# ---------------- macro windpipe set (far away at x=30) ----------------
C_MAC = coll('macro'); M0 = Vector((30, 0, 1.0))
wall_m = mat('trach_wall', (0.9, 0.42, 0.42), 0.16, sss=0.4, coat=0.7)
nt_ = wall_m.node_tree; pb_ = nt_.nodes['Principled BSDF']      # ivory cartilage bands every 0.18 units + wet micro-bump
tcn = nt_.nodes.new('ShaderNodeTexCoord'); sx_ = nt_.nodes.new('ShaderNodeSeparateXYZ'); m1 = nt_.nodes.new('ShaderNodeMath'); m1.operation = 'MULTIPLY'; m1.inputs[1].default_value = 2 * math.pi / 0.18
m2 = nt_.nodes.new('ShaderNodeMath'); m2.operation = 'COSINE'; cr_ = nt_.nodes.new('ShaderNodeValToRGB')
cr_.color_ramp.elements[0].position = 0.25; cr_.color_ramp.elements[0].color = (0.85, 0.3, 0.33, 1); cr_.color_ramp.elements[1].position = 0.8; cr_.color_ramp.elements[1].color = (0.97, 0.86, 0.78, 1)
nz_ = nt_.nodes.new('ShaderNodeTexNoise'); nz_.inputs['Scale'].default_value = 22; nz_.inputs['Detail'].default_value = 5; bpn = nt_.nodes.new('ShaderNodeBump'); bpn.inputs['Strength'].default_value = 0.35; bpn.inputs['Distance'].default_value = 0.03
m0_ = nt_.nodes.new('ShaderNodeMath'); m0_.operation = 'ADD'; m0_.inputs[1].default_value = -0.09
nt_.links.new(tcn.outputs['Object'], sx_.inputs[0]); nt_.links.new(sx_.outputs['X'], m0_.inputs[0]); nt_.links.new(m0_.outputs[0], m1.inputs[0]); nt_.links.new(m1.outputs[0], m2.inputs[0])
nt_.links.new(m2.outputs[0], cr_.inputs['Fac']); nt_.links.new(cr_.outputs['Color'], pb_.inputs['Base Color'])
nt_.links.new(tcn.outputs['Object'], nz_.inputs['Vector']); nt_.links.new(nz_.outputs['Fac'], bpn.inputs['Height']); nt_.links.new(bpn.outputs['Normal'], pb_.inputs['Normal'])
inner_m = mat('inner', (0.45, 0.03, 0.05), 0.25, coat=0.5)
tm = bpy.data.meshes.new('m_tube'); vs = []; fs = []; NA, NL = 96, 160
for j in range(NL + 1):
    x = -1.6 + 3.2 * j / NL
    for i in range(NA):
        a = 2 * math.pi * i / NA; rr = 0.35 + 0.016 * max(0.0, math.cos(2 * math.pi * (x - 0.09) / 0.18)) ** 2; vs.append((x, rr * math.sin(a), rr * math.cos(a)))
for j in range(NL):
    for i in range(NA): fs.append((j * NA + i, j * NA + (i + 1) % NA, (j + 1) * NA + (i + 1) % NA, (j + 1) * NA + i))
tm.from_pydata(vs, [], fs); tubeo = bpy.data.objects.new('m_tube', tm); S.collection.objects.link(tubeo); tubeo.location = M0; tubeo.data.materials.append(wall_m); smooth(tubeo)
so = tubeo.modifiers.new('s', 'SOLIDIFY'); so.thickness = 0.05; tubeo.data.materials.append(inner_m); so.material_offset = 1
HOLE = M0 + Vector((0, -0.36, 0.0))
cutter = obj_of('ico_sphere', 'm_cut', None, radius=1, subdivisions=4, location=HOLE); cutter.display_type = 'WIRE'; cutter.hide_render = True
ctx_ = bpy.data.textures.new('cut_t', 'CLOUDS'); ctx_.noise_scale = 0.45; cdm = cutter.modifiers.new('d', 'DISPLACE'); cdm.texture = ctx_; cdm.strength = 0.9   # ragged tear, not a neat oval
bo = tubeo.modifiers.new('cut', 'BOOLEAN'); bo.object = cutter; bo.operation = 'DIFFERENCE'; bo.solver = 'FAST'
ss = tubeo.modifiers.new('sub', 'SUBSURF'); ss.levels = 0; ss.render_levels = 1
mac_objs = [tubeo, cutter]
musc_m = bumpy(mat('muscle', (0.62, 0.05, 0.06), 0.2, sss=0.2, coat=0.6), 3.0, 0.6, 2.0, 0.05)
musc_m.node_tree.nodes['Noise Texture'].inputs['Scale'].default_value = 60
mp_ = musc_m.node_tree.nodes.new('ShaderNodeMapping'); mp_.inputs['Scale'].default_value = (0.03, 1, 1); tcm = musc_m.node_tree.nodes.new('ShaderNodeTexCoord')   # long fibres
musc_m.node_tree.links.new(tcm.outputs['Object'], mp_.inputs['Vector']); musc_m.node_tree.links.new(mp_.outputs['Vector'], musc_m.node_tree.nodes['Noise Texture'].inputs['Vector'])
for k, (y, z, r) in enumerate(((0.75, 0.45, 0.42), (0.85, -0.5, 0.5), (0.2, -0.95, 0.36))):
    mo = obj_of('cylinder', f'musc{k}', musc_m, radius=r, depth=5.0, location=M0 + Vector((0, y, z)), rotation=(0, math.radians(90), 0), vertices=48); smooth(mo); mac_objs.append(mo)
vein_m = mat('vein', (0.03, 0.12, 0.75), 0.15, coat=0.8); art_m = mat('artery', (0.85, 0.03, 0.04), 0.15, coat=0.8)
mac_objs.append(tube('vein', [M0 + Vector((-2.4, -0.2, 0.62)), M0 + Vector((-0.8, -0.12, 0.56)), M0 + Vector((0.8, -0.2, 0.6)), M0 + Vector((2.4, -0.1, 0.66))], 0.075, vein_m, 8))
mac_objs.append(tube('artery', [M0 + Vector((-2.4, -0.25, -0.6)), M0 + Vector((-0.7, -0.3, -0.55)), M0 + Vector((0.9, -0.22, -0.6)), M0 + Vector((2.4, -0.3, -0.56))], 0.065, art_m, 8))
fat_m = bumpy(mat('fat', (1.0, 0.78, 0.2), 0.25, sss=0.5, coat=0.5), 8.0, 0.4)
for i in range(16):
    fo = obj_of('uv_sphere', f'fat{i}', fat_m, radius=rnd.uniform(0.1, 0.2), location=M0 + Vector((rnd.uniform(-2.0, 2.0), rnd.uniform(0.15, 0.6), rnd.choice((-1, 1)) * rnd.uniform(0.75, 1.15))), segments=20, ring_count=10)
    fo.scale = (1.2, 1.0, 0.8); smooth(fo); mac_objs.append(fo)
bub_m = mat('bubble', (0.95, 0.98, 1.0), 0.03, trans=1.0)
bubbles = []
for i in range(34):
    o = obj_of('uv_sphere', f'bub{i}', bub_m, radius=1, location=M0, segments=24, ring_count=12); smooth(o); bubbles.append((o, rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.random(), rnd.uniform(0.02, 0.065)))
jet_m, _j = glow('jet', (0.6, 1.0, 0.1), 8.0, 0.97); jets = []
for i in range(46):
    o = obj_of('ico_sphere', f'jet{i}', jet_m, radius=1, subdivisions=2, location=M0); smooth(o)
    a = rnd.uniform(-0.5, 0.5); b = rnd.uniform(-0.4, 0.4); jets.append((o, Vector((math.sin(a), -math.cos(a) * math.cos(b), math.sin(b))) * rnd.uniform(1.5, 3.6), rnd.uniform(0.012, 0.03), rnd.random() * 0.5))
flash = bpy.data.lights.new('flash', 'POINT'); flash.color = (1, 0.12, 0.08); flash_o = bpy.data.objects.new('flash', flash); S.collection.objects.link(flash_o); flash_o.location = M0 + Vector((0, -0.75, 0))
BR0 = HOLE + Vector((-0.1, -0.03, 0.105)); BR1 = HOLE + Vector((0.1, -0.03, 0.105))
if G and hasattr(G, 'Bracket'):
    bracket = G.Bracket(BR0, BR1, '2 mm', C_MAC); lab2 = None
    for o in bracket.root.children_recursive:      # yellow reads on pink tissue (red does not)
        for sl in getattr(o, 'material_slots', []):
            if sl.material and sl.material.node_tree:
                for n in sl.material.node_tree.nodes:
                    if n.type == 'BSDF_PRINCIPLED': n.inputs['Base Color'].default_value = (1.0, 0.82, 0.02, 1); n.inputs['Emission Color'].default_value = (1.0, 0.8, 0.0, 1); n.inputs['Emission Strength'].default_value = 0.6
else:
    bracket = None; lab2 = text3d('label2', '2 mm', 0.09, (1.0, 0.06, 0.04), 1.2); lab2.location = HOLE + Vector((0, -0.05, 0.19)); mac_objs.append(lab2)
into(C_MAC, mac_objs + [b[0] for b in bubbles] + [j[0] for j in jets] + [flash_o])

# ---------------- graphics stations (far away, one per shot) ----------------
C_SKIN = coll('skin'); SK0 = Vector((40, 0, 1.0))
skinblock = G.SkinBlock(SK0, C_SKIN, size=0.5) if G and hasattr(G, 'SkinBlock') else None
C_CAL = coll('calendar'); CA0 = Vector((50, 0, 1.5))
calendar = G.Calendar(CA0, C_CAL) if G and hasattr(G, 'Calendar') else None
wall_teal = mat('wall_teal', (0.03, 0.2, 0.3), 0.7)
if K and hasattr(K, 'wall_material'):
    try: wall_teal = K.wall_material()
    except Exception as e: print('wall_material failed', repr(e))
calwall = obj_of('plane', 'cal_wall', wall_teal, size=6, location=CA0 + Vector((0, 0.03, 0)), rotation=(math.radians(90), 0, 0))
callab = None
if not calendar:
    callab = text3d('cal5', '5 weeks later', 0.09, (1, 1, 1), 1.0); callab.location = CA0 + Vector((0, -0.05, 0)); into(C_CAL, [callab])
into(C_CAL, [calwall])
C_SCAN = coll('scan'); SC0 = Vector((55, 0, 1.2))
scan = G.ScanMonitor(SC0, C_SCAN, width=0.5) if G and hasattr(G, 'ScanMonitor') else None
scanwall = obj_of('plane', 'scan_wall', wall_teal, size=6, location=SC0 + Vector((0, 1.2, 0.3)), rotation=(math.radians(90), 0, 0)); into(C_SCAN, [scanwall])
NECK_L = ned.bone_world('neck02') + Vector((0.062, -0.035, 0.0))     # where the doctor presses (his left side)
crackle = G.Crackle(NECK_L + Vector((0.02, -0.03, 0.0)), C_HOS) if G and hasattr(G, 'Crackle') else None
if crackle: crackle.root.scale = (0.55,) * 3

# ---------------- droplets (normal sneeze + final sneeze) and lens splats ----------------
C_DROP = coll('drops'); drop_m = mat('drop', (0.92, 0.97, 1.0), 0.02, trans=0.85, emit=(0.8, 0.95, 1.0), es=0.35); drops = []
for i in range(260):
    o = obj_of('ico_sphere', f'drop{i}', drop_m, radius=1, subdivisions=2, location=(0, 0, 0)); smooth(o)
    a = rnd.uniform(-0.55, 0.55); b = rnd.uniform(-0.4, 0.32); sp = rnd.uniform(1.4, 3.4); drops.append((o, Vector((math.sin(a), -math.cos(a) * math.cos(b), math.sin(b))) * sp, rnd.uniform(0.0012, 0.0042)))
into(C_DROP, [d[0] for d in drops])

# ---------------- lights, worlds, camera ----------------
def area(name, loc, e, size, colr, tgt):
    L = bpy.data.lights.new(name, 'AREA'); L.energy = e; L.size = size; L.color = colr; o = bpy.data.objects.new(name, L); S.collection.objects.link(o); o.location = loc
    o.rotation_euler = (Vector(tgt) - o.location).to_track_quat('-Z', 'Y').to_euler(); return o
head_c = ned.bone_world('head'); HC0 = head_c + Vector((0, -0.03, 0.03))
LK = 0.55 if K else 1.0   # sets bring their own HDRI light: keep ours as shaping light only
L_key = area('key', (0.6, -1.6, hz + 0.5), 200 * LK, 1.6, (1, 0.9, 0.78), head_c)
L_rim = area('rim', (-1.2, 0.3, hz + 0.3), 200 * LK, 0.8, (0.35, 0.65, 1.0), head_c)
L_fill = area('fill', (1.2, -0.4, hz - 0.2), 30 * LK, 1.5, (1, 0.9, 0.8), head_c)
PL = [(o, o.location.copy(), o.data.energy) for o in (L_key, L_rim, L_fill)]
L_mac = area('mac_key', (-1.2, -2.0, 1.4), 500, 2.5, (1, 0.96, 0.92), (0, 0, 0))
L_mac2 = area('mac_rim', (1.5, 0.8, 1.0), 300, 1.5, (0.55, 0.7, 1.0), (0, 0, 0))
L_mac3 = area('mac_fill', (0.6, -2.2, -0.9), 120, 2.5, (1, 0.9, 0.85), (0, 0, 0))
ML = [(o, o.location.copy(), o.data.energy) for o in (L_mac, L_mac2, L_mac3)]
def prop_lights(origin, sc=1.0, on=True, gain=1.0):
    for o, base, e in ML:
        o.hide_render = not on; o.location = Vector(origin) + base * sc; o.data.energy = e * sc * sc * gain; o.data.size = (2.5 if o is not L_mac2 else 1.5) * sc

# studio world: screen-space radial gradient + blueprint grid for camera rays, soft even light for everything else
W = bpy.data.worlds.new('kw_studio'); W.use_nodes = True; wn = W.node_tree; wn.nodes.clear()
w_out = wn.nodes.new('ShaderNodeOutputWorld'); w_tc = wn.nodes.new('ShaderNodeTexCoord'); w_sep = wn.nodes.new('ShaderNodeSeparateXYZ'); wn.links.new(w_tc.outputs['Window'], w_sep.inputs[0])
def wm(op, a, b=None):
    n = wn.nodes.new('ShaderNodeMath'); n.operation = op
    for i, v in enumerate((a, b)):
        if v is None: continue
        if isinstance(v, (int, float)): n.inputs[i].default_value = v
        else: wn.links.new(v, n.inputs[i])
    return n.outputs[0]
dx_ = wm('MULTIPLY', wm('SUBTRACT', w_sep.outputs['X'], 0.5), 0.5625); dy_ = wm('SUBTRACT', w_sep.outputs['Y'], 0.55)
dist_ = wm('SQRT', wm('ADD', wm('POWER', dx_, 2.0), wm('POWER', dy_, 2.0)))
w_grad = wn.nodes.new('ShaderNodeMix'); w_grad.data_type = 'RGBA'; wn.links.new(wm('MINIMUM', wm('MULTIPLY', dist_, 1.9), 1.0), w_grad.inputs[0])
gx = wm('ABSOLUTE', wm('SUBTRACT', wm('FRACT', wm('MULTIPLY', w_sep.outputs['X'], 9.0)), 0.5)); gy = wm('ABSOLUTE', wm('SUBTRACT', wm('FRACT', wm('MULTIPLY', w_sep.outputs['Y'], 16.0)), 0.5))
line_ = wm('GREATER_THAN', wm('MAXIMUM', gx, gy), 0.475)
w_grid = wn.nodes.new('ShaderNodeMix'); w_grid.data_type = 'RGBA'; w_grid.inputs[7].default_value = (1, 1, 1, 1); w_gs = wn.nodes.new('ShaderNodeMath'); w_gs.operation = 'MULTIPLY'; w_gs.inputs[1].default_value = 0.16
wn.links.new(line_, w_gs.inputs[0]); wn.links.new(w_gs.outputs[0], w_grid.inputs[0]); wn.links.new(w_grad.outputs[2], w_grid.inputs[6])
w_cam = wn.nodes.new('ShaderNodeBackground'); wn.links.new(w_grid.outputs[2], w_cam.inputs['Color']); w_amb = wn.nodes.new('ShaderNodeBackground')
w_lp = wn.nodes.new('ShaderNodeLightPath'); w_mx = wn.nodes.new('ShaderNodeMixShader'); wn.links.new(w_lp.outputs['Is Camera Ray'], w_mx.inputs[0])
wn.links.new(w_amb.outputs[0], w_mx.inputs[1]); wn.links.new(w_cam.outputs[0], w_mx.inputs[2]); wn.links.new(w_mx.outputs[0], w_out.inputs[0])
STUDIO = {'sky': ((0.2, 0.62, 1.0), (0.02, 0.16, 0.6), 0.16, (0.75, 0.85, 1.0), 0.3),      # centre, edge, grid strength, ambient colour, ambient strength
          'night': ((0.02, 0.1, 0.32), (0.0, 0.012, 0.07), 0.1, (0.2, 0.4, 0.9), 0.12),
          'warm': ((1.0, 0.62, 0.1), (0.85, 0.16, 0.05), 0.0, (1.0, 0.85, 0.7), 0.5)}
W0 = bpy.data.worlds.new('kw_plain'); W0.use_nodes = True
def world(kind):
    if kind in STUDIO:
        c, e, gs, amb, st = STUDIO[kind]; S.world = W
        w_grad.inputs[6].default_value = (*c, 1); w_grad.inputs[7].default_value = (*e, 1); w_gs.inputs[1].default_value = gs
        w_amb.inputs[0].default_value = (*amb, 1); w_amb.inputs[1].default_value = st
    elif K: K.set_world(S, kind)
    else:
        S.world = W0; bg = W0.node_tree.nodes['Background']; bg.inputs[0].default_value = (0.35, 0.6, 0.95, 1) if kind == 'car' else (0.5, 0.6, 0.65, 1); bg.inputs[1].default_value = 0.6

cam_d = bpy.data.cameras.new('cam'); CAM = bpy.data.objects.new('cam', cam_d); S.collection.objects.link(CAM); S.camera = CAM; cam_d.clip_start = 0.01
SAMPLES = int(os.environ.get('SAMPLES', '32'))
S.render.engine = 'CYCLES'; S.cycles.samples = SAMPLES; S.cycles.use_denoising = True; S.cycles.max_bounces = 6
S.cycles.transparent_max_bounces = 16; S.render.use_persistent_data = True
S.view_settings.view_transform = 'AgX'; S.view_settings.look = 'AgX - Punchy'
if K and hasattr(K, 'finish'):
    try: K.finish(S, SAMPLES)
    except Exception as e: print('finish failed', repr(e))
S.cycles.caustics_refractive = True   # MPFB eyes sit behind a refractive cornea: without this the eyeballs render black
S.render.resolution_x, S.render.resolution_y = 1080, 1920; S.render.resolution_percentage = int(os.environ.get('PCT', '100')); S.render.fps = FPS
# water beads that land on the lens in the last shot (children of the camera)
splats = []
for i in range(16):
    o = obj_of('uv_sphere', f'splat{i}', bub_m, radius=1, location=(0, 0, 0), segments=20, ring_count=10); smooth(o); o.parent = CAM
    splats.append((o, rnd.uniform(-0.034, 0.034), rnd.uniform(-0.06, 0.05), rnd.uniform(0.0012, 0.003), rnd.random() * 0.25))   # small beads: big ones read as soap bubbles
into(C_DROP, [s[0] for s in splats])

orig_mats = {o.name: [s.material for s in o.material_slots] for o in ned.parts if o.type == 'MESH'}
ALL_C = (C_CAR, C_HOS, C_XR, C_MAC, C_SKIN, C_CAL, C_SCAN, C_DROP)
def show(colls_on):
    for c in ALL_C: c.hide_render = c not in colls_on
def vis(p, on, xray=False):
    for o in p.parts:
        if o.type == 'ARMATURE': continue
        o.hide_render = (not on) or (xray and o is not p.body)   # curves too (stethoscope tube, lanyards)
    if p is ned:
        for i, s in enumerate(ned.body.material_slots): s.material = xray_body if xray else orig_mats[ned.body.name][i]
def look_at(pos, tgt, lens, fstop=2.8, focus=None, roll=0.0):
    CAM.location = pos; q = (Vector(tgt) - Vector(pos)).to_track_quat('-Z', 'Y'); CAM.rotation_euler = q.to_euler()
    if roll: CAM.rotation_euler.rotate_axis('Z', math.radians(roll))
    cam_d.lens = lens; cam_d.dof.use_dof = True; cam_d.dof.aperture_fstop = fstop; cam_d.dof.focus_distance = (Vector(focus or tgt) - Vector(pos)).length
def shake(t, amp, f=9.0):
    return Vector((math.sin(t * f * 1.3) * amp, math.sin(t * f * 0.7 + 1) * amp * 0.5, math.sin(t * f + 2) * amp))
def face(p, **vals):
    want = {}
    for nm, v in vals.items():
        for path, w in P.EXPR[nm]: want[path] = max(want.get(path, 0), v * w)
    for path, k in p.keys.items(): k.value = min(k.slider_max, want.get(path, 0.0))
PINCH = dict(idx=(60.4, 9.9, 12), curl=70, th1=(44.5, -10.9, 3.8), th2=(-9.1, 0, 0), th3=(0, 0, 0), wrist=(11.5, -11.5, -60.3), guess=(0.0247, -0.0295, -0.0907), mid=0.5)   # solved with PINCHOPT
def pinch_hand(p, side, k):
    """thumb and index clamp the nose, other fingers tucked (angles tuned by eye with CAMOV/PINCHVARS debug renders)"""
    c = PINCH; sg = -1 if side == 'L' else 1
    for j in (1, 2, 3):
        p.rot(f'finger2-{j}.{side}', (c['idx'][j - 1] * k + 10 * (1 - k), 0, 0))
        for f in (3, 4, 5): p.rot(f'finger{f}-{j}.{side}', ((25 + c['curl'] * k) * (0.8 if j == 1 else 1.0), 0, 0))
        a = c[f'th{j}']; p.rot(f'finger1-{j}.{side}', (k * a[0], k * a[1] * sg, k * a[2] * sg))
    w = c['wrist']; p.rot(f'wrist.{side}', (k * w[0], k * w[1] * sg, k * w[2] * sg))
def pinch_tip(p):
    """point that should sit on the nose: index tip, or between index and thumb tips (mid=0.5)"""
    return p.bone_world('finger2-3.R', tail=True).lerp(p.bone_world('finger1-3.R', tail=True), PINCH['mid'])
def calibrate_pinch():
    global NOSE_W
    pinch_hand(ned, 'R', 1.0); tgt = NOSE_TIP + Vector(PINCH['guess']); want = NOSTRIL_L.lerp(NOSTRIL_R, PINCH['mid'])
    for _ in range(7):
        ned.reach('R', tgt, w=1.0, pole=R_POLE); bpy.context.view_layer.update(); tgt = tgt + (want - pinch_tip(ned)) * 0.9
    NOSE_W = tgt
    print('pinch err', (want - pinch_tip(ned)).length, 'gap', (ned.bone_world('finger2-3.R', tail=True) - ned.bone_world('finger1-3.R', tail=True)).length)
def reach_tip(p, side, tip_bone, desired, pole, guess=None, iters=4):
    """wrist IK target that puts a fingertip (not the wrist) on a point"""
    tgt = Vector(guess if guess is not None else desired)
    for _ in range(iters):
        p.reach(side, tgt, w=1.0, pole=pole); bpy.context.view_layer.update()
        tgt = tgt + (Vector(desired) - p.bone_world(tip_bone, tail=True)) * 0.9
    return tgt
def poly_at(pts, s):
    s = min(1.0, max(0.0, s)); L = [(pts[i + 1] - pts[i]).length for i in range(len(pts) - 1)]; d = s * sum(L)
    for i, l in enumerate(L):
        if d <= l or i == len(L) - 1: return pts[i].lerp(pts[i + 1], min(1.0, d / l))
        d -= l
def set_drops(t0, t, origin, on):
    dt = t - t0
    for o, v, r in drops:
        if on and dt > 0:
            o.location = origin + v * (0.085 * (1 - math.exp(-7 * dt))) + Vector((0, 0, -0.9 * dt * dt)); o.scale = (r * (1 + 0.5 * min(dt, 0.4)),) * 3   # air drag: a spray that hangs and falls, never balloons at the lens
        else: o.scale = (0.00001,) * 3
wheel_rot0 = wheel.rotation_euler.copy()
# calibrate hand targets once (same result in every shard)
R_POLE = Vector((-0.55, -0.3, cz - 0.5))
def mesh_nose_tip(p):
    """most forward skin point on the face midline = tip of the nose (measured, not guessed)"""
    dg = bpy.context.evaluated_depsgraph_get(); ev = p.body.evaluated_get(dg); mw = ev.matrix_world; hb = p.bone_world('head'); best = None
    for v in ev.data.vertices:
        w = mw @ v.co
        if abs(w.x - hb.x) < 0.012 and -0.02 < w.z - hb.z < 0.12 and (best is None or w.y < best.y): best = w.copy()
    return best
NOSE_TIP = mesh_nose_tip(ned); print('nose tip', NOSE_TIP, 'guess was', nose_pt)
NOSTRIL_R = NOSE_TIP + Vector((-0.019, 0.013, 0.004)); NOSTRIL_L = NOSE_TIP + Vector((0.019, 0.013, 0.004));
NECK_R = ned.bone_world('neck02') + Vector((-0.06, -0.05, -0.01))
def doc_fingers():
    for j in (1, 2, 3):
        doc.rot(f'finger2-{j}.R', (5, 0, 0)); doc.rot(f'finger3-{j}.R', (9, 0, 0)); doc.rot(f'finger1-{j}.R', (20, 0, 0))
        for f in (4, 5): doc.rot(f'finger{f}-{j}.R', (72, 0, 0))
calibrate_pinch(); ned.rot('wrist.R', (0, 0, 0))
HEAD_INV = (ned.rig.matrix_world @ ned.pb('head').matrix).inverted(); NOSTRIL_LOC = HEAD_INV @ NOSTRIL_L
P.fingers(ned, 'R', 0.25, thumb=0.2); NECK_W = reach_tip(ned, 'R', 'finger3-3.R', NECK_R, R_POLE, NECK_R + Vector((-0.08, -0.1, -0.05)))
bpy.context.view_layer.update(); DOC_POLE = doc.bone_world('lowerarm01.R') + Vector((0.3, -0.2, -0.6))
doc_fingers(); DOC_W = reach_tip(doc, 'R', 'finger2-3.R', NECK_L, DOC_POLE, NECK_L + Vector((0.17, -0.08, -0.02)))
DOC_REST = doc.bone_world('upperarm01.R') + Vector((-0.05, -0.3, -0.3)); PRESS_DIR = (ned.bone_world('neck02') - NECK_L).normalized()
print('calibrated', NOSE_W, NECK_W, DOC_W)
def wheel_center(): return wheel.matrix_world.translation.copy() if K else wheel.location.copy()

def update(t):
    name, u, L = shot_at(t); un = u / L
    xr = name.startswith('xray'); mac = name.startswith('macro'); hosp = name.startswith('hos'); carsh = name.startswith('car')
    vis(ned, carsh or xr or hosp, xr); vis(doc, hosp); vis(ns, name == 'normal_sneeze')
    if nurse: vis(nurse, hosp)
    show({C_CAR, C_DROP} if carsh else {C_XR} if xr else {C_MAC} if mac else {C_HOS} if hosp else {C_SKIN} if name == 'skin_block'
         else {C_CAL} if name == 'calendar' else {C_SCAN} if name == 'scan' else {C_DROP})
    world('car' if carsh else 'night' if xr else 'sky' if (mac or name == 'skin_block') else 'warm' if name == 'normal_sneeze' else 'hospital')
    people_l = carsh or hosp or xr or name == 'normal_sneeze'
    for o, base, e in PL:
        o.hide_render = (not people_l) or bool(K and (carsh or hosp)); o.location = base + (NS0 if name == 'normal_sneeze' else Vector((0, 0, 0)))
        o.data.energy = e * (0.0 if xr else 1.0 / LK if name == 'normal_sneeze' else 1.0)
    prop_lights(M0, 1.0, on=False)
    if car:
        car.update(t)
        if getattr(car, 'belt', None): car.belt.hide_render = not carsh
    sa = math.sin(t * 0.9) * 0.07 + 0.25 * bump(t, 3.5, 0.35)
    if car and hasattr(car, 'steer'): car.steer(sa)
    else: wheel.rotation_euler = wheel_rot0.copy(); wheel.rotation_euler.rotate_axis('Z', sa)
    # ---- Ned's performance by time (continuous across shots) ----
    late = t >= 24.7
    pre = (1 - ramp(t, 0.25, 0.6))                                   # the "ah-" before the pinch lands
    pinch = (0.3 + 0.7 * ramp(t, 0.0, 0.5)) * (1 - ramp(t, 14.0, 14.7))
    puff = ramp(t, 1.45, 2.1) * (1 - ramp(t, 13.9, 14.3)); bulge = ramp(t, 1.7, 2.4) * (1 - ramp(t, 13.9, 14.5))
    red = ramp(t, 1.5, 3.4) * (1 - 0.75 * ramp(t, 13.9, 15.5)); swell = ramp(t, 14.2, 15.5)
    to_neck = ramp(t, 14.0, 14.8)
    inhale = ramp(t, 24.75, 25.35) * (1 - ramp(t, T_END, T_END + 0.08)); blast = ramp(t, T_END, T_END + 0.08) * (1 - ramp(t, T_END + 0.45, T_END + 0.85)); relief = ramp(t, T_END + 0.5, T_END + 0.9)
    wince = max(bump(t, PRESS[0] + 0.1, 0.2), bump(t, PRESS[1] + 0.1, 0.2)) if hosp else 0
    if late: pinch = puff = bulge = swell = to_neck = 0; red = 0.25 * blast
    worry = (0.9 * ramp(t, 14.2, 14.8) if not late else 0)
    face(ned, twitch=pre * 0.8, open=max(pre * 0.45 * (1 - ramp(t, 0.9, 1.3)), inhale * 0.5, blast), squint=max(pre * 0.5, inhale * 0.7, blast, wince * 0.5),
         puff=puff * (1.3 + 0.15 * math.sin(t * 9)), pressed=puff, bulge=bulge * (1 + 0.08 * math.sin(t * 7)), neckswell=swell * 1.3, worry=worry, grimace=wince * 0.7,
         wide=0.5 * worry, smile=relief * 0.8)
    flush(red)
    head_back = -pre * 12 - inhale * 16 + blast * 14
    ned.rot('head', (head_back - 4 + 6 * worry * (0 if hosp else 1), 0, 0)); ned.rot('neck02', (head_back * 0.5, 0, 0)); ned.rot('spine02', (blast * 7 - inhale * 5, 0, 0))
    bpy.context.view_layer.update(); nose_d = (ned.rig.matrix_world @ ned.pb('head').matrix @ NOSTRIL_LOC) - NOSTRIL_L
    wc = wheel_center()
    ned.reach('L', wc + Vector((0.16, 0.02, 0.05)), w=0.0 if hosp else 1.0, pole=ned.bone_world('lowerarm01.L') + Vector((0.5, 0.3, -0.6)))
    r_tgt = (wc + Vector((-0.16, 0.02, 0.05))).lerp(NOSE_W + nose_d, pinch).lerp(NECK_W, to_neck)
    ned.reach('R', r_tgt, w=0.0 if hosp else 1.0, pole=R_POLE)
    pinch_hand(ned, 'R', pinch); P.fingers(ned, 'L', 0.6, thumb=0.3)
    if to_neck > 0 and not late: P.fingers(ned, 'R', 0.25 + 0.3 * (1 - to_neck), thumb=0.2)
    if late: P.fingers(ned, 'R', 0.6, thumb=0.3)
    # ---- doctor ----
    if hosp:
        pr = max(bump(t, PRESS[0], 0.16), bump(t, PRESS[1], 0.16)); near = ramp(t, 15.9, 17.0)
        doc.reach('R', DOC_REST.lerp(DOC_W + PRESS_DIR * (0.014 * pr - 0.012), near), w=1.0, pole=DOC_POLE); doc_fingers()
        doc.rot('head', (12, 0, 0)); face(doc, worry=0.5, wide=0.3 * pr)
        if nurse: nurse.rot('head', (8, 0, 14)); face(nurse, worry=0.4)
        if crackle: crackle.set(pr)
    # ---- normal sneezer ----
    if name == 'normal_sneeze':
        ih = ramp(t, 9.45, 9.9) * (1 - ramp(t, T_NS, T_NS + 0.08)); bl = ramp(t, T_NS, T_NS + 0.08) * (1 - ramp(t, T_NS + 0.5, T_NS + 0.9))
        face(ns, open=max(ih * 0.5, bl), squint=max(ih * 0.7, bl), smile=0.6 * ramp(t, T_NS + 0.6, T_NS + 0.95))
        hb = -ih * 18 + bl * 15; ns.rot('head', (hb, 0, 0)); ns.rot('neck02', (hb * 0.5, 0, 0)); ns.rot('spine02', (bl * 8 - ih * 6, 0, 0))
        for s_, sx_ in (('L', 1), ('R', -1)): ns.reach(s_, NS_SH[s_] + Vector((0.07 * sx_, -0.05 - 0.1 * bl, -0.56 + 0.05 * bl)), w=1.0, pole=NS_SH[s_] + Vector((0.2 * sx_, 0.7, -0.3)))
    bpy.context.view_layer.update()
    hc = ned.bone_world('head') + Vector((0, -0.03, 0.03))
    # ---- x-ray dynamics ----
    if xr:
        heat = ramp(t, 6.0, 8.8); pulse = 0.5 + 0.5 * math.sin(t * 16)
        air_wall.node_tree.nodes['Principled BSDF'].inputs['Emission Strength'].default_value = 0.6 + heat * (2.5 + 2.0 * pulse)
        trachea.data.bevel_depth = 0.0105 * (1 + 0.45 * heat * (0.6 + 0.4 * pulse)); oral.data.bevel_depth = 0.0105 * (1 + 0.5 * ramp(t, 5.6, 6.6))
        sq = 1 - 0.14 * ramp(t, 5.0, 5.7)
        for o in C_XR.objects:
            if o.name.startswith('lung'): o.scale = (0.062 * sq, 0.06 * sq, 0.125 * (0.96 + 0.04 * sq))
        hit = ramp(t, 5.5, 5.62); sp_ = hit * (1.0 + 0.25 * math.sin(t * 20))
        for s_, b_ in zip(seals, seal_base): s_.scale = tuple(v * max(sp_, 0.001) for v in b_); s_.hide_render = hit <= 0
        if gauge: gauge.root.scale = (1, 1, 1) if name == 'xray_gauge' else (0.0001,) * 3
        seal_em.inputs['Strength'].default_value = 8 + 8 * pulse
        for o, ph_, ox, oy, sp, nose_way, side in parts:
            path = [lung_c[side], tr_bot, tr_top, ph] + ([nb, nostril] if nose_way else [ph.lerp(lips, 0.5), lips])
            s_end = 1.0 - 0.72 * sp
            s = min((t - 5.0 - 0.55 * ph_) * 1.9, s_end)
            jit = (0.0035 + 0.006 * heat) * (1 if s >= s_end else 0.4)
            p_ = poly_at(path, s) + Vector((ox * 0.004 + math.sin(t * (17 + 9 * sp) + ph_ * 20) * jit, oy * 0.004 + math.cos(t * (15 + 7 * ph_) + sp * 9) * jit, math.sin(t * (13 + 11 * ph_)) * jit))
            o.location = p_; o.scale = (1.0 if s > 0 else 0.0001,) * 3
        air_em.inputs['Color'].default_value = (0.55 + 0.45 * heat, 1.0 - 0.75 * heat, 0.05, 1)
        gv = 0.1 + 0.4 * ramp(t, 6.4, 7.85) + 0.5 * ramp(t, 8.35, 8.75); k20 = P_back(min(1, (t - 8.7) / 0.3)) if t >= 8.7 else 0.0
        if gauge: gauge.set(gv, shake=0.2 * heat + 0.8 * ramp(t, 8.6, 8.8)); lab20.set(scale=max(k20, 0.0001))
        else: lab20.scale = (max(k20, 0.0001),) * 3
    # ---- macro dynamics ----
    if mac:
        prop_lights(M0, 1.0, gain=0.42)
        open_ = ramp(t, T_TEAR, T_TEAR + 0.22) if t < 18 else 1.0
        strain = ramp(t, 11.0, T_TEAR) * (1 - ramp(t, T_TEAR, T_TEAR + 0.15)) if t < 13 else 0
        tubeo.scale = (1, 1 + 0.05 * strain * (0.7 + 0.3 * math.sin(t * 40)), 1 + 0.05 * strain * (0.7 + 0.3 * math.sin(t * 40)))
        cutter.scale = (0.105 * open_ + 0.0005, 0.14, 0.062 * open_ + 0.0005)
        flash.energy = 400 * math.exp(-max(0, t - T_TEAR) * 5) * (T_TEAR < t < 13)
        for o, v, r, d in jets:
            dt = t - T_TEAR - d * 0.5
            if 0 < dt < 1.2 and t < 13: o.location = HOLE + v * dt * 0.8 + Vector((0, 0, 0.3 * dt * dt)); o.scale = (r * (1 - dt / 1.2),) * 3
            else: o.scale = (0.00001,) * 3
        for o, ox, oy, ph_, r in bubbles:
            if name == 'macro_leak':
                s = max(0, (t - 18.45 - ph_ * 1.4)) * 0.6
                o.location = HOLE + Vector((ox * 0.05 + ox * s * 0.7, -s * 0.75, oy * 0.03 + s * (0.3 + 0.5 * oy))); o.scale = (r * min(1, s * 7),) * 3
            elif name == 'macro_hole':
                s = max(0, (t - 12.2 - ph_ * 2.5)) * 0.35
                o.location = HOLE + Vector((ox * 0.04 + ox * s * 0.4, -s * 0.8, oy * 0.02 + s * (0.5 + 0.3 * oy))); o.scale = (r * 0.5 * min(1, s * 7),) * 3
            else: o.scale = (0.0001,) * 3
        kb = ramp(t, 12.25, 12.7) if name == 'macro_hole' else 0.0
        if bracket: bracket.set(grow=kb)
        else: lab2.scale = (max(P_back(kb), 0.0001),) * 3 if kb > 0 else (0.0001,) * 3
    set_drops(T_NS, t, ns.bone_world('head') + fwd * 0.1 + Vector((0, 0, -0.035)), name == 'normal_sneeze') if name == 'normal_sneeze' else set_drops(T_END, t, ned.bone_world('head') + fwd * 0.1 + Vector((0, 0, -0.035)), name == 'car_sneeze')
    for o, x, y, r, d in splats:
        k = ramp(t, T_END + 0.2 + d, T_END + 0.28 + d) if name == 'car_sneeze' else 0
        o.location = (x, y - 0.006 * max(0, t - T_END - 0.3 - d), -0.14); o.scale = (max(r * k, 0.00001), max(r * k * 1.15, 0.00001), max(r * k * 0.35, 0.00001))
    # ---- cameras ----
    if name == 'car_pinch':
        look_at(HC0 + Vector((0.07, -0.6 + 0.12 * ease(un), 0.0)) + shake(t, 0.002), HC0 + Vector((0, 0, -0.035)), 42, 5.6)
    elif name == 'car_cheeks':
        look_at(hc + Vector((0.34 - 0.06 * un, -0.5 + 0.07 * un, 0.0)) + shake(t, 0.002 * (1 + 2 * puff), 14), hc + Vector((0.01, -0.03, -0.03)), 50, 5.6)
    elif name == 'car_hood':
        look_at(Vector((0.6 - 0.06 * un, -0.78 + 0.06 * un, hz + 0.03)) + shake(t, 0.004), hc + Vector((0.0, -0.06, -0.07)), 32, 4.0, focus=hc)   # from the passenger seat: wheel, road and trees going by
    elif name == 'car_plunge':
        k = un ** 2.2
        look_at(hc + Vector((0.05 * (1 - k), -0.55 + 0.47 * k, -0.02 - 0.03 * k)), hc + Vector((0, 0, -0.04 - 0.04 * k)), 38, 5.6)
    elif name == 'xray_profile':
        tg = tr_bot.lerp(ph, ease(un) * 0.9) + Vector((0, -0.03, 0.02))
        look_at(tg + Vector((0.72 - 0.16 * un, -0.12, 0.03)), tg, 38, 8.0)
    elif name == 'xray_throat':
        look_at(tr_top + Vector((0.3, -0.5 + 0.07 * un, -0.02)) + shake(t, 0.002, 15), tr_top + Vector((0.035, 0, -0.07)), 42, 8.0)
    elif name == 'xray_gauge':
        look_at(G0 + Vector((0.1, -0.5 + 0.1 * ease(un), 0.04)) + shake(t, 0.006 * ramp(t, 8.6, 8.8) * (1 - ramp(t, 9.0, 9.4)), 26), G0 + Vector((-0.045, 0, 0.035)), 44, 8.0)
    elif name == 'normal_sneeze':
        nh = NS_HEAD
        look_at(nh + Vector((0.55 - 0.08 * un, -1.15, 0.0)) + shake(t, 0.01 * math.exp(-max(0, t - T_NS) * 4) * (t > T_NS), 25), nh + Vector((0.03, -0.1, -0.1)), 46, 5.6, focus=nh)
    elif name == 'macro_tear':
        look_at(M0 + Vector((0.75 - 0.3 * un, -1.75 + 0.45 * un, 0.45 - 0.12 * un)) + shake(t, 0.012 * (t > T_TEAR) + 0.004 * (t <= T_TEAR), 22), HOLE + Vector((0, 0, 0.0)), 34, 5.6)
    elif name == 'macro_hole':
        look_at(HOLE + Vector((-0.18 + 0.1 * un, -0.78 + 0.1 * un, 0.14)), HOLE + Vector((0, 0, 0.05)), 40, 8.0)
    elif name == 'car_neck':
        look_at(hc + Vector((-0.1 + 0.05 * un, -0.66 + 0.1 * un, -0.05)) + shake(t, 0.002), hc + Vector((0, 0, -0.105)), 42, 4.0)
    elif name == 'hos_wide':
        nk = ned.bone_world('neck02')
        look_at(Vector((-0.42 + 0.1 * un, -1.45 + 0.12 * un, hz + 0.08)), nk + Vector((0.2, 0, 0.02)), 34, 4.0, focus=nk)
    elif name == 'hos_press':
        nk = NECK_L
        look_at(nk + Vector((0.02, -0.46 + 0.05 * un, 0.04)) + shake(t, 0.003 * wince, 20), nk + Vector((0.035, 0, -0.005)), 50, 5.6)
    elif name == 'macro_leak':
        look_at(M0 + Vector((-0.9 + 0.25 * un, -1.5 + 0.2 * un, 0.75 - 0.1 * un)), HOLE + Vector((0.05, -0.2, 0.22)), 34, 5.6)
    elif name == 'skin_block':
        prop_lights(SK0, 0.45, gain=0.8); bb = ramp(t, 20.15, 21.0); pr = bump(t, 21.3, 0.22)
        if skinblock: skinblock.set(bubbles=bb, press=pr)
        look_at(SK0 + Vector((0.55 - 0.1 * un, -1.0 + 0.12 * un, 0.55 - 0.05 * un)), SK0 + Vector((0, 0, 0.02)), 40, 8.0)
    elif name == 'calendar':
        prop_lights(CA0, 0.4, gain=0.5); cu_ = ramp(t, 21.85, 22.7)
        if calendar: calendar.set(cu_)
        else: callab.scale = (P_back(ramp(t, 21.85, 22.2)),) * 3
        look_at(CA0 + Vector((0.1 - 0.06 * un, -1.05 + 0.1 * un, 0.0)), CA0, 45, 5.6)
    elif name == 'scan':
        prop_lights(SC0, 0.4, gain=0.25)
        if scan: scan.set(heal=ramp(t, 23.55, 24.4), on=1.0)
        look_at(SC0 + Vector((-0.22 + 0.12 * un, -1.15 + 0.3 * ease(un), 0.06)), SC0 + Vector((0, 0, 0.0)), 42, 5.6)
    elif name == 'car_sneeze':
        look_at(HC0 + Vector((0.07, -0.6 - 0.1 * (1 - un), 0.0)) + shake(t, 0.014 * math.exp(-max(0, t - T_END) * 3) * (t > T_END), 25), HC0 + Vector((0, 0, -0.035)), 42, 11.0)

if __name__ == '__main__':
    out, i0, i1 = sys.argv[-3], int(sys.argv[-2]), int(sys.argv[-1]); os.makedirs(out, exist_ok=True)
    only = os.environ.get('ONLY')
    frames = [int(x) for x in only.split(',')] if only else range(i0, i1)
    if os.environ.get('PINCHOPT'):     # one-off solver: find the hand pose that clamps the nose (result is pasted into PINCH)
        import time, random as _r
        A_L = NOSTRIL_L; A_R = NOSTRIL_R; S.frame_set(30); update(30 / FPS)
        for b_ in ('head', 'neck02', 'spine02'): ned.rot(b_, (0, 0, 0))
        names = ['tx', 'ty', 'tz', 'wx', 'wy', 'wz', 'ax', 'ay', 'az', 'b', 'i1', 'i2']
        x0 = [0.0233, -0.2091, 1.6037, 12.8, -11.8, -59.6, 51.7, -17.5, -5.0, -12.9, 60.7, 6.7]; sc = [0.03, 0.03, 0.03, 25, 25, 25, 25, 25, 25, 20, 15, 15]
        def cost(x):
            PINCH.update(wrist=(x[3], x[4], x[5]), th1=(x[6], x[7], x[8]), th2=(x[9], 0, 0), idx=(x[10], x[11], 12)); pinch_hand(ned, 'R', 1.0)
            ned.reach('R', Vector(x[:3]), w=1.0, pole=R_POLE); bpy.context.view_layer.update()
            it = ned.bone_world('finger2-3.R', tail=True); tt = ned.bone_world('finger1-3.R', tail=True); c = (it - A_L).length ** 2 + (tt - A_R).length ** 2
            for b_ in ('finger2-1.R', 'finger2-2.R', 'finger1-2.R', 'finger3-1.R', 'finger3-2.R', 'finger3-3.R', 'wrist.R'):
                q = ned.bone_world(b_); c += max(0, q.y - (NOSE_TIP.y + 0.004)) ** 2 * 4 + max(0, q.z - (NOSE_TIP.z - 0.012)) ** 2 * 2
            for b_ in ('finger2-3.R', 'finger1-3.R'):
                d_ = (ned.bone_world(b_, tail=True) - ned.bone_world(b_)).normalized(); c += (1 - d_.z) ** 2 * float(os.environ.get('UPW', '4e-4'))
            for v_, lim in ((x[3], 45), (x[4], 60), (x[5], 60), (x[6], 60), (x[7], 45), (x[8], 45), (x[9], 50)): c += (max(0, abs(v_) - lim) * 0.002) ** 2
            for v_ in (x[10], x[11]): c += (max(0, -v_, v_ - 60) * 0.002) ** 2
            return c
        t0 = time.time(); n = len(x0); simp = [list(x0)] + [[x0[j] + (sc[j] if j == i else 0) for j in range(n)] for i in range(n)]; fv = [cost(p_) for p_ in simp]
        for it_ in range(int(os.environ['PINCHOPT'])):       # Nelder-Mead
            o = sorted(range(n + 1), key=lambda i: fv[i]); simp = [simp[i] for i in o]; fv = [fv[i] for i in o]
            cen = [sum(p_[j] for p_ in simp[:-1]) / n for j in range(n)]
            xr = [cen[j] + (cen[j] - simp[-1][j]) for j in range(n)]; fr = cost(xr)
            if fr < fv[0]:
                xe = [cen[j] + 2 * (cen[j] - simp[-1][j]) for j in range(n)]; fe = cost(xe)
                simp[-1], fv[-1] = (xe, fe) if fe < fr else (xr, fr)
            elif fr < fv[-2]: simp[-1], fv[-1] = xr, fr
            else:
                xc = [cen[j] + 0.5 * (simp[-1][j] - cen[j]) for j in range(n)]; fc = cost(xc)
                if fc < fv[-1]: simp[-1], fv[-1] = xc, fc
                else:
                    simp = [simp[0]] + [[simp[0][j] + 0.5 * (p_[j] - simp[0][j]) for j in range(n)] for p_ in simp[1:]]; fv = [fv[0]] + [cost(p_) for p_ in simp[1:]]
        b = simp[min(range(n + 1), key=lambda i: fv[i])]; print('PINCHOPT', min(fv), time.time() - t0, dict(zip(names, [round(v_, 4) for v_ in b])))
        cost(b); print('tips', (ned.bone_world('finger2-3.R', tail=True) - A_L).length, (ned.bone_world('finger1-3.R', tail=True) - A_R).length)
        for vi, v in enumerate(os.environ.get('CAMOV', '0,-0.5,-0.02,60').split(';')):
            dx, dy, dz, ln = [float(x) for x in v.split(',')]
            look_at(HC0 + Vector((dx, dy, dz)), HC0 + Vector((0, -0.06, -0.06)), ln, 16.0)
            S.render.filepath = os.path.join(out, f'opt_v{vi}.png'); bpy.ops.render.render(write_still=True)
        sys.exit(0)
    for f in frames:
        S.frame_set(f); update(f / FPS); bpy.context.view_layer.update()
        if os.environ.get('CAMOV'):      # debug views: "dx,dy,dz,lens;..." around his head; PINCHVARS = list of PINCH overrides
          for pi_, pv in enumerate(eval(os.environ.get('PINCHVARS', '[{}]'))):
            PINCH.update(pv); calibrate_pinch(); update(f / FPS); bpy.context.view_layer.update()
            for vi, v in enumerate(os.environ['CAMOV'].split(';')):
                dx, dy, dz, ln = [float(x) for x in v.split(',')]
                look_at(HC0 + Vector((dx, dy, dz)), HC0 + Vector((0, -0.06, -0.06)), ln, 16.0)
                S.render.filepath = os.path.join(out, f'f{f:04d}_p{pi_:02d}_v{vi}.png'); bpy.ops.render.render(write_still=True)
          continue
        S.render.filepath = os.path.join(out, f'f{f:04d}.png'); bpy.ops.render.render(write_still=True)
