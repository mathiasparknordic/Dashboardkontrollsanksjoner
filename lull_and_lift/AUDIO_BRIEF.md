# AUDIO_BRIEF.md — finding the *perfect* rain + calm piano for Lull &amp; Lift

This is the main task. Do a proper deep‑dive into **rain sounds** and **calm sleep piano**, find the best
sound, and ship a production **8‑hour render engine**. Treat the existing `audio/sleeparc_v*.py` as a
starting point and a log of mistakes — you are expected to beat them.

## Goal
Two layers — **rain** + **calm piano** (plus an optional low warm pad) — that:
1. help the listener fall asleep,
2. stay **non‑fatiguing across a full ~8‑hour night**,
3. give a gentle **lift toward waking** at the end.

## Hard constraints
- **100% copyright‑clear.** Either fully synthesized, or built from **CC0 / appropriately‑licensed**
  samples. Verify every file's license and keep `LICENSES.txt` (e.g. attribute CC‑BY). No copyrighted
  recordings, no recognizable copyrighted melodies.
- **No audible looping over hours** — generative/varied, or long non‑repeating renders.
- **No tonal artifacts in the rain. No earworm melodies in the piano.**

## What "perfect" means here — evaluation criteria
**Rain:** reads as *real rain* — broadband but soft (not white‑noise hiss, not a wind/whoosh), with
natural micro‑variation and slow swells, gentle high‑frequency "patter," **no tonal pings**, pleasant in
stereo on **small headband/pillow speakers**, and **no perceptible loop seam**.
**Piano:** slow, sparse, **low‑mid register**, soft, warm, consonant, lots of space/silence, natural long
decay, **no melodic hooks** (nothing the brain latches onto), and it should sit *under* the rain as
ambience — sound like a real **felt/soft piano**, not a bright synth or keyboard.
**Together:** balanced so rain masks and piano floats beneath; calm enough to disappear when you stop
attending to it.

## Lessons already learned (do NOT repeat — from v1–v4)
- Additive‑sine piano with many/high partials → sounds like **"high strings" / cheap keyboard**. Fixes
  that helped: few partials, steep high‑frequency rolloff, **low register**, minimal detune, soft attack,
  light short reverb.
- **Tonal sine "droplets"** for rain → sound **electronic/weird**. Never use tonal pings for droplets.
- Heavy low‑pass on noise → sounds like **wind**; flat white noise → **fatiguing hiss**. The sweet spot
  was: pink tilt + gentle low‑pass (~3–4 kHz) + amplitude micro‑variation + sparse **non‑tonal** patter +
  stereo decorrelation + very slow swell.

## Rain — directions to explore (then A/B them)
1. **Procedural** (copyright‑free, full control): noise → spectral shaping (pink tilt + soft LP) →
   multiply by (slow swell × fast *smoothed* amplitude jitter) for organic texture; add sparse droplet
   **transients** built from short **band‑limited noise bursts** (never sine); optional low rumble layer;
   decorrelate L/R. Optional surface coloration: rain‑on‑window vs rain‑on‑roof via resonant filters.
2. **Granular:** scatter many tiny droplet grains with stochastic timing/pitch/pan.
3. **Sample‑based (often the most realistic):** seamless **CC0 rain field recordings** (e.g. Freesound
   CC0) as a bed, layered with procedural variation so it never obviously loops. Verify licenses.
**Recommended:** try a **hybrid** (best procedural bed + a touch of granular patter) and compare it head‑
to‑head against a CC0 sample bed. Produce 20–30 s clips of each and pick by ear against the criteria above.

## Calm piano — directions to explore (then A/B them)
1. **Composition (generative):** a pentatonic/modal note pool in a **low‑mid octave**; sparse, rubato
   timing; soft velocities; long gaps; **no repeating motif**; note density follows the night arc. Use a
   seeded RNG for reproducibility.
2. **Sound source — compare two routes:**
   a. **Improved synthesis** — the current inharmonic model, but darker/softer (felt‑piano character).
   b. **Sampled piano** for realism — e.g. the **Salamander Grand Piano** (CC‑BY, must attribute) rendered
      via an SFZ player (`sfizz` / similar), or another CC‑licensed **soft/felt** piano. A good sampled
      instrument usually sounds far more real than synthesis.
   Render the *same generated notes* through both and A/B.
3. Add subtle space (short, **dark** convolution reverb) and keep the piano **low in the mix**.

## The night arc (timed to wake)
- **Zone 1 (0–45 min):** gentle, slightly more present piano; calm rain.
- **Zone 2 (the long middle):** piano recedes to **very sparse**; steady rain bed carries it; no events.
- **Zone 3 (last 30–60 min):** "audio sunrise" — piano returns a touch brighter/warmer; tempo/volume rise
  gently. (Honest: a gentle lift, **not** a stage‑aware alarm.)
Make **total duration** and **wake‑lift length** parameters.

## Deliverables
1. `audio_research/` — short **A/B demo clips** of the rain and piano options you tried, plus `NOTES.md`
   describing what you found, what you chose, and **why** (reference the criteria above).
2. `generate_audio.py` — the production engine:
   - CLI like: `--hours 8 --wake-lift-min 45 --rain {light,steady,heavy} --seed N --out track.wav`
   - **Chunked/streaming** render so memory stays sane for 8 h: write WAV frames incrementally; schedule
     piano notes across the *full* timeline; keep the rain **phase/continuity unbroken across chunks**
     (no clicks at boundaries).
   - Also export an **MP3** via ffmpeg and a **60–90 s preview**.
3. Update the README with how to run it, and `LICENSES.txt` for any samples used.

## Then (nice to have, lower priority)
Per‑scene audio variants for the 10‑video roadmap: thunder (#3), fireplace crackle (#1/2/4/6),
wind/blizzard (#5/7), birds + brighter morning piano (#10), gentle lake (#9). Same engine, extra layers.

## Setup
Python 3, `pip install numpy` (`soundfile`/`scipy` recommended). `ffmpeg` on PATH. For SFZ samples add
`sfizz`/`fluidsynth` or a Python SFZ renderer. Keep everything reproducible (seeds, pinned deps).
