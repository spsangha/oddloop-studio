"""Deterministic job casting on MPFB2's locally shipped CC0 wardrobe.

person(name, job, seed, **role) returns the standard person.Person; dress()
can replace an existing Person's wardrobe and supports repeated calls.
Coordinates for fittings are in the armature rest frame, not in world space.
All applied outfit and accessory objects also appear in Person.parts.
"""

from math import cos, pi, sin, sqrt, tau
from pathlib import Path
from random import Random
import os

import bpy
import bmesh
from mathutils import Matrix, Vector
from mathutils.bvhtree import BVHTree
from bl_ext.user_default.mpfb.entities.objectproperties import GeneralObjectProperties

try:
    from . import person as _P
    from . import cast as _C
except ImportError:
    import person as _P
    import cast as _C


JOBS = [
    "doctor", "nurse", "surgeon", "police", "paramedic", "firefighter",
    "patient", "chef", "construction worker", "business", "pilot",
    "scientist", "civilian",
]
__all__ = ["JOBS", "person", "dress"]

_CLOTHES = {"female_casualsuit01", "female_casualsuit02", "female_elegantsuit01",
            "female_sportsuit01", "male_elegantsuit01", "male_worksuit01", "fedora01",
            "fedora_cocked", *(f"male_casualsuit{i:02}" for i in range(1, 7)),
            *(f"shoes{i:02}" for i in range(1, 7))}
_HAIR = set(_C.HAIR_M) | set(_C.HAIR_F)
_TEX = Path(os.environ.get("ZK_TEX", str(Path(__file__).resolve().parents[2] / "assets" / "tex")))
_CAPS = {"surgeon", "police", "firefighter", "chef", "construction worker", "pilot"}
_MEDICAL = {"doctor", "nurse", "surgeon"}
_FORWARD = Vector((0, 1, 0))


def _job(job):
    label = str(job).strip().lower().replace("_", " ").replace("-", " ")
    label = {"cop": "police", "officer": "police", "construction": "construction worker",
             "fire fighter": "firefighter", "businessperson": "business", "emt": "paramedic"}.get(label, label)
    if label not in JOBS:
        raise ValueError(f"Unknown wardrobe job {job!r}; choose from {', '.join(JOBS)}")
    return label


def _rng(seed, key):
    return Random(f"kw-wardrobe-v1:{seed}:{key}")


def _asset(obj):
    if obj.type == "MESH":
        a = Path(GeneralObjectProperties.get_value("asset_source", entity_reference=obj) or "").stem.lower()
        return a if a in _CLOTHES else None
    return None


def _hair_name(obj):
    if obj.type == "MESH":
        a = Path(GeneralObjectProperties.get_value("asset_source", entity_reference=obj) or "").stem.lower()
        return a if a in _HAIR else None
    return None


def _resolve_outfit(job, female):
    scrub = "female_casualsuit01" if female else "male_casualsuit04"
    return {
        "doctor": (scrub, "shoes05"), "nurse": (scrub, "shoes05"), "surgeon": (scrub, "shoes05"),
        "police": ("male_casualsuit01", "shoes03"), "paramedic": ("male_casualsuit01", "shoes03"),
        "firefighter": ("male_casualsuit05", "shoes03"), "patient": (scrub, "shoes06"),
        "chef": ("male_casualsuit01", "shoes04"), "construction worker": ("male_worksuit01", "shoes01"),
        "business": ("male_elegantsuit01", "shoes04"), "pilot": ("male_casualsuit01", "shoes04"),
        "scientist": ("male_casualsuit05", "shoes04"), "civilian": ("male_casualsuit04", "shoes01"),
    }[job]


def person(name, job, seed, **role):
    """Build a deterministic person; accepts cast.cast's normal role keywords.

    Optional wardrobe overrides: mask, clipboard, gloves (booleans), plus
    outfit (tuple of supported CC0 clothes) and tee (civilian only).
    """
    job = _job(job)
    role = dict(role)
    options = {key: role.pop(key) for key in ("mask", "clipboard", "gloves") if key in role}
    if "gender" in role:
        role["gender"] = {"male": "m", "female": "f"}.get(role["gender"], role["gender"])
    if "age" in role:
        role["age"] = {"adult": "young"}.get(role["age"], role["age"])
    spec = _C.cast(role, seed, _P.MP)
    if job == "nurse" and "hair" not in role and spec["hair"] not in {None, "short01", "short02", "short03", "short04"}:
        spec["hair"] = "ponytail01"
    options["preserve_hair"] = "hair" in role
    options["female"] = spec["gender"] < .5
    explicit = role.get("outfit")
    outfit = tuple(explicit) if explicit else _resolve_outfit(job, options["female"])
    if any(a not in _CLOTHES for a in outfit):
        raise ValueError(f"An outfit asset is not available locally: {outfit!r}")
    if explicit:
        options["outfit"] = outfit
    options["tee"] = spec["tee"]
    spec["clothes"], spec["tee"] = outfit, spec["tee"] if job == "civilian" else None
    p = _P.build_person(name, **spec)
    p._kw_wardrobe_options = options
    return dress(p, job, seed)


def _rgba(s):
    if not isinstance(s, str):
        return (*s[:3], 1.)
    a = [int(s[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(c / 12.92 if c <= .04045 else ((c + .055) / 1.055) ** 2.4 for c in a) + (1.,)


def _mat(label, color, rough=.43, metal=0., textile=False, emission=0., patterned=False):
    signature = "KW wear | " + label + " | " + str(color)
    got = bpy.data.materials.get(signature)
    if got:
        return got
    m = bpy.data.materials.new(signature)
    m.diffuse_color, m.use_nodes = _rgba(color), True
    t = m.node_tree
    p = t.nodes.get("Principled BSDF")
    p.inputs["Base Color"].default_value = _rgba(color)
    p.inputs["Roughness"].default_value = rough
    p.inputs["Metallic"].default_value = metal
    p.inputs["Coat Weight"].default_value = .20 if not textile else .08
    p.inputs["Emission Color"].default_value = _rgba(color)
    p.inputs["Emission Strength"].default_value = emission
    if textile:
        p.inputs["Sheen Weight"].default_value = .25
        tex = t.nodes.new("ShaderNodeTexCoord").outputs["Object"]
        n = t.nodes.new("ShaderNodeTexNoise")
        n.inputs["Scale"].default_value = 265
        n.inputs["Detail"].default_value = 2.2
        t.links.new(tex, n.inputs["Vector"])
        bump = t.nodes.new("ShaderNodeBump")
        bump.inputs["Distance"].default_value = .0011
        bump.inputs["Strength"].default_value = .22
        t.links.new(n.outputs["Fac"], bump.inputs["Height"])
        t.links.new(bump.outputs["Normal"], p.inputs["Normal"])
        mottled = t.nodes.new("ShaderNodeTexNoise")
        mottled.inputs["Scale"].default_value = 12
        mottled.inputs["Detail"].default_value = 2
        t.links.new(tex, mottled.inputs["Vector"])
        mix = t.nodes.new("ShaderNodeMixRGB")
        mix.inputs[1].default_value = tuple(c * .78 for c in _rgba(color)[:3]) + (1,)
        mix.inputs[2].default_value = tuple(min(1, c * 1.13) for c in _rgba(color)[:3]) + (1,)
        t.links.new(mottled.outputs["Fac"], mix.inputs["Fac"])
        if patterned:
            # Sparse woven blue diamond specks, evocative of an unbranded hospital gown.
            wave = t.nodes.new("ShaderNodeTexVoronoi")
            wave.voronoi_dimensions = "3D"
            wave.inputs["Scale"].default_value = 34
            wave.inputs["Randomness"].default_value = .16
            t.links.new(tex, wave.inputs["Vector"])
            ramp = t.nodes.new("ShaderNodeValToRGB")
            ramp.color_ramp.elements[0].position = .14
            ramp.color_ramp.elements[1].position = .19
            t.links.new(wave.outputs["Distance"], ramp.inputs["Fac"])
            dot = t.nodes.new("ShaderNodeMixRGB")
            dot.inputs[1].default_value = _rgba("78A9BB")
            t.links.new(mix.outputs[0], dot.inputs[2])
            t.links.new(ramp.outputs[0], dot.inputs[0])
            mix = dot
        t.links.new(mix.outputs[0], p.inputs["Base Color"])
    return m


def _components(mesh):
    parents = list(range(len(mesh.vertices)))
    def root(i):
        while parents[i] != i:
            parents[i] = parents[parents[i]]
            i = parents[i]
        return i
    for a, b in (e.vertices for e in mesh.edges):
        parents[root(b)] = root(a)
    groups = {}
    identities = []
    for v in mesh.vertices:
        k = root(v.index)
        groups.setdefault(k, []).append(v.index)
        identities.append(k)
    return groups, identities


def _repaint(o, upper, lower, zref):
    g, idx = _components(o.data)
    span={k:(min(o.data.vertices[i].co.z for i in ids),max(o.data.vertices[i].co.z for i in ids))
          for k,ids in g.items()}
    upper_id = {k for k,(lo,hi) in span.items() if hi > zref+.055 and lo > zref-.21}
    mixed_id = {k for k,(lo,hi) in span.items() if hi > zref+.055 and lo <= zref-.21}
    o.data.materials.clear()
    o.data.materials.append(upper)
    o.data.materials.append(lower)
    if mixed_id:
        # One local asset welds the shirt to its trousers. A shader boundary
        # avoids drawing the large triangles of the triangulated waist seam.
        _rest_coordinates(o)
        m=upper.copy()
        m.name=f"{o.name} | tailored waist"
        t=m.node_tree
        link=t.links
        a=t.nodes.new("ShaderNodeAttribute")
        a.attribute_name="kw_rest"
        sep=t.nodes.new("ShaderNodeSeparateXYZ")
        link.new(a.outputs["Vector"],sep.inputs[0])
        high=t.nodes.new("ShaderNodeMath")
        high.operation="GREATER_THAN"
        link.new(sep.outputs["Z"],high.inputs[0])
        high.inputs[1].default_value=zref
        bs=t.nodes.get("Principled BSDF")
        bc=bs.inputs["Base Color"]
        mix=t.nodes.new("ShaderNodeMixRGB")
        link.new(high.outputs[0],mix.inputs[0])
        mix.inputs[1].default_value=lower.diffuse_color
        if bc.is_linked:
            link.new(bc.links[0].from_socket,mix.inputs[2])
        else:
            mix.inputs[2].default_value=bc.default_value
        link.new(mix.outputs[0],bc)
        e=bs.inputs["Emission Strength"]
        if e.is_linked:
            mul=t.nodes.new("ShaderNodeMath")
            mul.operation="MULTIPLY"
            link.new(high.outputs[0],mul.inputs[0])
            link.new(e.links[0].from_socket,mul.inputs[1])
            link.new(mul.outputs[0],e)
        o.data.materials.append(m)
    for face in o.data.polygons:
        v = face.vertices[0]
        face.material_index = 2 if idx[v] in mixed_id else int(idx[v] not in upper_id and o.data.vertices[v].co.z < zref)
    return {i for k in upper_id for i in g[k]}


def _shoes(o, mat, sole, cuff=None):
    z0, z1 = (f(v.co.z for v in o.data.vertices) for f in (min, max))
    o.data.materials.clear()
    o.data.materials.append(mat)
    o.data.materials.append(sole)
    if cuff:
        o.data.materials.append(cuff)
    for face in o.data.polygons:
        h=sum(o.data.vertices[i].co.z for i in face.vertices)/len(face.vertices)
        face.material_index = 2 if cuff and h > z0+.57*(z1-z0) else int(h < z0+.17*(z1-z0))


def _cuff_clearance(o):
    if o.data.attributes.get("kw_ankle_relief"):
        return
    o.data.attributes.new("kw_ankle_relief", "FLOAT", "POINT")
    high = max(v.co.z for v in o.data.vertices)
    for side in (-1, 1):
        top = [v for v in o.data.vertices if side*v.co.x > 0 and v.co.z > high-.035]
        if not top:
            continue
        cx = sum(v.co.x for v in top) / len(top)
        cy = sum(v.co.y for v in top) / len(top)
        for v in top:
            w = min(1, max(0, (v.co.z - high + .035)/.028))
            v.co.x += (cx-v.co.x)*.40*w
            v.co.y += (cy-v.co.y)*.40*w
            v.co.z -= .021*w
    o.data.update()


def _remove_asset(p, o, key):
    if o in p.parts:
        p.parts.remove(o)
    bpy.data.objects.remove(o, do_unlink=True)
    vg = "Delete." + key
    for mod in list(p.body.modifiers):
        if mod.type == "MASK" and mod.vertex_group == vg:
            p.body.modifiers.remove(mod)
    group = p.body.vertex_groups.get(vg)
    if group is not None:
        p.body.vertex_groups.remove(group)


def _move_masks(p):
    mods = p.body.modifiers
    for mod in list(mods):
        if mod.type == "MASK":
            first_sub = next((i for i, m in enumerate(mods) if m.type == "SUBSURF"), len(mods))
            current = mods.find(mod.name)
            if current > first_sub:
                mods.move(current, first_sub)


def _put_on(p, outfit):
    found = {}
    for o in tuple(p.parts):
        a = _asset(o)
        if not a:
            continue
        if a in outfit:
            found[a] = o
        else:
            _remove_asset(p, o, a)
    for a in outfit:
        if a not in found:
            file = Path(_P.UD) / "clothes" / a / (a + ".mhclo")
            o = _P.HumanService.add_mhclo_asset(str(file), p.body, asset_type="Clothes")
            found[a] = o
            p.parts.append(o)
    _move_masks(p)
    return [found[k] for k in outfit]


def _nurse_hair(p):
    if p._kw_wardrobe_options.get("preserve_hair"):
        return
    for o in tuple(p.parts):
        a = _hair_name(o)
        if a in {"bob01", "bob02", "long01", "braid01", "afro01"}:
            _remove_asset(p, o, a)
            asset = Path(_P.UD) / "hair/ponytail01/ponytail01.mhclo"
            o = _P.HumanService.add_mhclo_asset(str(asset), p.body, asset_type="Hair")
            p.parts.append(o)
            _move_masks(p)
            for s_ in [x for x in p.parts if x.name.endswith("_hair_strands")]:   # KW_HEADS=scan: the loose strand hair goes too
                p.parts.remove(s_); bpy.data.objects.remove(s_)
            if _P._HK.on():
                try: _P._HK.card_hair_fix(p, [o], getattr(p, "_kw_hair_value", 0.3))
                except Exception as e: print("card hair fix skipped", repr(e))
            break


def _bvh(o, coords=None, body=False):
    vs = coords or [v.co.copy() for v in o.data.vertices]
    vg = o.vertex_groups.get("body") if body else None
    allowed = ({v.index for v in o.data.vertices if any(g.group == vg.index and g.weight > .5 for g in v.groups)}
               if vg else None)
    faces = [tuple(p.vertices) for p in o.data.polygons if allowed is None or all(i in allowed for i in p.vertices)]
    return BVHTree.FromPolygons(vs, faces)


class _Fit:
    def __init__(self, p, main):
        self.p, self.main, self.rig = p, main, p.rig
        self.bodyv = [v.co.copy() for v in p.body.data.vertices]
        self.body = _bvh(p.body, self.bodyv, True)
        self.cloth = _bvh(main) if main else None
        self.bones = p.rig.data.bones
        self.head = self.bones["head"].head_local.copy()
        self.neck = self.bones["neck01"].head_local.copy()
        self.eyes = (self.bones["eye.L"].head_local + self.bones["eye.R"].head_local) / 2
        self.top = max(v.z for v in self.bodyv)
        self.q = (self.top - self.neck.z) / .247
        self.s = self.top / 1.60
        self.mid = self.bones["spine03"].head_local.z
        self.waist = self.bones["spine04"].tail_local.z
        self.collection = p.body.users_collection[0] if p.body.users_collection else bpy.context.scene.collection
        self.anchors = {}
        self._made = []

    def ray(self, tree, x, z, back=False):
        if not tree:
            return None
        return tree.ray_cast((x, 2 if back else -2, z), -_FORWARD if back else _FORWARD, 4)[0]

    def surface(self, x, z, pad=.005, garment=True, back=False):
        # Choose the frontmost skin or garment hit; this avoids inner neck rims.
        hits = [self.ray(t, x, z, back) for t in (self.cloth if garment else None, self.body)]
        ys = [h.y for h in hits if h is not None]
        if ys:
            return (max(ys) + pad if back else min(ys) - pad)
        return -.055 - pad if not back else .05 + pad

    def anchor(self, bone):
        if bone in self.anchors:
            return self.anchors[bone]
        b = self.bones[bone]
        o = bpy.data.objects.new(f"{self.p.name} | fit on {bone}", None)
        self.collection.objects.link(o)
        o.empty_display_size = .025
        o.parent, o.parent_type, o.parent_bone = self.rig, "BONE", bone
        # No pose dependence: rest attachment converts coordinates into the bone's
        # tip frame; a currently posed or subsequently animated rig follows cleanly.
        o.matrix_parent_inverse = (b.matrix_local @ Matrix.Translation((0, b.length, 0))).inverted()
        self.anchors[bone] = o
        self._made.append(o)
        self.p.parts.append(o)
        return o

    def object(self, label, data, bone, loc=(0, 0, 0)):
        o = bpy.data.objects.new(f"{self.p.name} | {label}", data)
        self.collection.objects.link(o)
        o.parent, o.location = self.anchor(bone), loc
        self._made.append(o)
        self.p.parts.append(o)
        return o

    def mesh(self, label, vs, faces, bone, material, smooth=True, thick=0):
        me = bpy.data.meshes.new(label)
        me.from_pydata(vs, [], faces)
        me.update()
        me.materials.append(material)
        for p in me.polygons:
            p.use_smooth = smooth
        o = self.object(label, me, bone)
        if thick:
            mod = o.modifiers.new("Material thickness", "SOLIDIFY")
            mod.thickness = thick
            mod.offset = 0
        return o

    def stroke(self, label, points, radius, bone, mat, cyclic=False, smooth=True):
        c = bpy.data.curves.new(label, "CURVE")
        c.dimensions, c.resolution_u = "3D", 12
        c.bevel_depth, c.bevel_resolution, c.use_fill_caps = radius, 3, not cyclic
        spl = c.splines.new("BEZIER" if smooth else "POLY")
        points = list(points)
        if smooth:
            spl.bezier_points.add(len(points) - 1)
            for v, p in zip(spl.bezier_points, points):
                v.co = p
                v.handle_left_type = v.handle_right_type = "AUTO"
        else:
            spl.points.add(len(points) - 1)
            for v, p in zip(spl.points, points):
                v.co = (*p, 1)
        spl.use_cyclic_u = cyclic
        c.materials.append(mat)
        return self.object(label, c, bone)

    def sphere(self, label, loc, radii, bone, mat):
        bm = bmesh.new()
        bmesh.ops.create_uvsphere(bm, u_segments=24, v_segments=12, radius=1)
        for v in bm.verts:
            for i in range(3):
                v.co[i] = v.co[i] * radii[i] + loc[i]
        m = bpy.data.meshes.new(label)
        bm.to_mesh(m)
        bm.free()
        m.materials.append(mat)
        for f in m.polygons:
            f.use_smooth = True
        return self.object(label, m, bone)

    def box(self, label, loc, dims, bone, mat, bevel=.003):
        x, y, z = (d / 2 for d in dims)
        vs = [Vector(loc) + Vector((u, v, w))
              for u, v, w in ((-x,-y,-z),(x,-y,-z),(x,y,-z),(-x,y,-z),(-x,-y,z),(x,-y,z),(x,y,z),(-x,y,z))]
        fs = [(3,2,1,0),(0,1,5,4),(1,2,6,5),(2,3,7,6),(3,0,4,7),(4,5,6,7)]
        o = self.mesh(label, vs, fs, bone, mat, False)
        if bevel:
            mod = o.modifiers.new("Rounded stitching edge", "BEVEL")
            mod.width, mod.segments = bevel, 3
            o.modifiers.new("Flat face normals", "WEIGHTED_NORMAL")
        return o

    def text(self, label, body, size, loc, bone, mat):
        g = bpy.data.curves.new(label, "FONT")
        g.body, g.size, g.align_x, g.align_y = body, size, "CENTER", "CENTER"
        g.extrude, g.bevel_depth = .00008, 0
        g.materials.append(mat)
        o = self.object(label, g, bone, loc)
        o.rotation_euler.x = pi / 2
        return o

    def on(self, x, z, pad=.006):
        return (x, self.surface(x, z, pad), z)

    def patch(self, label, outline, mat, bone="spine01", pad=.004):
        # Radial subdivision samples the fabric curvature, even on a shaped chest.
        xs, zs = zip(*outline)
        center = Vector((sum(xs) / len(xs), sum(zs) / len(zs)))
        points = [Vector(v) for v in outline]
        vs = [self.on(*center, pad)]
        expanded = []
        for a, b in zip(points, points[1:] + points[:1]):
            expanded.extend(a.lerp(b, i / 5) for i in range(5))
        n = len(expanded)
        for r in (.34, .68, 1.):
            vs += [self.on(*center.lerp(v, r), pad) for v in expanded]
        faces = [(0, 1+i, 1+(i+1)%n) for i in range(n)]
        for row in range(2):
            starts = 1 + row * n
            faces.extend((starts + i, starts + n + i, starts + n + (i+1)%n, starts + (i+1)%n)
                         for i in range(n))
        return self.mesh(label, vs, faces, bone, mat, True, .0015)


def _gloves(p, color=None):
    for idx, old in getattr(p, "_kw_glove_faces", ()):
        p.body.data.polygons[idx].material_index = old
    p._kw_glove_faces = []
    if not color:
        return
    b = p.body
    m = _mat("nitrile gloves", color, .29)
    slot = next((i for i, v in enumerate(b.data.materials) if v == m), -1)
    if slot < 0:
        b.data.materials.append(m)
        slot = len(b.data.materials) - 1
    groups = {g.index for g in b.vertex_groups if g.name.startswith(("wrist", "finger", "metacarpal"))}
    selected = {v.index for v in b.data.vertices if sum(g.weight for g in v.groups if g.group in groups) > .47}
    for face in b.data.polygons:
        if sum(v in selected for v in face.vertices) >= min(3, len(face.vertices)):
            p._kw_glove_faces.append((face.index, face.material_index))
            face.material_index = slot


def _scrub_seams(f, fabric):
    s, z = f.s, f.neck.z
    seam = _mat("scrub flat-felled seams", fabric, .54, textile=True)
    # Small twin stitched rows below the neckline give the top a structured scrub V.
    for j in (0, 1):
        points = [(-.089*s, z-.010*s-j*.006*s), (-.066*s,z-.043*s-j*.006*s),
                  (0,z-.103*s-j*.006*s), (.064*s,z-.043*s-j*.006*s), (.086*s,z-.009*s-j*.006*s)]
        f.stroke("scrub neck binding", [f.on(x,h,.0045) for x,h in points], .00155*s,
                 "spine01", seam, smooth=False)
    _pocket(f, .095*s, z-.23*s, .090*s, .089*s, seam, sewn=True)


def _pocket(f, x, z, w, h, mat, sewn=False):
    outline = [(x-w/2,z+h/2),(x-w/2,z-h*.32),(x-w*.30,z-h/2),
               (x+w*.31,z-h/2),(x+w/2,z-h*.32),(x+w/2,z+h/2)]
    f.patch("shaped patch pocket", outline, mat, pad=.004)
    if sewn:
        f.stroke("pocket stitching", [f.on(px,pz,.006) for px,pz in outline], .0012*f.s,
                 "spine01", mat, cyclic=True, smooth=False)


def _stethoscope(f):
    s, n = f.s, f.neck.z
    tubing = _mat("flexible stethoscope tubing", "232D45", .31)
    rim = _mat("brushed stethoscope steel", "B9CCD9", .22, .64)
    dark = _mat("stethoscope diaphragm", "253340", .27)
    earpad = _mat("rubber ear guides", "1A2129", .43)
    # Over-both-shoulders U with a deliberately long front drape to one side.
    main = [(.091*s,n-.083*s),(.078*s,n-.161*s),(.032*s,n-.264*s),
            (-.021*s,n-.338*s),(-.076*s,n-.305*s),(-.10*s,n-.197*s),(-.099*s,n-.119*s)]
    f.stroke("stethoscope hanging tube", [f.on(x,z,.017*s) for x,z in main],
             .0052*s,"spine01",tubing)
    rhs, lhs = main[0], main[-1]
    for j, (x, z) in enumerate((rhs, lhs)):
        sign = 1 if j == 0 else -1
        top_z = n + .009*s
        p0, p1 = f.on(x,z,.017*s), f.on(sign*.079*s,n-.038*s,.013*s)
        p2 = (sign*.062*s, f.surface(sign*.062*s, top_z,.006*s), top_z)
        p3 = (sign*.048*s, .021*s, n-.014*s)
        f.stroke("stethoscope spring steel earpiece", [p0,p1,p2,p3], .0035*s, "spine01", rim)
        f.sphere("stethoscope silicone tip", p3, (.008*s,.007*s,.006*s), "spine01", earpad)
    x,z = -.081*s,n-.295*s
    y = f.surface(x,z,.021*s)
    f.sphere("stethoscope silver chest bell",(x,y,z),(.023*s,.009*s,.024*s),"spine01",rim)
    f.sphere("stethoscope dark diaphragm",(x,y-.007*s,z),(.0152*s,.004*s,.016*s),"spine01",dark)


def _id_card(f, legend, stripe="259BAC", side=-1):
    s = f.s
    x, z = side*.103*s, f.neck.z-.20*s
    y = f.surface(x,z,.011*s)
    base = _mat("unbranded wipe-clean ID card","F6FAF8",.33)
    ink = _mat("generic ID ink","223E4F",.41)
    accent = _mat("generic ID accent",stripe,.43)
    metal = _mat("badge clip metal","AFC2C7",.27,.57)
    f.box("portrait badge face",(x,y,z),(.060*s,.004*s,.079*s),"spine01",base,.004*s)
    f.box("badge clip",(x,y-.002*s,z+.042*s),(.018*s,.008*s,.014*s),"spine01",metal,.002*s)
    f.box("badge color band",(x,y-.0028*s,z+.025*s),(.052*s,.0005*s,.014*s),"spine01",accent,.001*s)
    f.sphere("badge portrait dot",(x,y-.0031*s,z+.004*s),(.008*s,.0009*s,.009*s),"spine01",accent)
    f.text("plain job badge lettering",legend,.013*s,(x,y-.0035*s,z-.018*s),"spine01",ink)


def _face_mask(f, shade="B6DEDE"):
    q, cx = f.q, f.eyes.x
    ze = f.eyes.z
    width = .074*q
    upper = ze-.029*q
    lower = ze-.092*q
    side_y = f.surface(cx+width*.74,ze-.059*q,.006*q,False)
    tip_y = min(f.surface(cx,ze-.052*q,.008*q,False), f.surface(cx,upper,.010*q,False))
    mt = _mat("pleated mask cloth",shade,.47,textile=True)
    bind = _mat("mask cotton binding","F4FAF3",.51,textile=True)
    strip = _mat("mask pleat shadow","91C0C0" if shade != "F0F5EF" else "C5D2D0",.54,textile=True)
    def xy(u, v):
        a = abs(u)
        x = cx + width*u*(.90+.10*sin(pi*v))
        z1 = upper - .021*q*a**1.7
        z0 = lower + .022*q*a**1.2
        z = z0 + (z1-z0)*v
        face = f.ray(f.body, x, z)
        shell = tip_y + (side_y - tip_y) * a**1.7 + .023*q*(1-v)**3
        if face:
            shell = min(shell, face.y - .005*q)
        # Rolls must be in front of the clearance shell.
        y = shell - .0024*q*(.5+.5*cos(v*tau*3.13))*max(.10,1-u*u)
        return (x,y,z)
    nu,nv=21,26
    vs=[xy(-1+2*i/(nu-1),j/(nv-1)) for j in range(nv) for i in range(nu)]
    faces=[(a,a+1,a+1+nu,a+nu) for j in range(nv-1) for i in range(nu-1) for a in (j*nu+i,)]
    m=f.mesh("fitted pleated face mask",vs,faces,"head",mt,True,.0018*q)
    smooth = m.modifiers.new("Rounded cloth folds", "SUBSURF")
    smooth.levels=smooth.render_levels=1
    for end in (0.,1.):
        f.stroke("mask welded edge",[xy(-1+2*i/14,end) for i in range(15)],.0015*q,"head",bind)
    for v in (.310,.620):
        f.stroke("mask shallow pleat",[xy(-.91+1.82*i/15,v) for i in range(16)],.0009*q,"head",strip)
    for sign in (-1,1):
        bot,top=xy(sign,0),xy(sign,1)
        e_x=cx+sign*.077*q
        e_z=ze-.025*q
        # Surface ray locates the ear when the patient's head morphology permits.
        e_y=f.surface(e_x,e_z,.003*q,False)
        e_y=max(-.075*q,min(-.023*q,e_y))
        pts=[top,(e_x-sign*.004*q,e_y-.006*q,e_z+.014*q),
             (e_x+sign*.004*q,e_y+.004*q,e_z),
             (e_x+sign*.002*q,e_y+.002*q,e_z-.016*q),bot]
        f.stroke("mask elastic ear loop",pts,.0017*q,"head",bind)


def _clipboard(f):
    s=f.s
    bone="wrist.L"
    w=f.bones[bone].tail_local
    # Set the top edge behind the fingers so the hand can overlap the board
    # rather than the board cutting through the knuckles in the rest pose.
    hand=[v.y for v in f.bodyv if v.x>w.x+.012*s and abs(v.z-w.z)<.054*s]
    x,y,z=w.x+.031*s,max(hand,default=w.y)+.014*s,w.z-.105*s
    dark=_mat("chart board","4B7792",.43)
    paper=_mat("chart paper","F2F4E9",.52)
    ink=_mat("chart printed lines","7E9FAC",.48)
    clip=_mat("chart top clip","BBC9CD",.24,.61)
    f.box("wrist-parented chart board",(x,y,z),(.138*s,.009*s,.232*s),bone,dark,.006*s)
    f.box("chart paper sheet",(x,y-.006*s,z-.001*s),(.116*s,.002*s,.195*s),bone,paper,.002*s)
    f.box("chart top clip",(x,y-.008*s,z+.098*s),(.071*s,.008*s,.022*s),bone,clip,.003*s)
    for j in range(5):
        f.box("short generic chart rule",(x-.016*s,y-.0075*s,z+(.047-j*.025)*s),
              ((.094 if j%2 else .079)*s,.0005*s,.0021*s),bone,ink,.0002*s)


def _skull(f, z):
    q, x = f.q, f.head.x
    section = [v for v in f.bodyv if abs(v.z-z)<.025*q and abs(v.x-x)<.12*q]
    if not section:
        return x, f.head.y, .078*q, .100*q
    lo, hi = min(v.x for v in section), max(v.x for v in section)
    front, back = min(v.y for v in section), max(v.y for v in section)
    return (lo+hi)/2, (front+back)/2, (hi-lo)/2, (back-front)/2


def _headgear(f, job):
    q = f.q
    z = f.eyes.z + {"surgeon":.027,"police":.047,"firefighter":.046,
                     "construction worker":.054,"chef":.047,"pilot":.047}[job]*q
    cx, cy, r, d = _skull(f, z)
    r, d = r+.009*q, d+.010*q
    cap = {"surgeon":"439994","police":"202E49","firefighter":"C89317",
           "construction worker":"F0B51D","chef":"FAF6E9","pilot":"26384D"}[job]
    rigid = job in {"firefighter","construction worker"}
    cloth = _mat(job+" crown", cap, .29 if rigid else .55, textile=not rigid)
    dark = _mat("headwear visor or band","202934",.28)
    yellow = _mat("helmet reflective insert","F2D54E",.31,emission=.10)
    leather = _mat("helmet edge trim","473A23",.42)
    band = _mat(job+" hat band", {"chef":"E3DDD0","surgeon":"347E7E"}.get(job,"222D3A"),.51,textile=True)
    height = (max(f.top-z,.074*q)+.014*q)
    profiles = {
        "surgeon": [(0,1),(.18,1),(.56,.97),(.79,.86),(.95,.64),(1,.30),(1.02,.008)],
        "police": [(0,1),(.25,1.02),(.69,1.16),(.88,1.11),(1,.85),(1.02,.008)],
        "pilot": [(0,1),(.26,1),(.65,1.14),(.87,1.09),(1,.84),(1.02,.008)],
        "firefighter": [(0,1.06),(.24,1.04),(.53,.96),(.77,.81),(.94,.57),(1.09,.27),(1.11,.008)],
        "construction worker": [(0,1.035),(.22,1.025),(.48,1),(.72,.86),(.91,.58),(1.08,.27),(1.10,.008)],
        "chef": [(0,1),(.17,1),(.36,1.05),(.45,1.20),(.70,1.25),(.91,1.10),(1,.83),(1.04,.008)],
    }[job]
    if job == "chef":
        height *= 1.72
    def ring(a, level, scale):
        pleat = 1+.042*max(0,(level-.28))*cos(14*a) if job=="chef" else 1
        rise = ((-.023*q*max(0,sin(a)-.12)) if job=="surgeon" else
                max(0,-sin(a))*.023*q*min(level*1.55,1) if job in {"police","pilot"} else 0)
        return (cx+r*scale*pleat*cos(a),cy+d*scale*pleat*sin(a),z+height*level+rise)
    n=64
    vs = [ring(tau*i/n,h,k) for h,k in profiles for i in range(n)]
    faces = [(j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i)
             for j in range(len(profiles)-1) for i in range(n)]
    faces.append(tuple(range((len(profiles)-1)*n,len(profiles)*n)))
    crown = f.mesh(job+" constructed crown",vs,faces,"head",cloth,True,.002*q)
    sub=crown.modifiers.new("Rounded crown seams","SUBSURF")
    sub.levels=sub.render_levels=1
    if job in {"surgeon","chef","police","pilot"}:
        pts=[ring(tau*i/56,.015,1.005) for i in range(56)]
        f.stroke("cloth hat lower seam",pts,.0035*q,"head",band,cyclic=True)
        if job in {"chef","police","pilot"}:
            vs=[ring(tau*i/56,h,1.015) for h in (.008,.255) for i in range(56)]
            f.mesh("sewn crown band",vs,[(i,(i+1)%56,56+(i+1)%56,56+i) for i in range(56)],
                   "head",band,True,.0025*q)
        if job=="surgeon":
            pts=[ring(tau*i/56,.16,1.009) for i in range(56)]
            f.stroke("cloth cap stitched hem",pts,.0014*q,"head",band,cyclic=True)
    if job not in {"chef","surgeon"}:
        circular = job == "firefighter"
        angles=[tau*i/64 for i in range(64)] if circular else [pi+.10+(pi-.20)*i/36 for i in range(37)]
        def visor(a,u):
            front=max(0,-sin(a))
            rear=max(0,sin(a))
            widen=(.016+.034*front+.045*rear) if circular else (.040 if rigid else .044)*front**.76
            x=cx+(r+u*widen*q)*cos(a)
            y=cy+(d+u*widen*q)*sin(a)
            zz=z+(.003-.016*u*front-.026*u*rear)*q
            return (x,y,zz)
        n=len(angles)
        vs=[visor(a,u) for u in (0,.45,1) for a in angles]
        fs=[(j*n+i,j*n+(i+1)%n,(j+1)*n+(i+1)%n,(j+1)*n+i)
            for j in range(2) for i in range(n if circular else n-1)]
        f.mesh("helmet brim" if rigid else "peaked cap visor",vs,fs,"head",cloth if rigid else dark,True,.005*q)
        f.stroke("brim binding",[visor(a,1) for a in angles],.0026*q,"head",leather if rigid else dark,cyclic=circular)
    if rigid:
        f.stroke("raised helmet center ridge", [ring(a,h,k*1.012) for a,h,k in
                 [(1.5*pi,.08,1.03),(1.5*pi,.42,.98),(1.5*pi,.75,.86),
                  (1.5*pi,1.04,.45),(1.5*pi,1.105,.010),(.5*pi,1.04,.45),
                  (.5*pi,.75,.86),(.5*pi,.42,.98),(.5*pi,.08,1.03)]],
                 .005*q,"head",cloth)
    if job == "firefighter":
        shield=[(-.031,.014),(-.034,.058),(0,.075),(.034,.058),(.031,.014),(0,.005)]
        f.mesh("plain helmet front plate",[(cx+x*q,cy-d*1.06+.16*abs(x)*q,z+h*q) for x,h in shield],
               [tuple(range(6))],"head",leather,False,.005*q)
        f.box("reflective helmet tab",(cx,cy-d*1.06-.004*q,z+.036*q),
              (.030*q,.002*q,.025*q),"head",yellow,.002*q)
    if job == "pilot":
        gold=_mat("generic brass rank trim","D5AF57",.29,.50)
        f.stroke("plain cap strap", [ring(a,.16,1.031) for a in (3.5,3.85,4.18,4.71,5.24,5.57,5.92)],
                 .0026*q,"head",gold)


def _rest_coordinates(o):
    a=o.data.attributes.get("kw_rest") or o.data.attributes.new("kw_rest","FLOAT_VECTOR","POINT")
    a.data.foreach_set("vector",[c for v in o.data.vertices for c in v.co])


def _hi_vis(f, o, base, variant):
    # The POINT-domain rest coordinates travel through armature deformation,
    # keeping paint on the sleeve rather than projecting it through the pose.
    _rest_coordinates(o)
    m=base.copy()
    m.name=f"{o.name} | animated reflective tape"
    tree=m.node_tree
    bs=tree.nodes.get("Principled BSDF")
    link=tree.links
    attr=tree.nodes.new("ShaderNodeAttribute")
    attr.attribute_name="kw_rest"
    coord=tree.nodes.new("ShaderNodeSeparateXYZ")
    link.new(attr.outputs["Vector"],coord.inputs[0])
    def calc(op,a,b=0):
        n=tree.nodes.new("ShaderNodeMath")
        n.operation=op
        for i,arg in enumerate((a,b)):
            if isinstance(arg,(int,float)):
                n.inputs[i].default_value=arg
            else:
                link.new(arg,n.inputs[i])
        return n.outputs[0]
    def within(v, center, half):
        return calc("LESS_THAN",calc("ABSOLUTE",calc("SUBTRACT",v,center)),half)
    def both(a,b): return calc("MULTIPLY",a,b)
    def either(a,b): return calc("MAXIMUM",a,b)
    ax=calc("ABSOLUTE",coord.outputs["X"])
    z=coord.outputs["Z"]
    s=f.s
    def tape(w):
        if variant=="construction worker":
            return both(either(both(within(ax,.105*s,w),calc("GREATER_THAN",z,f.waist+.09*s)),
                               within(z,f.waist+.107*s,w)),calc("LESS_THAN",ax,.170*s))
        torso=both(within(z,f.waist+.105*s,w),calc("LESS_THAN",ax,.245*s))
        arm=within(ax,(.303 if variant=="paramedic" else .346)*s,w)
        return either(torso,arm) if variant=="firefighter" else both(arm, calc("GREATER_THAN",z,f.mid))
    color=bs.inputs["Base Color"]
    fabric=color.links[0].from_socket if color.is_linked else None
    def mix(mask,low,hex_color):
        n=tree.nodes.new("ShaderNodeMixRGB")
        link.new(mask,n.inputs[0])
        if low is None:
            n.inputs[1].default_value=color.default_value
        else:
            link.new(low,n.inputs[1])
        n.inputs[2].default_value=_rgba(hex_color)
        return n.outputs[0]
    outer=tape((.026 if variant!="paramedic" else .019)*s)
    inner=tape((.012 if variant!="paramedic" else .014)*s)
    if variant=="construction worker":
        opening=both(calc("LESS_THAN",ax,.023*s),calc("LESS_THAN",coord.outputs["Y"],-.020*s))
        sleeves=calc("GREATER_THAN",ax,.167*s)
        fabric=mix(either(sleeves,opening),fabric,"696D70")
    tint=mix(outer,fabric,"EFE648" if variant!="paramedic" else "A4A383")
    tint=mix(inner,tint,"E2EBEA")
    link.new(tint,color)
    link.new(tint,bs.inputs["Emission Color"])
    link.new(calc("MULTIPLY",inner,.15),bs.inputs["Emission Strength"])
    return m


def _waist(f):
    z=f.waist-.018*f.s
    s=f.s
    mat=_mat("black woven duty belt","282D34",.46,textile=True)
    hardware=_mat("duty belt buckle","949FA5",.31,.50)
    bone="spine04"
    center_y=(f.surface(0,z)+f.surface(0,z,back=True))/2
    front=f.surface(0,z,.008*s)
    back=f.surface(0,z,.008*s,back=True)
    outer_x=max((v.co.x for v in f.main.data.vertices if abs(v.co.z-z)<.038*s and abs(v.co.x)<.24*s),default=.175*s)+.008*s
    def pt(a,h):
        x=outer_x*cos(a)
        y=center_y+(.5*(back-front)+.009*s)*sin(a)
        hit=f.ray(f.cloth,x,z,sin(a)>0)
        if hit:
            y=max(hit.y+.007*s,y) if sin(a)>0 else min(hit.y-.007*s,y)
        return x,y,z+h
    n=80
    vs=[pt(tau*i/n,h) for h in (-.019*s,.019*s) for i in range(n)]
    f.mesh("contoured duty belt strap",vs,[(i,(i+1)%n,(i+1)%n+n,i+n) for i in range(n)],
           bone,mat,True,.005*s)
    f.box("plain metal belt buckle",(0,front-.017*s,z),(.064*s,.015*s,.046*s),bone,hardware,.004*s)
    f.box("buckle inset",(0,front-.026*s,z),(.046*s,.004*s,.031*s),bone,mat,.003*s)
    for x,w,h in [(-.136,.065,.103),(-.071,.046,.069),(.107,.073,.082)]:
        y=f.surface(x*s,z,.025*s)
        f.box("closed fabric utility pouch",(x*s,y,z-.015*s),(w*s,.045*s,h*s),bone,mat,.006*s)
        f.box("utility pouch cover flap",(x*s,y-.025*s,z+.012*s),(w*s,.006*s,.028*s),bone,mat,.004*s)
        f.sphere("utility pouch fastener",(x*s,y-.029*s,z+.009*s),(.005*s,.003*s,.005*s),bone,hardware)


def _name_strip(f,label,x=.104, bg="28373D"):
    s=f.s
    x=x*s
    z=f.neck.z-.154*s
    backing=_mat("plain stitched job strip",bg,.52,textile=True)
    lettering=_mat("plain uniform lettering","EDF5F0",.50)
    f.patch("unbranded uniform name strip",[(x-.056*s,z-.012*s),(x+.056*s,z-.012*s),
            (x+.056*s,z+.012*s),(x-.056*s,z+.012*s)],backing,pad=.006*s)
    f.text("generic occupational lettering",label,.013*s,f.on(x,z,.013*s),"spine01",lettering)


def _star(f):
    silver=_mat("generic brushed-silver star","B7CCD7",.25,.57)
    s=f.s
    x,z=-.102*s,f.neck.z-.151*s
    points=[(x+(.032 if i%2==0 else .014)*s*sin(tau*i/10),
             z+(.032 if i%2==0 else .014)*s*cos(tau*i/10)) for i in range(10)]
    f.patch("generic five-point silver star",points,silver,pad=.008*s)
    f.sphere("plain star center disk",f.on(x,z,.010*s),(.012*s,.004*s,.012*s),"spine01",silver)


def _buttons(f, double=False, pale=False):
    s=f.s
    m=_mat("uniform sewn buttons","EDDFCD" if pale else "2E3A4A",.37)
    for dx in ((-.05,.05) if double else (0,)):
        for j in range(4):
            x,z=dx*s,f.neck.z-(.11+j*.069)*s
            f.sphere("uniform button",f.on(x,z,.008*s),(.006*s,.0032*s,.006*s),"spine01",m)


def _coat_front(f, light=False):
    s,n=f.s,f.neck.z
    edge=_mat("coat sewn placket","CFD8D5" if light else "A09269",.57,textile=True)
    for sign in (-1,1):
        points=[(sign*.060*s,n+.012*s),(sign*.092*s,n-.080*s),(sign*.059*s,n-.109*s),
                (sign*.075*s,n-.122*s),(sign*.019*s,n-.257*s)]
        f.stroke("coat fold edge",[f.on(x,z,.007*s) for x,z in points],.0021*s,"spine01",edge,smooth=False)
    _pocket(f,-.116*s,n-.201*s,.079*s,.068*s,edge,sewn=True)


def _pilot_details(f):
    s,n=f.s,f.neck.z
    navy=_mat("pilot shoulder rank and tie","253548",.43,textile=True)
    gold=_mat("unbranded gold rank bars","CCA456",.32,.38)
    coords=[(-.024,n-.053*s),(.024,n-.053*s),(.012,n-.082*s),(.028,n-.234*s),
            (0,n-.261*s),(-.028,n-.234*s),(-.012,n-.082*s)]
    # Convex parts keep the tie edges clean around its narrow knot.
    f.patch("tie knot",[(x*s,z) for x,z in coords[:3]+coords[-1:]],navy,pad=.012*s)
    f.patch("tie blade",[(x*s,z) for x,z in coords[2:]],navy,pad=.010*s)
    for sign in (-1,1):
        x=.138*s*sign
        z=n-.042*s
        outline=[(x-.040*s,z+.012*s),(x+.040*s,z+.006*s),(x+.041*s,z-.020*s),(x-.040*s,z-.014*s)]
        f.patch("dark shoulder epaulet",outline,navy,pad=.006*s)
        for a in (-.017,.003,.023):
            xx=x+a*s
            f.stroke("plain gold rank bar",[f.on(xx,z+.007*s,.009*s),f.on(xx,z-.012*s,.009*s)],
                     .0025*s,"spine01",gold,smooth=False)


def _glasses(f):
    q=f.q
    frame=_mat("plain safety frame","314246",.26)
    centers=[f.bones["eye."+side].head_local for side in ("L","R")]
    rx=min(.029*q,.425*abs(centers[0].x-centers[1].x))
    inner=[]
    for e in centers:
        sign=1 if e.x>f.eyes.x else -1
        # An eye-centre ray alone can go through the open eyelid into the
        # cavity. Fit against the whole rim and ignore far-side hits.
        hits=[f.ray(f.body,e.x+rx*cos(a),e.z+.019*q*sin(a))
              for a in (i*tau/28 for i in range(28))]
        y_front=min((v.y for v in hits if v is not None and v.y<f.head.y-.020*q),
                    default=e.y-.020*q)-.006*q
        def rim(a):
            x=e.x+rx*cos(a)
            z=e.z+.019*q*sin(a)
            y=y_front+.005*q*max(0,sign*cos(a))
            hit=f.ray(f.body,x,z)
            if hit is not None:
                y=min(y,hit.y-.004*q)
            return x,y,z
        f.stroke("plain safety glasses lens rims",[rim(tau*i/28) for i in range(28)],
                 .0023*q,"head",frame,cyclic=True)
        inner.append(rim(pi if sign==1 else 0))
        x,y,z=rim(0 if sign==1 else pi)
        ex=f.eyes.x+sign*.076*q
        f.stroke("safety glasses temple arm",[(x,y,z),(x+sign*.008*q,y+.021*q,z+.002*q),
                 (ex,f.head.y+.017*q,z),(ex,f.head.y+.033*q,z-.006*q)],.0017*q,"head",frame)
    cx,cz=f.eyes.x,f.eyes.z+.004*q
    points=[inner[0],(cx,min(f.surface(cx,cz,.007*q,False),inner[0][1],inner[1][1]),cz+.003*q),inner[1]]
    f.stroke("safety glasses nose bridge",points,.0021*q,"head",frame)


def _patient_smock(f, fabric):
    s=f.s
    top,bot=f.waist+.061*s,f.waist-.224*s
    n,rows=64,19
    cy=(f.surface(0,top)+f.surface(0,top,back=True))/2
    def radius(a,z):
        d=Vector((cos(a),sin(a),0))
        origin=Vector((0,cy,z))
        hit=f.cloth.ray_cast(origin+.6*d,-d,.63)[0]
        return (hit-origin).dot(d) if hit is not None else .116*s
    start=[radius(tau*i/n,top) for i in range(n)]
    vs=[]
    for j in range(rows):
        u=j/(rows-1)
        z=top+(bot-top)*u
        for i in range(n):
            a=tau*i/n
            loose=max(start[i]+(.028+.007*cos(9*a))*s*u,
                      radius(a,z)+.008*s)
            blend=min(1,u*5)
            r=(start[i]-.003*s)*(1-blend)+loose*blend
            vs.append((r*cos(a),cy+r*sin(a),z+.008*s*cos(a*5)*u*u))
    fs=[(j*n+i,(j+1)*n+i,(j+1)*n+(i+1)%n,j*n+(i+1)%n) for j in range(rows-1) for i in range(n)]
    o=f.mesh("patterned hospital smock hem",vs,fs,"spine04",fabric,True,.0025*s)
    mod=o.modifiers.new("Soft smock folds","SUBSURF")
    mod.levels=mod.render_levels=1


_UNIFORMS={
    # Top, trousers, closed shoes. The business suit keeps the original UVs.
    "police":("283C5B","212D46","222833"),
    "paramedic":("254C3E","243F37","262F2C"),
    "firefighter":("B59A64","9A8056","373331"),
    "patient":("DBEFED","90B7BD","D9E3E0"),
    "chef":("F5F0E5","383E45","2D3338"),
    "construction worker":("E6A82B","555C69","45392C"),
    "pilot":("F2F4EC","27364D","293037"),
    "scientist":("F4F5EB","535F66","303D46"),
}


def _nonmedical(f, outfits, job):
    if job=="business":
        return
    top,lower,shoe=_UNIFORMS[job]
    fabric=_mat(job+" uniform cloth",top,.61,textile=True,patterned=job=="patient")
    if f.main:
        if job in {"paramedic","firefighter","construction worker"}:
            fabric=_hi_vis(f,f.main,fabric,job)
        _repaint(f.main,fabric,_mat(job+" trousers",lower,.62,textile=True),f.waist)
    for o in outfits:
        if (_asset(o) or "").startswith("shoes"):
            if job in {"patient","chef","scientist","pilot"}:
                _cuff_clearance(o)
            _shoes(o,_mat(job+" footwear",shoe,.48),_mat("gripping rubber sole","33383B",.62))
    s,n=f.s,f.neck.z
    if job=="police":
        _star(f)
        _name_strip(f,"POLICE",bg="334562")
        _buttons(f)
        if f.main:
            _waist(f)
        radio=_mat("plain radio case","272F39",.39)
        x,z=-.142*s,n-.236*s
        x,y,z=f.on(x,z,.020*s)
        f.box("shoulder radio housing",(x,y,z),(.031*s,.020*s,.055*s),"spine01",radio,.004*s)
        f.stroke("short radio antenna",[(x-.008*s,y,z+.018*s),(x-.014*s,y,z+.066*s)],
                 .0025*s,"spine01",radio,smooth=False)
    if job=="paramedic":
        _name_strip(f,"PARAMEDIC",x=-.102,bg="274D40")
        _pocket(f,.103*s,n-.189*s,.085*s,.064*s,_mat("utility pocket","30584C",.55,textile=True),True)
    if job=="firefighter":
        _coat_front(f)
        _name_strip(f,"FIRE",x=.116,bg="5D5039")
        latch=_mat("smoke-resistant coat latch","49483B",.39)
        for j in range(3):
            f.box("turnout coat fastener",f.on(0,n-(.12+j*.073)*s,.011*s),
                  (.048*s,.011*s,.017*s),"spine01",latch,.003*s)
    if job=="patient" and f.main:
        _patient_smock(f,fabric)
        edging=_mat("hospital smock neck facing","B7D3D6",.50,textile=True)
        line=[(-.080,n-.006*s),(-.051,n-.038*s),(0,n-.058*s),(.051,n-.038*s),(.080,n-.006*s)]
        f.stroke("bound smock neckline",[f.on(x*s,z,.007*s) for x,z in line],.0033*s,"spine01",edging)
        w=f.bones["wrist.R"].head_local
        f.box("plain hospital wristband",(w.x,w.y-.018*s,w.z),(.043*s,.005*s,.017*s),"wrist.R",edging,.003*s)
    if job=="chef":
        _buttons(f,double=True,pale=True)
        seam=_mat("chef jacket piping","D1C8B7",.58,textile=True)
        points=[(.020,n-.076*s),(.070,n-.105*s),(.070,n-.320*s)]
        f.stroke("double breasted jacket seam",[f.on(x*s,z,.007*s) for x,z in points],.002*s,
                 "spine01",seam,smooth=False)
    if job=="construction worker":
        dark=_mat("vest opening binding","4D5355",.49,textile=True)
        for sign in (-1,1):
            points=[(.071,n-.02*s),(.058,n-.085*s),(.026,n-.153*s),(.026,n-.365*s)]
            f.stroke("hi-vis vest center binding",[f.on(sign*x*s,z,.009*s) for x,z in points],.004*s,
                     "spine01",dark,smooth=False)
    if job=="pilot":
        _pilot_details(f)
    if job=="scientist":
        _coat_front(f,light=True)
        _id_card(f,"LAB","448DA1",side=1)
        _glasses(f)
        x,z=-.115*s,n-.175*s
        pen=_mat("pocket pen","205875",.34)
        f.box("lab coat pen",f.on(x,z,.012*s),(.008*s,.006*s,.050*s),"spine01",pen,.002*s)


_PALETTES = {
    "doctor": [("237E8F","216D80","3A9BA5"),("4F84A9","356F97","6799BA"),("2B8D8C","287D7F","53A8A4")],
    "nurse": [("79BBC9","609FAF","97CDCF"),("79ADCB","6298B7","99C8DC"),("8ABEB6","74A9A4","A7CFC4")],
    "surgeon": [("35888B","267277","559F9D")],
}


def dress(p, job, seed):
    """Replace recognizable local outfit meshes and generated accessories in place."""
    job=_job(job)
    p._kw_wardrobe_options = getattr(p,"_kw_wardrobe_options",{})
    options=p._kw_wardrobe_options
    for o in reversed(getattr(p,"_kw_wardrobe_owned",[])):
        if o in p.parts:
            p.parts.remove(o)
        bpy.data.objects.remove(o,do_unlink=True)
    p._kw_wardrobe_owned=[]
    _gloves(p)
    for o in p.parts:
        if _hair_name(o):
            o.hide_render=o.hide_viewport=(job in _CAPS)
    if "female" not in options:
        options["female"] = _P.TargetService.get_macro_info_dict_from_basemesh(p.body)["gender"] < .5
    desired=options.get("outfit") or _resolve_outfit(job,options["female"])
    # On a true redress of civilian assets previously recoloured by this module,
    # reinstall the asset to bring back its original UV material and sole colors.
    if job=="civilian" and getattr(p,"wardrobe_job",None) not in {None,"civilian"}:
        for o in tuple(p.parts):
            a=_asset(o)
            if a:
                _remove_asset(p,o,a)
    outfits=_put_on(p,desired)
    main=next((o for o in outfits if "suit" in (_asset(o) or "")),None)
    if job=="nurse":
        _nurse_hair(p)
    p.wardrobe_job=job
    if job=="civilian":
        tex=options.get("tee") or _rng(seed,"civilian tee").choice(_C.TEES)
        if main and main.active_material and main.active_material.node_tree:
            n=main.active_material.node_tree.nodes.get("diffuseTexture")
            path=_TEX/f"tee_{tex}.jpg"
            if n is not None and path.is_file() and _asset(main)=="male_casualsuit04":
                n.image=bpy.data.images.load(str(path),check_existing=True)
        if main and options.get("brand",True):   # Zack look: the channel name printed on the main character's tee
            try:
                f=_Fit(p,main); sz=f.s; z=f.neck.z-.17*sz
                ink=_mat("tee chest print","1E2328" if tex in ("white","skyblue","mustard","grey","orange") else "F2F4F5",.6)
                f.text("kinda wild tee print","KINDA WILD",.022*sz,f.on(0.0,z,.012*sz),"spine01",ink)
                p._kw_wardrobe_owned=f._made
            except Exception as e:
                print("tee print skipped",repr(e))
        return p
    f=_Fit(p,main)
    if job in _MEDICAL:
        rng=_rng(seed,job+" color")
        top,pants,seam=rng.choice(_PALETTES[job])
        trouser_mat=_mat("scrub trousers",pants,.63,textile=True)
        if main:
            _repaint(main,_mat("scrub top",top,.59,textile=True),trouser_mat,f.waist)
        for o in outfits:
            if (_asset(o) or "").startswith("shoes"):
                _cuff_clearance(o)
                _shoes(o,_mat("hospital slip-resistant sneaker","D7E4E2",.49),
                       _mat("scrub sneaker sole","A6B4BA",.52),trouser_mat)
        _scrub_seams(f,seam)
        if job=="doctor":
            _stethoscope(f)
            _id_card(f,"MD","2E8C96",side=1)
            if options.get("mask",_rng(seed,"doctor mask").random()<.18):
                _face_mask(f)
            if options.get("gloves",True):
                _gloves(p,"2779D8")
        if job=="nurse":
            _id_card(f,"RN","3579AD",side=-1)
            if options.get("clipboard",_rng(seed,"nurse clipboard").random()<.24):
                _clipboard(f)
            if options.get("mask",False):
                _face_mask(f)
            if options.get("gloves",False):
                _gloves(p,"5AA5ED")
        if job=="surgeon":
            _face_mask(f,"F0F5EF")
            _gloves(p,"F1F5EB")
    else:
        _nonmedical(f,outfits,job)
    if job in _CAPS:
        _headgear(f,job)
    p._kw_wardrobe_owned=f._made
    return p
