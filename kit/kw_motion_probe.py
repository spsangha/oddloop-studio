"""Render old and new acting from the same episode, camera subject and scene.

Example:
PCT=18 SAMPLES=2 flock /tmp/blender.lock blender -b --python-exit-code 1 -P kit/kw_motion_probe.py -- \
    loop/kw/ep_pepper.py room_clap1 /tmp/motion 0 4

The last two arguments are indices at 8 sampled frames/sec. Keeping batches short
lets another process render between them. Results are review footage, not episode media.
"""
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
ep.shots = [shot]
ep.people = [a for a in ep.people if a in shot.cast]
ep.macros = []
rt = kwrun.Runtime(ep)
rt.build()

for name in ('before', 'after'): Path(output, name).mkdir(parents=True, exist_ok=True)
initial = ceil(shot.t * kwkit.FPS - 1e-8)
for i in range(int(first), int(stop)):
    t0 = time.monotonic()
    f = initial + i * (kwkit.FPS // 8)
    if f / kwkit.FPS >= shot.end: break
    for name, mode in (('before', False), ('after', True)):
        rt.body_r4 = rt.camera_r4 = mode
        rt.S.frame_set(f)
        rt.update(f / kwkit.FPS)
        rt.S.render.filepath = str(Path(output, name, f'{i:04d}.png'))
        bpy.ops.render.render(write_still=True)
    print(f'motion probe pair {i}: {time.monotonic() - t0:.2f}s', flush=True)
