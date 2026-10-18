"""
Configuración de DeliPack.

Todo lo que cambia entre tu computador y el servidor publicado se lee de
variables de entorno (archivo .env). Ver .env.example.
"""
import os
from pathlib import Path

from django.core.exceptions import ImproperlyConfigured

BASE_DIR = Path(__file__).resolve().parent.parent


def env(nombre, defecto=None):
    return os.environ.get(nombre, defecto)


def env_bool(nombre, defecto=False):
    return env(nombre, str(defecto)).strip().lower() in {"1", "true", "si", "sí", "yes", "on"}


def env_lista(nombre, defecto=""):
    return [x.strip() for x in env(nombre, defecto).split(",") if x.strip()]


DEBUG = env_bool("DEBUG", False)

SECRET_KEY = env("SECRET_KEY")
if not SECRET_KEY:
    if DEBUG:
        SECRET_KEY = "solo-para-desarrollo-cambiar-en-produccion"
    else:
        raise ImproperlyConfigured("Define SECRET_KEY en el archivo .env")

ALLOWED_HOSTS = env_lista("ALLOWED_HOSTS", "localhost,127.0.0.1")
# El chequeo de salud de Docker llama desde dentro del contenedor
ALLOWED_HOSTS += [h for h in ("localhost", "127.0.0.1") if h not in ALLOWED_HOSTS]
CSRF_TRUSTED_ORIGINS = env_lista("CSRF_TRUSTED_ORIGINS", "http://localhost,http://127.0.0.1")

# URL del panel de administración (cámbiala al publicar para que no sea obvia)
ADMIN_URL = env("ADMIN_URL", "admin/").strip("/") + "/"

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "django.contrib.humanize",
    "apps.cuentas",
    "apps.catalogo",
    "apps.pedidos",
    "apps.paginas",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "whitenoise.middleware.WhiteNoiseMiddleware",
    "django.middleware.gzip.GZipMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
    "apps.paginas.middleware.CabecerasSeguridadMiddleware",
]

ROOT_URLCONF = "config.urls"
WSGI_APPLICATION = "config.wsgi.application"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
                "apps.pedidos.context_processors.carrito",
                "apps.paginas.context_processors.sitio",
            ],
        },
    }
]

# ---------- Base de datos: PostgreSQL ----------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.postgresql",
        "NAME": env("DB_NAME", "delipack"),
        "USER": env("DB_USER", "delipack"),
        "PASSWORD": env("DB_PASSWORD", "delipack"),
        "HOST": env("DB_HOST", "localhost"),
        "PORT": env("DB_PORT", "5432"),
        # Reutiliza conexiones entre peticiones (menos tiempo por consulta)
        "CONN_MAX_AGE": int(env("DB_CONN_MAX_AGE", "60")),
        "CONN_HEALTH_CHECKS": True,
    }
}

# Caché compartida en la base de datos (sirve para limitar intentos de inicio de sesión
# entre varios procesos). Para crecer, se cambia por Redis sin tocar el código.
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.db.DatabaseCache",
        "LOCATION": "cache_delipack",
    }
}

# ---------- Usuarios y contraseñas ----------
AUTH_USER_MODEL = "cuentas.Usuario"
LOGIN_URL = "cuentas:ingresar"
LOGIN_REDIRECT_URL = "paginas:inicio"
LOGOUT_REDIRECT_URL = "paginas:inicio"

# Argon2 es el algoritmo recomendado hoy para guardar contraseñas (hash con sal)
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.Argon2PasswordHasher",
    "django.contrib.auth.hashers.PBKDF2PasswordHasher",
]

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator",
     "OPTIONS": {"user_attributes": ("email", "nombres", "apellidos")}},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator", "OPTIONS": {"min_length": 10}},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
    {"NAME": "apps.cuentas.validadores.ContrasenaFuerteValidator"},
]

# Inicio de sesión: intentos fallidos permitidos antes de bloquear temporalmente
LOGIN_MAX_INTENTOS = int(env("LOGIN_MAX_INTENTOS", "5"))
LOGIN_BLOQUEO_MINUTOS = int(env("LOGIN_BLOQUEO_MINUTOS", "15"))
# Validez del enlace de verificación de correo y de recuperación de contraseña
PASSWORD_RESET_TIMEOUT = 60 * 60 * 24  # 24 horas

# ---------- Sesiones ----------
SESSION_ENGINE = "django.contrib.sessions.backends.cached_db"
SESSION_COOKIE_AGE = 60 * 60 * 24 * 14  # el carrito de visitantes dura 14 días
SESSION_COOKIE_HTTPONLY = True
SESSION_COOKIE_SAMESITE = "Lax"
CSRF_COOKIE_SAMESITE = "Lax"

# ---------- Correo ----------
# En desarrollo los correos se imprimen en la terminal. Al publicar, configura SMTP en .env
EMAIL_BACKEND = env("EMAIL_BACKEND", "django.core.mail.backends.console.EmailBackend")
EMAIL_HOST = env("EMAIL_HOST", "")
EMAIL_PORT = int(env("EMAIL_PORT", "587"))
EMAIL_HOST_USER = env("EMAIL_HOST_USER", "")
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", "")
EMAIL_USE_TLS = env_bool("EMAIL_USE_TLS", True)
DEFAULT_FROM_EMAIL = env("DEFAULT_FROM_EMAIL", "DeliPack <no-responder@delipack.ec>")
SERVER_EMAIL = DEFAULT_FROM_EMAIL

# ---------- Idioma y zona horaria ----------
LANGUAGE_CODE = "es-ec"
TIME_ZONE = "America/Guayaquil"
USE_I18N = True
USE_TZ = True

# ---------- Archivos estáticos (CSS, JS, fuentes) y subidos (fotos de productos) ----------
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
STATICFILES_DIRS = [BASE_DIR / "static"]
MEDIA_URL = "/media/"
MEDIA_ROOT = Path(env("MEDIA_ROOT", str(BASE_DIR / "media")))
# Si no hay nginx delante (por ejemplo, un hosting simple), Django sirve /media/
SERVIR_MEDIA = env_bool("SERVIR_MEDIA", DEBUG)

STORAGES = {
    "default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
    # Archivos con huella en el nombre + gzip: el navegador los guarda en caché por un año
    "staticfiles": {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"},
}
WHITENOISE_MAX_AGE = 60 * 60 * 24 * 365

DATA_UPLOAD_MAX_MEMORY_SIZE = 6 * 1024 * 1024
FILE_UPLOAD_MAX_MEMORY_SIZE = 6 * 1024 * 1024

DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------- Seguridad al publicar (HTTPS) ----------
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_REFERRER_POLICY = "strict-origin-when-cross-origin"
X_FRAME_OPTIONS = "DENY"
if not DEBUG:
    SESSION_COOKIE_SECURE = env_bool("COOKIES_SEGURAS", True)
    CSRF_COOKIE_SECURE = env_bool("COOKIES_SEGURAS", True)
    SECURE_SSL_REDIRECT = env_bool("FORZAR_HTTPS", True)
    SECURE_PROXY_SSL_HEADER = ("HTTP_X_FORWARDED_PROTO", "https")
    SECURE_HSTS_SECONDS = int(env("HSTS_SEGUNDOS", "31536000"))
    SECURE_HSTS_INCLUDE_SUBDOMAINS = True
    SECURE_HSTS_PRELOAD = False
    SECURE_REDIRECT_EXEMPT = [r"^salud/$"]

LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "handlers": {"consola": {"class": "logging.StreamHandler"}},
    "root": {"handlers": ["consola"], "level": "INFO"},
    "loggers": {"django.db.backends": {"level": "WARNING"}},
}

# ---------- Datos del negocio ----------
NEGOCIO = {
    "nombre": "DeliPack",
    "lema": "Empacar sabor y entregar felicidad",
    "ciudad": "Tulcán, Ecuador",
    "telefono": env("NEGOCIO_TELEFONO", "+593 99 000 0000"),
    "correo": env("NEGOCIO_CORREO", "pedidos@delipack.ec"),
    "banco": env("NEGOCIO_BANCO", "Banco Pichincha · Cta. de ahorros 0000000000 · DeliPack"),
}
