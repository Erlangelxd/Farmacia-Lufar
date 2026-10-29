"""Vistas iniciales del catálogo."""

from apps.core.views import ModulePlaceholderView


class CatalogoIndexView(ModulePlaceholderView):
    module_title = "Catálogo"
    module_code = "CT"
    module_description = (
        "Maestro de productos, categorías, presentaciones y precios de venta."
    )
    module_scope = (
        "Categorías y subcategorías de productos.",
        "Productos, código interno, presentación y precio.",
        "Búsqueda, filtros y estado activo/inactivo.",
    )
    module_note = (
        "Los modelos, formularios y validaciones del catálogo se implementarán "
        "en la siguiente etapa."
    )
