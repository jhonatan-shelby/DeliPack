from django import forms
from django.contrib.auth import authenticate, password_validation
from django.core.cache import cache
from django.conf import settings

from .models import Usuario

# Dominios de correos temporales que no se aceptan
DOMINIOS_TEMPORALES = {
    "mailinator.com", "10minutemail.com", "guerrillamail.com", "tempmail.com", "temp-mail.org",
    "yopmail.com", "trashmail.com", "sharklasers.com", "getnada.com", "dispostable.com",
}


class RegistroForm(forms.Form):
    nombres = forms.CharField(max_length=80, widget=forms.TextInput(attrs={"autocomplete": "given-name"}))
    apellidos = forms.CharField(max_length=80, widget=forms.TextInput(attrs={"autocomplete": "family-name"}))
    email = forms.EmailField(label="Correo", max_length=254,
                             widget=forms.EmailInput(attrs={"autocomplete": "email"}))
    telefono = forms.CharField(label="Celular", max_length=20, required=False,
                               widget=forms.TextInput(attrs={"autocomplete": "tel", "inputmode": "tel"}))
    password1 = forms.CharField(label="Contraseña", strip=False,
                                widget=forms.PasswordInput(attrs={"autocomplete": "new-password",
                                                                  "data-fuerza": "true"}))
    password2 = forms.CharField(label="Repite la contraseña", strip=False,
                                widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}))
    acepta = forms.BooleanField(label="Acepto que DeliPack use mis datos para gestionar mis pedidos")

    def clean_email(self):
        email = self.cleaned_data["email"].strip().lower()
        dominio = email.rsplit("@", 1)[-1]
        if "." not in dominio:
            raise forms.ValidationError("Escribe un correo completo, por ejemplo nombre@gmail.com.")
        if dominio in DOMINIOS_TEMPORALES:
            raise forms.ValidationError("No se aceptan correos temporales. Usa tu correo personal o del trabajo.")
        if Usuario.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("Ya existe una cuenta con este correo. Inicia sesión o recupera tu contraseña.")
        return email

    def clean_telefono(self):
        tel = self.cleaned_data.get("telefono", "").replace(" ", "")
        if tel and not tel.lstrip("+").isdigit():
            raise forms.ValidationError("El celular solo puede tener números.")
        if tel and not 9 <= len(tel.lstrip("+")) <= 13:
            raise forms.ValidationError("Revisa el número de celular.")
        return tel

    def clean(self):
        datos = super().clean()
        p1, p2 = datos.get("password1"), datos.get("password2")
        if p1 and p2 and p1 != p2:
            self.add_error("password2", "Las contraseñas no coinciden.")
        if p1:
            temporal = Usuario(email=datos.get("email", ""), nombres=datos.get("nombres", ""),
                               apellidos=datos.get("apellidos", ""))
            try:
                password_validation.validate_password(p1, temporal)
            except forms.ValidationError as e:
                self.add_error("password1", e)
        return datos

    def save(self):
        d = self.cleaned_data
        return Usuario.objects.create_user(
            email=d["email"], password=d["password1"], nombres=d["nombres"].strip(),
            apellidos=d["apellidos"].strip(), telefono=d.get("telefono", ""),
        )


def _ip(request):
    reenviada = request.META.get("HTTP_X_FORWARDED_FOR")
    return (reenviada.split(",")[0].strip() if reenviada else request.META.get("REMOTE_ADDR", "")) or "?"


class IngresoForm(forms.Form):
    """Inicio de sesión con bloqueo temporal tras varios intentos fallidos."""

    email = forms.EmailField(label="Correo", widget=forms.EmailInput(attrs={"autocomplete": "email", "autofocus": True}))
    password = forms.CharField(label="Contraseña", strip=False,
                               widget=forms.PasswordInput(attrs={"autocomplete": "current-password"}))

    def __init__(self, request, *args, **kwargs):
        self.request = request
        self.usuario = None
        super().__init__(*args, **kwargs)

    def _clave(self, email):
        return f"login-fallos:{email}:{_ip(self.request)}"

    def clean(self):
        datos = super().clean()
        email = (datos.get("email") or "").lower()
        password = datos.get("password")
        if not email or not password:
            return datos
        clave = self._clave(email)
        fallos = cache.get(clave, 0)
        if fallos >= settings.LOGIN_MAX_INTENTOS:
            raise forms.ValidationError(
                f"Demasiados intentos fallidos. Espera {settings.LOGIN_BLOQUEO_MINUTOS} minutos o recupera tu contraseña.",
                code="bloqueado")
        usuario = authenticate(self.request, email=email, password=password)
        if usuario is None:
            cache.set(clave, fallos + 1, settings.LOGIN_BLOQUEO_MINUTOS * 60)
            raise forms.ValidationError("Correo o contraseña incorrectos.", code="invalido")
        cache.delete(clave)
        self.usuario = usuario
        return datos


class PerfilForm(forms.ModelForm):
    class Meta:
        model = Usuario
        fields = ["nombres", "apellidos", "telefono"]
        labels = {"telefono": "Celular"}
