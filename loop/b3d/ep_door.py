"""Odd Loop ep01 'The Swinging Door'. frame(t) poses everything; render(i0, i1) writes frames. Times in seconds."""
import sys, os, math
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import bpy
from mathutils import Vector
from toon import *
from cast import *
from set_kitchen import *

FPS = 30; TWOS = True          # animate on twos like classic cartoons (each pose held 2 frames)
DURATION = 7.4
YP = 0.75                      # running lane (y) = middle of the doorway
VM, VC = 3.0, 3.1              # mouse and cat speeds
T_IN = 1.25                    # mouse reaches the door
T_HIT = 1.95                   # door swings back into the cat's face

def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def ease(u): u = clamp(u); return u * u * (3 - 2 * u)
def lin(t, a, b): return clamp((t - a) / (b - a))

def door_angle(t):
    """+ = opens away from the kitchen. Mouse bursts through, door swings back hard and stops on the cat's face."""
    if t < T_IN: return 0.0
    if t < T_HIT:
        u = (t - T_IN) / (T_HIT - T_IN)                # 0..1: open to 1.5 rad then back to 0
        return 1.5 * math.sin(math.pi * u) ** 0.7
    if t < 2.75: return -0.03 * math.exp(-(t - T_HIT) * 8) * math.sin((t - T_HIT) * 60)   # rattles on the cat
    if t < 4.3: return 0.0
    if t < 6.6: return 0.32 * ease(lin(t, 4.3, 4.55)) * (1 - ease(lin(t, 6.2, 6.6)))      # mouse peeks out
    return 0.0

def cat_pose(t):
    nose = 1.05                                       # nose distance ahead of the root
    if t < T_HIT:
        x = XD - 0.06 - nose - VC * (T_HIT - t)
        return dict(x=x, run=x * 4.0, lean=0.28, mood='hunt', mouth=0.55, tongue=0.6, arms='reach', yaw=0.55, t=t)
    if t < 2.75:                                      # pancake on the door
        u = lin(t, T_HIT, T_HIT + 0.06)
        return dict(x=XD - 0.06 - nose * (1 - 0.84 * u), flat=u, mood='shock', mouth=0.2, arms='up', yaw=0.0, pop=0.0, t=t, blink=1.0 if t > T_HIT + 0.1 else 0)
    if t < 3.25:                                      # peels off and topples backwards, stiff as a plank
        u = ease(lin(t, 2.75, 3.25)) ** 1.6
        return dict(x=XD - 0.06 - nose * 0.16 - 0.3 * u, flat=1 - 0.5 * u, lean=-1.5 * u, mood='shock', arms='up', yaw=0.0, t=t, blink=1.0)
    k = math.exp(-(t - 3.25) * 10) * math.sin((t - 3.25) * 50)
    return dict(x=XD - 0.06 - nose * 0.16 - 0.3, z=0.05 * k, flat=0.5 - 0.2 * ease(lin(t, 3.25, 4.0)), lean=-1.5, mood='dizzy', arms='up', yaw=0.0, t=t,
                tongue=0.9, mouth=0.5, blink=0.0)

def mouse_pose(t):
    if t < T_IN + 0.3:
        x = XD - 0.2 - VM * (T_IN - t)
        return dict(x=x, run=x * 8.0, lean=0.2, mood='happy', mouth=0.7, look=(1, 0), t=t), True
    if 4.35 < t < 6.6:                                # peeks round the door, giggles and waves
        return dict(x=XD + 0.25, yaw=2.4, mood='cheeky', mouth=0.9, arms='wave', look=(1, 0), t=t, tilt=0.15 * math.sin(t * 14)), True
    return dict(x=XD + 3, t=t), False

def build():
    clear(); s = bpy.context.scene
    s.render.engine = 'CYCLES'; s.cycles.device = 'CPU'; s.cycles.samples = int(os.environ.get('SAMPLES', 8)); s.cycles.use_denoising = True; s.cycles.denoiser = 'OPENIMAGEDENOISE'; s.cycles.denoising_prefilter = 'FAST'; s.cycles.adaptive_threshold = 0.1; s.cycles.caustics_reflective = s.cycles.caustics_refractive = False
    s.cycles.max_bounces = 3; s.cycles.diffuse_bounces = 2; s.cycles.glossy_bounces = 1; s.cycles.transmission_bounces = 0; s.render.use_persistent_data = False
    s.render.resolution_x, s.render.resolution_y = 1080, 1920; s.render.resolution_percentage = int(os.environ.get('PCT', 67))
    s.view_settings.view_transform = 'Standard'; s.render.image_settings.file_format = 'PNG'
    w = bpy.data.worlds.new('w'); s.world = w; w.use_nodes = True; bg = w.node_tree.nodes['Background']; bg.inputs[0].default_value = (*hexc('#FFE9C7'), 1); bg.inputs[1].default_value = 0.75
    sun = bpy.data.lights.new('sun', 'SUN'); sun.energy = 3.0; sun.angle = math.radians(6); sun.color = hexc('#FFF1D6')
    so = link(bpy.data.objects.new('sun', sun)); so.rotation_euler = (math.radians(52), 0, math.radians(-38))
    fill = bpy.data.lights.new('fill', 'AREA'); fill.energy = 450; fill.size = 6; fill.color = hexc('#CFE3FF')
    fo = link(bpy.data.objects.new('fill', fill)); fo.location = (-3, -6, 5); fo.rotation_euler = (math.radians(55), 0, math.radians(-25))
    S = build_kitchen(); C = build_cat(); M = build_mouse()
    import bmesh
    star_m = mat('star', hexc('#FFD23F'), 0.3, 0.4, emit=0.6); S['stars'] = []
    for k in range(5):
        me = bpy.data.meshes.new('star'); bm = bmesh.new(); pts = []
        for j in range(10):
            a = math.pi / 2 + j * math.pi / 5; r = 0.16 if j % 2 == 0 else 0.07
            pts.append(bm.verts.new((r * math.cos(a), 0, r * math.sin(a))))
        f = bm.faces.new(pts); bmesh.ops.extrude_face_region(bm, geom=[f]); bmesh.ops.translate(bm, vec=(0, 0.05, 0), verts=[v for v in bm.verts if v.co.y == 0 and False])
        bm.to_mesh(me); bm.free(); o = link(bpy.data.objects.new('star', me)); me.materials.append(star_m)
        sol = o.modifiers.new('sol', 'SOLIDIFY'); sol.thickness = 0.05; bev = o.modifiers.new('bev', 'BEVEL'); bev.width = 0.015; bev.segments = 2
        S['stars'].append(o)
    cam = bpy.data.cameras.new('cam'); cam.lens = 34; co = link(bpy.data.objects.new('cam', cam)); s.camera = co
    return s, S, C, M, co

def frame(s, S, C, M, co, t):
    S['door'].rotation_euler = (0, 0, door_angle(t))
    cp = cat_pose(t); cp.setdefault('t', t); pose_cat(C, **cp); C.root.location.y = YP
    mp, vis = mouse_pose(t); pose_mouse(M, **mp); M.root.location.y = YP if mp.get('yaw', 0.85) < 2 else YP - 0.25
    for o in [M.root] + list(M.root.children_recursive): o.hide_render = not vis
    bpy.context.view_layer.update()
    hp = C.head.matrix_world.translation
    for k, o in enumerate(S['stars']):
        on = t > 3.3; o.hide_render = not on
        a = t * 5 + k * 2 * math.pi / 5
        o.location = (hp.x + 0.75 * math.cos(a), hp.y + 0.6 * math.sin(a), hp.z + 0.55 + 0.1 * math.sin(a * 2)); o.rotation_euler = (0, t * 4 + k, 0)
    sh = 0.0
    if t >= T_HIT: sh += 0.09 * math.exp(-(t - T_HIT) * 9) * math.sin((t - T_HIT) * 70)
    if t >= 3.25: sh += 0.06 * math.exp(-(t - 3.25) * 9) * math.sin((t - 3.25) * 70)
    cx = cp['x'] + 1.0 if t < T_HIT else XD - 1.2
    cx = max(-1.6, min(XD - 1.0, cx))
    push = ease(lin(t, T_HIT, T_HIT + 0.5)) * 0.5
    camy = -5.0 + push; camz = 1.7
    if t < 3.45:
        u = ease(lin(t, 2.75, 3.3)) * 0.6                # ease back a little as he topples
        co.location = (cx - 0.5 - 0.8 * u + sh, camy - 1.2 * u, camz + sh * 0.5); co.rotation_euler = (math.radians(86), 0, math.radians(-9))
    else:                                                 # cut: high angle on the pancaked cat, door and peeking mouse
        dr = 0.25 * ease(lin(t, 3.45, DURATION))
        co.location = (-0.05 + sh, -5.6 + dr, 4.6 - dr * 0.5); co.rotation_euler = (math.radians(63), 0, 0)

def cues():
    """Sound cues and impact words, worked out from the same motion the picture uses."""
    C, P = [], []
    pc = pm = None
    for i in range(int(DURATION / 0.002)):
        t = i * 0.002
        if t < T_HIT:
            k = math.floor((cat_pose(t)['x'] * 4.0 - math.pi / 2) / math.pi)
            if pc is not None and k != pc: C.append((t, 'step_cat'))
            pc = k
        mp, vis = mouse_pose(t)
        if vis and mp.get('run') is not None:
            k = math.floor((mp['run'] - math.pi / 2) / math.pi)
            if pm is not None and k != pm: C.append((t, 'step_blob'))
            pm = k
    C += [(T_IN - 0.02, 'door_bash'), (T_HIT, 'door_slam'), (T_HIT + 0.01, 'splat'), (2.75, 'flip_back'), (3.25, 'land'), (3.26, 'splat'),
          (3.36, 'stars'), (4.28, 'door_creak'), (4.6, 'giggle'), (5.25, 'giggle'), (6.58, 'button')]
    P += [(T_HIT, 'BONK!', 0.62, 0.30, 150), (3.25, 'THUD!', 0.38, 0.62, 130), (4.6, 'hee hee', 0.78, 0.48, 80)]
    return dict(duration=DURATION, fps=FPS, twos=TWOS, cues=sorted(C), pow=P)

if __name__ == '__main__':
    if '--cues' in sys.argv:
        import json; json.dump(cues(), open(sys.argv[-1], 'w'), indent=1); sys.exit(0)
    # blender -b -P ep_door.py -- outdir i0 i1   (frame indices at FPS)
    out, i0, i1 = sys.argv[-3], int(sys.argv[-2]), int(sys.argv[-1])
    os.makedirs(out, exist_ok=True)
    s, S, C, M, co = build(); n = int(round(DURATION * FPS))
    for i in range(i0, min(i1, n)):
        if TWOS and i % 2: continue
        frame(s, S, C, M, co, i / FPS)
        s.render.filepath = os.path.join(out, f'f{i:04d}.png'); bpy.ops.render.render(write_still=True)
