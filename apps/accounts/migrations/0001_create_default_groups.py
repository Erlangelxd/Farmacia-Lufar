"""Crea los grupos base del sistema.

Los permisos por modelo se asignarán cuando existan los modelos de cada app.
Esta migración solo prepara los roles Administrador y Vendedor.
"""

from django.db import migrations

GROUPS = ("Administrador", "Vendedor")


def create_default_groups(apps, schema_editor):
    """Crea los grupos base de forma idempotente."""
    Group = apps.get_model("auth", "Group")
    for name in GROUPS:
        Group.objects.get_or_create(name=name)


def delete_default_groups(apps, schema_editor):
    """Elimina los grupos base al revertir la migración."""
    Group = apps.get_model("auth", "Group")
    Group.objects.filter(name__in=GROUPS).delete()


class Migration(migrations.Migration):
    initial = True

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        migrations.RunPython(create_default_groups, delete_default_groups),
    ]
