"""Vistas iniciales de compras."""

from apps.core.views import ModulePlaceholderView


class ComprasIndexView(ModulePlaceholderView):
    module_title = "Compras"
    module_code = "CP"
    module_description = (
        "Proveedores, compras y recepción de mercadería."
    )
    module_scope = (
        "Registro de proveedores.",
        "Compras y detalle de productos.",
        "Recepción y actualización de inventario.",
    )
    module_note = (
        "Proveedor se ubicará en esta app para mantener las ocho aplicaciones "
        "del alcance inicial. La recepción de compras actualizará inventario "
        "dentro de una transacción."
    )
