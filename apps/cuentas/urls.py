from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

from . import views

app_name = "cuentas"

urlpatterns = [
    path("registro/", views.registro, name="registro"),
    path("ingresar/", views.ingresar, name="ingresar"),
    path("salir/", views.salir, name="salir"),
    path("perfil/", views.perfil, name="perfil"),
    path("verificar/<uidb64>/<token>/", views.verificar, name="verificar"),
    path("verificacion/", views.verificacion_enviada, name="verificacion_enviada"),
    path("verificacion/reenviar/", views.reenviar_verificacion, name="reenviar_verificacion"),
    # Recuperar contraseña (vistas de Django con plantillas propias)
    path("recuperar/", auth_views.PasswordResetView.as_view(
        template_name="cuentas/recuperar.html",
        email_template_name="cuentas/correo_recuperar.txt",
        subject_template_name="cuentas/asunto_recuperar.txt",
        success_url=reverse_lazy("cuentas:recuperar_enviado")), name="recuperar"),
    path("recuperar/enviado/", auth_views.PasswordResetDoneView.as_view(
        template_name="cuentas/recuperar_enviado.html"), name="recuperar_enviado"),
    path("recuperar/<uidb64>/<token>/", auth_views.PasswordResetConfirmView.as_view(
        template_name="cuentas/recuperar_nueva.html",
        success_url=reverse_lazy("cuentas:recuperar_listo")), name="recuperar_confirmar"),
    path("recuperar/listo/", auth_views.PasswordResetCompleteView.as_view(
        template_name="cuentas/recuperar_listo.html"), name="recuperar_listo"),
]
