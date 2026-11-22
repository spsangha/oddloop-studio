"""Semi-realistic people for Odd Loop (Zack D. format) built with MPFB2 + MakeHuman CC0 system assets.
build_person(name, spec) -> Person with .rig .body; expressions are shape keys (Person.expr(name, value, frame));
arms reach with IK (Person.reach(side, world_pos, frame, w)); bones rotate with Person.rot(bone, (x,y,z) deg, frame)."""
import bpy, os, math
from mathutils import Vector, Euler
from bl_ext.user_default.mpfb.services.humanservice import HumanService
from bl_ext.user_default.mpfb.services.targetservice import TargetService
import heads_kw as _HK
UD = os.environ.get('MPFB_UD', os.path.expanduser('~/.config/blender/4.2/extensions/.user/user_default/mpfb/data'))
SYS = os.path.dirname(os.path.dirname(os.path.abspath(__import__('bl_ext.user_default.mpfb', fromlist=['x']).__file__))) if False else None
MP = os.path.dirname(os.path.abspath(__import__('bl_ext.user_default.mpfb', fromlist=['x']).__file__)) + '/data'
# round 3: CC0 MakeHuman community assets kept in the repo (assets/mh, see assets/LICENCES.md); used when not in the system data
MH = os.environ.get('KW_MH', os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'assets', 'mh'))
def _res(p): return f'{UD}/{p}' if os.path.exists(f'{UD}/{p}') else f'{MH}/{p}'
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

# round 3: the 6 most real-looking CC0/CC-BY community strand-card styles (assets/mh/hair) replace the system shells; KW_SYS_HAIR=1 keeps the old ones
HAIR_UP = {'short01': 'elvs_grump_hair', 'short02': 'culturalibre_hair_02', 'short03': 'elvs_grump_hair', 'short04': 'culturalibre_hair_02',
           'long01': 'elvs_hazel_hair',   # daisy (6.6k alpha cards) tripled a hospital frame (22.8 s vs 7.6 s)
           'bob01': 'elvs_wavy_bob', 'bob02': 'littleright_bobcut_hair', 'ponytail01': 'elvs_hazel_hair'}
EYE_SCALE = (('eyes/l-eye-scale-incr', 0.6), ('eyes/r-eye-scale-incr', 0.6))

def build_person(name, *, gender=1.0, age=0.5, weight=0.55, muscle=0.5, height=0.5, race=(0.0, 0.2, 0.8), skin='young_caucasian_male',
                 eyes='brown', hair='short02', brows='eyebrow001', clothes=('male_casualsuit04', 'shoes01'), cloth_tint=None, extra_targets=(), tee='teal', hair_value=0.45, skin_rough=None, beard=None, scan_seed=None):
    macro = {"gender": gender, "age": age, "muscle": muscle, "weight": weight, "proportions": 0.5, "height": height, "cupsize": 0.5, "firmness": 0.5,
             "race": {"african": race[0], "asian": race[1], "caucasian": race[2]}}
    before = set(bpy.data.objects)
    h = HumanService.create_human(macro_detail_dict=macro)
    h.name = name
    style0 = hair
    if os.environ.get('KW_SYS_HAIR') != '1' and hair in HAIR_UP and os.path.exists(os.path.join(MH, 'hair', HAIR_UP[hair])): hair = HAIR_UP[hair]
    extra_targets = tuple(extra_targets) + EYE_SCALE   # Zack look round 2: eyes ~12 % larger
    if extra_targets:  # face/body shape first, baked, so rig + hair + clothes fit the final head
        for path, wgt in extra_targets: TargetService.load_target(h, f'{MP}/targets/{path}.target.gz', weight=wgt)
        TargetService.bake_targets(h)
    if scan_seed is not None and _HK.on(): _HK.apply_shape(h, scan_seed)   # KW_HEADS=scan: light-stage scan identity (heads_kw.py)
    HumanService.set_character_skin(_res(f'skins/{skin}/{skin}.mhmat'), h, skin_type='ENHANCED_SSS')
    HumanService.add_builtin_rig(h, 'default')
    def add(p, t, **k):
        b_ = set(bpy.data.objects); HumanService.add_mhclo_asset(_res(p), h, asset_type=t, **k); return [o for o in bpy.data.objects if o not in b_]
    add('eyes/high-poly/high-poly.mhclo', 'Eyes', material_type='PROCEDURAL_EYES')
    IRIS = {'brown': ((0.16, 0.07, 0.02), (0.05, 0.02, 0.01)), 'darkbrown': ((0.07, 0.035, 0.015), (0.02, 0.01, 0.005)),
            'blue': ((0.18, 0.48, 0.91), (0.11, 0.16, 0.41)), 'green': ((0.2, 0.42, 0.18), (0.08, 0.16, 0.06)), 'lightblue': ((0.35, 0.6, 0.9), (0.15, 0.25, 0.45))}
    if eyes in IRIS:
        for o in bpy.data.objects:
            if o not in before and 'high-poly' in o.name.lower() and o.active_material and o.active_material.node_tree:
                for nd in o.active_material.node_tree.nodes:
                    for nm, col in (('IrisMajorColor', IRIS[eyes][0]), ('IrisMinorColor', IRIS[eyes][1])):
                        if nm in nd.inputs: nd.inputs[nm].default_value = (*col, 1)
    brow_objs = add(f'eyebrows/{brows}/{brows}.mhclo', 'Eyebrows'); add('eyelashes/eyelashes01/eyelashes01.mhclo', 'Eyelashes')
    hair_objs = add(f'hair/{hair}/{hair}.mhclo', 'Hair') if hair else []
    card_objs = list(hair_objs)
    beard_objs = add(f'clothes/{beard}/{beard}.mhclo', 'Clothes') if beard else []
    hair_objs += beard_objs   # round 3: CC0 beard/stubble cards, tinted like the hair
    for c in clothes: add(f'clothes/{c}/{c}.mhclo', 'Clothes')
    add('teeth/teeth_base/teeth_base.mhclo', 'Teeth')
    p = Person(name, h.parent, h, [o for o in bpy.data.objects if o not in before])
    p._kw_hair_value = hair_value
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
        if o in brow_objs and 'diffuseTexture' in nt.nodes and 'kw_dark' not in nt.nodes:   # round 3: darker, visible brows
            tx = nt.nodes['diffuseTexture']; hs = nt.nodes.new('ShaderNodeHueSaturation'); hs.name = 'kw_dark'; hs.inputs['Value'].default_value = 0.45
            for l in list(tx.outputs['Color'].links): to = l.to_socket; nt.links.remove(l); nt.links.new(hs.outputs['Color'], to)
            nt.links.new(tx.outputs['Color'], hs.inputs['Color'])
        if o in hair_objs and 'diffuseTexture' in nt.nodes:
            tx = nt.nodes['diffuseTexture']; hs = nt.nodes.new('ShaderNodeHueSaturation'); hs.inputs['Value'].default_value = min(hair_value, 1.0) if hair_value > 1 else 1.0; hs.inputs['Saturation'].default_value = 0.08 if hair_value > 1 else 1.0
            for l in list(tx.outputs['Color'].links):
                to = l.to_socket; nt.links.remove(l)
                if hair_value > 1:  # grey/white: blend toward a light grey so dark textures still go grey
                    mx = nt.nodes.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.inputs[0].default_value = min(0.9, 0.35 * hair_value)
                    mx.inputs[7].default_value = (0.62, 0.62, 0.63, 1); nt.links.new(hs.outputs['Color'], mx.inputs[6]); nt.links.new(mx.outputs[2], to)
                else:   # round 3: natural hair colour from the strand luminance (community textures come pink/blond/grey)
                    bw = nt.nodes.new('ShaderNodeRGBToBW'); nt.links.new(hs.outputs['Color'], bw.inputs['Color'])
                    k_ = max(0.0, min(1.0, hair_value)); col = tuple(a_ + (b_ - a_) * k_ for a_, b_ in zip((0.022, 0.016, 0.011), (0.30, 0.19, 0.10)))
                    mx = nt.nodes.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'; mx.inputs[0].default_value = 1.0
                    bwm = nt.nodes.new('ShaderNodeMath'); bwm.operation = 'MULTIPLY'; bwm.inputs[1].default_value = 2.4; nt.links.new(bw.outputs[0], bwm.inputs[0])
                    nt.links.new(bwm.outputs[0], mx.inputs[6]); mx.inputs[7].default_value = (*col, 1); nt.links.new(mx.outputs[2], to)
            nt.links.new(tx.outputs['Color'], hs.inputs['Color'])
            # round 3: dark matte strands (round-2 sheen read as grey shiny clay) - bump from the strand texture, low sheen
            bs = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
            if bs is not None:
                for k, v in (('Roughness', 0.62), ('Anisotropic', 0.2), ('Specular IOR Level', 0.22), ('Coat Weight', 0.0), ('Sheen Weight', 0.0)):
                    if k in bs.inputs and not bs.inputs[k].links: bs.inputs[k].default_value = v
                if not bs.inputs['Normal'].links:
                    bm = nt.nodes.new('ShaderNodeBump'); bm.inputs['Strength'].default_value = 0.4; bm.inputs['Distance'].default_value = 0.002
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
    try:  # round 3: real pore/lip/brow normal detail on every skin (CC0 mindfront NRM, same MakeHuman UV layout) when the skin has none
        gt = next(g.node_tree for s_ in p.body.material_slots if s_.material for g in s_.material.node_tree.nodes if g.type == 'GROUP' and g.node_tree)
        if 'NormalMapTexture' not in gt.nodes and 'Bump' in gt.nodes:
            nrm = os.path.join(MH, 'skins', 'mindfront_skin_male_african_middleage', 'skin_male_african_middleage_NRM.png')
            if os.path.exists(nrm):
                ti = gt.nodes.new('ShaderNodeTexImage'); ti.name = 'kw_nrm'; ti.image = bpy.data.images.load(nrm, check_existing=True); ti.image.colorspace_settings.name = 'Non-Color'
                nm = gt.nodes.new('ShaderNodeNormalMap'); nm.inputs['Strength'].default_value = 0.8
                gt.links.new(ti.outputs['Color'], nm.inputs['Color']); gt.links.new(nm.outputs['Normal'], gt.nodes['Bump'].inputs['Normal'])
    except Exception as e: print('skin normal skipped', e)
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
    if _HK.on():
        try: _HK.skin(p, age=age, gender=gender, seed=scan_seed, skin_name=skin); _HK.eyes(p, eyes); _HK.lashes(p); _HK.lips(p)
        except Exception as e: print('scan skin skipped', repr(e))
        strands = None
        if (style0 in _HK.CURVE_STYLES or style0 in _HK.FALL_STYLES) and os.environ.get('KW_SCAN_HAIR', '1') != '0':
            try:
                strands = _HK.strand_hair(p, style0, hair_value, scan_seed, african=race[0] >= 0.5)
                if strands:
                    for o in card_objs:   # keep the card mesh (wardrobe finds hair by asset), but never render it
                        o.visible_camera = o.visible_shadow = o.visible_diffuse = o.visible_glossy = o.visible_transmission = o.visible_volume_scatter = False
            except Exception as e: print('strand hair skipped', repr(e))
        if os.environ.get('KW_SCAN_BROWS', '1') != '0':   # round 2: strand brows / beard on the skin surface (follow expressions)
            for objs, kind in ((brow_objs, 'brow'), (beard_objs, 'stubble' if 'stubble' in str(beard) else 'beard')):
                if not objs: continue
                try:
                    if _HK.card_strands(p, objs, kind, hair_value, scan_seed):
                        for o in objs: o.visible_camera = o.visible_shadow = o.visible_diffuse = o.visible_glossy = o.visible_transmission = o.visible_volume_scatter = False
                except Exception as e: print(kind, 'strands skipped', repr(e))
        if not strands and card_objs:
            try: _HK.card_hair_fix(p, card_objs, hair_value)
            except Exception as e: print('card hair fix skipped', repr(e))
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
