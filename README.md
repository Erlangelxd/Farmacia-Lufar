# Farmacia Lufar — Sistema de gestión

Sistema web local para centralizar productos, inventario, compras, clientes,
proveedores, ventas, usuarios y reportes de Farmacia Lufar. Está construido con
Python, Django, SQLite y plantillas renderizadas en el servidor.

> **Estado actual:** estructura base funcional con autenticación, gestión de
> usuarios y roles, navegación, dashboard provisional, módulo de catálogo con
> productos y categorías, módulo de inventario con lotes, movimientos y alertas
> de stock, módulo de clientes con registro y consulta, módulo de ventas con
> cálculo de totales y ticket imprimible, módulo de compras con proveedores y
> recepción que actualiza inventario, reportes de solo lectura y esquema de
> datos completo. **No incluye todavía integración automática de stock con
> ventas ni edición o anulación de ventas.**

## 1. Objetivo y alcance inicial

El objetivo de esta entrega es dejar preparada una base mantenible para que dos
desarrolladores puedan implementar el sistema por módulos, sin rehacer la
autenticación, la navegación ni la organización del proyecto.

### Incluido

- Proyecto Django de Farmacia Lufar con configuración en `config/`.
- Ocho aplicaciones: `core`, `accounts`, `catalogo`, `inventario`, `compras`,
  `clientes`, `ventas` y `reportes`.
- Login y logout con el sistema de autenticación de Django.
- Grupos base `Administrador` y `Vendedor` creados por migración.
- Permisos por modelo sincronizados para cada grupo después de migrar.
- Gestión visual de usuarios: alta, edición, asignación de rol, activación y
  desactivación.
- Restricción de vistas mediante autenticación y roles, con `403` para los
  módulos no permitidos.
- Interfaz administrativa responsive con plantilla base, menú, encabezado,
  mensajes y área de contenido.
- Dashboard con indicadores de ejemplo marcados como **provisionales**.
- Módulo de clientes: registro, listado con búsqueda y filtro por estado,
  ficha de consulta, historial de ventas y administración desde Django Admin.
- Módulo de catálogo: productos (código, nombre, precio de venta, stock mínimo
  y estado) y categorías, con alta, edición, búsqueda, filtros y
  activación/desactivación.
- Catálogos auxiliares de `Laboratorio`, `FormaFarmaceutica` y `Presentacion`
  administrados desde Django Admin.
- Módulo de inventario: existencias por producto, lotes con vencimiento, alta
  con stock inicial, edición de datos, movimientos de entrada, salida y ajuste,
  y alertas de stock bajo y vencimientos.
- Módulo de ventas: registro con líneas de detalle, cálculo de total y cambio,
  listado con búsqueda y filtro por cliente, ficha de consulta y ticket
  imprimible de 80 mm.
- Módulo de compras: proveedores con alta, edición y activación, compras con
  líneas de detalle, edición y anulación de borradores, y recepción sobre lotes
  existentes que registra entradas de inventario.
- Módulo de reportes de solo lectura: ventas por periodo y vendedor, compras
  por proveedor y estado, e inventario con stock por lote, valor del
  inventario, alertas de stock bajo y vencimientos.
- Estilos y JavaScript locales, sin CDN.
- Pruebas transversales y pruebas propias de clientes, catálogo, inventario,
  compras y ventas.
- Documentación de arquitectura y decisiones en `docs/`.

### Fuera de alcance en esta entrega

- Edición, eliminación o anulación de ventas.
- Edición y eliminación de clientes; su historial comercial ya se muestra en la
  ficha.
- Integración automática del stock con ventas; la recepción de compras ya
  actualiza inventario.
- Facturación fiscal, descuentos y reglas comerciales avanzadas.
- Recuperación de contraseña por correo.
- Despliegue en producción, HTTPS y backups automáticos.
- Aplicación móvil o API REST independiente.

## 2. Arquitectura y responsabilidades

Se usa un **monolito modular Django con patrón MVT**: una sola aplicación
desplegable, una sola base de datos y módulos separados por dominio. No hay SPA,
API REST separada, React ni servicios en la nube.

| Aplicación | Responsabilidad | Estado |
|---|---|---|
| `core` | Dashboard, mixins, filtros y utilidades compartidas. | Base implementada |
| `accounts` | Login, logout, perfil, usuarios, roles, permisos por modelo y autorización por rol. | Implementado |
| `catalogo` | Productos, categorías, laboratorios, formas farmacéuticas, presentaciones y precios. | CRUD visual de productos y categorías implementado; catálogos auxiliares en admin |
| `inventario` | Existencias, lotes y movimientos de entrada, salida y ajuste. | Existencias, CRUD de lotes, movimientos y alertas implementados |
| `compras` | Proveedores, compras, detalle y recepción de mercadería. | Proveedores, borradores, recepción y anulación implementados |
| `clientes` | Datos de clientes e historial comercial. | Registro, consulta e historial implementados |
| `ventas` | Ventas, detalles, cálculo de totales, cambio y ticket. | Registro, consulta y ticket implementados |
| `reportes` | Consultas e informes de solo lectura. | Reportes de ventas, compras e inventario implementados |

Decisiones importantes:

- **Proveedores vive en `compras`.** El alcance menciona proveedores, pero no
  define una novena app. Se mantiene la estructura de ocho aplicaciones.
- **El usuario es el `User` integrado de Django.** No se creó un modelo de
  usuario personalizado en esta etapa.
- **Los permisos por modelo se sincronizan automáticamente.** El módulo
  `apps/accounts/permissions.py` es la fuente de verdad: `Administrador`
  recibe todos los permisos de `catalogo`, `compras`, `inventario`, `clientes`
  y `ventas`; `Vendedor` recibe solo los permisos operativos definidos en
  `SELLER_PERMISSIONS`. La sincronización corre en `post_migrate` y también
  puede ejecutarse con `python manage.py sync_roles`.
- **El acceso a los módulos se controla con `RoleRequiredMixin`.** El Vendedor
  accede a catálogo (consulta), clientes, ventas y al reporte de ventas; los
  módulos de inventario, compras, reporte de compras, reporte de inventario y
  administración de usuarios son exclusivos del Administrador. Los
  superusuarios siempre tienen acceso.
- **Clientes no guarda correo ni dirección en esta etapa.** El documento es
  opcional; si se registra, el tipo y el número deben ingresarse juntos y el
  número es único por tipo.
- **Inventario es el único dueño de las existencias.** Los cambios de stock se
  realizan con los servicios transaccionales de `apps/inventario/services.py`,
  que actualizan el lote y registran un movimiento inmutable. Compras y ventas
  deberán usar esos mismos servicios para no alterar el stock directamente.
- **El catálogo tiene CRUD visual para productos y categorías.** `Producto`
  pertenece a una categoría y puede referenciar laboratorio, forma farmacéutica
  y presentación. El Vendedor solo consulta; el Administrador crea, edita y
  desactiva. Una categoría con productos activos no puede desactivarse. Los
  catálogos auxiliares se administran desde Django Admin.
- **El inventario se organiza por lotes.** El stock inicial se registra al
  crear el lote; después solo cambia con movimientos de entrada, salida o
  ajuste. Un lote con existencias no puede desactivarse y los movimientos no se
  editan ni eliminan. Las alertas de stock bajo comparan el total de lotes
  activos con el `stock_minimo` del producto.
- **Las ventas son inmutables en esta etapa.** No se editan, eliminan ni anulan
  desde la interfaz. El admin de ventas es de solo lectura para proteger los
  registros financieros.
- **El pago es solo en efectivo.** La venta guarda el monto recibido y calcula
  el cambio; no se procesan tarjetas ni otros medios.
- **La venta conserva una copia histórica del producto.** Cada detalle guarda
  código, nombre y precio unitario del momento de la venta, aunque el catálogo
  cambie después. El stock no se descuenta todavía.
- **El ticket es HTML imprimible de 80 mm.** Se genera con plantillas y CSS de
  impresión locales, sin librerías PDF ni CDN.

El detalle completo, los límites entre módulos, el roadmap y las convenciones
están en [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md).

## 3. Requisitos de instalación

- **Python 3.12 o superior.** Django 6.1.1 requiere Python `>=3.12`.
- **pip** para instalar dependencias.
- **Git** para el control de versiones.
- **SQLite**, incluido en la biblioteca estándar de Python; no hay que instalar
  un servidor de base de datos.
- Un editor como Visual Studio Code (opcional).
- Sistema Linux. Los comandos de esta guía usan `python3` para crear el entorno
  y `python` dentro del entorno virtual.

Verifica las versiones desde la raíz del repositorio:

```bash
python3 --version
git --version
```

## 4. Creación y activación del entorno virtual

Desde la raíz del repositorio:

```bash
python3 -m venv .venv
source .venv/bin/activate
python --version
```

El indicador de la terminal debe mostrar el entorno virtual activo. Para salir:

```bash
deactivate
```

En Debian/Ubuntu, si `venv` no está disponible, instala el paquete del sistema:

```bash
sudo apt install python3-venv
```

## 5. Instalación de dependencias

Con el entorno virtual activo:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -c "import django; print(django.get_version())"
```

La última instrucción debe mostrar `6.1.1`. Las dependencias quedan instaladas
localmente; después de esta instalación el sistema no necesita Internet para
funcionar.

## 6. Migraciones de la base de datos

```bash
python manage.py migrate
```

Esto crea `db.sqlite3` y aplica las migraciones de Django, de `accounts`, de
`clientes`, de `catalogo` y de `ventas`. La migración
`accounts.0001_create_default_groups` crea los grupos base de forma idempotente
y la señal `post_migrate` les asigna los permisos por modelo;
`clientes.0001_initial` crea la tabla de clientes; `catalogo.0001_initial` crea
el modelo mínimo `Producto`; y `ventas.0001_initial` crea `Venta` y
`DetalleVenta`. Puedes verificar los grupos con:

```bash
python manage.py shell -c "from django.contrib.auth.models import Group; print(list(Group.objects.values_list('name', flat=True)))"
```

El resultado esperado es:

```text
['Administrador', 'Vendedor']
```

`db.sqlite3` está incluido en `.gitignore`; no debe subirse al repositorio.

Cuando se agreguen modelos en la siguiente etapa:

```bash
python manage.py makemigrations
python manage.py migrate
```

## 7. Creación del superusuario

```bash
python manage.py createsuperuser
```

El superusuario puede entrar a Django Admin en `/admin/` y también acceder a la
vista de usuarios del sistema. Para asignar un rol a una cuenta existente puedes
usar el admin o este comando, reemplazando `CAMBIA_ESTE_USUARIO`:

```bash
python manage.py shell -c "from django.contrib.auth import get_user_model; from django.contrib.auth.models import Group; u = get_user_model().objects.get(username='CAMBIA_ESTE_USUARIO'); u.groups.add(Group.objects.get(name='Vendedor'))"
```

Roles disponibles:

- `Administrador`: acceso completo a catálogo, inventario, compras, clientes,
  ventas, reportes y gestión de usuarios. También recibe todos los permisos por
  modelo de las apps de negocio.
- `Vendedor`: acceso a catálogo (consulta), clientes, ventas y reporte de
  ventas. Inventario, compras, reportes de compras/inventario y la gestión de
  usuarios le devuelven `403`.

La gestión visual está en `/cuentas/usuarios/`. Para sincronizar los permisos
por modelo sin ejecutar migraciones:

```bash
python manage.py sync_roles
```

## 8. Ejecución de las pruebas

```bash
python manage.py check
python manage.py test
python manage.py makemigrations --check --dry-run
```

Las 143 pruebas actuales cubren:

- Carga de las ocho aplicaciones.
- Resolución de las rutas iniciales.
- Creación de los grupos base.
- Redirección al login de todas las vistas de gestión.
- Protección CSRF del login, del registro de clientes y del registro de ventas.
- Login válido e inválido.
- Mensaje de bienvenida después del login.
- Logout solo por POST y limpieza de sesión.
- Acceso del Vendedor al dashboard, catálogo, clientes, ventas y reportes
  permitidos.
- Respuesta `403` del Vendedor en inventario, compras, reportes de
  compras/inventario y gestión de usuarios.
- Acceso del Administrador a todos los módulos y reportes.
- Visibilidad del menú y de los enlaces según el rol.
- Sincronización idempotente de permisos por modelo y matriz de menor
  privilegio del Vendedor.
- Alta y edición de usuarios, asignación de rol, contraseña opcional y
  conservación de grupos personalizados.
- Protección de la propia cuenta, del último administrador y de los
  superusuarios.
- Plantilla personalizada para páginas no encontradas (`404`).
- Validación del modelo `Cliente`: documento opcional, coherencia tipo/número,
  unicidad y normalización de espacios.
- Validación del formulario de clientes: nombre obligatorio, documento
  duplicado y ausencia de campos de correo y dirección.
- Listado de clientes con búsqueda por nombre, documento o teléfono, filtro por
  estado y paginación.
- Registro de clientes, asignación de `creado_por`, mensaje de éxito, ficha de
  consulta e historial de ventas.
- Validación del modelo `Producto`: normalización de código y nombre, unicidad
  sin distinguir mayúsculas, precio no negativo y orden por nombre.
- Validación del modelo `Categoria`: normalización y unicidad sin distinguir
  mayúsculas, y bloqueo al desactivar una categoría con productos activos.
- Formularios y vistas de catálogo: alta y edición de productos y categorías,
  búsqueda, filtros por categoría y estado, activación/desactivación y acceso
  de consulta del Vendedor.
- Servicio transaccional de ventas: cálculo de total y cambio, copia histórica
  de producto, cliente opcional, producto inactivo, cantidades inválidas,
  productos duplicados, efectivo insuficiente, total máximo y rollback.
- Formularios de venta: cliente opcional, solo clientes y productos activos,
  pago en efectivo, mínimo una línea y validación de cantidades.
- Vistas de ventas: listado con búsqueda por número, cliente o producto, filtro
  por cliente, paginación, registro, detalle, ticket imprimible y `404`.
- Ticket de 80 mm con datos de la venta, detalle, total, efectivo, cambio y
  acciones de impresión.

Las pruebas usan una base de datos temporal y no modifican `db.sqlite3`.

## 9. Inicio del servidor local

```bash
python manage.py runserver
```

Abre `http://127.0.0.1:8000/` en el navegador. Para detener el servidor usa
`Ctrl+C`.

| Ruta | Descripción |
|---|---|
| `/` | Dashboard; requiere sesión. |
| `/cuentas/login/` | Inicio de sesión. |
| `/cuentas/` | Perfil de la cuenta autenticada. |
| `/cuentas/usuarios/` | Listado y filtros de usuarios; solo Administrador o superusuario. |
| `/cuentas/usuarios/nuevo/` | Alta de usuario con rol y contraseña inicial. |
| `/cuentas/usuarios/<id>/editar/` | Edición de datos, rol, estado y contraseña. |
| `/cuentas/usuarios/<id>/estado/` | Activación o desactivación por POST. |
| `/catalogo/` | Listado y filtros de productos. |
| `/catalogo/productos/nuevo/` | Alta de producto; solo Administrador. |
| `/catalogo/productos/<id>/editar/` | Edición de producto; solo Administrador. |
| `/catalogo/productos/<id>/estado/` | Activación o desactivación de producto por POST. |
| `/catalogo/categorias/` | Listado de categorías y sus productos. |
| `/catalogo/categorias/nueva/` | Alta de categoría; solo Administrador. |
| `/catalogo/categorias/<id>/editar/` | Edición de categoría; solo Administrador. |
| `/catalogo/categorias/<id>/estado/` | Activación o desactivación de categoría por POST. |
| `/inventario/` | Existencias por producto, alertas de stock y vencimientos. |
| `/inventario/lotes/` | Listado y filtros de lotes. |
| `/inventario/lotes/nuevo/` | Alta de lote con stock inicial; solo Administrador. |
| `/inventario/lotes/<id>/editar/` | Edición de datos del lote; solo Administrador. |
| `/inventario/lotes/<id>/estado/` | Activación o desactivación de lote por POST. |
| `/inventario/movimientos/` | Historial de movimientos de inventario. |
| `/inventario/movimientos/nuevo/` | Registro de entrada, salida o ajuste. |
| `/compras/` | Listado y filtros de compras. |
| `/compras/nueva/` | Alta de compra en borrador con líneas de detalle. |
| `/compras/<id>/` | Ficha de consulta de la compra. |
| `/compras/<id>/editar/` | Edición de una compra en borrador. |
| `/compras/<id>/recibir/` | Recepción sobre lotes existentes y entrada de inventario. |
| `/compras/<id>/anular/` | Anulación de una compra en borrador por POST. |
| `/compras/proveedores/` | Listado y filtros de proveedores. |
| `/compras/proveedores/nuevo/` | Alta de proveedor. |
| `/compras/proveedores/<id>/editar/` | Edición de proveedor. |
| `/compras/proveedores/<id>/estado/` | Activación o desactivación de proveedor por POST. |
| `/clientes/` | Listado y búsqueda de clientes. |
| `/clientes/nuevo/` | Registro de un cliente. |
| `/clientes/<id>/` | Ficha de consulta e historial de ventas del cliente. |
| `/ventas/` | Listado y búsqueda de ventas. |
| `/ventas/nueva/` | Registro de una venta. |
| `/ventas/<id>/` | Ficha de consulta de una venta. |
| `/ventas/<id>/ticket/` | Ticket imprimible de 80 mm. |
| `/reportes/` | Página inicial de reportes. |
| `/reportes/ventas/` | Reporte de ventas por periodo y vendedor. |
| `/reportes/compras/` | Reporte de compras por periodo, proveedor y estado. |
| `/reportes/inventario/` | Reporte de inventario: stock por lote y alertas. |
| `/admin/` | Administración de Django, incluidos los catálogos auxiliares. |

Los productos se cargan y editan desde `/catalogo/` con una cuenta
Administrador. Deben estar activos y tener un precio de venta para aparecer en
el formulario de ventas. Los catálogos auxiliares de laboratorios, formas
farmacéuticas y presentaciones se cargan desde `/admin/`.

El inventario se opera desde `/inventario/` con una cuenta Administrador. Al
crear un lote se puede indicar el stock inicial; los cambios posteriores se
registran como movimientos de entrada, salida o ajuste. El sistema no permite
dejar el stock en negativo ni desactivar un lote con existencias.

Las compras se gestionan desde `/compras/` con una cuenta Administrador. Una
compra nace en borrador, puede editarse o anularse mientras siga en ese estado,
y al recibirse exige un lote existente por cada línea. La recepción registra una
entrada de inventario por línea dentro de una transacción; las compras recibidas
son de solo lectura y no se eliminan. Los proveedores se administran desde
`/compras/proveedores/` y solo los activos aparecen al crear una compra.

Si el puerto está ocupado:

```bash
python manage.py runserver 8001
```

Los estilos, el JavaScript y el logo se sirven desde `static/` con el servidor
de desarrollo. No hay CDN ni dependencias de fuentes externas.

## 10. Estrategia básica de ramas Git

El repositorio local ya está inicializado con las ramas `main` y `develop` en el
commit inicial. Solo falta agregar el remoto de GitHub.

El repositorio debe tener dos ramas permanentes y ramas cortas por funcionalidad.

| Rama | Uso |
|---|---|
| `main` | Código estable y entregable. Solo recibe merges desde `develop`. |
| `develop` | Integración continua del equipo. |
| `feature/<modulo>-<tema>` | Nueva funcionalidad. Ejemplo: `feature/catalogo-modelos`. |
| `fix/<modulo>-<tema>` | Corrección. Ejemplo: `fix/ventas-total-duplicado`. |
| `docs/<tema>` | Documentación. |

Flujo recomendado para cada tarea:

```bash
git switch develop
git pull --ff-only
git switch -c feature/catalogo-modelos
# implementar y probar
git add .
git commit -m "feat(catalogo): agrega modelos de productos"
git push -u origin feature/catalogo-modelos
```

Luego se abre un Pull Request hacia `develop`, lo revisa el otro desarrollador
y se integra. Cuando `develop` está estable, se abre un PR de `develop` hacia
`main` y se etiqueta la versión.

### Reglas para el equipo de dos desarrolladores

1. No hacer commits directos a `main` ni a `develop`.
2. Una funcionalidad por rama y por Pull Request.
3. Actualizar `develop` antes de crear una rama.
4. Mantener los cambios de `core` y `accounts` con revisión del compañero.
5. No editar migraciones ya aplicadas; crear una migración nueva.
6. Coordinar migraciones que toquen la misma app para evitar conflictos.
7. No subir `db.sqlite3`, `.env`, `staticfiles/` ni archivos locales del editor.
8. Ejecutar `python manage.py check` y `python manage.py test` antes de abrir el PR.
9. Usar mensajes de commit claros; se sugiere Conventional Commits:
   `feat:`, `fix:`, `docs:`, `test:`, `refactor:`, `chore:`.
10. Si dos ramas crean migraciones en la misma app, resolver el conflicto
    regenerando la migración sobre la versión actual de `develop`, no editando
    el archivo ya aplicado.

### Reparto sugerido para la siguiente etapa

- **Desarrollador A:** `catalogo`, `inventario` y `compras`.
- **Desarrollador B:** `clientes`, `ventas` y `reportes`.
- **Compartido:** `core` y `accounts`, con revisión cruzada.

### Publicación inicial en GitHub

Si el repositorio aún no tiene remoto:

```bash
git remote add origin git@github.com:USUARIO/Farmacia-Lufar.git
git push -u origin main
git push -u origin develop
```

Reemplaza `USUARIO` por la cuenta u organización correspondiente.

## Configuración y seguridad

El proyecto lee variables de entorno del proceso. No carga automáticamente un
archivo `.env` en esta etapa; si lo usas, expórtalo en la shell antes de ejecutar
Django.

| Variable | Valor local por defecto | Uso |
|---|---|---|
| `DJANGO_DEBUG` | `True` | Modo de desarrollo. En producción debe ser `False`. |
| `DJANGO_SECRET_KEY` | Clave insegura solo para desarrollo | Clave criptográfica. Obligatoria cuando `DEBUG=False`. |
| `DJANGO_ALLOWED_HOSTS` | `localhost,127.0.0.1,[::1]` | Hosts permitidos, separados por coma. |
| `DJANGO_TIME_ZONE` | `America/La_Paz` | Zona horaria del negocio. Ajustable si corresponde. |

Genera una clave para un entorno real:

```bash
python -c "from django.core.management.utils import get_random_secret_key; print(get_random_secret_key())"
export DJANGO_SECRET_KEY="PEGA_AQUI_LA_CLAVE_GENERADA"
export DJANGO_DEBUG=False
```

Controles ya presentes:

- Autenticación y sesiones de Django.
- CSRF en formularios y logout por POST.
- Contraseñas con hashing de Django y validadores de seguridad.
- `LoginRequiredMixin` en el perfil y `RoleRequiredMixin` en los módulos, con
  `403` para los roles no autorizados.
- Guardas para no desactivar la propia cuenta, no quitarse el rol
  Administrador, no eliminar al último administrador activo y no permitir que
  un administrador no superusuario edite superusuarios.
- Contraseñas opcionales al editar, validadas con los validadores de Django.
- Cabeceras `X-Frame-Options: DENY`, `X-Content-Type-Options: nosniff` y
  `Referrer-Policy: same-origin`.
- `db.sqlite3`, `.env` y archivos locales excluidos de Git.

Antes de un despliegue real se debe configurar HTTPS, `DJANGO_DEBUG=False`,
`DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`, `collectstatic`, backups y evaluar
el paso a PostgreSQL si habrá varios usuarios concurrentes.

## Estructura del proyecto

```text
.
├── manage.py
├── requirements.txt
├── .gitignore
├── README.md
├── CHANGELOG.md
├── config/
│   ├── __init__.py
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
├── apps/
│   ├── __init__.py
│   ├── core/
│   │   ├── apps.py
│   │   ├── mixins.py
│   │   ├── models.py
│   │   ├── urls.py
│   │   ├── views.py
│   │   ├── admin.py
│   │   ├── tests.py
│   │   └── templatetags/
│   ├── accounts/
│   │   ├── apps.py
│   │   ├── constants.py
│   │   ├── forms.py
│   │   ├── models.py
│   │   ├── urls.py
│   │   ├── views.py
│   │   ├── admin.py
│   │   ├── tests.py
│   │   └── migrations/0001_create_default_groups.py
│   ├── catalogo/
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── forms.py
│   │   ├── models.py
│   │   ├── urls.py
│   │   ├── views.py
│   │   ├── tests.py
│   │   └── migrations/
│   ├── inventario/
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── forms.py
│   │   ├── models.py
│   │   ├── selectors.py
│   │   ├── services.py
│   │   ├── urls.py
│   │   ├── views.py
│   │   ├── tests.py
│   │   └── migrations/0001_initial.py
│   ├── compras/
│   ├── clientes/
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── forms.py
│   │   ├── models.py
│   │   ├── urls.py
│   │   ├── views.py
│   │   ├── tests.py
│   │   └── migrations/0001_initial.py
│   ├── ventas/
│   │   ├── admin.py
│   │   ├── apps.py
│   │   ├── forms.py
│   │   ├── models.py
│   │   ├── services.py
│   │   ├── urls.py
│   │   ├── views.py
│   │   ├── tests.py
│   │   └── migrations/0001_initial.py
│   └── reportes/
│       ├── apps.py
│       ├── models.py
│       ├── urls.py
│       ├── views.py
│       └── tests.py
├── templates/
│   ├── base.html
│   ├── 403.html
│   ├── 404.html
│   ├── includes/
│   ├── core/
│   ├── accounts/
│   ├── catalogo/
│   ├── inventario/
│   ├── clientes/
│   ├── ventas/
│   ├── reportes/
│   └── registration/login.html
├── static/
│   ├── css/styles.css
│   ├── js/app.js
│   ├── js/ventas.js
│   └── img/logo.svg
├── tests/
│   └── test_smoke.py
└── docs/
    ├── ARCHITECTURE.md
    └── adr/
```

## Supuestos documentados

- La zona horaria inicial es `America/La_Paz`; se puede cambiar con
  `DJANGO_TIME_ZONE` sin modificar el código.
- Los indicadores del dashboard son ejemplos visuales, no datos reales.
- Los permisos por modelo de los grupos base se sincronizan automáticamente
  tras cada migración. Un usuario sin rol no puede acceder a los módulos de
  negocio y recibe `403`.
- No hay eliminación de usuarios: solo activación y desactivación para
  conservar la trazabilidad de ventas y compras.
- No se implementó recuperación de contraseña por correo; el administrador
  puede asignar una contraseña nueva desde la edición de la cuenta.
- Proveedor se administra dentro de `compras`, junto con las compras y su
  detalle.
- Las compras nacen en borrador; solo los borradores se editan o anulan. La
  recepción exige un lote existente por línea y registra entradas de inventario;
  una compra recibida es inmutable y no se elimina.
- Cliente se registra con nombre obligatorio; tipo y número de documento son
  opcionales y deben ingresarse juntos. No se guardan correo ni dirección en
  esta etapa.
- El catálogo permite administrar productos y categorías desde la interfaz; los
  laboratorios, formas farmacéuticas y presentaciones siguen en Django Admin. No
  hay imágenes ni stock propio en el catálogo: el stock vive en `inventario`.
- El inventario se controla por lotes. El stock solo cambia por los servicios
  transaccionales de `inventario`; un lote con existencias no puede desactivarse
  y los movimientos son inmutables.
- Las ventas son inmutables: no se editan, eliminan ni anulan desde la
  interfaz. El admin de ventas es de solo lectura.
- El pago es solo en efectivo. La venta registra el monto recibido y calcula el
  cambio; no se procesan tarjetas ni otros medios.
- La venta todavía no descuenta stock. La integración se hará usando los
  servicios de `inventario`.
- El ticket es un comprobante interno de 80 mm; no es una factura fiscal.
- SQLite es suficiente para la etapa local; no se asume concurrencia alta.
- No se implementaron impuestos, descuentos ni facturación fiscal.

## Próximos pasos

1. Integrar la salida de inventario en el servicio transaccional de ventas.
2. Completar clientes con edición y desactivación.
3. Endurecer seguridad, backups y despliegue.
4. Evaluar reglas FEFO para elegir lotes al vender.

## Documentación adicional

- [Arquitectura y convenciones](docs/ARCHITECTURE.md)
- [ADR-001: Monolito modular con Django MVT](docs/adr/ADR-001-arquitectura-monolitica-modular.md)
- [ADR-002: User integrado y autorización por grupos](docs/adr/ADR-002-user-integrado-y-grupos.md)
- [ADR-003: SQLite y operación local sin CDN](docs/adr/ADR-003-sqlite-local-sin-cdn.md)
- [ADR-004: Proveedores dentro de compras](docs/adr/ADR-004-proveedores-en-compras.md)
- [ADR-005: Registro y consulta de clientes](docs/adr/ADR-005-clientes-registro-consulta.md)
- [ADR-006: Ventas con catálogo mínimo y ticket HTML](docs/adr/ADR-006-ventas-catalogo-minimo-ticket.md)
- [ADR-007: Catálogo visual de productos y categorías](docs/adr/ADR-007-catalogo-visual-productos-categorias.md)
- [ADR-008: Inventario por lotes con movimientos transaccionales](docs/adr/ADR-008-inventario-lotes-movimientos.md)
- [ADR-009: Compras, proveedores y recepción sobre lotes](docs/adr/ADR-009-compras-proveedores-recepcion.md)
- [CHANGELOG](CHANGELOG.md)
