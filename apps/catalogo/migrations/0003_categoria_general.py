"""Crea la categoría ``General`` para los productos que no tienen una."""

from django.db import migrations


def crear_categoria_general(apps, schema_editor):
    Categoria = apps.get_model("catalogo", "Categoria")
    Producto = apps.get_model("catalogo", "Producto")

    categoria, _ = Categoria.objects.get_or_create(
        nombre="General",
        defaults={"descripcion": "Categoría asignada por defecto."},
    )
    Producto.objects.filter(categoria__isnull=True).update(categoria=categoria)


def eliminar_categoria_general(apps, schema_editor):
    Categoria = apps.get_model("catalogo", "Categoria")
    Categoria.objects.filter(nombre="General", productos__isnull=True).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("catalogo", "0002_categoria_formafarmaceutica_laboratorio_presentacion_and_more"),
    ]

    operations = [
        migrations.RunPython(
            crear_categoria_general,
            eliminar_categoria_general,
        ),
    ]
