"""Kitchen set: checker floor, papered back wall, window, counter, table, and a partition wall with a swinging kitchen door."""
import math, bpy
from toon import *

XD = 1.7            # door plane x
YH, YE = 1.45, 0.05 # hinge y and free-edge y (door width 1.4)
DH = 2.9            # door height

def checker_mat():
    m = bpy.data.materials.new('floor'); m.use_nodes = True; nt = m.node_tree; b = nt.nodes['Principled BSDF']
    ch = nt.nodes.new('ShaderNodeTexChecker'); ch.inputs['Scale'].default_value = 1.0
    ch.inputs['Color1'].default_value = (*hexc('#F3EBDD'), 1); ch.inputs['Color2'].default_value = (*hexc('#2E3A4F'), 1)
    tc = nt.nodes.new('ShaderNodeTexCoord'); mp = nt.nodes.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (0.9, 0.9, 0.9)
    nt.links.new(tc.outputs['Object'], mp.inputs['Vector']); nt.links.new(mp.outputs['Vector'], ch.inputs['Vector']); nt.links.new(ch.outputs['Color'], b.inputs['Base Color'])
    b.inputs['Roughness'].default_value = 0.25; b.inputs['Specular IOR Level'].default_value = 0.4
    return m

def stripes_mat(name, a, b_, scale=6.0):
    m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; b = nt.nodes['Principled BSDF']
    w = nt.nodes.new('ShaderNodeTexWave'); w.inputs['Scale'].default_value = scale; w.wave_profile = 'SIN'; w.bands_direction = 'X'
    r = nt.nodes.new('ShaderNodeValToRGB'); r.color_ramp.elements[0].color = (*hexc(a), 1); r.color_ramp.elements[1].color = (*hexc(b_), 1)
    r.color_ramp.elements[0].position = 0.45; r.color_ramp.elements[1].position = 0.55
    tc = nt.nodes.new('ShaderNodeTexCoord'); nt.links.new(tc.outputs['Object'], w.inputs['Vector'])
    nt.links.new(w.outputs['Fac'], r.inputs['Fac']); nt.links.new(r.outputs['Color'], b.inputs['Base Color']); b.inputs['Roughness'].default_value = 0.8
    return m

def build_kitchen():
    S = {}
    box('floor', checker_mat(), (30, 24, 0.1), (0, -6, -0.05), 0)
    wall = stripes_mat('wallpaper', '#F7E7B4', '#F2D88F', 5.0)
    box('backwall', wall, (16, 0.2, 7), (-1.5, 3.2, 3.5), 0)
    wains = mat('wainscot', hexc('#7FB6A4'), 0.55); trim = mat('trim', hexc('#FFFFFF'), 0.4)
    box('wainscot', wains, (16, 0.12, 1.25), (-1.5, 3.05, 0.62), 0.01); box('rail', trim, (16, 0.18, 0.1), (-1.5, 3.0, 1.27), 0.02)
    box('base', trim, (16, 0.16, 0.16), (-1.5, 3.0, 0.08), 0.02)
    # window with sky and curtains
    sky = mat('sky', hexc('#9FD3FF'), 0.5, emit=0.9); frame = trim
    box('win_sky', sky, (1.9, 0.05, 1.6), (-1.6, 3.08, 3.3), 0)
    for (sx, sz, x, z) in ((2.1, 0.12, -1.6, 4.15), (2.1, 0.12, -1.6, 2.45), (0.12, 1.8, -2.6, 3.3), (0.12, 1.8, -0.6, 3.3), (0.08, 1.6, -1.6, 3.3), (1.9, 0.08, -1.6, 3.3)):
        box('win_f', frame, (sx, 0.14, sz), (x, 3.0, z), 0.015)
    box('sill', frame, (2.4, 0.35, 0.1), (-1.6, 2.92, 2.4), 0.02)
    cur = stripes_mat('curtain', '#E9483F', '#FFFFFF', 14.0)
    for x in (-2.85, -0.35):
        c = box('curtain', cur, (0.55, 0.08, 2.1), (x, 2.9, 3.3), 0.04)
    box('rod', mat('rod', hexc('#8A5A2B'), 0.4), (3.2, 0.06, 0.06), (-1.6, 2.86, 4.38), 0.02)
    # counter + cabinets on the left
    cab = mat('cab', hexc('#7FB6A4'), 0.5); top = mat('top', hexc('#F6F1E7'), 0.3)
    box('counter', cab, (2.6, 0.9, 1.3), (-4.6, 2.6, 0.65), 0.03); box('countertop', top, (2.7, 1.0, 0.1), (-4.6, 2.55, 1.35), 0.02)
    box('upper', cab, (2.6, 0.6, 1.1), (-4.6, 2.85, 3.6), 0.03)
    # table with red check cloth
    cloth = mat('cloth', hexc('#D93B3B'), 0.8)
    box('tabletop', cloth, (1.6, 1.0, 0.12), (-1.5, 2.1, 1.25), 0.03)
    for dx in (-0.65, 0.65): box('tleg', mat('wood', hexc('#9A6A3A'), 0.5), (0.1, 0.1, 1.2), (-1.5 + dx, 2.35, 0.6), 0.01)
    # partition wall with doorway (x = XD), door hinged at y=YH
    pw = stripes_mat('wallpaper2', '#F7E7B4', '#F2D88F', 5.0)
    box('pw_back', pw, (0.2, 3.2 - YH, 7), (XD + 0.1, (3.2 + YH) / 2 + 0.05, 3.5), 0)
    box('pw_top', pw, (0.2, YH - YE + 0.1, 7 - DH), (XD + 0.1, (YH + YE) / 2, DH + (7 - DH) / 2), 0)
    box('pw_wains_b', wains, (0.12, 3.2 - YH, 1.25), (XD - 0.02, (3.2 + YH) / 2 + 0.05, 0.62), 0.01)
    for y in (YH + 0.06, YE - 0.06): box('jamb', trim, (0.3, 0.12, DH + 0.1), (XD + 0.05, y, (DH + 0.1) / 2), 0.02)
    box('lintel', trim, (0.3, YH - YE + 0.36, 0.14), (XD + 0.05, (YH + YE) / 2, DH + 0.1), 0.02)
    # the door: pivot empty at the hinge
    piv = link(bpy.data.objects.new('door_pivot', None)); piv.location = (XD + 0.05, YH, 0)
    dm = mat('door', hexc('#C9773B'), 0.45, 0.3); dk = mat('door_panel', hexc('#B4652E'), 0.45, 0.3)
    w = YH - YE
    d = box('door', dm, (0.1, w, DH), (0, -w / 2, DH / 2), 0.02); d.parent = piv
    for zc in (0.8, 2.15):
        p = box('door_panel', dk, (0.13, w * 0.7, 0.95), (0, -w / 2, zc), 0.03); p.parent = piv
    kick = box('kickplate', mat('brass', hexc('#D9A441'), 0.25, 0.8), (0.12, w * 0.9, 0.25), (0, -w / 2, 0.2), 0.01); kick.parent = piv
    box('room2', mat('room2', hexc('#BFD7EA'), 0.8), (0.2, 6, 7), (XD + 2.6, 0, 3.5), 0)
    S['door'] = piv
    return S
