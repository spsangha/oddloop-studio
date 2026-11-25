"""KW_HEADS=humgen: the whole person is a Human Generator V4 human (body, head, skin, hair, eyes, teeth, HG clothes),
driven bone-by-bone by the kit's MakeHuman rig.

Opt-in only (env KW_HEADS=humgen). The default 'scan' path never imports this file.
LICENCE: the cast library (.blend files built in the sandbox with the purchased add-on) lives ONLY in the private repo
spsangha/kw-assets (humgen/cast/<slot>.blend). Never commit, cache, upload or log those files from this public repo.

How it works (runs before the kit's calibration, so every mouth/nose/hand/belly anchor is measured on the HG mesh):
- the HG rig is scaled/placed by a similarity fit of its joints onto the MakeHuman joints (hips, shoulders, eyes);
- limb bones get a "fit pose": each HG bone is moved/rotated/scaled so its joints sit exactly on the MakeHuman joints;
- every mapped HG bone is unparented and follows its MakeHuman twin with a Child Of constraint (offset = fit);
- the MakeHuman meshes are hidden for good; person.body becomes the HG body (the x-ray glass body is the HG body);
- kit expressions -> HG ARKit face keys; the MakeHuman belly swell is transferred onto the HG body and clothes;
- the eyes aim where the MakeHuman eye bones aim; the MakeHuman safety glasses are refitted to the HG face.
"""
import os, time
import numpy as np
import bpy, math
import kwkit as KW
from mathutils import Vector as V, Matrix, Quaternion
from mathutils.kdtree import KDTree

LIB = os.environ.get('KW_HG_LIB', '/tmp/kw-assets/humgen/cast')
def on(): return os.environ.get('KW_HEADS', '') == 'humgen'

KEEP = ('glasses', 'clipboard', 'chart')   # chart* = the wrist-parented clipboard parts     # MakeHuman-side parts that stay (refitted); everything else MakeHuman is hidden
S2 = lambda k, w: {k + '_L': w, k + '_R': w}
ARK = {   # kit expression -> HG ARKit shape keys (weight)
    'puff': {'cheekPuff': 1.0, **S2('mouthPress', 0.4), 'mouthClose': 0.2},
    'wide': {**S2('eyeWide', 1.0), **S2('browOuterUp', 0.8), 'browInnerUp': 0.6},
    'squint': {**S2('eyeSquint', 1.0), **S2('eyeBlink', 0.45), **S2('browDown', 0.7), **S2('noseSneer', 0.3), **S2('cheekSquint', 0.5)},
    'twitch': {**S2('noseSneer', 1.0), **S2('mouthUpperUp', 0.4)},
    'open': {'jawOpen': 0.8, **S2('mouthLowerDown', 0.3)},
    'worry': {'browInnerUp': 1.0, **S2('mouthFrown', 0.5)},
    'smile': {**S2('mouthSmile', 1.0), **S2('cheekSquint', 0.35), **S2('mouthDimple', 0.2)},
    'pressed': {**S2('mouthPress', 1.0), 'mouthRollLower': 0.3, 'mouthRollUpper': 0.2},
    'bulge': {**S2('eyeWide', 1.0), **S2('browOuterUp', 1.0), 'browInnerUp': 0.8},
    'grimace': {**S2('mouthStretch', 1.0), **S2('eyeSquint', 0.8), **S2('browDown', 0.8), **S2('mouthUpperUp', 0.4), **S2('noseSneer', 0.4)},
    'blink': {**S2('eyeBlink', 1.0)},
    'talk': {'jawOpen': 0.35, 'mouthFunnel': 0.15},
    'frown': {**S2('browDown', 0.8), **S2('mouthFrown', 0.5)},
    'eyeswell_l': {'eyeBlink_L': 0.7, 'eyeSquint_L': 0.5}, 'eyeswell_r': {'eyeBlink_R': 0.7, 'eyeSquint_R': 0.5},
    'cheekswell_l': {'cheekPuff': 0.3}, 'cheekswell_r': {'cheekPuff': 0.3}, 'lipswell': {'mouthPucker': 0.3},
    'bloat': {'kw_bloat': 1.0},
    'jaw': {'jawOpen': 1.0}, 'lipsclose': {'mouthClose': 1.0},     # humgen spoon bite (ruling d): jaw open + lips closed on the handle
}
# cast v1.1 (KW_CAST=v1.1, kindawild/cast/v11_brief.md part A/B2): six expressions + named jaw openings; unused on v1.0
V11 = os.environ.get('KW_CAST', 'v1.1') == 'v1.1'
ARK.update({
    # tuned on Ben (strip s1 -> s2): HG ARKit keys read weaker than the brief's starting weights
    'x_surprise': {**S2('browOuterUp', 1.4), 'browInnerUp': 1.2, **S2('eyeWide', 1.0), 'jawOpen': 0.6, 'mouthFunnel': 0.3, 'mouthClose': 0.0},
    'x_fear': {'browInnerUp': 1.45, **S2('browDown', 0.25), **S2('browOuterUp', 0.35), **S2('eyeWide', 1.0), **S2('mouthStretch', 1.3),
               **S2('mouthLowerDown', 0.7), 'jawOpen': 0.2},
    'x_disgust': {**S2('noseSneer', 1.0), **S2('mouthUpperUp', 1.0), 'mouthShrugLower': 0.7, **S2('browDown', 0.6), **S2('cheekSquint', 0.7),
                  **S2('eyeSquint', 0.6), **S2('mouthFrown', 0.3)},
    'x_pain': {**S2('browDown', 1.0), **S2('cheekSquint', 1.0), **S2('eyeSquint', 1.0), **S2('eyeBlink', 0.7), **S2('noseSneer', 1.0),
               **S2('mouthUpperUp', 0.8), **S2('mouthStretch', 0.7), 'jawOpen': 0.05},
    'x_wince': {**S2('browDown', 0.9), **S2('eyeSquint', 0.8), 'eyeBlink_L': 0.6, 'eyeBlink_R': 0.5, **S2('noseSneer', 0.7), **S2('mouthPress', 0.3),
                **S2('mouthStretch', 0.45), **S2('cheekSquint', 0.6)},
    'x_laugh': {**S2('mouthSmile', 1.45), **S2('cheekSquint', 1.2), **S2('eyeSquint', 1.0), 'jawOpen': 0.55, **S2('mouthUpperUp', 0.5),
                **S2('mouthDimple', 0.3), 'browInnerUp': 0.3},
    # B2 jaw: jawOpen past 1.0 (slider raised) keeps opening linearly; lips part, lower lip down
    'x_jaw': {'jawOpen': 1.0}, 'x_lips': {**S2('mouthLowerDown', 0.45), **S2('mouthUpperUp', 1.0)},
})
JAW_TAB = {   # jawOpen -> front-teeth gap (mm) on the cast blend (measured: /tmp/b1/jaw_cal.py); x the graft scale in the kit
    'Ben': ((0.0, -2.1), (0.25, 3.3), (0.5, 8.7), (1.0, 18.9), (1.5, 28.1), (1.8, 33.0)),
    'Howard': ((0.0, -3.3), (0.25, 2.1), (0.5, 7.4), (1.0, 17.7), (1.5, 27.1), (1.8, 32.1))}
JAW_TAB['*'] = JAW_TAB['Ben']
def jaw_for_gap(name, mm, scale=1.0):
    t = JAW_TAB.get(name, JAW_TAB['*']); g = mm / scale
    for (j0, g0), (j1, g1) in zip(t, t[1:]):
        if g <= g1: return max(0.0, j0 + (j1 - j0) * (g - g0) / (g1 - g0))
    return t[-1][0]
JAW_MAX = 1.8                     # v1.1 jawOpen ceiling (HG key is linear past 1: ~21 mm incisor gap per unit)
# v1.1 keys allowed past 1.0 (HG brow / smile / stretch keys stay clean to 1.5; lids and lips are capped at 1.0)
KEY_MAX = {'jawOpen': JAW_MAX, 'browInnerUp': 1.5, 'browOuterUp_L': 1.5, 'browOuterUp_R': 1.5, 'mouthSmile_L': 1.5, 'mouthSmile_R': 1.5,
           'mouthStretch_L': 1.5, 'mouthStretch_R': 1.5}
ARK_NAMES = sorted({k for d in ARK.values() for k in d})

# HG bone -> (MakeHuman driver bone, HG point A, MakeHuman point A', HG point B, MakeHuman point B', scale?)
# points: 'h:bone' = bone head, 't:bone' = bone tail, 'm:b1,b2' = mean of heads. fit=None -> Child Of only (rest offset).
def _limb_map():
    m = {'spine': ('root', None), 'spine.001': ('spine04', None), 'spine.002': ('spine02', None), 'spine.003': ('spine01', None),
         'neck': ('neck01', None), 'head': ('head', None)}
    for s in 'LR':
        m.update({
            f'shoulder.{s}': (f'shoulder01.{s}', (f'h:shoulder.{s}', f'h:clavicle.{s}', f'h:upper_arm.{s}', f'h:upperarm01.{s}', True)),
            f'upper_arm.{s}': (f'upperarm02.{s}', (f'h:upper_arm.{s}', f'h:upperarm01.{s}', f'h:forearm.{s}', f'h:lowerarm01.{s}', True)),
            f'forearm.{s}': (f'lowerarm02.{s}', (f'h:forearm.{s}', f'h:lowerarm01.{s}', f'h:hand.{s}', f'h:wrist.{s}', True)),
            f'hand.{s}': (f'wrist.{s}', (f'h:hand.{s}', f'h:wrist.{s}', f'h:f_middle.01.{s}', f'h:finger3-1.{s}', True)),
            f'thigh.{s}': (f'upperleg02.{s}', (f'h:thigh.{s}', f'h:upperleg01.{s}', f'h:shin.{s}', f'h:lowerleg01.{s}', True)),
            f'shin.{s}': (f'lowerleg02.{s}', (f'h:shin.{s}', f'h:lowerleg01.{s}', f'h:foot.{s}', f'h:foot.{s}', True)),
            f'foot.{s}': (f'foot.{s}', (f'h:foot.{s}', f'h:foot.{s}', f'h:toe.{s}', f'm:toe2-1.{s},toe3-1.{s}', False)),
        })
        for k, (hf, mf) in enumerate((('f_index', 2), ('f_middle', 3), ('f_ring', 4), ('f_pinky', 5))):
            m[f'palm.0{k + 1}.{s}'] = (f'metacarpal{k + 1}.{s}', (f'h:palm.0{k + 1}.{s}', f'h:metacarpal{k + 1}.{s}', f'h:{hf}.01.{s}', f'h:finger{mf}-1.{s}', True))
            for j in (1, 2, 3):
                m[f'{hf}.0{j}.{s}'] = (f'finger{mf}-{j}.{s}', (f'h:{hf}.0{j}.{s}', f'h:finger{mf}-{j}.{s}', f't:{hf}.0{j}.{s}', f't:finger{mf}-{j}.{s}', True))
        for j in (1, 2, 3):
            m[f'thumb.0{j}.{s}'] = (f'finger1-{j}.{s}', (f'h:thumb.0{j}.{s}', f'h:finger1-{j}.{s}', f't:thumb.0{j}.{s}', f't:finger1-{j}.{s}', True))
    return m
MAP = _limb_map()


def slot_for(role):
    s = KW.hg_slot(role)
    if not os.path.isfile(os.path.join(LIB, s + '.blend')):   # LESSON: never mix old and new people -> stop the build
        raise RuntimeError(f'humgen: cast slot {s}.blend missing in {LIB} (KW_HEADS=humgen needs every slot)')
    return s


def _umeyama(src, dst):
    src, dst = np.asarray(src, float), np.asarray(dst, float)
    ms, md = src.mean(0), dst.mean(0); a, b = src - ms, dst - md
    U, S, Vt = np.linalg.svd(b.T @ a / len(src)); d = np.eye(3)
    if np.linalg.det(U @ Vt) < 0: d[2, 2] = -1
    R = U @ d @ Vt; s = np.trace(np.diag(S) @ d) / (a ** 2).sum(1).mean(); t = md - s * R @ ms
    return s, R, t


def _sim(s, R, t):
    return Matrix(((*(s * R[0]), t[0]), (*(s * R[1]), t[1]), (*(s * R[2]), t[2]), (0, 0, 0, 1)))


def _verts_world(o, dg=None):
    dg = dg or bpy.context.evaluated_depsgraph_get(); ev = o.evaluated_get(dg); me = ev.to_mesh()
    co = np.empty(len(me.vertices) * 3); me.vertices.foreach_get('co', co); co = co.reshape(-1, 3)
    W = np.array(ev.matrix_world); ev.to_mesh_clear()
    return co @ W[:3, :3].T + W[:3, 3]


class Graft:
    def __init__(self, p, objs):
        self.p = p; self.rig = next(o for o in objs if o.type == 'ARMATURE')
        self.body = next(o for o in objs if o.type == 'MESH' and o.name.startswith('HG_Body'))
        self.meshes = [o for o in objs if o.type == 'MESH']
        self.keys = [o.data.shape_keys.key_blocks for o in self.meshes if o.data.shape_keys]
        self.xray_mods = [m for m in self.body.modifiers if m.type in ('MASK', 'PARTICLE_SYSTEM') and m.show_render]
        self._xr = False

    def face(self, exprs):
        want = {}
        for e, v in exprs.items():
            if v <= 0: continue
            for k, w in ARK.get(e, {}).items(): want[k] = max(want.get(k, 0.0), v * w)
        if V11 and exprs.get('x_gap', 0) > 0:      # B2: named front-teeth gap (mm) -> jawOpen on this head
            want['jawOpen'] = max(want.get('jawOpen', 0.0), jaw_for_gap(self.p.name, exprs['x_gap'], getattr(self, 'scale', 1.0)))
        for kb in self.keys:
            for k in ARK_NAMES:
                b = kb.get(k)
                if b is not None:
                    mx_ = KEY_MAX.get(k, 1.0) if V11 else 1.0
                    nv = min(mx_, want.get(k, 0.0))
                    if mx_ > 1.0 and b.slider_max < mx_: b.slider_max = mx_
                    if abs(b.value - nv) > 1e-4: b.value = nv
        tg = getattr(self, 'v11_tongue', None)
        if tg is not None: tg.value = min(1.0, max(0.0, (want.get('jawOpen', 0.0) - 0.4) * 0.8))     # B2: tongue low at wide jaw

    def frame(self, kr, shot):
        """after kwfx placed the props: HG finger curls + props on the HG grip; clipboard on the left palm, pen tip on the paper."""
        _dress_can(kr)
        self.apply_contacts(kr, shot)
        if getattr(self, 'board', None) is None: return
        ra = self.ra
        jobs = [j for j in getattr(kr, '_hand_jobs', []) if ra.a in shot.cast and j[0] is ra and j[8] is not None]
        cj = next((j for j in jobs if j[8].kind == 'clipboard'), None); wj = next((j for j in jobs if j[8].kind == 'write'), None)
        show = cj is not None
        for o in self.board_objs: o.hide_render = not show
        self.pen.hide_render = not (show and wj is not None)
        if not show: return
        side = cj[1]; M = kr.wmat(self.p, f'wrist.{side}') @ self.Pl[(side, 'board')]
        self.board.matrix_world = M
        if wj is None: return
        R = self.rig.matrix_world; s2 = wj[1]
        P = ((R @ self.rig.pose.bones[f'thumb.03.{s2}'].tail) + (R @ self.rig.pose.bones[f'f_index.03.{s2}'].tail)) / 2
        nb = (M.to_3x3() @ V((0, 1, 0))).normalized(); front = M @ V((0, BOARD_T / 2 + PAPER_T, 0))
        T = P - nb * (P - front).dot(nb)
        P = self._pen_clear(s2, T, P)      # C4: no finger through the pen (thumb / index / middle pads rest on it)
        ax = P - T; Lp = max(ax.length, 0.005); z = ax.normalized(); x = z.orthogonal().normalized(); y = z.cross(x)
        Mp = Matrix((x, y, z)).transposed().to_4x4() @ Matrix.Diagonal((1, 1, Lp + 0.09, 1)); Mp.translation = T
        self.pen.matrix_world = Mp
        self.pen_state = (T, P, Lp)

    def _finger_skin(self, side):
        """world positions of the thumb / index / middle distal + middle phalanx skin verts by linear-blend skinning
        (the armature modifier's own maths; no shape key moves the fingers), cheap enough for every writing frame"""
        ck = getattr(self, '_fsk', {})
        if side not in ck:
            vg = {g.index: g.name for g in self.body.vertex_groups}; names = [f'{f}.0{k}.{side}' for f in ('thumb', 'f_index', 'f_middle') for k in (2, 3)]
            rows = []
            for v in self.body.data.vertices:
                ws = [(vg[g.group], g.weight) for g in v.groups if g.weight > 0.01 and vg.get(g.group) in self.rig.pose.bones]
                fn_ = next((nm.split('.')[0] for n, w_ in ws for nm in names if n == nm and w_ > 0.5), None)
                if fn_ is not None: rows.append((v.index, ws)); self._fskn = getattr(self, '_fskn', {}); self._fskn.setdefault(side, []).append(fn_)
            sk = self.body.data.shape_keys          # HG body shape keys move the hands (proportions): mix them like the mesh does
            if sk:
                kb = sk.key_blocks; base = kb[0]
                rows = [(V(base.data[i].co) + sum(((b.data[i].co - b.relative_key.data[i].co) * b.value for b in kb[1:] if b.value != 0.0 and not b.mute), V()), ws) for i, ws in rows]
            else: rows = [(V(self.body.data.vertices[i].co), ws) for i, ws in rows]
            ck[side] = rows; self._fsk = ck
        R = self.rig.matrix_world; Wb = self.body.matrix_world; Mi = (R.inverted() @ Wb); out = []
        for co, ws in ck[side]:
            c = Mi @ co; acc = V(); tw = 0.0
            for n, w_ in ws:
                pb = self.rig.pose.bones[n]; acc += w_ * ((pb.matrix @ pb.bone.matrix_local.inverted()) @ c); tw += w_
            out.append(R @ (acc / tw))
        return out

    def _pen_clear(self, side, T, P, r=0.0028, gap=0.0006):
        """rotate the pen about its paper tip T (move its grip point P in the plane across the pen) by the smallest offset
        that leaves every thumb / index / middle skin vert >= r + gap from the pen axis (1 mm grid, 16 mm disc)"""
        pts = np.array([list(q) for q in self._finger_skin(side)]); T_ = np.array(list(T)); z0 = (P - T).normalized()
        u_ = z0.orthogonal().normalized(); v_ = z0.cross(u_)
        def worst(Pc):
            z = Pc - T_; L = np.linalg.norm(z); z = z / L; d = pts - T_; t_ = d @ z
            m = (t_ > 0) & (t_ < L + 0.03)
            if not m.any(): return 0.0
            rad = np.linalg.norm(d[m] - np.outer(t_[m], z), axis=1); return float(max(0.0, (r + gap - rad).max()))
        P0 = np.array(list(P)); w0 = worst(P0)
        fn = np.array(self._fskn[side]); th, ix = fn == 'thumb', fn == 'f_index'
        def gaps(Pc):
            z = Pc - T_; L = np.linalg.norm(z); z = z / L; d = pts - T_; t_ = d @ z; m = (t_ > 0) & (t_ < L + 0.03)
            g = np.full(len(pts), 1.0); g[m] = np.linalg.norm(d[m] - np.outer(t_[m], z), axis=1) - r
            return g[th].min() if th.any() else 0.0, g[ix].min() if ix.any() else 0.0, g.min()
        if os.environ.get('KW_HG_AUDIT'): print('AUDIT penclear', side, len(pts), 'first depth mm', round(1000 * w0, 2))
        best = None      # C4: no finger inside the pen (all >= gap) AND thumb + index pads resting on it (aim 1 mm)
        for a in range(-16, 17):
            for b in range(-16, 17):
                o = 0.001 * (a * np.array(list(u_)) + b * np.array(list(v_))); n_ = np.linalg.norm(o)
                if n_ > 0.016: continue
                gt, gi, gm = gaps(P0 + o)
                if gm < gap - 1e-5: continue
                c = (gt - 0.001) ** 2 + (gi - 0.001) ** 2 + 1e-3 * n_ ** 2
                if best is None or c < best[0]: best = (c, o, gt, gi)
        if best is None: return P
        if os.environ.get('KW_HG_AUDIT'): print('AUDIT penclear moved mm', round(1000 * float(np.linalg.norm(best[1])), 1), 'thumb/index gap mm', round(1000 * best[2], 1), round(1000 * best[3], 1))
        return V(tuple(P0 + best[1]))

    def xray(self, on):
        """x-ray shots: the HG body is the glass body -> no clothing masks (whole silhouette), no hair strands."""
        if on == self._xr: return
        self._xr = on
        for m in self.xray_mods: m.show_render = not on; m.show_viewport = not on


def _pt(spec, hg, kr, p, Sim=None):
    k, n = spec.split(':', 1)
    if k == 'm': return sum((_pt('h:' + x, hg, kr, p, Sim) for x in n.split(',')), V()) / len(n.split(','))
    if hg is not None:
        b = hg.data.bones[n]; return (Sim if Sim is not None else hg.matrix_world) @ (b.tail_local if k == 't' else b.head_local)
    return kr.bw(p, n, k == 't')


def graft(kr, ra, role):
    """Called before kwrun._calibrate. kr: kwrun Runtime (reset/rig_at/bw/wmat), ra: runtime actor. Returns Graft or None."""
    slot = slot_for(role)
    p = ra.p
    kr.reset(p); kr.rig_at(p, (0, 0, 0), 0); bpy.context.view_layer.update()
    coll = p.body.users_collection[0] if p.body.users_collection else bpy.context.scene.collection
    with bpy.data.libraries.load(os.path.join(LIB, slot + '.blend'), link=False) as (src, dst):
        dst.objects = list(src.objects)
    objs = [o for o in dst.objects if o is not None]
    for o in objs: coll.objects.link(o)
    G = Graft(p, objs); rig, body = G.rig, G.body
    rig.name = f'{p.name}_HGrig'
    bpy.context.view_layer.update()
    # --- 1. global similarity: HG joints -> MakeHuman joints (rest, MakeHuman rig at the origin)
    pairs = [('h:thigh.L', 'h:upperleg01.L'), ('h:thigh.R', 'h:upperleg01.R'), ('h:upper_arm.L', 'h:upperarm01.L'),
             ('h:upper_arm.R', 'h:upperarm01.R'), ('h:eyeball.L', 'h:eye.L'), ('h:eyeball.R', 'h:eye.R'),
             ('h:foot.L', 'h:foot.L'), ('h:foot.R', 'h:foot.R')]
    src = [list(_pt(a, rig, kr, p)) for a, b in pairs]; dstp = [list(_pt(b, None, kr, p)) for a, b in pairs]
    s, R, t = _umeyama(src, dstp)
    G.scale = s
    # the global fit lives in the fit pose, not on the rig object (Child Of + object scale double-counts the scale)
    Sim = _sim(s, R, t) @ rig.matrix_world
    res = [(V(_pt(a, rig, kr, p, Sim)) - V(d)).length for (a, b), d in zip(pairs, dstp)]
    print(f'humgen {p.name}: slot {slot} global scale {s:.3f} joint residual cm', [round(100 * r, 1) for r in res])
    G.rest_world = {b.name: (Sim @ b.head_local, Sim @ b.tail_local, Sim @ b.matrix_local) for b in rig.data.bones}
    # --- 2. unparent the mapped bones (each follows its own MakeHuman twin)
    bpy.context.view_layer.objects.active = rig
    for o in bpy.context.selected_objects: o.select_set(False)
    rig.select_set(True)
    bpy.ops.object.mode_set(mode='EDIT')
    # corrective-driver probes: a non-deform copy of each driven bone, kept under the bone's original parent,
    # so its LOCAL rotation stays the true joint angle after the driven bone is unparented (drivers stay alive)
    drv = sorted({t.bone_target for o in objs if o.type == 'MESH' and o.data.shape_keys and o.data.shape_keys.animation_data
                  for d in o.data.shape_keys.animation_data.drivers for v in d.driver.variables for t in v.targets
                  if v.type == 'TRANSFORMS' and t.bone_target})
    probes = {}
    for hb in drv:
        eb = rig.data.edit_bones.get(hb)
        if eb is None or eb.parent is None: continue
        pr = rig.data.edit_bones.new('kwp_' + hb); pr.head, pr.tail, pr.roll = eb.head.copy(), eb.tail.copy(), eb.roll
        pr.parent = eb.parent; pr.use_deform = False; probes[hb] = pr.name
    for hb in MAP:
        eb = rig.data.edit_bones.get(hb)
        if eb: eb.use_connect = False; eb.parent = None
    bpy.ops.object.mode_set(mode='OBJECT')
    for hb, pn in probes.items():
        # swing only (4.12 puffed shoulders): a copied rotation also carries the arm twist, which the Euler
        # LOCAL read turns into false 'raise' angles -> the probe aims at the driven bone's tail instead
        c = rig.pose.bones[pn].constraints.new('DAMPED_TRACK'); c.target = rig; c.subtarget = hb; c.head_tail = 1.0; c.track_axis = 'TRACK_Y'
    nd = 0
    for o in objs:
        if o.type != 'MESH' or not o.data.shape_keys or not o.data.shape_keys.animation_data: continue
        for d in o.data.shape_keys.animation_data.drivers:
            for v in d.driver.variables:
                for t in v.targets:
                    if v.type == 'TRANSFORMS' and t.bone_target in probes: t.id = rig; t.bone_target = probes[t.bone_target]; nd += 1
    print(f'humgen {p.name}: corrective drivers kept, {nd} targets on {len(probes)} probes')
    # --- 3. fit pose (world targets from the rest data, so the order does not matter)
    Mi = rig.matrix_world.inverted(); fit = {}
    for hb, (mb, f) in MAP.items():
        b = rig.data.bones.get(hb)
        if b is None or p.rig.pose.bones.get(mb) is None: print('humgen map skip', hb, mb); continue
        Mr = Sim @ b.matrix_local
        if f is None: W = Mr
        else:
            A, A2 = _pt(f[0], rig, kr, p, Sim), _pt(f[1], None, kr, p); B, B2 = _pt(f[2], rig, kr, p, Sim), _pt(f[3], None, kr, p)
            q = (B - A).rotation_difference(B2 - A2); k = (B2 - A2).length / max((B - A).length, 1e-6) if f[4] else 1.0
            W = Matrix.Translation(A2) @ q.to_matrix().to_4x4() @ Matrix.Scale(k, 4) @ Matrix.Translation(-A) @ Mr
        sd_ = hb[-1]
        if ARM_SHIFT.get((p.name, sd_)) and hb.endswith('.' + sd_) and hb.split('.')[0] in ARM_CHAIN:
            # 4.2 allows joint positions to differ (~5 cm), rotations must not: the idle arm sits ARM_SHIFT further out so
            # it rests against the (wider) HG torso instead of through the tee side (overlap test)
            W = Matrix.Translation(V((math.copysign(ARM_SHIFT[(p.name, sd_)], W.translation.x), 0, 0))) @ W
        fit[hb] = (mb, W)
    for hb, (mb, W) in fit.items():
        pb = rig.pose.bones[hb]
        for c in list(pb.constraints): pb.constraints.remove(c)
        pb.matrix = Mi @ W
    bpy.context.view_layer.update()
    for hb, (mb, W) in fit.items():
        pb = rig.pose.bones[hb]
        c = pb.constraints.new('CHILD_OF'); c.name = 'kw_follow'; c.target = p.rig; c.subtarget = mb
        c.inverse_matrix = (p.rig.matrix_world @ p.pb(mb).matrix).inverted()
    bpy.context.view_layer.update()
    G.fit = {hb: (mb, (p.rig.matrix_world @ p.pb(mb).matrix).inverted() @ W) for hb, (mb, W) in fit.items()}
    # --- 4. eyes aim where the MakeHuman eyes aim
    for s_ in 'LR':
        eb = rig.pose.bones.get(f'eyeball.{s_}'); me = p.pb(f'eye.{s_}')
        if eb is None or me is None: continue
        e = bpy.data.objects.new(f'{p.name}_hg_eyetgt.{s_}', None); coll.objects.link(e)
        e.parent = p.rig; e.parent_type = 'BONE'; e.parent_bone = me.name
        bpy.context.view_layer.update(); hw = rig.matrix_world @ eb.head
        e.matrix_world = Matrix.Translation(hw + V((0, -1.5, 0)))
        c = eb.constraints.new('DAMPED_TRACK'); c.target = e; c.track_axis = 'TRACK_Y'
    # --- 5. MakeHuman meshes out (glasses / clipboard stay, refitted), HG meshes in; person.body = HG body
    p.mh_body = p.body
    # old face height for the camera face anchor (kit nose method on the MakeHuman mesh, head-local; read before it is hidden)
    bpy.context.view_layer.update(); Mh = kr.wmat(p, 'head'); hb = Mh.translation; old = _verts_world(p.body, bpy.context.evaluated_depsgraph_get())
    m = (np.abs(old[:, 0] - hb.x) < 0.012) & (old[:, 2] - hb.z > -0.02) & (old[:, 2] - hb.z < 0.12)
    G.old_nose_local = Mh.inverted() @ V(old[m][np.argmin(old[m][:, 1])])
    for o in list(p.parts):
        if o.type == 'ARMATURE' or o.type == 'EMPTY': continue
        if any(k in o.name.lower() for k in KEEP): continue
        o.hide_render = True; o.hide_viewport = True; p.parts.remove(o)
    p.body.hide_render = True
    p.body = body
    p.parts.extend(G.meshes)
    _bloat(p, G)
    _fit(p, G)
    _hide_under(p, G)
    _skin_tone(p, G)
    _outfit_color(p, G)
    if V11:
        import cast_v11; cast_v11.apply(kr, p, G)
    _glasses(kr, p, G)
    if role.get('clipboard'): G.pen = _pen(coll); G.board, G.board_objs = _board(coll)
    p.hg = G
    return G


def _dress_can(kr):
    """the kit can is a plain red cylinder: give it silver lids + rims and a printed label band so it reads as a soda can"""
    import bmesh
    ob = kr.FX.props.get('can') if hasattr(kr, 'FX') else None
    if ob is None or ob.get('kw_hg_can'): return
    ob['kw_hg_can'] = 1
    def M(name, build):
        m = bpy.data.materials.get(name)
        if m is None: m = bpy.data.materials.new(name); m.use_nodes = True; build(m)
        return m
    def silver(m):
        b = m.node_tree.nodes['Principled BSDF']; b.inputs['Base Color'].default_value = (0.78, 0.79, 0.8, 1); b.inputs['Metallic'].default_value = 1.0; b.inputs['Roughness'].default_value = 0.22
    def label(m):
        nt = m.node_tree; b = nt.nodes['Principled BSDF']; tc = nt.nodes.new('ShaderNodeTexCoord'); sx = nt.nodes.new('ShaderNodeSeparateXYZ')
        ramp = nt.nodes.new('ShaderNodeValToRGB'); ramp.color_ramp.interpolation = 'CONSTANT'; el = ramp.color_ramp.elements
        el[0].position = 0.0; el[0].color = (0.62, 0.03, 0.04, 1); el[1].position = 0.40; el[1].color = (0.95, 0.95, 0.93, 1)
        e = el.new(0.47); e.color = (0.62, 0.03, 0.04, 1); e = el.new(0.53); e.color = (0.95, 0.95, 0.93, 1); e = el.new(0.60); e.color = (0.62, 0.03, 0.04, 1)
        nt.links.new(tc.outputs['Generated'], sx.inputs[0]); nt.links.new(sx.outputs['Z'], ramp.inputs['Fac']); nt.links.new(ramp.outputs['Color'], b.inputs['Base Color'])
        b.inputs['Metallic'].default_value = 0.35; b.inputs['Roughness'].default_value = 0.3
    me = ob.data
    while len(me.materials) < 1: me.materials.append(None)
    me.materials[0] = M('kw_hg_can_label', label); me.materials.append(M('kw_hg_can_silver', silver))
    def dark(m):
        b = m.node_tree.nodes['Principled BSDF']; b.inputs['Base Color'].default_value = (0.015, 0.012, 0.012, 1); b.inputs['Roughness'].default_value = 0.6
    me.materials.append(M('kw_hg_can_hole', dark))
    bm = bmesh.new(); bm.from_mesh(me); r0, h0 = GRIP['can']
    def part(rad1, rad2, dep, Mx, mat, seg=48):
        res = bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=rad1, radius2=rad2, depth=dep, matrix=Mx)
        for f in {f for v in res['verts'] for f in v.link_faces}: f.material_index = mat; f.smooth = True
    T = lambda x, y, z: Matrix.Translation((x, y, z))
    S = lambda sx, sy: Matrix.Diagonal((sx, sy, 1, 1))
    # TOP (+z): rolled rim ring, recessed silver lid, the drinking opening toward local +y (the lip side) and the pull tab
    part(r0 + 0.0006, r0 + 0.0006, 0.005, T(0, 0, h0 / 2 - 0.0022), 1)
    part(r0 * 0.86, r0 * 0.86, 0.0016, T(0, 0, h0 / 2 + 0.0004), 1)
    part(0.0045, 0.0045, 0.0005, T(0, r0 * 0.52, h0 / 2 + 0.0013) @ S(1.0, 0.75), 2, 24)
    part(0.0065, 0.0065, 0.0006, T(0, r0 * 0.12, h0 / 2 + 0.0015) @ S(0.62, 1.0), 1, 24)
    # BOTTOM (-z): narrower silver base (tapered neck + recessed dome), not a copy of the top
    part(r0 * 0.80, r0 + 0.0004, 0.007, T(0, 0, -h0 / 2 + 0.0035), 1)
    part(r0 * 0.70, r0 * 0.70, 0.0012, T(0, 0, -h0 / 2 + 0.0002), 1)
    bm.to_mesh(me); bm.free()


def _skin_tone(p, G):
    want = SKIN_TONE.get(p.name, {})
    for m in G.body.data.materials:
        if m is None or not m.use_nodes: continue
        for n in m.node_tree.nodes:
            if n.type == 'GROUP' and n.node_tree and 'Skin_Tone' in n.node_tree.name:
                for k, v in want.items():
                    if k in n.inputs and not n.inputs[k].is_linked: n.inputs[k].default_value = v
                print('humgen skin tone', p.name, {k: round(n.inputs[k].default_value, 2) for k in ('Tone', 'Redness', 'Saturation') if k in n.inputs})


OUTFIT_COLOR = {'Howard': {'SHIRT': (1.0, 1.0, 1.0), 'JEANS': (0.11, 0.115, 0.12)}, 'Ben': {'SHIRT': (0.62, 1.0, 0.84)}}   # 4.4: old look = white shirt + grey trousers under the coat


def _outfit_color(p, G):
    for o in G.meshes:
        for tag, rgb in OUTFIT_COLOR.get(p.name, {}).items():
            if tag not in o.name.upper(): continue
            for i, m in enumerate(o.data.materials):
                if m is None or not m.use_nodes: continue
                for n in m.node_tree.nodes:
                    if n.type == 'GROUP' and 'Main Color_C0' in n.inputs: n.inputs['Main Color_C0'].default_value = (*rgb, 1.0)
            print('humgen outfit colour', p.name, o.name, rgb)


def _bloat(p, G):
    """MakeHuman 'stomach-pregnant' delta -> HG body + clothes (nearest MakeHuman vertex, rest pose, world space)."""
    mh = p.mh_body; kb = mh.data.shape_keys.key_blocks if mh.data.shape_keys else None
    k = next((x for x in (kb or []) if 'stomach-pregnant' in x.name), None)
    if k is None: print('humgen bloat: no MakeHuman key'); return
    n = len(mh.data.vertices)
    a = np.empty(n * 3); b = np.empty(n * 3); k.data.foreach_get('co', a); k.relative_key.data.foreach_get('co', b)
    M3 = np.array(mh.matrix_world.to_3x3()); d = (a - b).reshape(-1, 3) @ M3.T
    W = np.array(mh.matrix_world); base = b.reshape(-1, 3) @ W[:3, :3].T + W[:3, 3]
    big = np.where(np.linalg.norm(d, axis=1) > 1e-5)[0]
    kd = KDTree(n); [kd.insert(base[i], i) for i in range(n)]; kd.balance()
    for o in G.meshes:
        if o.name.startswith(('HG_Eyes', 'HG_Teeth')): continue
        if o.data.shape_keys is None: o.shape_key_add(name='Basis', from_mix=False)
        ks = o.data.shape_keys.key_blocks
        nk = o.shape_key_add(name='kw_bloat', from_mix=False); nk.slider_max = 1.5
        Mw = o.matrix_world; Mi3 = np.array(Mw.to_3x3().inverted())
        co = np.empty(len(o.data.vertices) * 3); ks[0].data.foreach_get('co', co); co = co.reshape(-1, 3)
        W2 = np.array(Mw); cw = co @ W2[:3, :3].T + W2[:3, 3]
        out = co.copy(); moved = 0
        for i, c in enumerate(cw):
            _, j, dist = kd.find(c)
            if dist < 0.06 and np.linalg.norm(d[j]) > 1e-5:
                side_fall = min(1.0, max(0.0, (0.19 - abs(c[0])) / 0.05))     # sleeves / arms do not swell (4.12)
                if side_fall <= 0: continue
                out[i] += Mi3 @ d[j] * max(0.0, 1 - dist / 0.06) * side_fall; moved += 1
        nk.data.foreach_set('co', out.ravel())
        print('humgen bloat', p.name, o.name, moved)
    G.keys = [o.data.shape_keys.key_blocks for o in G.meshes if o.data.shape_keys]


def _mix_world(o):
    """rest-pose mixed shape (all key values) in world space"""
    kb = o.data.shape_keys.key_blocks if o.data.shape_keys else None; n = len(o.data.vertices)
    co = np.empty(n * 3)
    if kb is None: o.data.vertices.foreach_get('co', co); co = co.reshape(-1, 3)
    else:
        kb[0].data.foreach_get('co', co); co = co.reshape(-1, 3); out = co.copy(); a = np.empty(n * 3); b = np.empty(n * 3)
        for k in kb[1:]:
            if k.mute or abs(k.value) < 1e-4 or k.name == 'kw_bloat': continue
            k.data.foreach_get('co', a); k.relative_key.data.foreach_get('co', b); out += k.value * (a - b).reshape(-1, 3)
        co = out
    W = np.array(o.matrix_world); return co @ W[:3, :3].T + W[:3, 3]


def _fit(p, G):
    """4.12: sleeves and shoulders lie on the arm like cloth: shape key kw_fit pulls tee / coat sleeve verts that stand
    off the arm by more than FIT_GAP toward the nearest body (or inner cloth) point, keeping FIT_GAP (rest pose)."""
    bw = _mix_world(G.body); kd = KDTree(len(bw)); [kd.insert(c, i) for i, c in enumerate(bw)]; kd.balance()
    order = sorted([o for o in G.meshes if any(t in o.name.upper() for t in ('SHIRT', 'COAT'))], key=lambda o: 'COAT' in o.name.upper())
    inner = []
    xs = bw[:, 0]; cx = float(np.median(xs))
    for o in order:
        under = 'SHIRT' in o.name.upper() and any('COAT' in x.name.upper() for x in G.meshes)
        gap = FIT_GAP['COAT' if 'COAT' in o.name.upper() else ('UNDER' if under else 'SHIRT')]
        cw = _mix_world(o); n = len(cw)
        kds = [kd] + inner
        ec = {}
        for pl in o.data.polygons:
            vs = list(pl.vertices)
            for a_, b_ in zip(vs, vs[1:] + vs[:1]): e = (min(a_, b_), max(a_, b_)); ec[e] = ec.get(e, 0) + 1
        bnd = sorted({v for e, c_ in ec.items() if c_ == 1 for v in e}); kb_ = KDTree(max(1, len(bnd)))
        for i, v in enumerate(bnd): kb_.insert(cw[v], i)
        kb_.balance()
        tgt = cw.copy(); moved = 0; mx = 0.0
        for i, c in enumerate(cw):
            ax = abs(c[0] - cx); wgt = min(1.0, max(0.0, (ax - FIT_X0) / 0.05))       # arms / shoulders / torso sides under the arms; front untouched
            if under: wgt = 1.0                                                       # shirt under the coat: whole shirt lies on the body
            if bnd: wgt *= min(1.0, max(0.0, (kb_.find(c)[2] - 0.03) / 0.04))     # cuffs / hems keep their width (no cut at the wrist)
            if wgt <= 0: continue
            best = None
            for t in kds:
                q, j, dd = t.find(c)
                if best is None or dd < best[1]: best = (np.array(q), dd)
            q, dd = best
            if dd > gap and dd < 0.06:
                mvd = (dd - gap) * FIT_K * wgt; tgt[i] = c + (q - c) / dd * mvd; moved += 1; mx = max(mx, mvd)
        if 'COAT' in o.name.upper():      # clearance: the coat never sits closer than FIT_CLEAR to the body / shirt (closure, sides)
            pushed = 0
            for i in range(n):
                c = tgt[i]; best = None
                for t in kds:
                    q, j, dd = t.find(c)
                    if best is None or dd < best[1]: best = (np.array(q), dd)
                q, dd = best
                if 1e-6 < dd < FIT_CLEAR:
                    # outward = away from the inner surface point (direction q->c)
                    tgt[i] = q + (c - q) / dd * FIT_CLEAR; pushed += 1
            print(f'humgen fit {p.name} {o.name}: {pushed} verts pushed out to {1000 * FIT_CLEAR:.0f} mm clearance')
        if o.data.shape_keys is None: o.shape_key_add(name='Basis', from_mix=False)
        kb = o.data.shape_keys.key_blocks; nk = o.shape_key_add(name='kw_fit', from_mix=False)
        Mi = np.array(o.matrix_world.inverted()); base = np.empty(n * 3); kb[0].data.foreach_get('co', base); base = base.reshape(-1, 3)
        dl = (tgt - cw) @ Mi[:3, :3].T
        nk.data.foreach_set('co', (base + dl).ravel()); nk.value = 1.0
        k2 = KDTree(n); [k2.insert(c, i) for i, c in enumerate(tgt)]; k2.balance(); inner.append(k2)
        print(f'humgen fit {p.name} {o.name}: {moved} verts pulled in, max {1000 * mx:.1f} mm')
    G.keys = [o.data.shape_keys.key_blocks for o in G.meshes if o.data.shape_keys]


def _vnorm(w, polys):
    n = np.zeros_like(w)
    for pl in polys:
        a = w[pl[0]]
        for i in range(1, len(pl) - 1):
            c = np.cross(w[pl[i]] - a, w[pl[i + 1]] - a); n[pl[0]] += c; n[pl[i]] += c; n[pl[i + 1]] += c
    l = np.linalg.norm(n, axis=1, keepdims=True); l[l == 0] = 1; return n / l


def _hide_under(p, G):
    """4.4: under the lab coat, mask the shirt (and the body under shirt + coat) where the coat hides it, so nothing can
    poke through. Hidden = an outward ray (rest pose) hits the coat, eroded by HIDE_ERODE so the open front never shows a hole."""
    coat = next((o for o in G.meshes if 'COAT' in o.name.upper()), None)
    from mathutils.bvhtree import BVHTree
    def bvh(o): w = _mix_world(o); return BVHTree.FromPolygons([V(x) for x in w], [list(pl.vertices) for pl in o.data.polygons])
    tee = next((o for o in G.meshes if 'SHIRT' in o.name.upper()), None)
    jeans = next((o for o in G.meshes if 'JEANS' in o.name.upper()), None)
    outer = {}
    if coat is None:      # tee only (Ben): body skin under the tee (armpit / upper arm when the arm is raised)
        tasks = [(G.body, tuple(x for x in (tee, jeans) if x is not None))] if tee is not None else []
    else:
        tasks = ([(tee, tuple(x for x in (coat, jeans) if x is not None))] if HIDE_SHIRT else []) + [(G.body, tuple(x for x in (tee, coat, jeans) if x is not None))]
    for o, covers in tasks:
        if o is None or not covers: continue
        w = _mix_world(o); nr = _vnorm(w, [list(pl.vertices) for pl in o.data.polygons]); n = len(w)
        tr = [outer.get(id(c)) or bvh(c) for c in covers]
        hid = np.zeros(n, bool)
        for i in range(n):
            P = V(w[i]); d = V(nr[i])
            t1 = d.orthogonal().normalized(); t2 = d.cross(t1)
            dirs = [d] + [(d + (t1 * math.cos(a_) + t2 * math.sin(a_)) * 1.2).normalized() for a_ in np.linspace(0, 2 * math.pi, 8, endpoint=False)]
            if o is G.body:      # skin directly under the tee / shirt (openings are kept by HIDE_EDGE_BODY below)
                hid[i] = any(t.ray_cast(P + d * 0.0005, d, 0.04)[0] is not None for t in tr)
                continue
            hid[i] = tr[0].ray_cast(P + d * 0.0005, d, 0.15)[0] is not None and \
                     all(any(t.ray_cast(P + d * 0.0005, dd_, 0.15)[0] is not None for t in tr) for dd_ in dirs)    # coat in front + hidden from every outward view
        kd = KDTree(n); [kd.insert(c, i) for i, c in enumerate(w)]; kd.balance()
        er = HIDE_ERODE if o is not G.body else HIDE_ERODE_BODY
        keep = np.array([hid[i] and all(hid[j] for _, j, _ in kd.find_range(w[i], er)) for i in range(n)])
        if o is G.body or coat is not None:     # never mask near a cover's opening (collar, cuffs, hems, open coat front): it shows through the gap
            pts = []
            for c in (covers if o is G.body else covers[:1]):
                cw = _mix_world(c); cnt = {}
                for pl in c.data.polygons:
                    for k in pl.edge_keys: cnt[k] = cnt.get(k, 0) + 1
                pts += [cw[v] for v in sorted({v for k, c_ in cnt.items() if c_ == 1 for v in k})]
            if pts:
                r_ = HIDE_EDGE_BODY if o is G.body else HIDE_EDGE_COAT
                kb = KDTree(len(pts)); [kb.insert(x, j) for j, x in enumerate(pts)]; kb.balance()
                keep &= np.array([kb.find(w[i])[2] > r_ for i in range(n)])
        vg = o.vertex_groups.get('kw_hide') or o.vertex_groups.new(name='kw_hide')
        vg.add([int(i) for i in np.where(keep)[0]], 1.0, 'REPLACE')
        m = o.modifiers.new('kw_hide', 'MASK'); m.vertex_group = 'kw_hide'; m.invert_vertex_group = True
        o.modifiers.move(o.modifiers.find('kw_hide'), 0)
        print(f'humgen hide-under {p.name} {o.name}: {int(keep.sum())} of {n} verts masked under {covers[0].name}')
    # smallest layer offset that passes the overlap test (4.12): shirt in, coat out, along the normals after posing
    for o, st in ((tee, -LAYER_IN if coat is not None else 0), (coat, LAYER_OFF)):     # tee alone (Ben) stays put
        if o is None or st == 0: continue
        m = o.modifiers.new('kw_layer', 'DISPLACE'); m.direction = 'NORMAL'; m.mid_level = 0.0; m.strength = st
        if o is tee:       # shirt: full offset inside, fading to 0 at its openings (collar / hems stay on the skin)
            w_ = _mix_world(o); cnt = {}
            for pl in o.data.polygons:
                for k in pl.edge_keys: cnt[k] = cnt.get(k, 0) + 1
            bvs = sorted({v for k, c_ in cnt.items() if c_ == 1 for v in k}); kb3 = KDTree(len(bvs)); [kb3.insert(w_[v], j) for j, v in enumerate(bvs)]; kb3.balance()
            vg = o.vertex_groups.get('kw_in') or o.vertex_groups.new(name='kw_in')
            nr_ = _vnorm(w_, [list(pl.vertices) for pl in o.data.polygons]); cb_ = bvh(coat) if coat is not None else None
            for i_ in range(len(w_)):      # 0 within HIDE_EDGE_BODY of an opening (the body there is not masked: an inward shirt
                # would let the skin show through, check 1 f322 beside the lapel), full offset from 2 x HIDE_EDGE_BODY inward
                vg.add([i_], min(1.0, max(0.0, (kb3.find(w_[i_])[2] - HIDE_EDGE_BODY) / HIDE_EDGE_BODY)), 'REPLACE')
            m.vertex_group = 'kw_in'
        if o is coat:      # coat: cuffs only (wrist skin), the sleeve itself stays slim
            gi = {g.index for g in o.vertex_groups if g.name.startswith(('palm', 'hand', 'thumb', 'f_'))}
            vg = o.vertex_groups.get('kw_cuff') or o.vertex_groups.new(name='kw_cuff')
            vg.add([v.index for v in o.data.vertices if any(g.group in gi and g.weight > 0.01 for g in v.groups)], 1.0, 'REPLACE'); m.vertex_group = 'kw_cuff'
        ia = next((i for i, x in enumerate(o.modifiers) if x.type == 'ARMATURE'), None)
        if ia is not None: o.modifiers.move(o.modifiers.find('kw_layer'), ia + 1)
        print(f'humgen layer offset {p.name} {o.name}: {1000 * st:+.1f} mm')
        if o is coat and tee is not None:   # coat around the shirt neck opening: the shirt stays on the skin there (no inward offset), so the lapel steps out
            tw = _mix_world(tee); cnt = {}
            for pl in tee.data.polygons:
                for k in pl.edge_keys: cnt[k] = cnt.get(k, 0) + 1
            nb = [tw[v] for v in sorted({v for k, c_ in cnt.items() if c_ == 1 for v in k})]   # neck, sleeve and hem openings
            kc = KDTree(len(nb)); [kc.insert(x, j) for j, x in enumerate(nb)]; kc.balance()
            cw = _mix_world(o); vg = o.vertex_groups.get('kw_collar') or o.vertex_groups.new(name='kw_collar')
            for i_ in range(len(cw)):
                d_ = kc.find(cw[i_])[2]; wt = min(1.0, max(0.0, (COLLAR_R - d_) / (COLLAR_R / 2)))
                if wt > 0: vg.add([i_], wt, 'REPLACE')
            m2 = o.modifiers.new('kw_collar', 'DISPLACE'); m2.direction = 'NORMAL'; m2.mid_level = 0.0; m2.strength = COLLAR_OFF; m2.vertex_group = 'kw_collar'
            o.modifiers.move(o.modifiers.find('kw_collar'), o.modifiers.find('kw_layer') + 1)
            print(f'humgen collar offset {p.name} {o.name}: {1000 * COLLAR_OFF:+.1f} mm within {100 * COLLAR_R:.0f} cm of the shirt openings')

    if coat is not None and tee is not None: _cuff_fix(p, tee, coat)


CUFF_KEEP = 0.3      # A3: share of a coat vert's hand-bone weight kept on the hand (the rest moves to the forearm)
CUFF_HIDE_W = 0.02   # A3: shirt verts with more hand-bone weight than this are masked (they sit inside the coat cuff)


def _cuff_fix(p, tee, coat):
    """A3 (round 2): the white shirt cuff tore out through the coat cuff on a strong wrist turn (cup grip) because its
    end verts follow the hand bones. Under a coat the shirt cuff is never seen -> mask it; the coat cuff keeps only
    CUFF_KEEP of its hand weight so it rides the forearm instead of folding with the wrist."""
    is_hand = lambda nm: nm.startswith(('hand', 'palm', 'f_', 'thumb'))
    gi = {g.index for g in tee.vertex_groups if is_hand(g.name)}
    hid = [v.index for v in tee.data.vertices if sum(g.weight for g in v.groups if g.group in gi) > CUFF_HIDE_W]
    vg = tee.vertex_groups.get('kw_cuffhide') or tee.vertex_groups.new(name='kw_cuffhide'); vg.add(hid, 1.0, 'REPLACE')
    m = tee.modifiers.new('kw_cuffhide', 'MASK'); m.vertex_group = 'kw_cuffhide'; m.invert_vertex_group = True
    tee.modifiers.move(tee.modifiers.find('kw_cuffhide'), 0)
    moved = 0
    for side in ('L', 'R'):
        fa = coat.vertex_groups.get(f'forearm.{side}')
        if fa is None: continue
        hg = [g for g in coat.vertex_groups if is_hand(g.name) and g.name.endswith('.' + side)]
        hidx = {g.index: g for g in hg}
        for v in coat.data.vertices:
            tot = 0.0
            for g in v.groups:
                if g.group in hidx and g.weight > 0:
                    tot += g.weight * (1 - CUFF_KEEP); hidx[g.group].add([v.index], g.weight * CUFF_KEEP, 'REPLACE')
            if tot > 0:
                cur = next((g.weight for g in v.groups if g.group == fa.index), 0.0); fa.add([v.index], cur + tot, 'REPLACE'); moved += 1
    print(f'humgen cuff fix {p.name}: {len(hid)} shirt cuff verts masked, {moved} coat verts moved {100 * (1 - CUFF_KEEP):.0f}% onto the forearm')


ARM_SHIFT = {('Ben', 'L'): 0.025}
ARM_CHAIN = ('upper_arm', 'forearm', 'hand', 'palm', 'f_index', 'f_middle', 'f_ring', 'f_pinky', 'thumb')
FIT_X0 = 0.12
HIDE_ERODE = 0.015
LAYER_OFF = 0.004
BOARD_FWD = 0.03
BOARD_DROP = 0.235       # C1: holding wrist this far below the HG neck base -> board top ~0.17 m below it (breastbone); measured board top = wrist + 0.065
LAYER_IN = 0.010
COLLAR_OFF = 0.006
COLLAR_R = 0.10
HIDE_EDGE_BODY = 0.03
HIDE_EDGE_COAT = 0.03
HIDE_SHIRT = False     # the shirt stays whole: masking it under the coat showed holes in the open front
HIDE_ERODE_BODY = 0.012
FIT_GAP = {'SHIRT': 0.004, 'COAT': 0.009, 'UNDER': 0.004}
FIT_K = 1.0
FIT_CLEAR = 0.008


BOARD_W, BOARD_H, BOARD_T, PAPER_T, BOARD_TUCK, BOARD_GRIP, PEN_LIFT = 0.138, 0.232, 0.009, 0.002, 0.012, 0.025, 0.035


def _mat(name, rgb, rough):
    m = bpy.data.materials.get(name) or bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes.get('Principled BSDF'); b.inputs['Base Color'].default_value = (*rgb, 1); b.inputs['Roughness'].default_value = rough
    return m


def _board(coll):
    """clipboard (kit colours: board 4B7792, paper F2F4E9, clip BBC9CD): local x = width, y = normal (paper at +y), z = height"""
    import bmesh
    def box(name, size, loc, mat, parent=None):
        me = bpy.data.meshes.new(name); bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
        for v in bm.verts: v.co = V((v.co.x * size[0] + loc[0], v.co.y * size[1] + loc[1], v.co.z * size[2] + loc[2]))
        bm.to_mesh(me); bm.free(); me.materials.append(mat)
        o = bpy.data.objects.new(name, me); coll.objects.link(o)
        if parent: o.parent = parent
        return o
    srgb = lambda h: tuple(((int(h[i:i + 2], 16) / 255) ** 2.2) for i in (0, 2, 4))
    b = box('kw_hg_board', (BOARD_W, BOARD_T, BOARD_H), (0, 0, 0), _mat('kw_hg_board_m', srgb('4B7792'), 0.43))
    pa = box('kw_hg_board_paper', (BOARD_W - 0.022, PAPER_T, BOARD_H - 0.04), (0, BOARD_T / 2 + PAPER_T / 2, -0.008), _mat('kw_hg_paper_m', srgb('F2F4E9'), 0.52), b)
    cl = box('kw_hg_board_clip', (0.071, 0.008, 0.022), (0, BOARD_T / 2 + 0.004, BOARD_H / 2 - 0.016), _mat('kw_hg_clip_m', srgb('BBC9CD'), 0.24), b)
    objs = [b, pa, cl]
    for o in objs: o.hide_render = True
    return b, objs


def _pen(coll):
    """writing pen (kit 'pen' colours): unit-length tapered cylinder, tip at the origin, axis +Z"""
    import bmesh
    me = bpy.data.meshes.new('kw_hg_pen'); bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=12, radius1=0.0028, radius2=0.0028, depth=1.0)
    for v in bm.verts: v.co.z += 0.5     # 0..1 (tip at 0)
    bm.to_mesh(me); bm.free()
    o = bpy.data.objects.new('kw_hg_pen', me); coll.objects.link(o)
    me.materials.append(_mat('kw_pen_m', (0.1, 0.2, 0.8), 0.3)); o.hide_render = True
    return o


def _face_marks(co, eL, eR):
    """nose bridge + top-of-ear points on a head mesh (world verts), from the eye centres. Front = -Y."""
    ez = (eL.z + eR.z) / 2; ey = (eL.y + eR.y) / 2; ex = (eL.x + eR.x) / 2
    m = (np.abs(co[:, 0] - ex) < 0.006) & (np.abs(co[:, 2] - ez) < 0.012) & (co[:, 1] < ey)
    br = co[m][np.argmin(co[m][:, 1])]
    ears = []
    for sg in (1, -1):
        m = (sg * (co[:, 0] - ex) > 0.04) & (co[:, 2] > ez - 0.045) & (co[:, 2] < ez + 0.02) & (co[:, 1] > ey + 0.05) & (co[:, 1] < ey + 0.13)
        c = co[m]; xs = sg * c[:, 0]; c = c[xs > xs.max() - 0.008]
        ears.append(c[np.argmax(c[:, 2])])
    return V(br), V(ears[0]), V(ears[1])


def _frame(br, e1, e2):
    x = (e1 - e2).normalized(); mid = (e1 + e2) / 2; y = (mid - br); y = (y - x * y.dot(x)).normalized(); z = x.cross(y)
    return Matrix((x, y, z)).transposed(), (e1 - e2).length, (mid - br).dot(y)


def _glasses(kr, p, G):
    """Glasses: 3 landmarks (nose bridge, top of each ear) old head -> HG head; width scaled to the temple distance,
    depth to the bridge-ear distance; parented to the HG head bone; then set 2 mm off the nose bridge."""
    gl = [o for o in p.parts if 'glasses' in o.name.lower()]
    G.glasses = gl
    if not gl: return
    dg = bpy.context.evaluated_depsgraph_get()
    old = _verts_world(p.mh_body, dg); new = _verts_world(G.body, dg)
    me = [kr.bw(p, f'eye.{s}') for s in 'LR']; he = [G.rig.matrix_world @ G.rig.pose.bones[f'eyeball.{s}'].head for s in 'LR']
    a = _face_marks(old, *me); b = _face_marks(new, *he)
    Ra, wa, da = _frame(*a); Rb, wb, db = _frame(*b)
    S = Matrix.Diagonal((wb / wa, db / da, (wb / wa + db / da) / 2, 1.0))
    T = Matrix.Translation(b[0]) @ Rb.to_4x4() @ S @ Ra.to_4x4().transposed() @ Matrix.Translation(-a[0])
    hb = G.rig.pose.bones['head']; HW = G.rig.matrix_world @ hb.matrix
    for o in gl:
        W = T @ o.matrix_world
        o.parent = G.rig; o.parent_type = 'BONE'; o.parent_bone = 'head'
        bpy.context.view_layer.update()
        o.matrix_world = W
    bpy.context.view_layer.update()
    # level (4.12): the old eye line carried by T must lie along the HG eye line (lenses at one height)
    lo = (T @ me[1]) - (T @ me[0]); ln = he[1] - he[0]
    q = lo.normalized().rotation_difference(ln.normalized()); Rq = Matrix.Translation(b[0]) @ q.to_matrix().to_4x4() @ Matrix.Translation(-b[0])
    for o in gl: o.matrix_world = Rq @ o.matrix_world
    bpy.context.view_layer.update()
    print(f'humgen glasses {p.name}: level fix {math.degrees(q.angle):.2f} deg')
    # height: lens-rim centre onto the HG eye centre along the head up axis (the 3-mark fit left the rims ~1 cm low)
    rims = [o for o in gl if 'lens' in o.name.lower()] or gl
    rc = V(np.concatenate([_verts_world(o) for o in rims]).mean(axis=0)); ec = (he[0] + he[1]) / 2
    up = (Rb @ V((0, 0, 1))).normalized(); dz = (ec - rc).dot(up) + GLASS_DZ
    for o in gl: o.matrix_world = Matrix.Translation(up * dz) @ o.matrix_world
    bpy.context.view_layer.update()
    print(f'humgen glasses {p.name}: lift {1000 * dz:.1f} mm')
    # gap: glasses points within 2.5 cm of the bridge vs HG skin; push along the face normal to a 2 mm gap
    kd = KDTree(len(new)); [kd.insert(c, i) for i, c in enumerate(new)]; kd.balance()
    def near():
        g = np.concatenate([_verts_world(o) for o in gl]); m = np.linalg.norm(g - np.array(b[0]), axis=1) < 0.025
        return min(kd.find(c)[2] for c in g[m]) if m.any() else None, g
    d0, g = near()
    fwd = -(Rb @ V((0, 1, 0)))
    if d0 is not None:
        for o in gl: o.matrix_world = Matrix.Translation(fwd * (0.002 - d0)) @ o.matrix_world
        bpy.context.view_layer.update()
    d1, g = near()
    lens_y = float(np.median(g[:, 1][np.abs(g[:, 2] - np.mean([e.z for e in he])) < 0.015])) if len(g) else 0
    eye_front = min(e.y for e in he) - 0.012
    print(f'humgen glasses {p.name}: old marks', [tuple(round(x, 3) for x in v) for v in a], 'new', [tuple(round(x, 3) for x in v) for v in b],
          f'width {wa:.3f}->{wb:.3f} bridge gap {d0 if d0 is None else round(1000 * d0, 1)}->{d1 if d1 is None else round(1000 * d1, 1)} mm',
          f'lens y {lens_y:.3f} eye front y {eye_front:.3f} in_front {lens_y < eye_front}')
    G.glass_gap = d1


# ====================================================================== contacts (by construction, on the HG mesh)
GRIP = {'can': (0.033, 0.12), 'spoon': (0.005, 0.15)}     # kit prop radius, length (kwfx._make_prop)
ITEM_OFF = {}
ITEM_OFF_P = {}
# cast v1.1 hand-authored grips (fixed prop size; the prop follows the hand). Absolute finger angles (deg) on the kit finger
# bones: finger k (1 thumb .. 5 pinky) -> (joint1, joint2, joint3) flex about x; thumb also 'z' on joint 1. Per character
# override AUTH_P[(name, prop)]. Offsets (m) are in the grip frame named in AUTH_AT.
AUTH = {
    'g_pea': {1: ((42, 35, 35), -20), 2: ((42.75, 54, 42.75), 0), 3: ((45, 55, 40), 0), 4: ((50, 60, 40), 0), 5: ((55, 62, 40), 0)},
    'g_paperclip': {1: ((35.7, 29.75, 29.75), -10), 2: ((47.5, 60, 47.5), 0), 3: ((45, 55, 40), 0), 4: ((50, 60, 40), 0), 5: ((55, 62, 40), 0)},
    'g_tweezers': {1: ((42, 35, 35), -30), 2: ((47.5, 60, 47.5), 0), 3: ((45, 55, 40), 0), 4: ((50, 60, 40), 0), 5: ((55, 62, 40), 0)},
    'g_penlight': {1: ((48.3, 40.25, 40.25), -30), 2: ((47.5, 60, 47.5), 0), 3: ((45, 55, 40), 0), 4: ((50, 60, 40), 0), 5: ((55, 62, 40), 0)},
    'g_burger': {1: ((5, 10, 10), -55), 2: ((25, 35, 25), 0), 3: ((28, 38, 25), 0), 4: ((30, 40, 25), 0), 5: ((32, 42, 25), 0)},
}
AUTH_P = {}
AUTH_OFF = {'g_pea': (0.0006, 0.0016, 0.0146), 'g_paperclip': (0.0067, -0.0014, 0.011), 'g_burger': (0.0, 0.0, 0.0),
            'g_tweezers': (-0.0001, 0.0008, 0.0139), 'g_penlight': (-0.0027, 0.003, 0.0128)}
# tools: (grip point along the item's +X from its origin, item axis height above its origin) -> the pads close on the grip point
TOOL_AT = {'g_tweezers': (0.02, 0.0012), 'g_penlight': (-0.02, 0.0065)}
BURGER = dict(width=0.11, height=0.06, squash=0.96, tilt=12.0)     # bun dent = (1 - squash) * height ~ 2.4 mm; tilt toward the face
SKIN = 0.0015                                             # target skin-to-prop gap
INV = {v[0]: k for k, v in MAP.items()}                   # MakeHuman bone -> HG bone


def _sd_cyl(P, M, r, h):
    Mi = np.array(M.inverted()); lp = P @ Mi[:3, :3].T + Mi[:3, 3]
    dr = np.hypot(lp[:, 0], lp[:, 1]) - r; dz = np.abs(lp[:, 2]) - h / 2
    return np.hypot(np.maximum(dr, 0), np.maximum(dz, 0)) + np.minimum(np.maximum(dr, dz), 0)


def _sd_box(P, M, half):
    Mi = np.array(M.inverted()); lp = P @ Mi[:3, :3].T + Mi[:3, 3]
    q = np.abs(lp) - np.array(half)
    return np.linalg.norm(np.maximum(q, 0), axis=1) + np.minimum(q.max(1), 0)


def _sd_plane(P, M):      # half-space y < 0 of M is "inside"
    Mi = np.array(M.inverted()); lp = P @ Mi[:3, :3].T + Mi[:3, 3]
    return lp[:, 1]


def _body_world(G, dg=None):
    """HG body vertices (world), masks off so indices match the mesh"""
    ms = [m for m in G.body.modifiers if m.type == 'MASK' and m.show_viewport]
    for m in ms: m.show_viewport = False
    bpy.context.view_layer.update(); w = _verts_world(G.body)
    for m in ms: m.show_viewport = True
    bpy.context.view_layer.update(); return w


def after_calibrate(kr, ra):
    G = getattr(ra.p, 'hg', None)
    if G is None: return
    G.calibrate(kr, ra)


def _graft_calibrate(self, kr, ra):
    from mathutils.bvhtree import BVHTree
    p = self.p; self.kr, self.ra = kr, ra
    kr.reset(p); kr.rig_at(p, (0, 0, 0), 0)
    for s in 'LR': kr.set_shape(p, s, 'hold')
    bpy.context.view_layer.update()
    w = _body_world(self)
    # lower-lip landmark: midline vertices moved by jawOpen, top of that set, front-most -> MakeHuman head space
    kb = self.body.data.shape_keys.key_blocks; n = len(self.body.data.vertices)
    b0 = np.empty(n * 3); kb[0].data.foreach_get('co', b0); b0 = b0.reshape(-1, 3)
    jo = np.empty(n * 3); kb['jawOpen'].data.foreach_get('co', jo); jo = jo.reshape(-1, 3)
    cand = np.where((np.abs(b0[:, 0]) < 0.004) & (np.linalg.norm(jo - b0, axis=1) > 0.002))[0]
    top = cand[b0[cand, 2] > b0[cand, 2].max() - 0.012]; self.lip_idx = int(top[np.argmin(b0[top, 1])])
    self.lip_local = kr.wmat(p, 'head').inverted() @ V(w[self.lip_idx])
    # face camera anchor (4.3 / 4.10): the kit nose method on the old MakeHuman mesh vs the HG nose (kit calibration);
    # the HG face sits higher on the head bone, so face / face-close cameras lift by the same amount (framing follows the HG face)
    on_ = self.old_nose_local; nn_ = ra.parts['nose'][1]
    ra.hg_face_dz = float(nn_.y - on_.y)
    print(f'humgen face anchor {p.name}: nose head-local old {tuple(round(x, 3) for x in on_)} new {tuple(round(x, 3) for x in nn_)} -> camera face lift {1000 * ra.hg_face_dz:.1f} mm')
    # finger segment radii (HG bones, rest): median vertex distance to the bone axis
    vg = {g.index: g.name for g in self.body.vertex_groups}; grp = {}
    for v in self.body.data.vertices:
        for g in v.groups:
            if g.weight > 0.5: grp.setdefault(vg[g.group], []).append(v.index)
    R = self.rig.matrix_world; self.rad = {}
    for hb in MAP:
        if not hb.startswith(('f_', 'thumb')) or hb not in grp: continue
        pb = self.rig.pose.bones[hb]; a = np.array(R @ pb.head); b = np.array(R @ pb.tail); d = b - a
        P = w[grp[hb]]; tt = np.clip(((P - a) @ d) / (d @ d), 0, 1); self.rad[hb] = float(np.median(np.linalg.norm(P - (a + tt[:, None] * d), axis=1)))
    # palm skin point (wrist space) per side: ray from the kit palm axis point along the palm normal
    polys = [list(pl.vertices) for pl in self.body.data.polygons]
    bvh = BVHTree.FromPolygons([V(x) for x in w], polys)
    self.palm = {}; self.Pl = {}; self.curl = {}
    for s in 'LR':
        info = ra.hand[s]; Mw = kr.wmat(p, f'wrist.{s}'); n_ = info['pnorm']; f_ = info['fdir']
        # grip frame from the HG hand itself: the grip axis runs across the knuckles (index -> pinky), palm normal across it
        Mwi = Mw.inverted(); RH = self.rig.matrix_world
        ka = Mwi @ (RH @ self.rig.pose.bones[f'f_index.01.{s}'].head); kb_ = Mwi @ (RH @ self.rig.pose.bones[f'f_pinky.01.{s}'].head)
        g0 = f_.cross(n_).normalized(); gk = (kb_ - ka).normalized()
        if gk.dot(g0) < 0: gk = -gk
        f2 = (f_ - gk * f_.dot(gk)).normalized(); n2 = gk.cross(f2).normalized()
        if n2.dot(n_) < 0: n2 = -n2
        o_l = (ka + kb_) / 2 - f2 * 0.03 - n2 * 0.005
        hit = bvh.ray_cast(Mw @ o_l, (Mw.to_3x3() @ n2).normalized(), 0.1)
        S_l = Mwi @ hit[0] if hit[0] is not None else info['hold']['palm']
        self.palm[s] = S_l; self.pn = getattr(self, 'pn', {}); self.pn[s] = (n2.copy(), f2.copy())
        print(f'humgen grip frame {p.name} {s}: axis tilt {math.degrees(gk.angle(g0)):.1f} deg, normal tilt {math.degrees(n2.angle(n_)):.1f} deg, hit {hit[0] is not None}')
        # diagonal grip: the pinky end of the grip axis sits nearer the wrist (rotate about the palm normal)
        pk = (kb_ - ka).normalized(); Rg = Matrix.Rotation(math.radians(GRIP_DIAG), 3, n2)
        if (Rg @ pk).dot(f2) > pk.dot(f2): Rg = Matrix.Rotation(-math.radians(GRIP_DIAG), 3, n2)
        g3 = Rg @ gk
        f3 = n2.cross(g3).normalized()
        if f3.dot(f2) < 0: f3 = -f3
        f_, n_, g_ = f3, n2, g3.normalized()
        for prop, (r, h) in GRIP.items():
            M = Matrix((f_, n_, g_)).transposed().to_4x4(); M.translation = S_l + n_ * (r + SKIN); self.Pl[(s, prop)] = M
        Mb = Matrix((-g_, n_, f_)).transposed().to_4x4(); Mb.translation = S_l + n_ * (BOARD_T / 2 + SKIN) + f_ * 0.045
        self.Pl[(s, 'board')] = Mb
        Mp = Matrix((-g_, -n_, -f_)).transposed().to_4x4(); Mp.translation = S_l + n_ * 0.003; self.Pl[(s, 'plane')] = Mp   # belly: y<0 = inside cloth
        print(f'humgen grip {p.name} {s}: palm skin {round(1000 * (S_l - o_l).length, 1)} mm from the palm axis (kit assumed 16 mm)')
    # finger curls that land each finger on the prop surface: solved on the real HG skin (distal 2 segments)
    vgi = {g.name: g.index for g in self.body.vertex_groups}; self.fids = {}
    for s in 'LR':
        for k, f in enumerate(('thumb', 'f_index', 'f_middle', 'f_ring', 'f_pinky'), 1):
            gi = {vgi.get(f'{f}.0{j}.{s}') for j in (2, 3)}
            self.fids[(s, k)] = np.array([v.index for v in self.body.data.vertices if any(g.group in gi and g.weight > 0.5 for g in v.groups)], int)
    need = set()
    for sh in kr.ep.shots:
        ps = sh.cast.get(ra.a) if hasattr(sh.cast, 'get') else None
        if ps is None: continue
        for _, q in ps.keys:
            for sd, h in (('L', q.left), ('R', q.right)):
                if h is None: continue
                if h.kind == 'hold' and h.prop in GRIP: need.add((sd, h.prop, 'hold'))
                elif h.kind == 'clipboard': need.add((sd, 'board', 'hold'))
                elif h.kind == 'touch' and h.part == 'belly': need.add((sd, 'plane', 'claw'))
    for (sd, key, shape) in sorted(need):
        kr.set_shape(p, sd, shape); bpy.context.view_layer.update()
        self.curl[(sd, key)] = self._solve_can(kr, sd) if key == 'can' else self._solve_pen(kr, sd) if key == 'spoon' else self._solve_real(kr, sd, key)
        kr.set_shape(p, sd, 'relaxed')
    bpy.context.view_layer.update()
    print(f'humgen curls {p.name}', {f'{k[0]}{k[1]}': v for k, v in self.curl.items()})
    # seat: the kit seats the pelvis bone 7.5 cm above the seat; measure the HG trouser bottom under the pelvis instead
    kr.reset(p); [p.rot(f'{b}.{s_}', v) for b, v in __import__('sys').modules[type(kr).__module__].SIT.items() for s_ in 'LR']; kr.rig_at(p, (0, 0, 0), 0); bpy.context.view_layer.update()
    jeans = next((o for o in self.meshes if any(k in o.name for k in ('Jeans', 'Trousers', 'Pants'))), None)
    if jeans is not None:
        jw = _verts_world(jeans); hp = self.rig.matrix_world @ self.rig.pose.bones['spine'].head
        m = np.hypot(jw[:, 0] - hp.x, jw[:, 1] - hp.y) < 0.14
        dHG = kr.bw(p, 'spine05').z - float(np.percentile(jw[m, 2], 1))
        ra.hg_seat_drop = 0.075 - dHG + SEAT_SINK
        print(f'humgen seat {p.name}: pelvis-to-trouser-bottom {100 * dHG:.2f} cm (kit 7.5) -> drop {100 * ra.hg_seat_drop:.2f} cm')
    # belly swell: how far the tee moves out along the belly normal at full kw_bloat
    kr.reset(p); kr.rig_at(p, (0, 0, 0), 0); bpy.context.view_layer.update()
    pt, nr = kr.part_world(ra, 'belly'); self.belly_disp = 0.0
    tee = next((o for o in self.meshes if 'SHIRT' in o.name.upper()), None)
    if tee is not None and tee.data.shape_keys and tee.data.shape_keys.key_blocks.get('kw_bloat'):
        kb = tee.data.shape_keys.key_blocks; Mw = tee.matrix_world
        i = min(range(len(tee.data.vertices)), key=lambda i: (Mw @ kb[0].data[i].co - pt).length)
        self.belly_disp = max(0.0, (Mw.to_3x3() @ (kb['kw_bloat'].data[i].co - kb[0].data[i].co)).dot(nr))
    print(f'humgen belly {p.name}: tee moves {1000 * self.belly_disp:.1f} mm at kw_bloat 1, lip vertex {self.lip_idx}')


def _sdf(self, key, P, Mw):
    M = Mw @ self.Pl[(self._side, key)]
    if key in GRIP: r, h = GRIP[key]; return _sd_cyl(P, M, r, h)
    if key == 'board': return _sd_box(P, M, (BOARD_W / 2, BOARD_T / 2, BOARD_H / 2))
    return _sd_plane(P, M)


def _solve_curl(self, kr, s, key, shape):
    p = self.p; rig = p.rig; RW = rig.matrix_world; self._side = s
    Mw = kr.wmat(p, f'wrist.{s}'); out = {}
    for k in range(1, 6):
        names = [f'finger{k}-{j}.{s}' for j in (1, 2, 3)]
        pbs = [rig.pose.bones[nm] for nm in names]
        par = pbs[0].parent; Mpar = RW @ par.matrix
        rel = [pbs[0].bone.parent.matrix_local.inverted() @ pbs[0].bone.matrix_local] + \
              [pbs[j - 1].bone.matrix_local.inverted() @ pbs[j].bone.matrix_local for j in (1, 2)]
        eul = [pb.rotation_euler.copy() for pb in pbs]
        hgb = [INV.get(nm) for nm in names]
        def dist(c1, c2, tipdbg=False):
            M = Mpar; pts = []; rr = []
            for j in range(3):
                e = eul[j].copy(); e.x += math.radians(c1 if j == 0 else c2); M = M @ rel[j] @ e.to_matrix().to_4x4()
                hb = hgb[j]
                if hb is None or hb not in self.fit: continue
                Mh = M @ self.fit[hb][1]; ln = self.rig.data.bones[hb].length
                for y in np.linspace(0.15, 1.0, 5): pts.append(list(Mh @ V((0, ln * y, 0)))); rr.append(self.rad.get(hb, 0.008))
            if not pts: return 1.0
            if tipdbg:
                Mi = (Mw @ self.Pl[(s, key)]).inverted(); return tuple(round(1000 * x) for x in (Mi @ V(pts[-1])))
            return float((self._sdf(key, np.array(pts), Mw) - np.array(rr)).min())
        grid = [(c1, c2, dist(c1, c2)) for c1 in range(-40, 95, 5) for c2 in range(-30, 100, 5)]
        ok = [g for g in grid if 0.0 <= g[2] <= 2 * SKIN + 0.001]
        best = min(ok, key=lambda g: abs(g[0]) + abs(g[1])) if ok else min(grid, key=lambda g: abs(g[2] - SKIN))
        out[k] = (best[0], best[1], round(1000 * best[2], 1))
        if not ok: print(f'humgen curl {p.name} {s}{key} finger{k}: no contact pose, best {out[k]} tip in prop space mm', dist(best[0], best[1], True))
    return out


def _solve_real(self, kr, s, key):
    """per finger (c1 = base joint, c2 = outer joints; thumb: cx on all joints + cz on the base) -> gap SKIN on the HG skin"""
    p = self.p; rig = p.rig; self._side = s; Mw = kr.wmat(p, f'wrist.{s}')
    pbs = {k: [rig.pose.bones[f'finger{k}-{j}.{s}'] for j in (1, 2, 3)] for k in range(1, 6)}
    base = {k: [pb.rotation_euler.copy() for pb in v] for k, v in pbs.items()}
    def ev(cs):
        for k, (a, b) in cs.items():
            for j, pb in enumerate(pbs[k]):
                e = base[k][j].copy()
                if k == 1: e.x += math.radians(a); e.z += math.radians(b if j == 0 else 0.0)
                else:
                    e.x += math.radians(a if j == 0 else b)
                    if key == 'plane' and j == 0: e.z += math.radians(SPR.get(k, 0.0))
                pb.rotation_euler = e
        w = _body_world(self); out = {}
        for k in cs:
            ids = self.fids[(s, k)]; out[k] = float(self._sdf(key, w[ids], Mw).min()) if len(ids) else 1.0
        return out
    SPR = {}
    if key == 'plane':      # 4.12: flat palm on the belly -> fingers stay nearly straight (no claw), lying on the tee
        best = {}
        for c in range(-90, 31, 5):
            r = ev({k: ((0.0, 0.0) if k == 1 else (c, c * 0.6)) for k in range(1, 6)})
            for k in range(1, 6):
                cc = (0.0, 0.0) if k == 1 else (c, c * 0.6); sc = (0 if 0.0 <= r[k] <= 0.006 else 1, abs(c) if 0.0 <= r[k] <= 0.006 else abs(r[k] - SKIN))
                if k not in best or sc < best[k][2]: best[k] = (cc, r[k], sc)
        # fingers together (HG rest hand is splayed): per-finger side swing so neighbouring fingertips sit ~19 mm apart
        cs = {k: best[k][0] for k in range(1, 6)}
        def tips():
            ev(cs); w = _body_world(self); return {k: w[self.fids[(s, k)]].mean(0) for k in range(2, 6)}
        for k, nb in ((2, 3), (4, 3), (5, 4)):
            sc = []
            for z in range(-16, 17, 4):
                SPR[k] = float(z); tp = tips(); sc.append((abs(float(np.linalg.norm(tp[k] - tp[nb])) - 0.019), z))
            SPR[k] = float(min(sc)[1])
            if os.environ.get('KW_HG_AUDIT'): print('AUDIT spread scan', s, k, [(z, round(1000 * d)) for d, z in sc])
        self.spread = getattr(self, 'spread', {}); self.spread[s] = dict(SPR)
        tp = tips(); print(f'humgen plane spread {p.name} {s}', dict(SPR), 'tip gaps mm', [round(1000 * float(np.linalg.norm(tp[a] - tp[b]))) for a, b in ((2, 3), (3, 4), (4, 5))])
        r = ev(cs); best = {k: (best[k][0], r[k], None) for k in best}
        for k, v in pbs.items():
            for j, pb in enumerate(v): pb.rotation_euler = base[k][j]
        out = {k: (round(c[0], 1), round(c[1], 1), round(1000 * d, 1)) for k, (c, d, _) in best.items()}
        print(f'humgen curl {p.name} {s}{key}', out)
        return out
    th = [(x, z) for x in range(-30, 61, 15) for z in range(-40, 41, 20)]
    n = len(th); fc = [-40 + i * 130.0 / (n - 1) for i in range(n)]
    samp = {k: [] for k in range(1, 6)}
    for i in range(n):
        cs = {1: th[i]}; cs.update({k: (fc[i], fc[i]) for k in range(2, 6)})
        r = ev(cs)
        for k in cs: samp[k].append((cs[k], r[k]))
    def score(c, d):
        if key == 'board': return (0 if 0.0 <= d <= 0.002 else 1, abs(d - SKIN))      # C3: skin to board 0-2 mm (was the loosest curl in 0-4 mm)
        return (0 if 0.0 <= d <= 0.004 else 1, abs(d - SKIN) if not (0.0 <= d <= 0.004) else (abs(c[0]) + abs(c[1])) * 1e-4)
    best = {k: min(v, key=lambda x: score(*x)) for k, v in samp.items()}
    # fingers that never reach in the coupled scan: base joint and outer joints separately (base flex <= 100 deg extra)
    bad = [k for k in range(2, 6) if not (0.0 <= best[k][1] <= 0.004)]
    if bad:
        for c1 in range(40, 101, 10):
            for c2 in range(0, 101, 20):
                r = ev({k: (c1, c2) for k in bad})
                for k in bad:
                    if score((c1, c2), r[k]) < score(*best[k]): best[k] = ((c1, c2), r[k])
    # refine the four fingers: bisection on the bracket around the gap = SKIN crossing
    lo = {}; hi = {}
    for k in range(2, 6):
        v = samp[k]; br = None
        for (c0, d0), (c1_, d1) in zip(v, v[1:]):
            if d0 > SKIN >= d1: br = (c0[0], c1_[0]); break
        if br and k not in bad: lo[k], hi[k] = br
    for _ in range(3):
        if not lo: break
        mid = {k: ((lo[k] + hi[k]) / 2,) * 2 for k in lo}; r = ev(mid)
        for k in lo:
            if r[k] > SKIN: lo[k] = mid[k][0]
            else: hi[k] = mid[k][0]
            if score(mid[k], r[k]) < score(*best[k]): best[k] = (mid[k], r[k])
    for k, v in pbs.items():
        for j, pb in enumerate(v): pb.rotation_euler = base[k][j]
    if os.environ.get('KW_HG_AUDIT'):
        bad = {k: v for k, v in best.items() if not (0.0 <= v[1] <= 0.004)}
        if bad:
            ev({k: v[0] for k, v in best.items()}); w = _body_world(self); Mi = np.array((Mw @ self.Pl[(s, key)]).inverted())
            for k in bad:
                lp = w[self.fids[(s, k)]] @ Mi[:3, :3].T + Mi[:3, 3]
                print(f'AUDIT curldbg {p.name} {s}{key} f{k} local mm min', np.round(lp.min(0) * 1000), 'max', np.round(lp.max(0) * 1000))
    out = {k: (round(c[0], 1), round(c[1], 1), round(1000 * d, 1)) for k, (c, d) in best.items()}
    print(f'humgen curl {p.name} {s}{key}', out)
    return out


Graft._solve_real = _solve_real
Graft.calibrate = _graft_calibrate
Graft._solve_curl = _solve_curl
Graft._sdf = _sdf


def _goal(self, kr, ra, side, h, g, u, t):
    """retarget one kit hand goal onto the HG hand: prop contact on the HG lips / paper / tee (translation only)."""
    if g is None or not hasattr(self, 'Pl'): return g
    getattr(self, '_canrel', {}).pop(side, None)
    D, tip, shape, Rw, pole = g
    if not isinstance(D, V) or Rw is None: return g
    tl = ra.hand[side][shape][tip]
    if V11 and h is not None and h.kind == 'hold' and h.prop == 'g_burger':     # round 2: both hands from the burger frame
        return _burger_goal(self, kr, ra, side, h, tip, shape)
    if V11 and h is not None and h.kind == 'hold' and h.prop == 'can' and h.pad == 'cup' and h.at != 'mouth' and (side, 'can') in self.Pl:
        a_ = (Rw @ self.Pl[(side, 'can')].to_3x3()).col[2].normalized()       # cast v1.1 grip_cup: turn the wrist so the cup stands upright
        Rw = (a_.rotation_difference(V((0, 0, 1))).to_matrix() @ Rw.to_3x3()) if Rw.__len__() == 3 else a_.rotation_difference(V((0, 0, 1))).to_matrix().to_4x4() @ Rw
        g = (D, tip, shape, Rw, pole)
    W = Matrix.Translation(D - Rw @ tl) @ Rw.to_4x4()
    can_ = h is not None and h.kind == 'hold' and h.prop == 'can' and h.at == 'mouth' and shape == 'hold' and (side, 'can') in getattr(self, 'cangrip', {})
    # the kit IK chain is 4 bones (upperarm01/02, lowerarm01/02): the 02 twist bones may only TWIST while the can is held,
    # so the real elbow lands where the 2-bone arm solve put it (they bent ~10 cm off it); other hand jobs unchanged (G8)
    for bn in (f'upperarm02.{side}', f'lowerarm02.{side}'):
        pb_ = ra.p.rig.pose.bones.get(bn)
        if pb_ is not None: pb_.lock_ik_x = pb_.lock_ik_z = bool(can_)
    if can_:
        return self.can_goal(kr, ra, side, tip, shape, u)
    if h is not None and h.kind == 'hold' and h.prop == 'spoon' and h.at == 'mouth' and shape == 'hold' and (side, 'spoon') in getattr(self, 'curl', {}):
        return self.spoon_goal(kr, ra, side, tip, shape, u, pole)
    if h is not None and h.kind == 'hold' and h.prop in GRIP and h.at == 'mouth' and shape == 'hold':
        r, hh = GRIP[h.prop]
        L = kr.wmat(ra.p, 'head') @ self.lip_local; _, nr = kr.part_world(ra, 'mouth')
        # tilt: the can tips toward the lips while drinking (drink act weight), the spoon points into the mouth
        th = TILT.get(h.prop, 0.0) * (self.drink_w(kr, ra, u) if h.prop == 'can' else 1.0)
        if th > 1e-3:
            A = nr.cross(V((0, 0, 1))).normalized(); best = None
            for sg in (1, -1):
                Rt = Matrix.Rotation(sg * th, 3, A) @ Rw; Wt = Matrix.Translation(D - Rt @ tl) @ Rt.to_4x4(); Mt = Wt @ self.Pl[(side, h.prop)]
                ends = sorted((Mt @ V((0, 0, z)) for z in (-hh / 2, hh / 2)), key=lambda e: (e - L).length)
                sc = (ends[1] - L).dot(nr)
                if best is None or sc > best[0]: best = (sc, Rt, Wt)
            Rw, W = best[1], best[2]
        M = W @ self.Pl[(side, h.prop)]
        ax = (M.to_3x3() @ V((0, 0, 1))).normalized()
        E = min((M @ V((0, 0, z)) for z in (-hh / 2, hh / 2)), key=lambda e: (e - L).length)
        if h.prop == 'can':
            dv = L - E; dv = dv - ax * dv.dot(ax); C = E + dv.normalized() * r if dv.length > 1e-6 else E
            Lt = L + nr * 0.004
        else: C = E; Lt = L + nr * 0.006
        return D + (Lt - C), tip, shape, Rw, pole
    if h is not None and h.kind == 'clipboard':
        # board a little further from the chest so the writing forearm's sleeve clears the shirt (overlap test)
        _, fw = kr.part_world(ra, 'belly'); fw = V((fw.x, fw.y, 0)).normalized() * BOARD_FWD
        nz_ = (self.rig.matrix_world @ self.rig.pose.bones['neck'].head).z; fw = fw + V((0, 0, max(0.0, (nz_ - BOARD_DROP) - (D + fw).z)))   # C1: board top edge level with the breastbone (it sat at the hip)
        W = Matrix.Translation(fw) @ W; self._wl = (side, W)
        return (D + fw, tip, shape, Rw, pole)
    if h is not None and h.kind == 'write' and getattr(self, '_wl', None) is not None and self._wl[0] != side:
        Bw = self._wl[1] @ self.Pl[(self._wl[0], 'board')]
        wig = V((math.sin(t * 13) * 0.012, 0, math.sin(t * 5) * 0.004 - 0.02))
        return Bw @ (wig + V((0, BOARD_T / 2 + PAPER_T + PEN_LIFT, 0))), tip, shape, Rw, pole
    if h is not None and h.kind == 'touch' and h.part == 'belly' and shape == 'claw':
        from mathutils.bvhtree import BVHTree
        pt, nr = kr.part_world(ra, 'belly')
        tee = next(o for o in self.meshes if 'SHIRT' in o.name.upper())
        tw = _verts_world(tee); me = tee.evaluated_get(bpy.context.evaluated_depsgraph_get()).to_mesh()
        bv = BVHTree.FromPolygons([V(x) for x in tw], [list(pl.vertices) for pl in me.polygons]); tee.evaluated_get(bpy.context.evaluated_depsgraph_get()).to_mesh_clear()
        S = W @ self.palm[side]
        Ax = nr.cross(V((0, 0, 1))).normalized(); Ax = Ax if ((W @ tl) - pt).dot(Ax) > 0 else -Ax     # toward the hand's own side
        O = pt + V((0, 0, BELLY_UP)) + Ax * BELLY_SIDE + nr * 0.3                   # stomach (above the navel, below the print); from well in front
        loc, n2, _, _ = bv.ray_cast(O, -nr, 0.6)                   # first hit = the front of the (swollen) tee
        if loc is None: loc, n2, _, _ = bv.find_nearest(S, 0.3)
        if n2.dot(nr) < 0: n2 = -n2
        T = loc + n2 * 0.003
        # 4.12: the palm lies flat on the tee (palm normal into the belly), fingers across the belly toward the midline and a little down
        pn_l, pf_l = self.pn[side]; A = nr.cross(V((0, 0, 1))).normalized()
        if ((W @ tl) - pt).dot(A) > 0: A = -A
        fd = (A * math.cos(math.radians(BELLY_DOWN)) - V((0, 0, 1)) * math.sin(math.radians(BELLY_DOWN))); fd = (fd - n2 * fd.dot(n2)).normalized()
        nw = -n2; Rl = Matrix((pf_l, pn_l, pf_l.cross(pn_l))).transposed(); Rt = Matrix((fd, nw, fd.cross(nw))).transposed()
        Rw = Rt @ Rl.transposed(); W = Matrix.Translation(D - Rw @ tl) @ Rw.to_4x4(); S = W @ self.palm[side]
        self._bdbg = (side, T, D, W @ tl)
        if os.environ.get('KW_HG_AUDIT'): print('AUDIT bellyT', side, 'pt', tuple(round(c, 3) for c in pt), 'nr', tuple(round(c, 2) for c in nr), 'T', tuple(round(c, 3) for c in T), 'tee z', round(min(x[2] for x in tw), 3), round(max(x[2] for x in tw), 3))
        return D + (T - S), tip, shape, Rw, pole
    return g


GRIP_DIAG = 15.0
SPOON_TILT = 20.0
GLASS_DZ = 0.0     # lens-rim centre vs eye centre along head up (m)
BELLY_UP = 0.17
BELLY_DOWN = 20.0
BELLY_SIDE = 0.04
SEAT_SINK = 0.002
SKIN_TONE = {'Ben': dict(Tone=0.55, Redness=0.75, Saturation=1.6), 'Howard': dict(Redness=0.45)}   # 4.12: lids not red
TILT = {'can': math.radians(40), 'spoon': math.radians(SPOON_TILT)}


def _drink_w(self, kr, ra, u):
    acts = [ac for x in kr._cur if x[0] is ra for q in (x[1], x[2]) for ac in q.acts]
    sm = lambda x, a, b: 0.0 if x <= a else 1.0 if x >= b else (lambda y: y * y * (3 - 2 * y))((x - a) / (b - a))
    w = 0.0
    for ac in acts:
        if ac.kind == 'drink':
            d = ac.kw.get('dur', 1.2); w = max(w, sm(u, ac.at, ac.at + 0.4 * d) * (1 - sm(u, ac.at + 0.6 * d, ac.at + d)))     # up 40 %, hold 20 %, down 40 %
    return w



# ---------------------------------------------------------------- can grip (grip brief G1-G14 / M1-M8): built pose, not a retarget
CAN_REST = 17.0      # deg: can axis above horizontal when held at the lips (not drinking)
CAN_AB_MAX = 33.0   # deg upper-arm abduction ceiling on every frame of a sip (real drinking 30-39; G4 <= 40)
CAN_PEAK = 36      # deg: at the top of a sip (bottom raised)
CAN_BETA = 195.0     # deg: where the lip touches the rim, measured round the lid from its lowest point (180 = the highest point: opening on the lip, lid faces the chin)
CAN_YAW = 38.0       # deg: can axis swung from straight-ahead toward the hand side (keeps the nose/eyes clear, G9)
CAN_LIP = 0.002      # m: rim edge in front of the lower-lip landmark (G5 0-4 mm)
CAN_SLIDE = 0.010      # m: hand centre along the can axis (+ toward the top) for G1 ~50 %
CAN_ELB_OUT = 0.35   # hand-back target: down + this much out (keeps the wrist straight, elbow low)
CAN_DF = (0.015,)   # can offset search in the hand (finger direction, m)
CAN_DN = (0.002,)
CAN_DG = (0.010,)                       # hand lower on the can (m): index 3-4 cm under the rim like a real hold
CAN_ROLL = (8.0,)
CAN_PYAW = (10.0,)
FGAP = 0.0015        # m: skin gap between neighbouring middle finger segments (G10 side by side, 0 overlap)   # can axis turned in the palm plane (about the palm normal): the oblique palm crease, pinky end nearer the fingers
WRAP_MIN = 150.0                                # deg: fingertips round the can from the palm contact (G2)                    # deg                  # (palm normal, m)
CAN_NREF = 4                                     # capsule candidates refined on the real skin
CAN_POLE_F = 0.25    # pole forward (m): elbow low and forward, G4
CAN_POLE_O = 0.20    # pole out (m)
CAN_POLE_FS = (0.05, 0.15, 0.25, 0.35)   # pole search (forward, m): straightest wrist inside G4
CAN_POLE_OS = (-0.10, 0.0, 0.10, 0.20, 0.35)


def _can_goal(self, kr, ra, side, tip, shape, u):
    r, hh = GRIP['can']; p = ra.p
    sg = 1.0 if side == 'L' else -1.0; R = p.rig.matrix_world.to_3x3().normalized()
    Lp, Fp, Up = R @ V((1, 0, 0)), R @ V((0, -1, 0)), R @ V((0, 0, 1)); out = Lp * sg
    L = kr.wmat(p, 'head') @ self.lip_local; _, nr = kr.part_world(ra, 'mouth')
    Z = V((0, 0, 1)); nh = V((nr.x, nr.y, 0)).normalized()
    oh = out - nh * out.dot(nh); oh.z = 0; oh.normalize()
    th = math.radians(CAN_REST + (CAN_PEAK - CAN_REST) * self.drink_w(kr, ra, u))
    yw = math.radians(CAN_YAW); fh = (nh * math.cos(yw) + oh * math.sin(yw)).normalized()
    a = (-fh * math.cos(th) - Z * math.sin(th)).normalized()          # can axis bottom -> top; top at the lips, bottom out and down
    d0 = (-Z - a * (-Z).dot(a)).normalized(); s0 = a.cross(d0).normalized()
    if s0.dot(oh) > 0: s0 = -s0
    bt = math.radians(CAN_BETA); uu = (d0 * math.cos(bt) + s0 * math.sin(bt)).normalized()   # lid centre -> rim contact on the lower lip (lid sits up/toward the hand side, clear of the nose)
    P = L + nr * CAN_LIP; Ct = P - uu * r; C = Ct - a * (hh / 2)
    Pr = self.Pl[(side, 'can')].to_3x3(); f_, n_, g_ = Pr.col[0], Pr.col[1], Pr.col[2]
    hs = 1.0 if n_.cross(g_).dot(f_) > 0 else -1.0
    gw = -a                                                          # grip axis index -> pinky runs top -> bottom
    sh = kr.bw(p, f'upperarm01.{side}')
    l1 = (kr.bw(p, f'lowerarm01.{side}') - sh).length; l2 = (kr.bw(p, f'wrist.{side}') - kr.bw(p, f'lowerarm01.{side}')).length
    def elbow(W, pl):           # 2-bone IK elbow for shoulder sh, wrist W, pole pl
        d = W - sh; dl = min(d.length, l1 + l2 - 1e-4); u_ = d.normalized()
        aa = (l1 * l1 - l2 * l2 + dl * dl) / (2 * dl); hg_ = math.sqrt(max(l1 * l1 - aa * aa, 0.0))
        v_ = (pl - sh) - u_ * (pl - sh).dot(u_); v_ = v_.normalized() if v_.length > 1e-6 else -Z
        return sh + u_ * aa + v_ * hg_
    b0 = (-oh - a * (-oh).dot(a)).normalized()
    def frame(phi):
        nw = (Matrix.Rotation(phi, 3, a) @ b0).normalized()           # palm -> can axis
        fw = (nw.cross(gw) * hs).normalized()
        return Matrix((fw, nw, gw)).transposed() @ Pr.inverted()
    Wc = C - a * 0.02                       # wrist ~ near the can middle (refined below from the real frame)
    def solve(e_t):
        def cost(phi):
            Rw_ = frame(phi); return (Rw_ @ V((0, -1, 0))).normalized().angle(e_t)
        ph_ = min((i * math.pi / 18 for i in range(36)), key=cost); st = math.pi / 36
        for _ in range(12):
            ph_ = min((ph_ - st, ph_, ph_ + st), key=cost); st *= 0.5
        return ph_, cost(ph_)
    best = None
    # ONE elbow pole per shot (chosen on the shot's first solve = the M1 rest at the mouth, canonical pass): re-choosing it
    # per frame flipped the elbow between grid poles mid-tilt (abduction 16 -> 49 -> 14 deg in 4 frames, G12 pop)
    self._polememo = getattr(self, '_polememo', {}); sh_ = getattr(kr, '_hshot', None)
    pk = (side, sh_.name if sh_ is not None else None); fixed = self._polememo.get(pk)
    def trial(pf, po, Wc):
        pl = sh - Up * 0.6 + Fp * pf + out * po
        for _ in range(2):
            E_ = elbow(Wc, pl); e_t = (E_ - Wc).normalized(); ph, cb = solve(e_t)
            Wm_ = Matrix.Translation(C + a * CAN_SLIDE) @ (frame(ph) @ Pr).to_4x4() @ self.Pl[(side, 'can')].inverted(); Wc = Wm_.translation.copy()
        E_ = elbow(Wc, pl)                  # the elbow for the FINAL wrist (was the previous iterate's)
        drop = Wc.z - E_.z; el_ = math.degrees(math.asin(max(-1, min(1, (Wc - E_).normalized().z))))
        ua = (E_ - sh).normalized(); ab_ = math.degrees(math.atan2(ua.dot(out), -ua.dot(Up)))
        pen = (0 if drop >= 0.12 else (0.12 - drop) * 20) + (0 if 50 <= el_ <= 80 else min(abs(el_ - 50), abs(el_ - 80)) / 20) \
            + (0 if ab_ <= CAN_AB_MAX else (ab_ - CAN_AB_MAX) / 10) + (0 if (E_ - sh).dot(Fp) >= -0.02 else 1.0)
        return (cb + pen, ph, pl, cb, pf, po, ab_)
    if fixed:
        # same pole all shot; when the tilt swings the elbow out past CAN_AB_MAX the pole slides inward continuously (bisection)
        best = trial(fixed[0], fixed[1], Wc)
        if best[6] > CAN_AB_MAX:
            lo, hi = fixed[1] - 0.8, fixed[1]
            for _ in range(10):
                mid = (lo + hi) / 2; t_ = trial(fixed[0], mid, Wc)
                if t_[6] > CAN_AB_MAX: hi = mid
                else: lo = mid
            best = trial(fixed[0], lo, Wc)
    else:
        for pf in CAN_POLE_FS:
            for po in CAN_POLE_OS:
                t_ = trial(pf, po, Wc)
                if best is None or t_[0] < best[0]: best = t_
    _, ph, pole, cb, pf_, po_, _ = best
    if pk[1] is not None and not fixed: self._polememo[pk] = (pf_, po_)
    def cost(phi): return cb if phi == ph else 0.0
    Rw = frame(ph)
    Gw = Matrix.Translation(C + a * CAN_SLIDE) @ (Rw @ Pr).to_4x4()
    Wm = Gw @ self.Pl[(side, 'can')].inverted()
    yc = uu.copy(); xc = yc.cross(a).normalized()
    CanM = Matrix((xc, yc, a)).transposed().to_4x4(); CanM.translation = C        # can local +z = top, local +y = the lip side (drinking opening)
    self._canrel = getattr(self, '_canrel', {}); self._canrel[side] = Wm.inverted() @ CanM
    self._candbg = dict(side=side, th=math.degrees(th), phi=math.degrees(ph), wb=math.degrees(cost(ph)), L=L.copy(), P=P.copy(), a=a.copy())
    tl = ra.hand[side][shape][tip]
    return Wm @ tl, tip, shape, Rw, pole


def _solve_can(self, kr, s):
    """3-segment grip on the can (capsules on the HG finger bones): every finger/thumb segment 0-4 mm off the can.
    Searches the can offset in the hand (along the finger direction and the palm normal) and per-finger (base, middle, tip) flex."""
    p = self.p; rig = p.rig; RW = rig.matrix_world; key = 'can'; r, h = GRIP[key]
    Mw = kr.wmat(p, f'wrist.{s}'); P0 = self.Pl[(s, key)].copy()
    cache = os.environ.get('KW_CANCACHE')            # sandbox speed-up for the measuring loop only (never set in CI)
    if cache and os.path.exists(cache):
        import json as _j; cc = _j.load(open(cache))
        self.Pl[(s, key)] = Matrix(cc['Pl']); self.cangrip = getattr(self, 'cangrip', {}); self.cangrip[(s, key)] = True
        self.canax = getattr(self, 'canax', {}); self.canax[s] = {tuple(int(x) for x in kk.split(',')): tuple(v) for kk, v in cc['ax'].items()}
        print('humgen cangrip from cache', cache); return {int(k): tuple(v) for k, v in cc['out'].items()}
    f_, n_, g_ = P0.col[0].xyz, P0.col[1].xyz, P0.col[2].xyz
    def segc(g): return 0.0 if 0.0005 <= g <= 0.0035 else (0.0005 - g) * 12.0 if g < 0.0005 else (g - 0.0035) * 1.5 + 0.0002
    # refine on the REAL HG skin (all 3 segments, palm, thumb opposition): coordinate descent, all fingers at once
    vgi = {g.name: g.index for g in self.body.vertex_groups}
    def ids(names, wmin=0.5):
        gi = {vgi[n] for n in names if n in vgi}
        return np.array([v.index for v in self.body.data.vertices if any(g.group in gi and g.weight > wmin for g in v.groups)], int)
    FN = {1: 'thumb', 2: 'f_index', 3: 'f_middle', 4: 'f_ring', 5: 'f_pinky'}
    SEGI = {(k, j): ids([f'{FN[k]}.0{j}.{s}']) for k in FN for j in (1, 2, 3)}
    PALMI = ids([f'hand.{s}'] + [f'palm.0{i}.{s}' for i in range(1, 5)], 0.6)
    pbs = {k: [rig.pose.bones[f'finger{k}-{j}.{s}'] for j in (1, 2, 3)] for k in FN}
    base = {k: [pb.rotation_euler.copy() for pb in v] for k, v in pbs.items()}
    # true flex axis per finger bone (bone direction x palm normal, in the bone's own posed frame): the rig's X is not pure flexion
    n_arm = (RW.to_3x3().inverted() @ (Mw.to_3x3() @ n_)).normalized(); AX = {}
    # ONE hinge per finger = the can axis (made perpendicular to the base bone): every joint curls AROUND the can.
    # (bone-y x palm-normal per joint drifted 51-86 deg off the can axis on the bent middle/tip bones -> fingers curled along the can)
    g_arm = (RW.to_3x3().inverted() @ (Mw.to_3x3() @ g_)).normalized()
    for k in range(2, 6):
        y0 = (pbs[k][0].matrix.to_3x3().normalized() @ V((0, 1, 0))).normalized()
        hk = (g_arm - y0 * g_arm.dot(y0)).normalized()
        if hk.dot(y0.cross(n_arm)) < 0: hk = -hk
        for j, pb in enumerate(pbs[k]):
            R3 = pb.matrix.to_3x3().normalized()
            AX[(k, j)] = (R3.inverted() @ hk).normalized()
    self.canax = getattr(self, 'canax', {}); self.canax[s] = {kj: tuple(v) for kj, v in AX.items()}
    def setang(A):
        for k, ang in A.items():
            for j, pb in enumerate(pbs[k]):
                e = base[k][j].copy()
                if k == 1: e.x += math.radians(ang[0] if j == 0 else ang[3] if (j == 2 and len(ang) > 3) else ang[2]); e.z += math.radians(ang[1] if j == 0 else 0.0)
                else:
                    ax_ = axes(k)[j]; R_ = e.to_matrix() @ Matrix.Rotation(math.radians(ang[j]), 3, ax_)
                    if j == 0 and ADD.get(k): R_ = R_ @ Matrix.Rotation(math.radians(ADD[k][1]), 3, ADD[k][0])     # adduct first, then flex about the can hinge
                    e = R_.to_euler(e.order, e)
                pb.rotation_euler = e
    ADD = {}                                          # G10 finger adduction at the knuckle: (local axis, deg)
    R3b = {(k, j): pb.matrix.to_3x3().normalized() for k in range(2, 6) for j, pb in enumerate(pbs[k])}
    def axes(k):
        # middle / tip hinges stay ON the can axis when the knuckle is adducted (the adduction turns their frames)
        if not ADD.get(k): return [AX[(k, 0)], AX[(k, 1)], AX[(k, 2)]]
        Ri = Matrix.Rotation(-math.radians(ADD[k][1]), 3, ADD[k][0]); h0 = AX[(k, 0)]
        return [h0] + [(R3b[(k, j)].inverted() @ R3b[(k, 0)] @ Ri @ h0).normalized() for j in (1, 2)]
    def ev(A, Mc):
        setang(A); w = _body_world(self); Mi = np.array(Mc.inverted())
        gp = {kj: float(_sd_cyl(w[v], Mc, r, h).min()) for kj, v in SEGI.items() if len(v)}
        def arc(v): lp = w[v].mean(0) @ Mi[:3, :3].T + Mi[:3, 3]; return math.degrees(math.atan2(lp[1], lp[0]))
        d = abs(arc(SEGI[(1, 3)]) - arc(SEGI[(2, 3)])) % 360; d = min(d, 360 - d)
        dpal = _sd_cyl(w[PALMI], Mc, r, h); pg = float(dpal.min())
        # G2 wrap: each finger runs round the can from the palm contact (palm -> proximal -> middle -> tip), tip >= 150 deg
        a0 = arc(PALMI[[int(np.argmin(dpal))]]); wrap = {}
        for k in range(2, 6):
            prev = a0; tot_ = 0.0
            for j in (1, 2, 3):
                aj = arc(SEGI[(k, j)]); dd = (aj - prev + 180) % 360 - 180; tot_ += dd; prev = aj
            wrap[k] = tot_
        sg_ = 1.0 if sum(wrap.values()) >= 0 else -1.0
        self._wrap = {k: sg_ * v for k, v in wrap.items()}
        cs = {k: sum(segc(gp[(k, j)]) for j in (1, 2, 3) if (k, j) in gp) + 0.0002 * max(0.0, WRAP_MIN - sg_ * wrap[k]) for k in range(2, 6)}
        cs[1] = sum(segc(gp[(1, j)]) for j in (2, 3)) + (0.0 if 110 <= d <= 190 else 0.06 * min(abs(d - 110), abs(d - 190)) / 10)
        return cs, gp, d, pg
    def bis(A, Mc, j, lo, hi, n=7):
        # per finger (2-5): angle of joint j so that segment j+1 sits SKIN off the can (gap falls as the joint flexes)
        L_ = {k: lo for k in range(2, 6)}; H_ = {k: hi for k in range(2, 6)}
        B = {k: list(v) for k, v in A.items()}
        for k in L_: B[k][j] = hi
        _, gh, _, _ = ev(B, Mc)
        reach = {k: gh[(k, j + 1)] <= SKIN for k in L_}
        for _ in range(n):
            for k in L_: B[k][j] = (L_[k] + H_[k]) / 2
            _, gm, _, _ = ev(B, Mc)
            for k in L_:
                if gm[(k, j + 1)] > SKIN: L_[k] = B[k][j]
                else: H_[k] = B[k][j]
        for k in L_: A[k][j] = H_[k] if reach[k] else hi
        return A
    res = None
    Sp = P0.translation - n_ * (r + SKIN)                  # palm skin contact point (wrist space)
    for df, dn, rho, dg, yw in [(a_, b_, c_, d_, e_) for a_ in CAN_DF for b_ in CAN_DN for c_ in CAN_ROLL for d_ in CAN_DG for e_ in CAN_PYAW]:
            Rr = Matrix.Rotation(math.radians(yw), 4, n_) @ Matrix.Rotation(math.radians(rho), 4, f_)      # roll the can inside the palm about the finger direction (brings the little-finger end in)
            Pl = Matrix.Translation(Sp) @ Rr @ Matrix.Translation(-Sp) @ P0; Pl.translation = Pl.translation + f_ * df + n_ * dn - g_ * dg; Mc = Mw @ Pl     # -g: the can slides toward its top, the hand sits lower on it
            A = {k: [-20.0, -20.0, -20.0] for k in range(2, 6)}; A[1] = [30.0, -30.0, 35.0]
            A = bis(A, Mc, 0, -30.0, 100.0); A = bis(A, Mc, 1, -20.0, 110.0); A = bis(A, Mc, 2, -20.0, 90.0)
            bt_ = None
            for x1 in (0, 30, 60):
                for z1 in (-60, -30, 0, 30):
                    for x2 in (0, 35, 70):
                        A[1] = [x1, z1, x2]; c_, _, _, _ = ev(A, Mc)
                        if bt_ is None or c_[1] < bt_[0]: bt_ = (c_[1], [x1, z1, x2])
            A[1] = bt_[1]
            cs, gp, d, pg = ev(A, Mc)
            tot = sum(cs.values()) + (0.0 if -0.001 <= pg <= 0.004 else abs(pg - 0.0015) * 12)
            print(f'humgen cangrip try {p.name} {s}: f {1000 * df:.1f} n {1000 * dn:.1f} roll {rho} yaw {yw} axial {1000 * dg:.0f} real {tot:.4f} palm {1000 * pg:.1f} thumb-index {d:.0f} wrap', {k: round(v) for k, v in self._wrap.items()},
                  {k: [round(x) for x in v] for k, v in A.items()}, {f'{FN[k][-5:]}{j}': round(1000 * g, 1) for (k, j), g in gp.items()})
            if res is None or tot < res[0]: res = (tot, df, dn, {k: list(v) for k, v in A.items()}, Pl, d, pg, dict(gp))
    tot, df, dn, A, Pl, d, pg, gp = res; Mc = Mw @ Pl
    # per finger: back the knuckle off so the middle and tip joints can wrap (greedy base-first leaves the tip floating)
    cs0, _, _, _ = ev(A, Mc); keep = {k: (cs0[k], list(A[k])) for k in range(2, 6)}
    for bo in (3, 5, 6, 7, 8, 10, 13):
        B = {k: [A[k][0] - bo, -20.0, -20.0] for k in range(2, 6)}; B[1] = list(A[1])
        B = bis(B, Mc, 1, -20.0, 110.0); B = bis(B, Mc, 2, -20.0, 90.0); cb_, gb_, _, _ = ev(B, Mc)
        for k in range(2, 6):
            if cb_[k] < keep[k][0]: keep[k] = (cb_[k], list(B[k]))
        print(f'humgen cangrip knuckle back-off {bo}:', {FN[k]: [round(1000 * gb_[(k, j)], 1) for j in (1, 2, 3)] for k in range(2, 6)})
    for k in range(2, 6): A[k] = keep[k][1]
    # G10 side by side: each finger turns at the knuckle about the palm normal until its middle segment is FGAP from the
    # neighbour toward the middle finger (index -> middle, ring -> middle, little -> ring); the fingers no longer splay in a V
    from mathutils.kdtree import KDTree
    def fgap(a_, b_):           # min skin gap over the middle AND tip segments (the tip of a converging finger crossed the ring)
        setang(A); w = _body_world(self); P = np.concatenate([w[SEGI[(b_, j)]] for j in (2, 3)]); t_ = KDTree(len(P))
        for i_, q in enumerate(P): t_.insert(V(q), i_)
        t_.balance(); return min(t_.find(V(q))[2] for j in (2, 3) for q in w[SEGI[(a_, j)]])
    for k, nb in ((2, 3), (4, 3), (5, 4)):
        nl = (pbs[k][0].matrix.to_3x3().normalized().inverted() @ n_arm).normalized(); g0 = fgap(k, nb); tr = {}
        for sgn in (1.0, -1.0): ADD[k] = (nl * sgn, 6.0); tr[sgn] = fgap(k, nb)
        sg = min(tr, key=tr.get)
        if tr[sg] >= g0 or g0 <= FGAP: ADD[k] = None; print(f'humgen cangrip adduct finger{k}: none (gap {1000 * g0:.1f}, +6 {1000 * tr[1.0]:.1f}, -6 {1000 * tr[-1.0]:.1f} mm)'); continue
        lo, hi = 0.0, (10.0 if k == 2 else 18.0)      # index: more than 10 deg tips it into a cone and the tip leaves the can
        for _ in range(7):
            mid = (lo + hi) / 2; ADD[k] = (nl * sg, mid)
            if fgap(k, nb) > FGAP: lo = mid
            else: hi = mid
        ADD[k] = (nl * sg, lo)
        print(f'humgen cangrip adduct finger{k} toward {nb}: {lo:.1f} deg, middle-segment gap {1000 * g0:.1f} -> {1000 * fgap(k, nb):.1f} mm')
    if any(ADD.values()):
        c0_, _, _, _ = ev(A, Mc); B = {k: list(v) for k, v in A.items()}
        B = bis(B, Mc, 1, -20.0, 110.0); B = bis(B, Mc, 2, -20.0, 90.0); c1_, gb_, _, _ = ev(B, Mc)
        for k in range(2, 6):
            if c1_[k] < c0_[k]: A[k] = B[k]
        print('humgen cangrip after adduction re-fit:', {FN[k]: [round(x) for x in A[k]] for k in range(2, 6)})
    for k, nb in ((2, 3), (3, 4), (4, 3), (5, 4)):     # guard after the re-fit: the new curl must not push a finger into its neighbour
        if fgap(k, nb) >= 0.0005: continue
        g_ = fgap(k, nb)
        if ADD.get(k):
            ax_, dg_ = ADD[k]; lo, hi = 0.0, dg_
            for _ in range(7):
                mid = (lo + hi) / 2; ADD[k] = (ax_, mid)
                if fgap(k, nb) >= 0.0005: lo = mid
                else: hi = mid
            ADD[k] = (ax_, lo)
        print(f'humgen cangrip overlap guard finger{k}->{nb}: {1000 * g_:.1f} -> {1000 * fgap(k, nb):.1f} mm, adduct {ADD[k][1] if ADD.get(k) else 0:.1f}')
    AXo = dict(AX)
    for k in range(2, 6):
        for j, a_ in enumerate(axes(k)): AXo[(k, j)] = a_
        if ADD.get(k): AXo[(k, -2)] = ADD[k][0] * ADD[k][1]          # adduction: axis * deg (consumer)
    self.canax[s] = {kj: tuple(v) for kj, v in AXo.items()}
    # thumb on the chosen placement: coarse grid on the real skin (base x, base z, outer x), 2 outer segments + opposition
    best = None
    TLIM = ((-20, 60), (-60, 30), (0, 70), (0, 85))  # real thumb ranges (deg): base flex, base swing, MCP flex 0-70, IP flex 0-85
    for x1 in range(-20, 61, 10):
        for z1 in range(-60, 31, 15):
            for x2 in range(0, 71, 14):
                A[1] = [x1, z1, x2, x2]; cs, gp, d, pg = ev(A, Mc)
                if best is None or cs[1] < best[0]: best = (cs[1], [x1, z1, x2, x2])
    A[1] = best[1]
    for st in (10, 5, 2):
        for jj in (0, 1, 2, 3):
            for dd in (st, -st):
                B1 = list(A[1]); B1[jj] = min(max(B1[jj] + dd, TLIM[jj][0]), TLIM[jj][1]); A2 = dict(A); A2[1] = B1; c2_, _, _, _ = ev(A2, Mc)
                if c2_[1] < best[0]: best = (c2_[1], B1); A[1] = B1
    cs, gp, d, pg = ev(A, Mc); tot = sum(cs.values()) + (0.0 if -0.001 <= pg <= 0.004 else abs(pg - 0.0015) * 12)
    setang({k: (0, 0, 0) for k in FN})
    self.Pl[(s, key)] = Pl
    out = {k: tuple(round(x, 1) for x in A[k]) + (round(1000 * min(gp[(k, j)] for j in (1, 2, 3) if (k, j) in gp), 1),) for k in FN}     # thumb: (x1, z1, MCP, IP, gap)
    print(f'humgen cangrip {p.name} {s}: offset f {1000 * df:.1f} n {1000 * dn:.1f} mm real cost {tot:.4f} palm {1000 * pg:.1f} thumb-index {d:.0f} deg', out)
    self.cangrip = getattr(self, 'cangrip', {}); self.cangrip[(s, key)] = True
    if cache:
        import json as _j; _j.dump(dict(Pl=[list(rw) for rw in Pl], out=out, ax={f'{a},{b}': v for (a, b), v in self.canax[s].items()}), open(cache, 'w'))
    return out


Graft.can_goal = _can_goal


CAN_AB_REAL = 36.0    # deg, kit-bone abduction ceiling on the solved pose (HG mesh reads ~2 deg more -> <= 38-39, real drinking 30-39, G4 <= 40)


def _post_ik(self, kr, ra, side, h, shape):
    """the blended goals of a pose transition (lift / lower) put the IK elbow where neither solve checked it (abduction
    41-44 deg mid-lift): measure the real kit arm and slide the pole inward (continuous bisection) until it is under the ceiling."""
    spoon_ = (h is not None and h.kind == 'hold' and h.prop == 'spoon' and h.at == 'mouth' and shape == 'hold'
              and (side, 'spoon') in getattr(self, 'curl', {}) and getattr(self, '_sp_ab', None) is not None)
    if not spoon_ and not (h is not None and h.kind == 'hold' and h.prop == 'can' and h.at == 'mouth' and shape == 'hold'
            and (side, 'can') in getattr(self, 'cangrip', {})):
        return
    p = ra.p; R = p.rig.matrix_world.to_3x3().normalized(); sg = 1.0 if side == 'L' else -1.0
    out = R @ V((sg, 0, 0)); Up = R @ V((0, 0, 1)); pl = ra.ik[side][2]
    def ab():
        sh = kr.bw(p, f'upperarm01.{side}'); u_ = (kr.bw(p, f'lowerarm01.{side}') - sh).normalized()
        return math.degrees(math.atan2(u_.dot(out), -u_.dot(Up)))
    if spoon_:
        # R6: abduction follows the bite path (low point < 20, at the lips 35-55): continuous bisection of the pole along out
        T = self._sp_ab; P0 = pl.location.copy(); lo, hi = -0.6, 0.6
        for _ in range(10):
            mid = (lo + hi) / 2; pl.location = P0 + out * mid; bpy.context.view_layer.update()
            if ab() > T: hi = mid
            else: lo = mid
        pl.location = P0 + out * ((lo + hi) / 2); bpy.context.view_layer.update(); return
    if ab() <= CAN_AB_REAL: return
    P0 = pl.location.copy(); lo, hi = 0.0, 0.6        # metres the pole moves inward
    pl.location = P0 - out * hi; bpy.context.view_layer.update()
    if ab() > CAN_AB_REAL: return                     # cannot reach the ceiling: keep the widest slide
    for _ in range(9):
        mid = (lo + hi) / 2; pl.location = P0 - out * mid; bpy.context.view_layer.update()
        if ab() > CAN_AB_REAL: lo = mid
        else: hi = mid
    pl.location = P0 - out * hi; bpy.context.view_layer.update()


Graft.post_ik = _post_ik
Graft._solve_can = _solve_can


Graft.drink_w = _drink_w


def _v11_author(self, kr, side, prop, tab):
    """authoring aid only (KW_V11_AUTHOR=1): prints the thumb/index pad gap for scaled tables; the chosen numbers go into AUTH"""
    p = self.p; vg = {g.name: g.index for g in self.body.vertex_groups}
    def grp(n):
        gi = vg[n]; return np.array([v.index for v in self.body.data.vertices if any(g.group == gi and g.weight > 0.5 for g in v.groups)])
    it, ii = grp(f'thumb.03.{side}'), grp(f'f_index.03.{side}')
    RW = self.rig.matrix_world
    mk = [m for m in self.body.modifiers if m.type == 'MASK' and m.show_viewport]
    for m in mk: m.show_viewport = False
    for ti in (0.85, 1.0, 1.15):
        for ix in (0.9, 1.0, 1.1):
            for tz in (-10, -20, -30):
                for k, (ang, tz0) in tab.items():
                    if k not in (1, 2): continue
                    for jj in (1, 2, 3):
                        e = p.pb(f'finger{k}-{jj}.{side}').rotation_euler
                        sc = ti if k == 1 else ix
                        e.x = math.radians(ang[jj - 1] * sc); e.z = math.radians(tz if (k == 1 and jj == 1) else 0.0) * (1 if side == 'R' else -1)
                bpy.context.view_layer.update(); W = _verts_world(self.body)
                A, B = W[it], W[ii]; d = np.linalg.norm(A[:, None, :] - B[None, :, :], axis=2); a, b = np.unravel_index(np.argmin(d), d.shape)
                T = RW @ self.rig.pose.bones[f'thumb.03.{side}'].tail; I = RW @ self.rig.pose.bones[f'f_index.03.{side}'].tail
                Mw = kr.wmat(p, f'wrist.{side}'); mid = V(((A[a] + B[b]) / 2).tolist()); off = Mw.to_3x3().inverted() @ (mid - (T + I) / 2)
                print(f'V11AUTH {prop} thumb x{ti} index x{ix} tz {tz}: pad gap {1000 * d[a, b]:.1f} mm  bone tips {1000 * (T - I).length:.1f} mm  '
                      f'pad-mid off {tuple(round(c, 4) for c in off)}')
    for m in mk: m.show_viewport = True
    for k, (ang, tz0) in tab.items():
        for jj in (1, 2, 3):
            e = p.pb(f'finger{k}-{jj}.{side}').rotation_euler
            e.x = math.radians(ang[jj - 1]); e.z = math.radians(tz0 if jj == 1 else 0.0) * (1 if side == 'R' else -1)


def _v11_authored(self, kr, jobs):
    """cast v1.1 grip_pinch / grip_burger: fixed finger tables, then the item is put on the hand (it never moves the hand)"""
    p = self.p; RW = self.rig.matrix_world; moved = []
    _burger_hold(self, kr, jobs)
    for j in jobs:
        side, h = j[1], j[8]
        if not (h.kind == 'hold' and h.prop and h.prop in AUTH) or h.prop == 'g_burger': continue
        tab = AUTH_P.get((p.name, h.prop), AUTH[h.prop])
        for k, (ang, tz) in tab.items():
            for jj in (1, 2, 3):
                e = p.pb(f'finger{k}-{jj}.{side}').rotation_euler
                e.x = math.radians(ang[jj - 1]); e.y = 0.0; e.z = math.radians(tz if jj == 1 else 0.0) * (1 if side == 'R' else -1)
        moved.append((side, h))
        if os.environ.get('KW_V11_AUTHOR') and h.prop in ('g_pea', 'g_paperclip') and not getattr(self, '_v11_auth_done', {}).get(h.prop):
            self.__dict__.setdefault('_v11_auth_done', {})[h.prop] = 1; self._v11_author(kr, side, h.prop, tab)
    if not moved: return
    bpy.context.view_layer.update()
    tip = lambda b: RW @ self.rig.pose.bones[b].tail
    p = self.p
    for side, h in moved:
        ob = kr.FX.props.get(h.prop)
        if ob is None: continue
        Mw = kr.wmat(p, f'wrist.{side}'); n_, f_ = self.pn[side]; n = (Mw.to_3x3() @ n_).normalized(); f = (Mw.to_3x3() @ f_).normalized()
        off = V(AUTH_OFF.get(h.prop, (0, 0, 0)))
        if h.prop in ('g_pea', 'g_paperclip'):
            T, I = tip(f'thumb.03.{side}'), tip(f'f_index.03.{side}'); c = (T + I) / 2
            ax = (I - T).normalized(); up = n - ax * n.dot(ax); up.normalize()
            M = Matrix((ax, up.cross(ax), up)).transposed().to_4x4(); M.translation = c + Mw.to_3x3() @ off - (up * 0.004 if h.prop == 'g_pea' else V((0, 0, 0)))
            if h.prop == 'g_paperclip': M = M @ Matrix.Rotation(math.radians(90), 4, 'Y')      # clip plane between the pads
            ob.matrix_world = M
            if os.environ.get('KW_V11_DBG') or not getattr(self, '_v11_said', {}).get(h.prop):
                self.__dict__.setdefault('_v11_said', {})[h.prop] = 1
                print(f'cast v1.1 grip {p.name} {side}{h.prop}: tip-to-tip bone ends {1000 * (I - T).length:.1f} mm')
        elif h.prop in TOOL_AT:
            T, I = tip(f'thumb.03.{side}'), tip(f'f_index.03.{side}'); c = (T + I) / 2 + Mw.to_3x3() @ off
            Y = (I - T).normalized(); X = (f - Y * f.dot(Y)).normalized(); Z = X.cross(Y)
            gx, zc = TOOL_AT[h.prop]; M = Matrix((X, Y, Z)).transposed().to_4x4(); M.translation = c - X * gx - Z * zc
            ob.matrix_world = M
        elif h.prop == 'g_burger' and side == 'R':
            P = Mw @ self.palm[side]; L_ = kr.wmat(p, 'wrist.L'); PL = L_ @ self.palm['L']
            c = (P + PL) / 2 + Mw.to_3x3() @ off
            x = (PL - P).normalized(); z = V((0, 0, 1)); z = (z - x * z.dot(x)).normalized()
            fw = z.cross(x)          # toward the face side
            R = Matrix.Rotation(math.radians(-BURGER['tilt']), 3, x) @ Matrix((x, fw, z)).transposed()
            M = R.to_4x4(); M.translation = c - (R @ V((0, 0, BURGER['height'] * BURGER['squash'] / 2)))
            ob.matrix_world = M @ Matrix.Diagonal((1, 1, BURGER['squash'], 1))
            if os.environ.get('KW_V11_DBG'):
                bpy.context.view_layer.update()
                print('V11DBG near burger', sorted({o.name for o in bpy.data.objects if o.type in ('MESH', 'CURVE') and not o.hide_render and 'seed' not in o.name and
                                                    o.visible_camera and o not in ob.children_recursive and (o.matrix_world.translation - c).length < 0.6})[:60])
                bb_ = []
                for o in bpy.data.objects:
                    if o.type not in ('MESH', 'CURVE') or o.hide_render or not o.visible_camera or 'seed' in o.name: continue
                    cs = [o.matrix_world @ V(q) for q in o.bound_box]; lo = V([min(q[i] for q in cs) for i in range(3)]); hi = V([max(q[i] for q in cs) for i in range(3)])
                    cl = V([min(max(P[i], lo[i]), hi[i]) for i in range(3)])
                    if (cl - P).length < 0.08 and (hi - lo).length < 1.0: bb_.append((o.name, o.parent.name if o.parent else None, tuple(round(x, 3) for x in (hi - lo))))
                print('V11DBG bbox near right palm', bb_[:30])
            if os.environ.get('KW_V11_DBG'):
                for o_ in [ob] + list(ob.children_recursive)[:6]:
                    print('V11DBG burger obj', o_.name, 'z', tuple(round(x, 2) for x in o_.matrix_world.col[2][:3]), 'scale', tuple(round(x, 3) for x in o_.matrix_world.to_scale()),
                          'loc', tuple(round(x, 3) for x in o_.matrix_world.translation), 'mats', [m.name for m in getattr(o_.data, 'materials', [])][:2] if o_.data else None)
            if not getattr(self, '_v11_bsaid', False):
                self._v11_bsaid = True
                print(f'cast v1.1 grip {p.name} burger: palms {1000 * (PL - P).length:.1f} mm apart (bun {1000 * BURGER["width"]:.0f})')


# ============================================================ cast v1.1 round 2: finger closer (A1) + two-hand burger (A2)
BURGER2 = dict(width=0.11, height=0.06, front=0.24, tilt=20.0, lean=0.0, bite_in=0.012, bite_z=0.85, bite_tilt=30.0, bite_yaw=-15.0)
BURGER_HAND = dict(z=0.006, y=0.0)        # palm skin point in the burger frame: height above the bun bottom, front-back offset
BURGER_TIP_IN = 0.030                      # m: fingertips this far in from the crown edge
FINGER_ROM = {1: (60.0, 70.0, 80.0), 2: (90.0, 105.0, 80.0)}   # deg flex limits (MCP, PIP, DIP); thumb row 1, fingers row 2 (k >= 2)


def close_hand(self, kr, side, objs, fingers=(1, 2, 3, 4, 5), start=None, step=2.0, gap=0.002, pen=0.002, max_deg=110.0, thumb_z=(-70, -55, -40, -25), score=None, spread=0.022):
    """A1 reusable 'close the hand on the thing': every finger curls its three joints together from `start` (default open)
    in `step` degree steps until its distal two segments are within `gap` of the prop surface (signed distance against the
    evaluated prop meshes in `objs`, BVH nearest point), then stops (a last bisection keeps it within `pen` inside).
    The thumb does the same from the other side for each opposition angle in `thumb_z` (joint-1 z); `score(tip_world)` picks
    one (lower is better; default: nearest contact).  Returns {k: ((j1, j2, j3), z)} absolute degrees (AUTH format) and a
    report dict (gap mm per finger, neighbour tip gaps mm).  Joint limits: curls stop at `max_deg` on joint 1."""
    from mathutils.bvhtree import BVHTree
    p = self.p; dg = bpy.context.evaluated_depsgraph_get(); trees = []
    for o in objs:
        ev = o.evaluated_get(dg); me = ev.to_mesh(); Mw = ev.matrix_world
        vs = [Mw @ v.co for v in me.vertices]; fs = [tuple(pl.vertices) for pl in me.polygons]; ev.to_mesh_clear()
        if fs: trees.append(BVHTree.FromPolygons(vs, fs))
    def sdist(P):
        best = None
        for tr in trees:
            loc, nor, _, d = tr.find_nearest(V(P))
            if loc is None: continue
            sd = d if (V(P) - loc).dot(nor) >= 0 else -d
            if best is None or abs(sd) < abs(best): best = sd
        return 1.0 if best is None else best
    sg = 1 if side == 'R' else -1
    st = {k: (tuple(start[k][0]), start[k][1]) if start and k in start else ((0.0, 0.0, 0.0), 0.0) for k in fingers}
    rom = lambda k, jj, a: min(a, FINGER_ROM[1 if k == 1 else 2][jj - 1])
    def setf(k, c, z):
        a0, z0 = st[k]
        for jj in (1, 2, 3):
            e = p.pb(f'finger{k}-{jj}.{side}').rotation_euler
            e.x = math.radians(rom(k, jj, a0[jj - 1] + c)); e.y = 0.0; e.z = math.radians(z if jj == 1 else 0.0) * sg
    def measure(ks):
        w = _body_world(self); out = {}
        for k in ks:
            ids = self.fids[(side, k)]
            out[k] = min(sdist(q) for q in w[ids]) if len(ids) else 1.0
        return out, w
    res = {}
    def run(ks, zs):
        c = {k: 0.0 for k in ks}; done = {}; bst = {}
        for k in ks: setf(k, 0.0, zs[k])
        while len(done) < len(ks):
            m, w = measure([k for k in ks if k not in done])
            for k, d in m.items():
                if k not in bst or abs(d) < abs(bst[k][1]): bst[k] = (c[k], d)
                if d <= gap:
                    if d < -pen:       # passed through: bisect back between the previous and this step
                        lo, hi = c[k] - step, c[k]
                        for _ in range(3):
                            mid = (lo + hi) / 2; setf(k, mid, zs[k]); dm = measure([k])[0][k]
                            if dm < -pen: hi = mid
                            elif dm > gap: lo = mid
                            else: break
                        c[k] = mid; d = dm
                    done[k] = (c[k], d)
                elif c[k] >= max_deg: done[k] = bst[k]; setf(k, bst[k][0], zs[k])     # never reached: keep the closest curl
                else: c[k] += step; setf(k, c[k], zs[k])
        return done
    body = [k for k in fingers if k != 1]
    if spread and all(k in fingers for k in (2, 3, 4, 5)):      # tips together: side swing so neighbour tip centres sit `spread` apart
        def tips_(cc):
            for k in body: setf(k, cc, st[k][1])
            w = _body_world(self); return {k: w[self.fids[(side, k)]].mean(0) for k in body}
        for k, nb_ in ((2, 3), (4, 3), (5, 4)):
            sc_ = []
            for z in range(-16, 17, 4):
                st[k] = (st[k][0], float(z)); tp = tips_(30.0); sc_.append((abs(float(np.linalg.norm(tp[k] - tp[nb_])) - spread), z))
            st[k] = (st[k][0], float(min(sc_)[1]))
        for k in body: setf(k, 0.0, st[k][1])
    r = run(body, {k: st[k][1] for k in body})
    for k, (c, d) in r.items(): res[k] = (tuple(rom(k, jj, a + c) for jj, a in enumerate(st[k][0], 1)), st[k][1], d)
    if 1 in fingers:
        best = None
        for z in thumb_z:
            st[1] = (st[1][0], float(z)); rt = run([1], {1: float(z)}); c, d = rt[1]
            w = _body_world(self); tipw = V(w[self.fids[(side, 1)]].mean(0))
            sc = (0 if d <= gap else 1, score(tipw) if score else abs(d))
            if best is None or sc < best[0]: best = (sc, z, c, d)
        _, z, c, d = best; st[1] = (st[1][0], float(z)); res[1] = (tuple(rom(1, jj, a + c) for jj, a in enumerate(st[1][0], 1)), float(z), d)
    for k, (a, z, d) in res.items():
        for jj in (1, 2, 3):
            e = p.pb(f'finger{k}-{jj}.{side}').rotation_euler
            e.x = math.radians(a[jj - 1]); e.y = 0.0; e.z = math.radians(z if jj == 1 else 0.0) * sg
    w = _body_world(self); tips = {k: w[self.fids[(side, k)]].mean(0) for k in range(2, 6)}
    nb = {f'{a}-{b}': round(1000 * float(np.linalg.norm(tips[a] - tips[b])), 1) for a, b in ((2, 3), (3, 4), (4, 5))}
    rep = {'gap_mm': {k: round(1000 * d, 1) for k, (a, z, d) in res.items()}, 'tip_centres_mm': nb}
    return {k: (tuple(round(x, 1) for x in a), z) for k, (a, z, d) in res.items()}, rep


def _side_out(kr, ra, side):
    """unit world vector from the body midline toward this side's shoulder (horizontal)"""
    d = kr.bw(ra.p, f'upperarm01.{side}') - kr.bw(ra.p, f'upperarm01.{"L" if side == "R" else "R"}'); d.z = 0
    return d.normalized()


def _burger_B(self, kr, ra, at):
    """world frame of the burger (origin = bun bottom centre, z up through the bun, y away from the person, x to his right)"""
    p = ra.p; R = p.rig.matrix_world.to_3x3().normalized(); Up = V((0, 0, 1))
    xr = _side_out(kr, ra, 'R'); H, W = BURGER2['height'], BURGER2['width']
    if at == 'mouth':
        L = kr.wmat(p, 'head') @ self.lip_local; _, nr = kr.part_world(ra, 'mouth')
        yf = V((nr.x, nr.y, 0)).normalized(); xr = (xr - yf * xr.dot(yf)).normalized()
        # biting: the burger tips further (bite_tilt) so the crown's back edge goes between the teeth (a 6 cm stack in a
        # 32 mm gap) and the heel swings clear of the chin; upper teeth come down on the crown
        Rb = Matrix((xr, yf, xr.cross(yf))).transposed() @ Matrix.Rotation(math.radians(BURGER2['bite_tilt']), 3, 'X')
        E = V((0, -W / 2, H * BURGER2['bite_z'] - H / 2))        # back edge near the crown top (rel. the centre): upper teeth over the crown edge
        G = L - Up * 0.010 - yf * BURGER2['bite_in']             # open-mouth gap centre (lower lip drops at 'bite'), 12 mm in
        C = G - Rb @ E
    else:
        if not hasattr(self, '_chest_front'):      # chest skin depth in front of the collarbone (rig local, measured once)
            K = (kr.bw(p, 'clavicle.L') + kr.bw(p, 'clavicle.R')) / 2; Fp = R @ V((0, -1, 0)); w = _body_world(self)
            d = w - np.array(K); along = d @ np.array(Fp); perp = np.linalg.norm(d - np.outer(along, np.array(Fp)), axis=1)
            sel = (perp < 0.02) & (along > 0); self._chest_front = min(float(along[sel].max()), 0.075) if sel.any() else 0.06
            print(f'cast v1.1 burger {p.name}: chest skin {1000 * self._chest_front:.0f} mm in front of the collarbone')
        K = (kr.bw(p, 'clavicle.L') + kr.bw(p, 'clavicle.R')) / 2; Fp = R @ V((0, -1, 0)); Fp.z = 0; Fp.normalize()
        xr = (xr - Fp * xr.dot(Fp)).normalized()
        Rb = Matrix((xr, Fp, xr.cross(Fp))).transposed() @ Matrix.Rotation(math.radians(BURGER2['tilt']), 3, 'X')
        C = K + Fp * (self._chest_front + BURGER2['front'])
    return Matrix.Translation(C) @ Rb.to_4x4() @ Matrix.Translation(V((0, 0, -H / 2)))


def _burger_frame(self, kr, ra, side, zh, lean=None):
    """wrist-in-burger frame for a palm-skin height zh: palm on the bun side, fingers up over the crown (leaning in),
    index at the back (toward the person), thumb under the heel.  NB the kit grip normal self.pn n points out of the BACK
    of the HG hand (fingers flex toward -n), so n faces away from the bun and the palmar skin is measured on the mesh."""
    W = BURGER2['width']; sx = 1.0 if side == 'R' else -1.0; a = math.radians(BURGER2['lean'] if lean is None else lean)
    Rl = Matrix.Rotation(-sx * a, 3, 'Y'); n_t = Rl @ V((sx, 0, 0)); f_t = Rl @ V((0, 0, 1))     # lean: fingers tip in over the crown
    n_l, f_l = (V(v).normalized() for v in self.pn[side]); f_l = (f_l - n_l * f_l.dot(n_l)).normalized()
    T = Matrix((n_t, f_t, n_t.cross(f_t))).transposed(); Lm = Matrix((n_l, f_l, n_l.cross(f_l))).transposed()
    Rwb = T @ Lm.inverted()
    if not hasattr(self, '_palmar'): self._palmar = {}
    if side not in self._palmar:
        Mw = kr.wmat(ra.p, f'wrist.{side}'); w = _body_world(self); Mi = np.array(Mw.inverted()); lw = w @ Mi[:3, :3].T + Mi[:3, 3]
        RH = self.rig.matrix_world; Mwi = Mw.inverted()      # palm centre from the knuckles (self.palm L sits ~20 mm nearer the fingers than R)
        ka = Mwi @ (RH @ self.rig.pose.bones[f'f_index.01.{side}'].head); kb_ = Mwi @ (RH @ self.rig.pose.bones[f'f_pinky.01.{side}'].head)
        P0 = (ka + kb_) / 2 - f_l * 0.035; P0 = P0 + n_l * (V(self.palm[side]) - P0).dot(n_l)
        d_ = lw - np.array(P0); an = d_ @ np.array(n_l); af = d_ @ np.array(f_l)
        lat = np.linalg.norm(d_ - np.outer(an, n_l) - np.outer(af, f_l), axis=1)
        fing = np.zeros(len(lw), bool)
        for k_ in range(1, 6): fing[self.fids[(side, k_)]] = True
        vgi = {g.name: g.index for g in self.body.vertex_groups}; gi_ = {vgi.get(f'thumb.01.{side}'), vgi.get(f'thumb.02.{side}')} - {None}
        if gi_: fing[[v.index for v in self.body.data.vertices if any(g.group in gi_ and g.weight > 0.2 for g in v.groups)]] = True
        sel = (lat < 0.02) & (af > -0.015) & (af < 0.015) & (an < 0.01) & (an > -0.06) & ~fing
        dn = float(np.percentile(an[sel], 3)) if sel.sum() > 20 else -0.025
        self._palmar[side] = P0 + n_l * dn
        print(f'cast v1.1 burger hand {ra.p.name} {side}: palm centre (wrist local mm)', tuple(round(1000 * x) for x in self._palmar[side]),
              'old grip point', tuple(round(1000 * x) for x in self.palm[side]))
        gi = kr.bw(ra.p, f'finger2-1.{side}'); gp = kr.bw(ra.p, f'finger5-1.{side}'); g_l = (Mw.to_3x3().inverted() @ (gp - gi)).normalized()
        print(f'cast v1.1 burger hand {ra.p.name} {side}: palmar skin {1000 * dn:+.1f} mm along n ({int(sel.sum())} verts), '
              f'index->pinky along burger y {(Rwb @ g_l).y:+.2f} (want +1: index at the back)')
    P_t = V((sx * (W / 2 + SKIN), BURGER_HAND['y'], zh))
    return Matrix.Translation(P_t - Rwb @ self._palmar[side]) @ Rwb.to_4x4()


def _burger_meshes(kr):
    ob = kr.FX.props.get('g_burger'); it = getattr(kr.FX, 'grip_items', {}).get('g_burger')
    src = it.objs if it is not None and hasattr(it, 'objs') else ob.children_recursive
    return ob, [o for o in src if o.type == 'MESH' and o.display_type != 'WIRE' and any(t in o.name for t in ('hamburger_buns', 'kwp_patty'))]


def _burger_Pl(self, kr, ra, side):
    """burger frame in wrist local for this hand + the closed finger table, solved once (wrist relative) on the real
    kwprops burger: close_hand at the default palm height, then the hand slides down/up so the middle fingertip lands
    BURGER_TIP_IN in from the crown edge, and the fingers close again"""
    key = (side, 'g_burger2')
    if key in self.Pl: return self.Pl[key]
    self.__dict__.setdefault('_bclose', {}); p = ra.p; W = BURGER2['width']
    cf_ = os.environ.get('KW_BCLOSE_CACHE'); cc_ = None
    if cf_ and os.path.exists(cf_):
        import json; cc_ = json.load(open(cf_)).get(f'{p.name}:{side}')
    if cc_:
        self._bclose[side] = {int(k): (tuple(v[0]), v[1]) for k, v in cc_['tab'].items()}
        self.Pl[key] = _burger_frame(self, kr, ra, side, cc_['z'], cc_.get('lean')).inverted(); return self.Pl[key]
    ob, meshes = _burger_meshes(kr); zh = BURGER_HAND['z']; ln = BURGER2['lean']; t0 = time.time(); Mw = kr.wmat(p, f'wrist.{side}')
    keep = [(pb, pb.rotation_euler.copy()) for k in range(1, 6) for pb in (p.pb(f'finger{k}-{jj}.{side}') for jj in (1, 2, 3))]
    mw0 = ob.matrix_world.copy()
    for it_ in range(3):
        Pl = _burger_frame(self, kr, ra, side, zh, ln).inverted(); ob.matrix_world = Mw @ Pl; bpy.context.view_layer.update()
        Bi = ob.matrix_world.inverted()
        sc = lambda tw: (lambda q: q.z + 0.3 * abs(q.x))(Bi @ tw)      # thumb: tip under the heel, toward the middle
        tab, rep = close_hand(self, kr, side, meshes, score=sc)
        w_ = _body_world(self); tq = {k: Bi @ V(w_[self.fids[(side, k)]].mean(0)) for k in range(1, 6)}
        rin = W / 2 - math.hypot(tq[3].x, tq[3].y)          # middle tip: distance in from the crown edge
        print(f'cast v1.1 close_hand {p.name} {side} burger pass {it_}: palm z {1000 * zh:.0f} mm lean {ln:.0f} deg, middle tip {1000 * rin:.0f} mm in from the edge,',
              tab, rep, 'tips burger-local mm', {k: tuple(round(1000 * x) for x in q) for k, q in tq.items()})
        if abs(rin - BURGER_TIP_IN) < 0.006 or it_ == 2: break
        ln = max(-15.0, min(25.0, ln - math.degrees((rin - BURGER_TIP_IN) / 0.085)))   # reaching too far over the top -> fingers lean out
    for pb, e in keep: pb.rotation_euler = e
    ob.matrix_world = mw0; self._bclose[side] = tab; self.Pl[key] = Pl
    print(f'cast v1.1 burger hand {p.name} {side} solved in {time.time() - t0:.0f}s')
    if cf_:
        import json; d_ = json.load(open(cf_)) if os.path.exists(cf_) else {}
        d_[f'{p.name}:{side}'] = {'z': zh, 'lean': ln, 'tab': {str(k): [list(a), z] for k, (a, z) in tab.items()}}; json.dump(d_, open(cf_, 'w'))
    return Pl


def _burger_yaw(side, at):
    """biting: both hands slide round the bun toward its front (bite_yaw, about the bun axis, so the contacts hold) and the
    index finger leaves the lips"""
    if at != 'mouth': return Matrix.Identity(4)
    yw = float(os.environ.get('KW_BITE_YAW', BURGER2['bite_yaw']))
    return Matrix.Rotation(math.radians(yw) * (1 if side == 'R' else -1), 4, 'Z')


def _burger_goal(self, kr, ra, side, h, tip, shape):
    tl = ra.hand[side][shape][tip]; B = _burger_B(self, kr, ra, h.at); Wd = B @ _burger_yaw(side, h.at) @ _burger_Pl(self, kr, ra, side).inverted()
    R = ra.p.rig.matrix_world.to_3x3().normalized(); Up = R @ V((0, 0, 1)); sh = kr.bw(ra.p, f'upperarm01.{side}')
    out = _side_out(kr, ra, side); Fp = R @ V((0, -1, 0))
    pole = sh + out * 0.35 - Up * 0.6 - Fp * 0.1          # elbows down, ~30 deg out
    return Wd @ tl, tip, shape, Wd.to_3x3(), pole


def _burger_hold(self, kr, jobs):
    """frame hook: the closed finger tables on both hands, the burger on the first hand's wrist"""
    js = [j for j in jobs if j[8] is not None and j[8].kind == 'hold' and j[8].prop == 'g_burger']
    if not js or kr.FX.props.get('g_burger') is None: return False
    p = self.p; ob = kr.FX.props['g_burger']
    for j in js:
        side = j[1]; _burger_Pl(self, kr, self.ra, side)
        for k, (a, z) in self._bclose[side].items():
            for jj in (1, 2, 3):
                e = p.pb(f'finger{k}-{jj}.{side}').rotation_euler
                e.x = math.radians(a[jj - 1]); e.y = 0.0; e.z = math.radians(z if jj == 1 else 0.0) * (1 if side == 'R' else -1)
    side0 = js[0][1]; ob.matrix_world = kr.wmat(p, f'wrist.{side0}') @ _burger_Pl(self, kr, self.ra, side0) @ _burger_yaw(side0, js[0][8].at).inverted()
    if os.environ.get('KW_V11_DBG'):
        bpy.context.view_layer.update(); Bt = _burger_B(self, kr, self.ra, js[0][8].at)
        for j in js:
            Wd = Bt @ _burger_yaw(j[1], j[8].at) @ _burger_Pl(self, kr, self.ra, j[1]).inverted(); Wa = kr.wmat(p, f'wrist.{j[1]}')
            print('V11DBG burger', j[1], 'wrist pos err mm', round(1000 * (Wa.translation - Wd.translation).length, 1),
                  'rot err deg', round(math.degrees(Wa.to_quaternion().rotation_difference(Wd.to_quaternion()).angle), 1))
    return True


Graft.close_hand = close_hand


def _bloat_value(self):
    b = self.body.data.shape_keys.key_blocks.get('kw_bloat')
    return b.value if b is not None else 0.0


Graft.goal = _goal
Graft.bloat_value = _bloat_value


def _apply_contacts(self, kr, shot):
    """frame hook part 1: finger curls + HG prop placement (after kwfx placed the props on the kit hand)."""
    md_ = getattr(self, '_mound', None)
    if md_ is not None:      # the food mound follows its spoon out of the shot (it floated by the arm in hos_belly)
        h_ = md_.parent is None or md_.parent.hide_render; md_.hide_render = h_; md_.hide_viewport = h_
    if not hasattr(self, 'curl'): return
    if getattr(self, '_bdbg', None) is not None and os.environ.get('KW_HG_AUDIT'):
        sd, T, D0, Wt = self._bdbg; Mw = kr.wmat(self.p, f'wrist.{sd}')
        print('AUDIT bellydbg palm-target mm', round(1000 * ((Mw @ self.palm[sd]) - T).length, 1), 'D-vs-Wtl', round(1000 * (D0 - Wt).length, 1),
              'palm normal world', tuple(round(c, 2) for c in (Mw.to_3x3() @ self.pn[sd][0]).normalized()), 'fingers', tuple(round(c, 2) for c in (Mw.to_3x3() @ self.pn[sd][1]).normalized())); self._bdbg = None
    ra = self.ra; p = self.p
    jobs = [j for j in getattr(kr, '_hand_jobs', []) if j[0] is ra and ra.a in shot.cast and j[8] is not None]
    moved = False
    for j in jobs:
        side, shape, shapes, h = j[1], j[4], j[7], j[8]
        key = None
        if h.kind == 'hold' and h.prop in GRIP: key = h.prop
        elif h.kind == 'clipboard': key = 'board'
        elif h.kind == 'touch' and h.part == 'belly' and shape == 'claw': key = 'plane'
        if key is None or len(shapes) != 1 or (side, key) not in self.curl: continue
        for k, cv in self.curl[(side, key)].items():
            c1, c2 = cv[0], cv[1]; c3 = cv[2] if len(cv) in (4, 5) else None; c4 = cv[3] if len(cv) == 5 else c3
            for jj in (1, 2, 3):
                e = p.pb(f'finger{k}-{jj}.{side}').rotation_euler
                if k == 1 and c3 is not None: e.x += math.radians(c1 if jj == 1 else c3 if jj == 2 else c4); e.z += math.radians(c2 if jj == 1 else 0.0); continue
                if k > 1 and c3 is not None:
                    ax_ = getattr(self, 'canax', {}).get(side, {}).get((k, jj - 1)) if key == 'can' else getattr(self, 'penax', {}).get(side, {}).get((k, jj - 1)) if key == 'spoon' else None
                    ad_ = getattr(self, 'canax', {}).get(side, {}).get((k, -2)) if (key == 'can' and jj == 1) else None
                    if ax_ is not None:
                        R_ = e.to_matrix() @ Matrix.Rotation(math.radians((c1, c2, c3)[jj - 1]), 3, V(ax_))
                        if ad_ is not None and V(ad_).length > 1e-6: R_ = R_ @ Matrix.Rotation(math.radians(V(ad_).length), 3, V(ad_).normalized())
                        p.pb(f'finger{k}-{jj}.{side}').rotation_euler = R_.to_euler(e.order, e)
                    else: e.x += math.radians((c1, c2, c3)[jj - 1])
                    continue
                if k == 1: e.x += math.radians(c1); e.z += math.radians(c2 if jj == 1 else 0.0)
                else:
                    e.x += math.radians(c1 if jj == 1 else c2)
                    if key == 'plane' and jj == 1: e.z += math.radians(getattr(self, 'spread', {}).get(side, {}).get(k, 0.0))     # fingers together on the belly
        moved = True
        if key in GRIP:
            ob = kr.FX.props.get(h.prop)
            if ob is not None: self._prop_job = (ob, side, key)
    if moved: bpy.context.view_layer.update()
    for j in jobs:
        side, h = j[1], j[8]
        if h.kind == 'hold' and h.prop in GRIP:
            ob = kr.FX.props.get(h.prop)
            if ob is None: continue
            rel = getattr(self, '_canrel', {}).get(side) if h.prop == 'can' else None
            ob.matrix_world = kr.wmat(p, f'wrist.{side}') @ (rel if rel is not None else self.Pl[(side, h.prop)])
            if h.prop.startswith('g_'): ob.matrix_world = ob.matrix_world @ ITEM_OFF_P.get((p.name, h.prop), ITEM_OFF.get(h.prop, Matrix.Identity(4)))
            if h.prop.startswith('g_') and os.environ.get('KW_V11_DBG'): print('V11DBG place', h.prop, side, tuple(round(x, 3) for x in ob.matrix_world.translation), 'wrist', tuple(round(x, 3) for x in kr.wmat(p, f'wrist.{side}').translation))
            if h.prop == 'spoon':
                if getattr(self, '_mound', None) is None: self._mound = _build_spoon(ob)
                st_ = getattr(self, '_bite', None); hid = not (st_ is None or st_['mound'])     # food gone from the start of the pull-out
                hid = hid or bool(getattr(h, 'pad', None))       # cast v1.1 grip_tool: no food on a carried tool
                self._mound.hide_render = hid; self._mound.hide_viewport = hid
    if V11: self.v11_authored(kr, jobs)
    self.forearm_twist({j[1] for j in jobs})


FTW_K = 0.65     # share of the hand's twist (about the forearm axis) carried by the forearm: real pronation turns the radius, not the wrist (G6)


def _forearm_twist(self, sides='LR'):
    """No twist bones in the HG arm: without this the whole hand roll sits in the wrist joint (candy-wrapper crease).
    Rotates the HG forearm about its own axis by FTW_K of the hand twist; elbow and wrist positions do not move."""
    rig = self.rig; self._ftw = getattr(self, '_ftw', {}); self._fb0 = getattr(self, '_fb0', {})
    for sd in 'LR':
        fb = rig.pose.bones.get(f'forearm.{sd}'); hb = rig.pose.bones.get(f'hand.{sd}')
        if fb is None or hb is None: continue
        if sd not in self._fb0: fb.rotation_mode = 'QUATERNION'; self._fb0[sd] = fb.rotation_quaternion.copy()
        if sd not in sides:
            if self._ftw.get(sd, 0.0): self._ftw[sd] = 0.0; fb.rotation_quaternion = self._fb0[sd]; bpy.context.view_layer.update()
            continue
        rr = (rig.data.bones[f'forearm.{sd}'].matrix_local.inverted() @ rig.data.bones[f'hand.{sd}'].matrix_local)
        for _ in range(2):
            rel = rr.inverted() @ (fb.matrix.inverted() @ hb.matrix)
            tw = rel.to_euler('XZY').y; cur = self._ftw.get(sd, 0.0); new = FTW_K * (tw + cur)
            if abs(new - cur) < 1e-3: break
            self._ftw[sd] = new; fb.rotation_quaternion = self._fb0[sd] @ Quaternion((0, 1, 0), new)
            bpy.context.view_layer.update()


Graft.apply_contacts = _apply_contacts
Graft.v11_authored = _v11_authored
Graft._v11_author = _v11_author
Graft.forearm_twist = _forearm_twist


# ---------------------------------------------------------------- SPOON (direction S1-S9, addendum I R3/R4, part A R6, ruling D d/e)
# spoon local frame: z = handle -> bowl, y = bowl up (the thumb side), origin = the pinch point under the thumb pad
SP_END, SP_NECK, SP_TIP = -0.050, 0.075, 0.135          # handle end, neck, bowl tip (m): 18.5 cm long (S1 17-19)
SP_BOWL_W, SP_BOWL_D = 0.040, 0.008                     # bowl width 4 cm x length 6 cm (neck -> tip), depth 8 mm
SP_HX, SP_HY = 0.0055, 0.0010                           # handle half width / half thickness at the grip (11 x 2 mm)


def _spoon_hw(z):
    """half width of the spoon outline at z (handle widens to the end, slim neck, oval bowl)"""
    if z <= SP_NECK:
        k = (z - SP_END) / (SP_NECK - SP_END)
        return 0.0068 * (1 - k) + 0.0032 * k
    zc = (SP_NECK + SP_TIP) / 2; a = (SP_TIP - SP_NECK) / 2; e = max(0.0, 1 - ((z - zc) / a) ** 2)
    return max(0.0032 * (1 - min(1, (z - SP_NECK) / 0.012)), SP_BOWL_W / 2 * math.sqrt(e))


def _build_spoon(ob):
    """S1 / ruling e: replace the kit stick with an 18.5 cm stainless spoon (4 x 6 cm bowl) + the food mound (child)"""
    nz, nx = 64, 12; vs = []; fs = []
    zc = (SP_NECK + SP_TIP) / 2; a = (SP_TIP - SP_NECK) / 2
    for i in range(nz + 1):
        z = SP_END + (SP_TIP - SP_END) * i / nz; hw = max(_spoon_hw(z), 0.0004)
        for j in range(nx + 1):
            x = -hw + 2 * hw * j / nx; y = 0.0
            if z > SP_NECK:
                r2 = (x / (SP_BOWL_W / 2)) ** 2 + ((z - zc) / a) ** 2
                y = -SP_BOWL_D * max(0.0, 1 - r2) ** 0.8
            else:
                y = 0.0012 * ((z - SP_END) / (SP_NECK - SP_END) - 1) ** 2      # handle end bends up a little
            vs.append((x, y, z))
    for i in range(nz):
        for j in range(nx): fs.append((i * (nx + 1) + j, i * (nx + 1) + j + 1, (i + 1) * (nx + 1) + j + 1, (i + 1) * (nx + 1) + j))
    me = bpy.data.meshes.new('kw_spoon_hg'); me.from_pydata(vs, [], fs); me.update()
    for pl in me.polygons: pl.use_smooth = True
    old = ob.data; ob.data = me
    for m in list(ob.modifiers): ob.modifiers.remove(m)
    so = ob.modifiers.new('kw_thick', 'SOLIDIFY'); so.thickness = 2 * SP_HY; so.offset = 0.0
    ob.modifiers.new('kw_smooth', 'SUBSURF').levels = 1
    mat = bpy.data.materials.new('kw_spoon_steel'); mat.use_nodes = True
    bs = mat.node_tree.nodes.get('Principled BSDF')
    if bs is not None:
        bs.inputs['Base Color'].default_value = (0.46, 0.46, 0.47, 1); bs.inputs['Metallic'].default_value = 1.0
        bs.inputs['Roughness'].default_value = 0.24          # brushed steel: grey, not a blue mirror of the backdrop
    me.materials.append(mat)
    if old is not None and old.users == 0: bpy.data.meshes.remove(old)
    # food mound: pale yellow, ~2 cm, in the bowl (hidden from 55 % of each bite, S4 / ruling d)
    import bmesh
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=20, v_segments=10, radius=1.0)
    m2 = bpy.data.meshes.new('kw_spoon_mound'); bm.to_mesh(m2); bm.free()
    md = bpy.data.objects.new('kw_spoon_mound', m2)
    for c in ob.users_collection: c.objects.link(md)
    md.parent = ob; md.matrix_parent_inverse = Matrix.Identity(4)
    md.location = (0.0, -0.002, zc + 0.002); md.scale = (0.0105, 0.0075, 0.0130)    # top ~5 mm above the rim, base sunk in the bowl
    mm = bpy.data.materials.new('kw_mound'); mm.use_nodes = True; b2 = mm.node_tree.nodes.get('Principled BSDF')
    if b2 is not None: b2.inputs['Base Color'].default_value = (0.93, 0.80, 0.42, 1); b2.inputs['Roughness'].default_value = 0.7
    md.data.materials.append(mm)
    for pl in md.data.polygons: pl.use_smooth = True
    return md


def _box_sd(q):
    """signed distance (m) of handle-local points q (N x 3) to the handle box (grip region, end -> neck)"""
    c = np.array([0.0, 0.0, (SP_END + SP_NECK) / 2]); hx = np.array([SP_HX, SP_HY, (SP_NECK - SP_END) / 2])
    d = np.abs(q - c) - hx
    return np.linalg.norm(np.maximum(d, 0), axis=1) + np.minimum(d.max(axis=1), 0)


def _solve_pen(self, kr, s):
    """S2 pen (tripod) grip on the real HG skin: handle in the thumb-index web, resting on the side of the middle
    finger's tip segment, thumb pad on top, index pad along it, ring + little curled loosely underneath (not gripping).
    Every finger flexes about ONE hinge (bone x palm normal at the rest pose), all joints scaled from a template.
    Simplex search over 10 values (handle frame 4, thumb flex + opposition, index base / tip closure, middle, ring + little).
    Returns the curl dict for _apply_contacts and sets Pl[(s, 'spoon')] (spoon frame in wrist space), penax[s]."""
    p = self.p; rig = p.rig; RW = rig.matrix_world; Mw = kr.wmat(p, f'wrist.{s}'); Mwi = Mw.inverted()
    self.penax = getattr(self, 'penax', {})
    cache = os.environ.get('KW_SPOONCACHE')
    if cache and os.path.exists(cache):
        import json as _j; cc = _j.load(open(cache))
        self.Pl[(s, 'spoon')] = Matrix(cc['Pl']); self.penax[s] = {tuple(int(x) for x in kk.split(',')): tuple(v) for kk, v in cc['ax'].items()}
        print('humgen pen grip from cache', cache); return {int(k): tuple(v) for k, v in cc['out'].items()}
    vgi = {g.name: g.index for g in self.body.vertex_groups}
    def ids(names, wmin=0.5):
        gi = {vgi[n] for n in names if n in vgi}
        return np.array([v.index for v in self.body.data.vertices if any(g.group in gi and g.weight > wmin for g in v.groups)], int)
    FN = {1: 'thumb', 2: 'f_index', 3: 'f_middle', 4: 'f_ring', 5: 'f_pinky'}
    SEGI = {(k, j): ids([f'{FN[k]}.0{j}.{s}']) for k in FN for j in (1, 2, 3)}
    PALMI = ids([f'hand.{s}'] + [f'palm.0{i}.{s}' for i in range(1, 5)], 0.6)
    WEBI = ids([f'thumb.01.{s}', f'palm.01.{s}'], 0.4)
    HANDI = np.unique(np.concatenate([v for v in SEGI.values() if len(v)] + [PALMI]))
    pbs = {k: [rig.pose.bones[f'finger{k}-{j}.{s}'] for j in (1, 2, 3)] for k in FN}
    base = {k: [pb.rotation_euler.copy() for pb in v] for k, v in pbs.items()}
    n2, f2 = self.pn[s]; RH = self.rig.matrix_world
    n_arm = (RW.to_3x3().inverted() @ (Mw.to_3x3() @ n2)).normalized(); AX = {}
    for k in range(2, 6):
        y0 = (pbs[k][0].matrix.to_3x3().normalized() @ V((0, 1, 0))).normalized()
        hk = n_arm.cross(y0).normalized()               # pn[0] is the BACK-of-hand normal: +angle curls the finger toward the palm (kit +x)
        for j, pb in enumerate(pbs[k]): AX[(k, j)] = tuple((pb.matrix.to_3x3().normalized().inverted() @ hk).normalized())
    self.penax[s] = AX
    TPL = {2: (40.0, 45.0, 20.0), 3: (50.0, 60.0, 30.0), 4: (60.0, 75.0, 40.0), 5: (65.0, 80.0, 40.0)}
    hb = lambda nm: Mwi @ (RH @ self.rig.pose.bones[nm].head)
    gk = (hb(f'f_pinky.01.{s}') - hb(f'f_index.01.{s}')).normalized(); g2 = (gk - f2 * gk.dot(f2) - n2 * gk.dot(n2)).normalized()
    web0 = (hb(f'thumb.02.{s}') + hb(f'f_index.01.{s}')) / 2
    def angs(X):
        on, of, an, ag, t1, tz, s2, s3, s2b, s45 = X
        A = {1: (t1, tz, 0.8 * t1, 0.6 * t1), 2: (s2 * TPL[2][0], s2b * TPL[2][1], s2b * TPL[2][2]), 3: tuple(s3 * a for a in TPL[3]),
             4: tuple(s45 * a for a in TPL[4]), 5: tuple(s45 * a for a in TPL[5])}
        return A
    def setang(A):
        for k, ang in A.items():
            for j, pb in enumerate(pbs[k]):
                e = base[k][j].copy()
                if k == 1: e.x += math.radians(ang[0] if j == 0 else ang[2] if j == 1 else ang[3]); e.z += math.radians(ang[1] if j == 0 else 0.0)
                else: e = (e.to_matrix() @ Matrix.Rotation(math.radians(ang[j]), 3, V(AX[(k, j)]))).to_euler(e.order, e)
                pb.rotation_euler = e
    def frame(X, wl):
        on, of, an, ag = X[:4]
        Wb = web0 + n2 * on + f2 * of
        d = (f2 * math.cos(math.radians(an)) * math.cos(math.radians(ag)) + n2 * math.sin(math.radians(an)) - g2 * math.sin(math.radians(ag)) * math.cos(math.radians(an))).normalized()
        tc = V(wl[SEGI[(1, 3)]].mean(0)); O = Wb + d * (tc - Wb).dot(d)
        yv = (tc - O); yv = (yv - d * yv.dot(d)); yv = yv.normalized() if yv.length > 1e-6 else n2
        xv = yv.cross(d).normalized()
        M = Matrix((xv, yv, d)).transposed().to_4x4(); M.translation = O
        return M
    band = lambda g, lo, hi: 0.0 if lo <= g <= hi else (lo - g) * 20.0 if g < lo else (g - hi) * 3.0
    LO = np.array([-0.03, -0.04, -10.0, -40.0, -20.0, -70.0, 0.0, 0.0, -0.3, 0.75]); HI = np.array([0.03, 0.04, 80.0, 60.0, 80.0, 30.0, 1.6, 1.6, 1.6, 0.9])     # ring + little curled loosely (S2), not a fist
    def ev(X, full=False):
        X = np.clip(X, LO, HI); setang(angs(X)); w = _body_world(self)
        wl = w @ np.array(Mwi)[:3, :3].T + np.array(Mwi)[:3, 3]; M = frame(X, wl); Mi = np.array(M.inverted())
        q = wl @ Mi[:3, :3].T + Mi[:3, 3]
        sd = {kj: _box_sd(q[v]) for kj, v in SEGI.items() if len(v)}
        g = {kj: float(v.min()) for kj, v in sd.items()}
        c = band(g[(1, 3)], 0.0005, 0.002) + 2 * band(g[(2, 3)], 0.0005, 0.002) + band(g[(3, 3)], 0.0005, 0.002)
        sdh = _box_sd(q[HANDI]); pen = float(np.maximum(-sdh, 0).max()); c += 40 * max(0.0, pen - 0.0005)     # <= 0.5 mm skin compression allowed
        ym = q[SEGI[(3, 3)]][int(np.argmin(sd[(3, 3)]))][1]; c += 0.0 if ym < 0 else ym * 5           # middle finger UNDER the handle
        for k in (4, 5): c += band(min(g[(k, 2)], g[(k, 3)]), 0.003, 1.0) * 0.5                          # ring / little loose: never on the handle
        wd = float(_box_sd(q[WEBI]).min()); c += band(wd, 0.0, 0.006) * 0.5                             # upper end in the web
        zt = float(q[SEGI[(1, 3)]][:, 2].mean()); c += 0.0 if -0.01 <= zt <= 0.03 else 0.2 * min(abs(zt + 0.01), abs(zt - 0.03))
        ry = math.degrees(M.col[1].xyz.angle(-n2)); c += band(ry, 10.0, 35.0) * 0.002     # R6 palm-up 55-80 with the bowl level (-n2 = palmar)
        if full: return c, g, pen, M, ym, wd, X, ry
        return c
    # simplex (Nelder-Mead) from a tripod start
    x0 = np.array([-0.001, 0.011, 23.1, 34.8, -12.6, 6.6, 0.61, 0.92, 1.17, 0.85]); stp = np.array([0.01, 0.012, 20.0, 20.0, 25.0, 25.0, 0.4, 0.4, 0.5, 0.3])
    best = None
    for rs in range(2):
        P = [x0] + [x0 + np.eye(10)[i] * stp[i] for i in range(10)]; Fv = [ev(x) for x in P]; nev = 11
        for it in range(320 if rs == 0 else 200):
            o = np.argsort(Fv); P = [P[i] for i in o]; Fv = [Fv[i] for i in o]
            if Fv[-1] - Fv[0] < 1e-6: break
            cen = np.mean(P[:-1], 0); xr = cen + (cen - P[-1]); fr = ev(xr); nev += 1
            if fr < Fv[0]:
                xe = cen + 2 * (cen - P[-1]); fe = ev(xe); nev += 1
                P[-1], Fv[-1] = (xe, fe) if fe < fr else (xr, fr)
            elif fr < Fv[-2]: P[-1], Fv[-1] = xr, fr
            else:
                xc = cen + 0.5 * (P[-1] - cen); fc = ev(xc); nev += 1
                if fc < Fv[-1]: P[-1], Fv[-1] = xc, fc
                else:
                    P = [P[0]] + [P[0] + 0.5 * (x - P[0]) for x in P[1:]]; Fv = [Fv[0]] + [ev(x) for x in P[1:]]; nev += 10
        i = int(np.argmin(Fv)); x0 = np.clip(P[i], LO, HI); stp = stp * 0.4
        print(f'humgen pen simplex pass {rs}: cost {Fv[i]:.4f} evals {nev}')
    c, g, pen, M, ym, wd, X, ry = ev(x0, True); A = angs(X)
    setang({k: [0.0] * len(v) for k, v in A.items()})
    self.Pl[(s, 'spoon')] = M
    out = {1: tuple(round(x, 1) for x in A[1]) + (round(1000 * g[(1, 3)], 1),)}
    for k in range(2, 6): out[k] = tuple(round(x, 1) for x in A[k]) + (round(1000 * g[(k, 3)], 1),)
    print(f'humgen pen grip {p.name} {s}: cost {c:.4f} X {[round(float(x), 3) for x in X]} gaps mm',
          {f'{FN[k][-5:]}{j}': round(1000 * v, 1) for (k, j), v in g.items()}, f'pen {1000 * pen:.1f} mm, middle y {1000 * ym:.1f}, web {1000 * wd:.1f}, bowl-up vs palm {ry:.0f} deg', out)
    if cache:
        import json as _j; _j.dump(dict(Pl=[list(r) for r in M], out=out, ax={f'{a},{b}': list(v) for (a, b), v in AX.items()}), open(cache, 'w'))
    return out


Graft._solve_pen = _solve_pen


JAW_DEG = 28.0          # deg of jaw opening per unit ARKit jawOpen (measured on the HG head, see the cast sheet N-numbers)
SP_JAW, SP_CHEW = 12.0, 4.0     # deg: jaw open for the spoon (S4 10-15), one chew (S5 3-5)
SP_LIPS = (0.10, 0.30)          # (jawOpen, mouthClose) while the lips close on the spoon / chew: lips shut, jaw a little open
SP_IN0, SP_IN1 = -0.015, 0.025  # bowl tip vs the lips along the spoon (m): waiting just outside -> 2.5 cm inside (S4 2-3)
SP_YAW, SP_PITCH, SP_PITCH_M = 30.0, 6.0, 35.0   # deg: spoon comes in from the hand side; handle below the bowl: on the lift (bowl level within 10) / at the lips
# (elbow flexion 121 deg at the lips [D3] needs the hand beside the chin, not in front of the mouth)
SP_LOW = (0.37, 0.22, 0.06)     # low point of the bowl tip vs the mouth: down, forward, out to the hand side (m; S4 35-40 cm; shot 15 drop 0.16)
SP_MZ = 0.115                   # mouth height above the kit neck base (rest) - the low point does not follow the head nod
SP_ARC = 0.05                   # m: gentle forward arc of the lift
SP_AB = (14.0, 45.0)            # deg upper-arm abduction at the low point / at the mouth (R6: < 20, 35-55)


def _bite_state(self, kr, ra, u, acts=None):
    """S4-S6 / R3: per frame state of the spoon bites from the eat act's frame beats.
    p: path (0 low point -> 1 at the lips), ins: bowl insertion (0 outside -> 1 inside), mound: food on the bowl,
    jaw / lips: ARKit weights, lean: head + trunk toward the spoon (0..1)"""
    if acts is None: acts = [ac for x in kr._cur if x[0] is ra for q in (x[1], x[2]) for ac in q.acts]
    acts = [ac for ac in acts if ac.kind == 'eat' and ac.kw.get('beats')]
    st = dict(p=0.0, ins=0.0, mound=False, jaw=0.0, lips=0.0, lean=0.0, phase='low', drop=SP_LOW[0], gaze=0.0)
    if not acts: return st
    ac = acts[0]; st['drop'] = ac.kw.get('drop', SP_LOW[0]); Lf, If, Of, Df = ac.kw['beats']; n = int(ac.kw.get('bites', 1)); per = (Lf + If + Of + Df) / KW.FPS
    sm = lambda x: 0.0 if x <= 0 else 1.0 if x >= 1 else x * x * (3 - 2 * x)
    jaw_u = SP_JAW / JAW_DEG
    for i in range(n):
        c = ac.at + i * per; x = (u - c) * KW.FPS            # frames since this bite started
        if x < 0: continue
        if x < Lf:
            st.update(p=sm(x / Lf), ins=0.0, mound=True, phase='lift'); st['jaw'] = jaw_u * sm((x - 0.6 * Lf) / (0.4 * Lf))
            st['lean'] = sm((x - 0.4 * Lf) / (0.6 * Lf))
        elif x < Lf + If:
            k = (x - Lf) / If; st.update(p=1.0, ins=sm(k), mound=True, phase='in', lean=1.0)
            st['jaw'] = jaw_u * (1 - sm((k - 0.5) / 0.5)) + SP_LIPS[0] * sm((k - 0.5) / 0.5); st['lips'] = SP_LIPS[1] * sm((k - 0.5) / 0.5)
        elif x < Lf + If + Of:
            k = (x - Lf - If) / Of; st.update(p=1.0, ins=1 - sm(k), mound=False, phase='out', lean=1.0, jaw=SP_LIPS[0], lips=SP_LIPS[1])
        elif x < Lf + If + Of + Df or i == n - 1:
            k = min(1.0, (x - Lf - If - Of) / Df); st.update(p=1 - sm(k), ins=0.0, mound=False, phase='down', lean=1 - sm(k))
            st['lips'] = SP_LIPS[1] * (1 - sm(k / 0.5)); st['jaw'] = SP_LIPS[0] * (1 - sm(k / 0.5))
        ph_, xx = st['phase'], x       # F4: eyes reach the spoon 5 frames into the lift, leave it while it comes out
        st['gaze'] = (sm(xx / 5.0) if ph_ == 'lift' else 1.0 if ph_ == 'in' else (1 - sm((xx - Lf - If) / Of)) if ph_ == 'out' else 0.0)
        ch = ac.kw.get('chew')
        if ch and i == n - 1 and ch[0] <= (u - ac.at) * KW.FPS <= ch[1]:
            kk = ((u - ac.at) * KW.FPS - ch[0]) / max(1, ch[1] - ch[0])
            st['jaw'] = max(st['jaw'], (SP_CHEW / JAW_DEG) * math.sin(math.pi * kk)); st['lips'] = max(st['lips'], SP_LIPS[1])
    if ac.kw.get('gaze') == 'hold': st['gaze'] = 1.0      # F4 shot 15: eyes down on the spoon the whole shot
    return st


def _spoon_frame(self, kr, ra, side, st):
    """world frame of the spoon (z handle -> bowl, y bowl up) for a bite state"""
    p = ra.p; R = p.rig.matrix_world.to_3x3().normalized(); Z = V((0, 0, 1))
    sg = 1.0 if side == 'L' else -1.0; out = R @ V((sg, 0, 0)); Fp = R @ V((0, -1, 0))
    mpt, nr = kr.part_world(ra, 'mouth'); nh = V((nr.x, nr.y, 0)).normalized()
    oh = out - nh * out.dot(nh); oh.z = 0; oh.normalize()
    # at the lips: the spoon points into the mouth, coming from the hand side, bowl level
    pp = st['p']; k_ = max(0.0, min(1.0, (pp - 0.3) / 0.7)) if st['phase'] != 'down' else pp; k_ = k_ * k_ * (3 - 2 * k_)   # down: the bowl is empty, so the pitch unwinds over the whole path (no wrist flick, tip speed)
    yw = math.radians(SP_YAW); pt_ = math.radians(SP_PITCH + (SP_PITCH_M - SP_PITCH) * k_)     # bowl level on the lift, handle lower at the lips
    a_m = (-(nh * math.cos(yw) + oh * math.sin(yw)) * math.cos(pt_) + Z * math.sin(pt_)).normalized()
    tip = mpt + a_m * (SP_IN0 + (SP_IN1 - SP_IN0) * st['ins'])
    O_m = tip - a_m * SP_TIP
    # low point: hand just above the thighs, bowl level, spoon pointing forward-in (as if over a bowl in the lap)
    # anchored on the neck base (moves with the trunk, NOT with the head nod), short drops keep more of the mouth angle
    fh = V((Fp.x, Fp.y, 0)).normalized(); a_l = (fh * math.sin(math.radians(35)) - oh * math.cos(math.radians(35))).normalized()     # pointing across the lap
    dr = st['drop']; a_l = a_l.slerp(a_m, min(1.0, max(0.0, 1 - dr / SP_LOW[0]) * 1.4)).normalized()     # short drop (shot 15): less turn of the spoon
    nb = kr.bw(p, 'neck01')
    tip_l = V((mpt.x, mpt.y, nb.z + SP_MZ)) - Z * dr + fh * (SP_LOW[1] * dr / SP_LOW[0]) + oh * SP_LOW[2]
    O_l = tip_l - a_l * SP_TIP
    O = O_l.lerp(O_m, pp) + fh * (SP_ARC * math.sin(math.pi * pp))
    a = a_l.slerp(a_m, pp) if hasattr(a_l, 'slerp') else (a_l * (1 - pp) + a_m * pp).normalized()
    a = a.normalized(); y = (Z - a * Z.dot(a)).normalized(); x = y.cross(a).normalized()
    M = Matrix((x, y, a)).transposed().to_4x4(); M.translation = O
    return M


def _spoon_goal(self, kr, ra, side, tip, shape, u, pole):
    st = self.bite_state(kr, ra, u); self._bite = st
    Ms = self.spoon_frame(kr, ra, side, st)
    Wm = Ms @ self.Pl[(side, 'spoon')].inverted(); Rw = Wm.to_3x3().normalized()
    tl = ra.hand[side][shape][tip]
    p = ra.p; R = p.rig.matrix_world.to_3x3().normalized(); sg = 1.0 if side == 'L' else -1.0
    out = R @ V((sg, 0, 0)); Up = R @ V((0, 0, 1)); Fp = R @ V((0, -1, 0)); sh = kr.bw(p, f'upperarm01.{side}')
    pl = sh - Up * 0.6 + Fp * 0.05 + out * (0.10 + 0.35 * st['p'])
    self._sp_ab = SP_AB[0] + (SP_AB[1] - SP_AB[0]) * st['p']
    return Wm @ tl, tip, shape, Rw, pl


Graft.bite_state = _bite_state
Graft.spoon_frame = _spoon_frame
Graft.spoon_goal = _spoon_goal
