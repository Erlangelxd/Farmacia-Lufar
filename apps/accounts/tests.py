"""Pruebas de usuarios, roles y permisos por módulo."""

from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group, Permission
from django.test import TestCase
from django.urls import reverse

from apps.accounts.constants import ADMIN_GROUP, SELLER_GROUP
from apps.accounts.forms import UserCreateForm, UserUpdateForm
from apps.accounts.permissions import (
    MANAGED_APPS,
    SELLER_PERMISSIONS,
    is_administrator,
    is_seller,
    sync_role_permissions,
)

User = get_user_model()

PASSWORD = "ClaveSegura123!"


class RolePermissionSyncTests(TestCase):
    """Sincronización de permisos por modelo de los grupos base."""

    def test_administrador_recibe_todos_los_permisos_de_las_apps_gestionadas(self):
        sync_role_permissions()
        grupo = Group.objects.get(name=ADMIN_GROUP)

        esperados = set(
            Permission.objects.filter(
                content_type__app_label__in=MANAGED_APPS
            ).values_list("content_type__app_label", "codename")
        )
        obtenidos = set(
            grupo.permissions.values_list(
                "content_type__app_label", "codename"
            )
        )
        self.assertEqual(obtenidos, esperados)

    def test_vendedor_recibe_solo_los_permisos_de_menor_privilegio(self):
        sync_role_permissions()
        grupo = Group.objects.get(name=SELLER_GROUP)

        esperados = {
            (app_label, codename)
            for app_label, codenames in SELLER_PERMISSIONS.items()
            for codename in codenames
        }
        obtenidos = set(
            grupo.permissions.values_list(
                "content_type__app_label", "codename"
            )
        )
        self.assertEqual(obtenidos, esperados)

    def test_vendedor_no_puede_eliminar_ni_administrar_compras(self):
        sync_role_permissions()
        grupo = Group.objects.get(name=SELLER_GROUP)
        codenames = set(
            grupo.permissions.values_list("codename", flat=True)
        )

        self.assertNotIn("delete_cliente", codenames)
        self.assertNotIn("delete_venta", codenames)
        self.assertNotIn("add_compra", codenames)
        self.assertFalse(
            grupo.permissions.filter(
                content_type__app_label="compras"
            ).exists()
        )

    def test_sincronizacion_es_idempotente(self):
        primero = sync_role_permissions()
        segundo = sync_role_permissions()

        self.assertEqual(primero, segundo)
        self.assertEqual(
            Group.objects.get(name=ADMIN_GROUP).permissions.count(),
            primero[ADMIN_GROUP],
        )

    def test_helpers_de_rol_reconocen_grupos_y_superusuarios(self):
        vendedor = User.objects.create_user(
            username="vendedor_helper", password=PASSWORD
        )
        vendedor.groups.add(Group.objects.get(name=SELLER_GROUP))
        superusuario = User.objects.create_superuser(
            username="super_helper", password=PASSWORD
        )

        self.assertTrue(is_seller(vendedor))
        self.assertFalse(is_administrator(vendedor))
        self.assertTrue(is_administrator(superusuario))
        self.assertFalse(is_seller(superusuario))


class UserCreateFormTests(TestCase):
    """Alta de usuarios con rol."""

    def _datos(self, **overrides):
        datos = {
            "username": "nuevo_usuario",
            "first_name": "Nuevo",
            "last_name": "Usuario",
            "email": "nuevo@example.com",
            "role": SELLER_GROUP,
            "is_active": True,
            "password1": PASSWORD,
            "password2": PASSWORD,
        }
        datos.update(overrides)
        return datos

    def test_crea_usuario_con_rol_asignado(self):
        form = UserCreateForm(data=self._datos())
        self.assertTrue(form.is_valid(), form.errors)

        user = form.save()

        self.assertTrue(user.check_password(PASSWORD))
        self.assertEqual(
            list(user.groups.values_list("name", flat=True)),
            [SELLER_GROUP],
        )

    def test_permite_crear_usuario_inactivo(self):
        form = UserCreateForm(data=self._datos(is_active=False))
        self.assertTrue(form.is_valid(), form.errors)

        user = form.save()

        self.assertFalse(user.is_active)

    def test_rechaza_username_duplicado_sin_importar_mayusculas(self):
        User.objects.create_user(username="existente", password=PASSWORD)

        form = UserCreateForm(
            data=self._datos(username="EXISTENTE")
        )

        self.assertFalse(form.is_valid())
        self.assertIn("username", form.errors)


class UserUpdateFormTests(TestCase):
    """Edición de datos, rol y contraseña."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user(
            username="usuario_editable",
            password=PASSWORD,
            first_name="Original",
        )
        cls.user.groups.add(Group.objects.get(name=SELLER_GROUP))

    def _datos(self, **overrides):
        datos = {
            "username": self.user.username,
            "first_name": "Actualizado",
            "last_name": "Apellido",
            "email": "actualizado@example.com",
            "role": ADMIN_GROUP,
            "is_active": True,
            "nueva_password1": "",
            "nueva_password2": "",
        }
        datos.update(overrides)
        return datos

    def test_cambia_el_rol_sin_duplicar_grupos_base(self):
        form = UserUpdateForm(data=self._datos(), instance=self.user)
        self.assertTrue(form.is_valid(), form.errors)

        form.save()

        self.assertEqual(
            list(self.user.groups.values_list("name", flat=True)),
            [ADMIN_GROUP],
        )

    def test_conserva_grupos_personalizados_al_cambiar_rol(self):
        personalizado = Group.objects.create(name="Auditoría")
        self.user.groups.add(personalizado)

        form = UserUpdateForm(data=self._datos(), instance=self.user)
        self.assertTrue(form.is_valid(), form.errors)
        form.save()

        nombres = set(self.user.groups.values_list("name", flat=True))
        self.assertEqual(nombres, {ADMIN_GROUP, "Auditoría"})

    def test_restablece_password_opcional(self):
        form = UserUpdateForm(
            data=self._datos(
                nueva_password1="NuevaClave456!",
                nueva_password2="NuevaClave456!",
            ),
            instance=self.user,
        )
        self.assertTrue(form.is_valid(), form.errors)

        form.save()
        self.user.refresh_from_db()

        self.assertTrue(self.user.check_password("NuevaClave456!"))

    def test_rechaza_passwords_que_no_coinciden(self):
        form = UserUpdateForm(
            data=self._datos(
                nueva_password1="NuevaClave456!",
                nueva_password2="OtraClave789!",
            ),
            instance=self.user,
        )

        self.assertFalse(form.is_valid())
        self.assertIn("nueva_password2", form.errors)

    def test_sin_password_conserva_la_actual(self):
        form = UserUpdateForm(data=self._datos(), instance=self.user)
        self.assertTrue(form.is_valid(), form.errors)

        form.save()
        self.user.refresh_from_db()

        self.assertTrue(self.user.check_password(PASSWORD))


class UserManagementViewTests(TestCase):
    """Acceso y operaciones de la administración de usuarios."""

    @classmethod
    def setUpTestData(cls):
        cls.admin_group = Group.objects.get(name=ADMIN_GROUP)
        cls.seller_group = Group.objects.get(name=SELLER_GROUP)

        cls.admin = User.objects.create_user(
            username="admin_cuentas", password=PASSWORD
        )
        cls.admin.groups.add(cls.admin_group)

        cls.seller = User.objects.create_user(
            username="vendedor_cuentas", password=PASSWORD
        )
        cls.seller.groups.add(cls.seller_group)

        cls.otro_admin = User.objects.create_user(
            username="admin_secundario", password=PASSWORD
        )
        cls.otro_admin.groups.add(cls.admin_group)

    def test_vendedor_recibe_403_en_toda_la_gestion(self):
        self.client.force_login(self.seller)
        rutas = (
            reverse("accounts:usuarios"),
            reverse("accounts:usuario_crear"),
            reverse("accounts:usuario_editar", args=[self.seller.pk]),
            reverse("accounts:usuario_estado", args=[self.seller.pk]),
        )
        for url in rutas:
            with self.subTest(url=url):
                respuesta = self.client.get(url)
                self.assertEqual(respuesta.status_code, 403)

    def test_administrador_accede_al_listado_y_al_formulario(self):
        self.client.force_login(self.admin)

        listado = self.client.get(reverse("accounts:usuarios"))
        self.assertEqual(listado.status_code, 200)
        self.assertTemplateUsed(listado, "accounts/user_management.html")

        formulario = self.client.get(reverse("accounts:usuario_crear"))
        self.assertEqual(formulario.status_code, 200)
        self.assertTemplateUsed(formulario, "accounts/user_form.html")

    def test_filtra_por_rol_y_estado(self):
        inactivo = User.objects.create_user(
            username="vendedor_inactivo",
            password=PASSWORD,
            is_active=False,
        )
        inactivo.groups.add(self.seller_group)
        self.client.force_login(self.admin)

        por_rol = self.client.get(
            reverse("accounts:usuarios"), {"rol": SELLER_GROUP}
        )
        usuarios_por_rol = set(
            por_rol.context["users"].values_list("username", flat=True)
        )
        self.assertEqual(
            usuarios_por_rol, {"vendedor_cuentas", "vendedor_inactivo"}
        )

        por_estado = self.client.get(
            reverse("accounts:usuarios"), {"estado": "inactivos"}
        )
        usuarios_inactivos = set(
            por_estado.context["users"].values_list("username", flat=True)
        )
        self.assertEqual(usuarios_inactivos, {"vendedor_inactivo"})

    def test_crea_usuario_desde_la_interfaz(self):
        self.client.force_login(self.admin)

        respuesta = self.client.post(
            reverse("accounts:usuario_crear"),
            {
                "username": "creado_ui",
                "first_name": "Creado",
                "last_name": "Interfaz",
                "email": "creado@example.com",
                "role": SELLER_GROUP,
                "is_active": "on",
                "password1": PASSWORD,
                "password2": PASSWORD,
            },
        )

        self.assertRedirects(respuesta, reverse("accounts:usuarios"))
        creado = User.objects.get(username="creado_ui")
        self.assertEqual(
            list(creado.groups.values_list("name", flat=True)),
            [SELLER_GROUP],
        )

    def test_desactiva_y_reactiva_una_cuenta(self):
        self.client.force_login(self.admin)

        self.client.post(
            reverse("accounts:usuario_estado", args=[self.seller.pk])
        )
        self.seller.refresh_from_db()
        self.assertFalse(self.seller.is_active)

        self.client.post(
            reverse("accounts:usuario_estado", args=[self.seller.pk])
        )
        self.seller.refresh_from_db()
        self.assertTrue(self.seller.is_active)

    def test_estado_solo_acepta_post(self):
        self.client.force_login(self.admin)

        respuesta = self.client.get(
            reverse("accounts:usuario_estado", args=[self.seller.pk])
        )

        self.assertEqual(respuesta.status_code, 405)
        self.seller.refresh_from_db()
        self.assertTrue(self.seller.is_active)

    def test_no_puede_desactivar_la_propia_cuenta(self):
        self.client.force_login(self.admin)

        respuesta = self.client.post(
            reverse("accounts:usuario_estado", args=[self.admin.pk]),
            follow=True,
        )

        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)
        self.assertContains(
            respuesta, "No puedes desactivar tu propia cuenta."
        )

    def test_no_puede_quitarse_el_rol_administrador(self):
        self.client.force_login(self.admin)

        respuesta = self.client.post(
            reverse("accounts:usuario_editar", args=[self.admin.pk]),
            {
                "username": self.admin.username,
                "first_name": "",
                "last_name": "",
                "email": "",
                "role": SELLER_GROUP,
                "is_active": "on",
                "nueva_password1": "",
                "nueva_password2": "",
            },
        )

        self.assertEqual(respuesta.status_code, 200)
        self.admin.refresh_from_db()
        self.assertTrue(
            self.admin.groups.filter(name=ADMIN_GROUP).exists()
        )
        self.assertContains(
            respuesta, "No puedes quitarte el rol Administrador."
        )

    def test_no_puede_desactivar_su_cuenta_desde_el_formulario(self):
        self.client.force_login(self.admin)

        respuesta = self.client.post(
            reverse("accounts:usuario_editar", args=[self.admin.pk]),
            {
                "username": self.admin.username,
                "first_name": "",
                "last_name": "",
                "email": "",
                "role": ADMIN_GROUP,
                "nueva_password1": "",
                "nueva_password2": "",
            },
        )

        self.assertEqual(respuesta.status_code, 200)
        self.admin.refresh_from_db()
        self.assertTrue(self.admin.is_active)
        self.assertContains(
            respuesta, "No puedes desactivar tu propia cuenta."
        )

    def test_administrador_no_superusuario_no_puede_editar_superusuarios(self):
        superusuario = User.objects.create_superuser(
            username="super_cuentas", password=PASSWORD
        )
        self.client.force_login(self.admin)

        respuesta = self.client.get(
            reverse("accounts:usuario_editar", args=[superusuario.pk])
        )
        estado = self.client.post(
            reverse("accounts:usuario_estado", args=[superusuario.pk])
        )

        self.assertEqual(respuesta.status_code, 404)
        self.assertEqual(estado.status_code, 403)
        superusuario.refresh_from_db()
        self.assertTrue(superusuario.is_active)

    def test_superusuario_puede_editar_a_otro_superusuario(self):
        superusuario = User.objects.create_superuser(
            username="super_actor", password=PASSWORD
        )
        objetivo = User.objects.create_superuser(
            username="super_objetivo", password=PASSWORD
        )
        self.client.force_login(superusuario)

        respuesta = self.client.get(
            reverse("accounts:usuario_editar", args=[objetivo.pk])
        )

        self.assertEqual(respuesta.status_code, 200)
