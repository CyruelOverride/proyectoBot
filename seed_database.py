
from Util.database import get_db_session, Categoria, Producto, Repartidor
from sqlmodel import select

def seed_categorias(db):
    categorias_data = [
        {"nombre": "Todos"},
        {"nombre": "Minutas"},
        {"nombre": "Pizzas"},
        {"nombre": "Bebidas"},
        {"nombre": "Postres"},
        {"nombre": "Sandwiches"},
        {"nombre": "Ensaladas"},
        {"nombre": "Parrilla"},
    ]
    
    categorias_creadas = []
    for cat_data in categorias_data:
        stmt = select(Categoria).where(Categoria.nombre == cat_data["nombre"])
        categoria_existente = db.exec(stmt).first()
        
        if not categoria_existente:
            categoria = Categoria(**cat_data)
            db.add(categoria)
            categorias_creadas.append(categoria)
        else:
            categorias_creadas.append(categoria_existente)
    
    db.commit()
    
    for cat in categorias_creadas:
        db.refresh(cat)
    
    print(f"✅ {len(categorias_creadas)} categorías creadas/verificadas")
    return categorias_creadas


def seed_productos(db, categorias):
    """Crea al menos 25 productos distribuidos en las categorías."""
    # Mapeo de nombres de categorías a sus objetos
    cat_map = {cat.nombre: cat for cat in categorias}
    
    productos_data = [
        # MINUTAS (5 productos)
        {"nombre": "Hamburguesa Clásica", "precio": 250.0, "id_categoria": cat_map["Minutas"].id_categoria},
        {"nombre": "Hamburguesa Doble", "precio": 350.0, "id_categoria": cat_map["Minutas"].id_categoria},
        {"nombre": "Hamburguesa con Queso", "precio": 280.0, "id_categoria": cat_map["Minutas"].id_categoria},
        {"nombre": "Milanesa Napolitana", "precio": 320.0, "id_categoria": cat_map["Minutas"].id_categoria},
        {"nombre": "Milanesa Simple", "precio": 280.0, "id_categoria": cat_map["Minutas"].id_categoria},
        {"nombre": "Papas Fritas", "precio": 150.0, "id_categoria": cat_map["Minutas"].id_categoria},
        {"nombre": "Papas con Cheddar", "precio": 200.0, "id_categoria": cat_map["Minutas"].id_categoria},
        
        # PIZZAS (6 productos)
        {"nombre": "Pizza Muzzarella", "precio": 400.0, "id_categoria": cat_map["Pizzas"].id_categoria},
        {"nombre": "Pizza Napolitana", "precio": 450.0, "id_categoria": cat_map["Pizzas"].id_categoria},
        {"nombre": "Pizza Especial", "precio": 500.0, "id_categoria": cat_map["Pizzas"].id_categoria},
        {"nombre": "Pizza Cuatro Quesos", "precio": 550.0, "id_categoria": cat_map["Pizzas"].id_categoria},
        {"nombre": "Pizza Rúcula y Jamón", "precio": 520.0, "id_categoria": cat_map["Pizzas"].id_categoria},
        {"nombre": "Pizza Calabresa", "precio": 480.0, "id_categoria": cat_map["Pizzas"].id_categoria},
        
        # BEBIDAS (5 productos)
        {"nombre": "Coca Cola 500ml", "precio": 80.0, "id_categoria": cat_map["Bebidas"].id_categoria},
        {"nombre": "Coca Cola 1.5L", "precio": 120.0, "id_categoria": cat_map["Bebidas"].id_categoria},
        {"nombre": "Agua Mineral 500ml", "precio": 60.0, "id_categoria": cat_map["Bebidas"].id_categoria},
        {"nombre": "Cerveza Lata", "precio": 100.0, "id_categoria": cat_map["Bebidas"].id_categoria},
        {"nombre": "Jugo de Naranja", "precio": 90.0, "id_categoria": cat_map["Bebidas"].id_categoria},
        
        # POSTRES (4 productos)
        {"nombre": "Flan con Dulce de Leche", "precio": 120.0, "id_categoria": cat_map["Postres"].id_categoria},
        {"nombre": "Helado 1/4kg", "precio": 150.0, "id_categoria": cat_map["Postres"].id_categoria},
        {"nombre": "Brownie con Helado", "precio": 180.0, "id_categoria": cat_map["Postres"].id_categoria},
        {"nombre": "Tiramisú", "precio": 200.0, "id_categoria": cat_map["Postres"].id_categoria},
        
        # SANDWICHES (4 productos)
        {"nombre": "Sandwich de Milanesa", "precio": 220.0, "id_categoria": cat_map["Sandwiches"].id_categoria},
        {"nombre": "Sandwich de Pollo", "precio": 200.0, "id_categoria": cat_map["Sandwiches"].id_categoria},
        {"nombre": "Sandwich Vegetariano", "precio": 180.0, "id_categoria": cat_map["Sandwiches"].id_categoria},
        {"nombre": "Sandwich Completo", "precio": 250.0, "id_categoria": cat_map["Sandwiches"].id_categoria},
        
        # ENSALADAS (3 productos)
        {"nombre": "Ensalada César", "precio": 280.0, "id_categoria": cat_map["Ensaladas"].id_categoria},
        {"nombre": "Ensalada Mixta", "precio": 250.0, "id_categoria": cat_map["Ensaladas"].id_categoria},
        {"nombre": "Ensalada de Rúcula", "precio": 240.0, "id_categoria": cat_map["Ensaladas"].id_categoria},
        
        # PARRILLA (3 productos)
        {"nombre": "Asado para 2", "precio": 1200.0, "id_categoria": cat_map["Parrilla"].id_categoria},
        {"nombre": "Chorizo a la Parrilla", "precio": 180.0, "id_categoria": cat_map["Parrilla"].id_categoria},
        {"nombre": "Costilla de Cerdo", "precio": 450.0, "id_categoria": cat_map["Parrilla"].id_categoria},
    ]
    
    productos_creados = 0
    for prod_data in productos_data:
        stmt = select(Producto).where(Producto.nombre == prod_data["nombre"])
        producto_existente = db.exec(stmt).first()
        
        if not producto_existente:
            producto = Producto(**prod_data)
            db.add(producto)
            productos_creados += 1
    
    db.commit()
    print(f"✅ {productos_creados} productos creados (total: {len(productos_data)} productos)")
    return productos_creados


def seed_repartidores(db):
    repartidores_data = [
        {"nombre": "Juan", "apellido": "Pérez", "telefono": "+59899123456", "zonaasignada": "noroeste", "cantidadkmrecorridos": 0.0},
        {"nombre": "María", "apellido": "González", "telefono": "+59899234567", "zonaasignada": "noreste", "cantidadkmrecorridos": 0.0},
        {"nombre": "Carlos", "apellido": "Rodríguez", "telefono": "+59899345678", "zonaasignada": "suroeste", "cantidadkmrecorridos": 0.0},
        {"nombre": "Ana", "apellido": "Martínez", "telefono": "+59899456789", "zonaasignada": "sureste", "cantidadkmrecorridos": 0.0},
        {"nombre": "Luis", "apellido": "Fernández", "telefono": "+59899567890", "zonaasignada": "noroeste", "cantidadkmrecorridos": 0.0},
        {"nombre": "Laura", "apellido": "López", "telefono": "+59899678901", "zonaasignada": "noreste", "cantidadkmrecorridos": 0.0},
    ]
    
    repartidores_creados = 0
    for rep_data in repartidores_data:
        # Verificar si ya existe (por teléfono)
        stmt = select(Repartidor).where(Repartidor.telefono == rep_data["telefono"])
        repartidor_existente = db.exec(stmt).first()
        
        if not repartidor_existente:
            repartidor = Repartidor(**rep_data)
            db.add(repartidor)
            repartidores_creados += 1
    
    db.commit()
    print(f"✅ {repartidores_creados} repartidores creados")
    return repartidores_creados


def main():
    print("🌱 Iniciando seeding de la base de datos...")
    print("=" * 60)
    
    try:
        db = get_db_session()
        
        print("\n📁 Creando categorías...")
        categorias = seed_categorias(db)
        
        print("\n🍔 Creando productos...")
        productos_creados = seed_productos(db, categorias)
        
        print("\n🚴 Creando repartidores...")
        repartidores_creados = seed_repartidores(db)
        
        print("\n" + "=" * 60)
        print("✅ Seeding completado exitosamente!")
        print(f"   - Categorías: {len(categorias)}")
        print(f"   - Productos: {productos_creados} nuevos")
        print(f"   - Repartidores: {repartidores_creados} nuevos")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ Error durante el seeding: {e}")
        import traceback
        traceback.print_exc()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()

