"""Lightweight look-dev helpers and additive CMU motion tracks."""
import json
import math
import os
from pathlib import Path
import zlib

import bpy
from mathutils import Quaternion, Vector as V
import kwlib as L

# Local negative-Z end of the slushie straw in kwfx, after its ten-degree tilt.
SLUSH_STRAW_TIP = (-0.00329, 0.0, -0.16401)


def enabled(component):
    return os.environ.get(f'KW_{component}_R4', '1') != '0'


def phase_seed(name):
    return zlib.crc32(name.encode('utf-8')) / 4294967296.0


def body_beat(t, u, phase, acts, base):
    """Pure time function: irregular breath, weight transfer, delayed action recoil."""
    breath = (math.sin(t * 1.67 + phase * 6.283 + 0.20 * math.sin(t * 0.63))
              + 0.23 * math.sin(t * 3.34 + phase * 12.566 - 0.6)) / 1.23
    weight = 0.70 * math.sin(t * 1.11 + phase * 6.283) + 0.30 * math.sin(t * 2.19 + phase * 15.6)
    lift = 0.0
    for a in acts:
        delays = {'sneeze': (0.03,), 'blow_nose': (0.04,), 'drink': (0.19,), 'swallow': (0.04,), 'wince': (0.05,),
                  'flinch': (0.105,), 'gasp': (0.095,), 'eat': (0.06,)}.get(a.kind, ())
        if a.kind == 'cough':
            delays = tuple(i * a.kw.get('gap', 0.45) + 0.035 for i in range(int(a.kw.get('n', 3))))
        for delay in delays:
            dt = u - a.at - delay
            lift += (math.exp(-((dt + 0.095) / 0.13) ** 2) * 0.24
                     + math.exp(-(dt / 0.12) ** 2)
                     - 0.34 * math.exp(-((dt - 0.23) / 0.15) ** 2))
    lift = max(-0.35, min(1.30, lift))
    seated = base in ('sit', 'drive')
    if base == 'lie': return 0.45 * breath, 0.0, 0.16 * lift
    return breath, weight * (0.40 if seated else 1.0), lift


def auto_blink(t, phase, acts, u):
    """Irregular global blink intervals, with a response outside selected sharp acts."""
    def smooth(v):
        v = max(0.0, min(1.0, v)); return v * v * (3 - 2 * v)
    def pulse(dt):
        return smooth(1 + dt / 0.058) if dt < 0 else smooth(1 - dt / 0.102)
    shifted = t + 3.1 * phase
    cycle = int(shifted / 3.25)
    offset = 0.35 + 0.30 * math.sin(cycle * 2.399 + 6.283 * phase)
    natural = pulse(shifted - cycle * 3.25 - offset)
    response = max((0.88 * pulse(u - a.at - 0.24) for a in acts if a.kind in ('gasp', 'flinch', 'wince')), default=0.0)
    return max(natural, response)


def load_mocap():
    """Build the trimmed CMU torso rotation tracks once; no runtime rig imports."""
    if not enabled('MOCAP'): return {}
    path = Path(__file__).resolve().parents[2] / 'assets' / 'motion' / 'cmu_torso_r4.json'
    if not path.is_file():
        print('KW_MOCAP_R4: no captured tracks on disk; using procedural motion')
        return {}
    data = json.loads(path.read_text())
    names = ['drink', 'eat']
    contact = path.with_name('cmu_contact_r4.json')
    if enabled('CONTACT2') and contact.is_file():
        data.update(json.loads(contact.read_text()))
        names.extend(('clutch', 'lean'))
    # BVH Y up / +Z front -> kit Z up / -Y front; convert ZYX channel order exactly.
    basis = Quaternion((1, 0, 0), math.pi / 2)
    def qrot(row, j):
        z, y, x = (math.radians(d) for d in row[j:j + 3])
        return Quaternion((0, 0, 1), z) @ Quaternion((0, 1, 0), y) @ Quaternion((1, 0, 0), x)
    out = {}
    for k in names:
        out[k] = []
        for j in (0, 3, 6):
            neutral = qrot(data[k][0], j).inverted()
            out[k].append([basis @ qrot(row, j) @ neutral @ basis.inverted() for row in data[k]])
    return out


def _torso_delta(p, track, elapsed, weight, cap=None):
    for bone, samples in zip(('spine03', 'spine02', 'spine01'), track):
        f = elapsed * (len(samples) - 1); i = min(len(samples) - 2, int(f))
        sample = samples[i].slerp(samples[i + 1], f - i)
        if cap is not None:
            angle = Quaternion().rotation_difference(sample).angle
            angle = min(angle, math.tau - angle)
            if angle > cap: weight_ = weight * cap / angle
            else: weight_ = weight
        else: weight_ = weight
        delta = Quaternion().slerp(sample, weight_)
        pb = p.rig.pose.bones[bone]; rest = pb.bone.matrix_local.to_quaternion()
        pb.rotation_euler = (pb.rotation_euler.to_quaternion() @ rest.inverted() @ delta @ rest).to_euler('XYZ')


def mocap_pose(p, library, acts, u, base, pose=None, influence=1.0, cue=0., actor=None):
    """Retarget partial CMU deltas onto MPFB rest axes, before contact IK."""
    if not library or base == 'lie': return
    ingest = False
    for a in acts:
        track = library.get(a.kind)
        if not track: continue
        if a.kind == 'drink':
            elapsed = (u - a.at + 0.035) / max(0.35, a.kw.get('dur', 1.2) + 0.20)
        else:
            t = u - a.at + 0.13
            bite = max(0, int(t / 0.6))
            if bite >= a.kw.get('bites', 2): continue
            elapsed = (t - 0.6 * bite) / 0.56
        if not 0 < elapsed < 1: continue
        weight = min(1.0, elapsed / 0.13, (1.0 - elapsed) / 0.27)
        weight = weight * weight * (3 - 2 * weight) * (0.57 if base == 'drive' else 0.73)
        _torso_delta(p, track, elapsed, weight)
        ingest = True
    if ingest or pose is None or base not in ('sit', 'stand'): return
    hands = [h for h in (pose.left, pose.right) if h is not None]
    clutch = any(h.kind == 'touch' and (h.owner is None or h.owner is actor) and h.shape == 'claw' for h in hands)
    examiner = any(h.kind == 'touch' and h.owner is not None and h.owner is not actor for h in hands)
    if clutch:
        attack = next((a.at for a in acts if a.kind in ('flinch', 'wince', 'cough')), 0.)
        key, elapsed, amount = 'clutch', (u - max(cue, attack) + .09) / 1.52, .61
    elif examiner or pose.lean >= 5:
        key, elapsed, amount = 'lean', (u - cue) / 1.17, .52
    else: return
    track = library.get(key)
    if not track or not 0 < elapsed < 1: return
    weight = min(1., elapsed / .23, (1. - elapsed) / .33)
    _torso_delta(p, track, elapsed, weight * weight * (3 - 2 * weight) * amount * influence, math.radians(4.5))


def scan_shell(name, center, rim, energy, opacity, *, contour=False):
    """Clear face-on X-ray shell with a coloured, rather than white, contour."""
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear(); link = nt.links.new
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    layer = nt.nodes.new('ShaderNodeLayerWeight'); layer.inputs['Blend'].default_value = 0.22
    color = nt.nodes.new('ShaderNodeValToRGB')
    color.color_ramp.elements[0].color = (*center, 1)
    color.color_ramp.elements[1].color = (*rim, 1)
    link(layer.outputs['Facing'], color.inputs[0])
    em = nt.nodes.new('ShaderNodeEmission'); em.inputs['Strength'].default_value = energy
    link(color.outputs[0], em.inputs['Color'])
    alpha = nt.nodes.new('ShaderNodeValToRGB')
    alpha.color_ramp.elements[0].color = (0.022, 0.022, 0.022, 1)
    alpha.color_ramp.elements[1].position = 0.92
    alpha.color_ramp.elements[1].color = (opacity, opacity, opacity, 1)
    mid = alpha.color_ramp.elements.new(0.58); mid.color = (0.10, 0.10, 0.10, 1)
    if contour:
        layer.inputs['Blend'].default_value = .44
        color.color_ramp.elements[1].position = .973
        alpha.color_ramp.elements[0].color = (.031, .031, .031, 1)
        mid.position = .70; mid.color = (.070, .070, .070, 1)
        alpha.color_ramp.elements[-1].position = .975
    link(layer.outputs['Facing'], alpha.inputs[0])
    tr = nt.nodes.new('ShaderNodeBsdfTransparent'); mx = nt.nodes.new('ShaderNodeMixShader')
    link(alpha.outputs[0], mx.inputs[0]); link(tr.outputs[0], mx.inputs[1])
    link(em.outputs[0], mx.inputs[2]); link(mx.outputs[0], out.inputs['Surface'])
    return m, em


def texture(m, dark, light, scale, *, detail=2, stretch=None, rough=None,
            bump=None, source=None):
    """Object-space tonal variation and optional nested bump; returns the material."""
    nt = m.node_tree; p = L.bsdf(m); link = nt.links.new
    xyz = source if source is not None else nt.nodes.new('ShaderNodeTexCoord').outputs['Object']
    if stretch:
        v = nt.nodes.new('ShaderNodeVectorMath'); v.operation = 'MULTIPLY'
        link(xyz, v.inputs[0]); v.inputs[1].default_value = stretch; xyz = v.outputs[0]
    n = nt.nodes.new('ShaderNodeTexNoise'); n.inputs['Scale'].default_value = scale
    n.inputs['Detail'].default_value = detail; link(xyz, n.inputs['Vector'])
    r = nt.nodes.new('ShaderNodeValToRGB'); r.color_ramp.elements[0].position = 0.20
    r.color_ramp.elements[0].color = (*dark, 1); r.color_ramp.elements[1].position = 0.80
    r.color_ramp.elements[1].color = (*light, 1); link(n.outputs['Fac'], r.inputs[0])
    link(r.outputs[0], p.inputs['Base Color'])
    if rough:
        rng = nt.nodes.new('ShaderNodeMapRange'); rng.inputs['To Min'].default_value, rng.inputs['To Max'].default_value = rough
        link(n.outputs['Fac'], rng.inputs['Value']); link(rng.outputs[0], p.inputs['Roughness'])
    if bump:
        b = nt.nodes.new('ShaderNodeBump'); b.inputs['Strength'].default_value, b.inputs['Distance'].default_value = bump
        pin = p.inputs['Normal']
        if pin.is_linked: link(pin.links[0].from_socket, b.inputs['Normal'])
        link(n.outputs['Fac'], b.inputs['Height']); link(b.outputs[0], pin)
    return m


def cabin_stitch(c, name, points, thread, radius=0.0013):
    """Multiple short seams in one curve datablock, not dozens of separate objects."""
    cr = bpy.data.curves.new(name, 'CURVE'); cr.dimensions = '3D'
    cr.bevel_depth = radius; cr.bevel_resolution = 1
    for a, b in zip(points, points[1:]):
        a, b = V(a), V(b)
        n = max(1, int((a - b).length / 0.010))
        for j in range(n):
            spline = cr.splines.new('POLY'); spline.points.add(1)
            for k, f in enumerate((0.16, 0.73)):
                spline.points[k].co = (*a.lerp(b, (j + f) / n), 1)
    o = bpy.data.objects.new(name, cr); c.objects.link(o); cr.materials.append(thread)
    return o


def cabin_seat(B, sx, nm, P, H, border, thread):
    """Tailored top stitch and darker piping following the two cushion contours."""
    for suffix, sign in (('L', -1), ('R', 1)):
        x = sx + sign * 0.171
        pts = [(x - sign * 0.014, 0.274 + 0.213 * (z - 0.3235), P + z)
               for z in (0.596, 0.55, 0.38, 0.17, 0.05)]
        L.tube(f'kw_{nm}_piping{suffix}', pts, 0.0045, border, B.c, 3)
        cabin_stitch(B.c, f'kw_{nm}_thread{suffix}', [(a - sign * 0.010, b - 0.003, d) for a, b, d in pts], thread)
    pts = [(sx + x, 0.398 + 0.141 * z, H + z)
           for x in (-0.098, -0.067, -0.032, 0, 0.032, 0.067, 0.098)
           for z in (0.038 + 0.010 * (1 - (x / 0.098) ** 2),)]
    L.tube(f'kw_{nm}_headrest_seam', pts, 0.0028, border, B.c, 3)
    cabin_stitch(B.c, f'kw_{nm}_headrest_thread', [(a, b - 0.0015, d - 0.009) for a, b, d in pts], thread, 0.001)


def cabin_door(B, side, x, sgn, P, BL, dark, padded, bright, strip, thread):
    def panel(name, size, pos, m, bev, rot=(0, 0, 0)):
        return B.box(f'kw_{name}_{side}', size, (x + sgn * pos[0], pos[1], pos[2]), m, bev, rot, 3)
    panel('window_sill', (0.053, 2.39, 0.052), (0.051, 0.28, BL - 0.022), dark, 0.014)
    panel('door_insert', (0.035, 1.23, 0.18), (0.047, -0.19, BL - 0.16), padded, 0.015, (-5, 0, 0))
    panel('rear_door_insert', (0.035, 0.68, 0.16), (0.047, 1.05, BL - 0.17), padded, 0.014, (-4, 0, 0))
    panel('door_satin_inlay', (0.009, 1.28, 0.013), (0.074, -0.19, BL - 0.076), bright, 0.004, (-3, 0, 0))
    panel('door_accent', (0.006, 1.25, 0.005), (0.077, -0.19, BL - 0.087), strip, 0.002, (-3, 0, 0))
    panel('rear_door_inlay', (0.009, 0.71, 0.010), (0.072, 1.06, BL - 0.10), bright, 0.004, (-3, 0, 0))
    panel('pull_recess', (0.015, 0.19, 0.078), (0.073, -0.36, BL - 0.165), dark, 0.007, (-6, 0, 0))
    panel('pull_handle', (0.022, 0.125, 0.013), (0.086, -0.36, BL - 0.165), bright, 0.005, (-6, 0, 0))
    panel('switch_plate', (0.075, 0.15, 0.014), (0.071, -0.08, P + 0.18), dark, 0.006)
    for i in range(3):
        panel('window_switch', (0.030, 0.023, 0.006), (0.080, -0.13 + i * 0.039, P + 0.189), bright, 0.002)
    cabin_stitch(B.c, f'kw_door_stitch_{side}', [(x + sgn * 0.065, -0.73, BL - 0.211),
                                               (x + sgn * 0.065, 0.37, BL - 0.308)], thread)
