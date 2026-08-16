# Security notes

## Current controls

- Sessions use signed HttpOnly cookies with `SameSite=Lax`. Set `COOKIE_SECURE=true` for HTTPS deployments.
- Group-scoped endpoints require membership; group management, expenses, invites and billing requests require the owner.
- Participants are group-local roles. They can be guests and are not automatically matched to accounts.
- Completed billing requests can only transition once from pending to completed or cancelled. Completion stores the acting account and time.
- Receipt downloads require group membership. Uploads accept one JPEG or PNG up to 10 MB and only the event payer can upload.
- Authentication, group creation, invite creation and billing-request creation have a process-local per-IP rate limit. For multi-instance production, keep Cloudflare rate limiting enabled as the primary shared edge limit.

## Before public deployment

1. Create a new, random `JWT_SECRET`; never commit it.
2. Set `COOKIE_SECURE=true`, explicit `CORS_ORIGINS`, and explicit `TRUSTED_HOSTS` for the public hostname.
3. Use PostgreSQL with automated backups. Do not expose its port or an admin UI publicly.
4. Put the frontend/API behind HTTPS and Cloudflare proxying. Restrict the host firewall to the reverse proxy.
5. Move receipts to a private object-storage adapter before relying on hosted uploads; the current local receipt directory is only suitable for local testing.

Password recovery is intentionally operator-managed. Do not add a reset endpoint until an authenticated email delivery provider and an audit trail are configured.
