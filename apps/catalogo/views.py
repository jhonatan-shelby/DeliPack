from django.core.paginator import Paginator
from django.db.models import Count, F, Q
from django.http import Http404
from django.shortcuts import get_object_or_404, render

from .models import Atributo, Categoria, Producto, ValorAtributo

POR_PAGINA = 24
ORDENES = {
    "": ("orden", "nombre"),
    "precio": ("precio", "nombre"),
    "-precio": ("-precio", "nombre"),
    "nombre": ("nombre",),
}


def _filtrar(request, base):
    """Aplica búsqueda, filtros por atributo (OR dentro del grupo, AND entre grupos) y orden."""
    productos = base
    q = request.GET.get("q", "").strip()[:60]
    if q:
        productos = productos.filter(
            Q(nombre__icontains=q) | Q(resumen__icontains=q) | Q(ingredientes__icontains=q)
            | Q(valores__nombre__icontains=q)).distinct()

    elegidos = {}
    for atributo in Atributo.objects.all():
        slugs = [s for s in request.GET.getlist(atributo.slug) if s][:10]
        if slugs:
            elegidos[atributo.slug] = set(slugs)
            productos = productos.filter(valores__atributo=atributo, valores__slug__in=slugs)
    if elegidos:
        productos = productos.distinct()

    if request.GET.get("disponibles") == "1":
        productos = productos.filter(stock__gt=0)

    orden = request.GET.get("orden", "")
    productos = productos.order_by(*ORDENES.get(orden, ORDENES[""]))

    # Opciones de filtro presentes en esta sección, con su cantidad de productos
    valores = (ValorAtributo.objects.filter(productos__in=base).select_related("atributo")
               .annotate(total=Count("productos", filter=Q(productos__in=base), distinct=True))
               .order_by("atributo__orden", "atributo__nombre", "nombre"))
    grupos = {}
    for v in valores:
        v.marcado = v.slug in elegidos.get(v.atributo.slug, set())
        grupos.setdefault(v.atributo, []).append(v)

    hay_filtros = bool(q or elegidos or request.GET.get("disponibles") == "1")
    return productos, grupos, {"q": q, "orden": orden, "hay_filtros": hay_filtros,
                               "disponibles": request.GET.get("disponibles") == "1",
                               "num_filtros": sum(len(s) for s in elegidos.values())}


def _paginar(request, productos):
    pagina = Paginator(productos.prefetch_related("valores__atributo").select_related("categoria"),
                       POR_PAGINA).get_page(request.GET.get("pagina"))
    params = request.GET.copy()
    params.pop("pagina", None)
    return pagina, params.urlencode()


def categoria(request, slug):
    cat = get_object_or_404(Categoria, slug=slug)
    base = Producto.objects.visibles().filter(categoria=cat)
    productos, grupos, estado = _filtrar(request, base)
    pagina, query = _paginar(request, productos)
    return render(request, "catalogo/categoria.html", {
        "categoria": cat, "pagina": pagina, "grupos": grupos, "query": query, **estado,
        "seccion": cat.slug,
    })


def combos_promociones(request):
    """Apartado 4: combos + cualquier producto en oferta."""
    try:
        combos = Categoria.objects.get(slug="combos")
    except Categoria.DoesNotExist:
        combos = None
    base = Producto.objects.visibles().filter(Q(categoria=combos) | Q(precio_anterior__gt=F("precio")))
    productos, grupos, estado = _filtrar(request, base)
    pagina, query = _paginar(request, productos)
    return render(request, "catalogo/categoria.html", {
        "categoria": combos, "pagina": pagina, "grupos": grupos, "query": query, **estado,
        "seccion": "combos", "titulo": "Combos y promociones",
        "presentacion": "Paquetes para la semana y productos con precio especial. "
                        "Los precios tachados muestran cuánto ahorras.",
    })


def producto(request, slug):
    p = get_object_or_404(Producto.objects.select_related("categoria").prefetch_related("valores__atributo"),
                          slug=slug)
    if not p.activo:
        raise Http404
    plantilla = "catalogo/_detalle.html" if request.GET.get("parcial") == "1" else "catalogo/producto.html"
    respuesta = render(request, plantilla, {"p": p, "seccion": p.categoria.slug})
    if request.GET.get("parcial") == "1":
        respuesta["Cache-Control"] = "private, max-age=60"
    return respuesta
