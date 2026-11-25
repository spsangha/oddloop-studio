"""Kinda Wild Films - cast v1.1 close-view layer (kindawild/cast/v11_brief.md part B).  Only active with KW_CAST=v1.1:
the default cast (v1.0) is untouched.  Applied once per HG person at graft time (heads_hg.graft), after skin tone/outfit.

B1 eyes   off-white sclera with a little of the HG vein map, shaded corners (AO), darker limbal ring, one catch-light
          (a small disc light on the camera, light-linked to the eyes only -> same clock position in both eyes).
B2 mouth  tongue low and darker mouth inside at wide jaw (see JAW in heads_hg / kwkit FACES speak/spoon/bite).
B3 skin   red zones (nose, cheeks, ears, knuckles) + darker lips from a per-vertex mask measured on the HG mesh
          (shape-key displacement maps + landmark falloffs); fine procedural pores on the face; tighter skin SSS.
"""
import os, math
import bpy, numpy as np
from mathutils import Vector as V, Matrix

def on(): return os.environ.get('KW_CAST', '') == 'v1.1'

SCLERA = (0.86, 0.83, 0.79)      # sclera tint (HG = pure white)
SCLERA_VEIN = 0.18               # share of the HG eye colour map (veins) kept in the white
CORNER_AO = 0.55                 # sclera brightness in the eye corners (AO = 0)
LIMBAL = 0.45                    # iris brightness at the limbal ring
CATCH = dict(size=0.16, power=6.0, off=(-0.22, 0.20, 0.0))   # disc (m), W, offset in camera space (10-11 o'clock)
RED = dict(nose=0.55, cheek=0.45, ear=0.55, knuckle=0.40)    # mask strengths
RED_TINT = (1.10, 0.80, 0.78)    # base colour multiplier at full red mask
LIP_TINT = (0.80, 0.60, 0.60)    # base colour multiplier at full lip mask
PORE = dict(scale=1600.0, strength=0.35, dist=0.0007)        # Voronoi cells per m (~0.7 mm), bump
MOUTH_IN = (0.16, 0.07, 0.07)    # mouth-inside colour multiplier (deep)
LASH = dict(children=8, radius=1.25, light=0.45, red=0.6)   # + lash/brow hair colour = head hair (HG had ginger 1.9/0.9)   # eyelash children per guide, thickness multiplier
SSS_SCALE = 0.005                # m (HG 0.01 reads waxy at close range)


def _nodes(m): return m.node_tree.nodes, m.node_tree.links


def eyes(G):
    eye = next((o for o in G.meshes if o.name.startswith('HG_Eyes')), None)
    if eye is None: return
    for m in eye.data.materials:
        if m is None or not m.name.startswith('.HG_Eyes_Inner'): continue
        N, L = _nodes(m)
        if 'kw11_ring' in N: continue
        sc = N.get('HG_Scelera_Color'); mk = N.get('Image Texture.002'); mix = N.get('Mix'); bsdf = N.get('Principled BSDF')
        if not (sc and mk and mix and bsdf): print('cast v1.1: eye nodes missing', m.name); continue
        # sclera: off-white, a little of the veined colour map
        inv = sc.inputs['Factor'].links[0].from_node
        f = N.new('ShaderNodeMath'); f.operation = 'MULTIPLY'; f.inputs[1].default_value = 1.0 - SCLERA_VEIN
        L.new(inv.outputs[0], f.inputs[0]); L.new(f.outputs[0], sc.inputs['Factor']); sc.inputs['B'].default_value = (*SCLERA, 1.0)
        # limbal ring: darker band on the soft edge of the iris mask
        rr = N.new('ShaderNodeValToRGB'); rr.name = 'kw11_ring'; e = rr.color_ramp; e.interpolation = 'EASE'
        e.elements[0].position = 0.0; e.elements[0].color = (1, 1, 1, 1); e.elements[1].position = 1.0; e.elements[1].color = (1, 1, 1, 1)
        mid = e.elements.new(0.45); mid.color = (LIMBAL, LIMBAL, LIMBAL, 1)
        e.elements.new(0.08).color = (1, 1, 1, 1); e.elements.new(0.85).color = (1, 1, 1, 1)
        L.new(mk.outputs['Color'], rr.inputs['Fac'])
        # corners: ambient occlusion on the eyeball (lids / caruncle shade the white)
        ao = N.new('ShaderNodeAmbientOcclusion'); ao.samples = 8; ao.inputs['Distance'].default_value = 0.006
        aor = N.new('ShaderNodeMapRange'); aor.inputs['To Min'].default_value = CORNER_AO
        L.new(ao.outputs['AO'], aor.inputs['Value'])
        m1 = N.new('ShaderNodeMix'); m1.data_type = 'RGBA'; m1.blend_type = 'MULTIPLY'; m1.inputs['Factor'].default_value = 1.0
        m2 = N.new('ShaderNodeMix'); m2.data_type = 'RGBA'; m2.blend_type = 'MULTIPLY'; m2.inputs['Factor'].default_value = 1.0
        src = bsdf.inputs['Base Color'].links[0].from_socket
        L.new(src, m1.inputs['A']); L.new(rr.outputs['Color'], m1.inputs['B'])
        L.new(m1.outputs['Result'], m2.inputs['A']); L.new(aor.outputs['Result'], m2.inputs['B'])
        L.new(m2.outputs['Result'], bsdf.inputs['Base Color'])
    print('cast v1.1: eyes', eye.name)


def catch_light(kr, G):
    """one disc light parked on the camera; it lights (and is seen in) the eyes only"""
    cam = getattr(kr, 'CAM', None); eye = next((o for o in G.meshes if o.name.startswith('HG_Eyes')), None)
    if cam is None or eye is None: return
    coll = bpy.data.collections.get('kw11_eyes') or bpy.data.collections.new('kw11_eyes')
    if eye.name not in coll.objects: coll.objects.link(eye)
    if bpy.data.objects.get('kw11_catch') is not None: return
    ld = bpy.data.lights.new('kw11_catch', 'AREA'); ld.shape = 'DISK'; ld.size = CATCH['size']; ld.energy = CATCH['power']
    ld.use_shadow = False
    lo = bpy.data.objects.new('kw11_catch', ld); bpy.context.scene.collection.objects.link(lo)
    lo.parent = cam; lo.matrix_parent_inverse = Matrix.Identity(4); lo.location = V(CATCH['off'])
    lo.visible_camera = False
    lo.light_linking.receiver_collection = coll
    lo.light_linking.blocker_collection = coll
    print('cast v1.1: catch light on', cam.name)


def _disp(body, key):
    kb = body.data.shape_keys.key_blocks
    if key not in kb: return None
    n = len(body.data.vertices); a = np.empty(n * 3); b = np.empty(n * 3)
    kb[key].data.foreach_get('co', a); kb[0].data.foreach_get('co', b)
    return np.linalg.norm((a - b).reshape(-1, 3), axis=1)


def _norm(d):
    if d is None: return 0.0
    return np.clip(d / max(np.percentile(d[d > 1e-6], 97) if np.any(d > 1e-6) else 1.0, 1e-6), 0, 1)


def skin_mask(G):
    """per-vertex (red, lip, face) mask on the HG body, in the body's rest (basis) space"""
    body, rig = G.body, G.rig
    n = len(body.data.vertices); co = np.empty(n * 3); body.data.shape_keys.key_blocks[0].data.foreach_get('co', co); co = co.reshape(-1, 3)
    B2M = body.matrix_world.inverted() @ rig.matrix_world
    bone = lambda nm: np.array(B2M @ rig.data.bones[nm].head_local) if nm in rig.data.bones else None
    eL, eR = bone('eyeball.L'), bone('eyeball.R'); E = (eL + eR) / 2; iod = np.linalg.norm(eL - eR)
    g = lambda c, s: np.exp(-np.sum((co - c) ** 2, axis=1) / (2 * s * s))
    # nose tip: most forward vertex on the midline below the eyes
    m = (np.abs(co[:, 0] - E[0]) < 0.008) & (co[:, 2] < E[2] - 0.01) & (co[:, 2] > E[2] - 0.07) & (np.abs(co[:, 1] - E[1]) < 0.15)
    tip = co[m][np.argmin(co[m][:, 1])]
    nose = g(tip, 0.012) + 0.6 * g(tip + np.array([0, 0.012, 0.012]), 0.010)
    cheek = np.zeros(n)
    for s in (-1, 1):
        c = E + np.array([s * 0.62 * iod, 0, -0.035]); mm = (np.abs(co[:, 0] - c[0]) < 0.006) & (np.abs(co[:, 2] - c[2]) < 0.006)
        if mm.any(): c = co[mm][np.argmin(co[mm][:, 1])]
        cheek += g(c, 0.020)
    cheek = np.maximum(cheek, 0.6 * _norm(_disp(body, 'cheekSquint_L')) + 0.6 * _norm(_disp(body, 'cheekSquint_R'))) if 'cheekSquint_L' in body.data.shape_keys.key_blocks else cheek
    ear = np.zeros(n)
    hm = (np.abs(co[:, 2] - E[2]) < 0.035) & (np.abs(co[:, 1] - E[1]) < 0.15)
    for s in (-1, 1):
        sm = hm & (s * (co[:, 0] - E[0]) > 0)
        if sm.any(): c = co[sm][np.argmax(s * (co[sm][:, 0] - E[0]))]; ear += g(c, 0.022)
    kn = np.zeros(n)
    for s in 'LR':
        for f in ('f_index.01', 'f_middle.01', 'f_ring.01', 'f_pinky.01', 'thumb.02'):
            c = bone(f'{f}.{s}')
            if c is not None: kn += g(c, 0.011)
    red = np.clip(RED['nose'] * nose + RED['cheek'] * np.clip(cheek, 0, 1) + RED['ear'] * ear + RED['knuckle'] * kn, 0, 1)
    lipd = sum(_norm(_disp(body, k)) for k in ('mouthRollLower', 'mouthRollUpper', 'mouthPucker')) / 3.0
    near_mouth = g(tip + np.array([0, 0.01, -0.035]), 0.016)
    lip = np.clip((lipd - 0.35) / 0.4, 0, 1) * np.clip(near_mouth * 2.0, 0, 1)
    face = np.clip(g(tip, 0.035) + g(E + np.array([0, -0.01, -0.03]), 0.045), 0, 1)
    # mouth inside (B2 'dark inside'): skin behind the lip line, inside the head, fading with depth
    M = tip + np.array([0, 0.012, -0.034]); lipy = co[lip > 0.5][:, 1].mean() if (lip > 0.5).any() else M[1]
    dep = co[:, 1] - (lipy + 0.004)
    box = (dep > 0) & (np.abs(co[:, 0] - M[0]) < 0.032) & (np.abs(co[:, 2] - M[2]) < 0.035) & (dep < 0.09)
    from mathutils.bvhtree import BVHTree
    bvh = BVHTree.FromPolygons([V(c) for c in co], [tuple(pl.vertices) for pl in body.data.polygons])
    inside = np.zeros(n, bool)
    for i in np.nonzero(box)[0]:      # inside the mouth = the face is in front of it (a forward ray hits the body again)
        o_ = V(co[i]) + V((0, -0.0015, 0)); hit = bvh.ray_cast(o_, V((0, -1, 0)), 0.08)
        inside[i] = hit[0] is not None
    inner = np.clip(dep / 0.012, 0, 1) * inside
    me = body.data
    at = me.color_attributes.get('kw11_skin') or me.color_attributes.new('kw11_skin', 'FLOAT_COLOR', 'POINT')
    col = np.stack([red, lip, face, inner], axis=1).ravel()
    at.data.foreach_set('color', col)
    print(f'cast v1.1: skin mask red max {red.max():.2f} mean {red.mean():.3f} lip verts {(lip > 0.5).sum()} face verts {(face > 0.5).sum()} inner verts {(inner > 0.5).sum()}')


def skin(G):
    skin_mask(G)
    for m in G.body.data.materials:
        if m is None or not m.use_nodes or not m.name.startswith('.Human'): continue
        N, L = _nodes(m)
        if 'kw11_attr' in N: continue
        bsdf = N.get('Principled BSDF')
        at = N.new('ShaderNodeAttribute'); at.name = 'kw11_attr'; at.attribute_name = 'kw11_skin'
        sp = N.new('ShaderNodeSeparateColor'); L.new(at.outputs['Color'], sp.inputs['Color'])
        src = bsdf.inputs['Base Color'].links[0].from_socket
        r = N.new('ShaderNodeMix'); r.data_type = 'RGBA'; r.blend_type = 'MULTIPLY'; r.inputs['B'].default_value = (*RED_TINT, 1)
        L.new(sp.outputs[0], r.inputs['Factor']); L.new(src, r.inputs['A'])
        lp = N.new('ShaderNodeMix'); lp.data_type = 'RGBA'; lp.blend_type = 'MULTIPLY'; lp.inputs['B'].default_value = (*LIP_TINT, 1)
        L.new(sp.outputs[1], lp.inputs['Factor']); L.new(r.outputs['Result'], lp.inputs['A'])
        dk = N.new('ShaderNodeMix'); dk.data_type = 'RGBA'; dk.blend_type = 'MULTIPLY'; dk.inputs['B'].default_value = (*MOUTH_IN, 1)
        L.new(at.outputs['Alpha'], dk.inputs['Factor']); L.new(lp.outputs['Result'], dk.inputs['A'])
        L.new(dk.outputs['Result'], bsdf.inputs['Base Color'])
        # pores: fine Voronoi pits in object space, face only
        tc = N.new('ShaderNodeTexCoord'); vo = N.new('ShaderNodeTexVoronoi'); vo.feature = 'F1'; vo.inputs['Scale'].default_value = PORE['scale']
        vo.inputs['Randomness'].default_value = 0.9
        L.new(tc.outputs['Object'], vo.inputs['Vector'])
        pr = N.new('ShaderNodeMapRange'); pr.inputs['From Min'].default_value = 0.0; pr.inputs['From Max'].default_value = 0.35
        L.new(vo.outputs['Distance'], pr.inputs['Value'])
        st = N.new('ShaderNodeMath'); st.operation = 'MULTIPLY'; st.inputs[1].default_value = PORE['strength']
        L.new(sp.outputs[2], st.inputs[0])
        bp = N.new('ShaderNodeBump'); bp.inputs['Distance'].default_value = PORE['dist']
        L.new(st.outputs[0], bp.inputs['Strength']); L.new(pr.outputs['Result'], bp.inputs['Height'])
        nsrc = bsdf.inputs['Normal'].links[0].from_socket
        L.new(nsrc, bp.inputs['Normal']); L.new(bp.outputs['Normal'], bsdf.inputs['Normal'])
        bsdf.inputs['Subsurface Scale'].default_value = SSS_SCALE
    print('cast v1.1: skin', G.p.name)


def lashes(G):
    for md in G.body.modifiers:
        if md.type != 'PARTICLE_SYSTEM' or 'Eyelash' not in md.particle_system.settings.name: continue
        st = md.particle_system.settings
        if st.get('kw11'): continue
        st.rendered_child_count = LASH['children']; st.child_percent = LASH['children']; st.radius_scale *= LASH['radius']
        st['kw11'] = 1
        for m in G.body.data.materials:
            if m is not None and m.name.startswith('.HG_Hair_Eye'):
                g = m.node_tree.nodes.get('HG_Hair')
                if g: g.inputs['Lightness'].default_value = LASH['light']; g.inputs['Redness'].default_value = LASH['red']
        print('cast v1.1: lashes', st.name, st.rendered_child_count, round(st.radius_scale, 4))


def apply(kr, p, G):
    if not on(): return
    eyes(G); skin(G); lashes(G)      # B1 catch-light: the kit key light already gives one per eye at the same clock position (catch_light() kept, unused)
    tl = next((o for o in G.meshes if o.name.startswith('HG_TeethLower')), None)
    G.v11_tongue = tl.data.shape_keys.key_blocks.get('tongue_down') if tl is not None and tl.data.shape_keys else None
