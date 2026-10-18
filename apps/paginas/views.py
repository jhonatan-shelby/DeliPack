from django.http import HttpResponse, HttpResponsePermanentRedirect
from django.templatetags.static import static
from django.shortcuts import render
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_GET

from apps.catalogo.models import Categoria, Producto


def inicio(request):
    destacados = (Producto.objects.visibles().filter(destacado=True, stock__gt=0)
                  .select_related("categoria").prefetch_related("valores__atributo")[:4])
    categorias = Categoria.objects.all()
    return render(request, "paginas/inicio.html", {"destacados": destacados, "categorias": categorias,
                                                   "seccion": "inicio"})


@require_GET
@cache_control(max_age=86400, public=True)
def robots(request):
    return HttpResponse("User-agent: *\nDisallow: /cuentas/\nDisallow: /pago/\nDisallow: /pedidos/\n",
                        content_type="text/plain")


@require_GET
def salud(request):
    """Lo usa Docker para saber si la aplicación responde."""
    return HttpResponse("ok", content_type="text/plain")


def error_404(request, exception):
    return render(request, "404.html", status=404)


def error_500(request):
    return render(request, "500.html", status=500)


def favicon(request):
    return HttpResponsePermanentRedirect(static("img/favicon.svg"))
