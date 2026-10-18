from django.contrib import admin, messages
from django.utils.html import format_html

from .models import ConfiguracionNegocio, Pedido, PedidoItem
from .servicios import cancelar_pedido

COLORES = {
    "PENDIENTE": "#b54708", "CONFIRMADO": "#175cd3", "PREPARANDO": "#6941c6",
    "EN_CAMINO": "#0e7090", "ENTREGADO": "#3f7a24", "CANCELADO": "#667085",
}


class ItemInline(admin.TabularInline):
    model = PedidoItem
    extra = 0
    max_num = 0
    can_delete = False
    fields = ("nombre", "precio_unitario", "cantidad", "subtotal")
    readonly_fields = fields


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ("codigo", "cliente", "fecha_entrega", "franja", "tipo_entrega", "total", "metodo_pago",
                    "pagado", "estado_color", "creado")
    list_filter = ("estado", "fecha_entrega", "franja", "tipo_entrega", "metodo_pago", "pagado")
    search_fields = ("codigo", "usuario__email", "usuario__nombres", "usuario__apellidos", "telefono")
    date_hierarchy = "fecha_entrega"
    list_select_related = ("usuario",)
    list_per_page = 50
    inlines = [ItemInline]
    actions = ["confirmar", "preparar", "en_camino", "entregar", "marcar_pagado", "cancelar"]
    readonly_fields = ("codigo", "usuario", "subtotal", "descuento", "descuento_porcentaje", "envio", "total",
                       "creado", "actualizado")
    fieldsets = (
        ("Pedido", {"fields": ("codigo", "usuario", "estado", "creado", "actualizado")}),
        ("Entrega", {"fields": ("tipo_entrega", "fecha_entrega", "franja", "direccion", "referencia",
                                "telefono", "notas")}),
        ("Pago", {"fields": ("metodo_pago", "pagado", "referencia_pago", "subtotal", "descuento_porcentaje",
                             "descuento", "envio", "total")}),
    )

    @admin.display(description="cliente", ordering="usuario__nombres")
    def cliente(self, obj):
        return obj.usuario.get_full_name() or obj.usuario.email

    @admin.display(description="estado", ordering="estado")
    def estado_color(self, obj):
        return format_html('<strong style="color:{}">{}</strong>', COLORES.get(obj.estado, "#000"),
                           obj.get_estado_display())

    def has_add_permission(self, request):
        return False  # los pedidos llegan desde la página

    def has_delete_permission(self, request, obj=None):
        return False  # se cancelan, no se borran (así el inventario cuadra)

    def save_model(self, request, obj, form, change):
        if "estado" in form.changed_data and obj.estado == Pedido.Estado.CANCELADO:
            obj.estado = Pedido.objects.get(pk=obj.pk).estado
            super().save_model(request, obj, form, change)
            cancelar_pedido(obj, request.user)
            obj.refresh_from_db()
            self.message_user(request, "Pedido cancelado; las existencias volvieron al inventario.")
            return
        super().save_model(request, obj, form, change)

    def _cambiar(self, request, qs, estado):
        n = qs.exclude(estado__in=[Pedido.Estado.CANCELADO, Pedido.Estado.ENTREGADO]).update(estado=estado)
        self.message_user(request, f"{n} pedidos actualizados a «{Pedido.Estado(estado).label}».")

    @admin.action(description="Confirmar pedidos")
    def confirmar(self, request, qs):
        self._cambiar(request, qs, Pedido.Estado.CONFIRMADO)

    @admin.action(description="Pasar a «En preparación»")
    def preparar(self, request, qs):
        self._cambiar(request, qs, Pedido.Estado.PREPARANDO)

    @admin.action(description="Pasar a «En camino»")
    def en_camino(self, request, qs):
        self._cambiar(request, qs, Pedido.Estado.EN_CAMINO)

    @admin.action(description="Marcar como entregados")
    def entregar(self, request, qs):
        self._cambiar(request, qs, Pedido.Estado.ENTREGADO)

    @admin.action(description="Marcar como pagados")
    def marcar_pagado(self, request, qs):
        n = qs.update(pagado=True)
        self.message_user(request, f"{n} pedidos marcados como pagados.")

    @admin.action(description="Cancelar y devolver existencias")
    def cancelar(self, request, qs):
        n = sum(1 for p in qs if cancelar_pedido(p, request.user))
        self.message_user(request, f"{n} pedidos cancelados; el stock volvió al inventario.",
                          messages.SUCCESS if n else messages.WARNING)


@admin.register(ConfiguracionNegocio)
class ConfiguracionAdmin(admin.ModelAdmin):
    list_display = ("__str__", "capacidad_diaria", "anticipacion_dias", "costo_envio")

    def has_add_permission(self, request):
        return not ConfiguracionNegocio.objects.exists()

    def has_delete_permission(self, request, obj=None):
        return False
