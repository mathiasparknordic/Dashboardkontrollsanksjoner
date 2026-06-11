# audio_research/NOTES.md — rain + calm-piano A/B deep-dive

Status: **research / listening round — engine NOT frozen yet.**
The point of this folder is to pick "the perfect sound" *by ear* before
`generate_audio.py` (the production 8h engine) is finalized. Everything here is
reproducible: `python3 research_demos.py` regenerates every clip from seeds.

## What's in `clips/` (regenerate with `research_demos.py`)

| Clip | Route | Length | What to listen for |
|------|-------|--------|--------------------|
| `rain_A_procedural.wav` | Refined broadband bed (pink tilt + soft LP ~3.6 kHz + slow swell + 10 ms amplitude jitter + L/R decorrelation) | 20 s | Softest/darkest. "Steady rain bed", no patter ticks. |
| `rain_B_hybrid_patter.wav` | Bed A + **granular patter**: sparse band-limited *noise-burst* droplets (never sines), Poisson timing, random pan/colour | 20 s | More realistic "patter". Brighter. Any tick feel too electronic? |
| `rain_C_window_surface.wav` | Hybrid B + light resonant **rain-on-glass** colour | 20 s | Cozier/"indoors" tilt. Is the resonance pleasant or boxy? |
| `piano_A_additive_felt.wav` | Same notes → **additive inharmonic** felt model (evolved from v4: few partials, steep HF rolloff, low register, soft felt-hammer noise, short dark reverb) | 28 s | Timbre route A. Smooth, even decay. |
| `piano_B_physical_felt.wav` | Same notes → **Karplus–Strong** damped-string (felt) via IIR loop + dark body LP | 28 s | Timbre route B. More organic/woody decay. |
| `combined_night_arc.wav` | Best-guess mix (hybrid rain + physical piano) with the 3-zone arc **time-compressed to ~36 s** | 36 s | Balance (piano *under* rain) + the gentle end "lift". |

Piano A and B play the **same generated note sequence** (seed 7) so you're judging
*timbre only*, not composition. Both clips carry a low rain bed (−16 dB-ish) so the
piano is heard in context but stays clearly audible.

## Objective sanity checks (not a substitute for your ears)

Measured on the rendered clips:

- **Rain** — broadband, **no tonal pings** (spectral peak-to-median 18–26×; a true
  tonal artifact would be >100×). L/R correlation ≈ 0 → wide, decorrelated stereo.
  Brightness ladder by centroid: A ≈ 3.1 kHz (softest) < C ≈ 4.1 kHz < B ≈ 4.9 kHz.
- **Piano** — both routes are **dark**: negligible energy above 6 kHz (<0.7 %). The
  high tonal-peak number is just the notes (expected for piano).
- **Levels** — no clipping anywhere (peaks ≤ 0.77); soft-clip safety on the bus.

So all options are technically valid and on-brief. **What remains is taste**, which
is why this goes to a listening round before the engine is frozen.

## Lessons from v1–v4 that were honored here (not repeated)

- No additive high partials / no shrill "high strings" → few partials, steep rolloff,
  low register, soft attack (piano A).
- **No tonal sine droplets** for rain → patter is band-limited *noise* bursts only.
- Avoided heavy LP (→ wind) and flat white noise (→ hiss): pink tilt + gentle LP +
  amplitude micro-variation + slow swell + stereo decorrelation.

## Open questions for the listening round (taste calls)

1. **Rain:** A (soft bed), B (bed + patter), or C (window colour)? Or a blend
   (e.g. B's patter at lower level over A's bed)?
2. **Piano:** A (additive felt) or B (physical/Karplus felt)? Darker still? Sparser?
3. **Balance:** in `combined_night_arc`, is the piano sitting far enough *under* the
   rain? Is the end "lift" too much / too little?

## Known limitation in this sandbox (honest note)

The brief's recommended **sampled** piano route (Salamander Grand, CC-BY via an SFZ
player) and **CC0 rain field recordings** need network access + `sfizz`/sample
downloads, which aren't available here — so route "B (sampled)" for piano is
represented by a *physical-model* synth instead of true samples. `generate_audio.py`
will expose a pluggable piano source so a sampled instrument can drop in later
(with `LICENSES.txt` attribution). No copyrighted audio is used anywhere.

## Next step (after your feedback)

Freeze choices → build `generate_audio.py`: chunked/streaming N-hour render with
**unbroken rain phase across chunks** (no boundary clicks), full-timeline note
schedule, the night arc as `--hours` / `--wake-lift-min` params, MP3 export + a
60–90 s preview.

---

# ROUND 2 — after listening feedback + real-rain / classical-piano research

**Feedback that drove this round**
- Rain v1 was **"too monotone — a combination is best"**; *"analyze real rain
  (films, clips) as inspiration."*
- Piano was **"much better in both"**; *"use various classical piano as
  inspiration."*
- Combined arc: **"milder lift."**

**How it was researched (copyright-safe).** Three web-research passes gathered the
*acoustic characteristics* of real rain and real (felt/classical) piano — physics,
spectra, dynamics, voicing principles — **never any copyrighted recording or
melody.** Everything below is still 100 % synthesized. Key sources at the bottom.

## What changed

### Rain → `rain_v2.py` (layered, de-monotoned)
Replaced the single broadband bed with the **4–5 layer model** the literature agrees
on (Audiokinetic pure-synthesis rain; SIGGRAPH'19 impact+bubble model; Minnaert
bubble physics; granular Poisson scattering):
- **3 decorrelated noise beds** — distant wash (brown, 80–400 Hz), mid **"boiling"**
  (pink, 400–2 kHz, amplitude-modulated by filtered noise), high boiling (pink,
  2.5–8 kHz). Independent L/R sources → wide field.
- **Poisson-scattered patter** — band-limited **noise-burst** grains (never tonal),
  center-freq spread, **log-distributed amplitude** (many quiet, few loud, like real
  rain), random pan/length.
- **Sparse resonant "plinks"** — small fraction of drops use a high-Q damped
  resonator with a **rising-pitch glide** (Minnaert: a shrinking bubble rises in
  pitch — reads as *water*, not synth), centred.
- **1/f "breathing"** — a smoothed brown-noise master contour drives density +
  brightness over a slow timescale (minutes in production; sped up for these clips)
  → swells and lulls with **no period**.
- **Sleep bus** — low-cut ~35 Hz, high roll-off ~9–10 kHz, brown tilt; movement is
  in the *filters*, not big level pumps (avoids wind/whoosh).
- Presets: **light** (sleepy/dark), **steady** (the balanced "combination"),
  **window** (brighter, crisp glass tapping + light resonance).

### Piano → `voice_felt_v2.py` (felt voice from piano acoustics)
- **Double-decay (ADBDR)** amplitude: fast initial decay → long tail, **per partial**
  (higher partials decay faster ~1/√n) → timbre darkens as the note rings.
- **Register-scaled inharmonicity** B (fₙ = n·f₀·√(1+B·n²)).
- **Unison detune** (±1.5–4 cents, 2–3 strings) → gentle beating/warmth.
- **Felt character**: soft low-passed strike + quiet mechanical/key-noise transient.
- **Body resonance** formants (~95/200/400 Hz + broad ~1.8 kHz) for "wood."
- Dark, low **sympathetic-resonance bloom** (cheap diffuse convolution) for the
  pedal halo.

### Combined arc → **milder lift**
Zone-3 piano now returns only *gently* (peak level ~0.70 vs ~0.95 before) and stays
under the rain — an honest, subtle "audio sunrise," not a wake alarm.

## Objective check — v2 vs v1 (not a substitute for your ears)

| Metric | v1 rain | v2 rain | Reading |
|--------|---------|---------|---------|
| Liveliness (RMS-envelope CoV) | 0.22 | **0.30** | ~35 % more dynamic variation = less monotone |
| L/R correlation | ~0.0 | **+0.05…+0.17** | still a wide, decorrelated stereo field |
| Tonal-peak (rain) | 18–26× | **8–14×** | no tonal pings; even cleaner |
| Centroid ladder | — | light 2.8 k · steady 3.4 k · window 4.4 kHz | clear sleepy→crisp range |

Piano v2 centroid ≈ 2.58 kHz (darker/more felt than v1's ~2.9 kHz), liveliness 0.33.

## Round-2 clips to listen to (`clips/`)
- `rain_v2_light.wav`, `rain_v2_steady.wav`, `rain_v2_window.wav`
- `piano_v2_felt.wav` (same note seed 7 as round 1 → direct A/B vs the old voices)
- `combined_v2_milder_arc.wav` (v2 rain + v2 piano, **milder** end-lift)

## Open questions for round 2
1. Rain: does **steady** read as real rain now (less monotone)? Want it darker
   (**light**) or crisper (**window**)? Or a blend / different default density?
2. Piano: is the felt voice the keeper? Darker/sparser still?
3. Combined: is the **milder lift** right now, and is the piano far enough under the
   rain?

## Research sources (characteristics only — no audio reused)
Rain: Audiokinetic "Generating Rain With Pure Synthesis"; Liu/Cheng/Tong,
"Physically-based statistical simulation of rain sound" (SIGGRAPH 2019); Minnaert
resonance (f·a ≈ 3.26 m/s); NASA Earth Observatory "Listening to Raindrops";
Nystuen acoustic-disdrometer (drizzle 13–25 kHz, big drops 1–5 kHz); DAFx rain
synthesis; granular-synthesis grain-length/envelope standards (Truax/SFU).
Piano: piano string inharmonicity & tuning (Edinburgh/UB); "Sines, Transients,
Noise" neural piano modelling (double-decay/ADBDR); QMUL decay modelling; Euphonics
7.3 (multiple strings, double decays, soundboard); sympathetic resonance
(Pianoo/Wikipedia/KVR convolution trick); Salamander Grand (CC-BY — attribution if
ever used). Copyright: scales/modes/chord-progressions are not copyrightable;
specific melodies are — engine draws from modal pools, never a known tune.
