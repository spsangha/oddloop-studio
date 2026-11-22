# Asset licences (Kinda Wild 3D kit)

Every 3D asset the kit renders is CC0 (public domain). Nothing here comes from Zack D. Films, and nothing is AI-generated.
Round 2 of the Zack look match (2026-11-22) added 0 MB of new files to the repo: the photo skins, hair, eyebrows, eyelashes and eyes below are the
MakeHuman system assets the render workflow (`.github/workflows/render_kw.yml`) already downloads at render time. They are not committed.

## Characters (downloaded at render time, not in the repo)

| What | Files used | Source URL | Licence |
|---|---|---|---|
| Photo skins (diffuse with pores), 22 tones/ages: young/middleage/old x african/asian/caucasian x f/m | `skins/<name>/<name>_diffuse.png` + `.mhmat` | https://files.makehumancommunity.org/asset_packs/makehuman_system_assets/makehuman_system_assets_cc0.zip | CC0 1.0 ("explicitly released as CC0 in september 2020", Data Collection AB / Joel Palmius / Jonas Hauquier; stated in each .mhmat) |
| Alpha-card hair, 10 styles: afro01, bob01, bob02, braid01, long01, ponytail01, short01-short04 | `hair/<style>/*.obj, *_diffuse.png, *_normal.png` | same pack | CC0 1.0 |
| Eyebrows eyebrow001-012, eyelashes01-04 | `eyebrows/*`, `eyelashes/*` | same pack | CC0 1.0 |
| Eyes (high-poly, procedural iris material) | `eyes/high-poly/*` | same pack | CC0 1.0 |
| Body, targets (incl. `eyes/l-eye-scale-incr`, `eyes/r-eye-scale-incr`), rig, skin shader | MPFB 2.0.18 add-on data | https://extensions.blender.org/download/sha256:c075b3e9b94b8e5556a5f03f4653602d02ea306de08126e8f55ed6dee28a2dad/add-on-mpfb-v2.0.18.zip | MPFB code GPL-3.0; bundled MakeHuman data CC0 1.0 |

Skin pores come from the MPFB enhanced skin's procedural pore bump (no extra texture). Skin tones used by the kit: caucasian, african, asian (young/middleage/old), plus age variants: at least 4 tones.

## Sets, props, textures (in the repo)

See `assets/real/CREDITS.md` (Poly Haven and ambientCG, CC0 1.0). Room and hospital walls are now flat untextured materials (no plaster texture).

## Music

See each episode's description credit.
