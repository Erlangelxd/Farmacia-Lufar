"""Vistas del módulo de reportes.

Esta app no tiene modelos propios: consulta datos de catálogo, ventas,
compras e inventario. Todas las vistas son de solo lectura.
"""

from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.db.models import (
    Avg,
    Count,
    DecimalField,
    ExpressionWrapper,
    F,
    Max,
    Min,
    Q,
    Sum,
)
from django.db.models.functions import TruncDate
from django.utils import timezone
from django.views.generic import TemplateView

from apps.accounts.constants import ADMIN_GROUP, SELLER_GROUP
from apps.accounts.permissions import is_administrator
from apps.catalogo.models import Producto
from apps.compras.models import Compra, DetalleCompra, Proveedor
from apps.core.mixins import RoleRequiredMixin
from apps.inventario.models import CapaCosto, Lote, MovimientoInventario
from apps.inventario.selectors import productos_con_stock_bajo, stock_por_producto
from apps.ventas.models import DetalleVenta, Venta

User = get_user_model()


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _rango_desde_periodo(periodo: str) -> tuple[date, date]:
    """Devuelve (fecha_inicio, fecha_fin) para el periodo solicitado."""
    hoy = timezone.localdate()
    if periodo == "hoy":
        return hoy, hoy
    if periodo == "semana":
        inicio = hoy - timedelta(days=hoy.weekday())  # lunes
        return inicio, hoy
    if periodo == "mes":
        return hoy.replace(day=1), hoy
    if periodo == "trimestre":
        return hoy - timedelta(days=90), hoy
    # "año" o cualquier otro valor
    return hoy.replace(month=1, day=1), hoy


def _resumen_ganancia(ventas_qs):
    """Resume margen bruto solo para ventas con costo completo conocido."""
    ventas_con_costo = ventas_qs.annotate(
        lineas_sin_costo=Count(
            "detalles",
            filter=Q(detalles__costo_total__isnull=True),
        )
    ).filter(lineas_sin_costo=0)
    ids_con_costo = ventas_con_costo.values("pk")
    ingresos_con_costo = (
        ventas_con_costo.aggregate(total=Sum("total"))["total"]
        or Decimal("0.00")
    )
    costo_ventas = (
        DetalleVenta.objects.filter(venta__in=ventas_con_costo).aggregate(
            total=Sum("costo_total")
        )["total"]
        or Decimal("0.00")
    )
    return {
        "ingresos_con_costo": ingresos_con_costo,
        "costo_ventas": costo_ventas,
        "ganancia_bruta": ingresos_con_costo - costo_ventas,
        "ventas_con_costo": ventas_con_costo.count(),
        "ventas_sin_costo": ventas_qs.exclude(pk__in=ids_con_costo).count(),
    }


# ──────────────────────────────────────────────────────────────────────────────
# Índice de reportes
# ──────────────────────────────────────────────────────────────────────────────

class ReportesIndexView(RoleRequiredMixin, TemplateView):
    """Página principal del módulo con accesos directos a cada reporte."""

    allowed_groups = (ADMIN_GROUP, SELLER_GROUP)
    template_name = "reportes/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        hoy = timezone.localdate()
        inicio_mes = hoy.replace(day=1)
        limite_vencimiento = hoy + timedelta(days=30)
        puede_ver_inventario = is_administrator(self.request.user)

        # ── Resumen de ventas ────────────────────────────────────────────────
        ventas_hoy = Venta.objects.filter(creado_en__date=hoy)
        ingresos_hoy = (
            ventas_hoy.aggregate(t=Sum("total"))["t"] or Decimal("0.00")
        )
        ventas_mes = Venta.objects.filter(creado_en__date__gte=inicio_mes)
        ingresos_mes = (
            ventas_mes.aggregate(t=Sum("total"))["t"] or Decimal("0.00")
        )

        # ── Resumen de compras e inventario (solo administradores) ───────────
        compras_cantidad = 0
        gasto_mes = Decimal("0.00")
        stock_bajo = 0
        lotes_por_vencer = 0
        lotes_vencidos = 0
        ganancia_hoy = Decimal("0.00")
        ganancia_mes = Decimal("0.00")
        ventas_sin_costo_mes = 0
        if puede_ver_inventario:
            ganancia_hoy = _resumen_ganancia(ventas_hoy)["ganancia_bruta"]
            resumen_mes = _resumen_ganancia(ventas_mes)
            ganancia_mes = resumen_mes["ganancia_bruta"]
            ventas_sin_costo_mes = resumen_mes["ventas_sin_costo"]
            compras_mes = Compra.objects.filter(
                fecha_compra__gte=inicio_mes
            ).exclude(estado=Compra.Estado.ANULADA)
            datos_compras_mes = compras_mes.aggregate(
                cantidad=Count("pk"),
                monto=Sum("total"),
            )
            compras_cantidad = datos_compras_mes["cantidad"] or 0
            gasto_mes = datos_compras_mes["monto"] or Decimal("0.00")

            stock_bajo = productos_con_stock_bajo().count()
            lotes_activos = Lote.objects.filter(activo=True)
            lotes_por_vencer = lotes_activos.filter(
                fecha_vencimiento__gte=hoy,
                fecha_vencimiento__lte=limite_vencimiento,
                stock_actual__gt=0,
            ).count()
            lotes_vencidos = lotes_activos.filter(
                fecha_vencimiento__lt=hoy,
                stock_actual__gt=0,
            ).count()

        context.update(
            {
                "hoy": hoy,
                "ventas_hoy": ventas_hoy.count(),
                "ingresos_hoy": ingresos_hoy,
                "total_ventas_mes": ventas_mes.count(),
                "ingresos_mes": ingresos_mes,
                "puede_ver_inventario": puede_ver_inventario,
                "compras_mes": compras_cantidad,
                "gasto_mes": gasto_mes,
                "stock_bajo": stock_bajo,
                "lotes_por_vencer": lotes_por_vencer,
                "lotes_vencidos": lotes_vencidos,
                "ganancia_hoy": ganancia_hoy,
                "ganancia_mes": ganancia_mes,
                "ventas_sin_costo_mes": ventas_sin_costo_mes,
            }
        )
        return context


# ──────────────────────────────────────────────────────────────────────────────
# Reporte de ventas
# ──────────────────────────────────────────────────────────────────────────────

class ReporteVentasView(RoleRequiredMixin, TemplateView):
    """Reporte de ventas filtrable por periodo y vendedor."""

    allowed_groups = (ADMIN_GROUP, SELLER_GROUP)
    template_name = "reportes/reporte_ventas.html"

    PERIODOS = [
        ("hoy", "Hoy"),
        ("semana", "Esta semana"),
        ("mes", "Este mes"),
        ("trimestre", "Últimos 90 días"),
        ("año", "Este año"),
    ]

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        request = self.request

        periodo = request.GET.get("periodo", "mes")
        vendedor_id = request.GET.get("vendedor", "").strip()

        fecha_inicio, fecha_fin = _rango_desde_periodo(periodo)

        qs = Venta.objects.filter(
            creado_en__date__gte=fecha_inicio,
            creado_en__date__lte=fecha_fin,
        ).select_related("cliente", "vendedor").prefetch_related("detalles")

        if vendedor_id.isdigit():
            qs = qs.filter(vendedor_id=int(vendedor_id))

        # ── Totales generales ─────────────────────────────────────────────────
        agg = qs.aggregate(
            total_ventas=Count("pk"),
            ingresos_total=Sum("total"),
        )
        total_ventas = agg["total_ventas"] or 0
        ingresos_total = agg["ingresos_total"] or Decimal("0.00")
        ticket_promedio = (
            ingresos_total / total_ventas if total_ventas else Decimal("0.00")
        )
        unidades_total = (
            DetalleVenta.objects.filter(venta__in=qs).aggregate(
                t=Sum("cantidad")
            )["t"]
            or 0
        )
        puede_ver_costos = is_administrator(request.user)
        resumen_ganancia = (
            _resumen_ganancia(qs)
            if puede_ver_costos
            else {
                "ingresos_con_costo": Decimal("0.00"),
                "costo_ventas": Decimal("0.00"),
                "ganancia_bruta": Decimal("0.00"),
                "ventas_con_costo": 0,
                "ventas_sin_costo": 0,
            }
        )

        # ── Ventas por día (para mini-gráfico de barras) ──────────────────────
        ventas_por_dia = list(
            qs.annotate(dia=TruncDate("creado_en"))
            .values("dia")
            .annotate(
                cantidad=Count("pk"),
                ingresos=Sum("total"),
            )
            .order_by("dia")
        )

        # ── Ventas por vendedor ───────────────────────────────────────────────
        ventas_por_vendedor = (
            qs.values(
                "vendedor__id",
                "vendedor__first_name",
                "vendedor__last_name",
                "vendedor__username",
            )
            .annotate(
                cantidad=Count("pk"),
                ingresos=Sum("total"),
            )
            .order_by("-ingresos")
        )

        # ── Productos más vendidos ────────────────────────────────────────────
        productos_top_qs = (
            DetalleVenta.objects.filter(venta__in=qs)
            .values("nombre_producto", "codigo_producto")
            .annotate(
                unidades=Sum("cantidad"),
                ingresos=Sum(
                    ExpressionWrapper(
                        F("precio_unitario") * F("cantidad"),
                        output_field=DecimalField(max_digits=14, decimal_places=2),
                    )
                ),
            )
            .order_by("-unidades")
        )
        if puede_ver_costos:
            productos_top_qs = productos_top_qs.annotate(
                ganancia_bruta=Sum(
                    ExpressionWrapper(
                        F("precio_unitario") * F("cantidad")
                        - F("costo_total"),
                        output_field=DecimalField(
                            max_digits=16, decimal_places=2
                        ),
                    ),
                    filter=Q(costo_total__isnull=False),
                ),
                unidades_sin_costo=Sum(
                    "cantidad",
                    filter=Q(costo_total__isnull=True),
                ),
            )
        productos_top = productos_top_qs[:10]

        # ── Lista de vendedores (para filtro) ─────────────────────────────────
        vendedores = User.objects.filter(
            ventas_realizadas__isnull=False
        ).distinct().order_by("first_name", "username")

        # ── Serializar días para las etiquetas del gráfico ────────────────────
        dias_labels = [str(d["dia"]) for d in ventas_por_dia]
        dias_ingresos = [float(d["ingresos"] or 0) for d in ventas_por_dia]
        dias_cantidad = [d["cantidad"] for d in ventas_por_dia]

        context.update(
            {
                "periodos": self.PERIODOS,
                "periodo_actual": periodo,
                "vendedor_id": vendedor_id,
                "vendedores": vendedores,
                "fecha_inicio": fecha_inicio,
                "fecha_fin": fecha_fin,
                "total_ventas": total_ventas,
                "ingresos_total": ingresos_total,
                "ticket_promedio": ticket_promedio,
                "unidades_total": unidades_total,
                "puede_ver_costos": puede_ver_costos,
                **resumen_ganancia,
                "ventas_por_dia": ventas_por_dia,
                "ventas_por_vendedor": ventas_por_vendedor,
                "productos_top": productos_top,
                "dias_labels": dias_labels,
                "dias_ingresos": dias_ingresos,
                "dias_cantidad": dias_cantidad,
                "ventas_lista": qs.order_by("-creado_en")[:50],
            }
        )
        return context


# ──────────────────────────────────────────────────────────────────────────────
# Reporte de compras
# ──────────────────────────────────────────────────────────────────────────────

class ReporteComprasView(RoleRequiredMixin, TemplateView):
    """Reporte de compras filtrable por periodo, proveedor y estado."""

    allowed_groups = (ADMIN_GROUP,)
    template_name = "reportes/reporte_compras.html"

    PERIODOS = ReporteVentasView.PERIODOS

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        request = self.request

        periodo = request.GET.get("periodo", "mes")
        proveedor_id = request.GET.get("proveedor", "").strip()
        estado = request.GET.get("estado", "todos")

        fecha_inicio, fecha_fin = _rango_desde_periodo(periodo)

        qs = Compra.objects.filter(
            fecha_compra__gte=fecha_inicio,
            fecha_compra__lte=fecha_fin,
        ).select_related("proveedor", "usuario").prefetch_related("detalles")

        if proveedor_id.isdigit():
            qs = qs.filter(proveedor_id=int(proveedor_id))
        if estado in Compra.Estado.values:
            qs = qs.filter(estado=estado)

        # ── Totales del periodo ───────────────────────────────────────────────
        totales = qs.aggregate(
            total_compras=Count("pk"),
            monto_total=Sum("total"),
        )
        total_compras = totales["total_compras"] or 0
        monto_total = totales["monto_total"] or Decimal("0.00")
        ticket_promedio = (
            monto_total / total_compras if total_compras else Decimal("0.00")
        )
        unidades_total = (
            DetalleCompra.objects.filter(compra__in=qs).aggregate(
                t=Sum("cantidad")
            )["t"]
            or 0
        )

        # ── Compras por proveedor ─────────────────────────────────────────────
        compras_por_proveedor = (
            qs.values("proveedor__id", "proveedor__nombre")
            .annotate(
                cantidad=Count("pk"),
                monto=Sum("total"),
            )
            .order_by("-monto")
        )

        # ── Compras por estado ────────────────────────────────────────────────
        compras_por_estado = [
            {
                "estado": fila["estado"],
                "etiqueta": Compra.Estado(fila["estado"]).label,
                "cantidad": fila["cantidad"],
                "monto": fila["monto"],
            }
            for fila in qs.values("estado")
            .annotate(cantidad=Count("pk"), monto=Sum("total"))
            .order_by("estado")
        ]

        # ── Productos más comprados ───────────────────────────────────────────
        productos_comprados = (
            DetalleCompra.objects.filter(compra__in=qs)
            .values("producto__codigo", "producto__nombre")
            .annotate(
                unidades=Sum("cantidad"),
                monto=Sum("subtotal"),
                compras=Count("compra", distinct=True),
            )
            .order_by("-unidades")[:10]
        )

        # ── Catálogos para los filtros ────────────────────────────────────────
        proveedores = Proveedor.objects.filter(
            compras__isnull=False
        ).distinct().order_by("nombre")

        context.update(
            {
                "periodos": self.PERIODOS,
                "periodo_actual": periodo,
                "proveedores": proveedores,
                "proveedor_id": proveedor_id,
                "estados": Compra.Estado.choices,
                "estado_actual": estado,
                "fecha_inicio": fecha_inicio,
                "fecha_fin": fecha_fin,
                "total_compras": total_compras,
                "monto_total": monto_total,
                "ticket_promedio": ticket_promedio,
                "unidades_total": unidades_total,
                "compras_por_proveedor": compras_por_proveedor,
                "compras_por_estado": compras_por_estado,
                "productos_comprados": productos_comprados,
                "compras_lista": qs.order_by("-fecha_compra", "-pk")[:50],
            }
        )
        return context


# ──────────────────────────────────────────────────────────────────────────────
# Reporte de inventario
# ──────────────────────────────────────────────────────────────────────────────

class ReporteInventarioView(RoleRequiredMixin, TemplateView):
    """Reporte de inventario basado en lotes, existencias y movimientos."""

    allowed_groups = (ADMIN_GROUP,)
    template_name = "reportes/reporte_inventario.html"

    DIAS_POR_VENCER = 30

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        request = self.request

        busqueda = request.GET.get("q", "").strip()
        estado = request.GET.get("estado", "todos")
        alerta = request.GET.get("alerta", "todas")

        hoy = timezone.localdate()
        limite_vencimiento = hoy + timedelta(days=self.DIAS_POR_VENCER)

        # ── Catálogo con el stock sumado de sus lotes activos ─────────────────
        productos_qs = Producto.objects.annotate(stock_total=stock_por_producto())

        if busqueda:
            productos_qs = productos_qs.filter(
                Q(nombre__icontains=busqueda) | Q(codigo__icontains=busqueda)
            )

        if estado == "activos":
            productos_qs = productos_qs.filter(activo=True)
        elif estado == "inactivos":
            productos_qs = productos_qs.filter(activo=False)

        # Se usan subconsultas para no inflar la suma de stock al filtrar lotes.
        if alerta == "bajo":
            productos_qs = productos_qs.filter(
                activo=True, stock_total__lte=F("stock_minimo")
            )
        elif alerta == "vencido":
            productos_qs = productos_qs.filter(
                pk__in=Lote.objects.filter(
                    activo=True,
                    fecha_vencimiento__lt=hoy,
                    stock_actual__gt=0,
                ).values("producto_id")
            )
        elif alerta == "por_vencer":
            productos_qs = productos_qs.filter(
                pk__in=Lote.objects.filter(
                    activo=True,
                    fecha_vencimiento__gte=hoy,
                    fecha_vencimiento__lte=limite_vencimiento,
                    stock_actual__gt=0,
                ).values("producto_id")
            )

        # ── Composición del catálogo ──────────────────────────────────────────
        total_activos = Producto.objects.filter(activo=True).count()
        total_inactivos = Producto.objects.filter(activo=False).count()
        total_productos = total_activos + total_inactivos

        # ── Existencias y valor del inventario ────────────────────────────────
        lotes_activos = Lote.objects.filter(activo=True)
        stock_unidades = (
            lotes_activos.aggregate(t=Sum("stock_actual"))["t"]
            or Decimal("0.00")
        )
        capas_activas = CapaCosto.objects.filter(
            lote__activo=True,
            cantidad_restante__gt=0,
        )
        valor_inventario = (
            capas_activas.filter(costo_unitario__isnull=False).aggregate(
                v=Sum(
                    ExpressionWrapper(
                        F("cantidad_restante") * F("costo_unitario"),
                        output_field=DecimalField(
                            max_digits=16, decimal_places=2
                        ),
                    )
                )
            )["v"]
            or Decimal("0.00")
        )
        unidades_sin_costo = (
            capas_activas.filter(costo_unitario__isnull=True).aggregate(
                total=Sum("cantidad_restante")
            )["total"]
            or Decimal("0.00")
        )
        total_lotes = lotes_activos.count()

        # ── Alertas de vencimiento ────────────────────────────────────────────
        lotes_por_vencer = lotes_activos.filter(
            fecha_vencimiento__gte=hoy,
            fecha_vencimiento__lte=limite_vencimiento,
            stock_actual__gt=0,
        )
        lotes_vencidos = lotes_activos.filter(
            fecha_vencimiento__lt=hoy,
            stock_actual__gt=0,
        )
        total_por_vencer = lotes_por_vencer.count()
        total_vencidos = lotes_vencidos.count()

        # ── Productos con stock bajo ──────────────────────────────────────────
        productos_stock_bajo = productos_con_stock_bajo().order_by(
            "stock_total", "nombre"
        )
        total_stock_bajo = productos_stock_bajo.count()

        # ── Movimientos recientes ─────────────────────────────────────────────
        movimientos_recientes = MovimientoInventario.objects.select_related(
            "lote__producto", "usuario"
        ).order_by("-fecha", "-pk")[:15]

        # ── Productos más vendidos de todos los tiempos ───────────────────────
        productos_mas_vendidos = (
            DetalleVenta.objects.values(
                "producto__codigo", "producto__nombre", "producto__precio_venta"
            )
            .annotate(
                unidades_vendidas=Sum("cantidad"),
                ingresos_generados=Sum(
                    ExpressionWrapper(
                        F("precio_unitario") * F("cantidad"),
                        output_field=DecimalField(max_digits=14, decimal_places=2),
                    )
                ),
                ganancia_bruta=Sum(
                    ExpressionWrapper(
                        F("precio_unitario") * F("cantidad")
                        - F("costo_total"),
                        output_field=DecimalField(
                            max_digits=16, decimal_places=2
                        ),
                    ),
                    filter=Q(costo_total__isnull=False),
                ),
                unidades_sin_costo=Sum(
                    "cantidad",
                    filter=Q(costo_total__isnull=True),
                ),
                veces_vendido=Count("venta", distinct=True),
            )
            .order_by("-unidades_vendidas")[:10]
        )

        # ── Precio promedio y rango de precios ────────────────────────────────
        precio_stats = Producto.objects.filter(activo=True).aggregate(
            precio_min=Min("precio_venta"),
            precio_max=Max("precio_venta"),
            precio_avg=Avg("precio_venta"),
        )

        context.update(
            {
                "productos": productos_qs.order_by("nombre"),
                "total_productos": total_productos,
                "total_activos": total_activos,
                "total_inactivos": total_inactivos,
                "stock_unidades": stock_unidades,
                "valor_inventario": valor_inventario,
                "unidades_sin_costo": unidades_sin_costo,
                "total_lotes": total_lotes,
                "lotes_por_vencer": lotes_por_vencer.select_related(
                    "producto"
                ).prefetch_related("capas_costo")[:10],
                "total_por_vencer": total_por_vencer,
                "lotes_vencidos": lotes_vencidos.select_related(
                    "producto"
                ).prefetch_related("capas_costo")[:10],
                "total_vencidos": total_vencidos,
                "productos_stock_bajo": productos_stock_bajo[:10],
                "total_stock_bajo": total_stock_bajo,
                "movimientos_recientes": movimientos_recientes,
                "productos_mas_vendidos": productos_mas_vendidos,
                "precio_stats": precio_stats,
                "q": busqueda,
                "estado": estado,
                "alerta": alerta,
                "dias_por_vencer": self.DIAS_POR_VENCER,
            }
        )
        return context
