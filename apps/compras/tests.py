"""Pruebas del módulo de compras: proveedores, compras y recepción."""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.constants import ADMIN_GROUP, SELLER_GROUP
from apps.catalogo.models import Categoria, Producto
from apps.inventario.models import Lote, MovimientoInventario

from .forms import CompraForm, ProveedorForm, RecepcionCompraForm
from .models import Compra, DetalleCompra, Proveedor
from .services import (
    actualizar_compra,
    anular_compra,
    recibir_compra,
    registrar_compra,
)


class ComprasBaseTestData(TestCase):
    """Datos compartidos por las pruebas de compras."""

    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.admin_group = Group.objects.get(name=ADMIN_GROUP)
        cls.seller_group = Group.objects.get(name=SELLER_GROUP)

        cls.admin_user = user_model.objects.create_user(
            username="admin_compras",
            password="ClaveSegura123!",
            first_name="Admin",
            last_name="Compras",
        )
        cls.admin_user.groups.add(cls.admin_group)

        cls.seller_user = user_model.objects.create_user(
            username="vendedor_compras",
            password="ClaveSegura123!",
        )
        cls.seller_user.groups.add(cls.seller_group)

        cls.categoria = Categoria.objects.create(nombre="Analgésicos")

        cls.producto = Producto.objects.create(
            codigo="P-001",
            nombre="Paracetamol 500 mg",
            categoria=cls.categoria,
            precio_venta=Decimal("5.50"),
        )
        cls.producto_2 = Producto.objects.create(
            codigo="P-002",
            nombre="Ibuprofeno 400 mg",
            categoria=cls.categoria,
            precio_venta=Decimal("7.25"),
        )
        cls.producto_inactivo = Producto.objects.create(
            codigo="P-003",
            nombre="Amoxicilina 500 mg",
            categoria=cls.categoria,
            precio_venta=Decimal("9.00"),
            activo=False,
        )

        cls.proveedor = Proveedor.objects.create(
            nombre="Distribuidora Lufar",
            nit="123456789",
        )
        cls.proveedor_inactivo = Proveedor.objects.create(
            nombre="Proveedor Inactivo",
            activo=False,
        )

        cls.lote = Lote.objects.create(
            producto=cls.producto,
            codigo_lote="L-001",
            stock_actual=Decimal("0.00"),
        )
        cls.lote_2 = Lote.objects.create(
            producto=cls.producto_2,
            codigo_lote="L-002",
            stock_actual=Decimal("0.00"),
        )

    def crear_compra(self, lineas=None, **overrides):
        if lineas is None:
            lineas = [
                {
                    "producto": self.producto,
                    "cantidad": 10,
                    "costo_unitario": Decimal("4.50"),
                }
            ]
        data = {
            "proveedor": self.proveedor,
            "usuario": self.admin_user,
            "lineas": lineas,
        }
        data.update(overrides)
        return registrar_compra(**data)

    def compra_form_data(self, **overrides):
        data = {
            "proveedor": self.proveedor.pk,
            "numero_factura": "F-100",
            "fecha_compra": timezone.localdate().isoformat(),
            "impuesto": "13.00",
            "observaciones": "",
            "detalles-TOTAL_FORMS": "1",
            "detalles-INITIAL_FORMS": "0",
            "detalles-MIN_NUM_FORMS": "1",
            "detalles-MAX_NUM_FORMS": "1000",
            "detalles-0-producto": self.producto.pk,
            "detalles-0-cantidad": "10",
            "detalles-0-costo_unitario": "4.50",
        }
        data.update(overrides)
        return data


class ProveedorModelTests(ComprasBaseTestData):
    """Normalización y unicidad del NIT de proveedor."""

    def test_str_devuelve_nombre(self):
        self.assertEqual(str(self.proveedor), "Distribuidora Lufar")

    def test_save_normaliza_nombre_y_nit(self):
        proveedor = Proveedor.objects.create(
            nombre="  Farmacéutica   Andina  ",
            nit="  abc-123  ",
        )
        proveedor.refresh_from_db()
        self.assertEqual(proveedor.nombre, "Farmacéutica Andina")
        self.assertEqual(proveedor.nit, "ABC-123")

    def test_clean_rechaza_nit_duplicado_sin_distinguir_mayusculas(self):
        duplicado = Proveedor(nombre="Otro proveedor", nit="123456789")
        with self.assertRaises(ValidationError) as contexto:
            duplicado.full_clean()
        self.assertIn("nit", contexto.exception.message_dict)

    def test_clean_rechaza_nombre_vacio(self):
        proveedor = Proveedor(nombre="   ")
        with self.assertRaises(ValidationError) as contexto:
            proveedor.full_clean()
        self.assertIn("nombre", contexto.exception.message_dict)


class CompraModelTests(ComprasBaseTestData):
    """Reglas de estado y totales del modelo de compra."""

    def test_numero_visible(self):
        compra = self.crear_compra()
        self.assertEqual(compra.numero, f"C-{compra.pk:06d}")

    def test_detalle_calcula_subtotal_al_guardar(self):
        compra = self.crear_compra()
        detalle = DetalleCompra.objects.create(
            compra=compra,
            producto=self.producto,
            cantidad=3,
            costo_unitario=Decimal("2.50"),
        )
        self.assertEqual(detalle.subtotal, Decimal("7.50"))

    def test_compra_recibida_exige_fecha_de_recepcion(self):
        compra = Compra(
            proveedor=self.proveedor,
            usuario=self.admin_user,
            estado=Compra.Estado.RECIBIDA,
        )
        with self.assertRaises(ValidationError) as contexto:
            compra.full_clean()
        self.assertIn("fecha_recepcion", contexto.exception.message_dict)

    def test_compra_no_recibida_no_admite_fecha_de_recepcion(self):
        compra = Compra(
            proveedor=self.proveedor,
            usuario=self.admin_user,
            estado=Compra.Estado.BORRADOR,
            fecha_recepcion=timezone.localdate(),
        )
        with self.assertRaises(ValidationError) as contexto:
            compra.full_clean()
        self.assertIn("fecha_recepcion", contexto.exception.message_dict)


class CompraServiceTests(ComprasBaseTestData):
    """Alta, edición, recepción y anulación transaccionales."""

    def test_registrar_compra_calcula_totales_y_crea_detalles(self):
        compra = self.crear_compra(
            lineas=[
                {
                    "producto": self.producto,
                    "cantidad": 3,
                    "costo_unitario": Decimal("4.50"),
                },
                {
                    "producto": self.producto_2,
                    "cantidad": 2,
                    "costo_unitario": Decimal("7.00"),
                },
            ],
            impuesto=Decimal("1.00"),
        )

        self.assertEqual(compra.estado, Compra.Estado.BORRADOR)
        self.assertEqual(compra.subtotal, Decimal("27.50"))
        self.assertEqual(compra.impuesto, Decimal("1.00"))
        self.assertEqual(compra.total, Decimal("28.50"))
        self.assertEqual(compra.detalles.count(), 2)
        self.assertEqual(compra.cantidad_productos, 5)

    def test_registrar_compra_rechaza_sin_lineas(self):
        with self.assertRaises(ValidationError):
            self.crear_compra(lineas=[])

    def test_registrar_compra_rechaza_proveedor_inactivo(self):
        with self.assertRaises(ValidationError):
            self.crear_compra(proveedor=self.proveedor_inactivo)

    def test_registrar_compra_rechaza_producto_inactivo(self):
        with self.assertRaises(ValidationError):
            self.crear_compra(
                lineas=[
                    {
                        "producto": self.producto_inactivo,
                        "cantidad": 1,
                        "costo_unitario": Decimal("1.00"),
                    }
                ]
            )

    def test_registrar_compra_rechaza_cantidad_no_entera(self):
        with self.assertRaises(ValidationError):
            self.crear_compra(
                lineas=[
                    {
                        "producto": self.producto,
                        "cantidad": "uno",
                        "costo_unitario": Decimal("1.00"),
                    }
                ]
            )

    def test_actualizar_compra_reemplaza_lineas_y_totales(self):
        compra = self.crear_compra()
        actualizada = actualizar_compra(
            compra=compra,
            proveedor=self.proveedor,
            numero_factura="F-200",
            fecha_compra=timezone.localdate(),
            impuesto=Decimal("2.00"),
            observaciones="Actualizada",
            lineas=[
                {
                    "producto": self.producto_2,
                    "cantidad": 4,
                    "costo_unitario": Decimal("5.00"),
                }
            ],
        )

        self.assertEqual(actualizada.detalles.count(), 1)
        self.assertEqual(actualizada.subtotal, Decimal("20.00"))
        self.assertEqual(actualizada.total, Decimal("22.00"))
        self.assertEqual(actualizada.numero_factura, "F-200")
        self.assertEqual(
            actualizada.detalles.first().producto, self.producto_2
        )

    def test_actualizar_compra_rechaza_compra_recibida(self):
        compra = self.crear_compra()
        compra.estado = Compra.Estado.RECIBIDA
        compra.fecha_recepcion = timezone.localdate()
        compra.save(update_fields=["estado", "fecha_recepcion"])

        with self.assertRaises(ValidationError):
            actualizar_compra(
                compra=compra,
                proveedor=self.proveedor,
                lineas=[
                    {
                        "producto": self.producto,
                        "cantidad": 1,
                        "costo_unitario": Decimal("1.00"),
                    }
                ],
            )

    def test_recibir_compra_actualiza_stock_y_registra_movimiento(self):
        compra = self.crear_compra()
        detalle = compra.detalles.get()

        recibir_compra(
            compra=compra,
            usuario=self.admin_user,
            lotes_por_detalle={detalle.pk: self.lote},
        )

        compra.refresh_from_db()
        detalle.refresh_from_db()
        self.lote.refresh_from_db()

        self.assertEqual(compra.estado, Compra.Estado.RECIBIDA)
        self.assertEqual(compra.fecha_recepcion, timezone.localdate())
        self.assertEqual(detalle.lote_id, self.lote.pk)
        self.assertEqual(self.lote.stock_actual, Decimal("10.00"))

        movimiento = MovimientoInventario.objects.get(lote=self.lote)
        self.assertEqual(movimiento.tipo, MovimientoInventario.Tipo.ENTRADA)
        self.assertEqual(movimiento.cantidad, Decimal("10.00"))
        self.assertEqual(movimiento.stock_resultante, Decimal("10.00"))
        self.assertEqual(movimiento.usuario, self.admin_user)
        self.assertIn(compra.numero, movimiento.motivo)

    def test_recibir_compra_rechaza_lote_de_otro_producto(self):
        compra = self.crear_compra()
        detalle = compra.detalles.get()

        with self.assertRaises(ValidationError):
            recibir_compra(
                compra=compra,
                usuario=self.admin_user,
                lotes_por_detalle={detalle.pk: self.lote_2},
            )

        self.lote.refresh_from_db()
        self.assertEqual(self.lote.stock_actual, Decimal("0.00"))
        compra.refresh_from_db()
        self.assertEqual(compra.estado, Compra.Estado.BORRADOR)

    def test_recibir_compra_rechaza_lote_repetido(self):
        compra = self.crear_compra(
            lineas=[
                {
                    "producto": self.producto,
                    "cantidad": 2,
                    "costo_unitario": Decimal("1.00"),
                },
                {
                    "producto": self.producto,
                    "cantidad": 3,
                    "costo_unitario": Decimal("1.00"),
                },
            ]
        )
        detalles = list(compra.detalles.order_by("pk"))

        with self.assertRaises(ValidationError):
            recibir_compra(
                compra=compra,
                usuario=self.admin_user,
                lotes_por_detalle={
                    detalles[0].pk: self.lote,
                    detalles[1].pk: self.lote,
                },
            )

        self.lote.refresh_from_db()
        self.assertEqual(self.lote.stock_actual, Decimal("0.00"))

    def test_recibir_compra_es_atomica_si_una_linea_falla(self):
        compra = self.crear_compra(
            lineas=[
                {
                    "producto": self.producto,
                    "cantidad": 2,
                    "costo_unitario": Decimal("1.00"),
                },
                {
                    "producto": self.producto_2,
                    "cantidad": 3,
                    "costo_unitario": Decimal("1.00"),
                },
            ]
        )
        detalles = list(compra.detalles.order_by("pk"))

        with self.assertRaises(ValidationError):
            recibir_compra(
                compra=compra,
                usuario=self.admin_user,
                lotes_por_detalle={
                    detalles[0].pk: self.lote,
                    detalles[1].pk: self.lote,
                },
            )

        self.lote.refresh_from_db()
        self.lote_2.refresh_from_db()
        self.assertEqual(self.lote.stock_actual, Decimal("0.00"))
        self.assertEqual(self.lote_2.stock_actual, Decimal("0.00"))
        self.assertFalse(
            MovimientoInventario.objects.filter(lote=self.lote).exists()
        )

    def test_recibir_compra_rechaza_compra_anulada(self):
        compra = self.crear_compra()
        anular_compra(compra=compra)
        detalle = compra.detalles.get()

        with self.assertRaises(ValidationError):
            recibir_compra(
                compra=compra,
                usuario=self.admin_user,
                lotes_por_detalle={detalle.pk: self.lote},
            )

    def test_recibir_compra_exige_lote_por_linea(self):
        compra = self.crear_compra()
        with self.assertRaises(ValidationError):
            recibir_compra(
                compra=compra,
                usuario=self.admin_user,
                lotes_por_detalle={},
            )

    def test_anular_compra_en_borrador(self):
        compra = self.crear_compra()
        anulada = anular_compra(compra=compra)

        self.assertEqual(anulada.estado, Compra.Estado.ANULADA)
        self.assertFalse(
            MovimientoInventario.objects.filter(lote=self.lote).exists()
        )

    def test_anular_compra_rechaza_compra_recibida(self):
        compra = self.crear_compra()
        compra.estado = Compra.Estado.RECIBIDA
        compra.fecha_recepcion = timezone.localdate()
        compra.save(update_fields=["estado", "fecha_recepcion"])

        with self.assertRaises(ValidationError):
            anular_compra(compra=compra)


class CompraFormTests(ComprasBaseTestData):
    """Validación de formularios de proveedor, compra y recepción."""

    def test_proveedor_form_rechaza_nit_duplicado(self):
        form = ProveedorForm(
            data={
                "nombre": "Proveedor Nuevo",
                "nit": "123456789",
                "telefono": "",
                "email": "",
                "direccion": "",
                "contacto": "",
                "activo": "on",
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("nit", form.errors)

    def test_compra_form_acepta_impuesto_sin_totales_previos(self):
        form = CompraForm(data=self.compra_form_data())
        self.assertTrue(form.is_valid(), form.errors)

    def test_recepcion_form_rechaza_lote_de_otro_producto(self):
        compra = self.crear_compra()
        detalle = compra.detalles.get()

        form = RecepcionCompraForm(
            data={RecepcionCompraForm.nombre_campo(detalle): self.lote_2.pk},
            compra=compra,
        )
        self.assertFalse(form.is_valid())
        self.assertIn(
            RecepcionCompraForm.nombre_campo(detalle), form.errors
        )

    def test_recepcion_form_rechaza_lote_repetido(self):
        compra = self.crear_compra(
            lineas=[
                {
                    "producto": self.producto,
                    "cantidad": 2,
                    "costo_unitario": Decimal("1.00"),
                },
                {
                    "producto": self.producto,
                    "cantidad": 3,
                    "costo_unitario": Decimal("1.00"),
                },
            ]
        )
        detalles = list(compra.detalles.order_by("pk"))
        data = {
            RecepcionCompraForm.nombre_campo(detalle): self.lote.pk
            for detalle in detalles
        }

        form = RecepcionCompraForm(data=data, compra=compra)
        self.assertFalse(form.is_valid())


class ComprasViewTests(ComprasBaseTestData):
    """Acceso, alta, edición, recepción y anulación por la interfaz."""

    def test_vendedor_no_puede_acceder_a_compras(self):
        self.client.force_login(self.seller_user)
        for name in (
            "compras:index",
            "compras:proveedores",
            "compras:proveedor_crear",
            "compras:compra_crear",
        ):
            with self.subTest(route=name):
                self.assertEqual(
                    self.client.get(reverse(name)).status_code, 403
                )

        compra = self.crear_compra()
        for name in (
            "compras:compra_detalle",
            "compras:compra_editar",
            "compras:compra_recepcion",
        ):
            with self.subTest(route=name):
                self.assertEqual(
                    self.client.get(reverse(name, args=[compra.pk])).status_code,
                    403,
                )

    def test_administrador_puede_ver_paginas_de_compras(self):
        self.client.force_login(self.admin_user)
        rutas = (
            ("compras:index", "compras/compra_list.html"),
            ("compras:proveedores", "compras/proveedor_list.html"),
            ("compras:proveedor_crear", "compras/proveedor_form.html"),
            ("compras:compra_crear", "compras/compra_form.html"),
        )
        for name, template in rutas:
            with self.subTest(route=name):
                response = self.client.get(reverse(name))
                self.assertEqual(response.status_code, 200)
                self.assertTemplateUsed(response, template)

        compra = self.crear_compra()
        rutas_con_objeto = (
            (
                "compras:compra_detalle",
                "compras/compra_detail.html",
            ),
            (
                "compras:compra_editar",
                "compras/compra_form.html",
            ),
            (
                "compras:compra_recepcion",
                "compras/compra_recepcion.html",
            ),
            (
                "compras:proveedor_editar",
                "compras/proveedor_form.html",
            ),
        )
        for name, template in rutas_con_objeto:
            with self.subTest(route=name):
                args = (
                    [self.proveedor.pk]
                    if name == "compras:proveedor_editar"
                    else [compra.pk]
                )
                response = self.client.get(reverse(name, args=args))
                self.assertEqual(response.status_code, 200)
                self.assertTemplateUsed(response, template)

    def test_administrador_crea_compra_en_borrador(self):
        self.client.force_login(self.admin_user)
        response = self.client.post(
            reverse("compras:compra_crear"),
            self.compra_form_data(),
        )

        compra = Compra.objects.get()
        self.assertRedirects(
            response,
            reverse("compras:compra_detalle", args=[compra.pk]),
        )
        self.assertEqual(compra.estado, Compra.Estado.BORRADOR)
        self.assertEqual(compra.subtotal, Decimal("45.00"))
        self.assertEqual(compra.total, Decimal("58.00"))
        self.assertEqual(compra.detalles.count(), 1)

    def test_administrador_edita_borrador(self):
        compra = self.crear_compra()
        self.client.force_login(self.admin_user)

        data = self.compra_form_data(
            numero_factura="F-EDITADA",
            impuesto="0.00",
            **{
                "detalles-0-producto": self.producto_2.pk,
                "detalles-0-cantidad": "2",
                "detalles-0-costo_unitario": "6.00",
            },
        )
        data.pop("detalles-0-id", None)

        response = self.client.post(
            reverse("compras:compra_editar", args=[compra.pk]),
            data,
        )
        self.assertRedirects(
            response,
            reverse("compras:compra_detalle", args=[compra.pk]),
        )

        compra.refresh_from_db()
        self.assertEqual(compra.numero_factura, "F-EDITADA")
        self.assertEqual(compra.detalles.count(), 1)
        self.assertEqual(compra.subtotal, Decimal("12.00"))

    def test_administrador_recibe_compra(self):
        compra = self.crear_compra()
        detalle = compra.detalles.get()
        self.client.force_login(self.admin_user)

        response = self.client.post(
            reverse("compras:compra_recepcion", args=[compra.pk]),
            {
                RecepcionCompraForm.nombre_campo(detalle): self.lote.pk,
            },
        )
        self.assertRedirects(
            response,
            reverse("compras:compra_detalle", args=[compra.pk]),
        )

        compra.refresh_from_db()
        self.lote.refresh_from_db()
        self.assertEqual(compra.estado, Compra.Estado.RECIBIDA)
        self.assertEqual(self.lote.stock_actual, Decimal("10.00"))

    def test_administrador_anula_borrador(self):
        compra = self.crear_compra()
        self.client.force_login(self.admin_user)

        response = self.client.post(
            reverse("compras:compra_anular", args=[compra.pk])
        )
        self.assertRedirects(
            response,
            reverse("compras:compra_detalle", args=[compra.pk]),
        )

        compra.refresh_from_db()
        self.assertEqual(compra.estado, Compra.Estado.ANULADA)

    def test_compra_recibida_no_se_puede_editar(self):
        compra = self.crear_compra()
        detalle = compra.detalles.get()
        recibir_compra(
            compra=compra,
            usuario=self.admin_user,
            lotes_por_detalle={detalle.pk: self.lote},
        )
        self.client.force_login(self.admin_user)

        response = self.client.get(
            reverse("compras:compra_editar", args=[compra.pk])
        )
        self.assertRedirects(
            response,
            reverse("compras:compra_detalle", args=[compra.pk]),
        )

    def test_administrador_activa_y_desactiva_proveedor(self):
        self.client.force_login(self.admin_user)
        url = reverse("compras:proveedor_toggle", args=[self.proveedor.pk])

        response = self.client.post(url)
        self.assertRedirects(response, reverse("compras:proveedores"))
        self.proveedor.refresh_from_db()
        self.assertFalse(self.proveedor.activo)

        self.client.post(url)
        self.proveedor.refresh_from_db()
        self.assertTrue(self.proveedor.activo)
