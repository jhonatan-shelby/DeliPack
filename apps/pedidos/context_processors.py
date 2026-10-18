from .carrito import Carrito


def carrito(request):
    # Perezoso: solo consulta la base de datos si la plantilla usa el número
    c = Carrito(request)
    return {"carrito_cantidad": c.cantidad_total}
