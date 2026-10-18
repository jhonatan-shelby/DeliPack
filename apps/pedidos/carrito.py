"""Carrito con la misma interfaz para visitantes (sesión) y clientes (base de datos)."""
from dataclasses import dataclass
from decimal import Decimal

from apps.catalogo.models import Producto

from .models import CarritoItem

CLAVE = "carrito"
MAX_POR_PRODUCTO = 30


@dataclass
class Linea:
    producto: Producto
    cantidad: int

    @property
    def subtotal(self):
        return self.producto.precio * self.cantidad


class Carrito:
    def __init__(self, request):
        self.request = request
        self.usuario = request.user if request.user.is_authenticated else None
        self._cache = None

    # ---------- lectura ----------
    def _cantidades(self):
        if self._cache is None:
            if self.usuario:
                self._cache = dict(CarritoItem.objects.filter(usuario=self.usuario)
                                   .values_list("producto_id", "cantidad"))
            else:
                self._cache = {int(k): v for k, v in self.request.session.get(CLAVE, {}).items()}
        return self._cache

    def cantidad_total(self):
        return sum(self._cantidades().values())

    def cantidad_de(self, producto_id):
        return self._cantidades().get(producto_id, 0)

    def lineas(self):
        """Líneas con datos actuales del producto. Quita lo que ya no existe o se agotó y ajusta al stock."""
        cantidades = self._cantidades()
        if not cantidades:
            return []
        productos = Producto.objects.visibles().select_related("categoria").filter(pk__in=cantidades)
        lineas, cambios = [], False
        encontrados = set()
        for p in productos.order_by("categoria__orden", "nombre"):
            encontrados.add(p.pk)
            cant = min(cantidades[p.pk], p.stock)
            if cant != cantidades[p.pk]:
                cambios = True
                self.fijar(p, cant)
            if cant > 0:
                lineas.append(Linea(p, cant))
        for pid in set(cantidades) - encontrados:
            cambios = True
            self._quitar_id(pid)
        self.ajustado = cambios
        return lineas

    @staticmethod
    def subtotal(lineas):
        return sum((l.subtotal for l in lineas), Decimal("0.00"))

    # ---------- escritura ----------
    def agregar(self, producto, cantidad=1):
        return self.fijar(producto, self.cantidad_de(producto.pk) + cantidad)

    def fijar(self, producto, cantidad):
        """Deja la cantidad indicada, sin pasar del stock ni del máximo. Devuelve la cantidad final."""
        cantidad = max(0, min(int(cantidad), producto.stock, MAX_POR_PRODUCTO))
        if cantidad == 0:
            self._quitar_id(producto.pk)
            return 0
        if self.usuario:
            CarritoItem.objects.update_or_create(usuario=self.usuario, producto=producto,
                                                 defaults={"cantidad": cantidad})
        else:
            datos = self.request.session.get(CLAVE, {})
            datos[str(producto.pk)] = cantidad
            self.request.session[CLAVE] = datos
        self._cantidades()[producto.pk] = cantidad
        return cantidad

    def _quitar_id(self, producto_id):
        if self.usuario:
            CarritoItem.objects.filter(usuario=self.usuario, producto_id=producto_id).delete()
        else:
            datos = self.request.session.get(CLAVE, {})
            if datos.pop(str(producto_id), None) is not None:
                self.request.session[CLAVE] = datos
        self._cantidades().pop(producto_id, None)

    def quitar(self, producto):
        self._quitar_id(producto.pk)

    def vaciar(self):
        if self.usuario:
            CarritoItem.objects.filter(usuario=self.usuario).delete()
        else:
            self.request.session.pop(CLAVE, None)
        self._cache = {}
