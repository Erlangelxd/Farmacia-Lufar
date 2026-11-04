"""Sincroniza los permisos por modelo de los grupos base."""

from django.core.management.base import BaseCommand

from apps.accounts.permissions import sync_role_permissions


class Command(BaseCommand):
    help = (
        "Asigna los permisos por modelo a los grupos Administrador y Vendedor. "
        "Es idempotente y se ejecuta automáticamente después de migrar."
    )

    def handle(self, *args, **options):
        resumen = sync_role_permissions()
        for grupo, cantidad in resumen.items():
            self.stdout.write(
                self.style.SUCCESS(
                    f"{grupo}: {cantidad} permiso{'s' if cantidad != 1 else ''}."
                )
            )
