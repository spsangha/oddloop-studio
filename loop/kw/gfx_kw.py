"""Kinda Wild graphics props. Blender 4.2; +Z up, primary face toward -Y.

All objects are linked only to the supplied collection. Constructors build
geometry once; set() is random-access and never inserts animation keyframes.
Most props expose .root, an empty at their anchoring origin, for optional
whole-prop repositioning. Colors passed as tuples are scene-linear RGB.
"""

from bisect import bisect_right
from math import cos, exp, pi, sin, sqrt, tau
from pathlib import Path
from random import Random
from shutil import which
from subprocess import DEVNULL, SubprocessError, run
from tempfile import TemporaryDirectory

import bpy
import bmesh
from mathutils import Vector


__all__ = [
    "Backdrop", "Label3D", "Gauge", "Arrow3D", "Bracket", "Calendar",
    "ScanMonitor", "Crackle", "SkinBlock",
]

_FRONT = Vector((0, -1, 0))
_Z = Vector((0, 0, 1))
_FONT = Path(__file__).resolve().parents[1] / "Montserrat-Black.ttf"
# This static Montserrat file has legitimate TrueType overlaps (e.g. 1, 5, W).
# FreeType uses non-zero winding; Blender 4.2's font tessellator can leave holes.
# If the host has FontTools and Shapely, normalize only overlapping outlines
# once and pack the result. No installation, modified asset, or temp font
# dependency is required; raw Montserrat is the portable fallback.
_FONT_FIX = r"""
import sys
from fontTools.ttLib import TTFont
from fontTools.pens.basePen import BasePen
from fontTools.pens.ttGlyphPen import TTGlyphPen
from shapely.geometry import LinearRing, LineString, Polygon, MultiPolygon
from shapely.geometry.polygon import orient
from shapely.ops import polygonize, unary_union

class Flat(BasePen):
    def __init__(self):
        super().__init__(None)
        self.paths = []
    def _moveTo(self, p):
        self.paths.append([p])
    def _lineTo(self, p):
        if p != self.paths[-1][-1]:
            self.paths[-1].append(p)
    def _qCurveToOne(self, b, c):
        a = self.paths[-1][-1]
        for i in range(1, 11):
            t = i / 10
            v = 1 - t
            self._lineTo(tuple(v*v*x + 2*v*t*y + t*t*z for x,y,z in zip(a,b,c)))
    def _closePath(self):
        self._lineTo(self.paths[-1][0])
    def _endPath(self):
        self._closePath()

def winding(x, y, paths):
    result = 0
    for pts in paths:
        for a,b in zip(pts,pts[1:]):
            if (a[1]<=y<b[1]) or (b[1]<=y<a[1]):
                cross = (b[0]-a[0])*(y-a[1]) - (x-a[0])*(b[1]-a[1])
                if a[1]<=y and cross>0:
                    result += 1
                if b[1]<=y and cross<0:
                    result -= 1
    return result

font = TTFont(sys.argv[1])
table = font['glyf']
changed = False
for name in font.getGlyphOrder():
    g = table[name]
    if g.numberOfContours < 1:
        continue
    flat = Flat()
    try:
        g.draw(flat,table)
    except NotImplementedError:
        continue
    paths = [p for p in flat.paths if len(p) >= 4]
    rings = [LinearRing(p) for p in paths]
    if not rings:
        continue
    if all(r.is_simple for r in rings) and not any(a.intersects(b) for i,a in enumerate(rings) for b in rings[i+1:]):
        continue
    parts = polygonize(unary_union([LineString(p) for p in paths]))
    inside = []
    for p in parts:
        q = p.representative_point()
        if winding(q.x,q.y,paths):
            inside.append(p)
    if not inside:
        continue
    shape = unary_union(inside).simplify(.32,preserve_topology=True)
    polygons = list(shape.geoms) if isinstance(shape,MultiPolygon) else [shape]
    if not all(isinstance(p,Polygon) for p in polygons):
        continue
    pen = TTGlyphPen(None)
    for p in polygons:
        p = orient(p,-1.)
        for ring in (p.exterior, *p.interiors):
            pts = []
            for x,y in list(ring.coords)[:-1]:
                xy = (round(x),round(y))
                if not pts or pts[-1] != xy:
                    pts.append(xy)
            if len(pts) <= 2:
                continue
            pen.moveTo(pts[0])
            for xy in pts[1:]:
                pen.lineTo(xy)
            pen.closePath()
    repaired = pen.glyph()
    if repaired.numberOfContours > 0:
        table[name] = repaired
        changed = True
if changed:
    font.save(sys.argv[2])
"""


def _unit(x):
    return max(0.0, min(1.0, float(x)))


def _smooth(x):
    x = _unit(x)
    return x * x * (3 - 2 * x)


def _linear(s):
    return s / 12.92 if s < .04045 else ((s + .055) / 1.055) ** 2.4


def _hex(h):
    return tuple(_linear(int(h[i:i + 2], 16) / 255) for i in (0, 2, 4))


def _rgba(c):
    return tuple(c[:3]) + (1,)


def _object(name, data, coll, parent=None, loc=(0, 0, 0)):
    o = bpy.data.objects.new(name, data)
    coll.objects.link(o)
    o.parent = parent
    o.location = loc
    return o


def _root(name, coll, origin, parent=None):
    o = _object(name, None, coll, parent, origin)
    o.empty_display_size = .035
    return o


def _vis(obj, visible):
    hidden = not visible
    if obj.hide_render != hidden:
        obj.hide_render = hidden
    if obj.hide_viewport != hidden:
        obj.hide_viewport = hidden


def _tree(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    t = m.node_tree
    t.nodes.clear()
    out = t.nodes.new("ShaderNodeOutputMaterial")
    out.location = (560, 180)
    return m, t, out


def _socket(t, target, value):
    if isinstance(value, bpy.types.NodeSocket):
        t.links.new(value, target)
    else:
        target.default_value = value


def _math(t, op, a, b=0):
    n = t.nodes.new("ShaderNodeMath")
    n.operation = op
    _socket(t, n.inputs[0], a)
    _socket(t, n.inputs[1], b)
    return n.outputs[0]


def _vmath(t, op, a, b=None):
    n = t.nodes.new("ShaderNodeVectorMath")
    n.operation = op
    _socket(t, n.inputs[0], a)
    if b is not None:
        _socket(t, n.inputs[1], b)
    return n.outputs["Value"] if op in {"LENGTH", "DISTANCE", "DOT_PRODUCT"} else n.outputs[0]


def _mix(t, fac, a, b, blend="MIX"):
    n = t.nodes.new("ShaderNodeMixRGB")
    n.blend_type = blend
    for i, val in enumerate((fac, a, b)):
        _socket(t, n.inputs[i], val)
    return n.outputs[0]


def _ramp(t, value, stops):
    n = t.nodes.new("ShaderNodeValToRGB")
    r = n.color_ramp
    r.interpolation = "EASE"
    for i, (p, col) in enumerate(stops):
        el = r.elements[i] if i < 2 else r.elements.new(p)
        el.position, el.color = p, col
    _socket(t, n.inputs["Fac"], value)
    return n.outputs["Color"]


def _emit(t, out, color, strength=1):
    n = t.nodes.new("ShaderNodeEmission")
    _socket(t, n.inputs["Color"], color)
    _socket(t, n.inputs["Strength"], strength)
    t.links.new(n.outputs[0], out.inputs["Surface"])
    return n


def _ematerial(name, c, strength=1):
    m, t, out = _tree(name)
    m.diffuse_color = _rgba(c)
    return m, _emit(t, out, _rgba(c), strength)


def _paint(name, c, rough=.27, metal=0, coat=.28, glow=0, sss=0, tex=None):
    m, t, out = _tree(name)
    m.diffuse_color = _rgba(c)
    p = t.nodes.new("ShaderNodeBsdfPrincipled")
    for name_, val in (
        ("Base Color", _rgba(c)), ("Roughness", rough), ("Metallic", metal),
        ("Coat Weight", coat), ("Coat Roughness", .14), ("Subsurface Weight", sss),
        ("Subsurface Radius", (1, .5, .27)), ("Subsurface Scale", .025),
        ("Emission Color", _rgba(c)), ("Emission Strength", glow),
    ):
        p.inputs[name_].default_value = val
    if tex:
        dark, light, axes, scale, bump, distance = tex
        uv = t.nodes.new("ShaderNodeTexCoord").outputs["Generated"]
        n = t.nodes.new("ShaderNodeTexNoise")
        _socket(t, n.inputs["Vector"], _vmath(t, "MULTIPLY", uv, axes))
        n.inputs["Scale"].default_value = scale
        n.inputs["Detail"].default_value = 2.6
        n.inputs["Roughness"].default_value = .68
        col = _ramp(t, n.outputs["Fac"], ((.24, _rgba(dark)), (.78, _rgba(light))))
        _socket(t, p.inputs["Base Color"], col)
        b = t.nodes.new("ShaderNodeBump")
        b.inputs["Strength"].default_value = bump
        b.inputs["Distance"].default_value = distance
        _socket(t, b.inputs["Height"], n.outputs["Fac"])
        _socket(t, p.inputs["Normal"], b.outputs["Normal"])
    t.links.new(p.outputs[0], out.inputs["Surface"])
    return m


def _glass(name, coverage, tint, ior=1.35, rough=.12):
    """Mainly clear transmission, but retain a controllable reflected edge."""
    m, t, out = _tree(name)
    m.diffuse_color = (*tint, coverage)
    p = t.nodes.new("ShaderNodeBsdfPrincipled")
    p.inputs["Base Color"].default_value = _rgba(tint)
    p.inputs["Transmission Weight"].default_value = 1
    p.inputs["IOR"].default_value = ior
    p.inputs["Roughness"].default_value = rough
    clear = t.nodes.new("ShaderNodeBsdfTransparent")
    mix = t.nodes.new("ShaderNodeMixShader")
    mix.inputs[0].default_value = coverage
    t.links.new(clear.outputs[0], mix.inputs[1])
    t.links.new(p.outputs[0], mix.inputs[2])
    t.links.new(mix.outputs[0], out.inputs["Surface"])
    return m


def _mesh(name, verts, faces, coll, parent=None, mat=None, loc=(0, 0, 0)):
    me = bpy.data.meshes.new(name)
    me.from_pydata(verts, [], faces)
    me.update()
    o = _object(name, me, coll, parent, loc)
    if mat:
        me.materials.append(mat)
    return o


def _cube(name, size, coll, root, mat, loc=(0, 0, 0), bevel=.005):
    x, y, z = (d * .5 for d in size)
    vs = [(-x, -y, -z), (x, -y, -z), (x, y, -z), (-x, y, -z),
          (-x, -y, z), (x, -y, z), (x, y, z), (-x, y, z)]
    fs = [(3, 2, 1, 0), (0, 1, 5, 4), (1, 2, 6, 5),
          (2, 3, 7, 6), (3, 0, 4, 7), (4, 5, 6, 7)]
    o = _mesh(name, vs, fs, coll, root, mat, loc)
    if bevel:
        mod = o.modifiers.new("Rounded molding", "BEVEL")
        mod.width, mod.segments = bevel, 3
        norm = o.modifiers.new("Face normals", "WEIGHTED_NORMAL")
        norm.keep_sharp = True
    return o


def _sphere(name, dims, coll, root, mat, loc=(0, 0, 0), seg=24, rings=12):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=rings, radius=1)
    bm.to_mesh(me)
    bm.free()
    for v in me.vertices:
        for i in range(3):
            v.co[i] *= dims[i]
    for p in me.polygons:
        p.use_smooth = True
    me.materials.append(mat)
    return _object(name, me, coll, root, loc)


def _revolve(name, rows, coll, root, mat, loc=(0, 0, 0), sides=48):
    """Build radial profile rows (height along local Z, radius)."""
    vs = [(r * cos(i * tau / sides), r * sin(i * tau / sides), z)
          for z, r in rows for i in range(sides)]
    fs = [(j * sides + i, j * sides + (i + 1) % sides,
           (j + 1) * sides + (i + 1) % sides, (j + 1) * sides + i)
          for j in range(len(rows) - 1) for i in range(sides)]
    fs += [tuple(reversed(range(sides))),
           tuple((len(rows) - 1) * sides + i for i in range(sides))]
    o = _mesh(name, vs, fs, coll, root, mat, loc)
    for p in o.data.polygons[:-2]:
        p.use_smooth = True
    return o


def _disc(name, radius, depth, coll, root, mat, loc=(0, 0, 0)):
    b = min(radius * .08, depth * .30)
    p = [(-depth / 2, radius - b), (-depth / 2 + b, radius),
         (depth / 2 - b, radius), (depth / 2, radius - b)]
    o = _revolve(name, p, coll, root, mat, loc, 64)
    o.rotation_euler.x = pi / 2
    return o


def _plane(name, w, h, coll, root, mat, loc=(0, 0, 0)):
    o = _mesh(name, [(-w / 2, 0, -h / 2), (w / 2, 0, -h / 2),
                     (w / 2, 0, h / 2), (-w / 2, 0, h / 2)],
              [(0, 1, 2, 3)], coll, root, mat, loc)
    uv = o.data.uv_layers.new(name="UVMap")
    for i, xy in enumerate(((0, 0), (1, 0), (1, 1), (0, 1))):
        uv.data[i].uv = xy
    return o


def _stroke(name, points, radius, coll, root, mat, cyclic=False):
    cr = bpy.data.curves.new(name, type="CURVE")
    cr.dimensions = "3D"
    cr.resolution_u = 8
    cr.bevel_depth = radius
    cr.bevel_resolution = 3
    cr.use_fill_caps = not cyclic
    sp = cr.splines.new("POLY")
    sp.points.add(len(points) - 1)
    for p, co in zip(sp.points, points):
        p.co = (*co, 1)
    sp.use_cyclic_u = cyclic
    cr.materials.append(mat)
    return _object(name, cr, coll, root)


def _ring(name, radius, y, thickness, coll, root, mat, x=0., z=0.):
    pts = [(x + radius * cos(i * tau / 72), y, z + radius * sin(i * tau / 72))
           for i in range(72)]
    return _stroke(name, pts, thickness, coll, root, mat, cyclic=True)


def _font():
    repaired = bpy.data.fonts.get("KW Montserrat Black | clean fill")
    if repaired:
        return repaired
    known = None
    for font in bpy.data.fonts:
        if font.filepath and Path(bpy.path.abspath(font.filepath)).resolve() == _FONT:
            known = font
            break
    if known and known.get("kw_fill_checked"):
        return known
    original = known or bpy.data.fonts.load(str(_FONT), check_existing=True)
    original["kw_fill_checked"] = True
    host = which("python3") or which("python")
    if host:
        try:
            with TemporaryDirectory(prefix="kw-montserrat-") as tmp:
                path = Path(tmp) / _FONT.name
                run((host, "-c", _FONT_FIX, str(_FONT), str(path)), check=True,
                    timeout=12, stdout=DEVNULL, stderr=DEVNULL)
                if path.is_file():
                    repaired = bpy.data.fonts.load(str(path))
                    repaired.name = "KW Montserrat Black | clean fill"
                    repaired.pack()
                    return repaired
        except (OSError, RuntimeError, SubprocessError):
            pass
    return original


def _type(name, body, size, coll, root, mat, loc=(0, 0, 0), depth=.06,
          bevel=.025, face="-Y", space=1.0):
    cu = bpy.data.curves.new(name, "FONT")
    cu.body = str(body)
    cu.font = _font()
    cu.align_x, cu.align_y = "CENTER", "CENTER"
    cu.space_line = space
    cu.size = size
    cu.extrude, cu.bevel_depth = size * depth, size * bevel
    cu.bevel_resolution, cu.resolution_u = 4, 12
    cu.materials.append(mat)
    o = _object(name, cu, coll, root, loc)
    rot = {"-Y": (pi / 2, 0, 0), "+Y": (pi / 2, 0, pi),
           "-X": (pi / 2, 0, -pi / 2), "+X": (pi / 2, 0, pi / 2),
           "+Z": (0, 0, 0), "-Z": (pi, 0, 0)}
    if face not in rot:
        raise ValueError(f"Unknown text face {face!r}")
    o.rotation_euler = rot[face]
    return o


class Backdrop:
    """Centered XZ card; place its origin behind the subject, at greater Y."""

    def __init__(self, origin, coll, w=6, h=8, grid=True):
        self.root = _root("KW Blueprint", coll, origin)
        m, t, out = _tree("KW Blueprint | luminous ink")
        self.material = m
        uv = t.nodes.new("ShaderNodeTexCoord").outputs["UV"]
        v = _vmath(t, "SUBTRACT", uv, (.50, .51, 0))
        dist = _vmath(t, "LENGTH", _vmath(t, "MULTIPLY", v, (1.42, 1.62, 0)))
        col = _ramp(t, dist, ((0, _rgba(_hex("4FC3F7"))),
                             (.91, _rgba(_hex("1565C0")))))
        if grid:
            sep = t.nodes.new("ShaderNodeSeparateXYZ")
            _socket(t, sep.inputs[0], uv)
            lines = []
            for axis, span in zip("XY", (w, h)):
                def line(period, width):
                    repeat = _math(t, "ADD", _math(t, "MULTIPLY",
                                   _math(t, "SUBTRACT", sep.outputs[axis], .5), span / period), .5)
                    centered = _math(t, "SUBTRACT", _math(t, "FRACT", repeat), .5)
                    return _math(t, "LESS_THAN", _math(t, "ABSOLUTE", centered), width)
                fine = _math(t, "MULTIPLY", line(.26, .006), .069)
                bold = _math(t, "MULTIPLY", line(1.04, .0021), .103)
                lines.append(_math(t, "MAXIMUM", fine, bold))
            amount = _math(t, "MAXIMUM", *lines)
            col = _mix(t, amount, col, (.86, .96, 1, 1))
        self._tint = t.nodes.new("ShaderNodeRGB")
        self._tint.label = "User tint | linear multiply"
        col = _mix(t, 1, col, self._tint.outputs[0], "MULTIPLY")
        _emit(t, out, col)
        self.object = _plane("KW Blueprint | XZ back wall", w, h, coll, self.root, m)
        # Retain camera visibility without using the backdrop as a blue fill light.
        for ray in ("diffuse", "glossy", "transmission", "shadow"):
            setattr(self.object, "visible_" + ray, False)
        self.set()

    def set(self, tint=None):
        self._tint.outputs[0].default_value = _rgba((1, 1, 1) if tint is None else tint)
        return self


class Label3D:
    """Centered Montserrat with rounded, lacquered letter edges."""

    def __init__(self, text, origin, coll, size=.1, color=(1, .1, .1), face="-Y"):
        self.root = _root(f"KW Label | {text}", coll, origin)
        self.material = _paint("KW label | candy lacquer", color, .27, .11, .40, .055)
        self.object = _type("KW | dimensional letters", text, size, coll, self.root,
                            self.material, depth=.105, bevel=.012, face=face)

    @staticmethod
    def pop(u):
        u = _unit(u)
        x = u - 1
        return max(0, 1 + 2.78 * x ** 3 + 1.78 * x ** 2)

    def set(self, scale=1., text=None):
        scale = max(0.0, float(scale))
        if text is not None:
            text = str(text)
            if text != self.object.data.body:
                self.object.data.body = text
        self.object.scale = (max(.00001, scale),) * 3
        _vis(self.object, scale > .00001)
        return self


class Gauge:
    """Radius controls the whole dial; origin is its visual center."""

    @staticmethod
    def _angle(value):
        return (222 - 230 * value) * pi / 180

    def __init__(self, origin, coll, radius=.12):
        self.root = _root("KW Pressure Gauge", coll, origin)
        self.radius = float(radius)
        r = self.radius
        body = _paint("KW gauge | midnight enamel", _hex("152744"), .29, .18)
        steel = _paint("KW gauge | polished steel", _hex("CFDFEE"), .22, .67, .37)
        face = _paint("KW gauge | ivory dial", _hex("F4FAFF"), .38, 0, .10, .24)
        ink, _ = _ematerial("KW gauge | ink", _hex("142333"), .83)
        red = _paint("KW gauge | hot red needle", _hex("D72035"), .21, .12, .40, .14)
        red_ink, _ = _ematerial("KW gauge | red ink", _hex("AD0E24"), 1)
        dark_green, _ = _ematerial("KW gauge | low-pressure green ink", _hex("164F2A"), 1)
        _disc("KW Gauge | rubber body", r, .37 * r, coll, self.root, body, (0, .089 * r, 0))
        _disc("KW Gauge | enamel face", r * .889, .07 * r, coll, self.root, face, (0, -.080 * r, 0))
        _ring("KW Gauge | chrome rim", .935 * r, -.105 * r, .065 * r, coll, self.root, steel)
        _ring("KW Gauge | inside shadow bead", .874 * r, -.097 * r, .011 * r, coll, self.root, body)
        for index, (a, b, shade) in enumerate(((0, .32, "25BD62"), (.335, .66, "FFCE30"),
                                               (.675, 1, "F32648"))):
            mat = _paint("KW gauge | colored band " + shade, _hex(shade),
                         .29, 0, .34, .40)
            angles = [self._angle(a + (b - a) * i / 36) for i in range(37)]
            pts = [(.759 * r * cos(p), -.124 * r, .759 * r * sin(p)) for p in angles]
            _stroke(f"KW Gauge | range {index + 1}", pts, r * .050, coll, self.root, mat)
        for i in range(21):
            p = self._angle(i / 20)
            long = i in (0, 1, 5, 10, 15, 20)
            a = .575 if long else .638
            pts = [(r * d * cos(p), -.132 * r, r * d * sin(p)) for d in (a, .686)]
            _stroke(f"KW Gauge | tick {i:02d}", pts, r * (.013 if long else .0075),
                    coll, self.root, ink)
        # A low-scale leader keeps the text legible without colliding with ticks.
        p = self._angle(.05)
        _stroke("KW Gauge | normal-sneeze index",
                [(r * .565 * cos(p), -.133 * r, r * .565 * sin(p)),
                 (-.345 * r, -.133 * r, -.43 * r)],
                .010 * r, coll, self.root, dark_green)
        _type("KW Gauge | NORMAL SNEEZE", "NORMAL\nSNEEZE", .189 * r, coll, self.root,
              dark_green, (-.054 * r, -.144 * r, -.48 * r), depth=0, bevel=0, space=.83)
        p = self._angle(1)
        _stroke("KW Gauge | high-pressure index",
                [(r * .570 * cos(p), -.133 * r, r * .570 * sin(p)),
                 (.606 * r, -.133 * r, -.169 * r)],
                .0077 * r, coll, self.root, red_ink)
        _type("KW Gauge | full-scale label", "20x", .28 * r, coll, self.root, red_ink,
              (.542 * r, -.143 * r, -.262 * r), depth=0, bevel=0)
        _type("KW Gauge | title", "PRESSURE", .200 * r, coll, self.root, ink,
              (0, -.144 * r, .327 * r), depth=0, bevel=0)
        self._needle = _root("KW Gauge | needle pivot", coll, (0, -.155 * r, 0), self.root)
        poly = [(-.244 * r, 0, -.034 * r), (.43 * r, 0, -.023 * r),
                (.66 * r, 0, 0), (.43 * r, 0, .023 * r), (-.244 * r, 0, .034 * r)]
        verts = [(x, y + dy, z) for dy in (-.014 * r, .014 * r) for x, y, z in poly]
        faces = [tuple(range(5)), tuple(reversed(range(5, 10)))]
        faces.extend((i, 5 + i, 5 + (i + 1) % 5, (i + 1) % 5) for i in range(5))
        needle = _mesh("KW Gauge | solid needle", verts, faces, coll, self._needle, red)
        mod = needle.modifiers.new("Needle highlights", "BEVEL")
        mod.width, mod.segments = .009 * r, 3
        _disc("KW Gauge | floating chrome cap", .11 * r, .055 * r, coll, self.root,
              steel, (0, -.174 * r, 0))
        glass = _glass("KW gauge | anti-glare glass", .041, _hex("E4F8FF"), 1.11, .17)
        cover = _disc("KW Gauge | clear front lens", .884 * r, .027 * r, coll, self.root,
                      glass, (0, -.205 * r, 0))
        cover.visible_shadow = False
        self.set(0)

    def set(self, value, shake=0.0):
        """Set full-scale fraction and optional 0..1 shake intensity."""
        frame = bpy.context.scene.frame_current_final
        wiggle = sin(frame * 1.83) * .024 + sin(frame * .97 + 1.2) * .012
        v = _unit(_unit(value) + _unit(shake) * wiggle)
        self._needle.rotation_euler.y = -self._angle(v)
        return self


def _skin_slab(name, coll, parent, top_mat, cut_mat, size, bottom, top, n=27):
    """A continuous ring of cut faces, with matched deformation at interfaces."""
    vs, faces = [], []
    for z in (bottom, top):
        for j in range(n):
            y = j / (n - 1) - .5
            for i in range(n):
                x = i / (n - 1) - .5
                # Tiny XY rounding at the exposed corners, no over-rounding the cut.
                xx, yy = max(0, abs(x) - .458), max(0, abs(y) - .458)
                q = max(.042, sqrt(xx * xx + yy * yy)) / .042
                px = x if not xx else (1 if x > 0 else -1) * (.458 + xx / q)
                py = y if not yy else (1 if y > 0 else -1) * (.458 + yy / q)
                wave = .009 * sin(12 * x + 3 * z) * cos(11 * y - 5 * z)
                vs.append((px * size, py * size, (z + wave) * size))
    cell = n * n
    for j in range(n - 1):
        for i in range(n - 1):
            a = j * n + i
            f = [a, a + 1, a + n + 1, a + n]
            faces.append(tuple(reversed(f)))
            faces.append(tuple(v + cell for v in f))
    border = list(range(n)) + list(range(2 * n - 1, cell, n))
    border += list(range(cell - 2, cell - n - 1, -1))
    border += list(range(cell - 2 * n, 0, -n))
    for a, b in zip(border, border[1:] + border[:1]):
        faces.append((a, b, b + cell, a + cell))
    o = _mesh(name, vs, faces, coll, parent, cut_mat)
    o.data.materials.append(top_mat)
    for i, p in enumerate(o.data.polygons):
        if i < 2 * (n - 1) ** 2:
            p.material_index = i % 2
            p.use_smooth = True
        else:
            p.use_smooth = False
    basis = o.shape_key_add(name="Basis", from_mix=False)
    bulge = o.shape_key_add(name="Trapped air raises upper layers", from_mix=False)
    press = o.shape_key_add(name="Finger contact dimple", from_mix=False)
    for i, v in enumerate(basis.data):
        x, y, z = v.co / size
        b = _unit((z + .26) / .76)
        p = b ** 1.65
        b *= exp(-2.3 * (x * x + (y + .10) ** 2))
        p *= exp(-((x - .054) ** 2 + (y + .255) ** 2) / .035)
        bulge.data[i].co.z += size * .172 * b
        press.data[i].co.z -= size * .248 * p
    return bulge, press


class SkinBlock:
    """Cut skin volume centered at origin. Best seen from -Y, slightly above."""

    def __init__(self, origin, coll, size=.5):
        self.root = _root("KW Skin Block", coll, origin)
        self.size = s = float(size)
        code = _hex
        skin = _paint("KW anatomy | textured epidermis", code("E09170"), .40, 0, .26,
                      0, .065, (code("BF6247"), code("F5B794"), (1, 1, .35), 115, .28, .0014 * s))
        skin_edge = _paint("KW anatomy | epidermis cut face", code("D57C60"), .25, 0, .48,
                           0, .02, (code("A54843"), code("EDAA89"), (1, 1, 2), 23, .33, .004 * s))
        dermis = _paint("KW anatomy | moist pink dermis", code("CB586E"), .25, 0, .48,
                        0, .049, (code("A62A4E"), code("F69B9C"), (1, 1, 1), 36, .32, .004 * s))
        fat = _paint("KW anatomy | amber hypodermis", code("F2A52C"), .25, 0, .45,
                     0, .053, (code("C26D13"), code("FFD457"), (1, 1, 1), 16, .35, .006 * s))
        muscle = _paint("KW anatomy | wet longitudinal muscle", code("A5253C"), .24, 0, .49,
                        0, .040, (code("60152B"), code("DD405B"), (.32, 4, 2.6), 23, .38, .008 * s))
        self._morphs = []
        for nm, mat, edge, z0, z1 in (
            ("muscle", muscle, muscle, -.495, -.273), ("fat", fat, fat, -.273, -.026),
            ("dermis", dermis, dermis, -.026, .387), ("epidermis", skin, skin_edge, .387, .50),
        ):
            self._morphs.append(_skin_slab("KW Anatomy | " + nm, coll, self.root, mat, edge, s, z0, z1))
        rng = Random(18)
        lobe_mats = [
            _paint("KW anatomy | golden lipid nodule", code("FFBA37"), .26, 0, .52, 0, .029),
            _paint("KW anatomy | honey lipid nodule", code("E9971B"), .27, 0, .49, 0, .04),
            _paint("KW anatomy | cream lipid nodule", code("FFD256"), .29, 0, .44, 0, .04),
        ]
        self._lobes = []
        for side in ("front", "right"):
            for row in range(3):
                for i in range(11):
                    x = -.44 + .087 * i + rng.uniform(-.014, .014)
                    z = -.24 + .077 * row + rng.uniform(-.018, .018)
                    depth = -.477 + rng.uniform(-.008, .004)
                    bx, d, bz = rng.uniform(.037, .062), rng.uniform(.026, .043), rng.uniform(.038, .055)
                    loc = (x * s, depth * s, z * s) if side == "front" else (-depth * s, x * s, z * s)
                    dim = (bx * s, d * s, bz * s) if side == "front" else (d * s, bx * s, bz * s)
                    o = _sphere("KW Anatomy | fat lobule", dim, coll, self.root,
                                rng.choice(lobe_mats), loc, 14, 8)
                    self._lobes.append((o, Vector(loc)))
        air = _glass("KW anatomy | optically clear air pockets", .70, code("E9FCFF"), 1.29, .082)
        rim = _paint("KW anatomy | bubble film glints", code("DCFCFF"), .16, .22, .48, .15)
        self._bubbles = []
        for i in range(23):
            x = rng.uniform(-.37, .37)
            z = rng.uniform(-.124, .321)
            y = rng.uniform(-.532, -.501)
            r = rng.uniform(.025, .064) * s * (1.12 if i < 5 else .91)
            loc = Vector((x * s, y * s, z * s))
            dims = (r * rng.uniform(.90, 1.16), r * .68, r * rng.uniform(.84, 1.17))
            pivot = _root("KW Anatomy | air-pocket center", coll, loc, self.root)
            o = _sphere("KW Anatomy | transparent pocket", dims, coll, pivot, air, seg=20, rings=11)
            o.visible_shadow = False
            # Arc of front-facing specular film keeps clear pockets readable on mobile.
            arc = [(dims[0] * cos(a) * .84, -dims[1] * .62, dims[2] * sin(a) * .84)
                   for a in [(.48 + j / 13 * 1.55) * pi for j in range(14)]]
            hl = _stroke("KW Anatomy | air-pocket rim", arc, r * .049, coll, pivot, rim)
            self._bubbles.append((pivot, o, hl, loc, i / 26., rng.uniform(.65, 1.25)))
        glove = _paint("KW anatomy | blue nitrile", code("2789E8"), .36, 0, .29, 0, .023,
                       (code("1259B5"), code("49A9EE"), (1, 1, 1), 51, .19, .004 * s))
        finger_profile = [(z * s, r * s) for z, r in (
            (0, .018), (.015, .057), (.042, .089), (.081, .104), (.119, .111),
            (.200, .111), (.311, .104), (.400, .109), (.479, .116),
            (.538, .105), (.570, .068), (.581, .015))]
        self._finger = _revolve("KW Anatomy | nitrile fingertip", finger_profile,
                                coll, self.root, glove, sides=40)
        self._finger.rotation_euler.y = .24
        self._finger.rotation_euler.x = -.12
        self.set(0, 0)

    def set(self, bubbles, press):
        bubbles, press = _unit(bubbles), _unit(press)
        s = self.size
        for up, down in self._morphs:
            up.value, down.value = bubbles, press
        for lobe, loc in self._lobes:
            z = loc.z / s
            w = _unit((z + .26) / .76)
            bulge = exp(-2.3 * ((loc.x / s) ** 2 + (loc.y / s + .10) ** 2))
            lobe.location.z = loc.z + s * .172 * w * bulge * bubbles
        for pivot, air, glint, loc, threshold, strength in self._bubbles:
            grow = _smooth((bubbles - threshold) / .21)
            _vis(air, grow > .007)
            _vis(glint, grow > .007)
            x, y, z = loc / s
            spread = 1 if x >= .054 else -1
            shove = .105 * exp(-((x - .054) * 3) ** 2) * strength * press
            pivot.location = (
                max(-.444, min(.444, x + spread * shove)) * s,
                loc.y,
                (z + .081 * bubbles - .063 * press * strength * (1 - abs(x))) * s,
            )
            f = max(.001, grow)
            pivot.scale = (f * (1 + .22 * press), f, f * (1 - .24 * press))
        approach = _smooth(min(1, press * 1.85))
        z = .50 + .154 * bubbles - .232 * press + .215 * (1 - approach)
        self._finger.location = (.054 * s, -.255 * s, z * s)
        return self


class Calendar:
    """A 45 cm wide wall calendar, facing -Y with a hinged top binding."""

    def __init__(self, origin, coll):
        self.root = _root("KW Five-week Calendar", coll, origin)
        backing = _paint("KW calendar | deep blue card", _hex("143B62"), .48, 0, .18)
        paper = _paint("KW calendar | warm ivory paper", _hex("FFF7E4"), .52, 0, .17, .13)
        orange = _paint("KW calendar | vermilion masthead", _hex("D93530"), .35, 0, .31, .13)
        binding = _paint("KW calendar | steel coil", _hex("BBCFDA"), .26, .64, .35)
        white, _ = _ematerial("KW calendar | knocked-out lettering", _hex("FFFAEF"), 1.05)
        dark, _ = _ematerial("KW calendar | navy grid text", _hex("254058"), .87)
        gray, _ = _ematerial("KW calendar | fine grid ink", _hex("A6ACB2"), .65)
        soft_red, _ = _ematerial("KW calendar | red printed dates", _hex("B71D32"), .85)
        w, h = .448, .439
        hinge_h = h / 2 - .023
        _cube("KW Calendar | stiff backing", (.454, .012, .451),
              coll, self.root, backing, (0, .009, -.002), bevel=.008)
        _cube("KW Calendar | metal binding rail", (.418, .011, .012),
              coll, self.root, backing, (0, -.016, hinge_h + .005), bevel=.004)
        for i in range(9):
            x = -.170 + i * .0425
            pts = [(x, -.009 + .017 * cos(i * tau / 28.), hinge_h + .008 + .020 * sin(i * tau / 28.))
                   for i in range(28)]
            _stroke("KW Calendar | coil", pts, .0023, coll, self.root, binding, cyclic=True)
        self._pages = []
        for week in range(1, 6):
            hinge = _root(f"KW Calendar | week {week} hinge", coll,
                          (0, -.013, hinge_h), self.root)
            before = set(coll.objects)
            _cube("KW Calendar | sheet", (w, .0037, h), coll, hinge, paper,
                  (0, 0, -hinge_h), bevel=.0015)
            _cube("KW Calendar | red masthead", (.441, .0041, .107), coll, hinge,
                  orange, (0, -.0022, -.080), bevel=.002)
            _type(f"KW Calendar | WEEK {week}", f"WEEK {week}", .077, coll, hinge,
                  white, (0, -.0045, -.081), depth=0, bevel=0)
            x0, x1 = -.186, .186
            z_hi, z_lo = -.200, -.382
            step = (x1 - x0) / 7
            for i, title in enumerate("MTWTFSS"):
                _type("KW Calendar | weekday", title, .027, coll, hinge,
                      soft_red if i >= 5 else dark, (x0 + (i + .5) * step, -.0031, -.169),
                      depth=0, bevel=0)
            for i in range(8):
                x = x0 + step * i
                _stroke("KW Calendar | grid vertical", [(x, -.0025, z_lo), (x, -.0025, z_hi)],
                        .00052, coll, hinge, gray)
            for i in range(5):
                z = z_hi + (z_lo - z_hi) * (i / 4)
                _stroke("KW Calendar | grid horizontal", [(x0, -.0025, z), (x1, -.0025, z)],
                        .00052, coll, hinge, gray)
            for day in range(28):
                col, row = day % 7, day // 7
                dmat = soft_red if col >= 5 else dark
                x, z = x0 + (col + .5) * step, z_hi + (z_lo - z_hi) * ((row + .5) / 4)
                _type("KW Calendar | date", str(day + 1), .020, coll, hinge,
                      dmat, (x, -.0032, z), depth=0, bevel=0)
            self._pages.append((hinge, tuple(o for o in coll.objects if o not in before)))
        self._hinge_height = hinge_h
        self.set(0)

    def set(self, u):
        """The first four turns are staged; at 1 the WEEK 5 sheet remains."""
        progress = _unit(u) * 4
        index = min(4, int(progress))
        phase = progress - index
        f = _smooth((phase - .57) / .43)
        flipping = f > .001 and index < 4
        for i, (hinge, parts) in enumerate(self._pages):
            v = i == index or (flipping and i == index + 1)
            for o in parts:
                _vis(o, v)
            hinge.location = (0, -.013 + (.006 if i > index else 0), self._hinge_height)
            hinge.rotation_euler.x = 0
            if i == index and flipping:
                hinge.location.y -= .043 * f ** 2
                hinge.location.z -= .26 * _smooth((f - .64) / .36)
                hinge.rotation_euler.x = -2.72 * f
        return self


def _ellipse(t, uv, center, axes):
    p = _vmath(t, "SUBTRACT", uv, (*center, 0))
    return _vmath(t, "MULTIPLY", p, (1 / axes[0], 1 / axes[1], 0))


def _solid(t, signal, edge=.02):
    # Signal of 1 is the shape boundary, soften the thin antialiasing band.
    ramp = _ramp(t, signal, ((1 - edge, (1, 1, 1, 1)), (1, (0, 0, 0, 1))))
    return ramp


def _ellipse_alpha(t, uv, cx, cz, rx, rz, feather=.065):
    d = _vmath(t, "LENGTH", _ellipse(t, uv, (cx, cz), (rx, rz)))
    return _math(t, "MULTIPLY", _solid(t, d, feather), 1)


class ScanMonitor:
    """Centered screen with a small stand below; scan diagram is stylized.

    heal=0 exposes a break and air pockets; heal=1 shows an intact airway.
    Marker intensity follows scene frame number, without animation keyframes.
    """

    _AC = (.425, .620)    # center of airway in display UV
    _AR = (.080, .142)    # airway outer radii in display UV
    _GAP = .43           # gap angle from +X, radians in ellipse coordinates

    def __init__(self, origin, coll, width=.5):
        self.root = _root("KW CT Monitor", coll, origin)
        self.width = w = float(width)
        self.height = h = .68 * w
        sw, sh = self._screen_dims = (.883 * w, .835 * h)
        shell = _paint("KW CT | pale monitor molding", _hex("DAE7EB"), .26, .06, .34)
        border = _paint("KW CT | midnight inner bezel", _hex("1B3048"), .28, .15, .35)
        metal = _paint("KW CT | powdered aluminum stand", _hex("607487"), .39, .45, .18)
        rubber = _paint("KW CT | rubber body parts", _hex("344355"), .36, .08)
        indicator, self._indicator = _ematerial("KW CT | power indicator", _hex("5AFFA6"), 1.05)
        _cube("KW CT | body", (w, .16 * w, h), coll, self.root, shell, (0, .016 * w, 0), .038 * w)
        _cube("KW CT | deep inner bezel", (.926 * w, .040 * w, .888 * h), coll, self.root,
              border, (0, -.069 * w, .005 * h), .021 * w)
        _cube("KW CT | articulated stem", (.086 * w, .11 * w, .38 * w), coll, self.root,
              metal, (0, .10 * w, -.445 * w), .018 * w)
        _cube("KW CT | linkage", (.15 * w, .16 * w, .108 * w), coll, self.root,
              rubber, (0, .11 * w, -.245 * w), .018 * w)
        _cube("KW CT | low stand base", (.53 * w, .30 * w, .060 * w), coll, self.root,
              shell, (0, .04 * w, -.651 * w), .027 * w)
        _cube("KW CT | base inset", (.37 * w, .21 * w, .025 * w), coll, self.root,
              rubber, (0, .046 * w, -.674 * w), .008 * w)
        screen_y = -.091 * w
        self._sz = .005 * h
        m, t, out = _tree("KW CT | diagnostic scan, procedural")
        uv = t.nodes.new("ShaderNodeTexCoord").outputs["UV"]
        self._heal = t.nodes.new("ShaderNodeValue")
        self._heal.label = "Tear closure"
        heal = self._heal.outputs[0]
        self._power = t.nodes.new("ShaderNodeValue")
        self._power.label = "Backlight power"
        power = self._power.outputs[0]
        grain = t.nodes.new("ShaderNodeTexNoise")
        grain.inputs["Scale"].default_value = 88
        grain.inputs["Detail"].default_value = 2
        _socket(t, grain.inputs["Vector"], _vmath(t, "MULTIPLY", uv, (1.3, 1, 0)))
        foot = t.nodes.new("ShaderNodeSeparateXYZ")
        _socket(t, foot.inputs[0], uv)
        u, v = foot.outputs["X"], foot.outputs["Y"]
        rows = _math(t, "GREATER_THAN", _math(t, "FRACT", _math(t, "MULTIPLY", v, 98)), .83)
        noise = grain.outputs["Fac"]
        background = _mix(t, rows, (.012, .019, .030, 1), (.017, .028, .046, 1))
        panel = _math(t, "GREATER_THAN", u, .735)
        color = _mix(t, panel, background, (.022, .043, .068, 1))
        texture = _ramp(t, noise, ((.23, (.103, .119, .127, 1)), (.85, (.42, .444, .46, 1))))
        muscle = _ramp(t, noise, ((.24, (.089, .100, .112, 1)), (.78, (.26, .281, .30, 1))))
        grey = _ramp(t, noise, ((.18, (.216, .231, .243, 1)), (.83, (.66, .682, .691, 1))))
        bone = _ramp(t, noise, ((.15, (.37, .396, .426, 1)), (.84, (.87, .896, .922, 1))))
        def shape(c, cx, cz, rx, rz, material, feather=.065):
            return _mix(t, _ellipse_alpha(t, uv, cx, cz, rx, rz, feather), c, material)
        color = shape(color, .415, .488, .282, .342, grey, .026)
        color = shape(color, .415, .490, .266, .323, texture, .067)
        color = shape(color, .250, .465, .098, .211, muscle, .19)
        color = shape(color, .573, .462, .102, .214, muscle, .20)
        color = shape(color, .278, .604, .060, .058, texture, .22)
        color = shape(color, .549, .597, .049, .092, texture, .25)
        color = shape(color, .416, .330, .109, .159, grey, .27)
        # Irregular bright dorsal bone assembled from connected round forms.
        color = shape(color, .415, .331, .068, .079, bone, .15)
        color = shape(color, .415, .238, .024, .092, bone, .17)
        color = shape(color, .365, .286, .036, .040, bone, .20)
        color = shape(color, .461, .282, .037, .045, bone, .20)
        color = shape(color, .416, .303, .032, .045, muscle, .19)
        color = shape(color, .267, .338, .026, .049, grey, .20)
        color = shape(color, .563, .338, .029, .054, grey, .20)
        air = (.006, .010, .016, 1)
        for cx, cz, rx, rz in [(.636, .669, .024, .049), (.591, .732, .019, .032),
                               (.593, .598, .035, .030), (.234, .653, .017, .030),
                               (.184, .572, .020, .048), (.650, .545, .014, .034)]:
            pocket = _ellipse_alpha(t, uv, cx, cz, rx, rz, .15)
            opacity = _math(t, "POWER", _math(t, "SUBTRACT", 1, heal), .72)
            color = _mix(t, _math(t, "MULTIPLY", pocket, opacity), color, air)
        vec = _ellipse(t, uv, self._AC, self._AR)
        length = _vmath(t, "LENGTH", vec)
        sep = t.nodes.new("ShaderNodeSeparateXYZ")
        _socket(t, sep.inputs[0], vec)
        a = _math(t, "ARCTAN2", sep.outputs["Y"], sep.outputs["X"])
        delta = _math(t, "ABSOLUTE", _math(t, "SUBTRACT", a, self._GAP))
        gap_width = _math(t, "MULTIPLY", _math(t, "SUBTRACT", 1, heal), .52)
        gap = _math(t, "LESS_THAN", delta, gap_width)
        # Give the tear an actual channel through the bright airway rim.
        outer = _math(t, "MULTIPLY", _solid(t, length, .08), 1)
        ring = _math(t, "MULTIPLY", outer, _math(t, "SUBTRACT", 1, gap))
        color = _mix(t, ring, color, grey)
        dark_disk = _math(t, "MULTIPLY", _solid(t, _math(t, "MULTIPLY", length, 1.29), .069), 1)
        color = _mix(t, dark_disk, color, air)
        corridor_limit = _math(t, "LESS_THAN", length,
                               _math(t, "ADD", 1, _math(t, "MULTIPLY", gap_width, .55)))
        color = _mix(t, _math(t, "MULTIPLY", gap, corridor_limit), color, air)
        color = _mix(t, .035, color, (.135, .22, .31, 1))
        _emit(t, out, color, power)
        self.screen = _plane("KW CT | emissive medical image", sw, sh, coll, self.root,
                             m, (0, screen_y, self._sz))
        for ray in ("diffuse", "glossy", "transmission", "shadow"):
            setattr(self.screen, "visible_" + ray, False)
        ui, self._ui = _ematerial("KW CT | cyan UI labels", _hex("9EE7EA"), .85)
        subui, self._subui = _ematerial("KW CT | dim UI secondary labels", _hex("619CA9"), .7)
        markmat, self._mark = _ematerial("KW CT | scan focus ring", _hex("FF3851"), 1.2)
        top_y = screen_y - .0025 * w
        self._marker_xy = ((self._AC[0] + self._AR[0] * cos(self._GAP) - .5) * sw,
                           self._sz + (self._AC[1] + self._AR[1] * sin(self._GAP) - .5) * sh)
        self._marker = _ring("KW CT | blinking tear marker", .052 * w,
                             top_y, .003 * w, coll, self.root, markmat, *self._marker_xy)
        def field(title, txt, uvx, uvz, size, mat):
            return _type("KW CT | " + title, txt, size * w, coll, self.root,
                         mat, ((uvx - .5) * sw, top_y, self._sz + (uvz - .5) * sh), depth=0, bevel=0)
        self._ui_objs = [
            field("scan title", "CT / NECK", .247, .925, .042, ui),
            field("axial label", "AXIAL", .866, .800, .031, ui),
            field("view orientation", "A", .413, .858, .024, subui),
            field("view orientation rear", "P", .413, .110, .024, subui),
            field("slice number", "SLICE  04", .857, .248, .025, subui),
            field("diagnostic status", "REVIEW", .855, .123, .028, ui),
        ]
        self._status = self._ui_objs[-1]
        for ax, bx, yy in ((.764, .943, .730), (.765, .902, .685), (.765, .925, .637),
                           (.765, .868, .592), (.765, .949, .494), (.765, .889, .450)):
            pts = [((x - .5) * sw, top_y, self._sz + (yy - .5) * sh) for x in (ax, bx)]
            self._ui_objs.append(_stroke("KW CT | UI data strip", pts, .00125 * w,
                                         coll, self.root, subui))
        _sphere("KW CT | physical power LED", (.008 * w,) * 3, coll, self.root,
                indicator, (.416 * w, -.083 * w, -.458 * h), 14, 8)
        self.set(0)

    def set(self, heal, on=1.0):
        heal, on = _unit(heal), _unit(on)
        self._heal.outputs[0].default_value = heal
        self._power.outputs[0].default_value = .024 + .976 * on
        self._ui.inputs["Strength"].default_value = .91 * on
        self._subui.inputs["Strength"].default_value = .65 * on
        self._indicator.inputs["Strength"].default_value = 1.3 * on
        elapsed = bpy.context.scene.frame_current_final
        healed = _smooth((heal - .76) / .23)
        flash = .54 + .46 * (cos(elapsed * .47) if elapsed > 1 else 1)
        r, g, b = _hex("FF4054")
        R, G, B = _hex("41FFA0")
        self._mark.inputs["Color"].default_value = (
            r + (R - r) * healed, g + (G - g) * healed, b + (B - b) * healed, 1)
        self._mark.inputs["Strength"].default_value = on * ((1 - healed) * flash * 1.8 + healed * 1.4)
        status = "HEALED" if heal >= .96 else "REVIEW"
        if self._status.data.body != status:
            self._status.data.body = status
        return self


class Bracket:
    """Red ruler bracket, with world-space endpoints and a centered 3D callout."""

    def __init__(self, p0, p1, text, coll):
        p0, p1 = Vector(p0), Vector(p1)
        self.root = _root("KW Measuring Bracket", coll, p0.lerp(p1, .5))
        run = p1 - p0
        self.length = length = run.length
        if length < 1e-8:
            raise ValueError("Bracket endpoints must differ")
        self._direction = d = run.normalized()
        across = _FRONT.cross(d)
        if across.length < 1e-6:
            across = _Z.copy()
        across.normalize()
        if across.z < 0:
            across.negate()
        r = max(.00035, min(.012, .021 * length))
        cap = max(.0014, min(.083, .24 * length))
        color = _hex("FA2940")
        mat = _paint("KW measurement | glossy red enamel", color, .25, .11, .32, .13)
        self._bar = _stroke("KW Bracket | ruler span", [(-length / 2, 0, 0), (length / 2, 0, 0)],
                            r, coll, self.root, mat)
        self._bar.rotation_mode = "QUATERNION"
        self._bar.rotation_quaternion = Vector((1, 0, 0)).rotation_difference(d)
        self._caps = []
        for j in (-1, 1):
            o = _stroke("KW Bracket | endpoint",
                        [tuple(-across * cap / 2), tuple(across * cap / 2)],
                        r * 1.05, coll, self.root, mat)
            self._caps.append((j, o))
        font = max(.008, min(.17, .333 * length))
        center = across * (cap * .48 + font * (.60 if abs(across.z) > .65 else .98))
        center += _FRONT * max(.001, .042 * length)
        self.label = Label3D(text, center, coll, size=font, color=color)
        self.label.root.parent = self.root
        self.set()

    def set(self, grow=1.):
        f = _unit(grow)
        _vis(self._bar, f > .001)
        self._bar.scale.x = max(.0001, f)
        for s, o in self._caps:
            _vis(o, f > .015)
            o.location = self._direction * (s * self.length * f / 2)
            o.scale = (max(.001, _smooth(f / .28)),) * 3
        self.label.set(scale=Label3D.pop((f - .24) / .76))
        return self


class Crackle:
    """Short glossy yellow-white directional ticks in the front XZ plane."""

    def __init__(self, origin, coll):
        self.root = _root("KW Crackle Accent", coll, origin)
        white = _paint("KW crackle | hot center", _hex("FFFDE8"), .23, .01, .34, .9)
        sun = _paint("KW crackle | yellow enamel", _hex("FFD246"), .25, .06, .38, .36)
        marks = [
            (10, .042, .042, .001, 0),
            (45, .032, .066, .0025, -.13),
            (82, .042, .032, .002, .10),
            (130, .038, .053, .003, -.16),
            (167, .049, .033, .002, .08),
            (204, .038, .049, .0025, -.12),
            (245, .048, .027, .0012, .20),
            (288, .037, .055, .0026, -.14),
            (336, .043, .037, .0018, .12),
        ]
        self._rays = []
        for i, (degrees, r, length, jelly, kink) in enumerate(marks):
            theta = degrees * pi / 180
            orientation = Vector((cos(theta), 0, sin(theta)))
            normal = _FRONT.cross(orientation)
            pivot = _root("KW Crackle | ray pivot", coll, orientation * r, self.root)
            pts = [Vector((0, 0, 0)), orientation * (.57 * length) + normal * (kink * length),
                   orientation * length + normal * (-kink * .15 * length)]
            bg = _stroke("KW Crackle | warm outside", pts, .0025 + .55 * jelly,
                         coll, pivot, sun)
            fg = _stroke("KW Crackle | hot highlight",
                         [v + Vector((0, -.0031, 0)) for v in pts],
                         .0011 + .49 * jelly, coll, pivot, white)
            for o in (bg, fg):
                for pt, radius in zip(o.data.splines[0].points, (.67, 1, .38)):
                    pt.radius = radius
            self._rays.append((pivot, bg, fg, orientation, r, .026 * ((i * 3) % 7)))
        self.set(0)

    def set(self, amp):
        amp = _unit(amp)
        for p, bg, fg, d, r, offset in self._rays:
            f = _smooth((amp - offset) / .69)
            for m in (bg, fg):
                _vis(m, f > .008)
            p.scale = (max(.001, f),) * 3
            p.location = d * (r * (.74 + .26 * f))
        return self


def _catmull(points):
    """Sample a smooth 3D centerline; arbitrary f uses distance, not segment index."""
    raw = [Vector(x) for x in points]
    vertices = [raw[0]] if raw else []
    for x in raw[1:]:
        if (x - vertices[-1]).length > 1e-8:
            vertices.append(x)
    if len(vertices) < 2:
        raise ValueError("Arrow3D needs at least two different points")
    if len(vertices) == 2:
        return vertices
    dense = [vertices[0]]
    for i in range(len(vertices) - 1):
        p1, p2 = vertices[i:i + 2]
        p0 = vertices[i - 1] if i else 2 * p1 - p2
        p3 = vertices[i + 2] if i < len(vertices) - 2 else 2 * p2 - p1
        # Length-weighted tangents avoid hooks where source point spacing changes abruptly.
        lens = [(p1 - p0).length, (p2 - p1).length, (p3 - p2).length]
        m1 = (p2 - p0) * lens[1] / max(1e-8, lens[0] + lens[1])
        m2 = (p3 - p1) * lens[1] / max(1e-8, lens[1] + lens[2])
        for j in range(1, 23):
            t = j / 22
            u, v = t * t, t ** 3
            dense.append((2 * v - 3 * u + 1) * p1 + (v - 2 * u + t) * m1
                         + (-2 * v + 3 * u) * p2 + (v - u) * m2)
    return dense


class Arrow3D:
    """Arc-length growth along a curved 3D path; width is shaft diameter."""

    def __init__(self, points, coll, color, width):
        dense = _catmull(points)
        self.root = _root("KW Curved Arrow", coll, dense[0].copy())
        offset = dense[0]
        self._path = [p - offset for p in dense]
        self._cum = [0.]
        for a, b in zip(self._path, self._path[1:]):
            self._cum.append(self._cum[-1] + (b - a).length)
        self.length = self._cum[-1]
        self.width = width = max(1e-6, float(width))
        samples = max(24, min(121, int(2.5 * self.length / width)))
        uniform = [self._find(self.length * i / (samples - 1)) for i in range(samples)]
        mat = _paint("KW arrow | high-gloss enamel", color, .24, .08, .48, .23)
        self._shaft = _stroke("KW Arrow | continuous shaft", uniform, width * .5, coll,
                              self.root, mat)
        self._shaft.data.bevel_factor_mapping_end = "SPLINE"
        self._shaft.data.splines[0].points[0].radius = .58
        self._head_len = min(width * 2.50, self.length * .56)
        self._head = _revolve("KW Arrow | rounded spear tip",
                              [(-self._head_len * .22, width * .47),
                               (-self._head_len * .10, width * 1.04),
                               (self._head_len * .02, width * 1.15),
                               (self._head_len * .185, width * .98),
                               (self._head_len * .85, width * .15),
                               (self._head_len * .96, width * .063),
                               (self._head_len, width * .018)],
                              coll, self.root, mat, sides=36)
        self._head.rotation_mode = "QUATERNION"
        self.set()

    def _find(self, s):
        i = min(len(self._cum) - 2, max(0, bisect_right(self._cum, s) - 1))
        seg = self._cum[i + 1] - self._cum[i]
        return self._path[i].lerp(self._path[i + 1], _unit((s - self._cum[i]) / max(1e-8, seg)))

    def set(self, grow=1.):
        grow = _unit(grow)
        travel = self.length * grow
        visible = travel > self.width * .025
        _vis(self._head, visible)
        # Normal-size head on long paths; on an early partial path it follows a small nub.
        sz = max(.001, min(1., travel / max(1e-8, 1.6 * self._head_len)))
        base = max(0, travel - self._head_len * sz)
        tip, joint = self._find(travel), self._find(base)
        direction = tip - joint
        if direction.length < 1e-7:
            direction = self._path[1] - self._path[0]
        direction.normalize()
        self._head.rotation_quaternion = _Z.rotation_difference(direction)
        self._head.scale = (sz,) * 3
        self._head.location = tip - direction * self._head_len * sz
        shaft_end = _unit((base + self._head_len * sz * .053) / self.length)
        self._shaft.data.bevel_factor_end = max(.00001, shaft_end)
        _vis(self._shaft, visible and shaft_end > .007)
        return self
