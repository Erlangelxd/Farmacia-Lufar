# Changelog

Todos los cambios relevantes del proyecto se documentan en este archivo.

## [No publicado]

### Agregado

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
- La página de alcance de `catalogo` ahora indica que el modelo `Producto` se
  administra desde Django Admin.
- La ficha del cliente reemplazó el aviso de historial pendiente por el
  historial real de ventas.
- La documentación de arquitectura y el README reflejan el estado de ventas y
  del catálogo mínimo.
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
