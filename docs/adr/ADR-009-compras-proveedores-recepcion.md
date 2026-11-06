# ADR-009: Compras, proveedores y recepción sobre lotes existentes

**Estado:** Aceptado

## Contexto

La app `compras` ya tenía los modelos `Proveedor`, `Compra` y `DetalleCompra`,
y el reporte de compras consultaba sus datos. Sin embargo, `compras:index`
seguía mostrando una página de alcance: no había proveedores administrables,
compras editables ni una recepción que actualizara inventario.

El modelo `DetalleCompra` declara `lote` como opcional, pensado para asignarse
al recibir la compra. `inventario` es el único dueño del stock y expone
`registrar_movimiento()` para registrar entradas de forma transaccional. La
decisión pendiente era si la recepción debía crear lotes nuevos o reutilizar
lotes existentes.

## Decisión

Implementar en `apps/compras`:

- CRUD visual de proveedores en `/compras/proveedores/`: alta, edición,
  búsqueda, filtros por estado y activación/desactivación por POST. No hay
  eliminación.
- Compras en `/compras/`: listado con búsqueda y filtros por proveedor y estado,
  alta con líneas de detalle, edición y anulación de borradores, y ficha de
  consulta.
- Estados `BORRADOR`, `RECIBIDA` y `ANULADA`. Una compra nace en borrador; solo
  los borradores se editan o anulan. Una compra recibida o anulada es inmutable.
- Servicios transaccionales en `apps/compras/services.py`:
  - `registrar_compra()` y `actualizar_compra()` calculan los totales en el
    servidor y reemplazan las líneas dentro de `transaction.atomic()`.
  - `recibir_compra()` valida todas las líneas, exige un lote existente por
    línea y registra una entrada de inventario por cada una con
    `registrar_movimiento()`.
  - `anular_compra()` solo cambia el estado de un borrador y no toca inventario.
- **La recepción selecciona un lote existente por línea; no crea lotes.** Cada
  lote debe pertenecer al producto de la línea, estar activo y no repetirse
  entre líneas. Si un producto no tiene lotes, se crea primero desde
  `inventario`.
- `DetalleCompra.lote` se asigna durante la recepción. Los detalles de una
  compra recibida quedan de solo lectura.
- Se permite repetir un producto en varias líneas para asignar lotes distintos
  en la recepción.
- `Proveedor.nit` es opcional pero único sin distinguir mayúsculas cuando se
  informa. `Proveedor.nombre` es obligatorio.
- No se eliminan proveedores, compras ni detalles. El admin de proveedores y
  compras no permite borrar; las compras recibidas o anuladas son de solo
  lectura y los totales se recalculan a partir de las líneas.
- Acceso exclusivo del rol `Administrador` o superusuario. El Vendedor recibe
  `403` en todas las rutas de compras.

## Consecuencias

### Positivas

- Compras e inventario quedan integrados: recibir una compra aumenta el stock
  del lote elegido y deja un `MovimientoInventario` con usuario, motivo, fecha y
  stock resultante.
- La recepción es atómica y valida todas las líneas antes de mover stock; un
  error no deja entradas parciales.
- Los totales son autoritativos del servidor y no dependen del navegador.
- El historial de compras se conserva: no hay borrado y las compras cerradas son
  inmutables.
- La trazabilidad por lote permite distinguir vencimientos y costos dentro de
  una misma compra.

### Negativas

- La recepción es menos directa: exige que el lote exista antes de recibir la
  compra.
- No se crean lotes desde la recepción, así que una compra con un producto nuevo
  requiere dos pasos (lote y luego recepción).
- Un lote no puede recibir dos líneas de la misma compra, aunque el producto sea
  el mismo.
- SQLite limita la concurrencia; `select_for_update()` prepara el código para
  PostgreSQL, pero no replica sus garantías.

### Riesgos

- Seleccionar un lote equivocado. Mitigación: el formulario solo ofrece lotes
  activos del producto de la línea e impide repetir lotes.
- Recepciones parciales por fallos a mitad de proceso. Mitigación: validación
  previa de todas las líneas y `transaction.atomic()`.
- Cambios de estado manuales desde el admin. Mitigación: `estado` y
  `fecha_recepcion` son de solo lectura en el admin; la recepción y la anulación
  pasan por los servicios.
- Duplicidad de NIT. Mitigación: validación en modelo, formulario y restricción
  única condicional.

## Alternativas descartadas

- **Crear un lote nuevo por línea durante la recepción:** era la opción inicial,
  pero se descartó porque el usuario prefirió reutilizar lotes existentes y
  mantener el alta de lotes centralizada en `inventario`.
- **Permitir ambos modos (crear o seleccionar lote):** se descartó por el
  aumento de complejidad del formulario y de las validaciones.
- **Descontar o modificar stock directamente desde `compras`:** se descartó
  porque `inventario` es el único dueño de las existencias y toda alteración
  debe pasar por sus servicios.
- **Eliminar compras o proveedores:** se descartó para conservar el historial de
  abastecimiento y porque las compras pueden estar referenciadas por
  movimientos y reportes.
- **Permitir editar compras recibidas o anuladas:** se descartó para que el
  documento recibido coincida con el inventario ya movido.
