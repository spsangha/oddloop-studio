"""Odd Loop human cast (replaces the cat and mouse). Same pose API as cast.py so episodes swap with one import.
Bruno: big grumpy guy (white vest, brown trousers, bald top, huge moustache, stubble). Zip: cheeky kid (backwards red cap, yellow tee, freckles).
Bodies are metaball families (skin / clothes / shoes fuse softly); faces are mesh parts parented to the head empty. +x = facing."""
import math
from mathutils import Vector
import bpy
from toon import *
from cast import Rig, limb, lerp

def _face(R, pre, skin, hairc, iris_hex, big=1.0):
    eyew = mat('eye_white', (0.95, 0.95, 0.93), 0.12, 0.7); iris = mat(pre + '_iris', hexc(iris_hex), 0.2, 0.5)
    ink = mat('ink', (0.01, 0.008, 0.012), 0.2, 0.6); glint = mat('glint', (1, 1, 1), 0.1, 0.5, emit=1.5)
    mouth = mat('mouth', hexc('#5E1020'), 0.5); tongue = mat('tongue', hexc('#E8606E'), 0.4); tooth = mat('tooth', (0.98, 0.97, 0.92), 0.3)
    for k in range(2):
        for n, m in (('eye', eyew), ('iris', iris), ('pupil', ink), ('glint', glint), ('lid', skin), ('brow', hairc), ('ear', skin)):
            R.add(f'{n}{k}', sphere(f'{pre}_{n}{k}', m, 1), 'head')
    for n, m in (('nose', skin), ('mouth', mouth), ('tongue', tongue), ('teeth', tooth)):
        R.add(n, sphere(f'{pre}_{n}', m, 1), 'head')

def _eyes(R, mood, look, blink, pop, ex, ey, ez, er, browz, ang_extra=0.0):
    P = R.parts; lx, ly = look; s = 1 + 1.2 * pop; push = 0.25 * pop
    ang = {'hunt': 0.42, 'angry': 0.6, 'shock': -0.3, 'dizzy': -0.1, 'smug': 0.25, 'cheeky': -0.2, 'happy': -0.15}.get(mood, 0) + ang_extra
    for k, sgn in enumerate((-1, 1)):
        y = sgn * ey; x = ex + push
        P[f'eye{k}'].location = (x, y, ez); P[f'eye{k}'].scale = (er * 0.6 * s, er * s, er * 1.25 * s)
        P[f'iris{k}'].location = (x + er * 0.42 * s, y + er * 0.25 * lx - sgn * er * 0.08, ez + er * 0.3 * ly); P[f'iris{k}'].scale = (er * 0.3 * s, er * 0.55 * s, er * 0.66 * s)
        pz = er * 0.3 if mood != 'dizzy' else er * 0.14
        P[f'pupil{k}'].location = (x + er * 0.6 * s, y + er * 0.27 * lx - sgn * er * 0.08, ez + er * 0.32 * ly); P[f'pupil{k}'].scale = (er * 0.2 * s, er * 0.3 * s, pz * s * 1.2)
        P[f'glint{k}'].location = (x + er * 0.75 * s, y + er * 0.15 + er * 0.25 * lx, ez + er * 0.35 + er * 0.3 * ly); P[f'glint{k}'].scale = (er * 0.07, er * 0.09, er * 0.11)
        cl = max(blink, {'hunt': 0.42, 'angry': 0.45, 'smug': 0.3, 'cheeky': 0.3}.get(mood, 0.0))
        P[f'lid{k}'].location = (x + er * 0.04, y, ez + er * 1.15 * s - er * 1.0 * cl * s); P[f'lid{k}'].scale = (er * 0.64 * s, er * 1.06 * s, er * 0.42 * s + er * 0.3 * cl)
        P[f'lid{k}'].rotation_euler = (sgn * ang * 0.6, 0, 0); P[f'lid{k}'].hide_render = cl < 0.04
        P[f'brow{k}'].location = (x + er * 0.25, y * 1.08, ez + browz * s + (er * 0.35 if mood == 'shock' else 0) - er * 0.15 * cl)
        P[f'brow{k}'].rotation_euler = (sgn * ang, 0, 0)

def _walk(run, k, stride, lift_h):
    ph = (run or 0.0) + k * math.pi
    if run is None: return 0.0, 0.0
    return math.sin(ph) * stride, max(0.0, math.cos(ph)) * lift_h

def _arm(arms, k, side, run, t, sh, rest, up, reach, extra=None):
    ph = (run or 0.0) + (1 - k) * math.pi
    sw = math.sin(ph) * 0.5 if (run is not None and arms == 'swing') else 0.0
    if extra and arms in extra:
        h = extra[arms](k, side)
        if h is not None: return h
    if arms == 'up': return Vector((0.1, side * up[0], up[1]))
    if arms == 'reach': return Vector((reach[0], side * reach[1], reach[2]))
    if arms == 'flail': return Vector((0.2 + 0.25 * math.sin(t * 30 + k * 2), side * up[0] * 1.15, up[1] * 0.78 + 0.3 * math.cos(t * 30 + k)))
    return Vector((sw * rest[2], side * rest[0], rest[1] + abs(sw) * 0.3 * rest[2]))

# ------------------------------------------------------------------ Bruno
def build_bruno():
    B = Rig('bruno')
    B.skin_m = skin = mat('b_skin', hexc('#F2B98F'), 0.5, 0.25, sss=0.06); vest = mat('b_vest', hexc('#F7F5EE'), 0.7, 0.15)
    pants = mat('b_pants', hexc('#7A4A2A'), 0.7, 0.15); shoe = mat('b_shoe', hexc('#1E1A1C'), 0.3, 0.6); belt = mat('b_belt', hexc('#2B1D14'), 0.4, 0.4)
    hair = mat('b_hair', hexc('#2E2018'), 0.6, 0.2); stub = mat('b_stub', hexc('#9AA3B5'), 0.7, 0.1); nose = mat('b_nose', hexc('#EE9C82'), 0.45, 0.25, sss=0.08)
    B.vest = mball('BrunoVest', vest, 0.04); B.pants = mball('BrunoPants', pants, 0.035); B.belt = mball('BrunoBelt', belt, 0.03)
    B.arms = mball('BrunoArm', skin, 0.03); B.shoes = mball('BrunoShoe', shoe, 0.03)
    for o in (B.vest, B.pants, B.belt, B.arms, B.shoes): o.parent = B.root
    B.headb = mball('BrunoHead', skin, 0.035); B.stub = mball('BrunoStub', stub, 0.03); B.hair = mball('BrunoHair', hair, 0.025); B.mous = mball('BrunoMous', hair, 0.02)
    for o in (B.headb, B.stub, B.hair, B.mous): o.parent = B.head
    _face(B, 'b', skin, hair, '#4A6FA5')
    B.parts['nose'].data.materials[0] = nose
    for i in range(3): B.add(f'strand{i}', curve_line(f'b_strand{i}', hair, [(0, 0, 0), (0.08, 0, 0.22), (0.26, 0, 0.3)], 0.014), 'head')
    return B

def pose_bruno(B, x=0.0, z=0.0, d=1, yaw=0.85, run=None, lean=0.0, sq=(1, 1, 1), tilt=0.0, mood='hunt', mouth=0.25, tongue=0.0,
               look=(1, 0), arms='swing', pop=0.0, blink=0.0, t=0.0, flat=0.0, crouch=0.0, **_):
    B.root.location = (x, 0, z); B.root.rotation_euler = (0, lean * d, -yaw if d > 0 else math.pi + yaw)
    sx, sy, sz = sq
    if flat: sx, sy, sz = lerp(sx, 0.16, flat), lerp(sy, 1.45, flat), lerp(sz, 1.15, flat)
    B.root.scale = (sx, sy, sz)
    for o in (B.vest, B.pants, B.belt, B.arms, B.shoes): o.data.elements.clear()
    bob = abs(math.sin(run)) * 0.12 if run is not None else 0.0; low = 0.3 * crouch; h = bob - low
    # barrel chest + gut in a white vest, brown trousers, belt
    el(B.vest, 'ELLIPSOID', (0.04, 0, 1.38 + h), 0.56, (1.0, 1.05, 1.0)); el(B.vest, 'ELLIPSOID', (0.0, 0, 1.75 + h), 0.48, (0.85, 1.15, 0.65))
    el(B.vest, 'ELLIPSOID', (0.18, 0, 1.2 + h), 0.42, (1.0, 0.9, 0.85))          # gut
    el(B.belt, 'ELLIPSOID', (0.04, 0, 0.98 + h), 0.5, (0.98, 1.0, 0.16))
    el(B.pants, 'ELLIPSOID', (0.0, 0, 0.88 + h), 0.48, (0.95, 1.0, 0.45))
    for k, side in enumerate((-1, 1)):
        sw, lift = _walk(run, k, 0.5, 0.36)
        hip = Vector((0.0, side * 0.24, 0.8 + h)); foot = Vector((sw, side * 0.27, 0.16 + lift))
        limb(B.pants, hip, foot, 0.16, 0.12 + 0.3 * crouch, (1, 0, 0))
        el(B.shoes, 'ELLIPSOID', foot + Vector((0.13, 0, -0.06)), 0.18, (1.65, 0.95, 0.6))
    for k, side in enumerate((-1, 1)):
        sh = Vector((0.02, side * 0.6, 1.85 + h))
        hand = _arm(arms, k, side, run, t, sh, (0.78, 1.15 + h, 1.0), (0.85, 2.75), (1.05, 0.42, 1.75))
        limb(B.arms, sh, hand, 0.14, -0.08, (1, 0, 0)); el(B.arms, 'ELLIPSOID', hand, 0.17, (1.0, 0.8, 1.1))
        el(B.arms, 'BALL', sh + Vector((0, -side * 0.02, 0.02)), 0.17)
    # head: bald dome, big jaw with stubble, side hair, three strands, giant moustache
    B.head.location = (0.14, 0, 2.38 + h); B.head.rotation_euler = (0, -tilt, 0)
    for o in (B.headb, B.stub, B.hair, B.mous): o.data.elements.clear()
    el(B.headb, 'ELLIPSOID', (0, 0, 0.08), 0.5, (0.95, 0.9, 1.0)); el(B.headb, 'ELLIPSOID', (0.08, 0, -0.22), 0.46, (1.0, 1.05, 0.72))
    el(B.headb, 'BALL', (0, 0, -0.55), 0.22)                                         # neck
    el(B.stub, 'ELLIPSOID', (0.14, 0, -0.32), 0.43, (0.95, 1.02, 0.6))
    for sgn in (1, -1):
        el(B.hair, 'ELLIPSOID', (-0.18, sgn * 0.42, 0.06), 0.16, (1.4, 0.5, 0.9)); el(B.hair, 'ELLIPSOID', (-0.38, sgn * 0.22, 0.02), 0.16, (0.7, 1.1, 0.9))
        el(B.mous, 'ELLIPSOID', (0.53, sgn * 0.13, -0.24), 0.11, (0.6, 1.3, 0.55), (sgn * 0.35, 0, 0))
        el(B.mous, 'ELLIPSOID', (0.5, sgn * 0.27, -0.3), 0.08, (0.6, 1.2, 0.6), (sgn * 0.7, 0, 0))
    _eyes(B, mood, look, blink, pop, 0.4, 0.17, 0.12, 0.12, 0.2)
    P = B.parts
    for k, sgn in enumerate((-1, 1)):
        P[f'brow{k}'].scale = (0.05, 0.13, 0.045)
        P[f'ear{k}'].location = (-0.02, sgn * 0.47, -0.02); P[f'ear{k}'].scale = (0.06, 0.06, 0.12)
    for i in range(3):
        o = P[f'strand{i}']; o.location = (-0.15, (i - 1) * 0.08, 0.55); o.rotation_euler = (0, 0, (i - 1) * 0.25)
    P['nose'].location = (0.6, 0, -0.04); P['nose'].scale = (0.15, 0.13, 0.13)
    P['mouth'].location = (0.56, 0, -0.42); P['mouth'].scale = (0.07, 0.17, 0.02 + 0.13 * mouth)
    P['teeth'].location = (0.6, 0, -0.36); P['teeth'].scale = (0.03, 0.12, 0.012 + 0.03 * mouth); P['teeth'].hide_render = mouth < 0.3
    P['tongue'].location = (0.61, 0.03, -0.46 - 0.18 * tongue); P['tongue'].scale = (0.06, 0.08, 0.03 + 0.15 * tongue); P['tongue'].hide_render = tongue < 0.05

# ------------------------------------------------------------------ Zip
def build_zip():
    Z = Rig('zip')
    skin = mat('z_skin', hexc('#E9A877'), 0.5, 0.25, sss=0.06); tee = mat('z_tee', hexc('#FFC81E'), 0.65, 0.15); shorts = mat('z_shorts', hexc('#2F6FD0'), 0.65, 0.15)
    shoe = mat('z_shoe', hexc('#E3262E'), 0.35, 0.5); sole = mat('z_sole', (0.95, 0.95, 0.95), 0.5); sock = mat('z_sock', (0.96, 0.96, 0.96), 0.7)
    cap = mat('z_cap', hexc('#E3262E'), 0.5, 0.3); hair = mat('z_hair', hexc('#B4561E'), 0.6, 0.2); frk = mat('z_freckle', hexc('#B86A3E'), 0.6)
    Z.tee = mball('ZipTee', tee, 0.025); Z.shorts = mball('ZipShorts', shorts, 0.022); Z.limbs = mball('ZipLimb', skin, 0.018)
    Z.socks = mball('ZipSock', sock, 0.018); Z.shoes = mball('ZipShoe', shoe, 0.02); Z.soles = mball('ZipSole', sole, 0.02)
    for o in (Z.tee, Z.shorts, Z.limbs, Z.socks, Z.shoes, Z.soles): o.parent = Z.root
    Z.headb = mball('ZipHead', skin, 0.025); Z.cap = mball('ZipCap', cap, 0.022); Z.hair = mball('ZipHair', hair, 0.018)
    for o in (Z.headb, Z.cap, Z.hair): o.parent = Z.head
    _face(Z, 'z', skin, hair, '#6B4226')
    for i in range(6): Z.add(f'frk{i}', sphere(f'z_frk{i}', frk, 1, 16), 'head')
    return Z

def pose_zip(Z, x=0.0, z=0.0, d=1, yaw=0.85, run=None, lean=0.0, sq=(1, 1, 1), tilt=0.0, mood='cheeky', mouth=0.4, look=(1, 0),
             arms='swing', blink=0.0, t=0.0, scale=1.0, **_):
    Z.root.location = (x, 0, z); Z.root.rotation_euler = (0, lean * d, -yaw if d > 0 else math.pi + yaw)
    Z.root.scale = (sq[0] * scale, sq[1] * scale, sq[2] * scale)
    for o in (Z.tee, Z.shorts, Z.limbs, Z.socks, Z.shoes, Z.soles): o.data.elements.clear()
    bob = abs(math.sin(run)) * 0.07 if run is not None else 0.0
    el(Z.tee, 'ELLIPSOID', (0, 0, 0.78 + bob), 0.24, (0.85, 1.0, 1.15))
    el(Z.shorts, 'ELLIPSOID', (0, 0, 0.56 + bob), 0.23, (0.88, 1.02, 0.55))
    for k, side in enumerate((-1, 1)):
        sw, lift = _walk(run, k, 0.28, 0.2)
        hip = Vector((0, side * 0.11, 0.5 + bob)); knee_mid = Vector((sw * 0.5, side * 0.12, 0.33 + bob + lift * 0.5)); foot = Vector((sw, side * 0.13, 0.08 + lift))
        limb(Z.shorts, hip, (hip + knee_mid) / 2 + Vector((0, 0, -0.02)), 0.085)
        limb(Z.limbs, knee_mid, foot + Vector((0, 0, 0.08)), 0.05, 0.03, (1, 0, 0))
        el(Z.socks, 'CAPSULE', foot + Vector((0, 0, 0.1)), 0.058, (0.06, 1, 1), (0, -math.pi / 2, 0))
        el(Z.shoes, 'ELLIPSOID', foot + Vector((0.06, 0, 0.0)), 0.1, (1.6, 0.95, 0.8))
        el(Z.soles, 'ELLIPSOID', foot + Vector((0.06, 0, -0.05)), 0.1, (1.65, 1.0, 0.33))
    def wave(k, side): return Vector((0.12, side * 0.36, 1.32 + 0.05 * math.sin(t * 25))) if side < 0 else None
    def hips(k, side): return Vector((-0.02, side * 0.33, 0.66))
    def push(k, side): return Vector((0.42, side * 0.2, 0.9))
    def laugh(k, side): return Vector((0.16, side * 0.17, 0.66 + bob))
    for k, side in enumerate((-1, 1)):
        sh = Vector((0.02, side * 0.23, 0.95 + bob))
        hand = _arm(arms, k, side, run, t, sh, (0.3, 0.6 + bob, 0.62), (0.34, 1.4), (0.55, 0.2, 1.0), dict(wave=wave, hips=hips, push=push, laugh=laugh))
        el(Z.tee, 'BALL', sh + Vector((0, side * 0.02, -0.02)), 0.085)              # sleeve
        limb(Z.limbs, sh + (hand - sh) * 0.2, hand, 0.042, -0.03, (1, 0, 0)); el(Z.limbs, 'BALL', hand, 0.065)
    # head: big round kid head, backwards cap, ginger tuft, freckles, gap-tooth grin
    Z.head.location = (0.04, 0, 1.32 + bob); Z.head.rotation_euler = (0, -tilt, 0)
    for o in (Z.headb, Z.cap, Z.hair): o.data.elements.clear()
    el(Z.headb, 'ELLIPSOID', (0, 0, 0), 0.34, (0.98, 0.96, 1.0)); el(Z.headb, 'ELLIPSOID', (0.08, 0, -0.14), 0.26, (1.0, 1.05, 0.7))
    el(Z.headb, 'BALL', (0, 0, -0.32), 0.08)
    el(Z.cap, 'ELLIPSOID', (-0.02, 0, 0.13), 0.35, (1.02, 1.02, 0.62))
    el(Z.cap, 'ELLIPSOID', (-0.4, 0, 0.1), 0.2, (1.2, 1.05, 0.12), (0, -0.15, 0))   # brim, worn backwards
    el(Z.hair, 'ELLIPSOID', (0.27, 0.04, 0.17), 0.1, (0.8, 1.4, 0.5), (0, 0.4, 0.3))
    el(Z.hair, 'ELLIPSOID', (0.22, -0.1, 0.17), 0.08, (0.8, 1.1, 0.5), (0, 0.5, -0.4))
    for sgn in (1, -1): el(Z.hair, 'ELLIPSOID', (-0.05, sgn * 0.32, 0.0), 0.08, (1.0, 0.5, 1.0))
    _eyes(Z, mood, look, blink, 0.0, 0.25, 0.12, 0.03, 0.095, 0.17)
    P = Z.parts
    for k, sgn in enumerate((-1, 1)):
        P[f'brow{k}'].scale = (0.03, 0.075, 0.025)
        P[f'ear{k}'].location = (-0.02, sgn * 0.33, -0.04); P[f'ear{k}'].scale = (0.045, 0.05, 0.085)
    for i in range(6):
        sgn = 1 if i < 3 else -1; j = i % 3
        P[f'frk{i}'].location = (0.31, sgn * (0.13 + 0.04 * j), -0.09 - 0.025 * (j % 2)); P[f'frk{i}'].scale = (0.012, 0.014, 0.014)
    P['nose'].location = (0.36, 0, -0.05); P['nose'].scale = (0.06, 0.055, 0.05)
    P['mouth'].location = (0.32, 0, -0.17); P['mouth'].scale = (0.06, 0.12, 0.015 + 0.06 * mouth)
    P['teeth'].location = (0.36, 0, -0.145); P['teeth'].scale = (0.02, 0.07, 0.012 + 0.012 * mouth)
    P['tongue'].hide_render = True

# ------------------------------------------------------------------ Mr. Fumble (lead: lanky, awkward, silent; tweed jacket, skinny red tie)
def build_fumble():
    F = Rig('fumble')
    skin = mat('f_skin', hexc('#F1C3A0'), 0.5, 0.25, sss=0.06); jacket = mat('f_jacket', hexc('#7B5B3A'), 0.8, 0.1)
    shirt = mat('f_shirt', hexc('#F4F2EC'), 0.6, 0.15); tie = mat('f_tie', hexc('#B3202A'), 0.45, 0.3); pants = mat('f_pants', hexc('#3B3E45'), 0.7, 0.15)
    shoe = mat('f_shoe', hexc('#141214'), 0.25, 0.7); hair = mat('f_hair', hexc('#2A1E17'), 0.45, 0.35)
    F.jacket = mball('FumJacket', jacket, 0.03); F.shirt = mball('FumShirt', shirt, 0.02); F.tie = mball('FumTie', tie, 0.015)
    F.pants = mball('FumPants', pants, 0.025); F.shoes = mball('FumShoe', shoe, 0.02); F.hands = mball('FumHand', skin, 0.018)
    for o in (F.jacket, F.shirt, F.tie, F.pants, F.shoes, F.hands): o.parent = F.root
    F.headb = mball('FumHead', skin, 0.022); F.hair = mball('FumHair', hair, 0.02)
    for o in (F.headb, F.hair): o.parent = F.head
    _face(F, 'f', skin, hair, '#4E3523')
    return F

def pose_fumble(F, x=0.0, z=0.0, d=1, yaw=0.85, run=None, lean=0.0, sq=(1, 1, 1), tilt=0.0, mood='cheeky', mouth=0.2, tongue=0.0, look=(1, 0),
                arms='swing', blink=0.0, t=0.0, pop=0.0, flat=0.0, crouch=0.0, scale=1.0, tiptoe=0.0, **_):
    F.root.location = (x, 0, z); F.root.rotation_euler = (0, lean * d, -yaw if d > 0 else math.pi + yaw)
    sx, sy, sz = sq
    if flat: sx, sy, sz = lerp(sx, 0.18, flat), lerp(sy, 1.45, flat), lerp(sz, 1.12, flat)
    F.root.scale = (sx * scale, sy * scale, sz * scale)
    for o in (F.jacket, F.shirt, F.tie, F.pants, F.shoes, F.hands): o.data.elements.clear()
    bob = abs(math.sin(run)) * 0.1 if run is not None else 0.0; h = bob - 0.3 * crouch + 0.12 * tiptoe
    hunch = 0.1
    # narrow tweed jacket, shirt V, skinny tie
    el(F.jacket, 'ELLIPSOID', (0.0, 0, 1.62 + h), 0.3, (0.85, 1.05, 1.6)); el(F.jacket, 'ELLIPSOID', (0.02 + hunch * 0.5, 0, 2.02 + h), 0.3, (0.8, 1.25, 0.6))
    el(F.jacket, 'ELLIPSOID', (0.0, 0, 1.22 + h), 0.29, (0.88, 1.0, 0.7))
    el(F.shirt, 'ELLIPSOID', (0.2 + hunch * 0.5, 0, 1.98 + h), 0.12, (0.6, 0.85, 1.3), (0, 0.25, 0))
    el(F.tie, 'ELLIPSOID', (0.27 + hunch * 0.3, 0, 1.75 + h), 0.05, (0.35, 0.65, 4.0), (0, 0.18, 0))
    el(F.tie, 'BALL', (0.29 + hunch * 0.5, 0, 2.08 + h), 0.045)
    for k, side in enumerate((-1, 1)):   # long thin legs, big black shoes
        sw, lift = _walk(run, k, 0.55, 0.42)
        hip = Vector((0.0, side * 0.13, 1.08 + h)); foot = Vector((sw, side * 0.15, 0.12 + lift + 0.12 * tiptoe))
        limb(F.pants, hip, foot, 0.095, 0.1 + 0.3 * crouch, (1, 0, 0))
        el(F.shoes, 'ELLIPSOID', foot + Vector((0.12, 0, -0.05 - 0.04 * tiptoe)), 0.12, (1.9, 0.85, 0.6), (0, -0.5 * tiptoe, 0))
    def hips(k, side): return Vector((-0.05, side * 0.38, 1.35))
    def push(k, side): return Vector((0.62, side * 0.22, 1.75))
    def sneak(k, side): return Vector((0.3 + 0.1 * side, side * 0.3, 1.95 + 0.08 * side))
    def wave(k, side): return Vector((0.15, side * 0.5, 2.6 + 0.06 * math.sin(t * 25))) if side < 0 else None
    for k, side in enumerate((-1, 1)):   # thin jacket arms
        sh = Vector((0.03 + hunch * 0.5, side * 0.33, 2.08 + h))
        hand = _arm(arms, k, side, run, t, sh, (0.4, 1.28 + h, 0.75), (0.55, 2.85), (0.95, 0.25, 1.95), dict(hips=hips, push=push, sneak=sneak, wave=wave))
        limb(F.jacket, sh, hand + (sh - hand).normalized() * 0.08, 0.075, -0.05, (1, 0, 0))
        el(F.hands, 'ELLIPSOID', hand, 0.075, (1.0, 0.75, 1.2))
    # long oval face, neat side-parted hair, big nose, rubbery mouth
    F.head.location = (0.08 + hunch, 0, 2.5 + h); F.head.rotation_euler = (0, -tilt + 0.06, 0)
    F.headb.data.elements.clear(); F.hair.data.elements.clear()
    el(F.headb, 'ELLIPSOID', (0, 0, 0.0), 0.3, (0.95, 0.88, 1.28)); el(F.headb, 'ELLIPSOID', (0.06, 0, -0.2), 0.22, (1.0, 0.95, 0.9))
    el(F.headb, 'CAPSULE', (-0.03, 0, -0.42), 0.075, (0.15, 1, 1), (0, -math.pi / 2, 0))
    el(F.hair, 'ELLIPSOID', (-0.05, 0.02, 0.24), 0.27, (1.0, 0.95, 0.5)); el(F.hair, 'ELLIPSOID', (0.14, -0.08, 0.27), 0.15, (0.9, 1.3, 0.35), (0.25, 0.25, 0))
    for sgn in (1, -1): el(F.hair, 'ELLIPSOID', (-0.1, sgn * 0.24, 0.08), 0.1, (1.2, 0.5, 1.2))
    el(F.hair, 'ELLIPSOID', (-0.22, 0, 0.08), 0.2, (0.6, 1.0, 1.1))
    _eyes(F, mood, look, blink, pop, 0.24, 0.11, 0.08, 0.085, 0.15)
    P = F.parts
    for k, sgn in enumerate((-1, 1)):
        P[f'brow{k}'].scale = (0.025, 0.08, 0.02)
        P[f'ear{k}'].location = (-0.02, sgn * 0.27, 0.0); P[f'ear{k}'].scale = (0.04, 0.05, 0.09)
    P['nose'].location = (0.32, 0, -0.06); P['nose'].scale = (0.07, 0.055, 0.1)
    w = 0.13 if mood in ('smug', 'cheeky', 'happy') else 0.09
    P['mouth'].location = (0.29, 0, -0.24); P['mouth'].scale = (0.05, w, 0.012 + 0.07 * mouth)
    P['teeth'].location = (0.32, 0, -0.215); P['teeth'].scale = (0.02, w * 0.65, 0.01 + 0.015 * mouth); P['teeth'].hide_render = mouth < 0.25
    P['tongue'].location = (0.33, 0.02, -0.27 - 0.1 * tongue); P['tongue'].scale = (0.04, 0.05, 0.02 + 0.08 * tongue); P['tongue'].hide_render = tongue < 0.05
