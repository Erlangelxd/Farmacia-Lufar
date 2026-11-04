from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "apps.accounts"
    verbose_name = "Cuentas y permisos"

    def ready(self):
        """Sincroniza los permisos por rol después de cada migración."""
        from django.db.models.signals import post_migrate

        from .permissions import sync_role_permissions

        post_migrate.connect(
            sync_role_permissions,
            sender=self,
            dispatch_uid="accounts.sync_role_permissions",
        )
