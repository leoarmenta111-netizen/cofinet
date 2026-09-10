# Flujo auditado de emisión de PIN

## Comportamiento encontrado antes de este cambio

### Venta de efectivo desde el panel

`POST /admin/pins` valida un administrador con rol `super_admin` o `pin_operator`, carga el plan activo, genera un PIN aleatorio de seis dígitos y calcula `expires_at` desde la duración vigente. Después llama a RouterOS y guarda una `Purchase` pagada con el precio vigente, `issued_at`, operador y fuente `admin_cash`.

La escritura de PostgreSQL ya ocurría después de RouterOS y eliminaba el usuario Hotspot si el commit fallaba. Sin embargo, `create_hotspot_user` devolvía éxito cuando el usuario ya existía en MikroTik; eso podía asociar una compra nueva a credenciales ajenas ya presentes en el router.

### Mercado Pago

`POST /guest-purchases` guarda una compra `pending` con el plan y precio vigentes, crea la preferencia y guarda el pago pendiente. El webhook consulta el pago directamente en Mercado Pago, bloquea las filas locales, y solo para estado `approved` genera el PIN, crea el usuario Hotspot y marca compra/pago como aprobados.

La transacción de PostgreSQL se confirmaba fuera del bloque que compensaba la creación en MikroTik. Un fallo final del commit podía, por tanto, dejar un usuario Hotspot sin compra confirmada. También se usaba la creación no estricta descrita arriba.

### Validación pública

`POST /pins/validate` busca una compra por `pin_code` y exige estado `paid` con expiración futura. El portal usa el mismo PIN como usuario y contraseña del formulario de login Hotspot. La respuesta histórica mostraba la duración vigente del plan relacionado, no necesariamente la duración con la que se emitió el PIN.

### PIN permanentes

Las credenciales internas permanentes se gestionan en una tabla y flujo separados, sin `limit-uptime`. Este cambio no crea, elimina ni altera `654321`, `654322` ni ninguna credencial permanente.

## Garantías después de este cambio

- La creación de usuarios Hotspot para efectivo y Mercado Pago es estricta; una colisión en RouterOS provoca otro PIN.
- Usuario y contraseña son el PIN, el perfil es `default` y `limit-uptime` usa la duración vigente del plan.
- Un error de MikroTik devuelve error y no guarda una compra falsamente pagada.
- El commit de compra y pago de Mercado Pago ocurre dentro del bloque de compensación. Si PostgreSQL falla después de crear el usuario, se intenta eliminar ese usuario y se registra el error sin secretos.
- Precio y expiración se congelan al emitir. Las respuestas de PIN históricos derivan su duración de `issued_at` y `expires_at`, por lo que editar el plan no reinterpreta su duración.
- La restricción única de PostgreSQL sigue protegiendo contra concurrencia, además de las verificaciones en PostgreSQL y MikroTik.

No se agregó migración: `plans.price`, `plans.duration_minutes`, `purchases.amount`, `issued_at` y `expires_at` ya existen.
