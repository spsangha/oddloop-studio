"""kwfx - builds and animates every KW.fx item, x-ray bodies, macro sets, graphic stations, spray and held props."""
import bpy, math, random, os
from mathutils import Vector as V, Matrix
import kwkit as KW
# cast v1.1: kwprops item root in its carrier's frame (can: z = axis, centred; spoon: z = handle -> bowl, x = width, y = thickness)
CARRY_OFF = {'cup': Matrix.Translation((0, 0, -0.055)),
             'tweezers': Matrix(((0, 1, 0, 0), (0, 0, 1, 0), (1, 0, 0, 0.03), (0, 0, 0, 1))),
             'penlight': Matrix(((0, 1, 0, 0), (0, 0, 1, 0), (1, 0, 0, 0.0), (0, 0, 0, 1)))}
import kwlib as L
import kwbody as B
ramp, bump, pop = KW.ramp, KW.bump, KW.pop
LABEL_COL = {'red': (1.0, 0.06, 0.04), 'yellow': (1.0, 0.82, 0.02), 'white': (1.0, 1.0, 1.0), 'green': (0.1, 0.9, 0.2), 'blue': (0.1, 0.45, 1.0)}
STATIONS = {'skin_block': V((100, 0, 1.0)), 'gauge': V((110, 0, 1.0)), 'calendar': V((120, 0, 1.5)), 'scan': V((130, 0, 1.2)), 'earth': V((140, 0, 1.5))}
PROP_LIGHT = {'skin_block': (0.45, 0.8), 'gauge': (0.3, 0.5), 'calendar': (0.4, 0.5), 'scan': (0.4, 0.25), 'earth': (0.5, 0.55)}
RX90 = Matrix.Rotation(math.radians(-90), 3, 'X')

class Builder:
    def __init__(self, rt):
        self.rt = rt; self.ep = rt.ep; self.G = rt.G; self.bodies = {}; self.macros = {}; self.stations = {}; self.items = {}
        self.fx_coll = {}; self.props = {}; self.rnd = random.Random(5)

    # ================================================================== build
    def build_all(self):
        rt, ep = self.rt, self.ep
        need_body = set()
        for s in ep.shots:
            if s.xray is not None: need_body.add(s.xray)
            if isinstance(s.cam, KW.Cam) and s.cam.kind == 'xray': need_body.add(s.cam.subj)
            for f in s.fx:
                if f.kind in ('flow', 'pressure', 'glow', 'seal', 'swell_air', 'crack_line') or (f.kind == 'arrow' and f.o.get('path')):
                    need_body.add(f.o['person'])
        for a in need_body:
            self.bodies[a] = B.Body(rt, rt.actors[a])
        for m in ep.macros:
            self.macros[m] = B.Macro(rt, m, m.idx); m.obj = self.macros[m]
        kinds = set()
        for s in ep.shots:
            for f in s.fx:
                if f.is_prop(): kinds.add('gauge' if f.kind == 'gauge' else f.kind)
        for k in kinds: self._station(k)
        for si, s in enumerate(ep.shots):
            for fi, f in enumerate(s.fx):
                c = L.coll(f'kw_fx_{si:02d}_{fi}_{f.kind}'); c.hide_render = True; self.fx_coll[f] = c
                try: self.items[f] = self._build_fx(s, f, c)
                except Exception as e:
                    import traceback; traceback.print_exc(); print('fx build failed', s.name, f, repr(e)); self.items[f] = None
        self._build_spray(); self._build_props()
        for ra in rt.actors.values(): rt.reset(ra.p); rt.rig_at(ra.p, (0, 0, 0), 0)
        bpy.context.view_layer.update()
        print('fx built', len(self.items), 'bodies', len(self.bodies), 'macros', len(self.macros), 'stations', list(self.stations))

    def _station(self, kind):
        G = self.G; c = L.coll('kw_station_' + kind); c.hide_render = True; O = STATIONS[kind]; st = {'coll': c, 'origin': O}
        wall = L.mat('kw_st_wall', (0.03, 0.2, 0.3), 0.7)
        if self.rt.K and hasattr(self.rt.K, 'wall_material'):
            try: wall = self.rt.K.wall_material()
            except Exception: pass
        if kind == 'skin_block':
            st['obj'] = G.SkinBlock(O, c, size=0.5) if G else None
        elif kind == 'calendar':
            st['obj'] = G.Calendar(O, c) if G else None
            L.box('kw_cal_wall', (6, 0.02, 6), O + V((0, 0.04, 0)), wall, c, 0)
        elif kind == 'earth':
            import kwearth; st['obj'] = kwearth.EarthStation(O, c)
        elif kind == 'scan':
            st['obj'] = G.ScanMonitor(O, c, width=0.5) if G else None
            L.box('kw_scan_wall', (6, 0.02, 6), O + V((0, 1.2, 0.3)), wall, c, 0)
            if st['obj'] is not None: st['head_mat'] = self._head_scan(st['obj'])
        elif kind == 'gauge':
            st['obj'] = G.Gauge(O, c, radius=0.06) if G else None
            st['label'] = G.Label3D(' ', O + V((0, -0.02, 0.105)), c, size=0.06, color=LABEL_COL['red']) if G else None
            L.box('kw_g_wall', (6, 0.02, 6), O + V((0, 0.3, 0)), L.mat('kw_g_wallm', (0.05, 0.12, 0.3), 0.6), c, 0)
        self.stations[kind] = st

    def _head_scan(self, mon):
        """procedural axial head CT at orbit level; the problem is on the image right (= patient's left, radiology convention)"""
        G = self.G; m, t, out = G._tree('KW CT | head scan, procedural')
        uv = t.nodes.new('ShaderNodeTexCoord').outputs['UV']
        heal_n = t.nodes.new('ShaderNodeValue'); heal = heal_n.outputs[0]; pw_n = t.nodes.new('ShaderNodeValue'); pw_n.outputs[0].default_value = 1.0
        grain = t.nodes.new('ShaderNodeTexNoise'); grain.inputs['Scale'].default_value = 88; grain.inputs['Detail'].default_value = 2
        G._socket(t, grain.inputs['Vector'], G._vmath(t, 'MULTIPLY', uv, (1.3, 1, 0))); noise = grain.outputs['Fac']
        sep = t.nodes.new('ShaderNodeSeparateXYZ'); G._socket(t, sep.inputs[0], uv); u, v = sep.outputs['X'], sep.outputs['Y']
        rows = G._math(t, 'GREATER_THAN', G._math(t, 'FRACT', G._math(t, 'MULTIPLY', v, 98)), .83)
        color = G._mix(t, rows, (.012, .019, .030, 1), (.017, .028, .046, 1))
        color = G._mix(t, G._math(t, 'GREATER_THAN', u, .735), color, (.022, .043, .068, 1))
        soft = G._ramp(t, noise, ((.23, (.15, .165, .175, 1)), (.85, (.42, .444, .46, 1))))
        brain = G._ramp(t, noise, ((.2, (.25, .27, .29, 1)), (.8, (.45, .47, .49, 1))))
        fat = G._ramp(t, noise, ((.24, (.06, .07, .08, 1)), (.78, (.14, .15, .16, 1))))
        bone = G._ramp(t, noise, ((.15, (.62, .65, .68, 1)), (.84, (.95, .96, .98, 1))))
        eye = G._ramp(t, noise, ((.2, (.3, .32, .34, 1)), (.8, (.42, .44, .46, 1))))
        air = (.006, .010, .016, 1)
        def sh(c, cx, cz, rx, rz, mat, f=.06): return G._mix(t, G._ellipse_alpha(t, uv, cx, cz, rx, rz, f), c, mat)
        X0 = .415
        color = sh(color, X0, .47, .27, .41, soft, .03)
        color = sh(color, X0, .44, .245, .355, bone, .03)
        color = sh(color, X0, .43, .222, .325, brain, .05)
        color = sh(color, X0, .70, .07, .10, soft, .1)               # nasal / ethmoid block
        # swollen left eyelid (image right), grows with the problem (1 - heal)
        lid = G._math(t, 'MULTIPLY', G._ellipse_alpha(t, uv, .535, .835, .085, .065, .2), G._math(t, 'SUBTRACT', 1, G._math(t, 'MULTIPLY', heal, .8)))
        color = G._mix(t, lid, color, soft)
        for cx in (.295, .535):
            color = sh(color, cx, .72, .085, .13, bone, .05)            # orbit rim
            color = sh(color, cx, .72, .074, .115, fat, .07)            # orbital fat
            color = sh(color, cx, .75, .052, .08, eye, .06)             # eyeball
        color = sh(color, X0, .72, .03, .085, air, .12)                 # ethmoid air cells
        for dx in (-.012, .012):
            color = sh(color, X0 + dx, .72, .0035, .08, bone, .3)       # thin septa
        color = sh(color, X0, .87, .028, .045, soft, .1)                # nose
        color = sh(color, X0, .87, .01, .03, air, .2)
        # the fracture: a gap in the thin inner wall of the left socket + air pockets around the eye
        gap = G._math(t, 'MULTIPLY', G._ellipse_alpha(t, uv, .455, .72, .016, .03, .2), G._math(t, 'SUBTRACT', 1, heal))
        color = G._mix(t, gap, color, air)
        op = G._math(t, 'POWER', G._math(t, 'SUBTRACT', 1, heal), .72)
        for cx, cz, rx, rz in ((.53, .855, .03, .022), (.575, .815, .02, .03), (.488, .84, .016, .018), (.6, .735, .012, .03), (.47, .66, .012, .02), (.555, .885, .014, .012)):
            color = G._mix(t, G._math(t, 'MULTIPLY', G._ellipse_alpha(t, uv, cx, cz, rx, rz, .15), op), color, air)
        color = G._mix(t, .035, color, (.135, .22, .31, 1))
        G._emit(t, out, color, pw_n.outputs[0])
        self._scan_heal_node = heal_n; self._scan_pow_node = pw_n
        return m

    def _set_scan_kind(self, st, kind, title):
        mon = st['obj']
        if mon is None: return
        if kind == 'head':
            if mon.screen.data.materials[0] is not st['head_mat']: mon.screen.data.materials[0] = st['head_mat']
            sw, sh = mon._screen_dims; old = mon._marker_xy; new = ((.535 - .5) * sw, mon._sz + (.80 - .5) * sh)
            mon._marker.location = (new[0] - old[0], 0, new[1] - old[1]); mon._marker.scale = (1.5, 1, 1.5)
        else:
            mon._marker.location = (0, 0, 0); mon._marker.scale = (1, 1, 1)
            if not hasattr(mon, '_orig_mat'): mon._orig_mat = mon.screen.data.materials[0]
            if mon.screen.data.materials[0] is not mon._orig_mat: mon.screen.data.materials[0] = mon._orig_mat
        if mon._ui_objs[0].data.body != title: mon._ui_objs[0].data.body = title

    @staticmethod
    def _gauge_text(o):
        """dial printing from fx.gauge(low=, high=, title=); the kit defaults keep the old 'NORMAL SNEEZE' / '20x' dial"""
        low = o.get('low'); high = o.get('high')
        return dict(low='NORMAL\nSNEEZE' if low in (None, 'NORMAL') else low, high='20x' if high is None else high, title=o.get('title') or 'PRESSURE')

    def _pt(self, p):
        """world point from a tuple or (fx.item, 'point name')"""
        if isinstance(p, (tuple, list)) and len(p) == 2 and isinstance(p[0], KW.FX):
            it = self.items.get(p[0]); return it['prop'].point(p[1]) if it and it.get('prop') else V((0, 0, 0))
        return V(p)

    def _build_fx(self, s, f, c):
        G = self.G; o = f.o; k = f.kind; rt = self.rt
        if k == 'gauge' and o.get('place') != 'station':
            if not G: return None
            g = G.Gauge(V((0, 0, 0)), c, radius=0.06, **self._gauge_text(o))
            lab = G.Label3D(o['label'], V((0, 0, 0)), c, size=0.06, color=LABEL_COL['red']) if o.get('label') else None
            if o.get('title'):
                pass
            return dict(gauge=g, label=lab)
        if k == 'wound':
            ws = self.__dict__.setdefault('wounds', {}); a = o['person']
            if a not in ws:
                import kwwound; ra = rt.actors[a]; w = kwwound.Wound(rt, ra, side=o.get('side', 'R')); ws[a] = w
                bn = 'lowerleg01.' + o.get('side', 'R'); M = rt.wmat(ra.p, bn)
                ra.parts['calf_' + o.get('side', 'R').lower()] = (bn, M.inverted() @ w.C, (M.to_3x3().inverted() @ w.Nn).normalized())
            return dict(w=ws[a])
        if k == 'item':
            import kwprops
            pr = kwprops.make(o['item'], c, rt.K, **o['params']); base = V(o['pos'])
            if o.get('on') is not None:
                host = self.items.get(o['on'])
                if host and host.get('prop'):
                    bpy.context.view_layer.update(); hp = host['prop']; nm = o.get('point') or ('floor' if 'floor' in hp.pts else 'top')
                    base = hp.point(nm) + base
            pr.root.location = base; pr.root.rotation_euler = (0, math.radians(o.get('tilt', 0.0)), math.radians(o['rz'])); bpy.context.view_layer.update()
            if o['keys']: pr.set(**_key_vals(o['keys'], 0.0))
            return dict(prop=pr)
        if k == 'counter':
            if not G: return dict(label=None)
            return dict(label=G.Label3D(_counter_text(o, o['v1']), V((0, 0, 0)), c, size=0.06, color=LABEL_COL[o['color']]))
        if k == 'beam':
            bpy.context.view_layer.update(); P0 = self._pt(o['origin']); P1 = self._pt(o['target'])
            ld = bpy.data.lights.new(f'kw_beam_{id(f)}', 'SPOT'); ld.color = o['color']; ld.shadow_soft_size = 0.002; ld.spot_blend = 0.35
            lo = bpy.data.objects.new(ld.name, ld); c.objects.link(lo)
            r0 = 0.005; r1 = max(r0 * 1.2, o['width'] / 2); n = 32; vs = []; fs = []
            for z, r in ((0.0, r0), (1.0, r1)):
                for i in range(n): a = 2 * math.pi * i / n; vs.append((r * math.cos(a), r * math.sin(a), z))
            for i in range(n): fs.append((i, (i + 1) % n, n + (i + 1) % n, n + i))
            me = bpy.data.meshes.new(f'kw_beamcone_{id(f)}'); me.from_pydata(vs, [], fs); co = bpy.data.objects.new(me.name, me); c.objects.link(co); L.smooth(co)
            m = bpy.data.materials.new(me.name); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear(); N = nt.nodes; Lk = nt.links.new
            out = N.new('ShaderNodeOutputMaterial'); em = N.new('ShaderNodeEmission'); em.inputs['Color'].default_value = (*o['color'], 1)
            tr = N.new('ShaderNodeBsdfTransparent'); lw = N.new('ShaderNodeLayerWeight'); lw.inputs['Blend'].default_value = 0.5
            tc = N.new('ShaderNodeTexCoord'); sep = N.new('ShaderNodeSeparateXYZ'); Lk(tc.outputs['Object'], sep.inputs[0])
            def mth(op, a, b):
                q = N.new('ShaderNodeMath'); q.operation = op
                for i_, v in enumerate((a, b)):
                    if isinstance(v, (int, float)): q.inputs[i_].default_value = v
                    else: Lk(v, q.inputs[i_])
                return q.outputs[0]
            edge = mth('POWER', mth('SUBTRACT', 1.0, lw.outputs['Facing']), 2.5)
            along = mth('SUBTRACT', 1.0, mth('MULTIPLY', sep.outputs['Z'], 0.55))
            fadev = N.new('ShaderNodeValue'); fadev.outputs[0].default_value = 0.0
            fac = mth('MULTIPLY', mth('MULTIPLY', edge, along), fadev.outputs[0])
            mx = N.new('ShaderNodeMixShader'); Lk(mth('MINIMUM', mth('MULTIPLY', fac, 0.8), 1.0), mx.inputs[0]); Lk(tr.outputs[0], mx.inputs[1]); Lk(em.outputs[0], mx.inputs[2]); Lk(mx.outputs[0], out.inputs[0])
            em.inputs['Strength'].default_value = 2.5 * o['strength']; co.data.materials.append(m)
            co.visible_shadow = False; co.visible_diffuse = False; co.visible_glossy = False
            return dict(light=lo, cone=co, fade=fadev, P0=P0, P1=P1)
        if k == 'flow_path':
            col = B.COLORS[o['color']]; m, em = L.glow(f'kw_flowp_{id(f)}', col, 9.0, 0.97); rnd = random.Random(len(self.items) + 7); parts = []
            for i in range(int(o['count'])):
                ob = L.ico(f'kw_flowp{i}', 1, (0, 0, 0), m, c, 2); ob.scale = (1e-5,) * 3
                parts.append((ob, rnd.random(), rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.random()))
            return dict(parts=parts, em=em, col=col, path=L.smooth_path([V(p) for p in o['points']], 5))
        if k == 'earth':
            st = self.stations['earth']; key = f'{s.name}'
            st['obj'].add_line(key, o['mode'], o['lon'], o['lat']); return dict(key=key)
        if k == 'label':
            if not G: return dict(label=None)
            return dict(label=G.Label3D(o['text'], V((0, 0, 0)), c, size=0.06, color=LABEL_COL[o['color']]))
        if k == 'arrow':
            pts = o.get('points')
            if o.get('path'):
                rt.pose_all(s, 0.0, canonical=True); body = self.bodies[o['person']]; pts = body.path_world(o['path'])
            if not pts or not G: return None
            ar = G.Arrow3D([V(p) for p in pts], c, LABEL_COL.get(o['color'], (1, 0.82, 0.02)), o['width']); return dict(arrow=ar)
        if k == 'bracket':
            if not G: return None
            if o.get('macro') is not None or (o.get('p0') is None and s.macro is not None):
                mm = self.macros[o.get('macro') or s.macro]; p0 = mm.HOLE + V((-0.1, -0.03, 0.105)); p1 = mm.HOLE + V((0.1, -0.03, 0.105))
            else: p0, p1 = V(o['p0']), V(o['p1'])
            br = G.Bracket(p0, p1, o['text'], c)
            for ob in br.root.children_recursive:
                for sl in getattr(ob, 'material_slots', []):
                    if sl.material and sl.material.node_tree:
                        for n in sl.material.node_tree.nodes:
                            if n.type == 'BSDF_PRINCIPLED': n.inputs['Base Color'].default_value = (1.0, 0.82, 0.02, 1); n.inputs['Emission Color'].default_value = (1.0, 0.8, 0.0, 1); n.inputs['Emission Strength'].default_value = 0.6
            return dict(bracket=br)
        if k == 'crackle':
            if not G: return None
            cr = G.Crackle(V((0, 0, 0)), c); cr.root.scale = (0.55,) * 3; return dict(crackle=cr)
        if k == 'flow':
            col = B.COLORS[o['color']]; m, em = L.glow(f'kw_flow_{id(f)}', col, 9.0, 0.97); rnd = random.Random(len(self.items) + 3); parts = []
            for i in range(int(o['count'])):
                ob = L.ico(f'kw_flow{i}', 1, (0, 0, 0), m, c, 2); ob.scale = (1e-5,) * 3
                parts.append((ob, rnd.random(), rnd.uniform(-1, 1), rnd.uniform(-1, 1), rnd.random()))
            return dict(parts=parts, em=em, col=col)
        if k == 'seal':
            body = self.bodies[o['person']]; P = body.points; m, em = L.glow(f'kw_seal_{id(f)}', (1.0, 0.05, 0.02), 10.0, 1.0); objs = []
            rt.reset(body.p); rt.rig_at(body.p, (0, 0, 0), 0); bpy.context.view_layer.update()
            for w in o['where']:
                pt, r = (P['nostril'] + V((0, -0.008, 0)), 0.012) if w == 'nose' else (P['lips'] + V((0, -0.008, 0)), 0.017)
                ring = L.prim('torus', 'kw_seal', m, c, major_radius=r, minor_radius=r * 0.22, location=pt, rotation=(math.radians(90), 0, 0)); L.smooth(ring); objs.append(ring)
                for a in (45, -45): objs.append(L.box('kw_sealx', (r * 1.5, r * 0.3, r * 0.3), pt, m, c, 0.001, (0, a, 0)))
            for ob in objs: L.bone_parent(ob, body.p.rig, 'head')
            return dict(objs=objs, base=[tuple(ob.scale) for ob in objs], em=em)
        if k == 'swell_air':
            body = self.bodies[o['person']]; P = body.points; rt.reset(body.p); rt.rig_at(body.p, (0, 0, 0), 0); bpy.context.view_layer.update()
            w = o['where']; bone = 'head'
            if w in ('eye_l', 'eye_r'): ctr = P['lidL' if w == 'eye_l' else 'lidR']; ext = (0.018, 0.008, 0.014)
            elif w in ('cheek_l', 'cheek_r'): ctr = P['maxL' if w == 'cheek_l' else 'maxR'] + V((0, -0.02, 0)); ext = (0.02, 0.01, 0.015)
            elif w in ('neck_l', 'neck_r'): ctr = rt.part_world(rt.actors[o['person']], w)[0] + V((0, 0.012, 0)); ext = (0.02, 0.012, 0.03); bone = 'neck02'
            else: ctr = rt.part_world(rt.actors[o['person']], 'chest')[0] + V((0, 0.02, 0)); ext = (0.08, 0.02, 0.06); bone = 'spine02'
            m, em = L.glow(f'kw_swair_{id(f)}', (0.75, 1.0, 1.0), 6.0, 0.9); rnd = random.Random(9); bub = []
            for i in range(26):
                p = ctr + V((rnd.uniform(-1, 1) * ext[0], rnd.uniform(-1, 1) * ext[1], rnd.uniform(-1, 1) * ext[2]))
                r = rnd.uniform(0.0018, 0.0042) * (ext[0] / 0.018) ** 0.5
                ob = L.sphere('kw_swair', 1, p, m, c, 12, 6); L.bone_parent(ob, body.p.rig, bone); bub.append((ob, r, rnd.random()))
            return dict(bub=bub)
        if k == 'crack_line':
            body = self.bodies[o['person']]; P = body.points; rt.reset(body.p); rt.rig_at(body.p, (0, 0, 0), 0); bpy.context.view_layer.update()
            pts = P['crackL' if o['where'] != 'eye_r' else 'crackR']
            m, em = L.emis(f'kw_crackl_{id(f)}', (1.0, 0.08, 0.03), 12.0)
            cu = L.tube('kw_crackline', pts, 0.0011, m, c, 2); cu.data.bevel_factor_mapping_end = 'SPLINE'; cu.data.bevel_factor_end = 0.0
            L.bone_parent(cu, body.p.rig, 'head'); return dict(curve=cu, em=em)
        return None

    def _build_spray(self):
        self.spray = None
        need = any(ac.kind in ('sneeze', 'cough') and ac.kw.get('spray', ac.kind == 'sneeze') for s in self.ep.shots for ps in s.cast.values() for _, q in ps.keys for ac in q.acts)
        if not need: return
        c = L.coll('kw_spray'); rnd = random.Random(7); dm = L.mat('kw_drop', (0.92, 0.97, 1.0), 0.02, trans=0.85, emit=(0.8, 0.95, 1.0), es=0.35); drops = []
        for i in range(260):
            o = L.ico(f'kw_drop{i}', 1, (0, 0, 0), dm, c, 2); o.scale = (1e-5,) * 3
            a = rnd.uniform(-0.55, 0.55); b = rnd.uniform(-0.4, 0.32); sp = rnd.uniform(1.4, 3.4)
            drops.append((o, V((math.sin(a), -math.cos(a) * math.cos(b), math.sin(b))) * sp, rnd.uniform(0.0012, 0.0042)))
        splats = []
        sm = L.mat('kw_splat', (0.95, 0.98, 1.0), 0.02, trans=1.0)
        for i in range(14):
            o = L.sphere(f'kw_splat{i}', 1, (0, 0, 0), sm, c, 16, 8); o.parent = self.rt.CAM; o.scale = (1e-5,) * 3
            splats.append((o, rnd.uniform(-0.045, 0.045), rnd.uniform(-0.07, 0.07), rnd.uniform(0.001, 0.003), rnd.uniform(0, 0.15)))   # LESSON: beads 1-3 mm
        self.spray = dict(drops=drops, splats=splats, coll=c)

    def _build_props(self):
        used = set()
        for s in self.ep.shots:
            for ps in s.cast.values():
                for _, q in ps.keys:
                    for h in (q.left, q.right):
                        if h is not None and h.prop: used.add(h.prop)
        c = L.coll('kw_props')
        for pr in used:
            self.props[pr] = self._make_prop(pr, c)
        # cast v1.1 grips: a kwprops item carried by the solved can / spoon (carrier mesh hidden from every ray)
        self.carried = {}
        for s_ in self.ep.shots:
            for ps in s_.cast.values():
                for _, q in ps.keys:
                    for h in (q.left, q.right):
                        if h is not None and h.prop in ('can', 'spoon') and h.pad and h.prop not in self.carried and h.prop in self.props:
                            import kwprops
                            it = kwprops.make(h.pad, c, **({'height': 0.11, 'r_bottom': 0.029, 'r_top': 0.037} if h.pad == 'cup' else {}))
                            car = self.props[h.prop]; it.root.parent = car; it.root.matrix_parent_inverse = Matrix.Identity(4)
                            it.root.matrix_basis = CARRY_OFF[h.pad]
                            self.carried[h.prop] = it

    def _make_prop(self, pr, c):
        if pr.startswith('g_'):      # cast v1.1 grips: a kwprops item, its root empty is what the hand carries
            import kwprops; it = kwprops.make(pr[2:], c); it.root.name = 'kw_' + pr; self.grip_items = getattr(self, 'grip_items', {}); self.grip_items[pr] = it
            return it.root
        if pr == 'tissue':
            me = bpy.data.meshes.new('kw_tissue'); vs = []; fs = []; N = 22; rnd = random.Random(3)
            for j in range(N + 1):
                for i in range(N + 1):
                    # 15 x 11 cm (fingertips tuck behind its side edges), cupped around the nose and mouth (y = into the face), top edge under the eyes
                    x = -0.075 + 0.15 * i / N; z = -0.075 + 0.11 * j / N; r2 = x * x + (z + 0.015) ** 2
                    y = 4.5 * x * x + 2.0 * (z + 0.015) ** 2 + 0.0018 * math.exp(-((x * 0.8 - z * 0.6 + 0.012) / 0.006) ** 2) + rnd.uniform(-0.0002, 0.0002)   # smooth paper + one faint diagonal crease (LESSON: sin ripples read as egg-crate)
                    z += -0.008 * (x / 0.075) ** 2 * (j / N) + 0.004 * (x / 0.075) ** 2 * (1 - j / N)   # soft paper: top edge droops at the sides, bottom flares
                    y += 0.0025 * math.sin(x * 21 + 1.3) * ((z + 0.015) / 0.06) ** 2                    # gentle low-frequency flutter at the free edges
                    vs.append((x, y - 0.012, z))
            for j in range(N):
                for i in range(N): fs.append((j * (N + 1) + i, j * (N + 1) + i + 1, (j + 1) * (N + 1) + i + 1, (j + 1) * (N + 1) + i))
            me.from_pydata(vs, [], fs); o = bpy.data.objects.new('kw_tissue', me); c.objects.link(o); L.smooth(o)
            o.data.materials.append(L.bumpy(L.mat('kw_tissue_m', (0.86, 0.87, 0.88), 0.85, sss=0.25), 14.0, 0.06, 2.0, dist=0.001))
            so = o.modifiers.new('s', 'SOLIDIFY'); so.thickness = 0.0015; ss = o.modifiers.new('ss', 'SUBSURF'); ss.levels = 1; ss.render_levels = 1
            return o
        if pr == 'pepper':   # Carolina Reaper: lumpy, wrinkled, tapering red pod with a curled tail + green stem (long axis = z, stem up)
            me = bpy.data.meshes.new('kw_pepper'); vs = []; fs = []; NU, NV = 28, 24; rnd = random.Random(7)
            for j in range(NV + 1):
                v = j / NV; z = -0.075 * v; cx = 0.012 * math.sin(v * 2.2) + 0.010 * max(0.0, v - 0.75) / 0.25 * (v ** 3)   # bends, tail flicks sideways
                rr = 0.017 * (math.sin(math.pi * min(1.0, 0.18 + v * 0.9)) ** 0.7) * (1 - 0.9 * v ** 3) + 0.0012
                for i in range(NU):
                    a = 2 * math.pi * i / NU
                    w = 1 + 0.13 * math.sin(4 * a + 6 * v) + 0.06 * math.sin(9 * a - 11 * v) + 0.05 * math.sin(17 * v + 3 * a)   # wrinkles
                    vs.append((cx + rr * w * math.cos(a), rr * w * math.sin(a) * 0.92, z))
            for j in range(NV):
                for i in range(NU): fs.append((j * NU + i, j * NU + (i + 1) % NU, (j + 1) * NU + (i + 1) % NU, (j + 1) * NU + i))
            me.from_pydata(vs, [], fs); o = bpy.data.objects.new('kw_pepper', me); c.objects.link(o); L.smooth(o)
            o.data.materials.append(L.mat('kw_pepper_m', (0.50, 0.012, 0.006), 0.28, coat=0.6))
            ss = o.modifiers.new('ss', 'SUBSURF'); ss.levels = 1; ss.render_levels = 2
            gm = L.mat('kw_pepper_stem', (0.18, 0.42, 0.08), 0.5)
            cal = L.sphere('kw_pepper_cal', 0.011, (0, 0, 0.0015), gm, c, 16, 8, (1, 1, 0.35)); cal.parent = o
            st = L.cyl('kw_pepper_stem', 0.0022, 0.022, (0.002, 0, 0.012), gm, c, rot=(0, 14, 0), verts=10); st.parent = o
            return o
        if pr == 'slushie':  # takeaway slushie: bright blue frozen drink in a clear cup, clear dome lid, red straw (axis z; the hold puts +z DOWN, so lid + straw sit at -z)
            o = L.cyl('kw_slush', 0.037, 0.11, (0, 0, 0), L.bumpy(L.mat('kw_slush_m', (0.01, 0.16, 0.85), 0.35, coat=0.5), 60.0, 0.15, 2.0, dist=0.0015), c, verts=32)
            ld = L.sphere('kw_slush_lid', 0.038, (0, 0, -0.056), L.mat('kw_slush_lid_m', (0.9, 0.93, 0.97), 0.1, coat=0.8), c, 24, 12, (1, 1, 0.5)); ld.parent = o
            sw = L.cyl('kw_slush_straw', 0.0045, 0.13, (0.008, 0, -0.1), L.mat('kw_slush_straw_m', (0.85, 0.05, 0.05), 0.3), c, rot=(0, 10, 0), verts=12); sw.parent = o
            return o
        mk = {'cup': lambda: L.cyl('kw_cup', 0.04, 0.1, (0, 0, 0), L.mat('kw_cup_m', (0.95, 0.95, 0.92), 0.3, coat=0.6), c),
              'apple': lambda: L.sphere('kw_apple', 0.04, (0, 0, 0), L.mat('kw_apple_m', (0.75, 0.05, 0.04), 0.3, coat=0.5), c, 24, 12, (1, 1, 0.9)),
              'pill': lambda: L.sphere('kw_pill', 0.006, (0, 0, 0), L.mat('kw_pill_m', (0.95, 0.95, 0.97), 0.3), c, 16, 8, (2.2, 1, 1)),
              'phone': lambda: L.box('kw_phone', (0.072, 0.009, 0.15), (0, 0, 0), L.mat('kw_phone_m', (0.04, 0.04, 0.05), 0.2, 0.6), c, 0.006),
              'pen': lambda: L.cyl('kw_pen', 0.005, 0.14, (0, 0, 0), L.mat('kw_pen_m', (0.1, 0.2, 0.8), 0.3), c),
              'spoon': lambda: L.cyl('kw_spoon', 0.005, 0.15, (0, 0, 0), L.mat('kw_spoon_m', (0.85, 0.85, 0.88), 0.2, 1.0), c),
              'bottle': lambda: L.cyl('kw_bottle', 0.033, 0.2, (0, 0, 0), L.mat('kw_bottle_m', (0.6, 0.8, 1.0), 0.05, trans=0.9), c),
              'can': lambda: L.cyl('kw_can', 0.033, 0.12, (0, 0, 0), L.mat('kw_can_m', (0.85, 0.1, 0.1), 0.25, 0.8), c),
              'earbud': lambda: L.sphere('kw_earbud', 0.009, (0, 0, 0), L.mat('kw_earbud_m', (0.96, 0.96, 0.96), 0.2, coat=0.8), c),
              'swab': lambda: L.cyl('kw_swab', 0.002, 0.075, (0, 0, 0), L.mat('kw_swab_m', (0.95, 0.95, 0.95), 0.6), c),
              'pepper': lambda: L.sphere('kw_pepper', 0.02, (0, 0, 0), L.mat('kw_pepper_m', (0.9, 0.08, 0.02), 0.2, coat=0.8), c, 20, 10, (0.8, 0.8, 1.6))}
        return mk[pr]()

    # ================================================================== queries
    def world_of(self, f):
        it = self.items.get(f)
        if not it: return None
        for k in ('gauge', 'label', 'crackle'):
            if it.get(k) is not None: return it[k].root.matrix_world.translation.copy()
        return None
    def organ_point(self, actor, organ): return self.bodies[actor].organ_point(organ)
    def macro_info(self, m):
        mm = self.macros[m]; return dict(hole=mm.HOLE, origin=mm.M0, kind=mm.kind, block_pt=mm.block_pt)
    def station(self, f):
        if f is None: raise ValueError('cam.prop() needs a prop fx in the shot')
        k = 'gauge' if f.kind == 'gauge' else f.kind; return self.stations[k]['origin'], k

    # ================================================================== visibility
    def xray_body(self, ra, on):
        b = self.bodies.get(ra.a)
        if b and not on: b.show(False)
    def visibility(self, shot):
        for a, b in self.bodies.items(): b.show(shot.xray is a and shot.set == 'xray', shot.organs)
        for m, mm in self.macros.items():
            h = not (shot.set == 'macro' and shot.macro is m)
            if mm.coll.hide_render != h: mm.coll.hide_render = h
        kinds = {('gauge' if f.kind == 'gauge' else f.kind) for f in shot.fx if f.is_prop()}
        for k, st in self.stations.items():
            h = not (shot.set == 'graphic' and k in kinds)
            if st['coll'].hide_render != h: st['coll'].hide_render = h
        for f, c in self.fx_coll.items():
            h = f.shot is not shot
            if c.hide_render != h: c.hide_render = h
        if self.spray: self.spray['coll'].hide_render = False

    # ================================================================== per frame
    def update(self, shot, u, t):
        rt = self.rt
        for b in self.bodies.values(): b.reset_fx()
        if shot.set == 'xray' and shot.xray in self.bodies and 'heart' in (shot.organs or ()): self.bodies[shot.xray].beat(t)
        # macro
        if shot.set == 'macro' and shot.macro in self.macros:
            mm = self.macros[shot.macro]; mm.update(shot, u, t, self.ep.shots); rt.prop_lights(mm.M0, 1.0, gain=0.42)
        # wounds (kwwound): stage values from the shot's keys, hidden in shots without one
        ws = self.__dict__.get('wounds', {})
        if ws:
            act = {}
            for f in shot.fx:
                if f.kind == 'wound': act[f.o['person']] = f.o['keys']
            for a, w in ws.items():
                if a in act: w.set(**_wound_vals(act[a], u))
                else: w.set(show=False)
        # table-top items, beams, counters' lights (kwprops)
        items = [(f, self.items.get(f)) for f in shot.fx if f.kind == 'item' and self.items.get(f)]
        for f, it in items:
            if f.o['keys']: it['prop'].set(**_key_vals(f.o['keys'], u))
        if items and not shot.cast:
            pts = [it['prop'].root.matrix_world.translation for f, it in items if f.o['item'] != 'bench']
            if not pts: pts = [it['prop'].point('top') for f, it in items]
            ctr = sum(pts, V((0, 0, 0))) / len(pts); sc = next((f.o['light'] for f, _ in items if f.o.get('light')), 0.45)
            rt.prop_lights(ctr + V((0, 0, 0.05)), sc)
        for f in shot.fx:
            it = self.items.get(f)
            if f.kind == 'beam' and it:
                o = f.o; P1 = V(it['P1'])
                if o.get('sweep'):
                    t2, t0, t1 = o['sweep']; P1 = P1.lerp(self._pt(t2), ramp(u, t0, t1))
                P0 = it['P0']; d = P1 - P0; L_ = max(1e-4, d.length); q = d.to_track_quat('Z', 'Y')
                k_ = ramp(u, o['at'], o['at'] + max(0.01, o['fade']))
                co = it['cone']; co.location = P0; co.rotation_euler = q.to_euler(); co.scale = (1, 1, L_); co.hide_render = k_ <= 0
                lo = it['light']; lo.location = P0; lo.rotation_euler = d.to_track_quat('-Z', 'Y').to_euler(); lo.hide_render = k_ <= 0
                lo.data.spot_size = min(3.0, 2 * math.atan(o['width'] * 0.6 / L_) * 1.6); lo.data.energy = 8.0 * o['strength'] * k_ * (L_ / 0.3) ** 2
                it['fade'].outputs[0].default_value = k_
            elif f.kind == 'flow_path' and it: self._flow(f, it, u, t)
        # stations
        for f in shot.fx:
            o = f.o; it = self.items.get(f)
            if f.is_prop() and shot.set == 'graphic':
                k = 'gauge' if f.kind == 'gauge' else f.kind; st = self.stations[k]; sc, gain = PROP_LIGHT[k]; rt.prop_lights(st['origin'], sc, gain=gain); ob = st['obj']
                if ob is None: continue
                if k == 'calendar': ob.set(ramp(u, o['at'], o['at'] + o['dur']) * (o['weeks'] - 1) / 4.0)
                elif k == 'earth':
                    g = ramp(u, o['at'], o['at'] + o['dur']); pa = o.get('pulse_at') if o.get('pulse_at') is not None else o['at'] + o['dur']
                    ob.update(it['key'] if it else shot.name, g, o['spin'] * u, bump(u, pa + 0.15, 0.3))
                elif k == 'scan':
                    self._set_scan_kind(st, o['kind'], o.get('title') or 'CT / ' + o['kind'].upper())
                    hl = ramp(u, o['heal_at'], o['heal_at'] + 0.85) if o['heal'] else 0.0
                    ob.set(heal=hl, on=1.0)
                    if o['kind'] == 'head': self._scan_heal_node.outputs[0].default_value = hl
                elif k == 'skin_block':
                    pr = bump(u, o['press_at'], 0.22) if o.get('press_at') is not None else 0.0
                    ob.set(bubbles=ramp(u, o['at'], o['at'] + 0.85), press=pr)
                elif k == 'gauge':
                    gv = 0.1 + (o['to'] - 0.1) * ramp(u, o['at'], o['at'] + o['dur']); ob.set(gv, shake=0.8 * ramp(u, o['at'] + o['dur'] - 0.2, o['at'] + o['dur']))
                    if st['label'] is not None:
                        ka = pop((u - o['at'] - o['dur']) / 0.3) if o.get('label') and u > o['at'] + o['dur'] else 0.0
                        st['label'].set(scale=max(ka, 1e-5), text=o.get('label') or ' ')
                continue
            if it is None: continue
            if f.kind == 'arrow': it['arrow'].set(grow=ramp(u, o['at'], o['at'] + o['dur']))
            elif f.kind == 'bracket': it['bracket'].set(grow=ramp(u, o['at'], o['at'] + 0.45))
            elif f.kind == 'crackle':
                cr = it['crackle']; cr.root.location = rt.anchor_world(o['near']) + V((0, -0.02, 0)); cr.set(max([bump(u, x, 0.16) for x in o['times']] + [0]))
            elif f.kind == 'flow': self._flow(f, it, u, t)
            elif f.kind == 'pressure':
                b = self.bodies[o['person']]; k = ramp(u, o['at'], o['at'] + o['dur'] * 0.8); b.heat(o['organ'], k, 0.5 + 0.5 * math.sin(t * 16), o['swell'])
            elif f.kind == 'glow':
                b = self.bodies[o['person']]; k = ramp(u, o['at'], o['at'] + 0.2) * (1 - 0.5 * ramp(u, o['at'] + o['dur'], o['at'] + o['dur'] + 0.4)); b.heat(o['organ'], k, 0.5 + 0.5 * math.sin(t * 10), 0.0, color=(LABEL_COL.get(o.get('color')) if o.get('color') not in (None, 'red') else None))
            elif f.kind == 'seal':
                hit = ramp(u, o['at'], o['at'] + 0.12); sp = hit * (1.0 + 0.25 * math.sin(t * 20))
                for ob, bs in zip(it['objs'], it['base']): ob.scale = tuple(x * max(sp, 1e-4) for x in bs); ob.hide_render = hit <= 0
                it['em'].inputs['Strength'].default_value = 8 + 8 * (0.5 + 0.5 * math.sin(t * 16))
            elif f.kind == 'swell_air':
                g = ramp(u, o['at'], o['at'] + o['dur']); sh = 1 - ramp(u, o['shrink_at'], o['shrink_at'] + 1.0) if o.get('shrink_at') is not None else 1.0
                for ob, r, ph in it['bub']:
                    k = ramp(g, ph * 0.6, ph * 0.6 + 0.4) * sh; ob.scale = (max(r * k, 1e-5),) * 3
            elif f.kind == 'crack_line':
                it['curve'].data.bevel_factor_end = max(1e-4, ramp(u, o['at'], o['at'] + 0.35)); it['em'].inputs['Strength'].default_value = 10 + 14 * math.exp(-max(0, u - o['at']) * 4)
        self._spray(shot, u, t)
        self._props(shot, u, t)

    def _flow(self, f, it, u, t):
        o = f.o; path = it.get('path') or L.smooth_path(self.bodies[o['person']].path_world(o['path']), 5); heat = o.get('heat', 0.0)
        stop = o.get('stop', 1.0); sp_ = o.get('speed', 1.0); dur = o.get('dur')
        it['em'].inputs['Color'].default_value = (*[a + (b - a) * heat for a, b in zip(it['col'], (1.0, 0.25, 0.05))], 1)
        span = sum((path[i + 1] - path[i]).length for i in range(len(path) - 1)); rr = o.get('size') or (0.0035 if span < 0.25 else 0.0042); spr = o.get('spread', 0.003)
        for ob, ph, ox, oy, sp in it['parts']:
            if u < o['at'] or (dur is not None and u > o['at'] + dur + 0.6): ob.scale = (1e-5,) * 3; continue
            if stop < 1.0:
                s_end = stop - 0.35 * sp * stop; s = min((u - o['at'] - 0.55 * ph) * 1.9 * sp_, s_end); vis = s > 0
            else:
                raw = (u - o['at']) * 0.9 * sp_ - ph; vis = raw > 0; s = raw % 1.0
                if dur is not None and u > o['at'] + dur and raw - (u - o['at'] - dur) * 0.9 * sp_ > 1.0 - 1e-9: vis = False
            jit = (0.0025 + 0.004 * heat) * (1 if stop < 1 and s >= stop * 0.6 else 0.4)
            p = L.poly_at(path, s) + V((ox * spr + math.sin(t * 17 + ph * 20) * jit, oy * spr + math.cos(t * 15 + sp * 9) * jit, math.sin(t * 13 + ph * 11) * jit))
            ob.location = p; ob.scale = ((rr if vis else 1e-5),) * 3

    def _spray(self, shot, u, t):
        if not self.spray: return
        rt = self.rt; act = None
        for a, ps in shot.cast.items():
            for _, q in ps.keys:
                for ac in q.acts:
                    if ac.kind in ('sneeze', 'cough') and ac.kw.get('spray', ac.kind == 'sneeze'): act = (a, ac)
        drops, splats = self.spray['drops'], self.spray['splats']
        if act is None:
            for o, *_ in drops: o.scale = (1e-5,) * 3
            for o, *_ in splats: o.scale = (1e-5,) * 3
            return
        a, ac = act; ra = rt.actors[a]; at = ac.at; dt = u - at
        mo = rt.part_world(ra, 'mouth')[0]; A = rt.anchors(ra); fwd = A['fwd']; R = V((0, -1, 0)).rotation_difference(fwd).to_matrix()
        origin = mo + fwd * 0.02
        for o, v, r in drops:
            if dt > 0:   # LESSON: air drag - the spray hangs and falls instead of flying to the lens
                o.location = origin + (R @ v) * (0.085 * (1 - math.exp(-7 * dt))) + V((0, 0, -0.9 * dt * dt)); o.scale = (r * (1 + 0.5 * min(dt, 0.4)),) * 3
            else: o.scale = (1e-5,) * 3
        cam = rt.CAM.matrix_world.translation; facing = (cam - A['face']).normalized().dot(fwd) > 0.75 and (cam - A['face']).length < 1.2
        for o, x, y, r, d in splats:
            k = ramp(dt, 0.2 + d, 0.28 + d) if facing and ac.kind == 'sneeze' else 0.0
            o.location = (x, y - 0.006 * max(0, dt - 0.3 - d), -0.14); o.scale = (max(r * k, 1e-5), max(r * k * 1.15, 1e-5), max(r * k * 0.35, 1e-5))

    def _props(self, shot, u, t):
        rt = self.rt; used = set()
        jobs = getattr(rt, '_hand_jobs', [])
        for ra, side, D, tip, shape, Rw, pole, shapes, h in jobs:
            if h is None or not h.prop or ra.a not in shot.cast: continue
            pr = h.prop; ob = self.props.get(pr)
            if ob is None or pr in used: continue
            used.add(pr); ob.hide_render = False
            if pr == 'tissue':
                pt, nr = rt.part_world(ra, 'nose'); A = rt.anchors_light(ra); Mh = rt.wmat(ra.p, 'head'); up = (Mh.to_3x3() @ V((0, 1, 0))).normalized()
                yv = -nr; zv = (up - yv * up.dot(yv)).normalized(); xv = yv.cross(zv)
                M = Matrix((xv, yv, zv)).transposed().to_4x4(); M.translation = pt + nr * 0.02 - zv * 0.018   # paper sits in front of the fingers (hides them)
                ob.matrix_world = M
            else:
                Mw = rt.wmat(ra.p, f'wrist.{side}'); info = ra.hand[side]; palm = Mw @ info[shape]['palm']; n = (Mw.to_3x3() @ info['pnorm']).normalized()
                fdir = (Mw.to_3x3() @ info['fdir']).normalized()
                M = Matrix((fdir, n, fdir.cross(n))).transposed().to_4x4(); M.translation = palm + n * 0.025
                ob.matrix_world = M
        for pr, ob in self.props.items():
            if pr not in used: ob.hide_render = True
        for pr, it in getattr(self, 'grip_items', {}).items():     # cast v1.1: the item meshes follow their root's visibility
            for o in it.objs: o.hide_render = it.root.hide_render
        for pr, it in getattr(self, 'carried', {}).items():
            car = self.props[pr]; mine = set(it.objs) | {it.root}
            for o in [car] + list(car.children_recursive):
                if o in mine: continue
                o.visible_camera = o.visible_shadow = o.visible_diffuse = o.visible_glossy = o.visible_transmission = o.visible_volume_scatter = False
            for o in it.objs: o.hide_render = car.hide_render
        if os.environ.get('KW_V11_DBG'): print('V11DBG kit props', {pr: (ob.hide_render, tuple(round(x, 3) for x in ob.matrix_world.translation)) for pr, ob in self.props.items()})

    def update_screen(self, shot, u, t):
        """screen-space graphics (gauge / label with pos=) placed in front of the camera after it moved"""
        rt = self.rt; cam = rt.CAM; cd = cam.data; Rc = cam.matrix_world.to_3x3().normalized(); P0 = cam.matrix_world.translation
        fd_ = cd.dof.focus_distance
        # H1: closer than 14 cm the old 12 cm floor put the word behind the subject; there it sits at 0.93 x focus (in front, little blur).
        # Apparent size does not depend on d (sc grows with d), so a still camera renders exactly as before.
        d = fd_ * 0.85 if fd_ * 0.85 >= 0.12 else min(0.12, fd_ * 0.93); d = max(d, cd.clip_start * 3)
        th = 18.0 / cd.lens; hh = d * th; hw = hh * 9 / 16; sc = d / 0.55
        def place(root, pos, size=1.0):
            x = (pos[0] - 0.5) * 2 * hw; y = (pos[1] - 0.5) * 2 * hh
            root.matrix_world = (Matrix.Translation(P0 + Rc @ V((x, y, -d))) @ (Rc @ RX90).to_4x4() @ Matrix.Scale(sc * size, 4))
        for f in shot.fx:
            it = self.items.get(f); o = f.o
            if not it: continue
            if f.kind == 'gauge' and o.get('place') != 'station':
                g = it['gauge']; place(g.root, o['pos'], o['size'])
                gv = 0.1 + (o['to'] - 0.1) * ramp(u, o['at'], o['at'] + o['dur']); g.set(gv, shake=0.8 * ramp(u, o['at'] + o['dur'] - 0.2, o['at'] + o['dur']))
                lab = it.get('label')
                if lab:
                    place(lab.root, (o['pos'][0], o['pos'][1] + 0.115 * o['size']), o['size'])
                    ka = pop((u - o['at'] - o['dur']) / 0.3) if u > o['at'] + o['dur'] else 0.0; lab.set(scale=max(ka, 1e-5))
            elif f.kind == 'label':
                lab = it.get('label')
                if lab is None: continue
                if o.get('near') is not None:
                    w = rt.anchor_world(o['near']); dd = (w - P0).length
                    lab.root.matrix_world = Matrix.Translation(w) @ (Rc @ RX90).to_4x4() @ Matrix.Scale(dd / 0.55 * o['size'], 4)
                else:
                    if 'fit' not in it:       # H1: whole word at full size <= 960 px of 1080 (60 px free each side)
                        place(lab.root, o['pos'], o['size']); lab.set(scale=1.0); bpy.context.view_layer.update()     # text bbox evaluated (a shard may start here)
                        Mo = lab.root.matrix_world @ lab.object.matrix_parent_inverse @ lab.object.matrix_basis; RcT = Rc.transposed(); xs = []
                        for q in lab.object.bound_box:
                            cq = RcT @ ((Mo @ V(q)) - P0); xs.append(cq.x / max(1e-6, -cq.z) / (th * 9 / 16) * 540 + 540)
                        wpx = max(xs) - min(xs); it['fit'] = min(1.0, 945.0 / max(1.0, wpx)); it['wpx'] = wpx * it['fit']
                        print(f"KW label '{o['text']}' width {wpx:.0f} px -> {it['wpx']:.0f} px at 1080 (fit {it['fit']:.3f})", flush=True)
                    place(lab.root, o['pos'], o['size'] * it['fit'])
                ka = pop((u - o['at']) / 0.3) if u > o['at'] else 0.0
                if o.get('dur') is not None and u > o['at'] + o['dur']: ka = 0.0
                lab.set(scale=max(ka, 1e-5))
            elif f.kind == 'counter':
                lab = it.get('label')
                if lab is None: continue
                place(lab.root, o['pos'], o['size'] * 0.62)
                v = o['v0'] + (o['v1'] - o['v0']) * ramp(u, o['at'], o['at'] + o['dur'])
                ka = pop((u - o['at'] + 0.15) / 0.3) if u > o['at'] - 0.15 else 0.0; lab.set(scale=max(ka, 1e-5), text=_counter_text(o, v))


def _counter_text(o, v):
    s = f"{v:,.{o['decimals']}f}" if abs(v) >= 1000 else f"{v:.{o['decimals']}f}"
    if o['sign'] and v > 0: s = '+' + s
    return (s + ' ' + o['unit']).strip() if o['unit'] and o['unit'] not in ('%', 'x') else s + o['unit']


def _key_vals(keys, u):
    """smoothstep between item keys [(t, {name: v})]; names carry forward from the previous key"""
    full = []; cur = {}
    for t, v in sorted(keys, key=lambda x: x[0]):
        cur = dict(cur); cur.update(v); full.append((t, cur))
    if u <= full[0][0]: return dict(full[0][1])
    for (t0, a), (t1, b) in zip(full, full[1:]):
        if u <= t1:
            x = (u - t0) / max(1e-6, t1 - t0); x = x * x * (3 - 2 * x)
            return {k: a.get(k, b[k]) + (b[k] - a.get(k, b[k])) * x for k in b}
    return dict(full[-1][1])


def _wound_vals(keys, u):
    """smoothstep between wound keys; names carry forward ('sink' eases only between the keys that set it)"""
    r = _wound_vals0(keys, u)
    sk = sorted((t, v['sink']) for t, v in keys if 'sink' in v)
    if sk:
        if u <= sk[0][0]: r['sink'] = sk[0][1]
        elif u >= sk[-1][0]: r['sink'] = sk[-1][1]
        else:
            for (t0, a), (t1, b) in zip(sk, sk[1:]):
                if u <= t1: x = (u - t0) / max(1e-6, t1 - t0); r['sink'] = a + (b - a) * x; break     # linear: each strand's own 0.45 window = 8 frames over 0.75 s
    return r


def _wound_vals0(keys, u):
    """smoothstep between wound keys; names carry forward"""
    names = ('open', 'stitches', 'out', 'red', 'collagen', 'vessels', 'line', 'scar', 'pink', 'dots', 'level', 'cpink', 'cells', 'specks', 'cinch', 'lwid', 'sink')
    full = []; cur = dict.fromkeys(names, 0.0); cur['line'] = None; cur['specks'] = -1.0; cur['cinch'] = None; cur['lwid'] = 1.0     # specks -1 = hidden
    for t, v in sorted(keys, key=lambda x: x[0]):
        cur = dict(cur); cur.update(v); full.append((t, cur))
    if u <= full[0][0]: return {k: v for k, v in full[0][1].items() if v is not None}
    for (t0, a), (t1, b) in zip(full, full[1:]):
        if u <= t1:
            x = (u - t0) / max(1e-6, t1 - t0); x = x * x * (3 - 2 * x); r = {}
            for k in names:
                if a[k] is None or b[k] is None: r[k] = b[k] if b[k] is not None else a[k]
                else: r[k] = a[k] + (b[k] - a[k]) * x
            return {k: v for k, v in r.items() if v is not None}
    return {k: v for k, v in full[-1][1].items() if v is not None}
