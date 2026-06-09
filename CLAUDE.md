# CLAUDE.md

Guidance for AI assistants (Claude Code and others) working in this repository.
Read this fully before making changes.

> **Language note:** The product, UI, domain terms, and team communication are
> **Norwegian**. Keep all user-facing strings, comments that mirror UI copy, and
> domain vocabulary in Norwegian. This file is in English for tooling clarity; a
> glossary of domain terms is at the end.

---

## 1. What this repository is

The core artifact is `parknordic_dashboard.html` — a self-contained, single-file
**frontend mockup** of the **Sanksjon** (sanction-handling) dashboard / portal shell
for Park Nordic AS, an internal parking-enforcement company.

The repo also now holds the **felles-auth changeset** (shared login + access control)
built toward the architecture in §5/§6:

```
parknordic_dashboard.html   Portal/dashboard. Single login + admin "Brukere og tilganger"
                            (gated by LAUNCHER_MODUS; mockup still works standalone).
pn-auth/                    Standalone felles Auth API (FastAPI + SQLite + JWT). Tested
                            (pytest). Owns users/permissions; bcrypt; secret-or-die; rate-limit.
  app/  migrate.py  schema.sql  tests/  README.md
integrasjon/                Drop-in glue for the systems whose source is NOT in this repo:
  oppdrag-node/pnAuth.js        Express middleware (verifies pn_auth JWT, no npm deps)
  sanksjon-fastapi/pn_auth.py   FastAPI dependency (requires permissions.sanksjon)
  nginx/                        security headers + HSTS + auth_request for Datakvalitet
  systemd/                      hardened service units (dedicated users, 127.0.0.1)
DEPLOY.md                   Ordered deploy notes; maps acceptance criteria + security findings.
```

> The **pn-auth token contract** (HS256 JWT in cookie `pn_auth`, payload
> `{sub,name,email,permissions{oppdrag,sanksjon,datakvalitet,admin},exp}`) is shared
> across `pn-auth/app/security.py`, the Node middleware and the FastAPI dependency —
> change them in lockstep. Tests: `pn-auth/tests/`, `integrasjon/*/`. See DEPLOY.md.

- **Pure client-side.** No backend, no build step, no package manager, no
  dependencies installed locally. Everything (HTML, CSS, JS) lives in the one
  file. The only external runtime dependencies are two CDNs:
  - **Chart.js 4.4.0** (`cdn.jsdelivr.net`) for the dashboard charts.
  - **Google Fonts – Saira** (the Park Nordic brand typeface).
- **It is a mockup / prototype.** There are **no `fetch`/API calls**. Login,
  users, and data are hardcoded or stored in `localStorage`. Several panels are
  explicitly labelled as not-yet-built (e.g. the full sanctions list says
  *"ikke i mockup"*). Treat the data layer as throwaway scaffolding, not product.

To view it: open `parknordic_dashboard.html` directly in a browser, or serve the
folder statically (`python3 -m http.server`). There is nothing to install or compile.

### This repo's place in the bigger picture

Park Nordic runs three internal systems behind nginx on
`kontrollverktoy.parknordic.no`, each on a subpath:

| System         | Stack                | Subpath          | Role |
|----------------|----------------------|------------------|------|
| **Oppdrag**    | Node.js / Express    | `/oppdrag/`      | Today's identity provider (bcrypt + `express-session`, users in `data/data.json`) |
| **Sanksjon**   | FastAPI + SQLite     | `/sanksjon/`     | **This dashboard's system.** Holds the ~10 real employee accounts in `parknordic.db`; cookie `pn_session` (itsdangerous) |
| **Datakvalitet** | Static HTML (no backend) | `/datakvalitet/` | Anders' CSV-quality tool; runs entirely in the browser |

This repository is the **frontend mockup for Sanksjon** (and doubles as the
candidate portal/dashboard shell). The real Sanksjon backend (FastAPI/SQLite) is
**not** in this repo. The broader architecture, security, and auth direction the
team has already decided on is captured in a handoff package (see §6) — **follow
those decisions, do not reinvent the architecture.**

---

## 2. Structure of `parknordic_dashboard.html`

One file, ~2340 lines, three sections:

1. **`<style>`** (top) — All CSS. Starts with the Park Nordic design tokens in
   `:root` (see §4). Then login screen, app shell, nav, pages, modals, components.
2. **Markup** — Two top-level states toggled by a class:
   - `.login-screen#loginScreen` — the login view.
   - `.app#app` — the authenticated shell: left `nav.nav` + a stack of
     `.page` elements.
   - Modals: `#forgotModal`, `#changePwdModal`, the PDF-upload modal.
3. **`<script>`** (bottom) — All JS as plain functions on the global scope
   (no modules, no framework). Wired with inline `onclick=`/`oninput=` handlers
   and a few `addEventListener` calls at the end.

### Pages (`id="page-…"`, switched by `goTo(pageId)`)

| `data-page` / id        | Purpose |
|-------------------------|---------|
| `page-dashboard`        | Landing: PDF dropzone, KPI cards, Chart.js charts |
| `page-sanctions`        | Full sanction list (placeholder — *"ikke i mockup"*) |
| `page-anlegg`           | Parking facilities ("anlegg") table + search |
| `page-weekly`           | Preview of the week's outgoing batch |
| `page-settings`         | User/role settings |

### Key JS entry points

- `doLogin()` / `doLogout()` — toggle login vs app; set `CURRENT_USER`.
- `applyCurrentUser()` — fills every `[data-user-*]` slot (name, email, initials,
  role) from `CURRENT_USER`. **Use these `data-user-*` hooks** rather than
  hardcoding user info in markup.
- `goTo(pageId)` — page navigation (toggles `.active`, scrolls to top).
- `getStoredPwd(email)` / `setStoredPwd(email, pwd)` — passwords in
  `localStorage` key `pn_passwords`; default password is `nordic1234`.
- `searchAnlegg` / `pickAnlegg` / `renderAnleggTable` — facility autocomplete,
  backed by the hardcoded `ANLEGG` array (~500 `{nr, navn}` entries).
- `openModal()` / `confirmUpload()` and the global drag-and-drop block — the
  "drop a PDF anywhere → open upload modal" flow.

### Hardcoded data you will see (all mock)

- `USERS` — 10 Park Nordic employees, all `rolle: 'Admin'`, keyed by
  `@parknordic.no` email. No real auth.
- The login form ships with a **prefilled email + password** for demo convenience
  (`mathias@parknordic.no` / `nordic1234`). Fine for a mockup; must never ship to
  production.
- `ANLEGG` — the parking-facility list.

---

## 3. Core domain workflow (what the product does)

1. A parking attendant issues a sanction; the paper/PDF blankett is the source.
2. In the dashboard the user **drops the PDF** → the system "reads" it → the user
   chooses how the sanction is handled:
   - **Betalt av Park Nordic** ("Paid by PN") — PN covers the cost (this feeds the
     daily Riverty delivery file, see §6).
   - **Trekkes fra leieberegningen** — deducted from the rent calculation for that
     *anlegg* (facility), with a written justification.
3. Choices are collected into a **weekly batch** sent automatically **Friday 08:00**.

When touching this flow, preserve the two-way "Paid by PN vs. deduct-from-rent"
distinction — it is a financial/billing decision, not cosmetic.

---

## 4. Conventions to follow

### Design system (Park Nordic brand)

Always use the CSS custom properties in `:root`; never hardcode brand colours.

```
--pn-darkblue   #1a2641   (primary)      --pn-turkis1/2/3  teal accents
--pn-yellow     #ffcc00   (highlight)    --pn-gray1..4     neutrals
--pn-bg         #eaf3f3   (page bg)       --pn-text-muted  #6b7280
--radius 6px  --radius-lg 12px  --shadow-soft …
```

- **Font:** `'Saira'` everywhere.
- **Language:** Norwegian (Bokmål) for all UI copy. `lang="nb"`.
- **Style of the code:** vanilla HTML/CSS/JS, no framework, functions on global
  scope, inline event handlers. Match this style — do **not** introduce React,
  bundlers, npm, TypeScript, or a build step unless the user explicitly asks.
  Keep it a single self-contained file unless asked otherwise.

### Editing rules

- Keep CSS in the `<style>` block, JS in the `<script>` block; don't split the file.
- Reuse existing component classes and the `data-user-*` / `data-page` hooks.
- Don't add new external CDNs casually; the team prefers minimal external calls
  (they've discussed self-hosting Saira to avoid third-party requests).
- This is a mockup: it's fine for data to be hardcoded, but never wire a mockup to
  real credentials or a real endpoint without being asked.

---

## 5. Architecture & security guardrails (when this grows up)

If asked to evolve this mockup toward the real product, the team has **already made
these decisions** — build toward them, don't relitigate them. Source: the handoff
package (§6).

**Target end-state:** one login → dashboard shows only the systems the user has
access to → admin grants per-system access from the dashboard → each system's
separate login is removed. There is currently a known login-loop bug; the fix is
**consolidation to one source of truth**, *not* force-logout / cookie-clearing.

**Hard rules (do not break):**

- **Shared session across Node + Python = a signed JWT** in a cookie on
  `.parknordic.no`, verified statelessly in each system with a shared
  `AUTH_SECRET` (≥32 chars). **No shared session store.**
- **Access is enforced server-side** in every system (and via nginx
  `auth_request → /auth/verify?system=…` for the static Datakvalitet tool).
  Hiding a card in the UI is **not** a security boundary.
- APIs live on subpaths: `/oppdrag/api/*`, `/sanksjon/api/*` — **never** `/api/*`.
- FastAPI runs with `root_path="/sanksjon"`; nginx `proxy_pass` to FastAPI
  **without** a trailing slash.
- Oppdrag's front page is a **PWA with a service worker at the root** — never move
  or overwrite it.
- Master user DB = **Sanksjon's SQLite** (it has the real accounts). Add a
  `permissions` table; migrate Oppdrag users in. Password hashes are **not**
  cross-compatible (bcrypt vs. Sanksjon's format) — users reset, don't migrate raw.
- E-mail goes via the **SMTP2GO relay**, never directly against Microsoft 365.

**Security baseline (must hold before any access-control ships):**

- `DEBUG=false` in production (no Swagger / API docs exposed).
- Secrets come from the environment and the app **stops if they're missing** — no
  hardcoded fallback (e.g. never `SESSION_SECRET || "bytt-meg"`).
- App processes bind to `127.0.0.1`, never `0.0.0.0`, behind nginx.
- Rate-limit every login endpoint.
- nginx security headers: HSTS, `X-Content-Type-Options`, `X-Frame-Options`,
  `Referrer-Policy`, `server_tokens off`; TLS 1.2/1.3 only.
- Session cookies `httpOnly`, `secure`, `sameSite=lax`.
- Run maintained runtimes (Node 22 LTS; not EOL versions).
- Dedicated, login-less service users + systemd hardening (not a personal account).

**Working boundary:** build and test against a **copy** of the codebase. Do **not**
assume production access. Deliver a tested changeset + short deploy notes; a human
(Thomas) deploys. Run and test your code before calling it done.

---

## 6. Reference material (handoff package)

The authoritative context lives in a separately delivered handoff package
(`ParkNordic_handoff_komplett`), **not committed to this repo**. It is confidential
and internal to Park Nordic. Key documents and what they cover:

- `00_START_HER.md` — overview, work split, ordered roadmap.
- `CLAUDE_CODE_BRIEF.md` — operational brief for AI agents; read first.
- `FELLES_AUTH_spec.md` — shared-auth data model, Auth API contract, migration.
- `BYGGESTANDARD_parknordic.md` — server/architecture build standard (living doc).
- `SIKKERHETSGJENNOMGANG.md` — prioritized security findings to close first.
- `RIVERTY_leveranse_spec.md` — daily "Paid by PN" delivery file format (plain
  `.txt`, one sanction number per line, no header; delivered via SFTP).
- `datakvalitet/INSTALL_datakvalitet.md` + `datakvalitet/index.html` — the static
  data-quality tool and how to wire it behind nginx `auth_request`.

If the user references these, ask for them or work from the summary above; **the
decisions in those docs override convenience** — don't reinvent the architecture.

---

## 7. Git workflow

- Default/integration branch: `main`.
- Develop on a feature branch; commit with clear, descriptive messages.
- Push with `git push -u origin <branch>`. On network errors, retry with
  exponential backoff (2s, 4s, 8s, 16s).
- **Do not open a pull request unless explicitly asked.**
- This is **confidential, internal Park Nordic material** — do not share outside
  the project or paste it into external services.

---

## 8. Glossary (Norwegian → English)

| Term | Meaning |
|------|---------|
| **Sanksjon** | Sanction / parking fine; also the FastAPI system handling them |
| **Anlegg** | Parking facility / site (each has a number `nr` and `navn`) |
| **Oppdrag** | The Node.js system; today's identity provider |
| **Datakvalitet** | Anders' static data-quality (CSV) tool |
| **Ileggelse / blankett** | The issued fine / its form (PDF) |
| **Betalt av Park Nordic** | "Paid by PN" — PN covers the fine (→ Riverty file) |
| **Trekkes fra leieberegning** | Deducted from the facility's rent calculation |
| **Brukere og tilganger** | "Users and access" — the admin access-management screen |
| **Felles innlogging** | Shared/single sign-on login |
| **Sikkerhetsgjennomgang** | Security review |
| **Byggestandard** | Build standard |
| **LAUNCHER_MODUS** | Portal flag; `true` = no shared login yet (stable interim) |

---

*Park Nordic AS – internal. Confidential.*
