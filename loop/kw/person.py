"""Semi-realistic people for Odd Loop (Zack D. format) built with MPFB2 + MakeHuman CC0 system assets.
build_person(name, spec) -> Person with .rig .body; expressions are shape keys (Person.expr(name, value, frame));
arms reach with IK (Person.reach(side, world_pos, frame, w)); bones rotate with Person.rot(bone, (x,y,z) deg, frame)."""
import bpy, os, math
from mathutils import Vector, Euler
from bl_ext.user_default.mpfb.services.humanservice import HumanService
from bl_ext.user_default.mpfb.services.targetservice import TargetService
UD = os.environ.get('MPFB_UD', os.path.expanduser('~/.config/blender/4.2/extensions/.user/user_default/mpfb/data'))
SYS = os.path.dirname(os.path.dirname(os.path.abspath(__import__('bl_ext.user_default.mpfb', fromlist=['x']).__file__))) if False else None
MP = os.path.dirname(os.path.abspath(__import__('bl_ext.user_default.mpfb', fromlist=['x']).__file__)) + '/data'
EXPR = {  # friendly name -> list of (target file, weight)
    'puff':     [('cheek/l-cheek-volume-incr', 1.0), ('cheek/r-cheek-volume-incr', 1.0), ('expression/units/caucasian/mouth-compression', 1.0)],
    'wide':     [('expression/units/caucasian/eye-left-opened-up', 1.0), ('expression/units/caucasian/eye-right-opened-up', 1.0),
                 ('expression/units/caucasian/eyebrows-left-up', 1.0), ('expression/units/caucasian/eyebrows-right-up', 1.0)],
    'squint':   [('expression/units/caucasian/eye-left-closure', 1.0), ('expression/units/caucasian/eye-right-closure', 1.0),
                 ('expression/units/caucasian/nose-compression', 1.0), ('expression/units/caucasian/eyebrows-left-down', 1.0), ('expression/units/caucasian/eyebrows-right-down', 1.0)],
    'twitch':   [('expression/units/caucasian/nose-left-elevation', 1.0), ('expression/units/caucasian/nose-right-elevation', 1.0), ('expression/units/caucasian/nose-left-dilatation', 1.0), ('expression/units/caucasian/nose-right-dilatation', 1.0),
                 ('expression/units/caucasian/mouth-upward-retraction', 0.6)],
    'open':     [('expression/units/caucasian/mouth-open', 1.0)],
    'worry':    [('expression/units/caucasian/eyebrows-left-inner-up', 1.0), ('expression/units/caucasian/eyebrows-right-inner-up', 1.0), ('expression/units/caucasian/mouth-depression', 0.7)],
    'smile':    [('expression/units/caucasian/mouth-corner-puller', 1.0)],
    'pressed':  [('expression/units/caucasian/mouth-compression', 1.0), ('expression/units/caucasian/mouth-pursing', 0.4)],
    'bulge':    [('expression/units/caucasian/eye-left-opened-up', 1.5), ('expression/units/caucasian/eye-right-opened-up', 1.5),
                 ('expression/units/caucasian/eyebrows-left-up', 1.2), ('expression/units/caucasian/eyebrows-right-up', 1.2)],
    'neckswell': [('neck/measure-neck-circ-incr', 1.0), ('neck/neck-scale-horiz-incr', 1.0), ('neck/neck-scale-depth-incr', 0.7), ('neck/neck-double-incr', 0.5)],
    'grimace':  [('expression/units/caucasian/mouth-retraction', 1.0), ('expression/units/caucasian/eye-left-slit', 0.8), ('expression/units/caucasian/eye-right-slit', 0.8),
                 ('expression/units/caucasian/eyebrows-left-down', 0.8), ('expression/units/caucasian/eyebrows-right-down', 0.8), ('expression/units/caucasian/neck-platysma', 1.0)],
}

class Person:
    def __init__(self, name, rig, body, parts):
        self.name, self.rig, self.body, self.parts = name, rig, body, parts
        self.keys = {}; self.ik = {}
    def pb(self, b): return self.rig.pose.bones[b]
    def rot(self, bone, deg, frame=None):
        p = self.pb(bone); p.rotation_mode = 'XYZ'; p.rotation_euler = Euler([math.radians(a) for a in deg], 'XYZ')
        if frame is not None: p.keyframe_insert('rotation_euler', frame=frame)
    def expr(self, name, value, frame=None):
        for path, w in EXPR[name]:
            k = self.keys.get(path)
            if k is None: continue
            k.value = min(1.0, value * w) if k.slider_max <= 1 else value * w
        # several expressions can share one target: take the max of their asks this frame
        if frame is not None:
            for path, w in EXPR[name]:
                k = self.keys.get(path)
                if k: k.keyframe_insert('value', frame=frame)
    def reach(self, side, pos, frame=None, w=1.0, pole=None):
        tgt, con, pl = self.ik[side]
        tgt.location = Vector(pos); con.influence = w
        if pole is not None: pl.location = Vector(pole)
        if frame is not None:
            tgt.keyframe_insert('location', frame=frame); con.keyframe_insert('influence', frame=frame)
            if pole is not None: pl.keyframe_insert('location', frame=frame)
    def place(self, loc, rz=0.0):
        self.rig.location = Vector(loc); self.rig.rotation_euler = (0, 0, math.radians(rz))
    def head_world(self):
        return self.rig.matrix_world @ self.pb('head').head
    def bone_world(self, b, tail=False):
        p = self.pb(b); return self.rig.matrix_world @ (p.tail if tail else p.head)

EYE_SCALE = (('eyes/l-eye-scale-incr', 0.6), ('eyes/r-eye-scale-incr', 0.6))

def build_person(name, *, gender=1.0, age=0.5, weight=0.55, muscle=0.5, height=0.5, race=(0.0, 0.2, 0.8), skin='young_caucasian_male',
                 eyes='brown', hair='short02', brows='eyebrow001', clothes=('male_casualsuit04', 'shoes01'), cloth_tint=None, extra_targets=(), tee='teal', hair_value=0.45, skin_rough=None):
    macro = {"gender": gender, "age": age, "muscle": muscle, "weight": weight, "proportions": 0.5, "height": height, "cupsize": 0.5, "firmness": 0.5,
             "race": {"african": race[0], "asian": race[1], "caucasian": race[2]}}
    before = set(bpy.data.objects)
    h = HumanService.create_human(macro_detail_dict=macro)
    h.name = name
    extra_targets = tuple(extra_targets) + EYE_SCALE   # Zack look round 2: eyes ~12 % larger
    if extra_targets:  # face/body shape first, baked, so rig + hair + clothes fit the final head
        for path, wgt in extra_targets: TargetService.load_target(h, f'{MP}/targets/{path}.target.gz', weight=wgt)
        TargetService.bake_targets(h)
    HumanService.set_character_skin(f'{UD}/skins/{skin}/{skin}.mhmat', h, skin_type='ENHANCED_SSS')
    HumanService.add_builtin_rig(h, 'default')
    def add(p, t, **k): HumanService.add_mhclo_asset(f'{UD}/{p}', h, asset_type=t, **k)
    add('eyes/high-poly/high-poly.mhclo', 'Eyes', material_type='PROCEDURAL_EYES')
    IRIS = {'brown': ((0.16, 0.07, 0.02), (0.05, 0.02, 0.01)), 'darkbrown': ((0.07, 0.035, 0.015), (0.02, 0.01, 0.005)),
            'blue': ((0.18, 0.48, 0.91), (0.11, 0.16, 0.41)), 'green': ((0.2, 0.42, 0.18), (0.08, 0.16, 0.06)), 'lightblue': ((0.35, 0.6, 0.9), (0.15, 0.25, 0.45))}
    if eyes in IRIS:
        for o in bpy.data.objects:
            if o not in before and 'high-poly' in o.name.lower() and o.active_material and o.active_material.node_tree:
                for nd in o.active_material.node_tree.nodes:
                    for nm, col in (('IrisMajorColor', IRIS[eyes][0]), ('IrisMinorColor', IRIS[eyes][1])):
                        if nm in nd.inputs: nd.inputs[nm].default_value = (*col, 1)
    add(f'eyebrows/{brows}/{brows}.mhclo', 'Eyebrows'); add('eyelashes/eyelashes01/eyelashes01.mhclo', 'Eyelashes')
    if hair: add(f'hair/{hair}/{hair}.mhclo', 'Hair')
    for c in clothes: add(f'clothes/{c}/{c}.mhclo', 'Clothes')
    add('teeth/teeth_base/teeth_base.mhclo', 'Teeth')
    p = Person(name, h.parent, h, [o for o in bpy.data.objects if o not in before])
    # expression shape keys
    for nm, lst in EXPR.items():
        for path, w in lst:
            if path in p.keys: continue
            full = f'{MP}/targets/{path}.target.gz'
            TargetService.load_target(h, full, weight=0.0, name='x_' + os.path.basename(path))
            k = h.data.shape_keys.key_blocks['x_' + os.path.basename(path)]; k.slider_max = 1.5; p.keys[path] = k
    sub = h.modifiers.new('sub', 'SUBSURF'); sub.levels = 0; sub.render_levels = 1
    for o in p.parts:
        if o.type == 'MESH' and o is not h:
            for m in o.modifiers:
                if m.type == 'SUBSURF': m.levels = 0; m.render_levels = 1
    # arm IK (target + pole empties live in the rig's space, parented to the rig)
    for s in 'LR':
        t = bpy.data.objects.new(f'{name}_ik{s}', None); bpy.context.scene.collection.objects.link(t); t.empty_display_size = 0.05
        pl = bpy.data.objects.new(f'{name}_pole{s}', None); bpy.context.scene.collection.objects.link(pl)
        t.location = p.bone_world(f'wrist.{s}', tail=True); pl.location = p.bone_world(f'lowerarm01.{s}') + Vector((0, 0.6, -0.3))
        c = p.pb(f'wrist.{s}').constraints.new('IK'); c.target = t; c.pole_target = pl; c.chain_count = 5; c.influence = 0.0
        c.pole_angle = math.radians(-90 if s == 'L' else -90)
        p.ik[s] = (t, c, pl)
    TEX = os.environ.get('ZK_TEX', os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'assets', 'tex'))
    for o in p.parts:
        mt = o.active_material if o.type == 'MESH' else None
        if not mt or not mt.node_tree: continue
        nt = mt.node_tree
        if tee and 'casualsuit04' in o.name and 'diffuseTexture' in nt.nodes:
            nt.nodes['diffuseTexture'].image = bpy.data.images.load(os.path.join(TEX, f'tee_{tee}.jpg'))
        if hair and hair in o.name and 'diffuseTexture' in nt.nodes:
            tx = nt.nodes['diffuseTexture']; hs = nt.nodes.new('ShaderNodeHueSaturation'); hs.inputs['Value'].default_value = min(hair_value, 1.0); hs.inputs['Saturation'].default_value = 0.08 if hair_value > 1 else 1.1
            for l in list(tx.outputs['Color'].links):
                to = l.to_socket; nt.links.remove(l)
                if hair_value > 1:  # grey/white: blend toward a light grey so dark textures still go grey
                    mx = nt.nodes.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.inputs[0].default_value = min(0.9, 0.35 * hair_value)
                    mx.inputs[7].default_value = (0.62, 0.62, 0.63, 1); nt.links.new(hs.outputs['Color'], mx.inputs[6]); nt.links.new(mx.outputs[2], to)
                else: nt.links.new(hs.outputs['Color'], to)
            nt.links.new(tx.outputs['Color'], hs.inputs['Color'])
            # Zack look round 2: strand detail instead of clay - bump from the strand texture, glossy anisotropic sheen
            bs = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
            if bs is not None:
                for k, v in (('Roughness', 0.45), ('Anisotropic', 0.6), ('Specular IOR Level', 0.35), ('Coat Weight', 0.0)):
                    if k in bs.inputs and not bs.inputs[k].links: bs.inputs[k].default_value = v
                if not bs.inputs['Normal'].links:
                    bm = nt.nodes.new('ShaderNodeBump'); bm.inputs['Strength'].default_value = 0.7; bm.inputs['Distance'].default_value = 0.002
                    nt.links.new(tx.outputs['Color'], bm.inputs['Height']); nt.links.new(bm.outputs['Normal'], bs.inputs['Normal'])
    # Zack look round 2 (2026-11-22): photo skin with visible pores, less wax/gloss, warmer tone (skin R-B 0.18-0.24).
    # LESSON: the MPFB skin is one group per material slot; set EVERY skin slot (p.body.active_material is the genitals slot)
    for s_ in p.body.material_slots:
        m_ = s_.material
        if not m_ or not m_.node_tree: continue
        for g in m_.node_tree.nodes:
            if g.type != 'GROUP' or 'Pore strength' not in g.inputs: continue
            nm_ = m_.name.lower()
            if 'nail' in nm_: continue
            vals = {'Roughness': 0.33 if 'lips' in nm_ else (skin_rough or 0.44), 'Clearcoat': 0.04, 'Clearcoat Roughness': 0.4,
                    'Pore strength': 0.25 if 'lips' in nm_ else 0.6, 'SSS strength': 0.3, 'SSS radius scale': 0.1}
            for k, v in vals.items():
                if k in g.inputs: g.inputs[k].default_value = v
    try:  # warmer photo skin (measured graded R-B 0.12-0.14 vs Zack 0.18-0.24): saturate the diffuse inside the shared skin group once
        gt = next(g.node_tree for s_ in p.body.material_slots if s_.material for g in s_.material.node_tree.nodes if g.type == 'GROUP' and g.node_tree)
        if 'kw_skin_hs' not in gt.nodes:
            for nd in list(gt.nodes):
                if nd.type == 'TEX_IMAGE' and nd.image and 'diffuse' in (nd.image.name + nd.name).lower():
                    hs2 = gt.nodes.new('ShaderNodeHueSaturation'); hs2.name = 'kw_skin_hs'
                    hs2.inputs['Hue'].default_value = 0.5; hs2.inputs['Saturation'].default_value = 1.35; hs2.inputs['Value'].default_value = 0.92
                    for l in list(nd.outputs['Color'].links):
                        to = l.to_socket; gt.links.remove(l); gt.links.new(hs2.outputs['Color'], to)
                    gt.links.new(nd.outputs['Color'], hs2.inputs['Color']); break
    except Exception as e: print('skin tone skipped', e)
    if cloth_tint:
        for o in p.parts:
            for nm, col in cloth_tint.items():
                if nm in o.name and o.active_material:
                    for n in o.active_material.node_tree.nodes:
                        if n.type == 'BSDF_PRINCIPLED':
                            n.inputs['Base Color'].default_value = (*col, 1)
                            for l in list(n.inputs['Base Color'].links): o.active_material.node_tree.links.remove(l)
    return p

def fingers(p, side, curl, frame=None, thumb=None):
    """curl 0..1 for fingers 2-5 (and thumb if given)."""
    for f in range(2, 6):
        for j in (1, 2, 3): p.rot(f'finger{f}-{j}.{side}', (curl * (55 if j == 1 else 70), 0, 0), frame)
    if thumb is not None:
        for j in (1, 2, 3): p.rot(f'finger1-{j}.{side}', (thumb * 30, 0, thumb * (-25 if side == 'L' else 25)), frame)

def sit(p, frame=None, lean=0.0):
    for s in 'LR':
        p.rot(f'upperleg01.{s}', (-88, 0, 0), frame); p.rot(f'lowerleg01.{s}', (95, 0, 0), frame); p.rot(f'foot.{s}', (-8, 0, 0), frame)
    p.rot('spine03', (lean, 0, 0), frame)
