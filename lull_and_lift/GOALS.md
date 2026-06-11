# GOALS.md — what we are trying to achieve

**Norsk kort:** Målene er (1) lage den **beste mulige lyden** — realistisk regn + rolig piano, helt fri
for opphavsrett, behagelig i 8 timer; (2) lage **alle de 10 videoene** (koselig scene + bevegelse + full
lyd); (3) en **gjenbrukbar pipeline** så nye videoer er enkle. Detaljer + suksesskriterier under.
(Read `AUDIO_BRIEF.md` for the deep audio spec and `CLAUDE.md` for the file map.)

---

## North star
A calm rain‑and‑piano sleep experience with a gentle night‑to‑morning arc, fronted by Charlie the dog —
good enough to use every night, and good enough to publish as a small YouTube channel. Everything must be
**100% copyright‑clear**.

---

## Goal 1 — The best possible AUDIO  *(top priority)*
Realistic, calm, copyright‑clean rain + piano that doesn't fatigue over a full night.

**Done when:**
- [ ] Rain sounds like *real rain* — soft and broadband, **no white‑noise hiss, no wind/whoosh, no tonal
      pings**; natural variation + slow swells; pleasant in stereo on small speakers.
- [ ] Piano is **slow, sparse, low‑register, warm, soft**, no earworm melody; sounds like a real
      felt/soft piano, not a synth; sits *under* the rain.
- [ ] The two are balanced and **non‑fatiguing across ~8 hours** with **no audible loop seam**.
- [ ] The **night arc** works: gentle start → minimal middle → gentle "audio sunrise" lift at the end.
- [ ] 100% copyright‑clear (synth, or CC0/CC‑BY samples with `LICENSES.txt`).
- [ ] Delivered as a **production engine** `generate_audio.py` that renders a full N‑hour track
      (chunked/streaming, no clicks), exports MP3, and produces a short preview + A/B research clips.

## Goal 2 — Produce ALL the videos  *(the 10‑scene slate)*
Each video = a cozy still scene + subtle genre motion + the full‑length audio, exported as one MP4.

The slate (title — length — extra needs beyond rain‑on‑window + warm flicker):
1. Rainy Cabin Night — 8h — fireplace crackle (audio)
2. Fireplace &amp; Rain — 8h — fireplace flicker + crackle
3. Thunderstorm Night — 8h — **lightning flashes (video)** + **thunder (audio)**
4. Cozy Library — 4h — soft fireplace
5. Autumn Storm — 8h — **falling leaves (video)** + wind (audio)
6. Winter Cabin — 10h — **snow on glass (video)** + fireplace
7. Snowstorm Night — 8h — **snow/blizzard (video)** + **wind (audio)**
8. Mountain Lodge — 10h — **fog drift (video)**
9. Lakeside Cabin — 8h — gentle **water/lake (audio)**
10. Rainy Sunday Morning — 8h — **daytime palette (video)** + **birds + brighter morning piano (audio)**

**Done when (per video):**
- [ ] Full Charlie + scene visible in frame (16:9, 1080p), nothing important cropped.
- [ ] Rain/snow stays **on the window**, not over the room; any flicker/flashes look natural.
- [ ] The scene‑specific motion + audio layers above are present.
- [ ] Runs the full advertised length with the matching audio; loops with **no obvious seam**.
- [ ] Exported as a single MP4 ready to upload.

## Goal 3 — A reusable, reproducible pipeline
**Done when:**
- [ ] Making a new video is roughly: pick a clean still → set the window/flicker params → run one script →
      get a finished MP4. Parameters and seeds are documented; results are reproducible.
- [ ] `render_video.py` is extended with the new motions (snow, fog, leaves, lightning, day palette).

---

## Priority order
1. **Audio deep‑dive + 8h engine** (Goal 1) — this is the foundation; do it first.
2. Pick **2–3 lead scenes** (e.g. 1, 2, 3) and produce them end‑to‑end as full videos to prove the
   pipeline, including the new motions/audio layers they need.
3. Roll out the remaining scenes; finish the reusable pipeline (Goal 3).

## Inputs still needed (not code)
- Clean **16:9, 1080p** scene stills, **no caption text**, with the **whole dog in frame** — one per
  video. (The current concept grid is too small/portrait for finished video.)

## Non‑goals / guardrails
- **No copyright risk.** No copyrighted recordings or melodies; samples must be CC0/CC‑BY with attribution.
- **Don't oversell the wake‑up.** It's a gentle audio sunrise, not a stage‑aware alarm.
- **Don't over‑animate Charlie.** The genre wins on atmosphere (rain, warm light, stillness), not motion.
- Keep it calm: nothing bright, sudden, or busy that would wake a sleeper (except the deliberate, gentle
  end‑of‑night lift).
