"""kwrun - Blender side of kwkit: builds people/sets/fx for an Episode and renders it.  Not edited per episode."""
import bpy, os, sys, math, random, json, time, zlib
from mathutils import Vector, Matrix, Euler, Quaternion
from mathutils.bvhtree import BVHTree
import kwkit as KW
V11 = os.environ.get('KW_CAST', 'v1.1') == 'v1.1'
BURGER_HALF = 0.051           # m wrist out from the midline for grip_burger
LAUGH_BACK, LAUGH_BOUNCE = 4.0, 1.4      # deg head back, deg clavicle lift per bounce (~3.5 mm at the shoulder)
import kwlib as L
import kwlook as Q
import person as P
FPS = KW.FPS
ease, ramp, bump, clamp = KW.ease, KW.ramp, KW.bump, KW.clamp
V = Vector
LIE = Matrix(((0, 0, -1), (1, 0, 0), (0, -1, 0))).to_4x4()   # rig X->(0,1,0), Y->(0,0,-1), Z->(-1,0,0): on the back, head to -X
SIT = {'upperleg01': (-85, 0, 0), 'lowerleg01': (88, 0, 0)}  # same as ep_sneeze (sets are built around it)
RACE_TAN = {'caucasian': 0.45, 'asian': 0.3, 'african': 0.1, 'mixed': 0.25}
SHAPES = {   # finger angles. curl: fingers 3-5 (0..1); idx: index curl; thumb: 0..1 ; spread not used
    'relaxed': dict(idx=0.25, curl=0.32, thumb=0.25), 'open': dict(idx=0.04, curl=0.05, thumb=0.05), 'fist': dict(idx=1.0, curl=1.0, thumb=0.9),
    'point': dict(idx=0.0, curl=1.0, thumb=0.7), 'press2': dict(idx=0.12, mid=0.12, curl=0.95, thumb=0.5), 'hold': dict(idx=0.55, curl=0.6, thumb=0.6),
    'cup': dict(idx=0.28, curl=0.3, thumb=0.15), 'claw': dict(idx=0.45, curl=0.5, thumb=0.35), 'pinch': 'PINCH'}
PINCH = dict(idx=(60.4, 9.9, 12), curl=70, th1=(44.5, -10.9, 3.8), th2=(-9.1, 0, 0), th3=(0, 0, 0))   # ep_sneeze PINCHOPT result (finger part)
# part -> (bone, start offset (left, fwd, up) from bone head in person axes, ray direction (left, fwd, up) INTO the body, mesh set)
PARTSPEC = {
    'forehead': ('head', (0, 0.25, 0.10), (0, -1, 0), 'body'), 'head_top': ('head', (0, 0.0, 0.4), (0, 0, -1), 'body'),
    'eye_l': ('eye.L', (0, 0.25, 0), (0, -1, 0), 'body'), 'eye_r': ('eye.R', (0, 0.25, 0), (0, -1, 0), 'body'),
    'cheek_l': ('eye.L', (0.18, 0.25, -0.04), (-0.55, -0.83, 0), 'body'), 'cheek_r': ('eye.R', (-0.18, 0.25, -0.04), (0.55, -0.83, 0), 'body'),
    'ear_l': ('head', (0.3, -0.005, 0.035), (-1, 0, 0), 'body'), 'ear_r': ('head', (-0.3, -0.005, 0.035), (1, 0, 0), 'body'),
    'neck_l': ('neck02', (0.25, 0.25, 0.0), (-0.7, -0.7, 0), 'body'), 'neck_r': ('neck02', (-0.25, 0.25, 0.0), (0.7, -0.7, 0), 'body'),
    'throat': ('neck02', (0, 0.3, -0.01), (0, -1, 0), 'body'),
    'chest': ('spine01', (0, 0.4, -0.06), (0, -1, 0), 'all'), 'chest_l': ('spine01', (0.07, 0.4, -0.06), (0, -1, 0), 'all'), 'chest_r': ('spine01', (-0.07, 0.4, -0.06), (0, -1, 0), 'all'),
    'belly': ('spine04', (0, 0.4, 0.02), (0, -1, 0), 'all'), 'back': ('spine02', (0, -0.4, 0), (0, 1, 0), 'all'),
    'shoulder_l': ('upperarm01.L', (0, 0.0, 0.3), (0, 0, -1), 'all'), 'shoulder_r': ('upperarm01.R', (0, 0.0, 0.3), (0, 0, -1), 'all'),
    'wrist_l': ('wrist.L', (0, 0.0, 0.25), (0, 0, -1), 'body'), 'wrist_r': ('wrist.R', (0, 0.0, 0.25), (0, 0, -1), 'body'),
    'knee_l': ('lowerleg01.L', (0, 0.3, 0.0), (0, -1, 0), 'all'), 'knee_r': ('lowerleg01.R', (0, 0.3, 0.0), (0, -1, 0), 'all'),
}
FACE_PARTS = ('nose', 'mouth', 'chin', 'forehead', 'eye_l', 'eye_r', 'cheek_l', 'cheek_r', 'ear_l', 'ear_r', 'head_top')

DRINK_HG = (13.5, 5.5, 0.45)
HG_SWALLOW_DIP = 1.0             # deg
HG_DRIFT = (0.7, 0.8, 0.3)       # alive head drift: pitch, turn amplitude (deg), amplitude while a rim/spoon is at the lips (L2)
CHEW_SEAL, CHEW_SIDE = 0.35, 0.25     # ep08 chew: mouthClose per 7 mm of jaw gap (lips stay sealed), jawLeft at the close
SP_HEAD_FWD, SP_TRUNK_FWD = 10.0, 3.0   # humgen spoon bite: head forward / trunk forward at the spoon (deg, R4 8-12 / 2-4)
HG_SP_EYE = (-22.0, 0.65, 0.0)    # F4 spoon gaze (rendered check: +x on the HG eye bone looks UP): eye pitch deg at the low point, fraction lost by the lips, yaw toward the hand
HG_BREATH_SPINE = (-0.40, -0.40, 0.0)   # humgen breath: spine03/02/01 pitch per unit breath (deg; negative = extension, chest rises)
HG_DART = 0.8                    # idle eye dart amplitude (deg, R5 <= 1); one every HG_DART_F frames
HG_DART_F = 14
HG_FINGER_OFF = (0.0, 2.5, 5.0, 8.0)   # resting hand: index..pinky extra curl (deg, L6 not parallel)     # humgen drink: head nod back, neck back (deg; total ~12, addendum I R1), lid lowering


def side_sign(side): return 1.0 if side == 'L' else -1.0

class Actor:
    """runtime state of one person"""
    def __init__(self, rt, a):
        self.a, self.rt = a, rt; self.p = None; self.parts = {}; self.hand = {}; self.props = {}
        self.phase = Q.phase_seed(a.name)

class Runtime:
    def __init__(self, ep):
        self.ep = ep; self.t0 = time.time()
        self.body_r4 = Q.enabled('ACTING'); self.camera_r4 = Q.enabled('CAMERA')
        self.mocap = Q.load_mocap() if self.body_r4 else {}

    # ================================================================== build
    def build(self):
        ep = self.ep
        bpy.ops.wm.read_factory_settings(use_empty=True); self.S = S = bpy.context.scene
        for k, v in KW.EXTRA_EXPR.items(): P.EXPR.setdefault(k, v)     # extra shape keys (blink, swelling...) on every person
        self.K = self.G = None
        if not os.environ.get('NOSETS'):
            try: import sets_kw as K; self.K = K
            except Exception as e: print('sets_kw unavailable:', repr(e))
        if not os.environ.get('NOGFX'):
            try: import gfx_kw as G; self.G = G
            except Exception as e: print('gfx_kw unavailable:', repr(e))
        try: import wardrobe_kw as Wd
        except Exception as e: Wd = None; print('wardrobe unavailable', repr(e))
        import cast as C
        self.actors = {}
        for a in ep.people:
            ra = Actor(self, a); role = dict(a.role)
            if Wd: p = Wd.person(a.name, a.job, a.seed, **role)
            else:
                r2 = {k: v for k, v in role.items() if k in ('gender', 'age', 'race', 'build', 'hair', 'tee', 'outfit', 'beard')}
                p = P.build_person(a.name, **C.cast(r2, a.seed, P.MP))
            ra.p = p; a.p = p; self.actors[a] = ra
            if self.K and hasattr(self.K, 'skin'):
                amt = a.tan if a.tan is not None else RACE_TAN.get(a.role.get('race', 'mixed'), 0.25)
                try: self.K.skin(p, amount=amt)
                except Exception as e: print('skin failed', repr(e))
            self._ik_setup(ra)
            for o in p.parts:    # MPFB: avoid self-shadow acne from eyelash cards etc. (nothing to do) / name all parts
                pass
        print(f'people built {time.time() - self.t0:.0f}s')
        bpy.context.view_layer.update()
        if os.environ.get('KW_HEADS') == 'humgen':   # opt-in Human Generator people (heads_hg.py; assets only from the private kw-assets repo)
            import heads_hg as HGH
            for a_, ra_ in self.actors.items(): HGH.graft(self, ra_, dict(a_.role))
            Q.LOOP_T = round(max(s_.t + s_.length for s_ in self.ep.shots) * FPS) / FPS    # alive layer loop-locked (addendum H L9)
            bpy.context.view_layer.update()
        for ra in self.actors.values(): self._calibrate(ra)
        for ra in self.actors.values():
            if getattr(ra.p, 'hg', None) is not None: ra.p.hg.calibrate(self, ra)
        self._sets()
        self._lights_world_camera()
        import kwfx
        self.FX = kwfx.Builder(self); self.FX.build_all()
        self._canon()
        print(f'build done {time.time() - self.t0:.0f}s')

    def _ik_setup(self, ra):
        """IK on the forearm (target = wrist joint) so the kit can set the hand orientation freely afterwards."""
        p = ra.p; ra.ik = {}
        for s in 'LR':
            tgt, con, pole = p.ik[s]; con.influence = 0.0; con.mute = True
            c2 = p.pb(f'lowerarm02.{s}').constraints.new('IK'); c2.target = tgt; c2.pole_target = pole; c2.chain_count = 4; c2.pole_angle = math.radians(-90)
            c2.influence = 1.0; ra.ik[s] = (tgt, c2, pole)

    # ------------------------------------------------------------------ person-level calibration (deterministic, at origin)
    def reset(self, p):
        for pb in p.rig.pose.bones:
            pb.rotation_mode = 'XYZ'; pb.rotation_euler = (0, 0, 0); pb.location = (0, 0, 0); pb.scale = (1, 1, 1)
    def rig_at(self, p, loc, rz, lie=False):
        p.rig.rotation_mode = 'QUATERNION'
        M = Matrix.Translation(V(loc)) @ Matrix.Rotation(math.radians(rz), 4, 'Z') @ (LIE if lie else Matrix.Identity(4))
        p.rig.matrix_world = M
    def wmat(self, p, bone):
        return p.rig.matrix_world @ p.pb(bone).matrix
    def bw(self, p, bone, tail=False):
        pb = p.pb(bone); return p.rig.matrix_world @ (pb.tail if tail else pb.head)
    def set_shape(self, p, side, shape, k=1.0):
        """finger angles for a hand shape (k blends from relaxed)"""
        sg = -1 if side == 'L' else 1
        if shape == 'pinch':
            c = PINCH
            for j in (1, 2, 3):
                p.rot(f'finger2-{j}.{side}', (c['idx'][j - 1] * k + 10 * (1 - k), 0, 0))
                for f in (3, 4, 5): p.rot(f'finger{f}-{j}.{side}', ((25 + c['curl'] * k) * (0.8 if j == 1 else 1.0), 0, 0))
                a = c[f'th{j}']; p.rot(f'finger1-{j}.{side}', (k * a[0], k * a[1] * sg, k * a[2] * sg))
            return
        d = SHAPES[shape]
        for j in (1, 2, 3):
            m = 55 if j == 1 else 70
            p.rot(f'finger2-{j}.{side}', (d['idx'] * m, 0, 0)); p.rot(f'finger3-{j}.{side}', (d.get('mid', d['curl']) * m, 0, 0))
            for f in (4, 5): p.rot(f'finger{f}-{j}.{side}', (d['curl'] * m * (1.05 if f == 5 else 1.0), 0, 0))
            th = d['thumb']; p.rot(f'finger1-{j}.{side}', (th * 30, 0, th * 25 * sg))
    def _calibrate(self, ra):
        p = ra.p; S = self.S
        self.reset(p); self.rig_at(p, (0, 0, 0), 0); bpy.context.view_layer.update()
        rest_head = self.bw(p, 'head')
        # --- body parts measured on the real mesh (bone-local point + normal)
        meshes = {'body': [p.body], 'all': [o for o in p.parts if o.type == 'MESH' and not any(k in o.name.lower() for k in ('hair', 'eyebrow', 'eyelash', 'high-poly', 'teeth', 'tongue'))]}
        dg = bpy.context.evaluated_depsgraph_get(); bvh = {}
        for k, objs in meshes.items():
            verts, polys = [], []
            for o in objs:
                ev = o.evaluated_get(dg); me = ev.to_mesh(); mw = ev.matrix_world; off = len(verts)
                verts += [mw @ v.co for v in me.vertices]; polys += [[off + i for i in pl.vertices] for pl in me.polygons]; ev.to_mesh_clear()
            bvh[k] = BVHTree.FromPolygons(verts, polys)
        ra.bvh_rest = bvh
        # nose tip: most forward midline vertex near the head (ep_sneeze method)
        ev = p.body.evaluated_get(dg); hb = rest_head; best = None
        for v in ev.data.vertices:
            w = ev.matrix_world @ v.co
            if abs(w.x - hb.x) < 0.012 and -0.02 < w.z - hb.z < 0.12 and (best is None or w.y < best.y): best = w.copy()
        nose = best
        def store(name, bone, pt, nrm):
            M = self.wmat(p, bone); Mi = M.inverted()
            ra.parts[name] = (bone, Mi @ pt, (Mi.to_3x3() @ nrm).normalized())
        store('nose', 'head', nose, V((0, -1, 0.15)).normalized())
        for nm, dz, back in (('mouth', -0.032, 0.0), ('chin', -0.07, 0.0)):
            o = V((hb.x, nose.y - 0.2, nose.z + dz)); hit = bvh['body'].ray_cast(o, V((0, 1, 0)))
            store(nm, 'head', hit[0] if hit[0] else nose + V((0, 0.012, dz)), V((0, -1, 0)))
        for nm, (bone, off, dr, ms) in PARTSPEC.items():
            o = self.bw(p, bone) + V(off) * 1.0
            o = self.bw(p, bone) + V((off[0], -off[1], off[2]))       # person axes: left=+X, fwd=-Y, up=+Z at rest
            d = V((dr[0], -dr[1], dr[2])).normalized()
            hit = bvh[ms].ray_cast(o, d, 1.0)
            if hit[0] is None: hit = bvh['body'].ray_cast(o, d, 1.0)
            if hit[0] is None: print('part not found', p.name, nm); pt, nr = self.bw(p, bone), -d
            else: pt, nr = hit[0], hit[1]
            if nr.dot(d) > 0: nr = -nr
            store(nm, bone, pt, nr)
        # nostrils (pinch) in head space
        ra.nostril = {'L': ra.parts['nose'][1] + (self.wmat(p, 'head').inverted().to_3x3() @ V((0.019, 0.013, 0.004))),
                      'R': ra.parts['nose'][1] + (self.wmat(p, 'head').inverted().to_3x3() @ V((-0.019, 0.013, 0.004)))}
        # --- hands: tip points per shape in wrist-matrix space, palm normal, finger direction
        ra.hand = {}
        for s in 'LR':
            Mi = self.wmat(p, f'wrist.{s}').inverted(); info = {}
            self.set_shape(p, s, 'open'); bpy.context.view_layer.update(); Mi = self.wmat(p, f'wrist.{s}').inverted()
            f0 = Mi @ self.bw(p, f'finger3-3.{s}', True); base = Mi @ self.bw(p, f'finger3-1.{s}'); wh = Mi @ self.bw(p, f'wrist.{s}')
            self.set_shape(p, s, 'fist'); bpy.context.view_layer.update(); f1 = Mi @ self.bw(p, f'finger3-3.{s}', True)
            fdir = (base - wh).normalized(); n = (f1 - f0); n = (n - fdir * n.dot(fdir)).normalized()
            info['fdir'], info['pnorm'] = fdir, n
            for sh in SHAPES:
                self.set_shape(p, s, sh); bpy.context.view_layer.update(); Mi = self.wmat(p, f'wrist.{s}').inverted()
                g = lambda b, t=True: Mi @ self.bw(p, f'{b}.{s}', t)
                palm = wh.lerp(base, 0.62) + n * 0.016
                tips = dict(palm=palm, index=g('finger2-3'), thumb=g('finger1-3'), pads=(g('finger2-3') + g('finger3-3')) * 0.5 + n * 0.007,
                            mid2=g('finger2-2', False) + n * 0.01)
                tips['pinch'] = tips['index'].lerp(tips['thumb'], 0.5)
                info[sh] = tips
            ra.hand[s] = info
            self.set_shape(p, s, 'relaxed')
        # --- heights for spots
        self.reset(p); [p.rot(f'{b}.{s}', v) for b, v in SIT.items() for s in 'LR']; bpy.context.view_layer.update()
        ra.sit_pelvis = self.bw(p, 'spine05').z; ra.sit_head = self.bw(p, 'head').z
        self.reset(p); self.rig_at(p, (0, 0, 0), 0, lie=True); bpy.context.view_layer.update()
        ev = p.body.evaluated_get(bpy.context.evaluated_depsgraph_get())
        ra.lie_minz = min((ev.matrix_world @ v.co).z for v in ev.data.vertices); ra.lie_hip = self.bw(p, 'spine05')
        self.reset(p); self.rig_at(p, (0, 0, 0), 0); bpy.context.view_layer.update()
        ra.stand_head = self.bw(p, 'head').z
        ra.clip = next((o for o in p.parts if 'clipboard' in o.name.lower() and o.type == 'MESH'), None)
        print('calibrated', p.name, 'nose', tuple(round(x, 3) for x in nose), 'sit pelvis', round(ra.sit_pelvis, 3))

    # ------------------------------------------------------------------ sets
    def _sets(self):
        ep = self.ep; S = self.S
        used = {s.set for s in ep.shots}
        for s in ep.shots:
            for a, ps in s.cast.items():
                for _, q in ps.keys: used.add(ep.spot_of(s, q)[0])
        self.used_sets = used; self.colls = {}; self.ref = {}; self.set_obj = {}
        for st in ('car', 'hospital', 'room', 'street', 'studio'):
            if st not in used: continue
            ref = None
            for s in ep.shots:     # reference person: whoever sits on the main seat of that set
                for a, ps in s.cast.items():
                    for _, q in ps.keys:
                        sst, sp, spec = ep.spot_of(s, q)
                        if sst == st and spec[0] == 'seat' and ref is None: ref = self.actors[a]
            if ref is None: ref = self.actors[ep.people[0]]
            self.ref[st] = ref; p = ref.p
            self.reset(p); [p.rot(f'{b}.{s_}', v) for b, v in SIT.items() for s_ in 'LR']
            seat0 = {'car': (0, 0), 'hospital': (0, 0), 'room': (0, 0), 'street': KW.SPOTS['street']['bench'][1], 'studio': KW.SPOTS['studio']['centre_sit'][1]}[st]
            z0 = KW.SEAT_H[st] + 0.075 - ref.sit_pelvis if st in KW.SEAT_H else 0.0
            self.rig_at(p, (seat0[0], seat0[1], z0), 0); bpy.context.view_layer.update()
            obj = None
            try:
                if st in ('car', 'hospital') and self.K:
                    obj = getattr(self.K, 'build_' + st)(S, p); c = obj.coll
                else:
                    import kwsets
                    obj = kwsets.build(st, S, p, self.K); c = obj.coll
            except Exception as e:
                import traceback; traceback.print_exc(); print('set build failed', st, repr(e)); c = L.coll('kw_' + st + '_fallback')
                fl = L.box(st + '_floor', (12, 12, 0.05), (seat0[0], seat0[1], -0.025), L.mat(st + '_floor', (0.4, 0.42, 0.45), 0.6), c, 0)
            self.colls[st] = c; self.set_obj[st] = obj
            self.reset(p); self.rig_at(p, (0, 0, 0), 0)
        bpy.context.view_layer.update()
        self.hz_hosp = self.ref['hospital'].sit_head if 'hospital' in self.ref else None
        self.seat_pelvis = {st: r.sit_pelvis for st, r in self.ref.items()}

    def spot_matrix(self, ra, shot, q):
        st, sp, (kind, xy, rz, extra) = self.ep.spot_of(shot, q)
        p = ra.p
        if kind == 'seat':
            z = (KW.SEAT_H[st] + 0.075 - ra.sit_pelvis) if st in KW.SEAT_H else (self.seat_pelvis.get(st, ra.sit_pelvis) - ra.sit_pelvis)
            z -= getattr(ra, 'hg_seat_drop', 0.0)     # humgen only: its seat-to-pelvis depth differs from the 7.5 cm kit rule
            return Matrix.Translation(V((xy[0], xy[1], z))) @ Matrix.Rotation(math.radians(rz), 4, 'Z'), st
        if kind == 'stand_near':
            ref = self.ref.get(st); hz = ref.sit_head if ref else ra.stand_head
            z = hz + extra - ra.stand_head
            return Matrix.Translation(V((xy[0], xy[1], z))) @ Matrix.Rotation(math.radians(rz), 4, 'Z'), st
        if kind == 'lie':
            surf = 0.0
            if st == 'hospital': ref = self.ref.get('hospital'); surf = (ref.sit_pelvis - 0.075 + 0.012) if ref else 0.6
            R = Matrix.Rotation(math.radians(rz), 4, 'Z') @ LIE; hip = R @ (ra.lie_hip)   # lie_hip measured with LIE at origin
            loc = V((xy[0], xy[1], surf - ra.lie_minz + 0.004)) - V((ra.lie_hip.x, ra.lie_hip.y, 0))
            if rz: loc = V((xy[0], xy[1], surf - ra.lie_minz + 0.004)) - (Matrix.Rotation(math.radians(rz), 3, 'Z') @ V((ra.lie_hip.x, ra.lie_hip.y, 0)))
            return Matrix.Translation(loc) @ R, st
        return Matrix.Translation(V((xy[0], xy[1], 0))) @ Matrix.Rotation(math.radians(rz), 4, 'Z'), st

    # ------------------------------------------------------------------ lights / worlds / camera / render
    def _lights_world_camera(self):
        S = self.S; K = self.K
        def area(name, e, size, colr):
            Ld = bpy.data.lights.new(name, 'AREA'); Ld.energy = e; Ld.size = size; Ld.color = colr; o = bpy.data.objects.new(name, Ld); S.collection.objects.link(o); return o
        self.PL = [(area('kw_key', 200, 1.6, (1, 0.9, 0.78)), V((0.6, -1.6, 0.5)), 200), (area('kw_rim', 200, 0.8, (0.35, 0.65, 1.0)), V((-1.2, 0.3, 0.3)), 200),
                   (area('kw_fill', 30, 1.5, (1, 0.9, 0.8)), V((1.2, -0.4, -0.2)), 30)]
        self.ML = [(area('kw_pkey', 500, 2.5, (1, 0.96, 0.92)), V((-1.2, -2.0, 0.4)), 500), (area('kw_prim', 300, 1.5, (0.55, 0.7, 1.0)), V((1.5, 0.8, 0.0)), 300),
                   (area('kw_pfill', 120, 2.5, (1, 0.9, 0.85)), V((0.6, -2.2, -1.9)), 120)]
        # studio gradient world (from ep_sneeze): window-space radial gradient + grid for camera rays, even ambient otherwise
        W = bpy.data.worlds.new('kw_studio_grad'); W.use_nodes = True; wn = W.node_tree; wn.nodes.clear()
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
        self.W = W; self.w_grad, self.w_gs, self.w_amb = w_grad, w_gs, w_amb
        self.STUDIO = {'sky': ((0.2, 0.62, 1.0), (0.02, 0.16, 0.6), 0.16, (0.75, 0.85, 1.0), 0.3), 'night': ((0.02, 0.1, 0.32), (0.0, 0.012, 0.07), 0.1, (0.2, 0.4, 0.9), 0.12),
                       'warm': ((1.0, 0.62, 0.1), (0.85, 0.16, 0.05), 0.0, (1.0, 0.85, 0.7), 0.5), 'teal': ((0.05, 0.75, 0.7), (0.0, 0.18, 0.28), 0.12, (0.7, 0.95, 0.95), 0.35)}
        self.STUDIO['scan2'] = ((.0025, .009, .018), (.0004, .0015, .003), 0., (.37, .57, .82), .11)
        self.STUDIO['macro2'] = ((.095, .025, .036), (.026, .006, .013), 0., (.75, .85, 1.), .3)
        self.W0 = bpy.data.worlds.new('kw_plain'); self.W0.use_nodes = True
        cam_d = bpy.data.cameras.new('kw_cam'); self.CAM = bpy.data.objects.new('kw_cam', cam_d); S.collection.objects.link(self.CAM); S.camera = self.CAM; cam_d.clip_start = 0.01
        cam_d.sensor_fit = 'AUTO'; cam_d.sensor_width = 36
        self.SAMPLES = SAMPLES = int(os.environ.get('SAMPLES', '32'))
        S.render.engine = 'CYCLES'; S.cycles.samples = SAMPLES; S.cycles.use_denoising = True; S.cycles.max_bounces = 6
        S.cycles.transparent_max_bounces = 16; S.render.use_persistent_data = True
        S.view_settings.view_transform = 'AgX'; S.view_settings.look = 'AgX - Punchy'
        if K and hasattr(K, 'finish'):
            try: K.finish(S, SAMPLES)
            except Exception as e: print('finish failed', repr(e))
        try: import kw_realism as _R; _R.compositor_finish(S, glare=True, vignette=0, glare_threshold=1.0, glare_mix=-0.85)   # LESSON: the compositor ellipse-mask vignette renders as a sharp light oval in mid-frame (it looked like a skin patch); post_kw.grade does the vignette
        except Exception as e: print('compositor reset failed', repr(e))
        S.cycles.caustics_refractive = True   # LESSON: MPFB eyes sit behind a refractive cornea; without this the eyes render black
        S.render.resolution_x, S.render.resolution_y = tuple(int(v) for v in os.environ.get('KW_RES', '1080x1920').split('x'))   # KW_RES=WxH: brand stills (profile / banner)
        S.render.resolution_percentage = int(os.environ.get('PCT', '100')); S.render.fps = FPS
        self.path_defaults = {k: getattr(S.cycles, k) for k in (
            'max_bounces', 'diffuse_bounces', 'glossy_bounces', 'adaptive_threshold',
            'adaptive_min_samples', 'caustics_reflective')}
        self.render_budget_set = None

    def render_budget(self, kind):
        light = kind == 'studio' and os.environ.get('KW_LIGHT') == '1'     # ep07: light-render settings on the studio set (approved by the lead)
        if self.render_budget_set == kind or not (Q.enabled('PATH2') or light): return
        self.render_budget_set = kind
        opts = self.path_defaults.copy()
        if kind in ('room', 'hospital') or light:
            opts.update(max_bounces=4, diffuse_bounces=1, glossy_bounces=2,
                        caustics_reflective=False)
            if self.SAMPLES >= 16:
                opts.update(adaptive_threshold=.16, adaptive_min_samples=6)
        for k, v in opts.items(): setattr(self.S.cycles, k, v)

    def world(self, kind):
        S = self.S
        if kind in self.STUDIO:
            c, e, gs, amb, st = self.STUDIO[kind]; S.world = self.W
            self.w_grad.inputs[6].default_value = (*c, 1); self.w_grad.inputs[7].default_value = (*e, 1); self.w_gs.inputs[1].default_value = gs
            self.w_amb.inputs[0].default_value = (*amb, 1); self.w_amb.inputs[1].default_value = st
            return
        k = {'room': 'hospital', 'street': 'car', 'studio_hdr': 'studio'}.get(kind, kind)
        if self.K:
            try: self.K.set_world(S, k); return
            except Exception as e: print('world failed', kind, repr(e))
        S.world = self.W0; bg = self.W0.node_tree.nodes['Background']; bg.inputs[0].default_value = (0.35, 0.6, 0.95, 1) if kind in ('car', 'street') else (0.5, 0.6, 0.65, 1); bg.inputs[1].default_value = 0.6

    # ------------------------------------------------------------------ canonical anchors (camera reference, deterministic)
    def _canon(self):
        self.canon = {}
        for i, s in enumerate(self.ep.shots):
            subj = []
            c = s.cam
            if isinstance(c, KW.Cam):
                if isinstance(c.subj, KW.Actor): subj.append(c.subj)
                if isinstance(c.o.get('other'), KW.Actor): subj.append(c.o['other'])
            if not subj: continue
            self.pose_all(s, 0.0, canonical=True)
            for a in subj: self.canon[(i, a)] = self.anchors(self.actors[a])
        print('canonical anchors', len(self.canon))

    def anchors(self, ra):
        """live geometric frame of a person: face anchor, head basis, part points"""
        p = ra.p; Mh = self.wmat(p, 'head'); hb = Mh.translation.copy()
        nose = Mh @ ra.parts['nose'][1]; upb = (Mh.to_3x3() @ V((0, 1, 0))).normalized()
        f = nose - hb; f = (f - upb * f.dot(upb)).normalized(); left = upb.cross(f).normalized()
        R = p.rig.matrix_world.to_3x3().normalized()
        A = dict(head=hb, nose=nose, up=upb, fwd=f, left=left, face=hb + f * 0.03 + upb * (0.03 + getattr(ra, 'hg_face_dz', 0.0)),   # hg_face_dz: humgen only (HG face height on the head bone)
                 body_up=(R @ V((0, 0, 1))).normalized(), body_fwd=(R @ V((0, -1, 0))).normalized(), body_left=(R @ V((1, 0, 0))).normalized(),
                 hips=self.bw(p, 'spine05'), chest=self.part_world(ra, 'chest')[0], feet=p.rig.matrix_world.translation.copy())
        return A
    def part_world(self, ra, name):
        if name == 'face': A = self.anchors_light(ra); return A, None
        bone, loc, nrm = ra.parts[name]; M = self.wmat(ra.p, bone)
        return M @ loc, (M.to_3x3() @ nrm).normalized()
    def anchors_light(self, ra):
        Mh = self.wmat(ra.p, 'head'); hb = Mh.translation; up = (Mh.to_3x3() @ V((0, 1, 0))).normalized(); nose = Mh @ ra.parts['nose'][1]
        f = nose - hb; f = (f - up * f.dot(up)).normalized(); return hb + f * 0.03 + up * (0.03 + getattr(ra, 'hg_face_dz', 0.0))

    # ================================================================== per-frame posing
    def act_state(self, a, acts, u, t):
        """sum of act motions at local time u -> dict"""
        st = dict(nod=0.0, turn=0.0, tilt=0.0, lean=0.0, neck=0.0, face={}, shake=0.0)
        def F(k, v):
            if v > st['face'].get(k, 0): st['face'][k] = v
        for ac in acts:
            k, at, kw = ac.kind, ac.at, ac.kw
            if k == 'sneeze':
                big = kw.get('big', 1.0)
                ih = ramp(u, at - 0.6, at - 0.08) * (1 - ramp(u, at, at + 0.06)); bl = ramp(u, at, at + 0.07) * (1 - ramp(u, at + 0.45, at + 0.85))
                st['nod'] += (-16 * ih + 15 * bl) * big; st['neck'] += (-8 * ih + 7 * bl) * big; st['lean'] += (7 * bl - 5 * ih) * big
                F('open', max(ih * 0.5, bl)); F('squint', max(ih * 0.7, bl)); F('twitch', ih * 0.6)
            elif k == 'cough':
                for i in range(int(kw.get('n', 3))):
                    c = at + i * kw.get('gap', 0.45); b = bump(u, c + 0.05, 0.08)
                    st['nod'] += 9 * b; st['lean'] += 7 * b; F('open', 0.6 * b); F('squint', 0.6 * b); F('grimace', 0.3 * b)
            elif k == 'blow_nose':
                d = kw.get('dur', 1.4); h = kw.get('hard', 1.0); w = ramp(u, at, at + 0.15) * (1 - ramp(u, at + d, at + d + 0.25))
                ih = bump(u, at - 0.1, 0.12)
                st['nod'] += 6 * w * h - 6 * ih; st['lean'] += 4 * w * h; st['shake'] += 0.5 * w * h
                F('puff', 0.9 * w * h); F('pressed', 0.7 * w); F('squint', 0.75 * w * h); F('bulge', 0.35 * w * h); F('open', 0.25 * ih)
            elif k == 'swallow':
                b = bump(u, at, 0.15); st['nod'] += 7 * b; F('pressed', 0.8 * b); F('squint', 0.2 * b)
            elif k == 'eat' and kw.get('beats') and getattr(getattr(self.actors.get(a), 'p', None), 'hg', None) is not None:
                # humgen spoon (S4-S6, R3, R4): jaw opens before the spoon arrives, lips close on it, one chew; head + trunk lean in
                bs = self.actors[a].p.hg.bite_state(self, self.actors[a], u, acts)
                st['nod'] += kw.get('nod', SP_HEAD_FWD) * bs['lean']; st['lean'] += kw.get('trunk', SP_TRUNK_FWD) * bs['lean']
                F('jaw', bs['jaw']); F('lipsclose', bs['lips'])
            elif k == 'chew':
                # ep08: lips shut, jaw 6-8 mm, chin to his left on each close, cheek bulge; one swallow = 10-frame pause + 1 deg dip
                u0, u1 = at, kw.get('until', at + 3.0); env = ramp(u, u0, u0 + 0.12) * (1 - ramp(u, u1 - 0.15, u1))
                sw = kw.get('swallow'); ph_ = (u - u0) * kw.get('rate', 1.5)
                if sw is not None:
                    pz = 10.0 / FPS
                    if u > sw + pz: ph_ -= pz * kw.get('rate', 1.5)
                    elif u > sw: ph_ = (sw - u0) * kw.get('rate', 1.5); env = 0.0
                    st['nod'] += 1.0 * bump(u, sw + 0.2, 0.15)
                if env > 0:
                    c_ = 0.5 - 0.5 * math.cos(2 * math.pi * ph_); gp = kw.get('gap', 7.0) * c_ * env
                    F('x_gap', gp); F('lipsclose', CHEW_SEAL * gp / 7.0)
                    F('chewside', CHEW_SIDE * kw.get('side', 1.0) * env * max(0.0, -math.sin(2 * math.pi * ph_)))
                    F('cheekfull', kw.get('bulge', 0.35) * env * (1.0 if ph_ < 6 else 0.6) * (0.75 + 0.25 * c_))
            elif k == 'eat':
                for i in range(int(kw.get('bites', 2))):
                    c = at + i * 0.6; F('open', 0.55 * bump(u, c, 0.1)); F('open', 0.18 * max(0, math.sin((u - c) * 14)) * window_(u, c + 0.15, c + 0.55))
            elif k == 'drink':
                d = kw.get('dur', 1.2); ra_ = self.actors.get(a)
                if ra_ is not None and getattr(ra_.p, 'hg', None) is not None:
                    # humgen (grip brief M2-M5 + addendum I R1): 40/20/40 eased tilt about the lip; head+neck back ~12 deg at the
                    # peak; lips stay closed on the rim (no jaw open); lids lower to about half
                    sm_ = lambda x, a0, b0: 0.0 if x <= a0 else 1.0 if x >= b0 else (lambda y: y * y * (3 - 2 * y))((x - a0) / (b0 - a0))
                    w = sm_(u, at, at + 0.4 * d) * (1 - sm_(u, at + 0.6 * d, at + d))
                    st['nod'] -= DRINK_HG[0] * w; st['neck'] -= DRINK_HG[1] * w; F('blink', DRINK_HG[2] * w)
                    st['nod'] += HG_SWALLOW_DIP * bump(u, at + 0.62 * d, 0.13 * d)     # L4 swallow: 1 deg chin dip (no larynx control in the cast)
                else:
                    w = ramp(u, at, at + 0.3) * (1 - ramp(u, at + d, at + d + 0.3)); st['nod'] -= 16 * w; st['neck'] -= 6 * w; F('open', 0.2 * w)
            elif k == 'wince' and V11:
                # cast v1.1 wince: in 4 frames, hold 6, out 8 (eased); small flinch of the head
                f_ = (u - at) * FPS; e_ = 0.0 if f_ < 0 or f_ > 18 else min(1.0, f_ / 4) if f_ < 4 else 1.0 if f_ <= 10 else 1.0 - (f_ - 10) / 8
                b = e_ * e_ * (3 - 2 * e_) * kw.get('hard', 1.0); st['nod'] += 4 * b; st['tilt'] += 5 * b; F('x_wince', b)
            elif k == 'wince':
                b = bump(u, at, 0.16) * kw.get('hard', 1.0); st['nod'] += 5 * b; st['tilt'] += 6 * b; F('grimace', 0.8 * b); F('squint', 0.6 * b)
            elif k == 'nod':
                w = window_(u, at, at + 0.4 * kw.get('n', 2)); st['nod'] += 9 * math.sin((u - at) * 15.7) * w
            elif k == 'shake_head':
                w = window_(u, at, at + 0.45 * kw.get('n', 2)); st['turn'] += 16 * math.sin((u - at) * 14) * w
            elif k == 'gasp':
                b = ramp(u, at, at + 0.12) * (1 - 0.6 * ramp(u, at + 0.5, at + 1.0)); st['nod'] -= 7 * b; F('wide', b); F('open', 0.55 * b)
            elif k == 'breathe_hard':
                w = ramp(u, at, at + 0.2); s_ = math.sin((u - at) * 2 * math.pi * kw.get('rate', 1.6)); st['lean'] += 2.5 * s_ * w; st['nod'] -= 2 * s_ * w; F('open', (0.25 + 0.15 * s_) * w)
            elif k == 'look_around':
                st['turn'] += 30 * math.sin(clamp((u - at) / 1.6) * 2 * math.pi) * ramp(u, at, at + 0.1)
            elif k == 'flinch':
                b = bump(u, at + 0.08, 0.12); st['lean'] -= 8 * b; st['nod'] -= 6 * b; F('squint', b); F('wide', 0.4 * b)
            elif k == 'yawn':
                w = bump(u, at + 0.7, 0.45); st['nod'] -= 10 * w; F('open', w); F('squint', 0.6 * w)
            elif k == 'sniff':
                b = bump(u, at, 0.12); st['nod'] -= 4 * b; F('twitch', 0.9 * b); F('squint', 0.3 * b)
            elif k == 'scratch':
                st['tilt'] += 5 * math.sin((u - at) * 9) * ramp(u, at, at + 0.2)
        return st

    def face_values(self, ra, qa, qb, w, acts_st, u, t, shot, acts=()):
        want = {}
        def add(expr, v):
            if v <= 0: return
            for path, wt in P.EXPR.get(expr, ()): want[path] = max(want.get(path, 0.0), v * wt)     # humgen-only names (jaw, lipsclose) have no kit key
        mix = {}
        for nm, v in qa.face.items(): mix[nm] = mix.get(nm, 0) + v * (1 - w)
        for nm, v in qb.face.items(): mix[nm] = mix.get(nm, 0) + v * w
        exprs = {}
        for nm, v in mix.items():
            for e, ev in KW.FACES[nm].items(): exprs[e] = exprs.get(e, 0) + ev * v
        if 'talk' in exprs: exprs['talk'] = exprs['talk'] * (0.5 + 0.5 * math.sin(t * 17.0) * math.sin(t * 5.3 + 1))
        if 'puff' in exprs: exprs['puff'] *= 1 + 0.08 * math.sin(t * 9)
        for e, v in acts_st['face'].items(): exprs[e] = max(exprs.get(e, 0), v)
        # blinks (deterministic per person); not while eyes squeezed
        if getattr(ra.p, 'hg', None) is not None and getattr(self.ep, 'blinks', None) is not None:
            # humgen: blinks keyed to the frame timeline (addendum G), R7 shape: close 1-2 frames, shut 2, open over 2
            f_ = int(round(t * FPS)); bl = 0.0
            for b0 in self.ep.blinks.get(ra.a.name, ()):
                if isinstance(b0, tuple):        # soft eye close (a, b, c, d): close a..b, held to c, open c..d
                    a0, b1, c0, d0 = b0
                    v_ = 0.0 if f_ < a0 or f_ > d0 else min(1.0, (f_ - a0) / max(1, b1 - a0)) if f_ < b1 else 1.0 if f_ <= c0 else 1.0 - (f_ - c0) / max(1, d0 - c0)
                    bl = max(bl, 0.92 * v_ * v_ * (3 - 2 * v_)); continue
                k_ = f_ - b0
                if 0 <= k_ < 5: bl = max(bl, (0.5, 1.0, 1.0, 0.45, 0.12)[k_])
            exprs['blink'] = max(exprs.get('blink', 0), bl)
        elif qb.blink and exprs.get('blink', 0) < 0.5:
            if self.body_r4:
                if exprs.get('squint', 0) < 0.75:
                    exprs['blink'] = max(exprs.get('blink', 0), Q.auto_blink(t, ra.phase, acts, u))
            else:
                ph = (hash(ra.a.name) % 97) / 97.0 * 3.1
                c = (t + ph) % 3.3
                exprs['blink'] = max(exprs.get('blink', 0), bump(c, 0.1, 0.055))
        sw = {}
        for k, v in qa.swell.items(): sw[k] = sw.get(k, 0) + v * (1 - w)
        for k, v in qb.swell.items(): sw[k] = sw.get(k, 0) + v * w
        for k, v in sw.items(): exprs[KW.SWELL[k]] = max(exprs.get(KW.SWELL[k], 0), v * (1.3 if k == 'neck' else 1.0))
        if sw.get('eye_l', 0) > 0.4 or sw.get('eye_r', 0) > 0.4: pass
        for e, v in exprs.items(): add(e, v)
        for path, k in ra.p.keys.items(): k.value = min(k.slider_max, want.get(path, 0.0))
        if getattr(ra.p, 'hg', None) is not None: ra.p.hg.face(exprs)
        fl = qa.flush * (1 - w) + qb.flush * w
        if self.K and hasattr(self.K, 'flush'):
            try: self.K.flush(ra.p, fl)
            except Exception: pass

    def base_rot(self, base, u, t):
        R = {}
        if base in ('sit', 'drive'):
            for b, v in SIT.items():
                for s in 'LR': R[f'{b}.{s}'] = v
        elif base == 'walk':
            ph = t * 2 * math.pi * 0.95
            for s, sg in (('L', 1), ('R', -1)):
                a = math.sin(ph) * sg; R[f'upperleg01.{s}'] = (-24 * a, 0, 0); R[f'lowerleg01.{s}'] = (35 * max(0, -math.sin(ph + 0.6) * sg), 0, 0)
                R[f'foot.{s}'] = (-10 * a, 0, 0)
            R['spine04'] = (0, 4 * math.sin(ph), 0)
        return R

    def pose_all(self, shot, u, canonical=False):
        """bodies (not hands) for every cast member; then hands. canonical = no acts / no time effects (camera reference)"""
        t = shot.t + u; self._t_now = t       # read by the humgen burger track (ep08)
        self._cur = []
        for a, ps in shot.cast.items():
            ra = self.actors[a]; p = ra.p; qa, qb, w = ps.at_time(u)
            acts = [] if canonical else [ac for _, q in ps.keys for ac in q.acts]
            self.reset(p)
            Ra, ra_ = self.base_rot(qa.base, u, t), self.base_rot(qb.base, u, t)
            for b in set(Ra) | set(ra_):
                x = Ra.get(b, (0, 0, 0)); y = ra_.get(b, (0, 0, 0)); p.rot(b, tuple(x[i] + (y[i] - x[i]) * w for i in range(3)))
            Ma, _ = self.spot_matrix(ra, shot, qa); Mb, _ = self.spot_matrix(ra, shot, qb)
            if w <= 0: M = Ma
            elif w >= 1: M = Mb
            else:
                la, lb = Ma.to_translation(), Mb.to_translation(); qa_, qb_ = Ma.to_quaternion(), Mb.to_quaternion()
                M = Matrix.Translation(la.lerp(lb, w)) @ qa_.slerp(qb_, w).to_matrix().to_4x4()
            ws = qb.walk_speed if qb.base == 'walk' else 0.0
            if ws: M = M @ Matrix.Translation(V((0, -ws * u, 0)))
            if qb.base == 'walk' and not canonical: M = M @ Matrix.Translation(V((0, 0, 0.012 * abs(math.sin(t * 2 * math.pi * 0.95)))))
            p.rig.rotation_mode = 'QUATERNION'; p.rig.matrix_world = M
            st = self.act_state(a, acts, u, t) if not canonical else self.act_state(a, [], u, t)
            acts_b = [ac for ac in acts if not (ac.kind == 'eat' and ac.kw.get('beats'))]     # humgen spoon bites carry their own lean (R4): no kit recoil / mocap eat track
            ra.beat = Q.body_beat(t, u, ra.phase, acts_b, qb.base) if self.body_r4 and not canonical else (0.0, 0.0, 0.0)
            breath, shift, settle = ra.beat
            hd = tuple(qa.head[i] + (qb.head[i] - qa.head[i]) * w for i in range(3))
            nod, turn, tilt = hd[0] + st['nod'], hd[1] + st['turn'], hd[2] + st['tilt']
            look = qb.look if qb.look is not None else qa.look
            ra.cur_look = look
            if look is not None and not canonical:
                tgt = self.look_point(look) if look != 'held' else None
                if look == 'held':       # cast v1.1: head dips half way toward a burger held at the chest (eyes do the rest); none at the mouth
                    hs_ = [getattr(qb, sd_, None) for sd_ in ('left', 'right')]
                    if any(h_ is not None and h_.at == 'track' for h_ in hs_): pass     # ep08 track: head from the pose keys, eyes on the burger
                    elif not any(h_ is not None and h_.at == 'mouth' for h_ in hs_):
                        R3 = M.to_3x3().normalized(); hp0 = M @ p.rig.data.bones['head'].head_local
                        tgt = hp0 + (R3 @ V((0, -1, 0))) * 0.6 - (R3 @ V((0, 0, 1))) * 0.17
                    else:      # biting (bite_fix 1): chin down toward the bite point, the eyes do the rest
                        import heads_hg as _hh; nod += _hh.BURGER2['bite_nod']
                if tgt is not None:
                    hp = M @ p.rig.data.bones['head'].head_local; Ri = M.to_3x3().inverted(); d = Ri @ (tgt - hp)
                    lt = math.degrees(math.atan2(d.x, -d.y)); ln = -math.degrees(math.atan2(d.z, math.hypot(d.x, d.y)))
                    lw = w if qb.look is not None and qa.look is None else 1.0
                    turn += clamp(lt, -65, 65) * lw; nod += clamp(ln, -35, 40) * lw
            if st['shake']: nod += st['shake'] * 2.0 * math.sin(t * 47); tilt += st['shake'] * 1.5 * math.sin(t * 39)
            lw_ = (qa.face.get('laugh', 0) * (1 - w) + qb.face.get('laugh', 0) * w) if V11 and isinstance(qa.face, dict) and isinstance(qb.face, dict) else 0.0
            if lw_ > 0:      # cast v1.1 laugh: head back ~4 deg, shoulders bounce 3x at ~5/s (then a short rest), 3-4 mm
                nod -= LAUGH_BACK * lw_; ph_l = (u % 1.4) * 5.0
                ra.laugh_bounce = LAUGH_BOUNCE * lw_ * (math.sin(ph_l * math.pi) ** 2 if ph_l < 3 else 0.0)
            else: ra.laugh_bounce = 0.0
            if getattr(p, 'hg', None) is not None and not canonical:
                # L2: never a locked head; slow loop-locked drift, smaller while a rim / spoon is at the lips
                hm = [getattr(qb, sd_, None) for sd_ in ('left', 'right')]
                at_lips = any(h_ is not None and h_.kind == 'hold' and h_.at == 'mouth' and h_.prop == 'can' for h_ in hm)
                ap, at_ = (HG_DRIFT[2], HG_DRIFT[2]) if at_lips else (HG_DRIFT[0], HG_DRIFT[1]); ph_ = ra.phase * 6.283
                nod += ap * (0.7 * math.sin(t * Q.loop_w(3.9) + ph_) + 0.3 * math.sin(t * Q.loop_w(6.1) + 2 * ph_))
                turn += at_ * (0.7 * math.sin(t * Q.loop_w(2.7) + 1.3 + ph_) + 0.3 * math.sin(t * Q.loop_w(5.3) + 0.4))
            lean = qa.lean + (qb.lean - qa.lean) * w + st['lean']
            p.rot('neck02', (nod * 0.35 + st['neck'], turn * 0.35, tilt * 0.3)); p.rot('head', (nod * 0.65, turn * 0.65, tilt * 0.7))
            # L1 humgen: a breath IN is a small upper-back extension + the clavicle lift (measured on the HG mesh: chest
            # +3.3 mm, shoulders +4.5 mm per full breath); the kit's forward bend made the chest sink 2 mm on every breath in
            bk = HG_BREATH_SPINE if getattr(p, 'hg', None) is not None else (0.24, 0.47, 0.30)
            p.rot('spine03', (lean * 0.4 + bk[0] * breath, 0.35 * shift, 0.52 * shift))
            p.rot('spine02', (lean * 0.35 + bk[1] * breath + 0.75 * settle, 0.60 * shift, 0.75 * shift))
            p.rot('spine01', (lean * 0.25 + bk[2] * breath + 0.40 * settle, 0.34 * shift, 0.22 * shift))
            if self.body_r4 and not canonical:
                cue = next((at for at, q in ps.keys if q is qb), 0.)
                Q.mocap_pose(p, self.mocap, acts_b, u, qb.base, qb, w if qa is not qb else 1., cue, a)
                if any(ac.kind in ('flinch', 'wince') for ac in acts):
                    p.pb('spine02').rotation_euler.x -= math.radians(2.4 * settle)
                    p.pb('spine01').rotation_euler.x -= math.radians(1.8 * settle)
                for side in 'LR':
                    bone = 'clavicle.' + side
                    if bone not in p.rig.pose.bones: continue
                    h = getattr(qb, 'left' if side == 'L' else 'right')
                    raised = h is not None and h.kind in ('touch', 'point', 'hold', 'wave')
                    sign = side_sign(side)
                    lift = 0.52 * breath + 0.44 * sign * shift + settle * (2.3 if raised else 1.05) + getattr(ra, 'laugh_bounce', 0.0)
                    # World up axis in the bone's rest frame: avoids a rig roll-dependent shrug.
                    direction = p.rig.data.bones[bone].matrix_local.to_3x3() @ V((0, 1, 0))
                    axis = direction.cross(V((0, 0, 1)))
                    if axis.length > 0.1:
                        axis = p.rig.data.bones[bone].matrix_local.to_3x3().inverted() @ axis.normalized()
                        p.rot(bone, tuple(x * lift for x in axis))
            if not canonical: self.face_values(ra, qa, qb, w, st, u, t, shot, acts)
            if not canonical and qb.blink:   # Zack look round 2: small eye-darts (saccades) on every hold, deterministic per person
                ph = hash(ra.a.name) % 13; k_ = int((t + ph * 0.37) / 0.9)
                ex = ((k_ * 7919 + ph) % 9 - 4) * 0.9; ey = ((k_ * 104729 + ph) % 5 - 2) * 0.8
                if getattr(p, 'hg', None) is not None:     # R5: <= 1 deg, 1-2 per second, loop-locked (728 frames / 14)
                    ph = zlib.crc32(ra.a.name.encode()) % 13; k_ = (int(round(t * FPS)) + ph) // HG_DART_F
                    ex = ((k_ * 7919 + ph) % 5 - 2) / 2 * HG_DART; ey = ((k_ * 104729 + ph) % 3 - 1) * 0.5 * HG_DART
                if getattr(p, 'hg', None) is not None and any(ac.kind == 'eat' and ac.kw.get('beats') for ac in acts):
                    bs_ = p.hg.bite_state(self, ra, u, acts)    # F4: eyes follow the spoon (down at the low point, ~level at the lips)
                    ey += HG_SP_EYE[0] * bs_['gaze'] * (1 - HG_SP_EYE[1] * bs_['p']); ex += HG_SP_EYE[2] * bs_['gaze']
                for eb in ('eye.L', 'eye.R'):
                    if eb in p.rig.pose.bones: p.rot(eb, (ey, 0, ex))
            self._cur.append((ra, qa, qb, w))
        bpy.context.view_layer.update()
        self.solve_hands(shot, u, t, canonical)

    def look_point(self, look):
        if isinstance(look, KW.Actor):
            ra = self.actors.get(look); return self.anchors_light(ra) if ra else None
        if isinstance(look, KW.Anchor): return self.anchor_world(look)
        if isinstance(look, (tuple, list)): return V(look)
        if isinstance(look, KW.FX) and look.obj is not None: return self.FX.world_of(look)
        if look == 'camera': return self.CAM.matrix_world.translation.copy()
        return None
    def anchor_world(self, an):
        ra = self.actors[an.actor]
        if an.part in ('face', 'head'): base = self.anchors_light(ra) if an.part == 'face' else self.bw(ra.p, 'head')
        elif an.part == 'hips': base = self.bw(ra.p, 'spine05')
        elif an.part == 'feet': base = ra.p.rig.matrix_world.translation.copy()
        else: base, _ = self.part_world(ra, an.part)
        R = ra.p.rig.matrix_world.to_3x3().normalized(); o = an.offset
        return base + R @ V((o[0], -o[1], o[2]))

    # ------------------------------------------------------------------ hands
    def hand_goal(self, ra, side, h, u, t):
        """-> (D world point, tip key, shape, R_hand world 3x3, pole world) or None for a free hand"""
        p = ra.p; sg = side_sign(side); R = p.rig.matrix_world.to_3x3().normalized()
        Lp, Fp, Up = R @ V((1, 0, 0)), R @ V((0, -1, 0)), R @ V((0, 0, 1)); out = Lp * sg
        sh = self.bw(p, f'upperarm01.{side}')
        def orient(n_w, f_w):
            n_w = V(n_w).normalized(); f_w = V(f_w); f_w = (f_w - n_w * f_w.dot(n_w))
            if f_w.length < 1e-4: f_w = Up - n_w * Up.dot(n_w)
            f_w.normalize(); info = ra.hand[side]; fl, nl = info['fdir'], info['pnorm']; nl = (nl - fl * nl.dot(fl)).normalized()
            Lm = Matrix((fl, nl, fl.cross(nl))).transposed(); Wm = Matrix((f_w, n_w, f_w.cross(n_w))).transposed()
            return Wm @ Lm.inverted()
        pole = sh + out * 0.45 - Up * 0.6 - Fp * 0.2
        kind = h.kind if h is not None else 'rest'
        seated = walking = False
        for (r2, qa, qb, w) in self._cur:
            if r2 is ra: seated = qb.base in ('sit', 'drive'); walking = qb.base == 'walk'
        if kind == 'rest' and seated: kind = 'lap'
        if kind == 'rest':
            hip = self.bw(p, f'upperleg01.{side}'); D = hip + out * 0.1 - Up * 0.14 + Fp * 0.02
            if self.body_r4 and walking:
                step = sg * math.sin(t * 2 * math.pi * 0.95 - 0.20)
                D += Fp * (0.115 * step) + Up * (0.019 * (1.0 - abs(step)))
            return D, 'palm', 'relaxed', orient(-out, -Up), pole
        if kind == 'lap':
            a_, b_ = self.bw(p, f'upperleg01.{side}'), self.bw(p, f'lowerleg01.{side}'); D = a_.lerp(b_, 0.6) + Up * 0.085 - out * 0.01
            return D, 'palm', 'relaxed', orient(-Up, (b_ - a_)), sh + out * 0.4 - Up * 0.5 + Fp * 0.05
        if kind == 'wheel':
            car = self.set_obj.get('car'); wc = car.wheel.matrix_world.translation.copy() if car is not None else V((0, -0.52, 1.0))
            offset = V((0.17 * sg, 0.03, 0.04)); nrm = V((-0.4 * sg, -1, 0.15)); up = V((0, 0, 1))
            if self.body_r4 and car is not None:
                axis = Matrix.Rotation(car.wheel.rotation_euler.x, 3, 'X') @ up
                spin = Matrix.Rotation(car.wheel.rotation_euler.z, 3, axis)
                offset, nrm, up = spin @ offset, spin @ nrm, spin @ up
            return wc + offset, 'palm', 'hold', orient(nrm, up), sh + out * 0.5 + V((0, 0.3, -0.6))
        if kind == 'wave':
            D = sh + out * 0.3 + Up * 0.32 + Fp * 0.12; a_ = math.radians(22 * math.sin(t * 9)); f_w = Matrix.Rotation(a_, 3, Fp) @ Up
            return D, 'palm', 'open', orient(Fp, f_w), sh + out * 0.5 - Up * 0.3
        if kind == 'hips':
            D = self.bw(p, 'spine05') + out * 0.16 + Up * 0.06
            return D, 'palm', 'open', orient(-out, Fp - Up), sh + out * 0.6 - Fp * 0.3
        if kind in ('point', 'point_fwd'):
            tgt = self.look_point(h.at) if kind == 'point' else sh + Fp * 1.0
            if tgt is None: tgt = sh + Fp
            d = (tgt - sh).normalized(); D = sh + d * 0.6
            return D, 'index', 'point', orient(-Up, d), sh + out * 0.5 - Up * 0.4
        if kind == 'clipboard':
            D = self.bw(p, 'spine02') + Fp * 0.3 + out * 0.02 - Up * 0.08
            return D, 'palm', 'hold', orient(Up * 0.4 - out, -out + Fp * 0.6), sh + out * 0.5 - Up * 0.5
        if kind == 'write':
            other = 'L' if side == 'R' else 'R'; wl = self.bw(p, f'wrist.{other}', True)
            D = wl - out * 0.13 + Fp * 0.05 + Up * 0.03 + V((math.sin(t * 13) * 0.012, 0, math.sin(t * 5) * 0.004))
            return D, 'pinch', 'pinch', orient(-Up, -out * 0.3 + Fp), sh + out * 0.45 - Up * 0.5
        if kind == 'hold':
            if h.at in ('mouth', 'nose', 'ear'):
                part = {'mouth': 'mouth', 'nose': 'nose', 'ear': 'ear_l' if side == 'L' else 'ear_r'}[h.at]
                pt, nr = self.part_world(ra, part); D = pt + nr * 0.07 - Up * 0.05 + out * 0.03
                wrist = orient(-out, -nr + Up * 0.3)
                if self.body_r4 and h.at == 'mouth' and h.prop == 'slushie':
                    # Match the prop's exact wrist-to-cup transform in kwfx. Solve from the
                    # straw tip (the contact) rather than placing the cup at head height.
                    info = ra.hand[side]
                    f = (wrist @ info['fdir']).normalized()
                    n = (wrist @ info['pnorm']).normalized()
                    tip_x, tip_y, tip_z = Q.SLUSH_STRAW_TIP
                    D = pt + nr * 0.008 - f * tip_x - n * (0.025 + tip_y) - f.cross(n) * tip_z
                return D, 'palm', 'hold', wrist, sh + out * 0.4 - Up * 0.6
            if h.at == 'out':
                D = sh + Fp * 0.5 - Up * 0.15 + out * 0.05; return D, 'palm', 'hold', orient(Up, Fp), pole
            if V11 and h.prop == 'can' and h.pad == 'cup':     # cast v1.1 grip_cup: palm toward the midline, knuckles vertical -> cup upright
                D = self.bw(p, 'spine02') + Fp * 0.3 - Up * 0.1 + out * 0.1
                return D, 'palm', 'hold', orient(-out + Up * 0.1, Fp), sh + out * 0.45 - Up * 0.55
            if V11 and h.prop in ('g_pea', 'g_paperclip', 'g_tweezers', 'g_penlight'):     # cast v1.1 grip_pinch / grip_tool: palm toward the midline, thumb on top, tips forward
                D = self.bw(p, 'spine02') + Fp * 0.3 - Up * 0.05 + out * 0.1
                return D, 'palm', 'hold', orient(-out + Up * 0.3, Fp + Up * 0.4), sh + out * 0.45 - Up * 0.55
            if V11 and h.prop == 'g_burger':     # cast v1.1 grip_burger: both hands, palms facing, ~11 cm apart, elbows low
                D = self.bw(p, 'spine02') + Fp * 0.32 - Up * 0.02 + out * BURGER_HALF
                return D, 'palm', 'hold', orient(-out + Up * 0.15, Fp * 0.55 + Up), sh + out * 0.30 - Up * 0.65
            D = self.bw(p, 'spine02') + Fp * 0.3 - Up * 0.12 + out * 0.08
            return D, 'palm', 'hold', orient(Up * 0.6 - out, Fp), sh + out * 0.45 - Up * 0.55
        if kind == 'touch':
            owner = self.actors[h.owner] if isinstance(h.owner, KW.Actor) else ra
            if h.part == 'nose' and h.shape == 'pinch' or (h.kind == 'touch' and h.part == 'nose' and h.shape == 'pinch'):
                pass
            pt, nr = self.part_world(owner, h.part)
            own = owner is ra
            shape = h.shape or 'press2'
            pls = sum(bump(u, c, 0.14) for c in h.pulses) if h.pulses else 0.0
            if shape in ('press2', 'point'):
                tip = 'pads' if shape == 'press2' else 'index'; D = pt + nr * (0.009 - 0.012 * pls)
                upd = (Up if h.part not in ('chest', 'belly', 'back') else -out)
                if h.rub: D = D + upd.cross(nr).normalized() * 0.01 * math.sin(t * 10) * h.rub
                pole2 = sh + out * 0.4 - Up * 0.65 + Fp * (0.1 if own else -0.15)
                return D, tip, shape, orient(-nr, upd), pole2
            if shape == 'cup' and h.prop == 'tissue':      # palm on the side of the cupped tissue, fingers up the cheek
                D = pt + out * 0.115 - nr * 0.01 - Up * 0.035      # hands at the tissue's side edges: back of hand + thumb show, fingers point in toward the nose BEHIND the paper
                return D, 'palm', 'hold', orient(nr * 0.6 + out * 0.8, nr * 0.8 - out * 0.6 + Up * 0.2), sh + out * 0.4 - Up * 0.6 + Fp * 0.05   # 'hold' = curled grip (LESSON: 'cup' splayed the fingers like claws)
            if shape == 'cup':
                D = pt + nr * 0.03 + out * 0.03 - Up * 0.005
                return D, 'palm', 'cup', orient(-nr * 0.6 - out * 0.8, Up), sh + out * 0.35 - Up * 0.6 + Fp * 0.1
            if shape == 'open':
                D = pt + nr * 0.014
                fw = (-out + Up * 0.25) if h.part in ('mouth', 'nose', 'chin') else Up
                return D, 'palm', 'open', orient(-nr, fw), sh + out * 0.35 - Up * 0.6 + Fp * 0.1
            if shape == 'claw':
                D = pt + nr * 0.02
                return D, 'palm', 'claw', orient(-nr, -out + Up), sh + out * 0.45 - Up * 0.55
            if shape == 'pinch':
                if h.part == 'nose':
                    return ('PINCH', owner, side), 'pinch', 'pinch', None, sh + out * 0.55 - Up * 0.5 + Fp * 0.3
                D = pt + nr * 0.008; return D, 'pinch', 'pinch', orient(-out, -nr + Up * 0.2), sh + out * 0.4 - Up * 0.6
            if shape == 'hold':
                D = pt + nr * 0.04; return D, 'palm', 'hold', orient(-nr, Up), pole
            D = pt + nr * 0.01; return D, 'palm', shape, orient(-nr, Up), pole
        return None

    def pinch_goal(self, ra, owner, side):
        """two-point alignment: index tip on the far nostril, thumb on the near nostril"""
        Mh = self.wmat(owner.p, 'head'); far = Mh @ owner.nostril['L' if side == 'R' else 'R']; near = Mh @ owner.nostril[side]
        info = ra.hand[side]['pinch']; il, tl = info['index'], info['thumb']
        a = (tl - il).normalized(); b = (near - far).normalized()
        R1 = a.rotation_difference(b).to_matrix()
        p = ra.p; R = p.rig.matrix_world.to_3x3().normalized(); Fp, Up, out = R @ V((0, -1, 0)), R @ V((0, 0, 1)), R @ V((side_sign(side), 0, 0))
        want = (-Fp * 0.6 - out * 0.6 + Up * 0.35).normalized(); fl = ra.hand[side]['fdir']; best, bR = -9, R1
        for k in range(36):
            Rk = Matrix.Rotation(math.radians(k * 10), 3, b) @ R1; sc = (Rk @ fl).dot(want)
            if sc > best: best, bR = sc, Rk
        D = far.lerp(near, 0.5)
        return D, bR

    def solve_hands(self, shot, u, t, canonical=False):
        jobs = []; self._hshot = shot          # read by the humgen can arm (one elbow pole per shot)
        for (ra, qa, qb, w) in self._cur:
            for side in 'LR':
                ha = getattr(qa, 'left' if side == 'L' else 'right'); hb_ = getattr(qb, 'left' if side == 'L' else 'right')
                goals = []
                for h, wt in ((ha, 1 - w), (hb_, w)):
                    if wt <= 1e-4: continue
                    g = self.hand_goal(ra, side, h, u, t)
                    if g is not None and getattr(ra.p, 'hg', None) is not None: g = ra.p.hg.goal(self, ra, side, h, g, u, t)
                    if g is None: continue
                    D, tip, shape, Rw, pole = g
                    if isinstance(D, tuple) and D and D[0] == 'PINCH': D, Rw = self.pinch_goal(ra, D[1], side)
                    goals.append((D, tip, shape, Rw, pole, wt, h))
                if not goals: continue
                if len(goals) == 1 or goals[0][6] is goals[1][6] or (goals[0][6] is not None and goals[1][6] is not None and goals[0][6].key() == goals[1][6].key()):
                    g = goals[-1] if len(goals) == 1 else goals[1]; D, tip, shape, Rw, pole = g[:5]; shapes = [(shape, 1.0)]
                else:
                    (D0, t0, s0, R0, p0, w0, _), (D1, t1, s1, R1, p1, w1, _) = goals
                    D = D0.lerp(D1, w1); Rw = R0.to_quaternion().slerp(R1.to_quaternion(), w1).to_matrix(); pole = p0.lerp(p1, w1); tip, shape = (t1, s1) if w1 > 0.5 else (t0, s0)
                    shapes = [(s0, w0), (s1, w1)]
                if self.body_r4 and not canonical:
                    breath, shift, settle = ra.beat; sg = side_sign(side)
                    # Secondary elbow arc only; authored hand contacts remain pinned.
                    pole += ra.p.rig.matrix_world.to_3x3() @ V((sg * (0.018 * breath + 0.036 * settle), -0.026 * shift, 0.026 * settle))
                jobs.append((ra, side, D, tip, shape, Rw, pole, shapes, h))
        if not jobs: return
        for ra, side, D, tip, shape, Rw, pole, shapes, h in jobs:
            p = ra.p; tl = ra.hand[side][shape][tip]
            # finger pose (blend by weight)
            if len(shapes) == 1: self.set_shape(p, side, shape)
            else: self._blend_shapes(p, side, shapes)
            if self.body_r4 and not canonical and tip == 'palm' and shape in ('relaxed', 'open'):
                # Ripple through non-contact fingers, never rotate a pinch / prop / pressure pad.
                breath, _, settle = ra.beat
                for fi in (3, 4, 5):
                    flex = (0.9 * breath + 2.0 * settle) * (0.70 + 0.14 * (fi - 3))
                    p.pb(f'finger{fi}-2.{side}').rotation_euler.x += math.radians(flex)
                if getattr(p, 'hg', None) is not None:     # L6: resting fingers not parallel (each a little more curled toward the pinky)
                    for fi, off in zip((2, 3, 4, 5), HG_FINGER_OFF):
                        for jj, kf in ((1, 0.4), (2, 1.0), (3, 0.6)): p.pb(f'finger{fi}-{jj}.{side}').rotation_euler.x += math.radians(off * kf)
            tgt, con, pl = ra.ik[side]; ra._tgt = getattr(ra, '_tgt', {}); ra._tgt[side] = D - (Rw @ tl)
            tgt.location = ra._tgt[side]; pl.location = pole; con.influence = 1.0
        bpy.context.view_layer.update()
        for ra, side, D, tip, shape, Rw, pole, shapes, h in jobs:      # humgen only: closed-loop arm limits on the REAL solved pose
            hg_ = getattr(ra.p, 'hg', None)
            if hg_ is not None and hasattr(hg_, 'post_ik'): hg_.post_ik(self, ra, side, h, shape)
        for it in range(2):
            for ra, side, D, tip, shape, Rw, pole, shapes, h in jobs: self._set_wrist(ra, side, Rw)
            bpy.context.view_layer.update()
            if it == 1: break
            moved = False
            for ra, side, D, tip, shape, Rw, pole, shapes, h in jobs:
                tl = ra.hand[side][shape][tip]; cur = self.wmat(ra.p, f'wrist.{side}') @ tl; err = D - cur
                if err.length > 0.002:
                    ra._tgt[side] = ra._tgt[side] + err; ra.ik[side][0].location = ra._tgt[side]; moved = True
            if not moved: break
            bpy.context.view_layer.update()
        self._hand_jobs = jobs
        if os.environ.get('KW_DEBUG'):
            for ra, side, D, tip, shape, Rw, pole, shapes, h in jobs:
                tl = ra.hand[side][shape][tip]; cur = self.wmat(ra.p, f'wrist.{side}') @ tl
                print(f'HANDDBG {ra.a.name} {side} {shape}/{tip} goal {tuple(round(x, 3) for x in D)} err {(D - cur).length:.3f}')

    def _blend_shapes(self, p, side, shapes):
        vals = {}
        for sh, wt in shapes:
            self.set_shape(p, side, sh)
            for f in range(1, 6):
                for j in (1, 2, 3):
                    b = p.pb(f'finger{f}-{j}.{side}'); e = b.rotation_euler; acc = vals.setdefault(b.name, [0, 0, 0])
                    for i in range(3): acc[i] += e[i] * wt
        for nm, v in vals.items(): p.pb(nm).rotation_euler = v

    def _set_wrist(self, ra, side, Rw):
        p = ra.p; pb = p.pb(f'wrist.{side}'); head_w = self.wmat(p, f'wrist.{side}').translation
        Mw = Matrix.Translation(head_w) @ Rw.to_4x4()
        pb.matrix = p.rig.matrix_world.inverted() @ Mw

    # ================================================================== camera
    def cam_eval(self, shot, u, si=None):
        """-> (pos, target, up, lens, fstop, focus point)"""
        ep = self.ep; c = shot.cam; o = c.o if c else {}
        if si is None: si = ep.shots.index(shot)
        Lsh = shot.length; un = u / Lsh
        if c is None: c = KW.Cam('prop', None)
        if c.kind == 'loop':
            first = ep.shots[0]; un2 = (u - Lsh) / first.length       # arrives exactly at the first shot's start camera
            pos, tgt, up, lens, fs, foc = self.cam_eval_kind(first, first.cam, un2, 0, live=False, at_t=shot.t + u)
            return pos, tgt, up, lens, fs, foc
        return self.cam_eval_kind(shot, c, un, si, live=True, at_t=shot.t + u)

    def cam_eval_kind(self, shot, c, un, si, live=True, at_t=0.0):
        o = c.o; t = at_t; u = un * shot.length
        lens = o.get('lens'); fstop = o.get('fstop'); push = o.get('push', 0.08 if c.kind in ('face', 'medium', 'wide', 'two_shot', 'over_shoulder', 'profile', 'part') else 0.0); orbit = o.get('orbit', 0.0); side = o.get('side', None)   # push default: Zack look slow push-in
        height = o.get('height', 0.0); dist = o.get('dist'); follow = o.get('follow')
        mv = un      # linear progress (continuous for the loop extrapolation)
        if self.camera_r4 and 0.0 < un < 1.0:
            # Partial ease: endpoints and the loop's extrapolation stay fixed.
            mv = 0.72 * un + 0.28 * ease(un)
        def anc(actor, key=None):
            ra = self.actors[actor]; si_ = self.ep.shots.index(shot)
            C0 = self.canon.get((si_, actor))
            if C0 is None: C0 = self.anchors(ra)
            return ra, C0
        def blend_pt(ra, C0, pt0, livefn, fol):
            if not live or fol <= 0: return pt0
            return pt0.lerp(livefn(), fol)
        kind = c.kind
        up = V((0, 0, 1))
        if kind in ('face', 'medium', 'wide', 'low_hero', 'profile', 'part', 'plunge', 'top_down'):
            ra, C0 = anc(c.subj)
            F, Lf, U = C0['fwd'], C0['left'], C0['up']
            bodyU = C0['body_up']
            if abs(bodyU.z) < 0.5:     # lying: frame by the world (camera above)
                pass
            if kind == 'face':
                lens = lens or 46; d = dist or 0.58; fol = 0.5 if follow is None else follow
                A = blend_pt(ra, C0, C0['face'], lambda: self.anchors_light(ra), fol); tgt = A - U * 0.035; sd = 12 if side is None else side
            elif kind == 'medium':
                lens = lens or 38; d = dist or 1.05; fol = 0.3 if follow is None else follow
                A = blend_pt(ra, C0, C0['face'], lambda: self.anchors_light(ra), fol); tgt = A - U * 0.2; sd = 18 if side is None else side
            elif kind == 'wide':
                lens = lens or 28; d = dist or 2.1; fol = 0.0 if follow is None else follow
                A = C0['face']; tgt = A - C0['body_up'] * 0.45; sd = 25 if side is None else side
            elif kind == 'low_hero':
                lens = lens or 26; d = dist or 1.0; fol = 0.2 if follow is None else follow
                A = C0['face']; tgt = A - U * 0.12; sd = 15 if side is None else side; height = height - 0.75
            elif kind == 'profile':
                lens = lens or 42; fol = 0.3 if follow is None else follow
                part = o.get('part', 'face')
                if part == 'face': A = blend_pt(ra, C0, C0['face'], lambda: self.anchors_light(ra), fol); d = dist or 0.62
                elif part == 'neck': A = self.part_world(ra, 'throat')[0].lerp(self.part_world(ra, 'neck_l')[0], 0.5); d = dist or 0.62
                else: A = self.part_world(ra, part)[0]; d = dist or 0.95
                tgt = A - U * 0.02; sd = 90 if side is None else side
            elif kind in ('part', 'plunge', 'top_down'):
                part = o.get('part', 'chest'); fol = 0.6 if follow is None else follow
                pt, nr = self.part_world(ra, part)
                if kind == 'top_down':
                    lens = lens or 35; d = dist or 1.1
                    A = pt; pos = A + V((0, 0, 1)) * d * (1 - push * mv); fwd_ = -V((0, 0, 1)); upv = C0['up'] if abs(C0['up'].z) < 0.8 else C0['fwd']
                    pos = pos + self._shake(t, o, u)
                    fstop = fstop or 4.0; return pos, A, upv, lens, fstop, A
                if kind == 'part' and o.get('glide'):
                    # ONE continuous camera move over the whole film (ep07): visible height at the subject plane from absolute time
                    ta = o['at'] + u if o.get('at') is not None else t
                    lens = lens or 50; vis = KW.glide_eval(o['glide'], ta); d = vis * lens / 36.0
                    y0, y1, T_ = o.get('yaw', (0.0, 0.0, 1.0)); yaw = y0 + (y1 - y0) * (0.5 - 0.5 * math.cos(2 * math.pi * clamp(ta / T_)))   # y0 -> y1 at mid-film -> back to y0 (the loop)
                    s0, s1, sm_ = tuple(o.get('slide', (0.0, 1.0, 0.0)))[:3]; k_ = clamp((ta - s0) / max(s1 - s0, 1e-6)); k_ = k_ * k_ * (3 - 2 * k_)
                    sl_ = o.get('slide', ())
                    if len(sl_) == 5: kb_ = clamp((ta - sl_[3]) / max(sl_[4] - sl_[3], 1e-6)); k_ *= 1.0 - kb_ * kb_ * (3 - 2 * kb_)   # (t0, t1, m, t2, t3): slide back to 0 over t2-t3 (the loop)
                    bk = -C0['body_fwd']; bk = Vector((bk.x, bk.y, 0)).normalized()
                    try: cap = self.wmat(ra.p, o.get('cap_bone', 'lowerleg01.R')).translation.z - pt.z + o.get('cap_dz', 0.0)
                    except Exception: cap = 9.0
                    tgt = pt - Vector((0, 0, 1)) * (sm_ * k_) + Vector((0, 0, 1)) * (o.get('aim_dz', 0.0) + min(0.0, cap - vis / 2))   # frame top never above the knee crease
                    pos = tgt + (Matrix.Rotation(math.radians(yaw), 3, Vector((0, 0, 1))) @ bk) * d
                    fs = fstop or min(22.0, 5.6 * (0.69 / max(d, 0.01)) ** 0.6)
                    return pos, tgt, Vector((0, 0, 1)), lens, fs, tgt
                if kind == 'part':
                    lens = lens or 50; d = dist or 0.36; sd0 = o.get('side', 0.0)
                    pt = pt + V((0, 0, 1)) * o.get('aim_dz', 0.0)     # aim below/above the part (cast sheet: the hanging hand under the wrist)
                    if o.get('front'): nr = C0['body_fwd']                # view from the body's front (cast sheet hands), then 'side' orbits
                    nrm = Matrix.Rotation(math.radians(sd0 + orbit * mv), 3, U) @ nr
                    pos = pt + nrm * d * (1 - push * mv) + U * height; pos += self._shake(t, o, u)
                    return pos, pt, V((0, 0, 1)) if abs(nrm.z) < 0.9 else U, lens, fstop or 2.8, pt   # Zack look round 2: shallow part DOF
                # plunge: from a face close-up into the opening; stops 1.5 cm outside the skin
                lens = lens or 38; d0 = dist or 0.55; k = clamp(mv) ** 2.2
                start = pt + nr * d0 + U * 0.03
                end = pt + nr * 0.015
                pos = start.lerp(end, k); tgt = pt - nr * 0.05
                return pos + self._shake(t, o, u) * (1 - k), tgt, U, lens, fstop or 5.6, pt
            dd = d * (1 - push * mv)
            ang = math.radians(sd + orbit * mv)
            base_f = C0['body_fwd'] if kind in ('wide', 'medium', 'low_hero') else F
            if abs(C0['body_up'].z) < 0.5:     # lying person: orbit around the world vertical above the face
                base_f = V((0, 0, 1)); Uax = V((0, 0, 1))
            dirv = Matrix.Rotation(ang, 3, V((0, 0, 1))) @ base_f
            pos = A + dirv * dd + V((0, 0, 1)) * height + self._shake(t, o, u)
            if o.get('aim'): ao_ = V(o['aim']); pos = pos + ao_; tgt = tgt + ao_     # shift the framing (world offset; bite close-up keeps the burger in frame)
            if self.camera_r4 and kind == 'wide' and shot.set == 'room':
                bounds = getattr(self.set_obj.get('room'), 'camera_bounds', None)
                if bounds and all(bounds[0][i] < tgt[i] < bounds[1][i] for i in range(3)):
                    # A point outside the wall can pass a collision check while filming its
                    # opaque exterior. Dolly inside along the same sight line and widen the lens.
                    lo, hi = bounds; k = 1.0
                    for i in range(3):
                        if pos[i] > hi[i]: k = min(k, (hi[i] - tgt[i]) / (pos[i] - tgt[i]))
                        if pos[i] < lo[i]: k = min(k, (lo[i] - tgt[i]) / (pos[i] - tgt[i]))
                    if k < 1.0: pos = tgt.lerp(pos, k); lens = max(16.0, lens * k)
            return pos, tgt, up, lens, fstop or (2.0 if kind == 'face' else 4.0), A   # Zack look round 2: f/2 face DOF
        if kind in ('two_shot', 'over_shoulder'):
            ra, C0 = anc(c.subj); rb, C1 = anc(o['other'])
            Aa, Ab = C0['face'], C1['face']
            if kind == 'two_shot':
                lens = lens or 32; mid = Aa.lerp(Ab, 0.5); sep = (Ab - Aa); sepH = V((sep.x, sep.y, 0)).length
                nrm = V((-sep.y, sep.x, 0)).normalized()
                avgf = (C0['body_fwd'] + C1['body_fwd']); avgf.z = 0
                if avgf.length < 1e-3: avgf = V((0, -1, 0))
                if nrm.dot(avgf) < 0: nrm = -nrm
                vf = 2 * math.atan(18 / lens); need = max(sepH + 0.55, 0.6) * 16 / 9 * 0.5
                d = dist or max(0.9, need / math.tan(vf / 2) * 0.62)
                sd = o.get('side', 0.0); dirv = Matrix.Rotation(math.radians(sd + orbit * mv), 3, V((0, 0, 1))) @ nrm
                tgt = mid - V((0, 0, 0.12)); pos = tgt + dirv * d * (1 - push * mv) + V((0, 0, 0.1 + height)) + self._shake(t, o, u)
                return pos, tgt, up, lens, fstop or 4.0, mid
            lens = lens or 40; dv = (Ab - Aa); dv.z = 0; dv.normalize(); sgn = o.get('shoulder', 1)
            pos = Aa - dv * 0.42 + C0['body_left'] * 0.2 * sgn + V((0, 0, 0.06 + height)); pos = pos + (Ab - pos) * push * mv + self._shake(t, o, u)
            return pos, Ab - V((0, 0, 0.03)), up, lens, fstop or 4.0, Ab
        if kind == 'xray':
            ra, C0 = anc(c.subj); org = self.FX.organ_point(c.subj, o['organ'])
            view = o.get('view', '34'); F = C0['body_fwd']; Lf = C0['body_left']
            sd = {'profile': 90, 'front': 0, '34': 38, 'back34': 140, 'profile_r': -90}.get(view, 38) if side is None else side
            d = dist or (0.62 if o['organ'] in ('sinus', 'eyes', 'brain', 'airway', 'skull') else 0.95)
            lens = lens or 40; dirv = Matrix.Rotation(math.radians(sd + orbit * mv), 3, V((0, 0, 1))) @ F
            pos = org + dirv * d * (1 - push * mv) + V((0, 0, height)) + self._shake(t, o, u)
            return pos, org, up, lens, fstop or 8.0, org
        if kind == 'macro':
            m = c.subj; info = self.FX.macro_info(m); view = o.get('view', 'hole'); H = info['hole']; M0 = info['origin']
            if view == 'hole':
                lens = lens or 40; pos = H + V((-0.18 + 0.1 * mv, -0.82 + 0.1 * mv + push * 0.4 * mv, 0.14)); tgt = H + V((0, 0, 0.05))
            elif view == 'wide':
                lens = lens or 34; pos = M0 + V((0.75 - 0.3 * mv, -1.75 + 0.45 * mv + push * mv, 0.45 - 0.12 * mv)); tgt = H
            elif view == 'object':
                lens = lens or 40; ob = info['block_pt']; pos = ob + V((0.35 - 0.1 * mv, -0.55 + 0.1 * mv, 0.12)); tgt = ob
                if info['kind'] not in ('bone',): pos = M0 + V((-0.9 + 0.5 * mv, 0.0, 0.0)); tgt = ob
            else:   # inside the lumen, flying along the tube
                lens = lens or 24; pos = M0 + V((-1.3 + 1.0 * mv, 0.02, 0.03)); tgt = pos + V((1, 0, -0.02))
            if side: pos = M0 + Matrix.Rotation(math.radians(side), 3, V((0, 0, 1))) @ (pos - M0)
            pos = pos + self._shake(t, o, u) * 6
            rich_macro = Q.enabled('MACRO')
            if rich_macro and view == 'wide' and info['kind'] not in ('bone',):
                up = Matrix.Rotation(math.radians(17 - 5 * mv), 3, (tgt - pos).normalized()) @ up
            return pos, tgt, up, lens, fstop or (4.5 if rich_macro and view == 'wide' else 5.6), tgt if view != 'hole' else H
        if kind == 'prop':
            f = c.subj if isinstance(c.subj, KW.FX) else next((x for x in shot.fx if x.is_prop()), None)
            org, kindp = self.FX.station(f)
            lens = lens or {'calendar': 45, 'scan': 42, 'skin_block': 40, 'gauge': 44}.get(kindp, 42)
            off = {'calendar': V((0.0, -1.22 + 0.1 * mv + push * 0.4 * mv, 0.0)), 'scan': V((-0.22 + 0.12 * mv, -1.15 + 0.3 * mv + push * 0.3 * mv, 0.06)),
                   'skin_block': V((0.55 - 0.1 * mv, -1.0 + 0.12 * mv, 0.55 - 0.05 * mv)), 'gauge': V((0.1, -0.55 + 0.1 * mv, 0.04))}.get(kindp, V((0, -1, 0)))
            tgt = org + (V((0, 0, 0.02)) if kindp == 'skin_block' else V((0, 0, 0)))
            if kindp == 'earth':   # globe width ~80 % of the 9:16 frame (w1 = half-width at 1 m), slow push, optional raised angle
                import kwearth; lens = o.get('lens', 42); w1 = (18.0 / lens) * 9 / 16; fr = o.get('fill', 0.80)
                d = kwearth.R * math.sqrt(1 + 1 / (fr * w1) ** 2) * (1 + 0.5 * push * 0.12) * (1 - push * 0.12 * mv)
                rz = math.radians(f.o.get('cam_raise', 0.0)); off = V((0, -d * math.cos(rz), d * math.sin(rz)))
            pos = org + off + self._shake(t, o, u) * 3
            return pos, tgt, up, lens, fstop or (8.0 if kindp == 'skin_block' else 5.6), tgt
        if kind == 'path':
            ks = o['keys']; k1 = next((i for i, k in enumerate(ks) if k[0] >= u), len(ks) - 1); k0 = max(0, k1 - 1)
            x = 0.0 if k0 == k1 or u <= ks[k0][0] else min(1.0, (u - ks[k0][0]) / max(1e-6, ks[k1][0] - ks[k0][0])); x = x * x * (3 - 2 * x)
            def kv_(k):
                if isinstance(k[1], KW.Cam):
                    p_, t_, _, l_, _, _ = self.cam_eval_kind(shot, k[1], un, si, live, at_t); return V(p_), V(t_), l_
                return V(k[1]), V(k[2]), k[3]
            (pa, ta, la), (pb, tb, lb) = kv_(ks[k0]), kv_(ks[k1]); pos = pa.lerp(pb, x); tgt = ta.lerp(tb, x); ln = la + (lb - la) * x
            if o.get('shake') or o.get('hits'): pos = pos + self._shake(t, o, u)     # no base drift: the loop's last frame = frame 0
            return pos, tgt, up, ln, fstop or 4.0, tgt
        if kind == 'at':
            pos = V(o['pos']); tgt = V(o['look']); pos = pos.lerp(tgt, push * mv * 0.5) + self._shake(t, o, u)
            return pos, tgt, up, o.get('lens', 40), fstop or 4.0, tgt
        raise ValueError('unknown camera ' + kind)

    def _shake(self, t, o, u):
        if self.camera_r4:
            amp = o.get('shake', 0.0) * 0.0025 + 0.0011
            d = V((math.sin(t * 2.23), 0.38 * math.sin(t * 1.42 + 1), 0.68 * math.sin(t * 1.99 + 2))) * amp
            for h in o.get('hits', ()):
                dt = u - h
                if dt >= 0:
                    k = 0.014 * math.exp(-dt * 7.5)
                    d += V((0.43 * math.sin(dt * 24), 0.18 * math.sin(dt * 28), -math.sin(dt * 29))) * k
            return d
        amp = o.get('shake', 0.0) * 0.006 + 0.0015
        for h in o.get('hits', ()):
            if u >= h: amp += 0.014 * math.exp(-(u - h) * 4.5)
        f = 9.0 + 14 * bool(o.get('hits'))
        return V((math.sin(t * f * 1.3) * amp, math.sin(t * f * 0.7 + 1) * amp * 0.5, math.sin(t * f + 2) * amp))

    def _v11_eyes_to_camera(self):
        """cast v1.1 B4: with look='camera' the HG eyes aim at the lens (their targets normally sit 1.5 m ahead of the eye)"""
        bpy.context.view_layer.update(); cp = self.CAM.matrix_world.translation.copy()
        keep = self.__dict__.setdefault('_eyetgt0', {})
        for ra in self.actors.values():
            if getattr(ra.p, 'hg', None) is None: continue
            for s_ in 'LR':
                e = bpy.data.objects.get(f'{ra.p.name}_hg_eyetgt.{s_}')
                if e is None: continue
                if e.name not in keep: keep[e.name] = e.matrix_basis.copy()
                if getattr(ra, 'cur_look', None) == 'camera': e.matrix_world = Matrix.Translation(cp)
                elif getattr(ra, 'cur_look', None) == 'held' and self.FX.props.get('g_burger') is not None:
                    # aim along the eye->burger ray but 1.2 m out: the same gaze direction without the cross-eyed near convergence
                    bc_ = self.FX.props['g_burger'].matrix_world @ V((0, 0, 0.04)); R3_ = ra.p.rig.matrix_world.to_3x3().normalized(); eo_ = self.bw(ra.p, 'head') + (R3_ @ V((0, -0.08, 0.08)))
                    dl_ = R3_.inverted() @ (bc_ - eo_); yw_ = math.atan2(dl_.x, -dl_.y); pt_ = math.atan2(dl_.z, math.hypot(dl_.x, dl_.y))
                    # bite_fix 1: a burger at the mouth sits almost under the eyes -> irises rolled into the corners. Clamp the gaze
                    # (body frame) to 15 deg sideways and 32 deg down (head 12 + eyes 20): the iris stays mostly visible, lids follow
                    yw_ = max(-math.radians(15), min(math.radians(15), yw_)); pt_ = max(-math.radians(32), min(math.radians(10), pt_))
                    dd_ = R3_ @ V((math.sin(yw_) * math.cos(pt_), -math.cos(yw_) * math.cos(pt_), math.sin(pt_)))
                    e.matrix_world = Matrix.Translation(eo_ + dd_ * 1.2)
                else: e.matrix_basis = keep[e.name]
        bpy.context.view_layer.update()

    def set_cam(self, pos, tgt, up, lens, fstop, foc):
        if os.environ.get('KW_CAMPRINT'): print('CAMPRINT', bpy.context.scene.frame_current, tuple(round(x, 4) for x in pos), tuple(round(x, 4) for x in tgt), round(lens, 2), flush=True)
        cd = self.CAM.data; R = L.aim(V(tgt) - V(pos), up)
        self.CAM.matrix_world = Matrix.Translation(V(pos)) @ R.to_4x4()
        if os.environ.get('KW_CAST', 'v1.1') == 'v1.1':
            # cast v1.1: a face focus point sits inside the head (head bone + 3 cm) -> at f/2 the skin and eyes were soft.
            # Focus on the nearer HG eye when the old focus point is inside that head.
            best = None
            for ra_ in self.actors.values():
                g_ = getattr(ra_.p, 'hg', None)
                if g_ is None: continue
                for s_ in 'LR':
                    pb_ = g_.rig.pose.bones.get(f'eyeball.{s_}')
                    if pb_ is None: continue
                    e_ = g_.rig.matrix_world @ pb_.head
                    if (e_ - V(foc)).length < 0.15 and (best is None or (e_ - V(pos)).length < (best - V(pos)).length): best = e_
            if best is not None: foc = best + (V(pos) - best).normalized() * 0.011
        cd.lens = lens; cd.dof.use_dof = True; cd.dof.aperture_fstop = fstop; cd.dof.focus_distance = max(0.02, (V(foc) - V(pos)).length)

    # ================================================================== visibility
    def visibility(self, shot):
        for a, ra in self.actors.items():
            on = a in shot.cast; xr = shot.xray is a
            for o in ra.p.parts:
                if o.type == 'ARMATURE': continue
                h = (not on) or (xr and o is not ra.p.body)     # LESSON: every part incl. curves (stethoscope, lanyards)
                if o.hide_render != h: o.hide_render = h
            if getattr(ra.p, 'hg', None) is not None: ra.p.hg.xray(xr and on)
            self.FX.xray_body(ra, xr)
        cur = self.ep.spot_of(shot, next(iter(shot.cast.values())).keys[0][1])[0] if shot.cast and shot.set not in KW.SPOTS else shot.set
        for st, c in self.colls.items():
            h = st != shot.set
            if c.hide_render != h: c.hide_render = h
        self.FX.visibility(shot)
        real = shot.set in ('car', 'hospital', 'room', 'street') and self.K is not None
        # LESSON: in a real set hide the episode's own key/rim/fill (the set has its own lights)
        subj = shot.cam.subj if isinstance(shot.cam, KW.Cam) and isinstance(shot.cam.subj, KW.Actor) else (next(iter(shot.cast)) if shot.cast else None)
        lights_on = (not real) and shot.set in ('studio',) or (shot.set in ('car', 'hospital', 'room', 'street') and self.K is None)
        scan = shot.set == 'xray' and Q.enabled('XRAY')
        scan2 = scan and Q.enabled('SCAN2')
        lights_on = lights_on or scan
        self._pl_args = (subj, lights_on, scan, scan2)
        self.place_lights(*self._pl_args)
        w = shot.world or KW.SET_WORLD[shot.set]
        if scan2 and shot.world is None: w = 'scan2'
        if shot.set == 'macro' and shot.world is None and Q.enabled('MACRO') and Q.enabled('MACRO2'): w = 'macro2'
        self.world(w)
        # Zack look: every set lands at frame luma ~0.5-0.65 (room rendered 0.72, hospital 0.43 before; audit 2026-11-22)
        self.S.view_settings.exposure = {'room': -0.5, 'hospital': 0.1}.get(shot.set, 0.0)   # round 2: brighter flat walls -> hospital +0.4 -> +0.1

    def place_lights(self, subj, lights_on, scan, scan2):
        """key/rim/fill follow the subject's head; called again after posing (the first frame of a run saw the unposed rig at the origin)"""
        hb = self.bw(self.actors[subj].p, 'head') if subj is not None else V((0, 0, 1.5))
        R = self.actors[subj].p.rig.matrix_world.to_3x3().normalized() if subj is not None else Matrix.Identity(3)
        for o, off, e in self.PL:
            o.hide_render = not lights_on; o.location = hb + R @ off
            if Q.enabled('PEOPLE2'):
                stage = not scan
                if o is self.PL[0][0]:
                    o.data.size = 1.27 if stage else 1.6
                    if stage: o.location = hb + R @ V((1.02, -1.44, .57)); e = 236
                elif o is self.PL[1][0] and stage: e = 76
                elif o is self.PL[2][0] and stage: e = 19
            o.rotation_euler = (hb - o.location).to_track_quat('-Z', 'Y').to_euler()
            o.data.energy = e * (.49 if scan2 else .84 if scan else 1.)

    BACKDROP = {'room', 'hospital'}          # round 3: sets whose hold shots get Zack's full-frame sky-blue studio gradient
    BD_KINDS = ('face', 'medium', 'two_shot', 'over_shoulder', 'profile', 'low_hero', 'part')
    BD_COL = ((0.10, 0.56, 1.0), (0.015, 0.22, 0.62))   # centre, edge (linear, before AgX Punchy); graded target hue ~190, S 0.35-0.5, V 0.7-0.86
    def backdrop(self, shot, cam, tgt):
        """Zack look round 3: hold shots in a real set get a camera-only emissive sky-blue gradient card behind the cast
        (brighter in the centre, no wall/ceiling band). Invisible to light rays, so the set lighting is unchanged."""
        if not hasattr(self, 'BD'):
            bpy.ops.mesh.primitive_plane_add(size=1.0); o = bpy.context.active_object; o.name = 'kw_backdrop'
            for c in list(o.users_collection): c.objects.unlink(o)
            self.S.collection.objects.link(o)
            for a in ('visible_diffuse', 'visible_glossy', 'visible_transmission', 'visible_volume_scatter', 'visible_shadow'): setattr(o, a, False)
            m = bpy.data.materials.new('kw_backdrop'); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear(); Lk = nt.links.new
            tc = nt.nodes.new('ShaderNodeTexCoord'); mp = nt.nodes.new('ShaderNodeMapping'); mp.inputs['Location'].default_value = (-0.5, -0.42, 0)
            mp.inputs['Scale'].default_value = (1.0, 1.25, 1); Lk(tc.outputs['UV'], mp.inputs['Vector'])
            gr = nt.nodes.new('ShaderNodeTexGradient'); gr.gradient_type = 'SPHERICAL'; Lk(mp.outputs[0], gr.inputs['Vector'])
            cr = nt.nodes.new('ShaderNodeValToRGB'); Lk(gr.outputs['Fac'], cr.inputs['Fac'])
            cr.color_ramp.elements[0].color = (*self.BD_COL[1], 1); cr.color_ramp.elements[1].color = (*self.BD_COL[0], 1); cr.color_ramp.elements[1].position = 0.75
            em = nt.nodes.new('ShaderNodeEmission'); em.name = 'em'; Lk(cr.outputs[0], em.inputs['Color'])
            out = nt.nodes.new('ShaderNodeOutputMaterial'); Lk(em.outputs[0], out.inputs['Surface'])
            o.data.materials.append(m); self.BD = o; self.BD_EM = em
        o = self.BD
        c = shot.cam if isinstance(shot.cam, KW.Cam) else None
        on = (shot.set in self.BACKDROP and c is not None and c.kind in self.BD_KINDS and isinstance(c.subj, KW.Actor) and c.subj in self.actors
              and os.environ.get('KW_BACKDROP', '1') == '1')
        if on and Q.enabled('DRESSING') and c.kind in ('medium', 'two_shot', 'over_shoulder'):
            on = False                 # geography of wide coverage stays visible; blue hero cards remain on tight shots
        if on:
            ra = self.actors[c.subj]; up = ra.p.rig.matrix_world.to_3x3() @ V((0, 0, 1))
            on = abs(up.z) > 0.6          # lying patient: keep the real set
        if not on: o.hide_render = True; return
        cam = V(cam); fwd = (V(tgt) - cam).normalized()
        far = max(((self.bw(self.actors[a].p, 'head') - cam).dot(fwd) for a in shot.cast if a in self.actors), default=1.5)
        far = max(far, (V(tgt) - cam).dot(fwd))     # the card always sits behind the aim point too (part close-ups of a hand below the head)
        D = far + 0.6; ctr = cam + fwd * D
        h = 2 * D * math.tan(self.CAM.data.angle / 2) * 2.4
        o.hide_render = False; o.location = ctr; o.rotation_euler = (-fwd).to_track_quat('Z', 'Y').to_euler(); o.scale = (h, h, 1)
        self.BD_EM.inputs['Strength'].default_value = 2.0 ** (-self.S.view_settings.exposure)

    def rim_light(self, shot, cam):
        """Zack look round 2: one cool-white rim light behind the subject's head, opposite the camera (every person shot)"""
        if not hasattr(self, 'RIM'):
            Ld = bpy.data.lights.new('kw_rim_back', 'AREA'); Ld.size = 0.7; Ld.color = (0.85, 0.93, 1.0)
            self.RIM = bpy.data.objects.new('kw_rim_back', Ld); self.S.collection.objects.link(self.RIM)
        subj = shot.cam.subj if isinstance(shot.cam, KW.Cam) and isinstance(shot.cam.subj, KW.Actor) else (next(iter(shot.cast)) if shot.cast else None)
        if subj is None or subj not in self.actors: self.RIM.hide_render = True; return
        hb = self.bw(self.actors[subj].p, 'head'); d = hb - V(cam); d.z = 0
        if d.length < 1e-3: d = V((0, 1, 0))
        d.normalize(); side = V((-d.y, d.x, 0))
        self.RIM.hide_render = False; self.RIM.location = hb + d * 1.1 + side * 0.45 + V((0, 0, 0.55))
        self.RIM.rotation_euler = (hb - self.RIM.location).to_track_quat('-Z', 'Y').to_euler()
        if shot.set == 'xray' and Q.enabled('XRAY') and Q.enabled('SCAN2'):
            self.RIM.data.energy = 38
        else:
            self.RIM.data.energy = 57 if Q.enabled('PEOPLE2') and shot.set in ('car', 'hospital', 'room', 'street', 'studio') else 70

    def prop_lights(self, origin, sc=1.0, on=True, gain=1.0):
        for o, off, e in self.ML:
            o.hide_render = not on
            if not on: continue
            o.location = V(origin) + off * sc; o.rotation_euler = (V(origin) - o.location).to_track_quat('-Z', 'Y').to_euler()
            o.data.energy = e * sc * sc * gain; o.data.size = (2.5 if e != 300 else 1.5) * sc

    # ================================================================== frame update
    def update(self, t):
        ep = self.ep; shot = ep.shot_at(t); u = t - shot.t; si = ep.shots.index(shot)
        if os.environ.get('KW_BITE_SWEEP'):      # dev: per-shot bite yaw / turn ('shot:yaw:turn,...'), numeric sweeps in one run
            for it_ in os.environ['KW_BITE_SWEEP'].split(','):
                n_, y_, t_ = it_.split(':')
                if n_ == shot.name: os.environ['KW_BITE_YAW'] = y_; os.environ['KW_BITE_TURN'] = t_
        self.render_budget(shot.set)
        self.prop_lights((0, 0, 0), on=False)
        self.visibility(shot)
        ek = getattr(ep, 'exposure_keys', None)      # ep08: [(t, stops)] eased exposure offset on top of the set's (one-shot episodes whose camera moves from a face to a table top)
        if ek:
            v = ek[0][1] if t <= ek[0][0] else ek[-1][1]
            for (t0, v0), (t1, v1) in zip(ek, ek[1:]):
                if t0 <= t <= t1: x = (t - t0) / max(t1 - t0, 1e-6); v = v0 + (v1 - v0) * x * x * (3 - 2 * x); break
            self.S.view_settings.exposure += v
        for st, obj in self.set_obj.items():
            if obj is not None and hasattr(obj, 'update') and st == shot.set:
                try: obj.update(t)
                except Exception as e: print('set update', st, e)
            if st == 'car' and obj is not None and getattr(obj, 'belt', None) is not None:
                drv = any(self.ep.spot_of(shot, ps.keys[0][1])[1] == 'driver' for ps in shot.cast.values()) if shot.set == 'car' else False
                obj.belt.hide_render = not (shot.set == 'car' and drv)
            if st == 'car' and obj is not None and hasattr(obj, 'steer'): obj.steer(math.sin(t * 0.9) * 0.07)
        self.pose_all(shot, u)
        if V11 and any(getattr(ra, 'cur_look', None) == 'camera' for ra in self.actors.values()):
            # cast v1.1 B4: look='camera' read last frame's camera (posing runs before the camera) -> the head turned away.
            # Place the camera for this frame first, then pose again.
            pos, tgt, up, lens, fs, foc = self.cam_eval(shot, u, si); self.set_cam(pos, tgt, up, lens, fs, foc)
            bpy.context.view_layer.update(); self.pose_all(shot, u)
        self.FX.update(shot, u, t)
        for ra in self.actors.values():
            if getattr(ra.p, 'hg', None) is not None: ra.p.hg.frame(self, shot)
        pos, tgt, up, lens, fs, foc = self.cam_eval(shot, u, si)
        self.set_cam(pos, tgt, up, lens, fs, foc)
        if V11: self._v11_eyes_to_camera()
        if V11 and os.environ.get('KW_V11_DBG'):      # what the camera sees at each HG person's lips (hand in front of the mouth?)
            dg_ = bpy.context.evaluated_depsgraph_get(); cp_ = V(pos)
            for ra in self.actors.values():
                hg_ = getattr(ra.p, 'hg', None)
                if hg_ is None or not hasattr(hg_, 'lip_local'): continue
                L0_ = self.wmat(ra.p, 'head') @ hg_.lip_local; R3_ = ra.p.rig.matrix_world.to_3x3().normalized()
                fw_, rt_, up_ = R3_ @ V((0, -1, 0)), R3_ @ V((-1, 0, 0)), V((0, 0, 1))
                for s__ in 'LR':
                    for b__ in ('wrist', 'finger3-3', 'finger1-2'):
                        try:
                            q__ = R3_.inverted() @ (self.bw(ra.p, f'{b__}.{s__}') - L0_); print('V11DBG hand', shot.name, s__, b__, 'mm his-right/fwd/up', round(-q__.x * 1000), round(-q__.y * 1000), round(q__.z * 1000))
                        except Exception as ex__: print('V11DBG hand', b__, ex__)
                print('V11DBG lip world', shot.name, tuple(round(x, 3) for x in L0_), 'fwd', tuple(round(x, 3) for x in fw_), 'his right', tuple(round(x, 3) for x in rt_))
                for nm_, off_ in (('lip_up', up_ * 0.006), ('lip_lo', -up_ * 0.012), ('corner_R', rt_ * 0.024 - fw_ * 0.008), ('corner_L', -rt_ * 0.024 - fw_ * 0.008),
                                  ('chin', -up_ * 0.045 - fw_ * 0.005), ('cheek_R', rt_ * 0.05 + up_ * 0.025 - fw_ * 0.025), ('jaw_R', rt_ * 0.05 - up_ * 0.03 - fw_ * 0.03), ('eye_R', rt_ * 0.032 + up_ * 0.075 - fw_ * 0.01), ('eye_L', -rt_ * 0.032 + up_ * 0.075 - fw_ * 0.01),
                                  ('nose', up_ * 0.035 + fw_ * 0.02), ('cheek_L', -rt_ * 0.05 + up_ * 0.025 - fw_ * 0.025), ('jaw_L', -rt_ * 0.05 - up_ * 0.03 - fw_ * 0.03)):
                    L_ = L0_ + off_; d_ = (L_ - cp_); hit_ = bpy.context.scene.ray_cast(dg_, cp_, d_.normalized(), distance=d_.length + 0.01)
                    nmh_ = hit_[4].name if hit_[0] else None; gap_ = round((hit_[1] - L_).length * 1000) if hit_[0] else None
                    print('V11DBG lipview', shot.name, nm_, 'hit', nmh_, gap_, 'mm', 'BLOCKED' if hit_[0] and gap_ > 15 else 'ok')
        self.cam_walls(shot, V(pos))
        if getattr(self, '_pl_args', None) and getattr(self.ep, 'relight_after_pose', False): self.place_lights(*self._pl_args)
        if os.environ.get('KW_SWAPTEST'):      # ep08 dev: is every point of the bitten arc hidden from the camera (by the hands)?
            dg_ = bpy.context.evaluated_depsgraph_get(); cp_ = V(pos); cut_ = [o_ for o_ in self.S.objects if o_.name.startswith('kwp_bite') and o_.scale.length > 0.01]
            nvis_ = ntot_ = 0; hits_ = {}; vis_px_ = []
            for o_ in self.S.objects:
                if o_.type != 'MESH' or o_.hide_render or not o_.name.startswith(('hamburger_buns', 'kwp_patty', 'kwp_cheese', 'kwp_lettuce')): continue
                ev_ = o_.evaluated_get(dg_); Mw_ = ev_.matrix_world
                for v_ in list(ev_.data.vertices)[::3]:
                    P_ = Mw_ @ v_.co
                    def _in(c_):
                        ax_ = (c_.matrix_world.to_3x3() @ V((0, 0, 1))).normalized(); d0_ = P_ - c_.matrix_world.translation
                        return (d0_ - ax_ * d0_.dot(ax_)).length < c_.dimensions.x / 2 + 0.003
                    if not any(_in(c_) for c_ in cut_): continue
                    ntot_ += 1; d_ = P_ - cp_; dn_ = d_.normalized(); o0_ = cp_.copy(); left_ = d_.length - 0.002
                    for _k in range(6):
                        h_ = self.S.ray_cast(dg_, o0_, dn_, distance=left_)
                        if not h_[0] or not (h_[4].hide_render or any(c.hide_render for c in h_[4].users_collection)): break
                        step_ = (h_[1] - o0_).length + 0.0005; o0_ = o0_ + dn_ * step_; left_ -= step_
                    if not h_[0]:
                        nvis_ += 1; import bpy_extras as _bx; sc_ = _bx.object_utils.world_to_camera_view(self.S, self.S.camera, P_)
                        vis_px_.append((round(sc_.x * 1080), round((1 - sc_.y) * 1920)))
                    else: hits_[h_[4].name] = hits_.get(h_[4].name, 0) + 1
            print('SWAPTEST', round(t * 24), 'arc pts', ntot_, 'visible', nvis_, 'blockers', dict(sorted(hits_.items(), key=lambda kv: -kv[1])[:4]), 'vis px', vis_px_[:40], flush=True)
        self.rim_light(shot, pos)
        self.backdrop(shot, pos, tgt)
        if os.environ.get('KW_LIGHTPRINT'):
            for o_ in self.S.objects:
                if o_.type == 'LIGHT' and not o_.hide_render and all(not c.hide_render for c in o_.users_collection): print('LIGHTPRINT', round(t * 24), o_.name, tuple(round(x, 2) for x in o_.matrix_world.translation), round(o_.data.energy))
        self.FX.update_screen(shot, u, t)
        bpy.context.view_layer.update()

    # ================================================================== checks needing the scene
    def cam_walls(self, shot, pos):
        """A set wall the camera sits in or touches (e.g. a push that starts behind the back wall) is hidden
        from CAMERA rays only, for that frame; shadows, bounce light and every other frame stay the same."""
        for o in getattr(self, '_cam_hidden', ()): o.visible_camera = True
        self._cam_hidden = []
        for o in self.S.objects:
            if o.type != 'MESH' or 'wall' not in o.name.lower() or not self._visible(o): continue
            bb = [o.matrix_world @ V(c) for c in o.bound_box]
            if not all(min(b[i] for b in bb) - 0.01 < pos[i] < max(b[i] for b in bb) + 0.01 for i in range(3)): continue
            if self.inside_geometry(pos, only=o):
                o.visible_camera = False; self._cam_hidden.append(o)
                print(f'KW camwall hide {shot.name} {o.name} (camera rays only)', flush=True)

    def inside_geometry(self, pos, only=None):
        """True if the camera point is inside a visible closed mesh (ray parity, 6 directions)"""
        dg = bpy.context.evaluated_depsgraph_get(); hits = []
        for o in ([only] if only is not None else self.S.objects):
            if o.type != 'MESH' or o.hide_render or o.name == 'kw_backdrop': continue
            if only is None and not o.visible_camera: continue   # not seen by the camera (cam_walls)
            if any(c.hide_render for c in o.users_collection if c is not self.S.collection): continue
            if not self._visible(o): continue
            bb = [o.matrix_world @ V(c) for c in o.bound_box]
            mn = V((min(b.x for b in bb), min(b.y for b in bb), min(b.z for b in bb))); mx = V((max(b.x for b in bb), max(b.y for b in bb), max(b.z for b in bb)))
            if not all(mn[i] - 0.005 < pos[i] < mx[i] + 0.005 for i in range(3)): continue
            ev = o.evaluated_get(dg); Mi = ev.matrix_world.inverted(); lp = Mi @ pos; inside = 0
            try:
                for d in (V((1, 0, 0)), V((-1, 0, 0)), V((0, 1, 0)), V((0, -1, 0)), V((0, 0, 1)), V((0, 0, -1))):
                    ld = (Mi.to_3x3() @ d).normalized(); ok, loc, nrm, idx = ev.ray_cast(lp, ld)
                    if ok and nrm.dot(ld) > 0: inside += 1
            except Exception: continue
            if inside >= 5: hits.append(o.name)
            near = ev.closest_point_on_mesh(lp)
            if near[0] and (ev.matrix_world @ near[1] - pos).length < 0.006: hits.append(o.name + '(touching lens)')
        return hits
    def _visible(self, o):
        def chain(c):
            if c.hide_render: return False
            return True
        for c in o.users_collection:
            if c.hide_render: return False
            for st, sc in self.colls.items():
                if c is sc and sc.hide_render: return False
        return not o.hide_render

    def scene_check(self, frames):
        errs = []
        for f in frames:
            t = f / FPS; self.S.frame_set(f); self.update(t); shot = self.ep.shot_at(t)
            h = self.inside_geometry(self.CAM.matrix_world.translation)
            if h: errs.append(f'frame {f} ({shot.name}): camera inside/touching {", ".join(h[:4])}')
            for a in shot.cast:
                ra = self.actors[a]
                if ra.p.body.hide_render: errs.append(f'frame {f}: {a.name} posed but hidden')
            for a, ra in self.actors.items():
                if a not in shot.cast and not all(o.hide_render for o in ra.p.parts if o.type != 'ARMATURE'): errs.append(f'frame {f}: {a.name} not in the cast but visible')
        return errs

    # ================================================================== main
    def main(self, argv):
        self.build()
        ep = self.ep
        if os.environ.get('KW_HG_AUDIT'):   # sandbox-only build-time tests (tool lives outside the repo)
            sys.path.insert(0, os.environ['KW_HG_AUDIT']); import hg_audit; hg_audit.run(self); return
        if '--check' in argv:
            frames = sorted(set(int(round((s.t + k * s.length) * FPS)) for s in ep.shots for k in (0.02, 0.5, 0.97)))
            errs = self.scene_check(frames)
            for e in errs: print('SCENE CHECK ERROR:', e)
            print('scene check', 'OK' if not errs else f'FAILED ({len(errs)})')
            sys.exit(1 if errs else 0)
        out, i0, i1 = argv[-3], int(argv[-2]), int(argv[-1]); os.makedirs(out, exist_ok=True)
        only = os.environ.get('ONLY'); frames = [int(x) for x in only.split(',')] if only else range(i0, i1)
        for f in frames:
            t1 = time.time(); self.S.frame_set(f); self.update(f / FPS); shot = ep.shot_at(f / FPS)
            if os.environ.get('KW_CAMCHECK', '1') == '1':
                h = self.inside_geometry(self.CAM.matrix_world.translation)
                if h: print(f'WARNING frame {f} ({shot.name}): camera inside/touching {h[:3]}')
            if os.environ.get('KW_DEBUG'):
                cp = self.CAM.matrix_world.translation; fw = self.CAM.matrix_world.to_3x3() @ V((0, 0, -1))
                for o in self.S.objects:
                    if o.type != 'MESH' or o.hide_render: continue
                    bb = [o.matrix_world @ V(c) for c in o.bound_box]; c = sum(bb, V()) / 8; r = max((b - c).length for b in bb)
                    d = (c - cp).dot(fw)
                    if 0 < d < 2.5 and r < 3 and (c - cp - fw * d).length < r + 0.4: print(f'OBJDBG {o.name} d={d:.2f} r={r:.2f} c={tuple(round(x, 2) for x in c)}')
            if os.environ.get('NORENDER'): print(f'frame {f} {shot.name} (no render)'); continue
            self.S.render.filepath = os.path.join(out, f'f{f:04d}.png'); bpy.ops.render.render(write_still=True)
            print(f'frame {f} {shot.name} {time.time() - t1:.1f}s', flush=True)

def window_(t, a, b, fade=0.1): return KW.window(t, a, b, fade)
