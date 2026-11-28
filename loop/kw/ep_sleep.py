"""Kinda Wild Films ep17 - 'What Skipping One Night Of Sleep Does To Your Body'  Brief: kindawild/17_sleep/brief.md.
Facts: Sundelin et al., Sleep 2013;36:1355 (faces after sleep loss: hanging lids, red swollen eyes, dark circles, pale skin,
droopy mouth corners; rated sadder) + Dawson & Reid, Nature 1997;388:235 (40 people, 28 h awake; 17 h = 0.05 % BAC, 24 h = 0.10 %).
Ben alone on the clinic bed (a sleep-lab night).  Body changes on Ben's own mesh: lids hang (blink keys), red lid rims, puffy
under-eyes (2 mm shape key), dark circles, paler skin, mouth corners droop (ARKit mouthFrown).  Colour overlays <= 30 %.
The clinic screen shows PIL cards: tracking test 17 h / 24 h, the 40-people chart, rested-vs-tired face stills (kwsleepcard_gen.py).
Consequence (~57 %): at 24 h his head drops (micro-sleep) and snaps back.  Ladder rung 7: blinks timed to cuts and the head snap.
"""
import sys, os, math; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kwkit as KW
os.environ.setdefault('KW_LIGHT', '1')
HERE = os.path.dirname(os.path.abspath(__file__))
ep = KW.Episode('ep_sleep', injury="face shows it",
                voice_lines=[l.strip() for l in open(os.path.join(HERE, 'ep_sleep.txt')) if l.strip()],
                music='sneaky_snitch', gap=0.6)
ep.tts_say = {3: "After 17 hours awake, your hand-eye skills match a blood alcohol level of zero point zero five percent.",
              4: "After 24 hours, they match zero point one percent, over the U.S. drunk-driving limit."}
ben = ep.person('Ben', 'civilian', 'eatmore-ben', gender='m', age='young', race='caucasian', hair='short02', tee='teal')

FPS = 24; F = 1.0 / FPS
try: from mathutils import Vector as V
except ImportError: V = None
def ease(x): x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)
R = {}
OV = float(os.environ.get('KW17_OV', 0.28))            # colour overlays (<= 0.30 lead rule)
FORCE = os.environ.get('KW17_FORCE')                   # probe: force all tired changes to this value
FCAM = os.environ.get('KW17_CAM')                      # probe: force a shot (card stills)

KW.FACES.update({
    'fresh': {'smile': 0.15},
    'tired1': {'blink': 0.22},
    'tired2': {'blink': 0.45, 'worry': 0.15},
    'tired3': {'blink': 0.48, 'worry': 0.2, 'x_droop': 1.0},
    'nod': {'blink': 1.0, 'x_droop': 0.6},
    'snap': {'wide': 0.6, 'x_droop': 0.7},
    'heavy': {'blink': 0.78, 'worry': 0.25, 'x_droop': 1.0},
    'sadder': {'blink': 0.5, 'worry': 0.6, 'x_droop': 1.5},
})
try:
    import bpy  # noqa: F401
    import heads_hg as HH
    HH.ARK['x_droop'] = {'mouthFrown_L': 1.35, 'mouthFrown_R': 1.35, 'mouthLowerDown_L': 0.2, 'mouthLowerDown_R': 0.2}
    HH.ARK_NAMES = sorted({k for d in HH.ARK.values() for k in d})
except ImportError:
    pass

ep.waive = {"1 shots;": "brief: one kit shot; the hard cuts live in ep.cam_fn",
            "last shot must use cam=KW.cam.loop()": "brief: cam_fn cuts back to the frame-0 framing for the last 9 frames (the loop)",
            "HOOK cut <= 200 ms after the last word": "brief: CTA over the payoff shot, then the frame-0 cut",
            "shot face holds": "brief: cuts every 1.1-4 s inside cam_fn"}
fw = lambda i, w: int(round(ep.word(i, w) * FPS))
fl = lambda i: int(round(ep.line(i) * FPS))
fle = lambda i: int(round((ep.line(i) + ep.vo_dur[i]) * FPS))
f_last = fle(6); FN = max(f_last + 30, 760); NF = FN + 1; ep.duration = round(NF / FPS, 4)
CTA0 = FN - 40
FND = fl(4) + 11                        # consequence: head drops at 24 h (micro-sleep) ...
FSN = FND + 22                          # ... and snaps back
CUTS = [(0, 'MED0'), (22, 'CLOCK'), (46, 'CLOSE'), (fl(1) - 4, 'EYES'), (fl(2) - 4, 'FACE'), (fw(2, 'mouth') - 3, 'MOUTH'),
        (fl(3) - 4, 'EYES'), (fw(3, 'blood') - 3, 'SCR'), (fl(4) - 4, 'MED1'), (fw(4, 'percent') - 6, 'SCR'),
        (fl(5) - 4, 'BFACE'), (fw(5, '40') - 3, 'SCR'), (fl(6) - 4, 'MOUTH'), (fw(6, 'rated') - 3, 'SCR'),
        (CTA0 - 4, 'BFACE'), (FN - 9, 'MED0')]
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
def ramp(f, f0, n=10): return keys(f, [(f0 - 2, 0.0), (f0 + n, 1.0)])
def v_red(f): return ramp(f, fw(1, 'red'))
def v_puff(f): return ramp(f, fw(1, 'swollen.'))
def v_dark(f): return ramp(f, fw(2, 'Dark'), 14)
def v_pale(f): return ramp(f, fw(2, 'pale,'), 14)

PB = (KW.pose('sit', at='bed_sit', face='fresh', blend=5 * F)
      .then(8 * F, face='tired1', blend=30 * F)
      .then((fw(1, 'eyelids') + 4) * F, face='tired2', head=(4, 0, 0), blend=8 * F)
      .then((fw(2, 'droop.') - 3) * F, face='tired3', head=(7, 0, 0), blend=8 * F)
      .then((fl(3) - 2) * F, face='heavy', head=(10, 0, 1), blend=14 * F)          # 17 h: lids sink, eyes glaze
      .then((fw(3, 'blood') - 4) * F, face='tired3', head=(7, 0, 0), blend=10 * F)
      .then(FND * F, face='nod', head=(26, 0, 2), blend=12 * F)
      .then(FSN * F, face='snap', head=(-3, 0, 0), blend=6 * F)
      .then((FSN + 14) * F, face='tired3', head=(7, 0, 0), blend=12 * F)
      .then((fl(5) - 4) * F, face='tired3', act=KW.act.yawn(at=(fl(5) - 1) * F), blend=4 * F)   # 28 h test: a jaw-cracking yawn
      .then((fl(6) - 4) * F, face='sadder', head=(9, 0, -2), blend=10 * F)          # faces rated sadder: corners sink further
      .then((fw(6, 'rated') - 3) * F, face='tired3', head=(7, 0, 0), blend=10 * F)
      .then((FN - 14) * F, face='fresh', head=(0, 0, 0), blend=5 * F))
ep.blinks = {'Ben': [fl(1) + 14, fl(2) - 2, fl(3) + 30, FSN + 1, fl(5) + 40, fl(6) + 10]}

# ------------------------------------------------------------------ screen (same mount as ep14-16), 4 cards
SCR_C = (-0.10, 0.17, 2.05); SCR_W, SCR_H = 0.46, 0.2875
CARDS = ('test17', 'test24', 'chart', 'faces')
def card_of(f):
    if f >= fl(6) - 4: return 3
    if f >= fl(5) - 4: return 2
    if f >= fw(4, 'percent') - 6: return 1
    return 0
def build_screen(c):
    import bpy, kwlib as L
    tex = os.path.join(HERE, '..', '..', 'assets', 'real', 'tex', 'kw_sleep')
    m = bpy.data.materials.new('kw17_screen'); m.use_nodes = True; nt = m.node_tree; N = nt.nodes; N.clear(); Lk = nt.links.new
    out = N.new('ShaderNodeOutputMaterial'); em = N.new('ShaderNodeEmission'); uv = N.new('ShaderNodeTexCoord')
    def img(nm):
        n = N.new('ShaderNodeTexImage'); n.image = bpy.data.images.load(os.path.join(tex, nm + '.png'), check_existing=True)
        n.interpolation = 'Cubic'; Lk(uv.outputs['UV'], n.inputs['Vector']); return n
    ims = [img(nm) for nm in CARDS]; prev = ims[0].outputs['Color']; R['scr'] = []
    for im in ims[1:]:
        v = N.new('ShaderNodeValue'); x = N.new('ShaderNodeMix'); x.data_type = 'RGBA'
        Lk(v.outputs[0], x.inputs['Factor']); Lk(prev, x.inputs['A']); Lk(im.outputs['Color'], x.inputs['B']); prev = x.outputs['Result']; R['scr'].append(v)
    Lk(prev, em.inputs['Color']); em.inputs['Strength'].default_value = float(os.environ.get('KW_SCRE', 1.4)); Lk(em.outputs[0], out.inputs[0])
    R['scre'] = em
    cx, cy, cz = SCR_C; tilt = math.radians(-8)
    dark = L.mat('kw17_bezel', (0.035, 0.038, 0.042), 0.35, 0.2); steel = L.mat('kw17_steel', (0.72, 0.73, 0.75), 0.3, 1.0)
    L.box('kw17_bezel', (SCR_W + 0.024, 0.03, SCR_H + 0.024), (cx, cy + 0.016, cz), dark, c, 0.008, (math.degrees(tilt), 0, 0))
    bpy.ops.mesh.primitive_plane_add(size=1.0); pl = bpy.context.active_object; pl.name = 'kw17_panel'
    for u_ in list(pl.users_collection): u_.objects.unlink(pl)
    c.objects.link(pl); pl.scale = (SCR_W, SCR_H, 1); pl.rotation_euler = (math.radians(90) + tilt, 0, 0); pl.location = (cx, cy - 0.0005, cz)
    pl.data.materials.append(m)
    for a in ('visible_diffuse', 'visible_glossy', 'visible_transmission'): setattr(pl, a, a == 'visible_glossy')
    L.cyl('kw17_boom', 0.016, 2.80 - cz, (cx, cy + 0.06, (2.80 + cz) / 2), steel, c, (0, 0, 0), 20)
    L.box('kw17_mount', (0.12, 0.04, 0.08), (cx, cy + 0.045, cz), dark, c, 0.005)

# ------------------------------------------------------------------ Ben's own mesh: puffy under-eyes, dark circles, red rims, pale
def rest_local(o):
    import numpy as np
    n = len(o.data.vertices); kb = o.data.shape_keys.key_blocks if o.data.shape_keys else None
    co = np.empty(n * 3)
    if kb: kb[0].data.foreach_get('co', co)
    else: o.data.vertices.foreach_get('co', co)
    co = co.reshape(-1, 3); mix = co.copy()
    if kb:
        tmp = np.empty(n * 3); ref = np.empty(n * 3)
        for k in kb[1:]:
            if k.mute or abs(k.value) < 1e-6 or k.name.startswith('kw17'): continue
            k.data.foreach_get('co', tmp); k.relative_key.data.foreach_get('co', ref)
            mix += k.value * (tmp - ref).reshape(-1, 3)
    return co, mix

def body_keys(hg):
    """kw17_puff (2.2 mm under-eye bags) on Ben's HG_Body + vertex colour kw17g (R = dark circles, G = lid rims) and a skin
    desaturation node (pale); each overlay at most OV."""
    import numpy as np, bpy
    body = next(o for o in hg.meshes if o.name.startswith('HG_Body'))
    co, c = rest_local(body); n = len(c)
    B2M = np.array(body.matrix_world.inverted() @ hg.rig.matrix_world)
    bone = lambda nm: B2M[:3, :3] @ np.array(hg.rig.data.bones[nm].head_local) + B2M[:3, 3]
    nrm = np.empty(n * 3); body.data.vertices.foreach_get('normal', nrm); nrm = nrm.reshape(-1, 3)
    dark = np.zeros(n); rim = np.zeros(n); puff = np.zeros(n); P = {}
    for s, nm in ((1, 'eyeball.L'), (-1, 'eyeball.R')):
        e = bone(nm); d = c - e
        m = (np.abs(d[:, 0]) < 0.005) & (d[:, 2] < -0.012) & (d[:, 2] > -0.024) & (d[:, 1] < 0)
        if not m.any(): continue
        u = c[m][np.argmin(c[m][:, 1])]; P[nm] = np.round(u - e, 4).tolist()
        du = c - u; front = (d[:, 1] < 0.004).astype(float)
        dark = np.maximum(dark, front * np.exp(-(du[:, 0] ** 2) / (2 * 0.011 ** 2) - (du[:, 2] ** 2) / (2 * 0.0065 ** 2)))
        puff = np.maximum(puff, front * np.exp(-(du[:, 0] ** 2) / (2 * 0.008 ** 2) - (du[:, 2] ** 2) / (2 * 0.0045 ** 2)))
        rxz = np.sqrt(d[:, 0] ** 2 + (d[:, 2] * 1.5) ** 2)
        rim = np.maximum(rim, front * (d[:, 1] < -0.004) * np.exp(-((rxz - 0.0145) ** 2) / (2 * 0.0025 ** 2)))
    print('kw17 under-eye points', P, 'dark', int((dark > 0.3).sum()), 'rim', int((rim > 0.3).sum()))
    if body.data.shape_keys is None: body.shape_key_add(name='Basis', from_mix=False)
    k = body.shape_key_add(name='kw17_puff', from_mix=False); k.slider_max = 1.5; k.value = 0.0
    k.data.foreach_set('co', (co + 0.0022 * puff[:, None] * nrm).ravel())
    ca = body.data.color_attributes.get('kw17g') or body.data.color_attributes.new('kw17g', 'FLOAT_COLOR', 'POINT')
    ca.data.foreach_set('color', np.stack([dark, rim, np.zeros(n), np.ones(n)], 1).astype(np.float32).ravel())
    vd, vr, vp = [], [], []
    for mt in body.data.materials:
        if not mt or not mt.use_nodes or not mt.name.startswith('.Human'): continue
        N = mt.node_tree.nodes; Lk = mt.node_tree.links.new
        bs = next(q for q in N if q.bl_idname == 'ShaderNodeBsdfPrincipled'); bc = bs.inputs['Base Color']
        if not bc.is_linked: continue
        src = bc.links[0].from_socket
        hs = N.new('ShaderNodeHueSaturation'); Lk(src, hs.inputs['Color']); p = N.new('ShaderNodeValue'); p.outputs[0].default_value = 0.0; vp.append(p)
        ms = N.new('ShaderNodeMath'); ms.operation = 'MULTIPLY_ADD'; Lk(p.outputs[0], ms.inputs[0]); ms.inputs[1].default_value = -1.0; ms.inputs[2].default_value = 1.0
        Lk(ms.outputs[0], hs.inputs['Saturation'])
        mv = N.new('ShaderNodeMath'); mv.operation = 'MULTIPLY_ADD'; Lk(p.outputs[0], mv.inputs[0]); mv.inputs[1].default_value = 0.25; mv.inputs[2].default_value = 1.0
        Lk(mv.outputs[0], hs.inputs['Value'])
        at = N.new('ShaderNodeAttribute'); at.attribute_name = 'kw17g'; sp = N.new('ShaderNodeSeparateColor'); Lk(at.outputs['Color'], sp.inputs[0])
        cur = hs.outputs['Color']
        for ch, col, lst in ((0, (0.09, 0.05, 0.08, 1.0), vd), (1, (0.70, 0.16, 0.13, 1.0), vr)):
            a = N.new('ShaderNodeValue'); a.outputs[0].default_value = 0.0; lst.append(a)
            m1 = N.new('ShaderNodeMath'); m1.operation = 'MULTIPLY'; Lk(sp.outputs[ch], m1.inputs[0]); Lk(a.outputs[0], m1.inputs[1])
            mx = N.new('ShaderNodeMix'); mx.data_type = 'RGBA'; Lk(m1.outputs[0], mx.inputs['Factor']); Lk(cur, mx.inputs['A'])
            mx.inputs['B'].default_value = col; cur = mx.outputs['Result']
        Lk(cur, bc)
    R['ov'] = (vd, vr, vp); print('kw17 overlay nodes', len(vd)); R['body'] = body

def build(rt):
    import bpy
    c = bpy.data.collections.get('kw_ep17') or bpy.data.collections.new('kw_ep17')
    if c.name not in bpy.context.scene.collection.children: bpy.context.scene.collection.children.link(c)
    import kwlook as Q_; Q_.LOOP_T = FN / FPS
    build_screen(c); body_keys(rt.actors[ben].p.hg)
ep.build_hook = build

def eyes(rt, who):
    rg = rt.actors[who].p.hg.rig; W_ = rg.matrix_world
    EL = W_ @ rg.pose.bones['eyeball.L'].head; ER = W_ @ rg.pose.bones['eyeball.R'].head; return EL, ER, (EL + ER) / 2

def set_key(hg, name, v):
    for o in hg.meshes:
        kb = o.data.shape_keys.key_blocks if o.data.shape_keys else None
        k = kb.get(name) if kb else None
        if k is not None: k.value = v

def frame_hook(rt, t):
    import bpy, kwlook as Q_
    Q_.LOOP_T = FN / FPS
    f = t * FPS; hb = rt.actors[ben].p.hg
    fv = float(FORCE) if FORCE is not None else None
    red, puff, dark, pale = [(fv if fv is not None else fn(f)) for fn in (v_red, v_puff, v_dark, v_pale)]
    if f >= FN - 9 and fv is None: red = puff = dark = pale = 0.0
    set_key(hb, 'kw17_puff', puff)
    vd, vr, vp = R['ov']
    for n_ in vd: n_.outputs[0].default_value = OV * dark
    for n_ in vr: n_.outputs[0].default_value = OV * red
    for n_ in vp: n_.outputs[0].default_value = OV * pale
    k = card_of(f)
    for i, v in enumerate(R['scr']): v.outputs[0].default_value = 1.0 if k >= i + 1 else 0.0
    R['scre'].inputs['Strength'].default_value = float(os.environ.get('KW_SCRE', 1.4)) if (fl(3) - 4 <= f < FN - 9) else 0.0
    bpy.context.view_layer.update()
    sh_ = rt.ep.shot_at(t); rt.FX.update(sh_, t - sh_.t, t)
ep.frame_hook = frame_hook

def look(tg, dirv, dist, lens, fst=8.0, foc=None):
    dv = V(dirv).normalized(); return tg + dv * dist, tg, V((0, 0, 1)), lens, fst, (foc if foc is not None else tg)
CLOCK = (0.55, 1.52, 2.10)
def cam_fn(rt, t):
    import bpy
    f = t * FPS; bpy.context.view_layer.update(); shot, u = shot_of(f)
    if FCAM: shot, u = FCAM, 0.5
    _, _, EB = eyes(rt, ben)
    push = lambda a, b: a * (b / a) ** ease(u)
    if shot in ('MED0', 'MED1'):
        tg = EB + V((0.0, 0.0, -0.20)); d_ = push(1.30, 1.18) if shot == 'MED0' and f < FN - 9 else (push(1.25, 1.12) if shot == 'MED1' else 1.30)
        return look(tg, (-0.75, -1.0, 0.05), d_, 50.0, 8.0, EB)
    if shot == 'CLOCK':                                            # cutaway: the wall clock (night passing)
        tg = V(CLOCK); return look(tg, (-0.15, -1.0, -0.12), push(0.80, 0.68), 50.0, 8.0, tg)
    if shot in ('CLOSE', 'BFACE'):
        tg = EB + V((0, 0, -0.05)); return look(tg, (-0.25, -1.0, 0.02), push(0.55, 0.46), 85.0, 11.0, EB)
    if shot == 'EYES':                                             # tight on both eyes: lids, red rims, bags
        tg = EB + V((0, 0, -0.008)); return look(tg, (-0.18, -1.0, 0.02), push(0.42, 0.37), 85.0, 13.0, EB)
    if shot == 'FACE':                                             # 3/4 face: dark circles, pale skin
        tg = EB + V((0, 0, -0.04)); return look(tg, (-0.55, -1.0, 0.02), push(0.50, 0.43), 85.0, 11.0, EB)
    if shot == 'MOUTH':                                            # lower face: the drooping corners
        tg = EB + V((0, -0.02, -0.075)); return look(tg, (-0.30, -1.0, 0.0), push(0.38, 0.33), 85.0, 11.0, tg)
    tg = V(SCR_C) + V((0, 0, -0.15))                                 # SCR: screen + Ben below it, label clear above
    return look(tg, (0.06, -1.0, 0.25), push(1.55, 1.45), 50.0, 8.0, V(SCR_C))
ep.cam_fn = cam_fn

YL = dict(color='yellow', size=1.2); Y = 0.89
ep.label_outline = True; ep.label_maxw = 820.0; ep.label_lens_fix = True
def lab(txt, f0, f1, **k): return KW.fx.label(txt, at=f0 * F, pos=(0.5, Y), dur=(f1 - f0) * F, **(k or YL))
wd = fw
labels = [KW.fx.label('NO SLEEP', at=-1.0, pos=(0.5, Y), dur=1.0 + (fl(1) - 6) * F, **YL),
          lab('LIDS', wd(1, 'eyelids'), wd(1, 'red') - 1),
          lab('RED', wd(1, 'red'), wd(1, 'swollen.') - 1),
          lab('SWOLLEN', wd(1, 'swollen.'), fl(2) - 6),
          lab('DARK', wd(2, 'Dark'), wd(2, 'pale,') - 1),
          lab('PALE', wd(2, 'pale,'), wd(2, 'droop.') - 1),
          lab('DROOP', wd(2, 'droop.'), fl(3) - 6),
          lab('17 HOURS', fl(3), fl(4) - 6),
          lab('24 HOURS', fl(4), wd(4, 'over') - 1),
          lab('OVERLIMIT', wd(4, 'over'), fl(5) - 6),
          lab('TESTED', fl(5), fl(6) - 6),
          lab('SADDER', wd(6, 'sadder,'), CTA0 - 2),
          KW.fx.label('HOURS?', at=CTA0 * F, pos=(0.5, 0.30), dur=(FN - 10 - CTA0) * F, **YL),
          KW.fx.label('COMMENT BELOW', at=(CTA0 + 3) * F, pos=(0.5, 0.235), dur=(FN - 13 - CTA0) * F, color='white', size=0.5),
          KW.fx.label('NO SLEEP', at=(FN - 9) * F, pos=(0.5, Y), dur=2.0, **YL)]
labels[-1].o['nopop'] = True
ep.sound(0.0, 'thud', 0.6)
for f_ in (fw(1, 'red'), fw(2, 'Dark'), FSN, fl(5)): ep.sound(f_ * F, 'thud', 0.45)
ep.mouth_fix = True; ep.eyes_fix = True; ep.relight_after_pose = True
ep.shot(0.0, 'face', set='hospital', cast={ben: PB}, fx=labels, cam=KW.cam.face(ben))
ep.run()
