// Test av Worker-en uten nettverk: stubber fetch (Firebase + push-tjeneste) og
// dekrypterer det som sendes med http_ece (samme bibliotek som web-push bruker).
// Bruker et tilfeldig test-nøkkelpar – ingen ekte hemmeligheter her.
// Kjør: (cd ../push && npm ci) && node test.mjs
import { createRequire } from 'node:module';
import crypto from 'node:crypto';
const require = createRequire(new URL('../push/', import.meta.url));
const ece = require('http_ece');
import worker from './src/index.mjs';
import { b64u } from './src/webpush.mjs';

let pass = 0, fail = 0;
const ok = (n, c) => { (c ? pass++ : fail++); console.log(`${c ? 'PASS' : 'FAIL'}  ${n}`); };

// Tilfeldig VAPID-nøkkelpar kun for testen
const vk = crypto.createECDH('prime256v1'); vk.generateKeys();
const TEST_PRIV = b64u(vk.getPrivateKey()), TEST_PUB = b64u(vk.getPublicKey());

// "Telefonen": nøkkelpar + auth
const ua = crypto.createECDH('prime256v1'); ua.generateKeys();
const auth = crypto.randomBytes(16);
const sub = { endpoint: 'https://push.example/send/abc', keys: { p256dh: b64u(ua.getPublicKey()), auth: b64u(auth) } };
const decrypt = (buf) => JSON.parse(ece.decrypt(buf, { version: 'aes128gcm', privateKey: ua, authSecret: b64u(auth) }).toString('utf8'));

// due-tid = ett minutt siden (Oslo)
const hm = new Intl.DateTimeFormat('en-GB', { timeZone: 'Europe/Oslo', hour: '2-digit', minute: '2-digit', hour12: false }).format(new Date(Date.now() - 60000));
const DB = 'https://demo-default-rtdb.europe-west1.firebasedatabase.app';
const store = { hus: { meds: { m1: { id: 'm1', name: 'Escitalopram', dose: '15 mg', pills: 1, icon: '💊', times: [hm] } },
  pushSubs: { s1: sub, gone: { endpoint: 'https://push.example/send/gone', keys: sub.keys } } } };
const pushes = [];
globalThis.fetch = async (url, opts = {}) => {
  url = String(url); const method = opts.method || 'GET';
  if (url.startsWith('https://push.example/')) {
    if (url.endsWith('/gone')) return new Response('', { status: 410 });
    pushes.push({ headers: opts.headers, body: Buffer.from(opts.body) });
    return new Response('', { status: 201 });
  }
  const m = /\/households\/([^/]+?)(?:\/(.*))?\.json$/.exec(url);
  const path = (m[2] || '').split('/').filter(Boolean);
  let parent = store, key = m[1];
  for (const p of path) { if (parent[key] == null) parent[key] = {}; parent = parent[key]; key = p; }
  if (method === 'GET') return Response.json(parent[key] ?? null);
  if (method === 'PUT') { parent[key] = JSON.parse(opts.body); return Response.json(parent[key]); }
  if (method === 'DELETE') { delete parent[key]; return Response.json(null); }
};
const kv = new Map();
const env = { VAPID_PRIVATE_KEY: TEST_PRIV, VAPID_PUBLIC_KEY: TEST_PUB,
  CFG: { get: async (k, t) => (kv.has(k) ? (t === 'json' ? JSON.parse(kv.get(k)) : kv.get(k)) : null), put: async (k, v) => { kv.set(k, v); } } };
const call = (path, method = 'GET', body, key = TEST_PRIV) => worker.fetch(new Request('https://w.example' + path,
  { method, headers: { 'x-key': key, 'content-type': 'application/json' }, body: body ? JSON.stringify(body) : undefined }), env);

// --- tilgang ---
ok('uten riktig nøkkel -> 401', (await call('/status', 'GET', null, 'feil')).status === 401);
ok('register avviser ikke-Firebase-URL', (await call('/register', 'POST', { db: 'https://evil.example', households: 'hus' })).status === 400);
ok('ingen konfig -> ingen sending', (await (await call('/run', 'POST')).json()).log.join().includes('ingen konfig') && pushes.length === 0);
ok('register OK', (await call('/register', 'POST', { db: DB + '/', households: 'hus' })).status === 200);

// --- første varsel ---
await call('/run', 'POST');
ok('sender ett varsel', pushes.length === 1);
ok('markerer {c:1}', Object.values(store.hus.medNotif || {})[0]?.c === 1);
ok('fjerner utløpt abonnement, beholder friskt', !store.hus.pushSubs.gone && !!store.hus.pushSubs.s1);

// --- kryptering: telefonen kan dekryptere (RFC 8291) ---
const p = pushes[0];
const msg = decrypt(p.body);
ok('payload dekrypteres riktig', msg.title === '💊 Escitalopram' && msg.body === 'Ta 1 pille');
ok('riktige headere', p.headers['Content-Encoding'] === 'aes128gcm' && p.headers.Urgency === 'high');

// --- VAPID-signatur verifiseres med den offentlige nøkkelen ---
const [, t] = /t=([^,]+), k=/.exec(p.headers.Authorization);
const [h, b, s] = t.split('.');
const pubRaw = vk.getPublicKey();
const pubKey = crypto.createPublicKey({ format: 'jwk',
  key: { kty: 'EC', crv: 'P-256', x: b64u(pubRaw.subarray(1, 33)), y: b64u(pubRaw.subarray(33, 65)) } });
ok('VAPID-JWT er gyldig signert', crypto.verify('sha256', Buffer.from(h + '.' + b),
  { key: pubKey, dsaEncoding: 'ieee-p1363' }, Buffer.from(s, 'base64url')));
const claims = JSON.parse(Buffer.from(b, 'base64url').toString());
ok('VAPID aud = push-tjenestens origin', claims.aud === 'https://push.example' && claims.exp > Date.now() / 1000);

// --- purring ---
await call('/run', 'POST');
ok('ingen dobbel-sending rett etter', pushes.length === 1);
const k = Object.keys(store.hus.medNotif)[0];
store.hus.medNotif[k].t = Date.now() - 25 * 60000;
await call('/run', 'POST');
ok('purrer etter 20+ min (påminnelse 2)', pushes.length === 2 && store.hus.medNotif[k].c === 2);
ok('purre-tekst', decrypt(pushes[1].body).body === 'Ta 1 pille · påminnelse 2');
store.hus.medLog = { l1: { medId: 'm1', slot: `m1|${k.split('_')[1]}|${hm}` } };
store.hus.medNotif[k].t = Date.now() - 25 * 60000;
await call('/run', 'POST');
ok('tatt -> ingen flere varsler', pushes.length === 2);

// --- cron-inngangen ---
let waited; await worker.scheduled({}, env, { waitUntil: (pr) => { waited = pr; } }); await waited;
ok('scheduled() kjører uten feil', true);
ok('/status viser konfigurert', (await (await call('/status')).json()).configured === true);

console.log(`\n${pass}/${pass + fail} bestått`);
process.exit(fail ? 1 : 0);
