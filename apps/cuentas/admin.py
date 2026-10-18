from django import forms
from django.contrib import admin
from django.contrib.auth import password_validation
from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.forms import ReadOnlyPasswordHashField

from .models import Usuario


class CrearUsuarioForm(forms.ModelForm):
    password1 = forms.CharField(label="Contraseña", widget=forms.PasswordInput, strip=False,
                                help_text=password_validation.password_validators_help_text_html())
    password2 = forms.CharField(label="Repite la contraseña", widget=forms.PasswordInput, strip=False)

    class Meta:
        model = Usuario
        fields = ("email", "nombres", "apellidos")

    def clean_email(self):
        email = self.cleaned_data["email"].lower()
        if Usuario.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Ya existe un usuario con este correo.")
        return email

    def clean(self):
        datos = super().clean()
        if datos.get("password1") != datos.get("password2"):
            self.add_error("password2", "Las contraseñas no coinciden.")
        elif datos.get("password1"):
            try:
                password_validation.validate_password(datos["password1"], self.instance)
            except forms.ValidationError as e:
                self.add_error("password1", e)
        return datos

    def save(self, commit=True):
        usuario = super().save(commit=False)
        usuario.set_password(self.cleaned_data["password1"])
        usuario.email_verificado = True
        if commit:
            usuario.save()
        return usuario


class EditarUsuarioForm(forms.ModelForm):
    password = ReadOnlyPasswordHashField(
        label="Contraseña",
        help_text="La contraseña se guarda cifrada con Argon2 y nadie puede verla. "
                  "Usa el formulario de cambio de contraseña.")

    class Meta:
        model = Usuario
        fields = "__all__"


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    form = EditarUsuarioForm
    add_form = CrearUsuarioForm
    list_display = ("email", "nombre_completo", "email_verificado", "is_staff", "grupos", "fecha_registro")
    list_filter = ("is_staff", "is_active", "email_verificado", "groups")
    search_fields = ("email", "nombres", "apellidos", "telefono")
    ordering = ("-fecha_registro",)
    readonly_fields = ("fecha_registro", "last_login")
    fieldsets = (
        (None, {"fields": ("email", "password")}),
        ("Datos personales", {"fields": ("nombres", "apellidos", "telefono", "email_verificado")}),
        ("Descuento de bienvenida", {"fields": ("descuento_bienvenida", "descuento_usado")}),
        ("Permisos", {"fields": ("is_active", "is_staff", "is_superuser", "groups", "user_permissions"),
                      "description": "Para el personal: marca «acceso al panel» y asígnale un grupo "
                                     "(Gerencia, Inventario, Ventas o Atención al cliente)."}),
        ("Fechas", {"fields": ("last_login", "fecha_registro")}),
    )
    add_fieldsets = ((None, {"classes": ("wide",),
                             "fields": ("email", "nombres", "apellidos", "password1", "password2")}),)
    filter_horizontal = ("groups", "user_permissions")

    @admin.display(description="nombre")
    def nombre_completo(self, obj):
        return obj.get_full_name()

    @admin.display(description="grupos")
    def grupos(self, obj):
        return ", ".join(g.name for g in obj.groups.all()) or "—"

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("groups")

    def get_readonly_fields(self, request, obj=None):
        campos = list(super().get_readonly_fields(request, obj))
        # Solo un superusuario puede dar o quitar privilegios
        if not request.user.is_superuser:
            campos += ["is_staff", "is_superuser", "groups", "user_permissions"]
        return campos
