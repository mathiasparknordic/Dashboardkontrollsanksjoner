// Hjemmetavla – medisin-varsler på Cloudflare Workers.
// Cron hvert minutt: leser husholdningen(e) fra Firebase, finner doser som skal
// varsles (samme logikk som push/due.mjs) og sender web-push. Erstatter den
// upålitelige GitHub-cron-en (som i praksis bare kjørte hver 4.–8. time).
//
// Bindinger: KV-navnerom CFG, secret VAPID_PRIVATE_KEY.
// Konfig (Firebase-URL + husholdning) registreres av GitHub-jobben via POST /register.
import { osloParts, dueDoses, reminderBody } from '../../push/due.mjs';
import { sendPush } from './webpush.mjs';

const VAPID_PUBLIC = 'BDwqaA3cAWw6DwZ5LgGfszFvkZJR56Pmk8M9VEaF0EChrDrYcu73SeHMwBTZo15R6D1KgSdiNmfHybNz64mxGzM';
const VAPID_SUBJECT = 'mailto:hjemmetavla@example.com';
const FIREBASE_HOST = /^https:\/\/[a-z0-9-]+(\.[a-z0-9-]+)*\.(firebasedatabase\.app|firebaseio\.com)$/i;

const node = (db, code, path) => `${db}/households/${encodeURIComponent(code)}${path ? '/' + path : ''}.json`;

async function processHousehold(db, code, now, vapid, log) {
  const r = await fetch(node(db, code, ''));
  if (!r.ok) { log.push(`les-feil ${r.status}`); return; }
  const hh = await r.json();
  if (!hh) return;
  const due = dueDoses(hh, now);
  if (!due.length) return;
  const subs = Object.entries(hh.pushSubs || {}).map(([id, v]) => ({ id, ...(v || {}) }))
    .filter((s) => s.endpoint && s.keys && s.keys.p256dh && s.keys.auth);
  if (!subs.length) { log.push(`${due.length} due, ingen abonnement`); return; }

  for (const d of due) {
    const reminderNo = d.count + 1;
    const payload = JSON.stringify({
      title: `${d.med.icon || '💊'} ${d.med.name || 'Medisin'}`,
      body: reminderBody(d.med, reminderNo),
      tag: `med-${d.slotId}`, time: d.time, slot: d.slotId, url: './index.html',
    });
    let delivered = 0, gone = 0;
    for (const sub of subs) {
      let status = 0;
      try { status = await sendPush(sub, payload, vapid); } catch (e) { status = -1; }
      if (status >= 200 && status < 300) delivered++;
      else if (status === 404 || status === 410) {
        gone++; await fetch(node(db, code, `pushSubs/${sub.id}`), { method: 'DELETE' }).catch(() => {});
      } else log.push(`send-feil ${status}`);
    }
    if (delivered > 0 || (gone > 0 && gone === subs.length)) {
      await fetch(node(db, code, `medNotif/${d.key}`), {
        method: 'PUT', headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ c: reminderNo, t: now.ms }),
      });
      log.push(`varslet ${d.time} (#${reminderNo}) -> ${delivered}`);
    }
  }
}

async function run(env) {
  const cfg = await env.CFG.get('config', 'json');
  const now = osloParts();
  const log = [];
  if (!cfg || !cfg.db || !(cfg.households || []).length) log.push('ingen konfig registrert');
  else {
    const vapid = { subject: VAPID_SUBJECT, publicKey: env.VAPID_PUBLIC_KEY || VAPID_PUBLIC, privateKey: env.VAPID_PRIVATE_KEY };
    for (const code of cfg.households) {
      try { await processHousehold(cfg.db, code, now, vapid, log); } catch (e) { log.push('feil: ' + (e && e.message)); }
    }
  }
  // Skriv status kun når noe skjedde (sparer KV-skrivinger), pluss en gang i timen som hjerteslag.
  if (log.length || now.hhmm.endsWith(':00')) {
    await env.CFG.put('status', JSON.stringify({ at: new Date().toISOString(), oslo: now.hhmm, log }));
  }
  return log;
}

const authed = (req, env) => !!env.VAPID_PRIVATE_KEY && req.headers.get('x-key') === env.VAPID_PRIVATE_KEY;

export default {
  async scheduled(_event, env, ctx) { ctx.waitUntil(run(env)); },
  async fetch(req, env) {
    const url = new URL(req.url);
    if (!authed(req, env)) return new Response('Hjemmetavla push', { status: url.pathname === '/' ? 200 : 401 });
    if (req.method === 'POST' && url.pathname === '/register') {
      const b = await req.json().catch(() => null);
      const db = String((b && b.db) || '').trim().replace(/\/+$/, '');
      const households = String((b && b.households) || '').split(',').map((s) => s.trim()).filter(Boolean).slice(0, 5);
      if (!FIREBASE_HOST.test(db) || !households.length) return new Response('ugyldig konfig', { status: 400 });
      await env.CFG.put('config', JSON.stringify({ db, households, at: new Date().toISOString() }));
      return Response.json({ ok: true, households: households.length });
    }
    if (url.pathname === '/status') {
      const cfg = await env.CFG.get('config', 'json');
      return Response.json({ configured: !!cfg, registeredAt: cfg && cfg.at, last: await env.CFG.get('status', 'json') });
    }
    if (req.method === 'POST' && url.pathname === '/run') return Response.json({ log: await run(env) });
    return new Response('not found', { status: 404 });
  },
};
