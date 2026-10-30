# ADR-005: Registro y consulta de clientes

**Estado:** Aceptado

## Contexto

El alcance del sistema incluye registrar información de clientes cuando
corresponda. El prototipo de ventas muestra un selector y un buscador de cliente,
pero el PDF de la actividad no incluye un prototipo ni una lista de campos para
el módulo de clientes. La app `clientes` solo tenía una página de alcance.

Para avanzar por módulos se necesita el primer CRUD funcional del proyecto y un
patrón reutilizable para las siguientes entidades.

## Decisión

Implementar en `apps/clientes`:

- Modelo `Cliente` con nombre obligatorio, tipo y número de documento
  opcionales, teléfono opcional, estado activo y datos de auditoría.
- Documento opcional: si se registra, el tipo y el número deben ingresarse
  juntos; el número es único por tipo.
- Vistas de listado, registro y detalle.
- Búsqueda por nombre, documento o teléfono, filtro por estado y paginación de
  20 registros.
- Sin campos de correo ni dirección en esta etapa.
- Sin edición ni eliminación de clientes todavía.
- `LoginRequiredMixin` en las vistas. La autorización por grupo se aplicará
  cuando se definan los permisos por modelo.
- El historial comercial se muestra como aviso hasta que exista el módulo de
  ventas.
- Registro del modelo en Django Admin.

## Consecuencias

### Positivas

- El módulo cubre el registro y la consulta solicitados sin adelantar reglas de
  ventas.
- El documento opcional permite registrar clientes que no presentan
  identificación, sin perder la validación de unicidad cuando sí la presentan.
- El listado con búsqueda y filtro facilita la consulta operativa.
- La auditoría (`creado_por`, `creado_en`, `actualizado_en`) deja trazabilidad
  básica.
- El patrón de modelo, formulario, vistas, plantillas y pruebas puede
  reutilizarse en los siguientes módulos.

### Negativas

- La ficha no muestra aún historial de ventas ni permite editar o desactivar
  clientes desde la interfaz.
- No hay permisos por rol específicos para clientes; por ahora basta con estar
  autenticado.
- El documento se valida por tipo y número, pero no se normaliza a un formato
  único de CI o NIT.

### Riesgos

- Duplicados por diferencias de formato en el documento. Mitigación: la
  búsqueda y el formulario comparan sin distinguir mayúsculas; más adelante se
  puede agregar normalización por tipo.
- Crecimiento del listado. Mitigación: paginación y búsqueda ya implementadas.
- Cambios futuros en los campos de cliente. Mitigación: migraciones nuevas, sin
  editar la migración inicial.

## Alternativas descartadas

- **Incluir correo y dirección ahora:** se descartó por decisión del equipo para
  mantener el alcance mínimo de esta etapa.
- **Documento obligatorio:** se descartó porque no todos los clientes de una
  farmacia presentan documento al comprar.
- **CRUD completo con edición y eliminación:** fuera del alcance solicitado para
  esta etapa.
- **Implementar el historial comercial en clientes:** se acoplaría con ventas
  antes de que ese módulo exista. Se pospone.
