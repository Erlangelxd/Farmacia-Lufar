"""Vistas iniciales de reportes."""

from apps.core.views import ModulePlaceholderView


class ReportesIndexView(ModulePlaceholderView):
    module_title = "Reportes"
    module_code = "RP"
    module_description = (
        "Consultas e informes de las operaciones del sistema."
    )
    module_scope = (
        "Ventas por periodo y por vendedor.",
        "Existencias y movimientos de inventario.",
        "Compras y productos más vendidos.",
    )
    module_note = (
        "Esta app no tendrá modelos propios: consultará datos de los demás "
        "módulos cuando estén implementados."
    )
