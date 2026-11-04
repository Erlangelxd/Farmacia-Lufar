"""Pruebas de las vistas de reportes.

Cubren los tres reportes (ventas, compras e inventario), sus filtros y la
protección de acceso para usuarios no autenticados.
"""

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.constants import ADMIN_GROUP
from apps.catalogo.models import Producto
from apps.compras.models import Compra, DetalleCompra, Proveedor
from apps.inventario.models import Lote, MovimientoInventario
from apps.ventas.models import DetalleVenta, Venta


class ReportesBaseTestData(TestCase):
    """Datos compartidos por las pruebas de reportes."""

    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.usuario = user_model.objects.create_user(
            username="reportes_user",
            password="ClaveSegura123!",
            first_name="Ana",
            last_name="Reportes",
        )
        cls.usuario.groups.add(Group.objects.get(name=ADMIN_GROUP))

        cls.producto_bajo = Producto.objects.create(
            codigo="R-001",
            nombre="Producto con stock bajo",
            precio_venta=Decimal("10.00"),
            stock_minimo=10,
        )
        cls.producto_normal = Producto.objects.create(
            codigo="R-002",
            nombre="Producto con stock normal",
            precio_venta=Decimal("20.00"),
            stock_minimo=2,
        )

        hoy = timezone.localdate()
        cls.lote_bajo = Lote.objects.create(
            producto=cls.producto_bajo,
            codigo_lote="L-BAJO",
            fecha_vencimiento=hoy + timedelta(days=10),
            stock_actual=Decimal("3.00"),
        )
        cls.lote_normal = Lote.objects.create(
            producto=cls.producto_normal,
            codigo_lote="L-NORMAL",
            fecha_vencimiento=hoy + timedelta(days=200),
            stock_actual=Decimal("50.00"),
        )
        cls.lote_vencido = Lote.objects.create(
            producto=cls.producto_bajo,
            codigo_lote="L-VENCIDO",
            fecha_vencimiento=hoy - timedelta(days=5),
            stock_actual=Decimal("2.00"),
        )

        MovimientoInventario.objects.create(
            lote=cls.lote_normal,
            tipo=MovimientoInventario.Tipo.ENTRADA,
            cantidad=Decimal("50.00"),
            stock_resultante=Decimal("50.00"),
            usuario=cls.usuario,
            motivo="Carga inicial",
        )

        cls.proveedor = Proveedor.objects.create(
            nombre="Distribuidora Lufar",
            nit="123456789",
        )
        cls.compra = Compra.objects.create(
            proveedor=cls.proveedor,
            usuario=cls.usuario,
            numero_factura="F-001",
            fecha_compra=hoy,
            estado=Compra.Estado.RECIBIDA,
            subtotal=Decimal("100.00"),
            impuesto=Decimal("13.00"),
            total=Decimal("113.00"),
        )
        DetalleCompra.objects.create(
            compra=cls.compra,
            producto=cls.producto_bajo,
            lote=cls.lote_bajo,
            cantidad=10,
            costo_unitario=Decimal("10.00"),
            subtotal=Decimal("100.00"),
        )

        cls.venta = Venta.objects.create(
            vendedor=cls.usuario,
            metodo_pago=Venta.MetodoPago.EFECTIVO,
            monto_recibido=Decimal("20.00"),
            total=Decimal("10.00"),
        )
        DetalleVenta.objects.create(
            venta=cls.venta,
            producto=cls.producto_bajo,
            codigo_producto=cls.producto_bajo.codigo,
            nombre_producto=cls.producto_bajo.nombre,
            cantidad=1,
            precio_unitario=Decimal("10.00"),
        )

    def setUp(self):
        self.client.force_login(self.usuario)


class ReportesIndexTests(ReportesBaseTestData):
    """Índice del módulo de reportes."""

    def test_index_muestra_resumen_de_los_tres_modulos(self):
        respuesta = self.client.get(reverse("reportes:index"))

        self.assertEqual(respuesta.status_code, 200)
        self.assertTemplateUsed(respuesta, "reportes/index.html")
        self.assertContains(respuesta, "Compras del mes")
        self.assertContains(respuesta, "Stock bajo")
        self.assertContains(respuesta, "Reporte de Inventario")
        self.assertEqual(respuesta.context["compras_mes"], 1)
        self.assertEqual(respuesta.context["gasto_mes"], Decimal("113.00"))
        self.assertEqual(respuesta.context["stock_bajo"], 1)
        self.assertEqual(respuesta.context["lotes_por_vencer"], 1)


class ReporteVentasTests(ReportesBaseTestData):
    """Reporte de ventas."""

    def test_reporte_ventas_muestra_totales_y_productos(self):
        respuesta = self.client.get(reverse("reportes:ventas"))

        self.assertEqual(respuesta.status_code, 200)
        self.assertTemplateUsed(respuesta, "reportes/reporte_ventas.html")
        self.assertContains(respuesta, "Reporte de Ventas")
        self.assertContains(respuesta, "Producto con stock bajo")
        self.assertContains(respuesta, "Ana Reportes")
        self.assertEqual(respuesta.context["total_ventas"], 1)
        self.assertEqual(respuesta.context["unidades_total"], 1)

    def test_reporte_ventas_no_duplica_agregados_con_varias_lineas(self):
        DetalleVenta.objects.create(
            venta=self.venta,
            producto=self.producto_normal,
            codigo_producto=self.producto_normal.codigo,
            nombre_producto=self.producto_normal.nombre,
            cantidad=2,
            precio_unitario=Decimal("20.00"),
        )

        respuesta = self.client.get(reverse("reportes:ventas"))

        self.assertEqual(respuesta.context["total_ventas"], 1)
        self.assertEqual(respuesta.context["ingresos_total"], Decimal("10.00"))
        self.assertEqual(respuesta.context["unidades_total"], 3)

    def test_reporte_ventas_filtra_por_vendedor(self):
        otro = get_user_model().objects.create_user(
            username="otro_vendedor",
            password="ClaveSegura123!",
        )
        respuesta = self.client.get(
            reverse("reportes:ventas"), {"vendedor": otro.pk}
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.context["total_ventas"], 0)


class ReporteComprasTests(ReportesBaseTestData):
    """Reporte de compras."""

    def test_reporte_compras_muestra_totales_y_proveedor(self):
        respuesta = self.client.get(reverse("reportes:compras"))

        self.assertEqual(respuesta.status_code, 200)
        self.assertTemplateUsed(respuesta, "reportes/reporte_compras.html")
        self.assertContains(respuesta, "Reporte de Compras")
        self.assertContains(respuesta, "Distribuidora Lufar")
        self.assertContains(respuesta, "F-001")
        self.assertEqual(respuesta.context["total_compras"], 1)
        self.assertEqual(respuesta.context["monto_total"], Decimal("113.00"))
        self.assertEqual(respuesta.context["unidades_total"], 10)

    def test_reporte_compras_filtra_por_proveedor(self):
        otro = Proveedor.objects.create(nombre="Otro proveedor")
        respuesta = self.client.get(
            reverse("reportes:compras"), {"proveedor": otro.pk}
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.context["total_compras"], 0)
        self.assertContains(respuesta, "Sin compras en el periodo")

    def test_reporte_compras_filtra_por_estado(self):
        respuesta = self.client.get(
            reverse("reportes:compras"), {"estado": Compra.Estado.BORRADOR}
        )

        self.assertEqual(respuesta.status_code, 200)
        self.assertEqual(respuesta.context["total_compras"], 0)

    def test_reporte_compras_sin_datos_muestra_estado_vacio(self):
        Compra.objects.all().delete()
        respuesta = self.client.get(reverse("reportes:compras"))

        self.assertEqual(respuesta.status_code, 200)
        self.assertContains(respuesta, "Sin compras registradas")


class ReporteInventarioTests(ReportesBaseTestData):
    """Reporte de inventario basado en lotes."""

    def test_reporte_inventario_calcula_existencias_y_alertas(self):
        respuesta = self.client.get(reverse("reportes:inventario"))

        self.assertEqual(respuesta.status_code, 200)
        self.assertTemplateUsed(respuesta, "reportes/reporte_inventario.html")
        self.assertContains(respuesta, "Unidades en stock")
        self.assertContains(respuesta, "L-BAJO")
        self.assertContains(respuesta, "L-VENCIDO")
        self.assertEqual(respuesta.context["stock_unidades"], Decimal("55.00"))
        self.assertEqual(respuesta.context["valor_inventario"], Decimal("1050.00"))
        self.assertEqual(respuesta.context["total_stock_bajo"], 1)
        self.assertEqual(respuesta.context["total_por_vencer"], 1)
        self.assertEqual(respuesta.context["total_vencidos"], 1)

    def test_reporte_inventario_filtra_por_stock_bajo(self):
        respuesta = self.client.get(
            reverse("reportes:inventario"), {"alerta": "bajo"}
        )

        self.assertEqual(respuesta.status_code, 200)
        codigos = [p.codigo for p in respuesta.context["productos"]]
        self.assertEqual(codigos, ["R-001"])

    def test_reporte_inventario_filtra_por_vencidos(self):
        respuesta = self.client.get(
            reverse("reportes:inventario"), {"alerta": "vencido"}
        )

        self.assertEqual(respuesta.status_code, 200)
        codigos = [p.codigo for p in respuesta.context["productos"]]
        self.assertEqual(codigos, ["R-001"])

    def test_reporte_inventario_busca_por_nombre(self):
        respuesta = self.client.get(
            reverse("reportes:inventario"), {"q": "normal"}
        )

        self.assertEqual(respuesta.status_code, 200)
        codigos = [p.codigo for p in respuesta.context["productos"]]
        self.assertEqual(codigos, ["R-002"])


class ReportesAccesoTests(TestCase):
    """Los reportes exigen autenticación."""

    def test_reportes_redirigen_al_login_sin_autenticacion(self):
        for nombre in (
            "reportes:index",
            "reportes:ventas",
            "reportes:compras",
            "reportes:inventario",
        ):
            with self.subTest(ruta=nombre):
                respuesta = self.client.get(reverse(nombre))
                self.assertEqual(respuesta.status_code, 302)
                self.assertIn("/cuentas/login/", respuesta["Location"])
