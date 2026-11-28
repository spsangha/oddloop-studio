#!/usr/bin/env python3
"""HK Unlocked LOOKS v6 (2026-11-24): theme layer on top of build.py.

job.json "look":  "map_day" (default, = v5 picture, handled by build.Reel itself)
                  "neon"    Hong Kong street of hanging neon signboards at night + glowing night map
                  "menu"    cha chaan teng tiled wall, paper menu strips, placard with red price, framed map card, the bill
Every scene kind (map, week, compare, steps, ladder, days, summary) renders in every look; "mapcard" is new (menu world;
in the other looks it falls back to a normal map scene). Everything drawn in code; no photos, no AI imagery.
"""
import math, re, json
import numpy as np
import cairo
from PIL import Image, ImageDraw, ImageFilter, ImageChops
import build as B
from build import has_zh, W, H, SAFE, STAGE, rgb, ease, eout, back, font, keyed, smooth, sub_path, point_at, path_len, rrect, stroke_path

GOLD = (255, 200, 61)                                 # brand gold #FFC83D in every frame


# ---- shared helpers ------------------------------------------------------------------------------------------------
_cs = {}; _keep = []
def pil2cairo(im):
    """PIL RGBA -> cairo ARGB32 (premultiplied)"""
    a = np.asarray(im.convert('RGBA')).astype(np.float32); al = a[..., 3:4] / 255.0
    pm = np.concatenate([a[..., :3] * al, a[..., 3:4]], -1).astype(np.uint8)[..., [2, 1, 0, 3]]
    h, w = pm.shape[:2]; st = cairo.ImageSurface.format_stride_for_width(cairo.FORMAT_ARGB32, w)
    buf = np.zeros((h, st), np.uint8); buf[:, :w * 4] = pm.reshape(h, w * 4)
    s = cairo.ImageSurface.create_for_data(memoryview(buf), cairo.FORMAT_ARGB32, w, h, st); _keep.append(buf); return s


def paint(cr, surf, x, y, alpha=1.0, angle=0.0, pivot=(0, 0), scale=(1.0, 1.0)):
    """paint surf so that its pivot point lands on (x, y), rotated by angle (rad) and scaled"""
    if alpha <= 0.005: return
    cr.save(); cr.translate(x, y); cr.rotate(angle); cr.scale(*scale); cr.translate(-pivot[0], -pivot[1])
    cr.set_source_surface(surf, 0, 0); cr.get_source().set_filter(cairo.FILTER_GOOD); cr.paint_with_alpha(min(1.0, alpha)); cr.restore()


def tok_split(s):
    """'Cross the {HK$4 deal}' -> [('Cross',0),('the',0),('HK$4',1),('deal',1)]"""
    out = []
    for part in re.split(r'(\{[^}]*\})', s.replace('\n', ' ')):
        if not part.strip(): continue
        hi = part.startswith('{')
        out += [(w, hi) for w in part.strip('{}').split()]
    return out


def rich_img(toks, kind, size, col, hi_col, stroke=0):
    """one line of words, highlighted words in hi_col (coloured letters, no marker)"""
    f = font(kind, size); asc, desc = f.getmetrics(); pad = int(size * 0.12) + stroke
    sp = f.getlength(' '); ws = [f.getlength(w) for w, _ in toks]
    tw = int(sum(ws) + sp * (len(toks) - 1)) + 2 * pad + 2; th = asc + desc + 2 * pad
    im = Image.new('RGBA', (tw, th), (0, 0, 0, 0)); d = ImageDraw.Draw(im); x = pad
    for (w, hi), wd in zip(toks, ws):
        d.text((x, pad), w, font=f, fill=((hi if isinstance(hi, tuple) else hi_col) if hi else col) + (255,)); x += wd + sp
    return im


def wrap_fit(s, kind, maxw, sizes, maxlines=3):
    """largest size whose greedy word wrap fits maxw in <= maxlines lines with no word split -> (size, [toks per line])"""
    toks = tok_split(s)
    for sz in sizes:
        f = font(kind, sz); sp = f.getlength(' '); lines = [[]]; cw = 0
        ok = True
        for w, hi in toks:
            wl = f.getlength(w)
            if wl > maxw: ok = False; break
            if lines[-1] and cw + sp + wl > maxw: lines.append([]); cw = 0
            cw += (sp if lines[-1] else 0) + wl; lines[-1].append((w, hi))
        if ok and len(lines) <= maxlines: return sz, lines
    return sizes[-1], lines


def stack(ims, gap=0, align='l'):
    w = max(i.width for i in ims); h = sum(i.height for i in ims) + gap * (len(ims) - 1)
    out = Image.new('RGBA', (w, h), (0, 0, 0, 0)); y = 0
    for i in ims:
        out.alpha_composite(i, ((w - i.width) // 2 if align == 'm' else 0, y)); y += i.height + gap
    return out


def flick_on(u, fps=30):
    """off-on-off-on within 5 frames then steady (u = seconds since switch-on)"""
    if u < 0: return 0.0
    n = int(u * fps + 1e-6)
    return (1.0, 0.35, 1.0, 0.35, 1.0)[n] if n < 5 else 1.0     # dips, never fully dark (cards stay legible)


def mixc(a, b, k): return tuple(int(round(x + (y - x) * k)) for x, y in zip(a, b))


# =====================================================================================================================
# NIGHT MAP (neon) - same OSM vectors, night palette, water left transparent so the shimmer can move under the land
# =====================================================================================================================
NC = dict(water=(7, 12, 24), shimmer=(16, 30, 56), land=(20, 31, 52), build=(30, 45, 70), park=(20, 48, 39),     # land luma ~30 (lead 24 Nov)
          minor=(41, 58, 91), major=(61, 85, 131), rail=(74, 92, 134), pier=(30, 44, 70),
          text=(244, 247, 255), pink=(255, 79, 163), cyan=(53, 224, 255), gold=GOLD, green=(92, 255, 143),
          face=(11, 18, 32), ink=(11, 16, 32), zh=(186, 238, 255), mute=(132, 146, 176), glass=(10, 16, 30))


class NightMap(B.BaseMap):
    def __init__(self, area, view, mpp=0.85):
        import os
        self.data = json.load(open(f'{B.T5}/osm/cache/{area}.json'))
        w, s, e, n = view; self.x0, self.y0 = B.mx(w), B.my(n); self.x1, self.y1 = B.mx(e), B.my(s)
        self.ppu = B.M_PER_UNIT / mpp; self.Wb = int((self.x1 - self.x0) * self.ppu); self.Hb = int((self.y1 - self.y0) * self.ppu)
        self.cy = H * 0.40
        cache = f'{B.T5}/osm/cache/{area}_{w}_{s}_{e}_{n}_{mpp}_night3.png'
        if os.path.exists(cache): self.surf = cairo.ImageSurface.create_from_png(cache); return
        sf = cairo.ImageSurface(cairo.FORMAT_ARGB32, self.Wb, self.Hb); cr = cairo.Context(sf)
        cr.set_source_rgba(*rgb(NC['land'])); cr.paint()
        P = lambda ll: ((B.mx(ll[0]) - self.x0) * self.ppu, (B.my(ll[1]) - self.y0) * self.ppu)
        def poly(rings, col, clear=False):
            if clear: cr.set_operator(cairo.OPERATOR_CLEAR)
            else: cr.set_source_rgba(*rgb(col))
            cr.set_fill_rule(cairo.FILL_RULE_EVEN_ODD)
            for ring in rings:
                for i, (x, y) in enumerate(map(P, ring)): (cr.move_to if i == 0 else cr.line_to)(x, y)
                cr.close_path()
            cr.fill(); cr.set_operator(cairo.OPERATOR_OVER)
        for r in self.data['park']: poly(r, NC['park'])
        for r in self.data['water']: poly(r, None, clear=True)
        for r in self.data['building']: poly(r, NC['build'])
        for rd in self.data['roads']:
            if rd['c'] == 'pier_area': poly([rd['pts']], NC['pier'])
        widths = dict(motorway=14, trunk=12, primary=10, secondary=8, tertiary=6, minor=4, service=2.5, path=2, pier=4)
        major = ('motorway', 'trunk', 'primary', 'secondary')
        cr.set_line_cap(cairo.LINE_CAP_ROUND); cr.set_line_join(cairo.LINE_JOIN_ROUND)
        for cls in ('path', 'service', 'minor', 'pier', 'tertiary', 'secondary', 'primary', 'trunk', 'motorway'):
            for rd in self.data['roads']:
                if rd['c'] != cls: continue
                for i, (x, y) in enumerate(map(P, rd['pts'])): (cr.move_to if i == 0 else cr.line_to)(x, y)
                cr.set_line_width(widths[cls]); cr.set_source_rgba(*rgb(NC['major'] if cls in major else NC['minor'], 1.0 if cls != 'path' else 0.6)); cr.stroke()
        cr.set_dash([10, 8]); cr.set_line_width(3)
        for rd in self.data['roads']:
            if rd['c'] in ('rail', 'transit'):
                for i, (x, y) in enumerate(map(P, rd['pts'])): (cr.move_to if i == 0 else cr.line_to)(x, y)
                cr.set_source_rgba(*rgb(NC['rail'], 0.9)); cr.stroke()
        sf.write_to_png(cache); self.surf = sf

    def draw(self, cr, cam, blur=False, t=0.0):
        lon, lat, mpp = cam; s = (B.M_PER_UNIT / mpp) / self.ppu
        cx, cy = (B.mx(lon) - self.x0) * self.ppu, (B.my(lat) - self.y0) * self.ppu
        cr.save(); cr.set_source_rgba(*rgb(NC['water'])); cr.paint()
        # shimmer: 4 long thin lines drifting 12 px/s across the harbour (seen only where the map is water)
        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        for k in range(4):
            y = (k * 487 + t * 12) % (H + 200) - 100; x0 = (k * 331 + t * 7) % 500 - 250
            cr.set_source_rgba(*rgb(NC['shimmer'], 0.5)); cr.set_line_width(3 + k % 2)
            cr.move_to(x0, y); cr.curve_to(x0 + 300, y - 10, x0 + 700, y + 12, x0 + 1300, y - 4); cr.stroke()
            cr.set_source_rgba(*rgb(NC['shimmer'], 0.35)); cr.set_line_width(2)
            cr.move_to(x0 + 120, y + 26); cr.curve_to(x0 + 400, y + 18, x0 + 760, y + 34, x0 + 1200, y + 22); cr.stroke()
        cr.translate(W / 2, self.cy); cr.scale(s, s); cr.translate(-cx, -cy)
        cr.set_source_surface(self.surf, 0, 0); cr.get_source().set_filter(cairo.FILTER_GOOD); cr.paint(); cr.restore()

    def to_screen(self, cam):
        lon, lat, mpp = cam; ppu = B.M_PER_UNIT / mpp; cy = self.cy
        return lambda ll: (W / 2 + (B.mx(ll[0]) - B.mx(lon)) * ppu, cy + (B.my(ll[1]) - B.my(lat)) * ppu)


def tube_path(cr, col, k=1.0, scale=1.0):
    """neon tube on the current path: halo 26 @0.10, mid 14 @0.25, core 6 @1.0, white 2 px centre @0.6"""
    cr.set_line_cap(cairo.LINE_CAP_ROUND); cr.set_line_join(cairo.LINE_JOIN_ROUND)
    for wdt, al in ((26, 0.10), (14, 0.25)):
        cr.set_line_width(wdt * scale); cr.set_source_rgba(*rgb(col, al * k)); cr.stroke_preserve()
    cr.set_line_width(6 * scale); cr.set_source_rgba(*rgb(mixc((40, 46, 66), col, k) if k < 1 else col, 1.0)); cr.stroke_preserve()
    cr.set_line_width(2 * scale); cr.set_source_rgba(1, 1, 1, 0.6 * k); cr.stroke()


def glow_text_img(img, col, size):
    """text sprite + soft coloured glow (two blurs)"""
    pad = int(size * 0.5); w, h = img.width + 2 * pad, img.height + 2 * pad
    base = Image.new('RGBA', (w, h), (0, 0, 0, 0)); base.alpha_composite(img, (pad, pad))
    a = base.getchannel('A')
    out = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    for r, al in ((size * 0.30, 0.55), (size * 0.09, 0.85)):
        g = Image.new('RGBA', (w, h), col + (0,)); g.putalpha(a.filter(ImageFilter.GaussianBlur(r)).point(lambda v, al=al: int(min(255, v * al * 1.6))))
        out = Image.alpha_composite(out, g)
    out = Image.alpha_composite(out, base); out.info['pad'] = pad; return out


def glass_card(rows, col, width=None, pad=(30, 18), gap=4, radius=28, active=False, align='l'):
    """dark glass card with a 3 px glowing tube border; rows = [(text, kind, size, colour)]"""
    key = ('glass', tuple(rows), col, width, pad, gap, radius, active, align)
    if key in B._sc: return B._sc[key]
    ims = [B.fit_img(r[0], r[1], r[2], r[3], (width - 2 * pad[0]) if width else 2000) for r in rows]
    cw = width or max(i.width for i in ims) + 2 * pad[0]; chh = sum(i.height for i in ims) + gap * (len(ims) - 1) + 2 * pad[1]
    m = 22; S = 2
    big = Image.new('RGBA', ((cw + 2 * m) * S, (chh + 2 * m) * S), (0, 0, 0, 0))
    gl = Image.new('RGBA', big.size, (0, 0, 0, 0)); ImageDraw.Draw(gl).rounded_rectangle((m * S, m * S, (m + cw) * S, (m + chh) * S), radius=radius * S, outline=col + (200,), width=10 * S)
    big = Image.alpha_composite(big, gl.filter(ImageFilter.GaussianBlur(9 * S)))
    d = ImageDraw.Draw(big)
    d.rounded_rectangle((m * S, m * S, (m + cw) * S, (m + chh) * S), radius=radius * S, fill=(GOLD if active else NC['glass']) + (255 if active else 214,))
    d.rounded_rectangle((m * S, m * S, (m + cw) * S, (m + chh) * S), radius=radius * S, outline=col + (255,), width=3 * S)
    d.rounded_rectangle(((m + 1.5) * S, (m + 1.5) * S, (m + cw - 1.5) * S, (m + chh - 1.5) * S), radius=(radius - 1.5) * S, outline=(255, 255, 255, 140), width=1 * S)
    im = big.resize((cw + 2 * m, chh + 2 * m), Image.LANCZOS); y = m + pad[1]
    for t in ims:
        x = m + (pad[0] if align == 'l' else (cw - t.width) // 2); im.alpha_composite(t, (int(x), int(y))); y += t.height + gap
    im.info['inner'] = (m, m, cw, chh); B._sc[key] = im; return im


class LookReel(B.Reel):
    LOOK = 'map_day'

    def __init__(self, D, fps=B.FPS):
        super().__init__(D, fps)
        self._mapdrawn = False
        self.bd = Backdrop(D, self.job['backdrop']) if self.job.get('backdrop') else None
        self.rng = np.random.default_rng(abs(hash(self.job.get('slug', 'x'))) % (2 ** 31))

    def log(self, fr, tag, box, essential=True):
        fr.boxes.append(dict(tag=tag, box=[round(v) for v in box], essential=essential))

    def put_pil(self, fr, im, x, y, alpha=1.0, tag='', essential=True, anchor='lt', log=True):
        """paint a PIL sprite through cairo (so later cairo layers stay under the sprites), log its inner box"""
        if alpha <= 0.01: return
        fx = {'l': 0, 'm': 0.5, 'r': 1}[anchor[0]]; fy = {'t': 0, 'm': 0.5, 'b': 1}[anchor[1]]
        ix, iy = x - im.width * fx, y - im.height * fy
        key = id(im)
        if key not in _cs: _cs[key] = (pil2cairo(im), im)
        paint(fr.cr, _cs[key][0], ix, iy, alpha)
        inn = im.info.get('inner', (0, 0, im.width, im.height))
        if log and alpha > 0.5 and tag: self.log(fr, tag, (ix + inn[0], iy + inn[1], ix + inn[0] + inn[2], iy + inn[1] + inn[3]), essential)

    def scene_of(self, t):
        return next(s for s in self.scenes if s['t0'] <= t < s['t1'] + 1e-6) if t < self.dur else self.scenes[-1]

    def paint_scene(self, fr, t, sc):
        kind = sc['kind']
        if kind in ('map', 'mapcard'): self.scene_map(fr, t, sc)
        else: getattr(self, 'scene_' + kind)(fr, t, sc)

    def frame(self, t):
        fr = Frame2(t); sc = self.scene_of(t); self._mapdrawn = False
        self.paint_scene(fr, t, sc); md = self._mapdrawn
        self.hook_overlay(fr, t)
        if md: self.osm_credit(fr)
        self.fact_labels(fr, t); self.captions(fr, t)
        im = fr.image(); i0 = self.scenes.index(sc)
        if i0 > 0 and t - sc['t0'] < 0.22:
            prev = self.frame_scene(self.scenes[i0 - 1], t)
            im = Image.blend(prev, im, ease((t - sc['t0']) / 0.22))
        self.timeline['frames'].append(dict(t=round(t, 3), scene=sc['kind'], map=md, look=self.LOOK, boxes=fr.boxes))
        return im

    def frame_scene(self, sc, t):
        fr = Frame2(t); self._mapdrawn = False; self.paint_scene(fr, t, sc)
        if self._mapdrawn: self.osm_credit(fr)
        self.fact_labels(fr, t); self.captions(fr, t); return fr.image()

    def hook_overlay(self, fr, t): pass


class Frame2(B.Frame):
    pass


# =====================================================================================================================
# NEON
# =====================================================================================================================
class NeonReel(LookReel):
    LOOK = 'neon'
    TUBES = ('pink', 'cyan', 'gold', 'green')

    def __init__(self, D, fps=B.FPS):
        super().__init__(D, fps)
        m = self.job.get('map')
        if m: self.map = NightMap(m['area'], m['view'], m.get('mpp', 0.85))
        hd = self.job['headline']; nj = self.job.get('neon', {})
        if not hd.get('zh_sign'): raise SystemExit('neon look: job.headline.zh_sign (4-5 glyph Chinese phrase, written by hand) is required')
        self.E1 = 3.0; self.E0 = min(2.6, self.T(hd.get('until', 2.5)) - 0.1)      # signs rise out 2.4-3.0
        self.map_cy0 = nj.get('map_cy', 1270)
        pp = (m or {}).get('price_pin') or self.job.get('price') or {}
        self.pp = pp; self.price_on = max(1.3, min(1.5, self.T(pp.get('from', 1.3)))) if pp else None
        for a, b in zip(self.scenes, self.scenes[1:]):            # a card due within 0.3 s after the signs clear lands as they clear
            if self.E1 < b['t0'] <= self.E1 + 0.3 and b['kind'] != 'map': b['t0'] = self.E1; a['t1'] = self.E1 - 1e-4
        self._build_cluster()

    def frame_scene(self, sc, t): return None

    def frame(self, t):                                            # no cross-dissolve: every scene sits on the same night map
        fr = Frame2(t); sc = self.scene_of(t); self._mapdrawn = False
        self.paint_scene(fr, t, sc); md = self._mapdrawn
        self.hook_overlay(fr, t)
        if md: self.osm_credit(fr)
        self.fact_labels(fr, t); self.captions(fr, t)
        self.timeline['frames'].append(dict(t=round(t, 3), scene=sc['kind'], map=md, look=self.LOOK, boxes=fr.boxes))
        return fr.image()

    # ----- the opening sign cluster -----
    def _sign_surface(self, w, h, col, content, k, unlit=False, pad=40, face=None):
        """one hanging signboard: dark face, glowing tube border, content sprite (PIL, already glowing) centred"""
        key = ('sign', w, h, col, id(content), round(k, 2), unlit, face)
        if key in _cs: return _cs[key]
        sf = cairo.ImageSurface(cairo.FORMAT_ARGB32, w + 2 * pad, h + 2 * pad); cr = cairo.Context(sf)
        cr.set_source_rgba(0, 0, 0, 0.35); rrect(cr, pad + 8, pad + 14, w, h, 18); cr.fill()        # drop shadow on the dark
        cr.set_source_rgba(*rgb(face or NC['face'], 0.94)); rrect(cr, pad, pad, w, h, 18); cr.fill()
        g = cairo.LinearGradient(0, pad, 0, pad + h); g.add_color_stop_rgba(0, 1, 1, 1, 0.05); g.add_color_stop_rgba(1, 1, 1, 1, 0.0)
        cr.set_source(g); rrect(cr, pad, pad, w, h, 18); cr.fill()
        rrect(cr, pad + 12, pad + 12, w - 24, h - 24, 12)
        if unlit:                                                                   # unlit glass tube keeps a trace of its colour
            cr.set_line_width(6); cr.set_source_rgba(*rgb(mixc((44, 52, 74), NC[col], 0.35))); cr.stroke()
        else: tube_path(cr, NC[col], k)
        if content is not None and not unlit:
            cs = self._pc(content)
            cr.set_source_surface(cs, pad + (w - content.width) / 2, pad + (h - content.height) / 2); cr.paint_with_alpha(min(1.0, 0.25 + 0.75 * k))
        elif content is not None and unlit:                                         # unlit tube letters: dim glass
            cs = self._pc(content)
            cr.set_source_surface(cs, pad + (w - content.width) / 2, pad + (h - content.height) / 2); cr.paint_with_alpha(0.12)
        _cs[key] = sf; return sf

    def _pc(self, im):
        k = ('pc', id(im))
        if k not in _cs: _cs[k] = (pil2cairo(im), im)
        return _cs[k][0]

    def _build_cluster(self):
        hd = self.job['headline']; pp = self.pp
        # main wide sign: English headline (72-96 px, <= 3 lines, no word split), key word gold; full Chinese line under
        MW, inner = 660, 588
        sz, lines = wrap_fit(hd['en'], 'xb', inner, list(range(96, 70, -2)))
        en = [rich_img(l, 'xb', sz, NC['text'], GOLD) for l in lines]
        zt = tok_split(hd['zh']); zs = max(56, min(64, hd.get('size_zh', 60)))
        while zs > 56 and rich_img(zt, 'zh', zs, NC['text'], GOLD).width > inner: zs -= 2
        zh = rich_img(zt, 'zh', zs, NC['text'], GOLD)
        txt = stack(en + [zh], gap=-int(sz * 0.12), align='m')
        self.main_txt = glow_text_img(txt, NC['pink'], sz)
        MH = max(300, min(440, txt.height + 70))
        # tall Chinese sign: the hand-written 4-5 glyph core, one glyph per line
        core = hd['zh_sign']; n = len(core); gs = 104 if n <= 4 else 96
        gl = [rich_img([(c, False)], 'zh', gs, NC['text'], GOLD) for c in core]
        vt = stack(gl, gap=-int(gs * 0.16), align='m'); self.tall_txt = glow_text_img(vt, NC['cyan'], gs)
        TH = max(560, vt.height + 70)
        # price sign: price in gold tube letters, caveat in white under it
        if pp:
            pr = pp.get('price', ''); pz = 132
            while B.font('black', pz).getlength(pr) > 340 and pz > 84: pz -= 4
            pim = rich_img([(pr, True)], 'black', pz, NC['text'], GOLD)
            cav = pp.get('en2') or self.job.get('caveat', {}).get('text', '')
            cz = 40
            while cav and B.font('xb', cz).getlength(cav) > 360 and cz > 32: cz -= 2
            what = pp.get('en', '')
            rows = [pim] + ([rich_img([(w, False) for w in what.split()], 'xb', cz, NC['text'], GOLD)] if what else []) + ([rich_img([(w, False) for w in cav.split()], 'xb', cz, NC['text'], GOLD)] if cav else [])
            pt = stack(rows, gap=-int(pz * 0.18), align='m')
            self.price_txt = glow_text_img(pt, GOLD, 70)
        self.main = dict(x=50, y=352, w=MW, h=MH, col='pink', ph=0.0, txt=self.main_txt, arm='l')
        self.tall = dict(x=740, y=292, w=180, h=TH, col='cyan', ph=1.7, txt=self.tall_txt, arm='r')
        py = self.main['y'] + MH + 44
        self.price = dict(x=78, y=py, w=440, h=max(230, (self.price_txt.height - 50) if pp else 230), col='gold', ph=3.1, txt=self.price_txt if pp else None, arm='m')
        self.deco = [dict(x=552, y=py + 26, w=150, h=104, col='green', ph=4.4, txt=None, arm='m'),
                     dict(x=770, y=self.tall['y'] + TH + 40, w=140, h=86, col='pink', ph=2.2, txt=None, arm='r')]
        # blank decorative signs get a simple drawn mark (steaming bowl / arrow) instead of words
        self.deco[0]['mark'] = 'bowl'; self.deco[1]['mark'] = 'arrow'
        r = np.random.default_rng(11)
        self.windows = [(side, int(r.integers(0, 3)), int(r.integers(0, 20)), int(r.integers(0, 4))) for side in (0, 1) for _ in range(26)]
        self.flicks = [(0.62, 'tall'), (2.05, 'deco0'), (1.95, 'main'), (1.05, 'deco1')]     # 2-frame dips to 55 %

    def _k(self, name, t):
        for t0, nm in self.flicks:
            if nm == name and 0 <= t - t0 < 2 / 30 - 1e-6 and not (name == 'main' and t < 1.0): return 0.55
        return 1.0

    def _rise(self, t): return ease((t - self.E0) / (self.E1 - self.E0))

    def _draw_sign(self, fr, s, t, k, dy, unlit=False, tag=None, essential=True):
        cr = fr.cr; pad = 40
        ang = math.radians(1.0) * math.sin(2 * math.pi * t / 3.0 + s['ph'])
        content = s.get('txt')
        if content is None and s.get('mark'):
            content = self._mark(s['mark'], s['w'], s['h'], NC[s['col']])
        sf = self._sign_surface(s['w'], s['h'], s['col'], content, k, unlit)
        px, py = s['x'] + s['w'] / 2, s['y'] + dy
        # bracket: arm from the building edge, two short rods to the sign's top corners
        cr.set_source_rgba(0.13, 0.17, 0.26, 1); cr.set_line_width(5)
        ay = py - 34
        if s['arm'] == 'l': cr.move_to(0, ay); cr.line_to(s['x'] + s['w'] - 40, ay)
        elif s['arm'] == 'r': cr.move_to(W, ay); cr.line_to(s['x'] + 30, ay)
        else: cr.move_to(s['x'] + 30, ay); cr.line_to(s['x'] + s['w'] - 30, ay)
        cr.stroke(); cr.set_line_width(3)
        for cx in (s['x'] + 34, s['x'] + s['w'] - 34):
            dx = (cx - px); x1 = px + dx * math.cos(ang); y1 = py + dx * math.sin(ang)
            cr.move_to(cx, ay); cr.line_to(x1, y1 + 2); cr.stroke()
        if not unlit and k > 0:                                              # light spill of the tubes on the haze
            cx_, cy_ = px, py + s['h'] / 2; R = max(s['w'], s['h']) * 0.85
            g = cairo.RadialGradient(cx_, cy_, R * 0.2, cx_, cy_, R); c_ = NC[s['col']]
            g.add_color_stop_rgba(0, *rgb(c_, 0.20 * k)); g.add_color_stop_rgba(1, *rgb(c_, 0.0))
            cr.set_source(g); cr.arc(cx_, cy_, R, 0, 2 * math.pi); cr.fill()
        paint(cr, sf, px, py, 1.0, ang, pivot=(pad + s['w'] / 2, pad))
        if tag and content is not None:
            cw, ch = content.width - 2 * content.info['pad'], content.height - 2 * content.info['pad']
            cx0 = px - cw / 2; cy0 = py + (s['h'] - ch) / 2
            self.log(fr, tag, (cx0, cy0, cx0 + cw, cy0 + ch), essential)

    def _mark(self, kind, w, h, col):
        key = ('mark', kind, w, h, col)
        if key in B._sc: return B._sc[key]
        S = 2; im = Image.new('RGBA', (w * S, h * S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        c = (255, 255, 255, 255); lw = 5 * S
        if kind == 'bowl':
            cx, cy = w * S / 2, h * S * 0.58
            d.arc((cx - 36 * S, cy - 30 * S, cx + 36 * S, cy + 30 * S), 0, 180, fill=c, width=lw); d.line((cx - 40 * S, cy, cx + 40 * S, cy), fill=c, width=lw)
            for ox in (-14, 4, 22):
                d.arc((cx + (ox - 8) * S, cy - 40 * S, cx + (ox + 8) * S, cy - 16 * S), 90, 270, fill=c, width=3 * S)
        else:
            cy = h * S / 2; d.line((24 * S, cy, (w - 34) * S, cy), fill=c, width=lw)
            d.line(((w - 52) * S, cy - 18 * S, (w - 30) * S, cy), fill=c, width=lw); d.line(((w - 52) * S, cy + 18 * S, (w - 30) * S, cy), fill=c, width=lw)
        im = im.resize((w, h), Image.LANCZOS); g = glow_text_img(im, col, 40); B._sc[key] = g; return g

    def _sky(self, fr, t, dy):
        cr = fr.cr; SB = 1010 + dy
        if SB <= 0: return
        g = cairo.LinearGradient(0, dy, 0, SB)
        g.add_color_stop_rgba(0, *rgb((12, 20, 50))); g.add_color_stop_rgba(0.55, *rgb((24, 32, 74))); g.add_color_stop_rgba(0.85, *rgb((36, 36, 86))); g.add_color_stop_rgba(1, *rgb((36, 36, 86), 0.0))
        cr.rectangle(0, 0, W, SB); cr.set_source(g); cr.paint() if False else cr.fill()
        cr.set_source_rgba(*rgb((12, 20, 50))); cr.rectangle(0, 0, W, max(0, dy + 1)); cr.fill()
        # distant rooftops along the bottom of the sky, a few lit windows
        cr.set_source_rgba(*rgb((10, 16, 32), 0.95)); x = 60
        rr = np.random.default_rng(5)
        tops = []
        while x < W - 60:
            bw = int(rr.integers(60, 130)); bh = int(rr.integers(40, 150)); tops.append((x, bw, bh)); x += bw + int(rr.integers(4, 14))
        base = SB - 70
        for (x, bw, bh) in tops:
            cr.rectangle(x, base - bh, bw, bh + 20); cr.fill()
        for (x, bw, bh) in tops:
            for j in range(int(rr.integers(1, 4))):
                wx = x + 10 + int(rr.integers(0, max(1, bw - 26))); wy = base - bh + 12 + int(rr.integers(0, max(1, bh - 20)))
                cr.set_source_rgba(*rgb((255, 214, 130) if j % 2 == 0 else (150, 200, 255), 0.75)); cr.rectangle(wx, wy, 10, 12); cr.fill()
            cr.set_source_rgba(*rgb((10, 16, 32), 0.95))
        g2 = cairo.LinearGradient(0, base - 10, 0, SB)
        g2.add_color_stop_rgba(0, *rgb((10, 16, 32), 0.95)); g2.add_color_stop_rgba(1, *rgb((10, 16, 32), 0.0))
        cr.rectangle(0, base - 10, W, SB - base + 10); cr.set_source(g2); cr.fill()
        # near building edges at far left and right, full sky height, small lit windows
        for side in (0, 1):
            x0 = 0 if side == 0 else W - 46
            cr.set_source_rgba(*rgb((6, 10, 22))); cr.rectangle(x0, dy - 10, 46, SB - dy - 40); cr.fill()
            cr.set_source_rgba(*rgb((30, 40, 66))); cr.rectangle(x0 + (44 if side == 0 else 0), dy - 10, 2, SB - dy - 40); cr.fill()
        for side, col_, row, warm in self.windows:
            x0 = (8 if side == 0 else W - 38) + col_ * 10; y = dy + 30 + row * 46
            if y > SB - 80: continue
            cr.set_source_rgba(*rgb((255, 210, 120) if warm else (170, 210, 255), 0.9)); cr.rectangle(x0, y, 8, 14); cr.fill()

    def hook_overlay(self, fr, t):
        if t >= self.E1: return
        u = self._rise(t); dy = -u * 1150
        self._sky(fr, t, dy)
        # depth: tall sign and deco signs are a little further back (drawn first)
        self._draw_sign(fr, self.tall, t, self._k('tall', t), dy * 0.96, tag='headline_zh_sign', essential=u <= 0)
        for i, d in enumerate(self.deco): self._draw_sign(fr, d, t, self._k(f'deco{i}', t), dy * 0.98)
        if self.pp:
            on = flick_on(t - self.price_on)
            if on > 0.5: self._draw_sign(fr, self.price, t, 1.0, dy, tag='price_pin', essential=u <= 0)
            else: self._draw_sign(fr, self.price, t, 0.0, dy, unlit=True)
        self._draw_sign(fr, self.main, t, self._k('main', t), dy, tag='headline', essential=u <= 0)

    # ----- night map with glowing route -----
    def scene_map(self, fr, t, sc, cam=None):
        cr = fr.cr; cam = cam or self.cam(t)
        self.map.cy = H * 0.40 + (self.map_cy0 - H * 0.40) * (1 - self._rise(t)) if t < self.E1 else H * 0.40
        self.map.draw(cr, cam, t=t); S = self.map.to_screen(cam); self._mapdrawn = True
        allp_s = smooth([S(p) for p in self.route_all()])
        stroke_path(cr, allp_s, 5, rgb(NC['rail'], 0.8), dash=[2, 16], offset=-t * 40)
        # done part, coloured per segment mode (gold walk, cyan ferry / MTR / tram)
        u = self.progress(t); segs = []; acc = []
        for s in self.route:
            pts = smooth([S(p) for p in s['pts']]); segs.append((s['mode'], pts))
        Ls = [path_len(p)[1] for _, p in segs]; Lt = sum(Ls) or 1; d = u * Lt
        for (mode, pts), L in zip(segs, Ls):
            if d <= 0: break
            part = sub_path(pts, min(1.0, d / max(L, 1e-6))); d -= L
            if len(part) > 1:
                cr.new_path()
                for i, (x, y) in enumerate(part): (cr.move_to if i == 0 else cr.line_to)(x, y)
                tube_path(cr, GOLD if mode == 'walk' else NC['cyan'], 1.0, scale=1.25)
        m = self.job['map']
        for er in m.get('extra_routes', []):
            uu = max(0.0, min(1.0, (t - self.T(er['from'])) / er.get('dur', 1.0)))
            if uu > 0:
                ep = sub_path(smooth([S(p) for p in er['pts']]), uu); cr.new_path()
                for i, (x, y) in enumerate(ep): (cr.move_to if i == 0 else cr.line_to)(x, y)
                tube_path(cr, GOLD, 1.0, 1.25)
        pins = m.get('pins', [])
        for i, p in enumerate(pins):
            if t < self.T(p.get('from', 0)): continue
            x, y = S(p['at']); last = i == len(pins) - 1
            self._pin(cr, x, y, t, GOLD if last or p.get('col') == 'coral' else NC['cyan'], big=last)
        (lon, lat), ang, mode = self.traveller(t); x, y = S((lon, lat))
        g = cairo.RadialGradient(x, y, 0, x, y, 70); g.add_color_stop_rgba(0, 1, 0.85, 0.45, 0.35); g.add_color_stop_rgba(1, 1, 0.85, 0.45, 0)
        cr.set_source(g); cr.arc(x, y, 70, 0, 2 * math.pi); cr.fill()
        if mode == 'ferry': B.draw_boat(cr, x, y, ang, t, 1.3); B.draw_guide(cr, x, y - 2, t, walking=False, scale=0.85)
        elif mode == 'taxi': B.draw_taxi(cr, x, y, ang, t, m.get('taxi_scale', 1.25), moving=self.progress(t + 0.05) > self.progress(t) + 1e-5)
        else: B.draw_guide(cr, x, y, t, walking=self.progress(t + 0.05) > self.progress(t) + 1e-5, scale=0.95)
        if sc is not None and sc['kind'] in ('map', 'mapcard'): self.top_sign(fr, t, sc)
        if sc is not None and sc['kind'] in ('map', 'mapcard', 'summary'): self.map_labels(fr, t, S)
        return S

    def top_sign(self, fr, t, sc):
        """one lit signboard hanging into the top of frame (y 0-230, above the type zone) on map-only stretches > 2 s"""
        a0 = max(sc['t0'], self.E1)
        if sc['t1'] - a0 <= 2.0 or t < a0: return
        if not hasattr(self, '_tsign'):
            core = self.job.get('neon', {}).get('top_sign') or self.job['headline']['zh_sign']
            im = rich_img([(c, False) for c in core], 'zh', 92, NC['text'], GOLD)
            self._tsign = dict(x=W - 160 - im.width - 60, y=-30, w=im.width + 80, h=200, col='gold', ph=0.8, txt=glow_text_img(im, NC['pink'], 92), arm='r')
        u = t - a0; d = self._tsign; k = flick_on(u - 0.25) * (self._k('top', t))
        dy = -(1 - eout(u / 0.4)) * 240
        self._draw_sign(fr, d, t, 1.0 if k > 0.5 else 0.0, dy, unlit=k <= 0.5)

    def _pin(self, cr, x, y, t, col, big=True):
        for ph in (0.0, 0.5):
            v = ((t / 1.2) + ph) % 1.0; r = 14 + 46 * v
            cr.set_source_rgba(*rgb(col, 0.6 * (1 - v))); cr.set_line_width(4); cr.arc(x, y, r, 0, 2 * math.pi); cr.stroke()
        cr.new_path(); cr.arc(x, y, 12 if big else 9, 0, 2 * math.pi); tube_path(cr, col, 1.0, 0.8)
        cr.set_source_rgba(*rgb(col)); cr.arc(x, y, 8 if big else 6, 0, 2 * math.pi); cr.fill()
        cr.set_source_rgba(1, 1, 1, 0.9); cr.arc(x, y, 3.5, 0, 2 * math.pi); cr.fill()

    def map_labels(self, fr, t, S):
        m = self.job['map']
        for i, lb in enumerate(m.get('labels', [])):
            a0 = self.T(lb.get('from', 0)); a1 = self.T(lb['until']) if 'until' in lb else 1e9
            al = min(1.0, ease((a1 - t) / 0.3)) * flick_on(t - a0) if t >= a0 else 0
            if al <= 0: continue
            x, y = S(lb['at']); dx, dy = lb.get('off', (0, -70)); sz = lb.get('size', 40)
            rows = [(lb['en'], 'xb', sz, NC['text'])] + ([(lb['zh'], 'zh', int(sz * 0.92), NC['zh'])] if lb.get('zh') else [])
            im = glass_card(rows, NC[self.TUBES[(i + 1) % 4]], pad=(24, 12), gap=0, radius=22)
            fr.put(im, x + dx, y + dy, al, anchor=lb.get('anchor', 'mb'), tag='maplabel:' + lb['en'], clamp=True)
        pp = m.get('price_pin')
        if pp and t >= max(self.E1, self.T(pp['from'])) and t < self.T(pp.get('until', 'end')):    # before 3 s the price lives on its sign
            a0 = max(self.E1, self.T(pp['from'])); al = flick_on(t - a0) * min(1, ease((self.T(pp.get('until', 'end')) - t) / 0.3))
            seg = self.route[pp.get('seg', 0)]['pts']; p, _ = point_at([S(q) for q in seg], pp.get('at', 0.5))
            rows = [(pp['price'], 'black', pp.get('size', 66), GOLD), (pp['en'], 'xb', 36, NC['text'])] + ([(pp['en2'], 'xb', 36, NC['text'])] if pp.get('en2') else []) + [(pp['zh'], 'zh', 36, NC['zh'])]
            im = glass_card(rows, GOLD, width=pp.get('width', 520), pad=(28, 14), gap=0)
            dx, dy = pp.get('off', (0, -40))
            fr.put(im, p[0] + dx, p[1] + dy, al, anchor=pp.get('anchor', 'mb'), tag='price_pin', clamp=True)

    def osm_credit(self, fr, alpha=1.0):
        y = SAFE[3] if fr.t < 3.0 else 1418
        key = ('osm_n',)
        if key not in B._sc:
            f = font('semi', 24); txt = '© OpenStreetMap contributors'; tw = int(f.getlength(txt)) + 16
            im = Image.new('RGBA', (tw, 40), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
            d.text((8, 6), txt, font=f, fill=(214, 224, 245, 255), stroke_width=3, stroke_fill=(4, 8, 18, 230)); B._sc[key] = im
        fr.put(B._sc[key], SAFE[0], y, alpha, anchor='lb', tag='osm_credit', essential=False)

    # ----- cards after 3 s -----
    def paint_panel_bg(self, fr, t, sc):
        if self.map: self.scene_map(fr, t, None, cam=sc.get('cam') and tuple(sc['cam']) or None); return True
        cr = fr.cr; cr.set_source_rgba(*rgb(NC['water'])); cr.paint()
        if self.bd: self.bd.paint(fr, t)
        return False

    def panel(self, fr, x, y, w, h, al=1.0, col='cyan'):
        if al <= 0.01: return
        cr = fr.cr; cr.save()
        cr.set_source_rgba(*rgb(mixc(NC['glass'], NC[col], 0.22), 0.90 * al)); rrect(cr, x, y, w, h, 28); cr.fill()   # lit face (brightness ruling)
        rrect(cr, x + 1.5, y + 1.5, w - 3, h - 3, 27)
        for wdt, a in ((22, 0.10), (12, 0.25)):
            cr.set_line_width(wdt); cr.set_source_rgba(*rgb(NC[col], a * al)); cr.stroke_preserve()
        cr.set_line_width(3); cr.set_source_rgba(*rgb(NC[col], al)); cr.stroke(); cr.restore()

    def _row(self, fr, x, y, w, h, hi, k, r=22):
        cr = fr.cr
        if hi:
            cr.set_source_rgba(*rgb(GOLD, 0.25 * k)); rrect(cr, x - 6, y - 6, w + 12, h + 12, r + 6); cr.fill()
            cr.set_source_rgba(*rgb(GOLD, k)); rrect(cr, x, y, w, h, r); cr.fill()
        else:
            cr.set_source_rgba(*rgb((22, 32, 56), 0.95 * k)); rrect(cr, x, y, w, h, r); cr.fill()
            cr.set_line_width(2); cr.set_source_rgba(*rgb((80, 100, 150), 0.7 * k)); rrect(cr, x, y, w, h, r); cr.stroke()
        return (NC['ink'], (40, 30, 10)) if hi else (NC['text'], NC['zh'])

    def scene_week(self, fr, t, sc):
        self.paint_panel_bg(fr, t, sc); u = t - sc['t0']; k0 = flick_on(u)
        x0, y0, w = 90, 360, 790; h = 360 + (150 if sc.get('holiday') else 0); self.panel(fr, x0, y0, w, h, k0, 'cyan')
        fr.put(text_plain(sc['title_en'], 'xb', 46, NC['text']), x0 + 30, y0 + 28, k0, tag='week_title')
        fr.put(text_plain(sc['title_zh'], 'zh', 42, NC['zh']), x0 + 30, y0 + 92, k0, tag='week_title_zh')
        days = sc['days']; n = len(days); tw = (w - 60 - (n - 1) * 12) / n
        for i, d in enumerate(days):
            ks = ease((u - i * 0.03) / 0.18); k = 1.0; on = d.get('on', True)
            bx = x0 + 30 + i * (tw + 12); by = y0 + 180 + (1 - ks) * 30
            c1, c2 = self._row(fr, bx, by, tw, 150, on, k, 18) if on else ((100, 112, 140), (100, 112, 140))
            if not on:
                cr = fr.cr; cr.set_source_rgba(*rgb((16, 22, 38), k)); rrect(cr, bx, by, tw, 150, 18); cr.fill()
            fr.put(B.fit_img(d['en'], 'xb', 34, c1, tw), bx + tw / 2, by + 48, k, anchor='mm', tag='day')
            fr.put(text_plain(d['zh'], 'zh', 40, c1), bx + tw / 2, by + 106, k, anchor='mm', tag='day_zh')
        hol = sc.get('holiday')
        if hol:
            a0 = self.T(hol.get('from', sc['from'])); k = flick_on(t - a0); by = y0 + 350
            if k > 0:
                self.panel(fr, x0 + 30, by, w - 60, 120, k, 'pink')
                fr.put(text_plain(hol['en'], 'xb', 40, NC['text']), x0 + w / 2, by + 38, k, anchor='mm', tag='hol')
                fr.put(text_plain(hol['zh'], 'zh', 36, (255, 190, 222)), x0 + w / 2, by + 86, k, anchor='mm', tag='hol_zh')

    def scene_compare(self, fr, t, sc):
        self.paint_panel_bg(fr, t, sc); cr = fr.cr; u = t - sc['t0']; k0 = flick_on(u)
        ferry = sc.get('art') == 'ferry'
        x0, y0, w = 90, sc.get('y0', 340), 790; rows = sc['rows']; rh = 150
        h = 200 + len(rows) * 156 + (170 if ferry else 40); self.panel(fr, x0, y0, w, h, k0, 'pink')
        fr.put(text_plain(sc['title_en'], 'xb', 46, NC['text']), x0 + 40, y0 + 30, k0, tag='cmp_title')
        fr.put(text_plain(sc['title_zh'], 'zh', 42, NC['zh']), x0 + 40, y0 + 94, k0, tag='cmp_title_zh')
        bob = math.sin(t * 2.4) * 3 if ferry else 0; top = y0 + 200
        for i, r in enumerate(rows):
            k = ease((t - self.T(r.get('from', sc['from'])) - i * 0.1) / 0.35)
            hi = t >= self.T(r['hi_from']) if 'hi_from' in r else r.get('hi', False)
            rw = (620 + 70 * i) if ferry else w - 100; rx = x0 + (w - rw) / 2; ry = top + i * (rh + (6 if ferry else 24)) + (1 - k) * 30 + bob
            c1, c2 = self._row(fr, rx, ry, rw, rh, hi, k)
            fr.put(B.fit_img(r['en'], 'xb', 42, c1, rw - 330), rx + 34, ry + rh * 0.34, k, anchor='lm', tag=f'row{i}')
            fr.put(B.fit_img(r['zh'], 'zh', 38, c2, rw - 330), rx + 34, ry + rh * 0.70, k, anchor='lm', tag='row_zh')
            fr.put(text_plain(r['price'], 'black', 76, c1 if hi else GOLD), rx + rw - 30, ry + rh / 2, k, anchor='rm', tag='row_price')
        if ferry:                                                        # the hull as one cyan tube + tube waves
            hy = top + len(rows) * (rh + 6) + bob + 6; cx = x0 + w / 2
            cr.new_path(); cr.move_to(cx - 370, hy); cr.line_to(cx + 370, hy); cr.line_to(cx + 320, hy + 76); cr.line_to(cx - 320, hy + 76); cr.close_path()
            tube_path(cr, NC['cyan'], k0)
            for j in range(5):
                xx = x0 + 90 + j * 130 + (t * 40) % 130; cr.new_path(); cr.move_to(xx, hy + 118 - bob); cr.curve_to(xx + 22, hy + 104 - bob, xx + 44, hy + 132 - bob, xx + 66, hy + 118 - bob)
                tube_path(cr, NC['cyan'], 0.6 * k0, 0.6)

    def scene_steps(self, fr, t, sc):
        self.paint_panel_bg(fr, t, sc); cr = fr.cr
        x0, y0, w = 90, sc.get('y0', 330), 790; steps = sc['steps']; sh = 220
        ats = [self.T(s['from']) for s in steps]
        self.panel(fr, x0, y0, w, 60 + len(steps) * (sh + 20), flick_on(t - ats[0] + 0.1), 'cyan')
        for i, s in enumerate(steps):
            k = ease((t - ats[i]) / 0.35); cur = t >= ats[i] and (i == len(steps) - 1 or t < ats[i + 1]); done = i + 1 < len(steps) and t >= ats[i + 1]
            sy = y0 + 40 + i * (sh + 20) + (1 - k) * 30
            c1, c2 = self._row(fr, x0 + 30, sy, w - 60, sh, cur, k, 26)
            cr.new_path(); cr.arc(x0 + 100, sy + sh / 2, 44, 0, 2 * math.pi)
            if cur: cr.set_source_rgba(*rgb(NC['ink'], k)); cr.fill()
            else: tube_path(cr, NC['green'] if done else NC['cyan'], k, 0.6)
            if done: B.icon(cr, 'check', x0 + 100, sy + sh / 2, 60, NC['green'])
            else: fr.put(text_plain(str(i + 1), 'black', 50, GOLD if cur else NC['text']), x0 + 100, sy + sh / 2, k, anchor='mm', tag='stepnum')
            if s.get('icon'): B.icon(cr, s['icon'], x0 + w - 110, sy + sh / 2, 90, NC['ink'] if cur else NC['mute'])
            tw = w - 200 - (130 if s.get('icon') else 20)
            fr.put(B.fit_img(s['en'], 'xb', 40, c1, tw), x0 + 170, sy + sh * 0.36, k, anchor='lm', tag='step')
            fr.put(B.fit_img(s['zh'], 'zh', 38, c2, tw), x0 + 170, sy + sh * 0.68, k, anchor='lm', tag='step_zh')

    def scene_ladder(self, fr, t, sc):
        self.paint_panel_bg(fr, t, sc); cr = fr.cr
        items = sc['items']; x0, y0, w, h = 90, 330, 790, 840; self.panel(fr, x0, y0, w, h, flick_on(t - self.T(items[0]['from']) + 0.1), 'green')
        mxp = max(i['value'] for i in items); n = len(items); bw = (w - 120 - (n - 1) * 40) / n
        for i, it in enumerate(items):
            a0 = self.T(it['from']); k = eout((t - a0) / 0.6)
            bh = 420 * it['value'] / mxp * k; bx = x0 + 60 + i * (bw + 40); by = y0 + 560
            if k > 0.02:
                cr.new_path(); rrect(cr, bx + 6, by - bh + 6, bw - 12, max(1, bh - 6), 16)
                col = GOLD if it.get('hi') else NC['cyan']
                cr.set_source_rgba(*rgb(col, 0.22 * min(1, k * 3))); cr.fill_preserve(); tube_path(cr, col, min(1, k * 3))
                v = it['value'] * k; s = it.get('label') if k >= 0.999 else f"HK${v:.0f}"
                fr.put(text_plain(s or f"HK${it['value']:g}", 'black', 58, GOLD if it.get('hi') else NC['text']), bx + bw / 2, by - bh - 24, min(1, k * 3), anchor='mb', tag='ladder_price')
                fr.put(B.fit_img(it['en'], 'xb', 34, NC['text'], bw - 8), bx + bw / 2, by + 50, min(1, k * 3), anchor='mm', tag='ladder_en')
                fr.put(B.fit_img(it['zh'], 'zh', 32, NC['zh'], bw - 8), bx + bw / 2, by + 100, min(1, k * 3), anchor='mm', tag='ladder_zh')

    def scene_days(self, fr, t, sc):
        self.paint_panel_bg(fr, t, sc); u = t - sc['t0']
        days = sc['days']; n = len(days); x0, y0, w = 70, sc.get('y0', 560), 830; gap = 24; tw = (w - gap * (n - 1)) / n; th = sc.get('h', 640)
        if sc.get('title_en'):
            fr.put(text_plain(sc['title_en'], 'black', 48, NC['text']), x0 + 6, y0 - 92, ease(u / 0.3), tag='days_title')
            fr.put(text_plain(sc['title_zh'], 'zh', 40, NC['zh']), x0 + w - 6, y0 - 86, ease(u / 0.3), anchor='rt', tag='days_title_zh')
        for i, d in enumerate(days):
            a0 = self.T(d.get('from', sc['from'])); k = flick_on(t - a0)
            if k <= 0: continue
            hi = t >= self.T(d['hi_from']) if 'hi_from' in d else False
            bx = x0 + i * (tw + gap); self.panel(fr, bx, y0, tw, th, k, 'gold' if hi else 'cyan')
            fr.put(B.fit_img(d['en'], 'black', 52, NC['text'], tw - 60), bx + tw / 2, y0 + 60, k, anchor='mm', tag=f'day{i}')
            fr.put(B.fit_img(d['zh'], 'zh', 40, NC['zh'], tw - 60), bx + tw / 2, y0 + 118, k, anchor='mm', tag='day_zh')
            fr.put(text_plain(d['hi'], 'black', 96, GOLD), bx + tw / 2, y0 + th - 150, k, anchor='mm', tag='row_price')
            fr.put(text_plain(d['lo'], 'xb', 46, NC['zh']), bx + tw / 2, y0 + th - 64, k, anchor='mm', tag='day_lo')

    def scene_summary(self, fr, t, sc):
        """the cheat-sheet: ONE large signboard with a gold tube border, values in gold, over the night map pulled wide"""
        cr = fr.cr; u = t - sc['t0']; k = flick_on(u)
        if self.map:
            c0 = tuple(sc['cam']); c1 = (c0[0], c0[1], c0[2] * 0.97)
            self.scene_map(fr, t, sc, cam=keyed([(sc['t0'], c0), (self.dur, c1)], t))
        big = sc.get('big', False); x0, w = 70, 830; rows = sc['rows']; rh = 138 if big else 124; h = 120 + len(rows) * rh + (60 if sc.get('foot') else 20)
        y = (1262 - h if self.map else 380)
        cr.set_source_rgba(0, 0, 0, 0.35 * k); rrect(cr, x0 + 8, y + 14, w, h, 26); cr.fill()
        cr.set_source_rgba(*rgb(NC['face'], 0.94 * k)); rrect(cr, x0, y, w, h, 26); cr.fill()
        cr.new_path(); rrect(cr, x0 + 12, y + 12, w - 24, h - 24, 18); tube_path(cr, GOLD, k)
        cr.set_source_rgba(*rgb(GOLD, k)); rrect(cr, x0 + 24, y + 22, w - 48, 82, 14); cr.fill()                 # gold title row
        fr.put(B.fit_img(sc['title_en'], 'black', 46, NC['ink'], 470), x0 + 44, y + 30, k, tag='sum_title')
        fr.put(B.fit_img(sc['title_zh'], 'zh', 42, NC['ink'], 300), x0 + w - 44, y + 32, k, anchor='rt', tag='sum_title_zh')
        for i, r in enumerate(rows):
            ry = y + 122 + i * rh; kk = flick_on(u - 0.15 - i * 0.12)
            cr.set_source_rgba(*rgb(GOLD, 0.35 * kk)); cr.rectangle(x0 + 44, ry - 6, w - 88, 2); cr.fill()
            vi = B.fit_img(r.get('value', ''), 'black', 66 if big else 60, GOLD, 340) if r.get('value') else None
            lw = w - 88 - (vi.width + 16 if vi else 0)
            fr.put(B.fit_img(r['en'], 'xb', 44 if big else 38, NC['text'], lw), x0 + 44, ry + 8, kk, tag='sum_row')
            fr.put(B.fit_img(r['zh'], 'zh', 38 if big else 34, NC['zh'], lw), x0 + 44, ry + 60, kk, tag='sum_row_zh')
            if vi: fr.put(vi, x0 + w - 40, ry + rh / 2, kk, anchor='rm', tag='sum_val')
        if sc.get('foot'): fr.put(B.fit_img(sc['foot'], 'semi', 28, (190, 202, 228), w - 88), x0 + 44, y + h - 58, k, tag='sum_foot')

    def headline(self, fr, t): pass                                     # the headline lives on the main signboard

    def fact_labels(self, fr, t):
        for lb in self.job.get('labels', []):
            a0, a1 = self.T(lb['from']), self.T(lb['until'])
            if t < a0 or t >= a1: continue
            al = flick_on(t - a0) * min(1, ease((a1 - t) / 0.25))
            if al <= 0: continue
            col = dict(teal=NC['cyan'], gold=GOLD, coral=NC['pink']).get(lb.get('accent', 'gold'), GOLD)
            rows = [(lb['en'], 'black', lb.get('size', 52), NC['text']), (lb['zh'], 'zh', int(lb.get('size', 52) * 0.85), NC['zh'])]
            im = glass_card(rows, col, pad=(30, 14), gap=0, radius=24)
            fr.put(im, SAFE[0] - 22, lb.get('y', 280) - 22, al, anchor='lt', tag='label:' + lb['en'])


def text_plain(s, kind, size, col):
    return B.text_img(s, kind, size, col)


# =====================================================================================================================
# MENU (cha chaan teng wall)
# =====================================================================================================================
MC = dict(cream=(243, 235, 216), grout=(221, 210, 186), mint=(159, 212, 188), white=(255, 253, 246), yellow=(255, 226, 122),
          pink=(255, 194, 207), ink=(27, 27, 31), red=(215, 38, 30), tape=GOLD, plate=(250, 248, 240), rim=(46, 150, 110))
PAPERS = ('white', 'yellow', 'pink')


def ink_rough(im, seed=3, strength=0.35):
    """slightly uneven ink: knock random specks out of the alpha"""
    a = np.asarray(im.getchannel('A')).astype(np.float32)
    r = np.random.default_rng(seed); n = r.random(a.shape)
    n = np.asarray(Image.fromarray((n * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.2))).astype(np.float32) / 255
    m = np.clip((n - 0.5) * 6 + 0.5, 0, 1); k = 1 - strength * (1 - m)
    out = im.copy(); out.putalpha(Image.fromarray(np.clip(a * k, 0, 255).astype(np.uint8))); return out


def paper_img(w, h, col, content=None, tape='piece', seed=0, pad=30, dim=False):
    """paper slip with soft shadow (6,10) blur 14 alpha .25 and tape at the top; content = PIL sprite placed at (cx, cy) inside"""
    key = ('paper', w, h, col, id(content) if content else None, tape, seed, dim)
    if key in B._sc: return B._sc[key]
    S = 2; m = pad
    im = Image.new('RGBA', ((w + 2 * m) * S, (h + 2 * m) * S), (0, 0, 0, 0))
    sh = Image.new('RGBA', im.size, (0, 0, 0, 0)); ImageDraw.Draw(sh).rectangle(((m + 6) * S, (m + 10) * S, (m + 6 + w) * S, (m + 10 + h) * S), fill=(40, 28, 10, 64))
    im = Image.alpha_composite(im, sh.filter(ImageFilter.GaussianBlur(14 * S / 2)))
    d = ImageDraw.Draw(im); pc = MC[col] if isinstance(col, str) else col
    d.rectangle((m * S, m * S, (m + w) * S, (m + h) * S), fill=pc + (255,))
    # paper grain + a faint fold so it is not flat
    r = np.random.default_rng(seed); g = Image.new('RGBA', im.size, (0, 0, 0, 0)); gd = ImageDraw.Draw(g)
    for _ in range(int(w * h / 900)):
        x = r.integers(m * S, (m + w) * S); y = r.integers(m * S, (m + h) * S); gd.point((int(x), int(y)), fill=(120, 100, 60, 18))
    im = Image.alpha_composite(im, g); d = ImageDraw.Draw(im)
    gr = Image.new('L', (1, 256)); [gr.putpixel((0, i), int(18 * (1 - i / 255))) for i in range(256)]
    gr = gr.resize((w * S, h * S)); top = Image.new('RGBA', (w * S, h * S), (255, 255, 255, 0)); top.putalpha(gr)
    im.alpha_composite(top, (m * S, m * S))
    im = im.resize((w + 2 * m, h + 2 * m), Image.LANCZOS)
    if content is not None:
        im.alpha_composite(content, (int(m + (w - content.width) / 2), int(m + (h - content.height) / 2 + (8 if tape else 0))))
    d = ImageDraw.Draw(im)
    if tape == 'piece':
        tw, th = min(90, int(w * 0.42)), 30; tx = m + (w - tw) / 2; ty = m - 14
        t = Image.new('RGBA', (tw, th), MC['tape'] + (int(255 * 0.85),)); t = t.rotate(-3 + seed % 7, expand=True, resample=Image.BICUBIC)
        im.alpha_composite(t, (int(tx), int(ty)))
    elif tape == 'band':
        t = Image.new('RGBA', (w + 16, 34), MC['tape'] + (int(255 * 0.85),)); im.alpha_composite(t, (m - 8, m - 12))
    if dim:
        ov = Image.new('RGBA', im.size, MC['cream'] + (0,)); a = im.getchannel('A').point(lambda v: int(v * 0.30)); ov.putalpha(a); im = Image.alpha_composite(im, ov)
    im.info['inner'] = (m, m, w, h); B._sc[key] = im; return im


def vert_text(s, kind, size, col, gap=0.06):
    ims = [B.text_img(c, kind, size, col) for c in s]
    return stack(ims, gap=-int(size * (0.22 - gap)), align='m')


class MenuReel(LookReel):
    LOOK = 'menu'

    def __init__(self, D, fps=B.FPS):
        super().__init__(D, fps)
        mj = self.job.get('menu', {}); self.mj = mj
        r = np.random.default_rng(int(mj.get('seed', 7)))
        self.tilts = [float(v) for v in r.uniform(-2, 2, 24)]                # fixed per Reel (seeded)
        self._wall = None
        pp = (self.job.get('map') or {}).get('price_pin') or self.job.get('price') or {}
        self.pp = pp; self.stamp_t = max(1.3, min(1.45, self.T(pp.get('from', 1.3)))) if pp else 1.3
        self.hook_end = self.T(self.job['headline'].get('until', 2.5))
        self._build_hook()

    # ----- wall -----
    def wall(self):
        if self._wall is not None: return self._wall
        T_, gr = 54, 3; y0 = 300 - 6 * T_; r = np.random.default_rng(21)
        a = np.zeros((H, W, 3), np.float32)
        a[:] = MC['grout']
        for j in range(-1, H // T_ + 2):
            for i in range(0, W // T_ + 2):
                x, y = i * T_, y0 + j * T_
                band = 300 <= y < 300 + 5 * T_
                base = np.array(MC['mint'] if band else MC['cream'], np.float32) * (1 + r.uniform(-0.03, 0.03))
                xa, xb, ya, yb = max(0, x + gr // 2), min(W, x + T_ - gr // 2 - 1), max(0, y + gr // 2), min(H, y + T_ - gr // 2 - 1)
                if xa >= xb or ya >= yb: continue
                a[ya:yb, xa:xb] = base
                a[ya:ya + 2, xa:xb] = np.minimum(255, base * 1.05); a[yb - 2:yb, xa:xb] = base * 0.94   # glaze edge
                a[ya:yb, xb - 2:xb] = base * 0.95
        yy, xx = np.mgrid[0:H, 0:W]; g = 1.06 - 0.12 * np.clip((xx / W * 0.45 + yy / H * 0.75), 0, 1)
        a = np.clip(a * g[..., None], 0, 255).astype(np.uint8)
        im = Image.fromarray(a, 'RGB').convert('RGBA'); self._wall = pil2cairo(im); return self._wall

    def paint_wall(self, fr):
        fr.cr.set_source_surface(self.wall(), 0, 0); fr.cr.paint()

    def swing(self, t, t0, i):
        """tilt per paper (seeded) + a 4 deg swing that dies away over 0.5 s"""
        u = t - t0; sw = 4 * math.exp(-max(0, u) / 0.16) * math.cos(2 * math.pi * max(0, u) / 0.42) if u < 0.9 else 0
        return math.radians(self.tilts[i % len(self.tilts)] + sw)

    def hang(self, fr, im, x, y, ang, alpha=1.0, tag=None, essential=True, scale=1.0):
        """hang paper sprite by its top-centre at (x, y)"""
        key = id(im)
        if key not in _cs: _cs[key] = (pil2cairo(im), im)
        inn = im.info.get('inner', (0, 0, im.width, im.height))
        paint(fr.cr, _cs[key][0], x, y, alpha, ang, pivot=(inn[0] + inn[2] / 2, inn[1]), scale=(scale, scale))
        if tag and alpha > 0.5:
            self.log(fr, tag, (x - inn[2] / 2 * scale, y, x + inn[2] / 2 * scale, y + inn[3] * scale), essential)

    # ----- opening: wall strips, placard with the price, dish, stamp -----
    def _build_hook(self):
        hd = self.job['headline']; mj = self.mj
        strips = mj.get('strips') or [dict(zh='豆腐花'), dict(zh='熱豆漿'), dict(zh='凍豆漿'), dict(zh='煎釀豆腐')]
        self.wall_strips = []
        xs = mj.get('strip_x') or [60, 300, 560, 820]
        for i, s in enumerate(strips[:4]):
            col = s.get('col', PAPERS[i % 3]); wdt = 200; hh = 600 + (i * 37) % 90
            if s.get('zh'): c = vert_text(s['zh'], 'zh', 74, MC['red'] if i % 2 else MC['ink'])
            else: c = B.text_img(s['en'], 'black', 64, MC['ink']).rotate(-90, expand=True)
            if s.get('price'):
                pz = B.text_img(s['price'], 'black', 58, MC['red']); c = stack([c, pz], gap=6, align='m')
            self.wall_strips.append((paper_img(wdt, hh, col, c, 'piece', seed=i), xs[i] + wdt / 2, 236 + (i * 53) % 70))
        # placard: headline EN (72-96, <= 3 lines), ZH (60-70), the PRICE in big red numerals (digits 240-320 px high)
        pw = 820; inner = pw - 80
        en_s = hd.get('menu_en') or re.sub(r'\{[^}]*\}', '', hd['en']).replace('\n', ' ').strip()
        sz, lines = wrap_fit(en_s, 'black', inner, list(range(96, 70, -2)))
        en = [rich_img(l, 'black', sz, MC['ink'], MC['red']) for l in lines]
        zh_s = hd.get('menu_zh') or re.sub(r'\{[^}]*\}', '', hd['zh']).strip()
        zz = max(60, min(70, hd.get('size_zh', 66)))
        while B.font('zh', zz).getlength(zh_s) > inner and zz > 60: zz -= 2
        zh = B.text_img(zh_s, 'zh', zz, MC['ink'])
        price = self.pp.get('price', '') if self.pp else ''
        m = re.match(r'\s*(.*?)\s*(HK\$)\s*([\d.,]+)\s*(.*)$', price)
        pre, cur, num, post = (m.groups() if m else ('', '', price, ''))
        f_num = B.font('black', 340); asc = f_num.getbbox('0')
        numh = asc[3] - asc[1]; nsz = 340
        while numh < 240: nsz += 10; numh = B.font('black', nsz).getbbox('0')[3] - B.font('black', nsz).getbbox('0')[1]
        while numh > 300 or (B.font('black', nsz).getlength(num) + B.font('black', 110).getlength(cur) + B.font('xb', 64).getlength(pre) > inner and nsz > 300):
            nsz -= 10; bb = B.font('black', nsz).getbbox('0'); numh = bb[3] - bb[1]
        self.num_h = numh
        fn = B.font('black', nsz); fc = B.font('black', 110); fp = B.font('xb', 64)
        bbn = fn.getbbox(num); wn = fn.getlength(num); wc = fc.getlength(cur); wp = fp.getlength(pre + ' ') if pre else 0
        ph_ = bbn[3] - bbn[1] + 20; pim = Image.new('RGBA', (int(wp + wc + wn + 20), int(ph_)), (0, 0, 0, 0)); d = ImageDraw.Draw(pim)
        top = bbn[1] - 6; x = 4
        if pre: d.text((x, (bbn[3] - fp.getbbox('U')[3]) - top), pre, font=fp, fill=MC['red'] + (255,)); x += wp
        if cur: d.text((x, (bbn[1] - fc.getbbox('H')[1]) - top + 6), cur, font=fc, fill=MC['red'] + (255,)); x += wc + 4
        d.text((x, -top), num, font=fn, fill=MC['red'] + (255,))
        pim = ink_rough(pim, 5, 0.12)
        body = stack(en + [zh], gap=-int(sz * 0.10), align='m')
        self.placard_txt = stack([body, Image.new('RGBA', (10, 22)), pim], gap=0, align='m')
        ph = max(520, self.placard_txt.height + 70)
        self.placard = paper_img(pw, ph, 'white', self.placard_txt, 'piece', seed=9)
        self.placard_h = ph; self.price_img = pim
        # stamp (caveat) - red ink, rotated 5 deg, uneven
        cav = (self.pp.get('en2') if self.pp else None) or self.job.get('caveat', {}).get('text', '')
        cavz = self.pp.get('zh', '') if self.pp else ''
        self.stamp = self._stamp_img(cav.upper(), cavz)

    def _stamp_img(self, en, zh):
        fe = B.font('black', 44); fz = B.font('zh', 40)
        w = int(max(fe.getlength(en), fz.getlength(zh) if zh else 0) + 60); h = 150 if zh else 96
        S = 2; im = Image.new('RGBA', (w * S, h * S), (0, 0, 0, 0)); d = ImageDraw.Draw(im); c = MC['red'] + (255,)
        d.rounded_rectangle((3 * S, 3 * S, (w - 3) * S, (h - 3) * S), radius=12 * S, outline=c, width=6 * S)
        d.rounded_rectangle((12 * S, 12 * S, (w - 12) * S, (h - 12) * S), radius=8 * S, outline=c, width=2 * S)
        im = im.resize((w, h), Image.LANCZOS); d = ImageDraw.Draw(im)
        d.text((w / 2, 50 if zh else h / 2), en, font=fe, fill=c, anchor='mm')
        if zh: d.text((w / 2, 106), zh, font=fz, fill=c, anchor='mm')
        im = ink_rough(im, 13, 0.45); im.info['inner'] = (0, 0, w, h); return im

    def draw_dish(self, cr, cx, cy, t, kind='bowl', size=360):
        """our own drawn dish on a round plate with a green rim; 6 px ink line; soft shadow; 2-3 steam curls rising 20 px/s"""
        s = size / 360; ink = rgb(MC['ink']); cr.save(); cr.translate(cx, cy); cr.scale(s, s)
        for r_, a in ((190, 0.06), (176, 0.08), (165, 0.10)):                                  # soft shadow
            cr.save(); cr.translate(10, 26); cr.scale(1, 0.36); cr.arc(0, 0, r_, 0, 2 * math.pi); cr.restore(); cr.set_source_rgba(0.25, 0.18, 0.05, a); cr.fill()
        cr.save(); cr.scale(1, 0.36); cr.arc(0, 0, 170, 0, 2 * math.pi); cr.restore(); cr.set_source_rgba(*rgb(MC['plate'])); cr.fill_preserve(); cr.set_source_rgba(*ink); cr.set_line_width(6); cr.stroke()
        cr.save(); cr.scale(1, 0.36); cr.arc(0, 0, 150, 0, 2 * math.pi); cr.restore(); cr.set_source_rgba(*rgb(MC['rim'])); cr.set_line_width(12); cr.stroke()
        if kind == 'bowl':
            # bowl body (white porcelain, blue band), contents pale tofu with ginger syrup
            cr.move_to(-130, -60); cr.curve_to(-120, 40, -60, 70, 0, 70); cr.curve_to(60, 70, 120, 40, 130, -60); cr.close_path()
            cr.set_source_rgba(*rgb((255, 255, 252))); cr.fill_preserve(); cr.set_source_rgba(*ink); cr.set_line_width(6); cr.stroke()
            cr.move_to(-112, 0); cr.curve_to(-60, 30, 60, 30, 112, 0); cr.set_source_rgba(*rgb((60, 120, 190))); cr.set_line_width(10); cr.stroke()
            cr.save(); cr.translate(0, -60); cr.scale(1, 0.28); cr.arc(0, 0, 130, 0, 2 * math.pi); cr.restore(); cr.set_source_rgba(*rgb((250, 240, 214))); cr.fill_preserve(); cr.set_source_rgba(*ink); cr.set_line_width(6); cr.stroke()
            cr.save(); cr.translate(-8, -58); cr.scale(1, 0.24); cr.arc(0, 0, 92, 0, 2 * math.pi); cr.restore(); cr.set_source_rgba(*rgb((226, 178, 92), 0.75)); cr.fill()
            cr.save(); cr.translate(0, 70); cr.scale(1, 0.3); cr.arc(0, 0, 54, 0, math.pi); cr.restore(); cr.set_source_rgba(*ink); cr.set_line_width(6); cr.stroke()
            cr.move_to(40, -96); cr.line_to(150, -170); cr.set_line_width(16); cr.set_source_rgba(*rgb((250, 248, 240))); cr.stroke_preserve(); cr.set_line_width(6)    # spoon
            cr.set_source_rgba(*ink); cr.new_path(); cr.move_to(40, -96); cr.line_to(150, -170); cr.stroke()
        elif kind == 'cup':
            cr.move_to(-80, -120); cr.line_to(-64, 50); cr.curve_to(-60, 70, 60, 70, 64, 50); cr.line_to(80, -120); cr.close_path()
            cr.set_source_rgba(*rgb((255, 255, 252))); cr.fill_preserve(); cr.set_source_rgba(*ink); cr.set_line_width(6); cr.stroke()
            cr.save(); cr.translate(0, -120); cr.scale(1, 0.25); cr.arc(0, 0, 80, 0, 2 * math.pi); cr.restore(); cr.set_source_rgba(*rgb((140, 82, 40))); cr.fill_preserve(); cr.set_source_rgba(*ink); cr.stroke()
            cr.arc(98, -40, 36, -math.pi / 2, math.pi / 2); cr.set_line_width(14); cr.stroke()
        else:
            cr.save(); cr.translate(0, -30); cr.scale(1, 0.4)
            for (ox, oy, r_, c) in ((-40, 0, 70, (232, 170, 70)), (50, 10, 64, (210, 120, 60)), (0, -40, 58, (246, 210, 110))):
                cr.arc(ox, oy, r_, 0, 2 * math.pi); cr.set_source_rgba(*rgb(c)); cr.fill_preserve(); cr.set_source_rgba(*ink); cr.set_line_width(6); cr.stroke()
            cr.restore()
        top = -110 if kind != 'cup' else -160
        cr.set_line_cap(cairo.LINE_CAP_ROUND)
        for j in range(3):                                                                    # steam: pale curls drifting up 20 px/s
            ph = (t * 20 / 160 + j / 3) % 1.0; y = top - ph * 160; x = -50 + j * 50; a = 0.75 * math.sin(math.pi * ph)
            cr.move_to(x, y); cr.curve_to(x - 26, y - 30, x + 26, y - 50, x, y - 84)
            cr.set_source_rgba(1, 1, 1, a); cr.set_line_width(12); cr.stroke_preserve(); cr.set_source_rgba(0.55, 0.5, 0.42, a * 0.35); cr.set_line_width(3); cr.stroke()
        cr.restore()

    def hook_overlay(self, fr, t):
        if t >= 3.05: return
        cr = fr.cr; e = ease((t - self.hook_end) / 0.4)                           # placard + dish leave 2.5-2.9
        ph = self.placard_h; px = W / 2 - 15; py = 560
        ang = self.swing(t, -0.05, 5)
        if e < 1:
            self.hang(fr, self.placard, px, py - e * 900, ang, 1.0)
            if e < 0.5:
                tw_, th_ = self.placard_txt.width, self.placard_txt.height; ty = py - e * 900 + (ph - th_) / 2 + 8
                self.log(fr, 'headline', (px - tw_ / 2, ty, px + tw_ / 2, ty + th_), essential=e <= 0)
            # the stamp lands on the placard over the lower right, 2-frame squash, then rests
            if t >= self.stamp_t:
                n = int((t - self.stamp_t) * 30 + 1e-6); sq = (1.22, 0.9)[n] if n < 2 else 1.0
                sx, sy = px + 380 - self.stamp.width / 2 - 20, py + ph - 60 - e * 900
                sx, sy = px + math.cos(ang) * (sx - px) - math.sin(ang) * (sy - py), py + math.sin(ang) * (sx - px) + math.cos(ang) * (sy - py)
                if sy > 1230 - self.stamp.height / 2: sy = 1230 - self.stamp.height / 2
                key = id(self.stamp)
                if key not in _cs: _cs[key] = (pil2cairo(self.stamp), self.stamp)
                paint(cr, _cs[key][0], sx, sy, 1.0, math.radians(-5) + ang, pivot=(self.stamp.width / 2, self.stamp.height / 2), scale=(sq, 1 / sq))
                if e <= 0: self.log(fr, 'stamp', (sx - self.stamp.width / 2, sy - self.stamp.height / 2, sx + self.stamp.width / 2, sy + self.stamp.height / 2))
        dish = self.mj.get('dish', 'bowl')
        self.draw_dish(cr, 840 + e * 500, 1270, t, dish, self.mj.get('dish_size', 360))

    def scene_map(self, fr, t, sc, cam=None):
        if sc is self.scenes[0] and sc['kind'] == 'map':                      # opening: the wall itself (placard drawn on top)
            self.paint_wall(fr); self.draw_wall_strips(fr, t); return None
        return self.scene_mapcard(fr, t, sc)

    def draw_wall_strips(self, fr, t, alpha=1.0):
        for i, (im, x, y) in enumerate(self.wall_strips):
            self.hang(fr, im, x, y, self.swing(t, -0.1 - 0.06 * i, i), alpha, tag='wallstrip', essential=False)

    def paint_panel_bg(self, fr, t, sc):
        self.paint_wall(fr); self.draw_wall_strips(fr, t, 1.0); return False

    def wash(self, fr, k=0.55):
        """the cards in the body sit over the wall; soften the decorative strips so the reading paper wins"""
        cr = fr.cr; cr.set_source_rgba(*rgb(MC['cream'], k)); cr.rectangle(0, 0, W, H); cr.fill()

    # ----- mapcard: the only map in this world -----
    def scene_mapcard(self, fr, t, sc):
        self.paint_wall(fr); self.draw_wall_strips(fr, t); self.wash(fr, 0.35)
        cr = fr.cr; u = t - sc['t0']; v = 1 - eout(u / 0.55); out = ease((t - (sc['t1'] - 0.35)) / 0.35)
        cw, ch = 880, 700; x0 = (W - cw) / 2; y0 = 400 + v * 1200 + out * 1300
        ang = math.radians(self.tilts[7] * 0.4) + (math.radians(3) * math.exp(-max(0, u - 0.55) / 0.2) * math.cos(2 * math.pi * (u - 0.55) / 0.5) if u > 0.55 else 0)
        cr.save(); cr.translate(x0 + cw / 2, y0); cr.rotate(ang); cr.translate(-cw / 2, 0)
        for r_, a in ((28, 0.07), (18, 0.10), (10, 0.12)):
            cr.set_source_rgba(0.25, 0.18, 0.05, a); rrect(cr, 6 - r_ / 3, 10 - r_ / 3, cw + r_ * 0.66, ch + r_ * 0.66, 28 + r_ / 2); cr.fill()
        cr.set_source_rgba(*rgb((247, 238, 214))); rrect(cr, 0, 0, cw, ch, 28); cr.fill()
        cr.set_source_rgba(*rgb((222, 208, 176))); cr.set_line_width(2); rrect(cr, 1, 1, cw - 2, ch - 2, 27); cr.stroke()
        fw = 26; cr.save(); rrect(cr, fw, fw, cw - 2 * fw, ch - 2 * fw, 14); cr.clip()
        mcx, mcy = cw / 2, ch / 2
        cam = self.cam(t); lon, lat, mpp = cam; mpp = mpp * sc.get('zoom', 1.0)
        m = self.map; s = (B.M_PER_UNIT / mpp) / m.ppu; cx, cy = (B.mx(lon) - m.x0) * m.ppu, (B.my(lat) - m.y0) * m.ppu
        cr.set_source_rgba(*rgb(B.C['water'])); cr.paint()
        cr.save(); cr.translate(mcx, mcy); cr.scale(s, s); cr.translate(-cx, -cy); cr.set_source_surface(m.surf, 0, 0); cr.get_source().set_filter(cairo.FILTER_GOOD); cr.paint(); cr.restore()
        ppu = B.M_PER_UNIT / mpp
        S = lambda ll: (mcx + (B.mx(ll[0]) - B.mx(lon)) * ppu, mcy + (B.my(ll[1]) - B.my(lat)) * ppu)
        allp = smooth([S(p) for p in self.route_all()])
        stroke_path(cr, allp, 9, rgb(B.C['ink'], 0.35), dash=[2, 18], offset=-t * 40)
        done = sub_path(allp, self.progress(t)); stroke_path(cr, done, 22, rgb((255, 255, 255), 0.95)); stroke_path(cr, done, 12, rgb(MC['red']))
        for p in self.job['map'].get('pins', []):
            x, y = S(p['at']); B.draw_pin(cr, x, y, MC['red'] if p.get('col') == 'coral' else B.C['teal'], 1.0)
        (lo, la), a_, mode = self.traveller(t); x, y = S((lo, la)); B.draw_guide(cr, x, y, t, walking=self.progress(t + 0.05) > self.progress(t) + 1e-5, scale=0.95)
        cr.restore()
        # osm credit inside the frame (ink on cream)
        cr.restore()
        self._mapdrawn = True
        self._card_geo = (x0, y0, cw, ch, ang, mcx, mcy, S)
        tp = pil2cairo_cached(('tape', 160), lambda: Image.new('RGBA', (160, 36), MC['tape'] + (217,)))
        paint(cr, tp, x0 + cw / 2, y0 - 6, 1.0, ang - 0.03, pivot=(80, 18))
        # labels inside the card as small paper tags
        for i, lb in enumerate(self.job['map'].get('labels', [])):
            a0 = self.T(lb.get('from', 0)); a1 = self.T(lb['until']) if 'until' in lb else 1e9
            if not (sc['t0'] <= a0 < sc['t1'] + 0.01 or (a0 < sc['t0'] < a1)): continue
            al = min(ease((t - a0) / 0.3), ease((a1 - t) / 0.3), 1 - out)
            if al <= 0: continue
            lx, ly = S(lb['at']); dx, dy = lb.get('off', (0, -70))
            gx = x0 + cw / 2 + math.cos(ang) * (lx - cw / 2) - math.sin(ang) * ly; gy = y0 + math.sin(ang) * (lx - cw / 2) + math.cos(ang) * ly
            sz = lb.get('size', 40)
            rows = [(lb['en'], 'xb', sz, MC['ink'])] + ([(lb['zh'], 'zh', int(sz * 0.92), MC['red'])] if lb.get('zh') else [])
            im = B.card_img(rows, pad=(24, 14), radius=6, gap=2, bg=MC['yellow' if i % 2 else 'white'])
            fr.put(im, gx + dx, gy + dy, al, anchor=lb.get('anchor', 'mb'), tag='maplabel:' + lb['en'], clamp=True)
        return S

    def osm_credit(self, fr, alpha=1.0):
        if not getattr(self, '_card_geo', None): return
        x0, y0, cw, ch, ang, *_ = self._card_geo
        key = ('osm_m',)
        if key not in B._sc:
            f = font('semi', 24); txt = '© OpenStreetMap contributors'; tw = int(f.getlength(txt)) + 16
            im = Image.new('RGBA', (tw, 36), (0, 0, 0, 0)); ImageDraw.Draw(im).text((8, 4), txt, font=f, fill=(255, 255, 255, 255), stroke_width=4, stroke_fill=(20, 24, 30, 235)); B._sc[key] = im
        fr.put(B._sc[key], x0 + 40, min(1418, y0 + ch - 30), alpha, anchor='lb', tag='osm_credit', essential=False)

    # ----- body: paper strips -----
    def strip_row(self, fr, i, en, zh, price, x, y, t, a0, active, dim, col=None, num=None, tick=False, w=880, h=170):
        """one horizontal item strip (880 x 170) dropped from the top, swinging to rest"""
        col = col or PAPERS[i % 3]
        key = ('srow', en, zh, price, col, num, tick, w, h)
        if key not in B._sc:
            lx = 40 + (90 if num is not None or tick else 0); pw_ = 0
            im = Image.new('RGBA', (w, h), (0, 0, 0, 0))
            if price:
                pim = B.text_img(price, 'black', 92, MC['red']); pim = ink_rough(pim, 3, 0.1); pw_ = pim.width
                im.alpha_composite(pim, (w - pim.width - 26, (h - pim.height) // 2))
            tw = w - lx - pw_ - 50
            e = B.fit_img(en, 'xb', 60, MC['ink'], tw); z = B.fit_img(zh, 'zh', 56, MC['ink'], tw) if zh else None
            if z is not None:
                im.alpha_composite(e, (lx, 10)); im.alpha_composite(z, (lx + 2, 86))
            else: im.alpha_composite(e, (lx, (h - e.height) // 2))
            d = ImageDraw.Draw(im)
            if num is not None:
                d.ellipse((34, h / 2 - 38, 110, h / 2 + 38), outline=MC['red'] + (255,), width=6)
                d.text((72, h / 2), str(num), font=B.font('black', 48), fill=MC['red'] + (255,), anchor='mm')
            if tick:
                d.line((40, h / 2, 66, h / 2 + 28), fill=MC['red'] + (255,), width=12); d.line((64, h / 2 + 28, 108, h / 2 - 34), fill=MC['red'] + (255,), width=12)
            B._sc[key] = im
        content = B._sc[key]
        pim = paper_img(w, h, col, content, 'band' if active else 'piece', seed=i, dim=dim)
        u = t - a0; drop = 1 - eout(u / 0.35)
        ang = math.radians(self.tilts[10 + i] * 0.5) + (math.radians(4) * math.exp(-max(0, u - 0.3) / 0.16) * math.cos(2 * math.pi * (u - 0.3) / 0.4) if u > 0.3 else 0)
        self.hang(fr, pim, x, y - drop * (y + h + 60), ang, 1.0, tag=f'strip{i}' if drop < 0.05 else None)
        if drop < 0.05: self.log(fr, f'row{i}', (x - w / 2 + 40, y, x + w / 2 - 40, y + h))

    def count(self, val, k, label):
        return label if k >= 0.999 else f'HK${val * k:.0f}'

    def scene_ladder(self, fr, t, sc):
        self.paint_panel_bg(fr, t, sc); self.wash(fr, 0.30)
        items = sc['items']; ats = [self.T(it['from']) for it in items]
        for i, it in enumerate(items):
            if t < ats[i]: continue
            cur = i == len(items) - 1 or t < ats[i + 1]; k = eout((t - ats[i] - 0.25) / 0.6)
            lab = it.get('label') or (f"HK${it['value']:g}" if 'value' in it else '')
            pr = self.count(it['value'], k, lab) if 'value' in it and it.get('count', True) else lab
            self.strip_row(fr, i, it['en'], it.get('zh', ''), pr, W / 2, sc.get('y0', 380) + i * 215, t, ats[i], cur, not cur, it.get('paper'))

    def scene_steps(self, fr, t, sc):
        self.paint_panel_bg(fr, t, sc); self.wash(fr, 0.30)
        steps = sc['steps']; ats = [self.T(s['from']) for s in steps]
        for i, s in enumerate(steps):
            if t < ats[i]: continue
            cur = i == len(steps) - 1 or t < ats[i + 1]; done = not cur
            self.strip_row(fr, i, s['en'], s.get('zh', ''), s.get('value', ''), W / 2, sc.get('y0', 380) + i * 215, t, ats[i], cur, done, s.get('paper'), num=None if done else i + 1, tick=done)

    def scene_compare(self, fr, t, sc):
        self.paint_panel_bg(fr, t, sc); self.wash(fr, 0.30); u = t - sc['t0']
        title = paper_img(700, 150, 'white', stack([B.fit_img(sc['title_en'], 'black', 56, MC['ink'], 640), B.fit_img(sc['title_zh'], 'zh', 50, MC['red'], 640)], gap=-8, align='m'), 'piece', seed=31)
        self.hang(fr, title, W / 2, 330 - (1 - eout(u / 0.3)) * 500, self.swing(t, sc['t0'], 12), 1.0, tag='cmp_title')
        for i, r in enumerate(sc['rows']):
            a0 = self.T(r.get('from', sc['from'])) + i * 0.12
            if t < a0: continue
            hi = t >= self.T(r['hi_from']) if 'hi_from' in r else r.get('hi', False)
            self.strip_row(fr, i, r['en'], r.get('zh', ''), r['price'], W / 2, 560 + i * 215, t, a0, hi, False, 'yellow' if hi else 'white')

    def scene_week(self, fr, t, sc):
        self.paint_panel_bg(fr, t, sc); self.wash(fr, 0.30); cr = fr.cr; u = t - sc['t0']
        days = sc['days']; n = len(days); hol = sc.get('holiday')
        w, h = 860, 470 + (170 if hol else 0)
        key = ('weekcard', sc['title_en'], json.dumps(days, ensure_ascii=False), json.dumps(hol, ensure_ascii=False))
        if key not in B._sc:
            im = Image.new('RGBA', (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
            im.alpha_composite(B.fit_img(sc['title_en'], 'black', 60, MC['ink'], w - 80), (36, 26))
            im.alpha_composite(B.fit_img(sc['title_zh'], 'zh', 56, MC['red'], w - 80), (38, 112))
            tw = (w - 72 - (n - 1) * 12) / n
            for i, dd in enumerate(days):
                on = dd.get('on', True); bx = 36 + i * (tw + 12); by = 220
                d.rectangle((bx, by, bx + tw, by + 200), fill=(MC['yellow'] if on else (226, 222, 212)) + (255,), outline=MC['ink'] + (255,), width=3)
                c = MC['ink'] if on else (150, 146, 138)
                d.text((bx + tw / 2, by + 60), dd['en'], font=B.font('black', 34), fill=c + (255,), anchor='mm')
                d.text((bx + tw / 2, by + 140), dd['zh'], font=B.font('zh', 58), fill=c + (255,), anchor='mm')
                if not on: d.line((bx + 10, by + 190, bx + tw - 10, by + 10), fill=MC['red'] + (255,), width=6)
            B._sc[key] = im
        pim = paper_img(w, h, 'white', B._sc[key], 'piece', seed=41)
        self.hang(fr, pim, W / 2, 360 - (1 - eout(u / 0.35)) * 900, self.swing(t, sc['t0'] + 0.3, 13), 1.0, tag='week_card')
        if hol:
            a0 = self.T(hol.get('from', sc['from']))
            if t >= a0:
                n_ = int((t - a0) * 30 + 1e-6); sq = (1.22, 0.9)[n_] if n_ < 2 else 1.0
                st = self._stamp_cached(hol['en'].upper(), hol['zh'])
                paint(cr, pil2cairo_cached(('st', id(st)), lambda: st), W / 2, 360 + 560, 1.0, math.radians(-5), pivot=(st.width / 2, st.height / 2), scale=(sq, 1 / sq))
                self.log(fr, 'hol', (W / 2 - st.width / 2, 920 - st.height / 2, W / 2 + st.width / 2, 920 + st.height / 2))

    def _stamp_cached(self, en, zh):
        key = ('stamp', en, zh)
        if key not in B._sc: B._sc[key] = self._stamp_img(en, zh)
        return B._sc[key]

    def scene_summary(self, fr, t, sc):
        """THE BILL: white order slip, faint ruled lines, rows written on it, values in red, round 'checked' stamp"""
        self.paint_panel_bg(fr, t, sc); self.wash(fr, 0.25); u = t - sc['t0']
        rows = sc['rows']; w = 800; rh = 150; h = 200 + len(rows) * rh + 150
        key = ('bill', json.dumps(sc, ensure_ascii=False, default=str))
        if key not in B._sc:
            im = Image.new('RGBA', (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
            for y in range(150, h - 20, 50): d.line((24, y, w - 24, y), fill=(150, 176, 210, 90), width=2)
            d.line((96, 0, 96, h), fill=(230, 120, 120, 90), width=2)
            im.alpha_composite(B.fit_img(sc['title_en'], 'black', 58, MC['ink'], 470), (110, 28))
            im.alpha_composite(B.fit_img(sc['title_zh'], 'zh', 50, MC['ink'], 250), (w - 40 - B.fit_img(sc['title_zh'], 'zh', 50, MC['ink'], 250).width, 34))
            d.text((40, 60), 'No.', font=B.font('bold', 22), fill=(120, 120, 130, 255))
            for i, r in enumerate(rows):
                ry = 160 + i * rh
                vi = B.fit_img(r.get('value', ''), 'black', 70, MC['red'], 330) if r.get('value') else None
                lw = w - 150 - (vi.width + 20 if vi else 0)
                im.alpha_composite(B.fit_img(r['en'], 'xb', 46, MC['ink'], lw), (110, ry))
                im.alpha_composite(B.fit_img(r['zh'], 'zh', 40, MC['ink'], lw), (112, ry + 66))
                if vi: im.alpha_composite(ink_rough(vi, 7 + i, 0.12), (w - 30 - vi.width, ry + (rh - vi.height) // 2 - 10))
                d.text((50, ry + 30), str(i + 1), font=B.font('black', 40), fill=(120, 120, 130, 255))
            if sc.get('foot'):
                im.alpha_composite(B.fit_img(sc['foot'], 'semi', 28, (70, 70, 80), w - 300), (110, h - 78))
            # round "checked" stamp
            m_ = re.search(r'(\d{1,2}\s+[A-Z][a-z]{2})', sc.get('foot', '')); dt = (m_.group(1) if m_ else self.job.get('date', '')).upper()
            S = 2; R = 96; st = Image.new('RGBA', (R * 2 * S, R * 2 * S), (0, 0, 0, 0)); sd = ImageDraw.Draw(st); c = MC['red'] + (255,)
            sd.ellipse((4 * S, 4 * S, (2 * R - 4) * S, (2 * R - 4) * S), outline=c, width=7 * S); sd.ellipse((16 * S, 16 * S, (2 * R - 16) * S, (2 * R - 16) * S), outline=c, width=2 * S)
            st = st.resize((2 * R, 2 * R), Image.LANCZOS); sd = ImageDraw.Draw(st)
            sd.text((R, R - 26), 'CHECKED', font=B.font('black', 30), fill=c, anchor='mm'); sd.text((R, R + 16), dt, font=B.font('black', 36), fill=c, anchor='mm')
            sd.text((R, R + 54), '已核實', font=B.font('zh', 26), fill=c, anchor='mm')
            st = ink_rough(st.rotate(12, resample=Image.BICUBIC), 17, 0.4)
            im.alpha_composite(st, (w - 2 * R - 20, h - 2 * R - 6))
            B._sc[key] = im
        pim = paper_img(w, h, 'white', B._sc[key], 'piece', seed=51)
        sc_ = 1.0 + 0.025 * ease(u / max(1, self.dur - sc['t0']))                               # slow push so the end never freezes
        y = max(250, 1262 - h * sc_) - (1 - eout(u / 0.4)) * 1300
        self.hang(fr, pim, 520, y, math.radians(self.tilts[3] * 0.5) + self.swing(t, sc['t0'] + 0.35, 0) * 0.0, 1.0, tag='bill', scale=sc_)
        if self.mj.get('dish_on_bill', True) and 1262 - h > 470:
            self.draw_dish(fr.cr, 880, 300, t, self.mj.get('dish', 'bowl'), 260)
        for i, r in enumerate(rows):
            self.log(fr, 'sum_row', (520 - w / 2 + 110, y + 160 + i * rh, 520 + w / 2 - 30, y + 160 + i * rh + 120))

    def scene_days(self, fr, t, sc):
        B.Reel.scene_days(self, fr, t, sc)

    def headline(self, fr, t): pass

    def fact_labels(self, fr, t):
        """the walking countdown etc: a small paper tag at the top-left with a gold tape piece"""
        for i, lb in enumerate(self.job.get('labels', [])):
            a0, a1 = self.T(lb['from']), self.T(lb['until'])
            if t < a0 - 0.01 or t >= a1: continue
            al = min(1, ease((a1 - t) / 0.2))
            key = ('tag', lb['en'], lb['zh'], lb.get('accent'))
            if key not in B._sc:
                c = stack([B.text_img(lb['en'], 'black', lb.get('size', 56), MC['red'] if lb.get('accent') == 'gold' else MC['ink']), B.text_img(lb['zh'], 'zh', int(lb.get('size', 56) * 0.85), MC['ink'])], gap=-10)
                B._sc[key] = paper_img(c.width + 50, c.height + 30, 'yellow' if lb.get('accent') == 'gold' else 'white', c, 'piece', seed=60 + i)
            im = B._sc[key]; inn = im.info['inner']
            u = t - a0; drop = 1 - eout(u / 0.25)
            x = SAFE[0] + inn[2] / 2 + 6; y = lb.get('y', 280) - drop * 300
            self.hang(fr, im, x, y, math.radians(-1.5 + (i % 3)) + self.swing(t, a0 + 0.2, 20 + i) * 0.5, al, tag='label:' + lb['en'] if drop < 0.05 else None)


def pil2cairo_cached(key, mk):
    if key not in _cs: _cs[key] = (pil2cairo(mk()), None)
    return _cs[key][0]



# =====================================================================================================================
# backdrop clip (brief section 10): one real Hong Kong clip, darkened, behind any world's signs / cards / page margin
# =====================================================================================================================
class _ClipReader:
    """sequential rgb24 reader at 30 fps, 1080x1920 cover-crop; restarts with a seek only when asked out of order"""
    def __init__(self, f, w=W, h=H):
        self.f, self.w, self.h = f, w, h; self.p = None; self.i = -10

    def get(self, ct, fps=30):
        import subprocess
        n = int(round(ct * fps))
        if self.p is None or n < self.i or n > self.i + 45:
            if self.p: self.p.kill()
            self.p = subprocess.Popen(['ffmpeg', '-v', 'error', '-threads', '1', '-ss', f'{n / fps:.3f}', '-i', self.f, '-vf',
                                       f'fps={fps},scale={self.w}:{self.h}:force_original_aspect_ratio=increase,crop={self.w}:{self.h}',
                                       '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], stdout=subprocess.PIPE)
            self.i = n - 1; self.last = None
        while self.i < n:
            b = self.p.stdout.read(self.w * self.h * 3)
            if len(b) < self.w * self.h * 3: break
            self.last = np.frombuffer(b, np.uint8).reshape(self.h, self.w, 3); self.i += 1
        return self.last


class Backdrop:
    """job.backdrop = {"clip": file, "start": s, "dim": 0.45-0.7, "blur": 0-6}. dim sets a tone curve (gamma 1+2*dim): mid-tones darken, highlights keep their light.
    If the Reel outlasts the clip it loops with a 0.6 s cross-fade from the tail into the head (never a visible jump)."""
    XF = 0.6

    def __init__(self, D, spec):
        import os, subprocess
        f = spec['clip']; self.f = f if os.path.isabs(f) else os.path.join(D, f)
        self.start = float(spec.get('start', 0)); self.dim = max(0.45, min(0.7, float(spec.get('dim', 0.55)))); self.blur = max(0.0, min(6.0, float(spec.get('blur', 0))))
        L = float(subprocess.run(['ffprobe', '-v', 'error', '-show_entries', 'format=duration', '-of', 'csv=p=0', self.f], capture_output=True, text=True).stdout)
        self.len = L - self.start - 0.1; self.A = _ClipReader(self.f); self.B = _ClipReader(self.f); self._c = {}

    def frame(self, t):
        P = self.len - self.XF; c = t % P if t >= self.len else t
        a = self.A.get(self.start + c).astype(np.float32)
        if t >= P and c < self.XF:                                   # cross-fade the tail into the head
            b = self.B.get(self.start + c + P).astype(np.float32); k = ease(c / self.XF); a = b * (1 - k) + a * k
        im = Image.fromarray((255.0 * (a / 255.0) ** (1 + 2 * self.dim)).clip(0, 255).astype(np.uint8))  # tone curve: mids dim, highlights stay lit
        if self.blur > 0: im = im.filter(ImageFilter.GaussianBlur(self.blur))
        return im.convert('RGBA')

    def paint(self, fr, t):
        s_ = pil2cairo(self.frame(t)); paint(fr.cr, s_, 0, 0, 1.0); _keep.pop()        # the buffer is used at once; do not keep it


# =====================================================================================================================
# NEON "signs" format: hanging do / don't signboards over the night skyline, no map (job.signs; see examples/)
# =====================================================================================================================
def cairo2pil(sf):
    w, h = sf.get_width(), sf.get_height(); st = sf.get_stride()
    a = np.frombuffer(sf.get_data(), np.uint8).reshape(h, st)[:, :w * 4].reshape(h, w, 4).astype(np.float32)
    al = a[..., 3:4]; rgbv = np.where(al > 0, a[..., [2, 1, 0]] * 255.0 / np.maximum(al, 1), 0)
    return Image.fromarray(np.concatenate([rgbv, al], -1).clip(0, 255).astype(np.uint8), 'RGBA')


def glow_self(img, size, gain=1.0):
    """sprite + glow in its own colours (two blurs), padded; info['pad']"""
    pad = int(size * 0.5); w, h = img.width + 2 * pad, img.height + 2 * pad
    base = Image.new('RGBA', (w, h), (0, 0, 0, 0)); base.alpha_composite(img, (pad, pad)); out = Image.new('RGBA', (w, h), (0, 0, 0, 0))
    for r, al in ((size * 0.30, 1.0 * gain), (size * 0.09, 1.4 * gain)):
        g = base.filter(ImageFilter.GaussianBlur(r)); g.putalpha(g.getchannel('A').point(lambda v, al=al: int(min(255, v * al))))
        out = Image.alpha_composite(out, g)
    out = Image.alpha_composite(out, base); out.info['pad'] = pad; return out


def picto(kind, col, w=230, h=170, lw=7):
    """neon line pictogram (<= 7 strokes, drawn in code), PIL RGBA w x h in the sign colour"""
    sf = cairo.ImageSurface(cairo.FORMAT_ARGB32, w, h); cr = cairo.Context(sf)
    cr.set_line_width(lw); cr.set_line_cap(cairo.LINE_CAP_ROUND); cr.set_line_join(cairo.LINE_JOIN_ROUND); cr.set_source_rgba(*rgb(col))

    def person(cx, top=6, bw=38, bot=h - 6, r=18, ang=0.0):
        cr.save(); cr.translate(cx, bot); cr.rotate(ang); cr.translate(-cx, -bot)
        hy = top + r; cr.new_sub_path(); cr.arc(cx, hy, r, math.pi / 2 + 0.55, math.pi / 2 - 0.55 + 2 * math.pi)
        sh = hy + r + 8; cr.line_to(cx + bw / 2, sh + 14); cr.line_to(cx + bw / 2, bot); cr.line_to(cx - bw / 2, bot); cr.line_to(cx - bw / 2, sh + 14); cr.close_path()
        cr.stroke(); cr.restore()

    if kind == 'queue':
        for i in range(5): person(23 + 46 * i)
    elif kind == 'cutin':
        for cx in (22, 66, 164, 208): person(cx)
        person(122, top=2, ang=math.radians(-24))
    elif kind == 'escalator':
        cr.move_to(2, h - 6); cr.line_to(30, h - 6); cr.line_to(w - 30, 6); cr.line_to(w - 2, 6); cr.stroke()
        dx, dy = (w - 60), -(h - 12); L = math.hypot(dx, dy); nx, ny = -dy / L, dx / L          # normal pointing right-down
        for u in (0.25, 0.5, 0.75):
            x = 30 + dx * u + nx * 30; y = h - 6 + dy * u + ny * 30
            cr.new_sub_path(); cr.arc(x, y, 13, 0, 2 * math.pi); cr.stroke()
    elif kind == 'cup':
        cr.move_to(72, 50); cr.line_to(158, 50); cr.stroke()
        cr.move_to(78, 58); cr.line_to(152, 58); cr.line_to(140, h - 6); cr.line_to(90, h - 6); cr.close_path(); cr.stroke()
        cr.move_to(122, 50); cr.line_to(138, 8); cr.line_to(166, 8); cr.stroke()
        cr.set_line_width(lw + 3)
        cr.move_to(36, 28); cr.line_to(194, h - 14); cr.stroke(); cr.move_to(194, 28); cr.line_to(36, h - 14); cr.stroke()
    elif kind == 'tea':
        cr.move_to(20, 88); cr.line_to(140, 88); cr.curve_to(140, 150, 20, 150, 20, 88); cr.close_path(); cr.stroke()
        cr.move_to(58, 146); cr.line_to(102, 146); cr.stroke()
        cr.move_to(10, h - 4); cr.line_to(w - 6, h - 4); cr.stroke()
        cr.move_to(70, 66); cr.curve_to(56, 50, 88, 34, 72, 14); cr.stroke()
    elif kind == 'chopsticks':
        cr.move_to(24, 96); cr.line_to(206, 96); cr.curve_to(206, 178, 24, 178, 24, 96); cr.close_path(); cr.stroke()
        cr.move_to(44, 90); cr.curve_to(70, 58, 160, 58, 186, 90); cr.stroke()
        cr.move_to(102, 4); cr.line_to(106, 76); cr.stroke(); cr.move_to(128, 4); cr.line_to(124, 76); cr.stroke()
    elif kind == 'bin':
        cr.move_to(30, 34); cr.line_to(150, 34); cr.stroke()
        cr.move_to(76, 34); cr.line_to(76, 14); cr.line_to(104, 14); cr.line_to(104, 34); cr.stroke()
        cr.move_to(40, 46); cr.line_to(140, 46); cr.line_to(128, h - 6); cr.line_to(52, h - 6); cr.close_path(); cr.stroke()
        cr.move_to(90, 66); cr.line_to(90, h - 24); cr.stroke()
        cr.save(); cr.translate(192, 104); cr.rotate(0.5); cr.rectangle(-14, -14, 28, 28); cr.stroke(); cr.restore()
        cr.move_to(186, 52); cr.line_to(190, 76); cr.stroke()
    sf.flush(); return cairo2pil(sf)


def badge(kind, col, d=76, lw=7):
    sf = cairo.ImageSurface(cairo.FORMAT_ARGB32, d, d); cr = cairo.Context(sf); r = d / 2
    cr.set_line_width(lw); cr.set_line_cap(cairo.LINE_CAP_ROUND); cr.set_line_join(cairo.LINE_JOIN_ROUND); cr.set_source_rgba(*rgb(col))
    cr.arc(r, r, r - lw, 0, 2 * math.pi); cr.stroke()
    if kind == 'tick': cr.move_to(r * 0.52, r * 1.02); cr.line_to(r * 0.86, r * 1.36); cr.line_to(r * 1.46, r * 0.66); cr.stroke()
    else: cr.move_to(r * 0.62, r * 0.62); cr.line_to(r * 1.38, r * 1.38); cr.stroke(); cr.move_to(r * 1.38, r * 0.62); cr.line_to(r * 0.62, r * 1.38); cr.stroke()
    sf.flush(); return cairo2pil(sf)


def zh_mix(parts, size, col):
    """one line mixing EN (xb) and ZH glyph runs: parts = [(text, kind, colour)]"""
    ims = [text_plain(t, k, size if k == 'zh' else int(size * 0.9), c) for t, k, c in parts]
    w = sum(i.width for i in ims) + 10 * (len(ims) - 1); h = max(i.height for i in ims)
    out = Image.new('RGBA', (w, h), (0, 0, 0, 0)); x = 0
    for i in ims: out.alpha_composite(i, (x, (h - i.height) // 2)); x += i.width + 10
    return out


class SignsReel(NeonReel):
    LOOK = 'neon'
    CAP_ZH = GOLD
    KCOL = dict(love='green', hate='pink', money='gold')
    SLOT = dict(top=420, bottom=760, mid=520, gold=850)
    SX, SW, SH = 80, 820, 280

    def __init__(self, D, fps=B.FPS):
        super().__init__(D, fps)
        self.bg = self._backdrop(); self.bg_s = pil2cairo(self.bg)
        st, i = [], 0
        for ln in self.job['lines']: st.append(i); i += len(ln['text'].split())
        self._st = st
        self.ev = []; rr = np.random.default_rng(3)
        for e in self.job['signs']:
            t0 = self._wt(e['at'], e['word']) if e.get('word') else self.T(e['at'])
            ev = dict(e, ds=t0 - 0.05, ls=self.T(e['until']) - (0.6 if e['until'] == self.job['scenes'][-1]['from'] else 0.45), y0=self.SLOT[e['slot']], col=self.KCOL[e['kind']],
                      ph=float(rr.uniform(0, 6.28)), per=float(rr.uniform(2.4, 3.0)), amp=math.radians(float(rr.uniform(1.0, 1.5))))
            ev['on'] = (self._wt(e['at'], e['on_word']) - 0.05) if e.get('on_word') else ev['ds'] + 0.34
            if e['kind'] == 'money' and e.get('on_word'): ev['ds'] = ev['on'] - 0.5          # money drops in just before its word, then flickers on
            if e.get('move'): ev['mv'] = (self.T(e['move']['at']) - 0.3, self.SLOT[e['move']['slot']])
            ev['content'], ev['box'], ev['w'], ev['h'], ev['x'] = self._content(ev)
            self.ev.append(ev)
        self.sum_t0 = next(sc['t0'] for sc in self.scenes if sc['kind'] == 'summary')
        self.board = self._board()

    def _wt(self, lref, word):
        li = int(lref[1:]) - 1; a = self._st[li]; n = len(self.job['lines'][li]['text'].split())
        norm = lambda s: re.sub(r'[^a-z0-9$]', '', s.lower())
        for w in self.words[a:a + n]:
            if norm(w[0]) == norm(word): return w[1]
        raise SystemExit(f'signs: word {word!r} not in {lref}')

    def tick_times(self):
        return [self.price_on] + [e['on'] for e in self.ev] + [self.sum_t0 + 0.34]

    # ----- backdrop: night street edges + harbour skyline + water, drawn once, drifting -----
    def _backdrop(self):
        BW, BH, HZ = W + 40, H + 60, 1190
        r = np.random.default_rng(21)
        yy = np.arange(BH)[:, None].astype(np.float32)
        def lerp(c0, c1, u): return np.array(c0, np.float32) + (np.array(c1, np.float32) - np.array(c0, np.float32)) * u
        sky = np.where(yy < 700, lerp((14, 22, 56), (34, 36, 92), yy / 700), lerp((34, 36, 92), (78, 52, 112), np.clip((yy - 700) / (HZ - 700), 0, 1)))
        img = np.repeat(sky[:, None, :], BW, 1).reshape(BH, BW, 3) * np.ones((1, BW, 1), np.float32)
        im = Image.fromarray(img.clip(0, 255).astype(np.uint8)); d = ImageDraw.Draw(im)
        ridge = [(0, 930)] + [(x, 900 - 70 * math.sin(x / 170) - 50 * math.sin(x / 61 + 1) - (90 if 300 < x < 640 else 0) * math.sin((x - 300) / 340 * math.pi)) for x in range(0, BW + 20, 20)] + [(BW, HZ), (0, HZ)]
        d.polygon(ridge, fill=(26, 26, 64))
        x = 0; towers = []
        while x < BW:
            bw = int(r.integers(44, 110)); bh = int(r.integers(110, 470)) if not (380 < x < 560) else int(r.integers(380, 560))
            towers.append((x, bw, bh)); x += bw + int(r.integers(0, 8))
        for (x, bw, bh) in towers:
            y0 = HZ - bh; d.rectangle((x, y0, x + bw, HZ), fill=(13, 18, 40))
            warm = r.random() < 0.5
            for wy in range(y0 + 12, HZ - 10, 18):
                for wx in range(x + 7, x + bw - 9, 13):
                    if r.random() < 0.58:
                        c = ((255, 226, 170) if r.random() < 0.7 else GOLD) if (warm if r.random() < 0.8 else not warm) else (190, 222, 255)   # some windows are brand gold
                        k = float(r.uniform(0.8, 1.0)); d.rectangle((wx, wy, wx + 7, wy + 9), fill=tuple(int(v * k) for v in c))
            if bh > 330: d.rectangle((x + bw // 2 - 2, y0 - 26, x + bw // 2 + 2, y0), fill=(60, 66, 100)); d.ellipse((x + bw // 2 - 5, y0 - 34, x + bw // 2 + 5, y0 - 24), fill=(255, 120, 120))
        haze = Image.new('RGB', im.size, (0, 0, 0)); ImageDraw.Draw(haze).rectangle((0, HZ - 140, BW, HZ + 20), fill=(60, 40, 90))
        im = ImageChops.add(im, haze.filter(ImageFilter.GaussianBlur(60)))
        # water: mirrored skyline, stretched and smeared, broken by ripples
        band = im.crop((0, HZ - 520, BW, HZ)).transpose(Image.FLIP_TOP_BOTTOM).resize((BW, BH - HZ), Image.BILINEAR)
        band = band.filter(ImageFilter.GaussianBlur(3)).resize((BW // 3, (BH - HZ) // 18), Image.BILINEAR).resize((BW, BH - HZ), Image.BILINEAR)
        wa = np.asarray(band).astype(np.float32) * 0.80
        rip = 0.72 + 0.28 * np.sin(np.arange(BH - HZ)[:, None] * (0.16 + 0.10 * np.arange(BH - HZ)[:, None] / (BH - HZ)) + np.sin(np.arange(BW)[None, :] / 53.0) * 1.6)
        fade = np.clip(1.0 - np.arange(BH - HZ)[:, None] / (BH - HZ) * 0.7, 0.3, 1)
        wa = wa * rip[..., None] * fade[..., None] + np.array((8, 14, 34), np.float32)
        out = np.asarray(im).astype(np.float32); out[HZ:] = wa
        out = Image.fromarray(out.clip(0, 255).astype(np.uint8)); d = ImageDraw.Draw(out)
        self._hz = HZ
        d.line((0, HZ, BW, HZ), fill=(120, 96, 150), width=2)
        for (x, bw, bh) in towers:                                       # broken light streaks under the brightest towers
            if bh < 260 and r.random() < 0.6: continue
            cx = x + bw / 2; c = GOLD if r.random() < 0.5 else (255, 230, 190)
            for yy_ in range(HZ + 6, BH, 9):
                dep = (yy_ - HZ) / (BH - HZ)
                if r.random() < 0.18 + 0.45 * dep: continue
                calm = yy_ >= 1180                                          # caption band and below: half the dashes, 60 % light (lead 24 Nov)
                if calm and r.random() < 0.5: continue
                hw = float(r.uniform(4, 16)) * (1 + dep * 1.5); jx = float(r.normal(0, 4 + 10 * dep)); k = (1.0 - 0.45 * dep) * (0.6 if calm else 1.0)
                d.rectangle((cx + jx - hw, yy_, cx + jx + hw, yy_ + 3), fill=tuple(int(v * k) for v in c))
        # near street: building edges at both sides with small windows
        for side in (0, 1):
            x0 = 0 if side == 0 else BW - 64
            d.rectangle((x0, 0, x0 + 64, BH), fill=(7, 10, 24)); d.rectangle((x0 + (62 if side == 0 else 0), 0, x0 + (64 if side == 0 else 2), BH), fill=(34, 44, 72))
            for row in range(0, BH // 46):
                for c in range(3):
                    if r.random() < 0.45: d.rectangle((x0 + 10 + c * 16, 24 + row * 46, x0 + 18 + c * 16, 38 + row * 46), fill=(255, 210, 130) if r.random() < 0.6 else (170, 210, 255))
        return out.convert('RGBA')

    def _paint_bg(self, fr, t):
        if self.bd: self.bd.paint(fr, t); return                               # real clip instead of the drawn skyline
        u = t / max(1.0, self.dur); paint(fr.cr, self.bg_s, -20 + 20 * u, -60 + 40 * u, 1.0)

    # ----- sign sprites -----
    def _content(self, e):
        col = NC[e['col']]
        if e['kind'] == 'money':
            w, h = 520, 210
            pz = 104
            while B.font('black', pz).getlength(e['en']) > w - 80 and pz > 80: pz -= 4
            pim = rich_img([(e['en'], True)], 'black', pz, NC['text'], GOLD)
            parts = [(p, 'zh' if has_zh(p) else 'xb', NC['text']) for p in e['zh'].split(' ', 2)]
            en_ = ' '.join(p for p in e['zh'].split() if not has_zh(p)); zh_ = ''.join(p for p in e['zh'].split() if has_zh(p))
            sub = zh_mix([(en_, 'xb', NC['text']), (zh_, 'zh', NC['text'])], 40, NC['text'])
            txt = stack([pim, sub], gap=-10, align='m'); g = glow_self(txt, 60)
            box = ((w - txt.width) / 2, (h - txt.height) / 2, (w + txt.width) / 2, (h + txt.height) / 2)
            return g, box, w, h, 280
        w, h = self.SW, self.SH; P = 30
        can = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        can.alpha_composite(badge('tick' if e['kind'] == 'love' else 'cross', col), (P + 4, 20))
        if e.get('icon'): can.alpha_composite(picto(e['icon'], col), (P + 6, h - 170 - 20))
        tx = P + 250; TW = w - tx - P
        sz, lines = wrap_fit(e['en'], 'xb', TW, list(range(64, 54, -2)), maxlines=2)
        en = [rich_img(l, 'xb', sz, NC['text'], GOLD) for l in lines]
        zs = 56
        while zs > 44 and B.font('zh', zs).getlength(e['zh']) > TW: zs -= 2
        zh = text_plain(e['zh'], 'zh', zs, mixc(NC['text'], col, 0.45))
        txt = stack(en + [zh], gap=-int(sz * 0.14), align='l')
        ty = (h - txt.height) // 2; can.alpha_composite(txt, (tx, ty))
        g = glow_self(can, 40, 0.55); box = (tx, ty, tx + txt.width, ty + txt.height)
        return g, box, w, h, self.SX

    def _hang(self, fr, x, y, w, h, col, content, k, unlit, ph, per, amp, t, tag=None, box=None, essential=True, dyn=None):
        cr = fr.cr; pad = 40; ang = amp * math.sin(2 * math.pi * t / per + ph)
        face = mixc(NC['face'], NC[col], 0.16 if not unlit else 0.05)
        sf = self._sign_surface(w, h, col, content, k, unlit, face=face)
        px, py = x + w / 2, y
        if not unlit and k > 0:
            cx_, cy_ = px, py + h / 2; R = max(w, h) * 0.8
            g = cairo.RadialGradient(cx_, cy_, R * 0.2, cx_, cy_, R); c_ = NC[col]
            g.add_color_stop_rgba(0, *rgb(c_, 0.22 * k)); g.add_color_stop_rgba(1, *rgb(c_, 0.0)); cr.set_source(g); cr.arc(cx_, cy_, R, 0, 2 * math.pi); cr.fill()
        cr.set_source_rgba(0.55, 0.6, 0.72, 0.85); cr.set_line_width(2.2)                  # two thin cords from above
        for cx in (x + 40, x + w - 40):
            dx = cx - px; x1 = px + dx * math.cos(ang); y1 = py + dx * math.sin(ang)
            cr.move_to(cx, -10); cr.line_to(x1, y1 + 3); cr.stroke()
        paint(cr, sf, px, py, 1.0, ang, pivot=(pad + w / 2, pad))
        if dyn:
            cr.save(); cr.translate(px, py); cr.rotate(ang); cr.translate(-w / 2, 0); dyn(cr); cr.restore()
        if tag and box and not unlit: self.log(fr, tag, (x + box[0], y + box[1], x + box[2], y + box[3]), essential)

    def _draw_sign(self, fr, s, t, k, dy, unlit=False, tag=None, essential=True):         # opening cluster, now on cords
        content = s.get('txt')
        if content is None and s.get('mark'): content = s['mark_im']
        box = None
        if content is not None:
            cw, ch = content.width - 2 * content.info['pad'], content.height - 2 * content.info['pad']
            box = ((s['w'] - cw) / 2, (s['h'] - ch) / 2, (s['w'] + cw) / 2, (s['h'] + ch) / 2)
        self._hang(fr, s['x'], s['y'] + dy, s['w'], s['h'], s['col'], content, k, unlit, s['ph'], s['per'], s['amp'], t, tag, box, essential)

    def _build_cluster(self):
        hd = self.job['headline']; pp = self.pp; cmap = {k: NC[v] for k, v in hd.get('colours', {}).items()}
        MW, inner = 660, 588
        sz, lines = wrap_fit(hd['en'].replace('{', '').replace('}', ''), 'xb', inner, list(range(96, 70, -2)))
        en = [rich_img([(w_, cmap.get(w_.strip(',.'), False)) for w_, _ in l], 'xb', sz, NC['text'], GOLD) for l in lines]
        zs = 60
        while zs > 56 and B.font('zh', zs).getlength(hd['zh']) > inner: zs -= 2
        zh = text_plain(hd['zh'], 'zh', zs, NC['text'])
        txt = stack(en + [zh], gap=-int(sz * 0.12), align='m'); self.main_txt = glow_self(txt, sz)
        MH = max(300, min(460, txt.height + 70))
        core = hd['zh_sign']; gs = 104 if len(core) <= 4 else 96
        gl = [text_plain(c, 'zh', gs, NC['text']) for c in core]
        vt = stack(gl, gap=-int(gs * 0.16), align='m'); self.tall_txt = glow_text_img(vt, NC['cyan'], gs)
        TH = max(560, vt.height + 70)
        pz = 112
        while B.font('black', pz).getlength(pp['price']) > 400 and pz > 80: pz -= 4
        pr = rich_img([(pp['price'], True)], 'black', pz, NC['text'], GOLD)
        l1 = rich_img([(w_, False) for w_ in pp['en'].split()], 'xb', 32, NC['text'], GOLD)
        l2 = text_plain(pp['zh'], 'zh', 34, NC['text'])
        pt = stack([pr, l1, l2], gap=-8, align='m'); self.price_txt = glow_self(pt, 60)
        rr = np.random.default_rng(8)
        def sw(): return dict(ph=float(rr.uniform(0, 6.28)), per=float(rr.uniform(2.4, 3.0)), amp=math.radians(float(rr.uniform(1.0, 1.5))))
        self.main = dict(x=60, y=330, w=MW, h=MH, col='text', txt=self.main_txt, **sw())
        self.tall = dict(x=728, y=300, w=176, h=TH, col='cyan', txt=self.tall_txt, **sw())
        py = self.main['y'] + MH + 48
        self.price = dict(x=78, y=py, w=470, h=max(250, pt.height + 40), col='gold', txt=self.price_txt, **sw())
        self.deco = []
        for i, (kd, cl) in enumerate((('tick', 'green'), ('cross', 'pink'))):
            m = glow_self(badge(kd, NC[cl], 84, 8), 40)
            self.deco.append(dict(x=586, y=py + 10 + i * 160, w=136, h=124, col=cl, txt=None, mark=kd, mark_im=m, **sw()))
        ci = text_plain(self.job['caveat']['text'], 'xb', 30, (236, 240, 250)); pl = Image.new('RGBA', (ci.width + 36, ci.height + 14), (0, 0, 0, 0))
        ImageDraw.Draw(pl).rounded_rectangle((0, 0, pl.width - 1, pl.height - 1), radius=16, fill=(8, 12, 28, 225)); pl.alpha_composite(ci, (18, 7))
        pl.info['inner'] = (18, 7, ci.width, ci.height); self.cav_im = pl                   # small dark plate: readable over the water lights
        self.cav_y = py + self.price['h'] + 22
        self.flicks = []

    def _blink(self, i, t):
        t0 = (0.5, 0.9)[i]; return 0.15 if 0 <= t - t0 < 0.13 else 1.0

    def hook_overlay(self, fr, t):
        if t >= self.E1: return
        u = self._rise(t); dy = -(u ** 1.6) * 1250
        self._draw_sign(fr, self.tall, t, 1.0, dy * 0.97, tag='headline_zh_sign', essential=u <= 0)
        for i, d in enumerate(self.deco):
            k = self._blink(i, t); self._draw_sign(fr, d, t, k, dy * 0.99)
            if k < 1: self.log(fr, 'blink', (d['x'], d['y'], d['x'] + d['w'], d['y'] + d['h']), False)
        on = flick_on(t - self.price_on)
        self._draw_sign(fr, self.price, t, 1.0 if on > 0.5 else 0.0, dy, unlit=on <= 0.5, tag='price_pin', essential=u <= 0)
        ca = ease((t - self.T(self.job['caveat']['at'])) / 0.25)
        if ca > 0:
            self.put_pil(fr, self.cav_im, self.price['x'] + 4, self.cav_y + dy, ca, tag='caveat', essential=u <= 0, anchor='lt')
        self._draw_sign(fr, self.main, t, 1.0, dy, tag='headline', essential=u <= 0)

    # ----- sign events after 3 s -----
    def _ypos(self, e, t):
        if t < e['ds']: return None, False
        y = e['y0']
        if e.get('mv') and t >= e['mv'][0]: y += (e['mv'][1] - y) * ease((t - e['mv'][0]) / 0.45)
        u = (t - e['ds']) / 0.5
        if u < 0.6: y -= 1250 * (1 - (u / 0.6) ** 2)
        elif u < 1.0: y -= 20 * math.sin(math.pi * (u - 0.6) / 0.4)
        moving = u < 1.0 or (e.get('mv') and e['mv'][0] <= t < e['mv'][0] + 0.45)
        if t >= e['ls']:
            v = (t - e['ls']) / 0.5
            if v >= 1: return None, False
            y -= 1400 * v ** 2.2; moving = True
        return y, not moving

    def _dyn(self, e, t):
        col = NC[e['col']]
        def stroke(cr, pts, c, k=1.0):
            cr.set_line_cap(cairo.LINE_CAP_ROUND); cr.set_line_join(cairo.LINE_JOIN_ROUND)
            for wd, al in ((22, 0.14), (12, 0.3), (7, 1.0)):
                cr.move_to(*pts[0]); [cr.line_to(*p) for p in pts[1:]]; cr.set_line_width(wd); cr.set_source_rgba(*rgb(c, al * k)); cr.stroke()
        ox, oy = 36, self.SH - 190                                                   # pictogram origin inside the sign
        if e.get('icon') == 'escalator':
            u = ease((t - e['on'] - 0.25) / 0.9); dx, dy_ = 170, -158; L = math.hypot(dx, dy_); nx, ny = dy_ / L, -dx / L   # left-up normal
            a = 0.12 + 0.6 * u; x = ox + 36 + dx * a + nx * 34; y = oy + 164 + dy_ * a + ny * 34
            ux, uy = dx / L, dy_ / L
            def f(cr):
                stroke(cr, [(x - ux * 60, y - uy * 60), (x, y)], NC['cyan'])
                stroke(cr, [(x - ux * 22 + nx * 16, y - uy * 22 + ny * 16), (x, y), (x - ux * 22 - nx * 16, y - uy * 22 - ny * 16)], NC['cyan'])
            return f
        if e.get('icon') == 'tea':
            def f(cr):
                for j, bx in enumerate((ox + 178, ox + 206)):
                    dd = 0.0
                    for tap in (0.35, 0.60):
                        v = (t - e['on'] - tap - j * 0.04) / 0.16
                        if 0 <= v < 1: dd = max(dd, math.sin(math.pi * v))
                    y0 = oy + 20 + dd * 56; stroke(cr, [(bx, y0), (bx, y0 + 88)], col)
            return f
        return None

    def _events(self, fr, t):
        for e in self.ev:
            y, settled = self._ypos(e, t)
            if y is None: continue
            if e['kind'] == 'money': k = flick_on(t - e['on']); unlit = k <= 0.5
            else: k = flick_on(t - e['on']) if t >= e['on'] else 0.0; unlit = t < e['on']
            tag = ('money' if e['kind'] == 'money' else 'sign:' + e['en'])
            self._hang(fr, e['x'], y, e['w'], e['h'], e['col'], e['content'], 1.0 if not unlit else 0.0, unlit, e['ph'], e['per'], e['amp'], t,
                       tag, e['box'], settled, dyn=None if unlit else self._dyn(e, t))

    # ----- cheat-sheet board -----
    def _board(self):
        S = self.job['summary']; w, h = 880, 1010; P = 30          # lead 24 Nov: board 10-15 % larger (glyphs x 70-890)
        can = Image.new('RGBA', (w, h), (0, 0, 0, 0))
        t1 = text_plain(S['title_en'], 'xb', 70, NC['text']); t2 = text_plain(S['title_zh'], 'zh', 62, mixc(NC['text'], NC['cyan'], 0.0))
        can.alpha_composite(t1, ((w - t1.width) // 2, P)); can.alpha_composite(t2, ((w - t2.width) // 2, P + t1.height - 6))
        y0 = P + t1.height + t2.height + 26; cw = (w - 3 * P) // 2
        for ci, (key, kd, cl) in enumerate((('love', 'tick', 'green'), ('avoid', 'cross', 'pink'))):
            x0 = P + ci * (cw + P); col = S[key]
            b = badge(kd, NC[cl], 66, 6); can.alpha_composite(b, (x0, y0)); hl = text_plain(col['en'], 'black', 56, NC[cl]); can.alpha_composite(hl, (x0 + 78, y0 + (66 - hl.height) // 2))
            y = y0 + 94
            for en_, zh_ in col['rows']:
                ez = 47
                while ez > 34 and B.font('xb', ez).getlength(en_.replace('{', '').replace('}', '')) > cw: ez -= 2
                r1 = rich_img(tok_split(en_), 'xb', ez, NC['text'], GOLD); can.alpha_composite(r1, (x0 - 4, y)); y += r1.height - 6
                if zh_: r2 = text_plain(zh_, 'zh', 42, mixc(NC['text'], NC[cl], 0.4)); can.alpha_composite(r2, (x0, y)); y += r2.height
                y += 30
        ft = S['foot']; fz = 26; f = B.font('semi', fz)
        lines_ = [ft] if f.getlength(ft) <= w - 2 * P else [ft[:ft.index(' · ')], ft[ft.index(' · ') + 3:]]
        yb = h - P - len(lines_) * 34
        for i, l in enumerate(lines_):
            li = text_plain(l, 'semi', fz, (200, 208, 228)); can.alpha_composite(li, ((w - li.width) // 2, yb + i * 34))
        g = glow_self(can, 30, 0.5); self.board_box = (P, P, w - P, h - P); self.board_w, self.board_h = w, h
        return g

    def _summary(self, fr, t):
        e = dict(ds=self.sum_t0 - 0.2, ls=99, y0=270); y, settled = self._ypos(e, t)          # drops in while the last signs lift out
        if y is None: return
        on = self.sum_t0 - 0.16; k = 1.0 if t >= on else 0.0      # the board drops in already lit (brightness)
        def bm(cr):
            bl = 0.35
            for tb in (0.75, 1.35):
                if 0 <= t - self.sum_t0 - tb < 0.22: bl = 1.0
            x, y_ = self.board_w - 70, 24
            cr.move_to(x, y_); cr.line_to(x + 40, y_); cr.line_to(x + 40, y_ + 56); cr.line_to(x + 20, y_ + 42); cr.line_to(x, y_ + 56); cr.close_path()
            cr.set_line_join(cairo.LINE_JOIN_ROUND)
            for wd, al in ((14, 0.2), (5, 1.0)): cr.set_line_width(wd); cr.set_source_rgba(1, 1, 1, al * bl); cr.stroke_preserve()
            cr.new_path()
        self._hang(fr, 40, y, self.board_w, self.board_h, 'text', self.board, k, t < on, 0.4, 2.8, math.radians(0.6), t,
                   'summary', self.board_box, settled, dyn=bm if t >= on else None)

    def frame(self, t):
        fr = Frame2(t); sc = self.scene_of(t)
        self._paint_bg(fr, t); self.hook_overlay(fr, t)
        if t >= self.E1 - 0.2: self._events(fr, t)
        self._summary(fr, t); self.captions(fr, t)
        self.timeline['frames'].append(dict(t=round(t, 3), scene=sc['kind'], map=False, look=self.LOOK, boxes=fr.boxes))
        return fr.image()

    def scene_signs(self, fr, t, sc): pass


REEL = dict(neon=NeonReel, menu=MenuReel)   # menu: queued, not shipped (qa blocks it)
FORMATS = {('neon', 'signs'): SignsReel}       # (look, job.format) -> special reel class


# =====================================================================================================================
# SKETCH (looks_v6_brief section 9): sketchbook on a desk; real place drawn in ink from a free photo, watercolour wash,
# camera push 2.4-3.0 s (no page flip, no pop-up layers); body pages on the same paper; notebook cheat-sheet.
# =====================================================================================================================
SK = dict(paper=(246, 238, 220), ink=(30, 30, 38), red=(200, 52, 40), blue=(150, 196, 222), green=(176, 206, 150),
          teal=(24, 92, 104), tape=(232, 222, 190), wood=(70, 44, 28), rule=(170, 196, 220), margin=(222, 120, 120))


class SketchMap(B.BaseMap):
    """the OSM vectors redrawn as ink on paper: pale blue water wash, pale green parks, thin ink roads, faint buildings"""
    def __init__(self, area, view, mpp=0.85, sand=None, detail=None):
        import os
        self.det = SketchMap(area, detail['view'], detail['mpp'], sand=sand) if detail else None   # sharper inset for close-ups
        self.det_mpp = detail.get('below', 1.2) if detail else 0
        self.sand = sand or []
        self.data = json.load(open(f'{B.T5}/osm/cache/{area}.json'))
        w, s, e, n = view; self.x0, self.y0 = B.mx(w), B.my(n); self.x1, self.y1 = B.mx(e), B.my(s)
        self.ppu = B.M_PER_UNIT / mpp
        self.Wb = int((self.x1 - self.x0) * self.ppu); self.Hb = int((self.y1 - self.y0) * self.ppu)
        cache = f'{B.T5}/osm/cache/{area}_{w}_{s}_{e}_{n}_{mpp}_sketch6{"_s" + str(len(self.sand)) if self.sand else ""}.png'
        if os.path.exists(cache): self.surf = cairo.ImageSurface.create_from_png(cache); return
        import cv2
        Wb, Hb = self.Wb, self.Hb
        P = lambda ll: ((B.mx(ll[0]) - self.x0) * self.ppu, (B.my(ll[1]) - self.y0) * self.ppu)
        def mask(polys):
            sf = cairo.ImageSurface(cairo.FORMAT_A8, Wb, Hb); cr = cairo.Context(sf); cr.set_fill_rule(cairo.FILL_RULE_EVEN_ODD)
            for rings in polys:
                for ring in rings:
                    for i, (x, y) in enumerate(map(P, ring)): (cr.move_to if i == 0 else cr.line_to)(x, y)
                    cr.close_path()
                cr.fill()
            sf.flush(); st = sf.get_stride()
            return np.frombuffer(sf.get_data(), np.uint8).reshape(Hb, st)[:, :Wb].copy()
        wm = mask(self.data['water']); wm = cv2.morphologyEx(wm, cv2.MORPH_CLOSE, np.ones((9, 9), np.uint8))   # closes tile seams
        pm = mask(self.data['park'])
        nz = cv2.GaussianBlur(cv2_noise(Hb, Wb, 41), (0, 0), 14) * 1.6; nz2 = cv2.GaussianBlur(cv2_noise(Hb, Wb, 42), (0, 0), 10) * 1.6
        paper = np.zeros((Hb, Wb, 4), np.float32)
        def lay(col, a):                                                     # paint a wash colour with alpha a over the layer
            nonlocal paper
            a = a[..., None]; c = np.array(col, np.float32)
            paper[..., :3] = paper[..., :3] * (1 - a) + c * a; paper[..., 3:] = paper[..., 3:] * (1 - a) + a
        # parks: loose pale green wash, blurred noisy edge, slightly off register
        pk = cv2.GaussianBlur(np.roll(pm, (5, -4), (0, 1)).astype(np.float32) / 255, (0, 0), 6)
        lay((182, 212, 156), np.clip((pk - 0.35 + 0.25 * nz2) / 0.3, 0, 1) * (0.55 + 0.15 * nz))
        if self.sand:                                                        # beaches: warm sand wash
            sm_ = cv2.GaussianBlur(mask([[r] for r in self.sand]).astype(np.float32) / 255, (0, 0), 3)
            lay((236, 212, 160), np.clip((sm_ - 0.3) / 0.3, 0, 1) * (0.7 + 0.15 * nz))
        # water: uneven wash, darker pooled edge at the coast
        wf = wm.astype(np.float32) / 255
        dist = cv2.distanceTransform((wm > 127).astype(np.uint8), cv2.DIST_L2, 5)
        wa = np.clip((cv2.GaussianBlur(wf, (0, 0), 2) - 0.5) / 0.2, 0, 1) * (0.62 + 0.18 * nz)
        lay((158, 200, 222), wa)
        edge = np.clip(1 - (dist - 6 * nz2) / 22, 0, 1) * (wm > 127)
        lay((112, 164, 198), edge * 0.5)
        rgba = np.zeros((Hb, Wb, 4), np.uint8)                              # cairo premultiplied BGRA
        a8 = paper[..., 3:]; pre = paper[..., :3]                               # lay() already accumulates premultiplied colour
        rgba[..., 0] = pre[..., 2]; rgba[..., 1] = pre[..., 1]; rgba[..., 2] = pre[..., 0]; rgba[..., 3] = (a8[..., 0] * 255)
        sf = cairo.ImageSurface(cairo.FORMAT_ARGB32, Wb, Hb); st = sf.get_stride()
        buf = np.frombuffer(sf.get_data(), np.uint8).reshape(Hb, st); buf[:, :Wb * 4] = rgba.reshape(Hb, Wb * 4); sf.mark_dirty()
        cr = cairo.Context(sf); cr.set_line_cap(cairo.LINE_CAP_ROUND); cr.set_line_join(cairo.LINE_JOIN_ROUND)
        r = np.random.default_rng(5)
        # coastline: one thicker, slightly wobbly ink line
        cs, _ = cv2.findContours((wm > 127).astype(np.uint8), cv2.RETR_LIST, cv2.CHAIN_APPROX_NONE)
        for c in cs:
            if len(c) < 60: continue
            pts = c[::6, 0, :].astype(np.float32); ph_ = r.uniform(0, 6.28)
            k = np.arange(len(pts)); pts = pts + np.stack([2.2 * np.sin(k / 9 + ph_), 2.2 * np.cos(k / 11 + ph_)], 1)
            pen = False
            for (x, y), (ox, oy) in zip(pts, c[::6, 0, :]):
                onb = ox <= 2 or oy <= 2 or ox >= Wb - 3 or oy >= Hb - 3
                if onb: pen = False; continue
                (cr.line_to if pen else cr.move_to)(float(x), float(y)); pen = True
            cr.set_line_width(4.2); cr.set_source_rgba(*rgb(SK['ink'], 0.85)); cr.stroke()
        widths = dict(motorway=4, trunk=3.6, primary=3.2, secondary=2.6, pier=2.6, pier_area=2.4)
        for cls in ('pier_area', 'pier', 'secondary', 'primary', 'trunk', 'motorway'):          # main roads + piers only
            for rd in self.data['roads']:
                if rd['c'] != cls: continue
                for i, (x, y) in enumerate(map(P, rd['pts'])): (cr.move_to if i == 0 else cr.line_to)(x + float(r.normal(0, 0.4)), y + float(r.normal(0, 0.4)))
                if cls == 'pier_area': cr.close_path()
                cr.set_line_width(widths[cls]); cr.set_source_rgba(*rgb(SK['ink'], 0.72)); cr.stroke()
        sf.write_to_png(cache); self.surf = sf

    def draw(self, cr, cam, blur=False, t=0.0):
        lon, lat, mpp = cam; s = (B.M_PER_UNIT / mpp) / self.ppu
        cx, cy = (B.mx(lon) - self.x0) * self.ppu, (B.my(lat) - self.y0) * self.ppu
        cr.save(); cr.translate(W / 2, H * 0.40); cr.scale(s, s); cr.translate(-cx, -cy)
        cr.set_source_surface(self.surf, 0, 0); cr.get_source().set_filter(cairo.FILTER_GOOD); cr.paint(); cr.restore()
        if self.det:                                                          # close-ups: cross-fade to the sharper inset
            a = min(1.0, max(0.0, (self.det_mpp - mpp) / (0.35 * self.det_mpp)))
            if a > 0:
                d = self.det; s2 = (B.M_PER_UNIT / mpp) / d.ppu
                cr.save(); cr.translate(W / 2, H * 0.40); cr.scale(s2, s2); cr.translate(-(B.mx(lon) - d.x0) * d.ppu, -(B.my(lat) - d.y0) * d.ppu)
                cr.rectangle(0, 0, d.Wb, d.Hb); cr.clip(); cr.push_group()
                cr.set_source_rgba(*rgb(SK['paper'])); cr.paint()
                cr.set_source_surface(d.surf, 0, 0); cr.get_source().set_filter(cairo.FILTER_GOOD); cr.paint()
                cr.pop_group_to_source(); cr.paint_with_alpha(a); cr.restore()


def _grain(h, w, seed, amp=6.0):
    r = np.random.default_rng(seed); g = r.normal(0, 1, (h, w)).astype(np.float32)
    g = np.asarray(Image.fromarray(((g * 40) + 128).clip(0, 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(0.7))).astype(np.float32) - 128
    return g / 40 * amp


B.F_EN.setdefault('hand', B.T5 + '/fonts/PatrickHand-Regular.ttf')   # OFL 1.1, fonts/PatrickHand_OFL.txt (Google Fonts repo)


class SketchReel(LookReel):
    LOOK = 'sketch'
    CAP_ZH = YEL if False else (255, 214, 10)
    PG = (40, 40, 1000, 1920)                      # hook page: x, y, w, h (flat), before tilt and push
    DR = (30, 30, 940, 620)                        # drawing rectangle inside the page (crop aspect ~1.52, a landscape photo)
    PUSH = 1.07; PIV = (520, 1050)
    SUM_PIC_B = 1212; SUM_CRED_B = 1226     # cheat-sheet: print bottom (incl. its transparent margin) and photo-credit baseline box bottom; captions start ~1268                 # pivot low so the type stays inside the hook safe zone while pushing

    def __init__(self, D, fps=B.FPS):
        super().__init__(D, fps)
        import os, sketch as SKM
        m = self.job.get('map')
        if m: self.map = SketchMap(m['area'], m['view'], m.get('mpp', 0.85), sand=m.get('sand'), detail=m.get('detail'))
        ph = (self.job.get('photos') or [None])[0]
        if not ph: raise SystemExit('sketch look: job.photos[0] {file,title,author,licence,url,crop,label_en,label_zh} is required')
        f = ph['file'] if os.path.isabs(ph['file']) else f'{D}/{ph["file"]}'
        dw, dh = self.DR[2], self.DR[3]
        sk = self.job.get('sketch', {})
        self.seeds = [tuple(s_) for s_ in sk.get('bloom_from', [[0.62, 0.62], [0.5, 0.12]])]
        subj = sk.get('subject')                                             # [x0,y0,x1,y1] crop-normalised: inked + half washed at 0.0 s
        self.ink, self.wash, self.order = SKM.make_layers(f, ph.get('crop'), dw, dh, ph.get('near'), ph.get('quiet'), cache_dir=f'{D}/.sketch_cache',
                                                           start=self.seeds[0], subject=subj, warm=bool(ph.get("warm_bare")))
        yy, xx = np.mgrid[0:dh, 0:dw].astype(np.float32)
        fe = np.clip((dh - 6 - yy + 40 * cv2_noise(dh, dw, 13)) / 70, 0, 1)    # soft bottom edge: the wash runs on into the page water
        self.wash = self.wash.copy(); self.wash[..., 3] = (self.wash[..., 3] * fe).astype(self.wash.dtype)
        if subj:
            inb = (xx >= subj[0] * dw) & (xx <= subj[2] * dw) & (yy >= subj[1] * dh) & (yy <= subj[3] * dh) & (self.ink > 0.2)
            self.p0 = float(np.percentile(self.order[inb], 99.5)) + 0.004 if inb.any() else sk.get('drawn_at_0', 0.6)
        else: self.p0 = sk.get('drawn_at_0', 0.6)
        self.ink_t1 = 1.0; self.pen_t1 = 1.0; self.w0, self.w1 = 1.0, 2.0       # lead round 1: rest of the ink 0-1.0 s, sky wash 1.0-2.0 s
        nz = cv2_noise(dh, dw, 11)
        sx, sy = self.seeds[0]; self.d0 = np.hypot(xx - sx * dw, yy - sy * dh) + nz * 50
        if subj: self.R0 = max(np.hypot((cx - sx) * dw, (cy - sy) * dh) for cx in (subj[0], subj[2]) for cy in (subj[1], subj[3])) * 0.8
        else: self.R0 = 0.35 * dw
        rest = self.seeds[1:] or [(0.5, 0.1)]
        self.bdist = np.min(np.stack([np.hypot(xx - qx * dw, yy - qy * dh) for qx, qy in rest]), 0) + nz * 60
        self.bmax = float(self.bdist.max())
        msk = self.ink > 0.3; self.pen_o = self.order[msk]; srt = np.argsort(self.pen_o)
        ys, xs = np.nonzero(msk); self.pen_xy = np.stack([xs[srt], ys[srt]], 1).astype(np.float32); self.pen_o = self.pen_o[srt]
        self.grain_page = _grain(self.PG[3], self.PG[2], 5)
        self.paper = (np.ones((self.PG[3], self.PG[2], 3), np.float32) * np.array(SK['paper'], np.float32) + self.grain_page[..., None])
        self.desk = self._desk(); self.pen = self._pen_img()
        self._build_hook_parts()
        self.paper = self._water_ext(self.paper, subj)
        sh_ = lambda im_: (lambda z: (z.putalpha(im_.getchannel('A').point(lambda v: int(v * 0.32))), z.filter(ImageFilter.GaussianBlur(7)))[1])(Image.new('RGBA', im_.size, (40, 26, 10, 0)))
        self.tape_sh = sh_(self.tape); self.price_sh = sh_(self.price_img)

    def _water_ext(self, paper, subj):
        """lead round 1+GO fix: the harbour water runs on down the page behind the tapes as a painted shape (ragged sides,
        narrowing body, 2-3 tongues at the bottom, small paper gaps), blooming downward 0.3-2.0 s behind the ink ripples"""
        import cv2
        ph_, pw_ = paper.shape[:2]; x0, y0, dw, dh = self.DR; top = y0 + dh - 120; bot = 1460
        self.ext_top, self.ext_bot = top, bot; L = bot - top
        r = np.random.default_rng(31); ys = np.arange(ph_, dtype=np.float32)
        def wob(seed):                                                     # 1-D ragged edge: several periods 50-190 px, amplitude 30-70
            g = np.random.default_rng(seed); v = np.zeros(ph_, np.float32)
            for per, amp in ((190, 26), (110, 18), (63, 12), (37, 6)):
                v += amp * g.uniform(0.7, 1.3) * np.sin(2 * np.pi * ys / (per * g.uniform(0.85, 1.15)) + g.uniform(0, 6.3))
            return v
        u = np.clip((ys - top) / L, 0, 1)
        xl = x0 + 40 + 150 * u ** 1.4 + wob(1)                             # body narrows toward the bottom
        xr = x0 + dw - 40 - 120 * u ** 1.3 + wob(2)
        xs = np.arange(pw_, dtype=np.float32)
        bt = np.full(pw_, 1265.0, np.float32)                              # bottom: broken into three uneven, rounded tongues
        for cx, wd, dep in ((x0 + 0.24 * dw, 120, 125), (x0 + 0.56 * dw, 150, 175), (x0 + 0.84 * dw, 95, 100)):
            bt = np.maximum(bt, 1265 + dep * np.exp(-np.abs((xs - cx) / wd) ** 3))
        g_ = np.random.default_rng(3).normal(0, 1, pw_ // 30 + 3)
        bt += np.interp(xs, np.arange(len(g_)) * 30, g_).astype(np.float32) * 9
        yy, xx = np.mgrid[0:ph_, 0:pw_].astype(np.float32)
        ins = (xx > xl[:, None]) & (xx < xr[:, None]) & (yy < bt[None, :]) & (yy > top)
        m = ins.astype(np.uint8) * 255
        for _ in range(7):                                                  # small unpainted paper gaps
            cx = int(r.integers(x0 + 120, x0 + dw - 160)); cy = int(r.integers(top + 220, 1260))
            cv2.ellipse(m, (cx, cy), (int(r.integers(10, 26)), int(r.integers(6, 15))), float(r.uniform(-20, 20)), 0, 360, 0, -1)
        mf = cv2.GaussianBlur(m.astype(np.float32) / 255, (0, 0), 1.6)
        nz = cv2.GaussianBlur(cv2_noise(ph_, pw_, 21), (0, 0), 16) * 1.8 + 0.5 * cv2.GaussianBlur(cv2_noise(ph_, pw_, 22), (0, 0), 6) * 1.6
        dist = cv2.distanceTransform((m > 127).astype(np.uint8), cv2.DIST_L2, 5)
        a = mf * (0.6 + 0.14 * nz) * np.clip((yy - top) / 110, 0, 1) * (1 - 0.3 * np.clip((yy - top) / L, 0, 1))
        ef = self.job.get('sketch', {}).get('ext_from')                    # optional: sample the run-on colour at a water point, not the bottom band
        wb = self.wash[max(0, int(ef[1] * dh) - 30):int(ef[1] * dh) + 30, max(0, int(ef[0] * dw) - 30):int(ef[0] * dw) + 30] if ef else self.wash[-90:]; m_ = wb[..., 3] > 60
        col = wb[..., :3][m_].reshape(-1, 3).astype(np.float32).mean(0) if m_.any() else np.array((150, 200, 205), np.float32)
        col = col * 0.7 + np.array(SK['paper'], np.float32) * 0.3
        edge = np.clip(1 - dist / 9, 0, 1) * (yy > top + 140)               # watercolour pools slightly darker at its edge
        self.ext_col = col[None, None, :] * (1 - 0.16 * edge[..., None])
        self.ext_a = a.astype(np.float32); self.ext_nz = nz
        self.ripples = []; tb = (20, 600, 560, 1200); tries = 0
        while len(self.ripples) < 9 and tries < 600:                          # crisp ink ripples, inside the paint
            tries += 1; n_ = len(self.ripples)
            yb = int(r.integers(top + 90, 1330)) if n_ % 2 else int(r.integers(1215, 1300)); L_ = int(r.integers(90, 200)); xb = int(r.integers(x0 + 20, x0 + dw - L_ - 20))
            if tb[0] < xb + L_ and xb < tb[2] and tb[1] < yb < tb[3]: continue
            if not (ins[yb, xb] and ins[yb, xb + L_]): continue
            pts = [(xb + q, yb + 3 * math.sin(q / 17 + n_)) for q in range(0, L_, 6)]
            self.ripples.append((pts, int(185 - 60 * (yb - top) / 800), 3 if yb < 1000 else 2, yb))
        return paper

    def _ext_front(self, t):
        """paint front (page y): top third at 0.0 s, then down to the bottom 0.3-2.0 s"""
        L = self.ext_bot - self.ext_top
        return self.ext_top + L / 3 + (2 * L / 3 + 40) * ease((t - 0.3) / 1.7)

    def _ext_time(self, y):
        L = self.ext_bot - self.ext_top; f = (y - self.ext_top - L / 3) / (2 * L / 3 + 40)
        if f <= 0: return 0.0
        lo, hi = 0.0, 1.0                                                   # invert ease
        for _ in range(30):
            mid = (lo + hi) / 2
            if ease(mid) < f: lo = mid
            else: hi = mid
        return 0.3 + 1.7 * lo

    # ---------- static art ----------
    def _desk(self):
        r = np.random.default_rng(2); yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        g = np.sin(xx / 9.0 + 3 * np.sin(yy / 160.0) + 1.5 * np.sin(yy / 47.0)) * 0.5 + 0.5
        n = _grain(H, W, 4, 1.0)
        base = np.array(SK['wood'], np.float32)
        img = base[None, None, :] * (0.78 + 0.22 * g[..., None]) + n[..., None] * 6
        return Image.fromarray(img.clip(0, 255).astype(np.uint8)).convert('RGBA')

    def _pen_img(self):
        L = 400; im = Image.new('RGBA', (L + 40, 80), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
        d.polygon([(20, 40), (62, 30), (62, 50)], fill=(40, 40, 44, 255))                  # tip cone
        d.rectangle((62, 26, 120, 54), fill=(205, 205, 210, 255))                          # metal grip
        d.rounded_rectangle((116, 22, L, 58), radius=16, fill=(28, 30, 36, 255))           # barrel
        d.rectangle((250, 22, 276, 58), fill=GOLD + (255,))                                 # gold band
        d.rectangle((120, 27, L - 10, 32), fill=(255, 255, 255, 60))
        im = im.rotate(-34, expand=True, resample=Image.BICUBIC)                            # pen points down-left to the tip
        a = np.asarray(im.getchannel('A')); ys, xs = np.nonzero(a > 200)
        self._pen_tip = (int(xs[np.argmin(xs + 0.2 * -ys)]), int(ys[np.argmin(xs + 0.2 * -ys)]))
        sh = Image.new('RGBA', im.size, (0, 0, 0, 0)); sh.putalpha(im.getchannel('A').point(lambda v: int(v * 0.35)))
        out = Image.new('RGBA', (im.width + 30, im.height + 30), (0, 0, 0, 0))
        out.alpha_composite(sh.filter(ImageFilter.GaussianBlur(6)), (22, 26)); out.alpha_composite(im, (0, 0))
        return out

    def _hand(self, s, size, col, kind='xb', hi_col=None):
        return ink_rough(B.text_img(s, kind, size, col, hi_col=hi_col), seed=len(s), strength=0.07)

    def _build_hook_parts(self):
        hd = self.job['headline']; en = hd['en'].replace('\n', ' ')
        sz, lines = wrap_fit(en, 'black', hd.get('max_w', 780), list(range(96, 70, -2)), 3)
        ims = [self._hand(' '.join(('{%s}' % w) if hi else w for w, hi in ln), sz, SK['ink'], 'black') for ln in lines]
        zh = self._hand(hd['zh'], max(56, hd.get('size_zh', 60)), SK['teal'], 'zh')
        def tight(im_, top=6, bot=10):
            bb = im_.getbbox(); return im_.crop((0, max(0, bb[1] - top), im_.width, min(im_.height, bb[3] + bot)))
        txt = stack([tight(i) for i in ims] + [tight(zh, 10, 8)], gap=12, align='l')
        tw, th = min(850, txt.width + 60), txt.height + 10
        tape = Image.new('RGBA', (tw, th), SK['tape'] + (235,)); td = ImageDraw.Draw(tape)
        r = np.random.default_rng(9)
        for x in (0, tw - 1):                                                              # torn ends
            for y in range(0, th, 6): td.rectangle((x - int(r.integers(0, 7)) if x else 0, y, x if x else int(r.integers(0, 7)), y + 6), fill=(0, 0, 0, 0))
        tape.alpha_composite(txt, (30, 2))
        self.tape = tape.rotate(2.5, expand=True, resample=Image.BICUBIC)
        lt = [tight(i) for i in ims]; ys_ = np.cumsum([0] + [i.height + 12 for i in lt]); free = [800 - 66 - i.width for i in lt]
        j_ = int(np.argmax(free)); self.cav_y = 2 + ys_[j_] + lt[j_].height // 2 + 6 if free[j_] > 330 else -40   # else: just above the tape
        self.tape_inner = (30, 2, txt.width, txt.height)
        # price: gold watercolour circle, dark hand-lettered number
        pp = self.job.get('price') or (self.job.get('map') or {}).get('price_pin') or {}
        self.pp = pp; R = 112; c = Image.new('RGBA', (2 * R + 40, 2 * R + 40), (0, 0, 0, 0))
        yy, xx = np.mgrid[0:c.height, 0:c.width].astype(np.float32); cx = cy = R + 20
        ang = np.arctan2(yy - cy, xx - cx); rr = R * (1 + 0.05 * np.sin(3 * ang + 1) + 0.03 * np.sin(7 * ang))
        dd = np.hypot(xx - cx, yy - cy); a = np.clip((rr - dd) / 3, 0, 1)
        rim = np.clip(1 - np.abs(rr - dd - 5) / 6, 0, 1)
        col = np.array(GOLD, np.float32)[None, None] * (1 - 0.18 * rim[..., None])
        ca = np.dstack([col, (a * (0.92 + 0.08 * rim) * 255)]).clip(0, 255).astype(np.uint8)
        c = Image.fromarray(ca, 'RGBA').filter(ImageFilter.GaussianBlur(1.2))
        num = self._hand(pp.get('price', ''), 84, SK['ink'], 'black')
        if num.width > 2 * R - 20: num = num.resize((2 * R - 20, int(num.height * (2 * R - 20) / num.width)), Image.LANCZOS)
        c.alpha_composite(num, ((c.width - num.width) // 2, (c.height - num.height) // 2 - 4))
        self.price_img = c; self.price_num_w = num.width; self.price_num_h = num.height
        cv = self.job.get('caveat', {}).get('text') or pp.get('en', '')
        ci = self._hl(cv, 50, SK['red']); self.cav_img = paper_img(ci.width + 24, ci.height + 4, (253, 250, 242), ci, tape='piece', seed=3)

    # ---------- hook page ----------
    def _quad(self, t):
        x, y, w, h = self.PG
        tilt = 1.0 - ease((t - 2.4) / 0.6); s = 1 + (self.PUSH - 1) * ease((t - 2.4) / 0.6)
        ins = 0.03 * w * tilt
        q = [(x + ins, y), (x + w - ins, y), (x + w, y + h), (x, y + h)]
        px, py = self.PIV
        return np.float32([(px + (qx - px) * s, py + (qy - py) * s) for qx, qy in q])

    def _hook_page(self, t):
        x0, y0, dw, dh = self.DR
        p = self.p0 + (1 - self.p0) * min(1.0, max(0.0, t / self.ink_t1))
        vis = np.clip((p - self.order) / 0.012, 0, 1) * self.ink
        r0 = self.R0 * (0.5 + 0.5 * ease(t / 0.9))                          # subject wash: half bloomed at 0.0 s
        m0 = np.clip((r0 - self.d0) / 40, 0, 1)
        r1 = self.bmax * ease((t - self.w0) / (self.w1 - self.w0)) * 1.08
        wm = np.maximum(m0, np.clip((r1 - self.bdist) / 40, 0, 1)) if t > self.w0 else m0
        pg = self.paper.copy(); e0, e1 = self.ext_top, min(self.PG[3], self.ext_bot + 40)
        yf = self._ext_front(t); yy_ = np.arange(e0, e1, dtype=np.float32)[:, None]
        bl = np.clip((yf - yy_ + 45 * self.ext_nz[e0:e1]) / 50, 0, 1)                     # the wash bloom, following the ripples
        ea = (self.ext_a[e0:e1] * bl)[..., None]; pg[e0:e1] = pg[e0:e1] * (1 - ea) + self.ext_col[e0:e1] * ea
        reg = pg[y0:y0 + dh, x0:x0 + dw]
        wa = (self.wash[..., 3:4].astype(np.float32) / 255) * wm[..., None]
        reg = reg * (1 - wa) + self.wash[..., :3].astype(np.float32) * wa
        reg = reg * (1 + self.grain_page[y0:y0 + dh, x0:x0 + dw, None] * 0.004)
        reg = reg * (1 - 0.92 * vis[..., None]) + np.array(SK['ink'], np.float32) * 0.92 * vis[..., None]
        pg[y0:y0 + dh, x0:x0 + dw] = reg
        im = Image.fromarray(pg.clip(0, 255).astype(np.uint8)).convert('RGBA')
        dr_ = ImageDraw.Draw(im)
        for pts, al, wd, yb in self.ripples:                                   # each ripple is inked 0.4 s before the paint reaches it
            k = ease((t - max(0.0, self._ext_time(yb) - 0.4)) / 0.15) if self._ext_time(yb) > 0 else 1.0
            if k > 0: dr_.line(pts[:max(2, int(len(pts) * k))], fill=SK['ink'] + (al,), width=wd, joint='curve')
        boxes = []
        # headline tape under the drawing, price circle on the drawing's lower right, caveat from 1.3 s
        tx = 36; ty = int(1196 - self.PG[1] - self.tape.height); im.alpha_composite(self.tape_sh, (tx + 7, ty + 11)); im.alpha_composite(self.tape, (tx, ty))
        tin = self.tape_inner; boxes.append(('headline', (tx + tin[0], ty + tin[1] - 20, tx + tin[0] + tin[2], ty + tin[1] + tin[3] + 20)))
        if self.pp:
            pcx, pcy = 730, (ty - 96 if self.cav_y > 0 else ty - 200); pi = self.price_img   # caveat above the tape: lift the circle clear of it
            im.alpha_composite(self.price_sh, (pcx - pi.width // 2 + 6, pcy - pi.height // 2 + 10)); im.alpha_composite(pi, (pcx - pi.width // 2, pcy - pi.height // 2))
            boxes.append(('price_pin', (pcx - self.price_num_w / 2, pcy - self.price_num_h / 2, pcx + self.price_num_w / 2, pcy + self.price_num_h / 2)))
            if t >= 1.3:
                k = ease((t - 1.3) / 0.25); cv = self.cav_img
                c2 = cv.copy(); c2.putalpha(c2.getchannel('A').point(lambda v: int(v * k)))
                cin = cv.info['inner']; cx_ = 832 - cin[0] - cin[2]; cy_ = ty + self.cav_y - cin[1] - cin[3] // 2; im.alpha_composite(c2, (int(cx_), int(cy_)))
                if k > 0.5: boxes.append(('caveat', (cx_ + cin[0], cy_ + cin[1], cx_ + cin[0] + cin[2], cy_ + cin[1] + cin[3])))
        if t >= self.w0 + 0.05: boxes.append(('wash', (x0 + 200, y0 + 200, x0 + 400, y0 + 400)))
        pen = None
        if t < self.pen_t1 + 0.3:
            i = int(np.searchsorted(self.pen_o, p)) - 1; i = max(0, min(len(self.pen_o) - 1, i))
            j0 = max(0, i - 12); px_, py_ = self.pen_xy[j0:i + 1].mean(0)
            off = max(0.0, t - self.pen_t1) / 0.3                         # pen lifts away after the last line, gone by 1.3 s
            pen = (x0 + px_ + off * 520, y0 + py_ + off * 260)
        return im, boxes, pen

    def hook_frame(self, fr, t):
        im, boxes, pen = self._hook_page(t)
        q = self._quad(t); x, y, w, h = self.PG
        import cv2
        src = np.float32([(0, 0), (w, 0), (w, h), (0, h)]); Hm = cv2.getPerspectiveTransform(src, q)
        arr = np.asarray(im); out = cv2.warpPerspective(arr, Hm, (W, H), flags=cv2.INTER_LINEAR, borderValue=(0, 0, 0, 0))
        sh = np.zeros((H, W), np.uint8); cv2.fillPoly(sh, [np.int32(q + np.float32([10, 16]))], 150)
        sh = cv2.GaussianBlur(sh, (0, 0), 14)
        base = np.asarray(self.desk).astype(np.float32); base[..., :3] *= (1 - sh[..., None] / 255.0 * 0.6)
        a = out[..., 3:4].astype(np.float32) / 255; base[..., :3] = base[..., :3] * (1 - a) + out[..., :3] * a
        frame_im = Image.fromarray(base.clip(0, 255).astype(np.uint8), 'RGBA')
        def T(px, py):
            v = Hm @ np.array([px, py, 1.0]); return v[0] / v[2], v[1] / v[2]
        if pen:
            sx, sy = T(*pen); frame_im.alpha_composite(self.pen, (int(sx - self._pen_tip[0]), int(sy - self._pen_tip[1])))
        fr.put(frame_im, 0, 0, 1.0, log=False) if False else fr.sprites.append((frame_im, 0, 0, 1.0))
        for tag, (a0, b0, a1, b1) in boxes:
            pts = [T(a0, b0), T(a1, b0), T(a1, b1), T(a0, b1)]
            self.log(fr, tag, (min(p[0] for p in pts), min(p[1] for p in pts), max(p[0] for p in pts), max(p[1] for p in pts)), tag != 'wash')

    # ---------- body pages ----------
    def paint_panel_bg(self, fr, t, sc, ruled=False):
        key = ('skpage', ruled)
        if key not in _cs:
            pw, ph = W - 24, H - 14
            pg = np.ones((ph, pw, 3), np.float32) * np.array(SK['paper'], np.float32) + _grain(ph, pw, 8)[..., None]
            im = Image.fromarray(pg.clip(0, 255).astype(np.uint8)).convert('RGBA'); d = ImageDraw.Draw(im)
            if ruled:
                for yy in range(300, ph, 64): d.line((0, yy, pw, yy), fill=SK['rule'] + (255,), width=2)
                d.line((70, 0, 70, ph), fill=SK['margin'] + (255,), width=2)
            can = self.desk.copy(); sh = Image.new('RGBA', (W, H), (0, 0, 0, 0)); ImageDraw.Draw(sh).rectangle((18, 26, W - 4, H), fill=(0, 0, 0, 120))
            can.alpha_composite(sh.filter(ImageFilter.GaussianBlur(10))); can.alpha_composite(im, (12, 14))
            tp = Image.new('RGBA', (190, 46), GOLD + (215,)).rotate(-38, expand=True, resample=Image.BICUBIC)   # gold washi tape corner
            can.alpha_composite(tp, (W - tp.width + 28, -22))
            _cs[key] = (pil2cairo(can), can)
        paint(fr.cr, _cs[key][0], 0, 0, 1.0)
        return False

    def panel(self, fr, x, y, w, h, al=1.0, col=None):
        cr = fr.cr; cr.save()
        cr.set_source_rgba(0.2, 0.14, 0.06, 0.18 * al); cr.rectangle(x + 6, y + 10, w, h); cr.fill()
        cr.set_source_rgba(*rgb((253, 250, 242), al)); cr.rectangle(x, y, w, h); cr.fill()
        cr.set_source_rgba(*rgb(SK['tape'], 0.9 * al)); cr.translate(x + w / 2, y + 4); cr.rotate(math.radians(-2)); cr.rectangle(-70, -18, 140, 34); cr.fill()
        cr.restore()

    def scene_map(self, fr, t, sc, cam=None):
        self.paint_panel_bg(fr, t, sc); cr = fr.cr; cam = cam or self.cam(t)
        cr.save(); cr.rectangle(12, 14, W - 24, H - 14); cr.clip()
        self.map.draw(cr, cam, t=t); S = self.map.to_screen(cam); self._mapdrawn = True
        allp = smooth([S(p) for p in self.route_all()]); done = sub_path(allp, self.progress(t))
        stroke_path(cr, allp, 3, rgb(SK['red'], 0.25), dash=[14, 12])
        stroke_path(cr, done, 7, rgb(SK['red'], 0.92), dash=[18, 11])                       # red pencil dashes draw on
        for p_ in self.job['map'].get('pins', []):
            if t >= self.T(p_.get('from', 0)):
                x, y = S(p_['at']); cr.set_line_width(5); cr.set_source_rgba(*rgb(SK['ink'])); cr.arc(x, y, 16, 0, 2 * math.pi); cr.stroke()
                cr.set_source_rgba(*rgb(GOLD)); cr.arc(x, y, 10, 0, 2 * math.pi); cr.fill()
        (lon, lat), ang, mode = self.traveller(t); x, y = S((lon, lat))
        if mode == 'ferry': B.draw_boat(cr, x, y, ang, t, 1.2)
        elif mode == 'bus': self._bus(cr, x, y)
        else: B.draw_guide(cr, x, y, t, walking=self.progress(t + 0.05) > self.progress(t) + 1e-5, scale=0.9)
        cr.restore()
        self.map_labels(fr, t, S)

    def _bus(self, cr, x, y):
        """a small hand-inked bus (gold body, ink outline) riding the red pencil line"""
        cr.save(); cr.translate(x, y - 30)
        rrect(cr, -44, -26, 88, 52, 10); cr.set_source_rgba(*rgb(GOLD)); cr.fill_preserve(); cr.set_line_width(4); cr.set_source_rgba(*rgb(SK['ink'])); cr.stroke()
        for k in range(3): rrect(cr, -36 + k * 25, -18, 20, 16, 3); cr.set_source_rgba(*rgb((250, 248, 238))); cr.fill_preserve(); cr.set_line_width(2.5); cr.set_source_rgba(*rgb(SK['ink'])); cr.stroke()
        for wx in (-26, 26): cr.arc(wx, 26, 8, 0, 2 * math.pi); cr.set_source_rgba(*rgb(SK['ink'])); cr.fill()
        cr.restore()

    def _hl(self, txt, size, col, maxw=None):
        """Patrick Hand line; glyphs it lacks (arrows) fall back to Montserrat so nothing drops out"""
        from fontTools.ttLib import TTFont
        if not hasattr(self, '_hcmap'): self._hcmap = set(TTFont(B.F_EN['hand'])['cmap'].getBestCmap())
        parts = []; cur = ''; kind = 'hand'
        for ch in txt:
            k = 'hand' if (ord(ch) in self._hcmap or ch == ' ') else ('zh' if ord(ch) >= 0x2E80 else 'xb')
            if ch == ' ' and kind == 'zh': k = 'zh'
            if k != kind and cur: parts.append((kind, cur)); cur = ''
            kind = k; cur += ch
        if cur: parts.append((kind, cur))
        if len(parts) == 1 and parts[0][0] == 'hand': return B.fit_img(txt, 'hand', size, col, maxw) if maxw else B.text_img(txt, 'hand', size, col)
        ims = [B.text_img(t_, k_, size if k_ == 'hand' else int(size * (0.72 if k_ == 'zh' else 0.8)), col) for k_, t_ in parts]
        w_ = sum(i.width for i in ims); h_ = max(i.height for i in ims); out = Image.new('RGBA', (w_, h_), (0, 0, 0, 0)); x_ = 0
        for i in ims: out.alpha_composite(i, (x_, (h_ - i.height) // 2)); x_ += i.width
        if maxw and out.width > maxw: out = out.resize((maxw, int(out.height * maxw / out.width)), Image.LANCZOS)
        return out

    def _snapshot(self, pw=430):
        """the finished washed sketch (the 2.2 s picture) as a small print: cream border, two tape corners, shadow, -3 degrees"""
        key = ('sksnap', pw)
        if key in B._sc: return B._sc[key]
        x0, y0, dw, dh = self.DR; a = self.wash[..., 3:4].astype(np.float32) / 255
        reg = np.ones((dh, dw, 3), np.float32) * np.array(SK['paper'], np.float32)
        reg = reg * (1 - a) + self.wash[..., :3] * a; reg = reg * (1 - 0.92 * self.ink[..., None]) + np.array(SK['ink'], np.float32) * 0.92 * self.ink[..., None]
        ph = Image.fromarray(reg.clip(0, 255).astype(np.uint8)).resize((pw - 20, int((pw - 20) * dh / dw)), Image.LANCZOS)
        card = Image.new('RGBA', (pw, ph.height + 20), (252, 249, 240, 255)); card.paste(ph, (10, 10))
        m = 40; can = Image.new('RGBA', (card.width + 2 * m, card.height + 2 * m), (0, 0, 0, 0))
        sh = Image.new('RGBA', can.size, (0, 0, 0, 0)); ImageDraw.Draw(sh).rectangle((m + 7, m + 11, m + 7 + card.width, m + 11 + card.height), fill=(40, 26, 10, 90))
        can.alpha_composite(sh.filter(ImageFilter.GaussianBlur(8))); can.alpha_composite(card, (m, m))
        for (cx, cy, ang) in ((m + 6, m + 4, 40), (m + card.width - 6, m + card.height - 4, 40)):
            tp = Image.new('RGBA', (110, 32), SK['tape'] + (225,)).rotate(ang, expand=True, resample=Image.BICUBIC)
            can.alpha_composite(tp, (int(cx - tp.width / 2), int(cy - tp.height / 2)))
        can = can.rotate(3, expand=True, resample=Image.BICUBIC)        # PIL: positive = counter-clockwise = -3 degrees on screen
        B._sc[key] = can; return can

    def map_labels(self, fr, t, S):
        m = self.job['map']
        for lb in m.get('labels', []):
            a0 = self.T(lb.get('from', 0)); a1 = self.T(lb['until']) if 'until' in lb else 1e9
            for ph_ in getattr(self, 'phrases', []):                      # full opacity by the time its name is spoken
                if lb['en'].lower() in ph_[0].lower() and a0 - 3.0 < ph_[1] < a0 + 0.35 and ph_[1] < a1: a0 = ph_[1] - 0.35; break
            al = min(ease((t - a0) / 0.3), ease((a1 - t) / 0.3))
            if al <= 0: continue
            x, y = S(lb['at']); dx, dy = lb.get('off', (0, -70)); sz = lb.get('size', 38)
            rows_ = [self._hl(lb['en'], int(sz * 1.25), SK['ink'])] + ([self._hl(lb['en2'], int(sz * 1.25), SK['ink'])] if lb.get('en2') else []) \
                + ([self._hand(lb['zh'], int(sz * 0.92), SK['teal'], 'zh')] if lb.get('zh') else [])
            content = stack(rows_, gap=-10)
            im = paper_img(content.width + 36, content.height + 18, (253, 250, 242), content, tape='piece', seed=len(lb['en']))
            fr.put(im, x + dx, y + dy, al, anchor=lb.get('anchor', 'mb'), tag='maplabel:' + lb['en'], clamp=True)

    def osm_credit(self, fr, alpha=1.0):
        key = ('osm_sk',)
        if key not in B._sc:
            f = font('semi', 24); txt = '© OpenStreetMap contributors'; tw = int(f.getlength(txt)) + 16
            im = Image.new('RGBA', (tw, 40), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
            d.text((8, 6), txt, font=f, fill=SK['ink'] + (255,), stroke_width=3, stroke_fill=(250, 246, 234, 240)); B._sc[key] = im
        y_ = getattr(self, '_osm_y', None) or 1418; self._osm_y = None           # cheat-sheet: under the photo credit, above the captions
        fr.put(B._sc[key], SAFE[0], y_, alpha, anchor='lb', tag='osm_credit', essential=False)

    def fact_labels(self, fr, t):
        """screen-fixed map tag (e.g. bus number + fare) as a taped paper label in the hand lettering, price on the gold highlighter"""
        for i, lb in enumerate(self.job.get('labels', [])):
            a0, a1 = self.T(lb['from']), self.T(lb['until'])
            al = min(ease((t - a0) / 0.25), ease((a1 - t) / 0.25))
            if al <= 0: continue
            key = ('sktag', lb['en'], lb.get('zh'))
            if key not in B._sc:
                pr = (self.pp or {}).get('price', '')
                en = lb['en'].replace(pr, '{%s}' % pr) if pr and pr in lb['en'] else lb['en']
                rows_ = [ink_rough(B.text_img(en, 'hand', lb.get('size', 68), SK['ink'], hi_col=GOLD), seed=5, strength=0.05)]
                if lb.get('zh'): rows_.append(self._hand(lb['zh'], int(lb.get('size', 68) * 0.78), SK['teal'], 'zh'))
                c = stack(rows_, gap=-6)
                B._sc[key] = paper_img(c.width + 44, c.height + 24, (253, 250, 242), c, tape='piece', seed=70 + i)
            fr.put(B._sc[key], SAFE[0], lb.get('y', 280) + (1 - al) * -20, al, anchor='lt', tag='label:' + lb['en'])

    def scene_summary(self, fr, t, sc):
        """notebook cheat-sheet: ruled page, 3-4 facts lettered by hand, the price circled in gold, a paper clip, photo credits"""
        self.paint_panel_bg(fr, t, sc, ruled=True); cr = fr.cr; u = t - sc['t0']
        x0 = 100; y = 260                                                    # starts higher so print + both credits fit above the caption band
        fr.put(self._hl(sc['title_en'], 84, SK['ink'], 800), x0, y - 8, ease(u / 0.3), tag='sum_title'); y += 86
        fr.put(self._hand(sc['title_zh'], 56, SK['teal'], 'zh'), x0, y, ease(u / 0.3), tag='sum_title_zh'); y += 108
        price = (self.pp or {}).get('price', ''); nr = len(sc['rows'][:4]); step = 128 if nr <= 3 else 108
        for i, r in enumerate(sc['rows'][:4]):
            k = ease((u - 0.15 - i * 0.12) / 0.3)
            rc = SK['red'] if r.get('col') == 'red' else SK['ink']                         # a row may be lettered in red pencil
            vi = self._hl(r.get('value', ''), 68 if nr <= 3 else 60, rc, 440) if r.get('value') else None
            lw = 800 - (vi.width + 20 if vi else 0)
            fr.put(self._hl(r['en'], 50, rc, lw), x0, y - 6, k, tag='sum_row')
            fr.put(B.fit_img(r['zh'], 'zh', 36, SK['red'] if r.get('col') == 'red' else SK['teal'], lw), x0, y + 54, k, tag='sum_row_zh')
            if vi:
                vx = 900 - vi.width; fr.put(vi, vx, y + 2, k, tag='sum_val')
                if price and price.replace('HK$', '') in r['value'] and i == 0:                # the price circled in gold
                    cr.save(); cr.translate(vx + vi.width / 2, y + 2 + vi.height / 2); cr.scale(vi.width / 2 + 26, vi.height / 2 + 14)
                    cr.arc(0, 0, 1, math.radians(-200), math.radians(150)); cr.restore()
                    cr.set_source_rgba(*rgb(GOLD, 0.95 * k)); cr.set_line_width(9); cr.set_line_cap(cairo.LINE_CAP_ROUND); cr.stroke()
            y += step
        # paper clip, top left
        cr.save(); cr.set_line_width(7); cr.set_source_rgba(0.55, 0.57, 0.62, 1); cr.translate(150, 230); cr.rotate(math.radians(-8))
        rrect(cr, 0, -90, 46, 170, 23); cr.stroke(); rrect(cr, 10, -70, 26, 120, 13); cr.stroke(); cr.restore()
        if sc.get('foot'): fr.put(self._hl(sc['foot'], 35, (90, 90, 100), 800), x0, y + 2, ease(u / 0.4), tag='sum_foot')
        pic = self._snapshot(400 if nr <= 3 else 285); fl = 8 * math.sin(2 * math.pi * max(0.0, u - 0.65) / 4.0)   # the taped print floats gently so the held card never freezes
        fr.put(pic, 950 - fl, self.SUM_PIC_B + 0.25 * fl, ease((u - 0.3) / 0.35), anchor='rb', tag='sketch_pic', essential=False)   # the finished sketch, taped
        cy = self.SUM_CRED_B                                                 # photo credit(s) end here; the OSM credit sits directly under, both above the captions
        for ph in reversed(self.job.get('photos', [])):
            line = f"Sketch from photo by {ph['author']}, {ph['licence']}, {ph.get('platform', 'Wikimedia Commons')}"
            im = B.fit_img(line, 'zh' if any(ord(c_) > 0x2E7F for c_ in line) else 'semi', 24, (70, 70, 80), 820); fr.put(im, SAFE[0], cy, 1.0, anchor='lb', tag='photo_credit', essential=False); cy -= 32   # CJK author names need the zh font
        self._osm_y = self.SUM_CRED_B + 34
        if self.map: self._mapdrawn = True

    def frame(self, t):
        fr = Frame2(t); sc = self.scene_of(t); self._mapdrawn = False
        if t < 3.0: self.hook_frame(fr, t)
        else: self.paint_scene(fr, t, sc)
        md = self._mapdrawn
        if md: self.osm_credit(fr)
        if t >= 3.0: self.fact_labels(fr, t)
        self.captions(fr, t)
        im = fr.image(); i0 = self.scenes.index(sc)
        if t >= 3.0 and i0 > 0 and t - max(3.0, sc['t0']) < 0.22 and sc['t0'] > 3.0:
            prev = self.frame_scene(self.scenes[i0 - 1], t)
            im = Image.blend(prev, im, ease((t - sc['t0']) / 0.22))
        self.timeline['frames'].append(dict(t=round(t, 3), scene='hook' if t < 3.0 else sc['kind'], map=md, look=self.LOOK, boxes=fr.boxes))   # 0-3 s is the sketch hook, not a map
        return im

    def frame_scene(self, sc, t):
        fr = Frame2(t); self._mapdrawn = False; self.paint_scene(fr, t, sc)
        if self._mapdrawn: self.osm_credit(fr)
        self.fact_labels(fr, t); self.captions(fr, t); return fr.image()


def cv2_noise(h, w, seed):
    r = np.random.default_rng(seed); n = r.random((h // 24 + 2, w // 24 + 2)).astype(np.float32)
    return np.asarray(Image.fromarray((n * 255).astype(np.uint8)).resize((w, h), Image.BICUBIC)).astype(np.float32) / 255 - 0.5


REEL['sketch'] = SketchReel
