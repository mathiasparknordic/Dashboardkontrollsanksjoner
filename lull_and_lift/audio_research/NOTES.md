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
