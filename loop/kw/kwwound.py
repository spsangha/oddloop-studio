"""kwwound - a healing skin wound ON the HumGen body (ep07 'How Stitches Work').
The cut lives in the skin shader of the person's own body material (edges match the skin):
  anchor = ray cast on the evaluated body at rest -> UV of the hit + a fitted UV->metres frame (a = along the cut, c = across),
  so the mask sticks to the skin under any pose.  Shader layers: open gap (wet dark red, bump groove), edge rim, closed fresh
  line, red puffy halo, pink scar, procedural pores / fine furrows (macro close-ups; HG maps here are only 2K/1K).
Geometry (curves, bone-parented to the shin, placed by ray casts at rest): white stitches, pale-yellow collagen strands, tiny red vessels.
Stage values (all 0..1 unless noted) per frame via Wound.set(**v):
  open      gap opening (1 = 3.5 mm half-width at the middle)
  stitches  float 0..N: stitches placed one by one from the top; the gap zips shut behind them
  out       float 0..N: stitches removed one by one from the top
  red       redness + puff halo    collagen  strands grown     vessels  vessel sprouts grown
  line      fresh closed line      scar      thin pink scar
"""
import bpy, bmesh, math, os, random
from mathutils import Vector as V, Matrix
from mathutils.bvhtree import BVHTree
from mathutils.geometry import barycentric_transform
import kwlib as L

HALF_W = 0.005           # open 10 mm at the centre (F1: the red must read at phone size)
DEPTH = 0.004            # about 4 mm deep
THREAD_R = 0.0005        # thread 1 mm thick
HOLE_C = 0.0045          # holes 4-5 mm from the seam
LINE_W = 0.0015          # stitched seam: 3 mm dark red line
SEAM_HW = 0.00125        # stitched: a 2.5 mm gap ...
LIP_W, LIP_H = 0.003, 0.001   # ... between two rounded lips 3 mm wide, raised 1 mm (stage 2: +2 mm wide, +1 mm high)

def _sstep(a, b, x):
    t = max(0.0, min(1.0, (x - a) / (b - a))); return t * t * (3 - 2 * t)

class Wound:
    def __init__(self, rt, ra, side='R', height=0.66, length=0.09, n_stitch=10, outer=0.25, seed=7):
        self.rt, self.ra, self.p = rt, ra, ra.p
        self.L = length; self.N = n_stitch; self._pts = {}; self.rnd = random.Random(seed)
        hg = getattr(self.p, 'hg', None)
        self.body = bpy.data.objects.get('HG_Body') if hg is None else (getattr(hg, 'body', None) or bpy.data.objects.get('HG_Body'))
        b = self.body
        # bare lower leg: hide the jeans, drop the HG 'under the trousers' mask on the legs
        for o in bpy.data.objects:
            if o.type == 'MESH' and any(k in o.name for k in ('Jeans', 'Trousers', 'Pants', 'Shorts')):
                o.hide_render = True; o.hide_viewport = True
                if o in self.p.parts: self.p.parts.remove(o)      # else the per-shot visibility pass shows them again
            if o.name.startswith('st_'): o.hide_render = True; o.hide_viewport = True     # studio stool (standing shots)
        for md in b.modifiers:
            if md.type == 'MASK' and md.name in ('mask_lower_long', 'mask_lower_short'): md.show_render = False; md.show_viewport = False
        rt.reset(self.p); rt.rig_at(self.p, (0, 0, 0), 0); bpy.context.view_layer.update()
        # the kit's 'kw_hide' mask also drops the skin under the jeans: give the lower legs back (knee to sneaker top)
        vg = b.vertex_groups.get('kw_hide')
        if vg is not None:
            kz = max(rt.bw(self.p, 'lowerleg01.' + s_).z for s_ in 'LR') + 0.08
            az = min(rt.bw(self.p, 'foot.' + s_).z for s_ in 'LR') + 0.03
            dg = bpy.context.evaluated_depsgraph_get(); arm = None
            for md in b.modifiers:
                if md.type == 'ARMATURE': arm = md
            # rest positions of the body roughly match world z for a standing pose at the origin
            idx = [v.index for v in b.data.vertices if az < (b.matrix_world @ v.co).z < kz]
            vg.remove(idx); bpy.context.view_layer.update()
            print(f'wound: unmasked {len(idx)} lower-leg verts ({az:.2f} < z < {kz:.2f})')
        self.bone = 'shin.' + side if 'shin.' + side in self.p.rig.data.bones else 'lowerleg01.' + side
        if getattr(b.data, 'has_custom_normals', False):
            with bpy.context.temp_override(object=b, active_object=b): bpy.ops.mesh.customdata_custom_splitnormals_clear()
            print('wound: cleared custom normals on', b.name)
        self._smooth()
        self._anchor(side, height, outer)
        self.c = L.coll('kw_wound')
        self._lights()
        self._shader()
        self._geo()
        self._bind_state()             # stitches / fibres / vessels are placed on (and Surface-Deform bound to) the stitched seam with its lips
        # F6: two copies of every stitch, each lying straight on the lips of its own state (calm / swollen), cross-faded by 'red'
        self._bind_state(1.0); self.stitches_b = self._build_stitches('b', dent=0.00015)
        self._bind_state(0.0); self.stitches = self._build_stitches()
        self.collagen = self._build_collagen(48)
        self.vessels = self._build_vessels(46)
        self.cells, self.specks = self._build_cells(45, 12)
        self.set()
        bpy.context.view_layer.update(); dg = bpy.context.evaluated_depsgraph_get(); me = self.body.evaluated_get(dg).data
        sf = me.attributes.get('sharp_face'); se = me.attributes.get('sharp_edge')
        print('wound: eval body', len(me.vertices), 'verts; sharp faces', sum(1 for d in sf.data if d.value) if sf else 0, 'sharp edges', sum(1 for d in se.data if d.value) if se else 0,
              'mods', [(m.name, m.type, m.show_render) for m in self.body.modifiers], 'custom', me.has_custom_normals, 'attrs', [a.name for a in me.attributes])

    def _smooth(self, level=2):
        """Catmull-Clark x2 on the whole body BEFORE anchoring (the anchor, the UV field and the stitches must all see the same smoothed skin;
        a linear split of the low-poly skin keeps its flat facets, which show as bands)"""
        gt = bpy.data.node_groups.new('kw_wound_smooth', 'GeometryNodeTree'); N = gt.nodes; Lk = gt.links.new; it = gt.interface
        it.new_socket('Geometry', in_out='INPUT', socket_type='NodeSocketGeometry'); it.new_socket('Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')
        gi = N.new('NodeGroupInput'); go = N.new('NodeGroupOutput')
        cc = N.new('GeometryNodeSubdivisionSurface'); cc.inputs['Level'].default_value = level; Lk(gi.outputs[0], cc.inputs['Mesh']); Lk(cc.outputs[0], go.inputs[0])
        md = self.body.modifiers.new('kw_smooth', 'NODES'); md.node_group = gt; bpy.context.view_layer.update()

    def _lights(self):
        """a soft key from behind-above-outer and a weak fill from the other side, aimed at the calf (the person rig lights the face)"""
        for nm, off, e, sz in (('kw_wound_key', self.Nn * 0.45 + self.Up * 0.4 + self.T * 0.55, 30.0, 0.4), ('kw_wound_fill', self.Nn * 0.6 - self.T * 0.55 - self.Up * 0.1, 7.0, 0.8)):
            ld = bpy.data.lights.new(nm, 'AREA'); ld.energy = e; ld.size = sz; ld.color = (1.0, 0.97, 0.93)
            lo = bpy.data.objects.new(nm, ld); self.c.objects.link(lo); lo.location = self.C + off
            lo.rotation_euler = (-off).to_track_quat('-Z', 'Y').to_euler()
            L.bone_parent(lo, self.p.rig, self.bone)

    # ------------------------------------------------------------------ anchor on the evaluated skin
    def _surface(self):
        dg = bpy.context.evaluated_depsgraph_get(); be = self.body.evaluated_get(dg); me = be.to_mesh()
        me.calc_loop_triangles(); uvl = me.uv_layers.active.data
        verts = [be.matrix_world @ v.co for v in me.vertices]
        tris = [tuple(t.vertices) for t in me.loop_triangles]
        self._tri_uv = [tuple(uvl[l].uv.copy() for l in t.loops) for t in me.loop_triangles]
        self._tri_v = tris; self._verts = verts
        self.bvh = BVHTree.FromPolygons(verts, tris)
        be.to_mesh_clear()

    def hit(self, p, n):
        """ray from p + n*5cm along -n onto the skin -> (point, normal, uv)"""
        loc, nrm, i, d = self.bvh.ray_cast(p + n * 0.15, -n, 0.2)
        if loc is None: return None
        a, b_, c = (self._verts[k] for k in self._tri_v[i]); ua, ub, uc = (V((u.x, u.y, 0)) for u in self._tri_uv[i])
        uv = barycentric_transform(loc, a, b_, c, ua, ub, uc)
        if nrm.dot(n) < 0: nrm = -nrm
        return loc, nrm, V((uv.x, uv.y))

    def _anchor(self, side, height, outer):
        self._surface()
        kn = self.rt.bw(self.p, 'lowerleg01.' + side); an = self.rt.bw(self.p, 'foot.' + side)
        up = (kn - an).normalized(); mid = an.lerp(kn, height)
        sx = -1 if side == 'R' else 1                      # the right leg's outer side is -x (front of the body is -y)
        n0 = V((sx * outer, 1, 0)); n0 = (n0 - up * n0.dot(up)).normalized()
        h = self.hit(mid, n0)
        if h is None:
            lo = [v for v in self._verts if v.z < kn.z]
            raise RuntimeError(f'wound: no skin hit on the calf; mid={tuple(mid)} knee={tuple(kn)} ankle={tuple(an)} verts below knee {len(lo)} of {len(self._verts)} nearest={self.bvh.find_nearest(mid)} nearest_out={self.bvh.find_nearest(mid + n0 * 0.15)} tris={len(self._tri_v)}')
        self.C, self.Nn, self.uv0 = h
        self.Up = (up - self.Nn * up.dot(self.Nn)).normalized(); self.T = self.Up.cross(self.Nn).normalized()   # T = across the cut
        # fit uv = uv0 + J (a, c) by least squares on a grid of hits, then invert
        rows = []
        for a in (-0.03, -0.015, 0.0, 0.015, 0.03):
            for cc in (-0.012, 0.0, 0.012):
                hh = self.hit(self.C + self.Up * a + self.T * cc, self.Nn)
                if hh: rows.append((a, cc, hh[2] - self.uv0))
        sa = sum(r[0] * r[0] for r in rows); sc = sum(r[1] * r[1] for r in rows); sac = sum(r[0] * r[1] for r in rows)
        M = Matrix(((sa, sac), (sac, sc))).inverted()
        bu = V((sum(r[0] * r[2].x for r in rows), sum(r[1] * r[2].x for r in rows))); bv = V((sum(r[0] * r[2].y for r in rows), sum(r[1] * r[2].y for r in rows)))
        ju = M @ bu; jv = M @ bv                       # u = ju.x a + ju.y c ; v = jv.x a + jv.y c
        J = Matrix(((ju.x, ju.y), (jv.x, jv.y))); self.Jinv = J.inverted()
        print(f'wound anchor C={tuple(round(x, 3) for x in self.C)} uv0={tuple(round(x, 4) for x in self.uv0)} '
              f'uv/m={J[0][0]:.3f},{J[0][1]:.3f},{J[1][0]:.3f},{J[1][1]:.3f} fit pts {len(rows)}')

    def surf(self, a, c, lift=0.0):
        """skin point at (a along, c across) in rest world, lifted along the normal"""
        h = self.hit(self.C + self.Up * a + self.T * c, self.Nn)
        if h is None: return self.C + self.Up * a + self.T * c + self.Nn * lift
        return h[0] + h[1] * lift

    def _field(self, nt, uv, Vv):
        """the wound mask as node fields (same math in the skin shader and in the geometry-nodes groove)"""
        N = nt.nodes; Lk = nt.links.new
        def mth(op, a, b=None, c=None, clamp=False):
            n = N.new('ShaderNodeMath'); n.operation = op; n.use_clamp = clamp
            for i, x in enumerate((a, b, c)):
                if x is None: continue
                if isinstance(x, (int, float)): n.inputs[i].default_value = x
                else: Lk(x, n.inputs[i])
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
        def sm(e0, e1, x):
            n = N.new('ShaderNodeMapRange'); n.interpolation_type = 'SMOOTHSTEP'
            for i_, e_ in ((1, e0), (2, e1)):
                if isinstance(e_, (int, float)): n.inputs[i_].default_value = e_
                else: Lk(e_, n.inputs[i_])
            if isinstance(x, (int, float)): n.inputs[0].default_value = x
            else: Lk(x, n.inputs[0])
            return n.outputs[0]
        def mth(op, a, b=None, c=None, clamp=False):
            n = N.new('ShaderNodeMath'); n.operation = op; n.use_clamp = clamp
            for i, x in enumerate((a, b, c)):
                if x is None: continue
                if isinstance(x, (int, float)): n.inputs[i].default_value = x
                else: Lk(x, n.inputs[i])
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
        def sm(e0, e1, x):     # smoothstep via map range
            n = N.new('ShaderNodeMapRange'); n.interpolation_type = 'SMOOTHSTEP'
            for i_, e_ in ((1, e0), (2, e1)):
                if isinstance(e_, (int, float)): n.inputs[i_].default_value = e_
                else: Lk(e_, n.inputs[i_])
            if isinstance(x, (int, float)): n.inputs[0].default_value = x
            else: Lk(x, n.inputs[0])
            return n.outputs[0]
        # UV -> (a, c) metres
        sub = N.new('ShaderNodeVectorMath'); sub.operation = 'SUBTRACT'; Lk(uv, sub.inputs[0]); sub.inputs[1].default_value = (self.uv0.x, self.uv0.y, 0)
        def row(r):
            d = N.new('ShaderNodeVectorMath'); d.operation = 'DOT_PRODUCT'; Lk(sub.outputs[0], d.inputs[0]); d.inputs[1].default_value = (r[0], r[1], 0); return d.outputs['Value']
        a = row(self.Jinv[0]); c = row(self.Jinv[1])
        hl = self.L / 2
        tt = mth('DIVIDE', a, hl)
        env = mth('SQRT', mth('MAXIMUM', mth('SUBTRACT', 1.0, mth('MULTIPLY', tt, tt)), 0.0))               # lens-shaped opening
        envs = mth('SUBTRACT', 1.0, sm(0.85, 1.12, mth('ABSOLUTE', tt)))                                      # soft line ends
        envh = mth('SUBTRACT', 1.0, sm(0.6, 1.45, mth('ABSOLUTE', tt)))                                       # halo ends
        # natural edge: 1D noise wobble across
        nz = N.new('ShaderNodeTexNoise'); nz.noise_dimensions = '1D'; nz.inputs['Scale'].default_value = 1.0; nz.inputs['Detail'].default_value = 3.0
        Lk(mth('MULTIPLY', a, 55.0), nz.inputs['W'])
        cw = mth('ADD', c, mth('MULTIPLY', mth('SUBTRACT', nz.outputs['Fac'], 0.5), 0.0011))
        ac = mth('ABSOLUTE', cw)
        # zip: stitch k (top = k 0) closes its stretch; closure(a) = clamp(stitches - k(a))
        ka = mth('SUBTRACT', mth('MULTIPLY', mth('DIVIDE', mth('SUBTRACT', hl, a), 2 * hl), float(self.N)), 0.5)
        clo = sm(0.0, 1.0, mth('ADD', mth('SUBTRACT', Vv['stitches'], ka), 0.5))
        oe = mth('MULTIPLY', Vv['open'], mth('SUBTRACT', 1.0, clo))
        cl = mth('MULTIPLY', mth('MULTIPLY', Vv['open'], clo), mth('SUBTRACT', 1.0, Vv['level']))              # stitched + not yet levelled
        w = mth('MULTIPLY', mth('ADD', mth('MULTIPLY', oe, HALF_W), mth('MULTIPLY', cl, SEAM_HW)), env)
        g = mth('MULTIPLY', mth('ADD', mth('DIVIDE', mth('SUBTRACT', w, ac), 0.00045), 0.5, clamp=True), mth('DIVIDE', w, 0.00025, clamp=True))
        g = mth('MINIMUM', g, 1.0)
        deep = mth('MULTIPLY', g, sm(0.0, 1.0, mth('DIVIDE', mth('SUBTRACT', mth('MULTIPLY', w, 0.6), ac), 0.0008)))
        rim = mth('MULTIPLY', mth('MULTIPLY', mth('EXPONENT', mth('MULTIPLY', -1.0, mth('POWER', mth('DIVIDE', mth('SUBTRACT', ac, w), 0.0013), 2.0))), envs), mth('MAXIMUM', oe, mth('MULTIPLY', Vv['line'], 0.3)))
        rim = mth('MULTIPLY', rim, mth('SUBTRACT', 1.0, g))
        lwh = mth('MULTIPLY', Vv['lwid'], LINE_W) if 'lwid' in Vv else LINE_W                                  # H2: the levelled pink band narrows to the 2 mm scar (shader only)
        line = mth('MULTIPLY', mth('MULTIPLY', mth('MULTIPLY', Vv['line'], Vv['level']), mth('SUBTRACT', 1.0, sm(mth('SUBTRACT', lwh, 0.0004) if 'lwid' in Vv else LINE_W - 0.0004, mth('ADD', lwh, 0.0002) if 'lwid' in Vv else LINE_W + 0.0002, ac))), envs)
        depth = mth('MULTIPLY', mth('MULTIPLY', DEPTH, mth('SQRT', mth('MAXIMUM', mth('SUBTRACT', 1.0, mth('POWER', mth('DIVIDE', ac, mth('MAXIMUM', w, 1e-5)), 2.0)), 0.0))), mth('DIVIDE', w, HALF_W, clamp=True))
        depth = mth('MULTIPLY', depth, mth('DIVIDE', w, 0.0004, clamp=True))
        lw = mth('ADD', LIP_W, mth('MULTIPLY', Vv['red'], 0.002)); lh = mth('ADD', LIP_H, mth('MULTIPLY', Vv['red'], 0.001))
        lipd = mth('SUBTRACT', ac, w)
        lip = mth('EXPONENT', mth('MULTIPLY', -1.0, mth('POWER', mth('DIVIDE', mth('SUBTRACT', lipd, mth('MULTIPLY', lw, 0.3)), mth('MULTIPLY', lw, 0.42)), 2.0)))
        lip = mth('MULTIPLY', mth('MULTIPLY', lip, sm(-0.0005, 0.0002, lipd)), mth('MULTIPLY', mth('MULTIPLY', cl, envs), lh))
        halo = mth('MULTIPLY', mth('MULTIPLY', Vv['red'], mth('EXPONENT', mth('MULTIPLY', -1.0, mth('POWER', mth('DIVIDE', c, 0.011), 2.0)))), envh)
        scar = mth('MULTIPLY', mth('MULTIPLY', Vv['scar'], mth('SUBTRACT', 1.0, sm(0.0005, 0.0013, ac))), envs)
        # pores + fine furrows in metric (a, c) space around the wound (fade out 10 cm away)
        loc = N.new('ShaderNodeCombineXYZ'); Lk(a, loc.inputs[0]); Lk(c, loc.inputs[1])
        # F5: fine pores + criss-cross micro-creases (bump only; faded by camera distance in the shader) + mottling noise
        vor = N.new('ShaderNodeTexVoronoi'); vor.feature = 'F1'; vor.inputs['Scale'].default_value = 1.0 / 0.00035; vor.inputs['Randomness'].default_value = 1.0
        Lk(loc.outputs[0], vor.inputs['Vector'])
        sep_ = N.new('FunctionNodeSeparateColor' if nt.bl_idname == 'GeometryNodeTree' else 'ShaderNodeSeparateColor'); Lk(vor.outputs['Color'], sep_.inputs[0])
        rad_ = mth('ADD', 0.16, mth('MULTIPLY', sep_.outputs[1], 0.14))                                 # G1: pore dots 0.15-0.25 mm, irregular
        pore = mth('MULTIPLY', mth('SUBTRACT', 1.0, sm(mth('MULTIPLY', rad_, 0.45), rad_, vor.outputs['Distance'])), sm(0.18, 0.32, sep_.outputs[0]))   # ~8 per mm2
        def crease(ang, per, seed):
            ca, sa = math.cos(math.radians(ang)), math.sin(math.radians(ang))
            vv = N.new('ShaderNodeCombineXYZ'); Lk(mth('ADD', mth('MULTIPLY', a, ca), mth('MULTIPLY', c, sa)), vv.inputs[0]); Lk(mth('SUBTRACT', mth('MULTIPLY', c, ca), mth('MULTIPLY', a, sa)), vv.inputs[1]); vv.inputs[2].default_value = seed
            wv = N.new('ShaderNodeTexWave'); wv.wave_type = 'BANDS'; wv.bands_direction = 'X'; wv.inputs['Scale'].default_value = 1.0 / per
            wv.inputs['Distortion'].default_value = 2.5; wv.inputs['Detail'].default_value = 2.0; wv.inputs['Detail Scale'].default_value = 1.5
            Lk(vv.outputs[0], wv.inputs['Vector']); return mth('SUBTRACT', 1.0, sm(0.0, 0.12, wv.outputs['Fac']))
        cr = mth('MAXIMUM', crease(38.0, 0.0011, 0.3), crease(-44.0, 0.0013, 0.7))
        fn = N.new('ShaderNodeTexNoise'); fn.inputs['Scale'].default_value = 1.0 / 0.0012; fn.inputs['Detail'].default_value = 6.0; Lk(loc.outputs[0], fn.inputs['Vector'])
        dist = mth('SQRT', mth('ADD', mth('MULTIPLY', a, a), mth('MULTIPLY', c, c)))
        near = mth('SUBTRACT', 1.0, sm(0.07, 0.12, dist))
        micro = mth('MULTIPLY', near, mth('ADD', mth('ADD', mth('MULTIPLY', pore, -0.0001), mth('MULTIPLY', cr, -0.00007)), mth('MULTIPLY', fn.outputs['Fac'], 0.00006)))   # G1: bump x2
        micro = mth('MULTIPLY', micro, float(os.environ.get('KW_WD_MICRO', '1.0')))
        return dict(lip=lip, cl=cl, ac=ac, w=w, envs=envs, g=g, deep=deep, rim=rim, line=line, halo=halo, scar=scar, loc=loc, fn=fn, near=near, micro=micro, depth=depth, a=a, c=c, pore=pore, cr=cr,
                    _mth=mth, _mixc=mixc, _mulc=mulc, _sm=sm)

    # ------------------------------------------------------------------ shader
    def _shader(self):
        m = self.body.active_material if self.body.active_material.name.startswith('.Human') else next(s.material for s in self.body.material_slots if s.material and s.material.name.startswith('.Human'))
        self.mat = m; nt = m.node_tree; N = nt.nodes; Lk = nt.links.new
        bsdf = next(n for n in N if n.type == 'BSDF_PRINCIPLED'); out = next(n for n in N if n.type == 'OUTPUT_MATERIAL' and n.is_active_output)
        print('wound: HG bsdf', [(i.name, (i.links[0].from_node.name if i.links else (tuple(i.default_value) if hasattr(i.default_value, '__len__') else i.default_value))) for i in bsdf.inputs if i.enabled and (i.links or i.name in ('Subsurface Weight', 'Subsurface Scale', 'Coat Weight', 'Sheen Weight', 'Specular IOR Level', 'Roughness', 'Metallic'))])
        def val(name, v=0.0):
            n = N.new('ShaderNodeValue'); n.name = n.label = 'kw_w_' + name; n.outputs[0].default_value = v; return n.outputs[0]
        self.V = {k: val(k, 0.0) for k in ('open', 'stitches', 'red', 'line', 'scar', 'level')}
        self.V.update({k: val(k, 0.0) for k in ('pink', 'holes', 'hout', 'dots', 'blood')})
        self.V['lwid'] = val('lwid', 1.0)
        tc = N.new('ShaderNodeTexCoord')
        F = self._field(nt, tc.outputs['UV'], self.V)
        mth, mixc, mulc, sm = F['_mth'], F['_mixc'], F['_mulc'], F['_sm']
        g, deep, rim, line, halo, scar, loc, fn, near, micro = (F[k] for k in ('g', 'deep', 'rim', 'line', 'halo', 'scar', 'loc', 'fn', 'near', 'micro'))
        # colour
        base_link = bsdf.inputs['Base Color'].links[0]; base = base_link.from_socket
        cd = N.new('ShaderNodeCameraData'); mf = mth('SUBTRACT', 1.0, sm(0.12, 0.3, cd.outputs['View Distance']))     # 1 in the macro, 0 at the wide view
        mfn = mth('MULTIPLY', mf, near)
        # G1: in the macro the HG colour map is magnified into smeared streaks -> a flat tan skin tone carries the procedural detail instead
        base = mixc(base, (0.47, 0.27, 0.155), mth('MULTIPLY', mfn, 0.92))
        nl = bsdf.inputs['Normal'].links
        while nl and nl[0].from_node.type == 'REROUTE': nl = nl[0].from_node.inputs[0].links
        if nl and nl[0].from_node.type == 'NORMAL_MAP':
            nm_ = nl[0].from_node; s0 = nm_.inputs['Strength'].default_value; Lk(mth('MULTIPLY', s0, mth('SUBTRACT', 1.0, mth('MULTIPLY', mfn, 0.9))), nm_.inputs['Strength'])
        elif nl: print('wound: HG normal input from', nl[0].from_node.type, '(not faded)')
        cvar = mixc(base, mulc(base, (0.93, 0.86, 0.84)), mth('MULTIPLY', mth('MULTIPLY', fn.outputs['Fac'], near), 0.6))
        mo = N.new('ShaderNodeTexNoise'); mo.inputs['Scale'].default_value = 1.0 / 0.006; mo.inputs['Detail'].default_value = 2.0; Lk(loc.outputs[0], mo.inputs['Vector'])
        mo2 = N.new('ShaderNodeTexNoise'); mo2.noise_dimensions = '4D'; mo2.inputs['Scale'].default_value = 1.0 / 0.0045; mo2.inputs['Detail'].default_value = 2.0; mo2.inputs['W'].default_value = 3.7; Lk(loc.outputs[0], mo2.inputs['Vector'])
        cvar = mixc(cvar, mulc(base, (1.06, 0.95, 0.95)), mth('MULTIPLY', sm(0.5, 0.68, mo.outputs['Fac']), mfn))       # mottling +-6 % red
        cvar = mixc(cvar, mulc(base, (1.02, 1.03, 0.90)), mth('MULTIPLY', sm(0.5, 0.68, mo2.outputs['Fac']), mfn))      # ... and yellow
        fv = N.new('ShaderNodeTexVoronoi'); fv.feature = 'F1'; fv.inputs['Scale'].default_value = 1.0 / 0.006; Lk(loc.outputs[0], fv.inputs['Vector'])
        fsep = N.new('ShaderNodeSeparateColor'); Lk(fv.outputs['Color'], fsep.inputs[0])
        frk = mth('MULTIPLY', mth('SUBTRACT', 1.0, sm(0.04, 0.085, fv.outputs['Distance'])), sm(0.80, 0.82, fsep.outputs[0]))   # a few 0.5-1 mm freckles
        cvar = mixc(cvar, mulc(base, (0.70, 0.56, 0.46)), mth('MULTIPLY', frk, mth('MULTIPLY', mfn, 0.8)))
        cvar = mixc(cvar, mulc(base, (0.86, 0.84, 0.84)), mth('MULTIPLY', F['cr'], mth('MULTIPLY', mfn, 0.7)))       # fine crease lines, slightly darker
        cvar = mixc(cvar, mulc(base, (0.62, 0.58, 0.58)), mth('MULTIPLY', F['pore'], mfn))                              # pore dots 35-40 % darker
        c1 = mixc(cvar, mulc(base, (1.0, 0.40, 0.36)), mth('MULTIPLY', halo, 0.6))
        ac_, w_ = F['ac'], F['w']
        rimc = mth('MULTIPLY', mth('EXPONENT', mth('MULTIPLY', -1.0, mth('POWER', mth('DIVIDE', mth('SUBTRACT', ac_, w_), 0.00045), 2.0))), mth('MULTIPLY', F['envs'], self.V['open']))
        rimc = mth('MULTIPLY', rimc, mth('SUBTRACT', 1.0, mth('MULTIPLY', g, 0.6)))
        lipn = mth('DIVIDE', F['lip'], 0.001, clamp=True)
        # F2: the FULL width of both lips is raw saturated pink-red while inflamed (red), glossy; the halo flush fades out beyond
        lwc = mth('ADD', LIP_W, mth('MULTIPLY', self.V['red'], 0.002))
        ew = N.new('ShaderNodeTexNoise'); ew.noise_dimensions = '1D'; ew.inputs['Scale'].default_value = 1.0; ew.inputs['Detail'].default_value = 3.0
        Lk(mth('MULTIPLY', F['a'], 230.0), ew.inputs['W']); sgn_ = N.new('ShaderNodeTexNoise'); sgn_.noise_dimensions = '1D'; sgn_.inputs['Scale'].default_value = 1.0; sgn_.inputs['W'].default_value = 0.0
        Lk(mth('ADD', mth('MULTIPLY', F['a'], 230.0), mth('MULTIPLY', mth('GREATER_THAN', F['c'], 0.0), 17.0)), sgn_.inputs['W'])
        acb = mth('ADD', ac_, mth('MULTIPLY', mth('SUBTRACT', sgn_.outputs['Fac'], 0.5), 0.0012))                    # G2: lip outer edge wavy +-0.5 mm
        band = mth('MULTIPLY', mth('SUBTRACT', 1.0, sm(mth('ADD', w_, mth('MULTIPLY', lwc, 0.86)), mth('ADD', w_, mth('MULTIPLY', lwc, 1.0)), acb)), mth('MULTIPLY', F['cl'], F['envs']))
        bandr = mth('MULTIPLY', band, self.V['red'])
        fo = mth('SUBTRACT', acb, mth('ADD', w_, lwc))                                                             # flush 4-6 mm on the skin beyond the lip
        flush = mth('MULTIPLY', mth('EXPONENT', mth('MULTIPLY', -1.0, mth('POWER', mth('DIVIDE', mth('MAXIMUM', fo, 0.0), 0.0035), 2.0))), mth('MULTIPLY', mth('MULTIPLY', F['cl'], F['envs']), self.V['red']))
        c1 = mixc(c1, mulc(base, (0.95, 0.36, 0.32)), mth('MULTIPLY', flush, 0.8))
        tl_ = sm(0.0, 1.0, mth('DIVIDE', mth('SUBTRACT', ac_, w_), mth('MULTIPLY', lwc, 0.5)))                       # 0 at the gap .. 1 on the crest
        bl_ = N.new('ShaderNodeTexNoise'); bl_.inputs['Scale'].default_value = 1.0 / 0.002; bl_.inputs['Detail'].default_value = 2.0; Lk(loc.outputs[0], bl_.inputs['Vector'])
        GAPC, CRC = (0.105, 0.0040, 0.0080), (0.250, 0.0090, 0.0140)                                               # sRGB ~(120,25,35) -> (175,45,55) before the view transform
        lipc = mixc(mixc(tuple(x * 0.88 for x in GAPC), tuple(x * 0.88 for x in CRC), tl_), mixc(tuple(x * 1.12 for x in GAPC), tuple(x * 1.12 for x in CRC), tl_), sm(0.3, 0.7, bl_.outputs['Fac']))
        c1 = mixc(c1, lipc, mth('MULTIPLY', bandr, 0.97))
        c1 = mixc(c1, mulc(base, (0.97, 0.72, 0.68)), mth('MULTIPLY', mth('MULTIPLY', lipn, 0.5), mth('SUBTRACT', 1.0, bandr)))   # fresh lips a little pinker than skin
        c2 = mixc(c1, (0.24, 0.02, 0.025), mth('MULTIPLY', rimc, 0.8))
        # blood trickle: one thin wet line a few cm down from the lower tip (only while the cut is open, before stitching)
        hl_ = self.L / 2; aa_, cc_ = F['a'], F['c']
        tr_t = mth('DIVIDE', mth('SUBTRACT', mth('MULTIPLY', -1.0, aa_), hl_ * 0.92), 0.034)                 # 0 at the tip .. 1 at the end
        wob = N.new('ShaderNodeTexNoise'); wob.noise_dimensions = '1D'; wob.inputs['Scale'].default_value = 1.0; wob.inputs['Detail'].default_value = 2.0
        Lk(mth('MULTIPLY', aa_, 60.0), wob.inputs['W'])
        tc_ = mth('ADD', mth('MULTIPLY', mth('SUBTRACT', wob.outputs['Fac'], 0.5), mth('MULTIPLY', mth('MAXIMUM', tr_t, 0.0), 0.0035)), 0.0)
        trw = mth('ADD', 0.00055, mth('MULTIPLY', mth('MINIMUM', mth('MAXIMUM', tr_t, 0.0), 1.0), -0.0002))      # half width 0.55 -> 0.35 mm
        drop = mth('MULTIPLY', 0.00035, sm(0.85, 1.0, tr_t))                                                    # a slightly fatter drop at the end
        trw = mth('ADD', trw, drop)
        blood = mth('MULTIPLY', mth('SUBTRACT', 1.0, sm(trw, mth('ADD', trw, 0.0002), mth('ABSOLUTE', mth('SUBTRACT', cc_, tc_)))),
                    mth('MULTIPLY', mth('GREATER_THAN', tr_t, -0.05), mth('LESS_THAN', tr_t, 1.0)))
        blood = mth('MULTIPLY', blood, self.V['blood'])
        c2 = mixc(c2, (0.20, 0.006, 0.012), mth('MULTIPLY', blood, 0.95))
        c3 = mixc(c2, (0.50, 0.11, 0.13), mth('MULTIPLY', scar, 0.9))
        lc = mixc((0.12, 0.006, 0.01), (0.56, 0.14, 0.16), self.V['pink'])
        c4 = mixc(c3, lc, mth('MULTIPLY', line, 0.95))
        # stitch holes: small dark dimples while a stitch sits in them, pink dots after (stage 5)
        sp = self.L / self.N; a_, c_ = F['a'], F['c']
        kf = mth('SUBTRACT', mth('DIVIDE', mth('SUBTRACT', self.L / 2, a_), sp), 0.5); kr = mth('ROUND', kf)
        da = mth('MULTIPLY', mth('SUBTRACT', kf, kr), sp); dc = mth('SUBTRACT', mth('ABSOLUTE', c_), HOLE_C)
        H = mth('EXPONENT', mth('MULTIPLY', -1.0 / (0.00055 ** 2), mth('ADD', mth('MULTIPLY', da, da), mth('MULTIPLY', dc, dc))))
        H = mth('MULTIPLY', H, mth('MULTIPLY', mth('GREATER_THAN', kr, -0.5), mth('LESS_THAN', kr, self.N - 0.5)))
        Hs = mth('MULTIPLY', mth('MULTIPLY', H, mth('LESS_THAN', kr, mth('SUBTRACT', self.V['holes'], 0.5))), mth('GREATER_THAN', kr, mth('SUBTRACT', self.V['hout'], 0.5)))
        Hd = mth('MULTIPLY', H, self.V['dots'])
        c4 = mixc(c4, (0.10, 0.015, 0.015), mth('MULTIPLY', Hs, 0.9))
        c4 = mixc(c4, (0.48, 0.10, 0.12), mth('MULTIPLY', Hd, 0.85))
        wn = N.new('ShaderNodeTexNoise'); wn.inputs['Scale'].default_value = 1.0 / 0.0015; wn.inputs['Detail'].default_value = 4.0; Lk(loc.outputs[0], wn.inputs['Vector'])
        dpt = mth('DIVIDE', F['depth'], DEPTH, clamp=True)
        inner = mixc((0.30, 0.018, 0.024), (0.22, 0.01, 0.016), wn.outputs['Fac'])
        inner = mixc(inner, (0.045, 0.0, 0.004), mth('POWER', dpt, 0.6))
        c5 = mixc(c4, inner, g)
        Lk(c5, bsdf.inputs['Base Color'])
        # HG skin scatters 1 cm (SSS weight 1): it washes thin wound detail out to pale pink, so cut the scatter on the wound marks
        mk = mth('MAXIMUM', mth('MAXIMUM', mth('MULTIPLY', g, 2.0), mth('MAXIMUM', mth('MAXIMUM', rimc, mth('MULTIPLY', bandr, 0.8)), blood)), mth('MAXIMUM', mth('MAXIMUM', line, scar), mth('MAXIMUM', Hs, Hd)))
        if not bsdf.inputs['Subsurface Weight'].links:
            Lk(mth('SUBTRACT', bsdf.inputs['Subsurface Weight'].default_value, mth('MULTIPLY', mth('MINIMUM', mth('MULTIPLY', mk, 1.5), 1.0), 0.97)), bsdf.inputs['Subsurface Weight'])
        # wet interior: low roughness, more specular
        rl = bsdf.inputs['Roughness'].links; r0 = rl[0].from_socket if rl else None
        if r0 is not None:
            rn = N.new('ShaderNodeMix'); rn.data_type = 'FLOAT'; rn.clamp_factor = True; Lk(mth('MAXIMUM', g, mth('MAXIMUM', mth('MULTIPLY', lipn, 0.75), mth('MULTIPLY', bandr, 0.9))), rn.inputs[0]); Lk(rn.outputs[0], bsdf.inputs['Roughness'])
            gn_ = N.new('ShaderNodeTexNoise'); gn_.inputs['Scale'].default_value = 1.0 / 0.0011; gn_.inputs['Detail'].default_value = 3.0; Lk(loc.outputs[0], gn_.inputs['Vector'])
            Lk(mth('ADD', 0.07, mth('MULTIPLY', sm(0.42, 0.62, gn_.outputs['Fac']), 0.38)), rn.inputs[3])          # G2: wet glints broken into small spots
            rh = N.new('ShaderNodeMix'); rh.data_type = 'FLOAT'; rh.clamp_factor = True; Lk(mth('MULTIPLY', halo, 0.5), rh.inputs[0]); Lk(r0, rh.inputs[2]); rh.inputs[3].default_value = 0.28
            Lk(rh.outputs[0], rn.inputs[2])        # inflamed skin is a little shinier
        micro = mth('MULTIPLY', mth('MULTIPLY', micro, mf), mth('SUBTRACT', 1.0, bandr))   # detail only in the macro; not on the raw lips (they read as fabric)
        # height -> Displacement (material displacement method = BUMP)
        hgt = mth('ADD', mth('ADD', mth('MULTIPLY', g, -0.0002), mth('MULTIPLY', deep, -0.0002)),
                  mth('ADD', mth('ADD', mth('MULTIPLY', halo, 0.0002), mth('MULTIPLY', mth('MULTIPLY', rim, self.V['open']), 0.00025)), mth('ADD', mth('ADD', mth('MULTIPLY', scar, 0.00012), micro), mth('MULTIPLY', Hs, -0.0004))))
        wb = N.new('ShaderNodeTexNoise'); wb.inputs['Scale'].default_value = 1.0 / 0.0007; wb.inputs['Detail'].default_value = 5.0; wb.inputs['Roughness'].default_value = 0.6; Lk(loc.outputs[0], wb.inputs['Vector'])
        hgt = mth('ADD', hgt, mth('MULTIPLY', mth('MULTIPLY', g, wb.outputs['Fac']), 0.00035))      # glistening lumpy tissue inside the cut
        hgt = mth('ADD', hgt, mth('MULTIPLY', blood, 0.00012))
        lu = N.new('ShaderNodeTexNoise'); lu.noise_dimensions = '4D'; lu.inputs['Scale'].default_value = 1.0 / 0.0016; lu.inputs['Detail'].default_value = 1.5; lu.inputs['W'].default_value = 1.3; Lk(loc.outputs[0], lu.inputs['Vector'])
        gr = N.new('ShaderNodeTexNoise'); gr.inputs['Scale'].default_value = 1.0 / 0.0003; gr.inputs['Detail'].default_value = 2.0; Lk(loc.outputs[0], gr.inputs['Vector'])
        lump = mth('ADD', mth('MULTIPLY', mth('SUBTRACT', lu.outputs['Fac'], 0.5), 0.0009), mth('MULTIPLY', mth('SUBTRACT', gr.outputs['Fac'], 0.5), 0.00012))
        hgt = mth('ADD', hgt, mth('MULTIPLY', lump, mth('MULTIPLY', bandr, mf)))                                  # G2: lumpy raw lips (1-2 mm lumps, 0.3 mm grain)
        dn = N.new('ShaderNodeDisplacement'); dn.inputs['Midlevel'].default_value = 0.0; dn.inputs['Scale'].default_value = 1.0; Lk(hgt, dn.inputs['Height'])
        if not os.environ.get('KW_WD_NOBUMP'): Lk(dn.outputs[0], out.inputs['Displacement'])
        try: m.displacement_method = 'BUMP'
        except Exception: m.cycles.displacement_method = 'BUMP'

    # ------------------------------------------------------------------ geometry: subdivided calf patch + groove + puff (end of the stack)
    def _geo(self, level=4):
        gt = bpy.data.node_groups.new('kw_wound_geo', 'GeometryNodeTree'); N = gt.nodes; Lk = gt.links.new
        it = gt.interface; it.new_socket('Geometry', in_out='INPUT', socket_type='NodeSocketGeometry'); it.new_socket('Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')
        for k in ('open', 'stitches', 'red', 'line', 'scar', 'level'): it.new_socket(k, in_out='INPUT', socket_type='NodeSocketFloat')
        gi = N.new('NodeGroupInput'); go = N.new('NodeGroupOutput')
        uv = N.new('GeometryNodeInputNamedAttribute'); uv.data_type = 'FLOAT_VECTOR'; uv.inputs['Name'].default_value = 'UVMap'
        Vv = {k: gi.outputs[k] for k in ('open', 'stitches', 'red', 'line', 'scar', 'level')}
        F = self._field(gt, uv.outputs['Attribute'], Vv); mth = F['_mth']
        # selection: faces of the patch (|a| < 7 cm, |c| < 3.5 cm), evaluated on the face domain
        selp = mth('MULTIPLY', mth('LESS_THAN', mth('ABSOLUTE', F['a']), 0.062), mth('LESS_THAN', mth('ABSOLUTE', F['c']), 0.026))
        sep = N.new('GeometryNodeSeparateGeometry'); sep.domain = 'FACE'; Lk(gi.outputs['Geometry'], sep.inputs['Geometry']); Lk(selp, sep.inputs['Selection'])
        sub = N.new('GeometryNodeSubdivideMesh'); sub.inputs['Level'].default_value = level; Lk(sep.outputs['Selection'], sub.inputs['Mesh'])
        # groove down the normal + puff up (after subdivision the fields are re-evaluated on the new points)
        h = mth('SUBTRACT', mth('ADD', mth('ADD', mth('MULTIPLY', F['halo'], 0.0003), F['lip']), mth('MULTIPLY', F['rim'], 0.0004)), F['depth'])
        nrm = N.new('GeometryNodeInputNormal'); off = N.new('ShaderNodeVectorMath'); off.operation = 'SCALE'; Lk(nrm.outputs[0], off.inputs[0]); Lk(h, off.inputs['Scale'])
        sp = N.new('GeometryNodeSetPosition'); Lk(sub.outputs[0], sp.inputs['Geometry']); Lk(off.outputs[0], sp.inputs['Offset'])
        j = N.new('GeometryNodeJoinGeometry'); Lk(sp.outputs[0], j.inputs[0]); Lk(sep.outputs['Inverted'], j.inputs[0])
        # NO merge-by-distance here: its vertex count changes with the pose and breaks the stitches' Surface Deform bind
        ss = N.new('GeometryNodeSetShadeSmooth'); Lk(j.outputs[0], ss.inputs['Geometry']); ss.domain = 'FACE'
        se = N.new('GeometryNodeSetShadeSmooth'); Lk(ss.outputs[0], se.inputs['Geometry']); se.domain = 'EDGE'
        Lk(se.outputs[0], go.inputs['Geometry'])
        md = self.body.modifiers.new('kw_wound', 'NODES'); md.node_group = gt
        if os.environ.get('KW_WD_NOGEO'): md.show_render = md.show_viewport = False
        self.gmod = md; self.gid = {k: it.items_tree[k].identifier for k in ('open', 'stitches', 'red', 'line', 'scar', 'level')}

    # ------------------------------------------------------------------ curves
    def _curve(self, name, pts, r, mat, radii=None):
        cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = r; cu.bevel_resolution = 3; cu.use_fill_caps = True
        sp = cu.splines.new('BEZIER'); sp.bezier_points.add(len(pts) - 1)
        for bp, q in zip(sp.bezier_points, pts): bp.co = q; bp.handle_left_type = bp.handle_right_type = 'AUTO'
        if radii:
            for bp, rr in zip(sp.bezier_points, radii): bp.radius = rr
        cu.bevel_factor_mapping_end = 'SPLINE'
        o = bpy.data.objects.new(name, cu); self.c.objects.link(o); o.data.materials.append(mat)
        self._pts[o.name] = [V(q) for q in pts]; return o

    def _grow_mat(self, mt):
        """mask the material where the per-vertex 'kw_t' (0 at the start of a strand) is past the object's 'kw_grow'"""
        nt = mt.node_tree; N = nt.nodes; Lk = nt.links.new; out = N['Material Output']; b = N['Principled BSDF']
        at = N.new('ShaderNodeAttribute'); at.attribute_type = 'GEOMETRY'; at.attribute_name = 'kw_t'
        ag = N.new('ShaderNodeAttribute'); ag.attribute_type = 'OBJECT'; ag.attribute_name = 'kw_grow'
        cmp = N.new('ShaderNodeMath'); cmp.operation = 'LESS_THAN'; Lk(ag.outputs['Fac'], cmp.inputs[0]); Lk(at.outputs['Fac'], cmp.inputs[1])
        av = N.new('ShaderNodeAttribute'); av.attribute_type = 'OBJECT'; av.attribute_name = 'kw_vis'
        inv = N.new('ShaderNodeMath'); inv.operation = 'SUBTRACT'; inv.inputs[0].default_value = 1.0; Lk(av.outputs['Fac'], inv.inputs[1])
        mxx = N.new('ShaderNodeMath'); mxx.operation = 'MAXIMUM'; mxx.use_clamp = True; Lk(cmp.outputs[0], mxx.inputs[0]); Lk(inv.outputs[0], mxx.inputs[1]); cmp = mxx
        tr = N.new('ShaderNodeBsdfTransparent'); mx = N.new('ShaderNodeMixShader')
        Lk(cmp.outputs[0], mx.inputs[0]); Lk(b.outputs[0], mx.inputs[1]); Lk(tr.outputs[0], mx.inputs[2]); Lk(mx.outputs[0], out.inputs['Surface'])

    def _skin(self, objs, name, falloff=4.0):
        """bake curves / spheres into ONE world-space mesh glued to the posed skin with a Surface Deform (a rigid bone parent drifts mm off the skin)"""
        bpy.context.view_layer.update(); dg = bpy.context.evaluated_depsgraph_get()
        bm = bmesh.new(); tl = bm.verts.layers.float.new('kw_t'); mats = []
        for o in objs:
            oe = o.evaluated_get(dg); me = bpy.data.meshes.new_from_object(oe); me.transform(o.matrix_world)
            n0 = len(bm.verts); bm.from_mesh(me); bm.verts.ensure_lookup_table()
            pts = self._pts.get(o.name); new = bm.verts[n0:]
            if pts:
                seg = [(pts[i], pts[i + 1]) for i in range(len(pts) - 1)]; ln = [(b_ - a_).length for a_, b_ in seg]; tot = sum(ln) or 1.0
                for v in new:
                    best = (1e9, 0.0); acc = 0.0
                    for (a_, b_), l_ in zip(seg, ln):
                        d_ = b_ - a_; u = max(0.0, min(1.0, (v.co - a_).dot(d_) / max(l_ * l_, 1e-12))); dd = (a_ + d_ * u - v.co).length
                        if dd < best[0]: best = (dd, (acc + u * l_) / tot)
                        acc += l_
                    v[tl] = best[1]
            else:
                for v in new: v[tl] = 0.999
            for m_ in o.data.materials:
                if m_ not in mats: mats.append(m_)
            bpy.data.meshes.remove(me)
        me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
        for m_ in mats: me.materials.append(m_)
        for pl in me.polygons: pl.use_smooth = True
        ob = bpy.data.objects.new(name, me); self.c.objects.link(ob); ob['kw_grow'] = 1.0; ob['kw_vis'] = 1.0
        for o in objs:
            d_ = o.data; bpy.data.objects.remove(o)
            if d_ is not None and d_.users == 0:
                (bpy.data.curves if isinstance(d_, bpy.types.Curve) else bpy.data.meshes).remove(d_)
        md = ob.modifiers.new('kw_skin', 'SURFACE_DEFORM'); md.target = self.body; md.falloff = falloff
        bpy.context.view_layer.update()
        with bpy.context.temp_override(object=ob, active_object=ob, selected_objects=[ob]):
            bpy.ops.object.surfacedeform_bind(modifier=md.name)
        if not md.is_bound: print(f'wound: WARNING surface deform not bound for {name}')
        return ob

    def _bind_state(self, red=0.0):
        for k, v in dict(open=1.0, stitches=float(self.N) + 1.0, red=red, line=0.0, scar=0.0, level=0.0).items(): self.gmod[self.gid[k]] = v
        self.body.update_tag(); bpy.context.view_layer.update(); self._surface()

    def _build_stitches(self, tag='', dent=0.0):
        self.rnd = random.Random(11)                                   # identical stitches in both copies
        mt = bpy.data.materials.new('kw_suture' + tag); mt.use_nodes = True; b = mt.node_tree.nodes['Principled BSDF']
        b.inputs['Base Color'].default_value = (0.86, 0.86, 0.84, 1); b.inputs['Roughness'].default_value = 0.55   # G5: pure white
        ntm = mt.node_tree; tcm = ntm.nodes.new('ShaderNodeTexCoord'); wvm = ntm.nodes.new('ShaderNodeTexWave'); wvm.bands_direction = 'DIAGONAL'; wvm.inputs['Scale'].default_value = 1.0 / 0.0009
        ntm.links.new(tcm.outputs['Object'], wvm.inputs['Vector']); bpm = ntm.nodes.new('ShaderNodeBump'); bpm.inputs['Strength'].default_value = 0.25; bpm.inputs['Distance'].default_value = 0.00005
        ntm.links.new(wvm.outputs['Fac'], bpm.inputs['Height']); ntm.links.new(bpm.outputs['Normal'], b.inputs['Normal'])          # faint twist
        self._grow_mat(mt)
        hl = self.L / 2; out = []; sp = self.L / self.N
        for k in range(self.N):
            a = hl - (k + 0.5) * sp; cw = HOLE_C; tw = 0.0          # ends exactly in the shader's puncture dimples
            tr = 0.0003                                                 # white cord 0.6 mm thick
            # straight across, resting on the two lips (upper hull of the skin profile), then dipping into the holes
            M = 17; us = [-1 + 2 * i / (M - 1) for i in range(M)]; hits = [self.surf(a + tw * cw * u, cw * u, 0.0) for u in us]
            hh = [(q - self.C).dot(self.Nn) for q in hits]; inn = [i for i, u in enumerate(us) if abs(u) <= 0.8]
            hull = []
            for i in inn:                                               # upper convex hull (monotone chain) in (c, h)
                while len(hull) >= 2 and ((us[hull[-1]] - us[hull[-2]]) * (hh[i] - hh[hull[-2]]) - (hh[hull[-1]] - hh[hull[-2]]) * (us[i] - us[hull[-2]])) >= 0: hull.pop()
                hull.append(i)
            def hull_h(u):
                for x, y in zip(hull, hull[1:]):
                    if us[x] <= u <= us[y]: f = (u - us[x]) / max(us[y] - us[x], 1e-9); return hh[x] + (hh[y] - hh[x]) * f
                return hh[hull[0]] if u < 0 else hh[hull[-1]]
            prof = []
            for i, u in enumerate(us):
                e = abs(u)
                if e <= 0.8: prof.append(hits[i] + self.Nn * (hull_h(u) - hh[i] + tr * 1.0 - dent))
                else: prof.append(hits[i] + self.Nn * (tr * 1.0 - dent * (1 - (e - 0.8) / 0.2) - (tr + 0.0009) * ((e - 0.8) / 0.2) ** 2))   # sinks into the puncture
            loop = self._curve(f'kw_stitch{tag}_{k}', prof, tr, mt)
            # small knot just inside the LEFT hole (-c) + two ~3 mm tails at slightly uneven angles, lying on the skin
            kp = prof[2] + self.Nn * (tr * 0.4)                         # on the thread at u = -0.75 (left side)
            knot = L.sphere(f'kw_knot{tag}_{k}', tr * 1.5, kp, mt, self.c, seg=12, rings=8)
            tails = []
            for nm, ang, ln in (('a', math.radians(self.rnd.uniform(25, 72)), self.rnd.uniform(0.0021, 0.0039)),        # G5: +-25 deg, +-30 % per knot
                                ('b', -math.radians(self.rnd.uniform(55, 103)), self.rnd.uniform(0.0020, 0.0037))):
                da_, dc_ = math.sin(ang) * ln, -math.cos(ang) * ln
                ka, kc = a - tw * cw * 0.75, -cw * 0.75
                tails.append(self._curve(f'kw_tail{tag}_{k}{nm}', [kp, self.surf(ka + da_ * 0.5, kc + dc_ * 0.5, tr * 1.05), self.surf(ka + da_, kc + dc_, tr * 0.95)], tr * 0.85, mt))
            t1, t2 = tails
            out.append(self._skin([loop, knot, t1, t2], f'kw_stitch{tag}_{k}', falloff=float(os.environ.get('KW_WD_FALL', '4.0'))))
        return out

    def _strand_mat(self, kind, col, rough, emit, col2=None):
        mt = bpy.data.materials.new('kw_' + kind); mt.use_nodes = True; nt = mt.node_tree; b = nt.nodes['Principled BSDF']
        b.inputs['Roughness'].default_value = rough; b.inputs['Emission Strength'].default_value = emit
        b.inputs['Coat Weight'].default_value = 0.5; b.inputs['Coat Roughness'].default_value = 0.08        # wet
        mx = nt.nodes.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.inputs[6].default_value = (*col, 1); mx.inputs[7].default_value = (*(col2 or col), 1)
        vn = nt.nodes.new('ShaderNodeValue'); vn.name = 'kw_mix'; vn.outputs[0].default_value = 0.0; nt.links.new(vn.outputs[0], mx.inputs[0])
        col_out = mx.outputs[2]
        if kind == 'collagen':                                                       # G3: a little more contrast between strands
            oi = nt.nodes.new('ShaderNodeObjectInfo'); mr = nt.nodes.new('ShaderNodeMapRange'); nt.links.new(oi.outputs['Random'], mr.inputs[0]); mr.inputs[3].default_value = 0.72; mr.inputs[4].default_value = 1.12
            ml = nt.nodes.new('ShaderNodeMix'); ml.data_type = 'RGBA'; ml.blend_type = 'MULTIPLY'; ml.inputs[0].default_value = 1.0
            cc = nt.nodes.new('ShaderNodeCombineColor'); [nt.links.new(mr.outputs[0], cc.inputs[i]) for i in range(3)]
            nt.links.new(mx.outputs[2], ml.inputs[6]); nt.links.new(cc.outputs[0], ml.inputs[7]); col_out = ml.outputs[2]
        nt.links.new(col_out, b.inputs['Base Color']); nt.links.new(col_out, b.inputs['Emission Color'])
        self._grow_mat(mt); return mt

    def _gap_pt(self, a, c, lift):
        """a point inside the stitched gap: 'lift' above the gap floor at (a, c)"""
        return self.surf(a, c, lift)

    def _gap_w(self, a):
        t = a / (self.L / 2); return SEAM_HW * math.sqrt(max(0.0, 1 - t * t))

    def _build_collagen(self, n):
        """stage 3: a warm-yellow braided ribbon of fibres (0.3 mm) filling the gap, woven, overlapping, laid from the top down"""
        self.col_mat = mt = self._strand_mat('collagen', (0.92, 0.62, 0.12), 0.35, 0.06, col2=(0.80, 0.30, 0.32)); hl = self.L / 2; out = []
        for k in range(n):
            a0 = hl * 0.9 - (k + self.rnd.uniform(0.0, 1.0)) / n * 1.8 * hl * 0.82       # top first (+a = toward the knee)
            span = self.rnd.uniform(0.022, 0.034); P = self.rnd.uniform(0.003, 0.0045); ph = self.rnd.uniform(0, 2 * math.pi)
            layer = k % 3; r = self.rnd.uniform(0.000125, 0.000175); pts = []
            M = max(8, int(span / 0.0007))
            for i in range(M + 1):
                a = a0 - span * i / M
                if a < -hl * 0.9: break
                w = self._gap_w(a); cc = 0.95 * w * math.sin(2 * math.pi * (a - a0) / P + ph)
                pts.append(self._gap_pt(a, cc, r + 0.00012 + layer * 0.00026 + 0.00008 * math.cos(2 * math.pi * (a - a0) / P + ph)))
            if len(pts) < 4: continue
            o = self._curve(f'kw_collagen_{k}', pts, r, mt)
            out.append(self._skin([o], f'kw_collagen_{k}'))
        return out

    def _build_vessels(self, n):
        """stage 4: glossy red capillaries (0.25 mm -> 0.08 mm) sprouting from both lips, forking, meeting in a net over the yellow band"""
        self.ves_mat = mt = self._strand_mat('vessels', (0.56, 0.006, 0.003), 0.22, 0.2); hl = self.L / 2; out = []; r = 0.0003
        per = n // 2; meets = [hl * 0.86 - (j + self.rnd.uniform(0.25, 0.75)) / per * 1.72 * hl for j in range(per)]
        top = 0.00125                                                                  # above the gap floor: over the collagen band
        for k in range(n):
            side = 1 if k % 2 == 0 else -1; j = k // 2; am = meets[j]
            a0 = am + self.rnd.uniform(-0.003, 0.003); wl = self._gap_w(a0)
            c0 = side * (wl + self.rnd.uniform(0.0013, 0.0022)); pts = []; rad = []
            for i in range(7):
                u = i / 6; a = a0 + (am - a0) * u + 0.0004 * math.sin(u * math.pi) * side; cc = c0 * (1 - u) + side * 0.00005 * u
                w = self._gap_w(a); inside = abs(cc) < w + 0.0002
                pts.append(self._gap_pt(a, cc, top if inside else r * 0.9)); rad.append(1.0 - 0.75 * u)
            grp = [self._curve(f'kw_vessel_{k}', pts, r, mt, rad)]
            for f in range(self.rnd.randint(1, 2)):                                    # forks to the neighbouring meeting points (the net)
                jj = min(per - 1, max(0, j + (1 if f == 0 else -1))); i0 = self.rnd.randint(1, 2); u0 = i0 / 6
                q = [pts[i0]]; qr = [rad[i0] * 0.8]; fa, fc = a0 + (am - a0) * u0, c0 * (1 - u0)
                for i in range(1, 5):
                    v = i / 4; a = fa + (meets[jj] - fa) * 0.45 * v; cc = fc * (1 - v) + side * 0.00005 * v
                    w = self._gap_w(a); inside = abs(cc) < w + 0.0002
                    q.append(self._gap_pt(a, cc, top * 1.05 if inside else r * 0.8)); qr.append(rad[i0] * 0.8 * (1 - 0.65 * v))
                grp.append(self._curve(f'kw_vessel_{k}f{f}', q, r, mt, qr))
            out.append(self._skin(grp, f'kw_vessel_{k}'))
        return out

    def _build_cells(self, n, ns):
        """B4: pale white blood cells drifting in from both sides onto the lips / along the gap; grey-green germ specks that sink away"""
        mc = bpy.data.materials.new('kw_cell'); mc.use_nodes = True; b = mc.node_tree.nodes['Principled BSDF']
        nt_ = mc.node_tree; lw_ = nt_.nodes.new('ShaderNodeLayerWeight'); lw_.inputs['Blend'].default_value = 0.35
        mx_ = nt_.nodes.new('ShaderNodeMix'); mx_.data_type = 'RGBA'; mx_.inputs[6].default_value = (0.66, 0.62, 0.60, 1); mx_.inputs[7].default_value = (0.95, 0.93, 0.89, 1)
        nt_.links.new(lw_.outputs['Facing'], mx_.inputs[0]); nt_.links.new(mx_.outputs[2], b.inputs['Base Color'])          # a faint darker core
        b.inputs['Roughness'].default_value = 0.35
        b.inputs['Subsurface Weight'].default_value = 0.6; b.inputs['Subsurface Radius'].default_value = (0.4, 0.35, 0.3); b.inputs['Subsurface Scale'].default_value = 0.0004
        b.inputs['Transmission Weight'].default_value = 0.25; b.inputs['Coat Weight'].default_value = 0.4
        ms = bpy.data.materials.new('kw_speck'); ms.use_nodes = True; b = ms.node_tree.nodes['Principled BSDF']
        b.inputs['Base Color'].default_value = (0.25, 0.32, 0.20, 1); b.inputs['Roughness'].default_value = 0.6
        cells = []; specks = []
        for i in range(n):
            side = 1 if i % 2 == 0 else -1; a = self.rnd.uniform(-0.028, 0.028); w = self._gap_w(a)
            ing = i % 3 == 0; c = side * (self.rnd.uniform(0.0, max(0.0, w - 0.0007)) if ing else w + self.rnd.uniform(0.0006, 0.0030))     # G4: on the red lips only
            r = self.rnd.uniform(0.0006, 0.00075)                   # F3: 1.2-1.5 mm, on the red lips and along the gap
            o = L.sphere(f'kw_cell_{i}', r, self.surf(a, c, r * 0.8 if not ing else r + 0.0003), mc, self.c, seg=18, rings=12)
            o.scale = (1.0, 1.0, 0.85); ob = self._skin([o], f'kw_cell_{i}'); ob['kw_side'] = side; cells.append(ob)
        for i in range(ns):
            a = self.rnd.uniform(-0.024, 0.024); w = self._gap_w(a); c = self.rnd.choice((-1, 1)) * (w + self.rnd.uniform(0.0, 0.0025)); r = self.rnd.uniform(0.00036, 0.00044)
            o = L.sphere(f'kw_speck_{i}', r, self.surf(a, c, r * 0.7 if abs(c) > w else r + 0.0003), ms, self.c, seg=10, rings=6)
            specks.append(self._skin([o], f'kw_speck_{i}'))
        return cells, specks

    def set(self, open=0.0, stitches=0.0, out=0.0, red=0.0, collagen=0.0, vessels=0.0, line=None, scar=0.0, pink=0.0, dots=0.0, blood=None, level=0.0, cpink=0.0, cells=0.0, specks=-1.0, cinch=None, show=True, lwid=1.0):
        self.V['lwid'].default_value = lwid
        if line is None: line = min(1.0, max(0.0, stitches - 0.0) / max(1, self.N)) if stitches > 0 else 0.0
        for k, v in dict(open=open if show else 0.0, stitches=stitches if cinch is None else cinch, red=red if show else 0.0, line=line if show else 0.0, scar=scar if show else 0.0, level=level).items():
            self.V[k].default_value = v; self.gmod[self.gid[k]] = float(v)
        self.body.update_tag(); self.gmod.show_viewport = self.gmod.show_viewport     # LESSON: modifier socket values set from Python are not seen by the depsgraph without a tag
        if blood is None: blood = 0.0          # policy: no blood anywhere (YouTube first-frame rule)
        self.V['blood'].default_value = blood if show else 0.0
        self.V['pink'].default_value = pink; self.V['dots'].default_value = dots if show else 0.0
        self.V['holes'].default_value = min(stitches, self.N) if show else 0.0; self.V['hout'].default_value = out
        fr = _sstep(0.3, 0.7, red)
        for k, (o, ob_) in enumerate(zip(self.stitches, self.stitches_b)):
            o['kw_vis'] = 1.0 - fr; ob_['kw_vis'] = fr
            on = show and stitches > k + 0.05
            grow = min(1.0, max(0.0, (stitches - k) / 0.6)); so = min(1.0, max(0.0, out - k))     # out: pulled 2 cm sideways, then gone
            for x in (o, ob_):
                x.hide_render = not on or so >= 0.999 or x['kw_vis'] <= 0.001; x['kw_grow'] = 1.001 if grow >= 1 else grow
                x.location = self.T * (0.02 * so * so) + self.Nn * (0.004 * so); x.update_tag()
        if os.environ.get('KW_WD_PROBE'):
            bpy.context.view_layer.update(); dg = bpy.context.evaluated_depsgraph_get()
            for o in self.stitches[:3]:
                me = o.evaluated_get(dg).data; ps = [o.matrix_world @ v.co for v in me.vertices]
                ext = [max(p_[i] for p_ in ps) - min(p_[i] for p_ in ps) for i in range(3)]
                print(f'wound probe {o.name} n={len(ps)} ext_mm={[round(e * 1000, 1) for e in ext]} bound={o.modifiers[0].is_bound} body_n={len(self.body.evaluated_get(dg).data.vertices)}')
        self.col_mat.node_tree.nodes['kw_mix'].outputs[0].default_value = cpink
        n_ = len(self.cells)
        for i, o in enumerate(self.cells):              # cells: 0 = outside the frame (8 mm out), 1 = settled; >1 fades them away again
            k = min(1.0, max(0.0, cells * 1.5 - i / n_ * 0.5)); k = k * k * (3 - 2 * k)
            sk = min(1.0, max(0.0, (cells - 1.0) * 1.6 - (i % 5) / 5 * 0.6)) if cells > 1.0 else 0.0     # >1: they sink into the skin one after another (no pop)
            o.hide_render = not show or k <= 0.0 or sk >= 0.999; o.location = self.T * (o['kw_side'] * 0.008 * (1 - k)) - self.Nn * (0.0018 * sk); o.update_tag()
        for i, o in enumerate(self.specks):             # specks: -1 = hidden (sunk), -1..0 rising, 0 = there, 1 = all sunk away (one after the other)
            k = min(1.0, max(0.0, specks * 1.6 - i / len(self.specks) * 0.6)) if specks >= 0 else min(1.0, -specks)   # -1..0: they rise out of the skin
            o.hide_render = not show or specks <= -0.999 or k >= 0.999; o.location = -self.Nn * (0.0011 * k); o.update_tag()
        for grp, val in ((self.collagen, collagen), (self.vessels, vessels)):
            for i, o in enumerate(grp):
                kk = min(1.0, max(0.0, val * 1.6 - (i / max(1, len(grp))) * 0.6))
                o.hide_render = not (show and kk > 0.01); o['kw_grow'] = 1.001 if kk >= 1 else kk; o.update_tag()
