#!/usr/bin/env python3
"""Lull & Lift - still-to-video render pipeline.

Turns a still cozy scene into an animated sleep clip:
 - gentle Ken Burns zoom/pan
 - animated rain streaks
 - warm flickering glow (fire/lamp)
 - optional warm 'sunrise' grade toward the end
 - audio muxed in (looped/trimmed to video length)

Examples:
  # short demo with audio + sunrise grade
  python render_video.py --image scene.png --audio track.wav --seconds 50 --out demo.mp4

  # seamless-ish LOOP clip (no grade, no zoom) to later loop to 8h:
  python render_video.py --image scene.png --seconds 180 --grade 0 --zoom 0 --out loop.mp4
  # then stretch to a full night and add the 8h audio WITHOUT re-encoding video:
  ffmpeg -stream_loop -1 -i loop.mp4 -i audio_8h.wav -shortest -c:v copy -c:a aac out_8h.mp4

Requires: ffmpeg on PATH, pip install pillow numpy
"""
import argparse, shutil, subprocess, numpy as np
from PIL import Image, ImageDraw


def resolve_ffmpeg():
    """Use ffmpeg from PATH, else fall back to the binary bundled with imageio-ffmpeg."""
    exe = shutil.which('ffmpeg')
    if exe:
        return exe
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception:
        raise SystemExit('ffmpeg not found: install ffmpeg or `pip install imageio-ffmpeg`')


FFMPEG = resolve_ffmpeg()

ap = argparse.ArgumentParser()
ap.add_argument('--image', required=True)
ap.add_argument('--audio', default='')
ap.add_argument('--seconds', type=float, default=50)
ap.add_argument('--fps', type=int, default=24)
ap.add_argument('--w', type=int, default=1280)
ap.add_argument('--h', type=int, default=720)
ap.add_argument('--out', default='out.mp4')
ap.add_argument('--grade', type=int, default=1, help='1=warm sunrise grade in last 30%')
ap.add_argument('--zoom', type=float, default=0.08, help='ken burns zoom amount (0 to disable)')
ap.add_argument('--rain', type=int, default=170, help='number of rain streaks')
ap.add_argument('--firexy', default='', help='"x,y" 0..1 flicker-glow center, e.g. 0.82,0.5')
ap.add_argument('--window', default='', help='"x0,y0,x1,y1" 0..1 rect; rain only inside (the glass)')
a = ap.parse_args()

W, H, FPS = a.w, a.h, a.fps
N = max(1, int(a.seconds * FPS))

base = Image.open(a.image).convert('RGB')
zmax = 1.0 + max(a.zoom, 0.0)
need_w, need_h = W * zmax, H * zmax
s = max(need_w / base.width, need_h / base.height)
base = base.resize((int(base.width * s) + 1, int(base.height * s) + 1), Image.LANCZOS)
BW, BH = base.size

rng = np.random.default_rng(0)
NP = a.rain
if a.window:
    wx0f, wy0f, wx1f, wy1f = [float(v) for v in a.window.split(',')]
else:
    wx0f, wy0f, wx1f, wy1f = 0.0, 0.0, 1.0, 1.0
RX0, RY0, RX1, RY1 = wx0f * W, wy0f * H, wx1f * W, wy1f * H
px = rng.uniform(RX0, RX1, NP); py = rng.uniform(RY0, RY1, NP)
plen = rng.uniform(8, 20, NP); psp = rng.uniform(12, 22, NP); pa = rng.uniform(16, 60, NP)

yy, xx = np.mgrid[0:H, 0:W]
d = np.sqrt(((xx - W / 2) / (W * 0.62)) ** 2 + ((yy - H / 2) / (H * 0.62)) ** 2)
vig = np.clip(1.0 - (d - 0.62) * 0.85, 0.5, 1.0)[..., None]

fire = None
if a.firexy:
    fx, fy = [float(v) for v in a.firexy.split(',')]
    fd = np.sqrt((xx - fx * W) ** 2 + (yy - fy * H) ** 2)
    fire = (np.clip(1.0 - fd / (W * 0.30), 0, 1) ** 2)[..., None]

ff = [FFMPEG, '-y', '-f', 'rawvideo', '-pix_fmt', 'rgb24', '-s', f'{W}x{H}', '-r', str(FPS), '-i', '-']
if a.audio:
    ff += ['-stream_loop', '-1', '-i', a.audio, '-shortest', '-c:a', 'aac', '-b:a', '160k']
ff += ['-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '20', '-preset', 'veryfast', a.out]
proc = subprocess.Popen(ff, stdin=subprocess.PIPE)

for i in range(N):
    t = i / max(1, N - 1)
    z = 1.0 + a.zoom * t
    cw, ch = W / z, H / z
    ox = (BW - cw) * 0.5 + (BW - cw) * 0.04 * np.sin(t * 3.1416)
    oy = (BH - ch) * 0.5
    crop = base.crop((int(ox), int(oy), int(ox + cw), int(oy + ch))).resize((W, H), Image.LANCZOS)
    arr = np.asarray(crop).astype(np.float32)

    if a.grade:
        g = max(0.0, (t - 0.7) / 0.3)
        arr[..., 0] *= (1 + 0.12 * g); arr[..., 1] *= (1 + 0.05 * g); arr[..., 2] *= (1 - 0.04 * g)
        arr *= (1 + 0.13 * g)
    if fire is not None:
        fl = 0.55 + 0.45 * np.sin(i * 0.7) + 0.18 * np.sin(i * 1.9 + 1)
        arr = arr + fire * np.array([62, 34, 12]) * max(0.0, fl) * 0.5

    ov = Image.new('RGBA', (W, H), (0, 0, 0, 0)); dr = ImageDraw.Draw(ov)
    for k in range(NP):
        ey = min(py[k] + plen[k], RY1)
        dr.line([(px[k], py[k]), (px[k] + 1.6, ey)], fill=(202, 214, 238, int(pa[k])), width=1)
    py += psp
    off = py > RY1
    if off.any():
        py[off] = RY0 - plen[off]; px[off] = rng.uniform(RX0, RX1, int(off.sum()))
    ova = np.asarray(ov).astype(np.float32); al = ova[..., 3:4] / 255.0
    arr = arr * (1 - al) + ova[..., :3] * al

    arr = np.clip(arr * vig, 0, 255).astype(np.uint8)
    proc.stdin.write(arr.tobytes())

proc.stdin.close()
proc.wait()
print('done', a.out)
