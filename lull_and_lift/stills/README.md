# Stills — Lull & Lift

Clean 16:9 scene stills used as the still→video base. One per planned video.

## `rainy_cabin_night.png` (Scene 1 — Rainy Cabin Night)

**Provenance / honest state:** this is a **proof-of-concept** still cropped from the
ChatGPT brand board (`assets_from_chatgpt/brand_board.png`, the cozy-cabin hero) and
upscaled to 1920×1080. Crop box `(300, 18, 820, 310)` — chosen to clear the baked-in
"LULL & LIFT" logo and the right-hand text panel while keeping the window (rain
surface), the warm lamp (flicker target) and Charlie as a background presence.

It is upscaled ~3.7×, so it is **soft**. For final upload, replace it with a clean
native 1920×1080 still from the image generator (no caption text, full Charlie in
frame) — the render commands below stay identical; only `--image` changes.

## Pipeline for this scene

`render_video.py` auto-resolves ffmpeg (PATH, else the `imageio-ffmpeg` binary).

```bash
# 1) Render a short SEAMLESS LOOP base (no zoom/grade so it tiles cleanly to 8h).
#    Rain is confined to the window rect; warm flicker sits on the lamp.
python video/render_video.py \
  --image stills/rainy_cabin_night.png \
  --seconds 20 --fps 24 --w 1920 --h 1080 \
  --grade 0 --zoom 0 --rain 220 \
  --window 0.02,0.04,0.40,0.55 --firexy 0.55,0.40 \
  --out video/work/loop_rainy_cabin_1080.mp4

# 2) Loop the base to full length and mux the 8h audio WITHOUT re-encoding video
#    (cheap: ~45× realtime). Swap in generate_audio.py's 8h track when ready.
ffmpeg -y -stream_loop -1 -i video/work/loop_rainy_cabin_1080.mp4 \
  -i AUDIO_8H.wav -map 0:v -map 1:a -shortest \
  -c:v copy -c:a aac -b:a 160k video/work/rainy_cabin_night_8h.mp4
```

An 8h 1080p file at this bitrate is ~6–7 GB; keep it in `video/work/` (gitignored).

## Still TODO toward final quality
- Native 1920×1080 ChatGPT stills (no logo/text, full Charlie) per scene.
- `generate_audio.py` 8h engine (balance F locked) for step 2's `AUDIO_8H.wav`.
- Optional: subtle masked "breathing" on Charlie's torso in `render_video.py`
  (only worthwhile once a still shows his torso clearly).
