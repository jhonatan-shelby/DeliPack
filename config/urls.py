from django.conf import settings
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.static import serve

admin.site.site_header = "DeliPack · Administración"
admin.site.site_title = "DeliPack"
admin.site.index_title = "Panel del negocio"

urlpatterns = [
    path(settings.ADMIN_URL, admin.site.urls),
    path("", include("apps.paginas.urls")),
    path("cuentas/", include("apps.cuentas.urls")),
    path("", include("apps.pedidos.urls")),
    # Va al final: /platos-fuertes/, /mise-en-place/, /combos-y-promociones/, /producto/...
    path("", include("apps.catalogo.urls")),
]

if settings.SERVIR_MEDIA:
    urlpatterns.insert(0, re_path(r"^media/(?P<path>.*)$", serve, {"document_root": settings.MEDIA_ROOT}))

handler404 = "apps.paginas.views.error_404"
handler500 = "apps.paginas.views.error_500"
