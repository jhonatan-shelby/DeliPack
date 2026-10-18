"""Crea los grupos del personal con sus permisos (como los roles del admin de Django).

Se puede ejecutar varias veces: deja cada grupo exactamente con los permisos definidos aquí.
"""
from django.contrib.auth.models import Group, Permission
from django.core.management.base import BaseCommand

TODOS = ["add", "change", "delete", "view"]

GRUPOS = {
    "Gerencia": {
        "catalogo": {"categoria": TODOS, "atributo": TODOS, "valoratributo": TODOS, "producto": TODOS + ["ajustar_stock"],
                     "movimientoinventario": ["add", "view"], "promocion": TODOS},
        "pedidos": {"pedido": ["change", "view"], "pedidoitem": ["view"], "configuracionnegocio": ["change", "view"],
                    "carritoitem": ["view"]},
        "cuentas": {"usuario": ["change", "view"]},
        "auth": {"group": ["view"]},
    },
    "Inventario": {
        "catalogo": {"categoria": ["view"], "atributo": ["add", "change", "view"],
                     "valoratributo": ["add", "change", "view"],
                     "producto": ["add", "change", "view", "ajustar_stock"],
                     "movimientoinventario": ["add", "view"], "promocion": ["view"]},
        "pedidos": {"pedido": ["view"], "pedidoitem": ["view"]},
    },
    "Ventas": {
        "catalogo": {"producto": ["view"], "movimientoinventario": ["view"], "promocion": ["change", "view"]},
        "pedidos": {"pedido": ["change", "view"], "pedidoitem": ["view"], "configuracionnegocio": ["view"]},
        "cuentas": {"usuario": ["view"]},
    },
    "Atención al cliente": {
        "catalogo": {"producto": ["view"]},
        "pedidos": {"pedido": ["view"], "pedidoitem": ["view"]},
        "cuentas": {"usuario": ["view"]},
    },
}


def codigo(accion, modelo):
    return accion if accion == "ajustar_stock" else f"{accion}_{modelo}"


class Command(BaseCommand):
    help = "Crea o actualiza los grupos del personal y sus permisos"

    def handle(self, *args, **opciones):
        for nombre, apps in GRUPOS.items():
            grupo, _ = Group.objects.get_or_create(name=nombre)
            permisos = []
            for app, modelos in apps.items():
                for modelo, acciones in modelos.items():
                    for accion in acciones:
                        permisos.append(Permission.objects.get(content_type__app_label=app,
                                                               codename=codigo(accion, modelo)))
            grupo.permissions.set(permisos)
            self.stdout.write(f"Grupo «{nombre}»: {len(permisos)} permisos")
