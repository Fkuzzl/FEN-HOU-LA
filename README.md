# 分好啦 · Family & Friends Expense Splitter

A small, responsive Traditional Chinese/HKD expense splitter for family and friends.

## Run locally

1. Copy `.env.example` to `.env` and adjust secrets if needed.
2. Start PostgreSQL and the API: `docker compose up --build db backend`.
3. Run the Vite app from `frontend/`: `npm install`, then `npm run dev`.
4. Open <http://localhost:5173>.

For a source-based local test without Docker, start the API with a fresh SQLite file and the Vite frontend:

```powershell
$env:DATABASE_URL = "sqlite:///C:/Code Project/Expense_Splitter/backend/local-test.db"
$env:JWT_SECRET = "local-only-change-me"
cd backend
alembic upgrade head
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

In a second terminal run `cd frontend; npm run dev -- --host 127.0.0.1 --port 5173`, then open <http://localhost:5173>. Registration uses an account name, display name, recovery email, and password. This local test database is separate from the public deployment.

For a full containerized stack, run `docker compose up --build` and open <http://localhost:5173>.

## Public demo stack

To run an isolated public-test instance without touching the normal local database, set a one-time secret and start the separate Compose project:

```powershell
$env:PUBLIC_JWT_SECRET = "generate-a-long-random-value"
docker compose -p expense_splitter_public -f docker-compose.yml -f docker-compose.public.yml up -d --build
```

The public override uses a separate PostgreSQL volume, keeps PostgreSQL/Adminer/FastAPI private to the Docker network, and exposes only the frontend on `127.0.0.1:55173`. If the Cloudflare Tunnel connector is running, it can publish that frontend at `https://app.99696699.xyz`; tunnel availability is not guaranteed by this repository.

The API is at <http://localhost:8000/docs>. Migrations can be run from `backend/` with `alembic upgrade head`.

## Where the data is stored

- The local API uses whichever SQLite file is supplied in `DATABASE_URL` (the current local command uses `backend/local-test.db`).
- Docker Compose uses PostgreSQL in the named Docker volume `expense_splitter_expense_db` (the `db` service), so the data survives container restarts.
- To inspect the Docker database visually, run `docker compose up -d db db-viewer`, open <http://localhost:8080>, and use system `PostgreSQL`, server `db`, user `expense`, password `expense_dev_password`, database `expense_splitter`.
- For the SQLite file, use SQLite Browser or any SQLite viewer and open `backend/dev.db`.

## Checks

```text
cd backend && pytest
cd frontend && npm run lint && npm run build
cd frontend && npm run test:e2e  # requires the local API on :8000 and Vite app on :5173
docker compose build
```

The current slice supports unique account-name login, owner-controlled groups, named participant roles that do not require accounts, date-only bill entry, equal/fixed-per-bill splits, viewing completed event details, and creating/closing billing requests. Event details can generate an aggregated message for each person who owes money; merged multi-event settlement also generates one copyable transfer message. Each recipient now gets a copyable text message plus a generated PNG payment card that can be shared or downloaded. Groups can create 7-day invite links for registered users, and several completed events can be combined into net transfer suggestions. Bills accept one private local JPG/PNG receipt up to 10 MB; cloud object-storage adapters remain a deployment task. It does not send directly through WhatsApp/WeChat yet. Production uses hosted PostgreSQL, a separately configured frontend/API deployment, and private object storage for receipts.

The participant/ownership schema is introduced by migration `0003_accounts_participants`. For a fresh deployment run `alembic upgrade head` before starting the API. Existing databases must be backed up first; this release intentionally treats the production database as a fresh reset and does not automatically migrate old guest-user records.
