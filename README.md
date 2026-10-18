# DeliPack

Tienda en línea de DeliPack (Tulcán, Ecuador): platos fuertes listos para calentar, porciones de mise en place, combos y promociones, con carrito guardado, pago, inventario y panel de administración por permisos.

**Lema:** Empacar sabor y entregar felicidad.

## Cómo ejecutarla en tu computador

Necesitas **Docker Desktop**.

1. En la carpeta `delipack`, copia `.env.example` y renombra la copia a `.env`. Cambia por lo menos `SECRET_KEY`, `DB_PASSWORD` y `DJANGO_SUPERUSER_PASSWORD`.
2. Abre una terminal en la carpeta `delipack` y ejecuta:

   ```
   docker compose up --build
   ```

3. Abre **http://localhost:8080**. El panel está en **http://localhost:8080/admin/**, con el correo y la contraseña de `DJANGO_SUPERUSER_*`.

Para detenerla presiona `Ctrl + C`. Los contenedores tienen `restart: "no"`, así que **nunca arrancan solos** al encender el computador.

Los correos (verificación de cuenta, avisos de pedido) se muestran en la terminal mientras no configures SMTP. Para ver el enlace de verificación usa `docker compose logs web`.

### Sin Docker (para programar)

```
python -m venv venv
venv\Scripts\activate          (en Windows)
pip install -r requirements.txt
set DEBUG=1                    (en PowerShell: $env:DEBUG=1)
python manage.py migrate
python manage.py createcachetable
python manage.py configurar_grupos
python manage.py cargar_catalogo
python manage.py createsuperuser
python manage.py runserver
```

Necesita PostgreSQL en `localhost:5432`. Para levantar solo la base de datos: `docker compose up db`, y agrega `ports: ["5432:5432"]` al servicio `db`.

Para correr las pruebas automáticas: `python manage.py test apps`

## Apartados de la página

| Dirección | Contenido |
|---|---|
| `/` | Página principal: cómo nació, propósito, misión, visión y cómo funciona |
| `/platos-fuertes/` | Platos fuertes, con buscador y filtros |
| `/mise-en-place/` | Porciones de mise en place, con buscador y filtros |
| `/combos-y-promociones/` | Combos y cualquier producto con precio de oferta |
| `/pago/` | Carrito guardado, entrega, forma de pago y confirmación |
| `/cuentas/registro/`, `/cuentas/ingresar/`, `/cuentas/perfil/` | Cuenta del cliente y sus pedidos |
| `/admin/` | Panel de administración (cámbialo con `ADMIN_URL`) |

- **Al pasar el cursor** sobre la foto de un producto aparece un resumen corto.
- **Al hacer clic** en la foto se abre una ventana con la imagen más grande, la descripción, los ingredientes, los alérgenos y la tabla nutricional. En celular se toca la foto.
- **Filtros:** proteína (pollo, res, cerdo, pescado...), carbohidrato (quinua, arroz, galletas integrales...), verduras, tipo de porción y preferencia. Dentro de un grupo se suman (pollo **o** res) y entre grupos se combinan (pollo **y** quinua). Solo aparecen las opciones que existen en cada apartado.
- **Ventana flotante de registro:** invita a crear la cuenta con un 20 % en el primer pedido que incluya un plato fuerte y una porción de mise en place. Se edita desde el panel (texto, porcentaje, imagen, categorías requeridas y si está activa).

## Panel de administración y permisos

Es el panel de Django, con los colores de la marca. Al personal se le marca «acceso al panel» y se le asigna un grupo:

| Grupo | Puede |
|---|---|
| **Gerencia** | Todo el catálogo y el inventario, pedidos, promoción, configuración del negocio, ver y editar usuarios |
| **Inventario** | Crear y editar productos y filtros, registrar entradas, mermas y ajustes de stock, ver pedidos |
| **Ventas** | Ver y gestionar pedidos (confirmar, preparar, entregar, cancelar), editar la promoción, ver clientes |
| **Atención al cliente** | Solo ver pedidos, productos y clientes |

Solo un superusuario puede dar o quitar permisos. Los grupos se recrean con `python manage.py configurar_grupos`.

### Inventario

- El stock nunca se escribe "a mano": cada cambio queda como **movimiento de inventario** (entrada, venta, devolución, merma o ajuste), con quién lo hizo y el stock resultante. Los movimientos no se pueden editar ni borrar.
- Una venta descuenta el stock bloqueando la fila del producto (`SELECT ... FOR UPDATE`), así dos compras al mismo tiempo no pueden vender la misma unidad.
- Si un pedido se cancela, las existencias vuelven al inventario y, si se había usado, se devuelve el descuento de bienvenida.
- La portada del panel muestra los productos con stock bajo.
- En **Configuración del negocio** se ajustan la capacidad diaria (30 comidas), los días de anticipación, el costo de entrega y los datos para transferencias.

## Seguridad

| Medida | Dónde |
|---|---|
| Contraseñas guardadas con **Argon2** (hash con sal; nadie puede leerlas) | `config/settings.py`, `PASSWORD_HASHERS` |
| Contraseñas fuertes: 10 caracteres o más, mayúscula, minúscula, número y símbolo; no se aceptan contraseñas comunes ni parecidas al nombre o al correo | `apps/cuentas/validadores.py` |
| Verificación del correo con un enlace firmado que vale 24 horas; sin correo verificado no se puede pagar | `apps/cuentas/tokens.py` |
| Rechazo de correos temporales y de correos repetidos | `apps/cuentas/forms.py` |
| Bloqueo de 15 minutos tras 5 intentos fallidos de inicio de sesión | `apps/cuentas/forms.py` |
| Protección CSRF en todos los formularios y cookies `HttpOnly` y `SameSite` | Django |
| Política de seguridad de contenido (CSP): solo se ejecutan scripts propios | `apps/paginas/middleware.py` |
| HTTPS obligatorio, HSTS y cookies seguras al publicar | `FORZAR_HTTPS=1`, `COOKIES_SEGURAS=1` |
| No se guardan datos de tarjetas: se paga al recibir o por transferencia | `apps/pedidos` |

**Sobre "hashear la comunicación":** los datos entre el navegador y el servidor se protegen con **HTTPS (TLS)**, que cifra todo el tráfico. Hashear la contraseña en el navegador no agrega seguridad: ese hash se convertiría en la nueva contraseña. Por eso el hash (Argon2) se hace en el servidor y el transporte va cifrado con HTTPS.

## Rendimiento

- Las páginas se generan en el servidor: llegan listas para mostrarse, sin frameworks de JavaScript (un solo archivo de 6 KB).
- Una sola hoja de estilos (unos 7 KB comprimida) y dos fuentes locales.
- Cada foto subida se convierte a **WebP en 480 y 960 px**. El celular descarga la pequeña (`srcset`), con carga diferida (`loading="lazy"`) y tamaño reservado para que la página no salte.
- CSS y JS llevan una huella en el nombre y se guardan en caché un año. nginx los entrega comprimidos sin pasar por Django.
- Consultas optimizadas (`select_related`, `prefetch_related`, índices), conexiones reutilizadas y paginación de 24 productos.
- Medido en esta versión: unos 4–5 KB de HTML comprimido por página y LCP por debajo de 200 ms en local.

## Estructura (pensada para crecer)

```
delipack/
├── config/                 configuración (settings, urls, wsgi)
├── apps/
│   ├── cuentas/            usuario por correo, registro, verificación, permisos
│   ├── catalogo/           categorías, filtros, productos, inventario, promoción
│   ├── pedidos/            carrito, pago, pedidos, capacidad diaria
│   └── paginas/            inicio, cabeceras de seguridad
├── templates/              HTML (Django templates)
├── static/                 CSS, JS, fuentes e imágenes fijas
├── semillas/imagenes/      fotos del catálogo inicial
├── deploy/                 nginx y script de arranque
├── Dockerfile
└── docker-compose.yml
```

Cada módulo es independiente: para agregar, por ejemplo, suscripciones semanales o pagos con tarjeta en línea se crea una app nueva sin tocar las demás. Para más tráfico: subir `GUNICORN_WORKERS`, cambiar la caché a Redis y las fotos a un almacenamiento en la nube, sin cambiar el código de las vistas.

## Publicarla

1. Un servidor (VPS) con Docker y un dominio, por ejemplo `delipack.ec`.
2. En `.env`: `ALLOWED_HOSTS=delipack.ec,www.delipack.ec`, `CSRF_TRUSTED_ORIGINS=https://delipack.ec,https://www.delipack.ec`, `FORZAR_HTTPS=1`, `COOKIES_SEGURAS=1`, un `ADMIN_URL` difícil de adivinar y los datos SMTP reales.
3. Pon HTTPS delante de nginx (Cloudflare, Certbot o Caddy) y ejecuta `docker compose up -d --build`.
4. Si quieres que el servidor la reinicie solo tras un corte de luz, cambia `restart: "no"` por `restart: unless-stopped` **solo en el servidor**, no en tu computador.

## Productos y precios

Los precios iniciales están pensados para Tulcán en 2026: platos fuertes de USD 4,25 a 6,90, porciones de mise en place de USD 1,20 a 3,40 y combos de USD 6,90 a 24,00. Todo se cambia desde el panel.
