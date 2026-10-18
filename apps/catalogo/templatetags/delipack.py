from django import template
from django.db.models import F
from django.template.defaultfilters import floatformat

register = template.Library()


@register.filter
def dinero(valor):
    """5.5 -> $5,50"""
    if valor in (None, ""):
        return ""
    return f"${floatformat(valor, 2)}"


@register.simple_tag
def productos_stock_bajo(limite=8):
    from apps.catalogo.models import Producto
    return (Producto.objects.filter(activo=True, stock__lte=F("stock_minimo"))
            .select_related("categoria").order_by("stock")[:limite])
