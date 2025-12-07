from whatsapp_api import enviar_mensaje_whatsapp, enviar_imagen_whatsapp
from Util.database import get_db_connection

def obtener_pedidos_pendientes_repartidor(id_repartidor):
    from Services.RepartidorService import RepartidorService
    
    tandas_repartidor = [
        tanda for tanda in RepartidorService.TandasActuales
        if tanda["id_repartidor"] == id_repartidor
    ]
    
    pedidos_ids = []
    for tanda in tandas_repartidor:
        pedidos_ids.extend(tanda["pedidos_ids"])
    
    if not pedidos_ids:
        return []
    
    conn = get_db_connection()
    cur = conn.cursor()
    
    placeholders = ','.join(['%s'] * len(pedidos_ids))
    cur.execute(f"""
        SELECT idpedido, direccion 
        FROM pedido 
        WHERE idpedido IN ({placeholders})
        ORDER BY idpedido
    """, tuple(pedidos_ids))
    
    resultados = cur.fetchall()
    cur.close()
    conn.close()
    
    pedidos = []
    for row in resultados:
        pedidos.append({
            'idpedido': row[0],
            'direccion': row[1]
        })
    
    return pedidos

def menu_pedidos_repartidor(numero, pedidos):
    rows = []

    for p in pedidos:
        rows.append({
            "id": f"pedido_{p['idpedido']}",
            "title": f"Pedido #{p['idpedido']}",
            "description": p["direccion"]
        })

    secciones = [{
        "title": "Pedidos Pendientes",
        "rows": rows
    }]

    payload = {
        "messaging_product": "whatsapp",
        "to": numero,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "header": {"type": "text", "text": "📦 Tus pedidos pendientes"},
            "body": {"text": "Elegí el pedido que acabás de entregar:"},
            "footer": {"text": "Seleccioná un pedido"},
            "action": {"button": "Ver pedidos", "sections": secciones},
        },
    }

    return enviar_mensaje_whatsapp(numero, payload)

def handle_interactive(numero, interactive):
    if interactive["type"] == "list_reply":
        seleccion = interactive["list_reply"]["id"]
        return manejar_seleccion_pedido(numero, seleccion)
    elif interactive["type"] == "button_reply":
        seleccion = interactive["button_reply"]["id"]
        return manejar_seleccion_pedido(numero, seleccion)
    return None

def manejar_seleccion_pedido(numero, seleccion_id):
    from Services.RepartidorService import RepartidorService
    
    if seleccion_id.startswith("entregado_"):
        id_pedido = int(seleccion_id.replace("entregado_", ""))
    else:
        id_pedido = int(seleccion_id.replace("pedido_", ""))

    repartidor_service = RepartidorService()
    repartidor = repartidor_service.obtener_repartidor_por_telefono(numero)

    if not repartidor:
        return enviar_mensaje_whatsapp(numero, "No estás registrado como repartidor.")

    conn = get_db_connection()
    cur = conn.cursor()
    cur.execute("SELECT codigo_verificacion FROM pedido WHERE idpedido = %s", (id_pedido,))
    row = cur.fetchone()
    cur.close()
    conn.close()

    if not row:
        return enviar_mensaje_whatsapp(numero, "Pedido no encontrado.")

    codigo = row[0]

    resultado = RepartidorService().confirmar_entrega(
        repartidor["id"], id_pedido, codigo
    )
    
    return None

def enviar_actualizacion_repartidor(telefono, pedido, ruta_imagen, mensaje):
    if ruta_imagen:
        enviar_imagen_whatsapp(telefono, ruta_imagen, mensaje)

    if not pedido:
        enviar_mensaje_whatsapp(telefono, "No tenés más pedidos pendientes Flander🙌")
        return

    payload = {
        "messaging_product": "whatsapp",
        "to": telefono,
        "type": "interactive",
        "interactive": {
            "type": "button",
            "header": {"type": "text", "text": f"📦 Pedido #{pedido['idpedido']}"},
            "body": {
                "text": f"{pedido.get('direccion', 'Sin dirección')}\n\nCódigo: {pedido.get('codigo_verificacion', 'N/A')}\n\nPresioná 'Entregado' cuando completes la entrega:"
            },
            "footer": {"text": "Confirmá la entrega"},
            "action": {
                "buttons": [{
                    "type": "reply",
                    "reply": {
                        "id": f"entregado_{pedido['idpedido']}",
                        "title": "✅ Entregado"
                    }
                }]
            }
        },
    }

    enviar_mensaje_whatsapp(telefono, payload)
