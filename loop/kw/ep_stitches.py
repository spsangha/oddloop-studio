"""Kinda Wild Films ep07 - 'What Stitches Really Do To A Cut'.  Written only with kwkit (+ the kwwound calf part).
Brief: kindawild/07_stitches/brief.md + Addendum A, B (B1-B4) and the CHECK 1 fixes F1-F6.  Facts: facts.md; script: script.txt.
ONE continuous camera glide over the whole film on Ben's left calf (Addendum B2); the 17 'shots' are only timeline segments
on the spoken words (no cuts).  No blood anywhere (policy).  Shot 7 artery dropped (B4): the macro stays on the seam.
Voice line starts (s): L1 0.00, L2 4.84, L3 7.08, L4 12.86, L5 18.22, L6 21.45; speech ends 27.77, film 27.92 s (670 frames).
"""
import sys, os; sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kwkit as KW
os.environ.setdefault('KW_LIGHT', '1')      # light-render settings on the studio set (lead: approved for the full render)

HERE = os.path.dirname(os.path.abspath(__file__))
ep = KW.Episode('ep_stitches', injury="gashes his leg",
                voice_lines=[l.strip() for l in open(os.path.join(HERE, 'ep_stitches.txt')) if l.strip()],
                music='sneaky_snitch', gap=0.4)
# brief rulings (lead), shown as warnings by --check:
ep.waive = {"voice line 6 must be exactly one sentence": "brief s3: the last word 'until' runs into line 1 (the loop)",
            **{f"shot {n} holds": "brief Addendum B2: ONE continuous glide, no cuts - the segments are labels on the words; a visible change every <= 2.2 s is kept by the wound timeline" for n in ('stitch_6_10', 'inflamed', 'collagen_grow', 'vessels_sprout', 'stitches_out')},
            "HOOK 8-11 words": "brief s3: script.txt is final (12 words before 3.0 s; changing words is a STOP rule)",
            "HOOK inside the body": "brief s0/B4: single-site skin macro format, no xray/macro shot (artery shot dropped)"}
ben = ep.person('Ben', 'civilian', 'eatmore-ben', gender='m', age='young', race='caucasian', hair='short02', tee='teal')

W = ep.word; L = ep.line
F = 1 / 24.0
END = round(int(round(ep.duration * 24)) - 1, 0) * F          # time of the last frame (= frame 0 again)

# ---- camera: Addendum B2 keys re-anchored to the real voice (visible height m at the cut) ------------------------
GLIDE = [(0.0, 0.38), (W(0, 'and'), 0.27), (L(1), 0.16), (L(2), 0.12), (W(2, 'and'), 0.08), (W(2, 'to'), 0.06),
         (L(5), 0.05), (W(5, 'and'), 0.18), (W(5, 15), 0.38), (W(5, 'strength'), 0.35),
         (END - 8 * F, 0.38), (END, 0.38)]
CAMO = dict(glide=GLIDE, yaw=(-10.0, 10.0, END), slide=(W(2, 'to'), L(5), 0.02, L(5), W(5, 'and') + 1.0),
            lens=50, cap_bone='lowerleg01.L', cap_dz=0.02)

# ---- wound timeline (absolute seconds; brief 6b re-timed) ---------------------------------------------------------
T2 = W(0, 'and') + 2 * F                    # stitch 1 starts at shot 2 f2
SP = 0.23                                   # one stitch every ~5.5 frames -> all ten done by shot 3 f30
K = [(0.0, dict(open=1.0, stitches=0.0, cinch=0.0))]
K += [(T2 + SP * k, dict(stitches=float(k), open=1.0 - 0.04 * k)) for k in range(11)]   # G6: laced loosely, the gap stays open, narrowing to about 6 mm
TC, SC = 3.5, 0.13                                                          # ... then cinched one by one, top to bottom, 3.5-4.8 s
K += [(TC + SC * k, dict(cinch=float(k))) for k in range(11)]
K += [(TC + SC * 10 - 0.25, dict(open=0.6)), (TC + SC * 10 + 0.2, dict(open=1.0))]
T5 = 5.3                                                                    # G6: faint pink from 5.3 s
K += [(T5, dict(red=0.0)), (L(2), dict(red=0.2)), (L(2) + 36 * F, dict(red=1.0))]
K += [(W(2, 'and') - 0.3, dict(specks=-1.0)), (W(2, 'and'), dict(cells=0.0, specks=0.0)),           # B4: cells drift in, specks rise
      (W(2, 'to'), dict(cells=1.0)), (W(2, 'to') + 6 * F, dict(specks=0.0)), (W(2, 'to') + 30 * F, dict(specks=1.0)),
      (L(3), dict(cells=1.0)), (L(3) + 0.6, dict(cells=2.0))]                                         # cells sink away
K += [(L(3) + 9 * F, dict(collagen=0.0)), (W(3, 'the') + 12 * F, dict(collagen=1.0))]
K += [(L(4) + 6 * F, dict(vessels=0.0)), (L(4) + 42 * F, dict(vessels=1.0))]
K += [(W(4, 'to') + 6 * F, dict(level=0.0, cpink=0.0, red=1.0, pink=0.0)), (L(5), dict(level=1.0, cpink=1.0, collagen=1.0, vessels=1.0, pink=1.0, lwid=1.0)), (L(5) + 0.75, dict(collagen=0.0, vessels=0.0))]   # strands and vessels sink into the levelled pink   # yellow -> pink, seam fills level
T14 = L(5) + 12 * F                         # stitches out: one every 3 frames, each 5 frames
K += [(L(5) + 12 * F, dict(red=0.4, out=0.0, scar=0.0, dots=0.0))]          # H2: the band under the strands is pink from L(5) on (pink=0 here showed the dark seam)
K += [(T14 + 3 * F * k, dict(out=float(k), lwid=1.0 - 0.333 * k / 10)) for k in range(1, 10)] + [(T14 + 3 * F * 9 + 5 * F, dict(out=10.0, scar=1.0, dots=0.6, pink=1.0, lwid=0.667))]   # H2: pink band 3 mm -> 2 mm while the stitches leave
K += [(W(5, 'and') + 30 * F, dict(red=0.1, dots=0.3)), (W(5, 'strength'), dict(red=0.05, scar=0.6, dots=0.0))]
TS = END - 6 * F                            # last 6 frames: the scar splits back into the frame-0 cut
K += [(TS, dict(open=1.0, stitches=10.0, cinch=10.0, out=10.0, level=1.0, cpink=1.0, scar=0.6, red=0.05)),
      (END, dict(open=1.0, stitches=0.0, cinch=0.0, out=0.0, level=0.0, cpink=0.0, scar=0.0, red=0.0, collagen=0.0, vessels=0.0, line=0.0, pink=0.0, dots=0.0, lwid=1.0))]

YL = dict(color='yellow', size=1.2); LP = (0.5, 0.84)
TICKS = [T2 + SP * k + 4 * F for k in range(10)] + [TC + SC * k + 0.08 for k in range(10)] + [T14 + 3 * F * k for k in range(10)]
LABELS = [('INFLAMED', W(2, 'vessels')), ('COLLAGEN', W(3, 'collagen')), ('VESSELS', W(4, 'blood')),
          ('2 WEEKS', W(5, 'two')), ('80%', W(5, 'eighty'))]
for t in TICKS: ep.sound(t, 'tick', 0.35)
ep.sound(0.0, 'thud', 0.8)
for _, t in LABELS: ep.sound(t, 'thud', 0.6)
# LDUR (below): every label stays on as long as 80% does today (its word -> the loop_split segment)
ep.sound(TS, 'thud', 1.0)

# ---- the 17 timeline segments (brief section 6 rows, on their words) ----------------------------------------------
SEG = [(0.0, 'cut_open'), (W(0, 'and'), 'stitch_1_5'), (W(0, 'thread'), 'stitch_6_10'), (L(1), 'seam_close'),
       (W(1, 'to'), 'seam_calm'), (L(2), 'inflamed'), (W(2, 'and'), 'cells_in'), (W(2, 'to'), 'germs_out'),
       (L(3), 'collagen_grow'), (W(3, 'a'), 'lattice'), (W(3, 'the'), 'lattice_full'), (L(4), 'vessels_sprout'),
       (W(4, 'to'), 'fill_level'), (L(5), 'stitches_out'), (W(5, 'and'), 'scar_back'), (W(5, 15), 'scar_pale'),
       (W(5, 'strength'), 'loop_split')]
LDUR = round(SEG[-1][0] - LABELS[-1][1], 3)
for i, (t0, nm) in enumerate(SEG):
    keys = [(t - t0, v) for t, v in K]
    fx = [KW.fx.wound(ben, keys, side='L')]
    t1 = SEG[i + 1][0] if i + 1 < len(SEG) else 99
    fx += [KW.fx.label(tx, at=round(tl - t0, 3), pos=LP, dur=LDUR, **YL) for tx, tl in LABELS if tl < t1 and tl + LDUR > t0]   # H1: on through segment changes
    cam = KW.cam.loop() if i == len(SEG) - 1 else KW.cam.part(ben, 'calf_l', **CAMO)
    ep.shot(t0, nm, set='studio', world='sky', cast={ben: KW.pose('stand', at='centre')}, fx=fx, cam=cam)
ep.run()
