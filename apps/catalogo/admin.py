from django import forms
from django.contrib import admin
from django.db.models import F
from django.utils.html import format_html

from .inventario import registrar_movimiento
from .models import Atributo, Categoria, MovimientoInventario, Producto, Promocion, ValorAtributo


@admin.register(Categoria)
class CategoriaAdmin(admin.ModelAdmin):
    list_display = ("nombre", "slug", "orden", "cuenta_capacidad", "productos_visibles")
    list_editable = ("orden",)
    prepopulated_fields = {"slug": ("nombre",)}

    @admin.display(description="productos visibles")
    def productos_visibles(self, obj):
        return obj.productos.filter(activo=True).count()


class ValorInline(admin.TabularInline):
    model = ValorAtributo
    extra = 2
    prepopulated_fields = {"slug": ("nombre",)}


@admin.register(Atributo)
class AtributoAdmin(admin.ModelAdmin):
    list_display = ("nombre", "slug", "orden", "opciones")
    list_editable = ("orden",)
    prepopulated_fields = {"slug": ("nombre",)}
    inlines = [ValorInline]

    @admin.display(description="opciones")
    def opciones(self, obj):
        return ", ".join(v.nombre for v in obj.valores.all())


class StockFiltro(admin.SimpleListFilter):
    title = "existencias"
    parameter_name = "existencias"

    def lookups(self, request, model_admin):
        return [("agotado", "Agotado"), ("bajo", "Stock bajo"), ("ok", "Suficiente")]

    def queryset(self, request, qs):
        if self.value() == "agotado":
            return qs.filter(stock=0)
        if self.value() == "bajo":
            return qs.filter(stock__gt=0, stock__lte=F("stock_minimo"))
        if self.value() == "ok":
            return qs.filter(stock__gt=F("stock_minimo"))
        return qs


class MovimientoInline(admin.TabularInline):
    model = MovimientoInventario
    extra = 0
    max_num = 0
    can_delete = False
    fields = ("fecha", "tipo", "cantidad", "stock_resultante", "motivo", "usuario")
    readonly_fields = fields
    ordering = ("-fecha",)
    verbose_name_plural = "historial de inventario (últimos movimientos)"

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("usuario")


@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ("miniatura", "nombre", "categoria", "precio", "oferta", "existencias", "activo", "destacado")
    list_display_links = ("miniatura", "nombre")
    list_editable = ("activo", "destacado")
    list_filter = ("categoria", StockFiltro, "activo", "destacado", "valores__atributo")
    search_fields = ("nombre", "resumen", "ingredientes")
    list_select_related = ("categoria",)
    list_per_page = 40
    filter_horizontal = ("valores",)
    readonly_fields = ("vista_imagen", "creado", "actualizado")
    inlines = [MovimientoInline]
    actions = ["mostrar", "ocultar"]
    fieldsets = (
        ("Producto", {"fields": ("categoria", "nombre", "slug", "resumen", "descripcion", "ingredientes")}),
        ("Precio", {"fields": ("precio", "precio_anterior")}),
        ("Inventario", {"fields": ("stock", "stock_minimo"),
                        "description": "Cada cambio de existencias queda registrado en el historial de abajo."}),
        ("Filtros de búsqueda", {"fields": ("valores",),
                                 "description": "Proteína, carbohidrato, verduras... Crea nuevas opciones en "
                                                "«Grupos de filtros»."}),
        ("Información nutricional (por porción)", {"fields": (
            ("peso_g", "calorias"), ("proteinas_g", "carbohidratos_g", "grasas_g"), "alergenos", "conservacion")}),
        ("Imagen", {"fields": ("imagen", "vista_imagen")}),
        ("Publicación", {"fields": ("activo", "destacado", "orden", "creado", "actualizado")}),
    )
    prepopulated_fields = {"slug": ("nombre",)}

    @admin.display(description="")
    def miniatura(self, obj):
        if obj.imagen_chica:
            return format_html('<img src="{}" alt="" style="width:56px;height:42px;object-fit:cover;border-radius:4px">',
                               obj.imagen_chica.url)
        return "—"

    @admin.display(description="vista previa")
    def vista_imagen(self, obj):
        if obj and obj.imagen_grande:
            return format_html('<img src="{}" alt="" style="max-width:320px;border-radius:6px">', obj.imagen_grande.url)
        return "Se mostrará al guardar."

    @admin.display(description="existencias", ordering="stock")
    def existencias(self, obj):
        color = "#b42318" if obj.stock == 0 else ("#b54708" if obj.stock_bajo else "#3f7a24")
        return format_html('<strong style="color:{}">{}</strong>', color, obj.stock)

    @admin.display(description="oferta", boolean=True)
    def oferta(self, obj):
        return obj.en_oferta

    def get_readonly_fields(self, request, obj=None):
        campos = list(super().get_readonly_fields(request, obj))
        if not request.user.has_perm("catalogo.ajustar_stock"):
            campos.append("stock")
        return campos

    def save_model(self, request, obj, form, change):
        """El stock no se escribe directo: se registra como movimiento para tener historial."""
        if "stock" not in form.changed_data:
            super().save_model(request, obj, form, change)
            return
        nuevo = obj.stock
        anterior = Producto.objects.filter(pk=obj.pk).values_list("stock", flat=True).first() if change else 0
        obj.stock = anterior or 0
        super().save_model(request, obj, form, change)
        diferencia = nuevo - obj.stock
        if diferencia:
            tipo = MovimientoInventario.ENTRADA if not change else MovimientoInventario.AJUSTE
            registrar_movimiento(obj.pk, diferencia, tipo,
                                 motivo="Stock inicial" if not change else "Ajuste desde la ficha del producto",
                                 usuario=request.user)
            obj.stock = nuevo

    @admin.action(description="Mostrar en la tienda")
    def mostrar(self, request, qs):
        n = qs.update(activo=True)
        self.message_user(request, f"{n} productos visibles.")

    @admin.action(description="Ocultar de la tienda")
    def ocultar(self, request, qs):
        n = qs.update(activo=False)
        self.message_user(request, f"{n} productos ocultos.")


class MovimientoForm(forms.ModelForm):
    class Meta:
        model = MovimientoInventario
        fields = ("producto", "tipo", "cantidad", "motivo")

    def clean(self):
        datos = super().clean()
        producto, tipo, cantidad = datos.get("producto"), datos.get("tipo"), datos.get("cantidad")
        if producto is None or cantidad is None:
            return datos
        if cantidad == 0:
            self.add_error("cantidad", "La cantidad no puede ser 0.")
        efectivo = _cantidad_efectiva(tipo, cantidad)
        if producto.stock + efectivo < 0:
            self.add_error("cantidad", f"Solo hay {producto.stock} unidades de {producto.nombre}.")
        if tipo in (MovimientoInventario.MERMA, MovimientoInventario.AJUSTE) and not datos.get("motivo"):
            self.add_error("motivo", "Explica el motivo de la merma o del ajuste.")
        return datos


def _cantidad_efectiva(tipo, cantidad):
    if tipo == MovimientoInventario.MERMA:
        return -abs(cantidad)
    if tipo == MovimientoInventario.ENTRADA:
        return abs(cantidad)
    return cantidad


@admin.register(MovimientoInventario)
class MovimientoInventarioAdmin(admin.ModelAdmin):
    """Entradas de producción, mermas y ajustes. Los movimientos no se editan ni se borran."""

    list_display = ("fecha", "producto", "tipo", "cantidad_signo", "stock_resultante", "motivo", "pedido", "usuario")
    list_filter = ("tipo", "producto__categoria", "fecha")
    search_fields = ("producto__nombre", "motivo", "pedido__codigo")
    date_hierarchy = "fecha"
    autocomplete_fields = ("producto",)
    list_select_related = ("producto", "pedido", "usuario")
    form = MovimientoForm
    fields = ("producto", "tipo", "cantidad", "motivo")

    @admin.display(description="cantidad", ordering="cantidad")
    def cantidad_signo(self, obj):
        color = "#3f7a24" if obj.cantidad > 0 else "#b42318"
        return format_html('<strong style="color:{}">{}{}</strong>', color, "+" if obj.cantidad > 0 else "",
                           obj.cantidad)

    def formfield_for_choice_field(self, db_field, request, **kwargs):
        if db_field.name == "tipo":
            kwargs["choices"] = [c for c in MovimientoInventario.TIPOS
                                 if c[0] in (MovimientoInventario.ENTRADA, MovimientoInventario.MERMA,
                                             MovimientoInventario.AJUSTE)]
        return super().formfield_for_choice_field(db_field, request, **kwargs)

    def save_model(self, request, obj, form, change):
        mov = registrar_movimiento(obj.producto_id, _cantidad_efectiva(obj.tipo, obj.cantidad), obj.tipo,
                                   obj.motivo, usuario=request.user)
        obj.pk, obj.cantidad, obj.stock_resultante = mov.pk, mov.cantidad, mov.stock_resultante

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Promocion)
class PromocionAdmin(admin.ModelAdmin):
    list_display = ("titulo", "porcentaje", "activa", "actualizado")
    filter_horizontal = ("categorias_requeridas",)
