# CofiCenter POS — Cocina y Barra

Date: 2026-09-02

## Objetivo

Agregar dos pantallas operativas independientes al POS:

- Cocina
- Barra

Cada producto tendrá una estación de preparación configurable.

Valores permitidos:

- KITCHEN
- BAR
- NONE

Una venta seguirá siendo una sola orden comercial, pero sus artículos se
distribuirán automáticamente a las estaciones correspondientes.

---

## 1. Producto y estación

Cada producto tendrá:

preparation_station = KITCHEN | BAR | NONE

Ejemplos:

Latte -> BAR
Smoothie Mango -> BAR
Club Sandwich -> KITCHEN
Papas -> KITCHEN
Agua embotellada -> NONE

La estación pertenece al producto, no a la categoría.

La configuración podrá modificarse desde el catálogo administrativo.

---

## 2. Orden principal

La venta POS seguirá creando una sola orden.

Ejemplo:

Orden NUE-000042

1 x Latte            BAR
1 x Smoothie Mango   BAR
1 x Club Sandwich    KITCHEN
1 x Papas            KITCHEN

No se crearán dos ventas ni dos cobros.

---

## 3. Tickets por estación

Al registrar una orden se generará trabajo únicamente para las estaciones
que tengan artículos.

Ejemplo:

BAR
- 1 x Latte
- 1 x Smoothie Mango

KITCHEN
- 1 x Club Sandwich
- 1 x Papas

Los productos NONE no aparecen en Cocina ni Barra.

---

## 4. Estado por estación

Cada estación de una orden tendrá estado independiente:

NEW
PREPARING
READY

Ejemplo:

Orden NUE-000042

BAR       READY
KITCHEN   PREPARING

La estación de Barra no necesita esperar a Cocina para marcar sus artículos
como listos.

---

## 5. Estado general de la orden

El POS continuará mostrando un estado general.

Reglas:

- Si todas las estaciones requeridas están NEW:
  orden = NEW

- Si cualquier estación está PREPARING:
  orden = PREPARING

- Si alguna estación está READY pero otra todavía no:
  orden = PREPARING

- Si todas las estaciones requeridas están READY:
  orden = READY

- DELIVERED continúa siendo una acción de entrega de la orden completa.

La orden no pasa automáticamente a DELIVERED.

---

## 6. Pantalla Cocina

Ruta conceptual:

/pos/kitchen?branch=nuevo-vallarta

La pantalla mostrará únicamente artículos KITCHEN de la sucursal activa.

Cada ticket mostrará:

- Folio
- Hora
- Tiempo transcurrido
- Cliente cuando exista
- Artículos de cocina
- Cantidades
- Notas/modificadores
- Estado
- Acción Empezar
- Acción Marcar lista

Flujo:

NEW -> PREPARING -> READY

No mostrará artículos de Barra.

---

## 7. Pantalla Barra

Ruta conceptual:

/pos/bar?branch=nuevo-vallarta

La pantalla mostrará únicamente artículos BAR de la sucursal activa.

Cada ticket mostrará:

- Folio
- Hora
- Tiempo transcurrido
- Cliente cuando exista
- Bebidas/artículos de barra
- Cantidades
- Modificadores
- Estado
- Acción Empezar
- Acción Marcar lista

Flujo:

NEW -> PREPARING -> READY

No mostrará artículos de Cocina.

---

## 8. Sucursal

Todas las estaciones estarán aisladas por sucursal.

Ejemplo:

Nuevo Vallarta Cocina
solo recibe órdenes Nuevo Vallarta.

Bucerías Cocina
solo recibe órdenes Bucerías.

Ixtapa Barra
solo recibe órdenes Ixtapa.

Nunca se deben mezclar órdenes entre sucursales.

---

## 9. POS / Órdenes

La pantalla actual de Órdenes seguirá siendo la vista general.

El detalle de una orden deberá poder mostrar:

BAR
READY

KITCHEN
PREPARING

Estado general
PREPARING

El usuario del POS podrá ver el progreso de preparación sin entrar a las
pantallas operativas.

---

## 10. Catálogo administrativo

Cada producto tendrá selector:

Estación de preparación

- Cocina
- Barra
- Sin preparación

El backend almacenará los valores:

KITCHEN
BAR
NONE

NONE será seguro para productos que no requieren preparación.

---

## 11. Persistencia

No dependeremos de inferir la estación usando nombre, SKU o categoría.

La estación será información persistente del producto.

También se persistirá el estado de preparación de cada estación por orden,
de forma que recargar una tablet no pierda el progreso.

---

## 12. Concurrencia

Cocina y Barra pueden actualizar la misma orden al mismo tiempo.

Cada estación modifica solamente su propio estado.

Ejemplo:

Barra:
NEW -> PREPARING -> READY

Cocina:
NEW -> PREPARING -> READY

El servidor recalcula el estado general después de cada actualización.

---

## 13. Offline

La venta POS conservará el comportamiento offline existente.

Una venta local pendiente de sincronización no debe aparecer en las pantallas
de Cocina o Barra del servidor hasta estar sincronizada.

Una vez sincronizada, se enruta normalmente a sus estaciones.

No se implementará sincronización offline independiente de tablets de Cocina
o Barra en esta primera versión.

---

## 14. Seguridad de alcance

Primera versión incluye:

- KITCHEN / BAR / NONE
- configuración por producto
- división automática de artículos
- pantalla Cocina
- pantalla Barra
- estados independientes
- estado general calculado
- aislamiento por sucursal
- notas y modificadores de artículos

Primera versión NO incluye:

- impresoras automáticas de cocina
- múltiples estaciones para un mismo producto
- expo station
- inventario por estación
- tiempos objetivo por receta
- asignación a empleados
- pago dividido
- notificaciones push externas

La arquitectura debe permitir agregar estas funciones posteriormente sin
cambiar el modelo principal.

---

## 15. Criterios de aceptación

Una venta con únicamente bebidas aparece solo en Barra.

Una venta con únicamente comida aparece solo en Cocina.

Una venta mixta aparece simultáneamente en Cocina y Barra con los artículos
correctos.

Un producto NONE no aparece en ninguna estación.

Cocina puede pasar a READY sin modificar el estado de Barra.

Barra puede pasar a READY sin modificar el estado de Cocina.

La orden general solo pasa a READY cuando todas las estaciones requeridas
están READY.

DELIVERED continúa siendo una acción posterior de la orden general.

Una pantalla de una sucursal nunca muestra órdenes de otra sucursal.

Los modificadores y notas del producto llegan a la estación correspondiente.

Recargar Cocina o Barra conserva correctamente el estado de preparación.
