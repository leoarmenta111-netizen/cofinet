#!/usr/bin/env bash
set -Eeuo pipefail

environment="${1:-qa}"
case "$environment" in
  dev) env_file=.env.local; overlay=docker-compose.dev.yml ;;
  qa) env_file=.env.qa; overlay=docker-compose.qa.yml ;;
  prod) env_file=.env.production; overlay=docker-compose.prod.yml ;;
  *) echo "Usage: $0 {dev|qa|prod}" >&2; exit 2 ;;
esac

timestamp="$(date -u +%Y%m%dT%H%M%SZ)"
container_dump="/tmp/cofinet-${environment}-${timestamp}.dump"
host_dump="backups/cofinet-${environment}-${timestamp}.dump"
mkdir -p backups

compose=(docker compose --env-file "$env_file" -f docker-compose.yml -f "$overlay")
"${compose[@]}" exec -T postgres sh -c \
  'pg_dump -Fc --no-owner --no-privileges -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f "$1"' \
  sh "$container_dump"
"${compose[@]}" cp "postgres:${container_dump}" "$host_dump"
"${compose[@]}" exec -T postgres rm -f "$container_dump"
echo "Backup created: $host_dump"

