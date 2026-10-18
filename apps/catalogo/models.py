from decimal import Decimal
from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.validators import MinValueValidator
from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from PIL import Image, ImageOps


class Categoria(models.Model):
    """Cada apartado de la tienda: Platos fuertes, Mise en place, Combos..."""

    nombre = models.CharField(max_length=60, unique=True)
    slug = models.SlugField(max_length=60, unique=True,
                            help_text="Parte de la dirección web, por ejemplo: platos-fuertes")
    titulo = models.CharField("título de la página", max_length=120)
    descripcion = models.CharField("texto de presentación", max_length=300, blank=True)
    orden = models.PositiveSmallIntegerField(default=0)
    cuenta_capacidad = models.BooleanField(
        "cuenta para la capacidad diaria", default=False,
        help_text="Márcalo si cada unidad es una comida preparada en cocina (platos fuertes, combos de comida).")

    class Meta:
        ordering = ["orden", "nombre"]
        verbose_name = "categoría"
        verbose_name_plural = "categorías"

    def __str__(self):
        return self.nombre

    def get_absolute_url(self):
        return reverse("catalogo:categoria", args=[self.slug])


class Atributo(models.Model):
    """Grupo de filtros: Proteína, Carbohidrato, Verduras, Preferencia..."""

    nombre = models.CharField(max_length=40, unique=True)
    slug = models.SlugField(max_length=40, unique=True,
                            help_text="Nombre corto que aparece en la dirección al filtrar, por ejemplo: proteina")
    orden = models.PositiveSmallIntegerField(default=0)

    class Meta:
        ordering = ["orden", "nombre"]
        verbose_name = "grupo de filtros"
        verbose_name_plural = "grupos de filtros"

    def __str__(self):
        return self.nombre


class ValorAtributo(models.Model):
    """Una opción de filtro: Res, Cerdo, Pollo, Quinua, Arroz..."""

    atributo = models.ForeignKey(Atributo, on_delete=models.CASCADE, related_name="valores")
    nombre = models.CharField(max_length=40)
    slug = models.SlugField(max_length=40)

    class Meta:
        ordering = ["atributo__orden", "nombre"]
        unique_together = [("atributo", "slug")]
        verbose_name = "opción de filtro"
        verbose_name_plural = "opciones de filtro"

    def __str__(self):
        return f"{self.atributo.nombre}: {self.nombre}"

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.nombre)
        super().save(*args, **kwargs)


def _ruta_imagen(instancia, archivo):
    return f"productos/{slugify(instancia.nombre)[:50]}{Path(archivo).suffix.lower()}"


class ProductoQuerySet(models.QuerySet):
    def visibles(self):
        return self.filter(activo=True, categoria__isnull=False)

    def en_oferta(self):
        return self.filter(precio_anterior__isnull=False, precio_anterior__gt=models.F("precio"))


class Producto(models.Model):
    categoria = models.ForeignKey(Categoria, on_delete=models.PROTECT, related_name="productos")
    nombre = models.CharField(max_length=90)
    slug = models.SlugField(max_length=100, unique=True, blank=True)
    resumen = models.CharField(max_length=160, help_text="Se muestra al pasar el cursor sobre la foto.")
    descripcion = models.TextField("descripción detallada",
                                   help_text="Se muestra al hacer clic en la foto. Dos o tres frases.")
    ingredientes = models.CharField(max_length=300, blank=True)
    precio = models.DecimalField(max_digits=8, decimal_places=2, validators=[MinValueValidator(Decimal("0.01"))])
    precio_anterior = models.DecimalField(
        "precio antes de la promoción", max_digits=8, decimal_places=2, null=True, blank=True,
        help_text="Si lo llenas y es mayor al precio, el producto aparece en Combos y promociones.")
    stock = models.PositiveIntegerField("existencias", default=0)
    stock_minimo = models.PositiveIntegerField("aviso de stock bajo", default=5)

    # Información nutricional por porción (diferencia de la marca)
    peso_g = models.PositiveIntegerField("peso (g)", null=True, blank=True)
    calorias = models.PositiveIntegerField("calorías (kcal)", null=True, blank=True)
    proteinas_g = models.DecimalField("proteínas (g)", max_digits=5, decimal_places=1, null=True, blank=True)
    carbohidratos_g = models.DecimalField("carbohidratos (g)", max_digits=5, decimal_places=1, null=True, blank=True)
    grasas_g = models.DecimalField("grasas (g)", max_digits=5, decimal_places=1, null=True, blank=True)
    alergenos = models.CharField("alérgenos", max_length=120, blank=True)
    conservacion = models.CharField("conservación", max_length=160, blank=True,
                                    default="Refrigerar entre 0 y 4 °C. Consumir en máximo 4 días.")

    valores = models.ManyToManyField(ValorAtributo, blank=True, related_name="productos",
                                     verbose_name="filtros (proteína, carbohidrato...)")

    imagen = models.ImageField(upload_to=_ruta_imagen,
                               help_text="JPG, PNG o WEBP. Se crean versiones livianas automáticamente.")
    imagen_chica = models.ImageField(upload_to="productos/480/", editable=False, blank=True)
    imagen_grande = models.ImageField(upload_to="productos/960/", editable=False, blank=True)
    imagen_ancho = models.PositiveIntegerField(default=960, editable=False)
    imagen_alto = models.PositiveIntegerField(default=720, editable=False)

    activo = models.BooleanField("visible en la tienda", default=True)
    destacado = models.BooleanField(default=False, help_text="Aparece en la página principal.")
    orden = models.PositiveSmallIntegerField(default=0)
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    objects = ProductoQuerySet.as_manager()

    class Meta:
        ordering = ["orden", "nombre"]
        verbose_name = "producto"
        verbose_name_plural = "productos"
        indexes = [models.Index(fields=["categoria", "activo", "orden"])]
        permissions = [("ajustar_stock", "Puede ajustar existencias")]

    def __str__(self):
        return self.nombre

    def get_absolute_url(self):
        return reverse("catalogo:producto", args=[self.slug])

    @property
    def en_oferta(self):
        return self.precio_anterior is not None and self.precio_anterior > self.precio

    @property
    def ahorro_porcentaje(self):
        if not self.en_oferta:
            return 0
        return round((1 - self.precio / self.precio_anterior) * 100)

    @property
    def agotado(self):
        return self.stock == 0

    @property
    def stock_bajo(self):
        return 0 < self.stock <= self.stock_minimo

    def save(self, *args, **kwargs):
        if not self.slug:
            base = slugify(self.nombre)[:90] or "producto"
            slug, n = base, 2
            while Producto.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug, n = f"{base}-{n}", n + 1
            self.slug = slug
        imagen_cambio = self._imagen_cambio()
        super().save(*args, **kwargs)
        if imagen_cambio and self.imagen:
            self.generar_versiones()

    def _imagen_cambio(self):
        if not self.pk:
            return True
        anterior = Producto.objects.filter(pk=self.pk).values_list("imagen", flat=True).first()
        return anterior != self.imagen.name or not self.imagen_chica

    def generar_versiones(self):
        """Crea dos versiones WebP (480 y 960 px) para que el celular descargue la pequeña."""
        self.imagen.open("rb")
        with Image.open(self.imagen) as original:
            original = ImageOps.exif_transpose(original).convert("RGB")
            nombre = Path(self.imagen.name).stem
            for ancho, campo in ((480, "imagen_chica"), (960, "imagen_grande")):
                copia = original.copy()
                if copia.width > ancho:
                    copia = copia.resize((ancho, round(copia.height * ancho / copia.width)), Image.LANCZOS)
                if campo == "imagen_grande":
                    self.imagen_ancho, self.imagen_alto = copia.size
                buffer = BytesIO()
                copia.save(buffer, "WEBP", quality=80, method=6)
                viejo = getattr(self, campo)
                if viejo:
                    viejo.delete(save=False)
                getattr(self, campo).save(f"{nombre}.webp", ContentFile(buffer.getvalue()), save=False)
        self.imagen.close()
        Producto.objects.filter(pk=self.pk).update(
            imagen_chica=self.imagen_chica.name, imagen_grande=self.imagen_grande.name,
            imagen_ancho=self.imagen_ancho, imagen_alto=self.imagen_alto)


class MovimientoInventario(models.Model):
    """Registro de cada entrada o salida de stock. El stock del producto es el resultado de estos movimientos."""

    ENTRADA = "ENTRADA"
    VENTA = "VENTA"
    AJUSTE = "AJUSTE"
    DEVOLUCION = "DEVOLUCION"
    MERMA = "MERMA"
    TIPOS = [
        (ENTRADA, "Entrada (producción o compra)"),
        (VENTA, "Salida por venta"),
        (DEVOLUCION, "Devolución por pedido cancelado"),
        (MERMA, "Merma (vencido o dañado)"),
        (AJUSTE, "Ajuste manual"),
    ]

    producto = models.ForeignKey(Producto, on_delete=models.CASCADE, related_name="movimientos")
    tipo = models.CharField(max_length=12, choices=TIPOS)
    cantidad = models.IntegerField(help_text="Positivo suma al stock, negativo resta.")
    stock_resultante = models.PositiveIntegerField(editable=False)
    motivo = models.CharField(max_length=200, blank=True)
    pedido = models.ForeignKey("pedidos.Pedido", on_delete=models.SET_NULL, null=True, blank=True,
                               related_name="movimientos")
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True,
                                related_name="+", verbose_name="registrado por")
    fecha = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-fecha"]
        verbose_name = "movimiento de inventario"
        verbose_name_plural = "movimientos de inventario"

    def __str__(self):
        signo = "+" if self.cantidad > 0 else ""
        return f"{self.producto} {signo}{self.cantidad} ({self.get_tipo_display()})"


class Promocion(models.Model):
    """Ventana flotante de registro: descuento en el primer pedido con plato fuerte + mise en place."""

    titulo = models.CharField("título", max_length=80)
    mensaje = models.CharField(max_length=260)
    porcentaje = models.PositiveSmallIntegerField(validators=[MinValueValidator(1)],
                                                  help_text="Descuento que recibe el cliente nuevo.")
    categorias_requeridas = models.ManyToManyField(
        Categoria, blank=True, verbose_name="el pedido debe incluir",
        help_text="El descuento aplica solo si el pedido tiene al menos un producto de cada categoría marcada.")
    imagen = models.ImageField(upload_to="promociones/")
    activa = models.BooleanField(default=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "promoción de bienvenida"
        verbose_name_plural = "promoción de bienvenida"

    def __str__(self):
        return self.titulo

    @classmethod
    def bienvenida_activa(cls):
        return cls.objects.filter(activa=True).prefetch_related("categorias_requeridas").order_by("-actualizado").first()
