from django.contrib import messages
from django.contrib.auth import get_user_model, login, logout
from django.contrib.auth.decorators import login_required
from django.core.cache import cache
from django.shortcuts import redirect, render
from django.utils.encoding import force_str
from django.utils.http import url_has_allowed_host_and_scheme, urlsafe_base64_decode
from django.views.decorators.http import require_POST

from apps.catalogo.models import Promocion

from .correos import enviar_verificacion
from .forms import IngresoForm, PerfilForm, RegistroForm
from .tokens import token_verificacion


def _destino(request, defecto="paginas:inicio"):
    siguiente = request.POST.get("next") or request.GET.get("next")
    if siguiente and url_has_allowed_host_and_scheme(siguiente, {request.get_host()}, request.is_secure()):
        return siguiente
    return defecto


def registro(request):
    if request.user.is_authenticated:
        return redirect("cuentas:perfil")
    form = RegistroForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        usuario = form.save()
        promo = Promocion.bienvenida_activa()
        if promo:
            usuario.descuento_bienvenida = promo.porcentaje
            usuario.save(update_fields=["descuento_bienvenida"])
        login(request, usuario, backend="django.contrib.auth.backends.ModelBackend")
        enviar_verificacion(request, usuario)
        request.session["mostrar_bienvenida"] = True
        return redirect(_destino(request, "cuentas:verificacion_enviada"))
    return render(request, "cuentas/registro.html", {"form": form, "promo": Promocion.bienvenida_activa(),
                                                     "next": request.GET.get("next", "")})


def ingresar(request):
    if request.user.is_authenticated:
        return redirect(_destino(request))
    form = IngresoForm(request, request.POST or None)
    if request.method == "POST" and form.is_valid():
        login(request, form.usuario)
        messages.success(request, f"Hola, {form.usuario.get_short_name()}.")
        return redirect(_destino(request))
    return render(request, "cuentas/ingresar.html", {"form": form, "next": request.GET.get("next", "")})


@require_POST
def salir(request):
    logout(request)
    return redirect("paginas:inicio")


def verificar(request, uidb64, token):
    Usuario = get_user_model()
    try:
        usuario = Usuario.objects.get(pk=force_str(urlsafe_base64_decode(uidb64)))
    except (Usuario.DoesNotExist, ValueError, TypeError, OverflowError):
        usuario = None
    if usuario is not None and token_verificacion.check_token(usuario, token):
        usuario.email_verificado = True
        usuario.save(update_fields=["email_verificado"])
        messages.success(request, "Tu correo quedó verificado. Ya puedes hacer pedidos.")
        return redirect("pedidos:pago" if request.user == usuario else "cuentas:ingresar")
    return render(request, "cuentas/verificacion_invalida.html", status=400)


@login_required
def verificacion_enviada(request):
    if request.user.email_verificado:
        return redirect("cuentas:perfil")
    return render(request, "cuentas/verificacion_enviada.html")


@login_required
@require_POST
def reenviar_verificacion(request):
    clave = f"reenvio:{request.user.pk}"
    if request.user.email_verificado:
        return redirect("cuentas:perfil")
    if cache.get(clave):
        messages.info(request, "Ya te enviamos un correo hace poco. Revisa también la carpeta de spam.")
    else:
        enviar_verificacion(request, request.user)
        cache.set(clave, True, 60)
        messages.success(request, f"Te enviamos un nuevo enlace a {request.user.email}.")
    return redirect("cuentas:verificacion_enviada")


@login_required
def perfil(request):
    form = PerfilForm(request.POST or None, instance=request.user)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Datos actualizados.")
        return redirect("cuentas:perfil")
    pedidos = request.user.pedidos.prefetch_related("items").order_by("-creado")[:20]
    return render(request, "cuentas/perfil.html", {"form": form, "pedidos": pedidos})
