# Plan de Implementación — HTTPS con Let's Encrypt

## Dominio: cofinet-portal.duckdns.org
## Fecha: 2026-07-18
## Entorno: Ubuntu 24.04 + Docker Compose

---

## Resumen

Migrar CofiNet+ de HTTP a HTTPS usando Let's Encrypt (Certbot) dentro de Docker.
Sin modificar la lógica del backend. Sin downtime significativo.

---

## Archivos Nuevos Creados

| Archivo | Propósito |
|---------|-----------|
| `docker-compose.ssl.yml` | Compose con HTTPS, certbot, volúmenes SSL |
| `nginx/default-ssl.conf` | Nginx con redirect HTTP→HTTPS + SSL |
| `certbot/conf/.gitkeep` | Directorio para certificados Let's Encrypt |
| `certbot/www/.gitkeep` | Directorio para ACME challenge webroot |
| `scripts/init-letsencrypt.sh` | Script para obtener certificados iniciales |
| `scripts/renew-certs.sh` | Script para renovar certificados |

## Archivos Existentes Modificados

| Archivo | Cambio |
|---------|--------|
| `backend/.env` | `FRONTEND_URL` → `https://cofinet-portal.duckdns.org` |
| `frontend/vercel.json` | `destination` → `https://cofinet-portal.duckdns.org/api/:path*` |
| `frontend/js/api.js` | Fallback localhost → `https://cofinet-portal.duckdns.org/api` |

## Archivos NO Modificados

- `docker-compose.yml` (original intacto)
- `nginx/default.conf` (original intacto)
- Todos los archivos de backend (endpoints, servicios, modelos)

---

## Pasos de Despliegue en Ubuntu

### Prerequisitos

```bash
# Verificar Docker
docker --version
docker compose version

# Verificar que el dominio resuelve
dig cofinet-portal.duckdns.org
```

### Paso 1 — Subir los archivos al VPS

```bash
# Opción A: git pull
cd /ruta/a/cofinet
git pull origin main

# Opción B: scp (si no usas git en el VPS)
scp -r docker-compose.ssl.yml nginx/default-ssl.conf scripts/ certbot/ usuario@IP:/ruta/a/cofinet/
```

### Paso 2 — Detener los contenedores actuales

```bash
cd /ruta/a/cofinet
docker compose down
```

### Paso 3 — Hacer ejecutables los scripts

```bash
chmod +x scripts/init-letsencrypt.sh
chmod +x scripts/renew-certs.sh
```

### Paso 4 — Obtener el certificado SSL

```bash
sudo bash scripts/init-letsencrypt.sh
```

Este script:
1. Crea un certificado dummy temporal
2. Arranca nginx con ese certificado
3. Ejecuta certbot para obtener el certificado real de Let's Encrypt
4. Recarga nginx con el certificado válido
5. Arranca todos los servicios

### Paso 5 — Verificar

```bash
# Verificar HTTPS
curl -I https://cofinet-portal.duckdns.org

# Verificar redirección HTTP → HTTPS
curl -I http://cofinet-portal.duckdns.org

# Verificar API
curl https://cofinet-portal.duckdns.org/api/health

# Verificar todos los contenedores
docker compose -f docker-compose.ssl.yml ps
```

### Paso 6 — Configurar renovación automática

```bash
sudo crontab -e
```

Agregar esta línea:
```
0 3 * * * /ruta/a/cofinet/scripts/renew-certs.sh >> /var/log/certbot-renew.log 2>&1
```

### Paso 7 — Redesplegar Vercel (si aplica)

Si el frontend de Vercel necesita el nuevo `vercel.json`:
```bash
cd frontend
npx vercel --prod
```

---

## Comandos Docker Útiles

```bash
# Ver logs de nginx
docker compose -f docker-compose.ssl.yml logs nginx

# Ver logs del backend
docker compose -f docker-compose.ssl.yml logs backend

# Ver logs de certbot
docker compose -f docker-compose.ssl.yml logs certbot

# Reiniciar nginx
docker compose -f docker-compose.ssl.yml restart nginx

# Ver estado de certificados
docker compose -f docker-compose.ssl.yml run --rm certbot certificates

# Forzar renovación
docker compose -f docker-compose.ssl.yml run --rm certbot renew --force-renewal
docker compose -f docker-compose.ssl.yml exec nginx nginx -s reload
```

---

## Checklist Final

- [ ] HTTPS funciona en `https://cofinet-portal.duckdns.org`
- [ ] HTTP redirige a HTTPS
- [ ] API responde en `https://cofinet-portal.duckdns.org/api/health`
- [ ] Admin carga en `https://cofinet-portal.duckdns.org/admin`
- [ ] Vercel funciona sin Mixed Content
- [ ] Compra de prueba → Mercado Pago checkout funciona
- [ ] Webhook de Mercado Pago se recibe correctamente
- [ ] Crontab de renovación configurado
- [ ] Certificado válido por ~90 días
