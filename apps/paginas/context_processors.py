from django.conf import settings

from apps.catalogo.models import Promocion

SECCIONES = [
    ("inicio", "Inicio", "/"),
    ("platos-fuertes", "Platos fuertes", "/platos-fuertes/"),
    ("mise-en-place", "Mise en place", "/mise-en-place/"),
    ("combos", "Combos y promociones", "/combos-y-promociones/"),
    ("pago", "Pago", "/pago/"),
]


def sitio(request):
    datos = {"negocio": settings.NEGOCIO, "secciones": SECCIONES, "admin_url": settings.ADMIN_URL}
    # Ventana de bienvenida justo después de registrarse
    if request.session.get("mostrar_bienvenida"):
        datos["bienvenida_ahora"] = True
        del request.session["mostrar_bienvenida"]
    # La promoción solo se consulta para visitantes sin sesión o tras registrarse
    if not request.user.is_authenticated or datos.get("bienvenida_ahora"):
        datos["promo"] = Promocion.bienvenida_activa()
    return datos
