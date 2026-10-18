from decimal import Decimal

from django.conf import settings
from django.core.validators import MinValueValidator
from django.db import models


class ConfiguracionNegocio(models.Model):
    """Ajustes que el administrador cambia sin tocar código (solo existe una fila)."""

    capacidad_diaria = models.PositiveIntegerField(
        "comidas por día", default=30,
        help_text="Máximo de comidas preparadas que la cocina puede entregar en un día.")
    anticipacion_dias = models.PositiveSmallIntegerField(
        "días de anticipación", default=1, help_text="1 = el pedido se entrega desde mañana.")
    dias_a_mostrar = models.PositiveSmallIntegerField("días disponibles para elegir", default=10)
    costo_envio = models.DecimalField("costo de entrega (USD)", max_digits=6, decimal_places=2,
                                      default=Decimal("0.00"))
    datos_transferencia = models.CharField(
        "datos para transferencia", max_length=200,
        default="Banco Pichincha, cuenta de ahorros 0000000000, a nombre de DeliPack")

    class Meta:
        verbose_name = "configuración del negocio"
        verbose_name_plural = "configuración del negocio"

    def __str__(self):
        return "Configuración del negocio"

    @classmethod
    def actual(cls):
        obj, _ = cls.objects.get_or_create(pk=1)
        return obj


class CarritoItem(models.Model):
    """Carrito guardado en la base de datos para clientes con sesión (se conserva entre dispositivos)."""

    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="carrito")
    producto = models.ForeignKey("catalogo.Producto", on_delete=models.CASCADE, related_name="+")
    cantidad = models.PositiveSmallIntegerField(default=1)
    agregado = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("usuario", "producto")]
        verbose_name = "producto en carrito"
        verbose_name_plural = "carritos guardados"


class Pedido(models.Model):
    class Estado(models.TextChoices):
        PENDIENTE = "PENDIENTE", "Recibido"
        CONFIRMADO = "CONFIRMADO", "Confirmado"
        PREPARANDO = "PREPARANDO", "En preparación"
        EN_CAMINO = "EN_CAMINO", "En camino"
        ENTREGADO = "ENTREGADO", "Entregado"
        CANCELADO = "CANCELADO", "Cancelado"

    class TipoEntrega(models.TextChoices):
        OFICINA = "OFICINA", "Entrega en oficina"
        HOGAR = "HOGAR", "Entrega en domicilio"
        RETIRO = "RETIRO", "Retiro en el local"

    class Franja(models.TextChoices):
        ALMUERZO = "ALMUERZO", "Almuerzo (11:30 a 13:00)"
        CENA = "CENA", "Cena (18:00 a 19:30)"

    class MetodoPago(models.TextChoices):
        EFECTIVO = "EFECTIVO", "Efectivo al recibir"
        TRANSFERENCIA = "TRANSFERENCIA", "Transferencia bancaria"
        TARJETA = "TARJETA", "Tarjeta al recibir (datáfono)"

    codigo = models.CharField(max_length=12, unique=True, editable=False)
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="pedidos")
    estado = models.CharField(max_length=12, choices=Estado.choices, default=Estado.PENDIENTE, db_index=True)

    tipo_entrega = models.CharField("entrega", max_length=10, choices=TipoEntrega.choices)
    direccion = models.CharField("dirección", max_length=200, blank=True)
    referencia = models.CharField(max_length=160, blank=True)
    telefono = models.CharField("celular", max_length=20)
    fecha_entrega = models.DateField(db_index=True)
    franja = models.CharField("horario", max_length=10, choices=Franja.choices)
    metodo_pago = models.CharField("forma de pago", max_length=15, choices=MetodoPago.choices)
    pagado = models.BooleanField(default=False)
    referencia_pago = models.CharField("n.º de comprobante", max_length=60, blank=True)
    notas = models.CharField(max_length=300, blank=True)

    subtotal = models.DecimalField(max_digits=9, decimal_places=2)
    descuento = models.DecimalField(max_digits=9, decimal_places=2, default=Decimal("0.00"))
    descuento_porcentaje = models.PositiveSmallIntegerField(default=0)
    envio = models.DecimalField(max_digits=7, decimal_places=2, default=Decimal("0.00"))
    total = models.DecimalField(max_digits=9, decimal_places=2)

    creado = models.DateTimeField(auto_now_add=True, db_index=True)
    actualizado = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-creado"]
        verbose_name = "pedido"
        verbose_name_plural = "pedidos"
        indexes = [models.Index(fields=["fecha_entrega", "estado"])]

    def __str__(self):
        return self.codigo

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if not self.codigo:
            self.codigo = f"DP-{self.pk:06d}"
            Pedido.objects.filter(pk=self.pk).update(codigo=self.codigo)


class PedidoItem(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name="items")
    producto = models.ForeignKey("catalogo.Producto", on_delete=models.SET_NULL, null=True, related_name="+")
    # Copia del nombre y precio al momento de la compra
    nombre = models.CharField(max_length=90)
    precio_unitario = models.DecimalField(max_digits=8, decimal_places=2)
    cantidad = models.PositiveSmallIntegerField(validators=[MinValueValidator(1)])
    subtotal = models.DecimalField(max_digits=9, decimal_places=2)
    cuenta_capacidad = models.BooleanField(default=False, editable=False)

    class Meta:
        verbose_name = "producto del pedido"
        verbose_name_plural = "productos del pedido"

    def __str__(self):
        return f"{self.nombre} × {self.cantidad}"
