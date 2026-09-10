# Administrator RBAC and dashboard redesign

## Architecture summary

Administrator authentication keeps the existing `/admin/login` token flow. Authorization is now resolved from the current `admins` row on every request, so disabling an account or changing its role takes effect without trusting a stale frontend state or token claim.

`AdminRole` provides two validated roles. Reusable FastAPI dependencies enforce permissions at the route layer. The static admin UI calls `/admin/me` before rendering protected content and builds navigation only after the backend-confirmed role is known.

Manual PINs continue to use `Purchase`. `creation_source` distinguishes `admin_cash`, `mercadopago`, and `system`; `created_by_admin_id` records the operator for manual cash PINs. No PIN format, duration, expiry, payment webhook, or MikroTik behavior changed.

## Permission matrix

| Capability | Super admin | PIN operator |
|---|---:|---:|
| Login and own profile | Yes | Yes |
| Dashboard and revenue | Yes | No (`403`) |
| Generate cash PIN | Yes | Yes |
| View cash PIN history | All audited cash PINs | Own audited PINs only |
| View active plans for PIN sale | Yes | Yes |
| Create/update/delete plans through API | Yes | No (`403`) |
| View local payment history/details | Yes | No (`403`) |
| List/create/disable administrators | Yes | No (`403`) |
| Change roles/reset passwords | Yes | No (`403`) |
| Disable or demote final active super admin | No (`409`) | No |
| Reports, settings, technical logs, MikroTik monitoring | Not implemented; marked unavailable | Hidden and forbidden |

## Database migration

Revision `20260724_0001` adds:

- `admins.role`, `updated_at`, `last_login_at`, and `created_by_admin_id`
- `purchases.creation_source` and `created_by_admin_id`
- PostgreSQL enums and supporting indexes/foreign keys

Every existing administrator is backfilled as `super_admin`. Existing purchases with Mercado Pago records are marked `mercadopago`; historical cash-like PINs without payments are marked `admin_cash`, but their creator remains unknown because that information did not previously exist.

The migration is additive and tolerates fresh databases created from current SQLAlchemy metadata.

## Local startup and migration

Use only `.env.local` and the `cofinet-dev` overlay:

```powershell
docker compose --env-file .env.local -f docker-compose.yml -f docker-compose.dev.yml up -d postgres
docker compose --env-file .env.local -f docker-compose.yml -f docker-compose.dev.yml --profile tools run --rm db-init
docker compose --env-file .env.local -f docker-compose.yml -f docker-compose.dev.yml --profile tools run --rm db-migrate
docker compose --env-file .env.local -f docker-compose.yml -f docker-compose.dev.yml up -d --build backend nginx
```

For an already initialized copied local database, `db-init` is optional; run `db-migrate` before the new backend starts.

## Local test accounts

No password or weak default account is committed. Provision accounts through the local-only CLI, which refuses to run unless `APP_ENV` is `development` or `qa` and prompts for passwords without echoing them.

First local super administrator, only when the local database has no admins:

```powershell
docker compose --env-file .env.local -f docker-compose.yml -f docker-compose.dev.yml run --rm backend python -m app.cli.create_local_admin --email owner@example.com --full-name "Local Owner" --role super_admin --confirm-super-admin
```

Subsequent local operator:

```powershell
docker compose --env-file .env.local -f docker-compose.yml -f docker-compose.dev.yml run --rm backend python -m app.cli.create_local_admin --email cashier@example.com --full-name "Local Cashier" --role pin_operator --created-by-email owner@example.com
```

If the copied database already contains an administrator, the migration makes that existing local copy a super admin; use the UI to create test operators.

## Validation commands

```powershell
docker compose --env-file .env.local -f docker-compose.yml -f docker-compose.dev.yml config
docker compose --env-file .env.local -f docker-compose.yml -f docker-compose.dev.yml --profile tools run --rm db-migrate
docker compose --env-file .env.local -f docker-compose.yml -f docker-compose.dev.yml run --rm backend pytest -q
```

Manual smoke tests:

1. Sign in with the migrated existing administrator and verify the dashboard.
2. Create a local PIN operator and sign in with it.
3. Verify direct requests to `/api/admin/dashboard`, `/api/admin/payments`, `/api/admin/accounts`, and plan mutation endpoints return `403` for the operator.
4. With a dedicated local MikroTik configured, generate one cash PIN and validate copy, print, operator audit, and customer PIN validation.
5. With MikroTik blank, verify PIN creation shows an honest unavailable message and no purchase is committed.
6. Disable the operator and verify future login returns `403`.
7. Attempt to demote/disable the final active super admin and verify `409`.

## Files created

- Alembic configuration and `20260724_0001` migration
- `admin/admin.css`, `payments.html`, `plans.html`, and `administrators.html`
- Local administrator provisioning CLI
- Backend authorization regression tests and development requirements
- This guide

## Principal files modified

- Administrator/Purchase models, schemas, security dependencies, API, and service
- Plan mutation authorization and purchase creation-source assignments
- Existing admin login, dashboard, PIN page, and shared JavaScript
- Backend Dockerfile and local tool services

## Known limitations

- Reports, settings, activity logs, charts, and live MikroTik monitoring are not implemented because no real backing data/endpoints exist.
- Historical manual PINs cannot be attributed to an administrator retroactively.
- Local PIN creation still requires explicitly configured local/dedicated MikroTik credentials; no simulated production success is returned.
- Tokens are not server-side revoked. Database role and active-state checks still make access changes effective on the next API request.

## Local rollback

Back up the local database first. Then:

```powershell
docker compose --env-file .env.local -f docker-compose.yml -f docker-compose.dev.yml --profile tools run --rm db-migrate alembic downgrade base
```

Revert the RBAC/UI commit after the schema downgrade. Downgrading removes role and audit metadata; do not run it against production without a separate approved migration plan.

## Future production deployment checklist (do not execute from local work)

- [ ] Review all code and migration changes in a pull request
- [ ] Run automated tests and manual role/403 tests in isolated QA
- [ ] Restore a sanitized production backup into QA and run the migration there
- [ ] Confirm all existing admins that should become super admins
- [ ] Configure a production backup and tested rollback window
- [ ] Verify there is always at least one active super admin
- [ ] Test payment webhook, automatic PIN creation, customer PIN validation, and dedicated MikroTik behavior unchanged
- [ ] Build and scan an immutable release image
- [ ] Schedule and approve the production migration separately
- [ ] Never use local test accounts or local secrets in production
