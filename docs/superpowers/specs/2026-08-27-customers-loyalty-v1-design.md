# Cofi POS — Clientes + Loyalty V1

Fecha: 2026-08-27

## Objetivo

Agregar a Cofi POS un módulo global de clientes para todas las sucursales de CofiCenter, con historial de compras, métricas básicas y programa de puntos.

El sistema debe seguir funcionando con la filosofía offline-first del POS.

---

## 1. Cliente global

Cada cliente pertenece a CofiCenter, no a una sucursal individual.

Un mismo cliente podrá:

- comprar en Nuevo Vallarta;
- comprar después en Bucerías;
- comprar después en Ixtapa;
- mantener el mismo perfil;
- mantener el mismo saldo de puntos;
- consultar un historial consolidado.

### Datos del cliente

Obligatorios:

- nombre;
- teléfono.

Opcionales:

- correo electrónico;
- fecha de cumpleaños.

El teléfono será el identificador principal para detectar duplicados.

El servidor deberá normalizar teléfonos antes de comparar registros.

Ejemplos que deben reconocerse como el mismo número:

- 3221234567
- 322 123 4567
- 322-123-4567
- +52 322 123 4567

---

## 2. Estados automáticos del cliente

Los estados no serán editados manualmente.

### Nuevo

Cliente recientemente creado y que todavía no cumple criterio de frecuente.

### Activo

Cliente con actividad reciente que no cumple criterio de frecuente.

### Frecuente

Cliente con 4 o más compras durante los últimos 30 días.

### Inactivo

Cliente que lleva 60 días o más sin comprar.

Los estados se calcularán automáticamente con base en el historial de ventas.

---

## 3. Métricas del cliente

La ficha del cliente mostrará:

- puntos disponibles;
- valor equivalente de puntos en MXN;
- total gastado;
- número de compras;
- ticket promedio;
- última compra;
- sucursal de última compra;
- estado actual;
- historial de ventas;
- historial de movimientos de puntos.

---

## 4. Programa de puntos

Regla de acumulación:

- $10 MXN pagados = 1 punto.

No se otorgarán puntos por fracciones menores a $10.

Ejemplos:

- $75 pagados = 7 puntos;
- $100 pagados = 10 puntos;
- $238 pagados = 23 puntos.

### Valor

- 1 punto = $0.50 MXN.

Esto representa una recompensa aproximada de 5%.

### Redención mínima

- mínimo 20 puntos para redimir.

20 puntos equivalen a $10 MXN.

### Máximo por compra

Los puntos podrán cubrir como máximo 50% del ticket.

Ejemplo:

Ticket:
$200

Máximo descuento con puntos:
$100

### Generación después de redimir

Los puntos nuevos se calcularán únicamente sobre el dinero realmente pagado.

Ejemplo:

Ticket:
$200

Puntos utilizados:
$50 MXN

Pago real:
$150 MXN

Puntos nuevos:
15

---

## 5. Vigencia

Los puntos vencerán después de 12 meses sin actividad del cliente.

Actividad válida:

- compra;
- redención de puntos.

Una nueva actividad reinicia el periodo de 12 meses.

La expiración debe quedar registrada como movimiento dentro del Loyalty Ledger.

---

## 6. Loyalty Ledger

No se manejará el saldo únicamente como un número editable.

Cada movimiento de puntos quedará registrado en un libro de movimientos.

Tipos iniciales:

- EARN
- REDEEM
- SALE_REVERSAL
- REDEMPTION_REVERSAL
- EXPIRE

Ejemplo:

+12 pts — Compra NUE-001245
-20 pts — Redención BUC-000833
+20 pts — Reembolso BUC-000833
-12 pts — Venta cancelada NUE-001245
-30 pts — Expiración

Cada movimiento deberá guardar como mínimo:

- cliente;
- cantidad de puntos;
- tipo;
- fecha;
- venta relacionada cuando exista;
- sucursal relacionada;
- referencia idempotente.

---

## 7. Cancelaciones y devoluciones

Si una venta que generó puntos se cancela:

- los puntos otorgados por esa venta se revierten.

Si una venta utilizó puntos y posteriormente se cancela o reembolsa:

- los puntos utilizados regresan al cliente.

Las reversas deben ser automáticas y auditables.

No se permitirán movimientos duplicados.

---

## 8. Ajustes manuales

Los ajustes manuales de puntos quedan fuera de V1.

En una versión futura podrán existir únicamente en Admin, con:

- usuario administrador;
- motivo obligatorio;
- fecha;
- cantidad;
- auditoría.

---

## 9. Integración con Caja

En la venta existirá una acción:

`+ Agregar cliente`

Permitirá:

- buscar por teléfono;
- buscar por nombre;
- seleccionar cliente existente;
- crear cliente rápidamente;
- cambiar cliente;
- quitar cliente.

El cliente podrá cambiarse mientras la venta no haya sido finalizada.

### Cliente seleccionado

El carrito mostrará:

- nombre;
- puntos disponibles;
- equivalencia aproximada en pesos.

Ejemplo:

Cliente:
María López

85 puntos
$42.50 disponibles

---

## 10. Redención en cobro

Durante el cobro, si:

- existe cliente seleccionado;
- hay conexión con el servidor;
- el cliente tiene mínimo 20 puntos;

se habilitará:

`Usar puntos`

El sistema deberá calcular automáticamente:

- saldo disponible;
- valor en MXN;
- máximo de 50% del ticket;
- número de puntos requerido.

El cajero podrá utilizar menos puntos que el máximo disponible.

No se requiere PIN del cliente en V1.

---

## 11. Offline

Cofi POS debe continuar vendiendo sin Internet.

### Cliente existente

La terminal tendrá una copia local ligera de clientes para permitir:

- búsqueda;
- selección;
- asociación a la venta.

### Cliente nuevo offline

Se permitirá crear un cliente provisional sin conexión.

Al recuperar conexión:

1. el cliente provisional se envía al servidor;
2. el servidor normaliza el teléfono;
3. si no existe, crea el cliente;
4. si ya existe, reutiliza el cliente existente;
5. la venta local queda asociada al cliente global correcto.

No deben generarse dos clientes por una misma sincronización.

### Acumulación offline

Una venta offline asociada a cliente podrá generar puntos.

Los puntos quedarán pendientes hasta que la venta sea sincronizada y aceptada por el servidor.

El servidor será la autoridad final sobre los puntos otorgados.

### Redención offline

No se permitirá redimir puntos sin conexión.

Motivo:

el saldo es global entre sucursales y permitir redenciones offline podría ocasionar doble gasto del mismo saldo.

El POS mostrará:

`Sin conexión. Puedes acumular puntos, pero no redimirlos hasta recuperar conexión.`

---

## 12. Modelos propuestos

### Customer

Campos principales:

- id
- customer_uuid
- name
- phone
- phone_normalized
- email
- birthday
- created_at
- updated_at
- last_activity_at

`phone_normalized` será único.

### LoyaltyLedgerEntry

Campos principales:

- id
- entry_uuid
- customer_id
- points
- entry_type
- order_uuid
- branch_id
- idempotency_key
- created_at

`idempotency_key` deberá ser único.

### Venta

La venta tendrá relación opcional con cliente.

Campo conceptual:

- customer_id

Las ventas sin cliente continuarán siendo válidas.

---

## 13. Saldo

El servidor será la autoridad del saldo global.

El saldo efectivo será:

suma de movimientos vigentes del Loyalty Ledger.

La interfaz podrá recibir un saldo calculado desde backend para evitar recalcular todo el historial en cada pantalla.

Nunca se confiará en un saldo enviado por el POS.

---

## 14. Idempotencia

La sincronización offline no podrá otorgar puntos dos veces.

El mismo `order_uuid` sincronizado nuevamente deberá devolver el resultado existente sin crear:

- venta duplicada;
- cliente duplicado;
- puntos duplicados.

El Loyalty Ledger utilizará claves idempotentes relacionadas con la venta y el tipo de movimiento.

Ejemplo conceptual:

`EARN:<order_uuid>`

---

## 15. Pantalla Clientes

La navegación Clientes mostrará:

- buscador;
- todos;
- nuevos;
- activos;
- frecuentes;
- inactivos.

Columnas / información principal:

- cliente;
- teléfono;
- puntos;
- compras;
- gasto total;
- ticket promedio;
- última visita;
- estado.

Al abrir un cliente:

### Resumen

- datos personales;
- saldo;
- valor en pesos;
- compras;
- gasto;
- ticket promedio;
- última visita.

### Compras

Historial cronológico de tickets.

### Actividad de puntos

Historial del Loyalty Ledger.

---

## 16. Privacidad operacional

El cajero podrá:

- buscar clientes;
- crear clientes;
- asociarlos a ventas;
- utilizar puntos cuando corresponda.

V1 no permitirá al cajero:

- editar saldo manualmente;
- crear movimientos manuales;
- eliminar historial;
- modificar movimientos pasados.

---

## 17. Flujo principal

### Venta online

Cliente
→ carrito
→ cobro
→ redención opcional
→ venta
→ Loyalty Ledger
→ saldo actualizado

### Venta offline

Cliente cacheado o provisional
→ carrito
→ cobro sin redención
→ venta local
→ sincronización
→ resolución de cliente
→ creación de venta
→ Loyalty Ledger
→ saldo global actualizado

---

## 18. Reglas V1 definitivas

- clientes globales entre sucursales;
- teléfono como identificador principal;
- nombre y teléfono obligatorios;
- correo y cumpleaños opcionales;
- 1 punto por cada $10 pagados;
- 1 punto vale $0.50 MXN;
- mínimo 20 puntos para redimir;
- máximo 50% del ticket mediante puntos;
- puntos nuevos únicamente sobre efectivo real pagado;
- expiración tras 12 meses sin actividad;
- sin PIN para redimir;
- cajero puede cambiar cliente antes de finalizar venta;
- acumulación permitida offline;
- redención prohibida offline;
- creación provisional de cliente offline;
- cancelaciones y devoluciones revierten puntos;
- ajustes manuales fuera de V1;
- frecuente = 4 compras / 30 días;
- inactivo = 60 días sin compra;
- backend es autoridad de cliente, saldo y Loyalty Ledger.
