# Development report

## Scope and outcome

FEN HOU LA was developed as a small, deployable expense-sharing experiment. The delivered product covers account registration/login, owner-managed groups, named participants, multi-bill events, cent-safe splitting, event history, billing requests, recipient messages, PNG invoice cards, private receipt boundaries, Cloudflare-ready public mode, and a no-code operator workbench.

The application is intentionally not a payment processor. It records what people owe and whether a request was manually marked paid; it does not move money, send WhatsApp/email messages, perform OCR, or link guest participants automatically to accounts.

## Technology stack

- Frontend: React 18, TypeScript, Vite, responsive CSS, browser share/print APIs, Playwright E2E.
- Backend: Python 3.12, FastAPI, SQLAlchemy, Pydantic, Argon2 password hashing, JWT cookie sessions.
- Data: PostgreSQL for Docker deployments, SQLite-compatible test paths, Alembic migrations, integer cents for calculations and `DECIMAL(12,2)` persistence.
- Storage: provider-independent receipt interface with local-disabled behavior; R2 configuration hooks are server-side only.
- Delivery: Docker Compose, nginx same-origin `/api` proxy, Cloudflare Tunnel for optional public HTTPS access.
- Quality: GitHub Actions CI, pytest unit/API tests, TypeScript checks, production frontend builds, browser flow checks.

## Development phases

### Phase 1 — Foundation and vertical slice

Created the Dockerized FastAPI/React application, PostgreSQL persistence, migrations, Traditional Chinese/HKD interface, registration/login, groups, bills, equal splitting, completion, and reloadable event history.

### Phase 2 — Product workflow

Added named participant roles independent from application accounts, exact per-person totals across bills, fixed/percentage allocation support, billing requests, manual paid status, copyable recipient messages, merged settlement calculations, event detail review, and date-only bill entry.

### Phase 3 — Sharing and receipts

Added recipient-specific invoice-style message cards, PNG generation, browser share/download/print handling, receipt metadata and validation boundaries, and print-focused fixes for blank pages, duplicated content, and whole-event versus recipient-only output.

### Phase 4 — Authorization and lifecycle hardening

Introduced group ownership boundaries, member read-only access, owner-only mutation/sharing actions, safe participant/member removal, event and bill deletion confirmations, in-application notifications, immutable completed events, and cross-group ID validation.

### Phase 5 — Responsive UX and deployment

Refined desktop/mobile layouts, mobile group navigation and compact action controls, validation focus/error states, local/public Docker mode switching, migration-on-startup for PostgreSQL, Cloudflare HTTPS settings, secure headers/cookies, isolated public data, and deployment documentation.

### Phase 6 — Operator workbench and auditability

Added an environment-configured admin account, account disable/enable controls, group archival, summary metrics, confirmation-gated operations, immutable audit records, and meaningful audit descriptions that include target identity, resulting status, operator, and timestamp. Legacy terse status records are normalized when read.

## Verification record

- Backend unit and integration suite: 11 tests passed in the final verification run.
- Frontend TypeScript lint: passed.
- Frontend production build: passed.
- Local Docker frontend health: HTTP 200.
- Local Docker API health: HTTP 200.
- Public HTTPS API health through Cloudflare hostname: HTTP 200.
- Public audit API verified with operator login; entries returned account name, username, status, and operator name.
- CI includes backend, frontend, and E2E jobs. Browser testing was performed during development for owner/member permissions, deletion confirmations, billing flows, responsive layouts, and operator controls.

The browser session may require a fresh login after a container restart because the running environment is intentionally replaceable. This does not reset either Docker database volume.

## AI assistance and token cost

The implementation was produced with OpenAI Codex-style coding assistance in this workspace. The exact model can vary by task/session; this repository does not embed a model name, prompt transcript, token counter, or billing account data. No AI API key or model credential is required to run the application.

Consequently, an exact total token cost cannot be calculated from the repository and should not be guessed. Token usage and monetary cost belong to the account/platform billing records that ran the development sessions, not to the application runtime. The project itself has no AI runtime cost, inference endpoint, or recurring model dependency.

## Known boundaries and future work

- R2 object storage requires the clone owner to create their own private bucket and server-only credentials; no credentials are included.
- Password recovery remains operator-managed.
- Partial payments, automatic notifications, direct payment providers, OCR, multi-currency, and enterprise roles remain out of scope.
- Production operators still need independent backups, restore rehearsal, rate-limit policy, monitoring, and secret rotation.

## Final handoff

The final repository is intended to be cloned and run locally first. Public mode is an optional same-machine Cloudflare Tunnel demonstration, not a managed hosting service. Before using real financial data, replace development secrets, use a managed PostgreSQL database with backups, keep the database and viewer private, and complete an independent security review.
