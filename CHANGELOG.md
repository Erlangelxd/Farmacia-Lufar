# Changelog

Todos los cambios relevantes del proyecto se documentan en este archivo.

## [No publicado]

### Agregado

- Módulo de clientes con modelo `Cliente`, migración inicial, formulario de
  registro, listado con búsqueda y filtro por estado, ficha de consulta y
  registro en Django Admin.
- Pruebas del modelo, formulario y vistas de clientes, incluida la protección
  CSRF y la paginación.
- ADR-005 con las decisiones del módulo de clientes.
- Este archivo `CHANGELOG.md`.

### Cambiado

- La ruta `clientes:index` dejó de ser un placeholder y ahora muestra el listado
  real de clientes.
- El menú lateral marca activo el módulo de clientes también en las vistas de
  registro y detalle.
- La documentación de arquitectura y el README reflejan el estado del módulo.
- El formulario de login fue rediseñado con estilos locales y fondo SVG, sin
  dependencias de CDN ni imágenes externas.

## [0.1.0] - 2026-09-26

### Agregado

- Estructura inicial del proyecto Django con las ocho aplicaciones.
- Autenticación, grupos `Administrador` y `Vendedor`, dashboard y navegación.
- Documentación de arquitectura y decisiones iniciales.
