# FEN HOU LA — Family & Friends Expense Splitter

FEN HOU LA (分好啦) is a Traditional Chinese, HKD-first web application for recording shared bills, splitting exact amounts, and creating copy/share payment messages. Participants can be named people without accounts; only the group owner can edit or share financial records. Registered members can view group events and bill details.

The repository runs locally with Docker and can be exposed through a separately managed Cloudflare Tunnel for a private public demo. It contains no production credentials, user data, or permanent domain.

## Features

- Account-name login with Argon2 password hashing and HttpOnly cookie sessions.
- Owner-controlled groups, invitations, participant roles, and safe member access.
- Date-only bills with HKD cent-accurate equal, fixed, and percentage allocations.
- Completed event history with per-person totals and recipient-specific billing messages.
- Copyable text and PNG invoice-style cards; browser print/share is client-side.
- Private JPEG/PNG receipt validation (10 MB limit) through a provider-independent storage boundary.
- Manual billing-request completion and immutable completed events.
- No-code operator workbench for account status, group archival, health counts, and audit logs.

## Requirements

- Windows PowerShell (scripts are `.ps1`), Docker Desktop with Compose, and Git.
- Node.js 22+ and Python 3.12+ only for checks outside containers.

## Local Docker setup

1. Clone the repository:

   ```powershell
   git clone https://github.com/Fkuzzl/FEN-HOU-LA.git
   cd FEN-HOU-LA
   ```

2. Create the private environment file:

   ```powershell
   Copy-Item .env.example .env.local
   ```

   Change `JWT_SECRET` to a long random value. Keep `.env.local` private; it is ignored by Git. The default local PostgreSQL password is for development only. For backwards compatibility, the script also accepts `.env` when `.env.local` does not exist.

3. Start the complete stack:

   ```powershell
   .\scripts\start-local.ps1 -Build
   ```

   Open [http://localhost:5173](http://localhost:5173). The API health check is [http://localhost:8000/api/health](http://localhost:8000/api/health). Migrations run automatically for Docker PostgreSQL.

   Stop containers without deleting data:

   ```powershell
   .\scripts\stop-all.ps1
   .\scripts\status.ps1
   ```

The local database is stored in the Docker volume `expense_db`. To inspect it, run `docker compose --env-file .env.local up -d db db-viewer` and open [http://localhost:8080](http://localhost:8080). Use server `db`, database `expense_splitter`, user `expense`, and the password from the local compose file. Never expose this viewer publicly.

## Public/demo mode through Cloudflare Tunnel

This mode remains hosted by your machine; Cloudflare provides the public HTTPS edge. It uses a separate PostgreSQL volume and never reuses local data.

1. In Cloudflare Zero Trust, create a named tunnel and run its connector on the same machine as Docker.
2. Add a public hostname such as `app.example.com` and route it to `http://host.docker.internal:55173` (the local binding printed by the script). Keep the database, API port, and Adminer private.
3. Copy the public environment template and set a fresh secret:

   ```powershell
   Copy-Item .env.public.example .env.public
   ```

4. Start the isolated public stack:

   ```powershell
   .\scripts\start-public.ps1 -PublicOrigin https://app.example.com -TrustedHosts app.example.com -Build
   ```

Verify `https://app.example.com/api/health`. The public script explicitly loads `.env.public` and never reads `.env.local` or `.env`. It binds the public frontend to localhost only and enables secure cookies for HTTPS. A Quick Tunnel URL is suitable only for short-lived testing; use a persistent connector for a real demo. Never commit tunnel credentials, R2 keys, admin passwords, or environment files.

## Cloudflare R2 receipts

Local mode defaults to `STORAGE_PROVIDER=local`; receipts stay in the backend's private local storage and are not public URLs. Public mode supports a private R2 bucket. R2 is optional for a basic demo, but required if public receipt uploads must survive container replacement.

1. In Cloudflare, open **R2 Object Storage → Create bucket** and create a private bucket, such as `fen-hou-la-receipts-public`. Do not enable public bucket access.
2. Open **R2 → Manage R2 API Tokens → Create API token**. Grant **Object Read & Write** only for this bucket. Copy the access key ID and secret once; the secret cannot be recovered later.
3. Use this S3-compatible endpoint:

   ```text
   https://<cloudflare-account-id>.r2.cloudflarestorage.com
   ```

4. Put the values only in the private `.env.public` file:

   ```text
   STORAGE_PROVIDER=r2
   R2_ENDPOINT=https://<cloudflare-account-id>.r2.cloudflarestorage.com
   R2_ACCESS_KEY_ID=<server-only-access-key>
   R2_SECRET_ACCESS_KEY=<server-only-secret>
   R2_BUCKET=fen-hou-la-receipts-public
   ```

   The backend uses these credentials server-side through its storage adapter; they are never sent to the browser. Use a separate bucket and token for local R2 testing, or leave local storage enabled.

5. Restart public mode and test one editable event receipt. Verify an authorized group member can download it and that the bucket has no public URL access.

## Operator workbench

Set `ADMIN_USERNAME`, `ADMIN_NAME`, `ADMIN_EMAIL`, and `ADMIN_PASSWORD` in the private environment file before startup. Sign in through the normal application to open the management workbench. It can disable/enable non-admin accounts and archive groups, with confirmation dialogs and immutable audit records. The administrator cannot disable itself. Use a unique random password and rotate it outside the repository.

## Development checks

```powershell
cd backend
python -m pytest -q --basetemp .pytest-tmp
cd ..\frontend
npm.cmd run lint
npm.cmd run build
npm.cmd run test:e2e
```

The E2E flow expects the local API and frontend to be running. CI runs backend, frontend, and E2E checks. See [SECURITY.md](SECURITY.md), [ARCHITECTURE.md](ARCHITECTURE.md), and [DEPLOYMENT.md](DEPLOYMENT.md) for operational details.

## Data and reset warning

Local and public modes intentionally use separate Docker volumes. Removing a volume permanently deletes its database; export or back it up first. A fresh production deployment must start from an empty database and apply all Alembic migrations. Completed financial records are immutable by design.

## License and contributions

This is an experimental open-source project. Do not use it as a payment processor or financial ledger without independent security, backup, and compliance review. Contributions should preserve cent-safe calculations, group authorization boundaries, and secret-free commits.
