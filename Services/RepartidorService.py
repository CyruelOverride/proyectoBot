from Util.database import get_db_connection, Pedido
from Util.coordenadas_gifs import calcular_y_generar_ruta_tanda, calcular_ruta_simple, generar_imagen_ruta_delivery
from whatsapp_api import enviar_imagen_whatsapp, enviar_mensaje_whatsapp, normalizar_numero_telefono
from Util.repartidor_util import enviar_actualizacion_repartidor
from Util.calificacion_util import enviar_solicitud_calificacion
import math
import random


def simplificar_pedido(tupla):
    return Pedido(
        idpedido=tupla[0],
        id_chat=tupla[1],
        id_cliente=tupla[2],
        id_repartidor=tupla[3],
        direccion=tupla[4],
        latitud=tupla[5],
        longitud=tupla[6],
        estado=tupla[7],
        codigo_verificacion=tupla[8],
        id_tanda=tupla[9]
    )


class RepartidorService:
    cola_tandas_pendientes = []
    repartidores_ocupados = {}
    TandasActuales = []  
    
    def __init__(self):
        pass
    
    def _obtener_info_repartidor(self, id_repartidor):
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT telefono, nombre, apellido FROM repartidor WHERE idrepartidor = %s", (id_repartidor,))
        repartidor_info = cur.fetchone()
        cur.close()
        conn.close()
        return repartidor_info
    
    def _crear_pedido_data(self, pedido):
        return {
            'latitud': pedido.latitud,
            'longitud': pedido.longitud,
            'direccion': pedido.direccion,
            'idpedido': pedido.idpedido,
            'codigo_verificacion': pedido.codigo_verificacion
        }
    
    def obtener_repartidores_disponibles(self):
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("SELECT idrepartidor, nombre, apellido FROM repartidor")
        todos_repartidores = cur.fetchall()
        
        cur.close()
        conn.close()
        
        disponibles = []
        for rep in todos_repartidores:
            id_repartidor = rep[0]
            if id_repartidor not in RepartidorService.repartidores_ocupados:
                disponibles.append(rep)
        
        return disponibles
    
    def obtener_repartidor_por_telefono(self, telefono):
        telefono = str(telefono).strip().replace("+", "")
        
        solo_digitos = "".join(ch for ch in telefono if ch.isdigit())

        conn = get_db_connection()
        cur = conn.cursor()

        cur.execute("""
            SELECT idrepartidor, telefono
            FROM repartidor
            WHERE REPLACE(REPLACE(REPLACE(telefono, '+', ''), ' ', ''), '-', '') LIKE %s
            LIMIT 1
        """, (f"%{solo_digitos}",))

        resultado = cur.fetchone()

        cur.close()
        conn.close()

        if resultado:
            print(f"[debug] Repartidor encontrado: DB={resultado[1]} input={solo_digitos}")
            return {"id": resultado[0]}

        print(f"[debug] No se encontró repartidor para número limpio={solo_digitos}")
        return None
    
    def asignar_tanda_a_repartidor(self, tanda, id_repartidor):
        conn = get_db_connection()
        cur = conn.cursor()
        
        pedidos_ordenados = self.ordenar_pedidos_por_cercania_restaurante(tanda["pedidos"])
        tanda["pedidos"] = pedidos_ordenados
        
        for pedido in tanda["pedidos"]:
            cur.execute(
                "UPDATE pedido SET id_repartidor = %s WHERE idpedido = %s",
                (id_repartidor, pedido.idpedido)
            )
        
        conn.commit()
        cur.close()
        conn.close()
        
        repartidor_info = self._obtener_info_repartidor(id_repartidor)
        
        RepartidorService.repartidores_ocupados[id_repartidor] = tanda["id"]
        
        pedidos_ids = [pedido.idpedido for pedido in tanda["pedidos"]]
        RepartidorService.TandasActuales.append({
            "id_repartidor": id_repartidor,
            "id_tanda": tanda["id"],
            "pedidos_ids": pedidos_ids
        })
        
        nombre_repartidor_completo = f"{repartidor_info[1]} {repartidor_info[2]}" if repartidor_info else "N/A"
        print(f"Repartidor {id_repartidor} ({nombre_repartidor_completo}) asignado a Tanda {tanda['id']} (Zona: {tanda['zona']})")
        
        try:
            if repartidor_info:
                telefono_repartidor = repartidor_info[0]
                nombre_repartidor = f"{repartidor_info[1]} {repartidor_info[2]}"
                
                primer_pedido = tanda["pedidos"][0]
                
                print(f"\n Generando ruta para {nombre_repartidor}...")
                
                pedido_data = [self._crear_pedido_data(primer_pedido)]
                ruta_imagen, info_ruta = calcular_y_generar_ruta_tanda(pedido_data, tanda["id"], ubicacion_origen=None)
                
                mensaje = f"Nueva Tanda Asignada #{tanda['id']}\n\n"
                mensaje += f"Pedido #{primer_pedido.idpedido}\n"
                mensaje += f"{primer_pedido.direccion}\n\n"
                mensaje += f"Distancia: {info_ruta['distancia_km']} km\n"
                mensaje += f"Tiempo estimado: {int(info_ruta['tiempo_min'])} min\n"
                mensaje += f"Zona: {tanda['zona']}\n\n"
                mensaje += f"Código de verificación: {primer_pedido.codigo_verificacion}\n\n"
                mensaje += f"Kick buttowski"
                
                pedido_para_menu = {
                    'idpedido': primer_pedido.idpedido,
                    'direccion': primer_pedido.direccion,
                    'codigo_verificacion': primer_pedido.codigo_verificacion
                }

                enviar_actualizacion_repartidor(
                    telefono_repartidor,
                    pedido_para_menu,
                    ruta_imagen,
                    mensaje
                )
                
                mensaje_cliente = (
                    f"🚚 Tu pedido está en camino!\n\n"
                    f"Pedido #{primer_pedido.idpedido}\n"
                    f"{primer_pedido.direccion}\n"
                    f"Llega en: {int(info_ruta['tiempo_min'])} minutos\n\n"
                    f"Código de verificación: {primer_pedido.codigo_verificacion}"
                )
                enviar_mensaje_whatsapp(primer_pedido.id_chat, mensaje_cliente)
                print(f"Cliente notificado: {primer_pedido.id_chat}")
                
                self.registrar_recorrido(id_repartidor, info_ruta['distancia_km'])
                
        except Exception as e:
            print(f" Error calculando/enviando ruta: {e}")
        return True
    
    def asignar_tanda(self, tanda):
        repartidores_disponibles = self.obtener_repartidores_disponibles()
        
        if len(repartidores_disponibles) > 0:
            repartidor_elegido = random.choice(repartidores_disponibles)
            id_repartidor = repartidor_elegido[0]
            print(f"Asignando Tanda {tanda['id']} a repartidor {id_repartidor} (disponibles: {len(repartidores_disponibles)})")
            self.asignar_tanda_a_repartidor(tanda, id_repartidor)
            return True
        else:
            RepartidorService.cola_tandas_pendientes.append(tanda)
            print(f"Tanda {tanda['id']} encolada (sin repartidores disponibles)")
            
            return self.asignar_tanda_aleatoria(tanda)
    
    def asignar_tanda_aleatoria(self, tanda):
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("SELECT idrepartidor FROM repartidor")
        todos_repartidores = cur.fetchall()
        
        cur.close()
        conn.close()
        
        if len(todos_repartidores) == 0:
            return False
        
        repartidor_elegido = random.choice(todos_repartidores)
        id_repartidor = repartidor_elegido[0]
        
        self.asignar_tanda_a_repartidor(tanda, id_repartidor)
        print(f" Tanda {tanda['id']} asignada aleatoriamente a repartidor {id_repartidor}")
        return True
    
    def finalizar_tanda(self, id_repartidor):
        if id_repartidor in RepartidorService.repartidores_ocupados:
            tanda_id = RepartidorService.repartidores_ocupados[id_repartidor]
            del RepartidorService.repartidores_ocupados[id_repartidor]
            
            RepartidorService.TandasActuales = [
                tanda for tanda in RepartidorService.TandasActuales 
                if tanda["id_repartidor"] != id_repartidor
            ]
            
            print(f" Tanda {tanda_id} finalizada para repartidor {id_repartidor}")
            
            if len(RepartidorService.cola_tandas_pendientes) > 0:
                siguiente_tanda = RepartidorService.cola_tandas_pendientes.pop(0)
                self.asignar_tanda(siguiente_tanda)
    
    def obtener_tandas_pendientes(self):
        return len(RepartidorService.cola_tandas_pendientes)
    
    def obtener_proximo_pedido(self, tanda_id):
        tanda_actual = None
        for tanda in RepartidorService.TandasActuales:
            if tanda["id_tanda"] == tanda_id:
                tanda_actual = tanda
                break
        
        if not tanda_actual or not tanda_actual["pedidos_ids"]:
            return None
        
        id_pedido = tanda_actual["pedidos_ids"][0]
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT idpedido, id_chat, id_cliente, id_repartidor, direccion, 
                   latitud, longitud, estado, codigo_verificacion, id_tanda
            FROM pedido 
            WHERE idpedido = %s
        """, (id_pedido,))
        
        resultado = cur.fetchone()
        cur.close()
        conn.close()
        
        if resultado:
            return simplificar_pedido(resultado)
        return None
    
    def obtener_info_pedido(self, id_pedido):
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT codigo_verificacion, id_tanda, id_chat, id_cliente, latitud, longitud 
            FROM pedido 
            WHERE idpedido = %s
        """, (id_pedido,))
        pedido_info = cur.fetchone()
        
        cur.close()
        conn.close()
        
        if not pedido_info:
            return None
        
        codigo_correcto, tanda_id, id_chat, id_cliente, lat_actual, lon_actual = pedido_info
        return {
            'codigo_verificacion': codigo_correcto,
            'id_tanda': tanda_id,
            'id_chat': id_chat,
            'id_cliente': id_cliente,
            'latitud': lat_actual,
            'longitud': lon_actual
        }
    
    def validar_codigo(self, codigo_ingresado, codigo_correcto):
        return int(codigo_ingresado) == int(codigo_correcto)
    
    def marcar_como_entregado(self, id_pedido):
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("UPDATE pedido SET estado = 'entregado' WHERE idpedido = %s", (id_pedido,))
        conn.commit()
        
        cur.close()
        conn.close()
        
        print(f"Pedido {id_pedido} entregado")
        return True
    
    def enviar_calificacion(self, id_chat):
        numero_cliente = id_chat.replace("chat_", "").strip() if id_chat and id_chat.startswith("chat_") else (id_chat.strip() if id_chat else None)
        
        if not numero_cliente:
            return
        
        try:
            numero_cliente_normalizado = normalizar_numero_telefono(numero_cliente)
            print(f"Enviando solicitud de calificación a {numero_cliente_normalizado}...")
            resultado = enviar_solicitud_calificacion(numero_cliente_normalizado)
            if resultado and not resultado.get("success"):
                print(f"Error al enviar calificación: {resultado.get('error')}")
        except Exception as e:
            print(f"Error al enviar solicitud de calificación: {e}")
    
    def actualizar_tanda(self, id_repartidor, tanda_id, id_pedido):
        tanda_actual = None
        for tanda in RepartidorService.TandasActuales:
            if tanda["id_tanda"] == tanda_id and tanda["id_repartidor"] == id_repartidor:
                tanda_actual = tanda
                if id_pedido in tanda["pedidos_ids"]:
                    tanda["pedidos_ids"].remove(id_pedido)
                break
        
        pedidos_restantes = tanda_actual["pedidos_ids"] if tanda_actual else []
        return tanda_actual, pedidos_restantes
    
    def enviar_ruta_al_restaurante(self, id_repartidor, tanda_id, lat_actual, lon_actual):
        repartidor_info = self._obtener_info_repartidor(id_repartidor)
        
        if not repartidor_info:
            return
        
        try:
            from Util.coordenadas_gifs import RESTAURANTE_LAT, RESTAURANTE_LON
            restaurante_data = [{
                'latitud': RESTAURANTE_LAT,
                'longitud': RESTAURANTE_LON,
                'direccion': 'Restaurante',
                'idpedido': 0
            }]
            
            ubicacion_origen = (float(lat_actual), float(lon_actual))
            ruta_imagen, info_ruta = calcular_y_generar_ruta_tanda(
                restaurante_data, 
                tanda_id, 
                ubicacion_origen=ubicacion_origen
            )
            
            telefono_repartidor = repartidor_info[0]
            mensaje_restaurante = (
                f"🎉 Tanda #{tanda_id} Completada sos un crack kick buttowski "
                f"✅ Todos los pedidos entregados"
                f"📍 Ruta de regreso al restaurante:"
                f"Distancia: {info_ruta['distancia_km']} km"
                f"Tiempo estimado: {int(info_ruta['tiempo_min'])} min"
                f"Vuelve a casa patada culowoski!!!!! "
            )
            
            enviar_imagen_whatsapp(telefono_repartidor, ruta_imagen, mensaje_restaurante)
            print(f"Ruta al restaurante enviada a repartidor {id_repartidor}")
            
        except Exception as e:
            print(f"Error generando/enviando ruta al restaurante: {e}")
    
    def enviar_siguiente_pedido(self, id_repartidor, tanda_id, id_pedido_entregado, lat_actual, lon_actual):
        proximo_pedido = self.obtener_proximo_pedido(tanda_id)
        
        if not proximo_pedido:
            return {"success": True, "mensaje": "No hay más pedidos", "tanda_finalizada": True}
        
        _, distancia_km, tiempo_min = calcular_ruta_simple(
            float(lat_actual), float(lon_actual),
            float(proximo_pedido.latitud), float(proximo_pedido.longitud)
        )
        
        mensaje_cliente = (
            f"Tu pedido está en camino!\n\n"
            f"Pedido #{proximo_pedido.idpedido}\n"
            f"{proximo_pedido.direccion}\n"
            f"Llega en: {int(tiempo_min)} minutos\n\n"
            f"Código de verificación: {proximo_pedido.codigo_verificacion}"
        )
        
        enviar_mensaje_whatsapp(proximo_pedido.id_chat, mensaje_cliente)
        print(f"Cliente notificado: {proximo_pedido.id_chat}")
        
        repartidor_info = self._obtener_info_repartidor(id_repartidor)
        
        if repartidor_info:
            pedido_data = [self._crear_pedido_data(proximo_pedido)]
            
            ubicacion_origen = (float(lat_actual), float(lon_actual))
            ruta_imagen, info_ruta = calcular_y_generar_ruta_tanda(pedido_data, tanda_id, ubicacion_origen=ubicacion_origen)
            
            telefono_repartidor = repartidor_info[0]
            
            mensaje_rep = (
                f"Tanda #{tanda_id} - Próximo Pedido\n\n"
                f"✅ Entregado: Pedido #{id_pedido_entregado}\n\n"
                f"📦 Siguiente: Pedido #{proximo_pedido.idpedido}\n"
                f"{proximo_pedido.direccion}\n\n"
                f"Distancia: {info_ruta['distancia_km']} km\n"
                f"Tiempo estimado: {int(info_ruta['tiempo_min'])} min\n\n"
                f"Código de verificación: {proximo_pedido.codigo_verificacion}"
            )
            
            pedido_para_menu = {
                'idpedido': proximo_pedido.idpedido,
                'direccion': proximo_pedido.direccion,
                'codigo_verificacion': proximo_pedido.codigo_verificacion
            }
            
            enviar_actualizacion_repartidor(
                telefono_repartidor,
                pedido_para_menu,
                ruta_imagen,
                mensaje_rep
            )
        
        return {
            "success": True,
            "mensaje": "Entrega confirmada",
            "proximo_pedido": proximo_pedido.idpedido,
            "eta_minutos": int(tiempo_min)
        }
    
    def confirmar_entrega(self, id_repartidor, id_pedido, codigo_ingresado):
        pedido_info = self.obtener_info_pedido(id_pedido)
        if not pedido_info:
            return {"success": False, "mensaje": "Pedido no encontrado"}
        
        codigo_correcto = pedido_info['codigo_verificacion']
        tanda_id = pedido_info['id_tanda']
        id_chat = pedido_info['id_chat']
        lat_actual = float(pedido_info['latitud'])
        lon_actual = float(pedido_info['longitud'])
        
        if not self.validar_codigo(codigo_ingresado, codigo_correcto):
            return {"success": False, "mensaje": "Código incorrecto"}
        
        self.marcar_como_entregado(id_pedido)
        
        self.enviar_calificacion(id_chat)
        
        tanda_actual, pedidos_restantes = self.actualizar_tanda(id_repartidor, tanda_id, id_pedido)
        
        if not tanda_actual or not pedidos_restantes:
            print(f"Tanda {tanda_id} completada")
            self.enviar_ruta_al_restaurante(id_repartidor, tanda_id, lat_actual, lon_actual)
            self.finalizar_tanda(id_repartidor)
            return {"success": True, "mensaje": "Tanda completada", "tanda_finalizada": True}
        
        resultado = self.enviar_siguiente_pedido(id_repartidor, tanda_id, id_pedido, lat_actual, lon_actual)
        return resultado


    def registrar_recorrido(self, id_repartidor, km):
        km = float(km)  

        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            "UPDATE repartidor SET cantidadkmrecorridos = cantidadkmrecorridos + %s WHERE idrepartidor = %s",
            (km, id_repartidor)
        )
        conn.commit()
        cur.close()
        conn.close()

    def distancia_haversine(self, lat1, lon1, lat2, lon2):
        R = 6371.0
        
        lat1_rad = math.radians(float(lat1))
        lon1_rad = math.radians(float(lon1))
        lat2_rad = math.radians(float(lat2))
        lon2_rad = math.radians(float(lon2))
        
        dlat = lat2_rad - lat1_rad
        dlon = lon2_rad - lon1_rad
        
        a = math.sin(dlat / 2)**2 + math.cos(lat1_rad) * math.cos(lat2_rad) * math.sin(dlon / 2)**2
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        
        distancia = R * c
        return distancia
    
    def ordenar_pedidos_por_cercania_restaurante(self, pedidos):
        from Util.coordenadas_gifs import RESTAURANTE_LAT, RESTAURANTE_LON
        
        def obtener_distancia(pedido):
            if hasattr(pedido, 'latitud') and hasattr(pedido, 'longitud'):
                lat = float(pedido.latitud)
                lon = float(pedido.longitud)
            else:
                lat = float(pedido.get('latitud', pedido.get('lat', 0)))
                lon = float(pedido.get('longitud', pedido.get('lon', 0)))
            
            return self.distancia_haversine(RESTAURANTE_LAT, RESTAURANTE_LON, lat, lon)
        
        pedidos_ordenados = sorted(pedidos, key=obtener_distancia)
        return pedidos_ordenados
    
    def calcular_km_ruta(self, id_repartidor, lista_pedidos):
        from Util.database import get_db_connection
        from Util.coordenadas_gifs import RESTAURANTE_LAT, RESTAURANTE_LON
        
        if not lista_pedidos:
            return 0
        
        conn = get_db_connection()
        cur = conn.cursor()
        
        centro_lat = RESTAURANTE_LAT
        centro_lon = RESTAURANTE_LON
        
        total_km = 0
        lat_anterior = centro_lat
        lon_anterior = centro_lon
        
        for id_pedido, lat, lon in lista_pedidos:
            km = RepartidorService.distancia_haversine(lat_anterior, lon_anterior, lat, lon)
            total_km += km
            lat_anterior = lat
            lon_anterior = lon
        
        cur.close()
        conn.close()
        return total_km
