from whatsapp_api import enviar_mensaje_whatsapp, normalizar_numero_telefono
from Util.database import get_db_session, Calificaciones, ClientesCalificaciones, Cliente
from sqlmodel import Session, select
from sqlalchemy import text

def enviar_solicitud_calificacion(numero_cliente):
    numero_cliente_normalizado = normalizar_numero_telefono(numero_cliente)
    
    rows = [
        {
            "id": "calificar_1",
            "title": "⭐ 1 estrella",
            "description": "Muy malo"
        },
        {
            "id": "calificar_2",
            "title": "⭐⭐ 2 estrellas",
            "description": "Malo"
        },
        {
            "id": "calificar_3",
            "title": "⭐⭐⭐ 3 estrellas",
            "description": "Regular"
        },
        {
            "id": "calificar_4",
            "title": "⭐⭐⭐⭐ 4 estrellas",
            "description": "Bueno"
        },
        {
            "id": "calificar_5",
            "title": "⭐⭐⭐⭐⭐ 5 estrellas",
            "description": "Excelente"
        }
    ]
    
    payload = {
        "messaging_product": "whatsapp",
        "to": numero_cliente_normalizado,
        "type": "interactive",
        "interactive": {
            "type": "list",
            "header": {
                "type": "text",
                "text": "⭐ Califica nuestro servicio"
            },
            "body": {
                "text": "¿Cómo calificarías nuestro servicio?"
            },
            "footer": {
                "text": "Selecciona una opción"
            },
            "action": {
                "button": "Ver opciones",
                "sections": [{
                    "title": "Calificación",
                    "rows": rows
                }]
            }
        }
    }
    
    resultado = enviar_mensaje_whatsapp(numero_cliente_normalizado, payload)
    return resultado


def manejar_calificacion(numero, calificacion_id):
  
    try:
      
        partes = calificacion_id.split("_")
        if len(partes) < 2:
            return enviar_mensaje_whatsapp(numero, "Error al procesar la calificación. Por favor, intenta nuevamente.")
        
        estrellas = int(partes[1])  
        
        if estrellas < 1 or estrellas > 5:
            return enviar_mensaje_whatsapp(numero, "Calificación inválida. Por favor, selecciona entre 1 y 5 estrellas.")
        
        db = get_db_session()
        try:
            numero_limpio = numero.strip().replace("+", "").replace(" ", "").replace("-", "")
            
            resultado = db.execute(
                text("SELECT idcliente FROM cliente WHERE REPLACE(REPLACE(REPLACE(telefono, '+', ''), ' ', ''), '-', '') LIKE :numero LIMIT 1"),
                {"numero": f"%{numero_limpio}%"}
            ).fetchone()
            
            if not resultado:
                print(f"Cliente no encontrado para número: {numero_limpio}")
                return enviar_mensaje_whatsapp(numero, "Cliente no encontrado.")
            
            id_cliente = resultado[0]
            
            cliente = db.query(Cliente).filter(Cliente.idcliente == id_cliente).first()
            if not cliente:
                print(f"Cliente con ID {id_cliente} no encontrado después de la búsqueda")
                return enviar_mensaje_whatsapp(numero, "Cliente no encontrado.")
            
            
            calificacion = Calificaciones(
                estrellas=estrellas
            )
            db.add(calificacion)
            db.commit()
            db.refresh(calificacion)
            
            usuario_calificacion = ClientesCalificaciones(
                id_calificacion=calificacion.id_calificacion,
                id_cliente=id_cliente
            )
            db.add(usuario_calificacion)
            db.commit()
            
            print(f"Calificación guardada: {estrellas} estrellas para cliente {id_cliente}")
            
            mensaje_agradecimiento = f"Gracias por tu calificación de {estrellas} {'⭐' * estrellas} gordo comilon! Tu opinión me importa... Te juro!"
            return enviar_mensaje_whatsapp(numero, mensaje_agradecimiento)
            
        except Exception as e:
            db.rollback()
            print(f"Error al guardar calificación: {type(e).__name__} → {e}")
            import traceback
            traceback.print_exc()
            return enviar_mensaje_whatsapp(numero, "Hubo un error al guardar tu calificación. Por favor, intenta nuevamente.")
        finally:
            db.close()
            
    except Exception as e:
        print(f"Error inesperado en manejar_calificacion: {e}")
        return enviar_mensaje_whatsapp(numero, "Hubo un error inesperado. Por favor, intenta nuevamente.")

