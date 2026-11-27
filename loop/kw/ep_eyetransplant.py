"""Kinda Wild Films ep11 - 'His Transplanted Eye Stayed Alive'.  Brief: kindawild/11_eye/brief.md (+ lead GO rulings 27 Nov).
ONE unbroken camera in the clinic: extreme close of Ben's left eye with a penlight sweep -> eased pull-back to Ben on the exam
bed -> the RETINA SCAN screen above him (vessels pulse 1.1 Hz, ERG trace after the flash) -> both eyes in the light: his right
pupil constricts, the new (left) pupil stays fixed -> back to the left-eye close (loop).  Ben stands in for the patient
(generic, unharmed).  Camera keys live in the frame of his left eyeball (ep.cam_fn); the penlight is tool-only and only ever
in the extreme close (lead ruling 3: eased exit before the pull-back passes the face close).
"""
import sys, os, math; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kwkit as KW
os.environ.setdefault('KW_LIGHT', '1')
HERE = os.path.dirname(os.path.abspath(__file__))
ep = KW.Episode('ep_eyetransplant', injury="burned away",
                voice_lines=[l.strip() for l in open(os.path.join(HERE, 'ep_eyetransplant.txt')) if l.strip()],
                music='sneaky_snitch', gap=0.9)
ep.tts_say = {0: ep.lines_text[0].replace('eye, so', 'eye so')}     # lead GO ruling 1: no pause between "eye," and "so"
ep.waive = {"1 shots;": "brief s6: ONE unbroken shot (no cuts)",
            "last shot must use cam=KW.cam.loop()": "brief s6: the camera path itself returns to the frame-0 view at fN (the loop)",
            "HOOK cut <= 200 ms after the last word": "brief s6: 1.1 s loop return carrying the end question, then the frame-0 title",
            "HOOK 8-11 words": "brief s3: script approved by the lead (GO 27 Nov)",
            "shot eye holds": "brief s6: ONE unbroken shot; a visible change every <= 2.2 s comes from the eye, light, screen and camera",
            "HOOK inside the body": "brief s5: no diagram in the first 3 s (STAY GATE); the retina is shown on the clinic screen"}
ben = ep.person('Ben', 'civilian', 'eatmore-ben', gender='m', age='young', race='caucasian', hair='short02', tee='teal')

FPS = 24; F = 1.0 / FPS
try: from mathutils import Vector as V, Matrix
except ImportError: V = Matrix = None     # kwvo.py runs outside Blender
fw = lambda i, w: int(round(ep.word(i, w) * FPS))
fl = lambda i: int(round(ep.line(i) * FPS))
fle = lambda i: int(round((ep.line(i) + ep.vo_dur[i]) * FPS))

# ---- timeline (frames) ---------------------------------------------------------------------------------------------------
SW0, SW1 = 0, 22                        # the beam sweeps across the eye (opening rule: change inside 1 s)
SACC = [(0, (0.0, 0.0)), (6, (0.0085, 0.0030)), (13, (-0.0040, 0.0065)), (19, (0.0030, -0.0020))]   # micro-saccades in the first second
BLINK0 = 40                             # lead ruling 2: one natural blink after the sweep
PX0, PX1 = 48, 76                       # penlight eases out of frame (before the pull-back passes the face close)
PB0 = 62                                # pull-back starts
f_nobody, f_hours, f_alive, f_blood = fw(1, 'Nobody'), fw(2, 'twenty-one'), fw(3, 'alive,'), fw(3, 'blood')
f_its, f_fired, f_signals, f_light = fl(4), fw(4, 'fired'), fw(4, 'signals'), fw(4, 'light')
f_L5, f_cant, f_see5, f_L6 = fl(5), fw(5, "can't"), fw(5, 'see'), fl(6)
f_last = fle(6)
FL0 = f_its + 4; FL1 = fl(5) - 8        # the flash: light on both eyes
FLA1 = FL0 + 26; FL2 = f_light - 4        # flash 1 (FL0..FLA1) drives the ERG on the screen; flash 2 (FL2..FL1) in the both-eyes close
CON0, CON1 = FL2 + 5, FL2 + 15          # his right pupil constricts on flash 2 (~0.2 s latency, ~0.5 s); the new (left) one never does
DIL0, DIL1 = FL1, FL1 + 30              # ... and relaxes when the light goes off
FN = max(f_last + 26, 720); NF = FN + 1
ep.duration = round(NF / FPS, 4)
CTA0 = FN - 40
PI0, PI1 = FN - 72, FN - 30             # penlight glides back in from the right edge (tool only, extreme close)
PION0 = FN - 32                         # ... and its light fades on over 6 frames before the loop point
CNT_END = fl(3) - 12
ERG0 = FL0 + 2                          # the ERG trace starts drawing at the flash

def ease(x): x = max(0.0, min(1.0, x)); return x * x * (3 - 2 * x)
def keys(f, ks):
    if f <= ks[0][0]: return ks[0][1]
    for (f0, v0), (f1, v1) in zip(ks, ks[1:]):
        if f0 <= f <= f1: return v0 + (v1 - v0) * ease((f - f0) / max(1e-6, f1 - f0))
    return ks[-1][1]

# ---- Ben: seated on the exam bed, hands at rest, calm face ----------------------------------------------------------------
P = KW.pose('sit', at='bed_sit', face='calm', blend=5 * F)
ep.blinks = {'Ben': [BLINK0, 128, 222, 300, 384, 532, 618, 664]}       # none during the flash (FL0..FL1) and none in the last 12 frames

R = {}                                  # built parts

def eyeball(rt, s='L'):
    hg = rt.actors[ben].p.hg; rg = hg.rig
    return rg.matrix_world @ rg.pose.bones[f'eyeball.{s}'].head

# ---- ladder rung 4: nose tip, ears, knuckles and fingertips a touch redder than cheeks and palms -------------------------
RUNG4 = float(os.environ.get('KW_R4', 0.16))     # added to the v1.1 red mask (RED_TINT 1.10/0.80/0.78 at 1): small on purpose
def skin_rung4(G):
    import numpy as np
    body, rig = G.body, G.rig; me = body.data; at = me.color_attributes.get('kw11_skin')
    if at is None or RUNG4 <= 0: print('ep11 rung4: no kw11_skin mask'); return
    n = len(me.vertices); co = np.empty(n * 3); me.shape_keys.key_blocks[0].data.foreach_get('co', co); co = co.reshape(-1, 3)
    B2M = body.matrix_world.inverted() @ rig.matrix_world
    bh = lambda nm, tail=False: np.array(B2M @ (rig.data.bones[nm].tail_local if tail else rig.data.bones[nm].head_local)) if nm in rig.data.bones else None
    g = lambda c, s_: np.exp(-np.sum((co - c) ** 2, axis=1) / (2 * s_ * s_))
    eL, eR = bh('eyeball.L'), bh('eyeball.R'); E = (eL + eR) / 2
    m = (np.abs(co[:, 0] - E[0]) < 0.008) & (co[:, 2] < E[2] - 0.01) & (co[:, 2] > E[2] - 0.07) & (np.abs(co[:, 1] - E[1]) < 0.15)
    tip = co[m][np.argmin(co[m][:, 1])]; add = g(tip, 0.010)
    hm = (np.abs(co[:, 2] - E[2]) < 0.035) & (np.abs(co[:, 1] - E[1]) < 0.15)
    for s_ in (-1, 1):
        sm = hm & (s_ * (co[:, 0] - E[0]) > 0)
        if sm.any(): add += g(co[sm][np.argmax(s_ * (co[sm][:, 0] - E[0]))], 0.018)
    for sd in 'LR':
        for f_ in ('f_index', 'f_middle', 'f_ring', 'f_pinky'):
            c = bh(f'{f_}.01.{sd}')
            if c is not None: add += g(c, 0.009)                       # knuckle
            c = bh(f'{f_}.03.{sd}', True)
            if c is not None: add += 0.9 * g(c, 0.007)                 # fingertip pad
        c = bh(f'thumb.03.{sd}', True)
        if c is not None: add += 0.9 * g(c, 0.008)
    col = np.empty(n * 4, np.float32); at.data.foreach_get('color', col); col = col.reshape(-1, 4)
    r0 = col[:, 0].copy(); col[:, 0] = np.clip(r0 + RUNG4 * np.clip(add, 0, 1), 0, 1); at.data.foreach_set('color', col.ravel())
    print(f'ep11 rung4: red mask +{RUNG4} at nose/ears/knuckles/fingertips, verts > 0.5 add: {(add > 0.5).sum()}, mean change {(col[:, 0] - r0).mean():.4f}')

# ---- lashes (CHECK 1 fix a) -------------------------------------------------------------------------------------------------
def lash_fix(hg):
    """Taper every lash (thick root, fine tip), soften the clump-to-a-spike look; the lower lid keeps ~60% of its lashes,
    each ~55% long, via a length vertex group (a zero-length lash renders nothing)."""
    import bpy, random
    body = hg.body
    for md in body.modifiers:
        if md.type != 'PARTICLE_SYSTEM' or 'Eyelash' not in md.particle_system.settings.name: continue
        ps = md.particle_system; st = ps.settings
        st.root_radius = 0.014; st.tip_radius = 0.0; st.shape = float(os.environ.get('KW_LSHAPE', -0.45))
        st.clump_factor = float(os.environ.get('KW_LCLUMP', 0.6)); st.child_radius = 0.0016; st.roughness_endpoint = 0.00025
        locs = [tuple(p_.location) for p_ in ps.particles]
        rng = random.Random(11); vg = body.vertex_groups.get('kw11_lashlen') or body.vertex_groups.new(name='kw11_lashlen')
        me = body.data; nv = len(me.vertices); w = {}
        for side in (1, -1):
            pts = [q for q in locs if q[0] * side > 0]
            if not pts: continue
            z0, z1 = min(q[2] for q in pts), max(q[2] for q in pts); zm = z0 + 0.42 * (z1 - z0)
            for q in pts:
                lower = q[2] < zm
                val = 1.0 if not lower else (0.0 if rng.random() < float(os.environ.get('KW_LTHIN', 0.4)) else float(os.environ.get('KW_LLEN', 0.55)))
                w[q] = val; w[(-q[0], q[1], q[2])] = val      # particle.location reports both lids at +x (probe 27 Nov): mirror onto his right eye
        import mathutils
        kd = mathutils.kdtree.KDTree(nv)
        for vi, v in enumerate(me.vertices): kd.insert(v.co, vi)
        kd.balance()
        vg.add(list(range(nv)), 1.0, 'REPLACE')
        keys_ = list(w.keys()); kr = mathutils.kdtree.KDTree(len(keys_))
        for i_, q in enumerate(keys_): kr.insert(q, i_)
        kr.balance(); hit = set()
        for q in keys_:
            for co, vi, d in kd.find_range(q, 0.0015): hit.add(vi)
        for vi in hit:                                   # each vertex near a root takes the value of its nearest root
            co, i_, d = kr.find(me.vertices[vi].co); vg.add([vi], w[keys_[i_]], 'REPLACE')
        ps.vertex_group_length = vg.name
        print(f'ep11 lashes: taper root {st.root_radius} tip 0, shape {st.shape}, clump {st.clump_factor}; lower lid {sum(1 for v in w.values() if v < 1)} roots, {sum(1 for v in w.values() if v == 0)} removed')

# ---- pupils ----------------------------------------------------------------------------------------------------------------
def pupil_keys(eye):
    """The HG pupil is a real hole in the iris mesh (r about 1.45 mm, probe 27 Nov). Shape key 'ep11_conR' pulls his right
    iris in radially: rim r0 -> r0 * PUP_CON, iris edge fixed, the cone depth unchanged (the iris texture stretches with it)."""
    me = eye.data; inner = [i for i, m in enumerate(me.materials) if m and m.name.startswith('.HG_Eyes_Inner')]
    if not inner: print('ep11 pupil: no inner material'); return
    if me.shape_keys is None: eye.shape_key_add(name='Basis', from_mix=False)
    sk = eye.shape_key_add(name='ep11_conR', from_mix=False); sk.value = 0.0
    vs = sorted(set(v for po in me.polygons if po.material_index in inner for v in po.vertices))
    R_ = [v for v in vs if me.vertices[v].co.x < 0]          # his right eye (Ben faces -Y, his right is -X)
    cx = sum(me.vertices[v].co.x for v in R_) / len(R_); cz = sum(me.vertices[v].co.z for v in R_) / len(R_)
    ymin = min(me.vertices[v].co.y for v in R_)
    rr = lambda c: ((c.x - cx) ** 2 + (c.z - cz) ** 2) ** 0.5
    front = [v for v in R_ if me.vertices[v].co.y - ymin < 0.003 and rr(me.vertices[v].co) < 0.0062]
    r0 = min(rr(me.vertices[v].co) for v in front); ri = 0.0058; k = PUP_CON; n = 0
    for v in front:
        c = me.vertices[v].co; r = rr(c)
        if r >= ri or r < 1e-6: continue
        rn = r0 * k + (ri - r0 * k) * max(0.0, (r - r0) / (ri - r0)) ** PUP_G; f_ = rn / r     # gamma > 1: the dark ring beside the hole stays thin
        sk.data[v].co = (cx + (c.x - cx) * f_, c.y, cz + (c.z - cz) * f_); n += 1
    R['pupil'] = sk; print(f'ep11 pupil key: right eye rim {r0 * 1000:.2f} mm -> {r0 * k * 1000:.2f} mm, {n} verts moved')

PUP_CON = float(os.environ.get('KW_PC', 0.25)); PUP_G = float(os.environ.get('KW_PG', 1.8))       # his right pupil in the light

# ---- the screen ------------------------------------------------------------------------------------------------------------
SCR_C = (-0.10, 0.17, 2.05)             # world centre (Ben sits at the origin facing -Y; the screen hangs above-behind his right side)
SCR_W, SCR_H = 0.46, 0.2875
def build_screen(rt):
    import bpy, kwlib as L
    c = bpy.data.collections.get('kw_ep11') or bpy.data.collections.new('kw_ep11')
    if c.name not in bpy.context.scene.collection.children: bpy.context.scene.collection.children.link(c)
    tex = os.path.join(HERE, '..', '..', 'assets', 'real', 'tex', 'kw_retina')
    m = bpy.data.materials.new('kw11_screen'); m.use_nodes = True; nt = m.node_tree; N = nt.nodes; N.clear(); Lk = nt.links.new
    out = N.new('ShaderNodeOutputMaterial'); em = N.new('ShaderNodeEmission'); uv = N.new('ShaderNodeTexCoord')
    def img(nm, colour=False):
        n = N.new('ShaderNodeTexImage'); n.image = bpy.data.images.load(os.path.join(tex, nm + '.png'), check_existing=True)
        if not colour: n.image.colorspace_settings.name = 'Non-Color'
        n.interpolation = 'Cubic'; Lk(uv.outputs['UV'], n.inputs['Vector']); return n
    sc, mk, eg = img('scan', True), img('mask'), img('erg')
    def mth(op, a, b=None):
        n = N.new('ShaderNodeMath'); n.operation = op
        for i, v in enumerate((a, b)):
            if v is None: continue
            if isinstance(v, (int, float)): n.inputs[i].default_value = v
            else: Lk(v, n.inputs[i])
        return n.outputs[0]
    smk = N.new('ShaderNodeSeparateColor'); Lk(mk.outputs['Color'], smk.inputs[0])
    seg = N.new('ShaderNodeSeparateColor'); Lk(eg.outputs['Color'], seg.inputs[0])
    tval = N.new('ShaderNodeValue'); tval.name = 'kw11_t'                 # seconds (the pulse phase)
    rev = N.new('ShaderNodeValue'); rev.name = 'kw11_reveal'              # 0..1 across the trace box (ERG drawn left of it)
    # pulse: 1.1 Hz, travelling out from the disc (phase lag 0.35 cycle across the fundus), sharp systolic rise
    ph = mth('SUBTRACT', mth('MULTIPLY', tval.outputs[0], 1.1), mth('MULTIPLY', smk.outputs['Green'], 0.35))
    fr = mth('FRACT', ph); pulse = mth('POWER', mth('SUBTRACT', 1.0, fr), 3.0)          # 1 at the beat, decays over the cycle
    vb = mth('MULTIPLY', mth('MULTIPLY', smk.outputs['Red'], pulse), 0.55)
    gain = mth('ADD', 1.0, vb)
    mul = N.new('ShaderNodeMix'); mul.data_type = 'RGBA'; mul.blend_type = 'MULTIPLY'; mul.inputs['Factor'].default_value = 1.0
    Lk(sc.outputs['Color'], mul.inputs['A'])
    cg = N.new('ShaderNodeCombineColor'); Lk(gain, cg.inputs['Red']); Lk(mth('ADD', 1.0, mth('MULTIPLY', vb, 0.35)), cg.inputs['Green']); Lk(mth('ADD', 1.0, mth('MULTIPLY', vb, 0.25)), cg.inputs['Blue'])
    Lk(cg.outputs[0], mul.inputs['B'])
    # ERG: wave where x < reveal, the flat baseline where x >= reveal (trace box x 890..1490 of 1600)
    su = N.new('ShaderNodeSeparateXYZ'); Lk(uv.outputs['UV'], su.inputs[0])
    xb = mth('DIVIDE', mth('SUBTRACT', su.outputs['X'], 890 / 1600), 600 / 1600)
    drawn = mth('LESS_THAN', xb, rev.outputs[0])
    wave = mth('MULTIPLY', seg.outputs['Red'], drawn)
    base = mth('MULTIPLY', seg.outputs['Green'], mth('SUBTRACT', 1.0, drawn))
    tickv = N.new('ShaderNodeValue'); tickv.name = 'kw11_tick'
    tick = mth('MULTIPLY', seg.outputs['Blue'], tickv.outputs[0])
    c1 = N.new('ShaderNodeMix'); c1.data_type = 'RGBA'; Lk(base, c1.inputs['Factor']); Lk(mul.outputs['Result'], c1.inputs['A']); c1.inputs['B'].default_value = (0.25, 0.32, 0.40, 1)
    c2 = N.new('ShaderNodeMix'); c2.data_type = 'RGBA'; Lk(wave, c2.inputs['Factor']); Lk(c1.outputs['Result'], c2.inputs['A']); c2.inputs['B'].default_value = (0.20, 1.0, 0.72, 1)
    c3 = N.new('ShaderNodeMix'); c3.data_type = 'RGBA'; Lk(tick, c3.inputs['Factor']); Lk(c2.outputs['Result'], c3.inputs['A']); c3.inputs['B'].default_value = (1.0, 0.82, 0.18, 1)
    Lk(c3.outputs['Result'], em.inputs['Color']); em.inputs['Strength'].default_value = float(os.environ.get('KW_SCRE', 1.4))
    Lk(em.outputs[0], out.inputs[0])
    R['scr_nodes'] = (tval, rev, tickv)
    # the monitor: a slim bezel, the lit panel, a swing arm to a pole standing in front of the bed's head end
    cx, cy, cz = SCR_C; tilt = math.radians(-8)
    dark = L.mat('kw11_bezel', (0.035, 0.038, 0.042), 0.35, 0.2)
    steel = L.mat('kw11_steel', (0.72, 0.73, 0.75), 0.3, 1.0)
    bez = L.box('kw11_bezel', (SCR_W + 0.024, 0.03, SCR_H + 0.024), (cx, cy + 0.016, cz), dark, c, 0.008, (math.degrees(tilt), 0, 0))
    bpy.ops.mesh.primitive_plane_add(size=1.0); pl = bpy.context.active_object; pl.name = 'kw11_panel'
    for u_ in list(pl.users_collection): u_.objects.unlink(pl)
    c.objects.link(pl); pl.scale = (SCR_W, SCR_H, 1); pl.rotation_euler = (math.radians(90) + tilt, 0, 0); pl.location = (cx, cy - 0.0005, cz)
    pl.data.materials.append(m)
    for a in ('visible_diffuse', 'visible_glossy', 'visible_transmission'): setattr(pl, a, a == 'visible_glossy')
    L.cyl('kw11_boom', 0.016, 2.80 - cz, (cx, cy + 0.06, (2.80 + cz) / 2), steel, c, (0, 0, 0), 20)     # ceiling boom, hidden behind the panel
    L.box('kw11_mount', (0.12, 0.04, 0.08), (cx, cy + 0.045, cz), dark, c, 0.005)
    R['screen'] = pl

# ---- penlight + beams ------------------------------------------------------------------------------------------------------
TIP = (float(os.environ.get('KW_TIPX', 0.0185)), float(os.environ.get('KW_TIPY', -0.036)), -0.001)      # tip offset from the left eyeball centre (right frame edge in the close)
SWA, SWB = (0.017, -0.013, 0.000), (-0.011, -0.012, 0.0015)           # the beam spot slides from the outer corner across the cornea
REST = (0.0, -0.0125, 0.0008)                                         # ... and rests on the pupil
def build_pen(rt):
    import bpy, kwprops
    c = bpy.data.collections.get('kw_ep11')
    pen = kwprops.penlight(c); pen.set(on=1.0); R['pen'] = pen
    ld = bpy.data.lights.new('kw11_beam', 'SPOT'); ld.spot_size = math.radians(float(os.environ.get('KW_BEAMA', 26))); ld.spot_blend = 1.0
    ld.shadow_soft_size = 0.008; ld.energy = float(os.environ.get('KW_BEAME', 0.9)); ld.color = (1.0, 0.80, 0.56)   # warm, soft falloff (CHECK 1 fix b)
    lo = bpy.data.objects.new('kw11_beam', ld); c.objects.link(lo); R['beam'] = lo
    fd = bpy.data.lights.new('kw11_flash', 'SPOT'); fd.spot_size = math.radians(24); fd.spot_blend = 0.6; fd.shadow_soft_size = 0.004
    fd.energy = 0.0; fd.color = (1.0, 0.96, 0.88)
    fo = bpy.data.objects.new('kw11_flash', fd); c.objects.link(fo); R['flash'] = fo

def build(rt):
    import bpy
    ra = rt.actors[ben]; p = ra.p; hg = p.hg
    eye = next((o for o in hg.meshes if o.name.startswith('HG_Eyes')), None)
    pupil_keys(eye)
    skin_rung4(hg)
    lash_fix(hg)
    import kwlook as Q_; Q_.LOOP_T = FN / FPS
    build_screen(rt); build_pen(rt)
ep.build_hook = build

# ---- per frame -------------------------------------------------------------------------------------------------------------
def gaze_off(f):
    """eye-target offset (m at 0.6 m): micro-saccades at f0..19, small darts later, back to the f0 offset for the loop"""
    if f >= FN - 14: return (0.0, 0.0)
    if f < 30:
        cur = SACC[0][1]
        for f_, o_ in SACC:
            if f >= f_: cur = o_
        if f >= 26: cur = (cur[0] * (1 - (f - 26) / 4), cur[1] * (1 - (f - 26) / 4))
        return cur
    k = int(f // 31); h = (k * 7919) % 7 - 3; v = (k * 104729) % 5 - 2
    return (h * 0.0028, v * 0.0022)

def frame_hook(rt, t):
    import bpy, kwlook as Q_
    Q_.LOOP_T = FN / FPS          # the alive drift repeats on frame FN (= frame 0), so the last frame matches frame 0 exactly
    f = t * FPS; ra = rt.actors[ben]; p = ra.p
    EL, ER = eyeball(rt, 'L'), eyeball(rt, 'R'); Em = (EL + ER) / 2
    # gaze: at the doctor (just right of the lens, where the light comes from), micro-saccades
    go = gaze_off(f); tgt = Em + V((0.10 + go[0], -0.60, 0.015 + go[1]))
    rt.eyes_at(ra, tgt)
    # penlight: tip at the right frame edge in the close, aimed at the beam spot; eased out / back in
    pen = R['pen']; beam = R['beam']
    if f < SW1: aim = V(SWA).lerp(V(SWB), ease((f - SW0) / (SW1 - SW0)))
    elif f < SW1 + 10: aim = V(SWB).lerp(V(REST), ease((f - SW1) / 10))
    else: aim = V(REST)
    if f >= PI0: aim = V(SWA)
    tipw = EL + V(TIP); aimw = EL + aim
    d = (aimw - tipw).normalized()
    out_ = 0.0
    if PX0 <= f < PI1: out_ = ease((f - PX0) / (PX1 - PX0)) if f < PI0 else 1.0 - ease((f - PI0) / (PI1 - PI0))
    if f >= PI1 or f < PX0: out_ = 0.0
    pen_vis = out_ < 0.999 and os.environ.get('KW_PENVIS', '0') == '1'     # CHECK 1 build: the penlight body read as a blob at 25 cm -> light only, the tool stays off-screen
    shift = (-d * 0.16 + V((0.05, -0.02, 0.0))) * out_
    tipw = tipw + shift
    Xa = d; Za = V((0, 0, 1)); Za = (Za - Xa * Za.dot(Xa)).normalized(); Ya = Za.cross(Xa)
    Rm = Matrix((Xa, Ya, Za)).transposed().to_4x4(); tip_l = V(pen.pts['tip'])
    pen.root.matrix_world = Matrix.Translation(tipw - Rm.to_3x3() @ tip_l) @ Rm
    for o in pen.objs: o.hide_render = not pen_vis
    on = 1.0
    if PX0 <= f < PION0 + 6: on = 1.0 - ease((f - PX0 - 6) / 8) if f < PI0 else ease((f - PION0) / 6)
    pen.set(on=on)
    beam.matrix_world = Matrix.Translation(tipw + d * 0.002) @ (d.to_track_quat('-Z', 'Y').to_matrix().to_4x4())
    beam.data.energy = float(os.environ.get('KW_BEAME', 0.9)) * on; beam.hide_render = on <= 1e-3
    # the flash on both eyes (off-screen penlight, from his left and in front)
    fo = R['flash']; fon = max(ease((f - FL0) / 3) * (1 - ease((f - FLA1) / 6)) if FL0 <= f < FLA1 + 6 else 0.0,
              ease((f - FL2) / 3) * (1 - ease((f - FL1) / 6)) if FL2 <= f < FL1 + 6 else 0.0)
    fp = Em + V((0.12, -0.26, 0.03)); fd_ = (Em + V((0, -0.01, 0)) - fp).normalized()
    fo.matrix_world = Matrix.Translation(fp) @ fd_.to_track_quat('-Z', 'Y').to_matrix().to_4x4()
    fo.data.energy = float(os.environ.get('KW_FLASHE', 2.5)) * fon; fo.hide_render = fon <= 1e-3
    # pupils: the new (left) pupil never moves; the right one constricts in the flash and relaxes after
    if 'pupil' in R:
        R['pupil'].value = keys(f, [(0, 0.0), (CON0, 0.0), (CON1, 1.0), (DIL0, 1.0), (DIL1, 0.0)])
    # screen: pulse clock, ERG reveal, flash tick
    tval, rev, tickv = R['scr_nodes']; tval.outputs[0].default_value = f / FPS
    if f < ERG0: rv = 0.0
    else: x_ = min(1.0, (f - ERG0) / 54.0); rv = 0.08 + 0.92 * (1 - (1 - x_) ** 2)
    rev.outputs[0].default_value = rv; tickv.outputs[0].default_value = 1.0 if f >= FL0 else 0.0
    # the kit places labels before the camera moves (one frame late, and wrong on frame 0): place them again on this frame's camera
    if not R.get('refit'):       # the width fit was measured on the stale camera too: measure again on the real one
        R['refit'] = 1
        for it_ in rt.FX.items.values():
            if it_: it_.pop('fit', None)
    bpy.context.view_layer.update(); sh_ = rt.ep.shot_at(t); rt.FX.update(sh_, t - sh_.t, t)
ep.frame_hook = frame_hook

# ---- camera: keys (frame, target offset from the left eyeball, direction target->camera, distance, lens) -------------------
def K(tgt, dirv, dist, lens): return (V(tgt), V(dirv).normalized(), dist, lens)
EYE = lambda: K((0.004, 0.0, 0.004), (0.0, -1.0, 0.016), 0.249, 100.0)
CAMK = None
def cam_keys():
    E0 = EYE()
    FACE = K((-0.031, 0.0, -0.03), (0.0, -1.0, 0.02), 0.72, 85.0)
    MED = K((-0.13, 0.06, 0.02), (0.08, -1.0, 0.03), 1.0, 50.0)
    MED2 = K((-0.08, 0.06, 0.03), (0.04, -1.0, 0.06), 0.95, 50.0)
    SCR = K((-0.135, 0.30, 0.27), (0.10, -1.0, -0.04), 0.86, 40.0)       # the monitor centred, Ben's head just below the frame
    SCR2 = K((-0.135, 0.30, 0.26), (0.07, -1.0, -0.03), 0.80, 40.0)
    EYES = K((-0.0355, 0.0, 0.002), (0.0, -1.0, 0.02), 0.47, 85.0)
    EYEW = K((0.003, 0.0, 0.004), (0.0, -1.0, 0.016), 0.285, 100.0)
    return [(0, E0), (PB0, E0), (PB0 + 40, FACE), (f_nobody - 2, MED), (f_hours + 30, MED2), (f_alive - 20, SCR), (FL0 + 12, SCR2),
            (f_signals + 1, EYES), (f_L5 + 2, EYES), (f_see5 + 14, EYEW), (FN - 30, E0), (FN, E0)]

def cam_fn(rt, t):
    global CAMK
    import bpy
    f = t * FPS; bpy.context.view_layer.update()
    if CAMK is None: CAMK = cam_keys()
    O = eyeball(rt, 'L')
    k1 = next((i for i, k in enumerate(CAMK) if k[0] >= f), len(CAMK) - 1); k0 = max(0, k1 - 1)
    (fa, A), (fb, B) = CAMK[k0], CAMK[k1]
    x = ease((f - fa) / max(1e-6, fb - fa)) if fb > fa else 0.0
    tg = A[0].lerp(B[0], x); dv = A[1].slerp(B[1], x) if hasattr(A[1], 'slerp') else A[1].lerp(B[1], x).normalized()
    dist = A[2] * (B[2] / A[2]) ** x; lens = A[3] * (B[3] / A[3]) ** x
    tgw = O + tg; pos = tgw + dv * dist
    Em = (O + eyeball(rt, 'R')) / 2
    foc = O if dist < 0.36 else Em                     # focus on his eyes always (labels ride at 0.85 x focus: in front of his face)
    fstop = (90.0 if dist < 0.36 else 56.0) if dist < 0.5 else 8.0                # deep focus in the closes: the labels just in front of the eye stay sharp
    R['focd'] = (foc - pos).length
    return pos, tgw, V((0, 0, 1)), lens, fstop, foc
ep.cam_fn = cam_fn

# ---- labels + sounds ---------------------------------------------------------------------------------------------------
YL = dict(color='yellow', size=1.2); Y = 0.86; YB = 0.17
ep.label_outline = True; ep.label_maxw = 820.0; ep.label_lens_fix = True
def camdist(f):
    global CAMK
    if CAMK is None: CAMK = cam_keys()
    k1 = next((i for i, k in enumerate(CAMK) if k[0] >= f), len(CAMK) - 1); k0 = max(0, k1 - 1)
    (fa, A), (fb, B) = CAMK[k0], CAMK[k1]; x = ease((f - fa) / max(1e-6, fb - fa)) if fb > fa else 0.0
    return A[2] * (B[2] / A[2]) ** x
ep.label_dk = lambda f: (camdist(f) - 0.05) if camdist(f) < 0.36 else None     # closes: the word rides 11 mm in front of the eye (sharp at f/40)
labels = [KW.fx.label('HIS NEW EYE', at=-1.0, pos=(0.5, Y), dur=1.0 + (PB0 - 4) * F, **YL),          # opening rule (3): the title promise on frame 0
          KW.fx.label('WORLD FIRST', at=(f_nobody + 4) * F, pos=(0.5, YB), dur=(fl(2) - 8 - f_nobody) * F, **YL),
          KW.fx.counter(0, 21, 'HOURS', at=(f_hours - 3) * F, dur=0.8, pos=(0.5, YB), size=1.0, color='yellow'),
          KW.fx.label('BLOOD FLOW', at=f_blood * F, pos=(0.5, YB), dur=(FL0 + 6 - f_blood) * F, **YL),
          KW.fx.label('SIGNALS', at=f_signals * F, pos=(0.5, YB), dur=(f_L5 - 6 - f_signals) * F, **YL),
          KW.fx.label('NO SIGHT', at=f_cant * F, pos=(0.5, Y), dur=(f_L6 - 4 - f_cant) * F, **YL),
          KW.fx.label('WOULD YOU TAKE IT?', at=CTA0 * F, pos=(0.5, 0.62), dur=(FN - 10 - CTA0) * F, **YL),
          KW.fx.label('COMMENT BELOW', at=(CTA0 + 3) * F, pos=(0.5, 0.575), dur=(FN - 13 - CTA0) * F, color='white', size=0.125),
          KW.fx.label('HIS NEW EYE', at=(FN - 9) * F, pos=(0.5, Y), dur=2.0, **YL)]
labels[-1].o['nopop'] = True
labels[2].o['end'] = CNT_END * F
ep.sound(0.0, 'thud', 0.6)
for f_ in (f_nobody + 4, f_blood, f_signals, f_cant): ep.sound(f_ * F, 'thud', 0.45)
ep.sound(FL0 * F, 'tick', 0.4); ep.sound(FL2 * F, 'tick', 0.4)     # penlight clicks
ep.mouth_fix = True; ep.eyes_fix = True; ep.relight_after_pose = True
ep.shot(0.0, 'eye', set='hospital', cast={ben: P}, fx=labels, cam=KW.cam.face(ben))
ep.run()
