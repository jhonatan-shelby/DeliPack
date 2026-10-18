from django.conf import settings


class CabecerasSeguridadMiddleware:
    """Política de seguridad de contenido: el navegador solo ejecuta scripts y estilos de nuestro dominio.

    Bloquea la inyección de código (XSS) aunque alguien lograra insertar HTML en la página.
    El panel de administración de Django queda fuera porque usa estilos en línea propios.
    """

    POLITICA = "; ".join([
        "default-src 'self'",
        "img-src 'self' data: blob:",
        "script-src 'self'",
        "style-src 'self'",
        "font-src 'self'",
        "connect-src 'self'",
        "form-action 'self'",
        "frame-ancestors 'none'",
        "base-uri 'self'",
        "object-src 'none'",
    ])

    def __init__(self, get_response):
        self.get_response = get_response
        self.admin = "/" + settings.ADMIN_URL

    def __call__(self, request):
        respuesta = self.get_response(request)
        if not request.path.startswith(self.admin):
            respuesta.setdefault("Content-Security-Policy", self.POLITICA)
        respuesta.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=(), payment=()")
        respuesta.setdefault("Cross-Origin-Opener-Policy", "same-origin")
        return respuesta
