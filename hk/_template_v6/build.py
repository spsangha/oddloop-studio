#!/usr/bin/env python3
"""HK Unlocked Reel builder v6 (2026-11-24; v5 + job.json "look": map_day | neon | menu, see looks.py). ONE script for all three formats, driven by <reel>/job.json.

  map     original stylised Hong Kong map drawn from cached OpenStreetMap vectors, route moving on frame 0,
          price pinned on the right segment, faceless guide figure travelling the route, saveable summary at the end
  steps   self-drawn 3-step booking / eligibility walkthrough (our own design, never an official app UI)
  ladder  animated 2-3 item price ladder

usage:
  python3 build.py <reel_folder> voice          # TTS (Ava +4%) -> vo.wav + words.json (word timings from the TTS itself)
  python3 build.py <reel_folder> stills 0,0.5,1  # low-CPU check: render only these seconds to <reel>/stills/
  python3 build.py <reel_folder> render [--draft] # full mp4 (draft = 15 fps, fast encode, for timing checks only)
  python3 build.py <reel_folder> all             # voice (if missing) + render + sheets + qa
Everything is drawn in code (cairo + PIL). No AI imagery, no tile images, no whoosh, no music unless job.json names a
licensed file that ships in the kit.
"""
import asyncio, json, math, os, re, subprocess, sys, time
import numpy as np
import cairo
from PIL import Image, ImageDraw, ImageFont, ImageFilter

T5 = os.path.dirname(os.path.abspath(__file__))
W, H, FPS = 1080, 1920, 30
SAFE = (70, 270, 900, 1230)                       # hook_spec: essential type in the first 3 s
STAGE = (70, 230, 900, 1400)                      # visual_rules: everything after 3 s (captions 1295-1380), nothing essential below 1420
YEL = (255, 214, 10)
STYLE = 'paper3'                                 # bump when the map palette changes (base-map PNG cache key)
FD = '/usr/local/share/fonts/asi-document'
F_EN = {'black': FD + '/Montserrat-Black.ttf', 'xb': FD + '/Montserrat-ExtraBold.ttf', 'bold': FD + '/Montserrat-Bold.ttf',
        'semi': FD + '/Montserrat-SemiBold.ttf'}
F_ZH = ('/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc', 4)       # face 4 = Noto Sans CJK HK (Hong Kong glyph forms)
F_ZH_REG = ('/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc', 4)

# ---- HK Unlocked v5 look: "harbour paper" -------------------------------------------------------------------------
C = dict(land=(214, 198, 166), build=(196, 178, 146), park=(172, 196, 140), water=(62, 138, 164), water_deep=(50, 120, 148),
         road=(247, 241, 228), casing=(188, 172, 146), rail=(150, 136, 118), pier=(238, 228, 205),
         ink=(14, 33, 46), teal=(11, 79, 92), gold=(255, 201, 60), coral=(232, 84, 56), mute=(120, 128, 134),
         card=(255, 255, 255), paper=(248, 245, 238), off=(206, 210, 212))


def rgb(c, a=1.0): return (c[0] / 255, c[1] / 255, c[2] / 255, a)
def ease(u): u = max(0.0, min(1.0, u)); return u * u * (3 - 2 * u)
def eout(u): u = max(0.0, min(1.0, u)); return 1 - (1 - u) ** 3
def back(u):
    u = max(0.0, min(1.0, u)); s = 1.6; u -= 1; return u * u * ((s + 1) * u + s) + 1


def has_zh(s): return any(ord(ch) > 0x2E80 for ch in s)
_fc = {}
def font(kind, size):
    k = (kind, int(size))
    if k not in _fc:
        if kind == 'zh': _fc[k] = ImageFont.truetype(F_ZH[0], int(size), index=F_ZH[1])
        elif kind == 'zhr': _fc[k] = ImageFont.truetype(F_ZH_REG[0], int(size), index=F_ZH_REG[1])
        else: _fc[k] = ImageFont.truetype(F_EN[kind], int(size))
    return _fc[k]


# ---- timeline helpers -----------------------------------------------------------------------------------------------
class Clock:
    """resolves job times: number = seconds; 'L3' = start of spoken line 3; 'L3+0.4'; 'L3e' = end of line 3; 'end-2'"""
    def __init__(self, lines_t, dur): self.L = lines_t; self.dur = dur
    def __call__(self, v):
        if isinstance(v, (int, float)): return float(v)
        m = re.fullmatch(r'\s*(L(\d+)(e?)|end)\s*([+-]\s*[\d.]+)?\s*', str(v))
        if not m: raise ValueError(f'bad time {v!r}')
        if m.group(1) == 'end': base = self.dur
        else:
            a, b = self.L[int(m.group(2)) - 1]; base = b if m.group(3) else a
        return base + (float(m.group(4).replace(' ', '')) if m.group(4) else 0.0)


def keyed(keys, t):
    """piecewise eased interpolation of [(t, value-or-tuple), ...]"""
    if t <= keys[0][0]: return keys[0][1]
    for (t0, v0), (t1, v1) in zip(keys, keys[1:]):
        if t <= t1:
            u = ease((t - t0) / max(1e-6, t1 - t0))
            if isinstance(v0, (tuple, list)): return tuple(a + (b - a) * u for a, b in zip(v0, v1))
            return v0 + (v1 - v0) * u
    return keys[-1][1]


# ---- projection ------------------------------------------------------------------------------------------------------
def mx(lon): return (lon + 180) / 360
def my(lat): r = math.radians(lat); return (1 - math.log(math.tan(r) + 1 / math.cos(r)) / math.pi) / 2
M_PER_UNIT = 40075016.7 * math.cos(math.radians(22.29))          # metres per mercator unit at Hong Kong latitude


# ---- text sprites (PIL, cached) --------------------------------------------------------------------------------------
_sc = {}
def text_img(s, kind, size, col, hi=None, hi_col=None):
    """one line of text; {braces} = highlighted (gold marker behind) span"""
    key = (s, kind, size, col, hi_col)
    if key in _sc: return _sc[key]
    f = font(kind, size); segs = []
    for part in re.split(r'(\{[^}]*\})', s):
        if part: segs.append((part.strip('{}'), part.startswith('{')))
    asc, desc = f.getmetrics(); pad = int(size * 0.18)
    wds = [f.getlength(p) for p, _ in segs]; tw = int(sum(wds)) + 2 * pad + 4; th = asc + desc + 2 * pad
    im = Image.new('RGBA', (tw, th), (0, 0, 0, 0)); d = ImageDraw.Draw(im); x = pad
    for (p, on), w in zip(segs, wds):
        if on:
            d.rounded_rectangle((x - pad * 0.55, pad + asc * 0.12, x + w + pad * 0.55, pad + asc + desc * 0.55), radius=int(size * 0.16), fill=(hi_col or C['gold']) + (255,))
        d.text((x, pad), p, font=f, fill=col + (255,)); x += w
    _sc[key] = im; return im


def fit_img(s, kind, size, col, maxw, hi_col=None):
    """text_img shrunk (never below 70 %) until it is at most maxw wide"""
    sz = size
    while True:
        im = text_img(s, kind, sz, col, hi_col=hi_col)
        if im.width <= maxw or sz <= size * 0.7: return im
        sz -= 2


def card_img(rows, width=None, pad=(38, 26), radius=30, bg=None, gap=8, align='left', accent=None, shadow=True):
    """rows = [(text, kind, size, colour), ...] -> rounded card sprite (2x supersampled corners)"""
    key = ('card', tuple(rows), width, pad, radius, bg, gap, align, accent, shadow)
    if key in _sc: return _sc[key]
    ims = [fit_img(r[0], r[1], r[2], r[3], (width - 2 * pad[0] - (12 if accent else 0)) if width else 2000) for r in rows]
    cw = width or max(i.width for i in ims) + 2 * pad[0]
    chh = sum(i.height for i in ims) + gap * (len(ims) - 1) + 2 * pad[1]
    S = 2; sh = 24 if shadow else 0
    big = Image.new('RGBA', ((cw + 2 * sh) * S, (chh + 2 * sh) * S), (0, 0, 0, 0)); d = ImageDraw.Draw(big)
    if shadow:
        sd = Image.new('RGBA', big.size, (0, 0, 0, 0)); ImageDraw.Draw(sd).rounded_rectangle((sh * S, (sh + 10) * S, (sh + cw) * S, (sh + chh + 10) * S), radius=radius * S, fill=(10, 30, 40, 70))
        big = Image.alpha_composite(big, sd.filter(ImageFilter.GaussianBlur(14 * S))); d = ImageDraw.Draw(big)
    d.rounded_rectangle((sh * S, sh * S, (sh + cw) * S, (sh + chh) * S), radius=radius * S, fill=(bg or C['card']) + (255,))
    if accent: d.rounded_rectangle((sh * S, sh * S, (sh + 12) * S, (sh + chh) * S), radius=6 * S, fill=accent + (255,))
    im = big.resize((cw + 2 * sh, chh + 2 * sh), Image.LANCZOS); y = sh + pad[1]
    for t in ims:
        x = sh + (pad[0] + (10 if accent else 0) if align == 'left' else (cw - t.width) // 2)
        im.alpha_composite(t, (int(x), int(y))); y += t.height + gap
    im.info['inner'] = (sh, sh, cw, chh); _sc[key] = im; return im


def paper_tag(price, en, zh):
    """hand-lettered paper price tag (cream card, gold band, string hole): our own drawing, not a copy of any real sign"""
    key = ('ptag', price, en, zh)
    if key in _sc: return _sc[key]
    fp = ImageFont.truetype(T5 + '/fonts/PatrickHand-Regular.ttf', 120)
    rows = [fit_img(en, 'xb', 40, C['ink'], 440), fit_img(zh, 'zh', 40, C['teal'], 440)]
    pw = int(fp.getlength(price)); w = max(pw + 60, max(r.width for r in rows) + 40, 300); h = 70 + 128 + sum(r.height for r in rows) + 24
    S = 2; im = Image.new('RGBA', ((w + 40) * S, (h + 40) * S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    sd = Image.new('RGBA', im.size, (0, 0, 0, 0)); ImageDraw.Draw(sd).rounded_rectangle((20 * S, 30 * S, (20 + w) * S, (30 + h) * S), radius=18 * S, fill=(0, 0, 0, 110))
    im = Image.alpha_composite(im, sd.filter(ImageFilter.GaussianBlur(10 * S))); d = ImageDraw.Draw(im)
    d.rounded_rectangle((20 * S, 20 * S, (20 + w) * S, (20 + h) * S), radius=18 * S, fill=(250, 240, 214, 255), outline=C['ink'] + (255,), width=3 * S)
    d.rounded_rectangle((20 * S, 20 * S, (20 + w) * S, (20 + 52) * S), radius=18 * S, fill=C['gold'] + (255,))
    d.rectangle((20 * S, 50 * S, (20 + w) * S, 72 * S), fill=C['gold'] + (255,)); d.line((20 * S, 72 * S, (20 + w) * S, 72 * S), fill=C['ink'] + (255,), width=3 * S)
    d.ellipse(((20 + w / 2 - 9) * S, 35 * S, (20 + w / 2 + 9) * S, 53 * S), fill=(250, 240, 214, 255), outline=C['ink'] + (255,), width=3 * S)
    im = im.resize((w + 40, h + 40), Image.LANCZOS); d = ImageDraw.Draw(im)
    d.text((20 + w / 2, 20 + 70 + 62), price, font=fp, fill=C['ink'] + (255,), anchor='mm')
    y = 20 + 70 + 126
    for r in rows: im.alpha_composite(r, (int(20 + (w - r.width) / 2), int(y))); y += r.height
    im.info['inner'] = (20, 20, w, h); _sc[key] = im; return im


class Frame:
    """one output frame: cairo surface for shapes, then PIL sprites on top; records every text box for the QA"""
    def __init__(self, t):
        self.t = t; self.surf = cairo.ImageSurface(cairo.FORMAT_ARGB32, W, H); self.cr = cairo.Context(self.surf)
        self.sprites = []; self.boxes = []
    def put(self, im, x, y, alpha=1.0, anchor='lt', essential=True, tag='', scale=1.0, clamp=False):
        if alpha <= 0.01: return
        if scale != 1.0:                                       # scale first so the clamp and the logged box see the real size
            inn0 = im.info.get('inner'); im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.BILINEAR)
            if inn0: im.info['inner'] = tuple(v * scale for v in inn0)
            scale = 1.0
        if clamp:                                              # keep a drifting label's card inside the safe zone
            inn = im.info.get('inner', (0, 0, im.width, im.height)); fx = {'l': 0, 'm': 0.5, 'r': 1}[anchor[0]]; fy = {'t': 0, 'm': 0.5, 'b': 1}[anchor[1]]
            bx0 = x - im.width * fx + inn[0]; by0 = y - im.height * fy + inn[1]
            Z = SAFE if self.t < 3.0 else (STAGE[0], SAFE[1], STAGE[2], 1270)
            x += max(0, Z[0] - bx0) - max(0, bx0 + inn[2] - Z[2]); y += max(0, Z[1] - by0) - max(0, by0 + inn[3] - Z[3])
        ix, iy = x - (im.width / 2 if anchor[0] == 'm' else im.width if anchor[0] == 'r' else 0), y - (im.height / 2 if anchor[1] == 'm' else im.height if anchor[1] == 'b' else 0)
        self.sprites.append((im, int(round(ix)), int(round(iy)), alpha))
        inn = im.info.get('inner')
        bx = (ix + inn[0] * scale, iy + inn[1] * scale, ix + (inn[0] + inn[2]) * scale, iy + (inn[1] + inn[3]) * scale) if inn else (ix, iy, ix + im.width, iy + im.height)
        if alpha > 0.5: self.boxes.append(dict(tag=tag, box=[round(v) for v in bx], essential=essential))
    def image(self):
        a = np.ndarray((H, W, 4), np.uint8, self.surf.get_data(), strides=(self.surf.get_stride(), 4, 1))
        im = Image.fromarray(a[:, :, [2, 1, 0, 3]].copy(), 'RGBA')
        for s, x, y, al in self.sprites:
            if al < 0.999: s = s.copy(); s.putalpha(s.getchannel('A').point(lambda v, al=al: int(v * al)))
            im.alpha_composite(s, (x, y)) if x >= 0 and y >= 0 and x + s.width <= W and y + s.height <= H else im.paste(s, (x, y), s)
        return im.convert('RGB')


# ---- base map (rendered once from the OSM cache) ---------------------------------------------------------------------
class BaseMap:
    def __init__(self, area, view, mpp=0.85):
        self.data = json.load(open(f'{T5}/osm/cache/{area}.json'))
        w, s, e, n = view; self.x0, self.y0 = mx(w), my(n); self.x1, self.y1 = mx(e), my(s)
        self.ppu = M_PER_UNIT / mpp                                 # pixels per mercator unit in the base image
        self.Wb = int((self.x1 - self.x0) * self.ppu); self.Hb = int((self.y1 - self.y0) * self.ppu)
        cache = f'{T5}/osm/cache/{area}_{w}_{s}_{e}_{n}_{mpp}_{STYLE}.png'
        if os.path.exists(cache): self.surf = cairo.ImageSurface.create_from_png(cache); return
        sf = cairo.ImageSurface(cairo.FORMAT_RGB24, self.Wb, self.Hb); cr = cairo.Context(sf)
        cr.set_source_rgba(*rgb(C['land'])); cr.paint()
        P = lambda ll: ((mx(ll[0]) - self.x0) * self.ppu, (my(ll[1]) - self.y0) * self.ppu)
        def poly(rings, col):
            cr.set_source_rgba(*rgb(col)); cr.set_fill_rule(cairo.FILL_RULE_EVEN_ODD)
            for ring in rings:
                for i, (x, y) in enumerate(map(P, ring)): (cr.move_to if i == 0 else cr.line_to)(x, y)
                cr.close_path()
            cr.fill()
        for r in self.data['park']: poly(r, C['park'])
        for r in self.data['water']: poly(r, C['water'])
        for r in self.data['building']: poly(r, C['build'])
        for rd in self.data['roads']:
            if rd['c'] == 'pier_area': poly([rd['pts']], C['pier'])
        widths = dict(motorway=15, trunk=13, primary=11, secondary=9, tertiary=7, minor=5, service=3, path=2, pier=5)
        cr.set_line_cap(cairo.LINE_CAP_ROUND); cr.set_line_join(cairo.LINE_JOIN_ROUND)
        for casing in (True, False):
            for cls in ('path', 'service', 'minor', 'pier', 'tertiary', 'secondary', 'primary', 'trunk', 'motorway'):
                for rd in self.data['roads']:
                    if rd['c'] != cls: continue
                    for i, (x, y) in enumerate(map(P, rd['pts'])): (cr.move_to if i == 0 else cr.line_to)(x, y)
                    if casing and cls in ('path', 'service', 'pier'): cr.new_path(); continue
                    cr.set_line_width(widths[cls] + (3 if casing else 0)); cr.set_source_rgba(*rgb(C['casing'] if casing else (C['pier'] if cls == 'pier' else C['road']))); cr.stroke()
        cr.set_dash([10, 8]); cr.set_line_width(3)
        for rd in self.data['roads']:
            if rd['c'] in ('rail', 'transit'):
                for i, (x, y) in enumerate(map(P, rd['pts'])): (cr.move_to if i == 0 else cr.line_to)(x, y)
                cr.set_source_rgba(*rgb(C['rail'], 0.7)); cr.stroke()
        sf.write_to_png(cache); self.surf = sf

    def draw(self, cr, cam, blur=False):
        """cam = (lon, lat, metres-per-pixel on screen); paints the base map filling the frame"""
        lon, lat, mpp = cam; s = (M_PER_UNIT / mpp) / self.ppu
        cx, cy = (mx(lon) - self.x0) * self.ppu, (my(lat) - self.y0) * self.ppu
        cr.save(); cr.set_source_rgba(*rgb(C['water'])); cr.paint()
        cr.translate(W / 2, H * 0.40); cr.scale(s, s); cr.translate(-cx, -cy)
        cr.set_source_surface(self.surf, 0, 0); cr.get_source().set_filter(cairo.FILTER_GOOD); cr.paint(); cr.restore()

    def to_screen(self, cam):
        lon, lat, mpp = cam; ppu = M_PER_UNIT / mpp
        return lambda ll: (W / 2 + (mx(ll[0]) - mx(lon)) * ppu, H * 0.40 + (my(ll[1]) - my(lat)) * ppu)


# ---- drawn elements --------------------------------------------------------------------------------------------------
def path_len(pts):
    seg = [math.dist(a, b) for a, b in zip(pts, pts[1:])]; return seg, sum(seg)


def point_at(pts, u):
    seg, L = path_len(pts); d = max(0.0, min(1.0, u)) * L
    for (a, b), s in zip(zip(pts, pts[1:]), seg):
        if d <= s or s == seg[-1]:
            k = d / s if s else 0; return (a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k), math.atan2(b[1] - a[1], b[0] - a[0])
        d -= s
    return pts[-1], 0.0


def sub_path(pts, u):
    seg, L = path_len(pts); d = max(0.0, min(1.0, u)) * L; out = [pts[0]]
    for (a, b), s in zip(zip(pts, pts[1:]), seg):
        if d >= s: out.append(b); d -= s
        else:
            k = d / s if s else 0; out.append((a[0] + (b[0] - a[0]) * k, a[1] + (b[1] - a[1]) * k)); break
    return out


def smooth(pts, n=6):
    """Catmull-Rom smoothing so routes look drawn, not jagged"""
    if len(pts) < 3: return pts
    P = [pts[0]] + list(pts) + [pts[-1]]; out = []
    for i in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[i - 1], P[i], P[i + 1], P[i + 2]
        for k in range(n):
            t = k / n; t2, t3 = t * t, t * t * t
            out.append(tuple(0.5 * (2 * p1[j] + (-p0[j] + p2[j]) * t + (2 * p0[j] - 5 * p1[j] + 4 * p2[j] - p3[j]) * t2 + (-p0[j] + 3 * p1[j] - 3 * p2[j] + p3[j]) * t3) for j in (0, 1)))
    return out + [pts[-1]]


def stroke_path(cr, pts, width, col, dash=None, offset=0.0):
    if len(pts) < 2: return
    cr.new_path()
    for i, (x, y) in enumerate(pts): (cr.move_to if i == 0 else cr.line_to)(x, y)
    cr.set_line_width(width); cr.set_line_cap(cairo.LINE_CAP_ROUND); cr.set_line_join(cairo.LINE_JOIN_ROUND)
    cr.set_dash(dash or [], offset); cr.set_source_rgba(*col); cr.stroke(); cr.set_dash([])


def rrect(cr, x, y, w, h, r):
    cr.new_sub_path(); cr.arc(x + w - r, y + r, r, -math.pi / 2, 0); cr.arc(x + w - r, y + h - r, r, 0, math.pi / 2)
    cr.arc(x + r, y + h - r, r, math.pi / 2, math.pi); cr.arc(x + r, y + r, r, math.pi, 1.5 * math.pi); cr.close_path()


def draw_guide(cr, x, y, t, walking=True, scale=1.0):
    """HK Unlocked's own faceless guide: teal capsule body, plain round head, gold cap, small backpack. No face, no brand cast."""
    cr.save(); cr.translate(x, y); cr.scale(scale, scale)
    ph = t * 2 * math.pi * 1.8; bob = abs(math.sin(ph)) * 4 if walking else math.sin(t * 2 * math.pi * 0.7) * 2
    cr.set_source_rgba(0, 0, 0, 0.18); cr.save(); cr.scale(1, 0.35); cr.arc(0, 0, 22, 0, 2 * math.pi); cr.restore(); cr.fill()
    sw = math.sin(ph) * 7 if walking else 0
    cr.set_line_cap(cairo.LINE_CAP_ROUND); cr.set_line_width(8); cr.set_source_rgba(*rgb(C['ink']))
    for s in (1, -1): cr.move_to(s * 6, -24 - bob); cr.line_to(s * 6 + s * sw * 0.0 + (sw if s > 0 else -sw), -2); cr.stroke()
    cr.set_source_rgba(*rgb(C['gold'])); rrect(cr, -21, -62 - bob, 14, 28, 6); cr.fill()                 # backpack
    cr.set_source_rgba(*rgb(C['teal'])); rrect(cr, -15, -66 - bob, 30, 44, 14); cr.fill()                # body
    cr.set_source_rgba(*rgb(C['card'])); cr.arc(0, -80 - bob, 13, 0, 2 * math.pi); cr.fill()            # head (faceless)
    cr.set_line_width(2.5); cr.set_source_rgba(*rgb(C['ink'], 0.85)); cr.arc(0, -80 - bob, 13, 0, 2 * math.pi); cr.stroke()
    cr.set_source_rgba(*rgb(C['gold'])); cr.arc(0, -84 - bob, 13.5, math.pi, 2 * math.pi); cr.fill()     # cap
    rrect(cr, 4, -87 - bob, 16, 6, 3); cr.fill()
    cr.restore()


def draw_boat(cr, x, y, ang, t, scale=1.0):
    """generic two-deck harbour ferry, top-down; our own simple shape, no operator livery"""
    cr.save(); cr.translate(x, y + math.sin(t * 2 * math.pi * 0.6) * 1.5); cr.rotate(ang); cr.scale(scale, scale)
    cr.set_source_rgba(1, 1, 1, 0.55)                                                                   # wake
    for k in (1, 2, 3):
        cr.set_line_width(3); cr.move_to(-46 - 16 * k, -10 - 6 * k); cr.line_to(-40, -6); cr.move_to(-46 - 16 * k, 10 + 6 * k); cr.line_to(-40, 6); cr.stroke()
    cr.set_source_rgba(0, 0, 0, 0.16); rrect(cr, -44, -18, 92, 40, 18); cr.fill()
    cr.set_source_rgba(*rgb(C['teal'])); rrect(cr, -46, -21, 92, 42, 19); cr.fill()
    cr.set_source_rgba(*rgb(C['card'])); rrect(cr, -36, -14, 72, 28, 12); cr.fill()
    cr.set_source_rgba(*rgb(C['gold'])); rrect(cr, -8, -8, 16, 16, 4); cr.fill()
    cr.restore()


def draw_taxi(cr, x, y, ang, t, scale=1.0, moving=True):
    """generic Hong Kong urban taxi, top-down: red body, silver roof, roof sign; our own simple shape, no operator livery"""
    cr.save(); cr.translate(x, y); cr.rotate(ang); cr.scale(scale, scale)
    cr.set_source_rgba(0, 0, 0, 0.22); rrect(cr, -33, -14, 70, 34, 10); cr.fill()                       # shadow
    cr.set_source_rgba(0.80, 0.10, 0.12, 1); rrect(cr, -35, -17, 70, 34, 10); cr.fill()                 # red body
    cr.set_source_rgba(0.55, 0.05, 0.07, 1); cr.set_line_width(2); rrect(cr, -35, -17, 70, 34, 10); cr.stroke()
    cr.set_source_rgba(0.20, 0.27, 0.33, 1); rrect(cr, 9, -13, 11, 26, 4); cr.fill()                    # windscreen
    cr.set_source_rgba(0.20, 0.27, 0.33, 1); rrect(cr, -27, -12, 7, 24, 3); cr.fill()                   # rear window
    cr.set_source_rgba(0.86, 0.87, 0.88, 1); rrect(cr, -20, -13, 29, 26, 5); cr.fill()                  # silver roof
    cr.set_source_rgba(1.0, 0.93, 0.55, 1); rrect(cr, -9, -7, 9, 14, 2); cr.fill()                      # roof sign
    cr.set_source_rgba(1, 0.98, 0.8, 0.95)                                                              # headlights
    for sy in (-11, 11): cr.arc(34, sy, 3, 0, 2 * math.pi); cr.fill()
    if not moving:                                                                                      # brake lights on at stops
        cr.set_source_rgba(1, 0.25, 0.2, 0.95)
        for sy in (-11, 11): cr.arc(-34, sy, 3.2, 0, 2 * math.pi); cr.fill()
    cr.restore()


def draw_pin(cr, x, y, col, s=1.0):
    if s < 0.02: return
    cr.save(); cr.translate(x, y); cr.scale(s, s)
    cr.set_source_rgba(0, 0, 0, 0.2); cr.save(); cr.scale(1, 0.4); cr.arc(0, 0, 14, 0, 2 * math.pi); cr.restore(); cr.fill()
    cr.move_to(0, 0); cr.curve_to(-6, -14, -22, -26, -22, -42); cr.arc(0, -42, 22, math.pi, 2 * math.pi); cr.curve_to(22, -26, 6, -14, 0, 0); cr.close_path()
    cr.set_source_rgba(*rgb(col)); cr.fill_preserve(); cr.set_line_width(3); cr.set_source_rgba(1, 1, 1, 1); cr.stroke()
    cr.arc(0, -42, 8, 0, 2 * math.pi); cr.set_source_rgba(1, 1, 1, 1); cr.fill(); cr.restore()


def icon(cr, name, x, y, s, col):
    """small self-drawn icons for walkthroughs / ladders"""
    cr.save(); cr.translate(x, y); cr.scale(s / 100, s / 100); cr.set_source_rgba(*rgb(col)); cr.set_line_width(9)
    cr.set_line_cap(cairo.LINE_CAP_ROUND); cr.set_line_join(cairo.LINE_JOIN_ROUND)
    if name == 'check': cr.move_to(-30, 2); cr.line_to(-8, 24); cr.line_to(32, -22); cr.stroke()
    elif name == 'card': rrect(cr, -42, -28, 84, 56, 10); cr.stroke(); cr.rectangle(-42, -12, 84, 10); cr.fill(); cr.rectangle(-30, 10, 26, 8); cr.fill()
    elif name == 'calendar': rrect(cr, -38, -32, 76, 66, 10); cr.stroke(); cr.rectangle(-38, -32, 76, 16); cr.fill(); [cr.rectangle(-26 + 20 * i, 2 + 16 * j, 10, 10) or cr.fill() for i in range(3) for j in range(2)]
    elif name == 'clock': cr.arc(0, 0, 38, 0, 2 * math.pi); cr.stroke(); cr.move_to(0, 0); cr.line_to(0, -24); cr.move_to(0, 0); cr.line_to(18, 8); cr.stroke()
    elif name == 'pin': cr.arc(0, -10, 24, 0, 2 * math.pi); cr.stroke(); cr.move_to(-18, 6); cr.line_to(0, 40); cr.line_to(18, 6); cr.stroke()
    elif name == 'boat': cr.move_to(-44, 6); cr.line_to(44, 6); cr.line_to(30, 30); cr.line_to(-30, 30); cr.close_path(); cr.fill(); rrect(cr, -26, -22, 52, 24, 6); cr.stroke()
    elif name == 'form': rrect(cr, -32, -40, 64, 80, 8); cr.stroke(); [cr.move_to(-18, -20 + 18 * i) or cr.line_to(18, -20 + 18 * i) or cr.stroke() for i in range(3)]
    elif name == 'id': rrect(cr, -44, -28, 88, 56, 10); cr.stroke(); cr.arc(-18, -2, 11, 0, 2 * math.pi); cr.fill(); cr.move_to(4, -8); cr.line_to(30, -8); cr.move_to(4, 10); cr.line_to(24, 10); cr.stroke()
    else: cr.arc(0, 0, 30, 0, 2 * math.pi); cr.fill()
    cr.restore()


# ---- the Reel ---------------------------------------------------------------------------------------------------------
class Reel:
    def __init__(self, D, fps=FPS):
        self.D = D; self.job = json.load(open(f'{D}/job.json')); self.fps = fps
        self.words = json.load(open(f'{D}/words.json'))
        self.lines_t = self._line_times()
        self.dur = round(self.words[-1][2] + self.job.get('tail', 1.4), 2)
        self.T = Clock(self.lines_t, self.dur)
        j = self.job; m = j.get('map')
        self.map = BaseMap(m['area'], m['view'], m.get('mpp', 0.85)) if m else None
        if m:
            self.route = [dict(mode=s.get('mode', 'walk'), pts=s['pts']) for s in m['route']]
            self.cam_keys = [(self.T(k[0]), (k[1], k[2], k[3])) for k in m['camera']]
            self.prog_keys = [(self.T(k[0]), k[1]) for k in m['progress']]
        self.scenes = [dict(s, t0=self.T(s['from'])) for s in j['scenes']]
        for a, b in zip(self.scenes, self.scenes[1:]): a['t1'] = b['t0']
        self.scenes[-1]['t1'] = self.dur
        self.timeline = dict(frames=[], dur=self.dur, lines=self.lines_t)

    def _line_times(self):
        out, i = [], 0
        for ln in self.job['lines']:
            n = len(ln['text'].split()); seg = self.words[i:i + n]; i += n
            out.append((seg[0][1], seg[-1][2]))
        return out

    # ----- route helpers (lon/lat space) -----
    def route_all(self):
        pts = []
        for s in self.route: pts += s['pts'] if not pts else s['pts'][1:]
        return pts

    def progress(self, t): return keyed(self.prog_keys, t)

    def traveller(self, t):
        """where the guide is: (lon,lat), heading, mode"""
        allp = self.route_all(); u = self.progress(t)
        seg, L = path_len(allp); d = u * L; acc = 0; k = 0
        for s in self.route:
            sl = path_len(s['pts'])[1]
            if d <= acc + sl or s is self.route[-1]: mode = s['mode']; break
            acc += sl
        (p, ang) = point_at(allp, u); return p, ang, mode

    def cam(self, t): return keyed(self.cam_keys, t)

    # ----- scene painters -----
    def paint_map(self, fr, t, cam=None, dim=0.0):
        cr = fr.cr; cam = cam or self.cam(t); self.map.draw(cr, cam); S = self.map.to_screen(cam)
        allp = [S(p) for p in self.route_all()]; allp_s = smooth(allp)
        stroke_path(cr, allp_s, 9, rgb(C['ink'], 0.35), dash=[2, 18], offset=-t * 40)   # whole route, faint dotted
        done = sub_path(allp_s, self.progress(t))
        stroke_path(cr, done, 20, rgb(C['card'], 0.95)); stroke_path(cr, done, 11, rgb(C['coral']))
        m = self.job['map']
        for er in m.get('extra_routes', []):   # extra walks drawn as growing lines (no traveller), e.g. one per MTR exit
            u = max(0.0, min(1.0, (t - self.T(er['from'])) / er.get('dur', 1.0)))
            if u > 0:
                ep = smooth([S(p) for p in er['pts']]); stroke_path(cr, ep, 9, rgb(C['ink'], 0.35), dash=[2, 18], offset=-t * 40)
                d = sub_path(ep, u); stroke_path(cr, d, 20, rgb(C['card'], 0.95)); stroke_path(cr, d, 11, rgb(C['coral']))
        for p in m.get('pins', []):
            if t >= self.T(p.get('from', 0)):
                x, y = S(p['at']); draw_pin(cr, x, y, C[p.get('col', 'teal')], back((t - self.T(p.get('from', 0))) / 0.45))
        (lon, lat), ang, mode = self.traveller(t); x, y = S((lon, lat))
        if mode == 'ferry':
            draw_boat(cr, x, y, ang, t, 1.3); draw_guide(cr, x, y - 2, t, walking=False, scale=0.85)
        elif mode == 'taxi':
            draw_taxi(cr, x, y, ang, t, self.job['map'].get('taxi_scale', 1.25), moving=self.progress(t + 0.05) > self.progress(t) + 1e-5)
        else: draw_guide(cr, x, y, t, walking=self.progress(t + 0.05) > self.progress(t) + 1e-5, scale=0.95)
        if dim: cr.set_source_rgba(*rgb(C['paper'], dim)); cr.paint()
        return S

    def map_labels(self, fr, t, S):
        m = self.job['map']
        for lb in m.get('labels', []):
            a0 = self.T(lb.get('from', 0)); a1 = self.T(lb['until']) if 'until' in lb else 1e9
            al = min(ease((t - a0) / 0.35), ease((a1 - t) / 0.3))
            if al <= 0: continue
            x, y = S(lb['at']); dx, dy = lb.get('off', (0, -70))
            rows = [(lb['en'], 'xb', lb.get('size', 40), C['ink'])] + ([(lb['zh'], 'zh', int(lb.get('size', 40) * 0.92), C['teal'])] if lb.get('zh') else [])
            im = card_img(rows, pad=(24, 14), radius=20, gap=2)
            fr.put(im, x + dx, y + dy, al, anchor=lb.get('anchor', 'mb'), tag='maplabel:' + lb['en'], clamp=True)
        pp = m.get('price_pin')
        if pp and t >= self.T(pp['from']) and t < self.T(pp.get('until', 'end')):
            seg = self.route[pp.get('seg', 0)]['pts']; p, _ = point_at([S(q) for q in seg], pp.get('at', 0.5))
            u = (t - self.T(pp['from'])) / 0.4; al = min(1, u * 2.5) * min(1, ease((self.T(pp.get('until', 'end')) - t) / 0.3))
            cr = fr.cr; cr.set_source_rgba(*rgb(C['ink'])); cr.arc(p[0], p[1], max(0.1, 10 * back(u)), 0, 2 * math.pi); cr.fill()
            cr.set_source_rgba(*rgb(C['gold'])); cr.arc(p[0], p[1], max(0.1, 6 * back(u)), 0, 2 * math.pi); cr.fill()
            dx, dy = pp.get('off', (0, -40)); cr.set_line_width(4); cr.set_source_rgba(*rgb(C['ink'], al))
            cr.move_to(p[0], p[1]); cr.line_to(p[0] + dx * 0.8, p[1] + dy * 0.8); cr.stroke()
            rows = [(pp['price'], 'black', pp.get('size', 66), C['ink']), (pp['en'], 'xb', 36, C['ink'])] + ([(pp['en2'], 'xb', 36, C['ink'])] if pp.get('en2') else []) + [(pp['zh'], 'zh', 36, C['ink'])]
            im = card_img(rows, width=pp.get('width', 520), pad=(28, 14), radius=26, gap=0, bg=C['gold'])
            fr.put(im, p[0] + dx, p[1] + dy, al, anchor=pp.get('anchor', 'mb'), tag='price_pin', clamp=True, scale=max(0.3, 0.85 + 0.15 * back(u)))

    def osm_credit(self, fr, alpha=1.0):
        """legible ODbL credit on every map frame; above the IG/FB bottom chrome (y < 1420) and clear of the captions"""
        key = ('osm',)
        if key not in _sc:
            f = font('semi', 24); txt = '© OpenStreetMap contributors'; tw = int(f.getlength(txt)) + 16
            im = Image.new('RGBA', (tw, 40), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
            d.text((8, 6), txt, font=f, fill=(255, 255, 255, 255), stroke_width=4, stroke_fill=(10, 20, 28, 230)); _sc[key] = im
        y = SAFE[3] if fr.t < 3.0 else 1418
        fr.put(_sc[key], SAFE[0], y, alpha, anchor='lb', tag='osm_credit', essential=False)

    def paint_panel_bg(self, fr, t, sc):
        """diagram scenes sit on the same map, softly dimmed, so the Reel keeps one world; or on plain paper"""
        if self.map: self.paint_map(fr, t, cam=sc.get('cam') and tuple(sc['cam']) or None, dim=0.30); return True
        cr = fr.cr; g = cairo.LinearGradient(0, 0, 0, H); g.add_color_stop_rgba(0, *rgb(C['paper'])); g.add_color_stop_rgba(1, *rgb((236, 230, 216))); cr.set_source(g); cr.paint()
        cr.set_source_rgba(*rgb(C['ink'], 0.05)); cr.set_line_width(2)
        off = (t * 12) % 60
        for k in range(-2, 40): cr.move_to(k * 60 - off, 0); cr.line_to(k * 60 - off - 600, H); cr.stroke()
        return False

    def panel(self, fr, x, y, w, h, al=1.0):
        cr = fr.cr; cr.save()
        cr.set_source_rgba(0.04, 0.12, 0.16, 0.12 * al); rrect(cr, x, y + 12, w, h, 36); cr.fill()
        cr.set_source_rgba(*rgb(C['card'], al)); rrect(cr, x, y, w, h, 36); cr.fill(); cr.restore()

    def scene_week(self, fr, t, sc):
        """eligibility by day: which days the price applies; off-days greyed, holidays struck"""
        self.paint_panel_bg(fr, t, sc); cr = fr.cr; u = (t - sc['t0'])
        x0, y0, w = 90, 360, 790; h = 360 + (150 if sc.get('holiday') else 0); self.panel(fr, x0, y0, w, h, ease(u / 0.25))
        days = sc['days']; n = len(days); tw = (w - 60 - (n - 1) * 12) / n
        fr.put(text_img(sc['title_en'], 'xb', 46, C['ink']), x0 + 30, y0 + 28, ease(u / 0.3), tag='week_title')
        fr.put(text_img(sc['title_zh'], 'zh', 42, C['teal']), x0 + 30, y0 + 92, ease(u / 0.3), tag='week_title_zh')
        for i, d in enumerate(days):
            k = ease((u - 0.12 - i * 0.07) / 0.3); on = d.get('on', True)
            bx = x0 + 30 + i * (tw + 12); by = y0 + 180 + (1 - k) * 40
            cr.set_source_rgba(*rgb(C['teal'] if on else C['off'], k)); rrect(cr, bx, by, tw, 150, 18); cr.fill()
            fr.put(fit_img(d['en'], 'xb', 34, C['card'] if on else C['mute'], tw), bx + tw / 2, by + 48, k, anchor='mm', tag='day')
            fr.put(text_img(d['zh'], 'zh', 40, C['card'] if on else C['mute']), bx + tw / 2, by + 106, k, anchor='mm', tag='day_zh')
        hol = sc.get('holiday')
        if hol:
            k = ease((t - self.T(hol.get('from', sc['from']))) / 0.35); by = y0 + 350
            cr.set_source_rgba(*rgb(C['off'], k)); rrect(cr, x0 + 30, by, w - 60, 120, 18); cr.fill()
            fr.put(text_img(hol['en'], 'xb', 40, C['coral']), x0 + w / 2, by + 38, k, anchor='mm', tag='hol')
            fr.put(text_img(hol['zh'], 'zh', 36, C['coral']), x0 + w / 2, by + 86, k, anchor='mm', tag='hol_zh')

    def scene_compare(self, fr, t, sc):
        """two or three options (e.g. ferry decks); the one in focus turns gold. art='ferry' stacks the rows as decks on a hull"""
        self.paint_panel_bg(fr, t, sc); cr = fr.cr; u = t - sc['t0']
        x0, y0, w = 90, sc.get('y0', 340), 790; h = 200 + len(sc['rows']) * 156 + (150 if sc.get('art') == 'ferry' else 40); self.panel(fr, x0, y0, w, h, ease(u / 0.25))
        fr.put(text_img(sc['title_en'], 'xb', 46, C['ink']), x0 + 40, y0 + 30, ease(u / 0.3), tag='cmp_title')
        fr.put(text_img(sc['title_zh'], 'zh', 42, C['teal']), x0 + 40, y0 + 94, ease(u / 0.3), tag='cmp_title_zh')
        rows = sc['rows']; rh = 150; ferry = sc.get('art') == 'ferry'; bob = math.sin(t * 2.4) * 3 if ferry else 0
        top = y0 + 200
        for i, r in enumerate(rows):
            k = ease((t - self.T(r.get('from', sc['from'])) - i * 0.1) / 0.35)
            hi = t >= self.T(r['hi_from']) if 'hi_from' in r else r.get('hi', False)
            rw = (620 + 70 * i) if ferry else w - 100; rx = x0 + (w - rw) / 2; ry = top + i * (rh + (6 if ferry else 24)) + (1 - k) * 30 + bob
            cr.set_source_rgba(*rgb(C['gold'] if hi else C['paper'], k)); rrect(cr, rx, ry, rw, rh, 22); cr.fill()
            cr.set_line_width(4); cr.set_source_rgba(*rgb(C['ink'], 0.18 * k)); rrect(cr, rx, ry, rw, rh, 22); cr.stroke()
            fr.put(fit_img(r['en'], 'xb', 42, C['ink'], rw - 330), rx + 34, ry + rh * 0.34, k, anchor='lm', tag=f'row{i}')
            fr.put(fit_img(r['zh'], 'zh', 38, C['teal'], rw - 330), rx + 34, ry + rh * 0.70, k, anchor='lm', tag='row_zh')
            fr.put(text_img(r['price'], 'black', 76, C['ink']), rx + rw - 30, ry + rh / 2, k, anchor='rm', tag='row_price')
        if ferry:
            k = ease(u / 0.4); hy = top + len(rows) * (rh + 6) + bob; cx = x0 + w / 2
            cr.set_source_rgba(*rgb(C['teal'], k)); cr.move_to(cx - 370, hy); cr.line_to(cx + 370, hy); cr.line_to(cx + 320, hy + 80); cr.line_to(cx - 320, hy + 80); cr.close_path(); cr.fill()
            cr.set_source_rgba(*rgb(C['water'], k)); rrect(cr, x0 + 30, hy + 70 - bob, w - 60, 60, 24); cr.fill()
            cr.set_source_rgba(1, 1, 1, 0.6 * k); cr.set_line_width(4)
            for j in range(6):
                xx = x0 + 70 + j * 120 + (t * 40) % 120; cr.move_to(xx, hy + 100 - bob); cr.curve_to(xx + 20, hy + 90 - bob, xx + 40, hy + 110 - bob, xx + 60, hy + 100 - bob); cr.stroke()

    def scene_days(self, fr, t, sc):
        """weather-desk tiles: 2-3 days side by side, drawn cloud/sun/rain art (animated), big high/low; hi day turns gold"""
        self.paint_panel_bg(fr, t, sc); cr = fr.cr; u = t - sc['t0']
        days = sc['days']; n = len(days); x0, y0, w = 70, sc.get('y0', 560), 830; gap = 24; tw = (w - gap * (n - 1)) / n; th = sc.get('h', 640)
        if sc.get('title_en'):
            fr.put(text_img(sc['title_en'], 'black', 48, C['ink']), x0 + 6, y0 - 92, ease(u / 0.3), tag='days_title')
            fr.put(text_img(sc['title_zh'], 'zh', 40, C['teal']), x0 + w - 6, y0 - 86, ease(u / 0.3), anchor='rt', tag='days_title_zh')
        for i, d in enumerate(days):
            a0 = self.T(d.get('from', sc['from'])); k = ease((t - a0) / 0.4)
            if k <= 0: continue
            hi = t >= self.T(d['hi_from']) if 'hi_from' in d else False
            bx = x0 + i * (tw + gap); by = y0 + (1 - k) * 50
            cr.set_source_rgba(0.04, 0.12, 0.16, 0.12 * k); rrect(cr, bx, by + 12, tw, th, 34); cr.fill()
            cr.set_source_rgba(*rgb(C['gold'] if hi else C['card'], k)); rrect(cr, bx, by, tw, th, 34); cr.fill()
            fr.put(fit_img(d['en'], 'black', 52, C['ink'], tw - 60), bx + tw / 2, by + 60, k, anchor='mm', tag=f'day{i}')
            fr.put(fit_img(d['zh'], 'zh', 40, C['teal'], tw - 60), bx + tw / 2, by + 118, k, anchor='mm', tag='day_zh')
            cx, cy = bx + tw / 2, by + 280
            if d.get('art', 'cloud') in ('cloud', 'rain'):
                drift = math.sin(t * 1.3 + i) * 10
                cr.set_source_rgba(*rgb((150, 165, 178) if d.get('art') == 'rain' else (196, 206, 214), k))
                for (ox, oy, r) in ((-62, 12, 52), (0, -22, 70), (66, 10, 54), (0, 30, 56)):
                    cr.arc(cx + ox + drift, cy + oy, r, 0, 2 * math.pi); cr.fill()
                if d.get('art') == 'rain':
                    cr.set_source_rgba(*rgb(C['water'], k)); cr.set_line_width(9); cr.set_line_cap(cairo.LINE_CAP_ROUND)
                    for j in range(5):
                        ph = ((t * 1.6 + j * 0.37) % 1.0); xx = cx - 80 + j * 40 + drift; yy = cy + 66 + ph * 36
                        cr.set_source_rgba(*rgb(C['water'], k * (1 - ph))); cr.move_to(xx, yy); cr.line_to(xx - 7, yy + 20); cr.stroke()
            fr.put(text_img(d['hi'], 'black', 96, C['ink']), bx + tw / 2, by + th - 150, k, anchor='mm', tag='row_price')
            fr.put(text_img(d['lo'], 'xb', 46, C['mute']), bx + tw / 2, by + th - 64, k, anchor='mm', tag='day_lo')

    def scene_steps(self, fr, t, sc):
        """self-drawn numbered walkthrough; each step lands on its line; the current step is gold, done steps get a tick"""
        self.paint_panel_bg(fr, t, sc); cr = fr.cr; u = t - sc['t0']
        x0, y0, w = 90, sc.get('y0', 330), 790; steps = sc['steps']; sh = 220
        ats = [self.T(s['from']) for s in steps]
        self.panel(fr, x0, y0, w, 60 + len(steps) * (sh + 20), ease((t - ats[0] + 0.1) / 0.25))
        for i, s in enumerate(steps):
            k = ease((t - ats[i]) / 0.35); cur = t >= ats[i] and (i == len(steps) - 1 or t < ats[i + 1]); done = i + 1 < len(steps) and t >= ats[i + 1]
            sy = y0 + 40 + i * (sh + 20) + (1 - k) * 30
            cr.set_source_rgba(*rgb(C['gold'] if cur else C['paper'], k)); rrect(cr, x0 + 30, sy, w - 60, sh, 26); cr.fill()
            cr.set_source_rgba(*rgb(C['teal'] if not done else C['ink'], k)); cr.arc(x0 + 100, sy + sh / 2, 44, 0, 2 * math.pi); cr.fill()
            if done: icon(cr, 'check', x0 + 100, sy + sh / 2, 60, C['card'])
            else: fr.put(text_img(str(i + 1), 'black', 50, C['card']), x0 + 100, sy + sh / 2, k, anchor='mm', tag='stepnum')
            if s.get('icon'): icon(cr, s['icon'], x0 + w - 110, sy + sh / 2, 90, C['ink'] if cur else C['mute'])
            tw = w - 200 - (130 if s.get('icon') else 20)
            fr.put(fit_img(s['en'], 'xb', 40, C['ink'], tw), x0 + 170, sy + sh * 0.36, k, anchor='lm', tag='step')
            fr.put(fit_img(s['zh'], 'zh', 38, C['teal'], tw), x0 + 170, sy + sh * 0.68, k, anchor='lm', tag='step_zh')

    def scene_ladder(self, fr, t, sc):
        """2-3 prices as rising bars, cheapest first; numbers count up as they land"""
        self.paint_panel_bg(fr, t, sc); cr = fr.cr; u = t - sc['t0']
        items = sc['items']; x0, y0, w, h = 90, 330, 790, 840; self.panel(fr, x0, y0, w, h, ease((t - self.T(items[0]['from']) + 0.1) / 0.25))
        mxp = max(i['value'] for i in items); n = len(items); bw = (w - 120 - (n - 1) * 40) / n
        for i, it in enumerate(items):
            a0 = self.T(it['from']); k = eout((t - a0) / 0.6)
            bh = 420 * it['value'] / mxp * k; bx = x0 + 60 + i * (bw + 40); by = y0 + 560
            cr.set_source_rgba(*rgb(C['gold'] if it.get('hi') else C['teal'], min(1, k * 3))); rrect(cr, bx, by - bh, bw, max(1, bh), 20); cr.fill()
            if k > 0.02:
                v = it['value'] * k; s = it.get('label') if k >= 0.999 else f"HK${v:.0f}"
                fr.put(text_img(s or f"HK${it['value']:g}", 'black', 58, C['ink']), bx + bw / 2, by - bh - 20, min(1, k * 3), anchor='mb', tag='ladder_price')
                fr.put(fit_img(it['en'], 'xb', 34, C['ink'], bw - 8), bx + bw / 2, by + 50, min(1, k * 3), anchor='mm', tag='ladder_en')
                fr.put(fit_img(it['zh'], 'zh', 32, C['teal'], bw - 8), bx + bw / 2, by + 100, min(1, k * 3), anchor='mm', tag='ladder_zh')
                if it.get('icon'): icon(cr, it['icon'], bx + bw / 2, by + 180, 70, C['mute'])

    # ----- plate: our own pre-rendered animation (e.g. Blender), retimed to the voice; never footage -----
    def plate_frame(self, t):
        pl = self.job['plate']; keys = [(self.T(k[0]), float(k[1])) for k in pl['keys']]; nmax = pl.get('frames', 1) - 1
        if t <= keys[0][0]: f = keys[0][1]
        else:
            f = keys[-1][1]
            for (t0, v0), (t1, v1) in zip(keys, keys[1:]):
                if t <= t1: f = v0 + (v1 - v0) * (t - t0) / max(1e-6, t1 - t0); break
        f = max(0.0, min(float(nmax), f)); a = int(math.floor(f)); u = f - a
        cache = self.__dict__.setdefault('_plate_cache', {})
        def load(n):
            if n not in cache:
                if len(cache) > 6: cache.pop(next(iter(cache)))
                im = Image.open(f"{self.D}/{pl['file'] % n}").convert('RGB')
                if im.size != (W, H): im = im.resize((W, H), Image.LANCZOS)
                g = pl.get('grade')                          # warm-below / cool-above grade (lamp-lit stalls, cool sky)
                if g:
                    a = np.asarray(im).astype(np.float32) / 255; yy = np.linspace(0, 1, H)[:, None, None]
                    w = np.clip((yy - g.get('from', 0.3)) / (g.get('full', 0.65) - g.get('from', 0.3)), 0, 1) ** 1.2; k = g.get('k', 0.45)
                    amb = np.array([1.0, 0.70, 0.36], np.float32); lum = a.mean(2, keepdims=True)
                    a = a * (1 - w * k) + a * amb * 1.75 * w * k + w * 0.10 * amb * lum ** 0.6
                    a = a * ((1 - w) * np.array([0.92, 0.98, 1.08], np.float32) + w)
                    im = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8))
                cache[n] = im
            return cache[n]
        im = load(a)
        if u > 0.05 and a + 1 <= nmax: im = Image.blend(im, load(a + 1), u)
        return im

    def scene_plate(self, fr, t, sc):
        im = self.plate_frame(t).convert('RGBA'); a = np.array(im)[:, :, [2, 1, 0, 3]].copy()
        s2 = cairo.ImageSurface.create_for_data(a, cairo.FORMAT_ARGB32, W, H)
        fr.cr.set_source_surface(s2, 0, 0); fr.cr.paint(); del s2
        j = self.job; pl = j['plate']
        pi = j.get('pill')                                   # the hook's second state: price pill (qa proof tag 'price_pin')
        cv = j.get('caveat', {}); cvim = None
        if cv.get('text') and t >= self.T(cv['at']) - 0.3 and t < self.T(cv.get('until', 3.0)) + 0.3:
            al = min(ease((t - self.T(cv['at'])) / 0.25), ease((self.T(cv.get('until', 3.0)) - t) / 0.25))
            cvim = card_img([(cv['text'], 'xb', 40, C['ink'])] + ([(cv['zh'], 'zh', 36, C['teal'])] if cv.get('zh') else []), pad=(30, 16), radius=24, gap=2, accent=C['gold'])
            if al > 0: fr.put(cvim, SAFE[0] - 24, SAFE[3] + 24, al, anchor='lb', tag=cv.get('tag', 'caveat'))
        if pi and self.T(pi['from']) - 0.01 <= t < self.T(pi['until']) + 0.3:
            u = (t - self.T(pi['from'])) / 0.35; al = min(1, max(0, u) * 2.5) * min(1, ease((self.T(pi['until']) - t) / 0.3))
            im = card_img([(pi['en'], 'black', 96, C['ink']), (pi['zh'], 'zh', 46, C['ink'])], pad=(40, 10), radius=30, gap=0, bg=C['gold'], align='center')
            yb = SAFE[3] + 24 - (cvim.info['inner'][3] + 30 if cvim else 0)
            if al > 0: fr.put(im, SAFE[0] - 24, yb, al, anchor='lb', tag='price_pin', scale=max(0.3, 0.85 + 0.15 * back(u)))
        for tg in pl.get('tags', []):
            a0, a1 = self.T(tg['from']), self.T(tg['until']); al = min(ease((t - a0) / 0.25), ease((a1 - t) / 0.25))
            if al <= 0: continue
            x, y = tg.get('pos', (SAFE[0], 300)); anc = tg.get('anchor', 'lt')
            if tg.get('kind') == 'tag':
                im = paper_tag(tg['price'], tg['en'], tg['zh']); sw = 0.03 * math.sin((t - a0) * 2.4) * (1 - ease((t - a0) / 3))
                k = back((t - a0) / 0.4)
                fr.put(im, x, y - (1 - min(1, k)) * 30, al, anchor=anc, tag='pricetag:' + tg['en'], scale=max(0.3, 0.9 + 0.1 * min(1.2, k)))
            else:
                im = card_img([(tg['en'], 'xb', 44, C['ink']), (tg['zh'], 'zh', 40, C['teal'])], pad=(28, 14), radius=24, gap=2, accent=C['gold'])
                fr.put(im, x, y + (1 - al) * -16, al, anchor=anc, tag='chip:' + tg['en'])

    def scene_summary(self, fr, t, sc):
        """the saveable end card: the whole route on the map above + a compact fact table below (all inside the safe zone)"""
        cr = fr.cr; u = t - sc['t0']; k = ease(u / 0.4)
        if self.map:
            c0 = tuple(sc['cam']); c1 = (c0[0], c0[1], c0[2] * 0.97)          # slow push-in so the end card never freezes
            S = self.paint_map(fr, t, cam=keyed([(sc['t0'], c0), (self.dur, c1)], t)); self.map_labels(fr, t, S)
        else: self.paint_panel_bg(fr, t, sc)
        big = sc.get('big', False); x0, w = 70, 830; rows = sc['rows']; rh = 138 if big else 112; h = 92 + len(rows) * rh + (56 if sc.get('foot') else 16)
        y = (1270 - h if self.map else 380) + (1 - k) * 60
        cr.set_source_rgba(0.04, 0.12, 0.16, 0.14 * k); rrect(cr, x0, y + 12, w, h, 34); cr.fill()
        cr.set_source_rgba(*rgb(C['card'], k)); rrect(cr, x0, y, w, h, 34); cr.fill()
        cr.set_source_rgba(*rgb(C['gold'], k)); rrect(cr, x0, y, 14, h, 7); cr.fill()
        fr.put(fit_img(sc['title_en'], 'black', 46, C['ink'], 470), x0 + 40, y + 20, k, tag='sum_title')
        fr.put(fit_img(sc['title_zh'], 'zh', 42, C['teal'], 300), x0 + w - 36, y + 22, k, anchor='rt', tag='sum_title_zh')
        for i, r in enumerate(rows):
            ry = y + 92 + i * rh; kk = ease((u - 0.15 - i * 0.12) / 0.35)
            cr.set_source_rgba(*rgb(C['ink'], 0.1 * kk)); cr.rectangle(x0 + 40, ry - 4, w - 76, 2); cr.fill()
            vi = fit_img(r.get('value', ''), 'black', 60 if big else 50, C['ink'], 340 if big else 330) if r.get('value') else None
            lw = w - 76 - (vi.width + 16 if vi else 0)
            fr.put(fit_img(r['en'], 'xb', 44 if big else 38, C['ink'], lw), x0 + 40, ry + (8 if big else 6), kk, tag='sum_row')
            fr.put(fit_img(r['zh'], 'zh', 38 if big else 34, C['teal'], lw), x0 + 40, ry + (74 if big else 56), kk, tag='sum_row_zh')
            if vi: fr.put(vi, x0 + w - 30, ry + rh / 2, kk, anchor='rm', tag='sum_val')
        if sc.get('foot'): fr.put(fit_img(sc['foot'], 'semi', 28, C['mute'], w - 76), x0 + 40, y + h - 50, k, tag='sum_foot')

    # ----- overlays -----
    def headline(self, fr, t):
        hd = self.job['headline']; t1 = self.T(hd.get('until', 2.5))
        al = 1.0 if t < t1 else 1 - ease((t - t1) / 0.3)
        if al <= 0: return
        rows = [(ln, 'black', hd.get('size_en', 76), C['ink']) for ln in hd['en'].split('\n')] + [(hd['zh'], 'zh', hd.get('size_zh', 64), C['teal'])]
        im = card_img(rows, width=hd.get('width', 800), pad=(40, 26), radius=34, gap=6, accent=C['gold'])
        fr.put(im, (SAFE[0] + SAFE[2]) / 2, SAFE[1] + 20 - (1 - al) * 40, al, anchor='mt', tag='headline')

    def fact_labels(self, fr, t):
        """at most one compact pill, upper-left (visual_rules: x 70, y ~290, max width 560)"""
        for lb in self.job.get('labels', []):
            a0, a1 = self.T(lb['from']), self.T(lb['until'])
            al = min(ease((t - a0) / 0.25), ease((a1 - t) / 0.25))
            if al <= 0: continue
            rows = [(lb['en'], 'black', lb.get('size', 52), C['ink']), (lb['zh'], 'zh', int(lb.get('size', 52) * 0.85), C['teal'])]
            im = card_img(rows, width=None, pad=(30, 14), radius=24, gap=0, accent=C[lb.get('accent', 'gold')])
            fr.put(im, SAFE[0] - 24, lb.get('y', 280) - 24 + (1 - al) * -20, al, anchor='lt', tag='label:' + lb['en'])

    def captions(self, fr, t):
        """accessibility captions: mixed-case English (white) over Traditional Chinese (yellow), stroked, no box,
        one 2-line pair centred at x ~474, y 1295-1380 (above the IG/FB bottom chrome). Starts after the hook headline."""
        c0 = self.T(self.job.get('captions_from', 'L2'))
        if t < c0: return
        for ph in self.phrases:
            if ph[1] - 0.05 <= t < ph[2] + 0.15 and ph[2] >= c0:
                key = ('cap', ph[0], ph[3])
                if key not in _sc:
                    fe, fz = font('xb', self.job.get('cap_en', 40)), font('zh', self.job.get('cap_zh', 42))   # optional per-Reel caption size
                    while fe.getlength(ph[0]) > 780 and fe.size > 30: fe = font('xb', fe.size - 2)
                    while fz.getlength(ph[3]) > 780 and fz.size > 32: fz = font('zh', fz.size - 2)
                    im = Image.new('RGBA', (860, 110), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
                    for (txt, f, col, y, sw) in ((ph[0], fe, (255, 255, 255), 24, 7), (ph[3], fz, getattr(self, 'CAP_ZH', YEL), 80, 8)):
                        if not txt: continue
                        d.text((432, y + 4), txt, font=f, fill=(0, 0, 0, 120), anchor='mm', stroke_width=sw, stroke_fill=(0, 0, 0, 120))
                        d.text((430, y), txt, font=f, fill=col + (255,), anchor='mm', stroke_width=sw, stroke_fill=(11, 14, 20, 245))
                    bb = im.getbbox(); im.info['inner'] = (bb[0], bb[1], bb[2] - bb[0], bb[3] - bb[1]); _sc[key] = im
                fr.put(_sc[key], 474, 1266, 1.0, anchor='mt', tag='caption'); return

    def build_phrases(self):
        """caption chunks of at most 8 English words (split long lines once, at a comma or near the middle, never after a
        small joining word); each chunk carries its line's Traditional Chinese (job lines[i].zh)"""
        SMALL = {'a', 'an', 'the', 'of', 'or', 'and', 'on', 'at', 'for', 'to', 'in', 'is', 'your', 'about'}
        ws = []; i = 0
        for ln in self.job['lines']:
            toks = ln['text'].split(); seg = self.words[i:i + len(toks)]; i += len(toks); zh = ln.get('zh', '')
            cuts = [len(toks)]
            if len(toks) > 8:
                best = min(range(3, len(toks) - 2), key=lambda k: abs(k - len(toks) / 2) - (3 if toks[k - 1][-1] in ',;' else 0) + (4 if toks[k - 1].lower() in SMALL else 0))
                cuts = [best, len(toks)]
            a0 = 0
            for c in cuts:
                ws.append((' '.join(toks[a0:c]), seg[a0][1], seg[c - 1][2], zh)); a0 = c
        self.phrases = ws

    def frame(self, t):
        fr = Frame(t); sc = next(s for s in self.scenes if s['t0'] <= t < s['t1'] + 1e-6) if t < self.dur else self.scenes[-1]
        kind = sc['kind']
        if kind == 'map': S = self.paint_map(fr, t); self.map_labels(fr, t, S)
        else: getattr(self, 'scene_' + kind)(fr, t, sc)
        # cross-dissolve the first 0.22 s of every scene from the previous one (cheap: re-render previous at same t)
        if self.map and kind in ('map', 'summary'): self.osm_credit(fr)
        self.headline(fr, t); self.fact_labels(fr, t); self.captions(fr, t)
        im = fr.image(); i0 = self.scenes.index(sc)
        if i0 > 0 and t - sc['t0'] < 0.22:
            prev = Reel.frame_scene(self, self.scenes[i0 - 1], t)
            im = Image.blend(prev, im, ease((t - sc['t0']) / 0.22))
        self.timeline['frames'].append(dict(t=round(t, 3), scene=kind, boxes=fr.boxes))
        return im

    def frame_scene(self, sc, t):
        fr = Frame(t); kind = sc['kind']
        if kind == 'map': S = self.paint_map(fr, t); self.map_labels(fr, t, S)
        else: getattr(self, 'scene_' + kind)(fr, t, sc)
        if self.map and kind in ('map', 'summary'): self.osm_credit(fr)
        self.fact_labels(fr, t); self.captions(fr, t)
        return fr.image()

    def render(self, draft=False):
        self.build_phrases(); fps = 15 if draft else self.fps; N = int(round(self.dur * fps))
        out = f'{self.D}/video_only.mp4'
        p = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(fps), '-i', '-',
                              '-c:v', 'libx264', '-preset', 'veryfast' if draft else 'medium', '-crf', '28' if draft else '18', '-pix_fmt', 'yuv420p',
                              '-threads', '1', '-r', str(fps), out], stdin=subprocess.PIPE)
        t0 = time.time()
        for n in range(N):
            p.stdin.write(self.frame(n / fps).tobytes())
            if n % 60 == 0: print(f'frame {n}/{N}  {time.time() - t0:.0f}s', flush=True)
        p.stdin.close(); p.wait()
        json.dump(self.timeline, open(f'{self.D}/timeline.json', 'w'))
        self.mix()

    def stills(self, ts):
        self.build_phrases(); os.makedirs(f'{self.D}/stills', exist_ok=True)
        for t in ts: self.frame(t).save(f'{self.D}/stills/t{t:05.2f}.png')
        json.dump(self.timeline, open(f'{self.D}/stills/timeline.json', 'w'))

    def foley(self):
        """quiet synthesised micro-foley (soft paper tick on pill/scene changes, a two-note chime on the end card).
        Never a whoosh, riser or boing. Returns event list; writes <reel>/foley.wav."""
        if not self.job.get('foley', True): return []
        sr = 48000; n = int(self.dur * sr); a = np.zeros(n); rng = np.random.default_rng(7); ev = []
        pp = (self.job.get('map') or {}).get('price_pin')
        ticks = [self.T(pp['from'])] if pp else []
        ticks += [sc['t0'] for sc in self.scenes[1:] if sc['kind'] != 'summary'] + [self.T(lb['from']) for lb in self.job.get('labels', [])]
        if hasattr(self, 'tick_times'): ticks = self.tick_times()             # theme layers name their own switch-on moments
        for t0 in ticks:
            i = int(t0 * sr); L = int(0.03 * sr)
            if i + L < n:
                x = np.arange(L) / sr; nz = rng.normal(0, 1, L); nz = np.convolve(nz, np.ones(6) / 6, 'same')
                a[i:i + L] += (nz * 0.5 + np.sin(2 * np.pi * 2400 * x) * 0.5) * np.exp(-x * 160) * 0.05; ev.append(('tick', round(t0, 2)))
        for sc in self.scenes:
            if sc['kind'] == 'summary':
                for k, f in enumerate((1318.5, 1760.0)):
                    i = int((sc['t0'] + 0.1 + k * 0.14) * sr); L = int(0.9 * sr)
                    if i + L < n: x = np.arange(L) / sr; a[i:i + L] += (np.sin(2 * np.pi * f * x) + 0.3 * np.sin(4 * np.pi * f * x)) * np.exp(-x * 5) * (1 - np.exp(-x * 400)) * 0.035
                ev.append(('chime', round(sc['t0'], 2)))
        if self.job.get('plate'): a += self.plate_foley(n, sr, rng, ev)
        a.astype(np.float32).tofile(f'{self.D}/foley.raw')
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'f32le', '-ar', str(sr), '-ac', '1', '-i', f'{self.D}/foley.raw', f'{self.D}/foley.wav'], check=True)
        os.remove(f'{self.D}/foley.raw'); self.timeline['foley'] = ev; return ev

    def plate_foley(self, n, sr, rng, ev):
        """street bed under the plate scenes, all synthesised: crowd murmur (band-passed noise, slow swell), wok/grill sizzle
        under job plate.sizzle [t0, t1], a faint wooden clapper under plate.clapper [t0, t1]. No music, no whoosh."""
        pl = self.job['plate']; out = np.zeros(n); tt = np.arange(n) / sr
        def band(x, lo, hi):
            X = np.fft.rfft(x); f = np.fft.rfftfreq(len(x), 1 / sr); X[(f < lo) | (f > hi)] = 0; return np.fft.irfft(X, len(x))
        end = next((sc['t1'] for sc in self.scenes if sc['kind'] == 'plate'), self.dur)
        env = np.clip(tt / 0.4, 0, 1) * np.clip((end + 0.6 - tt) / 0.8, 0, 1)
        mur = band(rng.normal(0, 1, n), 180, 900); mur /= np.abs(mur).max() + 1e-9
        sw = 1 + 0.35 * np.sin(2 * np.pi * 0.23 * tt) + 0.2 * np.sin(2 * np.pi * 0.61 * tt + 1)
        out += mur * sw * env * 0.05; ev.append(('murmur', 0.0))
        if pl.get('sizzle'):
            s0, s1 = self.T(pl['sizzle'][0]), self.T(pl['sizzle'][1])
            se = np.clip((tt - s0) / 0.5, 0, 1) * np.clip((s1 - tt) / 0.6, 0, 1)
            hz = band(rng.normal(0, 1, n), 2500, 9000); hz /= np.abs(hz).max() + 1e-9
            cr = (rng.random(n) < 300 / sr) * rng.normal(0, 1, n); cr = band(cr, 1500, 8000); cr /= np.abs(cr).max() + 1e-9
            out += (hz * 0.025 + cr * 0.05) * se; ev.append(('sizzle', round(s0, 2)))
        if pl.get('clapper'):
            c0, c1 = self.T(pl['clapper'][0]), self.T(pl['clapper'][1]); k = c0 + 0.2; L = int(0.12 * sr); x = np.arange(L) / sr
            while k < c1:
                for dt in (0.0, 0.16):
                    i = int((k + dt) * sr)
                    if i + L < n: out[i:i + L] += (np.sin(2 * np.pi * 1050 * x) + 0.5 * np.sin(2 * np.pi * 1730 * x)) * np.exp(-x * 55) * 0.03
                ev.append(('clapper', round(k, 2))); k += 0.95
        return out

    def mix(self):
        """voice (+ optional licensed bed from the kit, ducked) -> loudness -14 LUFS / -1.5 dBTP -> mux"""
        D = self.D; mus = self.job.get('music'); out = f"{D}/{self.job['out']}"
        ft = self.foley()
        if mus:
            fc = (f"[1:a]aresample=48000,apad[v];[2:a]aresample=48000,aloop=loop=-1:size=2e9,volume={mus.get('gain', 0.12)},afade=t=out:st={self.dur - 0.8}:d=0.8[m];"
                  "[m][v]sidechaincompress=threshold=0.03:ratio=6:attack=20:release=300[md];[v][md]amix=inputs=2:normalize=0[a0]")
            ins = ['-i', f'{D}/vo.wav', '-i', mus['file']]
        else:
            fc = '[1:a]aresample=48000,apad[a0]'; ins = ['-i', f'{D}/vo.wav']
        if ft:
            ins += ['-i', f'{D}/foley.wav']; fc += f';[a0][{len(ins) // 2}:a]amix=inputs=2:duration=first:normalize=0[a0x]'
        a_last = '[a0x]' if ft else '[a0]'
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', f'{D}/video_only.mp4', *ins, '-filter_complex', fc + ';' + a_last + 'atrim=0:' + str(self.dur) + '[a1]',
                        '-map', '[a1]', '-ar', '48000', '-ac', '2', f'{D}/mix.wav'], check=True)
        st = subprocess.run(['ffmpeg', '-hide_banner', '-i', f'{D}/mix.wav', '-af', 'loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json', '-f', 'null', '-'], capture_output=True, text=True).stderr
        js = json.loads(st[st.rindex('{'):st.rindex('}') + 1])
        ln = (f"loudnorm=I=-14:TP=-1.5:LRA=11:measured_I={js['input_i']}:measured_TP={js['input_tp']}:measured_LRA={js['input_lra']}:"
              f"measured_thresh={js['input_thresh']}:offset={js['target_offset']}:linear=true")
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', f'{D}/video_only.mp4', '-i', f'{D}/mix.wav', '-af', ln + ',aresample=48000', '-map', '0:v', '-map', '1:a',
                        '-c:v', 'copy', '-c:a', 'aac', '-b:a', '192k', '-t', str(self.dur), '-movflags', '+faststart', out], check=True)
        print('wrote', out, self.dur, 's')


# ---- voice ------------------------------------------------------------------------------------------------------------
def voice(D):
    job = json.load(open(f'{D}/job.json')); v = job.get('voice', {})
    VOICE, RATE = v.get('voice', 'en-US-AvaNeural'), v.get('rate', '+4%')
    say = ' '.join(ln.get('say', ln['text']) for ln in job['lines'])
    open(f'{D}/vo.txt', 'w').write(' '.join(ln['text'] for ln in job['lines']) + '\n')
    for i in range(6):
        try:
            async def go():
                c = edge_tts.Communicate(say, VOICE, rate=RATE, boundary='WordBoundary'); wb = []
                with open(f'{D}/vo.mp3', 'wb') as f:
                    async for ch in c.stream():
                        if ch['type'] == 'audio': f.write(ch['data'])
                        elif ch['type'] == 'WordBoundary': wb.append([ch['text'], ch['offset'] / 1e7, (ch['offset'] + ch['duration']) / 1e7])
                return wb
            import edge_tts; wb = asyncio.run(go())
            if os.path.getsize(f'{D}/vo.mp3') > 10000 and wb: break
        except Exception as e: print('tts retry', i + 1, type(e).__name__, flush=True)
        time.sleep(4 * (i + 1))
    else: sys.exit('voice service gave no audio')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', f'{D}/vo.mp3', '-ar', '48000', '-ac', '1', f'{D}/vo_raw.wav'], check=True)
    a = np.frombuffer(subprocess.run(['ffmpeg', '-v', 'error', '-i', f'{D}/vo_raw.wav', '-f', 'f32le', '-'], capture_output=True).stdout, np.float32)
    lead = int(np.argmax(np.abs(a) > 0.01)); keep = int(0.03 * 48000); cut = max(0, lead - keep)
    a = a[cut:]; a.astype(np.float32).tofile(f'{D}/vo.raw')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'f32le', '-ar', '48000', '-ac', '1', '-i', f'{D}/vo.raw', f'{D}/vo.wav'], check=True); os.remove(f'{D}/vo.raw')
    shift = (lead / 48000 - wb[0][1]) - cut / 48000                           # mp3 decoder delay minus our trim
    # TTS boundaries are per spoken token; map them back to the caption words of each line (say may differ from text)
    texts = ' '.join(ln['text'] for ln in job['lines']).split(); spoken = [[w, round(s + shift, 3), round(e + shift, 3)] for w, s, e in wb if re.search(r'\w', w)]
    words = align(texts, spoken)
    gp = v.get('gaps')                                   # optional: shorten silent pauses between lines (silence only, words untouched)
    if gp: words = trim_gaps(D, job, words, gp)
    json.dump(words, open(f'{D}/words.json', 'w')); print('voice ok', VOICE, RATE, 'words', len(words), 'end', words[-1][2])


def trim_gaps(D, job, words, gp):
    """gp = {"L4": 0.40, "default": 0.30}: the pause AFTER line Ln is cut to at most that many seconds, taken from the
    middle of the silence (checked to be quiet) so no word edge is touched"""
    a = np.frombuffer(subprocess.run(['ffmpeg', '-v', 'error', '-i', f'{D}/vo.wav', '-f', 'f32le', '-'], capture_output=True).stdout, np.float32).copy()
    sr = 48000; ends, i = [], 0
    for ln in job['lines']: i += len(ln['text'].split()); ends.append(i)
    cuts = []
    for k, e in enumerate(ends[:-1]):
        g0, g1 = words[e - 1][2], words[e][1]; want = gp.get(f'L{k + 1}', gp.get('default', 99))
        if g1 - g0 > want + 0.01:
            rm = g1 - g0 - want; m = (g0 + g1) / 2; c0, c1 = int((m - rm / 2) * sr), int((m + rm / 2) * sr)
            if np.sqrt(np.mean(a[c0:c1] ** 2)) < 0.01: cuts.append((c0, c1, rm, g1))
            else: print('gap after L%d not silent, kept' % (k + 1))
    for c0, c1, rm, g1 in reversed(cuts):
        x = np.arange(240) / 240.0; a[c0 - 240:c0] *= 1 - x; a[c1:c1 + 240] *= x   # 5 ms fades at the seam
        a = np.concatenate([a[:c0], a[c1:]])
        words = [[w, round(s0 - rm, 3) if s0 >= g1 - 1e-6 else s0, round(e0 - rm, 3) if s0 >= g1 - 1e-6 else e0] for w, s0, e0 in words]
    a.tofile(f'{D}/vo.raw')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'f32le', '-ar', '48000', '-ac', '1', '-i', f'{D}/vo.raw', f'{D}/vo.wav'], check=True); os.remove(f'{D}/vo.raw')
    print('gaps trimmed', len(cuts), 'saved', round(sum(c[2] for c in cuts), 2), 's'); return words


def align(texts, spoken):
    import difflib
    norm = lambda s: re.sub(r'[^a-z0-9]', '', s.lower())
    a = [norm(x) for x in texts]; b = [norm(x[0]) for x in spoken]; t = [None] * len(texts)
    for blk in difflib.SequenceMatcher(None, a, b, autojunk=False).get_matching_blocks():
        for k in range(blk.size): t[blk.a + k] = (spoken[blk.b + k][1], spoken[blk.b + k][2])
    i = 0
    while i < len(texts):
        if t[i] is None:
            j = i
            while j < len(texts) and t[j] is None: j += 1
            t0 = t[i - 1][1] if i else 0.0; t1 = t[j][0] if j < len(texts) else spoken[-1][2]
            st = (t1 - t0) / (j - i + 1)
            for k in range(i, j): t[k] = (round(t0 + st * (k - i + 1) - st * 0.5, 3), round(t0 + st * (k - i + 1), 3))
            i = j
        else: i += 1
    return [[w, s, e] for w, (s, e) in zip(texts, t)]


if __name__ == '__main__':
    D = os.path.abspath(sys.argv[1]); cmd = sys.argv[2] if len(sys.argv) > 2 else 'all'
    if cmd in ('voice',) or (cmd == 'all' and not os.path.exists(f'{D}/words.json')): voice(D)
    look = json.load(open(f'{D}/job.json')).get('look', 'map_day')
    if look == 'map_day': R = Reel                                  # the v5 picture, unchanged
    else:
        sys.path.insert(0, T5); import looks; R = looks.FORMATS.get((look, json.load(open(f'{D}/job.json')).get('format')), looks.REEL[look])   # theme layer (neon / menu)
    if cmd == 'stills': R(D).stills([float(x) for x in sys.argv[3].split(',')])
    if cmd in ('render', 'all'): R(D).render(draft='--draft' in sys.argv)
    if cmd == 'all':
        subprocess.run([sys.executable, f'{T5}/sheets.py', D], check=True)
        subprocess.run([sys.executable, f'{T5}/qa.py', D])
