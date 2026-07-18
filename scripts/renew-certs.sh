#!/bin/bash
# =============================================================
# renew-certs.sh
# Renueva los certificados Let's Encrypt y recarga nginx
#
# USO MANUAL:
#   sudo bash scripts/renew-certs.sh
#
# CRONTAB (renovación automática cada día a las 3 AM):
#   sudo crontab -e
#   0 3 * * * /ruta/a/cofinet/scripts/renew-certs.sh >> /var/log/certbot-renew.log 2>&1
# =============================================================

set -e

# Navegar al directorio del proyecto
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_DIR"

COMPOSE_FILE="docker-compose.ssl.yml"

echo "[$(date)] Iniciando renovación de certificados..."

# Intentar renovar
docker compose -f "$COMPOSE_FILE" run --rm certbot renew

# Recargar nginx para usar los nuevos certificados
docker compose -f "$COMPOSE_FILE" exec nginx nginx -s reload

echo "[$(date)] Renovación completada."
