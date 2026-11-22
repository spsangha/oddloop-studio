"""Hook gate for Kinda Wild Films (research/hook_spec.md, "Ten-Point Automated Pass/Fail Gate").

    python3 kwhook.py gate  <ep.py | cues.json> [frames_dir] [--tts] [--sheet out.png]

* ep.py written with kwkit -> cues come straight from the episode (no Blender needed).
  Any other episode: first run  blender -b -P ep_x.py -- --cues /tmp/cues.json  and pass the json.
* --tts      ask the voice service for the real word timings (needs network; same voice as post_kw) -> checks
             words spoken in 0-3 s and the end cut. Without it, timings are estimated (3.6 words/s).
* frames_dir PNG frames from a preview render (any PCT). Needs f0000, f0004, f0012, f0024, f0036, f0048, f0060, f0072
             and the last frame. Adds the picture checks and makes the labelled contact sheet (captions burned in,
             same grade/caption code as post_kw, so what you see is what the final video shows).

Prints one PASS/FAIL line per gate item. Items a script cannot judge (subject >= 45 %, ceiling, colour separation,
mute read, render defects) are printed as LOOK lines: a human/vision reviewer answers them from the sheet (kit/kw_card.md).
Exit code 1 if any automated item fails.
"""
import sys, os, json, math, re, glob
HERE = os.path.dirname(os.path.abspath(__file__)); sys.path.insert(0, HERE)

TRANSIENT = {'thud', 'pinch', 'bounce', 'rip', 'sneeze', 'crackle', 'pop', 'cough', 'gulp', 'beep', 'step', 'squelch', 'heartbeat'}
FILLER = ('so today', 'did you know', 'have you ever', 'this is the story', 'meet ', 'while he was', 'while she was', 'one day')
SHEET_FRAMES = (0, 4, 12, 24, 36, 48, 60, 72)
GATE = dict(onset_max=0.06, onset_hard=0.12, hook_words=12, words_0_3=(8, 11), cap_y=(0.66, 0.72), end_tail=0.2,
            first_shot_max=1.1, inside_by=1.2, cuts_0_3=2, lum0=(65, 210), mae_1s=35, mae_f12=10, loop_mae=55)


def load_cues(src):
    if src.endswith('.json'): return json.load(open(src))
    os.environ.setdefault('KW_NOCHECK', '1')
    import kwkit as KW
    eps = []; KW.Episode.run = lambda self: eps.append(self)
    exec(compile(open(src).read(), src, 'exec'), {'__name__': '__main__', '__file__': os.path.abspath(src)})
    return eps[0].cues()


def word_times(cj, use_tts, vo_json=None):
    """[(start, end, word)] absolute, as post_kw will place them.  Order: --tts (live voice) > the episode's .vo.json word
    timings written by kwvo.py (same voice, same trim) > an estimate at 3.6 words/s."""
    if use_tts:
        import post_kw
        _, words = post_kw.tts(cj); return words
    if vo_json and os.path.exists(vo_json):
        vj = json.load(open(vo_json)); ws = vj.get('words')
        if ws and vj.get('trim') and [l for l in vj.get('lines', [])] == [t for _, t in cj['vo']] and len(ws) == len(cj['vo']):
            return [(t0 + a, t0 + b, w) for (t0, _), line in zip(cj['vo'], ws) for a, b, w in line]
    out = []
    for t0, text in cj['vo']:
        for i, w in enumerate(text.split()): out.append((t0 + i / 3.6, t0 + (i + 0.9) / 3.6, w))
    return out


def script_items(cj, words):
    res = []; hk = cj.get('hook', {}); vo = cj['vo']
    s1 = vo[0][1]; w1 = s1.split(); low = [re.sub(r'[^a-z0-9]', '', w.lower()) for w in w1]
    inj = [re.sub(r'[^a-z0-9]', '', w.lower()) for w in hk.get('injury', '').split()]
    at = next((i for i in range(len(low)) if inj and low[i:i + len(inj)] == inj), None)
    ok = at is not None and at + len(inj) <= GATE['hook_words'] and not any(f in s1.lower() for f in FILLER)
    res.append(('6a hook names the injury in <= 12 words', ok, f"injury {hk.get('injury')!r} ends at word {None if at is None else at + len(inj)}; sentence 1 = {len(w1)} words"))
    onset = vo[0][0] + (0.012 if cj.get('vo_trim') else 0.18)
    res.append(('6b voice onset <= 60 ms (hard limit 120)', cj.get('vo_trim', False) and onset <= GATE['onset_max'] + 0.012,
                f"line 1 at {vo[0][0]:.3f}s, vo_trim={cj.get('vo_trim', False)} -> about {onset * 1000:.0f} ms"))
    n03 = sum(1 for a, b, w in words if a < 3.0)
    res.append(('6c 8-11 words spoken in 0-3 s', GATE['words_0_3'][0] <= n03 <= GATE['words_0_3'][1], f'{n03} words start before 3.0 s'))
    cy = cj.get('cap_y', 0.78)
    res.append(('5 caption on frame 0, 28-34 % up from the bottom', bool(cj.get('cap_lead0')) and vo[0][0] < 0.3 and GATE['cap_y'][0] <= cy <= GATE['cap_y'][1],
                f"cap_lead0={cj.get('cap_lead0', False)} cap_y={cy} ({(1 - cy) * 100:.0f} % up)"))
    shots = cj['shots']; starts = [a for a, n in shots]
    first_len = starts[1] if len(starts) > 1 else cj['duration']; cuts = sum(1 for a in starts[1:] if a < 3.0)
    inside = hk.get('inside', []); ins = [a for a, n in shots if n in inside or n.startswith(('xray', 'macro'))]
    ok = cuts >= GATE['cuts_0_3'] and first_len <= GATE['first_shot_max'] + 1e-6 and bool(ins) and min(ins) <= GATE['inside_by']
    res.append(('7+8 >= 2 cuts in 0-3 s, first shot <= 1.1 s, inside the body by 1.2 s', ok,
                f"cuts before 3 s: {cuts}; first shot {first_len:.2f}s; first inside-body shot at {min(ins) if ins else None}"))
    t0c = [(t, n) for t, n, g in cj['cues'] if t <= 0.08 and n in TRANSIENT]
    bad = [n for t, n, g in cj['cues'] if 'whoosh' in n.lower()]
    res.append(('sound: physical foley transient at 0-80 ms, no whoosh', bool(t0c) and not bad, f'{t0c or "no transient cue <= 0.08 s"} {bad or ""}'))
    last_word = max(b for a, b, w in words); tail = cj['duration'] - last_word
    loop = hk.get('loop'); last = shots[-1][1]
    res.append(('10 end cut <= 200 ms after the last word, last shot is the loop shot', 0 <= tail <= GATE['end_tail'] + 0.03 and (loop is None or last == loop),
                f'last word ends {last_word:.2f}s, video {cj["duration"]:.2f}s -> tail {tail * 1000:.0f} ms; last shot {last!r} (loop {loop!r})'))
    return res


def _img(path):
    from PIL import Image
    return Image.open(path).convert('RGB')


def _arr(im, size=(270, 480)):
    import numpy as np
    return np.asarray(im.resize(size)).astype('float32')


def frame_items(cj, fdir):
    import numpy as np
    res = []; n = int(round(cj['duration'] * cj['fps'])); last = n - 1
    fp = lambda i: os.path.join(fdir, f'f{i:04d}.png')
    need = list(SHEET_FRAMES) + [last]; miss = [i for i in need if not os.path.exists(fp(i))]
    if miss: return [('frames present', False, f'missing {miss} in {fdir}')]
    A = {i: _arr(_img(fp(i))) for i in need}
    lum = lambda a: float((a @ np.array([0.299, 0.587, 0.114], 'float32')).mean())
    mae = lambda a, b: float(np.abs(A[a] - A[b]).mean())
    l0 = lum(A[0]); res.append(('3a frame 0 mean luminance 65-210', GATE['lum0'][0] <= l0 <= GATE['lum0'][1], f'{l0:.0f}'))
    a0 = A[0] @ np.array([0.299, 0.587, 0.114], 'float32'); h, w = a0.shape
    centre = a0[int(h * .2):int(h * .8), int(w * .25):int(w * .75)].mean(); border = np.concatenate([a0[:int(h * .1)].ravel(), a0[:, :int(w * .1)].ravel(), a0[:, -int(w * .1):].ravel()]).mean()
    res.append(('3b (advisory) centre vs border luminance', None, f'centre {centre:.0f} vs border {border:.0f} (diff {abs(centre - border):.0f}; colour separation is judged by eye)'))
    m12 = mae(0, 12); res.append(('4 f0000 -> f0012 visibly different (mid-action)', m12 >= GATE['mae_f12'], f'MAE {m12:.1f} (>= {GATE["mae_f12"]})'))
    m1, m2 = mae(0, 24), mae(24, 48)
    res.append(('9a pixel change 0-1 s and 1-2 s (MAE >= 35)', m1 >= GATE['mae_1s'] and m2 >= GATE['mae_1s'], f'{m1:.1f} / {m2:.1f}'))
    ml = mae(last, 0); res.append(('10b loop: last frame matches frame 0 (MAE <= 55)', ml <= GATE['loop_mae'], f'{ml:.1f}'))
    return res


def sheet(cj, words, fdir, out):
    from PIL import Image, ImageDraw, ImageFont
    import post_kw
    n = int(round(cj['duration'] * cj['fps'])); fr = list(SHEET_FRAMES) + [n - 1]
    caps = post_kw.groups(words, cj.get('cap_lead0', False)); tw, th = 360, 640; cols = 5
    im = Image.new('RGB', (tw * cols, (th + 40) * 2), (18, 18, 18)); d = ImageDraw.Draw(im)
    f = ImageFont.truetype(post_kw.FONT, 26)
    for k, i in enumerate(fr):
        p = os.path.join(fdir, f'f{i:04d}.png')
        if not os.path.exists(p): continue
        base = post_kw.grade(_img(p).resize((post_kw.W, post_kw.H)))
        fimg = post_kw.caption(base, i / cj['fps'], caps, cj.get('cap_y', 0.78)).resize((tw, th))
        x, y = (k % cols) * tw, (k // cols) * (th + 40); im.paste(fimg, (x, y + 40))
        name = next((s for a, s in reversed(cj['shots']) if i / cj['fps'] >= a), cj['shots'][0][1])
        d.text((x + 8, y + 6), f"{'END ' if k == len(fr) - 1 else ''}f{i:04d} {i / cj['fps']:.2f}s {name}", font=f, fill=(255, 230, 90))
    im.save(out); return out


def main(argv):
    if len(argv) < 2 or argv[0] != 'gate': print(__doc__); return 2
    src = argv[1]; rest = argv[2:]; use_tts = '--tts' in rest; out = None
    if '--sheet' in rest: out = rest[rest.index('--sheet') + 1]
    fdir = next((a for a in rest if os.path.isdir(a)), None)
    if '--sheet' in rest and not fdir: print('HOOK GATE FAILED (frame folder missing: the render crashed, read the log)'); return 1
    cj = load_cues(src); words = word_times(cj, use_tts, src[:-3] + '.vo.json' if src.endswith('.py') else None)
    items = script_items(cj, words)
    if fdir: items += frame_items(cj, fdir)
    fails = 0
    for name, ok, why in items:
        tag = 'INFO' if ok is None else 'PASS' if ok else 'FAIL'; fails += ok is False
        print(f'{tag:4}  {name}: {why}')
    for q in ('2 LOOK subject (person + prop) fills >= 45 % of frame 0, <= 15 % empty ceiling above the head',
              '3 LOOK subject pops from the background (warm skin / bright costume against cool or dark set)',
              '1 LOOK frame 0 is full-bleed: no bars, logo, watermark or top title banner',
              '9 LOOK on mute, f0000-f0048 alone show something physically dangerous; no rig lines, clipping or shader blotches',
              '10 LOOK last frame has no black, logo or "subscribe" and echoes frame 0'):
        print(q)
    if fdir and out: print('sheet', sheet(cj, words, fdir, out))
    print('HOOK GATE', 'automated items OK' if not fails else f'FAILED ({fails})')
    return 1 if fails else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
