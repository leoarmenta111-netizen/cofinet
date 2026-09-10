# Deployment guide

Promote the same reviewed commit through local, QA, then production. Do not edit application files directly on the VPS.

## QA

```bash
docker compose --env-file .env.qa -f docker-compose.yml -f docker-compose.qa.yml config
docker compose --env-file .env.qa -f docker-compose.yml -f docker-compose.qa.yml up -d --build
docker compose --env-file .env.qa -f docker-compose.yml -f docker-compose.qa.yml --profile tools run --rm db-init
```

Restore a sanitized production dump using `RESTORE.md`, then run health, authentication, admin, PIN, sandbox-payment/webhook, and dedicated-router checks.

## Production release

First identify the current volume with `docker volume ls` and set that exact name as `POSTGRES_VOLUME_NAME`. The production overlay marks it external and will fail instead of silently creating an empty database.

```bash
docker compose --env-file .env.production -f docker-compose.yml -f docker-compose.prod.yml config
docker compose --env-file .env.production -f docker-compose.yml -f docker-compose.prod.yml build backend
docker compose --env-file .env.production -f docker-compose.yml -f docker-compose.prod.yml up -d
docker compose --env-file .env.production -f docker-compose.yml -f docker-compose.prod.yml ps
```

Run only after production gates pass. Startup does not automatically run `db-init` or schema changes.

## Rollback

Stop the new project without volumes and start the archived prior release. Never run `down -v`. Restore PostgreSQL only if an incompatible data change occurred; container rollback alone does not require database rollback.
