# Lull &amp; Lift — how to make the videos

You now have a working pipeline that turns a **still cozy scene** into an **animated sleep video**
(rain + warm flicker + slow zoom + optional sunrise grade), with audio. Files:

- `render_video.py` — the render tool (needs `ffmpeg` on PATH, `pip install pillow numpy`)
- `lull_and_lift_DEMO.mp4` — a 50‑second proof (made from a cropped scene, so it has a baked‑in logo)

## Before you start: get clean stills
The demo scene was cropped from the branding poster, so the logo is burned in. For real videos, ask
ChatGPT (or your image generator) to export **each scene individually at high resolution (1920×1080),
no text/logo overlaid**. One clean PNG per video. Keep the dog + framing consistent across all of them.

You also need the **audio**: an 8‑hour track. The synth in the bundle (`sleeparc_v3.py`) makes 3‑minute
demos — the full 8‑hour render tool is still the one piece left to build (chunked generation so memory
stays sane). Until then you can pair the video with any 8‑hour rain+piano track you own the rights to.

## Quick test (short clip with audio + sunrise grade)
```
python render_video.py --image scene1.png --audio track.wav --seconds 50 \
    --firexy 0.82,0.5 --out test.mp4
```
`--firexy x,y` places the flickering warm glow (0..1 of width/height) over the fireplace or lamp.

## Full 8‑hour video — the efficient way
Do **not** render 8 hours of frames. Render a short loop, then loop it with ffmpeg.

1) Render a ~3‑minute loop clip — no zoom, no grade so it loops cleanly:
```
python render_video.py --image scene1.png --seconds 180 --grade 0 --zoom 0 \
    --firexy 0.82,0.5 --out loop1.mp4
```
2) Stretch it to the full night and attach the 8‑hour audio **without re‑encoding the video** (fast):
```
ffmpeg -stream_loop -1 -i loop1.mp4 -i audio_8h.wav -shortest \
    -c:v copy -c:a aac -movflags +faststart video1_8h.mp4
```
Repeat per scene for your first 10 videos.

### Notes / honest caveats
- **Loop seam:** rain particles don't perfectly match the loop boundary, so there's a tiny hitch each
  loop. In a dark sleep video it's unnoticeable; use a longer loop (3–5 min) if you want it rarer.
- **Night→sunrise in the picture:** the simplest v1 keeps the *video* a static cozy night and lets the
  *audio* carry the night→morning arc (this matches how most rain channels work — static image, looping
  rain). If you later want the picture to brighten at the end too, render the full length once with
  `--grade 1` instead of looping (heavier), or apply a slow ffmpeg color ramp.
- **File size:** 8h at 720p is several GB. For sleep content 720p is fine; to shrink, raise the CRF in
  `render_video.py` (change `'-crf','20'` to e.g. `'28'`). Lower bitrate = smaller file, still fine in
  the dark.
- **YouTube:** upload 1080p if you can; keep the same thumbnail framing across videos for recognition.
```
