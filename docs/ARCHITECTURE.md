# Arquitectura — Farmacia Lufar

**Estado:** base funcional con autenticación y gestión de usuarios/roles, módulo de clientes (registro, consulta e historial), módulo de ventas (registro, consulta y ticket) y reportes de solo lectura de ventas, compras e inventario. Los modelos de catálogo, compras e inventario ya existen; sus capas de servicio y vistas siguen pendientes.

## 1. Visión general

Farmacia Lufar será un sistema web local construido como un **monolito modular con Django**, usando el patrón MVT (Modelo–Vista–Plantilla) y renderizado del lado del servidor. La interfaz no depende de una SPA, de una API REST independiente ni de CDN.

```mermaid
flowchart TB
    Usuario[Usuario] --> Navegador[Navegador web]
    Navegador -->|HTTP + sesión| URLs[config/urls.py]
    URLs --> Apps[Apps Django]
    Apps --> Vistas[Vistas y formularios]
    Vistas --> Plantillas[Plantillas Django]
    Vistas --> ORM[ORM de Django]
    ORM --> SQLite[(SQLite local)]
    Plantillas --> Estaticos[CSS, JS e imágenes locales]
    Vistas --> Permisos[Autenticación y grupos]
```

## 2. Responsabilidad de las aplicaciones

| App | Responsabilidad | Estado |
|---|---|---|
| `core` | Dashboard, mixins, filtros, utilidades compartidas y `ConfiguracionSistema`. No contiene entidades de negocio. | Base implementada |
| `accounts` | Login, logout, perfil, usuarios, grupos `Administrador` y `Vendedor`, permisos por modelo y autorización por rol. | Implementado |
| `catalogo` | Categorías, laboratorios, formas farmacéuticas, presentaciones, productos y precios. | Modelos y admin implementados; CRUD visual pendiente |
| `inventario` | Existencias, lotes y movimientos de entrada, salida y ajuste. | Modelos `Lote` y `MovimientoInventario`; servicios y vistas pendientes |
| `compras` | Proveedores, compras, detalle y recepción de mercadería. | Modelos `Proveedor`, `Compra` y `DetalleCompra`; vistas pendientes |
| `clientes` | Datos de clientes e historial comercial. | Registro, consulta e historial implementados |
| `ventas` | Ventas, detalles, cálculo de totales, cambio y ticket. | Registro, consulta y ticket implementados |
| `reportes` | Consultas e informes de solo lectura. No tendrá modelos propios. | Reportes de ventas, compras e inventario implementados |

### Decisión sobre proveedores

El alcance menciona proveedores, pero define ocho aplicaciones y no incluye una app `proveedores`. Para no crear una novena app sin necesidad, el modelo `Proveedor` pertenecerá a `compras`, que es el contexto donde se usa. Si en el futuro la gestión de proveedores crece de forma independiente, podrá extraerse con una migración planificada. Ver `docs/adr/ADR-004-proveedores-en-compras.md`.

## 3. Autenticación y autorización

```mermaid
sequenceDiagram
    actor U as Usuario
    participant L as LoginView
    participant A as Django Auth
    participant S as Sesión
    participant V as Vista protegida

    U->>L: POST /cuentas/login/ + CSRF
    L->>A: authenticate(username, password)
    A-->>L: Usuario válido
    L->>S: Inicia sesión
    L-->>U: Redirección al dashboard
    U->>V: GET /catalogo/
    V->>S: ¿Usuario autenticado?
    S-->>V: Sí
    V->>V: LoginRequiredMixin / RoleRequiredMixin
    V-->>U: Página permitida o 403
```

- Se usa el modelo `User` integrado de Django. No se crea un modelo de usuario propio en esta etapa.
- Los grupos base se crean mediante la migración `accounts.0001_create_default_groups`.
- `apps/accounts/permissions.py` es la fuente de verdad de la autorización:
  `MODULE_ACCESS` define qué módulos ve cada rol, `MANAGED_APPS` limita las apps
  cuyos permisos se sincronizan y `SELLER_PERMISSIONS` fija el menor privilegio
  del Vendedor.
- `sync_role_permissions()` se conecta a `post_migrate` desde
  `AccountsConfig.ready()` y también se ejecuta con
  `python manage.py sync_roles`. Asigna al Administrador todos los permisos de
  `catalogo`, `compras`, `inventario`, `clientes` y `ventas`, y al Vendedor solo
  los codenames declarados en `SELLER_PERMISSIONS`. La operación es idempotente y
  conserva permisos personalizados ajenos a las apps gestionadas.
- `RoleRequiredMixin` exige autenticación y pertenencia a un grupo permitido.
  Los superusuarios siempre tienen acceso y un usuario autenticado sin el rol
  recibe `403`.
- Matriz de acceso: el Vendedor usa panel general, catálogo (consulta),
  clientes, ventas y reporte de ventas. Inventario, compras, reportes de
  compras/inventario y gestión de usuarios son exclusivos del Administrador.
- La gestión visual de usuarios vive en `accounts` (`usuario_crear`,
  `usuario_editar`, `usuario_estado`). No hay eliminación: solo activación y
  desactivación. Se protege la propia cuenta, el último administrador activo y
  la edición de superusuarios por parte de administradores no superusuarios.
- El login y el logout usan las vistas de Django y protección CSRF. El logout solo acepta POST.

## 4. Límites entre módulos

Estas reglas buscan evitar dependencias circulares y duplicación de lógica:

1. Cada app es dueña de sus modelos, migraciones, formularios, vistas, URLs y pruebas.
2. Las referencias entre modelos se harán con cadenas (`"catalogo.Producto"`) para evitar importaciones circulares.
3. `catalogo` es dueño del maestro de productos. `inventario` referencia productos, pero no modifica sus datos maestros.
4. `inventario` es el único módulo que debe alterar existencias. Compras y ventas deberán solicitar movimientos a través de una función de servicio transaccional.
5. `compras` es dueño de `Proveedor`, `Compra` y `DetalleCompra`.
6. `clientes` es dueño de `Cliente`. `ventas` podrá referenciarlo, pero no modificar sus datos maestros.
7. `ventas` es dueño de `Venta` y `DetalleVenta`. En esta etapa el único medio de pago es efectivo, por lo que no existe un modelo `Pago` separado.
8. `reportes` solo consulta; no debe escribir datos ni crear dependencias inversas.
9. `core` contiene infraestructura compartida, no reglas de negocio de otros módulos.
10. Las operaciones que afecten varias tablas (venta + inventario, compra + inventario) se ejecutarán dentro de `transaction.atomic()` y con bloqueo de stock cuando corresponda.
11. Las vistas deben mantenerse delgadas. Cuando una operación tenga varias reglas, se extraerá a un servicio del módulo correspondiente. El registro de ventas usa `apps/ventas/services.py`.
12. `catalogo` es dueño del precio de venta; `ventas` guarda una copia histórica en `DetalleVenta` y no modifica el producto.

## 5. Flujo de venta

```mermaid
sequenceDiagram
    actor V as Vendedor
    participant F as Formulario y formset
    participant S as registrar_venta()
    participant DB as SQLite

    V->>F: Cliente opcional, efectivo y líneas
    F->>F: Valida clientes y productos activos, cantidades y mínimo una línea
    F->>S: Datos limpios
    S->>S: Calcula total, valida efectivo y evita productos repetidos
    S->>DB: BEGIN
    S->>DB: INSERT Venta
    S->>DB: INSERT DetalleVenta (copia de código, nombre y precio)
    S->>DB: COMMIT
    S-->>F: Venta registrada
    F-->>V: Redirección a la ficha de la venta
    V->>F: Abre el ticket imprimible de 80 mm
```

Reglas de esta etapa:

- El cliente es opcional; si no se selecciona, la venta queda como
  **Consumidor final**.
- El precio unitario se toma del catálogo y se copia al detalle. El navegador no
  puede modificarlo.
- El pago es solo en efectivo. El total y el cambio se calculan en el servidor.
- La venta es inmutable: no se edita, elimina ni anula desde la interfaz.
- No se descuenta stock. La integración con `inventario` queda para una etapa
  posterior.
- El ticket se genera como HTML imprimible de 80 mm con CSS `@media print`; no
  se usa una librería PDF.

## 6. Convenciones del equipo

- **Idioma:** nombres de dominio y textos de interfaz en español; APIs y conceptos propios de Django en inglés. Evitar tildes en identificadores de código (`Categoria`, no `Categoría`).
- **Modelos:** nombres en singular (`Producto`, `Compra`, `Venta`) y `related_name` explícitos en las relaciones.
- **URLs:** namespace por app (`catalogo:index`, `ventas:index`). Los nombres de ruta se mantienen estables.
- **Plantillas:** una carpeta por app dentro de `templates/`; los componentes compartidos van en `templates/includes/`.
- **Formularios:** validación del lado del servidor con `forms.ModelForm` o `forms.Form`; no confiar en la validación del navegador.
- **Estilos y scripts:** archivos locales en `static/`. No agregar CDN ni fuentes externas.
- **Migraciones:** una app por migración lógica; no editar migraciones ya aplicadas; crear una nueva para corregir.
- **Pruebas:** cada app tendrá pruebas propias; las pruebas transversales viven en `tests/`. Toda regla de negocio nueva debe incluir pruebas.
- **Seguridad:** toda vista de gestión debe ser autenticada; los módulos
  restringidos usan `RoleRequiredMixin`; toda escritura debe usar POST + CSRF;
  no se guardan contraseñas ni secretos en el repositorio.
- **Git:** una rama por funcionalidad, PR hacia `develop` y revisión del otro desarrollador.

## 7. Base de datos y migraciones

La base inicial es SQLite (`db.sqlite3`), ignorada por Git. SQLite es suficiente para el desarrollo local y una única instancia, pero tiene limitaciones de concurrencia. Si el sistema se despliega para varios usuarios simultáneos, se evaluará PostgreSQL antes de la puesta en producción.

El esquema ya cubre el modelo relacional completo: `clientes` (Cliente), `catalogo` (Categoria, Laboratorio, FormaFarmaceutica, Presentacion y Producto), `ventas` (Venta y DetalleVenta), `inventario` (Lote y MovimientoInventario), `compras` (Proveedor, Compra y DetalleCompra) y `core` (ConfiguracionSistema). El detalle de tablas, claves y restricciones está en `docs/modelo-er-relacional.pdf`.

Quedan pendientes las capas de servicio y las vistas:

1. `inventario`: servicios transaccionales de entrada, salida y ajuste con lógica FEFO.
2. `compras`: vistas de proveedores y recepción de compras que generen movimientos de entrada.
3. `ventas`: integrar la salida de inventario en `registrar_venta`.
4. `catalogo`: CRUD visual de productos y catálogos auxiliares.

## 8. Roadmap sugerido

| Fase | Entregable | Dependencias |
|---|---|---|
| 0 | Autenticación, usuarios, roles y permisos por modelo (implementado) | — |
| 1 | Catálogo mínimo (implementado) y CRUD visual de productos | `accounts`, `core` |
| 2 | Inventario y movimientos transaccionales | Fase 1 |
| 3 | Clientes: registro, consulta e historial (implementado) | `accounts` |
| 4 | Compras, proveedores y recepción | Fases 1 y 2 |
| 5 | Ventas: registro, total, cambio y ticket (implementado); salida de inventario pendiente | Fases 1, 2 y 3 |
| 6 | Reportes de ventas, compras y stock (implementado) | Fases 2, 4 y 5 |
| 7 | Endurecimiento de seguridad, backups y despliegue | Todas |

### Reparto sugerido para dos desarrolladores

- **Desarrollador A:** `catalogo`, `inventario`, `compras`.
- **Desarrollador B:** `clientes`, `ventas`, `reportes`.
- **Cambios compartidos:** `core` y `accounts` requieren revisión del otro desarrollador.
- Las integraciones entre ventas/compras e inventario se acuerdan antes de implementarse y se prueban en una rama conjunta.

## 9. Decisiones registradas

- [ADR-001: Monolito modular con Django MVT](adr/ADR-001-arquitectura-monolitica-modular.md)
- [ADR-002: User integrado y autorización por grupos](adr/ADR-002-user-integrado-y-grupos.md)
- [ADR-003: SQLite y operación local sin CDN](adr/ADR-003-sqlite-local-sin-cdn.md)
- [ADR-004: Proveedores dentro de compras](adr/ADR-004-proveedores-en-compras.md)
- [ADR-005: Registro y consulta de clientes](adr/ADR-005-clientes-registro-consulta.md)
- [ADR-006: Ventas con catálogo mínimo y ticket HTML](adr/ADR-006-ventas-catalogo-minimo-ticket.md)
