"""Pruebas del módulo de clientes."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.core.exceptions import ValidationError
from django.test import Client, TestCase
from django.urls import reverse

from apps.accounts.constants import SELLER_GROUP

from .forms import ClienteForm
from .models import Cliente


class ClienteModelTests(TestCase):
    """Reglas básicas del modelo Cliente."""

    def test_str_sin_documento(self):
        cliente = Cliente(nombre="Ana Pérez")
        self.assertEqual(str(cliente), "Ana Pérez")

    def test_str_con_documento(self):
        cliente = Cliente(
            nombre="Ana Pérez",
            tipo_documento=Cliente.TipoDocumento.CI,
            numero_documento="12345678",
        )
        self.assertEqual(
            str(cliente),
            "Ana Pérez (Cédula de Identidad 12345678)",
        )

    def test_valores_por_defecto(self):
        cliente = Cliente.objects.create(nombre="Ana Pérez")
        self.assertTrue(cliente.activo)
        self.assertIsNotNone(cliente.creado_en)
        self.assertIsNotNone(cliente.actualizado_en)

    def test_orden_por_nombre(self):
        Cliente.objects.create(nombre="Zoe")
        Cliente.objects.create(nombre="Ana")
        self.assertEqual(
            list(Cliente.objects.values_list("nombre", flat=True)),
            ["Ana", "Zoe"],
        )

    def test_full_clean_rechaza_numero_sin_tipo(self):
        cliente = Cliente(nombre="Ana Pérez", numero_documento="12345678")
        with self.assertRaises(ValidationError) as contexto:
            cliente.full_clean()
        self.assertIn(
            "El tipo y el número de documento deben registrarse juntos.",
            str(contexto.exception),
        )

    def test_full_clean_rechaza_tipo_sin_numero(self):
        cliente = Cliente(
            nombre="Ana Pérez",
            tipo_documento=Cliente.TipoDocumento.CI,
        )
        with self.assertRaises(ValidationError) as contexto:
            cliente.full_clean()
        self.assertIn(
            "El tipo y el número de documento deben registrarse juntos.",
            str(contexto.exception),
        )

    def test_full_clean_rechaza_documento_duplicado(self):
        Cliente.objects.create(
            nombre="Ana Pérez",
            tipo_documento=Cliente.TipoDocumento.CI,
            numero_documento="12345678",
        )
        duplicado = Cliente(
            nombre="Luis Gómez",
            tipo_documento=Cliente.TipoDocumento.CI,
            numero_documento="12345678",
        )
        with self.assertRaises(ValidationError) as contexto:
            duplicado.full_clean()
        self.assertIn(
            "Ya existe un cliente con ese tipo y número de documento.",
            str(contexto.exception),
        )

    def test_permite_varios_clientes_sin_documento(self):
        Cliente.objects.create(nombre="Ana Pérez")
        Cliente.objects.create(nombre="Luis Gómez")
        self.assertEqual(Cliente.objects.count(), 2)

    def test_normaliza_espacios_al_guardar(self):
        cliente = Cliente.objects.create(
            nombre="  Ana   Pérez  ",
            tipo_documento="  CI  ",
            numero_documento="  12345678  ",
            telefono="  71234567  ",
        )
        cliente.refresh_from_db()
        self.assertEqual(cliente.nombre, "Ana Pérez")
        self.assertEqual(cliente.tipo_documento, "CI")
        self.assertEqual(cliente.numero_documento, "12345678")
        self.assertEqual(cliente.telefono, "71234567")


class ClienteFormTests(TestCase):
    """Validaciones del formulario de registro."""

    @classmethod
    def setUpTestData(cls):
        cls.cliente_existente = Cliente.objects.create(
            nombre="Cliente existente",
            tipo_documento=Cliente.TipoDocumento.CI,
            numero_documento="12345678",
        )
        Cliente.objects.create(
            nombre="Cliente pasaporte",
            tipo_documento=Cliente.TipoDocumento.PASAPORTE,
            numero_documento="AB123",
        )

    def test_formulario_valido_sin_documento(self):
        form = ClienteForm(
            data={
                "nombre": "  Ana   Pérez  ",
                "tipo_documento": "",
                "numero_documento": "",
                "telefono": " 71234567 ",
                "activo": "on",
            }
        )
        self.assertTrue(form.is_valid(), form.errors)
        cliente = form.save()
        self.assertEqual(cliente.nombre, "Ana Pérez")
        self.assertEqual(cliente.telefono, "71234567")
        self.assertTrue(cliente.activo)

    def test_formulario_valido_con_documento(self):
        form = ClienteForm(
            data={
                "nombre": "Luis Gómez",
                "tipo_documento": Cliente.TipoDocumento.CI,
                "numero_documento": "87654321",
                "telefono": "",
                "activo": "on",
            }
        )
        self.assertTrue(form.is_valid(), form.errors)

    def test_nombre_obligatorio(self):
        form = ClienteForm(
            data={
                "nombre": "   ",
                "tipo_documento": "",
                "numero_documento": "",
                "telefono": "",
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("nombre", form.errors)

    def test_numero_sin_tipo(self):
        form = ClienteForm(
            data={
                "nombre": "Ana Pérez",
                "tipo_documento": "",
                "numero_documento": "12345678",
                "telefono": "",
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("tipo_documento", form.errors)

    def test_tipo_sin_numero(self):
        form = ClienteForm(
            data={
                "nombre": "Ana Pérez",
                "tipo_documento": Cliente.TipoDocumento.CI,
                "numero_documento": "",
                "telefono": "",
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("numero_documento", form.errors)

    def test_documento_duplicado(self):
        form = ClienteForm(
            data={
                "nombre": "Otro cliente",
                "tipo_documento": Cliente.TipoDocumento.CI,
                "numero_documento": "12345678",
                "telefono": "",
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("numero_documento", form.errors)
        self.assertIn(
            "Ya existe un cliente con ese tipo y número de documento.",
            form.errors["numero_documento"],
        )

    def test_documento_duplicado_ignora_mayusculas(self):
        form = ClienteForm(
            data={
                "nombre": "Otro cliente",
                "tipo_documento": Cliente.TipoDocumento.PASAPORTE,
                "numero_documento": "ab123",
                "telefono": "",
            }
        )
        self.assertFalse(form.is_valid())
        self.assertIn("numero_documento", form.errors)

    def test_no_incluye_correo_ni_direccion(self):
        form = ClienteForm()
        self.assertNotIn("email", form.fields)
        self.assertNotIn("direccion", form.fields)

    def test_primera_opcion_de_documento_es_sin_documento(self):
        form = ClienteForm()
        self.assertEqual(
            form.fields["tipo_documento"].choices[0],
            ("", "Sin documento"),
        )

    def test_activo_se_muestra_marcado_por_defecto(self):
        form = ClienteForm()
        self.assertTrue(form.fields["activo"].initial)


class ClienteViewTests(TestCase):
    """Vistas de listado, registro y consulta."""

    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.seller_group = Group.objects.get(name=SELLER_GROUP)
        cls.seller_user = user_model.objects.create_user(
            username="vendedor_clientes",
            password="ClaveSegura123!",
            first_name="Vendedor",
            last_name="Clientes",
        )
        cls.seller_user.groups.add(cls.seller_group)

        cls.cliente_activo = Cliente.objects.create(
            nombre="Ana Pérez",
            tipo_documento=Cliente.TipoDocumento.CI,
            numero_documento="12345678",
            telefono="71234567",
            creado_por=cls.seller_user,
        )
        cls.cliente_inactivo = Cliente.objects.create(
            nombre="Luis Gómez",
            telefono="76543210",
            activo=False,
            creado_por=cls.seller_user,
        )

    def setUp(self):
        self.client.force_login(self.seller_user)

    def test_vistas_requieren_autenticacion(self):
        self.client.logout()
        login_url = reverse("accounts:login")
        urls = (
            reverse("clientes:index"),
            reverse("clientes:crear"),
            reverse("clientes:detalle", args=[self.cliente_activo.pk]),
        )
        for url in urls:
            with self.subTest(url=url):
                response = self.client.get(url)
                self.assertRedirects(response, f"{login_url}?next={url}")

    def test_formulario_de_registro_renderiza_campos(self):
        response = self.client.get(reverse("clientes:crear"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "clientes/cliente_form.html")
        self.assertContains(response, "Registrar cliente")
        self.assertContains(response, "csrfmiddlewaretoken")
        self.assertContains(response, "Sin documento")
        self.assertNotContains(response, 'name="email"')
        self.assertNotContains(response, 'name="direccion"')

    def test_listado_muestra_clientes(self):
        response = self.client.get(reverse("clientes:index"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "clientes/cliente_list.html")
        self.assertContains(response, "Ana Pérez")
        self.assertContains(response, "Luis Gómez")
        self.assertContains(response, "Clientes registrados")
        self.assertContains(response, "Registrar cliente")

    def test_detalle_muestra_ficha_del_cliente(self):
        response = self.client.get(
            reverse("clientes:detalle", args=[self.cliente_activo.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "clientes/cliente_detail.html")
        self.assertContains(response, "Ana Pérez")
        self.assertContains(response, "Cédula de Identidad 12345678")
        self.assertContains(response, "71234567")
        self.assertContains(response, "Historial comercial")
        self.assertContains(response, "Próxima etapa")

    def test_detalle_cliente_sin_usuario_registrador(self):
        cliente = Cliente.objects.create(nombre="Cliente del sistema")
        response = self.client.get(
            reverse("clientes:detalle", args=[cliente.pk])
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Cliente del sistema")
        self.assertContains(response, "Sistema")

    def test_busqueda_por_nombre_documento_y_telefono(self):
        casos = (
            ("Ana", "Ana Pérez", "Luis Gómez"),
            ("12345678", "Ana Pérez", "Luis Gómez"),
            ("76543210", "Luis Gómez", "Ana Pérez"),
        )
        for busqueda, esperado, no_esperado in casos:
            with self.subTest(busqueda=busqueda):
                response = self.client.get(
                    reverse("clientes:index"),
                    {"q": busqueda},
                )
                self.assertContains(response, esperado)
                self.assertNotContains(response, no_esperado)

    def test_filtro_por_estado(self):
        response = self.client.get(
            reverse("clientes:index"),
            {"estado": "activo"},
        )
        self.assertContains(response, "Ana Pérez")
        self.assertNotContains(response, "Luis Gómez")

        response = self.client.get(
            reverse("clientes:index"),
            {"estado": "inactivo"},
        )
        self.assertContains(response, "Luis Gómez")
        self.assertNotContains(response, "Ana Pérez")

        response = self.client.get(reverse("clientes:index"))
        self.assertContains(response, "Ana Pérez")
        self.assertContains(response, "Luis Gómez")

    def test_listado_sin_resultados(self):
        response = self.client.get(
            reverse("clientes:index"),
            {"q": "No existe"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No encontramos clientes")
        self.assertContains(response, "Limpiar filtros")

    def test_listado_vacio(self):
        Cliente.objects.all().delete()
        response = self.client.get(reverse("clientes:index"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Aún no hay clientes registrados")
        self.assertContains(response, "Registrar primer cliente")

    def test_paginacion_del_listado(self):
        for indice in range(25):
            Cliente.objects.create(
                nombre=f"Cliente de prueba {indice:02d}",
                telefono=f"700000{indice:02d}",
            )

        response = self.client.get(reverse("clientes:index"))
        self.assertTrue(response.context["is_paginated"])
        self.assertEqual(len(response.context["clientes"]), 20)
        self.assertEqual(response.context["paginator"].count, 27)

        response = self.client.get(reverse("clientes:index"), {"page": 2})
        self.assertEqual(len(response.context["clientes"]), 7)

    def test_registro_valido_redirige_al_detalle(self):
        response = self.client.post(
            reverse("clientes:crear"),
            {
                "nombre": "  Carla   Rojas  ",
                "tipo_documento": Cliente.TipoDocumento.CI,
                "numero_documento": "87654321",
                "telefono": "70000000",
                "activo": "on",
            },
            follow=True,
        )

        cliente = Cliente.objects.get(numero_documento="87654321")
        self.assertRedirects(
            response,
            reverse("clientes:detalle", args=[cliente.pk]),
        )
        self.assertEqual(cliente.nombre, "Carla Rojas")
        self.assertEqual(cliente.creado_por, self.seller_user)
        self.assertTrue(cliente.activo)
        self.assertContains(response, "se registró correctamente")
        self.assertContains(response, "Carla Rojas")

    def test_registro_invalido_por_documento_duplicado(self):
        cantidad_inicial = Cliente.objects.count()
        response = self.client.post(
            reverse("clientes:crear"),
            {
                "nombre": "Otro cliente",
                "tipo_documento": Cliente.TipoDocumento.CI,
                "numero_documento": "12345678",
                "telefono": "",
                "activo": "on",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("numero_documento", response.context["form"].errors)
        self.assertEqual(Cliente.objects.count(), cantidad_inicial)

    def test_registro_invalido_por_tipo_sin_numero(self):
        response = self.client.post(
            reverse("clientes:crear"),
            {
                "nombre": "Cliente incompleto",
                "tipo_documento": Cliente.TipoDocumento.CI,
                "numero_documento": "",
                "telefono": "",
                "activo": "on",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn("numero_documento", response.context["form"].errors)
        self.assertFalse(
            Cliente.objects.filter(nombre="Cliente incompleto").exists()
        )

    def test_registro_requiere_csrf(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.seller_user)
        response = csrf_client.post(
            reverse("clientes:crear"),
            {
                "nombre": "Cliente sin CSRF",
                "tipo_documento": "",
                "numero_documento": "",
                "telefono": "",
                "activo": "on",
            },
        )
        self.assertEqual(response.status_code, 403)

    def test_detalle_inexistente_devuelve_404(self):
        response = self.client.get(
            reverse("clientes:detalle", args=[999999])
        )
        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, "404.html")
