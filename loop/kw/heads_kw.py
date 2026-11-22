"""KW_HEADS=scan: scan-based faces on the MakeHuman head (same topology, rig, expression keys, UVs).
- face shape: ICT-FaceKit light-stage identity PCA (MIT, USC ICT) transferred to MakeHuman vertex deltas (assets/heads/ict_mh_deltas.npz);
  `seed` picks stable PCA coefficients, so every cast member gets a distinct, scan-plausible face.
- skin: Lee Perry-Smith head scan (CC BY 3.0, Infinite Realities) displacement / specular / colour baked to MakeHuman UVs
  (assets/heads/scan_*.jpg): real pores, lip lines, creases, oily T-zone and red zones layered on the MakeHuman photo skins.
Default off (env KW_HEADS unset) -> the kit renders exactly as before."""
import os, random, zlib
import numpy as np
HD = os.environ.get('KW_HEADS_DIR', os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'assets', 'heads'))
_D = None


def on(): return os.environ.get('KW_HEADS', '') == 'scan'


def _deltas():
    global _D
    if _D is None:
        z = np.load(os.path.join(HD, 'ict_mh_deltas.npz')); _D = (z['idx'], z['d'].astype(np.float32))
    return _D


def coeffs(seed, n):
    r = random.Random(f'kw-scanface-{seed}')
    return np.array([max(-2.2, min(2.2, r.gauss(0.0, 1.0))) for _ in range(n)], np.float32)


def apply_shape(h, seed, gain=None):
    """add the seed's scan identity to the (already baked) body mesh, before rig/proxies are fitted."""
    idx, D = _deltas()
    g = float(os.environ.get('KW_HEADS_GAIN', gain if gain is not None else 1.0))
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


def skin(p, age=0.5, gender=1.0):
    """scan detail on the shared MPFB skin group(s) of this person; idempotent per group."""
    import bpy
    done = set()
    for s_ in p.body.material_slots:
        m_ = s_.material
        if not m_ or not m_.node_tree: continue
        for g in m_.node_tree.nodes:
            if g.type != 'GROUP' or not g.node_tree or g.node_tree.name in done: continue
            gt = g.node_tree; done.add(gt.name)
            if 'kw_scan_h' in gt.nodes or 'Bump' not in gt.nodes: continue
            N, L = gt.nodes, gt.links
            uv = N.new('ShaderNodeUVMap')
            # 1) scan height detail (pores, lip lines, creases) -> extra bump feeding the existing bump chain
            th = N.new('ShaderNodeTexImage'); th.name = 'kw_scan_h'; th.image = _img(os.path.join(HD, 'scan_height.jpg'))
            L.new(uv.outputs['UV'], th.inputs['Vector'])
            bm = N.new('ShaderNodeBump'); bm.name = 'kw_scan_bump'
            bm.inputs['Strength'].default_value = float(os.environ.get('KW_SCAN_BUMP', 0.55 + 0.35 * age))
            bm.inputs['Distance'].default_value = 0.004
            L.new(th.outputs['Color'], bm.inputs['Height'])
            old = gt.nodes['Bump']
            src = old.inputs['Normal'].links[0].from_socket if old.inputs['Normal'].links else None
            if src is not None: L.new(src, bm.inputs['Normal'])
            L.new(bm.outputs['Normal'], old.inputs['Normal'])
            # 2) specular map -> roughness variation (oily nose/forehead, matte cheeks)
            ts = N.new('ShaderNodeTexImage'); ts.name = 'kw_scan_s'; ts.image = _img(os.path.join(HD, 'scan_spec.jpg'))
            L.new(uv.outputs['UV'], ts.inputs['Vector'])
            for b in [n for n in N if n.type in ('BSDF_PRINCIPLED', 'SUBSURFACE_SCATTERING')]:
                if 'Roughness' not in b.inputs: continue
                ri = b.inputs['Roughness']
                rs = ri.links[0].from_socket if ri.links else None
                mr = N.new('ShaderNodeMapRange'); mr.inputs['From Min'].default_value = 0.0; mr.inputs['From Max'].default_value = 1.0
                mr.inputs['To Min'].default_value = 1.18; mr.inputs['To Max'].default_value = 0.8
                L.new(ts.outputs['Color'], mr.inputs['Value'])
                mu = N.new('ShaderNodeMath'); mu.operation = 'MULTIPLY'; mu.use_clamp = True
                if rs is not None: L.new(rs, mu.inputs[0])
                else: mu.inputs[0].default_value = ri.default_value
                L.new(mr.outputs['Result'], mu.inputs[1]); L.new(mu.outputs[0], ri)
            # 3) red zones (nose, cheeks, ears, lips) from the scan's colour -> multiply over the photo albedo
            hs = N.get('kw_skin_hs')
            if hs is not None and hs.outputs['Color'].links:
                tc = N.new('ShaderNodeTexImage'); tc.name = 'kw_scan_r'; tc.image = _img(os.path.join(HD, 'scan_red.jpg'))
                L.new(uv.outputs['UV'], tc.inputs['Vector'])
                mx = N.new('ShaderNodeMix'); mx.data_type = 'RGBA'; mx.blend_type = 'MULTIPLY'
                mx.inputs[7].default_value = (1.0, 0.70, 0.66, 1)
                f = N.new('ShaderNodeMath'); f.operation = 'MULTIPLY'; f.inputs[1].default_value = float(os.environ.get('KW_SCAN_RED', 0.8))
                L.new(tc.outputs['Color'], f.inputs[0]); L.new(f.outputs[0], mx.inputs[0])
                for l in list(hs.outputs['Color'].links):
                    to = l.to_socket; L.remove(l); L.new(mx.outputs[2], to)
                L.new(hs.outputs['Color'], mx.inputs[6])


EYE = {'EyeWhiteColor': (0.80, 0.75, 0.72, 1), 'IrisToEyeWhiteRelation': 0.44, 'IrisSection4Color': (0.02, 0.02, 0.03, 1),
       'IrisBumpStrength': 0.5, 'Clearcoat': 0.2, 'OuterLayerIOR': 1.30}


def eyes(p):
    """real eyes are not paper-white and carry a larger iris with a dark limbal ring"""
    for o in p.parts:
        if o.type != 'MESH' or 'high-poly' not in o.name.lower() or not o.active_material or not o.active_material.node_tree: continue
        for nd in o.active_material.node_tree.nodes:
            for k, v in EYE.items():
                if k in nd.inputs: nd.inputs[k].default_value = v


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
    'short02': (44000, 0.030, 0.010, 0.70, (0.0, 0.8, 0.0), 0.0),      # short back
    'short03': (42000, 0.055, 0.016, 0.55, (0.15, 0.25, 0.4), 0.15),   # longer, messy
    'short04': (40000, 0.012, 0.007, 0.80, (0.0, 0.6, 0.0), 0.0),      # buzz
    'coil':    (52000, 0.016, 0.009, 0.25, (0.0, 0.0, 0.2), 0.6),      # tight short coils (African short styles)
    'afro01':  (34000, 0.040, 0.022, 0.05, (0.0, 0.0, 0.3), 1.0),      # short coils
}
FALL_STYLES = {    # style -> (strands, end height above the lowest scalp point m (negative = below), curl)
    'bob01': (52000, -0.07, 0.12), 'bob02': (52000, -0.05, 0.0), 'long01': (56000, -0.22, 0.05)}


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
    mel = 0.25 if grey else max(0.45, min(0.99, 1.02 - 0.5 * (hv - 0.15)))
    hb.inputs['Melanin'].default_value = mel
    hb.inputs['Melanin Redness'].default_value = 0.25 if grey else 0.55
    hb.inputs['Roughness'].default_value = 0.32; hb.inputs['Radial Roughness'].default_value = 0.4; hb.inputs['Coat'].default_value = 0.15
    if 'Random Roughness' in hb.inputs: hb.inputs['Random Roughness'].default_value = 0.3
    if 'Random Color' in hb.inputs: hb.inputs['Random Color'].default_value = 0.15
    if grey:   # grey/white: a share of strands with almost no pigment
        hi = N.new('ShaderNodeHairInfo'); gt_ = N.new('ShaderNodeMath'); gt_.operation = 'GREATER_THAN'
        gt_.inputs[1].default_value = 0.55 if hv < 2.0 else (0.72 if hv < 2.4 else 0.86)   # share of white strands
        mr = N.new('ShaderNodeMapRange'); mr.inputs['To Min'].default_value = 0.62; mr.inputs['To Max'].default_value = 0.03
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
    if african and style.startswith('short'): style = 'coil'
    fall = style in FALL_STYLES
    n, l_top, l_side, flat, comb, curl = CURVE_STYLES[style] if not fall else (FALL_STYLES[style][0], 0, 0, 0.5, (0.6, 0.6, 0.0), FALL_STYLES[style][2])
    n = int(n * float(os.environ.get('KW_HAIR_DENSITY', 1.0)))
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
    ts = T[(W[T].mean(1) > 0.5) & tb]
    if len(ts) == 0: return None
    A, B, C = V[ts[:, 0]], V[ts[:, 1]], V[ts[:, 2]]
    area = 0.5 * np.linalg.norm(np.cross(B - A, C - A), axis=1)
    rng = np.random.default_rng(zlib.crc32(f'kw-hair-{seed}'.encode()))   # stable across processes (str hash is salted)
    pick = rng.choice(len(ts), n, p=area / area.sum())
    u, v_ = rng.random(n), rng.random(n); sw = u + v_ > 1; u[sw], v_[sw] = 1 - u[sw], 1 - v_[sw]
    R0 = A[pick] + u[:, None] * (B[pick] - A[pick]) + v_[:, None] * (C[pick] - A[pick])
    wr = (1 - u - v_) * W[ts[pick, 0]] + u * W[ts[pick, 1]] + v_ * W[ts[pick, 2]]
    keep = rng.random(n) < np.clip((wr - 0.5) / 0.45, 0.15, 1.0)            # soft hairline instead of a hard shell edge
    pick, u, v_, R0 = pick[keep], u[keep], v_[keep], R0[keep]; n = len(R0)
    Nf = np.cross(B - A, C - A)[pick]; Nf /= np.linalg.norm(Nf, axis=1, keepdims=True) + 1e-9
    hc = V[W > 0.5].mean(0); top = V[W > 0.5][:, 2].max(); bot = V[W > 0.5][:, 2].min()
    Nf *= np.sign(((R0 - hc) * Nf).sum(1))[:, None]      # outward
    # head frame: rig forward is -Y; comb is given in (x = character left->right parting, y = backwards, z = up)
    cdir = np.array(comb, float)
    hz = np.clip((R0[:, 2] - bot) / max(top - bot, 1e-3), 0, 1)           # 0 at the nape/sideburns, 1 at the crown
    front = np.clip((hc[1] - R0[:, 1]) / 0.08, 0, 1)                       # 1 at the hairline (rig faces -Y)
    length = (l_side + (l_top - l_side) * hz ** 1.5) * (0.75 + 0.5 * rng.random(n)) * (1 - 0.35 * front * (style != 'afro01'))
    K = 7 if curl < 0.5 else 12
    jit = rng.random(n)
    if fall:
        flat = 0.88; K = 16; ez = (V[W > 0.5][:, 2].max() + bot) / 2   # roughly eye height
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
    cu = bpy.data.hair_curves.new(f'{p.name}_strands')
    cu.add_curves([K] * n)
    cu.position_data.foreach_set('vector', P.reshape(-1).astype(np.float32))
    rad = np.linspace(1.0, 0.35, K)[None, :] * (0.00008 + 0.00004 * rng.random(n))[:, None]
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


def _scalp_tint(p, W, hv):
    """skin under strand hair takes the hair colour (no pink scalp between strands)"""
    me = p.body.data
    ca = me.color_attributes.get('kw_scalp') or me.color_attributes.new('kw_scalp', 'FLOAT_COLOR', 'POINT')
    col = (0.55, 0.55, 0.56) if hv > 1 else tuple(a + (b - a) * max(0.0, min(1.0, hv)) for a, b in zip((0.02, 0.015, 0.01), (0.25, 0.16, 0.08)))
    w = np.clip((W - 0.2) / 0.6, 0, 1) * 0.85
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
