#!/usr/bin/env bash
set -Eeuo pipefail

environment="${1:-}"
dump_path="${2:-}"
confirmation="${3:-}"
if [[ "$environment" != "dev" && "$environment" != "qa" ]] || [[ ! -f "$dump_path" ]] || [[ "$confirmation" != "--confirm-restore" ]]; then
  echo "Usage: $0 {dev|qa} path/to/dump.{sql|dump|backup} --confirm-restore" >&2
  exit 2
fi

if [[ "$environment" == "dev" ]]; then
  env_file=.env.local; overlay=docker-compose.dev.yml
else
  env_file=.env.qa; overlay=docker-compose.qa.yml
fi

container_dump="/tmp/cofinet-restore-${RANDOM}.$(basename "$dump_path" | awk -F. '{print $NF}')"
compose=(docker compose --env-file "$env_file" -f docker-compose.yml -f "$overlay")
"${compose[@]}" stop nginx backend >/dev/null 2>&1 || true
"${compose[@]}" up -d postgres
"${compose[@]}" cp "$dump_path" "postgres:${container_dump}"
"${compose[@]}" exec -T postgres sh -c \
  'dropdb --if-exists --force -U "$POSTGRES_USER" "$POSTGRES_DB" && createdb -U "$POSTGRES_USER" "$POSTGRES_DB"'

case "$dump_path" in
  *.dump|*.backup)
    "${compose[@]}" exec -T postgres sh -c \
      'pg_restore --no-owner --no-privileges -U "$POSTGRES_USER" -d "$POSTGRES_DB" "$1"' \
      sh "$container_dump"
    ;;
  *)
    "${compose[@]}" exec -T postgres sh -c \
      'psql -v ON_ERROR_STOP=1 --single-transaction -U "$POSTGRES_USER" -d "$POSTGRES_DB" -f "$1"' \
      sh "$container_dump"
    ;;
esac

"${compose[@]}" exec -T postgres rm -f "$container_dump"
echo "Restore completed in the isolated $environment database."
