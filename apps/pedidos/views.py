from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.mail import send_mail
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from apps.catalogo.models import Producto

from .carrito import Carrito
from .forms import PagoForm
from .models import ConfiguracionNegocio, Pedido
from .servicios import PedidoError, calcular_totales, cancelar_pedido, crear_pedido, fechas_disponibles


def _quiere_json(request):
    return request.headers.get("Accept", "").startswith("application/json")


def _volver(request):
    destino = request.POST.get("next") or request.META.get("HTTP_REFERER") or "/"
    if url_has_allowed_host_and_scheme(destino, {request.get_host()}, request.is_secure()):
        return redirect(destino)
    return redirect("pedidos:pago")


def _entero(valor, defecto=1):
    try:
        return int(valor)
    except (TypeError, ValueError):
        return defecto


@require_POST
def carrito_agregar(request):
    producto = get_object_or_404(Producto.objects.visibles(), pk=_entero(request.POST.get("producto"), 0))
    carrito = Carrito(request)
    pedida = carrito.cantidad_de(producto.pk) + max(_entero(request.POST.get("cantidad")), 1)
    final = carrito.agregar(producto, max(_entero(request.POST.get("cantidad")), 1))
    if producto.stock == 0:
        mensaje, ok = f"{producto.nombre} está agotado.", False
    elif final < pedida:
        mensaje, ok = f"Solo hay {final} unidades de {producto.nombre}; quedaron todas en tu carrito.", True
    else:
        mensaje, ok = f"{producto.nombre} se guardó en tu carrito.", True
    if _quiere_json(request):
        return JsonResponse({"ok": ok, "mensaje": mensaje, "cantidad": carrito.cantidad_total()})
    (messages.success if ok else messages.error)(request, mensaje)
    return _volver(request)


@require_POST
def carrito_actualizar(request):
    producto = get_object_or_404(Producto, pk=_entero(request.POST.get("producto"), 0))
    carrito = Carrito(request)
    if request.POST.get("accion") == "quitar":
        carrito.quitar(producto)
    else:
        carrito.fijar(producto, _entero(request.POST.get("cantidad"), 0))
    return redirect("pedidos:pago")


def pago(request):
    """Apartado 5: carrito guardado + datos de entrega + forma de pago."""
    carrito = Carrito(request)
    lineas = carrito.lineas()
    if getattr(carrito, "ajustado", False):
        messages.info(request, "Actualizamos tu carrito según las existencias disponibles.")
    config = ConfiguracionNegocio.actual()
    fechas = fechas_disponibles(config) if lineas else []
    totales = calcular_totales(lineas, request.user, config)
    usuario = request.user if request.user.is_authenticated else None

    inicial = {"telefono": usuario.telefono} if usuario else {}
    form = PagoForm(request.POST or None, fechas=fechas, initial=inicial)

    if request.method == "POST":
        if not usuario:
            return redirect(f"{reverse('cuentas:ingresar')}?next={reverse('pedidos:pago')}")
        if not usuario.email_verificado:
            messages.error(request, "Antes de pagar confirma tu correo con el enlace que te enviamos.")
        elif form.is_valid():
            try:
                pedido = crear_pedido(usuario, lineas, form.cleaned_data)
            except PedidoError as e:
                messages.error(request, str(e))
            else:
                carrito.vaciar()
                _avisar_pedido(request, pedido)
                return redirect("pedidos:detalle", codigo=pedido.codigo)
        lineas = carrito.lineas()
        totales = calcular_totales(lineas, request.user, config)

    return render(request, "pedidos/pago.html", {
        "lineas": lineas, "totales": totales, "form": form, "config": config, "seccion": "pago",
    })


def _avisar_pedido(request, pedido):
    texto = render_to_string("pedidos/correo_pedido.txt", {
        "pedido": pedido, "items": pedido.items.all(), "config": ConfiguracionNegocio.actual()})
    send_mail(f"Recibimos tu pedido {pedido.codigo}", texto, None, [pedido.usuario.email], fail_silently=True)


@login_required
def detalle(request, codigo):
    pedido = get_object_or_404(Pedido.objects.prefetch_related("items"), codigo=codigo, usuario=request.user)
    return render(request, "pedidos/detalle.html", {"pedido": pedido, "config": ConfiguracionNegocio.actual()})


@login_required
@require_POST
def cancelar(request, codigo):
    pedido = get_object_or_404(Pedido, codigo=codigo, usuario=request.user)
    if pedido.estado != Pedido.Estado.PENDIENTE:
        messages.error(request, "Este pedido ya está en proceso. Para cambios, escríbenos por WhatsApp.")
    elif cancelar_pedido(pedido, request.user):
        messages.success(request, f"Cancelaste el pedido {pedido.codigo}.")
    return redirect("pedidos:detalle", codigo=codigo)
