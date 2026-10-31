"""Pruebas del módulo de ventas."""

from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.test import Client, TestCase
from django.urls import reverse

from apps.accounts.constants import SELLER_GROUP
from apps.catalogo.models import Producto
from apps.clientes.models import Cliente

from .forms import DetalleVentaFormSet, VentaForm
from .models import DetalleVenta, Venta
from .services import registrar_venta


class VentaBaseTestData(TestCase):
    """Datos compartidos por las pruebas de ventas."""

    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.seller_group = Group.objects.get(name=SELLER_GROUP)
        cls.seller_user = user_model.objects.create_user(
            username="vendedor_ventas",
            password="ClaveSegura123!",
            first_name="Vendedor",
            last_name="Ventas",
        )
        cls.seller_user.groups.add(cls.seller_group)

        cls.cliente = Cliente.objects.create(
            nombre="Ana Pérez",
            tipo_documento=Cliente.TipoDocumento.CI,
            numero_documento="12345678",
            telefono="71234567",
        )
        cls.otro_cliente = Cliente.objects.create(
            nombre="Luis Gómez",
            telefono="76543210",
        )
        cls.producto_a = Producto.objects.create(
            codigo="P-001",
            nombre="Paracetamol 500 mg",
            precio_venta=Decimal("5.50"),
        )
        cls.producto_b = Producto.objects.create(
            codigo="P-002",
            nombre="Ibuprofeno 400 mg",
            precio_venta=Decimal("7.25"),
        )
        cls.producto_inactivo = Producto.objects.create(
            codigo="P-003",
            nombre="Producto inactivo",
            precio_venta=Decimal("3.00"),
            activo=False,
        )


class VentaServiceTests(VentaBaseTestData):
    """Cálculos y validaciones del servicio transaccional."""

    def test_registra_venta_con_detalles_y_calcula_total(self):
        venta = registrar_venta(
            vendedor=self.seller_user,
            cliente=self.cliente,
            metodo_pago=Venta.MetodoPago.EFECTIVO,
            monto_recibido=Decimal("20.00"),
            lineas=[
                {"producto": self.producto_a, "cantidad": 2},
                {"producto": self.producto_b, "cantidad": 1},
            ],
        )

        self.assertEqual(venta.total, Decimal("18.25"))
        self.assertEqual(venta.cambio, Decimal("1.75"))
        self.assertEqual(venta.detalles.count(), 2)
        self.assertEqual(venta.cantidad_productos, 3)
        self.assertEqual(venta.numero, f"V-{venta.pk:06d}")

        detalle_a = venta.detalles.get(producto=self.producto_a)
        self.assertEqual(detalle_a.codigo_producto, "P-001")
        self.assertEqual(detalle_a.nombre_producto, "Paracetamol 500 mg")
        self.assertEqual(detalle_a.precio_unitario, Decimal("5.50"))
        self.assertEqual(detalle_a.subtotal, Decimal("11.00"))

    def test_registra_venta_sin_cliente(self):
        venta = registrar_venta(
            vendedor=self.seller_user,
            cliente=None,
            metodo_pago=Venta.MetodoPago.EFECTIVO,
            monto_recibido=Decimal("5.50"),
            lineas=[{"producto": self.producto_a, "cantidad": 1}],
        )

        self.assertIsNone(venta.cliente)
        self.assertIn("Consumidor final", str(venta))

    def test_rechaza_venta_sin_lineas(self):
        with self.assertRaises(ValidationError) as contexto:
            registrar_venta(
                vendedor=self.seller_user,
                cliente=self.cliente,
                metodo_pago=Venta.MetodoPago.EFECTIVO,
                monto_recibido=Decimal("10.00"),
                lineas=[],
            )
        self.assertIn(
            "Agrega al menos un producto a la venta.",
            contexto.exception.messages,
        )
        self.assertEqual(Venta.objects.count(), 0)

    def test_rechaza_producto_inactivo(self):
        with self.assertRaises(ValidationError) as contexto:
            registrar_venta(
                vendedor=self.seller_user,
                cliente=self.cliente,
                metodo_pago=Venta.MetodoPago.EFECTIVO,
                monto_recibido=Decimal("10.00"),
                lineas=[
                    {"producto": self.producto_inactivo, "cantidad": 1}
                ],
            )
        self.assertIn(
            "no está activo",
            " ".join(contexto.exception.messages),
        )
        self.assertEqual(Venta.objects.count(), 0)

    def test_rechaza_producto_con_precio_negativo(self):
        producto = Producto.objects.create(
            codigo="P-NEG",
            nombre="Producto con precio negativo",
            precio_venta=Decimal("-1.00"),
        )
        with self.assertRaises(ValidationError) as contexto:
            registrar_venta(
                vendedor=self.seller_user,
                cliente=self.cliente,
                metodo_pago=Venta.MetodoPago.EFECTIVO,
                monto_recibido=Decimal("10.00"),
                lineas=[{"producto": producto, "cantidad": 1}],
            )
        self.assertIn(
            "tiene un precio inválido",
            " ".join(contexto.exception.messages),
        )
        self.assertEqual(Venta.objects.count(), 0)

    def test_rechaza_cantidad_cero(self):
        with self.assertRaises(ValidationError) as contexto:
            registrar_venta(
                vendedor=self.seller_user,
                cliente=self.cliente,
                metodo_pago=Venta.MetodoPago.EFECTIVO,
                monto_recibido=Decimal("10.00"),
                lineas=[{"producto": self.producto_a, "cantidad": 0}],
            )
        self.assertIn(
            "La cantidad debe ser mayor que cero.",
            contexto.exception.messages,
        )

    def test_rechaza_producto_duplicado(self):
        with self.assertRaises(ValidationError) as contexto:
            registrar_venta(
                vendedor=self.seller_user,
                cliente=self.cliente,
                metodo_pago=Venta.MetodoPago.EFECTIVO,
                monto_recibido=Decimal("20.00"),
                lineas=[
                    {"producto": self.producto_a, "cantidad": 1},
                    {"producto": self.producto_a, "cantidad": 2},
                ],
            )
        self.assertIn(
            "está repetido en la venta",
            " ".join(contexto.exception.messages),
        )
        self.assertEqual(Venta.objects.count(), 0)

    def test_rechaza_efectivo_insuficiente(self):
        with self.assertRaises(ValidationError) as contexto:
            registrar_venta(
                vendedor=self.seller_user,
                cliente=self.cliente,
                metodo_pago=Venta.MetodoPago.EFECTIVO,
                monto_recibido=Decimal("5.00"),
                lineas=[{"producto": self.producto_a, "cantidad": 2}],
            )
        self.assertIn(
            "El monto recibido no cubre el total de la venta.",
            contexto.exception.messages,
        )
        self.assertEqual(Venta.objects.count(), 0)

    def test_rechaza_cliente_inactivo(self):
        cliente_inactivo = Cliente.objects.create(
            nombre="Cliente inactivo",
            activo=False,
        )
        with self.assertRaises(ValidationError) as contexto:
            registrar_venta(
                vendedor=self.seller_user,
                cliente=cliente_inactivo,
                metodo_pago=Venta.MetodoPago.EFECTIVO,
                monto_recibido=Decimal("10.00"),
                lineas=[{"producto": self.producto_a, "cantidad": 1}],
            )
        self.assertIn(
            "El cliente seleccionado no está activo.",
            contexto.exception.messages,
        )

    def test_rechaza_metodo_pago_no_disponible(self):
        with self.assertRaises(ValidationError) as contexto:
            registrar_venta(
                vendedor=self.seller_user,
                cliente=self.cliente,
                metodo_pago="TARJETA",
                monto_recibido=Decimal("10.00"),
                lineas=[{"producto": self.producto_a, "cantidad": 1}],
            )
        self.assertIn(
            "El método de pago seleccionado no está disponible.",
            contexto.exception.messages,
        )

    def test_rechaza_total_que_excede_el_maximo(self):
        producto_caro = Producto.objects.create(
            codigo="P-999",
            nombre="Producto de precio alto",
            precio_venta=Decimal("99999999.99"),
        )
        with self.assertRaises(ValidationError) as contexto:
            registrar_venta(
                vendedor=self.seller_user,
                cliente=self.cliente,
                metodo_pago=Venta.MetodoPago.EFECTIVO,
                monto_recibido=Decimal("9999999999.99"),
                lineas=[{"producto": producto_caro, "cantidad": 101}],
            )
        self.assertIn(
            "El total de la venta excede el máximo permitido.",
            contexto.exception.messages,
        )
        self.assertEqual(Venta.objects.count(), 0)

    def test_monto_igual_al_total_no_genera_cambio(self):
        venta = registrar_venta(
            vendedor=self.seller_user,
            cliente=self.cliente,
            metodo_pago=Venta.MetodoPago.EFECTIVO,
            monto_recibido=Decimal("5.50"),
            lineas=[{"producto": self.producto_a, "cantidad": 1}],
        )
        self.assertEqual(venta.cambio, Decimal("0.00"))

    def test_rollback_si_falla_la_creacion_de_detalles(self):
        with patch(
            "apps.ventas.services.DetalleVenta.objects.bulk_create",
            side_effect=RuntimeError("fallo simulado"),
        ):
            with self.assertRaises(RuntimeError):
                registrar_venta(
                    vendedor=self.seller_user,
                    cliente=self.cliente,
                    metodo_pago=Venta.MetodoPago.EFECTIVO,
                    monto_recibido=Decimal("10.00"),
                    lineas=[{"producto": self.producto_a, "cantidad": 1}],
                )

        self.assertEqual(Venta.objects.count(), 0)
        self.assertEqual(DetalleVenta.objects.count(), 0)


class VentaModelTests(VentaBaseTestData):
    """Reglas y propiedades de los modelos de venta."""

    def test_numero_sin_guardar(self):
        self.assertEqual(Venta().numero, "Sin número")

    def test_detalle_calcula_subtotal(self):
        detalle = DetalleVenta(
            cantidad=3,
            precio_unitario=Decimal("5.50"),
        )
        self.assertEqual(detalle.subtotal, Decimal("16.50"))

    def test_str_de_venta_y_detalle(self):
        venta = registrar_venta(
            vendedor=self.seller_user,
            cliente=self.cliente,
            metodo_pago=Venta.MetodoPago.EFECTIVO,
            monto_recibido=Decimal("5.50"),
            lineas=[{"producto": self.producto_a, "cantidad": 1}],
        )
        self.assertIn("Ana Pérez", str(venta))
        self.assertEqual(
            str(venta.detalles.first()),
            "Paracetamol 500 mg x 1",
        )

    def test_full_clean_rechaza_monto_menor_al_total(self):
        venta = Venta(
            cliente=self.cliente,
            vendedor=self.seller_user,
            metodo_pago=Venta.MetodoPago.EFECTIVO,
            monto_recibido=Decimal("5.00"),
            total=Decimal("10.00"),
        )
        with self.assertRaises(ValidationError):
            venta.full_clean()

    def test_full_clean_rechaza_cantidad_cero_en_detalle(self):
        venta = Venta.objects.create(
            cliente=self.cliente,
            vendedor=self.seller_user,
            metodo_pago=Venta.MetodoPago.EFECTIVO,
            monto_recibido=Decimal("0.00"),
            total=Decimal("0.00"),
        )
        detalle = DetalleVenta(
            venta=venta,
            producto=self.producto_a,
            codigo_producto=self.producto_a.codigo,
            nombre_producto=self.producto_a.nombre,
            cantidad=0,
            precio_unitario=self.producto_a.precio_venta,
        )
        with self.assertRaises(ValidationError):
            detalle.full_clean()

    def test_full_clean_rechaza_producto_duplicado_en_venta(self):
        venta = registrar_venta(
            vendedor=self.seller_user,
            cliente=self.cliente,
            metodo_pago=Venta.MetodoPago.EFECTIVO,
            monto_recibido=Decimal("5.50"),
            lineas=[{"producto": self.producto_a, "cantidad": 1}],
        )
        duplicado = DetalleVenta(
            venta=venta,
            producto=self.producto_a,
            codigo_producto=self.producto_a.codigo,
            nombre_producto=self.producto_a.nombre,
            cantidad=1,
            precio_unitario=self.producto_a.precio_venta,
        )
        with self.assertRaises(ValidationError):
            duplicado.full_clean()

    def test_detalle_conserva_copia_historica(self):
        venta = registrar_venta(
            vendedor=self.seller_user,
            cliente=self.cliente,
            metodo_pago=Venta.MetodoPago.EFECTIVO,
            monto_recibido=Decimal("5.50"),
            lineas=[{"producto": self.producto_a, "cantidad": 1}],
        )
        detalle = venta.detalles.get(producto=self.producto_a)

        self.producto_a.nombre = "Paracetamol 1 g"
        self.producto_a.precio_venta = Decimal("9.99")
        self.producto_a.save()

        detalle.refresh_from_db()
        self.assertEqual(detalle.nombre_producto, "Paracetamol 500 mg")
        self.assertEqual(detalle.precio_unitario, Decimal("5.50"))


class VentaFormTests(VentaBaseTestData):
    """Validaciones de los formularios y del formset."""

    def test_cliente_es_opcional(self):
        form = VentaForm(
            data={
                "cliente": "",
                "metodo_pago": Venta.MetodoPago.EFECTIVO,
                "monto_recibido": "10.00",
            }
        )
        self.assertTrue(form.is_valid(), form.errors)
        self.assertIsNone(form.cleaned_data["cliente"])

    def test_solo_muestra_clientes_activos(self):
        cliente_inactivo = Cliente.objects.create(
            nombre="Cliente inactivo formulario",
            activo=False,
        )
        form = VentaForm()
        ids = set(form.fields["cliente"].queryset.values_list("pk", flat=True))
        self.assertIn(self.cliente.pk, ids)
        self.assertNotIn(cliente_inactivo.pk, ids)

    def test_metodo_pago_solo_efectivo(self):
        form = VentaForm()
        self.assertEqual(
            list(form.fields["metodo_pago"].choices),
            [("EFECTIVO", "Efectivo")],
        )

    def test_rechaza_monto_negativo(self):
        form = VentaForm(
            data={
                "cliente": "",
                "metodo_pago": Venta.MetodoPago.EFECTIVO,
                "monto_recibido": "-1.00",
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("monto_recibido", form.errors)

    def test_formset_valido_con_una_linea(self):
        formset = DetalleVentaFormSet(
            data={
                "detalles-TOTAL_FORMS": "1",
                "detalles-INITIAL_FORMS": "0",
                "detalles-MIN_NUM_FORMS": "1",
                "detalles-MAX_NUM_FORMS": "1000",
                "detalles-0-producto": str(self.producto_a.pk),
                "detalles-0-cantidad": "2",
            },
            instance=Venta(),
            prefix="detalles",
        )
        self.assertTrue(formset.is_valid(), formset.errors)

    def test_formset_rechaza_venta_sin_lineas(self):
        formset = DetalleVentaFormSet(
            data={
                "detalles-TOTAL_FORMS": "1",
                "detalles-INITIAL_FORMS": "0",
                "detalles-MIN_NUM_FORMS": "1",
                "detalles-MAX_NUM_FORMS": "1000",
                "detalles-0-producto": "",
                "detalles-0-cantidad": "",
            },
            instance=Venta(),
            prefix="detalles",
        )
        self.assertFalse(formset.is_valid())
        self.assertIn(
            "Agrega al menos un producto a la venta.",
            formset.non_form_errors(),
        )

    def test_formset_rechaza_producto_duplicado(self):
        formset = DetalleVentaFormSet(
            data={
                "detalles-TOTAL_FORMS": "2",
                "detalles-INITIAL_FORMS": "0",
                "detalles-MIN_NUM_FORMS": "1",
                "detalles-MAX_NUM_FORMS": "1000",
                "detalles-0-producto": str(self.producto_a.pk),
                "detalles-0-cantidad": "1",
                "detalles-1-producto": str(self.producto_a.pk),
                "detalles-1-cantidad": "2",
            },
            instance=Venta(),
            prefix="detalles",
        )
        self.assertFalse(formset.is_valid())
        self.assertIn(
            "está repetido en la venta",
            " ".join(formset.non_form_errors()),
        )

    def test_formset_rechaza_producto_inactivo(self):
        formset = DetalleVentaFormSet(
            data={
                "detalles-TOTAL_FORMS": "1",
                "detalles-INITIAL_FORMS": "0",
                "detalles-MIN_NUM_FORMS": "1",
                "detalles-MAX_NUM_FORMS": "1000",
                "detalles-0-producto": str(self.producto_inactivo.pk),
                "detalles-0-cantidad": "1",
            },
            instance=Venta(),
            prefix="detalles",
        )
        self.assertFalse(formset.is_valid())
        self.assertIn("producto", formset.forms[0].errors)

    def test_formset_rechaza_cantidad_cero(self):
        formset = DetalleVentaFormSet(
            data={
                "detalles-TOTAL_FORMS": "1",
                "detalles-INITIAL_FORMS": "0",
                "detalles-MIN_NUM_FORMS": "1",
                "detalles-MAX_NUM_FORMS": "1000",
                "detalles-0-producto": str(self.producto_a.pk),
                "detalles-0-cantidad": "0",
            },
            instance=Venta(),
            prefix="detalles",
        )
        self.assertFalse(formset.is_valid())
        self.assertIn("cantidad", formset.forms[0].errors)


class VentaViewTests(VentaBaseTestData):
    """Listado, registro, detalle, ticket e historial de cliente."""

    @classmethod
    def setUpTestData(cls):
        super().setUpTestData()
        cls.venta = registrar_venta(
            vendedor=cls.seller_user,
            cliente=cls.cliente,
            metodo_pago=Venta.MetodoPago.EFECTIVO,
            monto_recibido=Decimal("20.00"),
            lineas=[
                {"producto": cls.producto_a, "cantidad": 2},
                {"producto": cls.producto_b, "cantidad": 1},
            ],
        )

    def setUp(self):
        self.client.force_login(self.seller_user)

    def _datos_venta(self, **cambios):
        datos = {
            "cliente": str(self.cliente.pk),
            "metodo_pago": Venta.MetodoPago.EFECTIVO,
            "monto_recibido": "20.00",
            "detalles-TOTAL_FORMS": "1",
            "detalles-INITIAL_FORMS": "0",
            "detalles-MIN_NUM_FORMS": "1",
            "detalles-MAX_NUM_FORMS": "1000",
            "detalles-0-producto": str(self.producto_a.pk),
            "detalles-0-cantidad": "2",
        }
        datos.update(cambios)
        return datos

    def test_vistas_requieren_autenticacion(self):
        self.client.logout()
        login_url = reverse("accounts:login")
        urls = (
            reverse("ventas:index"),
            reverse("ventas:crear"),
            reverse("ventas:detalle", args=[self.venta.pk]),
            reverse("ventas:ticket", args=[self.venta.pk]),
        )
        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertRedirects(response, f"{login_url}?next={url}")

    def test_listado_muestra_ventas(self):
        response = self.client.get(reverse("ventas:index"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "ventas/venta_list.html")
        self.assertContains(response, self.venta.numero)
        self.assertContains(response, "Ana Pérez")
        self.assertContains(response, "Paracetamol 500 mg")
        self.assertContains(response, "Bs 18.25")
        self.assertContains(response, "Registrar venta")
        self.assertContains(response, "Registrada")

    def test_busqueda_por_numero_cliente_y_producto(self):
        casos = (
            (self.venta.numero, "Ana Pérez"),
            ("Ana", "Ana Pérez"),
            ("Paracetamol", "Paracetamol 500 mg"),
        )
        for busqueda, esperado in casos:
            with self.subTest(busqueda=busqueda):
                response = self.client.get(
                    reverse("ventas:index"),
                    {"q": busqueda},
                )
                self.assertContains(response, esperado)
                self.assertContains(response, self.venta.numero)

        response = self.client.get(
            reverse("ventas:index"),
            {"q": "No existe"},
        )
        self.assertContains(response, "No encontramos ventas")

    def test_filtro_por_cliente(self):
        otra_venta = registrar_venta(
            vendedor=self.seller_user,
            cliente=self.otro_cliente,
            metodo_pago=Venta.MetodoPago.EFECTIVO,
            monto_recibido=Decimal("5.50"),
            lineas=[{"producto": self.producto_a, "cantidad": 1}],
        )
        response = self.client.get(
            reverse("ventas:index"),
            {"cliente": str(self.otro_cliente.pk)},
        )
        self.assertContains(response, otra_venta.numero)
        self.assertNotContains(response, self.venta.numero)

    def test_listado_vacio(self):
        Venta.objects.all().delete()
        response = self.client.get(reverse("ventas:index"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Aún no hay ventas registradas")
        self.assertContains(response, "Registrar primera venta")

    def test_paginacion_del_listado(self):
        Venta.objects.all().delete()
        for _ in range(25):
            Venta.objects.create(
                vendedor=self.seller_user,
                metodo_pago=Venta.MetodoPago.EFECTIVO,
                monto_recibido=Decimal("10.00"),
                total=Decimal("10.00"),
            )

        response = self.client.get(reverse("ventas:index"))
        self.assertTrue(response.context["is_paginated"])
        self.assertEqual(len(response.context["ventas"]), 20)
        self.assertEqual(response.context["paginator"].count, 25)

        response = self.client.get(reverse("ventas:index"), {"page": 2})
        self.assertEqual(len(response.context["ventas"]), 5)

    def test_formulario_de_registro_renderiza_campos(self):
        response = self.client.get(reverse("ventas:crear"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "ventas/venta_form.html")
        self.assertContains(response, "Registrar venta")
        self.assertContains(response, "csrfmiddlewaretoken")
        self.assertContains(response, "detalles-TOTAL_FORMS")
        self.assertContains(response, "Consumidor final")
        self.assertContains(response, "Paracetamol 500 mg")
        self.assertContains(response, "data-sale-form")

    def test_formulario_sin_productos_activos(self):
        Producto.objects.update(activo=False)
        response = self.client.get(reverse("ventas:crear"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No hay productos activos")
        self.assertContains(response, "disabled")

    def test_registro_valido_redirige_al_detalle(self):
        response = self.client.post(
            reverse("ventas:crear"),
            self._datos_venta(),
            follow=True,
        )

        venta = Venta.objects.latest("pk")
        self.assertRedirects(
            response,
            reverse("ventas:detalle", args=[venta.pk]),
        )
        self.assertEqual(venta.cliente, self.cliente)
        self.assertEqual(venta.vendedor, self.seller_user)
        self.assertEqual(venta.total, Decimal("11.00"))
        self.assertEqual(venta.detalles.count(), 1)
        self.assertContains(response, "se registró correctamente")
        self.assertContains(response, "Paracetamol 500 mg")

    def test_registro_sin_cliente_es_consumidor_final(self):
        response = self.client.post(
            reverse("ventas:crear"),
            self._datos_venta(
                cliente="",
                monto_recibido="11.00",
            ),
            follow=True,
        )
        venta = Venta.objects.latest("pk")
        self.assertIsNone(venta.cliente)
        self.assertContains(response, "Consumidor final")

    def test_registro_sin_productos_muestra_error(self):
        cantidad_inicial = Venta.objects.count()
        response = self.client.post(
            reverse("ventas:crear"),
            self._datos_venta(
                **{
                    "detalles-0-producto": "",
                    "detalles-0-cantidad": "",
                }
            ),
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            "Agrega al menos un producto a la venta.",
            response.context["formset"].non_form_errors(),
        )
        self.assertEqual(Venta.objects.count(), cantidad_inicial)

    def test_registro_con_efectivo_insuficiente_muestra_error(self):
        cantidad_inicial = Venta.objects.count()
        response = self.client.post(
            reverse("ventas:crear"),
            self._datos_venta(monto_recibido="1.00"),
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            "El monto recibido no cubre el total de la venta.",
            response.context["form"].non_field_errors(),
        )
        self.assertEqual(Venta.objects.count(), cantidad_inicial)

    def test_registro_con_producto_duplicado_muestra_error(self):
        cantidad_inicial = Venta.objects.count()
        response = self.client.post(
            reverse("ventas:crear"),
            self._datos_venta(
                **{
                    "detalles-TOTAL_FORMS": "2",
                    "detalles-1-producto": str(self.producto_a.pk),
                    "detalles-1-cantidad": "1",
                }
            ),
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            "está repetido en la venta",
            " ".join(response.context["formset"].non_form_errors()),
        )
        self.assertEqual(Venta.objects.count(), cantidad_inicial)

    def test_registro_ignora_linea_marcada_para_eliminar(self):
        response = self.client.post(
            reverse("ventas:crear"),
            self._datos_venta(
                **{
                    "detalles-TOTAL_FORMS": "2",
                    "detalles-0-DELETE": "on",
                    "detalles-0-cantidad": "1",
                    "detalles-1-producto": str(self.producto_b.pk),
                    "detalles-1-cantidad": "2",
                }
            ),
            follow=True,
        )
        venta = Venta.objects.latest("pk")
        self.assertRedirects(
            response,
            reverse("ventas:detalle", args=[venta.pk]),
        )
        self.assertEqual(venta.detalles.count(), 1)
        self.assertEqual(venta.detalles.first().producto, self.producto_b)
        self.assertEqual(venta.total, Decimal("14.50"))

    def test_registro_con_todas_las_lineas_eliminadas_muestra_error(self):
        cantidad_inicial = Venta.objects.count()
        response = self.client.post(
            reverse("ventas:crear"),
            self._datos_venta(**{"detalles-0-DELETE": "on"}),
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            "Agrega al menos un producto a la venta.",
            response.context["formset"].non_form_errors(),
        )
        self.assertContains(response, "is-removed")
        self.assertEqual(Venta.objects.count(), cantidad_inicial)

    def test_registro_requiere_csrf(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.seller_user)
        response = csrf_client.post(
            reverse("ventas:crear"),
            self._datos_venta(),
        )
        self.assertEqual(response.status_code, 403)

    def test_detalle_muestra_ficha_de_venta(self):
        response = self.client.get(
            reverse("ventas:detalle", args=[self.venta.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "ventas/venta_detail.html")
        self.assertContains(response, self.venta.numero)
        self.assertContains(response, "Ana Pérez")
        self.assertContains(response, "Paracetamol 500 mg")
        self.assertContains(response, "Ibuprofeno 400 mg")
        self.assertContains(response, "Bs 18.25")
        self.assertContains(response, "Ver ticket")
        self.assertContains(response, "Efectivo")

    def test_ticket_muestra_datos(self):
        response = self.client.get(
            reverse("ventas:ticket", args=[self.venta.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "ventas/ticket.html")
        self.assertContains(response, "ticket-page")
        self.assertContains(response, "Ticket de venta")
        self.assertContains(response, self.venta.numero)
        self.assertContains(response, "Ana Pérez")
        self.assertContains(response, "Paracetamol 500 mg")
        self.assertContains(response, "Bs 18.25")
        self.assertContains(response, "Efectivo")
        self.assertContains(response, "Cambio")
        self.assertContains(response, "Gracias por su compra")
        self.assertContains(response, "Imprimir ticket")

    def test_detalle_y_ticket_inexistentes_devuelven_404(self):
        for name in ("ventas:detalle", "ventas:ticket"):
            with self.subTest(route=name):
                response = self.client.get(reverse(name, args=[999999]))
                self.assertEqual(response.status_code, 404)
                self.assertTemplateUsed(response, "404.html")

    def test_cliente_detalle_muestra_historial_de_ventas(self):
        response = self.client.get(
            reverse("clientes:detalle", args=[self.cliente.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Historial comercial")
        self.assertContains(response, self.venta.numero)
        self.assertContains(response, "Bs 18.25")
        self.assertContains(response, "Ver todas")
