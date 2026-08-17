# Deployment readiness

The repository supports two reversible Docker modes. Local mode uses `expense_splitter_local` and the `expense_db` volume. Temporary online-demo mode uses `expense_splitter_public` and the separate `expense_splitter_public_v2_db` volume. Neither switch deletes volumes.

```powershell
.\scripts\start-local.ps1 -Build
.\scripts\start-public.ps1 -PublicOrigin https://your-temporary-host.example -TrustedHosts your-temporary-host.example -Build
.\scripts\status.ps1
.\scripts\stop-all.ps1
```

The public-demo container stack has been verified locally. External reachability depends on the separately managed tunnel or proxy. The repository includes a temporary Quick Tunnel workflow for verification; use a named, persistent tunnel for anything beyond a short demo.

## Environment files and R2

Local startup explicitly loads `.env.local` (falling back to `.env` for older checkouts). Public startup explicitly loads `.env.public` and refuses to read the local file. Copy the templates before starting:

```powershell
Copy-Item .env.example .env.local
Copy-Item .env.public.example .env.public
```

Local Docker uses the internal PostgreSQL hostname `db`; do not put a `localhost` database URL into the container's `DATABASE_URL`. The local compose file supplies the Docker database URL and local defaults. Public mode uses a separate database volume and requires a different JWT secret.

For hosted receipt persistence, create a private Cloudflare R2 bucket and a bucket-scoped API token with Object Read & Write. Put these values only in `.env.public`:

```text
STORAGE_PROVIDER=r2
R2_ENDPOINT=https://<cloudflare-account-id>.r2.cloudflarestorage.com
R2_ACCESS_KEY_ID=<server-only-access-key>
R2_SECRET_ACCESS_KEY=<server-only-secret>
R2_BUCKET=<private-bucket-name>
```

Never enable public bucket access and never place these values in frontend code, Git, or a browser-visible environment. Local mode can keep `STORAGE_PROVIDER=local`; use a separate R2 bucket/token if you need to test R2 locally.

## Fresh production database

Production starts from an empty database. Apply migrations on release:

```bash
cd backend
alembic upgrade head
```

The existing local SQLite development database was created before migrations were introduced. Do not run the migration command against it without first backing it up and planning its migration.

## Required production environment

```text
DATABASE_URL=postgresql+psycopg://...
JWT_SECRET=<long-random-secret>
COOKIE_SECURE=true
CORS_ORIGINS=https://temporary-host.example
TRUSTED_HOSTS=temporary-host.example
RECEIPT_DIR=/private-receipts
STORAGE_PROVIDER=r2
R2_ENDPOINT=https://<account-id>.r2.cloudflarestorage.com
R2_ACCESS_KEY_ID=<server-only-access-key>
R2_SECRET_ACCESS_KEY=<server-only-secret>
R2_BUCKET=<private-bucket-name>
```

## Release checklist

1. Back up the database and confirm one restore in a non-production environment.
2. Run `alembic upgrade head` and `/api/health` against the new service.
3. Confirm HTTPS login sets a Secure HttpOnly session cookie.
4. Confirm no database, backend, or receipt directory/bucket is directly public. R2 credentials must exist only in backend environment variables.
5. Run the full local test suite and browser journey before moving DNS.
6. Keep Cloudflare proxy, TLS, and rate-limiting rules enabled.

Rollback means restoring the last verified container image and database backup; do not downgrade schema migrations automatically.
