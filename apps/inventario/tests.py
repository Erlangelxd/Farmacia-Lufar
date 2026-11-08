"""Pruebas del módulo de inventario: lotes, movimientos y alertas."""

from datetime import timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from apps.accounts.constants import ADMIN_GROUP, SELLER_GROUP
from apps.catalogo.models import Categoria, Producto

from .forms import LoteForm, MovimientoForm
from .models import Lote, MovimientoInventario
from .services import crear_lote, registrar_movimiento


class InventarioBaseTestData(TestCase):
    """Datos compartidos por las pruebas de inventario."""

    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.admin_group = Group.objects.get(name=ADMIN_GROUP)
        cls.seller_group = Group.objects.get(name=SELLER_GROUP)

        cls.admin_user = user_model.objects.create_user(
            username="admin_inventario",
            password="ClaveSegura123!",
            first_name="Admin",
            last_name="Inventario",
        )
        cls.admin_user.groups.add(cls.admin_group)

        cls.seller_user = user_model.objects.create_user(
            username="vendedor_inventario",
            password="ClaveSegura123!",
        )
        cls.seller_user.groups.add(cls.seller_group)

        cls.categoria = Categoria.objects.create(nombre="Analgésicos")

        cls.producto = Producto.objects.create(
            codigo="P-001",
            nombre="Paracetamol 500 mg",
            categoria=cls.categoria,
            precio_venta=Decimal("5.50"),
            stock_minimo=10,
        )
        cls.producto_inactivo = Producto.objects.create(
            codigo="P-002",
            nombre="Ibuprofeno 400 mg",
            categoria=cls.categoria,
            precio_venta=Decimal("7.25"),
            activo=False,
        )

        hoy = timezone.localdate()
        cls.lote = Lote.objects.create(
            producto=cls.producto,
            codigo_lote="L-001",
            fecha_fabricacion=hoy - timedelta(days=30),
            fecha_vencimiento=hoy + timedelta(days=90),
            stock_actual=Decimal("25.00"),
        )
        cls.lote_sin_stock = Lote.objects.create(
            producto=cls.producto,
            codigo_lote="L-002",
            fecha_vencimiento=hoy + timedelta(days=10),
            stock_actual=Decimal("0.00"),
        )

    def lote_data(self, **overrides):
        data = {
            "producto": self.producto.pk,
            "codigo_lote": "L-100",
            "fecha_fabricacion": "",
            "fecha_vencimiento": "",
            "fecha_ingreso": timezone.localdate().isoformat(),
            "stock_inicial": "0.00",
            "costo_unitario_inicial": "2.00",
            "activo": "on",
        }
        data.update(overrides)
        return data

    def movimiento_data(self, **overrides):
        data = {
            "lote": self.lote.pk,
            "tipo": MovimientoInventario.Tipo.ENTRADA,
            "cantidad": "5.00",
            "costo_unitario": "2.00",
            "motivo": "Compra de prueba",
        }
        data.update(overrides)
        return data


class LoteModelTests(InventarioBaseTestData):
    """Reglas de normalización y estado de los lotes."""

    def test_str_incluye_producto_y_codigo(self):
        self.assertEqual(str(self.lote), f"{self.producto} — lote L-001")

    def test_normaliza_codigo_al_guardar(self):
        lote = Lote.objects.create(
            producto=self.producto,
            codigo_lote="  l-003  ",
            stock_actual=Decimal("0.00"),
        )
        lote.refresh_from_db()
        self.assertEqual(lote.codigo_lote, "L-003")

    def test_rechaza_codigo_duplicado_sin_distinguir_mayusculas(self):
        duplicado = Lote(
            producto=self.producto,
            codigo_lote="l-001",
            stock_actual=Decimal("0.00"),
        )
        with self.assertRaises(ValidationError) as contexto:
            duplicado.full_clean()
        self.assertIn("codigo_lote", contexto.exception.message_dict)
        self.assertIn(
            "El producto ya tiene un lote con ese código.",
            contexto.exception.message_dict["codigo_lote"],
        )

    def test_permite_mismo_codigo_en_producto_distinto(self):
        otro_producto = Producto.objects.create(
            codigo="P-003",
            nombre="Amoxicilina 500 mg",
            precio_venta=Decimal("12.00"),
        )
        lote = Lote(
            producto=otro_producto,
            codigo_lote="L-001",
            stock_actual=Decimal("0.00"),
        )
        lote.full_clean()
        lote.save()
        self.assertEqual(lote.codigo_lote, "L-001")

    def test_rechaza_fecha_vencimiento_anterior_a_fabricacion(self):
        hoy = timezone.localdate()
        lote = Lote(
            producto=self.producto,
            codigo_lote="L-004",
            fecha_fabricacion=hoy,
            fecha_vencimiento=hoy - timedelta(days=1),
            stock_actual=Decimal("0.00"),
        )
        with self.assertRaises(ValidationError) as contexto:
            lote.full_clean()
        self.assertIn("fecha_vencimiento", contexto.exception.message_dict)

    def test_no_permite_desactivar_lote_con_stock(self):
        self.lote.activo = False
        with self.assertRaises(ValidationError) as contexto:
            self.lote.full_clean()
        self.assertIn("activo", contexto.exception.message_dict)

    def test_permite_desactivar_lote_sin_stock(self):
        self.lote_sin_stock.activo = False
        self.lote_sin_stock.full_clean()
        self.lote_sin_stock.save()
        self.lote_sin_stock.refresh_from_db()
        self.assertFalse(self.lote_sin_stock.activo)

    def test_movimiento_calcula_su_signo(self):
        entrada = MovimientoInventario(
            tipo=MovimientoInventario.Tipo.ENTRADA
        )
        salida = MovimientoInventario(
            tipo=MovimientoInventario.Tipo.SALIDA
        )
        self.assertTrue(entrada.es_entrada)
        self.assertEqual(entrada.signo, 1)
        self.assertFalse(salida.es_entrada)
        self.assertEqual(salida.signo, -1)


class InventarioServiceTests(InventarioBaseTestData):
    """Operaciones transaccionales sobre lotes y movimientos."""

    def test_crear_lote_con_stock_inicial_registra_movimiento(self):
        lote = crear_lote(
            producto=self.producto,
            codigo_lote="  l-100  ",
            fecha_vencimiento=timezone.localdate() + timedelta(days=60),
            stock_inicial="12.50",
            costo_unitario="2.00",
            usuario=self.admin_user,
        )

        self.assertEqual(lote.codigo_lote, "L-100")
        self.assertEqual(lote.stock_actual, Decimal("12.50"))
        movimiento = lote.movimientos.get()
        self.assertEqual(movimiento.tipo, MovimientoInventario.Tipo.INICIAL)
        self.assertEqual(movimiento.cantidad, Decimal("12.50"))
        self.assertEqual(movimiento.stock_resultante, Decimal("12.50"))
        self.assertEqual(movimiento.usuario, self.admin_user)
        self.assertEqual(movimiento.motivo, "Carga inicial del lote.")

    def test_crear_lote_sin_stock_no_registra_movimiento(self):
        lote = crear_lote(
            producto=self.producto,
            codigo_lote="L-101",
            stock_inicial="0.00",
            usuario=self.admin_user,
        )
        self.assertEqual(lote.stock_actual, Decimal("0.00"))
        self.assertFalse(lote.movimientos.exists())

    def test_crear_lote_rechaza_producto_inactivo(self):
        with self.assertRaises(ValidationError) as contexto:
            crear_lote(
                producto=self.producto_inactivo,
                codigo_lote="L-102",
                usuario=self.admin_user,
            )
        self.assertIn("inactivo", str(contexto.exception))

    def test_crear_lote_rechaza_codigo_duplicado(self):
        with self.assertRaises(ValidationError) as contexto:
            crear_lote(
                producto=self.producto,
                codigo_lote="l-001",
                usuario=self.admin_user,
            )
        self.assertIn("codigo_lote", contexto.exception.message_dict)

    def test_crear_lote_rechaza_stock_inicial_negativo(self):
        with self.assertRaises(ValidationError):
            crear_lote(
                producto=self.producto,
                codigo_lote="L-103",
                stock_inicial="-1.00",
                usuario=self.admin_user,
            )

    def test_entrada_aumenta_el_stock(self):
        movimiento = registrar_movimiento(
            lote=self.lote,
            tipo=MovimientoInventario.Tipo.ENTRADA,
            cantidad="5.00",
            usuario=self.admin_user,
            motivo="  Compra   de prueba  ",
            costo_unitario="2.50",
        )

        self.lote.refresh_from_db()
        self.assertEqual(self.lote.stock_actual, Decimal("30.00"))
        self.assertEqual(movimiento.stock_resultante, Decimal("30.00"))
        self.assertEqual(movimiento.motivo, "Compra de prueba")
        self.assertEqual(movimiento.usuario, self.admin_user)

    def test_salida_disminuye_el_stock(self):
        registrar_movimiento(
            lote=self.lote,
            tipo=MovimientoInventario.Tipo.SALIDA,
            cantidad="5.00",
            usuario=self.admin_user,
        )
        self.lote.refresh_from_db()
        self.assertEqual(self.lote.stock_actual, Decimal("20.00"))

    def test_ajustes_positivos_y_negativos(self):
        registrar_movimiento(
            lote=self.lote,
            tipo=MovimientoInventario.Tipo.AJUSTE_POSITIVO,
            cantidad="3.00",
            usuario=self.admin_user,
            costo_unitario="2.50",
        )
        registrar_movimiento(
            lote=self.lote,
            tipo=MovimientoInventario.Tipo.AJUSTE_NEGATIVO,
            cantidad="2.00",
            usuario=self.admin_user,
        )

        self.lote.refresh_from_db()
        self.assertEqual(self.lote.stock_actual, Decimal("26.00"))
        self.assertEqual(self.lote.movimientos.count(), 2)

    def test_salida_no_puede_dejar_stock_negativo(self):
        with self.assertRaises(ValidationError):
            registrar_movimiento(
                lote=self.lote,
                tipo=MovimientoInventario.Tipo.SALIDA,
                cantidad="30.00",
                usuario=self.admin_user,
            )

        self.lote.refresh_from_db()
        self.assertEqual(self.lote.stock_actual, Decimal("25.00"))
        self.assertFalse(self.lote.movimientos.exists())

    def test_rechaza_cantidad_cero_o_negativa(self):
        for cantidad in ("0.00", "-1.00"):
            with self.subTest(cantidad=cantidad):
                with self.assertRaises(ValidationError):
                    registrar_movimiento(
                        lote=self.lote,
                        tipo=MovimientoInventario.Tipo.ENTRADA,
                        cantidad=cantidad,
                        usuario=self.admin_user,
                    )

    def test_rechaza_inventario_inicial_manual(self):
        with self.assertRaises(ValidationError) as contexto:
            registrar_movimiento(
                lote=self.lote,
                tipo=MovimientoInventario.Tipo.INICIAL,
                cantidad="1.00",
                usuario=self.admin_user,
            )
        self.assertIn("inventario inicial", str(contexto.exception).lower())

    def test_rechaza_movimiento_en_lote_inactivo(self):
        self.lote_sin_stock.activo = False
        self.lote_sin_stock.save(update_fields=["activo", "actualizado_en"])

        with self.assertRaises(ValidationError):
            registrar_movimiento(
                lote=self.lote_sin_stock,
                tipo=MovimientoInventario.Tipo.ENTRADA,
                cantidad="1.00",
                usuario=self.admin_user,
            )


class InventarioFormTests(InventarioBaseTestData):
    """Validación de los formularios de lotes y movimientos."""

    def test_lote_form_incluye_stock_inicial_al_crear(self):
        form = LoteForm()
        self.assertIn("stock_inicial", form.fields)

    def test_lote_form_no_incluye_stock_inicial_al_editar(self):
        form = LoteForm(instance=self.lote)
        self.assertNotIn("stock_inicial", form.fields)

    def test_lote_form_solo_ofrece_productos_activos(self):
        form = LoteForm()
        productos = form.fields["producto"].queryset
        self.assertIn(self.producto, productos)
        self.assertNotIn(self.producto_inactivo, productos)

    def test_lote_form_conserva_producto_inactivo_al_editar(self):
        lote_inactivo = Lote.objects.create(
            producto=self.producto_inactivo,
            codigo_lote="L-200",
            stock_actual=Decimal("0.00"),
        )
        form = LoteForm(instance=lote_inactivo)
        self.assertIn(
            self.producto_inactivo,
            form.fields["producto"].queryset,
        )

    def test_lote_form_rechaza_codigo_duplicado(self):
        form = LoteForm(data=self.lote_data(codigo_lote=" l-001 "))
        self.assertFalse(form.is_valid())
        self.assertIn("codigo_lote", form.errors)
        self.assertIn(
            "El producto ya tiene un lote con ese código.",
            form.errors["codigo_lote"],
        )

    def test_lote_form_rechaza_fechas_invertidas(self):
        hoy = timezone.localdate()
        form = LoteForm(
            data=self.lote_data(
                codigo_lote="L-104",
                fecha_fabricacion=hoy.isoformat(),
                fecha_vencimiento=(hoy - timedelta(days=1)).isoformat(),
            )
        )
        self.assertFalse(form.is_valid())
        self.assertIn("fecha_vencimiento", form.errors)

    def test_movimiento_form_excluye_inventario_inicial(self):
        form = MovimientoForm()
        valores = {valor for valor, _ in form.fields["tipo"].choices}
        self.assertNotIn(MovimientoInventario.Tipo.INICIAL, valores)
        self.assertIn(MovimientoInventario.Tipo.ENTRADA, valores)

    def test_movimiento_form_solo_ofrece_lotes_activos(self):
        lote_inactivo = Lote.objects.create(
            producto=self.producto,
            codigo_lote="L-201",
            stock_actual=Decimal("0.00"),
            activo=False,
        )
        form = MovimientoForm()
        lotes = form.fields["lote"].queryset
        self.assertIn(self.lote, lotes)
        self.assertNotIn(lote_inactivo, lotes)

    def test_movimiento_form_rechaza_salida_mayor_al_stock(self):
        form = MovimientoForm(
            data=self.movimiento_data(
                tipo=MovimientoInventario.Tipo.SALIDA,
                cantidad="30.00",
            )
        )
        self.assertFalse(form.is_valid())
        self.assertIn("cantidad", form.errors)

    def test_movimiento_form_acepta_entrada(self):
        form = MovimientoForm(data=self.movimiento_data())
        self.assertTrue(form.is_valid(), form.errors)


class InventarioViewTests(InventarioBaseTestData):
    """Acceso por rol, CRUD de lotes y registro de movimientos."""

    def test_vendedor_recibe_403_en_todas_las_rutas(self):
        self.client.force_login(self.seller_user)
        rutas = (
            reverse("inventario:index"),
            reverse("inventario:lotes"),
            reverse("inventario:lote_crear"),
            reverse("inventario:lote_editar", args=[self.lote.pk]),
            reverse("inventario:lote_estado", args=[self.lote.pk]),
            reverse("inventario:movimientos"),
            reverse("inventario:movimiento_crear"),
        )
        for url in rutas:
            with self.subTest(url=url):
                self.assertEqual(self.client.get(url).status_code, 403)

    def test_administrador_consulta_existencias(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse("inventario:index"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "inventario/index.html")
        self.assertContains(response, "Inventario")
        self.assertContains(response, "Paracetamol 500 mg")
        self.assertContains(response, "Lotes")
        self.assertContains(response, "Movimientos")

    def test_existencias_muestra_alerta_de_stock_bajo(self):
        producto_bajo = Producto.objects.create(
            codigo="P-010",
            nombre="Producto con reposición",
            categoria=self.categoria,
            precio_venta=Decimal("3.00"),
            stock_minimo=100,
        )
        Lote.objects.create(
            producto=producto_bajo,
            codigo_lote="L-010",
            stock_actual=Decimal("5.00"),
        )
        self.client.force_login(self.admin_user)
        response = self.client.get(
            reverse("inventario:index"),
            {"alerta": "bajo"},
        )

        self.assertContains(response, "Producto con reposición")
        self.assertContains(response, "Bajo mínimo")
        self.assertNotContains(response, "Paracetamol 500 mg")

    def test_existencias_filtra_por_busqueda(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(
            reverse("inventario:index"),
            {"q": "paracetamol"},
        )
        self.assertContains(response, "Paracetamol 500 mg")
        self.assertNotContains(response, "Ibuprofeno 400 mg")

    def test_administrador_crea_lote_con_stock_inicial(self):
        self.client.force_login(self.admin_user)
        response = self.client.post(
            reverse("inventario:lote_crear"),
            self.lote_data(codigo_lote=" l-100 ", stock_inicial="8.00"),
        )

        self.assertRedirects(response, reverse("inventario:lotes"))
        lote = Lote.objects.get(codigo_lote="L-100")
        self.assertEqual(lote.stock_actual, Decimal("8.00"))
        movimiento = lote.movimientos.get()
        self.assertEqual(movimiento.tipo, MovimientoInventario.Tipo.INICIAL)
        self.assertEqual(movimiento.stock_resultante, Decimal("8.00"))

    def test_administrador_edita_lote_sin_cambiar_stock(self):
        self.client.force_login(self.admin_user)
        response = self.client.post(
            reverse("inventario:lote_editar", args=[self.lote.pk]),
            self.lote_data(
                codigo_lote="L-001-A",
                fecha_vencimiento=(
                    timezone.localdate() + timedelta(days=120)
                ).isoformat(),
            ),
        )

        self.assertRedirects(response, reverse("inventario:lotes"))
        self.lote.refresh_from_db()
        self.assertEqual(self.lote.codigo_lote, "L-001-A")
        self.assertEqual(self.lote.stock_actual, Decimal("25.00"))
        self.assertFalse(self.lote.movimientos.exists())

    def test_administrador_no_desactiva_lote_con_stock(self):
        self.client.force_login(self.admin_user)
        response = self.client.post(
            reverse("inventario:lote_estado", args=[self.lote.pk]),
            follow=True,
        )

        self.assertContains(response, "No puedes desactivar un lote")
        self.lote.refresh_from_db()
        self.assertTrue(self.lote.activo)

    def test_administrador_desactiva_y_reactiva_lote_sin_stock(self):
        self.client.force_login(self.admin_user)
        url = reverse("inventario:lote_estado", args=[self.lote_sin_stock.pk])

        response = self.client.post(url)
        self.assertRedirects(response, reverse("inventario:lotes"))
        self.lote_sin_stock.refresh_from_db()
        self.assertFalse(self.lote_sin_stock.activo)

        response = self.client.post(url)
        self.assertRedirects(response, reverse("inventario:lotes"))
        self.lote_sin_stock.refresh_from_db()
        self.assertTrue(self.lote_sin_stock.activo)

    def test_administrador_registra_movimiento(self):
        self.client.force_login(self.admin_user)
        response = self.client.post(
            reverse("inventario:movimiento_crear"),
            self.movimiento_data(cantidad="5.00"),
        )

        self.assertRedirects(response, reverse("inventario:movimientos"))
        self.lote.refresh_from_db()
        self.assertEqual(self.lote.stock_actual, Decimal("30.00"))
        self.assertTrue(
            self.lote.movimientos.filter(
                tipo=MovimientoInventario.Tipo.ENTRADA,
                cantidad=Decimal("5.00"),
            ).exists()
        )

    def test_administrador_no_registra_salida_excesiva(self):
        self.client.force_login(self.admin_user)
        response = self.client.post(
            reverse("inventario:movimiento_crear"),
            self.movimiento_data(
                tipo=MovimientoInventario.Tipo.SALIDA,
                cantidad="30.00",
            ),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "solo tiene 25.00 unidades")
        self.lote.refresh_from_db()
        self.assertEqual(self.lote.stock_actual, Decimal("25.00"))
        self.assertFalse(self.lote.movimientos.exists())

    def test_listado_de_lotes_filtra_por_estado_y_vencimiento(self):
        hoy = timezone.localdate()
        vencido = Lote.objects.create(
            producto=self.producto,
            codigo_lote="L-300",
            fecha_vencimiento=hoy - timedelta(days=5),
            stock_actual=Decimal("1.00"),
        )
        por_vencer = Lote.objects.create(
            producto=self.producto,
            codigo_lote="L-301",
            fecha_vencimiento=hoy + timedelta(days=5),
            stock_actual=Decimal("1.00"),
        )
        self.client.force_login(self.admin_user)

        response = self.client.get(
            reverse("inventario:lotes"),
            {"vencimiento": "vencidos"},
        )
        self.assertContains(response, vencido.codigo_lote)
        self.assertNotContains(response, por_vencer.codigo_lote)

        response = self.client.get(
            reverse("inventario:lotes"),
            {"vencimiento": "por_vencer"},
        )
        self.assertContains(response, por_vencer.codigo_lote)
        self.assertNotContains(response, vencido.codigo_lote)

        response = self.client.get(
            reverse("inventario:lotes"),
            {"q": "L-001"},
        )
        self.assertContains(response, "L-001")
        self.assertNotContains(response, "L-300")

    def test_listado_de_movimientos_filtra_por_tipo_y_busqueda(self):
        registrar_movimiento(
            lote=self.lote,
            tipo=MovimientoInventario.Tipo.ENTRADA,
            cantidad="5.00",
            usuario=self.admin_user,
            motivo="Compra de proveedor",
            costo_unitario="2.00",
        )
        registrar_movimiento(
            lote=self.lote,
            tipo=MovimientoInventario.Tipo.SALIDA,
            cantidad="2.00",
            usuario=self.admin_user,
            motivo="Venta mostrador",
        )
        self.client.force_login(self.admin_user)

        response = self.client.get(
            reverse("inventario:movimientos"),
            {"tipo": MovimientoInventario.Tipo.ENTRADA},
        )
        self.assertContains(response, "Compra de proveedor")
        self.assertNotContains(response, "Venta mostrador")

        response = self.client.get(
            reverse("inventario:movimientos"),
            {"q": "venta mostrador"},
        )
        self.assertContains(response, "Venta mostrador")
        self.assertNotContains(response, "Compra de proveedor")

    def test_administrador_ve_formularios_de_inventario(self):
        self.client.force_login(self.admin_user)

        response = self.client.get(reverse("inventario:lote_crear"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "inventario/lote_form.html")
        self.assertContains(response, "Nuevo lote")

        response = self.client.get(reverse("inventario:movimiento_crear"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "inventario/movimiento_form.html")
        self.assertContains(response, "Registrar movimiento")
