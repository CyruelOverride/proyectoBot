from Util.database import (
    init_db, get_db_connection,
    Categoria, Producto, Cliente, Repartidor, Chat, Mensaje,
    Pedido, DetallePedido, Calificaciones, ClientesCalificaciones
)
import logging

logging.basicConfig(level=logging.INFO)

def main():
    try:
        print("Inicializando base de datos")
        
        conn = get_db_connection()
        conn.close()
        print("Conexión a la base de datos chequeada")
        
        models = [
            Categoria, Producto, Cliente, Repartidor, Chat, Mensaje,
            Pedido, DetallePedido, Calificaciones, ClientesCalificaciones
        ]
        print(f"Modelos importados: {len(models)}")
        
        init_db()
        
    except Exception as e:
        print(f"Error al inicializar la base de datos: {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    main()

