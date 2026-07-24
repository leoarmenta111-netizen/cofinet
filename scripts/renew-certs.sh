#!/usr/bin/env bash
set -Eeuo pipefail

script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$(dirname "$script_dir")"

env_file="${ENV_FILE:-.env.production}"
compose=(docker compose --env-file "$env_file" -f docker-compose.yml -f docker-compose.prod.yml)

echo "[$(date -Is)] Renewing TLS certificates"
"${compose[@]}" --profile certbot run --rm certbot renew
"${compose[@]}" exec nginx nginx -s reload
echo "[$(date -Is)] TLS renewal complete"

