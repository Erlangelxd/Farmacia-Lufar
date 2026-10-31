"""Pruebas del catálogo mínimo de productos."""

from decimal import Decimal

from django.core.exceptions import ValidationError
from django.test import TestCase

from .models import Producto


class ProductoModelTests(TestCase):
    """Reglas básicas del producto usado por ventas."""

    def test_str_incluye_codigo_y_nombre(self):
        producto = Producto(
            codigo="P-001",
            nombre="Paracetamol 500 mg",
            precio_venta=Decimal("5.50"),
        )
        self.assertEqual(str(producto), "P-001 — Paracetamol 500 mg")

    def test_valores_por_defecto(self):
        producto = Producto.objects.create(
            codigo="P-001",
            nombre="Paracetamol 500 mg",
            precio_venta=Decimal("5.50"),
        )
        self.assertTrue(producto.activo)
        self.assertIsNotNone(producto.creado_en)
        self.assertIsNotNone(producto.actualizado_en)

    def test_normaliza_codigo_y_nombre_al_guardar(self):
        producto = Producto.objects.create(
            codigo="  p-001  ",
            nombre="  Paracetamol   500 mg  ",
            precio_venta=Decimal("5.50"),
        )
        producto.refresh_from_db()
        self.assertEqual(producto.codigo, "P-001")
        self.assertEqual(producto.nombre, "Paracetamol 500 mg")

    def test_codigo_duplicado_sin_distinguir_mayusculas(self):
        Producto.objects.create(
            codigo="P-001",
            nombre="Paracetamol 500 mg",
            precio_venta=Decimal("5.50"),
        )
        duplicado = Producto(
            codigo="p-001",
            nombre="Otro producto",
            precio_venta=Decimal("3.00"),
        )
        with self.assertRaises(ValidationError) as contexto:
            duplicado.full_clean()
        self.assertIn("codigo", contexto.exception.message_dict)
        self.assertIn(
            "Ya existe un producto con ese código.",
            contexto.exception.message_dict["codigo"],
        )

    def test_precio_no_puede_ser_negativo(self):
        producto = Producto(
            codigo="P-002",
            nombre="Producto inválido",
            precio_venta=Decimal("-1.00"),
        )
        with self.assertRaises(ValidationError) as contexto:
            producto.full_clean()
        self.assertIn("precio_venta", contexto.exception.message_dict)

    def test_orden_por_nombre(self):
        Producto.objects.create(
            codigo="P-002",
            nombre="Zinc",
            precio_venta=Decimal("2.00"),
        )
        Producto.objects.create(
            codigo="P-001",
            nombre="Analgésico",
            precio_venta=Decimal("3.00"),
        )
        self.assertEqual(
            list(Producto.objects.values_list("nombre", flat=True)),
            ["Analgésico", "Zinc"],
        )
