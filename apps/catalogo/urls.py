from django.urls import path

from . import views

app_name = "catalogo"

urlpatterns = [
    path("combos-y-promociones/", views.combos_promociones, name="combos"),
    path("producto/<slug:slug>/", views.producto, name="producto"),
    path("<slug:slug>/", views.categoria, name="categoria"),
]
