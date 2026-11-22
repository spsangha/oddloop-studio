"""bake the MakeHuman neutral body's object-space position into its UVs (assets mask helper for post_bake.py)
usage: blender -b -P bake_pos.py -- OUT.npz"""
import bpy, sys, numpy as np
from bl_ext.user_default.mpfb.services.humanservice import HumanService
from bl_ext.user_default.mpfb.services.targetservice import TargetService
out = sys.argv[sys.argv.index('--') + 1]
for o in list(bpy.data.objects): bpy.data.objects.remove(o)
h = HumanService.create_human(macro_detail_dict={"gender": 0.5, "age": 0.5, "muscle": 0.5, "weight": 0.5, "proportions": 0.5, "height": 0.5,
                                                 "cupsize": 0.5, "firmness": 0.5, "race": {"african": 0.33, "asian": 0.33, "caucasian": 0.34}})
TargetService.bake_targets(h); h.modifiers.clear(); h.data.materials.clear()
gi = {g.name: g.index for g in h.vertex_groups}
V = np.array([v.co[:] for v in h.data.vertices])
def grp(n): return np.array([v.index for v in h.data.vertices for g in v.groups if g.group == gi[n] and g.weight > 0.5])
eyeL, eyeR = V[grp('joint-l-eye')].mean(0), V[grp('joint-r-eye')].mean(0)
m = bpy.data.materials.new('pos'); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
ge = nt.nodes.new('ShaderNodeNewGeometry'); em = nt.nodes.new('ShaderNodeEmission'); o_ = nt.nodes.new('ShaderNodeOutputMaterial')
nt.links.new(ge.outputs['Position'], em.inputs['Color']); nt.links.new(em.outputs[0], o_.inputs[0])
im = bpy.data.images.new('pos', 2048, 2048, float_buffer=True); im.colorspace_settings.name = 'Non-Color'
tn = nt.nodes.new('ShaderNodeTexImage'); tn.image = im; nt.nodes.active = tn
h.data.materials.append(m)
S = bpy.context.scene; S.render.engine = 'CYCLES'; S.cycles.samples = 1
for o in bpy.context.view_layer.objects: o.select_set(False)
h.select_set(True); bpy.context.view_layer.objects.active = h
bpy.ops.object.bake(type='EMIT', margin=8, use_clear=True)
px = np.array(im.pixels[:], np.float32).reshape(2048, 2048, 4)
np.savez_compressed(out, p=px[..., :3], eyeL=eyeL, eyeR=eyeR)
print('pos baked')
