"""Kinda Wild Films - realism helpers for Blender 4.2 (Cycles).
All assets referenced are CC0 (Poly Haven / ambientCG). Import with:
    sys.path.insert(0, '/home/user/workspace/kindawild/research'); import kw_realism as R
Functions:
    R.world_hdri(scene, path, strength=1.0, rot_deg=0.0, bg_strength=None)
    R.pbr(name, diff, rough=None, nor=None, scale=1.0, nor_strength=1.0, tint=None, rough_mul=1.0)
    R.pbr_dir(name, folder, scale=1.0, **kw)      # auto-finds Poly Haven *_diff/_rough/_nor_gl or ambientCG *_Color/_Roughness/_NormalGL
    R.import_gltf(path, location=(0,0,0), scale=1.0, collection=None) -> list of new objects
    R.render_look(scene, samples=32)               # colour management, sampling, denoise, bounces
    R.skin_sss(material, weight=0.25, radius=(1.0, 0.35, 0.2), scale=0.012)
    R.compositor_finish(scene, glare=True, vignette=0.2)
"""
import bpy, os, glob, math


# ---------------------------------------------------------------- world / HDRI
def world_hdri(scene, path, strength=1.0, rot_deg=0.0, bg_strength=None):
    """HDRI as world light. rot_deg spins the environment around Z (moves the sun / windows).
    bg_strength: if given, camera sees the HDRI at a different brightness than the lighting uses
    (e.g. bg_strength=0.0 for a plain backdrop while still lit by the HDRI)."""
    w = scene.world or bpy.data.worlds.new('kw_world'); scene.world = w
    w.use_nodes = True; nt = w.node_tree; nt.nodes.clear()
    tc = nt.nodes.new('ShaderNodeTexCoord'); mp = nt.nodes.new('ShaderNodeMapping')
    env = nt.nodes.new('ShaderNodeTexEnvironment'); env.image = bpy.data.images.load(path, check_existing=True)
    bg = nt.nodes.new('ShaderNodeBackground'); bg.inputs['Strength'].default_value = strength
    out = nt.nodes.new('ShaderNodeOutputWorld')
    mp.inputs['Rotation'].default_value[2] = math.radians(rot_deg)
    nt.links.new(tc.outputs['Generated'], mp.inputs['Vector'])
    nt.links.new(mp.outputs['Vector'], env.inputs['Vector'])
    nt.links.new(env.outputs['Color'], bg.inputs['Color'])
    if bg_strength is None:
        nt.links.new(bg.outputs['Background'], out.inputs['Surface'])
    else:  # light paths: camera rays see bg2, everything else sees bg
        bg2 = nt.nodes.new('ShaderNodeBackground'); bg2.inputs['Strength'].default_value = bg_strength
        nt.links.new(env.outputs['Color'], bg2.inputs['Color'])
        lp = nt.nodes.new('ShaderNodeLightPath'); mx = nt.nodes.new('ShaderNodeMixShader')
        nt.links.new(lp.outputs['Is Camera Ray'], mx.inputs['Fac'])
        nt.links.new(bg.outputs['Background'], mx.inputs[1]); nt.links.new(bg2.outputs['Background'], mx.inputs[2])
        nt.links.new(mx.outputs['Shader'], out.inputs['Surface'])
    return w


# ---------------------------------------------------------------- PBR materials
def _img(nt, path, non_color):
    n = nt.nodes.new('ShaderNodeTexImage'); n.image = bpy.data.images.load(path, check_existing=True)
    if non_color: n.image.colorspace_settings.name = 'Non-Color'
    return n


def pbr(name, diff, rough=None, nor=None, scale=1.0, nor_strength=1.0, tint=None, rough_mul=1.0):
    """Principled material from diffuse / roughness / OpenGL normal maps. Uses Object coords x scale,
    so it works on primitives without UVs (box-ish shapes). tint=(r,g,b) multiplies the colour map,
    handy to recolour a grey fabric to the seat colour you want."""
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree
    b = nt.nodes['Principled BSDF']
    tc = nt.nodes.new('ShaderNodeTexCoord'); mp = nt.nodes.new('ShaderNodeMapping')
    mp.inputs['Scale'].default_value = (scale, scale, scale)
    nt.links.new(tc.outputs['Object'], mp.inputs['Vector'])   # box projection needs Object coords
    d = _img(nt, diff, False); nt.links.new(mp.outputs['Vector'], d.inputs['Vector'])
    for n in [d]: n.projection = 'BOX'; n.projection_blend = 0.2
    col = d.outputs['Color']
    if tint:
        mx = nt.nodes.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'; mx.inputs[0].default_value = 1.0
        nt.links.new(col, mx.inputs[6]); mx.inputs[7].default_value = (*tint, 1); col = mx.outputs[2]
    nt.links.new(col, b.inputs['Base Color'])
    if rough:
        r = _img(nt, rough, True); r.projection = 'BOX'; r.projection_blend = 0.2
        nt.links.new(mp.outputs['Vector'], r.inputs['Vector'])
        if rough_mul != 1.0:
            mm = nt.nodes.new('ShaderNodeMath'); mm.operation = 'MULTIPLY'; mm.inputs[1].default_value = rough_mul
            nt.links.new(r.outputs['Color'], mm.inputs[0]); nt.links.new(mm.outputs[0], b.inputs['Roughness'])
        else:
            nt.links.new(r.outputs['Color'], b.inputs['Roughness'])
    if nor:
        n = _img(nt, nor, True); n.projection = 'BOX'; n.projection_blend = 0.2
        nt.links.new(mp.outputs['Vector'], n.inputs['Vector'])
        nm = nt.nodes.new('ShaderNodeNormalMap'); nm.inputs['Strength'].default_value = nor_strength
        nt.links.new(n.outputs['Color'], nm.inputs['Color']); nt.links.new(nm.outputs['Normal'], b.inputs['Normal'])
    return m


def pbr_dir(name, folder, scale=1.0, **kw):
    """Find maps in a folder: Poly Haven (<id>_diff_1k.jpg, _rough_1k, _nor_gl_1k) or
    ambientCG (<id>_1K-JPG_Color.jpg, _Roughness, _NormalGL)."""
    def f(*pats):
        for p in pats:
            g = sorted(glob.glob(os.path.join(folder, p)))
            if g: return g[0]
    diff = f('*_diff_*.jpg', '*_Color.jpg'); rough = f('*_rough_*.jpg', '*_Roughness.jpg'); nor = f('*_nor_gl_*.jpg', '*_NormalGL.jpg')
    if not diff: raise FileNotFoundError(f'no colour map in {folder}')
    return pbr(name, diff, rough, nor, scale=scale, **kw)


# ---------------------------------------------------------------- models
def import_gltf(path, location=(0, 0, 0), scale=1.0, rot_z_deg=0.0, collection=None):
    before = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=path)
    new = [o for o in bpy.data.objects if o not in before]
    roots = [o for o in new if o.parent is None or o.parent not in new]
    for o in roots:
        o.location = location; o.scale = (scale,) * 3; o.rotation_euler[2] += math.radians(rot_z_deg)
    if collection:
        for o in new:
            for c in list(o.users_collection): c.objects.unlink(o)
            collection.objects.link(o)
    return new


# ---------------------------------------------------------------- render look
def render_look(scene, samples=32, look='AgX - Medium High Contrast'):
    S = scene; c = S.cycles
    S.render.engine = 'CYCLES'
    # colour: AgX keeps bright saturated colours from clipping to flat cyan/yellow; a contrast look restores punch
    S.view_settings.view_transform = 'AgX'; S.view_settings.look = look
    S.view_settings.exposure = 0.0; S.view_settings.gamma = 1.0
    # sampling: low fixed count + adaptive + OIDN with albedo/normal guides is the best quality per second on CPU
    c.samples = samples; c.use_adaptive_sampling = True; c.adaptive_threshold = 0.02; c.adaptive_min_samples = 0
    c.use_denoising = True; c.denoiser = 'OPENIMAGEDENOISE'; c.denoising_input_passes = 'RGB_ALBEDO_NORMAL'
    c.denoising_prefilter = 'ACCURATE'
    try: c.denoising_quality = 'HIGH'          # 4.1+
    except Exception: pass
    c.denoising_use_gpu = False
    # bounces: enough for interiors (bounce light off walls) without wasting time
    c.max_bounces = 8; c.diffuse_bounces = 3; c.glossy_bounces = 3; c.transmission_bounces = 8
    c.volume_bounces = 0; c.transparent_max_bounces = 16
    c.sample_clamp_direct = 0.0; c.sample_clamp_indirect = 10.0   # kills fireflies that the denoiser turns into blotches
    c.blur_glossy = 1.0                                            # 'filter glossy': less noise in shiny surfaces
    c.caustics_reflective = False; c.caustics_refractive = False
    c.use_light_tree = True
    S.render.use_motion_blur = False   # see plan: Zack-style shots read crisp; enable per-shot only for whip moves
    S.render.film_transparent = False
    S.render.use_persistent_data = True
    return S


def skin_sss(mat, weight=0.25, radius=(1.0, 0.35, 0.2), scale=0.012):
    """Random Walk (Skin) SSS on any Principled BSDF in mat. scale is in metres (MakeHuman = 1 unit/m)."""
    for n in mat.node_tree.nodes:
        if n.type == 'BSDF_PRINCIPLED':
            n.subsurface_method = 'RANDOM_WALK_SKIN'
            n.inputs['Subsurface Weight'].default_value = weight
            n.inputs['Subsurface Radius'].default_value = radius
            n.inputs['Subsurface Scale'].default_value = scale


# ---------------------------------------------------------------- compositor
def compositor_finish(scene, glare=True, vignette=0.0, glare_threshold=1.0, glare_mix=-0.85, compositor_vignette=False):
    """Soft bloom on highlights. Cheap (2D, runs once per frame after render).
    LESSON (Kinda Wild ep_sneeze): the EllipseMask + relative-Blur vignette below rendered as a SHARP light oval in mid-frame
    (it looked like a skin patch on the cheek). The vignette is now done softly in post_kw.grade (max -15%), so `vignette`
    is IGNORED unless compositor_vignette=True is passed explicitly (kept only for old episodes)."""
    if not compositor_vignette: vignette = 0.0
    S = scene; S.use_nodes = True; nt = S.node_tree; nt.nodes.clear()
    rl = nt.nodes.new('CompositorNodeRLayers'); comp = nt.nodes.new('CompositorNodeComposite')
    cur = rl.outputs['Image']
    if glare:
        g = nt.nodes.new('CompositorNodeGlare'); g.glare_type = 'FOG_GLOW'; g.quality = 'MEDIUM'
        g.threshold = glare_threshold; g.mix = glare_mix; g.size = 8
        nt.links.new(cur, g.inputs['Image']); cur = g.outputs['Image']
    if vignette > 0:
        em = nt.nodes.new('CompositorNodeEllipseMask'); em.width = 0.95; em.height = 0.95
        bl = nt.nodes.new('CompositorNodeBlur'); bl.filter_type = 'GAUSS'; bl.use_relative = True
        bl.factor_x = 0.25; bl.factor_y = 0.25
        nt.links.new(em.outputs['Mask'], bl.inputs['Image'])
        mr = nt.nodes.new('CompositorNodeMapRange')          # mask 0..1 -> (1-vignette)..1
        mr.inputs['To Min'].default_value = 1.0 - vignette; mr.inputs['To Max'].default_value = 1.0
        nt.links.new(bl.outputs['Image'], mr.inputs['Value'])
        mx = nt.nodes.new('CompositorNodeMixRGB'); mx.blend_type = 'MULTIPLY'; mx.inputs['Fac'].default_value = 1.0
        nt.links.new(cur, mx.inputs[1]); nt.links.new(mr.outputs['Value'], mx.inputs[2]); cur = mx.outputs['Image']
    nt.links.new(cur, comp.inputs['Image'])
    return nt
