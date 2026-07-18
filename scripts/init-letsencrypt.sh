#!/bin/bash
# =============================================================
# init-letsencrypt.sh
# Obtiene el primer certificado Let's Encrypt para CofiNet+
#
# USO:
#   chmod +x scripts/init-letsencrypt.sh
#   sudo bash scripts/init-letsencrypt.sh
#
# Este script:
#   1. Crea un certificado dummy para que nginx pueda arrancar
#   2. Arranca nginx
#   3. Ejecuta certbot para obtener el certificado real
#   4. Recarga nginx con el certificado válido
# =============================================================

set -e

# ---- Configuración ----
DOMAIN="cofinet-portal.duckdns.org"
EMAIL="leoarmenta111@gmail.com"
DATA_PATH="./certbot"
COMPOSE_FILE="docker-compose.ssl.yml"
RSA_KEY_SIZE=4096
STAGING=0  # Cambiar a 1 para pruebas (evita rate limits de Let's Encrypt)

# ---- Colores ----
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m' # No Color

echo ""
echo -e "${GREEN}==========================================${NC}"
echo -e "${GREEN}  CofiNet+ — Inicialización Let's Encrypt ${NC}"
echo -e "${GREEN}==========================================${NC}"
echo ""

# ---- Verificar que Docker está corriendo ----
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}Error: Docker no está corriendo. Ejecuta: sudo systemctl start docker${NC}"
    exit 1
fi

# ---- Verificar que el dominio resuelve ----
echo -e "${YELLOW}► Verificando DNS para ${DOMAIN}...${NC}"
if ! host "$DOMAIN" > /dev/null 2>&1 && ! dig +short "$DOMAIN" > /dev/null 2>&1; then
    echo -e "${YELLOW}  Advertencia: No se pudo verificar DNS. Continuando de todos modos...${NC}"
else
    echo -e "${GREEN}  ✔ DNS resuelve correctamente${NC}"
fi

# ---- Crear directorios ----
echo -e "${YELLOW}► Creando directorios...${NC}"
mkdir -p "$DATA_PATH/conf"
mkdir -p "$DATA_PATH/www"
echo -e "${GREEN}  ✔ Directorios creados${NC}"

# ---- Descargar parámetros SSL recomendados ----
if [ ! -e "$DATA_PATH/conf/options-ssl-nginx.conf" ] || [ ! -e "$DATA_PATH/conf/ssl-dhparams.pem" ]; then
    echo -e "${YELLOW}► Descargando parámetros SSL recomendados...${NC}"
    curl -s https://raw.githubusercontent.com/certbot/certbot/master/certbot-nginx/certbot_nginx/_internal/tls_configs/options-ssl-nginx.conf > "$DATA_PATH/conf/options-ssl-nginx.conf"
    curl -s https://raw.githubusercontent.com/certbot/certbot/master/certbot/certbot/ssl-dhparams.pem > "$DATA_PATH/conf/ssl-dhparams.pem"
    echo -e "${GREEN}  ✔ Parámetros SSL descargados${NC}"
fi

# ---- Crear certificado dummy ----
CERT_PATH="/etc/letsencrypt/live/$DOMAIN"
echo -e "${YELLOW}► Creando certificado temporal (dummy)...${NC}"
mkdir -p "$DATA_PATH/conf/live/$DOMAIN"
docker compose --env-file backend/.env -f "$COMPOSE_FILE" run --rm --entrypoint "\
    openssl req -x509 -nodes -newkey rsa:$RSA_KEY_SIZE -days 1 \
    -keyout '$CERT_PATH/privkey.pem' \
    -out '$CERT_PATH/fullchain.pem' \
    -subj '/CN=localhost'" certbot
echo -e "${GREEN}  ✔ Certificado dummy creado${NC}"

# ---- Arrancar nginx ----
echo -e "${YELLOW}► Arrancando nginx...${NC}"
docker compose --env-file backend/.env -f "$COMPOSE_FILE" up --force-recreate -d nginx
echo -e "${GREEN}  ✔ Nginx arrancado${NC}"

# ---- Esperar a que nginx esté listo ----
echo -e "${YELLOW}► Esperando a que nginx esté listo...${NC}"
sleep 5

# ---- Eliminar certificado dummy ----
echo -e "${YELLOW}► Eliminando certificado temporal...${NC}"
docker compose --env-file backend/.env -f "$COMPOSE_FILE" run --rm --entrypoint "\
rm -rf /etc/letsencrypt/live/$DOMAIN && \
rm -rf /etc/letsencrypt/archive/$DOMAIN && \
rm -rf /etc/letsencrypt/renewal/$DOMAIN.conf" certbot
echo -e "${GREEN}  ✔ Certificado temporal eliminado${NC}"

# ---- Solicitar certificado real ----
echo -e "${YELLOW}► Solicitando certificado Let's Encrypt...${NC}"
echo ""

# Determinar si usar staging
STAGING_ARG=""
if [ $STAGING != "0" ]; then
    STAGING_ARG="--staging"
    echo -e "${YELLOW}  ⚠ Modo STAGING activado (certificado de prueba)${NC}"
fi

docker compose --env-file backend/.env -f "$COMPOSE_FILE" run --rm certbot \
    certonly --webroot \
    -w /var/www/certbot \
    $STAGING_ARG \
    --email "$EMAIL" \
    --domain "$DOMAIN" \
    --rsa-key-size "$RSA_KEY_SIZE" \
    --agree-tos \
    --no-eff-email \
    --force-renewal

echo ""
echo -e "${GREEN}  ✔ Certificado Let's Encrypt obtenido${NC}"

# ---- Recargar nginx con certificado real ----
echo -e "${YELLOW}► Recargando nginx con certificado válido...${NC}"
docker compose --env-file backend/.env -f "$COMPOSE_FILE" exec nginx nginx -s reloadecho -e "${GREEN}  ✔ Nginx recargado${NC}"

# ---- Arrancar todos los servicios ----
echo -e "${YELLOW}► Arrancando todos los servicios...${NC}"
docker compose --env-file backend/.env -f "$COMPOSE_FILE" up -d
echo -e "${GREEN}  ✔ Todos los servicios arrancados${NC}"

echo ""
echo -e "${GREEN}==========================================${NC}"
echo -e "${GREEN}  ✔ HTTPS configurado exitosamente       ${NC}"
echo -e "${GREEN}==========================================${NC}"
echo ""
echo -e "  Portal:  ${GREEN}https://$DOMAIN${NC}"
echo -e "  API:     ${GREEN}https://$DOMAIN/api/health${NC}"
echo -e "  Admin:   ${GREEN}https://$DOMAIN/admin${NC}"
echo ""
echo -e "${YELLOW}SIGUIENTE PASO:${NC}"
echo -e "  Configura la renovación automática:"
echo -e "  ${GREEN}sudo crontab -e${NC}"
echo -e "  Agrega esta línea:"
echo -e "  ${GREEN}0 3 * * * $(pwd)/scripts/renew-certs.sh >> /var/log/certbot-renew.log 2>&1${NC}"
echo ""
