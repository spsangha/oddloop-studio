"""KW_HEADS=scan: scan-based faces on the MakeHuman head (same topology, rig, expression keys, UVs).
- face shape: ICT-FaceKit light-stage identity PCA (MIT, USC ICT) transferred to MakeHuman vertex deltas (assets/heads/ict_mh_deltas.npz);
  `seed` picks stable PCA coefficients, so every cast member gets a distinct, scan-plausible face.
- skin: Lee Perry-Smith head scan (CC BY 3.0, Infinite Realities) displacement / specular / colour baked to MakeHuman UVs
  (assets/heads/scan_*.jpg): real pores, lip lines, creases, oily T-zone and red zones layered on the MakeHuman photo skins.
Default ON since 2026-11-23 (DEFAULT below); env KW_HEADS=legacy -> the kit renders the old heads."""
import os, random, zlib
import numpy as np
HD = os.environ.get('KW_HEADS_DIR', os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'assets', 'heads'))
_D = None


DEFAULT = 'scan'   # approved by the lead 2026-11-23 after round 2; set to 'legacy' (or env KW_HEADS=legacy) to go back
def on(): return os.environ.get('KW_HEADS', DEFAULT) == 'scan'


def _deltas():
    global _D
    if _D is None:
        z = np.load(os.path.join(HD, 'ict_mh_deltas.npz')); _D = (z['idx'], z['d'].astype(np.float32))
    return _D


def coeffs(seed, n):
    r = random.Random(f'kw-scanface-{seed}')
    return np.array([max(-2.0, min(2.0, r.gauss(0.0, 1.0))) for _ in range(n)], np.float32)


def apply_shape(h, seed, gain=None):
    """add the seed's scan identity to the (already baked) body mesh, before rig/proxies are fitted."""
    idx, D = _deltas()
    g = float(os.environ.get('KW_HEADS_GAIN', gain if gain is not None else 1.4))   # round 2: 1.0 -> 1.4 (further from MakeHuman proportions)
    c = coeffs(seed, D.shape[0]); c[0] *= 0.5    # mode 0 is mostly overall head size: keep cast heads near one size
    dv = np.tensordot(c, D, 1) * g
    me = h.data
    co = np.zeros(len(me.vertices) * 3, np.float32); me.vertices.foreach_get('co', co); co = co.reshape(-1, 3)
    co[idx] += dv; me.vertices.foreach_set('co', co.ravel())
    if me.shape_keys:
        for kb in me.shape_keys.key_blocks:
            k = np.zeros(len(me.vertices) * 3, np.float32); kb.data.foreach_get('co', k); k = k.reshape(-1, 3); k[idx] += dv; kb.data.foreach_set('co', k.ravel())
    me.update()


def _img(path, nonc=True):
    import bpy
    im = bpy.data.images.load(path, check_existing=True)
    if nonc: im.colorspace_settings.name = 'Non-Color'
    return im


V0 = 990 / 2048   # MakeHuman UV: the face midline (x = 0) is the row v = V0 on the head island (u > 0.63)


def _seedr(seed, tag): return random.Random(f'kw-skin-{tag}-{seed}')


# face chroma of the MakeHuman photo skins (linear mean, measured on the face island): the old Asian male is far more orange
SKIN_CHROMA = {'middleage_african_female': .88, 'middleage_african_male': .85, 'middleage_asian_female': .62, 'middleage_asian_male': .67,
               'middleage_caucasian_female': .62, 'middleage_caucasian_male': .67, 'old_african_female': .96, 'old_african_male': .92,
               'old_asian_female': .73, 'old_asian_male': .84, 'old_caucasian_female': .58, 'old_caucasian_male': .70, 'young_african_female': .86,
               'young_african_male': .79, 'young_asian_female': .64, 'young_asian_male': .65, 'young_caucasian_female': .60, 'young_caucasian_male': .68}


def skin(p, age=0.5, gender=1.0, seed=0, skin_name=''):
    """scan skin on the shared MPFB skin group(s) of this person; idempotent per group.
    round 2: the scan's colour mottling over the photo albedo, per-seed variation of the scan detail (mirrored scan blended in
    by a seeded noise mask, seeded region weights), random-walk skin SSS with real-skin radii, sheen, oil only in the T-zone."""
    import bpy
    if os.environ.get('KW_SCAN_SKIN', '1') == '0': return
    done = set(); r = _seedr(seed, 'v')
    w_fore = r.uniform(0.35, 1.25) + 0.5 * age; w_eye = r.uniform(0.4, 1.2) + 0.6 * age; mir = r.random(); nz_w = r.uniform(0, 100)
    k_col = float(os.environ.get('KW_SCAN_COL', 1.0)) * (0.3 if 'african' in str(skin_name).lower() else 1.0)   # mottling read as freckles on dark skin
    for s_ in p.body.material_slots:
        m_ = s_.material
        if not m_ or not m_.node_tree: continue
        for g in m_.node_tree.nodes:
            if g.type != 'GROUP' or not g.node_tree or g.node_tree.name in done: continue
            gt = g.node_tree; done.add(gt.name)
            if 'kw_scan_h' in gt.nodes or 'Bump' not in gt.nodes: continue
            lips = 'lips' in m_.name.lower()
            N, L = gt.nodes, gt.links
            def nd(t, **kw):
                n_ = N.new(t)
                for k, v in kw.items(): setattr(n_, k, v)
                return n_
            def math(op, a, b, clamp=False):
                m = nd('ShaderNodeMath', operation=op, use_clamp=clamp)
                for i, x in enumerate((a, b)):
                    if isinstance(x, (int, float)): m.inputs[i].default_value = x
                    else: L.new(x, m.inputs[i])
                return m.outputs[0]
            uv = nd('ShaderNodeUVMap')
            # mirrored UV (face island only) and a seeded soft noise mask choosing between scan and mirrored scan per area
            sep = nd('ShaderNodeSeparateXYZ'); L.new(uv.outputs['UV'], sep.inputs[0])
            isf = math('GREATER_THAN', sep.outputs[0], 0.63)
            vm = math('SUBTRACT', 2 * V0, sep.outputs[1])
            vsel = nd('ShaderNodeMix', data_type='FLOAT'); L.new(isf, vsel.inputs[0]); L.new(sep.outputs[1], vsel.inputs[2]); L.new(vm, vsel.inputs[3])
            cmb = nd('ShaderNodeCombineXYZ'); L.new(sep.outputs[0], cmb.inputs[0]); L.new(vsel.outputs[0], cmb.inputs[1])
            nz = nd('ShaderNodeTexNoise', noise_dimensions='4D'); nz.inputs['Scale'].default_value = 4.0; nz.inputs['W'].default_value = nz_w; nz.inputs['Detail'].default_value = 1.0
            L.new(uv.outputs['UV'], nz.inputs['Vector'])
            mm = nd('ShaderNodeMapRange'); mm.inputs['From Min'].default_value = 0.5 - 0.08 + 0.25 * (mir - 0.5); mm.inputs['From Max'].default_value = 0.5 + 0.08 + 0.25 * (mir - 0.5)
            L.new(nz.outputs['Fac'], mm.inputs['Value']); mmask = math('MULTIPLY', math('MULTIPLY', mm.outputs['Result'], isf), float(os.environ.get('KW_SCAN_MIRROR', 0)))
            def tex(name, img, vec):
                t = nd('ShaderNodeTexImage'); t.name = name; t.image = _img(os.path.join(HD, img)); L.new(vec, t.inputs['Vector']); return t
            def tex2(name, img):   # scan / mirrored scan blend
                a_ = tex(name, img, uv.outputs['UV']); b_ = tex(name + '_m', img, cmb.outputs[0])
                mx = nd('ShaderNodeMix', data_type='RGBA'); L.new(mmask, mx.inputs[0]); L.new(a_.outputs['Color'], mx.inputs[6]); L.new(b_.outputs['Color'], mx.inputs[7])
                return mx.outputs[2]
            msk = tex('kw_scan_mask', 'scan_mask.jpg', uv.outputs['UV']); ms = nd('ShaderNodeSeparateColor'); L.new(msk.outputs['Color'], ms.inputs[0])
            # 1) scan height detail, region weights per seed -> extra bump in front of the existing bump chain
            hcol = tex2('kw_scan_h', 'scan_height.jpg'); hbw = nd('ShaderNodeRGBToBW'); L.new(hcol, hbw.inputs[0])
            wreg = math('ADD', math('ADD', 1.0, math('MULTIPLY', ms.outputs[0], w_fore - 1.0)), math('MULTIPLY', ms.outputs[1], w_eye - 1.0))
            hh = math('ADD', 0.5, math('MULTIPLY', math('SUBTRACT', hbw.outputs[0], 0.5), wreg))
            bm = nd('ShaderNodeBump'); bm.name = 'kw_scan_bump'
            bm.inputs['Strength'].default_value = float(os.environ.get('KW_SCAN_BUMP', 0.45 + 0.3 * age)) * (0.4 if 'african' in str(skin_name).lower() else 1.0)
            bm.inputs['Distance'].default_value = 0.002
            L.new(hh, bm.inputs['Height'])
            old = gt.nodes['Bump']
            src = old.inputs['Normal'].links[0].from_socket if old.inputs['Normal'].links else None
            if src is not None: L.new(src, bm.inputs['Normal'])
            L.new(bm.outputs['Normal'], old.inputs['Normal'])
            # 2) specular map -> roughness variation (oily nose/forehead, matte cheeks) and a thin oil coat only where oily
            sp = tex2('kw_scan_s', 'scan_spec.jpg'); spb = nd('ShaderNodeRGBToBW'); L.new(sp, spb.inputs[0])
            bsdfs = [n for n in N if n.type == 'BSDF_PRINCIPLED']
            for b in bsdfs:
                ri = b.inputs['Roughness']; rs = ri.links[0].from_socket if ri.links else None
                mr = nd('ShaderNodeMapRange'); mr.inputs['To Min'].default_value = 1.25; mr.inputs['To Max'].default_value = 0.72
                L.new(spb.outputs[0], mr.inputs['Value'])
                mu = nd('ShaderNodeMath', operation='MULTIPLY', use_clamp=True)
                if rs is not None: L.new(rs, mu.inputs[0])
                else: mu.inputs[0].default_value = ri.default_value
                L.new(mr.outputs['Result'], mu.inputs[1]); L.new(mu.outputs[0], ri)
                for nm in ('Coat Weight',):
                    for l in list(b.inputs[nm].links): L.remove(l)
                cw = math('MULTIPLY', math('MAXIMUM', math('SUBTRACT', spb.outputs[0], 0.5), 0.0), 0.0 if lips else 0.25 * float(os.environ.get('KW_SCAN_LOBES', 1)))
                L.new(cw, b.inputs['Coat Weight']); b.inputs['Coat Roughness'].default_value = 0.3
                for l in list(b.inputs['Coat Roughness'].links): L.remove(l)
                # skin: random-walk skin SSS, real-skin mean free paths (mm), forward scattering; peach-fuzz sheen
                b.subsurface_method = os.environ.get('KW_SCAN_SSSM', 'BURLEY')   # random-walk skin cost +50% render time
                sw = b.inputs['Subsurface Weight']; ssrc = sw.links[0].from_node if sw.links else None
                for l in list(sw.links) + list(b.inputs['Subsurface Radius'].links): L.remove(l)
                sw.default_value = float(os.environ.get('KW_SCAN_SSS', 0.0))   # any SSS weight > 0 costs about +50% frame time (budget +25%)
                b.inputs['Subsurface Radius'].default_value = (1.0, 0.42, 0.24); b.inputs['Subsurface Scale'].default_value = 0.0035
                if 'Subsurface Anisotropy' in b.inputs: b.inputs['Subsurface Anisotropy'].default_value = float(os.environ.get('KW_SCAN_ANISO', 0.75))
                b.inputs['Sheen Weight'].default_value = 0.0 if lips else (0.06 if 'african' in str(skin_name).lower() else 0.18) * float(os.environ.get('KW_SCAN_LOBES', 1)); b.inputs['Sheen Roughness'].default_value = 0.35
                b.inputs['Sheen Tint'].default_value = (1.0, 0.93, 0.88, 1)
            # 3) colour: the scan's own mottling (multiplicative, mean 1), red zones; women lose the scan's stubble shadow
            hs = N.get('kw_skin_hs')
            if hs is not None:
                ch = SKIN_CHROMA.get(skin_name, 0.66); tgt = 0.82 if 'african' in skin_name else 0.65
                hs.inputs['Saturation'].default_value = max(0.95, min(1.45, 1.4 * (tgt / ch) ** 1.5))
            base_in = next((b.inputs['Base Color'] for b in bsdfs), None)
            if base_in is not None and base_in.links:
                src = base_in.links[0].from_socket
                cc = tex2('kw_scan_c', 'scan_col.jpg')
                vsub = nd('ShaderNodeVectorMath', operation='SUBTRACT'); L.new(cc, vsub.inputs[0]); vsub.inputs[1].default_value = (0.5, 0.5, 0.5)
                stub = 0.9 if gender < 0.5 else 0.15
                kk = math('MULTIPLY', math('MULTIPLY', math('SUBTRACT', 1.0, math('MULTIPLY', ms.outputs[2], stub)), math('SUBTRACT', 1.0, math('MULTIPLY', ms.outputs[1], 0.5))), 1.2 * k_col)
                vsc = nd('ShaderNodeVectorMath', operation='SCALE'); L.new(vsub.outputs[0], vsc.inputs[0]); L.new(kk, vsc.inputs['Scale'])
                vex = nd('ShaderNodeVectorMath', operation='ADD'); L.new(vsc.outputs[0], vex.inputs[0]); vex.inputs[1].default_value = (1, 1, 1)
                mul = nd('ShaderNodeVectorMath', operation='MULTIPLY'); L.new(src, mul.inputs[0]); L.new(vex.outputs[0], mul.inputs[1])
                cur = mul.outputs[0]
                tc = tex('kw_scan_r', 'scan_red.jpg', uv.outputs['UV'])
                mx = nd('ShaderNodeMix', data_type='RGBA', blend_type='MULTIPLY'); mx.inputs[7].default_value = (1.0, 0.72, 0.68, 1)
                L.new(math('MULTIPLY', math('MULTIPLY', tc.outputs['Color'], math('SUBTRACT', 1.0, math('MULTIPLY', ms.outputs[1], 0.8))), float(os.environ.get('KW_SCAN_RED', 0.8)) * (0.5 if 'african' in str(skin_name).lower() else 1.0)), mx.inputs[0])
                L.new(cur, mx.inputs[6])
                # flush (KW.pose(flush=v)): per-object property kw_flush 0..1 set by flush(); strongest in the red zones
                fa = nd('ShaderNodeAttribute', attribute_type='OBJECT', attribute_name='kw_flush')
                ff = math('MULTIPLY', fa.outputs['Fac'], math('ADD', 0.55, math('MULTIPLY', tc.outputs['Color'], 0.9)))
                fx = nd('ShaderNodeMix', data_type='RGBA', blend_type='MULTIPLY', clamp_factor=True); fx.inputs[7].default_value = (1.0, 0.4, 0.36, 1)
                L.new(ff, fx.inputs[0]); L.new(mx.outputs[2], fx.inputs[6])
                for b in bsdfs: L.new(fx.outputs[2], b.inputs['Base Color'])


EYE = {'EyeWhiteColor': (0.80, 0.75, 0.72, 1), 'IrisToEyeWhiteRelation': 0.44, 'IrisSection4Color': (0.02, 0.02, 0.03, 1),
       'IrisBumpStrength': 0.25, 'Clearcoat': 0.12, 'OuterLayerIOR': 1.376, 'InnerLayerRoughness': 0.28}


def _mpfb_dir():
    try:
        import bl_ext.user_default.mpfb as M; return os.path.dirname(M.__file__)
    except Exception: return os.path.expanduser('~/.config/blender/4.2/extensions/.user/user_default/mpfb')


EYE_TEX = {'darkbrown': ('brown', 0.55), 'brown': ('brown', 0.9), 'blue': ('blue', 1.0), 'green': ('green', 1.0), 'lightblue': ('lightblue', 1.0)}


def eyes(p, colour='brown'):
    """round 2: the MakeHuman CC0 photo eye texture (iris fibres, limbal ring, sclera veins) in place of the procedural iris,
    local occlusion (lids shade the eyeball), slightly damp sclera; the MPFB cornea layer (transmission + coat) stays."""
    import bpy
    tn, val = EYE_TEX.get(colour, ('brown', 0.9))
    path = os.path.join(_mpfb_dir(), 'data', 'eyes', 'materials', f'{tn}_eye.png')
    for o in p.parts:
        if o.type != 'MESH' or 'high-poly' not in o.name.lower() or not o.active_material or not o.active_material.node_tree: continue
        for nd in o.active_material.node_tree.nodes:
            for k, v in EYE.items():
                if k in nd.inputs: nd.inputs[k].default_value = v
            if nd.type != 'GROUP' or not nd.node_tree or 'IrisEyeWhiteColorSwitch' not in nd.node_tree.nodes or not os.path.exists(path): continue
            nd.node_tree = nd.node_tree.copy(); gt = nd.node_tree; N, L = gt.nodes, gt.links
            sw = N['InnerOuterLayerColorSwitch']
            uv = N.new('ShaderNodeUVMap'); tx = N.new('ShaderNodeTexImage'); tx.name = 'kw_eye_tex'; tx.image = bpy.data.images.load(path, check_existing=True)
            L.new(uv.outputs['UV'], tx.inputs['Vector'])
            hs = N.new('ShaderNodeHueSaturation'); hs.inputs['Value'].default_value = 0.92; L.new(tx.outputs['Color'], hs.inputs['Color'])
            # darker iris for dark-brown eyes: the iris is the saturated part of the texture
            sep = N.new('ShaderNodeSeparateColor'); sep.mode = 'HSV'; L.new(tx.outputs['Color'], sep.inputs[0])
            ir = N.new('ShaderNodeMapRange'); ir.inputs['From Min'].default_value = 0.25; ir.inputs['From Max'].default_value = 0.45; L.new(sep.outputs[1], ir.inputs['Value'])
            dk = N.new('ShaderNodeMix'); dk.data_type = 'RGBA'; dk.blend_type = 'MULTIPLY'; L.new(ir.outputs['Result'], dk.inputs[0])
            L.new(hs.outputs['Color'], dk.inputs[6]); dk.inputs[7].default_value = (val, val, val, 1)
            ao = N.new('ShaderNodeAmbientOcclusion'); ao.samples = int(os.environ.get('KW_SCAN_EYEAO', 8)); ao.inputs['Distance'].default_value = 0.012; ao.only_local = False
            L.new(dk.outputs[2], ao.inputs['Color'])
            aom = N.new('ShaderNodeMix'); aom.data_type = 'RGBA'; aom.blend_type = 'MULTIPLY'; aom.inputs[0].default_value = 1.0
            L.new(ao.outputs['Color'], aom.inputs[6]); 
            aor = N.new('ShaderNodeMapRange'); aor.inputs['To Min'].default_value = 0.35; L.new(ao.outputs['AO'], aor.inputs['Value'])
            L.new(aor.outputs['Result'], aom.inputs[7])
            L.new(aom.outputs[2], sw.inputs['Color2'])
            # fibre relief from the texture instead of the procedural iris bump
            bw = N.new('ShaderNodeRGBToBW'); L.new(tx.outputs['Color'], bw.inputs[0])
            msw = N['MainBumpmapSwitch']; L.new(bw.outputs[0], msw.inputs['Section2Color'])


def lashes(p):
    """dark, dense lash line (the card lashes rendered pale brown and the eyes read as stickers)"""
    for o in p.parts:
        if o.type != 'MESH' or 'eyelash' not in o.name.lower() or not o.active_material or not o.active_material.node_tree: continue
        nt = o.active_material.node_tree
        tx = nt.nodes.get('diffuseTexture')
        if tx is None or 'kw_lash' in nt.nodes: continue
        hs = nt.nodes.new('ShaderNodeHueSaturation'); hs.name = 'kw_lash'; hs.inputs['Value'].default_value = 0.2; hs.inputs['Saturation'].default_value = 0.6
        for l in list(tx.outputs['Color'].links):
            to = l.to_socket; nt.links.remove(l); nt.links.new(hs.outputs['Color'], to)
        nt.links.new(tx.outputs['Color'], hs.inputs['Color'])


def lips(p):
    for s_ in p.body.material_slots:
        m_ = s_.material
        if m_ and m_.node_tree and 'lips' in m_.name.lower():
            for g in m_.node_tree.nodes:
                if g.type == 'GROUP' and 'Roughness' in g.inputs: g.inputs['Roughness'].default_value = 0.48
                if g.type == 'GROUP' and 'Clearcoat' in g.inputs: g.inputs['Clearcoat'].default_value = 0.0


# ---------------------------------------------------------------------------------------------------------------- strand hair
# Real strand hair (Cycles curves + Principled Hair BSDF) grown procedurally on the MakeHuman scalp for the short styles,
# replacing the alpha-card shells, which read as plastic helmets. Long/bob/ponytail/braid styles keep their cards.
CURVE_STYLES = {   # style -> (strands, length top m, length sides m, flatness 0..1, comb (x, y, z) in head space, curl)
    'short01': (44000, 0.045, 0.014, 0.75, (0.35, 0.55, 0.0), 0.0),    # side-swept
    'short02': (44000, 0.035, 0.012, 0.7, (0.1, 0.8, 0.15), 0.05),    # short back, some lift on top
    'short03': (42000, 0.055, 0.016, 0.62, (0.15, 0.35, 0.15), 0.15),  # longer, messy
    'short04': (40000, 0.012, 0.007, 0.80, (0.0, 0.6, 0.0), 0.0),      # buzz
    'coil':    (52000, 0.016, 0.009, 0.25, (0.0, 0.0, 0.2), 0.6),      # tight short coils (African short styles)
    'afro01':  (34000, 0.040, 0.022, 0.05, (0.0, 0.0, 0.3), 1.0),      # short coils
}
FALL_STYLES = {    # style -> (strands, end height above the lowest scalp point m (negative = below), curl)
    'bob01': (28000, -0.07, 0.12), 'bob02': (28000, -0.05, 0.0), 'long01': (30000, -0.22, 0.05)}   # round 2: halved (render time), strands thicker


def _hair_mat(name, hv, seed):
    import bpy
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; N, L = nt.nodes, nt.links
    for n in list(N):
        if n.type != 'OUTPUT_MATERIAL': N.remove(n)
    out = next(n for n in N if n.type == 'OUTPUT_MATERIAL')
    hb = N.new('ShaderNodeBsdfHairPrincipled'); hb.parametrization = 'MELANIN'
    try: hb.model = 'CHIANG'
    except Exception: pass
    grey = hv > 1.0
    mel = 0.25 if grey else max(0.7, min(0.99, 0.99 - 0.16 * hv))   # round 2: darker (eatmore: hv 0.8 read grey-brown)
    hb.inputs['Melanin'].default_value = mel
    hb.inputs['Melanin Redness'].default_value = 0.25 if grey else 0.45
    hb.inputs['Roughness'].default_value = 0.36 if grey else 0.42; hb.inputs['Radial Roughness'].default_value = 0.5; hb.inputs['Coat'].default_value = 0.0; hb.inputs['IOR'].default_value = 1.45
    if 'Random Roughness' in hb.inputs: hb.inputs['Random Roughness'].default_value = 0.3
    if 'Random Color' in hb.inputs: hb.inputs['Random Color'].default_value = 0.15
    if grey:   # grey/white: a share of strands with almost no pigment
        hi = N.new('ShaderNodeHairInfo'); gt_ = N.new('ShaderNodeMath'); gt_.operation = 'LESS_THAN'
        gt_.inputs[1].default_value = (0.6 if hv < 1.5 else 0.3) if hv < 2.0 else (0.15 if hv < 2.4 else 0.05)   # share of pigmented strands left (round 2: old = white)
        mr = N.new('ShaderNodeMapRange'); mr.inputs['To Min'].default_value = 0.02; mr.inputs['To Max'].default_value = 0.55
        L.new(hi.outputs['Random'], gt_.inputs[0]); L.new(gt_.outputs[0], mr.inputs['Value']); L.new(mr.outputs['Result'], hb.inputs['Melanin'])
        hb.inputs['Melanin Redness'].default_value = 0.08
    L.new(hb.outputs[0], out.inputs['Surface'])
    return m


def strand_hair(p, style, hv, seed, african=False):
    """grow curves on the scalp, bone-parent them to the head; returns the object (also appended to p.parts) or None"""
    import bpy
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
    if style not in CURVE_STYLES and style not in FALL_STYLES: return None
    if style in FALL_STYLES and os.environ.get('KW_SCAN_LONGHAIR', '0') != '1': return None   # long/bob strands: ~+90% frame time, opt-in
    if african and style.startswith('short'): style = 'coil'
    fall = style in FALL_STYLES
    n, l_top, l_side, flat, comb, curl = CURVE_STYLES[style] if not fall else (FALL_STYLES[style][0], 0, 0, 0.5, (0.6, 0.6, 0.0), FALL_STYLES[style][2])
    n = int(n * float(os.environ.get('KW_HAIR_DENSITY', 1.0)) * (1.15 if not fall and style != 'afro01' else 1.0))   # round 2: denser short hair (1.6 cost +35% render time; thicker strands instead)
    b = p.body; me = b.data; mw = b.matrix_world
    gi = b.vertex_groups.get('scalp'); gb = b.vertex_groups.get('body')
    if gi is None: return None
    V = np.array([mw @ v.co for v in me.vertices]); W = np.zeros(len(V))
    for v in me.vertices:
        for g in v.groups:
            if g.group == gi.index: W[v.index] = g.weight
    body = np.zeros(len(V), bool)
    for v in me.vertices:
        for g in v.groups:
            if gb is not None and g.group == gb.index and g.weight > 0.5: body[v.index] = True
    tris = [t.vertices[:] for t in me.loop_triangles] if me.loop_triangles else None
    if not tris: me.calc_loop_triangles(); tris = [t.vertices[:] for t in me.loop_triangles]
    T = np.array(tris); tb = body[T].all(1)
    bvh = BVHTree.FromPolygons([Vector(v) for v in V], T[tb].tolist())
    ts = T[(W[T].mean(1) > 0.3) & tb]   # round 2: down to the scalp group edge (0.5 read as a receding hairline)
    if len(ts) == 0: return None
    A, B, C = V[ts[:, 0]], V[ts[:, 1]], V[ts[:, 2]]
    area = 0.5 * np.linalg.norm(np.cross(B - A, C - A), axis=1)
    rng = np.random.default_rng(zlib.crc32(f'kw-hair-{seed}'.encode()))   # stable across processes (str hash is salted)
    pick = rng.choice(len(ts), n, p=area / area.sum())
    u, v_ = rng.random(n), rng.random(n); sw = u + v_ > 1; u[sw], v_[sw] = 1 - u[sw], 1 - v_[sw]
    R0 = A[pick] + u[:, None] * (B[pick] - A[pick]) + v_[:, None] * (C[pick] - A[pick])
    wr = (1 - u - v_) * W[ts[pick, 0]] + u * W[ts[pick, 1]] + v_ * W[ts[pick, 2]]
    keep = rng.random(n) < np.clip((wr - 0.3) / 0.3, 0.3, 1.0)            # soft hairline instead of a hard shell edge
    pick, u, v_, R0 = pick[keep], u[keep], v_[keep], R0[keep]; n = len(R0)
    Nf = np.cross(B - A, C - A)[pick]; Nf /= np.linalg.norm(Nf, axis=1, keepdims=True) + 1e-9
    hc = V[W > 0.5].mean(0); top = V[W > 0.5][:, 2].max(); bot = V[W > 0.5][:, 2].min()
    Nf *= np.sign(((R0 - hc) * Nf).sum(1))[:, None]      # outward
    # head frame: rig forward is -Y; comb is given in (x = character left->right parting, y = backwards, z = up)
    cdir = np.array(comb, float)
    hz = np.clip((R0[:, 2] - bot) / max(top - bot, 1e-3), 0, 1)           # 0 at the nape/sideburns, 1 at the crown
    front = np.clip((hc[1] - R0[:, 1]) / 0.08, 0, 1)                       # 1 at the hairline (rig faces -Y)
    length = (l_side + (l_top - l_side) * hz ** 1.5) * (0.75 + 0.5 * rng.random(n)) * (1 - 0.15 * front * (style != 'afro01'))
    K = 7 if curl < 0.5 else 12
    jit = rng.random(n)
    if fall:
        flat = 0.88; K = 12; ez = (V[W > 0.5][:, 2].max() + bot) / 2   # roughly eye height
        z_end = bot + FALL_STYLES[style][1] + 0.02 * rng.random(n)
        length = (R0[:, 2] - z_end) * 1.2 + 0.05 + 0.04 * hz
    P = np.zeros((n, K, 3)); P[:, 0] = R0
    # comb: sideways away from a parting (x sign), backwards, and down the sides
    side = np.sign(R0[:, 0] - hc[0] - 0.02 * (cdir[0] > 0))
    cv = np.stack([cdir[0] * side, np.full(n, cdir[1]), np.full(n, -0.2) + cdir[2]], 1)
    cv = cv - (cv * Nf).sum(1)[:, None] * Nf; cv /= np.linalg.norm(cv, axis=1, keepdims=True) + 1e-9
    d = Nf * (1 - flat) + cv * flat + 0.25 * rng.normal(size=(n, 3)) * (0.3 + curl)
    d /= np.linalg.norm(d, axis=1, keepdims=True)
    seg = length / (K - 1); off = 0.0012 + 0.0006 * rng.random(n)
    ph = rng.random(n) * 6.283; cr = 0.0025 * curl
    e1 = np.cross(Nf, np.array([0.3, 0.2, 1.0])); e1 /= np.linalg.norm(e1, axis=1, keepdims=True); e2 = np.cross(Nf, e1)
    for k in range(1, K):
        q = P[:, k - 1] + d * seg[:, None]
        if curl > 0: q = q + (np.cos(ph + k * 1.9)[:, None] * e1 + np.sin(ph + k * 1.9)[:, None] * e2) * cr
        for i in range(n):   # keep the strand outside the scalp (simple projection; hair lies on the head)
            loc, nr, _, dist = bvh.find_nearest(Vector(q[i]))
            if loc is None: continue
            lo = np.array(loc[:]); nn = np.array(nr[:])
            lim = off[i] * (1 + (0.22 if fall else 0.6) * k * flat)
            if (q[i] - lo) @ nn < lim: q[i] = lo + nn * lim
        if fall:   # never across the face: strands in front of the forehead plane move out to the side
            fx_ = 0.068 + 0.02 * jit
            fr = (q[:, 1] < hc[1] - 0.045) & (np.abs(q[:, 0] - hc[0]) < fx_) & (q[:, 2] < top - 0.03)
            q[fr, 0] = hc[0] + np.sign(q[fr, 0] - hc[0] + 1e-6) * fx_[fr]
        nd_ = q - P[:, k - 1]; nd_ /= np.linalg.norm(nd_, axis=1, keepdims=True) + 1e-9
        if fall:
            g_ = min(1.0, 0.1 + 0.16 * k)
            d = nd_ * (1 - g_) + np.array([0, 0.08, -1.0]) * g_ + 0.05 * rng.normal(size=(n, 3))
            q2 = q - hc; q2[:, 2] = 0; d += 0.15 * q2 / (np.linalg.norm(q2, axis=1, keepdims=True) + 1e-9) * (k < 6)
        else:
            d = nd_ * 0.8 + (cv * flat + np.array([0, 0, -0.15 * flat])) * 0.2
        d /= np.linalg.norm(d, axis=1, keepdims=True)
        P[:, k] = q
    # round 2: clumps (strands pulled toward a leader strand toward the tips) + frizz: long hair read as a smooth curtain
    cl = (0.55 if fall else 0.3) * float(os.environ.get('KW_HAIR_CLUMP', 1.0))
    if cl > 0 and n > 100:
        m_ = max(20, n // (35 if fall else 60)); lead = rng.choice(n, m_, replace=False); near = np.zeros(n, int)
        for i0 in range(0, n, 4000):
            dd_ = ((R0[i0:i0 + 4000, None, :] - R0[None, lead, :]) ** 2).sum(-1); near[i0:i0 + 4000] = lead[dd_.argmin(1)]
        cf = cl * (0.6 + 0.4 * rng.random(n))
        for k in range(1, K):
            t_ = (k / (K - 1)) ** 1.3
            tg = 0.5 * P[near, k] + 0.5 * (P[:, 0] + P[near, k] - P[near, 0])
            P[:, k] += (tg - P[:, k]) * (cf * t_)[:, None]
        fz = (0.0025 if fall else 0.0008) * (rng.random(n) < 0.12)
        for k in range(2, K): P[:, k] += rng.normal(size=(n, 3)) * fz[:, None] * (k / (K - 1))
    cu = bpy.data.hair_curves.new(f'{p.name}_strands')
    cu.add_curves([K] * n)
    cu.position_data.foreach_set('vector', P.reshape(-1).astype(np.float32))
    rad = np.linspace(1.0, 0.4, K)[None, :] * (0.00011 + 0.00005 * rng.random(n))[:, None] * (1.4 if fall else 1.25)
    ra = cu.attributes.get('radius') or cu.attributes.new('radius', 'FLOAT', 'POINT')
    ra.data.foreach_set('value', rad.reshape(-1).astype(np.float32))
    cu.materials.append(_hair_mat(f'{p.name}_hairmat', hv, seed))
    ob = bpy.data.objects.new(f'{p.name}_hair_strands', cu); bpy.context.scene.collection.objects.link(ob)
    hb = p.rig.pose.bones['head']; M = (p.rig.matrix_world @ hb.matrix).inverted()
    bpy.context.view_layer.update()
    ob.parent = p.rig; ob.parent_type = 'BONE'; ob.parent_bone = 'head'
    bpy.context.view_layer.update(); ob.matrix_world = mw.__class__.Identity(4)
    p.parts.append(ob)
    _scalp_tint(p, W, hv)
    return ob


def scalp_weights(p):
    b = p.body; gi = b.vertex_groups.get('scalp'); W = np.zeros(len(b.data.vertices))
    if gi is None: return W
    for v in b.data.vertices:
        for g in v.groups:
            if g.group == gi.index: W[v.index] = g.weight
    return W


def card_hair_fix(p, card_objs, hv):
    """card hair kept (KW_SCAN_HAIR=0 or styles without strands): hair-coloured scalp under the cards, denser card alpha,
    so the sides never show grey see-through patches"""
    _scalp_tint(p, scalp_weights(p), hv)
    for o in card_objs:
        m = o.active_material
        if not m or not m.node_tree or 'kw_alpha' in m.node_tree.nodes: continue
        nt = m.node_tree; bs = next((n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'), None)
        if bs is None or not bs.inputs['Alpha'].links: continue
        src = bs.inputs['Alpha'].links[0].from_socket
        mu = nt.nodes.new('ShaderNodeMath'); mu.name = 'kw_alpha'; mu.operation = 'MULTIPLY'; mu.use_clamp = True; mu.inputs[1].default_value = 1.8
        nt.links.new(src, mu.inputs[0]); nt.links.new(mu.outputs[0], bs.inputs['Alpha'])


def _scalp_tint(p, W, hv):
    """skin under strand hair takes the hair colour (no pink scalp between strands)"""
    me = p.body.data
    ca = me.color_attributes.get('kw_scalp') or me.color_attributes.new('kw_scalp', 'FLOAT_COLOR', 'POINT')
    col = (0.45, 0.45, 0.46) if hv > 1 else tuple(a + (b - a) * max(0.0, min(1.0, hv)) for a, b in zip((0.010, 0.008, 0.006), (0.11, 0.07, 0.04)))
    w = np.clip((W - 0.25) / 0.45, 0, 1); w = w * w * (3 - 2 * w)   # round 2: full hair colour under the strands (low res/8 samples read the scalp)
    data = np.zeros((len(me.vertices), 4), np.float32); data[:, :3] = col; data[:, 3] = w
    ca.data.foreach_set('color', data.ravel())
    for s_ in p.body.material_slots:
        m_ = s_.material
        if not m_ or not m_.node_tree: continue
        for g in m_.node_tree.nodes:
            if g.type != 'GROUP' or not g.node_tree or 'kw_scalp_mix' in g.node_tree.nodes: continue
            gt = g.node_tree; N, L = gt.nodes, gt.links
            bs = next((n for n in N if n.type == 'BSDF_PRINCIPLED'), None)
            if bs is None or not bs.inputs['Base Color'].links: continue
            src = bs.inputs['Base Color'].links[0].from_socket
            at = N.new('ShaderNodeAttribute'); at.attribute_name = 'kw_scalp'
            mx = N.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.name = 'kw_scalp_mix'
            L.new(at.outputs['Alpha'], mx.inputs[0]); L.new(src, mx.inputs[6]); L.new(at.outputs['Color'], mx.inputs[7]); L.new(mx.outputs[2], bs.inputs['Base Color'])


# ---------------------------------------------------------------------------------------------------------------- brows / beard
def _deform_group():
    import bpy
    ng = bpy.data.node_groups.get('kw_deform_on_surface')
    if ng: return ng
    ng = bpy.data.node_groups.new('kw_deform_on_surface', 'GeometryNodeTree')
    ng.interface.new_socket('Geometry', in_out='INPUT', socket_type='NodeSocketGeometry')
    ng.interface.new_socket('Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')
    gi = ng.nodes.new('NodeGroupInput'); go = ng.nodes.new('NodeGroupOutput'); d = ng.nodes.new('GeometryNodeDeformCurvesOnSurface')
    ng.links.new(gi.outputs[0], d.inputs[0]); ng.links.new(d.outputs[0], go.inputs[0])
    return ng


def card_strands(p, objs, kind, hv, seed):
    """strands grown where an alpha card (eyebrow / beard) is opaque, attached to the body surface (Deform Curves on Surface),
    so they follow brow raises, jaw and expressions exactly like the skin. Returns the curves object or None."""
    import bpy
    from mathutils import Vector
    from mathutils.bvhtree import BVHTree
    b = p.body; me = b.data; mw = b.matrix_world; mwi = mw.inverted()
    uvl = me.uv_layers.active
    if uvl is None: return None
    me.calc_loop_triangles()
    V = np.array([mw @ v.co for v in me.vertices])
    LT = me.loop_triangles; T = np.array([t.vertices[:] for t in LT]); TL = np.array([t.loops[:] for t in LT])
    UV = np.zeros(len(me.loops) * 2, np.float32); uvl.data.foreach_get('uv', UV); UV = UV.reshape(-1, 2)
    bvh = BVHTree.FromPolygons([Vector(v) for v in V], T.tolist())
    rng = np.random.default_rng(zlib.crc32(f'kw-{kind}-{seed}'.encode()))
    pts, nrm, suv = [], [], []
    for o in objs:
        m = o.active_material; tx = next((n for n in m.node_tree.nodes if n.type == 'TEX_IMAGE' and n.image), None) if m and m.node_tree else None
        if tx is None: continue
        im = tx.image; w_, h_ = im.size; px = np.array(im.pixels[:], np.float32).reshape(h_, w_, -1)[..., -1]
        om = o.data; om.calc_loop_triangles(); ow = o.matrix_world
        OV = np.array([ow @ v.co for v in om.vertices]); OT = np.array([t.vertices[:] for t in om.loop_triangles]); OL = np.array([t.loops[:] for t in om.loop_triangles])
        OUV = np.zeros(len(om.loops) * 2, np.float32); om.uv_layers.active.data.foreach_get('uv', OUV); OUV = OUV.reshape(-1, 2)
        A, B_, C = OV[OT[:, 0]], OV[OT[:, 1]], OV[OT[:, 2]]; ar = 0.5 * np.linalg.norm(np.cross(B_ - A, C - A), axis=1)
        n = int(ar.sum() * (2.6e7 if kind == 'brow' else 1.6e7))
        n = min(n, 9000 if kind == 'brow' else 40000)
        if n <= 0: continue
        k = rng.choice(len(OT), n, p=ar / ar.sum()); u, v = rng.random(n), rng.random(n); s = u + v > 1; u[s], v[s] = 1 - u[s], 1 - v[s]
        P = A[k] + u[:, None] * (B_[k] - A[k]) + v[:, None] * (C[k] - A[k])
        tuv = OUV[OL[k, 0]] * (1 - u - v)[:, None] + OUV[OL[k, 1]] * u[:, None] + OUV[OL[k, 2]] * v[:, None]
        al = px[np.clip((tuv[:, 1] % 1) * h_, 0, h_ - 1).astype(int), np.clip((tuv[:, 0] % 1) * w_, 0, w_ - 1).astype(int)]
        keep = rng.random(n) < np.clip((al - 0.15) / 0.6, 0, 1)
        for q in P[keep]:
            loc, nr, ti, dist = bvh.find_nearest(Vector(q))
            if loc is None or dist > 0.012: continue
            loc = np.array(loc[:]); t3 = T[ti]; a_, b2, c2 = V[t3]
            v0, v1, v2 = b2 - a_, c2 - a_, loc - a_
            d00, d01, d11, d20, d21 = v0 @ v0, v0 @ v1, v1 @ v1, v2 @ v0, v2 @ v1; den = d00 * d11 - d01 * d01 + 1e-12
            bb = (d11 * d20 - d01 * d21) / den; cc = (d00 * d21 - d01 * d20) / den; aa = 1 - bb - cc
            suv.append(UV[TL[ti, 0]] * aa + UV[TL[ti, 1]] * bb + UV[TL[ti, 2]] * cc); pts.append(loc); nrm.append(np.array(nr[:]))
    if len(pts) < 50: return None
    R0 = np.array(pts); Nn = np.array(nrm); n = len(R0); SUV = np.array(suv, np.float32)
    hc = V[:, 0].mean() * 0 + np.median(R0[:, 0])   # face midline x
    sx = np.sign(R0[:, 0] - hc + 1e-6)
    if kind == 'brow':
        medial = np.clip(1 - np.abs(R0[:, 0] - hc) / 0.03, 0, 1)
        d = np.stack([sx * (0.9 - 0.6 * medial), np.zeros(n), 0.25 + 0.9 * medial], 1) + 0.25 * rng.normal(size=(n, 3)); lift = 0.18
        L_ = 0.0045 + 0.0035 * rng.random(n); K = 4; rad0 = 0.00003
    else:
        d = np.stack([sx * 0.25, np.zeros(n), -1.0 * np.ones(n)], 1) + 0.35 * rng.normal(size=(n, 3)); lift = 0.45
        L_ = 0.002 + 0.004 * rng.random(n) * (1.0 if kind == 'stubble' else 2.5); K = 4; rad0 = 0.000035
    d = d - (d * Nn).sum(1)[:, None] * Nn; d /= np.linalg.norm(d, axis=1, keepdims=True) + 1e-9
    d = d * (1 - lift) + Nn * lift; d /= np.linalg.norm(d, axis=1, keepdims=True)
    Pt = np.zeros((n, K, 3)); base = R0 + Nn * 0.0002
    for k_ in range(K):   # slight curve back toward the skin
        t_ = k_ / (K - 1); dd = d * (1 - 0.35 * t_) - Nn * 0.35 * t_ * lift
        Pt[:, k_] = base + dd * L_[:, None] * t_
    Pl = (np.c_[Pt.reshape(-1, 3), np.ones(n * K)] @ np.array(mwi).T)[:, :3]
    cu = bpy.data.hair_curves.new(f'{p.name}_{kind}_strands'); cu.add_curves([K] * n)
    cu.position_data.foreach_set('vector', Pl.reshape(-1).astype(np.float32))
    ra = cu.attributes.get('radius') or cu.attributes.new('radius', 'FLOAT', 'POINT')
    ra.data.foreach_set('value', (np.linspace(1, 0.4, K)[None] * rad0 * (0.8 + 0.4 * rng.random(n))[:, None]).reshape(-1).astype(np.float32))
    su = cu.attributes.get('surface_uv_coordinate') or cu.attributes.new('surface_uv_coordinate', 'FLOAT2', 'CURVE')
    su.data.foreach_set('vector', SUV.reshape(-1))
    cu.surface = b; cu.surface_uv_map = uvl.name
    cu.materials.append(_hair_mat(f'{p.name}_{kind}mat', hv if kind != 'brow' else (1.2 if hv > 1 else min(hv, 0.6)), seed))
    ob = bpy.data.objects.new(f'{p.name}_{kind}_strands', cu); bpy.context.scene.collection.objects.link(ob)
    ob.parent = b; ob.matrix_parent_inverse.identity(); ob.matrix_world = mw.copy()
    md = ob.modifiers.new('kw_deform', 'NODES'); md.node_group = _deform_group()
    p.parts.append(ob)
    return ob


def flush(p, v):
    """v 0..1 reddens the scan skin of this person only (object property read by the skin shader)."""
    v = max(0.0, min(1.0, float(v)))
    for o in [p.body]:
        if o.get('kw_flush') != v: o['kw_flush'] = v; o.update_tag()
