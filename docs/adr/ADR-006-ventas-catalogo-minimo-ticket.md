# ADR-006: Ventas con catálogo mínimo y ticket HTML

**Estado:** Aceptado

## Contexto

El alcance de la actividad pide registrar ventas, consultar su historial y
generar un comprobante. El prototipo de ventas muestra un formulario con cliente,
productos, cantidades, total, efectivo recibido y cambio. También se solicita un
ticket imprimible, pero no se define una integración con inventario ni un modelo
de pago distinto del efectivo.

La app `ventas` solo tenía una página de alcance y `catalogo` no tenía modelos.
Para implementar ventas hacía falta un maestro mínimo de productos y decisiones
claras sobre inmutabilidad, stock, impuestos y formato del ticket.

## Decisión

Implementar en `apps/catalogo` un modelo mínimo `Producto` con:

- Código único, normalizado a mayúsculas.
- Nombre, precio de venta no negativo y estado activo.
- Fechas de creación y actualización.
- Administración desde Django Admin. El CRUD visual del catálogo queda pendiente.

Implementar en `apps/ventas`:

- `Venta` con cliente opcional, vendedor, método de pago, monto recibido, total y
  fecha automática. El número visible se deriva de la clave primaria con formato
  `V-000001`; el cambio se calcula como `monto_recibido - total`.
- `DetalleVenta` con referencia protegida al producto y una copia histórica de
  código, nombre y precio unitario. El subtotal se calcula como
  `precio_unitario * cantidad`.
- Servicio `registrar_venta()` dentro de `transaction.atomic()`: valida que haya
  al menos una línea, que los productos estén activos, que no se repitan, que las
  cantidades sean válidas, que el total no exceda el máximo y que el efectivo
  cubra el total. Crea la venta y sus detalles en una sola transacción.
- Vistas protegidas con `LoginRequiredMixin` para listado, registro, detalle y
  ticket. El listado incluye búsqueda por número, cliente o producto, filtro por
  cliente y paginación.
- Venta inmutable en esta etapa: no se edita, elimina ni anula desde la
  interfaz. El admin de ventas es de solo lectura y las referencias a clientes y
  productos usan `PROTECT`.
- Ticket HTML de 80 mm con estilos de impresión locales. No se usa una librería
  PDF ni un CDN.
- Historial de las últimas ventas en la ficha del cliente.

Quedan fuera de esta etapa:

- Descuento o validación de stock.
- Edición, eliminación o anulación de ventas.
- Impuestos, descuentos y facturación fiscal.
- Medios de pago distintos de efectivo.
- CRUD visual del catálogo.

## Consecuencias

### Positivas

- El módulo de ventas es funcional sin esperar al inventario ni a un catálogo
  completo.
- La copia histórica de código, nombre y precio protege el ticket y la ficha de
  la venta frente a cambios posteriores del producto.
- El servicio transaccional centraliza los cálculos y evita que el navegador
  altere precios o totales.
- La inmutabilidad y el admin de solo lectura reducen el riesgo de modificar
  registros financieros por error.
- El ticket de 80 mm se puede imprimir desde el navegador sin dependencias
  externas.

### Negativas

- **Decisión reemplazada:** esta versión ya descuenta automáticamente el
  inventario mediante el servicio transaccional de ventas, usando FEFO para
  seleccionar lotes. El detalle de venta conserva el costo de adquisición.
- No se puede corregir ni anular una venta desde la interfaz; cualquier ajuste
  requerirá una etapa posterior con reglas contables.
- El catálogo solo se mantiene desde Django Admin, lo que limita la operación
  para un usuario Vendedor.
- El ticket es un comprobante interno, no una factura fiscal.

### Riesgos

- El registro de ventas puede rechazarse si no hay existencias activas y no
  vencidas suficientes. El servicio valida la disponibilidad y revierte toda
  la operación si falta stock.
- Cambios de precio que afecten ventas históricas. Mitigación: el detalle guarda
  una copia del precio y del nombre.
- Crecimiento del listado de ventas. Mitigación: paginación, búsqueda y filtro
  ya implementados.
- Errores de digitación en el efectivo recibido. Mitigación: validación del
  servidor y vista previa del cambio en el formulario.

## Alternativas descartadas

- **Implementar primero el catálogo completo:** retrasaría ventas sin aportar
  valor inmediato al alcance solicitado. Se optó por un producto mínimo.
- **Descontar stock ahora:** el módulo de inventario no existe y se duplicarían
  reglas de existencias. Se pospone.
- **Crear un modelo `Pago`:** con un solo medio de pago, agrega complejidad sin
  beneficio. Se puede incorporar cuando existan tarjetas u otros medios.
- **Permitir editar o anular ventas:** requiere reglas de auditoría y
  reversión de stock que no están en el alcance. Se pospone.
- **Generar PDF con una librería:** se prefiere HTML y CSS de impresión local
  para evitar dependencias y mantener el ticket simple.
- **Incluir impuestos y descuentos:** fuera del alcance de esta etapa.
