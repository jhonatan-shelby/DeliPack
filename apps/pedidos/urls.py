from django.urls import path

from . import views

app_name = "pedidos"

urlpatterns = [
    path("pago/", views.pago, name="pago"),
    path("carrito/agregar/", views.carrito_agregar, name="agregar"),
    path("carrito/actualizar/", views.carrito_actualizar, name="actualizar"),
    path("pedidos/<str:codigo>/", views.detalle, name="detalle"),
    path("pedidos/<str:codigo>/cancelar/", views.cancelar, name="cancelar"),
]
