#!/bin/sh
# Prepara la base de datos y arranca Gunicorn. Se ejecuta cada vez que inicia el contenedor.
set -e

python manage.py collectstatic --noinput -v0
python manage.py migrate --noinput
python manage.py createcachetable
python manage.py configurar_grupos
python manage.py cargar_catalogo

# Crea el administrador principal la primera vez (si se definieron las variables)
if [ -n "$DJANGO_SUPERUSER_EMAIL" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
  python manage.py createsuperuser --noinput --email "$DJANGO_SUPERUSER_EMAIL" --nombres "Administración" 2>/dev/null \
    && echo "Administrador creado: $DJANGO_SUPERUSER_EMAIL" || true
fi

# Procesos = 2 x núcleos + 1 es la regla habitual; se ajusta con GUNICORN_WORKERS
exec gunicorn config.wsgi:application \
  --bind 0.0.0.0:8000 \
  --workers "${GUNICORN_WORKERS:-3}" \
  --threads "${GUNICORN_THREADS:-2}" \
  --worker-class gthread \
  --timeout 30 \
  --access-logfile - \
  --forwarded-allow-ips "*"
