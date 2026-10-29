"""Vistas iniciales de inventario."""

from apps.core.views import ModulePlaceholderView


class InventarioIndexView(ModulePlaceholderView):
    module_title = "Inventario"
    module_code = "IN"
    module_description = (
        "Control de existencias y movimientos de entrada, salida y ajuste."
    )
    module_scope = (
        "Stock actual por producto y lote.",
        "Movimientos de entrada, salida y ajuste.",
        "Alertas de existencias mínimas.",
    )
    module_note = (
        "Los movimientos se integrarán con compras y ventas cuando existan sus "
        "modelos. Toda operación que altere stock deberá ser transaccional."
    )
