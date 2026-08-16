# Deployment readiness

The public deployment has not been verified in this repository. Use the local flow first; it deliberately preserves the existing `backend/local-test.db` and local receipt files.

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
CORS_ORIGINS=https://app.example.com
TRUSTED_HOSTS=app.example.com
RECEIPT_DIR=/private-receipts
```

## Release checklist

1. Back up the database and confirm one restore in a non-production environment.
2. Run `alembic upgrade head` and `/api/health` against the new service.
3. Confirm HTTPS login sets a Secure HttpOnly session cookie.
4. Confirm no database, backend, or receipt directory is directly public.
5. Run the full local test suite and browser journey before moving DNS.
6. Keep Cloudflare proxy, TLS, and rate-limiting rules enabled.

Rollback means restoring the last verified container image and database backup; do not downgrade schema migrations automatically.
