#!/usr/bin/env python3
"""
research_demos.py - A/B demo generator for Lull & Lift (rain + calm piano deep-dive).

Goal of THIS script (per AUDIO_BRIEF.md): produce short, reproducible A/B clips so a
human can pick "the perfect sound" by ear BEFORE the production 8h engine is frozen.
It is deliberately NOT the production engine - it renders ~20-30s comparison clips.

Routes compared:
  RAIN
    A  procedural   - refined broadband bed (pink tilt + soft LP + slow swell +
                      fast smoothed amplitude jitter + L/R decorrelation). No tones.
    B  hybrid       - bed A + sparse GRANULAR patter built from band-limited noise
                      bursts (never sines), Poisson timing, random pan/colour.
    C  window       - hybrid B + light resonant "rain-on-glass" surface colour.
  PIANO  (same generated notes through two sound sources)
    A  additive_felt   - darker/softer inharmonic additive model (evolved from v4).
    B  physical_felt   - Karplus-Strong damped-string (felt) model via lfilter loop.
  COMBINED
    night_arc       - best-guess rain + piano with the 3-zone arc, time-compressed.

Everything is seeded for reproducibility. Output: clips/*.wav (44.1 kHz, 16-bit stereo).

Usage:  python3 research_demos.py
"""
import os
import numpy as np
from scipy.signal import lfilter

SR = 44100
TWO = 2 * np.pi
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "clips")
os.makedirs(OUT, exist_ok=True)


# ---------------------------------------------------------------- io helpers
def write_wav(name, stereo, peak=0.92):
    """stereo: shape (2, N) float. Normalise, soft-clip, write 16-bit WAV."""
    import wave
    mix = np.asarray(stereo, dtype=np.float64)
    m = np.max(np.abs(mix)) + 1e-9
    mix = mix / m * peak
    mix = np.tanh(mix * 1.1) / np.tanh(1.1) * peak
    ints = (mix.T * 32767.0).astype("<i2")
    path = os.path.join(OUT, name)
    with wave.open(path, "wb") as wf:
        wf.setnchannels(2)
        wf.setsampwidth(2)
        wf.setframerate(SR)
        wf.writeframes(ints.tobytes())
    print("wrote %-30s %5.1f s  %4.1f MB" %
          (name, mix.shape[1] / SR, os.path.getsize(path) / 1e6))


def fade(stereo, fin=1.5, fout=2.0):
    N = stereo.shape[1]
    fi, fo = int(fin * SR), int(fout * SR)
    stereo[:, :fi] *= np.linspace(0, 1, fi)
    stereo[:, -fo:] *= np.linspace(1, 0, fo)
    return stereo


# ---------------------------------------------------------------- rain DSP
def _spectral_shape(N, lp_hz=3600.0, lp_order=1.6):
    """Frequency-domain shaping curve: pink tilt + soft low-pass + sub removal."""
    f = np.fft.rfftfreq(N, 1 / SR)
    shape = 1.0 / np.sqrt(np.maximum(f, 1.0))            # pink tilt (-3 dB/oct)
    shape *= 1.0 / (1.0 + (f / lp_hz) ** lp_order)        # soft LP -> rain not hiss
    shape *= f / np.sqrt(f ** 2 + 45.0 ** 2)             # high-pass out the sub rumble
    return shape


def rain_bed(N, seed, lp_hz=3600.0, swell_hz=0.05):
    """One channel of broadband procedural rain. Returns float array length N."""
    r = np.random.default_rng(seed)
    shape = _spectral_shape(N, lp_hz=lp_hz)
    base = np.fft.irfft(np.fft.rfft(r.standard_normal(N)) * shape, n=N)
    base /= (np.max(np.abs(base)) + 1e-9)
    # organic texture: slow swell * fast *smoothed* amplitude jitter (patter, no tones)
    jit = r.standard_normal(N)
    jit = np.convolve(jit, np.ones(440) / 440, "same")   # ~10 ms smoothing
    jit = (jit - jit.min()) / (jit.max() - jit.min() + 1e-9)
    t = np.arange(N) / SR
    swell = 0.85 + 0.15 * np.sin(TWO * swell_hz * t + r.uniform(0, 6))
    return base * (0.55 + 0.45 * jit) * swell


def droplet_patter(N, seed, rate=70.0, level=0.5):
    """Sparse GRANULAR patter: band-limited noise bursts (NEVER sines).
    rate = mean droplets/sec. Returns (L, R) tuple."""
    r = np.random.default_rng(seed)
    L = np.zeros(N)
    R = np.zeros(N)
    n_drops = int(rate * N / SR)
    # pre-build a few short noise-burst grains at different "colours"
    starts = np.sort(r.integers(0, N, size=n_drops))
    for s in starts:
        glen = int(r.uniform(0.004, 0.012) * SR)         # 4-12 ms grain
        if s + glen >= N:
            continue
        g = r.standard_normal(glen)
        # band-limit the burst (one-pole HP then LP) so it reads as a "tick", not a click
        hp = r.uniform(700, 2200)
        lp = hp + r.uniform(1500, 4000)
        a_hp = np.exp(-TWO * hp / SR)
        g = lfilter([1, -1], [1, -a_hp], g)              # crude high-pass
        a_lp = np.exp(-TWO * lp / SR)
        g = lfilter([1 - a_lp], [1, -a_lp], g)           # crude low-pass
        env = np.exp(-np.arange(glen) / (glen * 0.32))    # fast decay transient
        g = g * env
        g /= (np.max(np.abs(g)) + 1e-9)
        amp = level * r.uniform(0.25, 1.0)
        pan = r.uniform(0.1, 0.9)
        L[s:s + glen] += g * amp * np.sqrt(1 - pan)
        R[s:s + glen] += g * amp * np.sqrt(pan)
    return L, R


def window_colour(x, seed, amount=0.35):
    """Light resonant 'rain-on-glass' surface colour: a couple of soft resonators
    mixed in under the dry bed. Subtle - too much = a 'boing'."""
    r = np.random.default_rng(seed)
    wet = np.zeros_like(x)
    for fc in (r.uniform(900, 1300), r.uniform(1800, 2600)):
        bw = fc / 6.0
        rr = np.exp(-np.pi * bw / SR)
        th = TWO * fc / SR
        b = [1 - rr]
        a = [1, -2 * rr * np.cos(th), rr * rr]
        wet += lfilter(b, a, x)
    wet /= (np.max(np.abs(wet)) + 1e-9)
    return x * (1 - amount) + wet * amount * (np.max(np.abs(x)) + 1e-9)


# ---------------------------------------------------------------- piano: notes
def schedule_notes(dur, seed, density=2.8, present=False):
    """Generative low-mid pentatonic/modal note list: (start, freq, length, vel, pan).
    Sparse, rubato, soft, NO repeating motif. Seeded."""
    rng = np.random.default_rng(seed)
    # low-mid register A-minor pentatonic-ish pool (warm, consonant, dark)
    low = np.array([110.00, 130.81, 146.83, 164.81, 196.00, 220.00])
    mid = np.array([261.63, 293.66, 329.63, 392.00])
    notes = []
    t = 1.0
    while t < dur - 3.0:
        p_mid = 0.30 if present else 0.10
        scale = mid if rng.random() < p_mid else low
        freq = float(scale[rng.integers(len(scale))])
        length = rng.uniform(3.4, 6.8)
        vel = rng.uniform(0.34, 0.66) * (1.1 if present else 1.0)
        pan = rng.uniform(0.34, 0.66)
        notes.append((t, freq, length, vel, pan))
        gap = density * rng.uniform(0.7, 1.3)
        t += gap
    return notes


# ---------------------------------------------------------------- piano voice A
def voice_additive(freq, length, vel, seed):
    n = int(length * SR)
    if n <= 0:
        return np.zeros(0)
    tt = np.arange(n) / SR
    B = 0.00035                                          # inharmonicity
    out = np.zeros(n)
    for k in range(1, 9):                                # few partials -> dark
        fk = freq * k * np.sqrt(1 + B * k * k)
        if fk > 4200:
            break
        amp = 1.0 / (k ** 1.6)                           # steep rolloff
        tau = length * 0.55 / (1 + 1.0 * (k - 1))        # highs fade fast
        det = freq * 0.0004 * k
        out += amp * np.exp(-tt / max(tau, 0.04)) * 0.5 * (
            np.sin(TWO * fk * tt) + np.sin(TWO * (fk + det) * tt))
    na = int(0.010 * SR)                                 # soft felt hammer noise
    if na > 0:
        r = np.random.default_rng(seed)
        nz = np.convolve(r.standard_normal(na), np.ones(7) / 7, "same")
        out[:na] += nz * np.exp(-np.arange(na) / (na * 0.4)) * 0.32
    atk = int(0.009 * SR)
    out[:atk] *= np.linspace(0, 1, atk)
    out /= (np.max(np.abs(out)) + 1e-9)
    return out * vel


# ---------------------------------------------------------------- piano voice B
def voice_physical(freq, length, vel, seed):
    """Karplus-Strong damped string (felt-piano flavour) via an IIR feedback comb
    with a one-zero averaging low-pass in the loop. Renders a more organic decay."""
    n = int(length * SR)
    if n <= 0:
        return np.zeros(0)
    r = np.random.default_rng(seed)
    Ld = max(2, int(round(SR / freq)))                   # delay length = period
    # felt hammer excitation: short LOW-PASSED noise burst (soft strike, not bright)
    exc_len = min(n, int(0.012 * SR) + Ld)
    exc = np.zeros(n)
    burst = r.standard_normal(exc_len)
    burst = np.convolve(burst, np.ones(9) / 9, "same")   # darken the strike (felt)
    exc[:exc_len] = burst * np.exp(-np.arange(exc_len) / (exc_len * 0.5))
    # loop: y[k] = exc[k] + g*(y[k-Ld] + y[k-Ld-1])/2  -> denominator IIR
    g = 0.494 + 0.004 * np.exp(-(freq - 110.0) / 400.0)  # decay; clamp <0.5 for stability
    g = float(np.clip(g, 0.40, 0.4985))
    a = np.zeros(Ld + 2)
    a[0] = 1.0
    a[Ld] = -g
    a[Ld + 1] = -g
    out = lfilter([1.0], a, exc)
    # gentle body/output low-pass + soft attack
    aout = np.exp(-TWO * 2600.0 / SR)
    out = lfilter([1 - aout], [1, -aout], out)
    atk = int(0.006 * SR)
    out[:atk] *= np.linspace(0, 1, atk)
    out /= (np.max(np.abs(out)) + 1e-9)
    return out * vel


# ---------------------------------------------------------------- short dark reverb
def _ir(seed, L=0.9):
    m = int(L * SR)
    r = np.random.default_rng(seed)
    tt = np.arange(m) / SR
    h = r.standard_normal(m) * np.exp(-tt / 0.30)
    h = np.convolve(h, np.ones(28) / 28, "same")         # dark
    return h / (np.max(np.abs(h)) + 1e-9)


def _conv(x, h):
    Ln = len(x) + len(h) - 1
    nf = 1 << int(np.ceil(np.log2(Ln)))
    return np.fft.irfft(np.fft.rfft(x, nf) * np.fft.rfft(h, nf), nf)[:len(x)]


def render_piano(notes, voice_fn, N, wet=0.15):
    """Place notes (stereo) and add short dark reverb. Returns (2, N)."""
    Lp = np.zeros(N)
    Rp = np.zeros(N)
    for i, (start, freq, length, vel, pan) in enumerate(notes):
        w = voice_fn(freq, length, vel, seed=1000 + i)
        i0 = int(start * SR)
        i1 = min(i0 + len(w), N)
        seg = w[:i1 - i0] * 0.18
        Lp[i0:i1] += seg * np.sqrt(1 - pan)
        Rp[i0:i1] += seg * np.sqrt(pan)
    wl = _conv(Lp, _ir(101))
    wr = _conv(Rp, _ir(202))
    wl /= (np.max(np.abs(wl)) + 1e-9)
    wr /= (np.max(np.abs(wr)) + 1e-9)
    pk = max(np.max(np.abs(Lp)), np.max(np.abs(Rp)), 1e-9)
    return np.vstack([Lp * (1 - wet) + wl * pk * wet,
                      Rp * (1 - wet) + wr * pk * wet])


# ================================================================ build clips
def build_rain_clips():
    dur = 20.0
    N = int(dur * SR)
    # A: procedural bed
    a = np.vstack([rain_bed(N, 11), rain_bed(N, 23)])
    write_wav("rain_A_procedural.wav", fade(a.copy()))
    # B: hybrid (bed + granular patter)
    pL, pR = droplet_patter(N, 71, rate=80.0, level=0.55)
    b = np.vstack([rain_bed(N, 11) * 0.9 + pL * 0.5,
                   rain_bed(N, 23) * 0.9 + pR * 0.5])
    write_wav("rain_B_hybrid_patter.wav", fade(b.copy()))
    # C: window surface colour on the hybrid
    c = np.vstack([window_colour(b[0], 5), window_colour(b[1], 6)])
    write_wav("rain_C_window_surface.wav", fade(c.copy()))


def build_piano_clips():
    dur = 28.0
    N = int(dur * SR)
    notes = schedule_notes(dur, seed=7, density=2.6, present=True)
    # a low rain bed so timbre is judged in context, but piano stays audible
    bedL = rain_bed(N, 11) * 0.16
    bedR = rain_bed(N, 23) * 0.16
    for tag, fn in (("A_additive_felt", voice_additive),
                    ("B_physical_felt", voice_physical)):
        p = render_piano(notes, fn, N, wet=0.16)
        out = np.vstack([p[0] + bedL, p[1] + bedR])
        write_wav("piano_%s.wav" % tag, fade(out))


def build_combined():
    """Time-compressed night arc: zone1 -> zone2 -> zone3 in ~36 s so the
    rain/piano balance and the 'lift' are audible in one clip."""
    dur = 36.0
    N = int(dur * SR)
    t = np.arange(N) / SR
    z1, z2 = 9.0, 27.0   # compressed zone boundaries (s)
    notes = schedule_notes(dur, seed=13, density=2.4)
    piano = render_piano(notes, voice_physical, N, wet=0.16)
    # rain: hybrid bed
    pL, pR = droplet_patter(N, 91, rate=85.0, level=0.5)
    rainL = rain_bed(N, 11) * 0.9 + pL * 0.5
    rainR = rain_bed(N, 23) * 0.9 + pR * 0.5
    # arc envelopes
    rlvl = np.interp(t, [0, z1, (z1 + z2) / 2, z2, dur], [0.40, 0.55, 0.82, 0.70, 0.40])
    plvl = np.interp(t, [0, z1, (z1 + z2) / 2, z2, dur], [0.85, 0.65, 0.30, 0.55, 0.95])
    L = piano[0] * plvl + rainL * rlvl
    R = piano[1] * plvl + rainR * rlvl
    write_wav("combined_night_arc.wav", fade(np.vstack([L, R])))


if __name__ == "__main__":
    print("Rendering A/B research clips -> %s" % OUT)
    build_rain_clips()
    build_piano_clips()
    build_combined()
    print("done.")
