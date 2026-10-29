"""Vistas iniciales de clientes."""

from apps.core.views import ModulePlaceholderView


class ClientesIndexView(ModulePlaceholderView):
    module_title = "Clientes"
    module_code = "CL"
    module_description = (
        "Información de clientes y su historial comercial."
    )
    module_scope = (
        "Datos de contacto e identificación.",
        "Historial de ventas por cliente.",
        "Búsqueda y estado del cliente.",
    )
    module_note = (
        "El modelo de cliente y sus formularios se implementarán en la "
        "siguiente etapa."
    )
