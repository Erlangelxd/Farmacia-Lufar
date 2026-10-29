"""Pruebas transversales de la estructura inicial del sistema."""

from django.apps import apps
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.test import Client, TestCase
from django.urls import reverse

from apps.accounts.constants import ADMIN_GROUP, DEFAULT_GROUPS, SELLER_GROUP


class InitialStructureTests(TestCase):
    """Verifica apps, rutas, autenticación y permisos base."""

    @classmethod
    def setUpTestData(cls):
        user_model = get_user_model()
        cls.admin_group = Group.objects.get(name=ADMIN_GROUP)
        cls.seller_group = Group.objects.get(name=SELLER_GROUP)

        cls.admin_user = user_model.objects.create_user(
            username="admin_prueba",
            password="ClaveSegura123!",
            first_name="Admin",
            last_name="Prueba",
        )
        cls.admin_user.groups.add(cls.admin_group)

        cls.seller_user = user_model.objects.create_user(
            username="vendedor_prueba",
            password="ClaveSegura123!",
            first_name="Vendedor",
            last_name="Prueba",
        )
        cls.seller_user.groups.add(cls.seller_group)

    def test_all_apps_are_loaded(self):
        expected_apps = (
            "core",
            "accounts",
            "catalogo",
            "inventario",
            "compras",
            "clientes",
            "ventas",
            "reportes",
        )
        for label in expected_apps:
            with self.subTest(app=label):
                self.assertEqual(
                    apps.get_app_config(label).name,
                    f"apps.{label}",
                )

    def test_initial_routes_resolve(self):
        route_names = (
            "core:dashboard",
            "accounts:index",
            "accounts:login",
            "accounts:logout",
            "accounts:usuarios",
            "catalogo:index",
            "inventario:index",
            "compras:index",
            "clientes:index",
            "ventas:index",
            "reportes:index",
        )
        for name in route_names:
            with self.subTest(route=name):
                self.assertTrue(reverse(name).startswith("/"))

    def test_default_groups_exist(self):
        existing_groups = set(
            Group.objects.filter(name__in=DEFAULT_GROUPS).values_list(
                "name", flat=True
            )
        )
        self.assertEqual(existing_groups, set(DEFAULT_GROUPS))

    def test_management_views_require_authentication(self):
        login_url = reverse("accounts:login")
        protected_routes = (
            "core:dashboard",
            "accounts:index",
            "accounts:usuarios",
            "catalogo:index",
            "inventario:index",
            "compras:index",
            "clientes:index",
            "ventas:index",
            "reportes:index",
        )
        for name in protected_routes:
            with self.subTest(route=name):
                url = reverse(name)
                response = self.client.get(url)
                self.assertRedirects(response, f"{login_url}?next={url}")

    def test_login_page_renders_with_csrf_protection(self):
        response = self.client.get(reverse("accounts:login"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "registration/login.html")
        self.assertContains(response, "csrfmiddlewaretoken")
        self.assertContains(response, "Inicia sesión")

        csrf_client = Client(enforce_csrf_checks=True)
        csrf_response = csrf_client.post(
            reverse("accounts:login"),
            {
                "username": self.seller_user.username,
                "password": "ClaveSegura123!",
            },
        )
        self.assertEqual(csrf_response.status_code, 403)

    def test_seller_can_access_dashboard_and_modules(self):
        self.client.force_login(self.seller_user)
        response = self.client.get(reverse("core:dashboard"))
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "core/dashboard.html")
        self.assertContains(response, "Datos provisionales")
        self.assertContains(response, "Provisional")

        module_routes = (
            ("catalogo:index", "Catálogo"),
            ("inventario:index", "Inventario"),
            ("compras:index", "Compras"),
            ("clientes:index", "Clientes"),
            ("ventas:index", "Ventas"),
            ("reportes:index", "Reportes"),
        )
        for name, title in module_routes:
            with self.subTest(route=name):
                module_response = self.client.get(reverse(name))
                self.assertEqual(module_response.status_code, 200)
                self.assertTemplateUsed(module_response, "core/placeholder.html")
                self.assertContains(module_response, title)

    def test_seller_sees_profile_but_not_user_management(self):
        self.client.force_login(self.seller_user)
        response = self.client.get(reverse("accounts:index"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Mi cuenta")
        self.assertContains(response, SELLER_GROUP)
        self.assertNotContains(response, reverse("accounts:usuarios"))

        forbidden_response = self.client.get(reverse("accounts:usuarios"))
        self.assertEqual(forbidden_response.status_code, 403)

    def test_administrator_can_access_user_management(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse("accounts:usuarios"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Usuarios y permisos")
        self.assertContains(response, ADMIN_GROUP)
        self.assertContains(response, SELLER_GROUP)
        self.assertContains(response, self.seller_user.username)

    def test_login_redirects_to_dashboard(self):
        response = self.client.post(
            reverse("accounts:login"),
            {
                "username": self.seller_user.username,
                "password": "ClaveSegura123!",
            },
        )
        self.assertRedirects(response, reverse("core:dashboard"))
        self.assertIn("_auth_user_id", self.client.session)

    def test_login_shows_welcome_message(self):
        response = self.client.post(
            reverse("accounts:login"),
            {
                "username": self.seller_user.username,
                "password": "ClaveSegura123!",
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Bienvenido, Vendedor Prueba.")

    def test_invalid_login_shows_form_errors(self):
        response = self.client.post(
            reverse("accounts:login"),
            {
                "username": self.seller_user.username,
                "password": "clave-incorrecta",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.context["form"].non_field_errors())

    def test_authenticated_user_is_redirected_from_login(self):
        self.client.force_login(self.seller_user)
        response = self.client.get(reverse("accounts:login"))
        self.assertRedirects(response, reverse("core:dashboard"))

    def test_logout_requires_post_and_clears_session(self):
        self.client.force_login(self.seller_user)
        get_response = self.client.get(reverse("accounts:logout"))
        self.assertEqual(get_response.status_code, 405)

        post_response = self.client.post(reverse("accounts:logout"), follow=True)
        self.assertEqual(post_response.status_code, 200)
        self.assertTemplateUsed(post_response, "registration/login.html")
        self.assertContains(post_response, "Has cerrado sesión correctamente.")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_administrator_navigation_shows_user_link(self):
        self.client.force_login(self.admin_user)
        response = self.client.get(reverse("core:dashboard"))
        self.assertContains(response, reverse("accounts:usuarios"))

        self.client.force_login(self.seller_user)
        seller_response = self.client.get(reverse("core:dashboard"))
        self.assertNotContains(seller_response, reverse("accounts:usuarios"))

    def test_unknown_url_uses_custom_404_template(self):
        response = self.client.get("/ruta-que-no-existe/")
        self.assertEqual(response.status_code, 404)
        self.assertTemplateUsed(response, "404.html")
        self.assertContains(response, "Página no encontrada", status_code=404)
