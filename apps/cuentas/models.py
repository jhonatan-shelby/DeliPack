from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models
from django.utils import timezone


class UsuarioManager(BaseUserManager):
    use_in_migrations = True

    def _crear(self, email, password, **extra):
        if not email:
            raise ValueError("El correo es obligatorio")
        email = self.normalize_email(email).lower()
        usuario = self.model(email=email, **extra)
        usuario.set_password(password)
        usuario.save(using=self._db)
        return usuario

    def create_user(self, email, password=None, **extra):
        extra.setdefault("is_staff", False)
        extra.setdefault("is_superuser", False)
        return self._crear(email, password, **extra)

    def create_superuser(self, email, password=None, **extra):
        extra.setdefault("is_staff", True)
        extra.setdefault("is_superuser", True)
        extra.setdefault("email_verificado", True)
        extra.setdefault("nombres", "Administración")
        return self._crear(email, password, **extra)

    def get_by_natural_key(self, email):
        return self.get(email__iexact=email)


class Usuario(AbstractBaseUser, PermissionsMixin):
    """Usuario que inicia sesión con su correo. Sirve para clientes y para el personal."""

    email = models.EmailField("correo", unique=True, db_index=True)
    nombres = models.CharField(max_length=80)
    apellidos = models.CharField(max_length=80, blank=True)
    telefono = models.CharField("teléfono", max_length=20, blank=True)
    email_verificado = models.BooleanField("correo verificado", default=False)

    # Descuento de bienvenida asignado al registrarse (0 = sin descuento)
    descuento_bienvenida = models.PositiveSmallIntegerField("descuento de bienvenida (%)", default=0)
    descuento_usado = models.BooleanField("descuento usado", default=False)

    is_active = models.BooleanField("activo", default=True)
    is_staff = models.BooleanField(
        "acceso al panel", default=False,
        help_text="Permite entrar al panel de administración. Lo que puede hacer depende de sus grupos.",
    )
    fecha_registro = models.DateTimeField("registrado el", default=timezone.now)

    objects = UsuarioManager()

    USERNAME_FIELD = "email"
    EMAIL_FIELD = "email"
    REQUIRED_FIELDS = ["nombres"]

    class Meta:
        verbose_name = "usuario"
        verbose_name_plural = "usuarios"
        ordering = ["-fecha_registro"]

    def __str__(self):
        return self.email

    def get_full_name(self):
        return f"{self.nombres} {self.apellidos}".strip()

    def get_short_name(self):
        return self.nombres.split(" ")[0] if self.nombres else self.email

    @property
    def tiene_descuento(self):
        return self.descuento_bienvenida > 0 and not self.descuento_usado
