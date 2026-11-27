"""Kinda Wild Films ep12 - 'Where Does Fat Go When You Lose Weight?'  Brief: kindawild/12_fat/brief.md (+ lead GO 27 Nov).
Facts: Meerman & Brown, BMJ 2014;349:g7257 + UNSW Newsroom. Ben (HumGen) on the clinic bed; hard cuts between a medium shot,
a mouth close, a belly cut-away block (yellow fat cells, a separate mini stage) and the clinic screen (bar card).
"""
import sys, os, math; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kwkit as KW
os.environ.setdefault('KW_LIGHT', '1')
HERE = os.path.dirname(os.path.abspath(__file__))
ep = KW.Episode('ep_fatloss', injury="loses ten kilos of fat",
                voice_lines=[l.strip() for l in open(os.path.join(HERE, 'ep_fatloss.txt')) if l.strip()],
                music='sneaky_snitch', gap=0.5)
ben = ep.person('Ben', 'civilian', 'eatmore-ben', gender='m', age='young', race='caucasian', hair='short02', tee='teal')

ep.waive = {"1 shots;": "brief s6: one kit shot; the hard cuts (medium -> block -> mouth ...) live in ep.cam_fn",
            "last shot must use cam=KW.cam.loop()": "brief s6: cam_fn cuts back to the frame-0 framing for the last 9 frames (the loop)",
            "HOOK cut <= 200 ms after the last word": "brief s6: CTA over the payoff shot, then the frame-0 cut",
            "HOOK 8-11 words": "brief s3: script approved by the lead (GO 27 Nov), line 1 wording from the lead",
            "shot fat holds": "brief s6: cuts every 1.1-5 s inside cam_fn",
            "HOOK inside the body": "brief s5: the belly block is a cut-away at 1.1 s, the person opens"}
FPS = 24; F = 1.0 / FPS
try: from mathutils import Vector as V, Matrix
except ImportError: V = Matrix = None
fw = lambda i, w: int(round(ep.word(i, w) * FPS))
fl = lambda i: int(round(ep.line(i) * FPS))
fle = lambda i: int(round((ep.line(i) + ep.vo_dur[i]) * FPS))
f_last = fle(6); FN = max(f_last + 26, 720); NF = FN + 1; ep.duration = round(NF / FPS, 4)
CTA0 = FN - 40
f_carbon, f_water1 = fw(1, 'carbon'), fw(1, 'water.')
f_twenty, f_33, f_one4, f_water4, f_sweat, f_tears = fw(2, 'twenty-nine'), fw(3, 'thirty-three'), fw(4, 'one'), fw(4, 'water,'), fw(4, 'sweat,'), fw(4, 'tears.')
f_L5, f_energy, f_L6, f_breath = fl(5), fw(5, 'energy'), fl(6), fw(6, 'breath.')
# ---- cuts: (first frame, shot) -------------------------------------------------------------------------------------------
CUTS = [(0, 'MED'), (26, 'BLOCK'), (55, 'MOUTH'), (fl(1) - 6, 'BLOCK2'), (fl(2) - 4, 'MED2'), (fl(3) - 6, 'MOUTH2'), (f_33 + 17, 'LOW'),
        (fl(4), 'FACE'), (f_L5 - 2, 'SCR'), (f_L5 + 123, 'MED3'), (FN - 9, 'MED')]
def shot_of(f):
    cur = CUTS[0]
    for c in CUTS:
        if f >= c[0]: cur = c
    nxt = next((c[0] for c in CUTS if c[0] > cur[0]), FN + 1)
    return cur[1], (f - cur[0]) / max(1, nxt - cur[0])
EXH = [(-24, 22), (60, 108), (fl(3) - 2, f_33 + 14), (f_L6 - 4, f_breath + 6), (FN - 24, FN + 22)]     # breath-out windows (mouth open)
INH = [(fl(2) + 14, fl(2) + 58)]                                                                       # O2 flows in (nose)
BL0 = float(os.environ.get('KW_BL0', 1.2))
def belly(f):
    if f >= FN - 9: return 0.0 if os.environ.get('KW_BLT') else BL0
    return keys(f, [(0, BL0), (fl(2) + 20, BL0), (fl(2) + 76, BL0 * 0.62), (f_33 + 20, BL0 * 0.62), (f_33 + 58, 0.0)])

def ease(x): x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)
def keys(f, ks):
    if f <= ks[0][0]: return ks[0][1]
    for (f0, v0), (f1, v1) in zip(ks, ks[1:]):
        if f0 <= f <= f1: return v0 + (v1 - v0) * ease((f - f0) / max(1e-6, f1 - f0))
    return ks[-1][1]
def win(f, ws, e=6):
    return max([ease((f - a) / e) * (1 - ease((f - b) / e)) for a, b in ws] + [0.0])

P = KW.pose('sit', at='bed_sit', left=os.environ.get('KW_HAND', 'rest'), right=os.environ.get('KW_HAND', 'rest'), face='calm', blend=5 * F)
ep.blinks = {'Ben': [44, 150, 236, 330, 420, 560, 680]}
R = {}
BLK = (40.0, 40.0, 1.0)              # the belly cut-away block: its own mini stage far from the clinic

def eyeball(rt, s='L'):
    rg = rt.actors[ben].p.hg.rig; return rg.matrix_world @ rg.pose.bones[f'eyeball.{s}'].head
def mouth(rt):
    hg = rt.actors[ben].p.hg; Hm = rt.wmat(hg.p, 'head'); Lp = Hm @ hg.lip_local
    try: _, nr = rt.part_world(rt.actors[ben], 'mouth')
    except Exception: nr = Hm.to_3x3() @ V((0, -1, 0))
    return Lp, V(nr).normalized()
def bellypt(rt):
    pt, nr = rt.part_world(rt.actors[ben], 'belly'); return pt, nr

# ---- molecules: matte ball models (C black, O red, H white) -----------------------------------------------------------------
NPOOL = {'CO2': 44, 'H2O': 22, 'O2': 26}
def build_molecules(c):
    import bpy, kwlib as L
    mt = {'C': L.mat('kw12_C', (0.035, 0.035, 0.038), 0.55, 0.0), 'O': L.mat('kw12_O', (0.40, 0.025, 0.02), 0.62, 0.0),
          'H': L.mat('kw12_H', (0.80, 0.80, 0.78), 0.62, 0.0)}
    bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=12, radius=1.0); sp = bpy.context.active_object
    bpy.ops.object.shade_smooth(); sm = sp.data; bpy.data.objects.remove(sp)
    meshes = {}
    for k in mt:
        m = sm.copy(); m.name = 'kw12_atom_' + k; m.materials.append(mt[k]); meshes[k] = m
    a104 = math.radians(104.45) / 2
    SPEC = {'CO2': [('C', (0, 0, 0), 1.0), ('O', (-1.3, 0, 0), 0.9), ('O', (1.3, 0, 0), 0.9)],
            'H2O': [('O', (0, 0, 0), 1.0), ('H', (math.sin(a104) * 1.0, 0, -math.cos(a104) * 1.0), 0.6), ('H', (-math.sin(a104) * 1.0, 0, -math.cos(a104) * 1.0), 0.6)],
            'O2': [('O', (-0.62, 0, 0), 0.9), ('O', (0.62, 0, 0), 0.9)]}
    pool = {}
    for kind, n in NPOOL.items():
        pool[kind] = []
        for i in range(n):
            e = bpy.data.objects.new(f'kw12_{kind}_{i}', None); c.objects.link(e)
            for el, p_, r_ in SPEC[kind]:
                o = bpy.data.objects.new(f'kw12_{kind}_{i}_{el}', meshes[el]); c.objects.link(o); o.parent = e
                o.location = p_; o.scale = (r_, r_, r_)
                for a in ('visible_shadow',): setattr(o, a, False)
            pool[kind].append(e)
    R['pool'] = pool

def hsh(i, k=0):
    x = math.sin(i * 12.9898 + k * 78.233) * 43758.5453; return x - math.floor(x)

def mol_particles(rt, f, shot):
    """list of (kind, position, rotation euler, scale) for this frame"""
    out = []
    if shot in ('MED', 'MED2', 'MED3', 'MOUTH', 'MOUTH2', 'LOW'):
        Lp, nr = mouth(rt); dn = (nr + V((0, 0, -0.35))).normalized()
        u = {'MOUTH': 0.0021, 'MOUTH2': 0.0021}.get(shot, 0.0050)
        sp_ = 0.0032 if 'MOUTH' in shot else 0.0062; life = 40 if 'MOUTH' not in shot else 34
        for a, b in EXH:
            for j in range(int((b - a) / 2)):
                fb = a + j * 2 + (FN if False else 0); age = f - fb
                if not (0 <= age < life): continue
                idx = j + a * 7
                kind = 'H2O' if j % 4 == 3 else 'CO2'
                side = V((hsh(idx, 1) - 0.5, hsh(idx, 2) - 0.5, hsh(idx, 3) - 0.5)) * 0.9
                d_ = (dn + side * 0.55).normalized()
                pos = Lp + nr * 0.006 + d_ * (sp_ * age * (1 - 0.25 * age / life)) + V((0, 0, 1)) * (u * 0.4 * (age / life) ** 2 * 6)
                sc = u * ease(age / 4) * (1 - ease((age - life + 8) / 8))
                rot = (hsh(idx, 4) * 6.28 + age * 0.06, hsh(idx, 5) * 6.28 + age * 0.04, hsh(idx, 6) * 6.28)
                out.append((kind, pos, rot, sc))
        for a, b in INH:
            Mh = rt.wmat(rt.actors[ben].p, 'head'); nose = Mh @ rt.actors[ben].parts['nose'][1]
            for j in range(int((b - a) / 1.5)):
                fb = a + j * 1.5 - 20; age = f - fb; life = 28
                if not (0 <= age < life): continue
                idx = j + 911
                side = V((hsh(idx, 1) - 0.5, hsh(idx, 2) * 0.3, hsh(idx, 3) - 0.5))
                st = nose + V((0, -0.32, -0.08)) + V((side.x * 0.32, side.y * 0.2, side.z * 0.26))
                x = age / life; pos = st.lerp(nose + V((0, -0.008, -0.004)), x ** 1.3)
                sc = u * 0.95 * ease(age / 4) * (1 - ease((x - 0.8) / 0.2))
                out.append(('O2', pos, (hsh(idx, 4) * 6.28, hsh(idx, 5) * 6.28 + age * 0.05, 0), sc))
    if shot in ('BLOCK', 'BLOCK2'):
        hc = R['hero_c']; r0 = R['hero_r'] * R['hero'].scale[0]
        ws = [(20, 60)] if shot == 'BLOCK' else [(fl(1) + 4, fl(2) - 4)]
        for a, b in ws:
            for j in range(int((b - a) / 2.2)):
                fb = a + j * 2.2; age = f - fb; life = 46
                if not (0 <= age < life): continue
                idx = j + a * 3
                kind = 'H2O' if j % 5 in (2,) else 'CO2'
                if shot == 'BLOCK2' and j < 2: kind = ('CO2', 'H2O')[j]
                ang = hsh(idx, 1) * 6.28; up = V((math.cos(ang) * 0.5, -0.6 - 0.3 * hsh(idx, 2), 0.55 + 0.4 * hsh(idx, 3))).normalized()
                pos = hc + up * (r0 * 0.7 + 0.0022 * age) + V((0, 0, 1)) * 0.00002 * age * age
                sc = 0.0036 * ease(age / 5) * (1 - ease((age - life + 8) / 8))
                out.append((kind, pos, (hsh(idx, 4) * 6.28 + age * 0.05, hsh(idx, 5) * 6.28, age * 0.03), sc))
    return out

def place_molecules(rt, f, shot):
    pool = R['pool']; used = {k: 0 for k in pool}
    for kind, pos, rot, sc in mol_particles(rt, f, shot):
        if sc <= 1e-5 or used[kind] >= len(pool[kind]): continue
        e = pool[kind][used[kind]]; used[kind] += 1
        e.location = pos; e.rotation_euler = rot; e.scale = (sc, sc, sc)
        for ch in e.children: ch.hide_render = False
    for k, lst in pool.items():
        for e in lst[used[k]:]:
            e.scale = (1e-4,) * 3
            for ch in e.children: ch.hide_render = True

# ---- the belly cut-away block (skin / dermis / yellow fat cells / muscle), stylised cells ------------------------------------
def build_block(c):
    import bpy, kwlib as L, random
    rnd = random.Random(12)
    bx, by, bz = BLK
    skin = L.mat('kw12_skin', (0.62, 0.38, 0.28), 0.5, 0.0); derm = L.mat('kw12_derm', (0.72, 0.42, 0.38), 0.6, 0.0)
    musc = L.mat('kw12_musc', (0.36, 0.06, 0.05), 0.6, 0.0); fill = L.mat('kw12_fill', (0.62, 0.36, 0.20), 0.6, 0.0)
    fat = bpy.data.materials.new('kw12_fat'); fat.use_nodes = True; b = fat.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (0.92, 0.62, 0.10, 1); b.inputs['Roughness'].default_value = 0.38
    if 'Subsurface Weight' in b.inputs: b.inputs['Subsurface Weight'].default_value = 0.35; b.inputs['Subsurface Radius'].default_value = (0.004, 0.003, 0.0012)
    W_, D_ = 0.20, 0.12
    L.box('kw12_skin', (W_, D_, 0.010), (bx, by, bz + 0.085), skin, c, 0.002)
    L.box('kw12_derm', (W_, D_, 0.012), (bx, by, bz + 0.074), derm, c, 0.001)
    L.box('kw12_fill', (W_ - 0.004, D_ - 0.004, 0.064), (bx, by, bz + 0.036), fill, c, 0.0)
    L.box('kw12_musc', (W_, D_, 0.030), (bx, by, bz - 0.011), musc, c, 0.002)
    bpy.ops.mesh.primitive_uv_sphere_add(segments=20, ring_count=12, radius=1.0); sp = bpy.context.active_object
    bpy.ops.object.shade_smooth(); me = sp.data; me.materials.append(fat); bpy.data.objects.remove(sp)
    s_ = 0.0185; r_ = 0.0102
    for ix in range(11):
        for iy in range(7):
            for iz in range(4):
                x = bx - W_ / 2 + 0.006 + ix * s_ + (iz % 2) * s_ * 0.5 + (rnd.random() - 0.5) * 0.003
                y = by - D_ / 2 + 0.008 + iy * s_ + (rnd.random() - 0.5) * 0.003
                z = bz + 0.011 + iz * 0.0165 + (rnd.random() - 0.5) * 0.002
                if x > bx + W_ / 2 - 0.004: continue
                if abs(x - bx) < 0.022 and iy == 0 and iz in (1, 2): continue        # room for the hero cell
                o = bpy.data.objects.new('kw12_cell', me); c.objects.link(o); o.location = (x, y, z)
                k = r_ * (0.95 + 0.12 * rnd.random()); o.scale = (k * (1 + 0.1 * rnd.random()), k, k * (0.85 + 0.1 * rnd.random()))
    hero = bpy.data.objects.new('kw12_hero', me); c.objects.link(hero); R['hero_r'] = 0.0165
    R['hero_c'] = V((bx, by - D_ / 2 + 0.010, bz + 0.036)); hero.location = R['hero_c']; hero.scale = (R['hero_r'],) * 3; R['hero'] = hero
    # backdrop + light
    bd = L.mat('kw12_back', (0.07, 0.11, 0.14), 0.9, 0.0)
    bpy.ops.mesh.primitive_plane_add(size=6.0); pl = bpy.context.active_object; pl.name = 'kw12_backdrop'
    for u_ in list(pl.users_collection): u_.objects.unlink(pl)
    c.objects.link(pl); pl.location = (bx, by + 0.7, bz); pl.rotation_euler = (math.radians(80), 0, 0); pl.data.materials.append(bd)
    bpy.ops.mesh.primitive_plane_add(size=6.0); fl_ = bpy.context.active_object; fl_.name = 'kw12_floor'
    for u_ in list(fl_.users_collection): u_.objects.unlink(fl_)
    c.objects.link(fl_); fl_.location = (bx, by, bz - 0.027); fl_.data.materials.append(bd)
    for nm, loc, en, sz in (('kw12_key', (bx + 0.35, by - 0.45, bz + 0.55), 14.0, 0.4), ('kw12_fillL', (bx - 0.5, by - 0.3, bz + 0.25), 3.5, 0.6)):
        ld = bpy.data.lights.new(nm, 'AREA'); ld.energy = en; ld.size = sz; ld.color = (1.0, 0.96, 0.9)
        lo = bpy.data.objects.new(nm, ld); c.objects.link(lo); lo.location = loc
        lo.rotation_euler = (V((bx, by, bz + 0.04)) - V(loc)).to_track_quat('-Z', 'Y').to_euler()

# ---- sweat bead + tear: water drops that slide on the skin (ray cast onto the posed body) -----------------------------------
def build_drops(c):
    import bpy
    w = bpy.data.materials.new('kw12_water'); w.use_nodes = True; b = w.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (0.92, 0.95, 1.0, 1); b.inputs['Roughness'].default_value = 0.02; b.inputs['IOR'].default_value = 1.33
    b.inputs['Transmission Weight' if 'Transmission Weight' in b.inputs else 'Transmission'].default_value = 1.0
    if 'Coat Weight' in b.inputs: b.inputs['Coat Weight'].default_value = 1.0; b.inputs['Coat Roughness'].default_value = 0.0
    if 'Specular IOR Level' in b.inputs: b.inputs['Specular IOR Level'].default_value = 1.0
    for nm in ('kw12_sweat', 'kw12_tear'):
        bpy.ops.mesh.primitive_uv_sphere_add(segments=24, ring_count=14, radius=1.0); o = bpy.context.active_object; o.name = nm
        bpy.ops.object.shade_smooth()
        for u_ in list(o.users_collection): u_.objects.unlink(o)
        c.objects.link(o); o.data.materials.append(w); o.hide_render = True; R[nm] = o
        o.visible_shadow = False

def on_skin(rt, p_, d_=None):
    import bpy
    dg = bpy.context.evaluated_depsgraph_get(); d_ = d_ or V((0, 1, 0))
    for o_ in R['pool_objs_hide']: pass
    hit, loc, nrm, *_ = bpy.context.scene.ray_cast(dg, p_ - d_ * 0.12, d_)
    return (loc, nrm) if hit else (p_, -d_)

def place_drops(rt, f, shot):
    sw, tr = R['kw12_sweat'], R['kw12_tear']
    sw.hide_render = tr.hide_render = True
    if shot != 'FACE': return
    EL, ER = eyeball(rt, 'L'), eyeball(rt, 'R'); Em = (EL + ER) / 2
    a0 = f_sweat - 14
    if f >= a0:
        x = ease((f - a0) / 50.0); p_ = Em + V((-0.016, 0, 0.040 - 0.016 * x))
        loc, n_ = on_skin(rt, p_); g = ease((f - a0) / 6)
        sw.location = loc + n_ * 0.0012 * g; sw.scale = (0.0042 * g, 0.0042 * g, 0.0054 * g); sw.hide_render = g < 0.02
    a1 = f_tears - 14
    if f >= a1:
        x = ease((f - a1) / 40.0); p_ = EL + V((-0.008, 0, -0.013 - 0.022 * x))
        loc, n_ = on_skin(rt, p_); g = ease((f - a1) / 6)
        tr.location = loc + n_ * 0.0010 * g; tr.scale = (0.0034 * g, 0.0034 * g, 0.0044 * g); tr.hide_render = g < 0.02

# ---- clinic screen (bar card) --------------------------------------------------------------------------------------------
SCR_C = (-0.10, 0.17, 2.05); SCR_W, SCR_H = 0.46, 0.2875
def build_screen(c):
    import bpy, kwlib as L
    tex = os.path.join(HERE, '..', '..', 'assets', 'real', 'tex', 'kw_fat')
    m = bpy.data.materials.new('kw12_screen'); m.use_nodes = True; nt = m.node_tree; N = nt.nodes; N.clear(); Lk = nt.links.new
    out = N.new('ShaderNodeOutputMaterial'); em = N.new('ShaderNodeEmission'); uv = N.new('ShaderNodeTexCoord')
    def img(nm):
        n = N.new('ShaderNodeTexImage'); n.image = bpy.data.images.load(os.path.join(tex, nm + '.png'), check_existing=True)
        n.interpolation = 'Cubic'; Lk(uv.outputs['UV'], n.inputs['Vector']); return n
    i0, iA, iB = img('card0'), img('cardA'), img('cardB')
    su = N.new('ShaderNodeSeparateXYZ'); Lk(uv.outputs['UV'], su.inputs[0])
    rev = N.new('ShaderNodeValue'); rev.name = 'kw12_rev'; my = N.new('ShaderNodeValue'); my.name = 'kw12_myth'
    lt = N.new('ShaderNodeMath'); lt.operation = 'LESS_THAN'; Lk(su.outputs['X'], lt.inputs[0]); Lk(rev.outputs[0], lt.inputs[1])
    m1 = N.new('ShaderNodeMix'); m1.data_type = 'RGBA'; Lk(lt.outputs[0], m1.inputs['Factor']); Lk(i0.outputs['Color'], m1.inputs['A']); Lk(iA.outputs['Color'], m1.inputs['B'])
    m2 = N.new('ShaderNodeMix'); m2.data_type = 'RGBA'; Lk(my.outputs[0], m2.inputs['Factor']); Lk(m1.outputs['Result'], m2.inputs['A']); Lk(iB.outputs['Color'], m2.inputs['B'])
    Lk(m2.outputs['Result'], em.inputs['Color']); em.inputs['Strength'].default_value = float(os.environ.get('KW_SCRE', 1.4)); Lk(em.outputs[0], out.inputs[0])
    R['scr'] = (rev, my)
    cx, cy, cz = SCR_C; tilt = math.radians(-8)
    dark = L.mat('kw12_bezel', (0.035, 0.038, 0.042), 0.35, 0.2); steel = L.mat('kw12_steel', (0.72, 0.73, 0.75), 0.3, 1.0)
    L.box('kw12_bezel', (SCR_W + 0.024, 0.03, SCR_H + 0.024), (cx, cy + 0.016, cz), dark, c, 0.008, (math.degrees(tilt), 0, 0))
    bpy.ops.mesh.primitive_plane_add(size=1.0); pl = bpy.context.active_object; pl.name = 'kw12_panel'
    for u_ in list(pl.users_collection): u_.objects.unlink(pl)
    c.objects.link(pl); pl.scale = (SCR_W, SCR_H, 1); pl.rotation_euler = (math.radians(90) + tilt, 0, 0); pl.location = (cx, cy - 0.0005, cz)
    pl.data.materials.append(m)
    for a in ('visible_diffuse', 'visible_glossy', 'visible_transmission'): setattr(pl, a, a == 'visible_glossy')
    L.cyl('kw12_boom', 0.016, 2.80 - cz, (cx, cy + 0.06, (2.80 + cz) / 2), steel, c, (0, 0, 0), 20)
    L.box('kw12_mount', (0.12, 0.04, 0.08), (cx, cy + 0.045, cz), dark, c, 0.005)

# ---- ladder rung 2: teeth not uniformly white (per-tooth value / warmth variation), less shine ------------------------------
def teeth_rung2():
    import bpy
    done = set()
    for o in bpy.data.objects:
        if o.type != 'MESH' or not o.name.startswith('HG_Teeth'): continue
        for m in o.data.materials:
            if m is None or m.name in done or not m.use_nodes: continue
            done.add(m.name); nt = m.node_tree; b = next((n for n in nt.nodes if n.bl_idname == 'ShaderNodeBsdfPrincipled'), None)
            if b is None: continue
            bc = b.inputs['Base Color']
            tc = nt.nodes.new('ShaderNodeTexCoord'); nz = nt.nodes.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = float(os.environ.get('KW_TNZ', 160.0))
            nz.inputs['Detail'].default_value = 1.0; nt.links.new(tc.outputs['Object'], nz.inputs['Vector'])
            ramp = nt.nodes.new('ShaderNodeValToRGB'); ramp.color_ramp.elements[0].color = (0.90, 0.87, 0.80, 1); ramp.color_ramp.elements[1].color = (1.0, 1.0, 0.98, 1)
            ramp.color_ramp.elements[0].position = 0.35; ramp.color_ramp.elements[1].position = 0.65
            nt.links.new(nz.outputs['Fac'], ramp.inputs['Fac'])
            mx = nt.nodes.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'; mx.inputs['Factor'].default_value = 1.0
            if bc.links: src = bc.links[0].from_socket; nt.links.remove(bc.links[0]); nt.links.new(src, mx.inputs[6])
            else: mx.inputs[6].default_value = bc.default_value[:]
            nt.links.new(ramp.outputs['Color'], mx.inputs[7]); nt.links.new(mx.outputs[2], bc)
            rg = b.inputs['Roughness']
            if not rg.links: rg.default_value = max(rg.default_value, 0.38)
            print('ep12 rung2: teeth variation on', m.name, flush=True)

def build(rt):
    import bpy
    c = bpy.data.collections.get('kw_ep12') or bpy.data.collections.new('kw_ep12')
    if c.name not in bpy.context.scene.collection.children: bpy.context.scene.collection.children.link(c)
    import kwlook as Q_; Q_.LOOP_T = FN / FPS
    build_molecules(c); build_block(c); build_drops(c); build_screen(c); teeth_rung2()
    R['pool_objs_hide'] = []
ep.build_hook = build

def set_key(hg, name, v, objs=None):
    for o in hg.meshes:
        if objs and not any(s in o.name for s in objs): continue
        kb = o.data.shape_keys.key_blocks if o.data.shape_keys else None
        k = kb.get(name) if kb else None
        if k is not None:
            if k.slider_max < v: k.slider_max = v
            k.value = v

def frame_hook(rt, t):
    import bpy, kwlook as Q_
    Q_.LOOP_T = FN / FPS
    f = t * FPS; ra = rt.actors[ben]; hg = ra.p.hg
    shot, u = shot_of(f)
    EL, ER = eyeball(rt, 'L'), eyeball(rt, 'R'); Em = (EL + ER) / 2
    if shot == 'SCR': tgt = Em + V((0.05, -0.60, 0.03))
    else: tgt = Em + V((0.10, -0.60, 0.015))
    rt.eyes_at(ra, tgt)
    # belly (neutral weight-loss read from the silhouette; the tee keeps some of its volume -> hangs looser)
    bv = belly(f)
    for o in hg.meshes:
        kb = o.data.shape_keys.key_blocks if o.data.shape_keys else None
        k = kb.get('kw_bloat') if kb else None
        if k is None: continue
        tee = 'SHIRT' in o.name.upper()
        k.value = (0.25 + 0.75 * bv) if tee else bv
    # breath out: lips parted and rounded; breath in: nose (mouth closed), shoulders lift a touch
    ex = win(f, EXH, 6)
    if ex > 0:
        for k_, v_ in (('jawOpen', 0.16), ('mouthFunnel', 0.42), ('mouthPucker', 0.12), ('mouthLowerDown_L', 0.18), ('mouthLowerDown_R', 0.18)):
            set_key(hg, k_, v_ * ex)
    inh = win(f, INH, 10)
    rg = hg.rig
    for s_ in ('L', 'R'):
        pb = rg.pose.bones.get(f'shoulder.{s_}')
        if pb is not None:
            pb.rotation_mode = 'XYZ'; pb.rotation_euler = (0, 0, math.radians(float(os.environ.get('KW_SHR', 3.0))) * inh * (1 if s_ == 'L' else -1))
    # screen
    rev, my = R['scr']
    rev.outputs[0].default_value = 1.0 if f >= f_L5 + 40 else (0.0 if f < f_L5 + 8 else 0.08 + 0.92 * ease((f - f_L5 - 8) / 32))
    my.outputs[0].default_value = ease((f - f_energy) / 6)
    if f >= FN - 9: rev.outputs[0].default_value = 0.0; my.outputs[0].default_value = 0.0      # loop: the screen as on frame 0
    # hero fat cell shrinks
    h = R['hero']; s = keys(f, [(0, 1.0), (26, 1.0), (55, 0.82), (fl(1), 0.82), (fl(2) - 6, 0.42)]) * R['hero_r']; h.scale = (s, s, s)
    bpy.context.view_layer.update()
    place_molecules(rt, f, shot); place_drops(rt, f, shot)
    if not R.get('refit'):
        R['refit'] = 1
        for it_ in rt.FX.items.values():
            if it_: it_.pop('fit', None)
    bpy.context.view_layer.update(); sh_ = rt.ep.shot_at(t); rt.FX.update(sh_, t - sh_.t, t)
ep.frame_hook = frame_hook

# ---- camera (hard cuts) -----------------------------------------------------------------------------------------------------
def look(tg, dirv, dist, lens, fst=8.0, foc=None):
    dv = V(dirv).normalized(); pos = tg + dv * dist
    return pos, tg, V((0, 0, 1)), lens, fst, (foc if foc is not None else tg)
def cam_fn(rt, t):
    import bpy
    f = t * FPS; bpy.context.view_layer.update(); shot, u = shot_of(f)
    EL, ER = eyeball(rt, 'L'), eyeball(rt, 'R'); Em = (EL + ER) / 2; Lp, nr = mouth(rt); bp, bn = bellypt(rt)
    push = lambda a, b: a * (b / a) ** ease(u)
    if shot in ('MED', 'MED2', 'MED3'):
        tg = Em.lerp(bp, float(os.environ.get('KW_MEDL', 0.32)))
        d0 = {'MED': 1.60, 'MED2': 1.60, 'MED3': 1.50}[shot]
        d = d0 if (shot == 'MED' and (f < 26 or f >= FN - 9)) else push(d0, d0 * 0.93)
        return look(tg, (float(os.environ.get('KW_MEDX', 2.5)), -1.0, 0.06), d, 50.0, 8.0, Em)
    if shot in ('MOUTH', 'MOUTH2'):
        tg = Lp + nr * 0.03 + V((0, 0, -0.008))
        return look(tg, (0.75, -1.0, 0.08), push(0.40, 0.36), 85.0, 11.0, Lp)
    if shot in ('BLOCK', 'BLOCK2'):
        tg = V(BLK) + V((float(os.environ.get('KW_BLKX', 0.035)), -0.02, 0.035))
        return look(tg, (0.50, -1.0, 0.62), push(0.50, 0.45) if shot == 'BLOCK' else push(0.40, 0.30), 50.0, 11.0, R['hero_c'])
    if shot == 'LOW':
        tg = Em.lerp(bp, 0.45)
        return look(tg, (float(os.environ.get('KW_MEDX', 2.5)), -1.0, 0.05), push(1.45, 1.36), 50.0, 8.0, bp)
    if shot == 'FACE':
        tg = Em + V((0.0, 0.0, -0.005))
        return look(tg, (0.12, -1.0, 0.02), push(0.48, 0.42), 85.0, 11.0, Em)
    if shot == 'SCR':
        tg = V(SCR_C) + V((0, 0, -0.06))
        r_ = look(tg, (0.06, -1.0, 0.25), push(1.30, 1.20), 50.0, 8.0, V(SCR_C)); R['campos'] = r_[0]; return r_
ep.cam_fn = cam_fn

# ---- labels + sounds ------------------------------------------------------------------------------------------------------
YL = dict(color='yellow', size=1.2); Y = 0.89; YB = 0.17
ep.label_outline = True; ep.label_maxw = 820.0; ep.label_lens_fix = True
labels = [KW.fx.label('8.4 KG', at=-1.0, pos=(0.5, Y), dur=1.0 + 25 * F, **YL),
          KW.fx.label('CO2', at=f_carbon * F, pos=(0.36, 0.70), dur=(f_water1 - 4 - f_carbon) * F, color='white', size=0.75),
          KW.fx.label('H2O', at=f_water1 * F, pos=(0.64, 0.70), dur=(fl(2) - 6 - f_water1) * F, color='white', size=0.75),
          KW.fx.label('29 KG O2', at=f_twenty * F, pos=(0.5, Y), dur=(fl(3) - 10 - f_twenty) * F, **YL),
          KW.fx.counter(0, 33, 'MG', at=(f_33 - 3) * F, dur=0.8, pos=(0.5, YB), size=1.0, color='yellow'),
          KW.fx.label('10 KG GONE', at=(f_33 + 40) * F, pos=(0.5, Y), dur=(fl(4) - 4 - f_33 - 40) * F, **YL),
          KW.fx.label('1.6 KG', at=f_one4 * F, pos=(0.5, YB), dur=(f_water4 - 2 - f_one4) * F, **YL),
          KW.fx.label('WATER', at=f_water4 * F, pos=(0.5, YB), dur=(f_L5 - 6 - f_water4) * F, **YL),
          KW.fx.label('MYTH', at=f_energy * F, pos=(0.5, Y), dur=(f_L5 + 120 - f_energy) * F, color='red', size=1.2),
          KW.fx.label('EXHALED', at=(f_breath - 6) * F, pos=(0.5, Y), dur=(CTA0 - 2 - f_breath + 6) * F, **YL),
          KW.fx.label('WHAT DID YOU THINK?', at=CTA0 * F, pos=(0.5, 0.62), dur=(FN - 10 - CTA0) * F, **YL),
          KW.fx.label('COMMENT BELOW', at=(CTA0 + 3) * F, pos=(0.5, 0.575), dur=(FN - 13 - CTA0) * F, color='white', size=0.125),
          KW.fx.label('8.4 KG', at=(FN - 9) * F, pos=(0.5, Y), dur=2.0, **YL)]
labels[-1].o['nopop'] = True
labels[4].o['end'] = (f_33 + 16) * F
ep.sound(0.0, 'thud', 0.6)
for f_ in (26, 55, f_twenty, f_33 + 40, f_energy): ep.sound(f_ * F, 'thud', 0.45)
ep.mouth_fix = True; ep.eyes_fix = True; ep.relight_after_pose = True
ep.shot(0.0, 'fat', set='hospital', cast={ben: P}, fx=labels, cam=KW.cam.face(ben))
ep.run()
