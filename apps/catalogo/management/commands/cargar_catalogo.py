"""Carga las categorías, filtros, productos y la promoción de bienvenida (solo si la base está vacía)."""
from decimal import Decimal
from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.management.base import BaseCommand
from django.db import transaction

from apps.catalogo.inventario import registrar_movimiento
from apps.catalogo.models import Atributo, Categoria, MovimientoInventario, Producto, Promocion, ValorAtributo

IMAGENES = Path(settings.BASE_DIR) / "semillas" / "imagenes"

CATEGORIAS = [
    # slug, nombre, título, presentación, orden, cuenta para capacidad diaria
    ("platos-fuertes", "Platos fuertes", "Platos fuertes listos para calentar",
     "Comidas completas y equilibradas, empacadas al vacío. Las calientas tres minutos y están listas.", 1, True),
    ("mise-en-place", "Mise en place", "Porciones de mise en place",
     "Verduras y frutas lavadas, cortadas y porcionadas. Tú cocinas; nosotros adelantamos la parte lenta.", 2, False),
    ("combos", "Combos", "Combos y promociones",
     "Paquetes para la semana y productos con precio especial.", 3, False),
]

ATRIBUTOS = [
    ("proteina", "Proteína", 1, ["Pollo", "Res", "Cerdo", "Pescado", "Huevo", "Legumbres"]),
    ("carbohidrato", "Carbohidrato", 2, ["Arroz", "Quinua", "Camote", "Papa", "Pasta integral", "Galletas integrales"]),
    ("verdura", "Verduras", 3, ["Brócoli", "Espárragos", "Espinaca", "Pimiento", "Zanahoria", "Zucchini", "Mixtas"]),
    ("tipo", "Tipo de porción", 4, ["Verduras", "Frutas", "Tubérculos", "Proteínas"]),
    ("preferencia", "Preferencia", 5, ["Vegetariano", "Alto en proteína", "Sin gluten", "Bajo en carbohidratos"]),
]

# categoría, imagen, nombre, resumen, descripción, ingredientes, precio, precio anterior, stock,
# (peso g, kcal, proteína, carbohidrato, grasa), alérgenos, filtros, destacado
PRODUCTOS = [
    ("platos-fuertes", "plato-01", "Pollo a las finas hierbas con camote",
     "Pechuga jugosa con hierbas, camote asado y espinaca salteada.",
     "Pechuga de pollo marinada con orégano, tomillo y ajo, horneada a baja temperatura para que quede jugosa. "
     "La acompañan cubos de camote asado con paprika y espinaca salteada.",
     "Pechuga de pollo, camote, espinaca, ajo, hierbas, aceite de oliva, sal", "5.25", None, 24,
     (420, 520, 42, 48, 14), "", ["proteina:pollo", "carbohidrato:camote", "verdura:espinaca",
                                  "preferencia:alto-en-proteina", "preferencia:sin-gluten"], True),
    ("platos-fuertes", "plato-02", "Pechuga al limón con vegetales",
     "Pollo al limón con brócoli, zanahoria y zucchini al vapor.",
     "Una opción ligera para la oficina: pechuga al limón y pimienta con vegetales cocidos al vapor, "
     "que conservan su color y su textura al recalentar.",
     "Pechuga de pollo, brócoli, zanahoria, zucchini, limón, pimienta, aceite de oliva", "4.95", None, 20,
     (380, 390, 40, 18, 15), "", ["proteina:pollo", "verdura:brocoli", "verdura:zanahoria", "verdura:zucchini",
                                  "preferencia:bajo-en-carbohidratos", "preferencia:sin-gluten",
                                  "preferencia:alto-en-proteina"], False),
    ("platos-fuertes", "plato-03", "Salmón con quinua y espárragos",
     "Salmón al horno sobre quinua, con espárragos y limón.",
     "Filete de salmón horneado con perejil, servido sobre quinua blanca y roja de la sierra, con espárragos "
     "verdes y una rodaja de limón para exprimir al momento.",
     "Salmón, quinua, espárragos, limón, perejil, aceite de oliva", "6.90", None, 12,
     (400, 560, 36, 42, 24), "Pescado", ["proteina:pescado", "carbohidrato:quinua", "verdura:esparragos",
                                         "preferencia:alto-en-proteina", "preferencia:sin-gluten"], True),
    ("platos-fuertes", "plato-04", "Lomo de res salteado con brócoli",
     "Tiras de lomo salteadas con brócoli y pimientos de colores.",
     "Lomo de res salteado al wok con brócoli, pimiento rojo y amarillo en una salsa ligera de soya y jengibre. "
     "Alto en proteína y bajo en carbohidratos.",
     "Lomo de res, brócoli, pimientos, salsa de soya, jengibre, ajo", "5.75", None, 18,
     (390, 450, 38, 16, 24), "Soya", ["proteina:res", "verdura:brocoli", "verdura:pimiento",
                                      "preferencia:alto-en-proteina", "preferencia:bajo-en-carbohidratos"], True),
    ("platos-fuertes", "plato-05", "Guiso de garbanzos con vegetales",
     "Garbanzos en salsa de tomate con zucchini y zanahoria.",
     "Un guiso casero y sustancioso, sin carne: garbanzos cocidos lentamente en salsa de tomate y comino, "
     "con zucchini, zanahoria y hojas de espinaca.",
     "Garbanzos, tomate, zucchini, zanahoria, espinaca, cebolla, comino", "4.50", None, 22,
     (420, 470, 18, 62, 14), "", ["proteina:legumbres", "verdura:zucchini", "verdura:zanahoria",
                                  "preferencia:vegetariano", "preferencia:sin-gluten"], False),
    ("platos-fuertes", "plato-06", "Pollo criollo con camote y acelga",
     "Pollo al ajillo con camote dorado y acelga salteada.",
     "Pechuga al ajillo con un toque de comino, camote dorado al horno y acelga salteada con cebolla. "
     "El sabor de casa, listo en tres minutos.",
     "Pechuga de pollo, camote, acelga, ajo, comino, cebolla", "5.25", None, 16,
     (420, 510, 41, 47, 14), "", ["proteina:pollo", "carbohidrato:camote", "verdura:espinaca",
                                  "preferencia:sin-gluten"], False),
    ("platos-fuertes", "plato-07", "Penne integral a la napolitana",
     "Pasta integral con salsa de tomate natural y espinaca.",
     "Penne de trigo integral con salsa de tomate cocida a fuego lento, albahaca y espinaca fresca. "
     "Vegetariano y lleno de fibra.",
     "Pasta integral, tomate, espinaca, albahaca, ajo, aceite de oliva", "4.50", "5.00", 26,
     (400, 540, 17, 86, 12), "Gluten", ["carbohidrato:pasta-integral", "verdura:espinaca",
                                        "preferencia:vegetariano"], False),
    ("platos-fuertes", "plato-08", "Pollo mediterráneo con quinua",
     "Pollo a la plancha con quinua, pimientos y zucchini.",
     "Pechuga a la plancha con especias mediterráneas, quinua graneada y vegetales asados: pimiento rojo, "
     "zucchini y cebolla morada.",
     "Pechuga de pollo, quinua, pimiento, zucchini, cebolla morada, especias", "5.50", None, 20,
     (420, 530, 41, 44, 17), "", ["proteina:pollo", "carbohidrato:quinua", "verdura:pimiento", "verdura:zucchini",
                                  "preferencia:alto-en-proteina", "preferencia:sin-gluten"], False),
    ("platos-fuertes", "plato-09", "Salmón al horno con quinua y brócoli",
     "Salmón con quinua, brócoli, zanahoria y pimiento asado.",
     "Salmón horneado con finas hierbas sobre quinua, acompañado de brócoli, zanahoria y pimiento asado. "
     "Rico en omega 3.",
     "Salmón, quinua, brócoli, zanahoria, pimiento, hierbas", "6.90", None, 10,
     (410, 570, 37, 44, 24), "Pescado", ["proteina:pescado", "carbohidrato:quinua", "verdura:brocoli",
                                         "preferencia:alto-en-proteina", "preferencia:sin-gluten"], False),
    ("platos-fuertes", "plato-10", "Estofado de res con vegetales",
     "Res cocida a fuego lento en su jugo, con vegetales.",
     "Trozos de res cocidos por dos horas en un jugo de tomate y especias, con pimientos, zanahoria y vainitas. "
     "Mejor aún al día siguiente.",
     "Carne de res, pimientos, zanahoria, vainitas, tomate, especias", "5.75", None, 14,
     (420, 480, 39, 20, 26), "", ["proteina:res", "verdura:pimiento", "verdura:zanahoria",
                                  "preferencia:alto-en-proteina", "preferencia:bajo-en-carbohidratos"], False),
    ("platos-fuertes", "plato-11", "Tortilla de huevo con vegetales asados",
     "Tortilla al horno con pimientos, zucchini y tomate asados.",
     "Tortilla de huevos de campo horneada con queso fresco, acompañada de pimientos, zucchini y tomates "
     "cherry asados. Vegetariana y sin gluten.",
     "Huevo, queso fresco, pimientos, zucchini, tomate cherry, cebolla", "4.25", None, 18,
     (380, 420, 24, 18, 26), "Huevo, lácteos", ["proteina:huevo", "verdura:pimiento", "verdura:zucchini",
                                                 "preferencia:vegetariano", "preferencia:sin-gluten"], False),

    ("mise-en-place", "porcion-1", "Zucchini en rodajas",
     "300 g de zucchini lavado y cortado, listo para la sartén.",
     "Zucchini fresco cortado en rodajas parejas y sellado al vacío. Ideal para saltear, asar o sumar a una pasta.",
     "Zucchini", "1.40", None, 30, (300, 50, 3.6, 9.3, 1), "", ["tipo:verduras", "verdura:zucchini",
                                                                 "preferencia:vegetariano"], False),
    ("mise-en-place", "porcion-2", "Zanahoria en bastones",
     "300 g de zanahoria pelada y cortada en bastones.",
     "Zanahoria pelada y cortada en bastones del mismo tamaño para que se cocine pareja. Sirve al vapor, "
     "en horno o como snack.",
     "Zanahoria", "1.20", None, 35, (300, 120, 2.8, 28, 0.7), "", ["tipo:verduras", "verdura:zanahoria",
                                                                    "preferencia:vegetariano"], False),
    ("mise-en-place", "porcion-3", "Manzana verde en láminas",
     "250 g de manzana verde en láminas para avena o ensaladas.",
     "Manzana verde cortada en láminas finas y empacada al vacío para que no se oscurezca. "
     "Perfecta para el desayuno, una ensalada o un postre rápido.",
     "Manzana verde, jugo de limón", "1.60", None, 25, (250, 130, 0.6, 34, 0.4), "", ["tipo:frutas",
                                                                                       "preferencia:vegetariano"], False),
    ("mise-en-place", "porcion-4", "Mix de vegetales primavera",
     "500 g de brócoli, zanahoria, vainita, coliflor y maíz.",
     "Una mezcla lista para acompañar cualquier proteína: brócoli, coliflor, zanahoria, vainita y maíz tierno, "
     "todo cortado y blanqueado. Bolsa de 20 × 30 cm.",
     "Brócoli, coliflor, zanahoria, vainita, maíz", "2.80", None, 28, (500, 210, 12, 38, 2), "",
     ["tipo:verduras", "verdura:mixtas", "verdura:brocoli", "preferencia:vegetariano"], True),
    ("mise-en-place", "porcion-5", "Papa y camote en cubos",
     "600 g de papa y camote pelados, listos para sopa o puré.",
     "Papa y camote pelados y cortados en cubos de 2 cm. Ahorra el paso más pesado de un locro, un puré "
     "o unas papas al horno.",
     "Papa, camote", "2.20", None, 22, (600, 480, 10, 108, 0.6), "", ["tipo:tuberculos", "carbohidrato:papa",
                                                                     "carbohidrato:camote", "preferencia:vegetariano"],
     False),
    ("mise-en-place", "porcion-6", "Base para sopa",
     "400 g de zanahoria, zucchini, apio y cebolla en cubos.",
     "El punto de partida de una buena sopa o un arroz: zanahoria, zucchini, apio, cebolla y pimiento en "
     "cubos pequeños. Solo agrega agua o caldo.",
     "Zanahoria, zucchini, apio, cebolla, pimiento", "1.90", None, 26, (400, 140, 5, 30, 1), "Apio",
     ["tipo:verduras", "verdura:mixtas", "verdura:zanahoria", "preferencia:vegetariano"], False),
    ("mise-en-place", "porcion-7", "Frambuesas congeladas",
     "250 g de frambuesas congeladas para batidos y postres.",
     "Frambuesas seleccionadas y congeladas en su punto. Directo a la licuadora para un batido, a la avena "
     "o a un postre.",
     "Frambuesas", "3.40", None, 16, (250, 130, 3, 30, 1.6), "", ["tipo:frutas", "preferencia:vegetariano"],
     False),

    ("combos", "combo-mar-y-tierra", "Kit Mar y Tierra",
     "Salmón, carne molida de res y espárragos para dos platos.",
     "Un kit de mise en place para dos comidas completas: filete de salmón (250 g), carne molida de res "
     "(300 g) y un atado de espárragos. Todo porcionado y sellado al vacío.",
     "Salmón, carne molida de res, espárragos", "11.90", None, 10, (750, None, None, None, None),
     "Pescado", ["proteina:pescado", "proteina:res", "verdura:esparragos", "tipo:proteinas"], False),
    ("combos", "combo-despensa-semanal", "Despensa semanal",
     "Pescado, carnes y vegetales porcionados para toda la semana.",
     "Lo necesario para cocinar cinco días sin ir al mercado: pescado entero, carne de cerdo, salchichas, "
     "maíz, zanahoria, brócoli y uvas, cada cosa en su bolsa al vacío.",
     "Pescado, cerdo, salchichas, maíz, zanahoria, brócoli, uvas", "22.50", None, 6, (3200, None, None, None, None),
     "Pescado", ["proteina:pescado", "proteina:cerdo", "verdura:mixtas", "tipo:proteinas"], False),
    ("combos", "combo-semana-oficina", "Semana de oficina",
     "Cinco platos fuertes distintos, uno para cada día laboral.",
     "Cinco platos fuertes elegidos por la cocina, uno por día de lunes a viernes, con información nutricional "
     "en cada empaque. La forma más simple de resolver la semana.",
     "Cinco platos fuertes del menú de la semana", "24.00", "26.25", 8, (2100, None, None, None, None), "",
     ["proteina:pollo", "proteina:res", "proteina:pescado"], True),
    ("combos", "promo-duo-proteinas", "Dúo de proteínas",
     "Carne molida de res y filete de pescado marinado.",
     "500 g de carne molida de res y 400 g de filete de pescado marinado en achiote y ajo, listos para "
     "la sartén. Precio especial por tiempo limitado.",
     "Carne molida de res, filete de pescado, achiote, ajo", "7.50", "8.90", 14, (900, None, None, None, None),
     "Pescado", ["proteina:res", "proteina:pescado", "tipo:proteinas"], False),
    ("combos", "promo-pack-variado", "Pack despensa andina",
     "Granos, pimientos, embutido y arroz en porciones al vacío.",
     "Una selección para la alacena: arroz, fréjol rojo, lenteja, ají verde, embutido ahumado y queso "
     "en porciones individuales que duran más gracias al sellado al vacío.",
     "Arroz, fréjol, lenteja, pimiento verde, embutido ahumado, queso", "15.90", "18.50", 9,
     (2400, None, None, None, None), "Lácteos", ["proteina:cerdo", "proteina:legumbres", "carbohidrato:arroz"],
     False),
    ("combos", "promo-frutos-rojos", "Frutos rojos para batidos",
     "Fresas, moras y frambuesas congeladas, tres bolsas de 250 g.",
     "Tres bolsas de 250 g con fresas, moras y frambuesas congeladas. Una bolsa rinde dos batidos grandes.",
     "Fresas, moras, frambuesas", "6.90", "8.40", 18, (750, 380, 6, 88, 3), "", ["tipo:frutas",
                                                                                   "preferencia:vegetariano"], False),
]


class Command(BaseCommand):
    help = "Carga el catálogo inicial de DeliPack si todavía no hay productos"

    def add_arguments(self, parser):
        parser.add_argument("--forzar", action="store_true", help="Cargar aunque ya existan productos")

    @transaction.atomic
    def handle(self, *args, forzar=False, **kwargs):
        if Producto.objects.exists() and not forzar:
            self.stdout.write("El catálogo ya tiene productos; no se cargó nada.")
            return

        categorias = {}
        for slug, nombre, titulo, descripcion, orden, capacidad in CATEGORIAS:
            categorias[slug], _ = Categoria.objects.update_or_create(
                slug=slug, defaults={"nombre": nombre, "titulo": titulo, "descripcion": descripcion,
                                     "orden": orden, "cuenta_capacidad": capacidad})

        valores = {}
        for slug, nombre, orden, opciones in ATRIBUTOS:
            atributo, _ = Atributo.objects.update_or_create(slug=slug, defaults={"nombre": nombre, "orden": orden})
            for opcion in opciones:
                v, _ = ValorAtributo.objects.get_or_create(atributo=atributo, nombre=opcion)
                valores[f"{slug}:{v.slug}"] = v

        for orden, (cat, imagen, nombre, resumen, descripcion, ingredientes, precio, anterior, stock,
                    (peso, kcal, prot, carb, grasa), alergenos, filtros, destacado) in enumerate(PRODUCTOS):
            p = Producto(
                categoria=categorias[cat], nombre=nombre, resumen=resumen, descripcion=descripcion,
                ingredientes=ingredientes, precio=Decimal(precio),
                precio_anterior=Decimal(anterior) if anterior else None, stock=0, stock_minimo=5,
                peso_g=peso, calorias=kcal, proteinas_g=prot, carbohidratos_g=carb, grasas_g=grasa,
                alergenos=alergenos, destacado=destacado, orden=orden,
            )
            if cat == "combos" or cat == "mise-en-place":
                p.conservacion = ("Mantener congelado a -18 °C." if "congel" in descripcion.lower()
                                  else "Refrigerar entre 0 y 4 °C. Usar en máximo 5 días.")
            with open(IMAGENES / f"{imagen}.jpg", "rb") as f:
                p.imagen.save(f"{imagen}.jpg", File(f), save=False)
            p.save()
            p.valores.set([valores[x] for x in filtros])
            registrar_movimiento(p.pk, stock, MovimientoInventario.ENTRADA, motivo="Inventario inicial")

        promo = Promocion(
            titulo="Tu primer almuerzo, más barato",
            mensaje="Crea tu cuenta y llévate 20% de descuento en tu primer pedido que incluya un plato fuerte "
                    "y una porción de mise en place.",
            porcentaje=20, activa=True)
        with open(IMAGENES / "plato-08.jpg", "rb") as f:
            promo.imagen.save("bienvenida.jpg", File(f), save=False)
        promo.save()
        promo.categorias_requeridas.set([categorias["platos-fuertes"], categorias["mise-en-place"]])

        self.stdout.write(self.style.SUCCESS(f"Catálogo cargado: {len(PRODUCTOS)} productos."))
