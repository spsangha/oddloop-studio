# Asset licences (Kinda Wild 3D kit)

Every 3D asset the kit renders is CC0 (public domain). Nothing here comes from Zack D. Films, and nothing is AI-generated.
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

## Music

See each episode's description credit.

## Scan heads (`assets/heads`, 1.8 MB; used only with `KW_HEADS=scan`, built by `kit/heads/*.py`)

Licence pages read and files downloaded 2026-11-22. No photos of identifiable people from the web, no research-only models (FaceScape, FLAME, Basel), no AI generation.

| What | Files | Source | Licence | Notes |
|---|---|---|---|---|
| Face shape: 40 identity PCA modes of the ICT Face Model Light (built from USC ICT Light Stage scans), resampled to MakeHuman vertex deltas | `ict_mh_deltas.npz` | ICT-FaceKit, USC Institute for Creative Technologies, https://github.com/ICT-VGL/ICT-FaceKit (`FaceXModel/identity000-039.obj`, `generic_neutral_mesh.obj`) | MIT (Copyright (c) 2020 USC Institute for Creative Technologies; https://github.com/ICT-VGL/ICT-FaceKit/blob/master/LICENSE) | Statistical modes, not any one person's face. Keep this notice with the derived file. |
| Skin detail: scan displacement (pores, lip lines, creases), specular (oily/matte zones) and colour (red zones) baked into MakeHuman UVs, high-passed | `scan_height.jpg`, `scan_spec.jpg`, `scan_red.jpg` | "Infinite, 3D Head Scan" by Lee Perry-Smith (Infinite Realities, his own head), copy in three.js: https://github.com/mrdoob/three.js/tree/dev/examples/models/gltf/LeePerrySmith (`LeePerrySmith.glb`, `Map-COL.jpg`, `Map-SPEC.jpg`, `Infinite-Level_02_Disp_NoSmoothUV-4096.jpg`, `LeePerrySmith_License.txt`) | CC BY 3.0 Unported. Credit: "Infinite, 3D Head Scan by Lee Perry-Smith, CC BY 3.0, based on a work at www.triplegangers.com" | Only fine detail is used, on top of the CC0 MakeHuman photo skins; the scan's face shape and identity are not used. Put the credit in the description of any episode rendered with `KW_HEADS=scan`. |
| Strand hair | (procedural, no files) | `loop/kw/heads_kw.py` | own code | grown on the MakeHuman `scalp` group |
