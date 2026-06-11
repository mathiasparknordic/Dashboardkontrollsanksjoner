import numpy as np, wave, os

sr = 22050
T = 180.0
N = int(sr * T)
t_all = np.arange(N) / sr
z1, z2 = 55.0, 130.0
TWO = 2 * np.pi

Lp = np.zeros(N); Rp = np.zeros(N)   # piano + pad bus
low = np.array([220.00, 261.63, 293.66, 329.63, 392.00])
mid = np.array([440.00, 523.25, 587.33, 659.25, 783.99])

def sched(t, pts_t, pts_v):
    return float(np.interp(t, pts_t, pts_v))

dens_t = [0, z1, (z1 + z2) / 2, z2, T]
dens_v = [2.4, 2.6, 6.5, 5.0, 1.9]

def piano_note(freq, dur, vel, seed):
    n = int(dur * sr)
    if n <= 0:
        return np.zeros(0)
    tt = np.arange(n) / sr
    B = 0.0004                      # string stiffness -> stretched partials
    out = np.zeros(n)
    for k in range(1, 15):
        fk = freq * k * np.sqrt(1 + B * k * k)
        if fk > sr * 0.45:
            break
        amp = 1.0 / (k ** 1.12)
        tau = dur * 0.5 / (1 + 0.7 * (k - 1))   # high partials decay faster
        penv = np.exp(-tt / max(tau, 0.05))
        det = freq * 0.0007 * k                  # two slightly detuned strings
        out += amp * penv * 0.5 * (np.sin(TWO * fk * tt) + np.sin(TWO * (fk + det) * tt))
    na = int(0.012 * sr)                         # hammer attack noise
    if na > 0:
        r = np.random.default_rng(seed)
        nz = np.convolve(r.standard_normal(na), np.ones(5) / 5, mode="same")
        out[:na] += nz * np.exp(-np.arange(na) / (na * 0.3)) * 0.6
    atk = int(0.004 * sr)
    if atk > 0:
        out[:atk] *= np.linspace(0, 1, atk)
    out /= (np.max(np.abs(out)) + 1e-9)
    return out * vel

def add_note(start, freq, dur, vel, pan, seed):
    w = piano_note(freq, dur, vel, seed)
    i0 = int(start * sr); i1 = min(i0 + len(w), N)
    seg = w[: i1 - i0] * 0.16
    Lp[i0:i1] += seg * np.sqrt(1 - pan)
    Rp[i0:i1] += seg * np.sqrt(pan)

rng = np.random.default_rng(7)
t = 1.0; sd = 1
while t < T - 2:
    d = sched(t, dens_t, dens_v)
    pmid = 0.05 if t <= z2 else 0.15 + 0.55 * (t - z2) / (T - z2)
    scale = mid if rng.random() < pmid else low
    add_note(t, float(scale[rng.integers(len(scale))]),
             rng.uniform(3.2, 6.5), rng.uniform(0.32, 0.70),
             rng.uniform(0.32, 0.68), sd)
    sd += 1
    t += d * rng.uniform(0.7, 1.3)

pad = np.zeros(N)                                  # soft drone pad
for f in [110.0, 164.81, 220.0]:
    pad += np.sin(TWO * f * t_all)
lfo = 0.6 + 0.4 * np.sin(TWO * 0.03 * t_all)
padlvl = np.interp(t_all, [0, z1, (z1 + z2) / 2, z2, T], [0.04, 0.05, 0.07, 0.05, 0.035])
pad *= lfo * padlvl
Lp += pad; Rp += pad * 0.98

# --- convolution reverb on the piano bus (soundboard / room body) ---
def make_ir(seed, length=1.2):
    m = int(length * sr)
    r = np.random.default_rng(seed)
    tt = np.arange(m) / sr
    ir = r.standard_normal(m) * np.exp(-tt / 0.40)
    ir = np.convolve(ir, np.ones(12) / 12, mode="same")
    return ir / (np.max(np.abs(ir)) + 1e-9)

def fftconv(x, h):
    L = len(x) + len(h) - 1
    nfft = 1 << int(np.ceil(np.log2(L)))
    y = np.fft.irfft(np.fft.rfft(x, nfft) * np.fft.rfft(h, nfft), nfft)[: len(x)]
    return y

irL, irR = make_ir(101), make_ir(202)
wetL = fftconv(Lp, irL); wetR = fftconv(Rp, irR)
wetL /= (np.max(np.abs(wetL)) + 1e-9); wetR /= (np.max(np.abs(wetR)) + 1e-9)
pk = max(np.max(np.abs(Lp)), np.max(np.abs(Rp)), 1e-9)
Lp = Lp * 0.85 + wetL * pk * 0.25
Rp = Rp * 0.85 + wetR * pk * 0.25

# --- rain: dark, filtered, droplets, brought back UP in the mix ---
freqs = np.fft.rfftfreq(N, 1.0 / sr)
fc = 1500.0
shape = 1.0 / np.sqrt(np.maximum(freqs, 1.0))
shape *= 1.0 / (1.0 + (freqs / fc) ** 2.0)
shape *= freqs / np.sqrt(freqs ** 2 + 35.0 ** 2)

def rain_channel(seed):
    r = np.random.default_rng(seed)
    y = np.fft.irfft(np.fft.rfft(r.standard_normal(N)) * shape, n=N)
    y /= (np.max(np.abs(y)) + 1e-9)
    drops = np.zeros(N)
    for _ in range(620):
        i0 = r.integers(0, N - 1200)
        dl = int(r.uniform(0.006, 0.020) * sr)
        tt = np.arange(dl) / sr
        blip = np.sin(TWO * r.uniform(900, 2200) * tt) * np.exp(-tt / (dl / sr * 0.3))
        drops[i0:i0 + dl] += blip * r.uniform(0.06, 0.18)
    return 0.9 * y + 0.30 * drops

rainL = rain_channel(11); rainR = rain_channel(23)
swell = 0.82 + 0.18 * np.sin(TWO * 0.05 * t_all + 1.0)
rlvl = np.interp(t_all, [0, z1, (z1 + z2) / 2, z2, T], [0.45, 0.62, 0.92, 0.78, 0.40])
gain_rain = 0.60
L = Lp + rainL * rlvl * swell * gain_rain
R = Rp + rainR * rlvl * swell * gain_rain

mg = np.interp(t_all, [0, 30, z1, (z1 + z2) / 2, z2, 165, T],
               [0.58, 0.53, 0.48, 0.43, 0.49, 0.84, 0.94])
L *= mg; R *= mg

mix = np.vstack([L, R])
fi, fo = int(1.5 * sr), int(2.0 * sr)
mix[:, :fi] *= np.linspace(0, 1, fi)
mix[:, -fo:] *= np.linspace(1, 0, fo)
mix = mix / np.max(np.abs(mix)) * 0.92
mix = np.tanh(mix * 1.1) / np.tanh(1.1) * 0.92

ints = (mix.T * 32767).astype("<i2")
path = "/mnt/user-data/outputs/sleeparc_demo_v3.wav"
with wave.open(path, "wb") as wf:
    wf.setnchannels(2); wf.setsampwidth(2); wf.setframerate(sr)
    wf.writeframes(ints.tobytes())
print("wrote", path, round(os.path.getsize(path) / 1e6, 1), "MB")
