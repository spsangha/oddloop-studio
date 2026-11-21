# Kinda Wild Films — daily card (one page; follow it top to bottom)

One ~27 s Short: a true, bizarre medical case as 3D people + glass x-ray body + macro close-ups (Zack D. Films format).
You fill ONE declarative file `loop/kw/ep_<slug>.py`. Never write Blender code. API names: `kit/kw_api.md`.
Hard bans: NO whoosh/swoosh/riser sounds. NO AI images/video/voice. Music is always `'sneaky_snitch'` (Kevin MacLeod, CC BY 4.0).
Never run two Blender processes at once (2 shared cores).

## Steps
```bash
cd /tmp/oddloop-studio && git pull --ff-only && cd loop/kw
# 1 PICK: the highest-ranked card in /home/user/workspace/kindawild/research/topic_bank.md not yet posted
#   (check `gh run list --workflow render_kw.yml` and loop/kw/ep_*.py). Open both source URLs; every sentence needs a source line.
cp ep_template.py ep_<slug>.py          # 2 WRITE: fill every <<...>>; ep_blownose.py is the worked example
python3 kwvo.py ep_<slug>.py            # 3 VOICE timings -> ep_<slug>.vo.json (re-run after ANY script edit)
python3 kwkit.py --check ep_<slug>.py   # 4 GUARD RAILS: repeat 2-4 until "ep.check() OK"
# 5 TEST FRAMES (hook + end). LAST = round(duration*24)-1 (printed by the check)
ONLY=0,4,12,24,36,48,60,72,<LAST> PCT=25 SAMPLES=8 ZK_TEX=/tmp/oddloop-studio/assets/tex \
  /tmp/blender-4.2.3-linux-x64/blender -b -P ep_<slug>.py -- /tmp/prev_<slug> 0 1 > /tmp/prev_<slug>.log 2>&1
python3 kwhook.py gate ep_<slug>.py /tmp/prev_<slug> --tts --sheet /tmp/prev_<slug>/hook.png   # 6 GATE: "automated items OK"
#   then open hook.png and answer the LOOK list below. Fix, repeat 5-6. Optional mid-video frames: ONLY=<every 24th frame>.
git add ep_<slug>.py ep_<slug>.vo.json && git commit -m "kw: ep_<slug>" && git push     # 7 COMMIT + PUSH (render uses the pushed file)
gh workflow run render_kw.yml -f episode=ep_<slug> -f pct=100 -f samples=20 -f out=<Slug>.mp4   # 8 RENDER (~2 h)
sleep 15; gh run list --workflow render_kw.yml -L 1      # note <id>
gh run watch <id> --interval 60 --exit-status > /dev/null # 9 ONE blocking wait. Never poll in a loop, never start a 2nd run.
#   on failure: gh run view <id> --log-failed | tail -40 ; fix, push, run again once
gh run download <id> -n kindawild -D /home/user/workspace/kindawild/<NN>_<slug>   # 10 artifact "kindawild"
```
11 REVIEW: open the artifact's sheet + watch the mp4 once with sound: captions match the voice, no missing props/wrong
   person, no black/blown frames, loop lands on frame 0, no whoosh. Any defect: fix, re-render; do not upload.
12 UPLOAD (YouTube only). In the build folder write `job.json` `{ "channel": "kw", "mp4": "<Slug>.mp4", "title": "<≤50 chars> #shorts",
   "description_file": "description.txt", "comment": "<one question>", "altered": false }` (false: clearly animated 3D, same as Odd Atlas) + `description.txt` (hook line, 2-3 fact lines,
   both source URLs, the music credit as in kindawild/ep01_sneeze/meta.md, 4-5 hashtags). Load the browser-use skill, then the
   kit loader cell from `/home/user/workspace/kit/README.md` with:
   `await run({ do: 'publish', dir: '<folder>', only: ['yt', 'comment'] })` — never 'meta' or 'inbox'. Run it once; wait on the same cell.
13 HAND-OVER: give the owner the mp4 + ONE code block with the whole Facebook/Instagram caption (≤2,200 chars, 4-6 hashtags as the last line).

## Rules ep.check enforces (so you know why it fails)
5-7 sentences, 80-92 words, plain words · sentence 1 = 8-13 words, names the injury within 12 words (`injury=`), no
"imagine / did you know / one day" · line 1 at 0.0 s, 8-11 words in 0-3 s · shot 1 ≤ 1.0 s, x-ray/macro at 1.0 s, third
shot by 2.2-2.4 s · every shot ≤ 2.2 s · physical sound on frame 0 · last shot `KW.cam.loop()`, cut ≤ 200 ms after the last word.

## LOOK list (from hook.png; every answer must be YES)
1 f0 full-bleed: no bars, logo, watermark, title banner. 2 Person (face + hands/prop) fills ≥ 45 % of f0, ≤ 15 % empty above
the head. 3 Warm skin / bright clothes stand out from a cooler or darker set. 4 f0 already mid-action; f12 differs from f0.
5 Caption readable on f0, 2-4 words, lower-middle. 6 On mute, f0-f48 alone show something physically dangerous.
7 f24/f48 inside the body, f60 shows the injury. 8 No wires on bodies, hands through faces, floating props, odd patches,
black eyes. 9 END frame echoes f0, no black/logo/subscribe. 10 Nothing blown white or murky dark.

## Mistakes already made (do not repeat)
- Opening on a calm person + "while he was driving": hook 2/10, render cancelled. Injury first, context in sentence 2.
- Small x-ray push in the hook: 1 s and 2 s frames identical (gate 9a). Use push ≈ 0.55 + orbit ≈ 30 (see template).
- A sharp light oval on a cheek = the old compositor vignette (now off in kw_realism; post_kw does a soft one). Report it, do not "fix the face".
- Brown bar in front of a seated person = the office chair was turned backwards (fixed in kwsets). Report any prop crossing a body.
- A white hose under the chin in x-ray = the old jaw tube (removed). Stethoscope tube on a patient's arm = hidden person's part.
- Hands hovering beside a tissue: change the hand name/shape, never the timing. Eyes black = caustics off (kit handles it).
- "Within hours" was not in the source. Every claim must be in a source sentence; doubtful -> leave it out.
- MPFB male hair 'short03'/'short04' reads as long/female hair: pin `hair='short02'` for every man.
- "strain" (and some mixes) can render as a smirk: check every strain face by eye on the sheet; swap to a tissue/hand pose or another face if it smiles.
- Fingers on small props splay like claws: frame hands-on-prop shots medium/wide, or hide the fingers behind the prop.
- Macro bone sets are weak (pale, low contrast): prefer soft-tissue macros (windpipe, artery, sinus, intestine).
- Keep the calendar centred: end its flip by ~0.7 s local (`calendar(at=0.05, dur=0.6)`) and check the last frame of the shot.
- ep_blownose has only been PREVIEWED (PCT 25): its first full render needs a full review of the artifact sheet + mp4 before upload.
