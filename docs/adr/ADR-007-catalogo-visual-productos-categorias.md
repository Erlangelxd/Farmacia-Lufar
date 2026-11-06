# ADR-007: Catálogo visual de productos y categorías

**Estado:** Aceptado

## Contexto

La app `catalogo` ya tenía los modelos `Categoria`, `Laboratorio`,
`FormaFarmaceutica`, `Presentacion` y `Producto`, junto con su registro en
Django Admin. La ruta `catalogo:index` seguía mostrando una página de alcance y
el módulo de ventas dependía de que un administrador cargara productos desde
`/admin/`.

Para que el catálogo sea operable desde la interfaz se necesita un CRUD visual
acotado, sin duplicar la administración de los catálogos auxiliares ni adelantar
la lógica de stock, que pertenece a `inventario`.

## Decisión

Implementar en `apps/catalogo`:

- Listado de productos con búsqueda por código, nombre, principio activo o
  categoría, filtro por categoría y estado, paginación de 20 registros y
  tarjetas de resumen.
- Alta y edición visual de productos con los campos maestros existentes:
  código, nombre, categoría, laboratorio, forma farmacéutica, presentación,
  principio activo, concentración, unidad de medida, precio de venta, stock
  mínimo, descripción y estado.
- Listado de categorías con búsqueda, filtro por estado y conteo de productos
  totales y activos.
- Alta y edición visual de categorías: nombre, descripción y estado.
- Activación y desactivación por POST con CSRF, sin eliminar registros.
- Bloqueo de la desactivación de una categoría mientras tenga productos activos,
  tanto en el modelo como en la vista.
- Acceso de consulta para el rol `Vendedor`; alta, edición y cambios de estado
  solo para `Administrador` o superusuario.
- Mantener `Laboratorio`, `FormaFarmaceutica` y `Presentacion` administrados
  desde Django Admin.
- No agregar campos de stock al producto: `inventario` sigue siendo el único
  dueño de las existencias.

## Consecuencias

### Positivas

- El Administrador puede operar el catálogo sin salir de la aplicación.
- El Vendedor consulta productos y categorías sin recibir permisos de escritura.
- La desactivación conserva la trazabilidad de ventas y compras; no se borran
  registros referenciados.
- El formulario de productos solo ofrece categorías y laboratorios activos,
  salvo la referencia actual al editar un registro histórico.
- Las reglas de código y nombre único se validan en modelo y formulario.

### Negativas

- Los catálogos auxiliares siguen requiriendo Django Admin.
- No existen imágenes, códigos de barras ni edición masiva en esta etapa.
- Un producto inactivo puede permanecer asociado a una categoría inactiva; la
  restricción solo impide desactivar categorías con productos activos.

### Riesgos

- Duplicados por diferencias de mayúsculas o espacios. Mitigación: normalización
  y comparación sin distinguir mayúsculas en modelo y formulario.
- Crecimiento del listado. Mitigación: búsqueda, filtros y paginación.
- Uso indebido de la desactivación. Mitigación: POST con CSRF, guardas de rol y
  bloqueo de categorías en uso.

## Alternativas descartadas

- **Administrar todo el catálogo desde Django Admin:** se descartó porque el
  módulo debe ser operable desde la interfaz del sistema.
- **Incluir laboratorios, formas y presentaciones en el CRUD visual:** se
  pospone para mantener el alcance centrado en productos y categorías.
- **Eliminar productos o categorías:** se descartó para no romper referencias
  históricas; se usa el campo `activo`.
- **Agregar stock al producto:** se descartó porque el stock se controla por
  lote en `inventario`.
