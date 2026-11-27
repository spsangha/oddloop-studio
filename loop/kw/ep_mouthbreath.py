"""Kinda Wild Films ep13 - 'He Breathed Through His Mouth For Years'  Brief: kindawild/13_mouth/brief.md.
Facts: Harari et al. Laryngoscope 2010; Zhao et al. BMC Oral Health 2021.  Adult Ben (HumGen) on the clinic bed; his lower face
lengthens (shape key kw13_long: jaw rotates down/back, lower face taller), hard cuts between profile, face, mouth and the screen.
"""
import sys, os, math; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kwkit as KW
os.environ.setdefault('KW_LIGHT', '1')
HERE = os.path.dirname(os.path.abspath(__file__))
ep = KW.Episode('ep_mouthbreath', injury="through his mouth",
                voice_lines=[l.strip() for l in open(os.path.join(HERE, 'ep_mouthbreath.txt')) if l.strip()],
                music='sneaky_snitch', gap=0.7)
ben = ep.person('Ben', 'civilian', 'eatmore-ben', gender='m', age='young', race='caucasian', hair='short02', tee='teal')


FPS = 24; F = 1.0 / FPS
try: from mathutils import Vector as V, Matrix
except ImportError: V = Matrix = None
def ease(x): x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)
def sstep(a, b, x): return ease((x - a) / (b - a)) if b != a else float(x >= a)
R = {}
TH = float(os.environ.get('KW13_TH', 8.0)); ST = float(os.environ.get('KW13_ST', 0.008)); TIP = float(os.environ.get('KW13_TIP', 10.0))

def long_keys(hg):
    """kw13_long: lower jaw rotates down and back about the jaw joint (TH deg), mid face (nose base -> mouth) stretches ST m;
    kw13_tip: upper front teeth tip forward TIP deg.  Built on the rest shapes in world space (Ben faces -Y, up +Z)."""
    import numpy as np
    rig = hg.rig; RW = rig.matrix_world
    E = (RW @ rig.data.bones['eyeball.L'].head_local + RW @ rig.data.bones['eyeball.R'].head_local) / 2
    piv = E + V((0, float(os.environ.get('KW13_PY', 0.080)), float(os.environ.get('KW13_PZ', -0.050))))
    zn, zm = E.z - 0.030, E.z - 0.072             # nose base / mouth line (world z)
    th = math.radians(TH); c_, s_ = math.cos(th), math.sin(th)
    out = {}
    for o in hg.meshes:
        nm = o.name
        if not (nm.startswith('HG_Body') or nm.startswith('HG_Teeth')): continue
        if o.data.shape_keys is None: o.shape_key_add(name='Basis', from_mix=False)
        kb = o.data.shape_keys.key_blocks; n = len(o.data.vertices)
        co = np.empty(n * 3); kb[0].data.foreach_get('co', co); co = co.reshape(-1, 3)
        W = np.array(o.matrix_world); cw = co @ W[:3, :3].T + W[:3, 3]; Wi = np.linalg.inv(W[:3, :3])
        x, y, z = cw[:, 0] - E.x, cw[:, 1], cw[:, 2]
        lower = 'Lower' in nm or 'lower' in nm; upper = nm.startswith('HG_Teeth') and not lower
        # weights
        head = (np.abs(x) < 0.095) & (z > E.z - 0.26) & (z < E.z + 0.02) & (y < piv.y + 0.03)
        if nm.startswith('HG_Teeth'):
            wr = np.ones(n) if lower else np.zeros(n); wst = np.ones(n)
        else:
            wr = np.clip((zn - 0.012 - z) / 0.030, 0, 1); wr = wr * wr * (3 - 2 * wr)              # 0 above the upper lip, 1 below the mouth line
            neck = np.clip((z - (E.z - float(os.environ.get("KW13_NZ", 0.175)))) / 0.06, 0, 1); neck = neck * neck * (3 - 2 * neck)   # under the chin the skin stretches
            lat = np.clip((piv.y + 0.03 - y) / 0.05, 0, 1)                                           # fades in front of the ear
            wr = wr * neck * lat * head
            wst = np.clip((zn + 0.004 - z) / 0.030, 0, 1); wst = wst * wst * (3 - 2 * wst); wst = wst * neck * lat * head
        # rotation about the x axis through piv (chin goes down and back: rotate so that -Y (front) goes down)
        dy, dz = y - piv.y, z - piv.z
        ry = piv.y + dy * c_ - dz * s_; rz = piv.z + dy * s_ + dz * c_
        d = np.zeros_like(cw); d[:, 1] = (ry - y) * wr; d[:, 2] = (rz - z) * wr - ST * wst
        loc = d @ Wi.T
        k = o.shape_key_add(name='kw13_long', from_mix=False); k.slider_max = 1.5
        k.data.foreach_set('co', (co + loc).ravel())
        if upper:     # upper front teeth tip forward about a point 9 mm above the incisal edge
            front = (np.abs(x) < 0.016) & (y < np.percentile(y, 30))
            zt = np.max(z[front]) if front.any() else E.z
            px, pz = y[front].max() if front.any() else 0, zt
            a = math.radians(TIP); d2 = np.zeros_like(cw)
            w2 = np.clip((0.016 - np.abs(x)) / 0.006, 0, 1) * (y < np.percentile(y, 40))
            dy2, dz2 = y - px, z - pz
            d2[:, 1] = ((px + dy2 * math.cos(a) + dz2 * math.sin(a)) - y) * w2
            d2[:, 2] = ((pz - dy2 * math.sin(a) + dz2 * math.cos(a)) - z) * w2
            k2 = o.shape_key_add(name='kw13_tip', from_mix=False); k2.data.foreach_set('co', (co + d2 @ Wi.T).ravel())
        out[nm] = int((np.abs(loc).sum(1) > 1e-5).sum())
    print('ep13 kw13_long verts', out, 'pivot', tuple(round(v, 3) for v in piv), flush=True)
    hg.keys = [o.data.shape_keys.key_blocks for o in hg.meshes if o.data.shape_keys]

def set_key(hg, name, v):
    for o in hg.meshes:
        kb = o.data.shape_keys.key_blocks if o.data.shape_keys else None
        k = kb.get(name) if kb else None
        if k is not None: k.value = v


ep.waive = {"1 shots;": "brief: one kit shot; the hard cuts (profile -> screen -> close ...) live in ep.cam_fn",
            "last shot must use cam=KW.cam.loop()": "brief: cam_fn cuts back to the frame-0 framing for the last 9 frames (the loop)",
            "HOOK cut <= 200 ms after the last word": "brief: CTA over the payoff shot, then the frame-0 cut",
            "HOOK 8-11 words": "script approved (lead option c), vidIQ length check deliver",
            "shot face holds": "brief: cuts every 1.1-4 s inside cam_fn"}
fw = lambda i, w: int(round(ep.word(i, w) * FPS))
fl = lambda i: int(round(ep.line(i) * FPS))
fle = lambda i: int(round((ep.line(i) + ep.vo_dur[i]) * FPS))
f_last = fle(6); FN = max(f_last + 26, 680); NF = FN + 1; ep.duration = round(NF / FPS, 4)
CTA0 = FN - 40
CUTS = [(0, 'PROF0'), (26, 'SCR'), (55, 'CLOSE'), (fl(1) - 4, 'FRONT1'), (fl(2) - 4, 'PROF2'), (fl(3) - 4, 'FRONT2'),
        (fl(4) - 4, 'MOUTH'), (fl(5) - 4, 'SCR2'), (fl(6) - 4, 'PROF3'), (FN - 9, 'PROF0')]
def shot_of(f):
    cur = CUTS[0]
    for c in CUTS:
        if f >= c[0]: cur = c
    nxt = next((c[0] for c in CUTS if c[0] > cur[0]), FN + 1)
    return cur[1], (f - cur[0]) / max(1, nxt - cur[0])
def keys(f, ks):
    if f <= ks[0][0]: return ks[0][1]
    for (f0, v0), (f1, v1) in zip(ks, ks[1:]):
        if f0 <= f <= f1: return v0 + (v1 - v0) * ease((f - f0) / max(1e-6, f1 - f0))
    return ks[-1][1]
def morph(f):
    if f >= FN - 9: return 0.0
    return keys(f, [(0, 0.0), (60, 0.0), (fl(1) - 8, 0.25), (fl(2) + 6, 0.25), (fle(2), 0.55), (fl(3) + 4, 0.55), (fle(3), 0.85),
                    (fl(6) + 4, 0.85), (fle(6), 1.0)])
def tip(f):
    if f >= FN - 9: return 0.0
    return keys(f, [(0, 0.0), (fl(4) + 6, 0.0), (fw(4, 'forward') + 4, 1.0)])
def jaw_open(f):
    if f >= FN - 9: return 0.16
    return keys(f, [(0, 0.16), (fl(1) + 10, 0.16), (fw(1, 'blocked') + 6, 0.27), (fl(2), 0.20), (fl(4) - 4, 0.20), (fl(4) + 4, 0.30), (fl(5) - 6, 0.30), (fl(5) - 3, 0.18)])

P = KW.pose('sit', at='bed_sit', face='calm', blend=5 * F)
ep.blinks = {'Ben': [44, 150, 236, 330, 420, 560, 640]}

SCR_C = (-0.10, 0.17, 2.05); SCR_W, SCR_H = 0.46, 0.2875
def build_screen(c):
    import bpy, kwlib as L
    tex = os.path.join(HERE, '..', '..', 'assets', 'real', 'tex', 'kw_mouth')
    m = bpy.data.materials.new('kw13_screen'); m.use_nodes = True; nt = m.node_tree; N = nt.nodes; N.clear(); Lk = nt.links.new
    out = N.new('ShaderNodeOutputMaterial'); em = N.new('ShaderNodeEmission'); uv = N.new('ShaderNodeTexCoord')
    def img(nm):
        n = N.new('ShaderNodeTexImage'); n.image = bpy.data.images.load(os.path.join(tex, nm + '.png'), check_existing=True)
        n.interpolation = 'Cubic'; Lk(uv.outputs['UV'], n.inputs['Vector']); return n
    i0, iA, iB = img('card0'), img('cardA'), img('cardB')
    su = N.new('ShaderNodeSeparateXYZ'); Lk(uv.outputs['UV'], su.inputs[0])
    rev = N.new('ShaderNodeValue'); my = N.new('ShaderNodeValue')
    lt = N.new('ShaderNodeMath'); lt.operation = 'LESS_THAN'; Lk(su.outputs['Y'], lt.inputs[0]); Lk(rev.outputs[0], lt.inputs[1])
    m1 = N.new('ShaderNodeMix'); m1.data_type = 'RGBA'; Lk(lt.outputs[0], m1.inputs['Factor']); Lk(i0.outputs['Color'], m1.inputs['A']); Lk(iA.outputs['Color'], m1.inputs['B'])
    m2 = N.new('ShaderNodeMix'); m2.data_type = 'RGBA'; Lk(my.outputs[0], m2.inputs['Factor']); Lk(m1.outputs['Result'], m2.inputs['A']); Lk(iB.outputs['Color'], m2.inputs['B'])
    Lk(m2.outputs['Result'], em.inputs['Color']); em.inputs['Strength'].default_value = float(os.environ.get('KW_SCRE', 1.4)); Lk(em.outputs[0], out.inputs[0])
    R['scr'] = (rev, my)
    cx, cy, cz = SCR_C; tilt = math.radians(-8)
    dark = L.mat('kw13_bezel', (0.035, 0.038, 0.042), 0.35, 0.2); steel = L.mat('kw13_steel', (0.72, 0.73, 0.75), 0.3, 1.0)
    L.box('kw13_bezel', (SCR_W + 0.024, 0.03, SCR_H + 0.024), (cx, cy + 0.016, cz), dark, c, 0.008, (math.degrees(tilt), 0, 0))
    bpy.ops.mesh.primitive_plane_add(size=1.0); pl = bpy.context.active_object; pl.name = 'kw13_panel'
    for u_ in list(pl.users_collection): u_.objects.unlink(pl)
    c.objects.link(pl); pl.scale = (SCR_W, SCR_H, 1); pl.rotation_euler = (math.radians(90) + tilt, 0, 0); pl.location = (cx, cy - 0.0005, cz)
    pl.data.materials.append(m)
    for a in ('visible_diffuse', 'visible_glossy', 'visible_transmission'): setattr(pl, a, a == 'visible_glossy')
    L.cyl('kw13_boom', 0.016, 2.80 - cz, (cx, cy + 0.06, (2.80 + cz) / 2), steel, c, (0, 0, 0), 20)
    L.box('kw13_mount', (0.12, 0.04, 0.08), (cx, cy + 0.045, cz), dark, c, 0.005)

def build(rt):
    import bpy
    c = bpy.data.collections.get('kw_ep13') or bpy.data.collections.new('kw_ep13')
    if c.name not in bpy.context.scene.collection.children: bpy.context.scene.collection.children.link(c)
    import kwlook as Q_; Q_.LOOP_T = FN / FPS
    long_keys(rt.actors[ben].p.hg); build_screen(c)
ep.build_hook = build

def eyes(rt):
    rg = rt.actors[ben].p.hg.rig; W_ = rg.matrix_world
    EL = W_ @ rg.pose.bones['eyeball.L'].head; ER = W_ @ rg.pose.bones['eyeball.R'].head; return EL, ER, (EL + ER) / 2

def frame_hook(rt, t):
    import bpy, kwlook as Q_
    Q_.LOOP_T = FN / FPS
    f = t * FPS; ra = rt.actors[ben]; hg = ra.p.hg
    set_key(hg, 'kw13_long', morph(f)); set_key(hg, 'kw13_tip', tip(f))
    jo = jaw_open(f)
    for k_, v_ in (('jawOpen', 1.0), ('mouthLowerDown_L', 1.4), ('mouthLowerDown_R', 1.4), ('mouthUpperUp_L', 0.6), ('mouthUpperUp_R', 0.6)):
        set_key(hg, k_, v_ * jo)
    EL, ER, Em = eyes(rt); rt.eyes_at(ra, Em + V((0.10, -0.60, 0.015)))
    rev, my = R['scr']
    rev.outputs[0].default_value = 0.0 if f < 30 else ease((f - 30) / 18)
    my.outputs[0].default_value = 1.0 if (fl(5) - 4 <= f < FN - 9) else 0.0
    bpy.context.view_layer.update(); sh_ = rt.ep.shot_at(t); rt.FX.update(sh_, t - sh_.t, t)
ep.frame_hook = frame_hook

def look(tg, dirv, dist, lens, fst=8.0, foc=None):
    dv = V(dirv).normalized(); return tg + dv * dist, tg, V((0, 0, 1)), lens, fst, (foc if foc is not None else tg)
def cam_fn(rt, t):
    import bpy
    f = t * FPS; bpy.context.view_layer.update(); shot, u = shot_of(f)
    EL, ER, Em = eyes(rt)
    push = lambda a, b: a * (b / a) ** ease(u)
    PX = float(os.environ.get('KW13_PX', 1.6))
    if shot in ('PROF0', 'PROF3'):
        tg = Em + V((0.03, 0.05, -0.13))
        d = 1.05 if (shot == 'PROF0') else push(1.05, 0.90)
        return look(tg, (PX, -1.0, 0.04), d, 50.0, 8.0, Em)
    if shot == 'PROF2':
        tg = Em + V((0, 0.01, -0.06)); return look(tg, (1.0, -0.08, 0.02), push(0.74, 0.66), 85.0, 11.0, Em + V((0, 0, -0.05)))
    if shot == 'CLOSE':
        tg = Em + V((0, -0.02, -0.095)); return look(tg, (1.0, -0.25, 0.02), push(0.44, 0.40), 85.0, 11.0, tg)
    if shot in ('FRONT1', 'FRONT2'):
        tg = Em + V((0, 0, -0.045 if shot == 'FRONT1' else -0.06))
        return look(tg, (0.06, -1.0, 0.02), push(0.62, 0.55) if shot == 'FRONT1' else push(0.72, 0.66), 85.0, 11.0, Em)
    if shot == 'MOUTH':
        tg = Em + V((0, -0.06, -0.078)); return look(tg, (0.25, -1.0, 0.05), push(0.32, 0.29), 85.0, 11.0, tg)
    tg = V(SCR_C) + V((0, 0, -0.06))
    return look(tg, (0.06, -1.0, 0.25), push(1.30, 1.20), 50.0, 8.0, V(SCR_C))
ep.cam_fn = cam_fn

YL = dict(color='yellow', size=1.2); Y = 0.89; YB = 0.17
ep.label_outline = True; ep.label_maxw = 820.0; ep.label_lens_fix = True
labels = [KW.fx.label('OPEN MOUTH', at=-1.0, pos=(0.5, Y), dur=1.0 + 25 * F, **YL),
          KW.fx.label('LONGER', at=60 * F, pos=(0.5, Y), dur=(fl(1) - 8 - 60) * F, **YL),
          KW.fx.label('BLOCKED', at=fw(1, 'blocked') * F, pos=(0.5, Y), dur=(fl(2) - 6 - fw(1, 'blocked')) * F, **YL),
          KW.fx.label('JAW DOWN', at=fw(2, 'rotated') * F, pos=(0.5, Y), dur=(fl(3) - 6 - fw(2, 'rotated')) * F, **YL),
          KW.fx.label('TALLER', at=fw(3, 'taller,') * F, pos=(0.5, Y), dur=(fl(4) - 6 - fw(3, 'taller,')) * F, **YL),
          KW.fx.label('TEETH OUT', at=fw(4, 'forward') * F, pos=(0.5, Y), dur=(fw(4, 'narrowed.') - 2 - fw(4, 'forward')) * F, **YL),
          KW.fx.label('NARROW', at=fw(4, 'narrowed.') * F, pos=(0.5, Y), dur=(fl(5) - 6 - fw(4, 'narrowed.')) * F, **YL),
          KW.fx.label('LONG FACE', at=fw(6, 'longer,') * F, pos=(0.5, Y), dur=(CTA0 - 2 - fw(6, 'longer,')) * F, **YL),
          KW.fx.label('DO YOU?', at=CTA0 * F, pos=(0.5, 0.30), dur=(FN - 10 - CTA0) * F, **YL),
          KW.fx.label('COMMENT BELOW', at=(CTA0 + 3) * F, pos=(0.5, 0.235), dur=(FN - 13 - CTA0) * F, color='white', size=0.5),
          KW.fx.label('OPEN MOUTH', at=(FN - 9) * F, pos=(0.5, Y), dur=2.0, **YL)]
labels[-1].o['nopop'] = True
ep.sound(0.0, 'thud', 0.6)
for f_ in (26, 55, fw(2, 'rotated'), fw(3, 'taller,'), fw(4, 'forward')): ep.sound(f_ * F, 'thud', 0.45)
ep.mouth_fix = True; ep.eyes_fix = True; ep.relight_after_pose = True
ep.shot(0.0, 'face', set='hospital', cast={ben: P}, fx=labels, cam=KW.cam.face(ben))
ep.run()
