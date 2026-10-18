import re

from django.core.exceptions import ValidationError


class ContrasenaFuerteValidator:
    """Exige mayúscula, minúscula, número y símbolo (además del largo mínimo de 10)."""

    reglas = [
        (r"[A-ZÁÉÍÓÚÑ]", "una letra mayúscula"),
        (r"[a-záéíóúñ]", "una letra minúscula"),
        (r"\d", "un número"),
        (r"[^\w\s]|_", "un símbolo (por ejemplo ! # $ % *)"),
    ]

    def validate(self, password, user=None):
        faltan = [texto for patron, texto in self.reglas if not re.search(patron, password)]
        if faltan:
            raise ValidationError(
                "La contraseña debe incluir " + ", ".join(faltan) + ".",
                code="contrasena_debil",
            )
        if re.search(r"(.)\1\1\1", password):
            raise ValidationError("La contraseña no puede repetir el mismo carácter 4 veces seguidas.",
                                  code="contrasena_repetida")

    def get_help_text(self):
        return "Usa al menos 10 caracteres con mayúscula, minúscula, número y símbolo."
