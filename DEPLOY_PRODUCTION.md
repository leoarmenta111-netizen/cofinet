# Despliegue de CofiNet+ en producción

Esta guía prepara el despliegue; no autoriza conectarse ni ejecutar comandos en producción desde el entorno de desarrollo. El repositorio real usa `/opt/cofinet`, `.env.production`, `docker-compose.yml` y `docker-compose.prod.yml`. No usa `backend/.env` para Compose.

Defina una vez el comando para evitar diferencias entre pasos:

```bash
cd /opt/cofinet
COMPOSE='docker compose --env-file .env.production -f docker-compose.yml -f docker-compose.prod.yml'
```

## Pre-despliegue

```bash
cd /opt/cofinet
git status --short --branch
git fetch --prune origin
git rev-parse HEAD
git tag -a "pre-cofinet-$(date +%Y%m%d-%H%M%S)" -m "Estado anterior al despliegue"
docker compose --env-file .env.production -f docker-compose.yml -f docker-compose.prod.yml ps
df -h / /var/lib/docker
test -f .env.production && stat -c '%A %U:%G %n' .env.production
grep -E '^[A-Z][A-Z0-9_]*=' .env.production | cut -d= -f1 | sort
mkdir -p backups
docker compose --env-file .env.production -f docker-compose.yml -f docker-compose.prod.yml exec -T postgres sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > "backups/cofinet-$(date +%Y%m%d-%H%M%S).dump"
test -s "$(ls -1t backups/cofinet-*.dump | head -n1)"
```

El `grep` anterior muestra únicamente nombres de variables. Confirme permisos `600` para `.env.production`, la rama/commit aprobados y que `POSTGRES_VOLUME_NAME` corresponde al volumen existente (`docker volume ls`) sin imprimir secretos.

Valide la configuración antes de construir:

```bash
$COMPOSE config --quiet
$COMPOSE --profile tools run --rm db-migrate alembic heads
$COMPOSE --profile tools run --rm db-migrate alembic current
```

El cambio de catálogo no requiere migración nueva. Las migraciones ya incluidas llegan hasta `20260724_0002`; ejecute `upgrade head` solamente si `current` no coincide con `heads` y la migración pendiente fue revisada.

## Despliegue

Use la rama de release ya revisada o el commit aprobado. En el flujo normal, ese commit debe estar integrado en `main`:

```bash
cd /opt/cofinet
git switch main
git pull --ff-only origin main
$COMPOSE config --quiet
$COMPOSE build backend
$COMPOSE --profile tools run --rm db-migrate alembic current
# Solo si current no coincide con heads:
$COMPOSE --profile tools run --rm db-migrate alembic upgrade head
$COMPOSE up -d --no-deps backend
$COMPOSE up -d nginx
```

No ejecute `docker compose down -v`, no elimine el volumen PostgreSQL y no ejecute `db-init` sobre una base existente. Construir antes de recrear los servicios minimiza la interrupción.

## Posdespliegue

```bash
$COMPOSE ps
$COMPOSE logs --since=10m --no-log-prefix backend nginx
curl -fsS https://SU_DOMINIO/api/health
curl -fsS https://SU_DOMINIO/api/plans
```

Pruebe login administrativo desde `/admin/login.html`. Para pruebas API sin dejar contraseñas en el historial, capture el token con entrada oculta:

```bash
read -r -p 'Email super admin: ' ADMIN_EMAIL
read -r -s -p 'Password: ' ADMIN_PASSWORD; printf '\n'
SUPER_TOKEN=$(curl -fsS -X POST https://SU_DOMINIO/api/admin/login -H 'Content-Type: application/json' --data "$(jq -n --arg email "$ADMIN_EMAIL" --arg password "$ADMIN_PASSWORD" '{email:$email,password:$password}')" | jq -r .access_token)
unset ADMIN_PASSWORD
curl -fsS https://SU_DOMINIO/api/admin/me -H "Authorization: Bearer $SUPER_TOKEN"
curl -fsS -X PATCH https://SU_DOMINIO/api/admin/plans/PLAN_ID -H "Authorization: Bearer $SUPER_TOKEN" -H 'Content-Type: application/json' -d '{"price":26.00,"duration_minutes":30}'
```

Repita el `PATCH` con token de operador normal y confirme HTTP `403`; sin token debe devolver `401`. Restaure cualquier valor temporal desde el panel.

Después de generar un PIN real de prueba:

```bash
curl -fsS -X POST https://SU_DOMINIO/api/pins/validate -H 'Content-Type: application/json' -d '{"pin":"PIN_GENERADO"}'
$COMPOSE exec backend python scripts/verify_production_pin.py PIN_GENERADO
$COMPOSE exec backend python scripts/verify_production_pin.py 654321
```

La validación pública debe incluir `"valid": true`. Revise en la salida de diagnóstico compra, estado, plan, importe, fechas, perfil, `limit-uptime`, y si existe una sesión, IP/MAC/uptime. El script solo ejecuta lecturas.

## Rollback

Identifique primero el tag creado en pre-despliegue y conserve el respaldo:

```bash
cd /opt/cofinet
git tag --list 'pre-cofinet-*' --sort=-creatordate | head
git switch --detach TAG_PREVIO_VERIFICADO
$COMPOSE config --quiet
$COMPOSE build backend
$COMPOSE up -d --no-deps backend
$COMPOSE up -d nginx
$COMPOSE ps
curl -fsS https://SU_DOMINIO/api/health
```

Este cambio no agrega migración, por lo que el rollback normal no restaura PostgreSQL y conserva compras/PIN existentes. Restaure la base únicamente si una migración incompatible distinta se ejecutó y después de confirmar el impacto. Operación excepcional:

```bash
BACKUP=backups/ARCHIVO_VERIFICADO.dump
test -s "$BACKUP"
$COMPOSE exec -T postgres sh -c 'pg_restore --list >/dev/null' < "$BACKUP"
# Ventana de mantenimiento y aprobación explícita obligatorias antes de restaurar:
$COMPOSE exec -T postgres sh -c 'pg_restore --clean --if-exists --no-owner -U "$POSTGRES_USER" -d "$POSTGRES_DB"' < "$BACKUP"
$COMPOSE up -d backend nginx
$COMPOSE ps
curl -fsS https://SU_DOMINIO/api/health
```

Nunca use `down -v` ni borre volúmenes durante rollback.

## Checklist manual de producción

### Prueba de permisos

1. Iniciar sesión como administrador normal.
2. Confirmar que puede ver planes.
3. Confirmar que no puede editarlos.
4. Intentar llamar al endpoint y confirmar 403.

### Prueba de super admin

5. Iniciar sesión como super admin.
6. Cambiar Express de $25 a $26.
7. Confirmar que se actualiza la tarjeta.
8. Recargar y confirmar persistencia.
9. Regresar Express a $25.

### Prueba de duración

10. Cambiar temporalmente Express de 30 a 31 minutos.
11. Generar un PIN de efectivo.
12. Confirmar el registro en PostgreSQL.
13. Confirmar `issued_at`.
14. Confirmar `expires_at` cercano a 31 minutos después.
15. Confirmar plan asociado.
16. Confirmar usuario en MikroTik.
17. Confirmar `limit_uptime=31m`.
18. Validar el PIN desde `/api/pins/validate`.
19. Probar el PIN desde un dispositivo conectado al Hotspot.
20. Verificar que aparece en `/ip/hotspot/active`.
21. Confirmar IP, MAC y uptime.
22. Regresar Express a 30 minutos.

### Prueba visual

23. Revisar logo en escritorio.
24. Revisar logo en teléfono.
25. Confirmar mejor contraste de descripciones.
26. Confirmar que el portal sigue siendo responsivo.
27. Confirmar que ingresar PIN sigue funcionando.
28. Confirmar que comprar acceso sigue funcionando.
29. Confirmar que el selector de idioma sigue funcionando.
