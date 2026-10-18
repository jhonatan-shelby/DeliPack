from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode

from .tokens import token_verificacion


def enviar_verificacion(request, usuario):
    uid = urlsafe_base64_encode(force_bytes(usuario.pk))
    token = token_verificacion.make_token(usuario)
    enlace = request.build_absolute_uri(reverse("cuentas:verificar", args=[uid, token]))
    texto = render_to_string("cuentas/correo_verificacion.txt", {"usuario": usuario, "enlace": enlace})
    send_mail("Confirma tu correo en DeliPack", texto, None, [usuario.email])
