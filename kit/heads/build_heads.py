"""One-off builder for KW_HEADS=scan data (run once in Blender; outputs go to assets/heads).
1) ICT-FaceKit (MIT) light-stage identity PCA modes -> per-vertex deltas on the MakeHuman basemesh (ict_mh_deltas.npz)
2) Lee Perry-Smith head scan (CC BY 3.0) displacement + specular maps -> baked into MakeHuman skin UVs (scan_detail_*.jpg)
usage: blender -b -P build_heads.py -- ICT_DIR LPS_DIR OUT_DIR [NMODES]"""
import bpy, sys, os, json, numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree
from bl_ext.user_default.mpfb.services.humanservice import HumanService
from bl_ext.user_default.mpfb.services.targetservice import TargetService
a = sys.argv[sys.argv.index('--') + 1:]; ICT, LPS, OUT = a[:3]; NM = int(a[3]) if len(a) > 3 else 40
os.makedirs(OUT, exist_ok=True)
for o in list(bpy.data.objects): bpy.data.objects.remove(o)
h = HumanService.create_human(macro_detail_dict={"gender": 0.5, "age": 0.5, "muscle": 0.5, "weight": 0.5, "proportions": 0.5, "height": 0.5,
                                                 "cupsize": 0.5, "firmness": 0.5, "race": {"african": 0.33, "asian": 0.33, "caucasian": 0.34}})
TargetService.bake_targets(h)
M = np.array(h.matrix_world); print('MW', M.tolist())
V = np.array([v.co[:] for v in h.data.vertices])            # local coords
gi = {g.name: g.index for g in h.vertex_groups}
def grp(n): return np.array([v.index for v in h.data.vertices for g in v.groups if g.group == gi[n] and g.weight > 0.5])
eyeL, eyeR = V[grp('joint-l-eye')].mean(0), V[grp('joint-r-eye')].mean(0)
body = grp('body'); head_c = V[grp('joint-head')].mean(0)
print('eyes', eyeL, eyeR, 'head', head_c, 'bbox', V.min(0), V.max(0))
up = np.array([0, 0, 1.0]) if abs(V[:, 2]).max() > abs(V[:, 1]).max() else np.array([0, 1.0, 0])
fwd_axis = 1 if up[2] else 2
# nose tip: most forward body vert between eye height and 0.6 eye-dist below
ed = np.linalg.norm(eyeL - eyeR); ez = (eyeL + eyeR) @ up / 2
cand = body[(V[body] @ up < ez) & (V[body] @ up > ez - 0.7 * ed) & (np.abs(V[body, 0]) < 0.25 * ed)]
fsign = -1.0 if V[cand, fwd_axis].mean() < head_c[fwd_axis] else 1.0
nose = V[cand[np.argmax(fsign * V[cand, fwd_axis])]]
print('up', up, 'fsign', fsign, 'nose', nose)

def umeyama(src, dst):
    ms, md = src.mean(0), dst.mean(0); s_, d_ = src - ms, dst - md
    U, S, Vt = np.linalg.svd(d_.T @ s_ / len(src)); D = np.eye(3); D[2, 2] = np.sign(np.linalg.det(U @ Vt))
    R = U @ D @ Vt; sc = np.trace(np.diag(S) @ D) / (s_ ** 2).sum(1).mean(); t = md - sc * R @ ms
    return sc, R, t
bodyset = set(body.tolist())
mh_faces = [p.vertices[:] for p in h.data.polygons if all(i in bodyset for i in p.vertices)]
bvh_mh = BVHTree.FromPolygons([Vector(v) for v in V], mh_faces)
def icp(P, sc, R, t, it=30, maxd=None, fix_scale=False):
    for k in range(it):
        Q = (sc * (R @ P.T)).T + t
        hits = [bvh_mh.find_nearest(Vector(q)) for q in Q]
        D = np.array([hh[0][:] for hh in hits]); dist = np.array([hh[3] for hh in hits])
        md = maxd or np.percentile(dist, 90) * 1.5; ok = dist < md
        sc2, R, t = umeyama(P[ok], D[ok])
        if fix_scale: t = D[ok].mean(0) - sc * R @ P[ok].mean(0)
        else: sc = sc2
    return sc, R, t, float(np.median(dist))

def load_obj(f, faces=False):
    vs, fs, uvs = [], [], []
    for l in open(f):
        if l.startswith('v '): vs.append([float(x) for x in l.split()[1:4]])
        elif faces and l.startswith('f '): fs.append([int(x.split('/')[0]) - 1 for x in l.split()[1:]])
    return np.array(vs), fs
if os.environ.get('ONLY_LPS') != '1':
    # ---------- 1. ICT identity deltas
    N, F = load_obj(f'{ICT}/generic_neutral_mesh.obj', True)
    F = [f for f in F if max(f) < 24591]                       # skin, sockets, mouth, teeth, eyeballs (no lacrimal/occlusion/lash cards)
    toB = np.array([[1, 0, 0], [0, 0, -1], [0, 1, 0.]]) if up[2] else np.eye(3)   # ICT y-up z-forward -> MH
    if up[2] and fsign > 0: toB = np.array([[-1, 0, 0], [0, 0, 1], [0, 1, 0.]])
    Nb = (toB @ N.T).T
    iL, iR = Nb[21451:22221].mean(0), Nb[23021:23791].mean(0)
    if iL[0] * eyeL[0] < 0: iL, iR = iR, iL
    src = np.array([iL, iR, Nb[4857]]); dst = np.array([eyeL, eyeR, nose])
    sc, R, t = umeyama(src, dst); print('ict init scale', sc)
    sc, R, t, err = icp(Nb[:6706], sc, R, t); print('ict icp scale', sc, 'median err', err)
    Na = (sc * (R @ Nb.T)).T + t
    bvh_ict = BVHTree.FromPolygons([Vector(v) for v in Na], F)
    fidx = np.array([f[:3] for f in F]); fidx4 = F
    tris = []  # triangulate quads for barycentrics: map polygon index -> list of tris
    for f in F: tris.append([(f[0], f[i], f[i + 1]) for i in range(1, len(f) - 1)])
    hz = head_c @ up; chin_z = nose @ up - 0.9 * ed
    sel, bary, wts = [], [], []
    for i, v in enumerate(V):
        if v @ up < chin_z - 0.9 * ed: continue
        loc, nrm, pi, d = bvh_ict.find_nearest(Vector(v))
        if pi is None or d > 0.04 * (ed / 0.065 if ed < 1 else ed / 0.65): continue
        p = np.array(loc[:]); best = None
        for (a_, b_, c_) in tris[pi]:
            A, B, C = Na[a_], Na[b_], Na[c_]; v0, v1, v2 = B - A, C - A, p - A
            d00, d01, d11, d20, d21 = v0 @ v0, v0 @ v1, v1 @ v1, v2 @ v0, v2 @ v1; den = d00 * d11 - d01 * d01
            if den == 0: continue
            bv = (d11 * d20 - d01 * d21) / den; bw = (d00 * d21 - d01 * d20) / den; bu = 1 - bv - bw
            bb = np.clip([bu, bv, bw], 0, 1); bb /= bb.sum(); e = np.linalg.norm(bb[0] * A + bb[1] * B + bb[2] * C - p)
            if best is None or e < best[0]: best = (e, (a_, b_, c_), bb)
        scale_ref = ed / 0.065 if ed < 1 else ed / 0.65    # 1 unit per metre-ish reference
        w = np.clip((0.035 * scale_ref - d) / (0.02 * scale_ref), 0, 1)
        zf = np.clip((v @ up - (chin_z - 0.9 * ed)) / (0.6 * ed), 0, 1)   # fade out down the neck
        w *= zf * zf * (3 - 2 * zf)
        if w <= 0.001: continue
        sel.append(i); bary.append((best[1], best[2])); wts.append(w)
    print('ict mapped verts', len(sel))
    sel = np.array(sel); wts = np.array(wts)
    TI = np.array([b[0] for b in bary]); TB = np.array([b[1] for b in bary])
    D = np.zeros((NM, len(sel), 3), np.float32)
    for m in range(NM):
        I_ = (toB @ load_obj(f'{ICT}/identity{m:03d}.obj')[0].T).T
        dl = (sc * (R @ (I_ - Nb).T)).T                                # delta in MH local units
        D[m] = (dl[TI] * TB[..., None]).sum(1) * wts[:, None]
    np.savez_compressed(f'{OUT}/ict_mh_deltas.npz', idx=sel.astype(np.int32), d=D.astype(np.float16), ed=np.float32(ed))
    print('saved deltas', D.shape, 'rms per mode', np.sqrt((D ** 2).sum(2).mean(1))[:8])

# ---------- 2. scan skin detail (Lee Perry-Smith) baked into MH UVs
bpy.ops.import_scene.gltf(filepath=f'{LPS}/LeePerrySmith.glb')
lp = next(o for o in bpy.context.selected_objects if o.type == 'MESH')
bpy.context.view_layer.objects.active = lp; bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)
L = np.array([v.co[:] for v in lp.data.vertices]); print('lps bbox', L.min(0), L.max(0))
# landmarks from the scan's UV layout (Map-COL.jpg: eye centres, nose tip in texture space)
uvl = lp.data.uv_layers.active.data; LUV = np.zeros((len(L), 2))
for lo in lp.data.loops: LUV[lo.vertex_index] = uvl[lo.index].uv[:]
def at_uv(u, v): return L[np.argmin(((LUV - (u, v)) ** 2).sum(1))]
lE1, lE2, lN = at_uv(0.42, 0.293), at_uv(0.576, 0.293), at_uv(0.5, 0.387)
if (lE1[0] - lE2[0]) * (eyeL[0] - eyeR[0]) < 0: lE1, lE2 = lE2, lE1
print('lps landmarks', lE1, lE2, lN)
lid = lambda e: V[body[np.argmin(np.linalg.norm(V[body] - (e + np.array([0, fsign * 0.012, 0])), axis=1))]]
sc, R, t = umeyama(np.array([lE1, lE2, lN]), np.array([lid(eyeL), lid(eyeR), nose])); print('lps init scale', sc)
lfar = L[np.linalg.norm(L - lN, axis=1) < 1.3 * np.linalg.norm(lE1 - lE2)]
sc, R, t, err = icp(lfar[::2], sc, R, t, it=25, fix_scale=True); print('lps icp scale', sc, 'err', err)
import mathutils
Mx = np.eye(4); Mx[:3, :3] = sc * R; Mx[:3, 3] = t
lp.data.transform(mathutils.Matrix(Mx.tolist())); lp.data.update()
# bake target: copy of the MH body with one emissive material
hb = h.copy(); hb.data = h.data.copy(); bpy.context.scene.collection.objects.link(hb)
hb.modifiers.clear(); hb.data.materials.clear()
S = bpy.context.scene; S.render.engine = 'CYCLES'; S.cycles.samples = 1; S.cycles.device = 'CPU'
def bake(img_path, name, res=2048):
    m = bpy.data.materials.new('src_' + name); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    ti = nt.nodes.new('ShaderNodeTexImage'); ti.image = bpy.data.images.load(img_path); ti.image.colorspace_settings.name = 'Non-Color'
    tc = nt.nodes.new('ShaderNodeTexCoord'); mp = nt.nodes.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (1, -1, 1); mp.inputs['Location'].default_value = (0, 1, 0)
    nt.links.new(tc.outputs['UV'], mp.inputs['Vector']); nt.links.new(mp.outputs['Vector'], ti.inputs['Vector'])   # the scan's UVs are top-down
    em = nt.nodes.new('ShaderNodeEmission'); out = nt.nodes.new('ShaderNodeOutputMaterial')
    nt.links.new(ti.outputs['Color'], em.inputs['Color']); nt.links.new(em.outputs[0], out.inputs[0])
    lp.data.materials.clear(); lp.data.materials.append(m)
    tm = bpy.data.materials.new('dst_' + name); tm.use_nodes = True
    im = bpy.data.images.new(name, res, res, float_buffer=True); im.colorspace_settings.name = 'Non-Color'
    tn = tm.node_tree.nodes.new('ShaderNodeTexImage'); tn.image = im; tm.node_tree.nodes.active = tn
    hb.data.materials.clear(); hb.data.materials.append(tm)
    for o in bpy.context.view_layer.objects: o.select_set(False)
    lp.select_set(True); hb.select_set(True); bpy.context.view_layer.objects.active = hb
    rd = 0.03 * (ed / 0.065 if ed < 1 else ed / 0.65)
    bpy.ops.object.bake(type='EMIT', use_selected_to_active=True, cage_extrusion=rd, max_ray_distance=2 * rd, margin=8, use_clear=True)
    px = np.array(im.pixels[:], np.float32).reshape(res, res, 4)
    return px[..., 0], px[..., 3]
hmap, ha = bake(f'{LPS}/Infinite-Level_02_Disp_NoSmoothUV-4096.jpg', 'disp')
spec, _ = bake(f'{LPS}/Map-SPEC.jpg', 'spec')
col = [bake(f'{LPS}/_col_{c}.png', 'col' + c)[0] for c in 'RGB']
np.savez_compressed(f'{OUT}/_raw_bake.npz', h=hmap.astype(np.float32), a=ha, s=spec.astype(np.float32), c=np.stack(col).astype(np.float32))
print('baked', float(ha.mean()), float(hmap[ha > 0.5].mean()) if (ha > 0.5).any() else None)
