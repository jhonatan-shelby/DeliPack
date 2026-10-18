"""Reglas del negocio de pedidos: totales, descuento de bienvenida, capacidad diaria y stock."""
from dataclasses import dataclass
from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Sum
from django.utils import timezone

from apps.catalogo.inventario import StockInsuficiente, registrar_movimiento
from apps.catalogo.models import MovimientoInventario, Promocion

from .models import ConfiguracionNegocio, Pedido, PedidoItem

DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre",
         "octubre", "noviembre", "diciembre"]
CENTAVO = Decimal("0.01")


class PedidoError(Exception):
    pass


@dataclass
class Totales:
    subtotal: Decimal
    descuento: Decimal
    porcentaje: int
    envio: Decimal
    total: Decimal
    descuento_motivo: str = ""  # por qué no aplica todavía (para mostrarlo al cliente)


def calcular_totales(lineas, usuario, config=None):
    config = config or ConfiguracionNegocio.actual()
    subtotal = sum((l.subtotal for l in lineas), Decimal("0.00"))
    porcentaje, motivo = 0, ""
    if usuario is not None and usuario.is_authenticated and usuario.tiene_descuento and lineas:
        promo = Promocion.bienvenida_activa()
        requeridas = list(promo.categorias_requeridas.all()) if promo else []
        en_carrito = {l.producto.categoria_id for l in lineas}
        faltan = [c.nombre.lower() for c in requeridas if c.pk not in en_carrito]
        if faltan:
            motivo = f"Agrega {' y '.join(faltan)} para usar tu {usuario.descuento_bienvenida}% de bienvenida."
        else:
            porcentaje = usuario.descuento_bienvenida
    descuento = (subtotal * porcentaje / 100).quantize(CENTAVO, ROUND_HALF_UP)
    envio = config.costo_envio if lineas else Decimal("0.00")
    return Totales(subtotal, descuento, porcentaje, envio, subtotal - descuento + envio, motivo)


def comidas_reservadas(fecha):
    return (PedidoItem.objects.filter(pedido__fecha_entrega=fecha, cuenta_capacidad=True)
            .exclude(pedido__estado=Pedido.Estado.CANCELADO)
            .aggregate(n=Sum("cantidad"))["n"] or 0)


def fechas_disponibles(config=None):
    """Próximos días hábiles (lunes a viernes) con los cupos de cocina que quedan."""
    config = config or ConfiguracionNegocio.actual()
    hoy = timezone.localdate()
    dia = hoy + timedelta(days=config.anticipacion_dias)
    fechas = []
    while len(fechas) < config.dias_a_mostrar:
        if dia.weekday() < 5:
            libres = max(config.capacidad_diaria - comidas_reservadas(dia), 0)
            etiqueta = f"{DIAS[dia.weekday()].capitalize()} {dia.day} de {MESES[dia.month - 1]}"
            fechas.append({"fecha": dia, "valor": dia.isoformat(), "etiqueta": etiqueta, "libres": libres})
        dia += timedelta(days=1)
    return fechas


@transaction.atomic
def crear_pedido(usuario, lineas, datos):
    """Crea el pedido, descuenta stock (con historial) y marca el descuento como usado."""
    if not lineas:
        raise PedidoError("Tu carrito está vacío.")
    config = ConfiguracionNegocio.objects.select_for_update().get_or_create(pk=1)[0]

    fecha = datos["fecha_entrega"]
    validas = {f["fecha"] for f in fechas_disponibles(config)}
    if fecha not in validas:
        raise PedidoError("Elige una fecha de entrega de la lista.")
    comidas = sum(l.cantidad for l in lineas if l.producto.categoria.cuenta_capacidad)
    libres = config.capacidad_diaria - comidas_reservadas(fecha)
    if comidas > libres:
        raise PedidoError(
            f"Para esa fecha solo quedan {max(libres, 0)} comidas disponibles. Elige otro día o reduce la cantidad.")

    totales = calcular_totales(lineas, usuario, config)
    pedido = Pedido.objects.create(
        usuario=usuario, subtotal=totales.subtotal, descuento=totales.descuento,
        descuento_porcentaje=totales.porcentaje, envio=totales.envio, total=totales.total,
        **datos,
    )
    for l in lineas:
        try:
            registrar_movimiento(l.producto.pk, -l.cantidad, MovimientoInventario.VENTA,
                                 motivo=f"Pedido {pedido.codigo}", usuario=usuario, pedido=pedido)
        except StockInsuficiente as e:
            raise PedidoError(str(e)) from e
        PedidoItem.objects.create(
            pedido=pedido, producto=l.producto, nombre=l.producto.nombre, precio_unitario=l.producto.precio,
            cantidad=l.cantidad, subtotal=l.subtotal, cuenta_capacidad=l.producto.categoria.cuenta_capacidad)

    if totales.porcentaje:
        get_user_model().objects.filter(pk=usuario.pk).update(descuento_usado=True)
        usuario.descuento_usado = True
    return pedido


@transaction.atomic
def cancelar_pedido(pedido, usuario=None):
    """Devuelve las existencias al inventario y, si se usó, restituye el descuento de bienvenida."""
    pedido = Pedido.objects.select_for_update().get(pk=pedido.pk)
    if pedido.estado in (Pedido.Estado.CANCELADO, Pedido.Estado.ENTREGADO):
        return False
    for item in pedido.items.filter(producto__isnull=False):
        registrar_movimiento(item.producto_id, item.cantidad, MovimientoInventario.DEVOLUCION,
                             motivo=f"Cancelación {pedido.codigo}", usuario=usuario, pedido=pedido)
    pedido.estado = Pedido.Estado.CANCELADO
    pedido.save(update_fields=["estado", "actualizado"])
    if pedido.descuento_porcentaje:
        get_user_model().objects.filter(pk=pedido.usuario_id).update(descuento_usado=False)
    return True
