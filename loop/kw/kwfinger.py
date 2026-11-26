"""kwfinger - a fingertip on the HumGen body (ep10 'What Your Body Does To A Splinter'; reusable: any side / finger).

Fingertip(rt, ra, side='L', finger='index', shape='inspect')
  anchor   ray cast on the evaluated (smoothed) body with the hand in `shape`: the pad point C, the entry point E and a
           right-handed pad frame X = along the finger (to the tip), Z = out of the pad, Y = Z x X (for the left hand: his left).
           The frame is an empty bone-parented to the HG distal bone, so everything below follows the finger.
  body     one geometry-nodes modifier at the end of the body stack: Catmull-Clark x2 + the swell / dome / lump bumps
           (pad-local maths from the frame empty, masked by a 'kw_pad' point attribute = the finger's distal + middle bone weights)
  skin     the HG skin material gets: macro tone (the 2K HG colour map smears in a macro, ep07 G1), fingerprint ridges (bump,
           macro only, pad only), red ring, cream dome showing through, the splinter's faint dark line, pinker tip, 'vanish'
  splinter wood 15 x 1 x 0.6 mm, tapered deep end, frayed blunt end, fibres; enters at `angle` with `stub` metres outside
  block    a local skin block (ep07 / kwfx skin_block look) under the entry, cut in the plane of the splinter: top skin (the
           body's own material), thin epidermis, pink dermis, pale-buttery fat lobules; white cells, pus sheath + pocket,
           capsule, two block lights.  Hidden until set(cut>0).
Controls (set(**v)): red swell dome lump out line vanish cut ridges cells(frame-local time, s) pus pocket capsule tw_* ...
"""
import bpy, bmesh, math, random
from mathutils import Vector as V, Matrix
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform
import kwlib as L

FING = {'thumb': (1, 'thumb'), 'index': (2, 'f_index'), 'middle': (3, 'f_middle'), 'ring': (4, 'f_ring'), 'pinky': (5, 'f_pinky')}


def lin(h):
    def f(x): return x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4
    return tuple(f(int(h[i:i + 2], 16) / 255) for i in (0, 2, 4))


def sstep(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a))); return t * t * (3 - 2 * t)


# ---------------------------------------------------------------------------------------------------- bump shapes (metres)
SWELL_H, SWELL_R = 0.0015, 0.0055       # 1.5 mm puff, gaussian radius
DOME_H, DOME_R = 0.0011, 0.0026         # 5 mm pus dome
LUMP_H, LUMP_R = 0.0008, 0.0021         # 4 mm firm lump


class Fingertip:
    def __init__(self, rt, ra, side='L', finger='index', shape='inspect', entry=-0.004, angle=20.0, length=0.015, stub=0.004,
                 cam_side=1, seed=10, block=True):
        self.rt, self.ra, self.p = rt, ra, ra.p; self.side = side; self.finger = finger
        self.hg = ra.p.hg; self.body = self.hg.body; self.rig = self.hg.rig
        k, hgn = FING[finger]; self.mh_bone = f'finger{k}-3.{side}'; self.bone = f'{hgn}.03.{side}'; self.bone2 = f'{hgn}.02.{side}'
        self.ang = math.radians(angle); self.Ls = length; self.stub = stub; self.Lin = length - stub; self.cs = cam_side
        self.rnd = random.Random(seed); self.c = L.coll('kw_finger')
        # axis frame of the splinter in pad space: in = down into the skin, toward the fingertip
        self.u_in = V((math.cos(self.ang), 0.0, -math.sin(self.ang))); self.n_s = V((math.sin(self.ang), 0.0, math.cos(self.ang)))
        self.vals = dict(red=0.0, swell=0.0, dome=0.0, lump=0.0, out=0.0, line=1.0, vanish=0.0, cut=0.0, ridges=1.0, macro=1.0,
                         pus=0.0, pocket=0.0, capsule=0.0, cells=-1.0, cling=1.0, sheath_fade=1.0, tip_pink=1.0)
        if getattr(self.body.data, 'has_custom_normals', False):
            with bpy.context.temp_override(object=self.body, active_object=self.body): bpy.ops.mesh.customdata_custom_splitnormals_clear()
        rt.reset(self.p); rt.set_shape(self.p, side, shape); bpy.context.view_layer.update()
        self._pad_attr()
        self.gn = self._gn(); bpy.context.view_layer.update()
        self._anchor(entry)
        self._shader()
        self.splinter = self._splinter()
        self.blk = []
        if block:
            self._block(); self._cells(26); self._pus(); self._capsule(); self._lights()
        rt.reset(self.p); bpy.context.view_layer.update()
        self.set()

    # ------------------------------------------------------------------ pad attribute (finger distal + middle bones)
    def _pad_attr(self):
        b = self.body; vg = {g.name: g.index for g in b.vertex_groups}
        ids = {vg.get(self.bone), vg.get(self.bone2)} - {None}
        w = [0.0] * len(b.data.vertices)
        for v in b.data.vertices:
            s = sum(g.weight for g in v.groups if g.group in ids)
            w[v.index] = min(1.0, s)
        at = b.data.attributes.get('kw_pad') or b.data.attributes.new('kw_pad', 'FLOAT', 'POINT')
        at.data.foreach_set('value', w)
        print(f'finger: kw_pad on {sum(1 for x in w if x > 0.5)} verts ({self.bone}, {self.bone2}); body matrix scale', tuple(round(x, 3) for x in b.matrix_world.to_scale()))

    # ------------------------------------------------------------------ geometry nodes: smooth + bumps
    def _gn(self):
        gt = bpy.data.node_groups.new('kw_finger_gn', 'GeometryNodeTree'); N = gt.nodes; Lk = gt.links.new; it = gt.interface
        it.new_socket('Geometry', in_out='INPUT', socket_type='NodeSocketGeometry')
        self._sid = {}
        for nm, st in (('Frame', 'NodeSocketObject'), ('swell', 'NodeSocketFloat'), ('dome', 'NodeSocketFloat'), ('lump', 'NodeSocketFloat'), ('level', 'NodeSocketInt')):
            s = it.new_socket(nm, in_out='INPUT', socket_type=st); self._sid[nm] = s.identifier
        it.new_socket('Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')
        gi = N.new('NodeGroupInput'); go = N.new('NodeGroupOutput')
        cc = N.new('GeometryNodeSubdivisionSurface'); Lk(gi.outputs[0], cc.inputs['Mesh']); Lk(gi.outputs['level'], cc.inputs['Level'])
        oi = N.new('GeometryNodeObjectInfo'); oi.transform_space = 'RELATIVE'; Lk(gi.outputs['Frame'], oi.inputs['Object'])
        pos = N.new('GeometryNodeInputPosition'); nrm = N.new('GeometryNodeInputNormal')
        def vm(op, a, b=None):
            n = N.new('ShaderNodeVectorMath'); n.operation = op; Lk(a, n.inputs[0])
            if b is not None:
                if isinstance(b, (tuple, list)): n.inputs[1].default_value = b
                else: Lk(b, n.inputs[1])
            return n.outputs['Value'] if op in ('LENGTH', 'DOT_PRODUCT') else n.outputs[0]
        def m(op, a, b=None, clamp=False):
            n = N.new('ShaderNodeMath'); n.operation = op; n.use_clamp = clamp
            for i, x in enumerate((a, b)):
                if x is None: continue
                if isinstance(x, (int, float)): n.inputs[i].default_value = x
                else: Lk(x, n.inputs[i])
            return n.outputs[0]
        d = vm('SUBTRACT', pos.outputs[0], oi.outputs['Location'])
        rot = N.new('ShaderNodeVectorRotate'); rot.rotation_type = 'EULER_XYZ'; rot.invert = True
        Lk(d, rot.inputs['Vector']); Lk(oi.outputs['Rotation'], rot.inputs['Rotation'])
        loc = vm('DIVIDE', rot.outputs[0], oi.outputs['Scale'])
        sx = N.new('ShaderNodeSeparateXYZ'); Lk(loc, sx.inputs[0]); a_, c_, z_ = sx.outputs[0], sx.outputs[1], sx.outputs[2]
        def r2(a0):        # squared distance in the pad plane from (a0, 0)
            da = m('SUBTRACT', a_, a0); return m('ADD', m('MULTIPLY', da, da), m('MULTIPLY', c_, c_))
        def bumpf(a0, R):  # (1 - (r/R)^2)^2 inside R
            q = m('SUBTRACT', 1.0, m('DIVIDE', r2(a0), R * R), clamp=True); return m('MULTIPLY', q, q)
        g_sw = m('EXPONENT', m('MULTIPLY', r2(self.A_SW), -1.0 / (SWELL_R ** 2)))
        h = m('MULTIPLY', m('MULTIPLY', g_sw, SWELL_H), gi.outputs['swell'])
        h = m('ADD', h, m('MULTIPLY', m('MULTIPLY', bumpf(self.A_DOME, DOME_R), DOME_H), gi.outputs['dome']))
        h = m('ADD', h, m('MULTIPLY', m('MULTIPLY', bumpf(self.A_LUMP, LUMP_R), LUMP_H), gi.outputs['lump']))
        na = N.new('GeometryNodeInputNamedAttribute'); na.data_type = 'FLOAT'; na.inputs['Name'].default_value = 'kw_pad'
        zm = N.new('ShaderNodeMapRange'); zm.interpolation_type = 'SMOOTHSTEP'; zm.inputs[1].default_value = -0.0065; zm.inputs[2].default_value = -0.0025; Lk(z_, zm.inputs[0])
        h = m('MULTIPLY', m('MULTIPLY', h, na.outputs['Attribute']), zm.outputs[0])
        sc = N.new('ShaderNodeSeparateXYZ'); Lk(oi.outputs['Scale'], sc.inputs[0])
        off = vm('SCALE', nrm.outputs[0]); sk = off.node.inputs['Scale']; Lk(m('MULTIPLY', h, sc.outputs[0]), sk)
        sp = N.new('GeometryNodeSetPosition'); Lk(cc.outputs[0], sp.inputs['Geometry']); Lk(off, sp.inputs['Offset'])
        Lk(sp.outputs[0], go.inputs[0])
        md = self.body.modifiers.new('kw_finger', 'NODES'); md.node_group = gt; md[self._sid['level']] = 2
        self.md = md; return md

    # bump positions along the finger (pad-local a, metres from the entry; + = toward the tip)
    A_SW, A_DOME, A_LUMP = 0.0015, 0.0012, 0.0062

    def h(self, a, c, z=0.0):
        v = self.vals; r2 = lambda a0: (a - a0) ** 2 + c * c
        q = lambda a0, R: max(0.0, 1 - r2(a0) / (R * R)) ** 2
        return (v['swell'] * SWELL_H * math.exp(-r2(self.A_SW) / SWELL_R ** 2) + v['dome'] * DOME_H * q(self.A_DOME, DOME_R)
                + v['lump'] * LUMP_H * q(self.A_LUMP, LUMP_R))

    # ------------------------------------------------------------------ anchor
    def _surface(self):
        dg = bpy.context.evaluated_depsgraph_get(); be = self.body.evaluated_get(dg); me = be.to_mesh()
        me.calc_loop_triangles(); uvl = me.uv_layers.active.data; mw = be.matrix_world
        self._verts = [mw @ v.co for v in me.vertices]; self._tri_v = [tuple(t.vertices) for t in me.loop_triangles]
        self._tri_uv = [tuple(uvl[l].uv.copy() for l in t.loops) for t in me.loop_triangles]
        self.bvh = BVHTree.FromPolygons(self._verts, self._tri_v); be.to_mesh_clear()

    def hit(self, p, n, back=0.02, dist=0.035):
        loc, nrm, i, d = self.bvh.ray_cast(p + n * back, -n, dist)
        if loc is None: return None
        a, b_, c = (self._verts[k] for k in self._tri_v[i]); ua, ub, uc = (V((u.x, u.y, 0)) for u in self._tri_uv[i])
        uv = barycentric_transform(loc, a, b_, c, ua, ub, uc)
        if nrm.dot(n) < 0: nrm = -nrm
        return loc, nrm, V((uv.x, uv.y))

    def _anchor(self, entry):
        self.md.show_viewport = True; self._surface()
        R = self.rig.matrix_world; pb = self.rig.pose.bones[self.bone]; H, T = R @ pb.head, R @ pb.tail
        Mw = self.rt.wmat(self.p, f'wrist.{self.side}'); n = (Mw.to_3x3() @ V(self.ra.hand[self.side]['pnorm'])).normalized()
        ax = (T - H).normalized(); n = (n - ax * n.dot(ax)).normalized()
        h0 = self.hit(H.lerp(T, 0.5), n)
        if h0 is None: raise RuntimeError(f'finger: no pad hit on {self.bone}')
        C, Nc, _ = h0; A = (ax - Nc * ax.dot(Nc)).normalized()
        he = self.hit(C + A * entry, Nc); E, Ne, uv0 = he
        X = (A - Ne * A.dot(Ne)).normalized(); Z = Ne; Y = Z.cross(X)
        Fm = Matrix((X, Y, Z)).transposed().to_4x4(); Fm.translation = E
        self.F0 = Fm.copy(); Fi = Fm.inverted()
        e = bpy.data.objects.new('kw_tip_frame', None); self.c.objects.link(e); e.empty_display_size = 0.005; e.matrix_world = Fm
        L.bone_parent(e, self.rig, self.bone); self.frame_obj = e
        self.md[self._sid['Frame']] = e
        # pad-local profile of the real finger at c = 0 and across (for the block top) + UV->metres fit
        rows = []; prof = []
        for a in [x * 0.001 for x in range(-12, 15)]:
            hh = self.hit(Fm @ V((a, 0, 0)), Z)
            if hh: prof.append((a, (Fi @ hh[0]).z))
        for a in (-0.003, 0.0, 0.003):
            for c in (-0.003, 0.0, 0.003):
                hh = self.hit(Fm @ V((a, c, 0)), Z)
                if hh: rows.append((a, c, hh[2] - uv0))
        sa = sum(r[0] ** 2 for r in rows); sc = sum(r[1] ** 2 for r in rows); sac = sum(r[0] * r[1] for r in rows)
        Mi = Matrix(((sa, sac), (sac, sc))).inverted()
        bu = V((sum(r[0] * r[2].x for r in rows), sum(r[1] * r[2].x for r in rows))); bv = V((sum(r[0] * r[2].y for r in rows), sum(r[1] * r[2].y for r in rows)))
        ju = Mi @ bu; jv = Mi @ bv; self.J = Matrix(((ju.x, ju.y), (jv.x, jv.y))); self.uv0 = uv0
        # top curvature along the finger (fit z = -a^2 / 2Ra on |a| < 5 mm), across: the real finger near c = 0
        num = sum(a * a * z for a, z in prof if abs(a) < 0.0055); den = sum(a ** 4 for a, z in prof if abs(a) < 0.0055)
        k = -num / den if den > 0 else 0.0; self.Ra = max(0.02, 1.0 / (2 * k)) if k > 1e-6 else 0.05
        cprof = []
        for c in [x * 0.0005 for x in range(-16, 17)]:
            hh = self.hit(Fm @ V((0, c, 0)), Z)
            if hh: cprof.append((c, (Fi @ hh[0]).z))
        num = sum(c * c * z for c, z in cprof if abs(c) < 0.003); den = sum(c ** 4 for c, z in cprof if abs(c) < 0.003)
        kc = -num / den if den > 0 else 0.0; self.Rc_real = 1.0 / (2 * kc) if kc > 1e-6 else 0.05; self.Rc = max(0.022, self.Rc_real)
        self.prof, self.cprof = prof, cprof
        self.C_local = Fi @ C
        print(f'finger anchor E={tuple(round(x, 4) for x in E)} N={tuple(round(x, 3) for x in Ne)} X={tuple(round(x, 3) for x in X)} '
              f'pad C local {tuple(round(x * 1000, 1) for x in self.C_local)} mm  Ra {self.Ra * 1000:.1f} mm  Rc real {self.Rc_real * 1000:.1f} mm  uv/m {tuple(round(x, 2) for x in (ju.x, ju.y, jv.x, jv.y))}')
        print('finger profile c=0 (a mm, z mm):', [(round(a * 1000), round(z * 1000, 2)) for a, z in prof])

    def frame(self):
        return self.frame_obj.matrix_world.copy()

    # ------------------------------------------------------------------ skin shader
    def _shader(self):
        b = self.body
        m = next(s.material for s in b.material_slots if s.material and s.material.name.startswith('.Human'))
        self.mat = m; nt = m.node_tree; N = nt.nodes; Lk = nt.links.new
        bsdf = next(n for n in N if n.type == 'BSDF_PRINCIPLED'); out = next(n for n in N if n.type == 'OUTPUT_MATERIAL' and n.is_active_output)
        def val(name, v=0.0):
            n = N.new('ShaderNodeValue'); n.name = n.label = 'kwf_' + name; n.outputs[0].default_value = v; return n.outputs[0]
        self.SV = {k: val(k, self.vals.get(k, 0.0)) for k in ('red', 'dome', 'line', 'vanish', 'ridges', 'macro', 'lin_end', 'tip_pink')}
        def mth(op, a, b=None, clamp=False):
            n = N.new('ShaderNodeMath'); n.operation = op; n.use_clamp = clamp
            for i, x in enumerate((a, b)):
                if x is None: continue
                if isinstance(x, (int, float)): n.inputs[i].default_value = x
                else: Lk(x, n.inputs[i])
            return n.outputs[0]
        def sm(e0, e1, x):
            n = N.new('ShaderNodeMapRange'); n.interpolation_type = 'SMOOTHSTEP'; n.inputs[1].default_value = e0; n.inputs[2].default_value = e1
            if isinstance(x, (int, float)): n.inputs[0].default_value = x
            else: Lk(x, n.inputs[0])
            return n.outputs[0]
        def mixc(a, b, f):
            n = N.new('ShaderNodeMix'); n.data_type = 'RGBA'; n.blend_type = 'MIX'; n.clamp_factor = True
            for sock, x in ((n.inputs[0], f), (n.inputs[6], a), (n.inputs[7], b)):
                if isinstance(x, (tuple, list)): sock.default_value = (*x, 1.0) if len(x) == 3 else x
                elif isinstance(x, (int, float)): sock.default_value = x
                else: Lk(x, sock)
            return n.outputs[2]
        def mulc(a, col):
            n = N.new('ShaderNodeMix'); n.data_type = 'RGBA'; n.blend_type = 'MULTIPLY'; n.inputs[0].default_value = 1.0
            Lk(a, n.inputs[6]); n.inputs[7].default_value = (*col, 1.0); return n.outputs[2]
        tc = N.new('ShaderNodeTexCoord'); tc.object = self.frame_obj; P = tc.outputs['Object']
        sx = N.new('ShaderNodeSeparateXYZ'); Lk(P, sx.inputs[0]); a_, c_, z_ = sx.outputs[0], sx.outputs[1], sx.outputs[2]
        at = N.new('ShaderNodeAttribute'); at.attribute_type = 'GEOMETRY'; at.attribute_name = 'kw_pad'; pad = at.outputs['Fac']
        reg = mth('MULTIPLY', pad, sm(-0.006, -0.002, z_))                   # pad side of the finger
        cd = N.new('ShaderNodeCameraData'); mf = mth('MULTIPLY', mth('SUBTRACT', 1.0, sm(0.12, 0.32, cd.outputs['View Distance'])), self.SV['macro'])
        mfr = mth('MULTIPLY', mf, mth('MULTIPLY', pad, sm(-0.009, -0.004, z_)))
        bl = bsdf.inputs['Base Color'].links; base = bl[0].from_socket if bl else None
        if base is None:
            rgb = N.new('ShaderNodeRGB'); rgb.outputs[0].default_value = tuple(bsdf.inputs['Base Color'].default_value); base = rgb.outputs[0]
        # macro tone: flat v1.1 finger tone + procedural mottling (the HG map smears at this scale)
        tone = (0.45, 0.205, 0.135)        # matched to the v1.1 hand in the Ben views (sRGB ~172,123,102 lit)
        n1 = N.new('ShaderNodeTexNoise'); n1.inputs['Scale'].default_value = 1.0 / 0.004; n1.inputs['Detail'].default_value = 3.0; Lk(P, n1.inputs['Vector'])
        n2 = N.new('ShaderNodeTexNoise'); n2.inputs['Scale'].default_value = 1.0 / 0.0009; n2.inputs['Detail'].default_value = 2.0; Lk(P, n2.inputs['Vector'])
        flat = mixc(tone, (0.49, 0.20, 0.135), sm(0.35, 0.7, n1.outputs['Fac']))
        flat = mixc(flat, (0.42, 0.21, 0.13), mth('MULTIPLY', sm(0.45, 0.7, n2.outputs['Fac']), 0.6))
        # fingerprint whorl: ellipses round the pad centre, warped; ridge spacing 0.5 mm
        cx = float(self.C_local.x) + 0.002
        wn = N.new('ShaderNodeTexNoise'); wn.inputs['Scale'].default_value = 1.0 / 0.003; wn.inputs['Detail'].default_value = 1.0; Lk(P, wn.inputs['Vector'])
        da = mth('DIVIDE', mth('SUBTRACT', a_, cx), 1.15); dc = mth('DIVIDE', c_, 0.85)
        rr = mth('SQRT', mth('ADD', mth('MULTIPLY', da, da), mth('MULTIPLY', dc, dc)))
        rr = mth('ADD', rr, mth('MULTIPLY', mth('SUBTRACT', wn.outputs['Fac'], 0.5), 0.0021))
        rid = mth('ADD', 0.5, mth('MULTIPLY', 0.5, mth('SINE', mth('MULTIPLY', rr, 2 * math.pi / 0.0005))))
        # real ridges break and fork: a fine noise knocks ~1/5 of the crests down; sweat pores sit on the crests
        brk = N.new('ShaderNodeTexNoise'); brk.inputs['Scale'].default_value = 1.0 / 0.0011; brk.inputs['Detail'].default_value = 2.0; Lk(P, brk.inputs['Vector'])
        rid = mth('MULTIPLY', rid, mth('SUBTRACT', 1.0, mth('MULTIPLY', sm(0.58, 0.70, brk.outputs['Fac']), 0.75)))
        vp = N.new('ShaderNodeTexVoronoi'); vp.feature = 'F1'; vp.inputs['Scale'].default_value = 1.0 / 0.00042; Lk(P, vp.inputs['Vector'])
        pore = mth('MULTIPLY', mth('SUBTRACT', 1.0, sm(0.04, 0.16, vp.outputs['Distance'])), sm(0.6, 0.9, rid))
        rid = mth('SUBTRACT', rid, mth('MULTIPLY', pore, 0.5))
        rmask = mth('MULTIPLY', mth('MULTIPLY', mfr, self.SV['ridges']), reg)
        flat = mixc(flat, mulc(flat, (0.86, 0.82, 0.82)), mth('MULTIPLY', sm(0.55, 0.95, rid), 0.28))     # furrows slightly darker
        c0 = mixc(base, flat, mth('MULTIPLY', mfr, 0.92))
        # pinker tip (fingertip end, toward +a)
        c0 = mixc(c0, mulc(c0, (1.05, 0.88, 0.86)), mth('MULTIPLY', mth('MULTIPLY', sm(0.004, 0.012, a_), pad), mth('MULTIPLY', self.SV['tip_pink'], 0.6)))
        # the splinter under the skin: a faint dark line from the entry along +a, fading with depth
        a_end = self.SV['lin_end']
        inl = mth('MULTIPLY', sm(0.0002, 0.0009, a_), mth('LESS_THAN', a_, a_end))
        lw = mth('SUBTRACT', 1.0, sm(0.00028, 0.0008, mth('ABSOLUTE', c_)))
        depthf = mth('SUBTRACT', 1.0, mth('MULTIPLY', mth('DIVIDE', a_, self.Lin * math.cos(self.ang)), 0.75, clamp=False), clamp=True)
        dl = mth('MULTIPLY', mth('MULTIPLY', mth('MULTIPLY', inl, lw), depthf), mth('MULTIPLY', self.SV['line'], pad))
        c0 = mixc(c0, mulc(c0, (0.42, 0.33, 0.30)), mth('MULTIPLY', dl, 0.55))
        # red ring 9 mm across round the entry
        rE = mth('SQRT', mth('ADD', mth('MULTIPLY', a_, a_), mth('MULTIPLY', c_, c_)))
        redf = mth('MULTIPLY', mth('SUBTRACT', 1.0, sm(0.0026, 0.0047, rE)), mth('MULTIPLY', self.SV['red'], pad))
        redf = mth('MULTIPLY', redf, mth('ADD', 0.75, mth('MULTIPLY', 0.25, sm(0.0005, 0.0022, rE))))
        c0 = mixc(c0, mulc(c0, (1.0, 0.50, 0.46)), mth('MULTIPLY', redf, 0.75))
        # cream dome showing through the intact skin
        dA = mth('SUBTRACT', a_, self.A_DOME); rD = mth('SQRT', mth('ADD', mth('MULTIPLY', dA, dA), mth('MULTIPLY', c_, c_)))
        domef = mth('MULTIPLY', mth('SUBTRACT', 1.0, sm(0.0008, 0.0025, rD)), mth('MULTIPLY', self.SV['dome'], pad))
        c0 = mixc(c0, (0.80, 0.70, 0.46), mth('MULTIPLY', domef, 0.5))
        Lk(c0, bsdf.inputs['Base Color'])
        # HG skin scatters ~1 cm: less of it on the pad in the macro so ridges / ring / line stay crisp
        if not bsdf.inputs['Subsurface Weight'].links:
            Lk(mth('SUBTRACT', bsdf.inputs['Subsurface Weight'].default_value, mth('MULTIPLY', mfr, 0.45)), bsdf.inputs['Subsurface Weight'])
        rl = bsdf.inputs['Roughness'].links
        if rl:
            rn = N.new('ShaderNodeMix'); rn.data_type = 'FLOAT'; rn.clamp_factor = True; Lk(mth('MULTIPLY', mfr, 0.8), rn.inputs[0]); Lk(rl[0].from_socket, rn.inputs[2]); rn.inputs[3].default_value = 0.52
            Lk(rn.outputs[0], bsdf.inputs['Roughness'])      # no plastic sheen in the macro
        # ridges as bump on top of the HG normal map
        nl = bsdf.inputs['Normal'].links; prev = nl[0].from_socket if nl else None
        bp = N.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 1.0; bp.inputs['Distance'].default_value = 1.0
        Lk(mth('MULTIPLY', mth('MULTIPLY', rid, rmask), 0.000045), bp.inputs['Height'])
        if prev is not None: Lk(prev, bp.inputs['Normal'])
        Lk(bp.outputs[0], bsdf.inputs['Normal'])
        # vanish: the whole body fades (the dive)
        sl = out.inputs['Surface'].links[0].from_socket
        ms = N.new('ShaderNodeMixShader'); tr = N.new('ShaderNodeBsdfTransparent'); Lk(self.SV['vanish'], ms.inputs[0]); Lk(sl, ms.inputs[1]); Lk(tr.outputs[0], ms.inputs[2])
        Lk(ms.outputs[0], out.inputs['Surface'])
        try: m.blend_method = 'HASHED'
        except Exception: pass

    # ------------------------------------------------------------------ splinter
    def _wood_mat(self):
        m = L.mat('kwf_wood', lin('5A3B22'), 0.78); nt = m.node_tree; N = nt.nodes; Lk = nt.links.new; b = L.bsdf(m)
        tc = N.new('ShaderNodeTexCoord'); mp = N.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (180.0, 9000.0, 9000.0)
        Lk(tc.outputs['Object'], mp.inputs['Vector'])
        nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 1.0; nz.inputs['Detail'].default_value = 4.0; nz.inputs['Roughness'].default_value = 0.6
        Lk(mp.outputs[0], nz.inputs['Vector'])
        rp = N.new('ShaderNodeValToRGB'); r = rp.color_ramp
        r.elements[0].position = 0.45; r.elements[0].color = (*[x * 0.62 for x in lin('5A3B22')], 1); r.elements[1].position = 0.66; r.elements[1].color = (*[x * 0.62 for x in lin('8A6440')], 1)   # x0.62: lit, it read 1.5x too pale
        e = r.elements.new(0.30); e.color = (*[x * 0.45 for x in lin('5A3B22')], 1)
        Lk(nz.outputs['Fac'], rp.inputs[0]); Lk(rp.outputs[0], b.inputs['Base Color'])
        bp = N.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.6; bp.inputs['Distance'].default_value = 0.00004
        Lk(nz.outputs['Fac'], bp.inputs['Height']); Lk(bp.outputs[0], b.inputs['Normal'])
        b.inputs['Specular IOR Level'].default_value = 0.25
        return m

    def _splinter(self):
        """local X = axis from the blunt end (0) to the deep tip (Ls); Y = width 1 mm; Z = thickness 0.6 mm"""
        rnd = self.rnd; bm = bmesh.new(); Ls = self.Ls; W, Tk = 0.0005, 0.0003
        ring_n = 14; xs = [0.0, 0.00015, 0.0004] + [0.0004 + (Ls - 0.0004) * (i / 40) ** 1.0 for i in range(1, 41)]
        rings = []
        for i, x in enumerate(xs):
            tap = 1.0 if x < Ls - 0.0045 else max(0.0, (Ls - x) / 0.0045) ** 0.85
            wob = 1.0 + 0.05 * math.sin(x * 2300 + 1.3) + 0.03 * math.sin(x * 5100)
            ring = []
            for k in range(ring_n):
                t = 2 * math.pi * k / ring_n; cy, cz = math.cos(t), math.sin(t)
                # rounded rectangle (superellipse)
                ey = math.copysign(abs(cy) ** 0.45, cy); ez = math.copysign(abs(cz) ** 0.45, cz)
                y = ey * W * tap * wob; z = ez * Tk * tap * (1.0 + 0.04 * math.sin(x * 3700 + k))
                xx = x
                if i == 0: xx = x + rnd.uniform(-0.00012, 0.00018)       # frayed: a jagged break
                if tap <= 0.0: y = z = 0.0
                ring.append(bm.verts.new((xx, y, z)))
            rings.append(ring)
        for r0, r1 in zip(rings, rings[1:]):
            for k in range(ring_n):
                bm.faces.new((r0[k], r0[(k + 1) % ring_n], r1[(k + 1) % ring_n], r1[k]))
        bm.faces.new(list(reversed(rings[0])))
        bmesh.ops.remove_doubles(bm, verts=rings[-1], dist=1e-7)
        me = bpy.data.meshes.new('kwf_splinter'); bm.to_mesh(me); bm.free()
        o = bpy.data.objects.new('kwf_splinter', me); self.c.objects.link(o); L.smooth(o)
        wm = self._wood_mat(); o.data.materials.append(wm)
        # frayed fibres at the blunt end
        fb = bmesh.new()
        for j in range(7):
            y0 = rnd.uniform(-W * 0.8, W * 0.8); z0 = rnd.uniform(-Tk * 0.8, Tk * 0.8); ln = rnd.uniform(0.00025, 0.0007); th = rnd.uniform(0.00004, 0.00009)
            dy, dz = rnd.uniform(-0.25, 0.25), rnd.uniform(-0.25, 0.25)
            res = bmesh.ops.create_cube(fb, size=1.0)
            for v in res['verts']:
                x, y, z = v.co; f = (0.5 - x)                       # x in [-.5,.5] -> fibre from the end face (x=0) outward (-X)
                v.co = V((-(x + 0.5) * ln + 0.00008, y0 + y * th + dy * (x + 0.5) * ln, z0 + z * th * 0.7 + dz * (x + 0.5) * ln))
        fme = bpy.data.meshes.new('kwf_fibres'); fb.to_mesh(fme); fb.free()
        fo = bpy.data.objects.new('kwf_fibres', fme); self.c.objects.link(fo); fo.data.materials.append(wm); fo.parent = o
        o.parent = self.frame_obj; o.matrix_parent_inverse = Matrix.Identity(4)
        self.fibres = fo
        self._place_splinter(0.0)
        return o

    def splinter_M(self, out=0.0):
        """local matrix of the splinter in the pad frame; out = metres slid back out along its axis"""
        R = Matrix((self.u_in, V((0, 1, 0)), self.n_s)).transposed().to_4x4()
        R.translation = -self.u_in * (self.stub + out) + V((0, 0, 1)) * (0.9 * self.h(0.0, 0.0))     # the swelling skin lifts it
        return R

    def _place_splinter(self, out):
        self.splinter_local = self.splinter_M(out)
        return self.splinter_local

    def end_point(self, out=0.0, world=True, inset=0.0):
        """the blunt (outer) end centre, optionally `inset` m along the axis toward the tip"""
        p = self.splinter_M(out) @ V((inset, 0, 0))
        return self.frame() @ p if world else p

    # ------------------------------------------------------------------ block (cut-away)
    def ztop0(self, a, c):
        return -(a * a) / (2 * self.Ra) - (c * c) / (2 * self.Rc)

    def _bmat(self, name, col, rough=0.35, sss=0.0, ss_scale=0.0012, noise=None, coat=0.15, trans=0.0, alpha=1.0):
        m = L.mat(name, col, rough); b = L.bsdf(m); nt = m.node_tree; N = nt.nodes; Lk = nt.links.new
        b.inputs['Coat Weight'].default_value = coat; b.inputs['Coat Roughness'].default_value = 0.2
        if sss:
            b.inputs['Subsurface Weight'].default_value = sss; b.inputs['Subsurface Radius'].default_value = (1.0, 0.5, 0.27); b.inputs['Subsurface Scale'].default_value = ss_scale
        if trans: b.inputs['Transmission Weight'].default_value = trans
        if noise:
            dark, light, sc, bumpd = noise
            tc = N.new('ShaderNodeTexCoord'); nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = sc; nz.inputs['Detail'].default_value = 2.6; nz.inputs['Roughness'].default_value = 0.68
            Lk(tc.outputs['Object'], nz.inputs['Vector'])
            rp = N.new('ShaderNodeValToRGB'); r = rp.color_ramp; r.interpolation = 'EASE'
            r.elements[0].position = 0.24; r.elements[0].color = (*dark, 1); r.elements[1].position = 0.78; r.elements[1].color = (*light, 1)
            Lk(nz.outputs['Fac'], rp.inputs[0]); Lk(rp.outputs[0], b.inputs['Base Color'])
            bp = N.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.3; bp.inputs['Distance'].default_value = bumpd
            Lk(nz.outputs['Fac'], bp.inputs['Height']); Lk(bp.outputs[0], b.inputs['Normal'])
        if alpha < 1.0:
            b.inputs['Alpha'].default_value = alpha
            try: m.blend_method = 'HASHED'
            except Exception: pass
        return m

    BLK_A = (-0.012, 0.0165); BLK_C = -0.012; BLK_Z = 0.0085      # block extent (pad-local): a range, back face c, depth
    D_EPI, D_DER = 0.00012, 0.0046                                 # layer bottoms (depth below the top)

    def _block(self):
        A0, A1 = self.BLK_A; C0 = self.BLK_C; ZB = self.BLK_Z
        sc = 1.0 / 0.028                                           # noise scales as the 0.5 m SkinBlock, per block size
        self.m_epi = self._bmat('kwf_blk_epi', lin('E09170'), 0.4, 0.3, 0.0004, (lin('BF6247'), lin('F5B794'), 115 * sc * 0.5, 0.00002), 0.26)
        self.m_der = self._bmat('kwf_blk_derm', lin('CB586E'), 0.25, 0.48, 0.0012, (lin('A62A4E'), lin('F69B9C'), 36 * sc * 0.5, 0.00004), 0.2)
        self.m_fat = self._bmat('kwf_blk_fat', lin('D9B868'), 0.3, 0.45, 0.0012, (lin('C9A451'), lin('EBCB6E'), 16 * sc * 0.5, 0.00005), 0.2)
        self.m_lob = [self._bmat(f'kwf_lobule{i}', lin(h), 0.28, 0.5, 0.0009, None, 0.3, trans=0.12) for i, h in enumerate(('EBCB6E', 'F0D27A', 'E4C060'))]
        na = 113; nc = 49
        def wave_e(a): return 0.000025 * math.sin(a * 2 * math.pi / 0.0004) + 0.00001 * math.sin(a * 21000 + 0.7)
        def wave_d(a): return 0.00022 * math.sin(a * 2 * math.pi / 0.0047 + 0.6) + 0.00011 * math.sin(a * 2 * math.pi / 0.0021 + 1.9)
        self._bverts = []          # (obj, [(a, c, depth, kind)]) kind: 0 top (follows top + h), 1 layer (top - depth + h w(depth))
        def grid_obj(name, mat, pts, faces):
            me = bpy.data.meshes.new(name); me.from_pydata([(0, 0, 0)] * len(pts), [], faces); me.update()
            o = bpy.data.objects.new(name, me); self.c.objects.link(o); L.smooth(o)
            if isinstance(mat, (list, tuple)):
                for mm in mat: o.data.materials.append(mm)
            else: o.data.materials.append(mat)
            o.parent = self.frame_obj; o.matrix_parent_inverse = Matrix.Identity(4)
            self._bverts.append((o, pts)); self.blk.append(o); return o
        # top skin (body material, UVs from the fitted UV->metres map so the HG texture lines up)
        pts = []; faces = []
        for j in range(nc):
            c = C0 * (1 - j / (nc - 1))
            for i in range(na): a = A0 + (A1 - A0) * i / (na - 1); pts.append((a, c, 0.0, 0))
        for j in range(nc - 1):
            for i in range(na - 1):
                q = j * na + i; faces.append((q, q + 1, q + na + 1, q + na))
        top = grid_obj('kwf_blk_top', self.mat, pts, faces)
        uvl = top.data.uv_layers.new(name='UVMap'); pad = top.data.attributes.new('kw_pad', 'FLOAT', 'POINT'); pad.data.foreach_set('value', [1.0] * len(pts))
        for poly in top.data.polygons:
            for li in poly.loop_indices:
                vi = top.data.loops[li].vertex_index; a, c = pts[vi][0], pts[vi][1]
                uv = self.uv0 + self.J @ V((a, c)); uvl.data[li].uv = (uv.x, uv.y)
        self.top = top
        # front (cut) face per layer at c = 0 + end faces at a = A0 / A1 (one ring of faces per layer, as _skin_slab)
        def band(name, mat, d0f, d1f, nz):
            pts = []; faces = []
            for k in range(nz):
                t = k / (nz - 1)
                for i in range(na):
                    a = A0 + (A1 - A0) * i / (na - 1); d = d0f(a) + (d1f(a) - d0f(a)) * t; pts.append((a, 0.0, d, 1))
            for k in range(nz - 1):
                for i in range(na - 1):
                    q = k * na + i; faces.append((q, q + na, q + na + 1, q + 1))
            base = len(pts); ncz = 9
            for side_a, flip in ((A0, False), (A1, True)):
                s0 = len(pts)
                for k in range(nz):
                    t = k / (nz - 1)
                    for j in range(ncz):
                        c = C0 * j / (ncz - 1); d = d0f(side_a) + (d1f(side_a) - d0f(side_a)) * t; pts.append((side_a, c, d, 1))
                for k in range(nz - 1):
                    for j in range(ncz - 1):
                        q = s0 + k * ncz + j; f = (q, q + 1, q + ncz + 1, q + ncz); faces.append(tuple(reversed(f)) if flip else f)
            return grid_obj(name, mat, pts, faces)
        band('kwf_blk_epi', self.m_epi, lambda a: 0.0, lambda a: self.D_EPI + wave_e(a), 3)
        band('kwf_blk_derm', self.m_der, lambda a: self.D_EPI + wave_e(a), lambda a: self.D_DER + wave_d(a), 26)
        band('kwf_blk_fat', self.m_fat, lambda a: self.D_DER + wave_d(a), lambda a: ZB, 14)
        # bottom
        pts = []; faces = []
        for j in range(9):
            for i in range(na): pts.append((A0 + (A1 - A0) * i / (na - 1), C0 * j / 8, ZB, 1))
        for j in range(8):
            for i in range(na - 1):
                q = j * na + i; faces.append((q, q + 1, q + na + 1, q + na))
        grid_obj('kwf_blk_bottom', self.m_fat, pts, faces)
        # fat lobules on the cut face (pale buttery yellow, slightly translucent)
        rnd = random.Random(31); self.lobes = []
        a = A0 + 0.0004
        while a < A1 - 0.0004:
            for row in range(3):
                d = self.D_DER + 0.0011 + row * 0.0013 + rnd.uniform(-0.0002, 0.0002) + wave_d(a) * 0.6
                if d > ZB - 0.0006: continue
                rx, ry, rz = rnd.uniform(0.0006, 0.00095), rnd.uniform(0.00035, 0.0005), rnd.uniform(0.00052, 0.0008)
                o = L.sphere(f'kwf_lobe', 1.0, (0, 0, 0), rnd.choice(self.m_lob), None, 14, 8)
                for u in list(o.users_collection): u.objects.unlink(o)
                self.c.objects.link(o); o.scale = (rx, ry, rz)
                o.parent = self.frame_obj; o.matrix_parent_inverse = Matrix.Identity(4)
                aa = a + rnd.uniform(-0.0002, 0.0002); self.lobes.append((o, aa, d)); self.blk.append(o)
            a += rnd.uniform(0.0013, 0.0017)
        self._upd_block(force=True)

    def _wdepth(self, d): return 1.0 - sstep(0.0015, 0.0036, d)

    def _upd_block(self, force=False):
        key = tuple(round(self.vals[k], 4) for k in ('swell', 'dome', 'lump'))
        if not force and getattr(self, '_bkey', None) == key: return
        self._bkey = key
        for o, pts in self._bverts:
            co = []
            for a, c, d, kind in pts:
                if kind == 0: z = self.ztop0(a, c) + self.h(a, c)
                else: z = self.ztop0(a, c) - d + self.h(a, c) * self._wdepth(d)
                co.extend((a, c, z))
            o.data.vertices.foreach_set('co', co); o.data.update()
        for o, a, d in self.lobes:
            o.location = (a, -0.00012, self.ztop0(a, 0) - d + self.h(a, 0) * self._wdepth(d))

    # ------------------------------------------------------------------ white cells
    def _cell_mat(self):
        m = L.mat('kwf_cell', (0.86, 0.85, 0.89), 0.32); b = L.bsdf(m); nt = m.node_tree; N = nt.nodes; Lk = nt.links.new
        b.inputs['Subsurface Weight'].default_value = 0.55; b.inputs['Subsurface Radius'].default_value = (0.9, 0.85, 1.0); b.inputs['Subsurface Scale'].default_value = 0.00025
        b.inputs['Coat Weight'].default_value = 0.35; b.inputs['Coat Roughness'].default_value = 0.25
        lw = N.new('ShaderNodeLayerWeight'); lw.inputs['Blend'].default_value = 0.35
        mp = N.new('ShaderNodeMapRange'); mp.inputs[1].default_value = 0.0; mp.inputs[2].default_value = 0.55; Lk(lw.outputs['Facing'], mp.inputs[0])
        mx = N.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.clamp_factor = True
        inv = N.new('ShaderNodeMath'); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1.0; Lk(mp.outputs[0], inv.inputs[1])
        f2 = N.new('ShaderNodeMath'); f2.operation = 'MULTIPLY'; f2.inputs[1].default_value = 0.42; Lk(inv.outputs[0], f2.inputs[0])
        Lk(f2.outputs[0], mx.inputs[0]); mx.inputs[6].default_value = (0.86, 0.85, 0.89, 1); mx.inputs[7].default_value = (0.55, 0.42, 0.70, 1)
        Lk(mx.outputs[2], b.inputs['Base Color'])
        tc = N.new('ShaderNodeTexCoord'); nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 3.2; nz.inputs['Detail'].default_value = 3.0
        Lk(tc.outputs['Generated'], nz.inputs['Vector'])
        bp = N.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.35; bp.inputs['Distance'].default_value = 0.00004
        Lk(nz.outputs['Fac'], bp.inputs['Height']); Lk(bp.outputs[0], b.inputs['Normal'])
        return m

    def axis_pt(self, s, out=0.0):
        """pad-local point on the splinter axis at s metres from the blunt end"""
        return self.splinter_M(out) @ V((s, 0, 0))

    def _cells(self, n):
        rnd = random.Random(77); m = self._cell_mat(); self.cells = []
        self._cell_lift0 = 0.9 * self.h(0.0, 0.0)
        ylw = V((0, 1, 0))
        for i in range(n):
            r = rnd.uniform(0.00026, 0.00040)
            bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=3, radius=1.0)
            for v in bm.verts:     # soft irregular blob
                v.co *= 1.0 + 0.06 * math.sin(v.co.x * 3.1 + i) * math.cos(v.co.y * 2.7 + 2 * i) + 0.04 * math.sin(v.co.z * 4.3 + i * 0.7)
            me = bpy.data.meshes.new('kwf_cell'); bm.to_mesh(me); bm.free()
            o = bpy.data.objects.new('kwf_cell', me); self.c.objects.link(o); L.smooth(o); o.data.materials.append(m)
            o.parent = self.frame_obj; o.matrix_parent_inverse = Matrix.Identity(4)
            # landing spot: along the deep part, round the front / top / bottom of the wood
            s = self.stub + 0.0008 + (self.Ls - self.stub - 0.0028) * ((i + rnd.uniform(0.1, 0.9)) / n)
            th = rnd.uniform(-1.25, 1.25)                     # angle round the axis in the (n_s, +Y) half facing the camera
            half = (0.0003 * abs(math.cos(th)) + 0.0005 * abs(math.sin(th)))
            tap = 1.0 if s < self.Ls - 0.0045 else max(0.15, (self.Ls - s) / 0.0045)
            nrm = (self.n_s * math.cos(th) + ylw * math.sin(th) * self.cs).normalized()
            if rnd.random() < 0.35: nrm = (-self.n_s * math.cos(th) + ylw * math.sin(th) * self.cs).normalized()   # some underneath
            land = self.axis_pt(s) + nrm * (half * tap + r * 0.82)
            # start: off to the sides of the frame, in front of the cut face, curved path
            sa = rnd.choice((-1, 1)); start = V((land.x + sa * rnd.uniform(0.003, 0.006), self.cs * rnd.uniform(0.0006, 0.0018), land.z + rnd.uniform(-0.0025, 0.0015)))
            ctrl = (start + land) / 2 + V((rnd.uniform(-0.0015, 0.0015), self.cs * rnd.uniform(0.0002, 0.0012), rnd.uniform(-0.0018, 0.0018)))
            t0 = rnd.uniform(0.0, 2.6); dur = rnd.uniform(1.1, 2.6) / rnd.uniform(0.7, 1.3)
            self.cells.append(dict(o=o, r=r, land=land, start=start, ctrl=ctrl, nrm=nrm, t0=t0, dur=dur, ph=rnd.uniform(0, 6.28), wob=rnd.uniform(0.6, 1.4)))
            self.blk.append(o)
        order = sorted(range(n), key=lambda k: self.cells[k]['t0'] + self.cells[k]['dur'])
        self.land_times = [self.cells[k]['t0'] + self.cells[k]['dur'] for k in order]

    def _upd_cells(self, ts):
        """ts = seconds since the swarm began (<0: none); cells drift on curved paths, land, flatten 10 %, pulse 4 %"""
        for cdat in self.cells:
            o = cdat['o']
            if ts < 0: o.hide_render = True; continue
            x = (ts - cdat['t0']) / cdat['dur']
            if x < 0: o.hide_render = True; continue
            o.hide_render = False; r = cdat['r']
            if x < 1:
                xe = x * x * (3 - 2 * x) if x > 0.5 else 0.5 * (2 * x) ** 1.6 / 1.0 * 0.5 + x * 0.5
                xe = min(1.0, max(0.0, xe))
                p = (1 - xe) ** 2 * cdat['start'] + 2 * (1 - xe) * xe * cdat['ctrl'] + xe ** 2 * cdat['land']
                p = p + V((0, 0, 0.00008 * math.sin(ts * 3 * cdat['wob'] + cdat['ph']))) + self._slide_vec() * xe
                s_ = V((r, r, r)); fl = 0.0
                o.matrix_basis = Matrix.Translation(p) @ Matrix.Diagonal((*s_, 1.0)); continue
            k = min(1.0, (x - 1) * cdat['dur'] / 0.25)                  # flatten over a quarter second
            fl = 0.10 * k * self.vals['cling']; pul = 1.0 + 0.04 * math.sin((ts - cdat['t0'] - cdat['dur']) * 2 * math.pi * 0.9 + cdat['ph'])
            nrm = cdat['nrm']; q = V((0, 0, 1)).rotation_difference(nrm).to_matrix().to_4x4()
            S = Matrix.Diagonal(((1 + fl * 0.5) * pul, (1 + fl * 0.5) * pul, (1 - fl) * pul, 1.0)) @ Matrix.Diagonal((r, r, r, 1.0))
            land = cdat['land'] - nrm * (r * fl * 0.8) + self._slide_vec()
            o.matrix_basis = Matrix.Translation(land) @ q @ S

    def _slide_vec(self):
        return V((0, 0, 1)) * (0.9 * self.h(0.0, 0.0) - self._cell_lift0)     # follow the swell lift of the wood     # cells stay in the tissue while the wood slides

    def _out_m(self): return self.vals['out'] * (self.Lin + 0.0015)

    # ------------------------------------------------------------------ pus sheath + pocket
    def _pus(self):
        m = L.mat('kwf_pus', lin('EFE3B8'), 0.35, sss=0.4); b = L.bsdf(m); b.inputs['Subsurface Scale'].default_value = 0.0004
        b.inputs['Coat Weight'].default_value = 0.2; b.inputs['Base Color'].default_value = (*lin('E2CF94'), 1.0)
        nt = m.node_tree; out_ = next(n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL'); ms = nt.nodes.new('ShaderNodeMixShader'); tr = nt.nodes.new('ShaderNodeBsdfTransparent')
        ms.inputs[0].default_value = 0.7; nt.links.new(b.outputs[0], ms.inputs[1]); nt.links.new(tr.outputs[0], ms.inputs[2]); nt.links.new(ms.outputs[0], out_.inputs['Surface'])   # thin: the wood shows through
        try: m.blend_method = 'HASHED'
        except Exception: pass
        self.m_pus = m
        bm = bmesh.new(); W, Tk = 0.0005, 0.0003; n_ = 20; s0 = self.stub - 0.0002; s1 = self.Ls - 0.0003; nr = 30
        rings = []
        for i in range(nr):
            s = s0 + (s1 - s0) * i / (nr - 1); tap = 1.0 if s < self.Ls - 0.0045 else max(0.08, (self.Ls - s) / 0.0045) ** 0.85
            ring = []
            for k in range(n_):
                t = 2 * math.pi * k / n_; cy, cz = math.cos(t), math.sin(t)
                ring.append(bm.verts.new((s, cy, cz)))
            rings.append((ring, tap))
        for (r0, _), (r1, _) in zip(rings, rings[1:]):
            for k in range(n_): bm.faces.new((r0[k], r0[(k + 1) % n_], r1[(k + 1) % n_], r1[k]))
        bm.faces.new(list(reversed(rings[0][0]))); bm.faces.new(rings[-1][0])
        me = bpy.data.meshes.new('kwf_sheath'); bm.to_mesh(me); bm.free()
        o = bpy.data.objects.new('kwf_sheath', me); self.c.objects.link(o); L.smooth(o); o.data.materials.append(m)
        o.parent = self.frame_obj; o.matrix_parent_inverse = Matrix.Identity(4); self.sheath = o; self.blk.append(o)
        self._sheath_base = [(v.co.x, v.co.y, v.co.z) for v in me.vertices]
        self._sheath_tap = []
        for i in range(nr):
            for k in range(n_): self._sheath_tap.append(rings[i][1])
        # pocket: a soft cream lens under the dome, just inside the entry
        pk = L.sphere('kwf_pocket', 1.0, (0, 0, 0), m, None, 24, 12)
        for u in list(pk.users_collection): u.objects.unlink(pk)
        self.c.objects.link(pk); pk.parent = self.frame_obj; pk.matrix_parent_inverse = Matrix.Identity(4); self.pocket = pk; self.blk.append(pk)

    def _upd_pus(self):
        v = self.vals; th = 0.00022 * v['pus'] * v['sheath_fade'] * (1.0 - 0.6 * min(1.0, v['out']))
        W, Tk = 0.0005, 0.0003; co = []
        for (x, cy, cz), tap in zip(self._sheath_base, self._sheath_tap):
            ey = math.copysign(abs(cy) ** 0.5, cy); ez = math.copysign(abs(cz) ** 0.5, cz)
            wob = 1.0 + 0.15 * math.sin(x * 2900 + cy * 3) * math.cos(cz * 2 + x * 1700)
            co.extend((x, ey * (W * tap + th * wob) + cy * 0.00002, ez * (Tk * tap + th * wob) + cz * 0.00002))
        self.sheath.data.vertices.foreach_set('co', co); self.sheath.data.update()
        self.sheath.hide_render = th < 0.00002
        self.sheath.matrix_basis = self.splinter_M(0.0)      # the sheath stays in the tissue
        pk = v['pocket'] * v['sheath_fade']
        self.pocket.hide_render = pk < 0.02
        ctr = V((self.A_DOME, 0.0, self.ztop0(self.A_DOME, 0) - 0.00085 + self.h(self.A_DOME, 0) * 0.55))
        self.pocket.matrix_basis = Matrix.Translation(ctr) @ Matrix.Diagonal((0.0021 * pk + 1e-6, 0.0012 * pk + 1e-6, 0.00075 * pk + 1e-6, 1.0))

    # ------------------------------------------------------------------ capsule
    def _capsule(self):
        m = L.mat('kwf_capsule', lin('C9A6A0'), 0.42, sss=0.35); b = L.bsdf(m); nt = m.node_tree; N = nt.nodes; Lk = nt.links.new
        b.inputs['Subsurface Scale'].default_value = 0.0005; b.inputs['Coat Weight'].default_value = 0.15
        tc = N.new('ShaderNodeTexCoord'); nz = N.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 1.0 / 0.0007; nz.inputs['Detail'].default_value = 4.0
        Lk(tc.outputs['Object'], nz.inputs['Vector'])
        rp = N.new('ShaderNodeValToRGB'); r = rp.color_ramp; r.elements[0].position = 0.3; r.elements[0].color = (*[x * 0.66 for x in lin('C9A6A0')], 1); r.elements[1].position = 0.75; r.elements[1].color = (*[x * 0.8 for x in lin('D8BCB6')], 1)
        Lk(nz.outputs['Fac'], rp.inputs[0]); Lk(rp.outputs[0], b.inputs['Base Color'])
        bp = N.new('ShaderNodeBump'); bp.inputs['Strength'].default_value = 0.5; bp.inputs['Distance'].default_value = 0.00008; Lk(nz.outputs['Fac'], bp.inputs['Height']); Lk(bp.outputs[0], b.inputs['Normal'])
        # closing: visible where the angle round the axis is under capsule * pi (it wraps up from underneath)
        sx = N.new('ShaderNodeSeparateXYZ'); Lk(tc.outputs['Object'], sx.inputs[0])
        at2 = N.new('ShaderNodeMath'); at2.operation = 'ARCTAN2'; Lk(sx.outputs[1], at2.inputs[0]); ng = N.new('ShaderNodeMath'); ng.operation = 'MULTIPLY'; ng.inputs[1].default_value = -1.0
        Lk(sx.outputs[2], ng.inputs[0]); Lk(ng.outputs[0], at2.inputs[1])
        ab = N.new('ShaderNodeMath'); ab.operation = 'ABSOLUTE'; Lk(at2.outputs[0], ab.inputs[0])
        cv = N.new('ShaderNodeValue'); cv.name = 'kwf_cap'; self.cap_v = cv.outputs[0]
        lim = N.new('ShaderNodeMath'); lim.operation = 'MULTIPLY'; lim.inputs[1].default_value = math.pi * 1.02; Lk(cv.outputs[0], lim.inputs[0])
        lt = N.new('ShaderNodeMath'); lt.operation = 'LESS_THAN'; Lk(ab.outputs[0], lt.inputs[0]); Lk(lim.outputs[0], lt.inputs[1])
        al = N.new('ShaderNodeMath'); al.operation = 'MULTIPLY'; al.inputs[1].default_value = 0.9; Lk(lt.outputs[0], al.inputs[0])
        Lk(al.outputs[0], b.inputs['Alpha'])
        try: m.blend_method = 'HASHED'
        except Exception: pass
        bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=48, v_segments=24, radius=1.0)
        rnd = random.Random(5)
        sl = (self.Ls - self.stub) / 2 + 0.0006; ry, rz = 0.0012, 0.0010
        for v in bm.verts:
            x, y, z = v.co; lump = 1.0 + 0.07 * math.sin(x * 9 + y * 4) * math.cos(z * 7 + x * 3) + 0.05 * math.sin(y * 13 + z * 5)
            v.co = V((x * sl, y * ry * lump, z * rz * lump))
        me = bpy.data.meshes.new('kwf_capsule'); bm.to_mesh(me); bm.free()
        o = bpy.data.objects.new('kwf_capsule', me); self.c.objects.link(o); L.smooth(o); o.data.materials.append(m)
        o.parent = self.frame_obj; o.matrix_parent_inverse = Matrix.Identity(4)
        mid = (self.stub + self.Ls) / 2 - 0.0002
        M = self.splinter_M(0.0) @ Matrix.Translation(V((mid, 0, 0)))
        o.matrix_basis = M; self.capsule = o; self.blk.append(o)

    # ------------------------------------------------------------------ lights for the block
    def _lights(self):
        self.blights = []
        for nm, off, e, sz in (('kwf_blk_key', V((-0.02, 0.05 * self.cs, 0.05)), 0.9, 0.03), ('kwf_blk_fill', V((0.04, 0.05 * self.cs, -0.01)), 0.3, 0.05)):
            ld = bpy.data.lights.new(nm, 'AREA'); ld.energy = e; ld.size = sz; ld.color = (1.0, 0.97, 0.93)
            lo = bpy.data.objects.new(nm, ld); self.c.objects.link(lo); lo.parent = self.frame_obj; lo.matrix_parent_inverse = Matrix.Identity(4)
            lo.location = off; lo.rotation_euler = (-off).to_track_quat('-Z', 'Y').to_euler()
            self.blights.append((lo, e))

    # ------------------------------------------------------------------ state
    def set(self, **kw):
        v = self.vals; v.update(kw)
        md = self.md
        for k in ('swell', 'dome', 'lump'): md[self._sid[k]] = float(v[k])
        self.body.update_tag()
        out_m = self._out_m()
        lin_end = max(0.0, (self.Lin - out_m) * math.cos(self.ang)) - 0.0002 if out_m < self.Lin else -1.0
        for k in ('red', 'dome', 'line', 'vanish', 'ridges', 'macro', 'tip_pink'): self.SV[k].default_value = float(v[k])
        self.SV['lin_end'].default_value = lin_end
        self.splinter.matrix_basis = self.splinter_M(out_m)
        if v.get('tw_M') is not None: self.splinter.matrix_basis = v['tw_M']
        if self.blk:
            show = v['cut'] > 0.0
            for o in self.blk: o.hide_render = not show
            for lo, e in self.blights: lo.hide_render = not show; lo.data.energy = e * v['cut']
            if show:
                self._upd_block(); self._upd_cells(v['cells']); self._upd_pus()
                self.cap_v.default_value = float(v['capsule']); self.capsule.hide_render = v['capsule'] <= 0.001
