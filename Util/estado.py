"""
Variables locales para estado de sesión y citas.
No se persisten en BD, son temporales por sesión.
"""

# ESTADO: reemplaza SESSION - estado temporal de navegación (no se persiste en BD)
ESTADO = {}

def get_estado(numero):
    """Obtiene el estado de navegación del usuario."""
    return ESTADO.setdefault(numero, {
        "state": "inicio",
        "waiting_for": None,  # Función esperada para próximo mensaje
        "context_data": {}  # Datos de contexto para la función esperada
    })

def reset_estado(numero):
    """Resetea el estado de navegación del usuario."""
    if numero in ESTADO:
        ESTADO[numero] = {
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
    if context_data:
        # Actualizar context_data existente en lugar de reemplazarlo
        estado["context_data"].update(context_data)

def clear_waiting_for(numero):
    """Limpia la función esperada."""
    estado = get_estado(numero)
    estado["waiting_for"] = None
    estado["context_data"] = {}

# CITAS: variable local para las citas agendadas (no se persiste en BD)
CITAS = {}

def get_citas(numero):
    """Obtiene las citas del usuario."""
    return CITAS.setdefault(numero, [])

def add_cita(numero, cita):
    """Agrega una cita a la lista del usuario."""
    citas = get_citas(numero)
    citas.append(cita)
    return citas

def clear_citas(numero):
    """Limpia las citas del usuario."""
    if numero in CITAS:
        del CITAS[numero]

