# ADR-002: User integrado y autorización por grupos

**Estado:** Aceptado

## Contexto

La etapa inicial requiere login, logout y una base de permisos para `Administrador` y `Vendedor`. Todavía no se conocen todos los campos adicionales que podría necesitar el usuario del sistema.

## Decisión

Usar el modelo `User` integrado de Django y crear los grupos base mediante una migración de datos. Proteger las vistas con `LoginRequiredMixin` y `RoleRequiredMixin`; los permisos por modelo se asignarán a los grupos cuando existan los modelos correspondientes.

## Consecuencias

### Positivas

- No se agrega complejidad ni una migración de usuario personalizado antes de tiempo.
- Se reutilizan hashing de contraseñas, sesiones, admin y validaciones de Django.
- Los grupos permiten una autorización inicial clara y extensible.

### Negativas

- Si luego se necesita un usuario con campos adicionales, migrar de `User` a un modelo personalizado es costoso.
- La autorización por nombre de grupo no reemplaza los permisos granulares por modelo.

### Riesgos

- Asignar permisos por nombre de grupo de forma dispersa. Mitigación: centralizar los nombres en `apps/accounts/constants.py` y usar mixins.
- Olvidar permisos al crear modelos. Mitigación: cada PR que agregue un modelo debe revisar grupos, permisos y pruebas.

## Alternativas descartadas

- **Modelo de usuario personalizado desde el inicio:** se descartó porque el alcance no define campos adicionales y aumenta el costo inicial.
- **Autenticación propia:** prohibida por seguridad y por las convenciones de Django.
- **Permisos solo por `is_staff`:** insuficiente para distinguir Administrador de Vendedor.
