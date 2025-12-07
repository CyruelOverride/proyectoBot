from Util.product_util import filtrar_productos, paginar_productos, lista_productos

class ProductosService:
    def __init__(self):
        self.pagina_actual = 1
        self.filtro_actual = "cat_all"
        self.orden_asc = True

    def obtener_lista(self, numero: str):
        return lista_productos(numero, self.pagina_actual, self.filtro_actual, self.orden_asc)

    def siguiente_pagina(self, numero: str):
        self.pagina_actual += 1
        return self.obtener_lista(numero)

    def pagina_anterior(self, numero: str):
        if self.pagina_actual > 1:
            self.pagina_actual -= 1
        return self.obtener_lista(numero)

    def cambiar_orden(self, numero: str):
        self.orden_asc = not self.orden_asc
        return self.obtener_lista(numero)

    def aplicar_filtro(self, numero: str, filtro_id: str):
        self.filtro_actual = filtro_id
        self.pagina_actual = 1
        return self.obtener_lista(numero)

    def resetear(self):
        self.pagina_actual = 1
        self.filtro_actual = "cat_all"
        self.orden_asc = True
