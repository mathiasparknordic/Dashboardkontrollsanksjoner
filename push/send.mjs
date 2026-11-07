// Sender web-push-varsler for forfalte medisin-doser.
// Kjøres av GitHub Actions (cron). Leser husholdning(er) fra Firebase REST,
// finner due-doser, sender varsel til lagrede push-abonnement, og markerer
// slot som varslet så det ikke sendes på nytt.
//
// Miljøvariabler (GitHub Actions secrets):
//   FIREBASE_DB_URL     f.eks. https://xxx.europe-west1.firebasedatabase.app
//   FIREBASE_HOUSEHOLD  husholdnings-kode(r), komma-separert for flere
//   VAPID_PRIVATE_KEY   privat VAPID-nøkkel (hemmelig)
// Valgfritt:
//   VAPID_PUBLIC_KEY    (ellers brukes innebygd offentlig nøkkel)
//   VAPID_SUBJECT       mailto:... (default mailto:hjemmetavla@example.com)

import webpush from 'web-push';
import { osloParts, dueDoses } from './due.mjs';

const DB = (process.env.FIREBASE_DB_URL || '').trim().replace(/\/+$/, '');
const HOUSEHOLDS = (process.env.FIREBASE_HOUSEHOLD || '')
  .split(',').map((s) => s.trim()).filter(Boolean);
const VAPID_PUBLIC = (process.env.VAPID_PUBLIC_KEY || '').trim()
  || 'BDwqaA3cAWw6DwZ5LgGfszFvkZJR56Pmk8M9VEaF0EChrDrYcu73SeHMwBTZo15R6D1KgSdiNmfHybNz64mxGzM';
const VAPID_PRIVATE = (process.env.VAPID_PRIVATE_KEY || '').trim();
const VAPID_SUBJECT = (process.env.VAPID_SUBJECT || '').trim() || 'mailto:hjemmetavla@example.com';

function fail(msg) { console.error('FEIL:', msg); process.exit(1); }
// Hvis oppsettet ikke er lagt inn enda: hopp over stille (grønn kjøring),
// slik at jobben ikke spammer med feil før varsler er satt opp.
const missing = [];
if (!DB) missing.push('FIREBASE_DB_URL');
if (!HOUSEHOLDS.length) missing.push('FIREBASE_HOUSEHOLD');
if (!VAPID_PRIVATE) missing.push('VAPID_PRIVATE_KEY');
if (missing.length) {
  console.log('Hopper over – varsler ikke satt opp enda. Mangler secret(s): ' + missing.join(', '));
  process.exit(0);
}

webpush.setVapidDetails(VAPID_SUBJECT, VAPID_PUBLIC, VAPID_PRIVATE);

const node = (code, path) =>
  `${DB}/households/${encodeURIComponent(code)}${path ? '/' + path : ''}.json`;

async function getJson(url) {
  const r = await fetch(url);
  if (!r.ok) throw new Error(`GET ${url} -> ${r.status}`);
  return r.json();
}
async function putJson(url, body) {
  const r = await fetch(url, {
    method: 'PUT', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body),
  });
  if (!r.ok) throw new Error(`PUT ${url} -> ${r.status}`);
  return r.json().catch(() => null);
}
async function del(url) {
  const r = await fetch(url, { method: 'DELETE' });
  return r.ok;
}

const subsFrom = (map) =>
  map && typeof map === 'object'
    ? Object.entries(map).map(([id, v]) => ({ id, ...(v || {}) }))
    : [];

async function processHousehold(code, now) {
  let hh;
  try { hh = await getJson(node(code, '')); }
  catch (e) { console.error(`[${code}] kunne ikke lese:`, e.message); return; }
  if (!hh) { console.log(`[${code}] tom husholdning`); return; }

  const due = dueDoses(hh, now);
  if (!due.length) { console.log(`[${code}] ingen due-doser (${now.hhmm})`); return; }

  const subs = subsFrom(hh.pushSubs).filter((s) => s && s.endpoint && s.keys);
  if (!subs.length) { console.log(`[${code}] ${due.length} due, men ingen abonnement`); return; }

  for (const d of due) {
    const payload = JSON.stringify({
      title: `${d.med.icon || '💊'} ${d.med.name || 'Medisin'}`,
      body: [d.med.dose, d.med.pills ? `ta ${d.med.pills} pille(r)` : '']
        .filter(Boolean).join(', ') || 'Tid for medisinen',
      tag: `med-${d.slotId}`,
      time: d.time,
      slot: d.slotId,
      url: './index.html',
    });

    let delivered = 0, gone = 0;
    for (const sub of subs) {
      try {
        await webpush.sendNotification(
          { endpoint: sub.endpoint, keys: sub.keys }, payload, { TTL: 3600, urgency: 'high' }
        );
        delivered++;
      } catch (err) {
        const sc = err && err.statusCode;
        if (sc === 404 || sc === 410) {
          gone++;
          await del(node(code, `pushSubs/${sub.id}`)).catch(() => {});
          console.log(`[${code}] fjernet utløpt abonnement ${sub.id}`);
        } else {
          console.error(`[${code}] send-feil (${sc || '?'}) til ${sub.id}:`, err && err.body ? String(err.body).slice(0, 120) : err && err.message);
        }
      }
    }

    // Marker som varslet hvis minst én mottok, eller alle som feilet var "borte".
    if (delivered > 0 || (gone > 0 && gone === subs.length)) {
      try { await putJson(node(code, `medNotif/${d.key}`), new Date().toISOString()); }
      catch (e) { console.error(`[${code}] kunne ikke merke ${d.key}:`, e.message); }
      console.log(`[${code}] varslet «${d.med.name}» ${d.time} -> ${delivered} enhet(er)`);
    } else {
      console.log(`[${code}] «${d.med.name}» ${d.time}: ingen levert, prøver igjen neste runde`);
    }
  }
}

(async () => {
  const now = osloParts();
  console.log(`Kjører medisin-varsler ${now.dateISO} ${now.hhmm} (Oslo), husholdninger: ${HOUSEHOLDS.length}`);
  for (const code of HOUSEHOLDS) await processHousehold(code, now);
  console.log('Ferdig.');
})().catch((e) => fail(e && e.stack || e));
