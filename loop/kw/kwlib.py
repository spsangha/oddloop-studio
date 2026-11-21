"""kwlib - small Blender helpers shared by kwrun / kwbody / kwsets (materials, primitives, curves, collections, camera aim)."""
import bpy, math, os
from mathutils import Vector, Matrix
HERE = os.path.dirname(os.path.abspath(__file__))
_FONT = None
def S(): return bpy.context.scene
def font():
    global _FONT
    if _FONT is None: _FONT = bpy.data.fonts.load(os.path.join(HERE, '..', 'Montserrat-Black.ttf'), check_existing=True)
    return _FONT

def mat(name, col, rough=0.5, metal=0.0, emit=None, es=1.0, alpha=1.0, trans=0.0, sss=0.0, coat=0.0):
    m = bpy.data.materials.new(name); m.use_nodes = True; b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*col, 1); b.inputs['Roughness'].default_value = rough; b.inputs['Metallic'].default_value = metal
    if emit: b.inputs['Emission Color'].default_value = (*emit, 1); b.inputs['Emission Strength'].default_value = es
    if alpha < 1: b.inputs['Alpha'].default_value = alpha
    if trans: b.inputs['Transmission Weight'].default_value = trans
    if sss: b.inputs['Subsurface Weight'].default_value = sss; b.inputs['Subsurface Radius'].default_value = (0.2, 0.05, 0.03)
    if coat: b.inputs['Coat Weight'].default_value = coat; b.inputs['Coat Roughness'].default_value = 0.1
    return m
def bsdf(m): return m.node_tree.nodes['Principled BSDF']
def bumpy(m, scale=40.0, strength=0.3, detail=4.0, dist=0.02, stretch=None):
    nt = m.node_tree; b = nt.nodes['Principled BSDF']; nz = nt.nodes.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = scale; nz.inputs['Detail'].default_value = detail
    if stretch:
        tc = nt.nodes.new('ShaderNodeTexCoord'); mp = nt.nodes.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = stretch
        nt.links.new(tc.outputs['Object'], mp.inputs['Vector']); nt.links.new(mp.outputs['Vector'], nz.inputs['Vector'])
    bp_ = nt.nodes.new('ShaderNodeBump'); bp_.inputs['Strength'].default_value = strength; bp_.inputs['Distance'].default_value = dist
    nt.links.new(nz.outputs['Fac'], bp_.inputs['Height']); nt.links.new(bp_.outputs['Normal'], b.inputs['Normal']); return m
def glow(name, col, es, alpha=0.6, blend=0.35):
    """emission that fades at grazing angles (x-ray look). returns (material, emission node)"""
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial'); em = nt.nodes.new('ShaderNodeEmission'); em.inputs['Color'].default_value = (*col, 1); em.inputs['Strength'].default_value = es
    tr = nt.nodes.new('ShaderNodeBsdfTransparent'); lw = nt.nodes.new('ShaderNodeLayerWeight'); lw.inputs['Blend'].default_value = blend
    mx = nt.nodes.new('ShaderNodeMixShader'); mth = nt.nodes.new('ShaderNodeMath'); mth.operation = 'MULTIPLY_ADD'; mth.inputs[1].default_value = 1 - alpha; mth.inputs[2].default_value = alpha
    nt.links.new(lw.outputs['Facing'], mth.inputs[0]); nt.links.new(mth.outputs[0], mx.inputs[0]); nt.links.new(tr.outputs[0], mx.inputs[1]); nt.links.new(em.outputs[0], mx.inputs[2]); nt.links.new(mx.outputs[0], out.inputs[0])
    return m, em
def emis(name, col, es=4.0):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial'); em = nt.nodes.new('ShaderNodeEmission'); em.inputs['Color'].default_value = (*col, 1); em.inputs['Strength'].default_value = es
    nt.links.new(em.outputs[0], out.inputs[0]); return m, em
def coll(name, parent=None):
    c = bpy.data.collections.get(name)
    if c is None: c = bpy.data.collections.new(name)
    par = parent or S().collection
    if c.name not in par.children: par.children.link(c)
    return c
def into(c, objs):
    for o in objs:
        for u in list(o.users_collection): u.objects.unlink(o)
        c.objects.link(o)
    return objs
def smooth(o):
    if o.type == 'MESH':
        for p in o.data.polygons: p.use_smooth = True
    return o
def prim(kind, name, mt=None, c=None, **kw):
    getattr(bpy.ops.mesh, 'primitive_' + kind + '_add')(**kw); o = bpy.context.object; o.name = name
    if mt: o.data.materials.append(mt)
    if c: into(c, [o])
    return o
def sphere(name, r, loc, mt, c=None, seg=24, rings=12, scale=None):
    o = prim('uv_sphere', name, mt, c, radius=r, location=loc, segments=seg, ring_count=rings); smooth(o)
    if scale: o.scale = scale
    return o
def ico(name, r, loc, mt, c=None, sub=2):
    o = prim('ico_sphere', name, mt, c, radius=r, location=loc, subdivisions=sub); smooth(o); return o
def box(name, size, loc, mt, c=None, bev=0.02, rot=(0, 0, 0)):
    o = prim('cube', name, mt, c, size=1, location=loc, rotation=[math.radians(a) for a in rot]); o.scale = size
    if bev:
        m = o.modifiers.new('b', 'BEVEL'); m.width = bev; m.segments = 3; m.limit_method = 'NONE'; smooth(o)
    return o
def cyl(name, r, depth, loc, mt, c=None, rot=(0, 0, 0), verts=32):
    o = prim('cylinder', name, mt, c, radius=r, depth=depth, location=loc, rotation=[math.radians(a) for a in rot], vertices=verts); smooth(o); return o
def tube(name, pts, r, mt, c=None, res=6, radii=None, caps=True):
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = r; cu.bevel_resolution = res; cu.use_fill_caps = caps
    sp = cu.splines.new('BEZIER'); sp.bezier_points.add(len(pts) - 1)
    for i, (bp_, p) in enumerate(zip(sp.bezier_points, pts)):
        bp_.co = p; bp_.handle_left_type = bp_.handle_right_type = 'AUTO'
        if radii: bp_.radius = radii[i]
    o = bpy.data.objects.new(name, cu); (c or S().collection).objects.link(o)
    if mt: o.data.materials.append(mt)
    return o
def text3d(name, body, size, mt, c=None, extrude=0.18):
    fc = bpy.data.curves.new(name, 'FONT'); fc.body = body; fc.font = font(); fc.size = size; fc.extrude = size * extrude; fc.bevel_depth = size * 0.035; fc.bevel_resolution = 3
    fc.align_x = 'CENTER'; fc.align_y = 'CENTER'
    o = bpy.data.objects.new(name, fc); (c or S().collection).objects.link(o); o.rotation_euler = (math.radians(90), 0, 0)
    o.data.materials.append(mt); return o
def bone_parent(o, rig, bone):
    """parent o to a pose bone keeping its current world transform"""
    bpy.context.view_layer.update(); mw = o.matrix_world.copy()
    o.parent = rig; o.parent_type = 'BONE'; o.parent_bone = bone
    bpy.context.view_layer.update(); o.matrix_world = mw
    return o
def aim(fwd, up=(0, 0, 1)):
    """camera rotation matrix (3x3) looking along fwd with the given up vector"""
    f = Vector(fwd).normalized(); u = Vector(up)
    x = f.cross(u)
    if x.length < 1e-6: x = f.cross(Vector((0, 1, 0)) if abs(f.z) > 0.9 else Vector((0, 0, 1)))
    x.normalize(); z = -f; y = z.cross(x)
    return Matrix((x, y, z)).transposed()
def poly_at(pts, s):
    s = min(1.0, max(0.0, s)); L = [(pts[i + 1] - pts[i]).length for i in range(len(pts) - 1)]; tot = sum(L) or 1e-9; d = s * tot
    for i, l in enumerate(L):
        if d <= l or i == len(L) - 1: return pts[i].lerp(pts[i + 1], min(1.0, d / max(l, 1e-9)))
        d -= l
    return pts[-1]
def smooth_path(pts, n=6):
    """catmull-rom densify (list of Vectors)"""
    if len(pts) < 3: return [Vector(p) for p in pts]
    P = [Vector(pts[0])] + [Vector(p) for p in pts] + [Vector(pts[-1])]; out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for k in range(n):
            t = k / n; t2 = t * t; t3 = t2 * t
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t2 + (-p0 + 3 * p1 - 3 * p2 + p3) * t3))
    out.append(Vector(pts[-1])); return out
def hide(objs, h):
    for o in objs:
        if o.hide_render != h: o.hide_render = h
