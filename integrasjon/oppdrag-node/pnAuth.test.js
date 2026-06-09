'use strict';
/**
 * Kontrakttest: verifiserer at Node-siden godtar et token pn-auth (PyJWT) lager,
 * og avviser tuklet/utløpt token. Kjør: node --test integrasjon/oppdrag-node/
 * AUTH_SECRET injiseres av test-runneren under (se package i DEPLOY.md).
 */
const test = require('node:test');
const assert = require('node:assert');
const crypto = require('crypto');

process.env.AUTH_SECRET = 'x'.repeat(40);
const { verifyToken } = require('./pnAuth');

const SECRET = process.env.AUTH_SECRET;

function b64url(buf) {
  return Buffer.from(buf).toString('base64')
    .replace(/\+/g, '-').replace(/\//g, '_').replace(/=+$/, '');
}
// Lag et HS256-token slik PyJWT gjør (samme kontrakt som pn-auth).
function makeToken(payload, secret = SECRET) {
  const h = b64url(JSON.stringify({ alg: 'HS256', typ: 'JWT' }));
  const p = b64url(JSON.stringify(payload));
  const sig = b64url(crypto.createHmac('sha256', secret).update(h + '.' + p).digest());
  return `${h}.${p}.${sig}`;
}

const now = Math.floor(Date.now() / 1000);
const base = {
  sub: '7', name: 'Mathias', email: 'mathias@parknordic.no',
  permissions: { oppdrag: 1, sanksjon: 1, datakvalitet: 0, admin: 0 },
  iat: now, exp: now + 3600,
};

test('godtar gyldig token og leser claims', () => {
  const c = verifyToken(makeToken(base), SECRET);
  assert.ok(c);
  assert.strictEqual(c.email, 'mathias@parknordic.no');
  assert.strictEqual(c.permissions.oppdrag, 1);
});

test('avviser feil signatur (tuklet payload)', () => {
  const t = makeToken(base);
  const parts = t.split('.');
  const tampered = { ...base, permissions: { ...base.permissions, admin: 1 } };
  parts[1] = b64url(JSON.stringify(tampered)); // bytt payload, behold gammel signatur
  assert.strictEqual(verifyToken(parts.join('.'), SECRET), null);
});

test('avviser token signert med feil hemmelighet', () => {
  assert.strictEqual(verifyToken(makeToken(base, 'y'.repeat(40)), SECRET), null);
});

test('avviser utløpt token', () => {
  const expired = { ...base, exp: now - 10 };
  assert.strictEqual(verifyToken(makeToken(expired), SECRET), null);
});

test('avviser tull/manglende token', () => {
  assert.strictEqual(verifyToken('', SECRET), null);
  assert.strictEqual(verifyToken('a.b', SECRET), null);
  assert.strictEqual(verifyToken(null, SECRET), null);
});
