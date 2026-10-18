from django.contrib.auth.tokens import PasswordResetTokenGenerator


class TokenVerificacionCorreo(PasswordResetTokenGenerator):
    """Token firmado con SECRET_KEY. Deja de servir apenas el correo queda verificado."""

    key_salt = "delipack.verificacion-correo"

    def _make_hash_value(self, user, timestamp):
        return f"{user.pk}{user.email}{user.email_verificado}{timestamp}"


token_verificacion = TokenVerificacionCorreo()
