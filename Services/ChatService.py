from Util.database import get_db_session, Chat, Mensaje, Cliente
from typing import Optional
from datetime import datetime


class ChatService:
    def __init__(self, db_session):
        self.db = db_session
    
    def crear_chat(self, id_cliente: int, id_chat: str) -> Chat:
        chat = Chat(
            id_chat=id_chat,
            id_cliente=id_cliente,
            fecha_creacion=datetime.now()
        )
        self.db.add(chat)
        self.db.commit()
        self.db.refresh(chat)
        return chat
    
    def obtener_chat_por_id_chat(self, id_chat: str) -> Optional[Chat]:
        return self.db.query(Chat).filter(Chat.id_chat == id_chat).first()
    
    def obtener_chat_por_telefono(self, telefono: str) -> Optional[Chat]:
        id_chat = f"chat_{telefono}"
        return self.obtener_chat_por_id_chat(id_chat)
    
    def obtener_o_crear_chat(self, id_cliente: int, telefono: str) -> Chat:
        id_chat = f"chat_{telefono}"
        chat = self.obtener_chat_por_id_chat(id_chat)
        
        if not chat:
            chat = self.crear_chat(id_cliente, id_chat)
        
        return chat
    
    def registrar_mensaje(self, id_chat: str, contenido: str, es_cliente: bool = True) -> Mensaje:
        mensaje = Mensaje(
            id_chat=id_chat,
            contenido=contenido,
            es_cliente=es_cliente,
            fecha_envio=datetime.now()
        )
        self.db.add(mensaje)
        self.db.commit()
        self.db.refresh(mensaje)
        return mensaje
    
    
    def obtener_chat_con_cliente(self, id_chat: str) -> Optional[Chat]:
        return self.db.query(Chat).filter(Chat.id_chat == id_chat).first()

