import math, numpy as np, re

ROOM = '''<rect x="0" y="0" width="680" height="372" fill="url(#wall)"/>
<rect x="0" y="300" width="680" height="72" fill="#0b0f1a"/>
<ellipse cx="210" cy="348" rx="205" ry="24" fill="#141a2c"/>
<rect x="58" y="66" width="92" height="76" rx="4" fill="#3a2c1c"/>
<rect x="65" y="73" width="78" height="62" rx="2" fill="#22304e"/>
<path d="M65 120 L92 100 L112 118 L128 106 L143 120 L143 135 L65 135 Z" fill="#16223c"/>
<g><circle cx="104" cy="184" r="48" fill="#ffc24a" opacity="0.05"/><circle cx="104" cy="184" r="32" fill="#ffc24a" opacity="0.07"/><circle cx="104" cy="184" r="18" fill="#ffc24a" opacity="0.10"/></g>
<path d="M92 168 L116 168 L122 186 L86 186 Z" fill="#ffce86"/>
<g clip-path="url(#win)">
<rect x="404" y="40" width="244" height="196" fill="url(#sky)"/>
<g id="stars" fill="#eef2ff">
<circle class="tw" cx="420" cy="62" r="1.3"/><circle cx="438" cy="86" r="1"/><circle class="tw" cx="456" cy="56" r="1.4"/>
<circle cx="474" cy="78" r="1"/><circle class="tw" cx="492" cy="60" r="1.1"/><circle cx="510" cy="92" r="1"/>
<circle class="tw" cx="528" cy="66" r="1.3"/><circle cx="546" cy="54" r="1"/><circle cx="564" cy="84" r="1.1"/>
<circle class="tw" cx="582" cy="62" r="1"/><circle cx="600" cy="92" r="1.2"/><circle cx="618" cy="70" r="1"/>
<circle cx="430" cy="118" r="1"/><circle class="tw" cx="470" cy="128" r="1.1"/><circle cx="512" cy="120" r="1"/>
<circle cx="556" cy="128" r="1.1"/><circle cx="598" cy="120" r="1"/><circle cx="540" cy="104" r="1"/>
</g>
<circle id="moon" cx="470" cy="120" r="20" fill="#eef0e2"/>
<circle id="moonShade" cx="478" cy="114" r="20" fill="#0d1730"/>
<circle cx="462" cy="112" r="3.5" fill="#d6d8ca"/><circle cx="476" cy="126" r="2.5" fill="#d6d8ca"/>
<circle id="sun" cx="558" cy="234" r="22" fill="#ffd27a" opacity="0"/>
<path d="M404 196 Q470 168 540 192 Q600 210 648 188 L648 236 L404 236 Z" fill="#0c1426"/>
<path d="M404 210 Q500 186 560 206 Q610 220 648 206 L648 236 L404 236 Z" fill="#0a1120"/>
<rect id="warmSky" x="404" y="40" width="244" height="196" fill="#f0a35a" opacity="0"/>
</g>
<rect x="394" y="30" width="264" height="216" rx="7" fill="none" stroke="#3c2c1c" stroke-width="13"/>
<line x1="526" y1="34" x2="526" y2="242" stroke="#3c2c1c" stroke-width="8"/>
<line x1="398" y1="138" x2="654" y2="138" stroke="#3c2c1c" stroke-width="8"/>
<rect x="382" y="244" width="288" height="14" rx="4" fill="#4a3522"/>
<path d="M360 28 L398 28 L398 250 L372 250 Z" fill="#1e2840"/>
<path d="M654 28 L692 28 L680 250 L654 250 Z" fill="#1e2840"/>
<rect id="warmRoom" x="0" y="0" width="394" height="372" fill="#ff9a42" opacity="0"/>
<rect x="26" y="150" width="30" height="150" rx="6" fill="#4a3320"/>
<rect x="30" y="156" width="22" height="34" rx="4" fill="#5c4226"/>
<rect x="20" y="292" width="356" height="74" rx="16" fill="#2a3350"/>
<rect x="26" y="282" width="346" height="62" rx="14" fill="#e8e0ce"/>
<rect x="26" y="282" width="346" height="22" rx="12" fill="#d6cdb8"/>
<path d="M150 312 L138 346 M210 312 L198 346 M270 312 L258 346 M320 312 L308 346" stroke="#c9bfa6" stroke-width="3" fill="none" opacity="0.7"/>
<rect x="36" y="276" width="116" height="40" rx="14" fill="#f1eada"/>'''

POST = '''<g><rect x="598" y="318" width="34" height="40" rx="4" fill="#7a4a2c"/>
<path d="M615 318 Q598 296 606 280 Q616 300 615 318 Z" fill="#2f5e3a"/>
<path d="M615 318 Q632 298 626 280 Q616 302 615 318 Z" fill="#37704a"/>
<path d="M615 318 Q615 292 615 276 Q622 296 615 318 Z" fill="#274f33"/></g>'''

def fur(cx, cy, rx, ry, n, dirx, diry, lmin, lmax, wmin, wmax, colors, curl, seed, op=(0.45, 0.9)):
    r = np.random.default_rng(seed)
    dl = math.hypot(dirx, diry); dx, dy = dirx / dl, diry / dl; px, py = -dy, dx
    out = []
    for _ in range(n):
        a = r.uniform(0, 2 * math.pi); rr = math.sqrt(r.random())
        sx = cx + math.cos(a) * rx * rr; sy = cy + math.sin(a) * ry * rr
        L = r.uniform(lmin, lmax)
        cu = r.uniform(-curl, curl)
        mx = sx + dx * L * 0.5 + px * cu; my = sy + dy * L * 0.5 + py * cu
        ex = sx + dx * L + px * r.uniform(-curl * 0.5, curl * 0.5)
        ey = sy + dy * L + py * r.uniform(-curl * 0.5, curl * 0.5)
        c = colors[r.integers(len(colors))]
        w = r.uniform(wmin, wmax)
        out.append('<path d="M%.1f %.1f Q%.1f %.1f %.1f %.1f" stroke="%s" stroke-width="%.1f" fill="none" stroke-linecap="round" opacity="%.2f"/>' % (sx, sy, mx, my, ex, ey, c, w, r.uniform(*op)))
    return "\n".join(out)

DARK = ['#14171f', '#1c2029', '#262b36', '#313747']
SILVER = ['#7f8696', '#99a0af', '#b4bbc8', '#d2d7df']
GREY = ['#888b95', '#a6a9b3', '#c3c6ce']

# fur layers
body_fur = "\n".join([
    fur(290, 300, 80, 56, 120, 0.30, 1.0, 9, 22, 1.2, 2.6, DARK, 7, 1),
    fur(322, 312, 46, 34, 70, 0.45, 1.0, 8, 18, 1.0, 2.4, SILVER, 6, 2, op=(0.5, 0.95)),
    fur(232, 268, 70, 20, 60, 0.0, -1.0, 6, 13, 1.0, 2.2, DARK, 4, 3),
    fur(238, 332, 92, 18, 70, 0.08, 1.0, 7, 15, 1.0, 2.2, DARK, 4, 4),
])
chest_fur = fur(176, 320, 38, 26, 80, 0.10, 1.0, 12, 28, 1.2, 2.6, DARK, 8, 5)
nearear_fur = "\n".join([
    fur(150, 304, 24, 56, 110, 0.05, 1.0, 16, 36, 1.3, 2.8, DARK, 9, 6),
    fur(150, 344, 22, 18, 30, 0.05, 1.0, 12, 24, 1.0, 2.2, SILVER, 7, 7, op=(0.4, 0.8)),
])
farear_fur = fur(110, 300, 16, 52, 70, 0.02, 1.0, 14, 30, 1.2, 2.4, DARK, 8, 8)
leg_fur = "\n".join([
    fur(150, 348, 64, 14, 80, 0.05, 1.0, 8, 18, 1.1, 2.3, DARK, 5, 9),
    fur(108, 352, 28, 10, 36, 0.05, 1.0, 7, 15, 1.0, 2.0, DARK, 4, 10),
])
muzzle_fur = fur(94, 304, 27, 19, 70, -0.55, 0.7, 5, 11, 0.8, 1.7, GREY, 4, 11, op=(0.45, 0.85))

dog = '''
<ellipse cx="222" cy="348" rx="150" ry="13" fill="#000000" opacity="0.30" filter="url(#soft)"/>
<!-- far ear solid + fur -->
<path d="M116 252 C98 276 96 306 100 330 C102 344 108 352 114 350 C118 346 120 334 120 320 C120 298 122 274 126 256 C124 250 118 250 116 252 Z" fill="url(#earGrad)"/>
<g>%FAREAR%</g>
<g id="breath">
  <ellipse cx="290" cy="300" rx="84" ry="60" fill="url(#bodyGrad)"/>
  <ellipse cx="212" cy="292" rx="74" ry="52" fill="url(#bodyGrad)"/>
  <ellipse cx="320" cy="306" rx="46" ry="36" fill="url(#roanGrad)" opacity="0.85"/>
  <g>%BODYFUR%</g>
</g>
<g>%CHEST%</g>
<!-- head -->
<ellipse cx="128" cy="268" rx="47" ry="45" fill="url(#headGrad)"/>
<g>%MUZFUR%</g>
<ellipse cx="95" cy="301" rx="29" ry="21" fill="url(#muzGrad)"/>
<ellipse cx="99" cy="296" rx="17" ry="10" fill="#c8cbd3" opacity="0.7"/>
<!-- nose -->
<ellipse cx="70" cy="303" rx="13.5" ry="11.5" fill="url(#noseGrad)"/>
<path d="M64 300 Q67 305 64 308 M76 300 Q73 305 76 308" stroke="#000" stroke-width="1.6" fill="none" opacity="0.6"/>
<ellipse cx="65" cy="299" rx="3.5" ry="2.4" fill="#9aa0ad" opacity="0.8"/>
<path d="M78 314 Q92 322 106 315" stroke="#15171d" stroke-width="2.2" fill="none" stroke-linecap="round"/>
<!-- drowsy eye -->
<ellipse cx="120" cy="266" rx="12" ry="8.5" fill="#0e1015"/>
<ellipse cx="120" cy="269" rx="8.5" ry="5" fill="#5a3a22"/>
<circle cx="120" cy="269" r="3.2" fill="#150d07"/>
<circle cx="122.6" cy="266.8" r="1.5" fill="#eef1f6"/>
<path d="M108 263 Q120 254 132 263 L132 266 Q120 259 108 266 Z" fill="url(#headGrad)"/>
<path d="M108 263 Q120 256 132 263" stroke="#0c0d12" stroke-width="1.6" fill="none" opacity="0.8"/>
<path d="M109 273 Q120 278 131 273" stroke="#0c0d12" stroke-width="1.4" fill="none" opacity="0.5"/>
<path d="M104 258 Q116 250 130 256" stroke="#6b5a3c" stroke-width="2" fill="none" opacity="0.5"/>
<!-- near ear solid + fur (slight sway) -->
<g id="ear" style="transform-box:fill-box;transform-origin:150px 250px">
  <path d="M156 250 C180 276 178 308 172 332 C168 348 161 358 150 358 C139 358 133 348 129 332 C127 308 130 276 138 252 C144 248 151 246 156 250 Z" fill="url(#earGrad)"/>
  <g>%NEAREAR%</g>
</g>
<!-- legs / paws -->
<ellipse cx="160" cy="340" rx="58" ry="16" fill="url(#bodyGrad)"/>
<ellipse cx="108" cy="348" rx="26" ry="12" fill="url(#bodyGrad)"/>
<g>%LEGFUR%</g>
<path d="M120 334 L120 350 M150 334 L150 350" stroke="#0e1016" stroke-width="2.2" fill="none" opacity="0.6"/>
<!-- moonlight rim -->
<path d="M210 248 Q280 234 346 250" stroke="#6b7d9c" stroke-width="2.2" fill="none" opacity="0.4"/>
<path d="M100 236 Q116 226 138 232" stroke="#6b7d9c" stroke-width="2" fill="none" opacity="0.35"/>
<g id="zzz" fill="#c7d2ee" font-family="sans-serif" font-style="italic" font-weight="700">
<text x="178" y="240" font-size="12">z</text><text x="196" y="224" font-size="15">z</text><text x="216" y="204" font-size="19">z</text>
</g>
'''
dog = (dog.replace('%FAREAR%', farear_fur).replace('%BODYFUR%', body_fur)
          .replace('%CHEST%', chest_fur).replace('%MUZFUR%', muzzle_fur)
          .replace('%NEAREAR%', nearear_fur).replace('%LEGFUR%', leg_fur))

DEFS = '''
<linearGradient id="wall" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#1c2644"/><stop offset="100%" stop-color="#0e1426"/></linearGradient>
<linearGradient id="sky" x1="0" y1="0" x2="0" y2="1"><stop id="skyTop" offset="0%" stop-color="#3a2f5e"/><stop id="skyBot" offset="100%" stop-color="#7a4a5e"/></linearGradient>
<radialGradient id="bodyGrad" cx="38%" cy="32%" r="75%"><stop offset="0%" stop-color="#3a4252"/><stop offset="55%" stop-color="#262c38"/><stop offset="100%" stop-color="#171b24"/></radialGradient>
<radialGradient id="headGrad" cx="40%" cy="34%" r="78%"><stop offset="0%" stop-color="#3c4454"/><stop offset="60%" stop-color="#262c38"/><stop offset="100%" stop-color="#161922"/></radialGradient>
<radialGradient id="earGrad" cx="45%" cy="20%" r="90%"><stop offset="0%" stop-color="#262b36"/><stop offset="100%" stop-color="#0c0d12"/></radialGradient>
<linearGradient id="muzGrad" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stop-color="#bcbfc7"/><stop offset="100%" stop-color="#6b6e78"/></linearGradient>
<radialGradient id="noseGrad" cx="42%" cy="28%" r="80%"><stop offset="0%" stop-color="#43454d"/><stop offset="55%" stop-color="#1b1c22"/><stop offset="100%" stop-color="#090a0d"/></radialGradient>
<radialGradient id="roanGrad" cx="55%" cy="45%" r="70%"><stop offset="0%" stop-color="#aab1bf"/><stop offset="60%" stop-color="#7a8290"/><stop offset="100%" stop-color="#4a525f"/></radialGradient>
<clipPath id="scene"><rect x="0" y="0" width="680" height="372" rx="14"/></clipPath>
<clipPath id="win"><rect x="404" y="40" width="244" height="196" rx="5"/></clipPath>
<filter id="soft" x="-20%" y="-20%" width="140%" height="140%"><feGaussianBlur stdDeviation="4"/></filter>
'''

SVG = '<svg viewBox="0 0 680 372" role="img" xmlns="http://www.w3.org/2000/svg"><defs>%DEFS%</defs><g clip-path="url(#scene)">%ROOM%%DOG%%POST%</g></svg>'
SVG = SVG.replace('%DEFS%', DEFS).replace('%ROOM%', ROOM).replace('%DOG%', dog).replace('%POST%', POST)

CSS = '''
:root{--bg:#0c1018;--panel:#161c2b;--panel2:#1d2536;--bd:#2a3346;--tx:#e7ecf6;--tx3:#7e889c}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--tx);font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;display:flex;justify-content:center;padding:24px}
.card{width:100%;max-width:720px}.svgwrap{border-radius:14px;overflow:hidden}svg{display:block;width:100%}
.row{display:flex;align-items:center;gap:12px;margin-top:14px;flex-wrap:wrap}
.btn{font-size:14px;padding:9px 16px;border-radius:10px;border:1px solid var(--bd);background:var(--panel2);color:var(--tx);cursor:pointer}
input[type=range]{flex:1;min-width:160px;accent-color:#ffcc00}
.read{display:flex;gap:10px;margin-top:14px;flex-wrap:wrap}
.rc{flex:1;min-width:120px;background:var(--panel);border:1px solid var(--bd);border-radius:10px;padding:10px 12px}
.lab{font-size:12px;color:var(--tx3);margin:0 0 2px}.val{font-size:15px;font-weight:600;margin:0}
@media (prefers-reduced-motion: no-preference){
 #breath{transform-box:fill-box;transform-origin:center;animation:br 4.8s ease-in-out infinite}
 @keyframes br{0%,100%{transform:scale(1,1)}50%{transform:scale(1.01,1.03)}}
 #ear{animation:sw 6s ease-in-out infinite}@keyframes sw{0%,100%{transform:rotate(0deg)}50%{transform:rotate(1.6deg)}}
 #zzz text{animation:zz 4s ease-in-out infinite}#zzz text:nth-child(2){animation-delay:.5s}#zzz text:nth-child(3){animation-delay:1s}
 @keyframes zz{0%,100%{opacity:.2}50%{opacity:.9}}
 .tw{animation:tw 4s ease-in-out infinite}@keyframes tw{0%,100%{opacity:.5}50%{opacity:1}}
}
'''

JS = '''
var kf=[{t:0,top:'#3a2f5e',bot:'#7a4a5e'},{t:0.12,top:'#1a2542',bot:'#243353'},{t:0.45,top:'#0d1730',bot:'#13223e'},{t:0.68,top:'#15233f',bot:'#2c3d5e'},{t:0.86,top:'#2f3f6e',bot:'#9c6a50'},{t:1,top:'#5e7ab4',bot:'#f2a657'}];
function hx(c){return [parseInt(c.slice(1,3),16),parseInt(c.slice(3,5),16),parseInt(c.slice(5,7),16)];}
function th(a){return '#'+a.map(function(v){var s=Math.round(v).toString(16);return s.length<2?'0'+s:s;}).join('');}
function mix(a,b,f){var x=hx(a),y=hx(b);return th([0,1,2].map(function(i){return x[i]+(y[i]-x[i])*f;}));}
function clamp(v){return v<0?0:v>1?1:v;}
function interp(p,t){for(var i=0;i<p.length-1;i++){if(t<=p[i+1][0]){var f=(t-p[i][0])/(p[i+1][0]-p[i][0]);return p[i][1]+(p[i+1][1]-p[i][1])*f;}}return p[p.length-1][1];}
var topS=document.getElementById('skyTop'),botS=document.getElementById('skyBot'),moon=document.getElementById('moon'),moonSh=document.getElementById('moonShade'),sun=document.getElementById('sun'),stars=document.getElementById('stars'),warmSky=document.getElementById('warmSky'),warmRoom=document.getElementById('warmRoom'),clock=document.getElementById('clock'),phase=document.getElementById('phase'),audio=document.getElementById('audio'),slider=document.getElementById('slider');
var starOp=[[0,0],[0.05,0],[0.2,0.95],[0.5,0.95],[0.62,0.6],[0.74,0],[1,0]];
function update(t){var i=0;for(;i<kf.length-1;i++){if(t<=kf[i+1].t)break;}var f=(t-kf[i].t)/(kf[i+1].t-kf[i].t);
 topS.setAttribute('stop-color',mix(kf[i].top,kf[i+1].top,f));botS.setAttribute('stop-color',mix(kf[i].bot,kf[i+1].bot,f));
 var mp=clamp(t/0.82),mx=422+mp*208,my=220-Math.sin(Math.PI*mp)*121;moon.setAttribute('cx',mx);moon.setAttribute('cy',my);moonSh.setAttribute('cx',mx+8);moonSh.setAttribute('cy',my-6);
 var mo=t<0.05?t/0.05:(t>0.72?clamp((0.82-t)/0.1):1);moon.setAttribute('opacity',mo);moonSh.setAttribute('opacity',mo);
 var sp=clamp((t-0.8)/0.2);sun.setAttribute('cy',234-sp*120);sun.setAttribute('opacity',sp);
 stars.setAttribute('opacity',interp(starOp,t).toFixed(2));
 warmSky.setAttribute('opacity',(clamp((t-0.8)/0.2)*0.30).toFixed(2));warmRoom.setAttribute('opacity',(clamp((t-0.82)/0.18)*0.13).toFixed(2));
 var mins=23*60+t*480,hh=Math.floor(mins/60)%24,mm=Math.floor(mins%60);clock.textContent=(hh<10?'0':'')+hh+':'+(mm<10?'0':'')+mm;
 phase.textContent=t<0.30?'Dyp søvn':t<0.62?'Lett søvn / REM':t<0.82?'Mer REM, lettere':'Oppvåkning';
 audio.textContent=t<0.12?'Piano leder deg ned':t<0.80?'Regn-teppe bærer':'Volum stiger – soloppgang';}
slider.addEventListener('input',function(){stopit();update(this.value/1000);});
var playing=false,raf=null,last=null,period=34000,pbtn=document.getElementById('play'),picon=document.getElementById('picon'),ptext=document.getElementById('ptext');
function frame(ts){if(last==null)last=ts;var dt=ts-last;last=ts;var t=(+slider.value)/1000;t+=dt/period;if(t>1)t=0;slider.value=Math.round(t*1000);update(t);raf=requestAnimationFrame(frame);}
function playit(){playing=true;last=null;picon.textContent='⏸';ptext.textContent='Pause';raf=requestAnimationFrame(frame);}
function stopit(){playing=false;if(raf)cancelAnimationFrame(raf);raf=null;picon.textContent='▶';ptext.textContent='Spill av natta';}
pbtn.addEventListener('click',function(){playing?stopit():playit();});update(0);
'''

HTML = ('<!DOCTYPE html><html lang="no"><head><meta charset="utf-8"/>'
 '<meta name="viewport" content="width=device-width, initial-scale=1"/>'
 '<title>Lull &amp; Lift — Charlie</title><style>' + CSS + '</style></head><body><div class="card">'
 '<div class="svgwrap">' + SVG + '</div>'
 '<div class="row"><button id="play" class="btn"><span id="picon">▶</span> <span id="ptext">Spill av natta</span></button>'
 '<input id="slider" type="range" min="0" max="1000" step="1" value="0" aria-label="Tid gjennom natta"/></div>'
 '<div class="read"><div class="rc"><p class="lab">Tid på natten</p><p class="val" id="clock">23:00</p></div>'
 '<div class="rc"><p class="lab">Søvnfase</p><p class="val" id="phase">Innsovning</p></div>'
 '<div class="rc"><p class="lab">Lyden gjør</p><p class="val" id="audio">Piano leder deg ned</p></div></div>'
 '</div><script>' + JS + '</script></body></html>')

open('/mnt/user-data/outputs/lull_and_lift_charlie_v2.html', 'w').write(HTML)
import cairosvg
cairosvg.svg2png(bytestring=('<?xml version="1.0"?>' + SVG).encode(), write_to='charlie_v2.png',
                 output_width=680, output_height=372, background_color='#0c1018')
print('ok')
