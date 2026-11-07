// Ren logikk for å regne ut hvilke medisin-doser som er "due" akkurat nå.
// Ingen nettverk/IO her – gjør den enkel å teste.

export const WINDOW_MIN = 120; // hvor lenge etter planlagt tid vi fortsatt minner (min)

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
  };
}

const asArray = (mapOrArr) =>
  Array.isArray(mapOrArr) ? mapOrArr
    : mapOrArr && typeof mapOrArr === 'object'
      ? Object.entries(mapOrArr).map(([id, v]) => ({ id, ...(v || {}) }))
      : [];

// Regn ut due-doser for én husholdning.
// hh: { meds, medLog, medNotif } (maps eller arrays)
// now: resultat fra osloParts()
// Returnerer [{ med, time, slotId, key }]
export function dueDoses(hh, now, windowMin = WINDOW_MIN) {
  const meds = asArray(hh && hh.meds);
  const log = asArray(hh && hh.medLog);
  const notif = (hh && hh.medNotif) || {};

  // Sett med allerede-tatte slots
  const takenSlots = new Set(
    log.filter((e) => e && !e.deleted && e.slot).map((e) => e.slot)
  );

  const out = [];
  for (const med of meds) {
    if (!med || med.deleted) continue;
    if (med.active === false) continue;
    const times = Array.isArray(med.times) ? med.times : [];
    // days: array av ukedager (0=søn..6=lør). Mangler/ tom = hver dag.
    const days = Array.isArray(med.days) && med.days.length ? med.days.map(Number) : null;
    if (days && !days.includes(now.dow)) continue;

    for (const t of times) {
      const tm = hmToMin(t);
      if (tm == null) continue;
      const diff = now.minOfDay - tm;
      if (diff < 0 || diff > windowMin) continue; // ikke forfalt enda, eller for gammelt
      const slotId = `${med.id}|${now.dateISO}|${t}`;
      if (takenSlots.has(slotId)) continue;       // allerede tatt
      const key = slotKey(med.id, now.dateISO, t);
      if (notif[key]) continue;                    // allerede varslet
      out.push({ med, time: t, slotId, key });
    }
  }
  return out;
}
