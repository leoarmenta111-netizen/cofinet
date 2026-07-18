# Análisis de Riesgos — Migración HTTPS CofiNet+

## Fecha: 2026-07-18
## Dominio: cofinet-portal.duckdns.org

---

## Riesgos Identificados

| # | Riesgo | Probabilidad | Impacto | Mitigación |
|---|--------|-------------|---------|------------|
| R1 | Certbot no obtiene certificado | Media | Crítico | Verificar DNS y puerto 80 antes. Script tiene modo staging para pruebas. |
| R2 | Nginx no arranca con config SSL | Baja | Alto | docker-compose.yml original intacto. Rollback en 2 minutos. |
| R3 | MP rechaza webhooks | Baja | Alto | Let's Encrypt es CA reconocida. Si falla, revertir FRONTEND_URL. |
| R4 | Vercel Mixed Content | Baja | Medio | vercel.json ya apunta a HTTPS. Revertible con git checkout. |
| R5 | Certificado expira | Media | Alto | Crontab renueva diariamente. Certbot solo renueva si <30 días. |
| R6 | Downtime durante migración | Media | Medio | ~2-3 minutos. Hacer en horario de baja actividad. |
| R7 | Pérdida de datos | Ninguna | Crítico | No se tocan volúmenes de postgres ni la DB. |

---

## Plan de Rollback

### Tiempo estimado: < 5 minutos

```bash
# 1. Detener contenedores SSL
docker compose -f docker-compose.ssl.yml down

# 2. Restaurar FRONTEND_URL
sed -i 's|FRONTEND_URL=https://cofinet-portal.duckdns.org|FRONTEND_URL=http://cofinet-portal.duckdns.org|' backend/.env

# 3. Levantar compose original
docker compose up -d

# 4. Revertir frontend (si fue commiteado)
git checkout -- frontend/vercel.json frontend/js/api.js

# 5. Verificar
curl -I http://cofinet-portal.duckdns.org
```

---

## Qué NO se toca en esta migración

- Base de datos PostgreSQL
- Modelos SQLAlchemy
- Endpoints FastAPI
- Servicios de pago / membresía
- Migraciones Alembic
- Lógica de Mercado Pago
