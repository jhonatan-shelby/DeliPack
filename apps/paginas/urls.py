from django.urls import path

from . import views

app_name = "paginas"

urlpatterns = [
    path("", views.inicio, name="inicio"),
    path("robots.txt", views.robots, name="robots"),
    path("salud/", views.salud, name="salud"),
    path("favicon.ico", views.favicon),
]
