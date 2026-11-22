"""Render a review-only torso shot, without changing the episode or its audio.

PCT=25 SAMPLES=8 flock /tmp/blender.lock blender -b --python-exit-code 1 \
    -P kit/kw_scan_probe.py -- loop/kw/ep_pepper.py /tmp/torso-review.png
"""
import runpy
import sys
from pathlib import Path

ep_path, output = sys.argv[sys.argv.index('--') + 1:]
sys.path.insert(0, str(Path(ep_path).resolve().parent))

import bpy
import kwkit as KW
import kwrun

KW.Episode.run = lambda self: None
ep = runpy.run_path(ep_path)['ep']
actor = ep.people[0]
ep.people, ep.shots, ep.macros = [actor], [], []
shot = ep.shot(0., 'torso_probe', set='xray', xray=actor,
               organs=['airway', 'lungs', 'heart', 'liver', 'stomach'],
               cast={actor: KW.pose('stand', at='room.counter')},
               cam=KW.cam.xray(actor, 'lungs', side=20, dist=1.42, height=.16, fstop=9.))
shot.end = 2.
runtime = kwrun.Runtime(ep)
runtime.build()
runtime.S.frame_set(12)
runtime.update(.5)
body = runtime.FX.bodies[actor]
assert all(not mask.show_render for mask, _ in body.scan_masks)
runtime.S.render.filepath = str(Path(output).resolve())
bpy.ops.render.render(write_still=True)
body.show(False)
assert all(mask.show_render == original for mask, original in body.scan_masks)
print('Restored body masks:', [mask.vertex_group for mask, _ in body.scan_masks])
