# Development guide

Docker Desktop must use Linux containers. From PowerShell, Git Bash, WSL, or Linux at the repository root:

```bash
docker compose --env-file .env.local -f docker-compose.yml -f docker-compose.dev.yml up -d --build
docker compose --env-file .env.local -f docker-compose.yml -f docker-compose.dev.yml --profile tools run --rm db-init
docker compose --env-file .env.local -f docker-compose.yml -f docker-compose.dev.yml ps
```

Backend source is bind-mounted and Uvicorn reloads on changes. Static directories are bind-mounted through the shared file. Use `http://localhost:8080`; do not open HTML files directly because the browser expects the `/api` reverse proxy.

## Common commands

```bash
docker compose --env-file .env.local -f docker-compose.yml -f docker-compose.dev.yml logs -f backend nginx postgres
docker compose --env-file .env.local -f docker-compose.yml -f docker-compose.dev.yml build --no-cache backend
docker compose --env-file .env.local -f docker-compose.yml -f docker-compose.dev.yml down
```

Edit `.env.local` only for local values. Keep Mercado Pago and MikroTik blank until testing those integrations; then use sandbox/dedicated non-production credentials.

## Local smoke checklist

- `/api/health` returns 200
- Public portal and admin assets load
- Login and `/auth/me` work
- Plans load and safe non-production flows complete
- Logs contain no secrets or tracebacks
- Restarting the stack preserves local data

