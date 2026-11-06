"""Pruebas del catálogo mínimo de productos."""

from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from apps.accounts.constants import ADMIN_GROUP, SELLER_GROUP

from .forms import CategoriaForm, ProductoForm
from .models import Categoria, Producto


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


class CategoriaModelTests(TestCase):
    """Reglas de normalización y estado de las categorías."""

    def test_normaliza_nombre_y_str(self):
        categoria = Categoria.objects.create(
            nombre="  Analgésicos   y antitérmicos  "
        )
        categoria.refresh_from_db()
        self.assertEqual(categoria.nombre, "Analgésicos y antitérmicos")
        self.assertEqual(str(categoria), "Analgésicos y antitérmicos")

    def test_rechaza_nombre_duplicado_sin_distinguir_mayusculas(self):
        Categoria.objects.create(nombre="Analgésicos")
        duplicada = Categoria(nombre="analgésicos")
        with self.assertRaises(ValidationError) as contexto:
            duplicada.full_clean()
        self.assertIn("nombre", contexto.exception.message_dict)
        self.assertIn(
            "Ya existe una categoría con ese nombre.",
            contexto.exception.message_dict["nombre"],
        )

    def test_no_permite_desactivar_categoria_con_productos_activos(self):
        categoria = Categoria.objects.create(nombre="Analgésicos")
        Producto.objects.create(
            codigo="P-001",
            nombre="Paracetamol 500 mg",
            categoria=categoria,
            precio_venta=Decimal("5.50"),
        )

        categoria.activo = False
        with self.assertRaises(ValidationError) as contexto:
            categoria.full_clean()
        self.assertIn("activo", contexto.exception.message_dict)

    def test_permite_desactivar_categoria_sin_productos_activos(self):
        categoria = Categoria.objects.create(nombre="Sin productos")
        categoria.activo = False
        categoria.full_clean()
        categoria.save()
        categoria.refresh_from_db()
        self.assertFalse(categoria.activo)


class CatalogoBaseTestData(TestCase):
    """Datos compartidos por las pruebas de formularios y vistas."""

    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.admin_group = Group.objects.get(name=ADMIN_GROUP)
        cls.seller_group = Group.objects.get(name=SELLER_GROUP)

        cls.admin_user = user_model.objects.create_user(
            username="admin_catalogo",
            password="ClaveSegura123!",
        )
        cls.admin_user.groups.add(cls.admin_group)

        cls.seller_user = user_model.objects.create_user(
            username="vendedor_catalogo",
            password="ClaveSegura123!",
        )
        cls.seller_user.groups.add(cls.seller_group)

        cls.categoria = Categoria.objects.create(
            nombre="Analgésicos",
            descripcion="Medicamentos para el dolor y la fiebre.",
        )
        cls.categoria_inactiva = Categoria.objects.create(
            nombre="Descontinuados",
            activo=False,
        )

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
            categoria=cls.categoria_inactiva,
            precio_venta=Decimal("7.25"),
            activo=False,
        )

    def producto_data(self, **overrides):
        data = {
            "codigo": "P-003",
            "nombre": "  Amoxicilina   500 mg  ",
            "categoria": self.categoria.pk,
            "laboratorio": "",
            "forma_farmaceutica": "",
            "presentacion": "",
            "principio_activo": "  Amoxicilina  ",
            "concentracion": "  500 mg  ",
            "unidad_medida": " caja ",
            "precio_venta": "12.50",
            "stock_minimo": "5",
            "descripcion": "Antibiótico de prueba.",
            "activo": "on",
        }
        data.update(overrides)
        return data


class ProductoFormTests(CatalogoBaseTestData):
    """Validación de los formularios del catálogo."""

    def test_formulario_normaliza_y_guarda_producto(self):
        form = ProductoForm(data=self.producto_data())
        self.assertTrue(form.is_valid(), form.errors)
        producto = form.save()
        self.assertEqual(producto.codigo, "P-003")
        self.assertEqual(producto.nombre, "Amoxicilina 500 mg")
        self.assertEqual(producto.principio_activo, "Amoxicilina")
        self.assertEqual(producto.concentracion, "500 mg")
        self.assertEqual(producto.unidad_medida, "CAJA")

    def test_formulario_rechaza_codigo_duplicado(self):
        form = ProductoForm(
            data=self.producto_data(codigo="p-001")
        )
        self.assertFalse(form.is_valid())
        self.assertIn("codigo", form.errors)
        self.assertIn(
            "Ya existe un producto con ese código.",
            form.errors["codigo"],
        )

    def test_formulario_solo_ofrece_categorias_activas(self):
        form = ProductoForm()
        categorias = form.fields["categoria"].queryset
        self.assertIn(self.categoria, categorias)
        self.assertNotIn(self.categoria_inactiva, categorias)

    def test_formulario_conserva_la_categoria_inactiva_al_editar(self):
        form = ProductoForm(instance=self.producto_inactivo)
        categorias = form.fields["categoria"].queryset
        self.assertIn(self.categoria_inactiva, categorias)

    def test_formulario_de_categoria_rechaza_nombre_duplicado(self):
        form = CategoriaForm(
            data={"nombre": "analgésicos", "descripcion": "", "activo": "on"}
        )
        self.assertFalse(form.is_valid())
        self.assertIn("nombre", form.errors)
        self.assertIn(
            "Ya existe una categoría con ese nombre.",
            form.errors["nombre"],
        )


class CatalogoViewTests(CatalogoBaseTestData):
    """Acceso por rol y operaciones de las vistas del catálogo."""

    def test_vendedor_consulta_productos_sin_acciones_de_escritura(self):
        self.client.force_login(self.seller_user)
        response = self.client.get(reverse("catalogo:index"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "catalogo/producto_list.html")
        self.assertContains(response, "Catálogo de productos")
        self.assertContains(response, "Paracetamol 500 mg")
        self.assertNotContains(response, "Nuevo producto")
        self.assertNotContains(
            response,
            reverse("catalogo:producto_crear"),
        )

    def test_vendedor_consulta_categorias_sin_acciones_de_escritura(self):
        self.client.force_login(self.seller_user)
        response = self.client.get(reverse("catalogo:categorias"))

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "catalogo/categoria_list.html")
        self.assertContains(response, "Categorías registradas")
        self.assertContains(response, "Analgésicos")
        self.assertNotContains(response, "Nueva categoría")
        self.assertNotContains(
            response,
            reverse("catalogo:categoria_crear"),
        )

    def test_vendedor_no_puede_crear_ni_editar_productos(self):
        self.client.force_login(self.seller_user)
        for url in (
            reverse("catalogo:producto_crear"),
            reverse("catalogo:producto_editar", args=[self.producto.pk]),
        ):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 403)

        response = self.client.post(
            reverse("catalogo:producto_crear"),
            self.producto_data(),
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Producto.objects.filter(codigo="P-003").exists())

    def test_vendedor_no_puede_cambiar_estado_de_productos(self):
        self.client.force_login(self.seller_user)
        response = self.client.post(
            reverse("catalogo:producto_estado", args=[self.producto.pk])
        )
        self.assertEqual(response.status_code, 403)
        self.producto.refresh_from_db()
        self.assertTrue(self.producto.activo)

    def test_vendedor_no_puede_crear_ni_editar_categorias(self):
        self.client.force_login(self.seller_user)
        for url in (
            reverse("catalogo:categoria_crear"),
            reverse("catalogo:categoria_editar", args=[self.categoria.pk]),
        ):
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertEqual(response.status_code, 403)

        response = self.client.post(
            reverse("catalogo:categoria_crear"),
            {"nombre": "Nueva", "descripcion": "", "activo": "on"},
        )
        self.assertEqual(response.status_code, 403)
        self.assertFalse(Categoria.objects.filter(nombre="Nueva").exists())

    def test_vendedor_no_puede_cambiar_estado_de_categorias(self):
        self.client.force_login(self.seller_user)
        response = self.client.post(
            reverse("catalogo:categoria_estado", args=[self.categoria.pk])
        )
        self.assertEqual(response.status_code, 403)
        self.categoria.refresh_from_db()
        self.assertTrue(self.categoria.activo)

    def test_administrador_crea_producto(self):
        self.client.force_login(self.admin_user)
        response = self.client.post(
            reverse("catalogo:producto_crear"),
            self.producto_data(),
        )

        self.assertRedirects(response, reverse("catalogo:index"))
        producto = Producto.objects.get(codigo="P-003")
        self.assertEqual(producto.nombre, "Amoxicilina 500 mg")
        self.assertEqual(producto.categoria, self.categoria)
        self.assertTrue(producto.activo)

    def test_administrador_edita_producto(self):
        self.client.force_login(self.admin_user)
        response = self.client.post(
            reverse(
                "catalogo:producto_editar",
                args=[self.producto.pk],
            ),
            self.producto_data(
                codigo="P-001",
                nombre="Paracetamol 500 mg",
                precio_venta="6.00",
                stock_minimo="15",
            ),
        )

        self.assertRedirects(response, reverse("catalogo:index"))
        self.producto.refresh_from_db()
        self.assertEqual(self.producto.precio_venta, Decimal("6.00"))
        self.assertEqual(self.producto.stock_minimo, 15)

    def test_administrador_activa_y_desactiva_producto(self):
        self.client.force_login(self.admin_user)
        url = reverse("catalogo:producto_estado", args=[self.producto.pk])

        response = self.client.post(url)
        self.assertRedirects(response, reverse("catalogo:index"))
        self.producto.refresh_from_db()
        self.assertFalse(self.producto.activo)

        response = self.client.post(url)
        self.assertRedirects(response, reverse("catalogo:index"))
        self.producto.refresh_from_db()
        self.assertTrue(self.producto.activo)

    def test_administrador_crea_y_edita_categoria(self):
        self.client.force_login(self.admin_user)
        response = self.client.post(
            reverse("catalogo:categoria_crear"),
            {
                "nombre": "  Antiinflamatorios  ",
                "descripcion": "Productos para la inflamación.",
                "activo": "on",
            },
        )
        self.assertRedirects(response, reverse("catalogo:categorias"))
        categoria = Categoria.objects.get(nombre="Antiinflamatorios")

        response = self.client.post(
            reverse(
                "catalogo:categoria_editar",
                args=[categoria.pk],
            ),
            {
                "nombre": "Antiinflamatorios y analgésicos",
                "descripcion": "Descripción actualizada.",
                "activo": "on",
            },
        )
        self.assertRedirects(response, reverse("catalogo:categorias"))
        categoria.refresh_from_db()
        self.assertEqual(
            categoria.nombre,
            "Antiinflamatorios y analgésicos",
        )
        self.assertEqual(categoria.descripcion, "Descripción actualizada.")

    def test_no_desactiva_categoria_con_productos_activos(self):
        self.client.force_login(self.admin_user)
        response = self.client.post(
            reverse("catalogo:categoria_estado", args=[self.categoria.pk]),
            follow=True,
        )

        self.assertContains(response, "No puedes desactivar la categoría")
        self.categoria.refresh_from_db()
        self.assertTrue(self.categoria.activo)

    def test_desactiva_categoria_sin_productos_activos(self):
        categoria = Categoria.objects.create(nombre="Categoría vacía")
        self.client.force_login(self.admin_user)
        response = self.client.post(
            reverse("catalogo:categoria_estado", args=[categoria.pk])
        )

        self.assertRedirects(response, reverse("catalogo:categorias"))
        categoria.refresh_from_db()
        self.assertFalse(categoria.activo)

    def test_reactiva_categoria_inactiva(self):
        self.client.force_login(self.admin_user)
        response = self.client.post(
            reverse(
                "catalogo:categoria_estado",
                args=[self.categoria_inactiva.pk],
            )
        )

        self.assertRedirects(response, reverse("catalogo:categorias"))
        self.categoria_inactiva.refresh_from_db()
        self.assertTrue(self.categoria_inactiva.activo)

    def test_listado_de_productos_filtra_por_busqueda_y_estado(self):
        self.client.force_login(self.seller_user)

        response = self.client.get(
            reverse("catalogo:index"),
            {"q": "paracetamol"},
        )
        self.assertContains(response, "Paracetamol 500 mg")
        self.assertNotContains(response, "Ibuprofeno 400 mg")

        response = self.client.get(
            reverse("catalogo:index"),
            {"estado": "inactivo"},
        )
        self.assertContains(response, "Ibuprofeno 400 mg")
        self.assertNotContains(response, "Paracetamol 500 mg")

        response = self.client.get(
            reverse("catalogo:index"),
            {"categoria": self.categoria.pk},
        )
        self.assertContains(response, "Paracetamol 500 mg")
        self.assertNotContains(response, "Ibuprofeno 400 mg")

    def test_listado_de_categorias_filtra_por_busqueda(self):
        self.client.force_login(self.seller_user)
        response = self.client.get(
            reverse("catalogo:categorias"),
            {"q": "analgésicos"},
        )
        self.assertContains(response, "Analgésicos")
        self.assertNotContains(response, "Descontinuados")

    def test_administrador_ve_formularios_de_alta(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse("catalogo:producto_crear"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "catalogo/producto_form.html")
        self.assertContains(response, "Nuevo producto")

        response = self.client.get(reverse("catalogo:categoria_crear"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "catalogo/categoria_form.html")
        self.assertContains(response, "Nueva categoría")
