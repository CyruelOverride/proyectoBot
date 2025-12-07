from Util.database import get_db_session
from Services.PedidoService import PedidosService
from Services.ProductoService import ProductosService
from Models.chat import Chat


def crear_bot_instancia():
    """
    ⚠️ ADVERTENCIA: Esta función crea una sesión de DB que nunca se cierra.
    Solo usar para testing rápido. En producción, usar webhook_server.py
    que maneja las sesiones correctamente.
    """
    db_session = get_db_session()
    
    pedido_service = PedidosService(db_session)
    producto_service = ProductosService()
    
    bot = Chat(
        pedido_service=pedido_service,
        producto_service=producto_service
    )
    
    return bot  


# ⚠️ Esta sesión permanece abierta - solo para testing
bot = crear_bot_instancia()


if __name__ == "__main__":
    print("Bot gordura ok")
    print(f" Estado del bot: {bot}")
