'use strict';
/**
 * Park Nordic – felles auth for Oppdrag (Node/Express).
 *
 * Verifiserer pn_auth-JWT (HS256) STATELESS med delt AUTH_SECRET – samme token som
 * pn-auth utsteder (se pn-auth/app/security.py). Ingen npm-avhengighet: bruker Nodes
 * innebygde `crypto`. Dette ERSTATTER Oppdrags egen express-session-innlogging og
 * egen brukerliste i data.json.
 *
 * Bruk i server.js:
 *   const { pnAuth } = require('./pnAuth');
 *   app.use('/oppdrag/api', pnAuth({ system: 'oppdrag' }));   // håndhev server-side
 *   // uinnlogget → redirect til portalen (felles innlogging), ikke egen login-side.
 *
 * VIKTIG (BYGGESTANDARD): PWA-en/service workeren på roten skal IKKE beskyttes/flyttes.
 * Legg auth bare på /oppdrag/api og de sidene som krever innlogging.
 */
const crypto = require('crypto');

const COOKIE_NAME = process.env.COOKIE_NAME || 'pn_auth';

function getSecret() {
  const s = process.env.AUTH_SECRET;
  if (!s || s.length < 32) {
    // Sikkerhetsbaseline: ingen hardkodet reserve – stopp hvis nøkkel mangler.
    throw new Error('AUTH_SECRET må være satt (min 32 tegn).');
  }
  return s;
}

function b64urlToBuf(s) {
  s = String(s).replace(/-/g, '+').replace(/_/g, '/');
  while (s.length % 4) s += '=';
  return Buffer.from(s, 'base64');
}

/** Verifiser et HS256-JWT. Returnerer payload (claims) eller null. */
function verifyToken(token, secret) {
  if (!token || typeof token !== 'string') return null;
  const parts = token.split('.');
  if (parts.length !== 3) return null;
  const [h, p, sig] = parts;
  const expected = crypto.createHmac('sha256', secret).update(h + '.' + p).digest();
  const got = b64urlToBuf(sig);
  if (expected.length !== got.length || !crypto.timingSafeEqual(expected, got)) return null;
  let header, payload;
  try {
    header = JSON.parse(b64urlToBuf(h).toString('utf8'));
    payload = JSON.parse(b64urlToBuf(p).toString('utf8'));
  } catch (e) { return null; }
  if (!header || header.alg !== 'HS256') return null;
  const now = Math.floor(Date.now() / 1000);
  if (typeof payload.exp === 'number' && now >= payload.exp) return null;
  if (typeof payload.nbf === 'number' && now < payload.nbf) return null;
  return payload;
}

function readCookie(req, name) {
  if (req.cookies && req.cookies[name]) return req.cookies[name];
  const raw = req.headers && req.headers.cookie;
  if (!raw) return null;
  for (const part of raw.split(';')) {
    const i = part.indexOf('=');
    if (i > -1 && part.slice(0, i).trim() === name) {
      return decodeURIComponent(part.slice(i + 1).trim());
    }
  }
  return null;
}

/**
 * Express-middleware-fabrikk.
 * @param {object} opts
 * @param {string} [opts.system]        - krev permissions[system] (eller admin). Utelat = bare innlogget.
 * @param {string} [opts.loginRedirect] - hvor uinnloggede HTML-kall sendes (portalen). Default '/'.
 */
function pnAuth(opts = {}) {
  const secret = getSecret();
  const system = opts.system;
  const loginRedirect = opts.loginRedirect || '/';
  return function (req, res, next) {
    const claims = verifyToken(readCookie(req, COOKIE_NAME), secret);
    if (!claims) {
      if (req.accepts && req.accepts('html')) return res.redirect(302, loginRedirect);
      return res.status(401).json({ error: 'Ikke innlogget' });
    }
    const perms = claims.permissions || {};
    if (system && !perms.admin && !perms[system]) {
      return res.status(403).json({ error: 'Ingen tilgang til ' + system });
    }
    req.bruker = {
      id: Number(claims.sub), navn: claims.name, epost: claims.email,
      admin: !!perms.admin, permissions: perms,
    };
    next();
  };
}

module.exports = { pnAuth, verifyToken, readCookie, COOKIE_NAME };
