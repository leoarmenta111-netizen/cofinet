# CofiNet+

Proyecto preparado para desplegarse con Docker Compose y Nginx.

## Estructura

- `frontend/`: portal público y recursos estáticos.
- `admin/`: panel administrativo estático, disponible en `/admin/`.
- `backend/`: API FastAPI, dependencias y configuración de entorno.
- `nginx/default.conf`: servidor estático y proxy inverso de `/api/` hacia FastAPI.

## Configuración de producción

1. Copia `backend/.env.example` a `backend/.env`.
2. Configura credenciales seguras para PostgreSQL y Mercado Pago.
3. Define `DATABASE_HOST=postgres` y `FRONTEND_URL` con la URL pública HTTPS del VPS.
4. Ejecuta Docker Compose usando el archivo de entorno del backend:

   ```bash
   docker compose --env-file backend/.env up -d --build
   ```

Nginx publica el portal en el puerto 80 y enruta las solicitudes del navegador desde `/api/*` a los endpoints FastAPI existentes.
