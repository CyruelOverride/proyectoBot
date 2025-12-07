from fastapi import FastAPI, HTTPException, Depends
from fastapi.responses import JSONResponse
from typing import List, Optional
from pydantic import BaseModel
from datetime import datetime
from Util.database import (
    get_db_session, 
    Repartidor, 
    Pedido, 
    DetallePedido,
    Session
)

app = FastAPI(title="API de Repartidores y Pedidos", version="1.0.0")

class RepartidorResponse(BaseModel):
    idrepartidor: int
    nombre: str
    apellido: str
    telefono: str
    cantidadkmrecorridos: float
    zonaasignada: Optional[str] = None

    class Config:
        from_attributes = True

class RepartidorCreate(BaseModel):
    nombre: str
    apellido: str
    telefono: str
    cantidadkmrecorridos: float = 0.0
    zonaasignada: Optional[str] = None

class PedidoResponse(BaseModel):
    idpedido: int
    id_chat: str
    id_cliente: str
    id_repartidor: Optional[int] = None
    repartidor: Optional[RepartidorResponse] = None
    direccion: str
    latitud: Optional[str] = None
    longitud: Optional[str] = None
    estado: str
    fecha_confirmacion: Optional[datetime] = None
    zona: Optional[str] = None
    codigo_verificacion: Optional[int] = None
    id_tanda: Optional[int] = None

    class Config:
        from_attributes = True

def get_db():
    db = get_db_session()
    try:
        yield db
    finally:
        db.close()


@app.post("/repartidores", response_model=RepartidorResponse, status_code=201)
def crear_repartidor(repartidor: RepartidorCreate, db: Session = Depends(get_db)):
    try:
        nuevo_repartidor = Repartidor(
            nombre=repartidor.nombre,
            apellido=repartidor.apellido,
            telefono=repartidor.telefono,
            cantidadkmrecorridos=repartidor.cantidadkmrecorridos,
            zonaasignada=repartidor.zonaasignada
        )
        db.add(nuevo_repartidor)
        db.commit()
        db.refresh(nuevo_repartidor)
        return nuevo_repartidor
    except Exception as e:
        db.rollback()
        raise HTTPException(status_code=500, detail=f"Error al crear repartidor: {str(e)}")

@app.get("/repartidores/{id_repartidor}", response_model=RepartidorResponse)
def obtener_repartidor_por_id(id_repartidor: int, db: Session = Depends(get_db)):
    repartidor = db.query(Repartidor).filter(Repartidor.idrepartidor == id_repartidor).first()
    if not repartidor:
        raise HTTPException(status_code=404, detail=f"Repartidor con ID {id_repartidor} no encontrado")
    return repartidor

@app.get("/repartidores", response_model=List[RepartidorResponse])
def obtener_todos_los_repartidores(db: Session = Depends(get_db)):
    repartidores = db.query(Repartidor).all()
    return repartidores


def obtener_pedido_con_repartidor(pedido: Pedido, db: Session) -> PedidoResponse:
    repartidor_data = None
    if pedido.id_repartidor:
        repartidor = db.query(Repartidor).filter(Repartidor.idrepartidor == pedido.id_repartidor).first()
        if repartidor:
            repartidor_data = RepartidorResponse(
                idrepartidor=repartidor.idrepartidor,
                nombre=repartidor.nombre,
                apellido=repartidor.apellido,
                telefono=repartidor.telefono,
                cantidadkmrecorridos=repartidor.cantidadkmrecorridos,
                zonaasignada=repartidor.zonaasignada
            )
    
    return PedidoResponse(
        idpedido=pedido.idpedido,
        id_chat=pedido.id_chat,
        id_cliente=pedido.id_cliente,
        id_repartidor=pedido.id_repartidor,
        repartidor=repartidor_data,
        direccion=pedido.direccion,
        latitud=pedido.latitud,
        longitud=pedido.longitud,
        estado=pedido.estado,
        fecha_confirmacion=pedido.fecha_confirmacion,
        zona=pedido.zona,
        codigo_verificacion=pedido.codigo_verificacion,
        id_tanda=pedido.id_tanda
    )

@app.get("/pedidos/{id_pedido}", response_model=PedidoResponse)
def obtener_pedido_por_id(id_pedido: int, db: Session = Depends(get_db)):
    pedido = db.query(Pedido).filter(Pedido.idpedido == id_pedido).first()
    if not pedido:
        raise HTTPException(status_code=404, detail=f"Pedido con ID {id_pedido} no encontrado")
    
    return obtener_pedido_con_repartidor(pedido, db)

@app.get("/pedidos", response_model=List[PedidoResponse])
def obtener_todos_los_pedidos(db: Session = Depends(get_db)):
    pedidos = db.query(Pedido).all()
    return [obtener_pedido_con_repartidor(pedido, db) for pedido in pedidos]

@app.get("/pedidos/repartidor/{id_repartidor}", response_model=List[PedidoResponse])
def obtener_pedidos_por_repartidor(id_repartidor: int, db: Session = Depends(get_db)):
    repartidor = db.query(Repartidor).filter(Repartidor.idrepartidor == id_repartidor).first()
    if not repartidor:
        raise HTTPException(status_code=404, detail=f"Repartidor con ID {id_repartidor} no encontrado")
    
    pedidos = db.query(Pedido).filter(Pedido.id_repartidor == id_repartidor).all()
    return [obtener_pedido_con_repartidor(pedido, db) for pedido in pedidos]

class EstadisticaRepartidor(BaseModel):
    idrepartidor: int
    nombre: str
    apellido: str
    distancia_km: float
    combustible_litros: float
    pedidos_repartidos: int

class ClientePedidoResponse(BaseModel):
    idcliente: int
    nombre: str
    apellido: str
    telefono: str
    pedidos: List[PedidoResponse]

class ResumenEstadisticas(BaseModel):
    total_pedidos_repartidos: int
    repartidores: List[EstadisticaRepartidor]
    clientes_pedidos: List[ClientePedidoResponse]

@app.get("/estadisticas/pedidos-repartidos")
def obtener_pedidos_repartidos(db: Session = Depends(get_db)):
    total = db.query(Pedido).filter(Pedido.estado == "entregado").count()
    return {"total_pedidos_repartidos": total}

@app.get("/estadisticas/repartidores", response_model=List[EstadisticaRepartidor])
def obtener_estadisticas_repartidores(db: Session = Depends(get_db)):
    repartidores = db.query(Repartidor).all()
    estadisticas = []
    
    for repartidor in repartidores:
        pedidos_repartidos = db.query(Pedido).filter(
            Pedido.id_repartidor == repartidor.idrepartidor,
            Pedido.estado == "entregado"
        ).count()
        
        distancia_km = repartidor.cantidadkmrecorridos
        combustible_litros = distancia_km / 10.0  # 1 litro cada 10 km
        
        estadisticas.append(EstadisticaRepartidor(
            idrepartidor=repartidor.idrepartidor,
            nombre=repartidor.nombre,
            apellido=repartidor.apellido,
            distancia_km=round(distancia_km, 2),
            combustible_litros=round(combustible_litros, 2),
            pedidos_repartidos=pedidos_repartidos
        ))
    
    return estadisticas

@app.get("/estadisticas/clientes-pedidos", response_model=List[ClientePedidoResponse])
def obtener_clientes_pedidos(db: Session = Depends(get_db)):
    clientes = db.query(Cliente).all()
    resultado = []
    
    for cliente in clientes:
        # Buscar pedidos del cliente usando id_cliente (que es string en el modelo)
        pedidos = db.query(Pedido).filter(Pedido.id_cliente == str(cliente.idcliente)).all()
        
        pedidos_response = [obtener_pedido_con_repartidor(pedido, db) for pedido in pedidos]
        
        resultado.append(ClientePedidoResponse(
            idcliente=cliente.idcliente,
            nombre=cliente.nombre,
            apellido=cliente.apellido,
            telefono=cliente.telefono,
            pedidos=pedidos_response
        ))
    
    return resultado

@app.get("/estadisticas/resumen", response_model=ResumenEstadisticas)
def obtener_resumen_estadisticas(db: Session = Depends(get_db)):
    total_pedidos = db.query(Pedido).filter(Pedido.estado == "entregado").count()
    
    repartidores = db.query(Repartidor).all()
    estadisticas_repartidores = []
    
    for repartidor in repartidores:
        pedidos_repartidos = db.query(Pedido).filter(
            Pedido.id_repartidor == repartidor.idrepartidor,
            Pedido.estado == "entregado"
        ).count()
        
        distancia_km = repartidor.cantidadkmrecorridos
        combustible_litros = distancia_km / 10.0
        
        estadisticas_repartidores.append(EstadisticaRepartidor(
            idrepartidor=repartidor.idrepartidor,
            nombre=repartidor.nombre,
            apellido=repartidor.apellido,
            distancia_km=round(distancia_km, 2),
            combustible_litros=round(combustible_litros, 2),
            pedidos_repartidos=pedidos_repartidos
        ))
    
    clientes = db.query(Cliente).all()
    clientes_pedidos = []
    
    for cliente in clientes:
        pedidos = db.query(Pedido).filter(Pedido.id_cliente == str(cliente.idcliente)).all()
        pedidos_response = [obtener_pedido_con_repartidor(pedido, db) for pedido in pedidos]
        
        clientes_pedidos.append(ClientePedidoResponse(
            idcliente=cliente.idcliente,
            nombre=cliente.nombre,
            apellido=cliente.apellido,
            telefono=cliente.telefono,
            pedidos=pedidos_response
        ))
    
    return ResumenEstadisticas(
        total_pedidos_repartidos=total_pedidos,
        repartidores=estadisticas_repartidores,
        clientes_pedidos=clientes_pedidos
    )

@app.get("/")
def root():
    return {
        "mensaje": "API de Repartidores y Pedidos",
        "version": "1.0.0",
        "endpoints": {
            "repartidores": {
                "POST /repartidores": "Crear un nuevo repartidor",
                "GET /repartidores": "Obtener todos los repartidores",
                "GET /repartidores/{id}": "Obtener un repartidor por ID"
            },
            "pedidos": {
                "GET /pedidos": "Obtener todos los pedidos",
                "GET /pedidos/{id}": "Obtener un pedido por ID",
                "GET /pedidos/repartidor/{id_repartidor}": "Obtener pedidos por repartidor"
            },
            "estadisticas": {
                "GET /estadisticas/pedidos-repartidos": "Total de pedidos entregados",
                "GET /estadisticas/repartidores": "Estadísticas de repartidores (distancia, combustible, pedidos)",
                "GET /estadisticas/clientes-pedidos": "Lista de clientes con sus pedidos",
                "GET /estadisticas/resumen": "Resumen completo de todas las estadísticas"
            }
        }
    }

