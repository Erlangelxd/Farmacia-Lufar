# Farmacia Lufar — Sistema de gestión

Sistema web local para centralizar productos, inventario, compras, clientes,
proveedores, ventas, usuarios y reportes de Farmacia Lufar. Está construido con
Python, Django, SQLite y plantillas renderizadas en el servidor.

> **Estado actual:** estructura base funcional. Incluye autenticación, grupos,
> navegación, dashboard provisional, las ocho aplicaciones enrutadas y pruebas
> iniciales. **No incluye todavía CRUD ni la lógica de compras, ventas o
> movimientos de inventario.**

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
- Restricción de vistas mediante autenticación y roles.
- Interfaz administrativa responsive con plantilla base, menú, encabezado,
  mensajes y área de contenido.
- Dashboard con indicadores de ejemplo marcados como **provisionales**.
- Rutas iniciales y páginas de alcance para cada módulo.
- Estilos y JavaScript locales, sin CDN.
- Pruebas transversales de rutas, autenticación, CSRF, grupos y permisos.
- Documentación de arquitectura y decisiones en `docs/`.

### Fuera de alcance en esta entrega

- Modelos y CRUD completos de catálogo, clientes, proveedores, compras y ventas.
- Movimientos reales de inventario.
- Facturación, impuestos, precios y reglas comerciales.
- Reportes con datos reales.
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
| `accounts` | Login, logout, perfil, usuarios, grupos y autorización por rol. | Base funcional |
| `catalogo` | Categorías, productos, presentaciones y precios. | Ruta y estructura |
| `inventario` | Existencias, lotes y movimientos de entrada, salida y ajuste. | Ruta y estructura |
| `compras` | Proveedores, compras, detalle y recepción de mercadería. | Ruta y estructura |
| `clientes` | Datos de clientes e historial comercial. | Ruta y estructura |
| `ventas` | Ventas, detalles, pagos y comprobantes. | Ruta y estructura |
| `reportes` | Consultas e informes de solo lectura. | Ruta y estructura |

Decisiones importantes:

- **Proveedores vive en `compras`.** El alcance menciona proveedores, pero no
  define una novena app. Se mantiene la estructura de ocho aplicaciones.
- **El usuario es el `User` integrado de Django.** No se creó un modelo de
  usuario personalizado en esta etapa.
- **Los permisos por modelo se asignarán después.** Por ahora los grupos
  identifican el rol y `RoleRequiredMixin` restringe la vista de usuarios al
  grupo `Administrador`.
- **Inventario será el único dueño de las existencias.** Compras y ventas
  deberán registrar sus movimientos mediante servicios transaccionales.

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

Esto crea `db.sqlite3` y aplica las migraciones de Django y de `accounts`. La
migración `accounts.0001_create_default_groups` crea los grupos base de forma
idempotente. Puedes verificarlos con:

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

- `Administrador`: puede acceder a la vista de usuarios y grupos. En la
  siguiente etapa recibirá los permisos administrativos por modelo.
- `Vendedor`: usuario operativo para ventas y consultas. La vista de usuarios
  le devuelve `403`.

## 8. Ejecución de las pruebas

```bash
python manage.py check
python manage.py test
python manage.py makemigrations --check --dry-run
```

Las 15 pruebas iniciales cubren:

- Carga de las ocho aplicaciones.
- Resolución de las rutas iniciales.
- Creación de los grupos base.
- Redirección al login de todas las vistas de gestión.
- Protección CSRF del formulario de login.
- Login válido e inválido.
- Mensaje de bienvenida después del login.
- Logout solo por POST y limpieza de sesión.
- Acceso del Vendedor al dashboard y a los módulos.
- Acceso del Administrador a usuarios y grupos.
- Respuesta `403` para el Vendedor en la vista de usuarios.
- Visibilidad del enlace de usuarios según el rol.
- Plantilla personalizada para páginas no encontradas (`404`).

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
| `/cuentas/usuarios/` | Usuarios y grupos; solo Administrador o superusuario. |
| `/catalogo/` | Página inicial del catálogo. |
| `/inventario/` | Página inicial de inventario. |
| `/compras/` | Página inicial de compras. |
| `/clientes/` | Página inicial de clientes. |
| `/ventas/` | Página inicial de ventas. |
| `/reportes/` | Página inicial de reportes. |
| `/admin/` | Administración de Django. |

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
- `LoginRequiredMixin` en las vistas de gestión.
- Autorización por grupo en la vista de usuarios.
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
│   ├── inventario/
│   ├── compras/
│   ├── clientes/
│   ├── ventas/
│   └── reportes/
├── templates/
│   ├── base.html
│   ├── 403.html
│   ├── 404.html
│   ├── includes/
│   ├── core/
│   ├── accounts/
│   └── registration/login.html
├── static/
│   ├── css/styles.css
│   ├── js/app.js
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
- Los grupos base no tienen permisos por modelo todavía porque los modelos de
  negocio aún no existen.
- No se implementó recuperación de contraseña por correo; el administrador
  gestiona las cuentas desde Django Admin.
- Proveedor se implementará dentro de `compras`.
- SQLite es suficiente para la etapa local; no se asume concurrencia alta.
- No se implementaron reglas de negocio de precios, impuestos, descuentos,
  vencimientos ni facturación.

## Próximos pasos

1. Implementar `catalogo` con `Categoria`, `Producto`, formularios y CRUD.
2. Implementar existencias y movimientos transaccionales en `inventario`.
3. Implementar `clientes`.
4. Implementar `compras` y la recepción que actualiza inventario.
5. Implementar `ventas` y la salida de inventario en la misma transacción.
6. Implementar reportes de solo lectura.
7. Asignar permisos por modelo a los grupos y ampliar las pruebas.
8. Endurecer seguridad, backups y despliegue.

## Documentación adicional

- [Arquitectura y convenciones](docs/ARCHITECTURE.md)
- [ADR-001: Monolito modular con Django MVT](docs/adr/ADR-001-arquitectura-monolitica-modular.md)
- [ADR-002: User integrado y autorización por grupos](docs/adr/ADR-002-user-integrado-y-grupos.md)
- [ADR-003: SQLite y operación local sin CDN](docs/adr/ADR-003-sqlite-local-sin-cdn.md)
- [ADR-004: Proveedores dentro de compras](docs/adr/ADR-004-proveedores-en-compras.md)
# Farmacia-Lufar
