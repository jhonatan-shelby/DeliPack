"""Toda modificación de existencias pasa por aquí, así queda registrada en el historial."""
from django.db import transaction
from django.db.models import F

from .models import MovimientoInventario, Producto


class StockInsuficiente(Exception):
    def __init__(self, producto, disponible):
        self.producto = producto
        self.disponible = disponible
        if disponible == 0:
            msg = f"{producto.nombre} está agotado."
        else:
            msg = f"Solo quedan {disponible} unidades de {producto.nombre}."
        super().__init__(msg)


@transaction.atomic
def registrar_movimiento(producto_id, cantidad, tipo, motivo="", usuario=None, pedido=None):
    """Suma (cantidad > 0) o resta (cantidad < 0) stock bloqueando la fila del producto.

    El bloqueo (SELECT ... FOR UPDATE) evita que dos compras simultáneas vendan la misma unidad.
    """
    producto = Producto.objects.select_for_update().get(pk=producto_id)
    nuevo = producto.stock + cantidad
    if nuevo < 0:
        raise StockInsuficiente(producto, producto.stock)
    Producto.objects.filter(pk=producto.pk).update(stock=F("stock") + cantidad)
    producto.stock = nuevo
    return MovimientoInventario.objects.create(
        producto=producto, tipo=tipo, cantidad=cantidad, stock_resultante=nuevo,
        motivo=motivo[:200], usuario=usuario, pedido=pedido)
