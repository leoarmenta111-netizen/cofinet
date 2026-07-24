# Architecture analysis and migration plan

## Current architecture

Browser traffic terminates at Nginx, which serves `frontend/` and `admin/` and proxies `/api/*` to FastAPI. FastAPI connects to PostgreSQL and calls Mercado Pago and RouterOS. PostgreSQL persists in a named Docker volume; Certbot state is bind-mounted from the host.

No API contracts, routes, payment flow, PIN generation, MikroTik behavior, models, or frontend design are changed by this operational migration.

## Current problems

1. Local, QA, and production shared a Compose shape, service names, and implicit configuration, creating collision and wrong-environment risk.
2. `backend/.env` was used both by the application and indirectly by Compose interpolation, making variable provenance unclear.
3. The JWT signing key and CORS origins were hardcoded. The database settings were assembled separately from application settings.
4. Nginx depended only on container start, not backend readiness. Nginx and backend had no healthchecks.
5. The backend image ran as root, used two dependency-install layers, and had no dedicated development target.
6. Live ACME account material and generated Python bytecode exist in the working tree; bytecode is already tracked in Git.
7. `.gitignore` contained unresolved merge markers. The root requirements file is malformed and duplicates backend dependency ownership.
8. There was no guarded, cross-platform database backup/restore workflow.
9. Schema creation and ad-hoc alteration live in `init_db.py`; Alembic is installed but no migration history is present.
10. Documentation described a single production path and did not define QA, rollback gates, or secret handling.

## Proposed architecture

```text
Browser -> Nginx (static + /api) -> FastAPI -> Mercado Pago / MikroTik
                                      |
                               internal DB network
                                      |
                            PostgreSQL named volume
```

The base Compose file defines invariant services. One overlay selects environment behavior and an explicit project name. Each project receives separate networks and volumes. Only Nginx publishes application ports; PostgreSQL is published to loopback in local development only. QA and production do not expose PostgreSQL.

## Files added

- Environment examples and ignored local/QA/production files
- Development, QA, and production Compose overlays
- Development Nginx config and production template
- Windows and Linux backup/restore scripts
- `backups/`, `.dockerignore`, `.gitattributes`, and `docs/`

## Files modified

- `docker-compose.yml`: shared healthy service graph
- `backend/Dockerfile`: wheel builder, non-root runtime, reload development target
- Backend configuration/session/security/main: centralized operational settings
- `frontend/js/api.js`: same-origin proxy in every environment
- `.gitignore` and `README.md`

## Step-by-step migration

1. Create a migration branch from the exact production commit and preserve current VPS Compose files as a release artifact.
2. Review and commit existing application work separately from this infrastructure migration.
3. Generate unique QA secrets, configure sandbox payment credentials, and use a non-production MikroTik account/router.
4. Start local, run `db-init` once, and complete the local development checklist.
5. Restore a sanitized production dump into isolated QA and run contract/integration smoke tests.
6. Build production from the immutable release commit and record the image digest.
7. Back up production PostgreSQL and verify the dump with `pg_restore --list`.
8. Prepare `.env.production`; decide whether a JWT-key change and forced re-login are acceptable. Never deploy a placeholder.
9. Identify the existing VPS volume and set `POSTGRES_VOLUME_NAME`; the production overlay treats it as external and cannot create an empty replacement silently.
10. Validate rendered Compose/Nginx config, then deploy in a maintenance window without deleting the existing volume.
11. Verify health, login, PIN, payment webhook, portal, admin, and MikroTik authorization.
12. Retain legacy Compose files for one release, then remove them after rollback expiry.

## Rollback plan

1. Stop only the new `cofinet-prod` project; never use `down -v`.
2. Start the preserved legacy Compose release with its original environment and Nginx config.
3. This change runs no automatic schema migration. Future schema changes require a tested downgrade.
4. Verify `/api/health`, login, one read-only admin operation, and logs.
5. Restore a database backup only if data is corrupt or an incompatible migration actually ran.

## Risk analysis

| Risk | Impact | Mitigation |
|---|---|---|
| Wrong environment credentials | Critical | Unique env files, project names, volumes, deployment checklist |
| Accidental production restore | Critical | Restore scripts accept only dev/QA and require confirmation |
| JWT change logs users out | Medium | Explicit pre-deploy decision and communication |
| Payment/webhook regression | Critical | Sandbox QA test and stable API paths |
| QA RouterOS hits production | Critical | Dedicated QA account/router and blank defaults |
| PostgreSQL data loss | Critical | Verified backup; never `down -v`; no automatic restore |
| TLS template mismatch | High | Render/test before cutover; preserve legacy config |
| Dirty working tree mixes releases | High | Separate application and infrastructure commits |
| Certificate material enters Git | Critical | Ignore ACME state, rotate exposed credentials, audit history |
| Ad-hoc schema initialization drifts | High | Manual tool profile now; reviewed Alembic revisions later |

## Final checklist

- [ ] Existing business-logic changes are committed separately
- [ ] No env file, dump, certificate, private key, or ACME account is tracked
- [ ] Unique secrets exist for local, QA, and production
- [ ] `docker compose config` passes for all overlays
- [ ] Local and QA services become healthy
- [ ] Production dump restores successfully into QA
- [ ] API contract and integration smoke tests pass in QA
- [ ] Production backup is recent and verified
- [ ] Image digest and release commit are recorded
- [ ] Rollback commands and on-call owner are confirmed
- [ ] Production health, payment, PIN, admin, portal, and MikroTik checks pass
