import os
import json
from google import genai
from google.genai import types
from Util.estado import get_estado
from Util.database import get_db_session, Producto

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

acciones_posibles = [
    "flujo_inicio",
    "flujo_categorias",
    "flujo_productos",
    "flujo_cantidad",
    "flujo_carrito",
    "flujo_confirmacion"
]
palabras_clave = {
    "menu": "flujo_categorias",
    "productos": "flujo_productos",
    "cantidad": "flujo_cantidad",
    "carrito": "flujo_carrito",
    "confirmar": "flujo_confirmacion"
}
estados_posibles = {
    "inicio": "flujo_inicio",
    "categorias": "flujo_categorias",
    "productos": "flujo_productos",
    "cantidad": "flujo_cantidad",
    "carrito": "flujo_carrito",
    "confirmacion": "flujo_confirmacion"
}

def buscar_producto(nombre: str) -> dict:
    db = get_db_session()
    try:
        productos = db.query(Producto).filter(
            Producto.nombre.ilike(f"%{nombre}%")
        ).all()
        
        if productos:
            producto = productos[0]
            return {
                "producto_id": producto.idproducto,
                "nombre": producto.nombre
            }
        else:
            return {
                "producto_id": None,
                "nombre": None
            }
    except Exception as e:
        print(f"⚠️ Error al buscar producto: {e}")
        return {
            "producto_id": None,
            "nombre": None
        }
    finally:
        db.close()

def procesar_texto_gemini(texto: str, chat=None, numero: str = None) -> dict:
    if not numero:
        raise ValueError("El parámetro 'numero' es requerido")
    estado = get_estado(numero)
    waiting_for = estado.get("waiting_for")
    estado_actual = estado.get("state", "inicio")

    opciones_disponibles = []
    if estado_actual == "inicio" or not estado_actual:
        opciones_disponibles = [
            "- 'menu' o 'menú' → Ver categorías de productos",
            "- 'carrito' → Ver carrito actual",
            "- 'ayuda' → Ver ayuda"
        ]
    elif estado_actual == "viendo_categorias" or waiting_for == "flujo_categorias":
        opciones_disponibles = [
            "- 'menu' o 'menú' → Ver categorías (ya está viendo)",
            "- Seleccionar una categoría (se hace con botones interactivos)",
            "- 'carrito' → Ver carrito",
            "- 'ayuda' → Ver ayuda"
        ]
    elif estado_actual == "viendo_productos" or waiting_for == "flujo_productos":
        opciones_disponibles = [
            "- Seleccionar un producto (se hace con botones interactivos)",
            "- 'carrito' → Ver carrito",
            "- 'menu' → Volver a categorías",
            "- 'ayuda' → Ver ayuda"
        ]
    elif estado_actual == "esperando_cantidad" or waiting_for == "flujo_cantidad":
        opciones_disponibles = [
            "- Escribir un número (cantidad) → Ej: '2' o '2 sin cebolla'",
            "- 'cancelar' → Cancelar y volver al inicio"
        ]
    elif estado_actual == "en_carrito" or waiting_for == "flujo_carrito":
        opciones_disponibles = [
            "- '1', 'quitar' o 'eliminar' → Quitar producto del carrito",
            "- '2', 'seguir' o 'seguir pidiendo' → Continuar agregando productos",
            "- '3' o 'confirmar' → Confirmar pedido y enviar ubicación",
            "- 'carrito' → Ver carrito nuevamente",
            "- 'cancelar' o 'salir' → Cancelar pedido"
        ]
    elif estado_actual == "confirmando" or waiting_for == "flujo_confirmacion":
        opciones_disponibles = [
            "- Enviar ubicación (latitud, longitud) → Ej: '-31.38, -57.96'",
            "- 'cancelar' o 'salir' → Cancelar pedido"
        ]
    else:
        opciones_disponibles = [
            "- 'menu' → Ver menú",
            "- 'carrito' → Ver carrito",
            "- 'ayuda' → Ver ayuda"
        ]

    opciones_texto = "\n".join(opciones_disponibles)

    info_waiting_for = ""
    if waiting_for:
        info_waiting_for = f"""
IMPORTANTE - FUNCIÓN ESPERADA ACTIVA:
El sistema está esperando que el usuario responda a: "{waiting_for}"
Esto significa que el usuario está en medio de un flujo específico.

DEBES EVALUAR:
1. ¿El mensaje del usuario responde a lo que se espera en "{waiting_for}"?
   - Si SÍ → establece "respetar_waiting_for": true y devuelve la acción correspondiente
   - Si NO (el usuario quiere cambiar de flujo, ej: escribe "menu", "carrito", "cancelar") → establece "respetar_waiting_for": false y cambia la acción

Ejemplos:
- Si waiting_for es "flujo_cantidad" y el usuario escribe "2" → respetar_waiting_for: true, accion: "flujo_cantidad"
- Si waiting_for es "flujo_cantidad" y el usuario escribe "menu" → respetar_waiting_for: false, accion: "flujo_categorias"
- Si waiting_for es "flujo_carrito" y el usuario escribe "1" → respetar_waiting_for: true, accion: "flujo_carrito"
- Si waiting_for es "flujo_carrito" y el usuario escribe "menu" → respetar_waiting_for: false, accion: "flujo_categorias"
"""

    tool_schema = {
        "name": "buscar_producto",
        "description": "Busca un producto en la base de datos por nombre. Úsala cuando el usuario mencione un producto específico que quiere agregar al carrito.",
        "parameters": {
            "type": "object",
            "properties": {
                "nombre": {
                    "type": "string",
                    "description": "Nombre del producto a buscar (puede ser parcial, ej: 'coca cola', 'hamburguesa', 'pizza muzzarella')"
                }
            },
            "required": ["nombre"]
        }
    }

    prompt = f"""Eres un orquestador de flujo de conversación para un sistema de entrega de productos.

CONTEXTO: Estado={estado_actual}, Waiting_for={waiting_for if waiting_for else "ninguna"}, Mensaje="{texto}"
{info_waiting_for}

OPCIONES DISPONIBLES: {opciones_texto}
ACCIONES: {acciones_posibles}
PALABRAS CLAVE: "menu"/"menú"→flujo_categorias, "carrito"→flujo_carrito, "ayuda"→flujo_inicio, "confirmar"→flujo_confirmacion
COMANDOS CARRITO: "1"/"quitar"→quitar, "2"/"seguir"→continuar, "3"/"confirmar"→confirmar
NOTA: Comandos técnicos "cat_*", "prod_*", "add_*" son internos y NO deben procesarse.

DETECCIÓN DE PRODUCTOS, CANTIDADES Y OBSERVACIONES:
Si el mensaje menciona producto y cantidad (ej: "Quiero 3 Coca Cola", "Dame 2 hamburguesas, 1 con aceitunas", "Necesito 1 pizza sin cebolla"):
1. Usa buscar_producto para encontrar el producto
2. Extrae la cantidad (número)
3. Extrae observaciones si existen (ej: "con aceitunas", "sin cebolla", "1 de ellas con aceitunas")
4. Si encuentras producto_id y cantidad:
   - "accion": "flujo_carrito", "estado": "en_carrito"
   - "producto_id": [id encontrado], "cantidad_detectada": [cantidad]
   - "observacion": [observación extraída o "" si no hay]
   - "respetar_waiting_for": true, "actualizar_waiting_for": "flujo_carrito"
   - "mensaje": [confirmación amigable, ej: "Genial 😄 Agregué 2 hamburguesas (1 con aceitunas). ¿Confirmamos?"]
5. Si no encuentras producto: "accion": "flujo_inicio", "mensaje": [sugerir usar menú], "respetar_waiting_for": false
6. Si no detectas cantidad: "accion": "flujo_cantidad", "mensaje": [preguntar cantidad], "respetar_waiting_for": false

MANEJO DE SALUDOS:
CASO A - Sin waiting_for: Si es saludo (hola, buenos días, etc.) → "accion": "flujo_inicio", "estado": "inicio", "respetar_waiting_for": false, "mensaje": [saludo amigable + sugerir *menu*]
CASO B - Con waiting_for: Si es saludo que NO responde → "accion": [acción del waiting_for actual], "respetar_waiting_for": true, "mensaje": [recordar qué se espera según waiting_for]

ORQUESTACIÓN:
1. Detecta saludo/contexto (casos A/B)
2. Evalúa si mensaje responde a waiting_for o cambia de flujo
3. "menu"/"menú" → flujo_categorias (respetar_waiting_for: false)
4. "carrito" → flujo_carrito (respetar_waiting_for: false si hay otro waiting_for)
5. "ayuda" → flujo_inicio (respetar_waiting_for: false)
6. waiting_for="flujo_cantidad" + número → respetar_waiting_for: true, accion: "flujo_cantidad"
7. waiting_for="flujo_carrito" + "1"/"2"/"3"/"quitar"/"seguir"/"confirmar" → respetar_waiting_for: true, accion: "flujo_carrito"
8. waiting_for="flujo_confirmacion" + coordenadas → respetar_waiting_for: true, accion: "flujo_confirmacion"
9. Sin contexto claro → "flujo_inicio" (respetar_waiting_for: false)

REGLAS:
- Siempre devuelve JSON con "accion", "estado", "respetar_waiting_for"
- "estado" debe ser uno de: {list(estados_posibles.keys())}
- Si no entiendes → "flujo_inicio"
- Si cambias flujo (respetar_waiting_for: false) → opcional "actualizar_waiting_for"
- Si generas "mensaje" → se envía directamente, NO ejecuta acción

Formato JSON:
{{
    "accion": "flujo_inicio",
    "estado": "inicio",
    "respetar_waiting_for": false,
    "mensaje": "Texto opcional",
    "actualizar_waiting_for": "flujo_categorias",
    "producto_id": 123,
    "cantidad_detectada": 3,
    "observacion": "con aceitunas"
}}

NOTA: "producto_id", "cantidad_detectada" y "observacion" solo cuando detectes producto en el mensaje."""
    
    try:
        function_declaration = types.FunctionDeclaration(
            name=tool_schema["name"],
            description=tool_schema["description"],
            parameters={
                "type": "object",
                "properties": {
                    "nombre": {
                        "type": "string",
                        "description": tool_schema["parameters"]["properties"]["nombre"]["description"]
                    }
                },
                "required": tool_schema["parameters"]["required"]
            }
        )
        
        tools = [types.Tool(function_declarations=[function_declaration])]
    except Exception as e:
        print(f"⚠️ Error al configurar tools, continuando sin tool calling: {e}")
        tools = None
    
    try:
        # Primera llamada a Gemini con tools (si están disponibles)
        config_params = {
            "thinking_config": types.ThinkingConfig(thinking_budget=0)
        }
        if tools:
            config_params["tools"] = tools
        
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=[prompt, "Devolveme sólo un JSON en la respuesta, sin explicaciones."],
            config=types.GenerateContentConfig(**config_params),
        )
        
        function_results = []
        
        if hasattr(response, 'candidates') and response.candidates:
            candidate = response.candidates[0]
            if hasattr(candidate, 'content') and candidate.content:
                parts = candidate.content.parts if hasattr(candidate.content, 'parts') else []
                
                tool_calls = []
                for part in parts:
                    if hasattr(part, 'function_call') and part.function_call:
                        tool_calls.append(part)
                        tool_calls_found = True
                
                if tool_calls:
                    for tool_call in tool_calls:
                        func_name = tool_call.function_call.name
                        if hasattr(tool_call.function_call, 'args'):
                            if isinstance(tool_call.function_call.args, str):
                                args = json.loads(tool_call.function_call.args)
                            else:
                                args = tool_call.function_call.args
                        else:
                            args = {}
                        
                        if func_name == "buscar_producto":
                            nombre_producto = args.get("nombre", "")
                            resultado = buscar_producto(nombre_producto)
                            function_results.append(types.Part(
                                function_response=types.FunctionResponse(
                                    name=func_name,
                                    response=resultado
                                )
                            ))
                    
                    contents_with_result = [
                        prompt,
                        "Devolveme sólo un JSON en la respuesta, sin explicaciones.",
                        *[types.Part(function_call=tc.function_call) for tc in tool_calls],
                        *function_results
                    ]
                    
                    config_params_retry = {
                        "thinking_config": types.ThinkingConfig(thinking_budget=0)
                    }
                    if tools:
                        config_params_retry["tools"] = tools
                    
                    response = client.models.generate_content(
                        model="gemini-2.5-flash",
                        contents=contents_with_result,
                        config=types.GenerateContentConfig(**config_params_retry),
                    )
        
        response_text = response.text if hasattr(response, 'text') and response.text else ""
        
        if not response_text:
            print("⚠️ Respuesta vacía de Gemini, usando acción por defecto")
            return {"accion": "flujo_inicio", "estado": "inicio"}
        
        response_text = response_text.strip()
        
        if "```json" in response_text:
            start = response_text.find("```json") + 7
            end = response_text.find("```", start)
            if end != -1:
                response_text = response_text[start:end].strip()
        elif "```" in response_text:
            start = response_text.find("```") + 3
            end = response_text.find("```", start)
            if end != -1:
                response_text = response_text[start:end].strip()
        
        first_brace = response_text.find("{")
        last_brace = response_text.rfind("}")
        
        if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
            response_text = response_text[first_brace:last_brace + 1]
        
        resultado = json.loads(response_text)
        print(f"Resultado: {resultado}")

        if "accion" not in resultado:
            print(f"⚠️ Respuesta de Gemini no tiene 'accion', usando por defecto. Respuesta: {response_text}")
            return {
                "accion": "flujo_inicio",
                "estado": resultado.get("estado", "inicio"),
                "respetar_waiting_for": False
            }

        # Asegurar que los campos adicionales tengan valores por defecto
        resultado.setdefault("respetar_waiting_for", False)
        resultado.setdefault("estado", "inicio")
        
        # Si no hay actualizar_waiting_for pero respetar_waiting_for es true, no necesitamos actualizar
        # Si respetar_waiting_for es false y hay una nueva acción, limpiar waiting_for (se hace en handle_text)

        return resultado
        
    except json.JSONDecodeError as e:
        print(f"⚠️ Error al parsear JSON de Gemini: {e}")
        print(f"📝 Respuesta recibida: {response_text if 'response_text' in locals() else 'N/A'}")
        return {"accion": "flujo_inicio", "estado": "inicio"}
    except Exception as e:
        print(f"⚠️ Error al procesar con Gemini: {type(e).__name__} -> {e}")
        return {"accion": "flujo_inicio", "estado": "inicio"}

