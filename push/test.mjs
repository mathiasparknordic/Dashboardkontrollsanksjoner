// Enkle tester for due-logikken. Kjør: node test.mjs
import { dueDoses, hmToMin, slotKey, osloParts } from './due.mjs';

let pass = 0, fail = 0;
const ok = (name, cond) => { (cond ? pass++ : fail++); console.log(`${cond ? 'PASS' : 'FAIL'}  ${name}`); };

// hmToMin
ok('hmToMin 07:00', hmToMin('07:00') === 420);
ok('hmToMin 7:5 ugyldig', hmToMin('7:5') === null || hmToMin('7:5') === 425 ? true : false);
ok('hmToMin tull', hmToMin('xx') === null);

// slotKey trygg
ok('slotKey uten forbudte tegn', !/[.$#\[\]/]/.test(slotKey('m1', '2026-11-07', '07:00')));

const now = { dateISO: '2026-11-07', hhmm: '07:03', minOfDay: 7 * 60 + 3, dow: 6 };

const baseMed = { id: 'm1', name: 'Escitalopram', dose: '15 mg', pills: 1, icon: '💊', times: ['07:00'] };

// 1) due når innenfor vindu, ikke tatt, ikke varslet
ok('due innenfor vindu', dueDoses({ meds: { m1: baseMed } }, now).length === 1);

// 2) ikke due før tid
ok('ikke due før tid', dueDoses({ meds: { m1: { ...baseMed, times: ['09:00'] } } }, now).length === 0);

// 3) ikke due hvis for lenge siden (>120 min)
ok('ikke due hvis for gammelt', dueDoses({ meds: { m1: { ...baseMed, times: ['04:00'] } } }, now).length === 0);

// 4) tatt -> ikke due
ok('tatt -> ikke due', dueDoses({
  meds: { m1: baseMed },
  medLog: { l1: { medId: 'm1', slot: 'm1|2026-11-07|07:00', takenAt: '2026-11-07T07:01:00Z' } },
}, now).length === 0);

// 5) allerede varslet -> ikke due
ok('varslet -> ikke due', dueDoses({
  meds: { m1: baseMed },
  medNotif: { [slotKey('m1', '2026-11-07', '07:00')]: '2026-11-07T07:00:30Z' },
}, now).length === 0);

// 6) feil ukedag -> ikke due (now.dow=6 lør; med kun hverdager 1-5)
ok('feil ukedag -> ikke due', dueDoses({ meds: { m1: { ...baseMed, days: [1, 2, 3, 4, 5] } } }, now).length === 0);

// 7) riktig ukedag -> due
ok('riktig ukedag -> due', dueDoses({ meds: { m1: { ...baseMed, days: [6, 0] } } }, now).length === 1);

// 8) inaktiv -> ikke due
ok('inaktiv -> ikke due', dueDoses({ meds: { m1: { ...baseMed, active: false } } }, now).length === 0);

// 9) slettet -> ikke due
ok('slettet -> ikke due', dueDoses({ meds: { m1: { ...baseMed, deleted: true } } }, now).length === 0);

// 10) flere tidspunkter: bare den forfalte teller
ok('flere tidspunkt, kun forfalt', dueDoses({ meds: { m1: { ...baseMed, times: ['07:00', '20:00'] } } }, now).length === 1);

// 11) arrays (ikke bare maps) fungerer
ok('meds som array', dueDoses({ meds: [baseMed] }, now).length === 1);

// 12) osloParts gir fornuftige felter
const p = osloParts(new Date('2026-11-07T06:03:00Z'));
ok('osloParts dateISO', /^\d{4}-\d{2}-\d{2}$/.test(p.dateISO));
ok('osloParts dow 0-6', p.dow >= 0 && p.dow <= 6);

console.log(`\n${pass}/${pass + fail} bestått`);
process.exit(fail ? 1 : 0);
