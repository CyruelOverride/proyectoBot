"""
Variables locales para estado de sesión y carrito.
No se persisten en BD, son temporales por sesión.
"""

# ESTADO: reemplaza SESSION - estado temporal de navegación (no se persiste en BD)
ESTADO = {}

def get_estado(numero):
    """Obtiene el estado de navegación del usuario (página, filtro, orden)."""
    return ESTADO.setdefault(numero, {
        "page": 1,
        "filter": "cat_all",
        "order_asc": True,
        "state": "inicio",
        "waiting_for": None,  # Función esperada para próximo mensaje
        "context_data": {}  # Datos de contexto para la función esperada
    })

def reset_estado(numero):
    """Resetea el estado de navegación del usuario."""
    if numero in ESTADO:
        ESTADO[numero] = {
            "page": 1,
            "filter": "cat_all",
            "order_asc": True,
            "state": "inicio",
            "waiting_for": None,
            "context_data": {}
        }

def get_waiting_for(numero):
    """Obtiene la función que está esperando respuesta del usuario."""
    estado = get_estado(numero)
    return estado.get("waiting_for")

def set_waiting_for(numero, func_name, context_data=None):
    """Establece la función esperada para próximo mensaje del usuario."""
    estado = get_estado(numero)
    estado["waiting_for"] = func_name
    estado["context_data"] = context_data or {}

def clear_waiting_for(numero):
    """Limpia la función esperada."""
    estado = get_estado(numero)
    estado["waiting_for"] = None
    estado["context_data"] = {}

# CARRITO: variable local para el carrito temporal (no se persiste en BD)
CARRITO = {}

def get_cart(numero):
    """Obtiene el carrito del usuario."""
    return CARRITO.setdefault(numero, {})

def clear_cart(numero):
    """Limpia el carrito del usuario."""
    if numero in CARRITO:
        del CARRITO[numero]

