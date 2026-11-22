"""Procedural cortex and skeletal context; no external meshes."""
import math
import bpy
from mathutils import Vector as V, noise
import kwlib as L
import kwlook as Q


def cortex(mat):
    nt = mat.node_tree; p = L.bsdf(mat); link = nt.links.new
    Q.texture(mat, (.25, .026, .034), (.82, .31, .28), 12., detail=3,
              rough=(.32, .48), bump=(.29, .0014), source=nt.nodes.new('ShaderNodeTexCoord').outputs['Generated'])
    a = nt.nodes.new('ShaderNodeAttribute'); a.attribute_name = 'cortex_fold'
    r = nt.nodes.new('ShaderNodeValToRGB'); link(a.outputs['Fac'], r.inputs[0])
    r.color_ramp.elements[0].color = (.26, .105, .12, 1)
    r.color_ramp.elements[1].color = (1., .92, .86, 1)
    m = nt.nodes.new('ShaderNodeMixRGB'); m.blend_type = 'MULTIPLY'; m.inputs[0].default_value = .83
    link(p.inputs['Base Color'].links[0].from_socket, m.inputs[1])
    link(r.outputs[0], m.inputs[2]); link(m.outputs[0], p.inputs['Base Color'])


def lobe(name, center, side, mat):
    o = L.sphere(name, 1, center, mat, None, 104, 72)
    att = o.data.attributes.new('cortex_fold', 'FLOAT', 'POINT')
    for i, v in enumerate(o.data.vertices):
        x, y, z = v.co
        p = V((x * 1.85 + side * 4.9, y * 2.9, z * 2.55))
        p += noise.noise_vector(p * .84, noise_basis='PERLIN_ORIGINAL') * .76
        ds, _ = noise.voronoi(p)
        g = min(1., max(0., (ds[1] - ds[0]) * 4.35)); g = g * g * (3 - 2 * g)
        d = .877 + g * .145 * (1 - .58 * max(0., -x * side) ** 3) + .017 * math.sin(3.4 * y + 5.4 * z)
        xx = x * (.72 if x * side < 0 else 1.06) * (1 - .13 * y)
        zz = z * (.78 if z < 0 else 1.) - .13 * y
        v.co = (xx * d * .039, y * d * .081, zz * d * .064)
        att.data[i].value = g
    o.data.update()
    return o


def lobulate(o, side):
    for v in o.data.vertices:
        x, y, z = v.co
        f = 1.0 - .18 * math.exp(-((z + .22 - .43 * y) / .093) ** 2)
        v.co.x *= (1.10 - .26 * max(0., z) - .24 * max(0., -side * x) ** 2) * f
        v.co.y *= (1. - .20 * max(0., z)) * f
    o.data.update()


def organic(mat, dark, light, scale, bump, stretch=None):
    tc = mat.node_tree.nodes.new('ShaderNodeTexCoord').outputs['Generated']
    Q.texture(mat, dark, light, scale, detail=3, stretch=stretch, rough=(.33, .53),
              bump=(.34, bump), source=tc)


def lung_threads(body, center, side, material):
    # Thin, tapered bronchial/vascular branches hug the anterior lung.
    points = [center + V((-side*.031, -.040, .057)),
              center + V((-side*.010, -.052, .019)),
              center + V((side*.008, -.056, -.021)),
              center + V((side*.014, -.045, -.072))]
    body.add('lungs', L.tube('x_lung_tree', points, .0023, material, res=2, radii=(1.2, 1., .70, .33)), 'spine02')
    for k, (z, dx) in enumerate(((.087, .034), (.041, .045), (-.017, .044), (-.074, .031))):
        start = points[min(k+1, 3)].lerp(points[k], .42)
        finish = center + V((side*dx, -.040, z))
        mid = start.lerp(finish, .57) + V((0, -.006, -.011))
        body.add('lungs', L.tube('x_lung_branch', [start, mid, finish], .0016, material,
                                res=2, radii=(1., .61, .12)), 'spine02')


def skeleton(body, head, n1, spine, width):
    tint = L.mat('kw_scan_bone', (.14, .31, .43), .48, emit=(.019, .23, .40), es=.48)
    Q.texture(tint, (.054, .13, .21), (.29, .49, .59), 95., rough=(.43, .60), bump=(.28, .0014))
    s2, s3, s5 = spine
    bands = [('_cervical', 'neck01', head + V((0, .023, -.036)), n1 + V((0, .034, -.03)), 6, .016),
             ('_thorax', 'spine02', n1 + V((0, .035, -.055)), s3 + V((0, .043, .003)), 9, .021),
             ('_thorax', 'spine04', s3 + V((0, .040, -.016)), s5 + V((0, .04, .01)), 7, .023)]
    for layer, bone, a, b, n, w in bands:
        verts, faces = [], []
        seg, rings = 14, 8
        def oval(center, scale):
            base = len(verts)
            for k in range(rings + 1):
                v = k * math.pi / rings
                for j in range(seg):
                    u = j * math.tau / seg
                    verts.append(center + V((scale[0] * math.sin(v) * math.cos(u),
                                              scale[1] * math.sin(v) * math.sin(u), scale[2] * math.cos(v))))
            for k in range(rings):
                for j in range(seg):
                    i = base + k * seg + j; jj = base + k * seg + (j + 1) % seg
                    faces.append((i, i + seg, jj + seg, jj))
        for j in range(n):
            q = a.lerp(b, (j + .44) / n); h = min((a - b).length / n * .32, .009)
            oval(q, (w, w * .70, h))
            oval(q + V((0, w * .69, -h * .60)), (w * .32, w * .75, h * .60))
        me = bpy.data.meshes.new('x_vertebrae'); me.from_pydata(verts, [], faces)
        eo = bpy.data.objects.new('x_vertebrae', me); body.coll.objects.link(eo)
        eo.data.materials.append(tint); body.add(layer, L.smooth(eo), bone)
    for j in range(8):
        w = width * (.71 + .045 * j); z = n1.z - .077 - .024 * j
        rear = s2.y + .045; front = s2.y - .11
        for sx in (-1, 1):
            pts = [(sx * .019, rear, z), (sx * w * .78, rear - .019, z - .008),
                   (sx * w, front + .066, z - .023), (sx * w * .82, front + .017, z - .031),
                   (sx * .018, front, z - .042)]
            body.add('_thorax', L.tube('x_rib', pts, .0038, tint, res=2, radii=(1.06, .98, .83, .64, .44)), 'spine02')
