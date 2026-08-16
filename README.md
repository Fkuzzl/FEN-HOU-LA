# 分好啦 · Family & Friends Expense Splitter

A small, responsive Traditional Chinese/HKD expense splitter for family and friends.

## Run locally

The supported local Docker path is one command from PowerShell:

```powershell
.\scripts\start-local.ps1 -Build
```

Open <http://localhost:5173>. The local project is `expense_splitter_local` and uses the `expense_db` volume. Stop it with `.\scripts\stop-all.ps1`; volumes are preserved.

For a source-based local test without Docker, start the API with a fresh SQLite file and the Vite frontend:

```powershell
$env:DATABASE_URL = "sqlite:///C:/Code Project/Expense_Splitter/backend/local-test.db"
$env:JWT_SECRET = "local-only-change-me"
cd backend
alembic upgrade head
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

In a second terminal run `cd frontend; npm run dev -- --host 127.0.0.1 --port 5173`, then open <http://localhost:5173>. Registration uses an account name, display name, recovery email, and password. This local test database is separate from the public deployment.

For a full containerized stack without rebuilding, run `.\scripts\start-local.ps1`.

## Temporary online demo

The online mode uses the same Docker images but a separate project and database volume. It binds only to localhost; a Cloudflare Tunnel or another proxy is optional and configured outside this repository.

```powershell
.\scripts\start-public.ps1 -Build
```

By default it opens at <http://localhost:55173> and uses the separate `expense_splitter_public_v2_db` volume. To expose it through a temporary HTTPS tunnel, pass the origin and trusted host explicitly:

```powershell
.\scripts\start-public.ps1 -PublicOrigin https://your-temporary-host.example -TrustedHosts your-temporary-host.example -Build
```

The script automatically enables Secure cookies for HTTPS origins. No project file contains a permanent domain name.

The API is at <http://localhost:8000/docs>. Migrations can be run from `backend/` with `alembic upgrade head`.

## Switching modes and data

- Local Docker uses PostgreSQL in the `expense_db` volume.
- Temporary online mode uses PostgreSQL in the separate `expense_splitter_public_v2_db` volume.
- Switching modes never deletes either volume. Use `.\scripts\status.ps1` to inspect both projects and `.\scripts\stop-all.ps1` to stop both.
- To inspect the Docker database visually, run `docker compose up -d db db-viewer`, open <http://localhost:8080>, and use system `PostgreSQL`, server `db`, user `expense`, password `expense_dev_password`, database `expense_splitter`.
- For the SQLite file, use SQLite Browser or any SQLite viewer and open `backend/dev.db`.

## Checks

```text
cd backend && pytest
cd frontend && npm run lint && npm run build
cd frontend && npm run test:e2e  # requires the local API on :8000 and Vite app on :5173
docker compose build
```

The current slice supports unique account-name login, owner-controlled groups, named participant roles that do not require accounts, date-only bill entry, equal/fixed-per-bill splits, viewing completed event details, and creating/closing billing requests. Event details can generate an aggregated message for each person who owes money; merged multi-event settlement also generates one copyable transfer message. Each recipient now gets a copyable text message plus a generated PNG payment card that can be shared or downloaded. Groups can create 7-day invite links for registered users, and several completed events can be combined into net transfer suggestions. Bills accept one private local JPG/PNG receipt up to 10 MB; cloud object-storage adapters remain a deployment task. It does not send directly through WhatsApp/WeChat yet.

The participant/ownership schema is introduced by migration `0003_accounts_participants`. For a fresh deployment run `alembic upgrade head` before starting the API. Existing databases must be backed up first; this release intentionally treats the production database as a fresh reset and does not automatically migrate old guest-user records.
