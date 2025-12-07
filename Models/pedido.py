class Pedido:
    def __init__(self, idpedido, id_chat, id_cliente, id_repartidor, direccion, latitud, longitud):
        self.idpedido = idpedido
        self.id_chat = id_chat
        self.id_cliente = id_cliente
        self.id_repartidor = id_repartidor
        self.direccion = direccion
        self.latitud = latitud
        self.longitud = longitud
