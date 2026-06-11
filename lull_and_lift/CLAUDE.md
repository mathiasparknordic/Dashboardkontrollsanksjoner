# CLAUDE.md — Lull &amp; Lift (handoff for Claude Code)

**Norsk kort:** Dette er et personlig sove-verktøy / mulig YouTube-kanal: **regn + rolig piano** som
hjelper deg å sovne og våkne mildt, med hunden **Charlie** i en koselig scene. Viktigste oppgave nå:
ta et **grundig dypdykk i regnlyd + rolig piano** og bygg en **8-timers lydmotor**. Se `AUDIO_BRIEF.md`.
Alt annet er forklart under. Skriv gjerne kode/dokumentasjon på engelsk.

---

## What this project is
A sleep soundscape + video channel called **Lull &amp; Lift** ("rest, relax, rise"). The hook is a full
**night-to-morning arc**: the sound helps you *fall asleep* at the start, stays minimal through the
middle, and gives a gentle *lift* toward waking at the end — something most rain/piano channels don't do.
Mascot: **Charlie**, a dark blue‑roan cocker spaniel, asleep in a cozy cabin/bedroom.

**Honest framing to preserve:** the "wake" section is a gentle *audio sunrise*, NOT a stage‑aware alarm
(a fixed track can't sense sleep stages the way a smart‑alarm app does). Don't oversell it.

## YOUR PRIORITY TASK
A proper **audio deep‑dive** (rain + calm piano) and a production **8‑hour render engine**.
Everything you need is in **`AUDIO_BRIEF.md`** — read it first. The owner specifically wants you to
explore options and find the *perfect* sound, then ship an engine that renders full‑length tracks.

## What already exists (and its honest state)
- `audio/sleeparc_v4.py`, `audio/sleeparc_v3.py` — iterative **procedural** synths (piano + rain + the
  3‑zone arc). v4 is latest (darker low‑register piano, natural broadband rain). They render **3‑minute
  demo miniatures**, not full tracks. Use as reference + a record of what was tried; you're expected to
  surpass them.
- `audio/sleeparc_demo_v4.wav` — latest 3‑min demo (listen to hear where it's at).
- `video/render_video.py` — **works today.** Turns a still scene into an animated sleep clip:
  rain confined to the window (`--window x0,y0,x1,y1`), warm flicker (`--firexy x,y`), slow zoom
  (`--zoom`), sunrise grade (`--grade`), and muxes audio. 
- `video/MAKE_VIDEOS.md` — how to make full 8h videos efficiently (render a short loop, loop it with
  ffmpeg `-stream_loop`, mux the 8h audio without re‑encoding video).
- `scene/lull_and_lift_charlie_v4.html` — a **code‑drawn** animated scene (vector Charlie + room +
  animated rain). An alternative to the photoreal stills; open in a browser.
- `scene/charlie_build.py` — builder for that scene.
- `assets_from_chatgpt/` — branding board, a 10‑scene concept grid, and `..._v5_Strategy.md` (the visual
  direction + the 10‑video roadmap). These scenes are AI‑generated cozy cabins with a Charlie‑like dog.

## The 10‑video roadmap (from the assets) and what each still needs
1 Rainy Cabin Night · 2 Fireplace &amp; Rain · 3 Thunderstorm Night · 4 Cozy Library · 5 Autumn Storm ·
6 Winter Cabin · 7 Snowstorm Night · 8 Mountain Lodge · 9 Lakeside Cabin · 10 Rainy Sunday Morning.
- Already covered by the current tools: rain‑on‑window + warm flicker (1, 2, 4, 9; partly 3/5/8/10).
- **New video motions to build:** snow on glass (6, 7), lightning flashes (3), falling leaves (5),
  fog drift (8), and a **day/morning palette** for #10 (it's daytime, not night).
- **New audio layers to build:** thunder (3), fireplace crackle (1, 2, 4, 6), wind/blizzard (5, 7),
  birds + brighter morning piano (10), gentle lake/water (9).

## Pipeline overview
`still scene image → render_video.py (adds motion) → + full 8h audio (generate_audio.py, to build) →`
`ffmpeg loop‑to‑length → final MP4.`

## Known gaps / TODO (in priority order)
1. **8‑hour audio engine + the rain/piano deep‑dive** — see `AUDIO_BRIEF.md`. (Main task.)
2. Extra video motions: snow, fog, falling leaves, lightning, day palette for #10.
3. Extra audio layers: thunder, fireplace, wind, birds, brighter morning piano.
4. Clean **16:9 stills** (1920×1080, no caption text, full Charlie in frame) are needed from the image
   generator — the current grid tiles are too small/portrait for finished video. (This is an asset task,
   not code, but note it.)

## Setup
Python 3 with `numpy` (`pip install numpy`; `soundfile`/`scipy` optional and useful for audio I/O and
filtering). `ffmpeg` must be on PATH (audio MP3 export, video muxing). For sample‑based piano you may add
an SFZ/SoundFont renderer (e.g. `sfizz`, `fluidsynth`).

## Guardrails / honest notes
- **Copyright:** keep audio 100% clear — fully synthesized, or CC0/CC‑BY samples with attribution kept in
  a `LICENSES.txt`. No copyrighted recordings or melodies.
- **Wake = gentle audio sunrise**, not a stage‑aware alarm. Keep that honest in any copy.
- **Don't over‑animate the character.** The genre (e.g. leading channels) wins on *atmosphere* — rain,
  warm light, a still cozy scene — not on character animation. Subtle is correct.
