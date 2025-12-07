from Util.database import get_db_connection

class ClienteService:

    def obtener_o_crear_cliente(nombre, apellido, telefono):
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT idcliente FROM cliente WHERE telefono = %s", (telefono,))
        row = cur.fetchone()

        if row:
            id_cliente = row[0]
        else:
            cur.execute(
                "INSERT INTO cliente (nombre, apellido, telefono) VALUES (%s, %s, %s) RETURNING idcliente",
                (nombre, apellido, telefono)
            )
            id_cliente = cur.fetchone()[0]
            conn.commit()

        cur.close()
        conn.close()
        return id_cliente
