"""kwearth - the 'earth' graphic station for KW.fx.earth (ep06): NASA Blue Marble globe, a growing red vessel line, a white tick.
Texture: NASA Blue Marble Next Generation, July 2004, world.topo.bathy.200407.3x5400x2700.jpg (public domain, credit "NASA Earth Observatory").
Globe local frame: dir(lon, lat) = (-cos lat cos lon, -cos lat sin lon, sin lat) (Blender SPHERE projection of an equirectangular map)."""
import bpy, math, os
from mathutils import Vector as V, Matrix
import kwkit as KW
import kwlib as L

HERE = os.path.dirname(os.path.abspath(__file__))
TEX = os.path.normpath(os.path.join(HERE, '..', '..', 'assets', 'real', 'tex', 'bluemarble', 'world.topo.bathy.200407.3x5400x2700.jpg'))
R = 0.3                     # globe radius (m); station units in the brief are R = 1
LIFT = 0.02 * R             # line floats 0.02 R above the surface
TUBE = 0.015 * R            # tube radius 0.015 R
TILT = 23.0                 # axial tilt (deg, in the picture plane)
VESSEL = (0.95, 0.08, 0.06) # kwbody kw_vessel colour

def ldir(lon, lat):
    lo, la = math.radians(lon), math.radians(lat)
    return V((-math.cos(la) * math.cos(lo), -math.cos(la) * math.sin(lo), math.sin(la)))

def base_rot(lon0, lat0, spin=0.0):
    """world rotation that puts (lon0, lat0) facing the camera (world -Y), axis tilted TILT deg; spin deg eastward"""
    return (Matrix.Rotation(math.radians(TILT), 4, 'Y') @ Matrix.Rotation(math.radians(lat0), 4, 'X')
            @ Matrix.Rotation(math.radians(90 - lon0 + spin), 4, 'Z'))

def _globe_mat():
    m = bpy.data.materials.new('kw_earth_bluemarble'); m.use_nodes = True; nt = m.node_tree; b = nt.nodes['Principled BSDF']
    # explicit equirectangular lookup: lon = atan2(-y, -x), lat = asin(z) (same frame as ldir); u = lon/2pi + 0.5, v = lat/pi + 0.5
    tc = nt.nodes.new('ShaderNodeTexCoord'); im = nt.nodes.new('ShaderNodeTexImage'); im.interpolation = 'Cubic'
    im.image = bpy.data.images.load(TEX, check_existing=True); im.extension = 'REPEAT'
    nrm = nt.nodes.new('ShaderNodeVectorMath'); nrm.operation = 'NORMALIZE'; nt.links.new(tc.outputs['Object'], nrm.inputs[0])
    sp = nt.nodes.new('ShaderNodeSeparateXYZ'); nt.links.new(nrm.outputs[0], sp.inputs[0])
    def mth(op, a, b=None, v=None):
        n = nt.nodes.new('ShaderNodeMath'); n.operation = op
        for i, x in enumerate((a, b)):
            if x is None: continue
            if isinstance(x, (int, float)): n.inputs[i].default_value = x
            else: nt.links.new(x, n.inputs[i])
        return n.outputs[0]
    lon = mth('ARCTAN2', mth('MULTIPLY', sp.outputs['Y'], -1.0), mth('MULTIPLY', sp.outputs['X'], -1.0))
    lat = mth('ARCSINE', sp.outputs['Z'])
    u = mth('ADD', mth('DIVIDE', lon, 2 * math.pi), 0.5); v = mth('ADD', mth('DIVIDE', lat, math.pi), 0.5)
    cmb = nt.nodes.new('ShaderNodeCombineXYZ'); nt.links.new(u, cmb.inputs[0]); nt.links.new(v, cmb.inputs[1])
    nt.links.new(cmb.outputs[0], im.inputs['Vector'])
    # gentle lift so the dark oceans do not crush in the Zack grade
    cc = nt.nodes.new('ShaderNodeBrightContrast'); cc.inputs['Bright'].default_value = 0.04; cc.inputs['Contrast'].default_value = 0.08
    nt.links.new(im.outputs['Color'], cc.inputs['Color']); nt.links.new(cc.outputs['Color'], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = 0.6; b.inputs['Specular IOR Level'].default_value = 0.3
    return m

def _line_mat(name, col, alpha=1.0):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial'); em = nt.nodes.new('ShaderNodeEmission'); em.inputs['Color'].default_value = (*col, 1); em.inputs['Strength'].default_value = 3.0
    if alpha < 1.0:
        tr = nt.nodes.new('ShaderNodeBsdfTransparent'); mx = nt.nodes.new('ShaderNodeMixShader'); mx.inputs[0].default_value = alpha
        nt.links.new(tr.outputs[0], mx.inputs[1]); nt.links.new(em.outputs[0], mx.inputs[2]); nt.links.new(mx.outputs[0], out.inputs[0])
        m.blend_method = 'BLEND' if hasattr(m, 'blend_method') else None
    else: nt.links.new(em.outputs[0], out.inputs[0])
    return m, em

def _poly(name, pts, r, mt, c, parent):
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = r; cu.bevel_resolution = 4; cu.use_fill_caps = True
    sp = cu.splines.new('POLY'); sp.points.add(len(pts) - 1)
    for p, q in zip(sp.points, pts): p.co = (*q, 1.0)
    cu.bevel_factor_mapping_start = 'SPLINE'; cu.bevel_factor_mapping_end = 'SPLINE'
    o = bpy.data.objects.new(name, cu); c.objects.link(o); o.data.materials.append(mt); o.parent = parent
    return o

class EarthStation:
    """globe + backdrop + rim light at origin O; lines are added per shot with add_line()"""
    def __init__(self, O, c):
        self.O = V(O); self.c = c
        self.globe = L.sphere('kw_earth_globe', R, self.O, _globe_mat(), c, seg=128, rings=64)
        self.globe.rotation_mode = 'QUATERNION'
        # deep blue-black radial backdrop (not pure black), far behind so it stays soft
        bm = bpy.data.materials.new('kw_earth_backdrop'); bm.use_nodes = True; nt = bm.node_tree; nt.nodes.clear()
        out = nt.nodes.new('ShaderNodeOutputMaterial'); em = nt.nodes.new('ShaderNodeEmission'); tc = nt.nodes.new('ShaderNodeTexCoord')
        gr = nt.nodes.new('ShaderNodeTexGradient'); gr.gradient_type = 'SPHERICAL'; mp = nt.nodes.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (0.55, 0.55, 0.55)
        ramp_ = nt.nodes.new('ShaderNodeValToRGB'); cr = ramp_.color_ramp
        cr.elements[0].position = 0.0; cr.elements[0].color = (0.004, 0.010, 0.022, 1); cr.elements[1].position = 1.0; cr.elements[1].color = (0.020, 0.075, 0.140, 1)
        nt.links.new(tc.outputs['Object'], mp.inputs['Vector']); nt.links.new(mp.outputs['Vector'], gr.inputs['Vector']); nt.links.new(gr.outputs['Fac'], ramp_.inputs['Fac'])
        nt.links.new(ramp_.outputs['Color'], em.inputs['Color']); em.inputs['Strength'].default_value = 1.0; nt.links.new(em.outputs[0], out.inputs[0])
        self.back_em = em
        bpy.ops.mesh.primitive_plane_add(size=1, location=self.O + V((0, 2.5, 0)), rotation=(math.radians(90), 0, 0)); bd = bpy.context.object; bd.name = 'kw_earth_backdrop'
        bd.scale = (9, 9, 1); bd.data.materials.append(bm); L.into(c, [bd])
        bd.visible_shadow = False; bd.visible_diffuse = False; bd.visible_glossy = False
        # cool rim from behind so the globe edge reads
        ld = bpy.data.lights.new('kw_earth_rim', 'AREA'); ld.energy = 120; ld.size = 0.8; ld.color = (0.55, 0.75, 1.0)
        rim = bpy.data.objects.new('kw_earth_rim', ld); c.objects.link(rim); rim.location = self.O + V((0.55, 1.2, 0.55))
        rim.rotation_euler = (self.O - rim.location).to_track_quat('-Z', 'Y').to_euler()
        self.lines = {}

    def add_line(self, key, mode, lon0, lat0, cam_raise=0.0):
        """mode 'wrap2': 2 laps from the front-centre, 2nd lap 6 deg beside the 1st.  mode 'half': left limb -> 0.22 solid -> 0.47 pale, tick at 0.50."""
        c = self.c; R0 = base_rot(lon0, lat0).to_3x3(); Ri = R0.inverted(); rr = R + LIFT; parts = []
        if mode == 'wrap2':
            P0 = Ri @ V((0, -1, 0))                                  # front-centre (brief A1) in globe coords
            east = V((0, 0, 1)).cross(P0).normalized(); north = P0.cross(east).normalized()
            T = east * math.cos(math.radians(15)) + north * math.sin(math.radians(15)); N = P0.cross(T).normalized()
            n = 720; pts = []
            for i in range(n + 1):
                s = 2.0 * i / n; a = 2 * math.pi * s
                d = math.radians(6.0) * (KW.ease((s - 0.35) / 0.3) - KW.ease((s - 1.35) / 0.3))   # lap 2 shifts 6 deg on the BACK and returns on the back: two closed rings at the front
                q = (P0 * math.cos(a) + T * math.sin(a)) * math.cos(d) + N * math.sin(d)
                pts.append(q.normalized() * rr)
            mt, em = _line_mat('kw_earth_line_' + key, VESSEL)
            ob = _poly('kw_earth_line_' + key, pts, TUBE, mt, c, self.globe); parts.append(dict(obj=ob, em=em, pts=pts, s0=0.0, s1=1.0))
        else:
            # world frame: start on the left limb, across the lower-front face, tick on the right limb
            beta = math.radians(25.0)
            Xw = V((-1, 0, 0)); Fw = V((0, -math.cos(beta), -math.sin(beta)))
            def P(s): return (Ri @ (Xw * math.cos(2 * math.pi * s) + Fw * math.sin(2 * math.pi * s))).normalized() * rr
            for nm, a, b, col, al in (('solid', 0.0, 0.22, VESSEL, 1.0), ('pale', 0.215, 0.47, (1.0, 0.42, 0.38), 0.5)):
                pts = [P(a + (b - a) * i / 200) for i in range(201)]
                mt, em = _line_mat(f'kw_earth_{nm}_{key}', col, al)
                ob = _poly(f'kw_earth_{nm}_{key}', pts, TUBE * (1.0 if nm == 'solid' else 0.85), mt, c, self.globe)
                parts.append(dict(obj=ob, em=em, pts=pts, s0=a / 0.47, s1=b / 0.47))
            tick_m, _ = L.emis('kw_earth_tick', (1, 1, 1), 2.5); d = P(0.5).normalized()
            tk = L.tube('kw_earth_tick_' + key, [d * (R - 0.01 * R), d * (R + 0.11 * R)], 0.006 * R * 1.4, tick_m, c); tk.parent = self.globe
            parts.append(dict(tick=tk))
        tip_m, tip_em = _line_mat('kw_earth_tip_' + key, (1.0, 0.35, 0.25))
        tip = L.sphere('kw_earth_tip_' + key, TUBE * 1.9, V((0, 0, 0)), tip_m, c, seg=16, rings=8); tip.parent = self.globe
        self.lines[key] = dict(mode=mode, parts=parts, tip=tip, tip_em=tip_em, lon0=lon0, lat0=lat0)
        for p in parts:
            if 'obj' in p: p['obj'].data.bevel_factor_end = 0.0
        return self.lines[key]

    def update(self, key, grow, spin_deg, pulse=0.0):
        """grow 0..1 = share of the line drawn; spin_deg eastward spin; pulse 0..1 glow bump"""
        ln = self.lines[key]
        self.globe.rotation_quaternion = base_rot(ln['lon0'], ln['lat0'], spin_deg).to_quaternion()
        self.globe.location = self.O
        for k2, l2 in self.lines.items():
            vis = k2 == key
            for p in l2['parts']:
                o = p.get('obj') or p.get('tick'); o.hide_render = not vis
            l2['tip'].hide_render = not vis
        tip = None
        for p in ln['parts']:
            if 'obj' not in p: continue
            k = KW.clamp((grow - p['s0']) / max(1e-6, p['s1'] - p['s0']))
            p['obj'].data.bevel_factor_end = max(1e-4, k); p['obj'].hide_render = k <= 0
            p['em'].inputs['Strength'].default_value = 3.0 + 5.0 * pulse
            if k > 0:
                pts = p['pts']; x = k * (len(pts) - 1); i = min(int(x), len(pts) - 2); tip = pts[i].lerp(pts[i + 1], x - i)
        if tip is not None and grow < 0.999:
            ln['tip'].location = tip; ln['tip'].hide_render = False
        elif tip is not None and ln['mode'] == 'half':
            ln['tip'].location = tip; ln['tip'].hide_render = True    # rounded cap = the tube's own fill cap at the end
        else: ln['tip'].hide_render = True
        ln['tip_em'].inputs['Strength'].default_value = 6.0 + 6.0 * pulse
