#!/usr/bin/env python3
"""
research_demos_v2.py - SECOND A/B round, after listening feedback + research.

Feedback driving this round:
  - Rain v1 was "too monotone" -> use real-rain acoustics: layered beds + Poisson
    patter + resonant drops + 1/f breathing (rain_v2.render_rain).
  - Piano "good in both" -> a single improved felt voice from piano acoustics
    (voice_felt_v2): double-decay, inharmonicity, unison detune, body resonance.
  - "Milder lift" -> gentler Zone-3 rise in the combined night arc.

Outputs (clips/):
  rain_v2_light.wav, rain_v2_steady.wav, rain_v2_window.wav
  piano_v2_felt.wav            (new voice, same note seed 7 as round 1 for A/B vs old)
  combined_v2_milder_arc.wav   (v2 rain + v2 piano, MILD end-lift)
"""
import os
import numpy as np

from rain_v2 import render_rain
from voice_felt_v2 import voice_felt_v2

SR = 44100
TWO = 2 * np.pi
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "clips")
os.makedirs(OUT, exist_ok=True)


def write_wav(name, stereo, peak=0.92, normalize=True, master=1.0):
    import wave
    mix = np.asarray(stereo, dtype=np.float64)
    if normalize:                       # scale to peak (good for single-element clips)
        mix = mix / (np.max(np.abs(mix)) + 1e-9) * peak
    else:                               # fixed gain: PRESERVES relative balance
        mix = mix * master
    mix = np.tanh(mix * 1.08) / np.tanh(1.08) * peak
    ints = (mix.T * 32767.0).astype("<i2")
    path = os.path.join(OUT, name)
    with wave.open(path, "wb") as wf:
        wf.setnchannels(2); wf.setsampwidth(2); wf.setframerate(SR); wf.writeframes(ints.tobytes())
    print("wrote %-30s %5.1f s  %4.1f MB" % (name, mix.shape[1] / SR, os.path.getsize(path) / 1e6))


def fade(stereo, fin=1.5, fout=2.0):
    N = stereo.shape[1]; fi, fo = int(fin * SR), int(fout * SR)
    stereo[:, :fi] *= np.linspace(0, 1, fi); stereo[:, -fo:] *= np.linspace(1, 0, fo)
    return stereo


# -------- piano scheduling (modal, sparse, copyright-safe) + felt voice
def schedule_notes(dur, seed, density=2.8, present=False):
    rng = np.random.default_rng(seed)
    low = np.array([110.00, 130.81, 146.83, 164.81, 196.00, 220.00])   # A-aeolian-ish pool
    mid = np.array([261.63, 293.66, 329.63, 392.00])
    notes, t = [], 1.0
    while t < dur - 3.0:
        scale = mid if rng.random() < (0.30 if present else 0.10) else low
        freq = float(scale[rng.integers(len(scale))])
        notes.append((t, freq, rng.uniform(3.4, 6.8),
                      rng.uniform(0.34, 0.62) * (1.08 if present else 1.0),
                      rng.uniform(0.36, 0.64)))
        t += density * rng.uniform(0.7, 1.3)
    return notes


def _ir(seed, L=0.9):
    m = int(L * SR); r = np.random.default_rng(seed); tt = np.arange(m) / SR
    h = r.standard_normal(m) * np.exp(-tt / 0.30)
    h = np.convolve(h, np.ones(28) / 28, "same")
    return h / (np.max(np.abs(h)) + 1e-9)


def _conv(x, h):
    Ln = len(x) + len(h) - 1; nf = 1 << int(np.ceil(np.log2(Ln)))
    return np.fft.irfft(np.fft.rfft(x, nf) * np.fft.rfft(h, nf), nf)[:len(x)]


def render_piano(notes, N, wet=0.16):
    Lp = np.zeros(N); Rp = np.zeros(N)
    for i, (start, freq, length, vel, pan) in enumerate(notes):
        w = voice_felt_v2(freq, length, vel, seed=1000 + i, sr=SR)
        i0 = int(start * SR); i1 = min(i0 + len(w), N); seg = w[:i1 - i0] * 0.18
        Lp[i0:i1] += seg * np.sqrt(1 - pan); Rp[i0:i1] += seg * np.sqrt(pan)
    # dark sympathetic-resonance / pedal bloom (cheap: dark diffuse convolution, low level)
    wl = _conv(Lp, _ir(101)); wr = _conv(Rp, _ir(202))
    wl /= (np.max(np.abs(wl)) + 1e-9); wr /= (np.max(np.abs(wr)) + 1e-9)
    pk = max(np.max(np.abs(Lp)), np.max(np.abs(Rp)), 1e-9)
    return np.vstack([Lp * (1 - wet) + wl * pk * wet, Rp * (1 - wet) + wr * pk * wet])


def build_rain():
    for preset in ("light", "steady", "window"):
        x = render_rain(26.0, seed=11, preset=preset, sr=SR)
        write_wav("rain_v2_%s.wav" % preset, fade(x))


def build_piano():
    dur = 28.0; N = int(dur * SR)
    notes = schedule_notes(dur, seed=7, density=2.6, present=True)   # same seed as round 1
    p = render_piano(notes, N)
    rain = render_rain(dur, seed=11, preset="light", sr=SR) * 0.16   # low bed for context
    write_wav("piano_v2_felt.wav", fade(np.vstack([p[0] + rain[0], p[1] + rain[1]])))


def build_combined():
    """Time-compressed night arc with a MILDER end-lift (per feedback).
    Renders base layers once, then emits two rain/piano BALANCE options
    (rain a notch lower than round 1, per feedback)."""
    dur = 40.0; N = int(dur * SR); t = np.arange(N) / SR
    z1, z2 = 10.0, 30.0
    notes = schedule_notes(dur, seed=13, density=2.4)
    piano = render_piano(notes, N)
    rain = render_rain(dur, seed=11, preset="steady", sr=SR)
    # base contours (same shapes as before)
    rbase = np.interp(t, [0, z1, (z1 + z2) / 2, z2, dur], [0.42, 0.55, 0.80, 0.70, 0.46])
    # MILDER lift: zone-3 piano returns only gently, stays low under the rain
    pbase = np.interp(t, [0, z1, (z1 + z2) / 2, z2, dur], [0.80, 0.60, 0.30, 0.50, 0.70])
    # Better balance: keep PIANO FIXED, only lower the rain (per feedback "rain a
    # bit lower"). One shared fixed master (no per-file peak-norm, which would
    # re-pin loudness and cancel the change) -> piano identical across variants,
    # rain audibly lower. rain_gain 1.0 was the round-1 1:1 mix.
    pmix = np.vstack([piano[0] * pbase, piano[1] * pbase])
    rmix = np.vstack([rain[0] * rbase, rain[1] * rbase])
    variants = {"balanceE": 0.18, "balanceF": 0.10}     # rain as soft background (+3 / -2 dB vs piano)
    mixes = {tag: fade(pmix + rmix * rg) for tag, rg in variants.items()}
    master = 0.92 / (max(np.max(np.abs(m)) for m in mixes.values()) + 1e-9)
    for tag, m in mixes.items():
        write_wav("combined_v2_%s.wav" % tag, m, normalize=False, master=master)


if __name__ == "__main__":
    print("Rendering v2 A/B clips -> %s" % OUT)
    build_rain()
    build_piano()
    build_combined()
    print("done.")
