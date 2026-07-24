# CofiNet+

CofiNet+ is a FastAPI, PostgreSQL, Nginx, and static-frontend captive portal with Mercado Pago and MikroTik integrations. This repository keeps application behavior intact while providing isolated local, QA, and production operations.

## Quick start (Windows or Linux)

Prerequisites: Docker Desktop/Engine with Compose v2 and Git.

```bash
docker compose --env-file .env.local -f docker-compose.yml -f docker-compose.dev.yml up -d --build
docker compose --env-file .env.local -f docker-compose.yml -f docker-compose.dev.yml --profile tools run --rm db-init
```

Open `http://localhost:8080`. The API health endpoint is `http://localhost:8080/api/health`.

Stop the stack without deleting its database:

```bash
docker compose --env-file .env.local -f docker-compose.yml -f docker-compose.dev.yml down
```

Never add `-v` unless intentionally deleting that environment's database volume.

## Environment selection

| Environment | Environment file | Compose overlay | Default URL |
|---|---|---|---|
| Local | `.env.local` | `docker-compose.dev.yml` | `http://localhost:8080` |
| QA | `.env.qa` | `docker-compose.qa.yml` | `http://localhost:8081` |
| Production | `.env.production` | `docker-compose.prod.yml` | configured HTTPS domain |

Always use the shared `docker-compose.yml` plus exactly one overlay. Compose project names (`cofinet-dev`, `cofinet-qa`, `cofinet-prod`) create isolated networks and PostgreSQL volumes.

## Repository structure

```text
admin/                   Static administration panel
backend/                 FastAPI application and image definition
backups/                 Ignored local database dumps
certbot/                 Ignored ACME state and challenge directory
docs/                    Architecture and operating guides
frontend/                Static captive portal
nginx/                   Development config and production template
scripts/                 Windows/Linux backup, restore, and TLS tools
docker-compose.yml       Shared services
docker-compose.dev.yml   Local override
docker-compose.qa.yml    QA override
docker-compose.prod.yml  Production override
```

## Documentation

- [Architecture analysis](docs/ARCHITECTURE.md)
- [Development guide](docs/DEVELOPMENT.md)
- [Deployment guide](docs/DEPLOYMENT.md)
- [Production guide](docs/PRODUCTION.md)
- [Backup guide](docs/BACKUP.md)
- [Restore guide](docs/RESTORE.md)
- [Git workflow](docs/GIT_WORKFLOW.md)

The older `docker-compose.ssl.yml`, `docker-compose.backup.yml`, and Nginx configs remain temporarily for rollback compatibility. New work should use the environment overlays above; remove legacy files only after a verified production migration.
