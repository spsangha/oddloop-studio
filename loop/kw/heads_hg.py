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
import os
import numpy as np
import bpy, math
import kwkit as KW
from mathutils import Vector as V, Matrix
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
}
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
        for kb in self.keys:
            for k in ARK_NAMES:
                b = kb.get(k)
                if b is not None:
                    nv = min(1.0, want.get(k, 0.0))
                    if abs(b.value - nv) > 1e-4: b.value = nv

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
        ax = P - T; Lp = max(ax.length, 0.005); z = ax.normalized(); x = z.orthogonal().normalized(); y = z.cross(x)
        Mp = Matrix((x, y, z)).transposed().to_4x4() @ Matrix.Diagonal((1, 1, Lp + 0.09, 1)); Mp.translation = T
        self.pen.matrix_world = Mp
        self.pen_state = (T, P, Lp)

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
    bm = bmesh.new(); bm.from_mesh(me); r0, h0 = GRIP['can']
    for sg in (1, -1):
        for rad, dep, z in ((r0 * 0.86, 0.002, sg * (h0 / 2 + 0.0008)), (r0 + 0.0006, 0.005, sg * (h0 / 2 - 0.0022))):
            res = bmesh.ops.create_cone(bm, cap_ends=True, segments=48, radius1=rad, radius2=rad, depth=dep, matrix=Matrix.Translation((0, 0, z)))
            for f in {f for v in res['verts'] for f in v.link_faces}: f.material_index = 1; f.smooth = True
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


ARM_SHIFT = {('Ben', 'L'): 0.025}
ARM_CHAIN = ('upper_arm', 'forearm', 'hand', 'palm', 'f_index', 'f_middle', 'f_ring', 'f_pinky', 'thumb')
FIT_X0 = 0.12
HIDE_ERODE = 0.015
LAYER_OFF = 0.004
BOARD_FWD = 0.03
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
        self.curl[(sd, key)] = self._solve_real(kr, sd, key)
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
    def score(c, d): return (0 if 0.0 <= d <= 0.004 else 1, abs(d - SKIN) if not (0.0 <= d <= 0.004) else (abs(c[0]) + abs(c[1])) * 1e-4)
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
    D, tip, shape, Rw, pole = g
    if not isinstance(D, V) or Rw is None: return g
    tl = ra.hand[side][shape][tip]
    W = Matrix.Translation(D - Rw @ tl) @ Rw.to_4x4()
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
            d = ac.kw.get('dur', 1.2); w = max(w, sm(u, ac.at, ac.at + 0.3) * (1 - sm(u, ac.at + d, ac.at + d + 0.3)))
    return w


Graft.drink_w = _drink_w


def _bloat_value(self):
    b = self.body.data.shape_keys.key_blocks.get('kw_bloat')
    return b.value if b is not None else 0.0


Graft.goal = _goal
Graft.bloat_value = _bloat_value


def _apply_contacts(self, kr, shot):
    """frame hook part 1: finger curls + HG prop placement (after kwfx placed the props on the kit hand)."""
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
        for k, (c1, c2, _) in self.curl[(side, key)].items():
            for jj in (1, 2, 3):
                e = p.pb(f'finger{k}-{jj}.{side}').rotation_euler
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
            if ob is not None: ob.matrix_world = kr.wmat(p, f'wrist.{side}') @ self.Pl[(side, h.prop)]


Graft.apply_contacts = _apply_contacts
