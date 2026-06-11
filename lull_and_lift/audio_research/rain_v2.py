#!/usr/bin/env python3
"""
rain_v2.py - layered, non-monotone procedural rain, informed by rain-acoustics research.

Why v1 sounded monotone: a single broadband bed + uniform patter, correlated L/R, static gain.
v2 fixes all three per the literature (Audiokinetic 4-layer model; Minnaert bubble physics;
granular Poisson scattering; 1/f long-term contour):

  LAYERS (each its own RNG stream + own slow, incommensurate modulators):
    1. Distant wash   - brown-ish noise 80-400 Hz, decorrelated L/R, very slow drift.
    2. Mid "boiling"   - pink noise 400-2000 Hz, amplitude-modulated by filtered noise (boil).
    3. High boiling    - pink noise 2.5-8 kHz (sleep-rolled), faster boil, slow LPF wobble.
    4. Near patter     - Poisson-scattered band-limited NOISE-BURST grains (never tonal),
                         center-freq spread, random amp(log)/pan/length.
    5. Big drops       - sparse high-Q resonant "plinks" with a rising-pitch glide (bubble),
                         small fraction only, centred.
  BUS: low-cut ~35 Hz, high roll-off ~9-10 kHz (sleep comfort), gentle soft-clip.
  LONG-TERM: a smoothed 1/f (brown) master intensity contour couples gain+brightness so an
  8 h render breathes ("harder now... lighter now") with no audible period.

Pure synthesis, copyright-free. Presets: light / steady / window.
Designed so the production engine can call render_rain() per chunk with continuous RNG state.
"""
import numpy as np
from scipy.signal import butter, sosfilt

TWO = 2 * np.pi


# ---------------------------------------------------------------- noise helpers
def colored_noise(n, seed, slope=0.5, lo=None, hi=None, sr=44100):
    """FFT-shaped colored noise. slope: 0.5=pink (1/sqrt f), 1.0=brown (1/f).
    Optional band-limit to [lo,hi] Hz via butter sosfilt."""
    rng = np.random.default_rng(seed)
    f = np.fft.rfftfreq(n, 1 / sr)
    f[0] = f[1] if len(f) > 1 else 1.0
    X = np.fft.rfft(rng.standard_normal(n))
    X *= 1.0 / (f ** slope)
    x = np.fft.irfft(X, n=n)
    if lo or hi:
        lo = max(lo or 20.0, 20.0)
        hi = min(hi or sr * 0.49, sr * 0.49)
        sos = butter(2, [lo, hi], "bandpass", fs=sr, output="sos")
        x = sosfilt(sos, x)
    x /= (np.max(np.abs(x)) + 1e-9)
    return x


def slow_contour(n, seed, sr=44100, tau_s=4.0, lo_db=-4.0, hi_db=4.0):
    """Smoothed brown-noise 1/f contour mapped to a linear gain. tau_s = smoothing (s)."""
    rng = np.random.default_rng(seed)
    walk = np.cumsum(rng.standard_normal(n))
    w = int(max(2, tau_s * sr))
    kern = np.ones(w) / w
    walk = np.convolve(walk, kern, "same")
    walk = (walk - walk.min()) / (walk.max() - walk.min() + 1e-9)
    db = lo_db + (hi_db - lo_db) * walk
    return 10 ** (db / 20.0)


def boil_am(n, seed, sr=44100, rate=4.0, depth=0.5):
    """Amplitude-mod envelope from low-pass filtered noise ('boiling'). rate ~ Hz."""
    rng = np.random.default_rng(seed)
    sos = butter(2, max(0.5, rate), "low", fs=sr, output="sos")
    a = sosfilt(sos, rng.standard_normal(n))
    a /= (np.max(np.abs(a)) + 1e-9)
    return 1.0 + depth * a


# ---------------------------------------------------------------- grain banks
def _patter_bank(sr, rng, n=56, bright=False):
    """Band-limited noise-burst grains (the safe, non-tonal patter)."""
    bank = []
    for _ in range(n):
        L = int(rng.uniform(0.003, 0.015) * sr)
        x = rng.standard_normal(L)
        # center-freq spread: mostly low-mid for sleep; a brighter tail for 'window'
        if rng.random() < (0.45 if bright else 0.25):
            fc = rng.uniform(5000, 9500)       # bright drizzle 'tick'
        else:
            fc = rng.uniform(1400, 5000)       # body patter
        Q = rng.uniform(1.0, 3.5)
        lo = max(300.0, fc / (1 + 1 / (2 * Q)))
        hi = min(sr * 0.49, fc * (1 + 1 / (2 * Q)))
        sos = butter(2, [lo, hi], "bandpass", fs=sr, output="sos")
        x = sosfilt(sos, x)
        env = np.exp(-np.arange(L) / (L * 0.30))           # fast attack/decay transient
        env[:max(1, int(0.0004 * sr))] *= np.linspace(0, 1, max(1, int(0.0004 * sr)))
        x *= env
        x /= (np.max(np.abs(x)) + 1e-9)
        bank.append(x.astype(np.float32))
    return bank


def _plink_bank(sr, rng, n=16):
    """Sparse resonant 'plink' drops: damped osc with a RISING pitch glide (bubble)."""
    bank = []
    for _ in range(n):
        dur = rng.uniform(0.012, 0.045)
        L = int(dur * sr)
        t = np.arange(L) / sr
        f0 = rng.uniform(350, 2600)
        glide = rng.uniform(1.1, 1.45)                      # rises 10-45 %
        inst = f0 * (1 + (glide - 1) * (t / dur))
        phase = TWO * np.cumsum(inst) / sr
        tau = dur * rng.uniform(0.25, 0.45)
        y = np.exp(-t / tau) * np.sin(phase)
        y += 0.15 * np.exp(-t / (tau * 0.6)) * rng.standard_normal(L)   # texture, not pure
        y /= (np.max(np.abs(y)) + 1e-9)
        bank.append(y.astype(np.float32))
    return bank


def _scatter(N, sr, rng, bank, rate, amp_lo, amp_hi, pan_spread, intensity=None):
    """Poisson-scatter grains from `bank` into a stereo buffer. Returns (2, N)."""
    L = np.zeros(N, dtype=np.float32)
    R = np.zeros(N, dtype=np.float32)
    # Poisson onsets
    n_ev = int(rate * N / sr * 1.2)
    gaps = rng.exponential(1.0 / max(rate, 1e-6), n_ev)
    onsets = (np.cumsum(gaps) * sr).astype(int)
    onsets = onsets[onsets < N]
    for s in onsets:
        g = bank[rng.integers(len(bank))]
        gl = len(g)
        if s + gl >= N:
            continue
        # log-distributed amplitude: many quiet, few loud (real rain)
        amp = amp_lo * (amp_hi / amp_lo) ** rng.random()
        if intensity is not None:
            amp *= intensity[s]                            # density/level tracks contour
        pan = min(0.98, max(0.02, 0.5 + (rng.random() - 0.5) * pan_spread))
        L[s:s + gl] += g * amp * np.sqrt(1 - pan)
        R[s:s + gl] += g * amp * np.sqrt(pan)
    return np.vstack([L, R]).astype(np.float64)


# ---------------------------------------------------------------- main render
def render_rain(dur, seed=11, preset="steady", sr=44100, demo=True):
    """Render layered rain. preset in {light, steady, window}.
    demo=True speeds the slow modulators so variation is audible in short clips."""
    N = int(dur * sr)
    rng = np.random.default_rng(seed)
    t = np.arange(N) / sr

    # preset knobs
    P = {
        "light":  dict(wash=0.55, mid=0.7, hi=0.18, patter=260, bigdrop=2.5,
                       hp=110, lp=7500, bright=False, pan=1.4, amp=(0.05, 0.5)),
        "steady": dict(wash=0.6,  mid=1.0, hi=0.32, patter=520, bigdrop=4.0,
                       hp=90,  lp=9500, bright=False, pan=1.7, amp=(0.06, 0.8)),
        "window": dict(wash=0.45, mid=0.85, hi=0.5, patter=620, bigdrop=5.0,
                       hp=120, lp=10500, bright=True, pan=1.8, amp=(0.07, 0.95)),
    }[preset]

    # 1/f master intensity contour (couples density + a touch of brightness)
    cscale = 2.0 if demo else 30.0       # faster breathing in demo clips
    intensity = slow_contour(N, seed + 90, sr, tau_s=cscale, lo_db=-4, hi_db=4)

    # --- beds ---
    rfast = 2.5 if demo else 1.0
    washL = colored_noise(N, seed + 1, slope=0.9, lo=80, hi=400, sr=sr) * P["wash"]
    washR = colored_noise(N, seed + 2, slope=0.9, lo=80, hi=400, sr=sr) * P["wash"]
    # slow incommensurate amp LFOs
    for ch, sd in ((0, 11), (1, 17)):
        lfo = 1 + 0.12 * np.sin(TWO * (0.09 * rfast) * t + sd)
        if ch == 0:
            washL *= lfo
        else:
            washR *= lfo

    # mid/high beds: INDEPENDENT L/R noise sources (decorrelated wide field), each
    # with its own boil + slow incommensurate LFO so the stereo image stays open.
    mboil = boil_am(N, seed + 31, sr, rate=3.0 * rfast, depth=0.45) * P["mid"]
    midL = colored_noise(N, seed + 3, slope=0.5, lo=400, hi=2000, sr=sr) * mboil \
        * (1 + 0.08 * np.sin(TWO * 0.11 * rfast * t))
    midR = colored_noise(N, seed + 13, slope=0.5, lo=400, hi=2000, sr=sr) * mboil \
        * (1 + 0.08 * np.sin(TWO * 0.13 * rfast * t + 1.7))

    hboil = boil_am(N, seed + 41, sr, rate=7.0 * rfast, depth=0.5) * P["hi"]
    hiL = colored_noise(N, seed + 4, slope=0.5, lo=2500, hi=min(P["lp"], 8000), sr=sr) * hboil \
        * (1 + 0.10 * np.sin(TWO * 0.19 * rfast * t))
    hiR = colored_noise(N, seed + 14, slope=0.5, lo=2500, hi=min(P["lp"], 8000), sr=sr) * hboil \
        * (1 + 0.10 * np.sin(TWO * 0.23 * rfast * t + 2.3))

    bedL = washL + midL + hiL
    bedR = washR + midR + hiR
    bedL *= intensity
    bedR *= intensity

    # --- patter (Poisson grains) ---
    patter = _scatter(N, sr, rng, _patter_bank(sr, rng, bright=P["bright"]),
                      rate=P["patter"], amp_lo=P["amp"][0], amp_hi=P["amp"][1],
                      pan_spread=P["pan"], intensity=intensity)
    # --- sparse big drops ---
    drops = _scatter(N, sr, rng, _plink_bank(sr, rng),
                     rate=P["bigdrop"], amp_lo=0.06, amp_hi=0.22, pan_spread=0.8)

    L = bedL + patter[0] * 0.9 + drops[0] * 0.7
    R = bedR + patter[1] * 0.9 + drops[1] * 0.7

    # window surface: light resonant 'glass' colour
    if preset == "window":
        for fc, q, g in ((1100, 6, 0.12), (2200, 7, 0.10)):
            bw = fc / q
            sos = butter(2, [max(60, fc - bw), fc + bw], "bandpass", fs=sr, output="sos")
            L += g * sosfilt(sos, L)
            R += g * sosfilt(sos, R)

    # --- bus: low-cut + sleep high roll-off ---
    hp = butter(2, P["hp"], "high", fs=sr, output="sos")
    lp = butter(2, P["lp"], "low", fs=sr, output="sos")
    L = sosfilt(lp, sosfilt(hp, L))
    R = sosfilt(lp, sosfilt(hp, R))

    out = np.vstack([L, R])
    out /= (np.max(np.abs(out)) + 1e-9)
    return out


if __name__ == "__main__":
    import wave, os
    sr = 44100
    for preset in ("light", "steady", "window"):
        x = render_rain(26.0, seed=11, preset=preset, sr=sr)
        x = np.tanh(x * 1.05) / np.tanh(1.05) * 0.92
        ints = (x.T * 32767).astype("<i2")
        p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "clips",
                         "_selftest_rain_v2_%s.wav" % preset)
        os.makedirs(os.path.dirname(p), exist_ok=True)
        with wave.open(p, "wb") as wf:
            wf.setnchannels(2); wf.setsampwidth(2); wf.setframerate(sr); wf.writeframes(ints.tobytes())
        print("wrote", p)
