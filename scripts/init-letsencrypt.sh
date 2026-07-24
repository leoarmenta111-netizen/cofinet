#!/usr/bin/env bash

set -e

#############################################
# Configuración
#############################################

ENV_FILE="${ENV_FILE:-.env.production}"
env_value() {
    sed -n "s/^$1=//p" "$ENV_FILE" | tail -n 1
}

DOMAIN="${PUBLIC_DOMAIN:-$(env_value PUBLIC_DOMAIN)}"
EMAIL="${LETSENCRYPT_EMAIL:-$(env_value LETSENCRYPT_EMAIL)}"
STAGING="${LETSENCRYPT_STAGING:-0}"
DATA_PATH="${CERTBOT_DATA_PATH:-./certbot}"
COMPOSE_ARGS=(--env-file "$ENV_FILE" -f docker-compose.yml -f docker-compose.prod.yml --profile certbot)

if [ -z "$DOMAIN" ] || [ "$DOMAIN" = "REPLACE_ME" ] || [ -z "$EMAIL" ] || [ "$EMAIL" = "REPLACE_ME" ]; then
    echo "PUBLIC_DOMAIN and LETSENCRYPT_EMAIL must be configured in $ENV_FILE." >&2
    exit 2
fi

RSA_KEY_SIZE=4096

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

echo ""
echo "=========================================="
echo "  CofiNet+ - Inicialización Let's Encrypt"
echo "=========================================="
echo ""

#############################################
# Verificar Docker
#############################################

if ! docker info >/dev/null 2>&1; then
    echo -e "${RED}Docker no está corriendo.${NC}"
    exit 1
fi

#############################################
# Crear directorios
#############################################

mkdir -p ${DATA_PATH}/conf
mkdir -p ${DATA_PATH}/www

#############################################
# Descargar archivos SSL si no existen
#############################################

if [ ! -f "${DATA_PATH}/conf/options-ssl-nginx.conf" ] || [ ! -f "${DATA_PATH}/conf/ssl-dhparams.pem" ]; then

    echo -e "${YELLOW}Descargando parámetros SSL...${NC}"

    curl -s \
    https://raw.githubusercontent.com/certbot/certbot/master/certbot-nginx/certbot_nginx/_internal/tls_configs/options-ssl-nginx.conf \
    > ${DATA_PATH}/conf/options-ssl-nginx.conf

    curl -s \
    https://raw.githubusercontent.com/certbot/certbot/master/certbot/certbot/ssl-dhparams.pem \
    > ${DATA_PATH}/conf/ssl-dhparams.pem
fi

#############################################
# Certificado Dummy
#############################################

echo -e "${YELLOW}Creando certificado dummy...${NC}"

mkdir -p "${DATA_PATH}/conf/live/${DOMAIN}"

docker compose \
    "${COMPOSE_ARGS[@]}" \
    run --rm \
    --entrypoint "\
openssl req \
-x509 \
-nodes \
-newkey rsa:${RSA_KEY_SIZE} \
-days 1 \
-keyout '/etc/letsencrypt/live/${DOMAIN}/privkey.pem' \
-out '/etc/letsencrypt/live/${DOMAIN}/fullchain.pem' \
-subj '/CN=localhost'" \
certbot

#############################################
# Levantar nginx
#############################################

echo -e "${YELLOW}Levantando nginx...${NC}"

docker compose \
    "${COMPOSE_ARGS[@]}" \
    up --force-recreate -d nginx

sleep 5

#############################################
# Eliminar dummy
#############################################

echo -e "${YELLOW}Eliminando certificado dummy...${NC}"

docker compose \
    "${COMPOSE_ARGS[@]}" \
    run --rm \
    --entrypoint "\
rm -Rf /etc/letsencrypt/live/${DOMAIN} && \
rm -Rf /etc/letsencrypt/archive/${DOMAIN} && \
rm -f /etc/letsencrypt/renewal/${DOMAIN}.conf" \
certbot

#############################################
# Certificado real
#############################################

echo -e "${YELLOW}Solicitando certificado real...${NC}"

STAGING_ARG=""

if [ "$STAGING" != "0" ]; then
    STAGING_ARG="--staging"
fi

docker compose \
    "${COMPOSE_ARGS[@]}" \
    run --rm certbot \
    certonly \
    --webroot \
    -w /var/www/certbot \
    ${STAGING_ARG} \
    --email "${EMAIL}" \
    -d "${DOMAIN}" \
    --rsa-key-size ${RSA_KEY_SIZE} \
    --agree-tos \
    --force-renewal \
    --no-eff-email

#############################################
# Recargar nginx
#############################################

echo -e "${YELLOW}Recargando nginx...${NC}"

docker compose \
    "${COMPOSE_ARGS[@]}" \
    exec nginx nginx -s reload

#############################################
# Levantar todo
#############################################

echo -e "${YELLOW}Levantando servicios...${NC}"

docker compose \
    "${COMPOSE_ARGS[@]}" \
    up -d postgres backend nginx

echo ""
echo "=========================================="
echo " HTTPS instalado correctamente"
echo "=========================================="
echo ""
echo "Portal:"
echo "https://${DOMAIN}"
echo ""
echo "API:"
echo "https://${DOMAIN}/api/plans"
echo ""
