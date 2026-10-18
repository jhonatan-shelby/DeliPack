# Imagen de la aplicación DeliPack (Django + Gunicorn)
FROM python:3.13-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

# Archivos estáticos comprimidos y con huella en el nombre (caché de un año en el navegador)
RUN SECRET_KEY=solo-para-construir DEBUG=0 python manage.py collectstatic --noinput -v0 \
    && useradd --create-home --uid 1000 delipack \
    && mkdir -p /app/media \
    && chown -R delipack:delipack /app/media /app/staticfiles \
    && chmod +x /app/deploy/iniciar.sh

USER delipack
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/salud/')"
CMD ["/app/deploy/iniciar.sh"]
