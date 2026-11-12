// Ren logikk for å regne ut hvilke medisin-doser som skal varsles akkurat nå.
// Ingen nettverk/IO her – gjør den enkel å teste.
//
// Medisafe-stil: purrer flere ganger til dosen er registrert som tatt.
//   - Første varsel ved planlagt tid (ev. litt etter – cron kjører hvert 5. min)
//   - Nytt varsel hvert REPEAT_EVERY_MIN til den er tatt, opptil MAX_REMINDERS
//   - Gir opp etter GIVE_UP_MIN (slutter å mase for gamle doser)

export const REPEAT_EVERY_MIN = 20;  // minutter mellom hver purring
export const MAX_REMINDERS = 3;      // totalt antall varsler per dose (1 + 2 purringer)
export const GIVE_UP_MIN = 120;      // varsle ikke doser eldre enn dette

// Tidspunkt 'HH:MM' -> minutter siden midnatt
export function hmToMin(hm) {
  const m = /^(\d{1,2}):(\d{2})$/.exec(String(hm || '').trim());
  if (!m) return null;
  const h = +m[1], mi = +m[2];
  if (h > 23 || mi > 59) return null;
  return h * 60 + mi;
}

// Firebase-trygg nøkkel for et notif-merke (ingen . $ # [ ] /)
export function slotKey(medId, dateISO, time) {
  return `${medId}_${dateISO}_${String(time).replace(/[^0-9]/g, '')}`;
}

// Les et notif-merke uansett format: {c,t} (nytt) eller ISO-streng (gammelt)
export function readNotif(st) {
  if (!st) return { count: 0, lastMs: 0 };
  if (typeof st === 'object') return { count: st.c || 0, lastMs: st.t || 0 };
  const ms = Date.parse(st);
  return { count: 1, lastMs: isNaN(ms) ? 0 : ms }; // gammelt engangs-merke
}

// Oslo-lokale tidsdeler for et Date-objekt
export function osloParts(d = new Date()) {
  const fmt = new Intl.DateTimeFormat('en-GB', {
    timeZone: 'Europe/Oslo', year: 'numeric', month: '2-digit', day: '2-digit',
    hour: '2-digit', minute: '2-digit', weekday: 'short', hour12: false,
  });
  const p = Object.fromEntries(fmt.formatToParts(d).map((x) => [x.type, x.value]));
  const hour = p.hour === '24' ? '00' : p.hour; // enkelte miljøer gir 24
  const dowMap = { Sun: 0, Mon: 1, Tue: 2, Wed: 3, Thu: 4, Fri: 5, Sat: 6 };
  return {
    dateISO: `${p.year}-${p.month}-${p.day}`,
    hhmm: `${hour}:${p.minute}`,
    minOfDay: (+hour) * 60 + (+p.minute),
    dow: dowMap[p.weekday],
    ms: d.getTime(),
  };
}

const asArray = (mapOrArr) =>
  Array.isArray(mapOrArr) ? mapOrArr
    : mapOrArr && typeof mapOrArr === 'object'
      ? Object.entries(mapOrArr).map(([id, v]) => ({ id, ...(v || {}) }))
      : [];

// Regn ut hvilke doser som skal varsles nå.
// hh: { meds, medLog, medNotif } (maps eller arrays)
// now: resultat fra osloParts() (må ha .ms for purre-timing)
// opts: { everyMin, max, giveUp } – overstyrer standardverdiene
// Returnerer [{ med, time, slotId, key, count }] der count = antall sendt hittil
export function dueDoses(hh, now, opts = {}) {
  const everyMin = opts.everyMin != null ? opts.everyMin : REPEAT_EVERY_MIN;
  const max = opts.max != null ? opts.max : MAX_REMINDERS;
  const giveUp = opts.giveUp != null ? opts.giveUp : GIVE_UP_MIN;
  const nowMs = now.ms != null ? now.ms : Date.now();

  const meds = asArray(hh && hh.meds);
  const log = asArray(hh && hh.medLog);
  const notif = (hh && hh.medNotif) || {};

  const takenSlots = new Set(
    log.filter((e) => e && !e.deleted && e.slot).map((e) => e.slot)
  );

  const out = [];
  for (const med of meds) {
    if (!med || med.deleted) continue;
    if (med.active === false) continue;
    const times = Array.isArray(med.times) ? med.times : [];
    const days = Array.isArray(med.days) && med.days.length ? med.days.map(Number) : null;
    if (days && !days.includes(now.dow)) continue;

    for (const t of times) {
      const tm = hmToMin(t);
      if (tm == null) continue;
      const diff = now.minOfDay - tm;
      if (diff < 0 || diff > giveUp) continue;         // ikke forfalt enda, eller for gammelt
      const slotId = `${med.id}|${now.dateISO}|${t}`;
      if (takenSlots.has(slotId)) continue;            // allerede tatt

      const key = slotKey(med.id, now.dateISO, t);
      const { count, lastMs } = readNotif(notif[key]);
      if (count >= max) continue;                      // ferdig å purre
      if (count > 0) {
        const minsSince = (nowMs - lastMs) / 60000;
        if (minsSince < everyMin) continue;            // for tidlig for ny purring
      }
      out.push({ med, time: t, slotId, key, count });
    }
  }
  return out;
}
