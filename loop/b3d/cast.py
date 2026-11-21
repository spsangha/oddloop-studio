"""The two stars. Grumbles: a huge, chubby ginger tom cat (bipedal, Tom-style acting). Pip: a tiny white mouse in red sneakers.
Each character = metaball families (fur / white) + mesh face parts. build_*() once, pose_*(P) every frame."""
import math
from mathutils import Vector, Euler, Matrix
import bpy
from toon import *

def lerp(a, b, u): return a + (b - a) * u
def v3(*a): return Vector(a)

class Rig:
    """Root empty (position, facing, squash) -> head empty (tilt). Metaball elements are re-placed every frame."""
    def __init__(self, name):
        self.root = link(bpy.data.objects.new(name, None)); self.head = link(bpy.data.objects.new(name + '_head', None)); self.head.parent = self.root
        self.parts = {}
    def add(self, key, o, parent='root'):
        o.parent = self.root if parent == 'root' else self.head; self.parts[key] = o; return o

# ------------------------------------------------------------------ cat
def build_cat():
    C = Rig('cat')
    fur = mat('cat_fur', hexc('#F28B26'), 0.62, 0.2, sss=0.04); C.stripe_m = stripe = mat('cat_stripe', hexc('#C25A12'), 0.62, 0.2)
    white = mat('cat_white', hexc('#FFF3E0'), 0.6, 0.2, sss=0.04); pink = mat('cat_pink', hexc('#F29AA3'), 0.45)
    eyew = mat('eye_white', (0.95, 0.95, 0.93), 0.12, 0.7); iris = mat('cat_iris', hexc('#9BCB2E'), 0.2, 0.5); ink = mat('ink', (0.01, 0.008, 0.012), 0.2, 0.6)
    mouth = mat('mouth', hexc('#5E1020'), 0.5); tongue = mat('tongue', hexc('#E8606E'), 0.4); brow = mat('cat_brow', hexc('#7A3608'), 0.6)
    C.body = mball('CatFur', fur, 0.045); C.body.parent = C.root
    C.headb = mball('CatHead', fur, 0.04); C.headb.parent = C.head
    C.limbs = mball('CatLimb', fur, 0.035); C.limbs.parent = C.root
    C.bw = mball('CatWhite', white, 0.04); C.bw.parent = C.root
    C.mitt = mball('CatMitt', white, 0.035); C.mitt.parent = C.root
    C.hw = mball('CatMuzzle', white, 0.035); C.hw.parent = C.head
    C.st = mball('CatStripe', stripe, 0.035); C.st.parent = C.head
    for k in range(2):
        C.add(f'eye{k}', sphere(f'cat_eye{k}', eyew, 1), 'head'); C.add(f'iris{k}', sphere(f'cat_iris{k}', iris, 1), 'head')
        C.add(f'pupil{k}', sphere(f'cat_pupil{k}', ink, 1), 'head'); C.add(f'glint{k}', sphere(f'cat_glint{k}', mat('glint', (1, 1, 1), 0.1, 0.5, emit=1.5), 1), 'head')
        C.add(f'lid{k}', sphere(f'cat_lid{k}', fur, 1), 'head'); C.add(f'brow{k}', sphere(f'cat_brow{k}', brow, 1), 'head')
        C.add(f'ear{k}', cone(f'cat_ear{k}', fur, 0.3, 0.03, 0.62), 'head'); C.add(f'eari{k}', cone(f'cat_eari{k}', pink, 0.18, 0.0, 0.46), 'head')
    C.add('nose', sphere('cat_nose', pink, 1), 'head'); C.add('mouth', sphere('cat_mouth', mouth, 1), 'head'); C.add('tongue', sphere('cat_tongue', tongue, 1), 'head')
    wm = mat('whisker', (0.95, 0.92, 0.85), 0.4)
    for k in range(3):
        for sgn in (1, -1):
            C.add(f'wh{k}{sgn}', curve_line(f'cat_wh{k}{sgn}', wm, [(0, 0, 0), (0.22, 0, 0.02 - 0.03 * k), (0.42, 0, -0.03 - 0.08 * k)], 0.008), 'head')
    return C

def limb(o, a, c, r, bend=0.0, axis=(0, 0, 1)):
    """two capsules a->knee->c; knee pushed sideways by bend along axis"""
    knee = (a + c) / 2 + Vector(axis) * bend
    for p, q in ((a, knee), (knee, c)):
        m = (p + q) / 2; dv = q - p
        el(o, 'CAPSULE', m, r, (dv.length / 2, 1, 1), (0, -math.atan2(dv.z, math.hypot(dv.x, dv.y)) if abs(dv.x) + abs(dv.y) > 1e-6 else -math.pi / 2, math.atan2(dv.y, dv.x)))
    return knee

def pose_cat(C, x=0.0, z=0.0, d=1, yaw=0.85, run=None, lean=0.0, sq=(1, 1, 1), tilt=0.0, mood='hunt', mouth=0.25, tongue=0.0,
             look=(1, 0), arms='swing', pop=0.0, blink=0.0, t=0.0, flat=0.0, crouch=0.0):
    """run = phase (radians) for a two-legged cartoon sprint; flat 0..1 = pancaked against something in front."""
    C.root.location = (x, 0, z); C.root.rotation_euler = (0, lean * d, -yaw if d > 0 else math.pi + yaw)
    sx, sy, sz = sq
    if flat: sx, sy, sz = lerp(sx, 0.16, flat), lerp(sy, 1.5, flat), lerp(sz, 1.18, flat)
    C.root.scale = (sx, sy, sz)
    C.body.data.elements.clear(); C.bw.data.elements.clear(); C.limbs.data.elements.clear(); C.mitt.data.elements.clear()
    bob = abs(math.sin(run)) * 0.14 if run is not None else 0.0
    low = 0.35 * crouch
    # fat torso, belly forward
    el(C.body, 'ELLIPSOID', (0, 0, 1.12 + bob - low), 0.6, (1.05, 1.0, 1.05)); el(C.body, 'ELLIPSOID', (0.0, 0, 1.55 + bob - low), 0.42, (0.95, 1.0, 0.8))
    el(C.bw, 'ELLIPSOID', (0.36, 0, 1.12 + bob - low), 0.46, (0.62, 0.85, 1.0))
    for k, side in enumerate((-1, 1)):   # legs + big feet
        ph = (run or 0.0) + k * math.pi
        sw = math.sin(ph) * 0.5 if run is not None else 0.0; lift = max(0.0, math.cos(ph)) * 0.38 if run is not None else 0.0
        hip = Vector((0.0, side * 0.3, 0.62 + bob - low)); foot = Vector((sw, side * 0.34, 0.14 + lift))
        limb(C.limbs, hip, foot, 0.17, 0.14 + 0.3 * crouch, (1, 0, 0))
        el(C.mitt, 'ELLIPSOID', foot + Vector((0.16, 0, -0.04)), 0.24, (1.55, 0.95, 0.55))
    for k, side in enumerate((-1, 1)):   # arms + white mitts
        ph = (run or 0.0) + (1 - k) * math.pi
        sw = math.sin(ph) * 0.55 if (run is not None and arms == 'swing') else 0.0
        sh = Vector((0.05, side * 0.55, 1.62 + bob - low))
        if arms == 'up': hand = Vector((0.1, side * 0.8, 2.55))
        elif arms == 'reach': hand = Vector((1.1, side * 0.42, 1.75))
        elif arms == 'flail': hand = Vector((0.2 + 0.25 * math.sin(t * 30 + k * 2), side * 0.95, 1.9 + 0.35 * math.cos(t * 30 + k)))
        else: hand = Vector((sw, side * 0.72, 1.0 + bob - low + abs(sw) * 0.35))
        limb(C.limbs, sh, hand, 0.13, -0.08, (1, 0, 0))
        el(C.mitt, 'BALL', hand, 0.2)
    for i in range(26):                    # tail
        u = i / 25; sw = math.sin(t * 5 + u * 3) * 0.18 * u
        el(C.limbs, 'BALL', (-0.62 - 0.55 * u + 0.25 * u ** 3, sw, 0.62 + 1.3 * u * u + bob - low), 0.12 - 0.02 * u + 0.06 * max(0, u - 0.85) / 0.15)
    # head: wide, with cheek fluff and a white muzzle
    C.head.location = (0.12, 0, 2.3 + bob - low); C.head.rotation_euler = (0, -tilt, 0)
    C.headb.data.elements.clear(); C.hw.data.elements.clear(); C.st.data.elements.clear()
    el(C.headb, 'ELLIPSOID', (0, 0, 0), 0.8, (0.92, 1.0, 0.85))
    for sgn in (1, -1): el(C.headb, 'ELLIPSOID', (0.12, sgn * 0.42, -0.25), 0.4, (0.8, 0.9, 0.7))
    el(C.hw, 'ELLIPSOID', (0.55, 0, -0.22), 0.42, (0.75, 1.15, 0.62))
    el(C.hw, 'ELLIPSOID', (0.42, 0, -0.42), 0.3, (0.7, 0.9, 0.5))     # chin
    for k in range(3): el(C.st, 'ELLIPSOID', (0.25 - 0.22 * k, 0, 0.6 - 0.04 * k), 0.22, (0.35, 0.9, 0.4), (0, 0.3 + 0.25 * k, 0))
    P = C.parts; lx, ly = look; s = 1 + 1.4 * pop; push = 0.35 * pop
    ang = {'hunt': 0.45, 'angry': 0.7, 'shock': -0.35, 'dizzy': -0.15, 'smug': 0.3}.get(mood, 0)
    for k, sgn in enumerate((-1, 1)):
        ey = sgn * 0.23; ex, ez = 0.6 + push, 0.16
        P[f'eye{k}'].location = (ex, ey, ez); P[f'eye{k}'].scale = (0.16 * s, 0.19 * s, 0.27 * s)
        f = Vector((ex + 0.09 * s, ey + 0.03 * lx * sgn * 0, ez + 0.05 * ly))
        P[f'iris{k}'].location = (ex + 0.1 * s, ey + 0.03 * lx - sgn * 0.02, ez + 0.05 * ly - 0.02); P[f'iris{k}'].scale = (0.08 * s, 0.11 * s, 0.14 * s)
        dz = 0.05 if mood != 'dizzy' else 0.02
        P[f'pupil{k}'].location = (ex + 0.15 * s, ey + 0.03 * lx - sgn * 0.02, ez + 0.06 * ly - 0.02); P[f'pupil{k}'].scale = (0.05 * s, 0.06 * s, 0.1 * s if mood != 'dizzy' else 0.035)
        P[f'glint{k}'].location = (ex + 0.19 * s, ey + 0.035 + 0.03 * lx - sgn * 0.02, ez + 0.07 + 0.06 * ly); P[f'glint{k}'].scale = (0.015, 0.02, 0.025)
        cl = max(blink, 0.42 if mood in ('hunt', 'angry') else (0.25 if mood == 'smug' else 0.0))
        P[f'lid{k}'].location = (ex + 0.01, ey, ez + 0.3 * s - 0.26 * cl * s); P[f'lid{k}'].scale = (0.165 * s, 0.2 * s, 0.11 * s + 0.08 * cl)
        P[f'lid{k}'].rotation_euler = (sgn * ang * 0.6, 0, 0); P[f'lid{k}'].hide_render = cl < 0.04
        P[f'brow{k}'].location = (ex + 0.06, ey * 1.1, ez + 0.36 * s + (0.08 if mood == 'shock' else 0) - 0.04 * cl); P[f'brow{k}'].scale = (0.05, 0.16, 0.04)
        P[f'brow{k}'].rotation_euler = (sgn * ang, 0, 0)
        P[f'ear{k}'].location = (-0.08, sgn * 0.5, 0.62); P[f'ear{k}'].rotation_euler = (sgn * 0.5, -0.2, 0)
        P[f'eari{k}'].location = (0.02, sgn * 0.53, 0.6); P[f'eari{k}'].rotation_euler = (sgn * 0.5, -0.2, 0)
    P['nose'].location = (0.93, 0, -0.08); P['nose'].scale = (0.07, 0.11, 0.065)
    P['mouth'].location = (0.78, 0, -0.38); P['mouth'].scale = (0.14, 0.2, 0.02 + 0.13 * mouth)
    P['tongue'].location = (0.85, 0.04, -0.42 - 0.2 * tongue); P['tongue'].scale = (0.08, 0.09, 0.04 + 0.17 * tongue); P['tongue'].hide_render = tongue < 0.05
    for k in range(3):
        for sgn in (1, -1):
            o = P[f'wh{k}{sgn}']; o.location = (0.82, sgn * 0.3, -0.15); o.rotation_euler = (0, 0, sgn * (1.25 + 0.12 * k))

# ------------------------------------------------------------------ mouse
def build_mouse():
    M = Rig('mouse')
    fur = mat('m_fur', hexc('#F4F1EC'), 0.6, 0.2, sss=0.05); pink = mat('m_pink', hexc('#F6A3B4'), 0.45, 0.2, sss=0.1)
    shoe = mat('m_shoe', hexc('#E3262E'), 0.35, 0.5); sole = mat('m_sole', (0.95, 0.95, 0.95), 0.5)
    eyew = mat('eye_white', (0.95, 0.95, 0.93), 0.12, 0.7); iris = mat('m_iris', hexc('#3A2414'), 0.2, 0.5); ink = mat('ink', (0.01, 0.008, 0.012), 0.2, 0.6)
    mouth = mat('mouth', hexc('#5E1020'), 0.5); nose = mat('m_nose', hexc('#E2405A'), 0.3, 0.5); tooth = mat('tooth', (0.98, 0.97, 0.92), 0.3)
    M.body = mball('MouseBody', fur, 0.025); M.body.parent = M.root
    M.limbs = mball('MouseLimb', fur, 0.02); M.limbs.parent = M.root
    M.tail = mball('MouseTail', pink, 0.018); M.tail.parent = M.root
    M.shoes = mball('MouseShoe', shoe, 0.02); M.shoes.parent = M.root
    M.soles = mball('MouseSole', sole, 0.02); M.soles.parent = M.root
    M.headb = mball('MouseHead', fur, 0.025); M.headb.parent = M.head
    for k in range(2):
        M.add(f'eye{k}', sphere(f'm_eye{k}', eyew, 1), 'head'); M.add(f'iris{k}', sphere(f'm_iris{k}', iris, 1), 'head')
        M.add(f'pupil{k}', sphere(f'm_pupil{k}', ink, 1), 'head'); M.add(f'glint{k}', sphere(f'm_glint{k}', mat('glint', (1, 1, 1), 0.1, 0.5, emit=1.5), 1), 'head')
        M.add(f'lid{k}', sphere(f'm_lid{k}', fur, 1), 'head')
        M.add(f'ear{k}', sphere(f'm_ear{k}', fur, 1), 'head'); M.add(f'eari{k}', sphere(f'm_eari{k}', pink, 1), 'head')
    M.add('nose', sphere('m_nose', nose, 1), 'head'); M.add('mouth', sphere('m_mouth', mouth, 1), 'head'); M.add('teeth', sphere('m_teeth', tooth, 1), 'head')
    wm = mat('m_whisker', (0.35, 0.3, 0.3), 0.4)
    for k in range(2):
        for sgn in (1, -1):
            M.add(f'wh{k}{sgn}', curve_line(f'm_wh{k}{sgn}', wm, [(0, 0, 0), (0.12, 0, 0.01 - 0.02 * k), (0.24, 0, -0.02 - 0.05 * k)], 0.004), 'head')
    return M

def pose_mouse(M, x=0.0, z=0.0, d=1, yaw=0.85, run=None, lean=0.0, sq=(1, 1, 1), tilt=0.0, mood='cheeky', mouth=0.4, look=(1, 0),
               arms='swing', blink=0.0, t=0.0, wave=0.0, scale=1.0):
    M.root.location = (x, 0, z); M.root.rotation_euler = (0, lean * d, -yaw if d > 0 else math.pi + yaw)
    M.root.scale = (sq[0] * scale, sq[1] * scale, sq[2] * scale)
    for o in (M.body, M.limbs, M.tail, M.shoes, M.soles): o.data.elements.clear()
    bob = abs(math.sin(run)) * 0.07 if run is not None else 0.0
    el(M.body, 'ELLIPSOID', (0, 0, 0.5 + bob), 0.26, (0.9, 0.85, 1.15))
    for k, side in enumerate((-1, 1)):
        ph = (run or 0.0) + k * math.pi
        sw = math.sin(ph) * 0.26 if run is not None else 0.0; lift = max(0.0, math.cos(ph)) * 0.2 if run is not None else 0.0
        hip = Vector((0, side * 0.1, 0.32 + bob)); foot = Vector((sw, side * 0.12, 0.08 + lift))
        limb(M.limbs, hip, foot, 0.055, 0.06, (1, 0, 0))
        el(M.shoes, 'ELLIPSOID', foot + Vector((0.07, 0, 0.0)), 0.1, (1.6, 0.95, 0.85))
        el(M.soles, 'ELLIPSOID', foot + Vector((0.07, 0, -0.05)), 0.1, (1.65, 1.0, 0.35))
    for k, side in enumerate((-1, 1)):
        ph = (run or 0.0) + (1 - k) * math.pi
        sw = math.sin(ph) * 0.3 if (run is not None and arms == 'swing') else 0.0
        sh = Vector((0.02, side * 0.2, 0.68 + bob))
        if arms == 'wave' and side < 0: hand = Vector((0.1, side * 0.32, 1.0 + 0.04 * math.sin(t * 25)))
        elif arms == 'hips': hand = Vector((-0.02, side * 0.3, 0.5))
        elif arms == 'push': hand = Vector((0.36, side * 0.18, 0.72))
        elif arms == 'laugh': hand = Vector((0.12, side * 0.16, 0.45 + bob))
        else: hand = Vector((sw, side * 0.27, 0.42 + bob + abs(sw) * 0.2))
        limb(M.limbs, sh, hand, 0.045, -0.04, (1, 0, 0)); el(M.limbs, 'BALL', hand, 0.065)
    for i in range(30):
        u = i / 29; sw = math.sin(t * 7 + u * 5) * 0.08 * u
        el(M.tail, 'BALL', (-0.22 - 0.55 * u, sw, 0.3 + 0.35 * math.sin(u * 2.6) * (1 - 0.3 * u) + bob), 0.03 - 0.012 * u)
    M.head.location = (0.05, 0, 0.98 + bob); M.head.rotation_euler = (0, -tilt, 0)
    M.headb.data.elements.clear()
    el(M.headb, 'ELLIPSOID', (0, 0, 0), 0.3, (1.0, 1.0, 0.95)); el(M.headb, 'ELLIPSOID', (0.25, 0, -0.07), 0.17, (1.1, 0.8, 0.7))
    P = M.parts; lx, ly = look
    for k, sgn in enumerate((-1, 1)):
        ex, ey, ez = 0.22, sgn * 0.11, 0.07
        P[f'eye{k}'].location = (ex, ey, ez); P[f'eye{k}'].scale = (0.08, 0.1, 0.13)
        P[f'iris{k}'].location = (ex + 0.05, ey + 0.015 * lx - sgn * 0.01, ez + 0.025 * ly); P[f'iris{k}'].scale = (0.045, 0.06, 0.075)
        P[f'pupil{k}'].location = (ex + 0.075, ey + 0.017 * lx - sgn * 0.01, ez + 0.03 * ly); P[f'pupil{k}'].scale = (0.03, 0.035, 0.05)
        P[f'glint{k}'].location = (ex + 0.1, ey + 0.02 + 0.015 * lx, ez + 0.05 + 0.03 * ly); P[f'glint{k}'].scale = (0.01, 0.012, 0.015)
        cl = max(blink, 0.3 if mood == 'cheeky' else 0.0)
        P[f'lid{k}'].location = (ex + 0.005, ey, ez + 0.13 - 0.12 * cl); P[f'lid{k}'].scale = (0.085, 0.105, 0.05 + 0.04 * cl); P[f'lid{k}'].hide_render = cl < 0.04
        P[f'lid{k}'].rotation_euler = (-sgn * 0.3, 0, 0)
        P[f'ear{k}'].location = (-0.08, sgn * 0.3, 0.26); P[f'ear{k}'].scale = (0.05, 0.22, 0.22); P[f'ear{k}'].rotation_euler = (sgn * 0.5, 0, 0)
        P[f'eari{k}'].location = (-0.04, sgn * 0.3, 0.26); P[f'eari{k}'].scale = (0.035, 0.17, 0.17); P[f'eari{k}'].rotation_euler = (sgn * 0.5, 0, 0)
    P['nose'].location = (0.44, 0, -0.04); P['nose'].scale = (0.05, 0.05, 0.045)
    P['mouth'].location = (0.34, 0, -0.16); P['mouth'].scale = (0.07, 0.11, 0.015 + 0.06 * mouth)
    P['teeth'].location = (0.39, 0, -0.14); P['teeth'].scale = (0.02, 0.035, 0.03)
    for k in range(2):
        for sgn in (1, -1):
            o = P[f'wh{k}{sgn}']; o.location = (0.4, sgn * 0.06, -0.06); o.rotation_euler = (0, 0, sgn * (1.3 + 0.15 * k))
