"""kwvo - measure the real narrator timing of an episode script (same voice service as post_kw.py).

    python3 kwvo.py ep_xxx.py        -> writes ep_xxx.vo.json  {voice, rate, lines, durations}

kwkit reads the json so shots placed with ep.line(i) land on the spoken words.  Run it again whenever the script changes
(kwkit prints 'vo.json is stale' when the text no longer matches).  Without it kwkit estimates 3.25 words/s.
"""
import sys, os, json, asyncio, time, re

def measure(text, voice, rate, say=None):
    """-> (duration, words) of one line as post_kw will play it (vo_trim: the TTS lead-in silence is cut, so the
    line is audible from its start time).  words = [[start, end, word]] relative to the line start."""
    import post_kw
    for i in range(4):
        try:
            _, ws = post_kw.tts(dict(vo=[[0.0, text]], voice=voice, rate=rate, vo_trim=True, say={'0': say} if say else {}))
            if ws: return round(max(b for a, b, w in ws) + 0.03, 3), [[round(a, 3), round(b, 3), w] for a, b, w in ws]
        except SystemExit as e: print('tts retry', e)
        time.sleep(3 * (i + 1))
    raise SystemExit('voice service unreachable - kwkit will use its estimate')

if __name__ == '__main__':
    path = sys.argv[1]; here = os.path.dirname(os.path.abspath(path)); sys.path.insert(0, here); sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    os.environ['KW_NOCHECK'] = '1'
    import kwkit as KW
    eps = []
    orig = KW.Episode.run
    KW.Episode.run = lambda self: eps.append(self)
    src = open(path).read(); exec(compile(src, path, 'exec'), {'__name__': '__main__', '__file__': os.path.abspath(path)})
    KW.Episode.run = orig
    ep = eps[0]
    sy = getattr(ep, 'tts_say', None) or {}; m = [measure(l, ep.voice, ep.rate, sy.get(i)) for i, l in enumerate(ep.lines_text)]; durs = [d for d, w in m]
    out = os.path.join(here, ep.name + '.vo.json')
    json.dump(dict(voice=ep.voice, rate=ep.rate, trim=True, lines=ep.lines_text, durations=durs, words=[w for d, w in m]), open(out, 'w'), indent=1)
    print('wrote', out, durs, 'total speech', round(sum(durs), 2))
