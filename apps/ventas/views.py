"""Vistas iniciales de ventas."""

from apps.core.views import ModulePlaceholderView


class VentasIndexView(ModulePlaceholderView):
    module_title = "Ventas"
    module_code = "VT"
    module_description = (
        "Registro de ventas, detalles, pagos y comprobantes."
    )
    module_scope = (
        "Venta y detalle de productos.",
        "Cálculo de totales y medios de pago.",
        "Integración con inventario en una etapa posterior.",
    )
    module_note = (
        "La venta y la salida de inventario deberán registrarse en una misma "
        "transacción cuando se implemente la lógica de negocio."
    )
