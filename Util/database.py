import logging
import os
import psycopg2
from typing import Optional
from datetime import datetime
from sqlmodel import SQLModel, create_engine, Session, Field

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg2://postgres:Raboloko18!@localhost:5432/obligatorio_algoritmos"
)

if DATABASE_URL.startswith("postgresql://") and "+psycopg2" not in DATABASE_URL:
    DATABASE_URL = DATABASE_URL.replace("postgresql://", "postgresql+psycopg2://", 1)

engine = create_engine(DATABASE_URL, echo=True)

logger = logging.getLogger("database")

class Categoria(SQLModel, table=True):
    id_categoria: Optional[int] = Field(default=None, primary_key=True)
    nombre: str

class Producto(SQLModel, table=True):
    idproducto: Optional[int] = Field(default=None, primary_key=True)
    nombre: str
    precio: float
    id_categoria: Optional[int] = Field(default=None, foreign_key="categoria.id_categoria")


class Pedido(SQLModel, table=True):
    idpedido: Optional[int] = Field(default=None, primary_key=True)
    id_chat: str
    id_cliente: str
    id_repartidor: Optional[int] = None
    direccion: str
    latitud: Optional[str] = None
    longitud: Optional[str] = None
    estado: str = Field(default="en_carrito")
    fecha_confirmacion: Optional[datetime] = None
    zona: Optional[str] = None 
    codigo_verificacion: Optional[int] = None  
    id_tanda: Optional[int] = None 


class DetallePedido(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    id_pedido: int = Field(foreign_key="pedido.idpedido")
    id_producto: int = Field(foreign_key="producto.idproducto")
    cantidad: int


class Cliente(SQLModel, table=True):
    idcliente: Optional[int] = Field(default=None, primary_key=True)
    nombre: str
    apellido: str
    telefono: str


class Repartidor(SQLModel, table=True):
    idrepartidor: Optional[int] = Field(default=None, primary_key=True)
    nombre: str
    apellido: str
    telefono: str
    cantidadkmrecorridos: float = Field(default=0.0)
    zonaasignada: Optional[str] = None


class Chat(SQLModel, table=True):
    idchat: Optional[int] = Field(default=None, primary_key=True)
    id_chat: str = Field(unique=True, index=True)
    id_cliente: int = Field(foreign_key="cliente.idcliente")
    id_repartidor: Optional[int] = Field(default=None, foreign_key="repartidor.idrepartidor")
    fecha_creacion: Optional[datetime] = Field(default_factory=datetime.now)


class Mensaje(SQLModel, table=True):
    idmensaje: Optional[int] = Field(default=None, primary_key=True)
    id_chat: str = Field(foreign_key="chat.id_chat")
    contenido: str
    es_cliente: bool = Field(default=True)
    fecha_envio: Optional[datetime] = Field(default_factory=datetime.now)


class Calificaciones(SQLModel, table=True):
    id_calificacion: Optional[int] = Field(default=None, primary_key=True)
    estrellas: int = Field(ge=1, le=5)  


class ClientesCalificaciones(SQLModel, table=True):
    id_clientecalificaciones: Optional[int] = Field(default=None, primary_key=True)
    id_calificacion: int = Field(foreign_key="calificacion.id_calificacion")
    id_cliente: int = Field(foreign_key="cliente.idcliente")


def get_db_session():
    try:
        return Session(engine)
    except Exception as e:
        logger.error("No se pudo obtener la sesión de base de datos", exc_info=True)
        raise

def init_db():
    try:
        SQLModel.metadata.create_all(engine)
        logger.info("Base de datos inicializada correctamente")
    except Exception as e:
        logger.error("Error inicializando la base de datos", exc_info=True)
        raise


def get_db_connection():
    try:
        dsn = DATABASE_URL.replace("+psycopg2", "")
        
        conn = psycopg2.connect(dsn)
        return conn
    except Exception as e:
        logger.error(f"Error obteniendo conexión cruda a la base de datos: {e}", exc_info=True)
        logger.error(f"Intentando con DATABASE_URL: {DATABASE_URL[:50]}...") 

if __name__ == "__main__":
    init_db()
