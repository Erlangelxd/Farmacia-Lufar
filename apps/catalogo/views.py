"""Vistas iniciales del catálogo."""

from apps.core.views import ModulePlaceholderView


class CatalogoIndexView(ModulePlaceholderView):
    module_title = "Catálogo"
    module_code = "CT"
    module_description = (
        "Maestro de productos, categorías, presentaciones y precios de venta."
    )
    module_scope = (
        "Productos mínimos con código, nombre, precio y estado.",
        "Categorías y subcategorías de productos.",
        "Búsqueda, filtros y presentaciones.",
    )
    module_note = (
        "El modelo Producto ya está disponible y se administra desde Django "
        "Admin. El CRUD visual del catálogo se implementará en una etapa "
        "posterior."
    )
