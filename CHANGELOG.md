# Changelog

Todos los cambios relevantes del proyecto se documentan en este archivo.

## [No publicado]

### Agregado

- Módulo de compras completo: proveedores con alta, edición, activación y
  desactivación por POST; compras con líneas de detalle, edición y anulación de
  borradores; y recepción sobre lotes existentes que registra entradas de
  inventario.
- Servicios transaccionales `registrar_compra()`, `actualizar_compra()`,
  `recibir_compra()` y `anular_compra()` en `apps/compras/services.py`, con
  totales calculados en el servidor y recepción atómica mediante
  `apps.inventario.services.registrar_movimiento()`.
- Formularios `ProveedorForm`, `CompraForm`, `DetalleCompraFormSet` y
  `RecepcionCompraForm`, con validación de NIT único, lotes del mismo producto y
  lotes no repetidos.
- Vistas, rutas y plantillas de compras y proveedores, con listados, filtros,
  ficha de consulta, recepción y anulación de borradores.
- JavaScript `static/js/compras.js` para la vista previa de subtotales y total.
- Admin de compras endurecido: proveedores y compras sin eliminación, compras
  recibidas o anuladas de solo lectura, detalles de solo lectura y recálculo de
  totales al guardar.
- Pruebas del modelo, formularios, servicios y vistas de compras, incluidos
  permisos de rol y atomicidad de la recepción.
- ADR-009 con la decisión de recibir compras sobre lotes existentes.

- Esquema completo de base de datos en SQLite (sin `codigo_barras` en
  `Producto`): catálogos de categoría, laboratorio, forma farmacéutica y
  presentación; proveedores, compras y detalle de compra; lotes y movimientos
  de inventario; y configuración del sistema. Incluye migraciones, índices,
  restricciones `CHECK` y registro en Django Admin.
- Migración de datos `catalogo.0003_categoria_general` que crea la categoría
  `General` para los productos existentes.
- Documento `docs/modelo-er-relacional.tex` y su PDF con el modelo
  entidad-relación y el modelo relacional del sistema.
- Reporte de compras por periodo, proveedor y estado, con montos,
  distribución por estado y productos más comprados.
- Reporte de inventario basado en lotes: existencias totales, valor del
  inventario a precio de venta, productos con stock bajo, lotes por vencer y
  lotes vencidos, y movimientos recientes.
- Resumen de compras e inventario en el índice de reportes.
- Pruebas de las vistas de reportes: totales, filtros, estados vacíos y
  protección de acceso.
- Matriz de acceso por rol en `apps/accounts/permissions.py`, con
  `MODULE_ACCESS` para la interfaz y `SELLER_PERMISSIONS` para el menor
  privilegio del Vendedor.
- Sincronización idempotente de permisos por modelo mediante la señal
  `post_migrate` y el comando `python manage.py sync_roles`.
- Gestión visual de usuarios en `/cuentas/usuarios/`: alta, edición de datos,
  asignación de rol, contraseña opcional y activación/desactivación por POST.
- Filtros de usuarios por búsqueda, rol y estado, tarjetas de resumen, matriz
  de acceso por rol y resumen de permisos por app.
- Guardas para no desactivar la propia cuenta, no quitarse el rol
  Administrador, no dejar el sistema sin administradores activos y no permitir
  que un administrador no superusuario edite superusuarios.
- Pruebas de cuentas: sincronización de permisos, formularios, filtros, acceso
  por rol y guardas de seguridad.
- Módulo de clientes con modelo `Cliente`, migración inicial, formulario de
  registro, listado con búsqueda y filtro por estado, ficha de consulta y
  registro en Django Admin.
- Pruebas del modelo, formulario y vistas de clientes, incluida la protección
  CSRF y la paginación.
- Catálogo mínimo con modelo `Producto`, migración inicial, administración en
  Django Admin y pruebas de normalización, unicidad y precio.
- CRUD visual de productos en `/catalogo/`: listado con búsqueda por código,
  nombre, principio activo o categoría, filtros por categoría y estado,
  paginación, tarjetas de resumen, alta, edición y activación/desactivación por
  POST.
- CRUD visual de categorías en `/catalogo/categorias/`: listado con búsqueda,
  filtro por estado, conteo de productos totales y activos, alta, edición y
  activación/desactivación por POST.
- Formularios de catálogo con normalización de código y nombre, validación de
  unicidad sin distinguir mayúsculas y filtrado de categorías y laboratorios
  activos.
- Guarda que impide desactivar una categoría mientras tenga productos activos,
  aplicada en el modelo y en la vista.
- Pruebas del catálogo: modelo de categoría, formularios, listados, filtros,
  operaciones de escritura y acceso de consulta del Vendedor.
- ADR-007 con las decisiones del catálogo visual de productos y categorías.
- Módulo de inventario con existencias por producto, alertas de stock bajo,
  sin stock y vencimientos, y tarjetas de resumen.
- CRUD visual de lotes en `/inventario/lotes/`: alta con stock inicial, edición
  de datos sin tocar existencias, búsqueda, filtros por estado y vencimiento, y
  activación/desactivación por POST.
- Historial de movimientos en `/inventario/movimientos/` con búsqueda, filtro
  por tipo y registro manual de entradas, salidas y ajustes.
- Servicios transaccionales `crear_lote()` y `registrar_movimiento()`: bloqueo
  del lote, validación de stock suficiente, actualización de
  `Lote.stock_actual` y creación de `MovimientoInventario` en la misma
  transacción.
- Selectores `stock_por_producto()` y `productos_con_stock_bajo()` en
  `apps/inventario/selectors.py`, reutilizados por reportes.
- Normalización del código de lote, unicidad por producto sin distinguir
  mayúsculas, validación de fechas y bloqueo de desactivación de lotes con
  existencias.
- Pruebas de inventario: modelos, servicios, formularios, filtros, CRUD,
  movimientos, alertas y acceso por rol.
- ADR-008 con las decisiones de inventario por lotes y movimientos
  transaccionales.
- Módulo de ventas con modelos `Venta` y `DetalleVenta`, migración inicial,
  servicio transaccional de registro, formulario con formset, listado con
  búsqueda y filtro por cliente, ficha de consulta y ticket imprimible de
  80 mm.
- Cálculo de total y cambio, copia histórica de código, nombre y precio del
  producto, validaciones de líneas, efectivo insuficiente y rollback
  transaccional.
- Pruebas del servicio, modelos, formularios, vistas, ticket y protección CSRF
  de ventas.
- Historial de las últimas ventas en la ficha del cliente.
- ADR-005 con las decisiones del módulo de clientes.
- ADR-006 con las decisiones de ventas, catálogo mínimo y ticket HTML.
- Este archivo `CHANGELOG.md`.

### Cambiado

- La ruta `clientes:index` dejó de ser un placeholder y ahora muestra el listado
  real de clientes.
- La ruta `ventas:index` dejó de ser un placeholder y ahora muestra el listado
  real de ventas; se agregaron `ventas:crear`, `ventas:detalle` y
  `ventas:ticket`.
- El menú lateral marca activo el módulo de clientes también en las vistas de
  registro y detalle, y el módulo de ventas en listado, registro, detalle y
  ticket.
- La ruta `catalogo:index` dejó de ser un placeholder y ahora muestra el
  listado real de productos; se agregaron las rutas de productos y categorías
  bajo el namespace `catalogo`.
- El menú lateral marca activo el módulo de catálogo también en las vistas de
  productos y categorías.
- La ruta `inventario:index` dejó de ser un placeholder y ahora muestra las
  existencias reales; se agregaron `inventario:lotes`, `inventario:lote_crear`,
  `inventario:lote_editar`, `inventario:lote_estado`,
  `inventario:movimientos` y `inventario:movimiento_crear`.
- El menú lateral marca activo el módulo de inventario en sus listados,
  formularios y movimientos.
- El admin de lotes muestra el stock como campo de solo lectura y no permite
  eliminar lotes; el stock solo cambia por movimientos.
- Los reportes reutilizan los selectores de inventario para calcular existencias
  y alertas de stock bajo.
- La documentación de arquitectura y el README reflejan el estado del módulo de
  inventario.
- El catálogo pasó de administrarse solo desde Django Admin a tener CRUD visual
  para productos y categorías; los catálogos auxiliares siguen en admin.
- La ficha del cliente reemplazó el aviso de historial pendiente por el
  historial real de ventas.
- La documentación de arquitectura y el README reflejan el estado de ventas y
  del catálogo visual de productos y categorías.
- El formulario de login fue rediseñado con estilos locales y fondo SVG, sin
  dependencias de CDN ni imágenes externas.
- El reporte de compras dejó de ser un placeholder y ahora consulta
  `Compra`, `DetalleCompra` y `Proveedor`.
- El reporte de inventario dejó de basarse solo en el catálogo y ahora usa
  `Lote` y `MovimientoInventario` para calcular existencias, valor y alertas.
- Los módulos de inventario y compras, los reportes de compras/inventario y la
  gestión de usuarios quedaron restringidos al rol Administrador; el Vendedor
  recibe `403` y ya no ve esos enlaces en el menú.
- Los reportes de ventas y el índice de reportes usan `RoleRequiredMixin`; el
  índice oculta las tarjetas y los indicadores de compras e inventario al
  Vendedor.
- La vista de usuarios dejó de ser de solo lectura y ahora permite crear,
  editar, activar y desactivar cuentas.
- El dashboard oculta los enlaces e indicadores de inventario y compras a los
  usuarios que no son administradores.
- La página de la cuenta muestra los módulos disponibles según el rol y el
  estado real de los permisos por modelo.
- El reporte de ventas separa los agregados de ventas y de detalles para no
  duplicar el conteo de operaciones ni los ingresos cuando una venta tiene
  varias líneas.

## [0.1.0] - 2026-09-26

### Agregado

- Estructura inicial del proyecto Django con las ocho aplicaciones.
- Autenticación, grupos `Administrador` y `Vendedor`, dashboard y navegación.
- Documentación de arquitectura y decisiones iniciales.
