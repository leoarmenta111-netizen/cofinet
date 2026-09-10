# Production guide

## Security and release gates

1. Store `.env.production` only on the VPS with owner-only permissions (`chmod 600`).
2. Replace every sentinel and use a random JWT secret of at least 32 characters.
3. Use least-privilege PostgreSQL and RouterOS accounts and production Mercado Pago credentials.
4. Confirm CORS, frontend, webhook, and public-domain values match the HTTPS origin.
5. Rotate any ACME/private material copied outside the VPS or committed in history.
6. Back up PostgreSQL and verify the dump before deployment.
7. Pin and record the release commit and built image digest.
8. Verify `POSTGRES_VOLUME_NAME` against `docker volume ls`; do not guess it.

## TLS initialization and renewal

The production Nginx template expects certificates at `/etc/letsencrypt/live/$PUBLIC_DOMAIN/`. Set `PUBLIC_DOMAIN` and `LETSENCRYPT_EMAIL`, test issuance with `LETSENCRYPT_STAGING=1`, then set it to `0` for the real certificate. The initialization script uses `.env.production` by default:

```bash
bash scripts/init-letsencrypt.sh
```

Renewal uses the same environment and Compose overlay:

```bash
docker compose --env-file .env.production -f docker-compose.yml -f docker-compose.prod.yml --profile certbot run --rm certbot renew
docker compose --env-file .env.production -f docker-compose.yml -f docker-compose.prod.yml exec nginx nginx -s reload
```

## Post-deploy checks

- HTTPS certificate and HTTP redirect are valid
- Containers are healthy and PostgreSQL is not host-published
- `/api/health`, portal, and admin respond
- JWT-key/session impact matches the release decision
- Mercado Pago checkout and webhook complete
- PIN creation/redemption and RouterOS authorization complete
- Error rate and logs remain normal

## Capacity path

Before thousands of users, add automated tests and CI image scanning, Alembic migrations, metrics/alerting, centralized logs, encrypted off-host backups with restore drills, PostgreSQL connection/load tuning, and an image registry. Scale backend replicas only after validating database pool limits and confirming all state is external.
