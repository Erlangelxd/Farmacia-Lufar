# ADR-008: Inventario por lotes con movimientos transaccionales

**Estado:** Aceptado

## Contexto

La app `inventario` ya tenía los modelos `Lote` y `MovimientoInventario`, y el
reporte de inventario consultaba lotes y movimientos. Sin embargo,
`inventario:index` seguía mostrando una página de alcance y no existía una forma
operativa de cargar existencias, registrar entradas o salidas, ni consultar
lotes desde la interfaz.

El catálogo no guarda stock: `Producto.stock_minimo` solo define el umbral de
reposición. Para conservar la trazabilidad y no romper las ventas históricas, el
stock debía seguir viviendo por lote y cada cambio debía quedar explicado por un
movimiento.

## Decisión

Implementar en `apps/inventario`:

- Listado de existencias por producto con stock sumado de lotes activos,
  cantidad de lotes, stock mínimo, estado y alertas de stock bajo, sin stock,
  por vencer y vencido.
- CRUD visual de lotes en `/inventario/lotes/`: alta con stock inicial, edición
  de datos maestros, búsqueda, filtros por estado y vencimiento, y
  activación/desactivación por POST con CSRF.
- Historial de movimientos en `/inventario/movimientos/` con búsqueda, filtro
  por tipo y alta manual de entradas, salidas y ajustes.
- Servicios transaccionales en `apps/inventario/services.py`:
  - `crear_lote()` crea el lote con stock cero y, si se indica stock inicial,
    registra un movimiento `INICIAL` en la misma transacción.
  - `registrar_movimiento()` bloquea el lote con `select_for_update()`, valida
    que esté activo, aplica el signo del tipo y registra el movimiento
    inmutable con el stock resultante.
- Tipos manuales habilitados: `ENTRADA`, `SALIDA`, `AJUSTE_POSITIVO` y
  `AJUSTE_NEGATIVO`. `INICIAL` queda reservado al alta del lote.
- Validaciones de dominio:
  - código de lote normalizado a mayúsculas y único por producto sin distinguir
    mayúsculas;
  - fecha de vencimiento posterior o igual a la de fabricación;
  - cantidad mayor que cero, con dos decimales;
  - stock resultante nunca negativo;
  - lote con existencias no puede desactivarse.
- `MovimientoInventario` no se edita ni se elimina desde la interfaz; su admin
  es de solo lectura. El admin de lotes marca `stock_actual` como campo de solo
  lectura y no permite eliminar lotes.
- Acceso exclusivo del rol `Administrador` o superusuario. El Vendedor recibe
  `403`.
- Selectores compartidos `stock_por_producto()` y
  `productos_con_stock_bajo()` en `apps/inventario/selectors.py`, usados por el
  módulo y por reportes.
- No integrar todavía el descuento de stock en ventas ni la recepción de
  compras; esas operaciones deberán llamar a los servicios de inventario en una
  etapa posterior.

## Consecuencias

### Positivas

- El inventario se puede operar desde la aplicación, sin depender de Django
  Admin.
- El stock y su historial se actualizan en una sola transacción, por lo que no
  quedan movimientos sin efecto ni cambios sin trazabilidad.
- El reporte y el módulo de inventario comparten la misma definición de stock y
  de alerta de reposición.
- La inmutabilidad de los movimientos y el bloqueo de desactivación de lotes con
  existencias protegen la consistencia del inventario.
- La validación se repite en modelo, formulario y servicio, igual que en ventas,
  clientes y catálogo.

### Negativas

- El registro de movimientos sigue siendo manual; la integración automática con
  ventas y compras queda pendiente.
- No hay selección FEFO ni bloqueo de lotes vencidos al vender.
- SQLite no ofrece el mismo nivel de concurrencia que PostgreSQL;
  `select_for_update()` es una preparación para el futuro, no una garantía
  equivalente.
- El stock inicial solo se puede indicar al crear el lote; corregirlo requiere
  un ajuste.

### Riesgos

- Errores de carga o ajustes manuales. Mitigación: movimientos inmutables con
  usuario, motivo, fecha y stock resultante.
- Duplicados de código por mayúsculas o espacios. Mitigación: normalización y
  comparación sin distinguir mayúsculas en modelo y formulario.
- Venta de productos vencidos. Mitigación actual: alertas de vencimiento y
  bloqueo visual; la validación FEFO se abordará con la integración de ventas.
- Crecimiento del historial. Mitigación: paginación, búsqueda y filtros.

## Alternativas descartadas

- **Guardar el stock directamente en `Producto`:** se descartó porque impide
  distinguir lotes, vencimientos y movimientos, y porque el catálogo ya declara
  que no posee existencias.
- **Editar `stock_actual` desde el formulario del lote:** se descartó para que
  todo cambio quede explicado por un movimiento.
- **Permitir stock negativo:** se descartó porque oculta errores de carga y
  rompe las alertas y los reportes.
- **Eliminar lotes o movimientos:** se descartó para conservar la trazabilidad;
  se usa el estado `activo` para los lotes.
- **Registrar el inventario inicial como movimiento manual:** se descartó para
  evitar cargas iniciales duplicadas; lo genera únicamente `crear_lote()`.
- **Integrar ventas y compras en esta misma entrega:** se pospone para mantener
  el alcance y acordar antes la selección de lotes y las transacciones
  compartidas.
