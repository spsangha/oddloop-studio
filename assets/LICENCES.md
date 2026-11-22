# Asset licences (Kinda Wild 3D kit)

The kit uses CC0 and other licensed assets as noted below. Nothing in the rendering kit comes from Zack D. Films, and nothing is AI-generated.
Round 2 of the Zack look match (2026-11-22) added 0 MB (round 3 added the 18 MB `assets/mh` set below) of new files to the repo: the photo skins, hair, eyebrows, eyelashes and eyes below are the
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

## Round 3: community assets kept in the repo (`assets/mh`, 18 MB; 2048 px hair textures downscaled to 1024)

Licences are taken from each pack's `packs/<pack>.json` metadata (field `license`). CC-BY assets: credit "Hair by Elvaerwyn (MakeHuman Community), CC BY 4.0".

| Asset | Folder | Author | Licence | Asset page | Downloaded from |
|---|---|---|---|---|---|
| Short male hair | hair/culturalibre_hair_02 | culturalibre | CC0 | http://www.makehumancommunity.org/node/2892 | https://files.makehumancommunity.org/asset_packs/hair01/hair01_cc0.zip |
| Long hair | hair/o4saken_long01 | o4saken (packed by punkduck) | CC0 | http://www.makehumancommunity.org/node/1471 | hair01_cc0.zip (above) |
| Bob cut | hair/littleright_bobcut_hair | littleright | CC0 | http://www.makehumancommunity.org/node/936 | hair01_cc0.zip (above) |
| Side-swept male hair | hair/elvs_grump_hair | Elvaerwyn | CC-BY 4.0 | http://www.makehumancommunity.org/node/2796 | https://files.makehumancommunity.org/asset_packs/hair02/hair02_ccby.zip |
| Long straight hair | hair/elvs_hazel_hair | Elvaerwyn | CC-BY 4.0 | http://www.makehumancommunity.org/node/2816 | hair02_ccby.zip (above) |
| Wavy bob | hair/elvs_wavy_bob | Elvaerwyn | CC-BY 4.0 | http://www.makehumancommunity.org/node/1551 | hair02_ccby.zip (above) |
| Scruffy beard | clothes/wdg_scruffy_beard | WDG | CC0 | http://www.makehumancommunity.org/node/1769 | https://files.makehumancommunity.org/asset_packs/bodyparts05/bodyparts05_cc0.zip |
| Skin normal map (pores, lips, brows) used on every skin | skins/mindfront_skin_male_african_middleage/skin_male_african_middleage_NRM.png | Mindfront | CC0 | http://www.makehumancommunity.org/node/526 | https://files.makehumancommunity.org/asset_packs/skins02/skins02_cc0.zip |

## Sets, props, textures (in the repo)

See `assets/real/CREDITS.md` (Poly Haven and ambientCG, CC0 1.0). Room and hospital walls are now flat untextured materials (no plaster texture).

## Round 4: additive torso motion

`assets/motion/cmu_torso_r4.json` contains trimmed, decimated torso rotations from CMU Graphics Lab subject 79, trials 40 (drinking a soda) and 15 (eating a sandwich), downloaded 2026-11-23 (Hong Kong). Source data: [CMU subject 79 catalogue](http://mocap.cs.cmu.edu/search.php?subjectnumber=79); BVH conversion by Bruce Hahne, mirrored at [79_40.bvh](https://github.com/una-dinosauria/cmu-mocap/blob/master/data/079/79_40.bvh) and [79_15.bvh](https://github.com/una-dinosauria/cmu-mocap/blob/master/data/079/79_15.bvh). The [CMU FAQ](https://mocap.cs.cmu.edu/faqs.php) permits copying, modifying and redistributing the data. The [CMU terms](http://mocap.cs.cmu.edu/) explicitly permit inclusion in commercial products but prohibit resale of the motion data itself, including converted versions. The project keeps the terms for these tracks; do not redistribute the tracks as a paid dataset.

The data used in this project was obtained from mocap.cs.cmu.edu. The database was created with funding from NSF EIA-0196217.

`assets/motion/cmu_contact_r4.json` adds torso-only trims from [CMU subject 22](http://mocap.cs.cmu.edu/search.php?subjectnumber=22), [22_03 (seated face hold)](https://github.com/una-dinosauria/cmu-mocap/blob/master/data/022/22_03.bvh) and [22_18 (forward lean)](https://github.com/una-dinosauria/cmu-mocap/blob/master/data/022/22_18.bvh), downloaded 2026-11-23 (Hong Kong). The [same CMU commercial-product terms](http://mocap.cs.cmu.edu/) apply. The second look pass adds no external visual assets.

## Music

See each episode's description credit.
