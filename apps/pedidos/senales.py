from django.contrib.auth.signals import user_logged_in
from django.dispatch import receiver

from apps.catalogo.models import Producto

from .carrito import CLAVE, MAX_POR_PRODUCTO
from .models import CarritoItem


@receiver(user_logged_in)
def unir_carrito(sender, request, user, **kwargs):
    """Al iniciar sesión, lo que el visitante tenía en el carrito pasa a su carrito guardado."""
    datos = request.session.pop(CLAVE, None) if request is not None else None
    if not datos:
        return
    productos = {p.pk: p for p in Producto.objects.visibles().filter(pk__in=[int(k) for k in datos])}
    for pid, cant in datos.items():
        p = productos.get(int(pid))
        if not p:
            continue
        item, creado = CarritoItem.objects.get_or_create(usuario=user, producto=p, defaults={"cantidad": 0})
        item.cantidad = min(item.cantidad + int(cant), p.stock, MAX_POR_PRODUCTO)
        if item.cantidad:
            item.save()
        else:
            item.delete()
