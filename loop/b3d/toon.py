"""Odd Loop 3D kit (Blender, runs headless on GitHub). Characters are built from metaballs (soft, squashy, fused bodies) plus mesh eyes,
ears, nose and whiskers. Every frame the script sets poses directly, so one function per character drives all the acting."""
import bpy, bmesh, math
from mathutils import Vector, Euler, Matrix

def clear():
    bpy.ops.wm.read_factory_settings(use_empty=True)

def mat(name, rgb, rough=0.55, spec=0.25, sss=0.0, emit=0.0):
    m = bpy.data.materials.get(name)
    if m: return m
    m = bpy.data.materials.new(name); m.use_nodes = True
    b = m.node_tree.nodes['Principled BSDF']
    b.inputs['Base Color'].default_value = (*rgb, 1); b.inputs['Roughness'].default_value = rough
    b.inputs['Specular IOR Level'].default_value = spec
    if sss: b.inputs['Subsurface Weight'].default_value = sss; b.inputs['Subsurface Radius'].default_value = (0.3, 0.12, 0.08)
    if emit: b.inputs['Emission Color'].default_value = (*rgb, 1); b.inputs['Emission Strength'].default_value = emit
    return m

def hexc(h):
    h = h.lstrip('#'); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)   # sRGB -> linear

def link(o, coll=None):
    (coll or bpy.context.scene.collection).objects.link(o); return o

def mball(name, material, res=0.035):
    mb = bpy.data.metaballs.new(name); mb.resolution = mb.render_resolution = res; mb.threshold = 0.3
    o = link(bpy.data.objects.new(name, mb)); mb.materials.append(material); return o

def el(o, kind='ELLIPSOID', co=(0, 0, 0), r=0.3, size=(1, 1, 1), rot=(0, 0, 0), stiff=2.0):
    e = o.data.elements.new(type=kind); e.co = co; e.radius = r * 1.46; e.stiffness = stiff
    if kind in ('ELLIPSOID', 'CAPSULE', 'CUBE'): e.size_x, e.size_y, e.size_z = size
    e.rotation = Euler(rot).to_quaternion(); return e

def sphere(name, material, r=1, seg=48, parent=None):
    me = bpy.data.meshes.new(name); bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=seg // 2, radius=r)
    for f in bm.faces: f.smooth = True
    bm.to_mesh(me); bm.free(); o = link(bpy.data.objects.new(name, me)); me.materials.append(material)
    if parent: o.parent = parent
    return o

def cone(name, material, r1, r2, d, seg=32):
    me = bpy.data.meshes.new(name); bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=seg, radius1=r1, radius2=r2, depth=d)
    for f in bm.faces: f.smooth = True
    bm.to_mesh(me); bm.free(); o = link(bpy.data.objects.new(name, me)); me.materials.append(material)
    m = o.modifiers.new('sub', 'SUBSURF'); m.levels = m.render_levels = 2
    return o

def box(name, material, size, loc, bevel=0.02, rot=(0, 0, 0)):
    me = bpy.data.meshes.new(name); bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1)
    bmesh.ops.scale(bm, vec=size, verts=bm.verts); bm.to_mesh(me); bm.free()
    o = link(bpy.data.objects.new(name, me)); me.materials.append(material); o.location = loc; o.rotation_euler = rot
    if bevel: m = o.modifiers.new('bev', 'BEVEL'); m.width = bevel; m.segments = 3
    return o

def curve_line(name, material, pts, bevel=0.006):
    cu = bpy.data.curves.new(name, 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = bevel; cu.bevel_resolution = 2
    sp = cu.splines.new('BEZIER'); sp.bezier_points.add(len(pts) - 1)
    for p, c in zip(sp.bezier_points, pts): p.co = c; p.handle_left_type = p.handle_right_type = 'AUTO'
    o = link(bpy.data.objects.new(name, cu)); cu.materials.append(material); return o
