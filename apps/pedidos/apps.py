from django.apps import AppConfig


class PedidosConfig(AppConfig):
    name = "apps.pedidos"
    verbose_name = "Ventas y pedidos"

    def ready(self):
        from . import senales  # noqa: F401
