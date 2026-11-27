"""post_recap.py MP4 CI_CUES NEW_CUES FRAMES_DIR OUT: re-composite only frames whose caption must move (cap_avoid) or ZOOM_N first frames (push-in) or PATCH_DIR frames (patch render), from CI frame artifacts; no Blender."""
import sys, os, json, subprocess, numpy as np
sys.path.insert(0, '/tmp/oddloop-studio/loop/kw')
import post_kw as P
from PIL import Image
mp4, cues_ci, cues_new, fdir, out = sys.argv[1:6]; ZN = int(os.environ.get('ZOOM_N', 0)); ZS = float(os.environ.get('ZOOM_S', 1.06)); ZC = (0.5, float(os.environ.get('ZOOM_CY', 0.35))); PD = os.environ.get('PATCH_DIR', '')
cj = json.load(open(cues_ci)); avoid = json.load(open(cues_new))['cap_avoid']; caps = json.load(open(mp4 + '.captions.json'))['caps']
fps = cj['fps']; W, H = P.W, P.H; y0 = cj.get('cap_y', 0.78); cuts = P.whip_cuts(cj, fps)
def need(i):
    if i < ZN or (PD and os.path.exists(os.path.join(PD, f'f{i:04d}.png'))): return True
    t = i / fps; return any(a <= t < b for a, b, _ in caps) and abs(P.cap_y_at(t, y0, avoid) - y0) > 1e-6
dec = subprocess.Popen(['ffmpeg', '-v', 'error', '-i', mp4, '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-'], stdout=subprocess.PIPE)
enc = subprocess.Popen(['ffmpeg', '-v', 'error', '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(fps), '-i', '-', '-i', mp4,
                        '-map', '0:v', '-map', '1:a', '-c:v', 'libx264', '-preset', 'slow', '-crf', '16', '-pix_fmt', 'yuv420p', '-c:a', 'copy', '-movflags', '+faststart', out], stdin=subprocess.PIPE)
i = 0; fixed = []
while True:
    buf = dec.stdout.read(W * H * 3)
    if len(buf) < W * H * 3: break
    if need(i):
        src = os.path.join(PD, f'f{i:04d}.png') if PD and os.path.exists(os.path.join(PD, f'f{i:04d}.png')) else os.path.join(fdir, f'f{i:04d}.png')
        base = P.grade(Image.open(src).convert('RGB').resize((W, H), Image.LANCZOS))
        if i < ZN:
            u = i / ZN; z = 1 + (ZS - 1) * u * u * (3 - 2 * u)
            if z > 1.0001:
                cw_, ch_ = W / z, H / z; x0 = ZC[0] * W - cw_ / 2; y0_ = ZC[1] * H - ch_ / 2
                x0 = min(max(0, x0), W - cw_); y0_ = min(max(0, y0_), H - ch_)
                base = base.resize((W, H), Image.LANCZOS, box=(x0, y0_, x0 + cw_, y0_ + ch_))
        buf = P.caption(P.whip(base, i, cuts), i / fps, caps, y0, avoid).tobytes(); fixed.append(i)
    enc.stdin.write(buf); i += 1
enc.stdin.close(); enc.wait(); print('frames', i, 'fixed', fixed[:1], '..', fixed[-1:], len(fixed))
