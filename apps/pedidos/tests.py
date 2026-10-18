"""Pruebas del flujo completo. Se ejecutan con: python manage.py test"""
import re
import shutil
import tempfile

from django.contrib.auth.models import Group
from django.core import mail
from django.core.management import call_command
from django.test import TestCase, override_settings

from apps.catalogo.models import MovimientoInventario, Producto
from apps.cuentas.models import Usuario
from apps.pedidos.models import ConfiguracionNegocio, Pedido

MEDIA_TEMPORAL = tempfile.mkdtemp()
CLAVE = "Almuerzo#Tulcan26"


@override_settings(MEDIA_ROOT=MEDIA_TEMPORAL, EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
                   ALLOWED_HOSTS=["testserver"],
                   STORAGES={"default": {"BACKEND": "django.core.files.storage.FileSystemStorage"},
                             "staticfiles": {"BACKEND": "django.contrib.staticfiles.storage.StaticFilesStorage"}})
class FlujoDeliPackTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("createcachetable", verbosity=0)
        call_command("cargar_catalogo", stdout=open("/dev/null", "w"))
        call_command("configurar_grupos", stdout=open("/dev/null", "w"))
        cls.plato = Producto.objects.get(nombre="Salmón con quinua y espárragos")
        cls.porcion = Producto.objects.get(nombre="Mix de vegetales primavera")

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(MEDIA_TEMPORAL, ignore_errors=True)

    def setUp(self):
        from django.core.cache import cache
        cache.clear()

    # ---------- utilidades ----------
    def registrar(self, email="ana@correo.ec", clave=CLAVE):
        return self.client.post("/cuentas/registro/", {
            "nombres": "Ana", "apellidos": "Ruiz", "email": email, "telefono": "0991234567",
            "password1": clave, "password2": clave, "acepta": "on"})

    def verificar_correo(self):
        enlace = re.search(r"http://testserver(/cuentas/verificar/\S+)", mail.outbox[-1].body).group(1)
        return self.client.get(enlace)

    def agregar(self, producto, cantidad=1):
        return self.client.post("/carrito/agregar/", {"producto": producto.pk, "cantidad": cantidad},
                                HTTP_ACCEPT="application/json")

    def pagar(self, **extra):
        fecha = self.client.get("/pago/").context["form"].fields["fecha_entrega"].choices[0][0]
        datos = {"tipo_entrega": "OFICINA", "direccion": "Av. Coral y Sucre", "telefono": "0991234567",
                 "fecha_entrega": fecha, "franja": "ALMUERZO", "metodo_pago": "EFECTIVO"}
        datos.update(extra)
        return self.client.post("/pago/", datos)

    # ---------- cuentas y seguridad ----------
    def test_contrasena_debil_rechazada(self):
        r = self.registrar(clave="tulcan2026")
        self.assertEqual(r.status_code, 200)
        self.assertFalse(Usuario.objects.filter(email="ana@correo.ec").exists())
        self.assertContains(r, "mayúscula")

    def test_correo_temporal_rechazado(self):
        r = self.registrar(email="alguien@mailinator.com")
        self.assertContains(r, "correos temporales")

    def test_registro_guarda_hash_y_descuento(self):
        self.registrar()
        u = Usuario.objects.get(email="ana@correo.ec")
        self.assertTrue(u.password.startswith("argon2$"))  # nunca se guarda en texto plano
        self.assertEqual(u.descuento_bienvenida, 20)
        self.assertFalse(u.email_verificado)
        self.assertEqual(len(mail.outbox), 1)
        self.verificar_correo()
        u.refresh_from_db()
        self.assertTrue(u.email_verificado)

    def test_bloqueo_tras_intentos_fallidos(self):
        self.registrar()
        self.client.post("/cuentas/salir/")
        for _ in range(5):
            self.client.post("/cuentas/ingresar/", {"email": "ana@correo.ec", "password": "Incorrecta#123"})
        r = self.client.post("/cuentas/ingresar/", {"email": "ana@correo.ec", "password": CLAVE})
        self.assertContains(r, "Demasiados intentos")

    def test_cabecera_csp(self):
        r = self.client.get("/")
        self.assertIn("script-src 'self'", r["Content-Security-Policy"])

    # ---------- catálogo ----------
    def test_filtros_combinados(self):
        r = self.client.get("/platos-fuertes/", {"proteina": "pescado", "carbohidrato": "quinua"})
        nombres = {p.nombre for p in r.context["pagina"].object_list}
        self.assertEqual(nombres, {"Salmón con quinua y espárragos", "Salmón al horno con quinua y brócoli"})
        r = self.client.get("/platos-fuertes/", {"proteina": ["pollo", "res"]})
        self.assertTrue(all(any(v.slug in ("pollo", "res") for v in p.valores.all())
                            for p in r.context["pagina"].object_list))

    def test_detalle_parcial(self):
        r = self.client.get(self.plato.get_absolute_url(), {"parcial": "1"})
        self.assertContains(r, "Información nutricional")
        self.assertNotContains(r, "<html")

    # ---------- compra ----------
    def test_sin_verificar_no_paga(self):
        self.registrar()
        self.agregar(self.plato)
        self.pagar()
        self.assertEqual(Pedido.objects.count(), 0)

    def test_compra_descuenta_stock_y_aplica_descuento_una_vez(self):
        self.agregar(self.plato, 2)  # como visitante: el carrito pasa a la cuenta al registrarse
        self.registrar()
        self.verificar_correo()
        self.agregar(self.porcion)
        antes = Producto.objects.get(pk=self.plato.pk).stock
        r = self.pagar()
        pedido = Pedido.objects.get()
        self.assertRedirects(r, f"/pedidos/{pedido.codigo}/")
        self.assertEqual(pedido.subtotal, self.plato.precio * 2 + self.porcion.precio)
        self.assertEqual(pedido.descuento_porcentaje, 20)
        self.assertEqual(Producto.objects.get(pk=self.plato.pk).stock, antes - 2)
        self.assertTrue(MovimientoInventario.objects.filter(pedido=pedido, tipo="VENTA").exists())
        # segundo pedido: ya no hay descuento
        self.agregar(self.plato)
        self.agregar(self.porcion)
        self.pagar()
        self.assertEqual(Pedido.objects.order_by("-pk").first().descuento_porcentaje, 0)

    def test_descuento_exige_plato_y_mise_en_place(self):
        self.registrar()
        self.verificar_correo()
        self.agregar(self.plato)
        self.pagar()
        self.assertEqual(Pedido.objects.get().descuento, 0)

    def test_capacidad_diaria(self):
        ConfiguracionNegocio.objects.update_or_create(pk=1, defaults={"capacidad_diaria": 3})
        self.registrar()
        self.verificar_correo()
        self.agregar(self.plato, 4)
        self.pagar()
        self.assertEqual(Pedido.objects.count(), 0)

    def test_cancelar_devuelve_stock(self):
        self.registrar()
        self.verificar_correo()
        stock = self.plato.stock
        self.agregar(self.plato, 3)
        self.pagar()
        pedido = Pedido.objects.get()
        self.client.post(f"/pedidos/{pedido.codigo}/cancelar/")
        pedido.refresh_from_db()
        self.assertEqual(pedido.estado, "CANCELADO")
        self.assertEqual(Producto.objects.get(pk=self.plato.pk).stock, stock)

    # ---------- permisos del panel ----------
    def test_permisos_por_grupo(self):
        inventario = Usuario.objects.create_user("inv@delipack.ec", CLAVE, nombres="Rosa", is_staff=True)
        inventario.groups.add(Group.objects.get(name="Inventario"))
        self.client.force_login(inventario)
        self.assertEqual(self.client.get("/admin/catalogo/producto/").status_code, 200)
        self.assertEqual(self.client.get("/admin/cuentas/usuario/").status_code, 403)

        ventas = Usuario.objects.create_user("ven@delipack.ec", CLAVE, nombres="Luis", is_staff=True)
        ventas.groups.add(Group.objects.get(name="Ventas"))
        self.client.force_login(ventas)
        self.assertEqual(self.client.get("/admin/catalogo/producto/add/").status_code, 403)
        self.assertEqual(self.client.get("/admin/pedidos/pedido/").status_code, 200)

    def test_ajuste_de_stock_desde_admin_queda_en_historial(self):
        admin = Usuario.objects.create_superuser("jefe@delipack.ec", CLAVE)
        self.client.force_login(admin)
        r = self.client.post("/admin/catalogo/movimientoinventario/add/", {
            "producto": self.porcion.pk, "tipo": "MERMA", "cantidad": 3, "motivo": "Bolsa rota"})
        self.assertEqual(r.status_code, 302)
        mov = MovimientoInventario.objects.get(tipo="MERMA")
        self.assertEqual(mov.cantidad, -3)
        self.assertEqual(Producto.objects.get(pk=self.porcion.pk).stock, self.porcion.stock - 3)
