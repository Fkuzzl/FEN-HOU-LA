# 分好啦 · Family & Friends Expense Splitter

A small, responsive Traditional Chinese/HKD expense splitter for family and friends.

## Run locally

1. Copy `.env.example` to `.env` and adjust secrets if needed.
2. Start PostgreSQL and the API: `docker compose up --build db backend`.
3. Run the Vite app from `frontend/`: `npm install`, then `npm run dev`.
4. Open <http://localhost:5173>.

For a full containerized stack, run `docker compose up --build` and open <http://localhost:5173>.

## Public demo stack

To run an isolated public-test instance without touching the normal local database, set a one-time secret and start the separate Compose project:

```powershell
$env:PUBLIC_JWT_SECRET = "generate-a-long-random-value"
docker compose -p expense_splitter_public -f docker-compose.yml -f docker-compose.public.yml up -d --build
```

The public override uses a separate PostgreSQL volume, keeps PostgreSQL/Adminer/FastAPI private to the Docker network, and exposes only the frontend on `127.0.0.1:55173`. A Cloudflare Tunnel can then publish that single frontend port. This is for testing; a named tunnel and propagated Cloudflare DNS should be used for a persistent production URL.

The API is at <http://localhost:8000/docs>. Migrations can be run from `backend/` with `alembic upgrade head`.

## Where the data is stored

- The currently running local API uses SQLite at `backend/dev.db` when started with `DATABASE_URL=sqlite:///C:/Code Project/Expense_Splitter/backend/dev.db`.
- Docker Compose uses PostgreSQL in the named Docker volume `expense_splitter_expense_db` (the `db` service), so the data survives container restarts.
- To inspect the Docker database visually, run `docker compose up -d db db-viewer`, open <http://localhost:8080>, and use system `PostgreSQL`, server `db`, user `expense`, password `expense_dev_password`, database `expense_splitter`.
- For the SQLite file, use SQLite Browser or any SQLite viewer and open `backend/dev.db`.

## Checks

```text
cd backend && pytest
cd frontend && npm run lint && npm run build
docker compose build
```

The current slice also supports adding group-only friends who do not need an account, date-only bill entry, equal/percentage/fixed-per-bill splits, viewing completed event details, and creating/closing billing requests. Event details can generate an aggregated message for each person who owes money; each message can be copied, shared with the browser's native share sheet, or printed/saved as PDF. Groups can create 7-day invite links for registered users, and several completed events can be combined into net transfer suggestions. It does not send directly through WhatsApp/WeChat yet. Production uses hosted PostgreSQL (for example Neon), a separately configured frontend/API deployment, and private object storage for receipts. Receipt upload is intentionally not enabled yet; the API retains receipt metadata for the next phase.
