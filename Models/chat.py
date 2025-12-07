from typing import Any, Optional, Dict, Callable
from datetime import datetime
import re
from Services.ChatService import ChatService
from Services.ClienteService import ClienteService
from Services.RepartidorService import RepartidorService
from Util.database import get_db_session
from whatsapp_api import enviar_mensaje_whatsapp
from Util.estado import get_estado, reset_estado, get_waiting_for, set_waiting_for, clear_waiting_for, get_citas, add_cita, clear_citas
from Util.repartidor_util import handle_interactive
from Util.calificacion_util import manejar_calificacion


class Chat:
    def __init__(self, id_chat=None, id_cliente=None, id_repartidor=None, chat_service=None):
        self.id_chat = id_chat
        self.id_cliente = id_cliente
        self.id_repartidor = id_repartidor
        
        if chat_service:
            self.chat_service = chat_service
        else:
            db_session = get_db_session()
            self.chat_service = ChatService(db_session)

        
        self.conversation_data: Dict[str, Any] = {}
        
        self.function_graph: Dict[str, Dict] = {}
        self._register_commands()
        
        self.function_map = {
            "flujo_inicio": self.flujo_inicio,
            "flujo_nombre_completo": self.flujo_nombre_completo,
            "flujo_servicio": self.flujo_servicio,
            "flujo_dia_hora": self.flujo_dia_hora,
            "flujo_confirmacion_cita": self.flujo_confirmacion_cita,
        }
        
    
    def _register_commands(self):
        self.function_graph = {
            "ayuda": {
                'function': self.funcion_ayuda,
                'name': 'funcion_ayuda',
                'doc': self.funcion_ayuda.__doc__,
                'command': 'ayuda'
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

    def funcion_ayuda(self, numero, texto):
        ayuda_texto = (
            "🤖 *Sistema de Agendamiento de Citas*\n\n"
            "Para agendar una cita, simplemente escribe cualquier mensaje y te guiaré paso a paso.\n\n"
            "Necesitaré:\n"
            "• Tu nombre\n"
            "• Tu apellido\n"
            "• El día de la semana\n"
            "• La hora\n\n"
            "Escribe *cancelar* en cualquier momento para cancelar."
        )
        return enviar_mensaje_whatsapp(numero, ayuda_texto)

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

        # Comandos especiales
        if texto_lower in ("cancelar", "salir", "cancel"):
            self.clear_state(numero)
            clear_citas(numero)
            return enviar_mensaje_whatsapp(numero, "❌ Agendamiento cancelado. Escribe cualquier mensaje para comenzar de nuevo.")

        # Verificar si hay un comando registrado
        if texto_lower in self.function_graph:
            return self.function_graph[texto_lower]['function'](numero, texto_lower)

        # Verificar si hay un waiting_for activo
        estado = get_estado(numero)
        waiting_for = estado.get("waiting_for")
        
        if waiting_for and waiting_for in self.function_map:
            return self.function_map[waiting_for](numero, texto_lower)
        
        # Intentar extraer día y hora del mensaje si no hay waiting_for
        dia_encontrado, hora_encontrada = self.extraer_dia_y_hora(texto_strip)
        
        if dia_encontrado or hora_encontrada:
            # Si encontró día u hora, guardar en contexto y continuar flujo
            context_data = estado.get("context_data", {})
            if dia_encontrado:
                context_data["dia"] = dia_encontrado
            if hora_encontrada:
                context_data["hora"] = hora_encontrada
            estado["context_data"] = context_data
            
            # Verificar qué información ya tiene el usuario
            tiene_nombre = context_data.get("nombre")
            tiene_servicio = context_data.get("servicio")
            
            if not tiene_nombre:
                # No tiene nombre, iniciar flujo normal pero con día/hora ya guardados
                mensaje_bienvenida = "hola soy la demo asistente "
                if dia_encontrado and hora_encontrada:
                    mensaje_bienvenida += f"anoté {dia_encontrado.capitalize()} a las {hora_encontrada}. "
                elif dia_encontrado:
                    mensaje_bienvenida += f"anoté {dia_encontrado.capitalize()}. "
                elif hora_encontrada:
                    mensaje_bienvenida += f"anoté la hora {hora_encontrada}. "
                
                mensaje_bienvenida += "decime tu nombre y apellido para iniciar la agenda"
                
                estado["state"] = "solicitando_nombre_completo"
                self.set_waiting_for(numero, "flujo_nombre_completo")
                
                if self.id_chat:
                    self.chat_service.registrar_mensaje(self.id_chat, mensaje_bienvenida, es_cliente=False)
                
                return enviar_mensaje_whatsapp(numero, mensaje_bienvenida)
            elif not tiene_servicio:
                # Tiene nombre pero no servicio
                estado["state"] = "solicitando_servicio"
                self.set_waiting_for(numero, "flujo_servicio")
                mensaje = "¿Qué servicio querés reservar?\n\nEscribí:\n• *Corte de pelo*\n• *Barba*\n• *Corte + Barba*"
                return enviar_mensaje_whatsapp(numero, mensaje)
            elif dia_encontrado and hora_encontrada:
                # Tiene todo, mostrar resumen directamente
                return self.mostrar_resumen_directo(numero, context_data)
            elif dia_encontrado:
                # Tiene día pero falta hora
                estado["state"] = "solicitando_dia_hora"
                self.set_waiting_for(numero, "flujo_dia_hora")
                mensaje = f"✅ {dia_encontrado.capitalize()} anotado 📅\n\n¿A qué hora querés reservar?\n\nEscribí la hora (ejemplo: 14:30)"
                return enviar_mensaje_whatsapp(numero, mensaje)
            elif hora_encontrada:
                # Tiene hora pero falta día
                estado["state"] = "solicitando_dia_hora"
                self.set_waiting_for(numero, "flujo_dia_hora")
                mensaje = f"✅ Hora {hora_encontrada} anotada 🕐\n\n¿Para qué día querés reservar?\n\nEscribí el día y la hora juntos (ejemplo: jueves {hora_encontrada})"
                return enviar_mensaje_whatsapp(numero, mensaje)
        
        # Si no hay waiting_for, iniciar flujo de agendamiento
        return self.flujo_inicio(numero, texto_lower)

    def _registrar_y_enviar_mensaje(self, numero, mensaje):
        if self.id_chat:
            self.chat_service.registrar_mensaje(self.id_chat, mensaje, es_cliente=False)
        return enviar_mensaje_whatsapp(numero, mensaje)

    def extraer_dia_y_hora(self, texto):
        """Extrae día de la semana y hora del mensaje si están presentes."""
        texto_lower = texto.lower()
        dia_encontrado = None
        hora_encontrada = None
        
        # Buscar días de la semana
        dias_map = {
            "lunes": "lunes",
            "martes": "martes",
            "miercoles": "miércoles",
            "miércoles": "miércoles",
            "jueves": "jueves",
            "viernes": "viernes",
            "sabado": "sábado",
            "sábado": "sábado",
            "domingo": "domingo"
        }
        
        for dia_key, dia_valor in dias_map.items():
            if dia_key in texto_lower:
                dia_encontrado = dia_valor
                break
        
        # Buscar hora en formato HH:MM o HH MM
        # Patrón para hora: HH:MM, HH.MM, HH MM, o "a las HH:MM", "las HH"
        patrones_hora = [
            r'\b(\d{1,2}):(\d{2})\b',  # 14:30, 9:00
            r'\b(\d{1,2})\.(\d{2})\b',  # 14.30
            r'\b(\d{1,2})\s+(\d{2})\b',  # 14 30
            r'a\s+las\s+(\d{1,2}):?(\d{2})?',  # a las 14:30, a las 14
            r'las\s+(\d{1,2}):?(\d{2})?',  # las 14:30, las 14
        ]
        
        for patron in patrones_hora:
            match = re.search(patron, texto_lower)
            if match:
                horas = int(match.group(1))
                minutos = int(match.group(2)) if match.group(2) else 0
                
                if 0 <= horas <= 23 and 0 <= minutos <= 59:
                    hora_encontrada = f"{horas:02d}:{minutos:02d}"
                    break
        
        return dia_encontrado, hora_encontrada

    def flujo_inicio(self, numero, mensaje):
        """Inicia el flujo de agendamiento de citas solicitando el nombre completo."""
        estado = get_estado(numero)
        estado["state"] = "solicitando_nombre_completo"
        self.set_waiting_for(numero, "flujo_nombre_completo")
        
        mensaje_bienvenida = (
            "hola soy la demo asistente decime tu nombre y apellido para iniciar la agenda"
        )
        
        if self.id_chat:
            self.chat_service.registrar_mensaje(self.id_chat, mensaje_bienvenida, es_cliente=False)
        
        return enviar_mensaje_whatsapp(numero, mensaje_bienvenida)

    def flujo_inicio_con_dia_hora(self, numero, mensaje, dia_encontrado, hora_encontrada):
        """Inicia el flujo cuando ya se detectó día u hora en el mensaje."""
        estado = get_estado(numero)
        estado["state"] = "solicitando_nombre_completo"
        self.set_waiting_for(numero, "flujo_nombre_completo")
        
        mensaje_bienvenida = (
            "👋 ¡Hola! Soy el asistente de la barbería 💈\n\n"
            "¿Me decís tu nombre y apellido? "
        )
        
        if self.id_chat:
            self.chat_service.registrar_mensaje(self.id_chat, mensaje_bienvenida, es_cliente=False)
        
        return enviar_mensaje_whatsapp(numero, mensaje_bienvenida)

    def mostrar_resumen_directo(self, numero, context_data):
        """Muestra el resumen directamente cuando ya se tiene toda la información."""
        nombre = context_data.get("nombre", "")
        apellido = context_data.get("apellido", "")
        servicio = context_data.get("servicio", "")
        dia = context_data.get("dia", "")
        hora = context_data.get("hora", "")
        
        if not all([nombre, apellido, servicio, dia, hora]):
            # Faltan datos, continuar flujo normal
            return self.flujo_inicio(numero, "")
        
        estado = get_estado(numero)
        estado["state"] = "confirmando_cita"
        self.set_waiting_for(numero, "flujo_confirmacion_cita")
        
        mensaje_resumen = (
            "📋 *Resumen de tu turno:*\n\n"
            f"👤 *{nombre} {apellido}*\n"
            f"💈 *{servicio}*\n"
            f"📅 *{dia.capitalize()}*\n"
            f"🕐 *{hora}*\n\n"
            "¿Confirmás? (escribí *confirmar* o *si* para confirmar, *cancelar* para cancelar)"
        )
        
        if self.id_chat:
            self.chat_service.registrar_mensaje(self.id_chat, mensaje_resumen, es_cliente=False)
        
        return enviar_mensaje_whatsapp(numero, mensaje_resumen)

    def flujo_nombre_completo(self, numero, mensaje):
        """Captura el nombre completo y solicita el servicio."""
        nombre_completo = mensaje.strip()
        
        if not nombre_completo or len(nombre_completo) < 3:
            return enviar_mensaje_whatsapp(numero, "😅 Me parece muy corto. ¿Podrías escribir tu nombre completo?")
        
        # Separar nombre y apellido (tomar primera palabra como nombre, resto como apellido)
        partes = nombre_completo.split()
        if len(partes) < 2:
            return enviar_mensaje_whatsapp(numero, "😅 Necesito tu nombre y apellido. ¿Me los podés escribir juntos?")
        
        nombre = partes[0]
        apellido = " ".join(partes[1:])
        
        estado = get_estado(numero)
        estado["state"] = "solicitando_servicio"
        # Asegurar que context_data existe y actualizar correctamente
        if "context_data" not in estado:
            estado["context_data"] = {}
        estado["context_data"]["nombre"] = nombre
        estado["context_data"]["apellido"] = apellido
        self.set_waiting_for(numero, "flujo_servicio")
        
        mensaje_respuesta = (
            f"¡Perfecto, {nombre}! 👌\n\n"
            f"¿Qué servicio querés reservar?\n\n"
            "Escribí:\n"
            "• *Corte de pelo*\n"
            "• *Barba*\n"
            "• *Corte + Barba*"
        )
        
        if self.id_chat:
            self.chat_service.registrar_mensaje(self.id_chat, mensaje_respuesta, es_cliente=False)
        
        return enviar_mensaje_whatsapp(numero, mensaje_respuesta)

    def flujo_servicio(self, numero, mensaje):
        """Captura el servicio y solicita el día de la semana."""
        servicio_texto = mensaje.strip().lower()
        
        # Normalizar servicio
        servicios_map = {
            "corte de pelo": "Corte de pelo",
            "corte": "Corte de pelo",
            "pelo": "Corte de pelo",
            "barba": "Barba",
            "corte + barba": "Corte + Barba",
            "corte y barba": "Corte + Barba",
            "corte+barba": "Corte + Barba",
            "ambos": "Corte + Barba",
            "los dos": "Corte + Barba"
        }
        
        servicio = servicios_map.get(servicio_texto)
        
        if not servicio:
            return enviar_mensaje_whatsapp(
                numero,
                "😅 No entendí bien. Escribí una de estas opciones:\n\n"
                "• *Corte de pelo*\n"
                "• *Barba*\n"
                "• *Corte + Barba*"
            )
        
        estado = get_estado(numero)
        estado["state"] = "solicitando_dia_hora"
        # Asegurar que context_data existe y actualizar correctamente
        if "context_data" not in estado:
            estado["context_data"] = {}
        estado["context_data"]["servicio"] = servicio
        self.set_waiting_for(numero, "flujo_dia_hora")
        
        mensaje_respuesta = (
            f"✅ Perfecto, {servicio} 💈\n\n"
            "¿Para qué día y hora querés reservar?\n\n"
            "Escribí el día y la hora (ejemplo: jueves 14:30)"
        )
        
        if self.id_chat:
            self.chat_service.registrar_mensaje(self.id_chat, mensaje_respuesta, es_cliente=False)
        
        return enviar_mensaje_whatsapp(numero, mensaje_respuesta)

    def flujo_dia_hora(self, numero, mensaje):
        """Captura el día y hora juntos y muestra resumen para confirmar."""
        texto_strip = mensaje.strip()
        
        # Intentar extraer día y hora del mensaje
        dia_encontrado, hora_encontrada = self.extraer_dia_y_hora(texto_strip)
        
        estado = get_estado(numero)
        context_data = estado.get("context_data", {})
        
        # Si se encontró día, guardarlo
        if dia_encontrado:
            context_data["dia"] = dia_encontrado
            estado["context_data"] = context_data
        
        # Si se encontró hora, validarla y guardarla
        if hora_encontrada:
            context_data["hora"] = hora_encontrada
            estado["context_data"] = context_data
        else:
            # Intentar extraer hora del mensaje si no se detectó automáticamente
            hora = texto_strip
            try:
                partes = hora.split(":")
                if len(partes) == 2:
                    horas = int(partes[0])
                    minutos = int(partes[1])
                    if 0 <= horas <= 23 and 0 <= minutos <= 59:
                        hora_encontrada = f"{horas:02d}:{minutos:02d}"
                        context_data["hora"] = hora_encontrada
                        estado["context_data"] = context_data
            except (ValueError, IndexError):
                pass
        
        # Verificar qué falta
        dia = context_data.get("dia", "")
        hora = context_data.get("hora", "")
        
        # Si falta día
        if not dia:
            dias_validos = ["lunes", "martes", "miércoles", "miercoles", "jueves", "viernes", "sábado", "sabado", "domingo"]
            # Intentar extraer día del mensaje
            texto_lower = texto_strip.lower()
            for dia_key in ["lunes", "martes", "miercoles", "miércoles", "jueves", "viernes", "sabado", "sábado", "domingo"]:
                if dia_key in texto_lower:
                    if dia_key == "miercoles":
                        dia = "miércoles"
                    elif dia_key == "sabado":
                        dia = "sábado"
                    else:
                        dia = dia_key
                    context_data["dia"] = dia
                    estado["context_data"] = context_data
                    break
            
            if not dia:
                return enviar_mensaje_whatsapp(
                    numero,
                    "😅 No encontré el día. Escribí el día y la hora juntos:\n"
                    "Ejemplo: jueves 14:30 o lunes 09:00"
                )
        
        # Si falta hora
        if not hora:
            return enviar_mensaje_whatsapp(
                numero,
                "😅 No encontré la hora. Escribí el día y la hora juntos:\n"
                "Ejemplo: jueves 14:30 o lunes 09:00"
            )
        
        # Validar formato de hora
        try:
            partes = hora.split(":")
            if len(partes) != 2:
                raise ValueError
            
            horas_int = int(partes[0])
            minutos_int = int(partes[1])
            
            if not (0 <= horas_int <= 23) or not (0 <= minutos_int <= 59):
                raise ValueError
            
            # Formatear hora con ceros a la izquierda si es necesario
            hora_formateada = f"{horas_int:02d}:{minutos_int:02d}"
        except (ValueError, IndexError):
            return enviar_mensaje_whatsapp(
                numero,
                "😅 La hora no es válida. Escribí el día y la hora juntos:\n"
                "Ejemplo: jueves 14:30 o lunes 09:00"
            )
        
        # Actualizar hora formateada
        context_data["hora"] = hora_formateada
        estado["context_data"] = context_data
        
        # Obtener datos para el resumen
        nombre = context_data.get("nombre", "")
        apellido = context_data.get("apellido", "")
        servicio = context_data.get("servicio", "")
        
        # Normalizar día y guardarlo
        if dia == "miercoles":
            dia = "miércoles"
        elif dia == "sabado":
            dia = "sábado"
        
        # Guardar día normalizado en context_data
        context_data["dia"] = dia
        estado["context_data"] = context_data
        
        estado["state"] = "confirmando_cita"
        self.set_waiting_for(numero, "flujo_confirmacion_cita")
        
        mensaje_resumen = (
            "📋 *Resumen de tu turno:*\n\n"
            f"👤 *{nombre} {apellido}*\n"
            f"💈 *{servicio}*\n"
            f"📅 *{dia.capitalize()}*\n"
            f"🕐 *{hora_formateada}*\n\n"
            "¿Confirmás? (escribí *confirmar* o *si* para confirmar, *cancelar* para cancelar)"
        )
        
        if self.id_chat:
            self.chat_service.registrar_mensaje(self.id_chat, mensaje_resumen, es_cliente=False)
        
        return enviar_mensaje_whatsapp(numero, mensaje_resumen)

    def flujo_confirmacion_cita(self, numero, mensaje):
        """Confirma y guarda la cita en memoria."""
        texto_lower = mensaje.strip().lower()
        
        if texto_lower not in ("confirmar", "si", "sí", "confirmo", "ok"):
            if texto_lower in ("cancelar", "no", "salir"):
                self.clear_state(numero)
                return enviar_mensaje_whatsapp(numero, "❌ Turno cancelado. Escribí cualquier mensaje para comenzar de nuevo.")
            else:
                return enviar_mensaje_whatsapp(
                    numero,
                    "😅 Escribí *confirmar* o *si* para confirmar, o *cancelar* para cancelar."
                )
        
        estado = get_estado(numero)
        context_data = estado.get("context_data", {})
        
        nombre = context_data.get("nombre", "")
        apellido = context_data.get("apellido", "")
        servicio = context_data.get("servicio", "")
        dia = context_data.get("dia", "")
        hora = context_data.get("hora", "")
        
        if not all([nombre, apellido, servicio, dia, hora]):
            return enviar_mensaje_whatsapp(numero, "⚠️ Error: Faltan datos del turno. Por favor, comienza de nuevo.")
        
        # Validar si el horario ya está ocupado
        citas_existentes = get_citas(numero)
        for cita_existente in citas_existentes:
            if cita_existente.get("dia") == dia and cita_existente.get("hora") == hora:
                return enviar_mensaje_whatsapp(
                    numero,
                    f"⛔ Esa hora ya está ocupada ({dia.capitalize()} {hora}).\n\n"
                    "Por favor elegí otra hora."
                )
        
        # Guardar cita en memoria
        cita = {
            "nombre": nombre,
            "apellido": apellido,
            "servicio": servicio,
            "dia": dia,
            "hora": hora
        }
        
        add_cita(numero, cita)
        
        # Limpiar estado
        self.clear_state(numero)
        
        mensaje_confirmacion = (
            "✅ *¡Turno confirmado!* 🎉\n\n"
            f"👤 *{nombre} {apellido}*\n"
            f"💈 *{servicio}*\n"
            f"📅 *{dia.capitalize()}*\n"
            f"🕐 *{hora}*\n\n"
            "¡Te esperamos en la barbería! 💈\n\n"
            "Escribí cualquier mensaje para agendar otro turno."
        )
        
        if self.id_chat:
            self.chat_service.registrar_mensaje(self.id_chat, mensaje_confirmacion, es_cliente=False)
        
        return enviar_mensaje_whatsapp(numero, mensaje_confirmacion)

