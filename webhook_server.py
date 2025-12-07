from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
import traceback
from Models.chat import Chat
from Services.ChatService import ChatService
from Services.ClienteService import ClienteService
from Util.database import get_db_session, init_db, engine
from sqlmodel import text
from whatsapp_api import procesar_mensaje_recibido, WHATSAPP_PHONE_NUMBER_ID
from seed_database import main as seed_main

app = FastAPI()
VERIFY_TOKEN = "Chacalitas2025"

@app.on_event("startup")
async def startup_event():
    try:
        with engine.connect() as conn:
            result = conn.execute(text("""
                SELECT EXISTS (
                    SELECT FROM information_schema.tables 
                    WHERE table_schema = 'public' 
                    AND table_name = 'cliente'
                );
            """))
            tabla_existe = result.scalar()
        
        if not tabla_existe:
            print("🔄 Tablas no encontradas. Inicializando base de datos...")
            init_db()
            print("✅ Tablas creadas correctamente")
            
            print("🌱 Ejecutando seeding de datos iniciales...")
            try:
                seed_main()
            except Exception as e:
                print(f"⚠️ Error en seeding automático: {e}")
                print("💡 Puedes ejecutar el seeding manualmente visitando /seed-db")
        else:
            print("✅ Base de datos ya inicializada")
        
        print("🚀 Sistema de agendamiento de citas inicializado")
        
    except Exception as e:
        print(f"⚠️ Error al verificar/inicializar base de datos: {e}")
        print("💡 Puedes inicializar manualmente visitando /init-db")


@app.get("/")
async def root():
    return {
        "message": "WhatsApp Webhook Server funcionando",
        "phone_number_id": WHATSAPP_PHONE_NUMBER_ID,
        "endpoints": {
            "webhook": "/webhook",
            "health": "/health",
            "init_db": "/init-db",
            "seed_db": "/seed-db"
        },
    }


@app.get("/health")
async def health():
    return {"status": "ok"}


@app.get("/init-db")
async def init_database():
    """Endpoint para inicializar las tablas manualmente (si no se inicializaron automáticamente)."""
    try:
        init_db()
        return {
            "status": "success",
            "message": "✅ Tablas creadas correctamente",
            "tablas": [
                "categoria", "producto", "cliente", "repartidor",
                "chat", "mensaje", "pedido", "detalle_pedido"
            ]
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"❌ Error al inicializar: {str(e)}"
        }


@app.get("/seed-db")
async def seed_database():
    """Endpoint para poblar la base de datos con datos de prueba (categorías, productos, repartidores)."""
    try:
        seed_main()
        return {
            "status": "success",
            "message": "✅ Seeding completado exitosamente",
            "datos": {
                "categorias": 8,
                "productos": "32+ productos",
                "repartidores": 6
            }
        }
    except Exception as e:
        return {
            "status": "error",
            "message": f"❌ Error en seeding: {str(e)}"
        }


@app.get("/webhook")
async def verify(request: Request):
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode == "subscribe" and token == VERIFY_TOKEN:
        return PlainTextResponse(challenge)
    return PlainTextResponse("Token inválido", status_code=403)


@app.post("/webhook")
async def receive(request: Request):
    db_session = None
    try:
        data = await request.json()
        resultado = procesar_mensaje_recibido(data)

        if not resultado:
            return PlainTextResponse("EVENT_RECEIVED", status_code=200)

        numero, mensaje, tipo = resultado
        print(f"Mensaje recibido ({tipo}) de {numero}: {mensaje}")

        # Crear sesión de DB
        db_session = get_db_session()
        
        try:
            chat_service = ChatService(db_session)
            
            id_cliente = ClienteService.obtener_o_crear_cliente("", "", numero)
            
            chat_bd = chat_service.obtener_o_crear_chat(id_cliente, numero)
            id_chat = chat_bd.id_chat
            
            if tipo in ("text", "interactive"):
                chat_service.registrar_mensaje(id_chat, mensaje, es_cliente=True)
            
            chat = Chat(
                id_chat=id_chat,
                id_cliente=id_cliente,
                chat_service=chat_service
            )

            if tipo in ("text", "interactive"):
                chat.handle_text(numero, mensaje)
            else:
                chat.handle_text(numero, "Tipo de mensaje no soportado aún.")

            return PlainTextResponse("EVENT_RECEIVED", status_code=200)
        
        finally:
            # ✅ IMPORTANTE: Cerrar la sesión siempre
            if db_session:
                db_session.close()
                print("🔒 Sesión de DB cerrada")

    except Exception:
        traceback.print_exc()
        # Cerrar sesión en caso de error también
        if db_session:
            db_session.close()
            print("🔒 Sesión de DB cerrada (después de error)")
        return PlainTextResponse("ERROR", status_code=500)