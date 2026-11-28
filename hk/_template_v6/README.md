# HK Unlocked Reel template v6 (looks)

    nice -n 15 python3 build.py <reel_dir> stills 0,1.6,2.2      # stills only (lead reviews before any full render)
    nice -n 15 python3 build.py <reel_dir>                       # full render, then: python3 qa.py <reel_dir>

## Looks (job.json "look")
- `map_day`: the v5 picture (build.Reel). It may run on any day when `"route_guide": true` (qa exemption, lead 24 Nov).
- `neon`: hanging neon signboards and a glowing night map (looks.NeonReel). With `"format": "signs"` it is the love/hate sign cluster (looks.SignsReel).
- `sketch`: a sketchbook page on a desk (looks.SketchReel + sketch.py). It needs `photos[0]` and is described below.
- `menu`: the code is kept, but qa blocks it (queued).

## Backdrop clip: OFF (owner 24 Nov 2026: "Turn off real video clips too"). Do not use; qa.py fails any job with "backdrop". Kept below for reference only.
```json
"backdrop": {"clip": "clip.mp4", "start": 0, "dim": 0.55, "blur": 2},
"media": [{"platform": "Pexels", "id": "30428250", "url": "https://www.pexels.com/video/...", "author": "Nelemson G",
           "licence": "Pexels License", "used_at": "backdrop"}]
```
- `dim` (0.45-0.7) is a tone curve, gamma 1 + 2*dim. Mid-tones go dark and highlights stay lit, so the neon brightness limits pass by design.
- With look `neon`, prefer night clips (Pexels 30073057 night street, 36617176 night skyline). A daytime clip (e.g. 30428250 ferry dock) is fine for map_day cards and the sketch page margin.
- qa FAILs unless every media row has a platform in {Pexels, Pixabay, Unsplash, Wikimedia Commons}, an https url and an author. caption.txt must also contain "<author> / <platform>".

## Sketch world (section 9)
```json
"look": "sketch",
"photos": [{"file": "pier.jpg", "title": "File:...jpg", "author": "...", "licence": "CC BY 4.0", "url": "https://commons.wikimedia.org/wiki/File:...",
            "platform": "Wikimedia Commons", "crop": [x0, y0, x1, y1],
            "label_en": "...", "label_zh": "...",
            "near": [[[x, y], ...]], "quiet": [[[x, y], ...]]}],
"sketch": {"subject": [0.34, 0.44, 0.87, 0.93], "bloom_from": [[0.59, 0.62], [0.5, 0.1]]}
```
- sketch needs one free-licence photo of the subject per Reel (rules: looks_v6_brief.md 9.3); if no licensed photo exists, use map_day with "no_photo_reason". NEON IS OFF (owner 24 Nov 2026): never use look "neon".
- qa FAILs a sketch Reel if a photo lacks title, author, https url or a licence of CC0 / Public domain / CC BY* / CC BY-SA*. The proof tag defaults to `wash`.
- `subject` is the box [x0, y0, x1, y1] (crop-normalised) that is fully inked and half washed at 0.0 s. The rest of the ink draws 0-1.0 s, the sky wash 1.0-2.0 s, and the pen lifts by 1.3 s. `drawn_at_0` is used only when there is no `subject`.
- The harbour wash continues down the page behind the tapes and blooms 0.3-2.0 s. The cheat-sheet shows the finished sketch as a taped print. Labels, the caveat and cheat-sheet English use Patrick Hand (fonts/, OFL), with Montserrat for missing glyphs.
- The crop aspect should be about 1.52 (the drawing is 940x620 on the page).
- `near` is the subject polygon, in crop-normalised coordinates. Lines outside it are 65 % lighter.
- `quiet` covers water and fine texture: only long lines are kept there, and they are lighter.
- `bloom_from[0]` is where the pen starts and where the first wash blooms. Later entries bloom after it.
- Never use a food close-up or a crowd. Faces must be under 40 px.
- The layers are cached in `<reel_dir>/.sketch_cache/`.
