import numpy as np, wave, os
sr=22050; T=180.0; N=int(sr*T); t=np.arange(N)/sr; z1,z2=55.0,130.0; TWO=2*np.pi
Lp=np.zeros(N); Rp=np.zeros(N)

# lower, warmer register; cap brightness (no shrill high notes)
low=np.array([110.00,130.81,146.83,164.81,196.00,220.00])
mid=np.array([261.63,293.66,329.63,392.00,440.00])

def sched(x,a,b): return float(np.interp(x,a,b))
dens_t=[0,z1,(z1+z2)/2,z2,T]; dens_v=[2.6,2.8,6.8,5.2,2.1]

def note(freq,dur,vel,seed):
    n=int(dur*sr)
    if n<=0: return np.zeros(0)
    tt=np.arange(n)/sr; B=0.00035; out=np.zeros(n)
    for k in range(1,9):                    # fewer partials -> darker
        fk=freq*k*np.sqrt(1+B*k*k)
        if fk>4200: break
        amp=1.0/(k**1.6)                    # steep rolloff = quiet highs
        tau=dur*0.55/(1+1.0*(k-1))          # highs fade fast
        det=freq*0.0004*k                   # gentle detune (less shimmer)
        out+=amp*np.exp(-tt/max(tau,0.04))*0.5*(np.sin(TWO*fk*tt)+np.sin(TWO*(fk+det)*tt))
    na=int(0.010*sr)                        # soft hammer
    if na>0:
        r=np.random.default_rng(seed); nz=np.convolve(r.standard_normal(na),np.ones(7)/7,'same')
        out[:na]+=nz*np.exp(-np.arange(na)/(na*0.4))*0.32
    atk=int(0.009*sr); out[:atk]*=np.linspace(0,1,atk)
    out/=(np.max(np.abs(out))+1e-9); return out*vel

def add(start,freq,dur,vel,pan,seed):
    w=note(freq,dur,vel,seed); i0=int(start*sr); i1=min(i0+len(w),N); seg=w[:i1-i0]*0.16
    Lp[i0:i1]+=seg*np.sqrt(1-pan); Rp[i0:i1]+=seg*np.sqrt(pan)

rng=np.random.default_rng(7); tt=1.0; sd=1
while tt<T-2:
    d=sched(tt,dens_t,dens_v)
    pmid=0.04 if tt<=z2 else 0.10+0.30*(tt-z2)/(T-z2)
    scale=mid if rng.random()<pmid else low
    add(tt,float(scale[rng.integers(len(scale))]),rng.uniform(3.4,6.8),rng.uniform(0.34,0.66),rng.uniform(0.34,0.66),sd)
    sd+=1; tt+=d*rng.uniform(0.7,1.3)

pad=np.zeros(N)
for f in [82.41,110.0,164.81]: pad+=np.sin(TWO*f*t)   # lower, warmer drone
lfo=0.6+0.4*np.sin(TWO*0.03*t)
padlvl=np.interp(t,[0,z1,(z1+z2)/2,z2,T],[0.04,0.05,0.07,0.05,0.035])
pad*=lfo*padlvl; Lp+=pad; Rp+=pad*0.98

# light reverb (short, low wet)
def ir(seed,L=0.9):
    m=int(L*sr); r=np.random.default_rng(seed); tt2=np.arange(m)/sr
    h=r.standard_normal(m)*np.exp(-tt2/0.32); h=np.convolve(h,np.ones(14)/14,'same'); return h/(np.max(np.abs(h))+1e-9)
def fc(x,h):
    Ln=len(x)+len(h)-1; nf=1<<int(np.ceil(np.log2(Ln)))
    return np.fft.irfft(np.fft.rfft(x,nf)*np.fft.rfft(h,nf),nf)[:len(x)]
wl,wr=fc(Lp,ir(101)),fc(Rp,ir(202)); wl/=np.max(np.abs(wl))+1e-9; wr/=np.max(np.abs(wr))+1e-9
pk=max(np.max(np.abs(Lp)),np.max(np.abs(Rp)),1e-9)
Lp=Lp*0.9+wl*pk*0.15; Rp=Rp*0.9+wr*pk*0.15

# --- RAIN v4: natural broadband noise, organic patter, NO tonal droplets ---
freqs=np.fft.rfftfreq(N,1/sr)
shape=1.0/np.sqrt(np.maximum(freqs,1.0))            # pink tilt
shape*=1.0/(1.0+(freqs/3600.0)**1.6)                # soft low-pass ~3.6k (rain, not harsh white)
shape*=freqs/np.sqrt(freqs**2+45.0**2)              # remove sub rumble
def rain(seed):
    r=np.random.default_rng(seed)
    base=np.fft.irfft(np.fft.rfft(r.standard_normal(N))*shape,n=N)
    base/=(np.max(np.abs(base))+1e-9)
    # organic amplitude texture: slow swell * fast smoothed jitter (gives 'patter' without tones)
    jit=r.standard_normal(N); jit=np.convolve(jit,np.ones(220)/220,'same')   # ~10ms smoothing
    jit=(jit-jit.min())/(jit.max()-jit.min()+1e-9)
    swell=0.85+0.15*np.sin(TWO*0.05*t+r.uniform(0,6))
    return base*(0.55+0.45*jit)*swell
rainL,rainR=rain(11),rain(23)
rlvl=np.interp(t,[0,z1,(z1+z2)/2,z2,T],[0.40,0.55,0.82,0.70,0.34])
gain=0.5
L=Lp+rainL*rlvl*gain; R=Rp+rainR*rlvl*gain

mg=np.interp(t,[0,30,z1,(z1+z2)/2,z2,165,T],[0.58,0.53,0.48,0.43,0.49,0.84,0.94])
L*=mg; R*=mg
mix=np.vstack([L,R]); fi,fo=int(1.5*sr),int(2*sr)
mix[:, :fi]*=np.linspace(0,1,fi); mix[:, -fo:]*=np.linspace(1,0,fo)
mix=mix/np.max(np.abs(mix))*0.92; mix=np.tanh(mix*1.1)/np.tanh(1.1)*0.92
ints=(mix.T*32767).astype('<i2')
p='/mnt/user-data/outputs/sleeparc_demo_v4.wav'
with wave.open(p,'wb') as wf: wf.setnchannels(2); wf.setsampwidth(2); wf.setframerate(sr); wf.writeframes(ints.tobytes())
print('wrote',p,round(os.path.getsize(p)/1e6,1),'MB')
