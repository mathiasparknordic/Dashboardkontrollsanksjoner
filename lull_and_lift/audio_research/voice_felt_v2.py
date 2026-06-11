#!/usr/bin/env python3
"""
voice_felt_v2.py - improved felt/soft-piano voice, informed by piano-acoustics research.

Upgrades over the v4/additive model:
  - DOUBLE-DECAY (ADBDR) amplitude: fast initial decay -> slower long tail, per partial.
  - PER-PARTIAL decay: higher partials decay faster (~1/sqrt(n)) -> timbre darkens in tail.
  - INHARMONICITY B scaled by register (fn = n*f0*sqrt(1+B*n^2)).
  - UNISON detune: 2-3 slightly detuned strings (+/-1.5..4 cents) -> beating/warmth.
  - FELT character: soft slow low-passed strike + quiet mechanical/key noise transient.
  - BODY resonance: light formant EQ (~90/200/400 Hz + broad 1-3 kHz) for "wood".
Pure synthesis, copyright-free. Tunable; numbers are engineering ballparks to taste.
"""
import numpy as np
from scipy.signal import lfilter

TWO = 2 * np.pi


def _register_params(f0):
    """Return (B, n_partials, lp_cut_hz, n_strings) scaled by register."""
    if f0 < 130.0:                       # bass
        return 0.0005, 28, 3200.0, 2
    elif f0 < 520.0:                     # mid
        return 0.0020, 14, 4200.0, 3
    else:                                # upper
        return 0.012, 6, 6000.0, 3


def _double_decay(n, sr, tau_fast, tau_slow, break_level=0.5):
    """ADBDR-ish: sum of a fast and a slow exponential, normalised to start at 1."""
    t = np.arange(n) / sr
    fast = (1.0 - break_level) * np.exp(-t / max(tau_fast, 1e-3))
    slow = break_level * np.exp(-t / max(tau_slow, 1e-3))
    env = fast + slow
    return env / (env[0] + 1e-9)


def voice_felt_v2(freq, length, vel, seed, sr=44100):
    n = int(length * sr)
    if n <= 0:
        return np.zeros(0)
    rng = np.random.default_rng(seed)
    B, n_partials, lp_cut, n_strings = _register_params(freq)
    t = np.arange(n) / sr

    # register-scaled tail length (bass rings far longer than treble)
    if freq < 130.0:
        tau_fast, tau_slow = 0.6, min(length, 18.0)
    elif freq < 520.0:
        tau_fast, tau_slow = 0.3, min(length, 7.0)
    else:
        tau_fast, tau_slow = 0.12, min(length, 2.0)

    out = np.zeros(n)
    # unison string offsets in cents -> slight detune for beating/warmth
    cents = [0.0]
    if n_strings >= 2:
        cents.append(rng.uniform(1.5, 4.0))
    if n_strings >= 3:
        cents.append(-rng.uniform(1.5, 4.0))

    for k in range(1, n_partials + 1):
        fk = freq * k * np.sqrt(1 + B * k * k)
        if fk > 0.45 * sr or fk > 7500:
            break
        amp = 1.0 / (k ** 1.5)                          # steep rolloff (felt = dark)
        # higher partials decay faster: scale both decay constants by ~1/sqrt(k)
        pf = tau_fast / np.sqrt(k)
        ps = tau_slow / np.sqrt(k)
        env = _double_decay(n, sr, pf, ps) * amp
        partial = np.zeros(n)
        for c in cents:
            fc = fk * (2.0 ** (c / 1200.0))
            phase = rng.uniform(0, TWO)
            partial += np.sin(TWO * fc * t + phase)
        out += env * partial / len(cents)

    # felt strike: soft, low-passed short noise burst (longer/darker than a hard hammer)
    na = int(rng.uniform(0.008, 0.016) * sr)
    if na > 0:
        strike = rng.standard_normal(na)
        strike = np.convolve(strike, np.ones(11) / 11, "same")   # darken
        out[:na] += strike * np.exp(-np.arange(na) / (na * 0.5)) * 0.28
    # quiet mechanical/key noise (the "imperfection" that sells felt)
    nk = int(0.020 * sr)
    if nk > 0:
        key = rng.standard_normal(nk) * np.exp(-np.arange(nk) / (nk * 0.3))
        out[:nk] += key * 0.05

    # soft attack
    atk = int(rng.uniform(0.006, 0.014) * sr)
    out[:atk] *= np.linspace(0, 1, atk)

    # brightness roll-off (felt LPF, velocity -> darker when softer)
    cut = lp_cut * (0.7 + 0.3 * vel)
    a_lp = np.exp(-TWO * cut / sr)
    out = lfilter([1 - a_lp], [1, -a_lp], out)

    # body/soundboard resonance: a few light resonant peaks for "wood"
    body = np.zeros(n)
    for fb, q, g in ((95.0, 8, 0.5), (200.0, 9, 0.4), (400.0, 10, 0.3), (1800.0, 3, 0.25)):
        bw = fb / q
        rr = np.exp(-np.pi * bw / sr)
        th = TWO * fb / sr
        body += g * lfilter([1 - rr], [1, -2 * rr * np.cos(th), rr * rr], out)
    out = out + 0.18 * body

    out /= (np.max(np.abs(out)) + 1e-9)
    return out * vel


if __name__ == "__main__":
    # quick self-test render: a few sparse notes
    import wave, os
    sr = 44100
    notes = [(0.5, 146.83, 6.0, 0.5), (3.0, 220.0, 5.0, 0.45),
             (6.5, 196.0, 6.0, 0.5), (10.0, 293.66, 5.0, 0.4)]
    N = int(16 * sr)
    buf = np.zeros(N)
    for i, (s, f, ln, v) in enumerate(notes):
        w = voice_felt_v2(f, ln, v, seed=100 + i)
        i0 = int(s * sr); i1 = min(i0 + len(w), N)
        buf[i0:i1] += w[:i1 - i0] * 0.3
    buf = np.tanh(buf * 1.1) / np.tanh(1.1)
    ints = (np.vstack([buf, buf]).T / (np.max(np.abs(buf)) + 1e-9) * 0.9 * 32767).astype("<i2")
    p = os.path.join(os.path.dirname(os.path.abspath(__file__)), "clips", "_selftest_felt_v2.wav")
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with wave.open(p, "wb") as wf:
        wf.setnchannels(2); wf.setsampwidth(2); wf.setframerate(sr); wf.writeframes(ints.tobytes())
    print("wrote", p)
