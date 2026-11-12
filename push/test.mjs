// Tester for due-logikken, inkl. gjentatte påminnelser. Kjør: node test.mjs
import { dueDoses, hmToMin, slotKey, readNotif, osloParts, reminderBody } from './due.mjs';

let pass = 0, fail = 0;
const ok = (name, cond) => { (cond ? pass++ : fail++); console.log(`${cond ? 'PASS' : 'FAIL'}  ${name}`); };

// Fast "nå": lørdag 7. nov 2026, 07:03 Oslo (= 06:03Z)
const NOW_MS = Date.parse('2026-11-07T06:03:00Z');
const now = { dateISO: '2026-11-07', hhmm: '07:03', minOfDay: 7 * 60 + 3, dow: 6, ms: NOW_MS };
const minsAgo = (m) => NOW_MS - m * 60000;

const baseMed = { id: 'm1', name: 'Escitalopram', dose: '15 mg', pills: 1, icon: '💊', times: ['07:00'] };
const KEY = slotKey('m1', '2026-11-07', '07:00');

// --- enkle hjelpere ---
ok('hmToMin 07:00', hmToMin('07:00') === 420);
ok('hmToMin tull', hmToMin('xx') === null);
ok('slotKey uten forbudte tegn', !/[.$#\[\]/]/.test(KEY));
ok('readNotif tom', readNotif(undefined).count === 0);
ok('readNotif objekt', readNotif({ c: 2, t: 123 }).count === 2 && readNotif({ c: 2, t: 123 }).lastMs === 123);
ok('readNotif gammel streng', readNotif('2026-11-07T07:00:00Z').count === 1);

// --- første varsel ---
let d = dueDoses({ meds: { m1: baseMed } }, now);
ok('første varsel er due', d.length === 1 && d[0].count === 0);

// --- timing ---
ok('ikke due før tid', dueDoses({ meds: { m1: { ...baseMed, times: ['09:00'] } } }, now).length === 0);
ok('ikke due hvis for gammelt (>120 min)', dueDoses({ meds: { m1: { ...baseMed, times: ['04:00'] } } }, now).length === 0);

// --- tatt ---
ok('tatt -> ikke due', dueDoses({
  meds: { m1: baseMed },
  medLog: { l1: { medId: 'm1', slot: 'm1|2026-11-07|07:00', takenAt: '...' } },
}, now).length === 0);

// --- GJENTATTE PÅMINNELSER ---
ok('nylig varslet (5 min siden) -> ikke due enda', dueDoses({
  meds: { m1: baseMed }, medNotif: { [KEY]: { c: 1, t: minsAgo(5) } },
}, now).length === 0);

d = dueDoses({ meds: { m1: baseMed }, medNotif: { [KEY]: { c: 1, t: minsAgo(25) } } }, now);
ok('varslet for 25 min siden -> purrer (due, count 1)', d.length === 1 && d[0].count === 1);

ok('nådd maks (3) -> slutter å purre', dueDoses({
  meds: { m1: baseMed }, medNotif: { [KEY]: { c: 3, t: minsAgo(60) } },
}, now).length === 0);

d = dueDoses({ meds: { m1: baseMed }, medNotif: { [KEY]: { c: 2, t: minsAgo(30) } } }, now);
ok('andre purring etter nok tid (due, count 2)', d.length === 1 && d[0].count === 2);

// gammelt engangs-merke (ISO, >20 min siden) -> purrer videre
d = dueDoses({ meds: { m1: baseMed }, medNotif: { [KEY]: '2026-11-07T05:30:00Z' } }, now);
ok('gammelt ISO-merke (33 min) -> purrer (due)', d.length === 1);

// --- opts override ---
ok('max=1 stopper etter første', dueDoses({
  meds: { m1: baseMed }, medNotif: { [KEY]: { c: 1, t: minsAgo(60) } },
}, now, { max: 1 }).length === 0);
ok('everyMin=10 tillater purring etter 12 min', dueDoses({
  meds: { m1: baseMed }, medNotif: { [KEY]: { c: 1, t: minsAgo(12) } },
}, now, { everyMin: 10 }).length === 1);

// --- dager / tilstand ---
ok('feil ukedag -> ikke due', dueDoses({ meds: { m1: { ...baseMed, days: [1, 2, 3, 4, 5] } } }, now).length === 0);
ok('riktig ukedag -> due', dueDoses({ meds: { m1: { ...baseMed, days: [6, 0] } } }, now).length === 1);
ok('inaktiv -> ikke due', dueDoses({ meds: { m1: { ...baseMed, active: false } } }, now).length === 0);
ok('slettet -> ikke due', dueDoses({ meds: { m1: { ...baseMed, deleted: true } } }, now).length === 0);
ok('flere tidspunkt, kun forfalt teller', dueDoses({ meds: { m1: { ...baseMed, times: ['07:00', '20:00'] } } }, now).length === 1);
ok('meds som array', dueDoses({ meds: [baseMed] }, now).length === 1);

// --- varseltekst (uten dose, riktig flertall) ---
ok('body: 1 pille', reminderBody({ pills: 1 }, 1) === 'Ta 1 pille');
ok('body: 2 piller', reminderBody({ pills: 2 }, 1) === 'Ta 2 piller');
ok('body: standard 1 når pills mangler', reminderBody({}, 1) === 'Ta 1 pille');
ok('body: ingen dose i teksten', !/mg|15/.test(reminderBody({ pills: 1, dose: '15 mg' }, 1)));
ok('body: purring viser påminnelse-nr', reminderBody({ pills: 1 }, 2) === 'Ta 1 pille · påminnelse 2');

// --- osloParts ---
const p = osloParts(new Date('2026-11-07T06:03:00Z'));
ok('osloParts dateISO', /^\d{4}-\d{2}-\d{2}$/.test(p.dateISO));
ok('osloParts dow 0-6', p.dow >= 0 && p.dow <= 6);
ok('osloParts har ms', typeof p.ms === 'number' && p.ms > 0);

console.log(`\n${pass}/${pass + fail} bestått`);
process.exit(fail ? 1 : 0);
