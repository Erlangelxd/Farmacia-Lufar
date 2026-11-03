"""Vistas del módulo de reportes.

Esta app no tiene modelos propios; consulta datos de ventas y catálogo.
Cuando los módulos de compras e inventario estén implementados, sus
consultas se agregarán aquí sin necesidad de cambiar la estructura.
"""

from datetime import date, timedelta
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
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

from apps.catalogo.models import Producto
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


# ──────────────────────────────────────────────────────────────────────────────
# Índice de reportes
# ──────────────────────────────────────────────────────────────────────────────

class ReportesIndexView(LoginRequiredMixin, TemplateView):
    """Página principal del módulo con accesos directos a cada reporte."""

    template_name = "reportes/index.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        hoy = timezone.localdate()

        # Resumen rápido
        ventas_hoy = Venta.objects.filter(creado_en__date=hoy)
        ingresos_hoy = (
            ventas_hoy.aggregate(t=Sum("total"))["t"] or Decimal("0.00")
        )
        total_productos = Producto.objects.filter(activo=True).count()
        total_ventas_mes = Venta.objects.filter(
            creado_en__date__gte=hoy.replace(day=1)
        ).count()
        ingresos_mes = (
            Venta.objects.filter(creado_en__date__gte=hoy.replace(day=1))
            .aggregate(t=Sum("total"))["t"]
            or Decimal("0.00")
        )

        context.update(
            {
                "ventas_hoy": ventas_hoy.count(),
                "ingresos_hoy": ingresos_hoy,
                "total_productos": total_productos,
                "total_ventas_mes": total_ventas_mes,
                "ingresos_mes": ingresos_mes,
                "hoy": hoy,
            }
        )
        return context


# ──────────────────────────────────────────────────────────────────────────────
# Reporte de ventas
# ──────────────────────────────────────────────────────────────────────────────

class ReporteVentasView(LoginRequiredMixin, TemplateView):
    """Reporte de ventas filtrable por periodo y vendedor."""

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
            unidades_total=Sum("detalles__cantidad"),
        )
        total_ventas = agg["total_ventas"] or 0
        ingresos_total = agg["ingresos_total"] or Decimal("0.00")
        ticket_promedio = (
            ingresos_total / total_ventas if total_ventas else Decimal("0.00")
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

        # ── Filtros dinámicos para DetalleVenta ───────────────────────────────
        detalle_filtros: dict = {
            "venta__creado_en__date__gte": fecha_inicio,
            "venta__creado_en__date__lte": fecha_fin,
        }
        if vendedor_id.isdigit():
            detalle_filtros["venta__vendedor_id"] = int(vendedor_id)

        # ── Productos más vendidos ────────────────────────────────────────────
        productos_top = (
            DetalleVenta.objects.filter(**detalle_filtros)
            .values("nombre_producto", "codigo_producto")
            .annotate(
                unidades=Sum("cantidad"),
                ingresos=Sum(
                    ExpressionWrapper(
                        F("precio_unitario") * F("cantidad"),
                        output_field=DecimalField(),
                    )
                ),
            )
            .order_by("-unidades")[:10]
        )

        # ── Lista de vendedores (para filtro) ─────────────────────────────────
        vendedores = User.objects.filter(
            ventas_realizadas__isnull=False
        ).distinct().order_by("first_name", "username")

        # ── Serializar dias para JSON (etiquetas de gráfico) ─────────────────
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
                "unidades_total": agg["unidades_total"] or 0,
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

class ReporteComprasView(LoginRequiredMixin, TemplateView):
    """Reporte de compras (módulo pendiente de implementación)."""

    template_name = "reportes/reporte_compras.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["modulo_pendiente"] = True
        return context


# ──────────────────────────────────────────────────────────────────────────────
# Reporte de inventario
# ──────────────────────────────────────────────────────────────────────────────

class ReporteInventarioView(LoginRequiredMixin, TemplateView):
    """Reporte de inventario: estado actual del catálogo de productos."""

    template_name = "reportes/reporte_inventario.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        request = self.request

        busqueda = request.GET.get("q", "").strip()
        estado = request.GET.get("estado", "todos")

        qs = Producto.objects.all()

        if busqueda:
            qs = qs.filter(
                Q(nombre__icontains=busqueda) | Q(codigo__icontains=busqueda)
            )

        if estado == "activos":
            qs = qs.filter(activo=True)
        elif estado == "inactivos":
            qs = qs.filter(activo=False)

        # Totales del catálogo completo (sin filtro de búsqueda)
        total_activos = Producto.objects.filter(activo=True).count()
        total_inactivos = Producto.objects.filter(activo=False).count()
        total_productos = total_activos + total_inactivos

        # Productos más vendidos de todos los tiempos
        productos_mas_vendidos = (
            DetalleVenta.objects.values(
                "producto__codigo", "producto__nombre", "producto__precio_venta"
            )
            .annotate(
                unidades_vendidas=Sum("cantidad"),
                ingresos_generados=Sum(
                    ExpressionWrapper(
                        F("precio_unitario") * F("cantidad"),
                        output_field=DecimalField(),
                    )
                ),
                veces_vendido=Count("venta", distinct=True),
            )
            .order_by("-unidades_vendidas")[:10]
        )

        # Precio promedio y rango de precios
        precio_stats = Producto.objects.filter(activo=True).aggregate(
            precio_min=Min("precio_venta"),
            precio_max=Max("precio_venta"),
            precio_avg=Avg("precio_venta"),
        )

        context.update(
            {
                "productos": qs.order_by("nombre"),
                "total_productos": total_productos,
                "total_activos": total_activos,
                "total_inactivos": total_inactivos,
                "productos_mas_vendidos": productos_mas_vendidos,
                "precio_stats": precio_stats,
                "q": busqueda,
                "estado": estado,
            }
        )
        return context
