"""Render old and new acting from the same episode, camera subject and scene.

Example:
PCT=18 SAMPLES=2 flock /tmp/blender.lock blender -b --python-exit-code 1 -P kit/kw_motion_probe.py -- \
    loop/kw/ep_pepper.py room_clap1 /tmp/motion 0 4

The last two arguments are indices at 8 sampled frames/sec (or KW_PROBE_FPS=24
for native motion). Keeping batches short
lets another process render between them. Results are review footage, not episode media.
Set KW_PROBE_MEDIUM=1 to use identical medium framing if the legacy camera is occluded.
"""
import os
from math import ceil
from pathlib import Path
import runpy
import sys
import time


episode_path, shot_name, output, first, stop = sys.argv[sys.argv.index('--') + 1:]
sys.path.insert(0, str(Path(episode_path).resolve().parent))
import bpy
import kwkit
import kwrun

kwkit.Episode.run = lambda self: None
ep = runpy.run_path(episode_path)['ep']
ep.check(strict=False)  # Populate shot endpoints before isolating the take.
shot = next(s for s in ep.shots if s.name == shot_name)
if shot.cam.kind == 'loop' or shot.set not in kwkit.SPOTS:
    raise ValueError('Use a regular actor shot, not a loop or effect station.')
if os.environ.get('KW_PROBE_MEDIUM') == '1':
    shot.cam = kwkit.cam.medium(shot.cam.subj, side=28, height=0.12,
                                 push=shot.cam.o.get('push', 0.08), shake=shot.cam.o.get('shake', 0.0),
                                 hits=shot.cam.o.get('hits', ()))
ep.shots = [shot]
ep.people = [a for a in ep.people if a in shot.cast]
ep.macros = []
rt = kwrun.Runtime(ep)
rt.build()

rate = int(os.environ.get('KW_PROBE_FPS', '8'))
if not 0 < rate <= kwkit.FPS or kwkit.FPS % rate:
    raise ValueError('KW_PROBE_FPS must divide the source frame rate')
modes = {'before': False, 'after': True}
wanted = os.environ.get('KW_PROBE_TAKE', 'both')
if wanted != 'both': modes = {wanted: modes[wanted]}
for name in modes: Path(output, name).mkdir(parents=True, exist_ok=True)
initial = ceil(shot.t * kwkit.FPS - 1e-8)
for i in range(int(first), int(stop)):
    t0 = time.monotonic()
    f = initial + i * (kwkit.FPS // rate)
    if f / kwkit.FPS >= shot.end: break
    for name, mode in modes.items():
        rt.body_r4 = rt.camera_r4 = mode
        rt.S.frame_set(f)
        rt.update(f / kwkit.FPS)
        rt.S.render.filepath = str(Path(output, name, f'{i:04d}.png'))
        bpy.ops.render.render(write_still=True)
    print(f'motion probe pair {i}: {time.monotonic() - t0:.2f}s', flush=True)
