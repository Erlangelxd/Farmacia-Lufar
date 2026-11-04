"""Matriz de acceso por rol y sincronización de permisos por modelo.

Los roles del sistema son los grupos ``Administrador`` y ``Vendedor``. La
matriz ``MODULE_ACCESS`` define qué módulos puede usar cada rol en la
interfaz; ``SELLER_PERMISSIONS`` define los permisos por modelo que recibe el
rol ``Vendedor``. El rol ``Administrador`` recibe todos los permisos de las
apps de negocio.
"""

from django.apps import apps as global_apps
from django.contrib.auth.management import create_permissions
from django.contrib.auth.models import Group, Permission
from django.db import DEFAULT_DB_ALIAS
from django.db.models import Q

from .constants import ADMIN_GROUP, SELLER_GROUP

# Apps cuyos permisos por modelo administra este módulo. ``reportes`` no tiene
# modelos y ``core``/``accounts`` se gestionan con Django Admin.
MANAGED_APPS = (
    "catalogo",
    "compras",
    "inventario",
    "clientes",
    "ventas",
)

# Permisos por modelo que recibe el rol Vendedor. Se mantiene el principio de
# menor privilegio: consulta el catálogo, registra clientes y ventas, y solo
# consulta lotes. No puede eliminar registros ni administrar compras.
SELLER_PERMISSIONS = {
    "catalogo": (
        "view_categoria",
        "view_laboratorio",
        "view_formafarmaceutica",
        "view_presentacion",
        "view_producto",
    ),
    "clientes": (
        "view_cliente",
        "add_cliente",
        "change_cliente",
    ),
    "inventario": (
        "view_lote",
    ),
    "ventas": (
        "view_venta",
        "add_venta",
        "view_detalleventa",
        "add_detalleventa",
    ),
}

# Matriz visible en la interfaz. ``note`` aclara el alcance cuando el rol no
# tiene acceso completo al módulo.
MODULE_ACCESS = (
    {"module": "Panel general", "admin": True, "seller": True, "note": ""},
    {"module": "Catálogo", "admin": True, "seller": True, "note": "Consulta"},
    {"module": "Inventario", "admin": True, "seller": False, "note": ""},
    {"module": "Compras", "admin": True, "seller": False, "note": ""},
    {"module": "Clientes", "admin": True, "seller": True, "note": ""},
    {"module": "Ventas", "admin": True, "seller": True, "note": ""},
    {"module": "Reportes", "admin": True, "seller": True, "note": "Solo ventas"},
    {"module": "Usuarios y permisos", "admin": True, "seller": False, "note": ""},
)


def is_administrator(user) -> bool:
    """Indica si el usuario puede administrar el sistema.

    Los superusuarios siempre cuentan como administradores.
    """
    if not user or not user.is_authenticated:
        return False
    return user.is_superuser or user.groups.filter(name=ADMIN_GROUP).exists()


def is_seller(user) -> bool:
    """Indica si el usuario tiene el rol Vendedor."""
    if not user or not user.is_authenticated:
        return False
    return user.groups.filter(name=SELLER_GROUP).exists()


def _seller_permission_filter() -> Q:
    """Construye el filtro de permisos del rol Vendedor."""
    filtro = Q()
    for app_label, codenames in SELLER_PERMISSIONS.items():
        filtro |= Q(
            content_type__app_label=app_label,
            codename__in=codenames,
        )
    return filtro


def sync_role_permissions(
    sender=None,
    using=DEFAULT_DB_ALIAS,
    verbosity=0,
    **kwargs,
) -> dict[str, int]:
    """Asigna permisos por modelo a los grupos base.

    Es idempotente: se ejecuta después de las migraciones y puede invocarse
    manualmente con ``python manage.py sync_roles``. Antes de asignar asegura
    que los permisos por modelo existan, incluso en una base recién creada.
    """
    # El registro que llega en ``post_migrate`` contiene ``AppConfigStub`` sin
    # modelos; se usa siempre el registro real de la aplicación.
    # Django crea los permisos por modelo en ``post_migrate``. Al ejecutar esta
    # función también fuera de ese flujo, se crean de forma explícita.
    for app_config in global_apps.get_app_configs():
        create_permissions(
            app_config,
            verbosity=0,
            using=using,
            apps=global_apps,
        )

    admin_group, _ = Group.objects.using(using).get_or_create(name=ADMIN_GROUP)
    seller_group, _ = Group.objects.using(using).get_or_create(name=SELLER_GROUP)

    managed_permissions = Permission.objects.using(using).filter(
        content_type__app_label__in=MANAGED_APPS
    )
    seller_permissions = Permission.objects.using(using).filter(
        _seller_permission_filter()
    )

    # Se reemplazan solo los permisos de las apps administradas para no borrar
    # permisos personalizados que se agreguen en el futuro.
    admin_group.permissions.remove(*managed_permissions)
    admin_group.permissions.add(*managed_permissions)

    seller_group.permissions.remove(*managed_permissions)
    seller_group.permissions.add(*seller_permissions)

    return {
        ADMIN_GROUP: managed_permissions.count(),
        SELLER_GROUP: seller_permissions.count(),
    }
