"""kwbody - x-ray glass body + organ kit + macro tissue sets for kwkit.  Built procedurally (no external assets).

Organs are built at the rest pose (person at the origin facing -Y) from measured bone / mesh points and parented to
bones, so they follow every pose.  Paths (for fx.flow) are lists of (bone, bone-local point) evaluated live.
"""
import bpy, math, random
from mathutils import Vector as V, Matrix
import kwlib as L

XRAY_BODY = ((0.15, 0.75, 1.0), 2.2, 0.03, 0.42)     # ep_sneeze glass-body look
PATHS = ('air_out_nose', 'air_out_mouth', 'air_in', 'nose_to_sinus', 'sinus_to_eye', 'food_down', 'blood_heart', 'brain_blood')
COLORS = {'green': (0.55, 1.0, 0.05), 'red': (1.0, 0.08, 0.03), 'blue': (0.1, 0.45, 1.0), 'yellow': (1.0, 0.85, 0.05),
          'white': (0.9, 0.95, 1.0), 'orange': (1.0, 0.42, 0.02)}

def organ_mat(name, col, es=0.7, rough=0.25, sss=0.3, coat=0.5, bump=None):
    m = L.mat(name, col, rough, emit=col, es=es, sss=sss, coat=coat)
    if bump: L.bumpy(m, *bump)
    return m

class Body:
    """all x-ray anatomy of one person"""
    def __init__(self, rt, ra):
        self.rt, self.ra = rt, ra; p = ra.p; self.p = p
        self.coll = L.coll(f'kw_xray_{p.name}')
        self.organs = {}        # name -> list of objects
        self.base = {}          # obj -> (scale, bevel)
        self.mats = {}          # organ -> list of (principled or emission node, base strength)
        self.anchor = {}        # organ -> (bone, local point)
        self.paths = {}
        self.points = {}        # named rest-pose points (world == rest)
        self.xmat, self.xem = L.glow(f'kw_xray_body_{p.name}', *XRAY_BODY)
        self.orig = [s.material for s in p.body.material_slots]
        self._build()

    # ------------------------------------------------------------------ helpers
    def bw(self, b, tail=False): return self.rt.bw(self.p, b, tail)
    def local(self, bone, w):
        return self.rt.wmat(self.p, bone).inverted() @ V(w)
    def add(self, organ, o, bone):
        L.into(self.coll, [o]); L.bone_parent(o, self.p.rig, bone); self.organs.setdefault(organ, []).append(o)
        bev = o.data.bevel_depth if o.type == 'CURVE' else None
        self.base[o] = (tuple(o.scale), bev); return o
    def reg_mat(self, organ, m):
        n = m.node_tree.nodes.get('Principled BSDF')
        if n: self.mats.setdefault(organ, []).append((n.inputs['Emission Strength'], n.inputs['Emission Strength'].default_value, n.inputs['Emission Color']))
        else:
            em = next(x for x in m.node_tree.nodes if x.type == 'EMISSION')
            self.mats.setdefault(organ, []).append((em.inputs['Strength'], em.inputs['Strength'].default_value, em.inputs['Color']))
        return m
    def set_anchor(self, organ, bone, w): self.anchor[organ] = (bone, self.local(bone, w))
    def path(self, name, pts):
        self.paths[name] = [(b, self.local(b, w)) for b, w in pts]

    # ------------------------------------------------------------------ build
    def _build(self):
        rt, ra, p = self.rt, self.ra, self.p
        rt.reset(p); rt.rig_at(p, (0, 0, 0), 0); bpy.context.view_layer.update()
        F = V((0, -1, 0)); Lf = V((1, 0, 0)); U = V((0, 0, 1))
        pw = lambda n: rt.part_world(ra, n)[0]
        head = self.bw('head'); nose = pw('nose'); mouth = pw('mouth'); eyeL, eyeR = self.bw('eye.L'), self.bw('eye.R')
        n1, n2 = self.bw('neck01'), self.bw('neck02'); s1, s2, s3, s4, s5 = [self.bw(f'spine0{i}') for i in range(1, 6)]
        chest = pw('chest'); belly = pw('belly')
        depth_c = (chest.y - s2.y)            # negative (front is -Y)
        tr_top = n2 + F * 0.045; tr_bot = n1 + F * 0.04 - U * 0.09
        ph = head + F * 0.035 - U * 0.05; nb = head + F * 0.045 + U * 0.005
        nostril = nose + V((0, 0.012, -0.012)); lips = mouth + V((0, 0.012, 0))
        P = self.points = dict(head=head, nose=nose, mouth=mouth, eyeL=eyeL, eyeR=eyeR, tr_top=tr_top, tr_bot=tr_bot, ph=ph, nb=nb, nostril=nostril, lips=lips)
        # --- airway (windpipe, throat, nose and mouth channels)
        air_wall = self.reg_mat('airway', organ_mat('kw_airway', (0.95, 0.42, 0.45), 0.6))
        ring = organ_mat('kw_ring', (0.98, 0.93, 0.85), 0.5)
        self.add('airway', L.tube('x_trachea', [tr_bot, tr_top, ph], 0.0105, air_wall), 'neck01')
        self.add('airway', L.tube('x_oral', [ph, ph.lerp(lips, 0.5) + U * 0.004, lips], 0.0105, air_wall), 'head')
        self.add('airway', L.tube('x_nasal', [ph, nb, nb.lerp(nostril, 0.55) + U * 0.012, nostril], 0.0065, air_wall), 'head')
        d = (tr_top - tr_bot).normalized()
        for k in range(7):
            o = L.prim('torus', f'x_ring{k}', ring, None, major_radius=0.0115, minor_radius=0.0022, location=tr_bot.lerp(tr_top, 0.08 + k * 0.13), major_segments=24, minor_segments=8)
            o.rotation_euler = d.to_track_quat('Z', 'Y').to_euler(); L.smooth(o); self.add('airway', o, 'neck01')
        self.set_anchor('airway', 'neck02', tr_top.lerp(ph, 0.4))
        # --- lungs
        lung_m = self.reg_mat('lungs', organ_mat('kw_lungs', (1.0, 0.36, 0.22), 0.7, 0.3, 0.3, 0.4, (55, 0.5)))
        lc = []
        for sx in (-1, 1):
            c = tr_bot + V((sx * 0.082, 0.03, -0.105)); lc.append(c)
            o = L.sphere(f'x_lung{sx}', 1, c, lung_m, None, 40, 20, (0.062, 0.06, 0.125))
            tx = bpy.data.textures.new(f'kw_lt{sx}', 'CLOUDS'); tx.noise_scale = 0.9; dm = o.modifiers.new('d', 'DISPLACE'); dm.texture = tx; dm.strength = 0.22; dm.texture_coords = 'GLOBAL'
            self.add('lungs', o, 'spine02')
            self.add('lungs', L.tube(f'x_bronch{sx}', [tr_bot, tr_bot + V((sx * 0.035, 0.01, -0.03)), c + V((-sx * 0.015, -0.02, 0.05))], 0.0065, air_wall), 'spine02')
        self.set_anchor('lungs', 'spine02', (lc[0] + lc[1]) / 2)
        P['lungL'], P['lungR'] = lc[1], lc[0]
        # --- esophagus + stomach
        es_m = self.reg_mat('esophagus', organ_mat('kw_esoph', (0.95, 0.55, 0.45), 0.6, 0.3, 0.3, 0.5))
        st_c = belly + V((0.05, 0.035, 0.07))
        es_pts = [ph - U * 0.01 + V((0, 0.012, 0)), tr_top + V((0, 0.018, 0)), tr_bot + V((0, 0.02, 0)), s2 + V((0.004, -0.02, 0)), st_c + V((-0.03, 0.0, 0.06))]
        self.add('esophagus', L.tube('x_esoph', es_pts, 0.0085, es_m), 'spine02')
        self.set_anchor('esophagus', 'spine02', es_pts[2].lerp(es_pts[3], 0.5))
        stm = self.reg_mat('stomach', organ_mat('kw_stomach', (1.0, 0.45, 0.35), 0.7, 0.3, 0.4, 0.5, (30, 0.3)))
        o = L.sphere('x_stomach', 1, st_c, stm, None, 32, 16, (0.075, 0.045, 0.055)); o.rotation_euler = (0, math.radians(-25), 0)
        self.add('stomach', o, 'spine04'); self.set_anchor('stomach', 'spine04', st_c); P['stomach'] = st_c; P['es_pts'] = es_pts
        # --- heart + vessels
        hc = chest + V((0.025, 0.06, -0.02))
        hm = self.reg_mat('heart', organ_mat('kw_heart', (0.95, 0.06, 0.06), 1.0, 0.25, 0.3, 0.6, (20, 0.4)))
        o = L.sphere('x_heart', 1, hc, hm, None, 32, 16, (0.05, 0.042, 0.06)); o.rotation_euler = (0, math.radians(-30), math.radians(20))
        self.add('heart', o, 'spine02'); self.set_anchor('heart', 'spine02', hc); P['heart'] = hc
        vm = self.reg_mat('vessels', organ_mat('kw_vessel', (0.95, 0.08, 0.06), 0.9, 0.2, 0.2, 0.7))
        vb = self.reg_mat('vessels', organ_mat('kw_vein', (0.1, 0.25, 0.95), 0.9, 0.2, 0.2, 0.7))
        arch = hc + U * 0.06 + V((0, 0.01, 0))
        car = {}
        for sx in (1, -1):
            a0 = arch + V((sx * 0.012, 0, 0.02)); a1 = n1 + V((sx * 0.025, -0.02, 0)); a2 = n2 + V((sx * 0.03, -0.01, 0)); a3 = head + V((sx * 0.03, 0.0, 0.0))
            car[sx] = [hc, arch, a0, a1, a2, a3]
            self.add('vessels', L.tube(f'x_carotid{sx}', [arch, a0, a1, a2, a3], 0.0045, vm), 'neck01')
            self.add('vessels', L.tube(f'x_jugular{sx}', [hc + V((sx * 0.03, 0.0, 0.05)), a1 + V((sx * 0.02, 0.005, 0)), a2 + V((sx * 0.024, 0.006, 0)), a3 + V((sx * 0.02, 0.01, 0))], 0.005, vb), 'neck01')
        self.add('vessels', L.tube('x_aorta', [hc, arch, arch + V((-0.01, 0.03, 0)), s3 + V((-0.01, -0.02, 0)), s5 + V((0, -0.03, 0))], 0.008, vm), 'spine02')
        self.set_anchor('vessels', 'neck01', n1 + F * 0.01); P['carotid'] = car
        # --- brain + skull + orbits + eyes + sinus
        bc = head + U * 0.085 + V((0, 0.005, 0))
        bm = self.reg_mat('brain', organ_mat('kw_brain', (1.0, 0.55, 0.65), 0.8, 0.35, 0.4, 0.3))
        for sx in (1, -1):
            o = L.sphere(f'x_brain{sx}', 1, bc + V((sx * 0.033, 0, 0)), bm, None, 40, 20, (0.034, 0.08, 0.06))
            tx = bpy.data.textures.new(f'kw_gyri{sx}', 'VORONOI'); tx.noise_scale = 0.015; dm = o.modifiers.new('d', 'DISPLACE'); dm.texture = tx; dm.strength = 0.006; dm.texture_coords = 'GLOBAL'
            ss = o.modifiers.new('s', 'SUBSURF'); ss.levels = 0; ss.render_levels = 1
            o.modifiers.move(1, 0); self.add('brain', o, 'head')
        self.set_anchor('brain', 'head', bc); P['brain'] = bc
        sk_m, sk_em = L.glow('kw_skull', (0.95, 0.95, 1.0), 2.4, 0.04, 0.3); self.reg_mat('skull', sk_m)
        o = L.sphere('x_cranium', 1, bc + V((0, 0.0, -0.005)), sk_m, None, 40, 20, (0.078, 0.1, 0.085)); self.add('skull', o, 'head')
        rim = self.reg_mat('skull', organ_mat('kw_orbit', (1.0, 0.97, 0.9), 1.4, 0.3, 0.0, 0.3))
        ey_m = self.reg_mat('eyes', organ_mat('kw_xeye', (0.95, 0.97, 1.0), 0.9, 0.2, 0.2, 0.8))
        ir_m = organ_mat('kw_xiris', (0.1, 0.5, 1.0), 2.0)
        for nm, e, sx in (('L', eyeL, 1), ('R', eyeR, -1)):
            ec = e + F * 0.002
            o = L.prim('torus', f'x_orbit{nm}', rim, None, major_radius=0.02, minor_radius=0.0028, location=ec + F * 0.006, major_segments=32, minor_segments=8)
            o.rotation_euler = (math.radians(90), 0, 0); o.scale = (1.05, 1, 0.95); L.smooth(o); self.add('skull', o, 'head')
            o = L.sphere(f'x_eyeball{nm}', 0.0125, ec + V((0, 0.012, 0)), ey_m, None, 24, 12); self.add('eyes', o, f'eye.{nm}')
            o = L.sphere(f'x_iris{nm}', 0.0055, ec + V((0, 0.0005, 0)), ir_m, None, 16, 8, (1, 0.35, 1)); self.add('eyes', o, f'eye.{nm}')
        # (no jaw tube: every version floated outside the glass face as a hose-like loop under the chin -- LESSON, removed)
        self.set_anchor('eyes', 'head', (eyeL + eyeR) / 2 + F * 0.005); self.set_anchor('skull', 'head', bc - U * 0.03)
        # sinuses: ethmoid air cells between the eyes (the thin wall = lamina papyracea), maxillary under each eye
        sn = self.reg_mat('sinus', organ_mat('kw_sinus', (0.25, 0.95, 1.0), 1.3, 0.2, 0.2, 0.6))
        mid = (eyeL + eyeR) / 2
        for nm, e, sx in (('L', eyeL, 1), ('R', eyeR, -1)):
            ce = mid.lerp(e, 0.45) + V((0, 0.012, -0.004))
            o = L.sphere(f'x_ethmoid{nm}', 1, ce, sn, None, 24, 12, (0.0055, 0.016, 0.011)); self.add('sinus', o, 'head')
            cm = e + V((sx * 0.002, 0.012, -0.03))
            o = L.sphere(f'x_maxill{nm}', 1, cm, sn, None, 24, 12, (0.016, 0.017, 0.014)); self.add('sinus', o, 'head')
            P['eth' + nm] = ce; P['max' + nm] = cm
            P['wall' + nm] = mid.lerp(e, 0.62) + V((0, 0.012, -0.002))          # medial orbit wall point
            P['lid' + nm] = e + V((0, -0.008, -0.005))
        self.set_anchor('sinus', 'head', P['ethL'].lerp(P['ethR'], 0.5) + V((0, 0.01, -0.01)))
        # --- intestines (loops), liver, kidneys, bladder
        im = self.reg_mat('intestines', organ_mat('kw_gut', (1.0, 0.6, 0.45), 0.7, 0.3, 0.4, 0.5))
        ic = belly + V((0, 0.05, -0.06)); pts = []
        for k in range(36):
            a = k * 0.85; r = 0.05 + 0.025 * math.sin(k * 0.37)
            pts.append(ic + V((r * math.cos(a) * 1.25, 0.02 * math.sin(a * 1.7), -0.045 + 0.09 * k / 35 + 0.012 * math.sin(a))))
        self.add('intestines', L.tube('x_small_int', pts, 0.0085, im, res=4), 'spine05')
        self.add('intestines', L.tube('x_colon', [ic + V((-0.1, 0, -0.07)), ic + V((-0.11, 0, 0.07)), ic + V((0.0, -0.01, 0.1)), ic + V((0.11, 0, 0.07)), ic + V((0.1, 0, -0.07))], 0.016, im), 'spine05')
        self.set_anchor('intestines', 'spine05', ic); P['gut'] = pts
        lm = self.reg_mat('liver', organ_mat('kw_liver', (0.55, 0.08, 0.06), 0.7, 0.3, 0.3, 0.5))
        o = L.sphere('x_liver', 1, belly + V((-0.055, 0.04, 0.11)), lm, None, 32, 16, (0.085, 0.05, 0.042)); o.rotation_euler = (0, math.radians(12), 0)
        self.add('liver', o, 'spine03'); self.set_anchor('liver', 'spine03', belly + V((-0.055, 0.04, 0.11)))
        km = self.reg_mat('kidneys', organ_mat('kw_kidney', (0.75, 0.12, 0.1), 0.8, 0.3, 0.3, 0.5))
        for sx in (1, -1):
            o = L.sphere(f'x_kidney{sx}', 1, s4 + V((sx * 0.06, -0.02, 0.03)), km, None, 24, 12, (0.022, 0.018, 0.04)); self.add('kidneys', o, 'spine04')
        self.set_anchor('kidneys', 'spine04', s4 + V((0, -0.02, 0.03)))
        blm = self.reg_mat('bladder', organ_mat('kw_bladder', (1.0, 0.85, 0.2), 0.8, 0.25, 0.3, 0.5))
        bp = s5 + V((0, -0.07, -0.07)); o = L.sphere('x_bladder', 0.032, bp, blm, None, 24, 12); self.add('bladder', o, 'spine05'); self.set_anchor('bladder', 'spine05', bp)
        # --- flow paths
        out_n = nostril + V((0, -0.14, -0.03)); out_m = lips + V((0, -0.16, -0.02))
        H = 'head'; N1 = 'neck01'; S2 = 'spine02'
        self.path('air_out_nose', [(S2, lc[0]), (N1, tr_bot), (N1, tr_top), (H, ph), (H, nb), (H, nostril), (H, out_n)])
        self.path('air_out_mouth', [(S2, lc[1]), (N1, tr_bot), (N1, tr_top), (H, ph), (H, ph.lerp(lips, 0.5)), (H, lips), (H, out_m)])
        self.path('air_in', [(H, out_n), (H, nostril), (H, nb), (H, ph), (N1, tr_top), (N1, tr_bot), (S2, lc[0])])
        self.path('nose_to_sinus', [(N1, tr_bot), (N1, tr_top), (H, ph), (H, nb), (H, nb.lerp(nostril, 0.45) + U * 0.012), (H, P['ethL'])])
        self.path('nose_to_sinus_r', [(N1, tr_bot), (N1, tr_top), (H, ph), (H, nb), (H, nb.lerp(nostril, 0.45) + U * 0.012), (H, P['ethR'])])
        self.path('sinus_to_eye', [(H, P['ethL']), (H, P['wallL']), (H, eyeL + V((0.004, -0.004, -0.012))), (H, P['lidL'])])
        self.path('sinus_to_eye_r', [(H, P['ethR']), (H, P['wallR']), (H, eyeR + V((-0.004, -0.004, -0.012))), (H, P['lidR'])])
        self.path('food_down', [(H, lips), (H, ph.lerp(lips, 0.5)), (H, ph)] + [(S2, q) for q in es_pts[1:]] + [(S2, st_c)])
        self.path('blood_heart', [(S2, hc)] + [(N1, q) for q in car[1][1:]])
        self.path('brain_blood', [(N1, q) for q in car[1][2:]] + [(H, bc + V((0.02, 0, 0))), (H, bc + V((0.0, -0.04, 0.03))), (H, bc + V((-0.03, 0.03, 0.02)))])
        # orbit-wall crack points (for fx.crack_line): zigzag on the medial wall of each socket, facing the camera side
        for nm in 'LR':
            w = P['wall' + nm]; sx = 1 if nm == 'L' else -1
            zz = [w + V((sx * 0.0015 * ((-1) ** k), -0.004, 0.012 - 0.024 * k / 6)) for k in range(7)]
            self.points['crack' + nm] = zz
        self.coll.hide_render = True

    # ------------------------------------------------------------------ live queries
    def world(self, bone, lp): return self.rt.wmat(self.p, bone) @ lp
    def organ_point(self, organ):
        b, lp = self.anchor[organ]; return self.world(b, lp)
    def path_world(self, name):
        if name not in self.paths: raise ValueError(f'unknown flow path {name!r}; valid: {", ".join(self.paths)}')
        return [self.world(b, lp) for b, lp in self.paths[name]]
    def show(self, on, organs=()):
        self.coll.hide_render = not on
        for nm, objs in self.organs.items():
            h = not (on and nm in organs)
            for o in objs:
                if o.hide_render != h: o.hide_render = h
        for i, s in enumerate(self.p.body.material_slots):
            m = self.xmat if on else self.orig[i]
            if s.material is not m: s.material = m
    def reset_fx(self):
        for o, (sc, bev) in self.base.items():
            o.scale = sc
            if bev is not None: o.data.bevel_depth = bev
        for nm, lst in self.mats.items():
            for sock, base, col in lst: sock.default_value = base
    def heat(self, organ, k, pulse, swell, color=None):
        """organ glows hotter / swells; k 0..1"""
        for sock, base, col in self.mats.get(organ, []):
            sock.default_value = base + k * (2.5 + 2.0 * pulse)
        for o in self.organs.get(organ, []):
            sc, bev = self.base[o]; f = 1 + swell * k * (0.6 + 0.4 * pulse)
            if bev is not None: o.data.bevel_depth = bev * f
            else: o.scale = tuple(x * f for x in sc)


# ====================================================================================== macro sets
TUBE_KINDS = {   # radius, wall colour, band colour, band period (0 = none), inner colour, has cartilage rings
    'windpipe': (0.35, (0.85, 0.3, 0.33), (0.97, 0.86, 0.78), 0.18, (0.45, 0.03, 0.05)),
    'esophagus': (0.33, (0.85, 0.42, 0.38), (0.92, 0.55, 0.5), 0.0, (0.55, 0.08, 0.1)),
    'artery': (0.3, (0.75, 0.04, 0.05), (0.9, 0.2, 0.2), 0.0, (0.35, 0.0, 0.02)),
    'vein': (0.32, (0.15, 0.2, 0.7), (0.3, 0.35, 0.85), 0.0, (0.1, 0.02, 0.2)),
    'intestine': (0.34, (0.95, 0.55, 0.45), (1.0, 0.72, 0.6), 0.32, (0.6, 0.15, 0.12)),
    'stomach': (0.45, (0.9, 0.45, 0.4), (1.0, 0.62, 0.55), 0.0, (0.55, 0.1, 0.1)),
    'nerve': (0.25, (0.98, 0.9, 0.55), (1.0, 0.97, 0.75), 0.06, (0.9, 0.7, 0.3)),
    'sinus': (0.4, (0.95, 0.55, 0.55), (1.0, 0.75, 0.7), 0.0, (0.6, 0.15, 0.15)),
}

class Macro:
    def __init__(self, rt, m, idx):
        self.rt, self.m = rt, m; self.kind = m.kind
        self.M0 = V((30 + 12 * idx, 0, 1.0)); self.coll = L.coll(f'kw_macro{idx}_{m.kind}'); self.rnd = random.Random(11 + idx)
        self.objs = []; self.block = None
        (self._bone if m.kind == 'bone' else self._tube)()
        self._common()
        self.coll.hide_render = True

    def _tube(self):
        M0 = self.M0; R, wc, bc, per, ic = TUBE_KINDS[self.kind]
        wall = L.mat(f'kw_m_wall{self.m.idx}', wc, 0.16, sss=0.4, coat=0.7); nt = wall.node_tree; pb = nt.nodes['Principled BSDF']
        tc = nt.nodes.new('ShaderNodeTexCoord'); sx = nt.nodes.new('ShaderNodeSeparateXYZ'); nt.links.new(tc.outputs['Object'], sx.inputs[0])
        cr = nt.nodes.new('ShaderNodeValToRGB'); cr.color_ramp.elements[0].position = 0.25; cr.color_ramp.elements[0].color = (*wc, 1); cr.color_ramp.elements[1].position = 0.8; cr.color_ramp.elements[1].color = (*bc, 1)
        if per:
            m1 = nt.nodes.new('ShaderNodeMath'); m1.operation = 'MULTIPLY'; m1.inputs[1].default_value = 2 * math.pi / per; m2 = nt.nodes.new('ShaderNodeMath'); m2.operation = 'COSINE'
            nt.links.new(sx.outputs['X'], m1.inputs[0]); nt.links.new(m1.outputs[0], m2.inputs[0]); nt.links.new(m2.outputs[0], cr.inputs['Fac'])
        else:
            nz0 = nt.nodes.new('ShaderNodeTexNoise'); nz0.inputs['Scale'].default_value = 3.5; nz0.inputs['Detail'].default_value = 3; nt.links.new(tc.outputs['Object'], nz0.inputs['Vector']); nt.links.new(nz0.outputs['Fac'], cr.inputs['Fac'])
        nt.links.new(cr.outputs['Color'], pb.inputs['Base Color'])
        nz = nt.nodes.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 22; nz.inputs['Detail'].default_value = 5; bp = nt.nodes.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.35; bp.inputs['Distance'].default_value = 0.03
        nt.links.new(tc.outputs['Object'], nz.inputs['Vector']); nt.links.new(nz.outputs['Fac'], bp.inputs['Height']); nt.links.new(bp.outputs['Normal'], pb.inputs['Normal'])
        inner = L.mat(f'kw_m_inner{self.m.idx}', ic, 0.25, coat=0.5)
        me = bpy.data.meshes.new('m_tube'); vs = []; fs = []; NA, NL = 96, 160
        for j in range(NL + 1):
            x = -1.6 + 3.2 * j / NL
            for i in range(NA):
                a = 2 * math.pi * i / NA; rr = R + (0.016 * max(0.0, math.cos(2 * math.pi * (x - 0.09) / per)) ** 2 if per else 0.006 * math.sin(a * 5 + x * 7))
                vs.append((x, rr * math.sin(a), rr * math.cos(a)))
        for j in range(NL):
            for i in range(NA): fs.append((j * NA + i, j * NA + (i + 1) % NA, (j + 1) * NA + (i + 1) % NA, (j + 1) * NA + i))
        me.from_pydata(vs, [], fs); t = bpy.data.objects.new(f'kw_m_tube{self.m.idx}', me); self.coll.objects.link(t); t.location = M0; t.data.materials.append(wall); L.smooth(t)
        so = t.modifiers.new('s', 'SOLIDIFY'); so.thickness = 0.05; t.data.materials.append(inner); so.material_offset = 1
        self.HOLE = M0 + V((0, -R - 0.01, 0.0)); self.R = R
        cut = L.ico(f'kw_m_cut{self.m.idx}', 1, self.HOLE, None, self.coll, 4); cut.display_type = 'WIRE'; cut.hide_render = True
        ctx = bpy.data.textures.new('kw_cut_t', 'CLOUDS'); ctx.noise_scale = 0.45; cdm = cut.modifiers.new('d', 'DISPLACE'); cdm.texture = ctx; cdm.strength = 0.9
        bo = t.modifiers.new('cut', 'BOOLEAN'); bo.object = cut; bo.operation = 'DIFFERENCE'; bo.solver = 'FAST'
        ss = t.modifiers.new('sub', 'SUBSURF'); ss.levels = 0; ss.render_levels = 1
        self.tube, self.cut = t, cut; self.cut_open = (0.105, 0.14, 0.062); self.cut.scale = (0.0005, 0.14, 0.0005)
        # surroundings: muscle, vessels, fat (ep_sneeze look)
        rnd = self.rnd
        mus = L.bumpy(L.mat(f'kw_m_musc{self.m.idx}', (0.62, 0.05, 0.06), 0.2, sss=0.2, coat=0.6), 60.0, 0.6, 2.0, 0.05, stretch=(0.03, 1, 1))
        for k, (y, z, r) in enumerate(((0.75, 0.45, 0.42), (0.85, -0.5, 0.5), (0.2, -0.95, 0.36))):
            self.objs.append(L.cyl(f'kw_m_mus{k}', r, 5.0, M0 + V((0, y + R - 0.35, z)), mus, self.coll, (0, 90, 0), 48))
        vm = L.mat('kw_m_vein', (0.03, 0.12, 0.75), 0.15, coat=0.8); am = L.mat('kw_m_art', (0.85, 0.03, 0.04), 0.15, coat=0.8)
        L.tube('kw_m_v', [M0 + V((-2.4, -0.2, R + 0.27)), M0 + V((-0.8, -0.12, R + 0.21)), M0 + V((0.8, -0.2, R + 0.25)), M0 + V((2.4, -0.1, R + 0.31))], 0.075, vm, self.coll, 8)
        L.tube('kw_m_a', [M0 + V((-2.4, -0.25, -R - 0.25)), M0 + V((-0.7, -0.3, -R - 0.2)), M0 + V((0.9, -0.22, -R - 0.25)), M0 + V((2.4, -0.3, -R - 0.21))], 0.065, am, self.coll, 8)
        fat = L.bumpy(L.mat('kw_m_fat', (1.0, 0.78, 0.2), 0.25, sss=0.5, coat=0.5), 8.0, 0.4)
        for i in range(16):
            L.sphere(f'kw_m_fat{i}', rnd.uniform(0.1, 0.2), M0 + V((rnd.uniform(-2.0, 2.0), rnd.uniform(0.15, 0.6), rnd.choice((-1, 1)) * rnd.uniform(R + 0.4, R + 0.8))), fat, self.coll, 20, 10, (1.2, 1.0, 0.8))
        self.block_pt = M0 + V((0.25, 0, 0))

    def _bone(self):
        """thin curved porous bone plate (eye-socket wall). Camera side (-Y) = the eye socket: fat + eyeball. Behind = sinus air cells."""
        M0 = self.M0; rnd = self.rnd; i_ = self.m.idx
        bm = L.mat(f'kw_m_bone{i_}', (0.8, 0.64, 0.46), 0.45, sss=0.08, coat=0.15); nt = bm.node_tree; pb = nt.nodes['Principled BSDF']   # LESSON: the paler cream + sss 0.25 washed out to white under the macro lights
        vo = nt.nodes.new('ShaderNodeTexVoronoi'); vo.inputs['Scale'].default_value = 14; cr = nt.nodes.new('ShaderNodeValToRGB')
        cr.color_ramp.elements[0].position = 0.05; cr.color_ramp.elements[0].color = (0.38, 0.16, 0.1, 1); cr.color_ramp.elements[1].position = 0.22; cr.color_ramp.elements[1].color = (0.82, 0.66, 0.48, 1)
        nt.links.new(vo.outputs['Distance'], cr.inputs['Fac']); nt.links.new(cr.outputs['Color'], pb.inputs['Base Color'])
        bp = nt.nodes.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.6; bp.inputs['Distance'].default_value = 0.03; nt.links.new(vo.outputs['Distance'], bp.inputs['Height']); nt.links.new(bp.outputs['Normal'], pb.inputs['Normal'])
        me = bpy.data.meshes.new('m_plate'); vs = []; fs = []; NX, NZ = 120, 80
        for j in range(NZ + 1):
            z = -1.2 + 2.4 * j / NZ
            for i in range(NX + 1):
                x = -1.8 + 3.6 * i / NX; y = 0.12 * (x / 1.8) ** 2 * 2 + 0.06 * (z / 1.2) ** 2 + 0.015 * math.sin(x * 5 + z * 3)
                vs.append((x, y, z))
        for j in range(NZ):
            for i in range(NX): fs.append((j * (NX + 1) + i, j * (NX + 1) + i + 1, (j + 1) * (NX + 1) + i + 1, (j + 1) * (NX + 1) + i))
        me.from_pydata(vs, [], fs); t = bpy.data.objects.new(f'kw_m_plate{i_}', me); self.coll.objects.link(t); t.location = M0; t.data.materials.append(bm); L.smooth(t)
        so = t.modifiers.new('s', 'SOLIDIFY'); so.thickness = 0.035; so.offset = 0
        self.HOLE = M0 + V((0.0, -0.03, 0.05)); self.R = 0.3
        cut = L.ico(f'kw_m_cut{i_}', 1, self.HOLE, None, self.coll, 4); cut.display_type = 'WIRE'; cut.hide_render = True
        ctx = bpy.data.textures.new('kw_crack_t', 'CLOUDS'); ctx.noise_scale = 0.25; cdm = cut.modifiers.new('d', 'DISPLACE'); cdm.texture = ctx; cdm.strength = 1.2
        bo = t.modifiers.new('cut', 'BOOLEAN'); bo.object = cut; bo.operation = 'DIFFERENCE'; bo.solver = 'FAST'
        self.tube, self.cut = t, cut; self.cut_open = (0.34, 0.3, 0.06); cut.scale = (0.0005, 0.2, 0.0005)
        # behind the plate: sinus air cells (pink mucosa honeycomb, dark gaps)
        muc = L.bumpy(L.mat('kw_m_mucosa', (0.9, 0.42, 0.42), 0.2, sss=0.4, coat=0.7), 25.0, 0.3)
        for k in range(26):
            c = M0 + V((rnd.uniform(-2.0, 2.0), rnd.uniform(0.45, 0.8), rnd.uniform(-1.3, 1.3)))
            L.sphere(f'kw_m_cell{k}', 1, c, muc, self.coll, 20, 10, (rnd.uniform(0.18, 0.32),) * 3)
        L.box('kw_m_back', (6, 0.1, 4), M0 + V((0, 1.1, 0)), L.mat('kw_m_dark', (0.25, 0.04, 0.05), 0.4), self.coll, 0)
        # in front: orbital fat blobs low/left + the eyeball edge on the right, a nerve + vessels
        fat = L.bumpy(L.mat('kw_m_ofat', (1.0, 0.8, 0.25), 0.22, sss=0.5, coat=0.6), 8.0, 0.4)
        for k in range(14):
            sd = rnd.choice((-1, 1)); c = M0 + V((rnd.uniform(-2.2, -0.55) if sd < 0 else rnd.uniform(0.7, 2.2), rnd.uniform(-0.45, -0.15), rnd.uniform(-1.2, -0.35) if k % 2 else rnd.uniform(0.45, 1.2)))
            L.sphere(f'kw_m_ofat{k}', rnd.uniform(0.12, 0.24), c, fat, self.coll, 20, 10, (1.2, 0.9, 1.0))
        eye = L.mat('kw_m_eyeball', (0.96, 0.95, 0.93), 0.15, sss=0.3, coat=1.0)
        self.eye = L.sphere('kw_m_eye', 0.95, M0 + V((2.1, -1.0, 0.25)), eye, self.coll, 48, 24)
        L.tube('kw_m_vessel', [M0 + V((-2.4, -0.2, 0.75)), M0 + V((-0.8, -0.12, 0.68)), M0 + V((0.4, -0.16, 0.8)), M0 + V((2.0, -0.3, 0.95))], 0.035, L.mat('kw_m_art2', (0.85, 0.03, 0.04), 0.15, coat=0.8), self.coll, 6)
        L.tube('kw_m_vessel2', [M0 + V((-2.4, -0.15, -0.72)), M0 + V((-0.6, -0.1, -0.62)), M0 + V((0.8, -0.18, -0.7))], 0.028, L.mat('kw_m_vein2', (0.08, 0.15, 0.75), 0.15, coat=0.8), self.coll, 6)
        # crack line (glowing red zigzag growing along x)
        cm, self.crack_em = L.emis('kw_m_crack', (1.0, 0.1, 0.03), 6.0)
        pts = []; x = -0.75
        while x < 0.75:
            pts.append(V((x, -0.025 + 0.1 * (x / 1.8) ** 2 * 2, 0.05 + rnd.uniform(-0.04, 0.04)))); x += rnd.uniform(0.06, 0.12)
        self.crack_pts = [M0 + p for p in pts]
        self.crack = L.tube('kw_m_crackline', self.crack_pts, 0.008, cm, self.coll, 2)
        self.crack.data.bevel_factor_mapping_end = 'SPLINE'; self.crack.data.bevel_factor_start = 0.5; self.crack.data.bevel_factor_end = 0.5
        self.block_pt = M0 + V((0, 0.3, 0))

    def _common(self):
        M0 = self.M0; rnd = self.rnd
        bub = L.mat('kw_m_bubble', (0.95, 0.98, 1.0), 0.03, trans=1.0)
        self.bubbles = [(L.sphere(f'kw_m_bub{i}', 1, M0, bub, self.coll, 20, 10), rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.random(), rnd.uniform(0.02, 0.065)) for i in range(34)]
        jm, _ = L.glow('kw_m_jet', (0.6, 1.0, 0.1), 8.0, 0.97); self.jets = []
        for i in range(46):
            o = L.ico(f'kw_m_jet{i}', 1, M0, jm, self.coll, 2); a = rnd.uniform(-0.5, 0.5); b = rnd.uniform(-0.4, 0.4)
            self.jets.append((o, V((math.sin(a), -math.cos(a) * math.cos(b), math.sin(b))) * rnd.uniform(1.5, 3.6), rnd.uniform(0.012, 0.03), rnd.random() * 0.5))
        fl = bpy.data.lights.new('kw_m_flash', 'POINT'); fl.color = (1, 0.12, 0.08); fl.energy = 0; self.flash = bpy.data.objects.new('kw_m_flash', fl); self.coll.objects.link(self.flash); self.flash.location = self.HOLE + V((0, -0.4, 0))
        # stream particles inside the lumen + blockage objects
        self.stream = [(L.ico(f'kw_m_p{i}', 1, M0, None, self.coll, 2), rnd.random(), rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.uniform(0.6, 1.4)) for i in range(70)]
        self.stream_m = {k: L.mat(f'kw_m_pm_{k}', c, 0.2, emit=c if k in ('air',) else None, es=3.0, coat=0.6) for k, c in (('air', (0.55, 1.0, 0.05)), ('blood', (0.75, 0.02, 0.03)), ('food', (0.8, 0.55, 0.25)), ('acid', (0.7, 1.0, 0.1)), ('bubbles', (0.95, 0.98, 1.0)))}
        for o, *_ in self.stream: o.data.materials.append(self.stream_m['air']); o.scale = (1e-5,) * 3
        self.blocks = {}

    def make_block(self, kind):
        if kind in self.blocks: return self.blocks[kind]
        c = self.coll; p = self.block_pt
        if kind in ('bolus', 'stone', 'clot'):
            col = {'bolus': (0.75, 0.52, 0.25), 'stone': (0.85, 0.78, 0.5), 'clot': (0.35, 0.0, 0.02)}[kind]
            o = L.bumpy(L.mat('kw_m_blk_' + kind, col, 0.5, coat=0.3), 6, 0.6)
            o = L.sphere('kw_m_block_' + kind, 0.22 if kind != 'stone' else 0.15, p, o, c, 32, 16, (1.3, 1.0, 0.95))
            tx = bpy.data.textures.new('kw_blk', 'CLOUDS'); dm = o.modifiers.new('d', 'DISPLACE'); dm.texture = tx; dm.strength = 0.05
        elif kind == 'coin':
            o = L.cyl('kw_m_block_coin', 0.16, 0.025, p, L.mat('kw_m_coin', (0.85, 0.65, 0.3), 0.25, 1.0), c, (0, 70, 0), 48)
        elif kind == 'pill':
            o = L.sphere('kw_m_block_pill', 0.09, p, L.mat('kw_m_pill', (0.95, 0.95, 0.97), 0.3, coat=0.5), c, 24, 12, (2.4, 1, 1))
        elif kind == 'earbud':
            o = L.sphere('kw_m_block_earbud', 0.12, p, L.mat('kw_m_ebud', (0.95, 0.95, 0.95), 0.2, coat=0.8), c, 24, 12, (1.3, 1, 1))
            L.cyl('kw_m_block_ebstem', 0.045, 0.3, p + V((0.18, 0, -0.1)), self.blocks.setdefault('_m', L.mat('kw_m_ebud2', (0.95, 0.95, 0.95), 0.2, coat=0.8)), c, (0, 50, 0))
        elif kind == 'bone':
            o = L.box('kw_m_block_bone', (0.5, 0.06, 0.12), p, L.mat('kw_m_fbone', (0.95, 0.9, 0.78), 0.5), c, 0.02, (0, 25, 15))
        elif kind == 'denture':
            o = L.prim('torus', 'kw_m_block_denture', L.mat('kw_m_dent', (0.98, 0.98, 0.95), 0.2, coat=0.7), c, major_radius=0.17, minor_radius=0.04, location=p); o.scale = (1, 1, 0.5)
        else:   # worm
            pts = [p + V((-0.35 + 0.07 * k, 0.05 * math.sin(k), 0.06 * math.cos(k * 1.3))) for k in range(11)]
            o = L.tube('kw_m_block_worm', pts, 0.03, L.mat('kw_m_worm', (0.9, 0.85, 0.75), 0.4, sss=0.3), c, 4)
        self.blocks[kind] = o; o.hide_render = True; return o

    def reset(self):
        self.cut.scale = (0.0005, self.cut_open[1], 0.0005); self.tube.scale = (1, 1, 1); self.flash.data.energy = 0
        for o, *_ in self.jets: o.scale = (1e-5,) * 3
        for b in self.bubbles: b[0].scale = (1e-5,) * 3
        for o, *_ in self.stream: o.scale = (1e-5,) * 3
        for k, o in self.blocks.items():
            if not k.startswith('_'): o.hide_render = True
        if self.kind == 'bone': self.crack.data.bevel_factor_start = 0.5; self.crack.data.bevel_factor_end = 0.5

    def opened(self, k):
        a, b, c = self.cut_open; self.cut.scale = (a * k + 0.0005, b, c * k + 0.0005)

    def update(self, shot, u, t, ep_shots):
        """apply the macro fx of this shot; the hole state carries over from earlier shots of the same macro set"""
        self.reset(); open_ = 0.0; crack = 0.0
        for s in ep_shots:          # state from earlier shots
            if s.macro is not self.m or s.t >= shot.t: continue
            for f in s.fx:
                if f.kind in ('tear', 'crack'): open_ = 1.0; crack = 1.0
                if f.kind == 'heal': open_ = 0.0; crack = 0.0
        for f in shot.fx:
            o = f.o; at = o.get('at', 0.0)
            if f.kind in ('tear', 'crack'):
                strain = ramp(u, at - 0.9, at) * (1 - ramp(u, at, at + 0.15))
                k = ramp(u, at, at + (0.22 if f.kind == 'tear' else 0.12)); open_ = max(open_, k * o.get('size', 1.0)); crack = max(crack, ramp(u, at - 0.05, at + 0.35))
                wob = 0.05 * strain * (0.7 + 0.3 * math.sin(t * 40))
                self.tube.scale = (1, 1 + wob, 1 + wob) if self.kind != 'bone' else (1, 1 + 3 * wob, 1)
                self.flash.data.energy = 400 * math.exp(-max(0, u - at) * 5) * (u > at)
                for jo, v, r, d in self.jets:
                    dt = u - at - d * 0.5
                    if 0 < dt < 1.2 and f.kind == 'tear': jo.location = self.HOLE + v * dt * 0.8 + V((0, 0, 0.3 * dt * dt)); jo.scale = (r * (1 - dt / 1.2),) * 3
                    elif 0 < dt < 0.8 and f.kind == 'crack': jo.location = self.HOLE + v * dt * 0.35 + V((0, 0, -0.4 * dt * dt)); jo.scale = (r * 0.5 * (1 - dt / 0.8),) * 3
            elif f.kind == 'heal':
                k = ramp(u, at, at + o.get('dur', 1.0)); open_ *= 1 - k; crack *= 1 - k
            elif f.kind == 'leak':
                rate = o.get('rate', 1.0)
                for bo, ox, oy, ph, r in self.bubbles:
                    s_ = max(0, (u - at - ph * 1.4 / rate)) * 0.6
                    if s_ <= 0: continue
                    bo.location = self.HOLE + V((ox * 0.05 + ox * s_ * 0.7, -s_ * 0.75, oy * 0.03 + s_ * (0.3 + 0.5 * oy) * (0.4 if self.kind == 'bone' else 1))); bo.scale = (r * min(1, s_ * 7),) * 3
            elif f.kind == 'particles':
                m = self.stream_m.get(o.get('kind', 'air'), self.stream_m['air']); n = min(70, int(o.get('count', 60)))
                for i, (po, ph, oy, oz, sp) in enumerate(self.stream):
                    if i >= n: continue
                    if po.data.materials[0] is not m: po.data.materials[0] = m
                    x = ((u - at) * 0.9 * o.get('speed', 1.0) * sp + ph * 3.2) % 3.2 - 1.6
                    stop = self.block_pt.x - self.M0.x - 0.3 if any(g.kind == 'block' for g in shot.fx) else 9
                    x = min(x, stop - 0.05 * ph)
                    rr = self.R * 0.7
                    po.location = self.M0 + V((x, oy * rr * 0.8, oz * rr * 0.8)); po.scale = ((0.025 if o.get('kind') != 'bubbles' else 0.04) * sp,) * 3
            elif f.kind == 'block':
                bo = self.make_block(o.get('obj', 'bolus')); bo.hide_render = False
                bo.location = self.block_pt + V((o.get('move', 0.0) * u, 0, 0))
        self.opened(open_)
        if self.kind == 'bone':
            self.crack.data.bevel_factor_start = 0.5 - 0.5 * crack; self.crack.data.bevel_factor_end = 0.5 + 0.5 * crack
            self.crack_em.inputs['Strength'].default_value = 6.0 + 10 * math.exp(-max(0.0, u - 0.5) * 3)

def ramp(t, a, b):
    import kwkit as KW
    return KW.ramp(t, a, b)
