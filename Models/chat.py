from typing import Any, Optional, Dict, Callable
from datetime import datetime
from Services.PedidoService import PedidosService
from Services.ProductoService import ProductosService
from Services.ChatService import ChatService
from Services.ClienteService import ClienteService
from Services.RepartidorService import RepartidorService
from Util.database import get_db_session
from whatsapp_api import enviar_mensaje_whatsapp
from Util.menus import menu_categorias, mostrar_productos
from Util.product_util import lista_productos
from Util.estado import clear_cart, get_cart, get_estado, reset_estado, get_waiting_for, set_waiting_for, clear_waiting_for
from Util.repartidor_util import handle_interactive
from Util.calificacion_util import manejar_calificacion
from Util.procesar_texto_gemini import procesar_texto_gemini


class Chat:
    def __init__(self, id_chat=None, id_cliente=None, id_repartidor=None, pedido_service=None, producto_service=None, chat_service=None):
        self.id_chat = id_chat
        self.id_cliente = id_cliente
        self.id_repartidor = id_repartidor
        self.pedido_service = pedido_service
        self.producto_service = producto_service
        
        if chat_service:
            self.chat_service = chat_service
        else:
            db_session = get_db_session()
            self.chat_service = ChatService(db_session)

        
        self.conversation_data: Dict[str, Any] = {}
        
        self.function_graph: Dict[str, Dict] = {}
        self._register_commands()
        
        self.function_map = {
            "flujo_categorias": self.flujo_categorias,
            "flujo_productos": self.flujo_productos,
            "flujo_cantidad": self.flujo_cantidad,
            "flujo_carrito": self.flujo_carrito,
            "flujo_confirmacion": self.flujo_confirmacion,
        }
        
    
    def _register_commands(self):
        self.function_graph = {
            "menu": {
                'function': self.cmd_menu,
                'name': 'cmd_menu',
                'doc': self.cmd_menu.__doc__,
                'command': 'menu'
            },
            "ayuda": {
                'function': self.funcion_ayuda,
                'name': 'funcion_ayuda',
                'doc': self.funcion_ayuda.__doc__,
                'command': 'ayuda'
            },
            "carrito": {
                'function': self.cmd_carrito,
                'name': 'cmd_carrito',
                'doc': self.cmd_carrito.__doc__,
                'command': 'carrito'
            },
        }
    
    def get_session(self, numero):
        estado = get_estado(numero)
        return estado
    
    def reset_session(self, numero):
        reset_estado(numero)
    
    def clear_state(self, numero):
        self.reset_session(numero)
        self.reset_conversation(numero)
    
    def set_waiting_for(self, numero, func_name: str, context_data=None):
        set_waiting_for(numero, func_name, context_data)
        print(f"{numero}: Esperando respuesta para: {func_name}")
    
    def set_conversation_data(self, key: str, value: Any):
        self.conversation_data[key] = value
    
    def get_conversation_data(self, key: str, default: Any = None) -> Any:
        return self.conversation_data.get(key, default)
    
    def clear_conversation_data(self):
        self.conversation_data = {}
    
    def reset_conversation(self, numero):
        clear_waiting_for(numero)
        self.conversation_data = {}
        print("Conversación reseteada.")
    
    def is_waiting_response(self, numero) -> bool:
        return get_waiting_for(numero) is not None
    
    def get_waiting_function(self, numero) -> Optional[Callable]:
        func_name = get_waiting_for(numero)
        if func_name and func_name in self.function_map:
            return self.function_map[func_name]
        return None
    
    def print_state(self):
        print(f"\n{'='*60}")
        print("ESTADO DE LA CONVERSACIÓN")
        print(f"{'='*60}")
        estado_memoria = get_estado(self.id_cliente if isinstance(self.id_cliente, str) else "") if self.id_cliente else "N/A"
        print(f"Estado en memoria: {estado_memoria}")
        print(f"Datos de conversación: {self.conversation_data}")
        print(f"{'='*60}\n")

    def cmd_menu(self, numero, texto):
        return self.flujo_categorias(numero, texto)

    def funcion_ayuda(self, numero, texto):
        ayuda_texto = (
            "🤖 *Comandos disponibles:*\n"
            "/menu - Ver el menú de productos\n"
            "/carrito - Ver tu carrito actual\n"
            "/ayuda - Mostrar esta ayuda\n"
            "/cancelar - Cancelar pedido actual"
        )
        return enviar_mensaje_whatsapp(numero, ayuda_texto)

    def cmd_carrito(self, numero, texto):
        return self.flujo_carrito(numero, texto)

    def handle_text(self, numero, texto):

        texto_strip = texto.strip()
        texto_lower = texto_strip.lower()
        repartidor_service = RepartidorService()
        repartidor = repartidor_service.obtener_repartidor_por_telefono(numero)

        if repartidor:
            print(f"Repartidor: {repartidor}")

            if texto_strip.startswith("pedido_") or texto_strip.startswith("entregado_"):
                if texto_strip.startswith("entregado_"):
                    interactive = {
                        "type": "button_reply",
                        "button_reply": { "id": texto_strip }
                    }
                else:
                    interactive = {
                        "type": "list_reply",
                        "list_reply": { "id": texto_strip }
                    }

                resultado = handle_interactive(numero, interactive)
                return resultado

            return enviar_mensaje_whatsapp(numero, "Eres repartidor no puedo procesar un mensaje que no sea conversacion")

        if texto_strip.startswith("calificar_"):
            return manejar_calificacion(numero, texto_strip)

        if not self.id_chat:
            self.id_chat = f"chat_{numero}"

        if texto_strip.startswith(("cat_", "prod_", "add_")):
            if texto_strip.startswith("cat_"):
                return self.flujo_categorias(numero, texto_lower)
            elif texto_strip.startswith("prod_") or texto_strip.startswith("add_"):
                return self.flujo_productos(numero, texto_lower)

        if texto_lower in ("cancelar", "salir", "cancel"):
            self.clear_state(numero)
            clear_cart(numero)
            return enviar_mensaje_whatsapp(numero, "❌ Pedido cancelado. Escribí *menu* para comenzar de nuevo.")

        try:
            salida_gemini = procesar_texto_gemini(
                texto_strip,
                chat=self,
                numero=numero
            )

            if salida_gemini and isinstance(salida_gemini, dict):
                accion = salida_gemini.get("accion")
                respetar_waiting_for = salida_gemini.get("respetar_waiting_for", False)
                actualizar_waiting_for = salida_gemini.get("actualizar_waiting_for")
                mensaje_gemini = salida_gemini.get("mensaje")
                producto_id = salida_gemini.get("producto_id")
                cantidad_detectada = salida_gemini.get("cantidad_detectada")
                observacion = salida_gemini.get("observacion", "")
                
                if accion == "flujo_carrito" and producto_id and cantidad_detectada:
                    try:
                        ok, err = self.pedido_service.add_to_cart_pedidos(
                            numero, 
                            producto_id, 
                            cantidad_detectada,
                            observacion
                        )
                        
                        if not ok:
                            mensaje_error = f"❌ Error al agregar producto: {err}"
                            if self.id_chat:
                                self.chat_service.registrar_mensaje(self.id_chat, mensaje_error, es_cliente=False)
                            return enviar_mensaje_whatsapp(numero, mensaje_error)
                        
                        estado = get_estado(numero)
                        estado["state"] = "en_carrito"
                        self.set_waiting_for(numero, "flujo_carrito")
                            
                        res = self.pedido_service.mostrar_carrito_pedidos(numero)
                        mensaje_carrito = res["body"]
                        
                        if mensaje_gemini:
                            mensaje_final = f"{mensaje_gemini}\n\n{mensaje_carrito}"
                        else:
                            mensaje_final = mensaje_carrito
                        
                        if self.id_chat:
                            self.chat_service.registrar_mensaje(self.id_chat, mensaje_final, es_cliente=False)
                        
                        return enviar_mensaje_whatsapp(numero, mensaje_final)
                    except Exception as e:
                        print(f"⚠️ Error al agregar producto al carrito: {e}")
                        return self.flujo_inicio(numero, texto_lower)
                
                if mensaje_gemini:
                    if actualizar_waiting_for:
                        context_data = salida_gemini.get("context_data")
                        self.set_waiting_for(numero, actualizar_waiting_for, context_data)
                    elif not respetar_waiting_for:
                        clear_waiting_for(numero)
                    
                    if self.id_chat:
                        self.chat_service.registrar_mensaje(self.id_chat, mensaje_gemini, es_cliente=False)
                    
                    if respetar_waiting_for:
                        estado = get_estado(numero)
                        waiting_for_actual = estado.get("waiting_for")
                        if waiting_for_actual and waiting_for_actual in self.function_map:
                            enviar_mensaje_whatsapp(numero, mensaje_gemini)
                            return self.function_map[waiting_for_actual](numero, texto_lower)
                    
                    return enviar_mensaje_whatsapp(numero, mensaje_gemini)
                
                if respetar_waiting_for:
                    estado = get_estado(numero)
                    waiting_for_actual = estado.get("waiting_for")
                    if waiting_for_actual and waiting_for_actual in self.function_map:
                        return self.function_map[waiting_for_actual](numero, texto_lower)
                
                if actualizar_waiting_for:
                    context_data = salida_gemini.get("context_data")
                    self.set_waiting_for(numero, actualizar_waiting_for, context_data)
                elif not respetar_waiting_for and accion:
                    clear_waiting_for(numero)
                
                if accion and (accion in self.function_map or accion in self.function_graph):
                    if accion in self.function_map:
                        return self.function_map[accion](numero, texto_lower)
                    elif accion in self.function_graph:
                        return self.function_graph[accion]['function'](numero, texto_lower)
            
            return self.flujo_inicio(numero, texto_lower)
        except Exception as e:
            print(f"Error en procesar_texto_gemini: {type(e).__name__} -> {e}")
            return self.flujo_inicio(numero, texto_lower)

    def _registrar_y_enviar_mensaje(self, numero, mensaje):
        if self.id_chat:
            self.chat_service.registrar_mensaje(self.id_chat, mensaje, es_cliente=False)
        return enviar_mensaje_whatsapp(numero, mensaje)


    def flujo_inicio(self, numero, mensaje):
        self.set_waiting_for(numero, "flujo_categorias")
        estado = get_estado(numero)
        estado["state"] = "viendo_categorias"
        estado["cat_page"] = 1  
        mensaje_menu = menu_categorias(numero, 1)
        self.chat_service.registrar_mensaje(self.id_chat, "menu", es_cliente=False)
        return enviar_mensaje_whatsapp(numero, mensaje_menu)

    def flujo_categorias(self, numero, mensaje):
        estado = get_estado(numero)
        pagina_actual = estado.get("cat_page", 1)
        
        if mensaje == "cat_next":
            estado["cat_page"] = pagina_actual + 1
            mensaje_menu = menu_categorias(numero, estado["cat_page"])
            self.chat_service.registrar_mensaje(self.id_chat, "menu", es_cliente=False)
            return enviar_mensaje_whatsapp(numero, mensaje_menu)
        
        if mensaje == "cat_prev":
            estado["cat_page"] = max(1, pagina_actual - 1)
            mensaje_menu = menu_categorias(numero, estado["cat_page"])
            self.chat_service.registrar_mensaje(self.id_chat, "menu", es_cliente=False)
            return enviar_mensaje_whatsapp(numero, mensaje_menu)
        
        if mensaje == "cat_home":
            estado["cat_page"] = 1
            mensaje_menu = menu_categorias(numero, 1)
            self.chat_service.registrar_mensaje(self.id_chat, "menu", es_cliente=False)
            return enviar_mensaje_whatsapp(numero, mensaje_menu)
        
        if mensaje.startswith("cat_"):
            self.set_waiting_for(numero, "flujo_productos")
            estado["state"] = "viendo_productos"
            estado["page"] = 1
            return mostrar_productos(numero, mensaje)
        
        self.set_waiting_for(numero, "flujo_categorias")
        estado["state"] = "viendo_categorias"
        estado["cat_page"] = pagina_actual
        mensaje_menu = menu_categorias(numero, pagina_actual)
        self.chat_service.registrar_mensaje(self.id_chat, "menu", es_cliente=False)
        return enviar_mensaje_whatsapp(numero, mensaje_menu)

    def flujo_productos(self, numero, mensaje):
        estado = get_estado(numero)
        pagina_actual = estado.get("page", 1)
        filtro_actual = estado.get("filter", "cat_all")
        orden_asc = estado.get("order_asc", True)
        
        if mensaje == "prod_next":
            estado["page"] = pagina_actual + 1
            payload = lista_productos(numero, estado["page"], filtro_actual, orden_asc)
            self.chat_service.registrar_mensaje(self.id_chat, "productos", es_cliente=False)
            return enviar_mensaje_whatsapp(numero, payload)
        
        if mensaje == "prod_prev":
            estado["page"] = max(1, pagina_actual - 1)
            payload = lista_productos(numero, estado["page"], filtro_actual, orden_asc)
            self.chat_service.registrar_mensaje(self.id_chat, "productos", es_cliente=False)
            return enviar_mensaje_whatsapp(numero, payload)
        
        if mensaje == "prod_home":
            estado["page"] = 1
            payload = lista_productos(numero, 1, filtro_actual, orden_asc)
            self.chat_service.registrar_mensaje(self.id_chat, "productos", es_cliente=False)
            return enviar_mensaje_whatsapp(numero, payload)
        
        if mensaje == "prod_filter":
            estado["state"] = "viendo_categorias"
            clear_waiting_for(numero)
            mensaje_menu = menu_categorias(numero, estado.get("cat_page", 1))
            self.chat_service.registrar_mensaje(self.id_chat, "menu", es_cliente=False)
            return enviar_mensaje_whatsapp(numero, mensaje_menu)
        
        if mensaje == "prod_order":
            estado["order_asc"] = not orden_asc
            estado["page"] = 1
            payload = lista_productos(numero, 1, filtro_actual, estado["order_asc"])
            self.chat_service.registrar_mensaje(self.id_chat, "productos", es_cliente=False)
            return enviar_mensaje_whatsapp(numero, payload)
        
        if mensaje.startswith("add_"):
            prod_id = mensaje.replace("add_", "")
            estado_global = get_estado(numero)
            estado_global["context_data"] = {"prod_id": prod_id}
            estado_global["state"] = "esperando_cantidad"
            self.set_waiting_for(numero, "flujo_cantidad", {"prod_id": prod_id})
            return enviar_mensaje_whatsapp(numero, "📝 Escribí la cantidad con observación (ej: 2 sin cebolla)")

        return enviar_mensaje_whatsapp(numero, "📋 Escribí *carrito* para ver tu pedido o *menu* para volver al inicio.")

    def flujo_cantidad(self, numero, mensaje):
        estado_global = get_estado(numero)
        context_data = estado_global.get("context_data", {})
        prod_id = context_data.get("prod_id")
        
        if not prod_id:
            return enviar_mensaje_whatsapp(numero, "⚠️ Error: No se encontró el producto. Intenta seleccionarlo de nuevo.")
        
        partes = mensaje.split()
        try:
            cantidad = int(partes[0])
            if cantidad <= 0:
                raise ValueError
        except ValueError:
            return enviar_mensaje_whatsapp(numero, "⚠️ Cantidad inválida. Escribí un número válido (ej: 2).")

        aclaracion = " ".join(partes[1:]) if len(partes) > 1 else ""
        ok, err = self.pedido_service.add_to_cart_pedidos(numero, prod_id, cantidad, aclaracion)
        if not ok:
            return enviar_mensaje_whatsapp(numero, f"❌ Error al agregar: {err}")

        estado = get_estado(numero)
        estado["state"] = "en_carrito"
        estado["context_data"] = {}
        clear_waiting_for(numero)
        
        respuesta = f"✅ {cantidad} agregado(s) al carrito.\nEscribí *carrito* para ver tu pedido"
        self.chat_service.registrar_mensaje(self.id_chat, respuesta, es_cliente=False)
        
        return enviar_mensaje_whatsapp(numero, respuesta)

    def flujo_carrito(self, numero, mensaje):
        if mensaje in ("2", "seguir", "seguir pidiendo"):
            estado = get_estado(numero)
            estado["state"] = "viendo_categorias"
            estado["cat_page"] = estado.get("cat_page", 1)
            clear_waiting_for(numero)
            mensaje_menu = menu_categorias(numero, estado["cat_page"])
            self.chat_service.registrar_mensaje(self.id_chat, "menu", es_cliente=False)
            return enviar_mensaje_whatsapp(numero, mensaje_menu)

        if mensaje in ("3", "confirmar"):
            estado = get_estado(numero)
            estado["state"] = "confirmando"
            clear_waiting_for(numero)
            respuesta = "📍 Enviá tu ubicación para calcular el envío."
            self.chat_service.registrar_mensaje(self.id_chat, respuesta, es_cliente=False)
            return enviar_mensaje_whatsapp(numero, respuesta)

        if mensaje in ("1", "quitar", "eliminar"):
            return enviar_mensaje_whatsapp(numero, "🗑️ Escribí el nombre del producto a quitar (a implementar).")

        if mensaje in ("salir", "cancelar"):
            self.clear_state(numero)
            clear_cart(numero)
            return enviar_mensaje_whatsapp(numero, "❌ Pedido cancelado. Escribí *menu* para comenzar de nuevo.")

        res = self.pedido_service.mostrar_carrito_pedidos(numero)
        estado = get_estado(numero)
        estado["state"] = "en_carrito"
        self.set_waiting_for(numero, "flujo_carrito")
        return enviar_mensaje_whatsapp(numero, res["body"])

    def es_ubicacion(self, contenido: str) -> bool:
        try:
            partes = contenido.split(',')
            return len(partes) == 2 and float(partes[0]) and float(partes[1])
        except (ValueError, IndexError):
            return False

    def flujo_confirmacion(self, numero, mensaje):
        if mensaje in ("cancelar", "salir"):
            self.clear_state(numero)
            clear_cart(numero)
            return enviar_mensaje_whatsapp(numero, "❌ Pedido cancelado.")

        if self.es_ubicacion(mensaje):
            return self.handle_location(numero, mensaje)

        return enviar_mensaje_whatsapp(numero, "📍 Enviá tu ubicación para calcular el envío.")

    def handle_location(self, numero, contenido):
        repartidor_service = RepartidorService()
        repartidor = repartidor_service.obtener_repartidor_por_telefono(numero)
        if repartidor:
            return enviar_mensaje_whatsapp(numero, "Eres repartidor no puedo procesar un mensaje que no sea conversacion")
        
        try:
            partes = [p.strip() for p in contenido.split(",")]
            if len(partes) != 2:
                return enviar_mensaje_whatsapp(numero, "⚠️ Enviá la ubicación como: lat, lon")

            lat = float(partes[0])
            lon = float(partes[1])

            if not (-31.7 <= lat <= -30.9 and -58.3 <= lon <= -57.0):
                return enviar_mensaje_whatsapp(
                    numero,
                    "⚠️ La ubicación no corresponde a Salto, Uruguay. Enviá tu ubicación nuevamente."
                )

        except:
            return enviar_mensaje_whatsapp(
                numero,
                "⚠️ No pude entender la ubicación. Usá este formato: -31.38, -57.96"
            )

        try:
            id_cliente = self.id_cliente or self.conversation_data.get('id_cliente')
            id_chat = self.id_chat or self.conversation_data.get('id_chat')
            direccion = self.conversation_data.get('direccion') or ''
            pedido_service = self.pedido_service

            if not (pedido_service and id_cliente and id_chat):
                return enviar_mensaje_whatsapp(numero, "⚠️ Faltan datos para crear el pedido. Intentalo de nuevo.")

            detalle_carrito = pedido_service.detalle_carrito(numero)
            total = detalle_carrito.get('total', 0)

            if total <= 250:
                mensaje_error = (
                    f"El pedido mínimo es de $250. Tu pedido actual es de ${total:.2f}. "
                    f"Agregá más productos para completar tu pedido."
                )
                self.chat_service.registrar_mensaje(id_chat, mensaje_error, es_cliente=False)
                return enviar_mensaje_whatsapp(numero, mensaje_error)

            self.chat_service.registrar_mensaje(id_chat, f"Ubicación: {lat}, {lon}", es_cliente=True)

            pedido = pedido_service.crear_pedido(
                id_chat=id_chat,
                id_cliente=id_cliente,
                direccion=direccion,
                latitud=lat,
                longitud=lon
            )

            self.conversation_data['id_pedido'] = getattr(pedido, 'idpedido', None)

            from Util.coordenadas_gifs import calcular_ruta_simple, RESTAURANTE_LAT, RESTAURANTE_LON
            _, distancia_km, tiempo_min = calcular_ruta_simple(
                RESTAURANTE_LAT, RESTAURANTE_LON,
                lat, lon
            )
            estado = get_estado(numero)
            estado["state"] = "pedido_confirmado"

            cart = get_cart(numero)
            if cart:
                estado["state"] = "viendo_categorias"
                clear_cart(numero)

            msg = (
                f"📍Tu pedido fue registrado con ID: {getattr(pedido, 'idpedido', 'N/A')}\n"
                f"📏 Distancia: {distancia_km:.2f} km\n"
                f"⏱️ Tiempo estimado de entrega: {int(tiempo_min)} minutos\n"
                f"🔐 Código de verificación: {getattr(pedido, 'codigo_verificacion', 'N/A')}"
            )

            self.chat_service.registrar_mensaje(id_chat, msg, es_cliente=False)

            clear_waiting_for(numero)
            return enviar_mensaje_whatsapp(numero, msg)

        except Exception as e:
            print(f"Error en handle_location: {e}")
            return enviar_mensaje_whatsapp(numero, "⚠️ No se pudo procesar la ubicación correctamente.")

    
    def manejar_mensaje_repartidor(self, numero, repartidor, texto):
        from Util.repartidor_util import menu_pedidos_repartidor, obtener_pedidos_pendientes_repartidor
        
        texto = texto.strip()
        partes = texto.split()
        
        if len(partes) >= 2:
            try:
                id_pedido = int(partes[0])
                codigo = int(partes[1])
            except ValueError:
                return enviar_mensaje_whatsapp(numero, "Formato incorrecto. Envía: <id_pedido> <codigo>")
            
            repartidor_service = RepartidorService()
            resultado = repartidor_service.confirmar_entrega(
                repartidor["id"],
                id_pedido,
                codigo
            )
            
            if resultado["success"]:
                if resultado.get("tanda_finalizada"):
                    mensaje = f" {resultado['mensaje']}\n\nTanda completada! Sos un capo kick buttowski"
                    return enviar_mensaje_whatsapp(numero, mensaje)
                else:
                    mensaje = f" {resultado['mensaje']}\n\n"
                    mensaje += f"Próximo pedido: #{resultado['proximo_pedido']}\n"
                    mensaje += f"ETA: {resultado['eta_minutos']} minutos"
                    return enviar_mensaje_whatsapp(numero, mensaje)
            else:
                mensaje = f"Error {resultado['mensaje']}"
                return enviar_mensaje_whatsapp(numero, mensaje)
        
        pedidos = obtener_pedidos_pendientes_repartidor(repartidor["id"])
        if not pedidos:
            return enviar_mensaje_whatsapp(numero, "No tenés pedidos pendientes en este momento.")
        
        return menu_pedidos_repartidor(numero, pedidos)

