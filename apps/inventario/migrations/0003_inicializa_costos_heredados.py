from django.db import migrations


def crear_capas_sin_costo(apps, schema_editor):
    """Preserva existencias previas sin inventar su costo de adquisición."""
    Lote = apps.get_model("inventario", "Lote")
    CapaCosto = apps.get_model("inventario", "CapaCosto")
    alias = schema_editor.connection.alias

    lotes = Lote.objects.using(alias).filter(stock_actual__gt=0).iterator()
    CapaCosto.objects.using(alias).bulk_create(
        [
            CapaCosto(
                lote_id=lote.pk,
                cantidad_inicial=lote.stock_actual,
                cantidad_restante=lote.stock_actual,
                costo_unitario=None,
                movimiento_entrada=None,
            )
            for lote in lotes
        ]
    )


class Migration(migrations.Migration):
    dependencies = [
        ("inventario", "0002_movimientoinventario_costo_total_capacosto_and_more"),
    ]

    operations = [
        migrations.RunPython(crear_capas_sin_costo, migrations.RunPython.noop),
    ]
