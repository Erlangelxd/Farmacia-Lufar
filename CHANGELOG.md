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

## [0.1.0] - 2026-09-26

### Agregado

- Estructura inicial del proyecto Django con las ocho aplicaciones.
- Autenticación, grupos `Administrador` y `Vendedor`, dashboard y navegación.
- Documentación de arquitectura y decisiones iniciales.
