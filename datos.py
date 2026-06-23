import hashlib
import json
import os
import socket
import sqlite3
import threading


HOST = "localhost"
PUERTO = 9001
BUFFER_SIZE = 4096
MAX_MENSAJE = 1024 * 1024
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "votacion.db")


def conectar_db():
    conexion = sqlite3.connect(DB_PATH)
    conexion.row_factory = sqlite3.Row
    conexion.execute("PRAGMA foreign_keys = ON")
    return conexion


def respuesta_ok(mensaje="Operación realizada correctamente", **datos):
    respuesta = {"estado": "ok", "mensaje": mensaje}
    respuesta.update(datos)
    return respuesta


def respuesta_error(mensaje="Error interno del servidor", **datos):
    respuesta = {"estado": "error", "mensaje": mensaje}
    respuesta.update(datos)
    return respuesta


def enviar_json(conexion, mensaje):
    datos = json.dumps(mensaje, ensure_ascii=False) + "\n"
    conexion.sendall(datos.encode("utf-8"))


def recibir_json(conexion):
    partes = []
    total = 0

    while True:
        bloque = conexion.recv(BUFFER_SIZE)
        if not bloque:
            break

        partes.append(bloque)
        total += len(bloque)
        if total > MAX_MENSAJE:
            raise ValueError("Mensaje demasiado grande")
        if b"\n" in bloque:
            break

    if not partes:
        raise ValueError("No se recibió información")

    linea = b"".join(partes).split(b"\n", 1)[0]
    return json.loads(linea.decode("utf-8"))


def generar_hash_voto(usuario_id, opcion_id, fecha_hora):
    contenido = f"{usuario_id}{opcion_id}{fecha_hora}"
    return hashlib.sha256(contenido.encode("utf-8")).hexdigest()


def obtener_usuario(solicitud):
    codigo = solicitud.get("codigo")
    if not codigo:
        return respuesta_error("Debe enviar el código del alumno")

    conexion = conectar_db()
    try:
        cursor = conexion.execute(
            """
            SELECT id, codigo, nombre, password, ha_votado
            FROM usuarios
            WHERE codigo = ?
            """,
            (codigo,),
        )
        fila = cursor.fetchone()
    finally:
        conexion.close()

    if fila is None:
        return respuesta_error("Usuario no encontrado")

    return respuesta_ok(
        "Usuario encontrado",
        usuario={
            "id": fila["id"],
            "codigo": fila["codigo"],
            "nombre": fila["nombre"],
            "password": fila["password"],
            "ha_votado": fila["ha_votado"],
        },
    )


def listar_opciones(_solicitud):
    conexion = conectar_db()
    try:
        cursor = conexion.execute("SELECT id, nombre FROM opciones ORDER BY id")
        opciones = [{"id": fila["id"], "nombre": fila["nombre"]} for fila in cursor.fetchall()]
    finally:
        conexion.close()

    return respuesta_ok("Opciones consultadas correctamente", opciones=opciones)


def verificar_voto_usuario(solicitud):
    usuario_id = solicitud.get("usuario_id")
    if not usuario_id:
        return respuesta_error("Debe enviar el id del usuario")

    conexion = conectar_db()
    try:
        cursor = conexion.execute(
            """
            SELECT u.ha_votado, v.id AS voto_id
            FROM usuarios u
            LEFT JOIN votos v ON v.usuario_id = u.id
            WHERE u.id = ?
            """,
            (usuario_id,),
        )
        fila = cursor.fetchone()
    finally:
        conexion.close()

    if fila is None:
        return respuesta_error("Usuario no encontrado")

    ya_voto = fila["ha_votado"] == 1 or fila["voto_id"] is not None
    return respuesta_ok("Estado de voto consultado", ya_voto=ya_voto)


def verificar_opcion_existe(conexion, opcion_id):
    cursor = conexion.execute("SELECT id FROM opciones WHERE id = ?", (opcion_id,))
    return cursor.fetchone() is not None


def registrar_voto(solicitud):
    usuario_id = solicitud.get("usuario_id")
    opcion_id = solicitud.get("opcion_id")
    fecha_hora = solicitud.get("fecha_hora")
    hash_voto = solicitud.get("hash_voto")

    if not usuario_id or not opcion_id or not fecha_hora or not hash_voto:
        return respuesta_error("Datos incompletos para registrar el voto")

    try:
        conexion = conectar_db()
        try:
            cursor = conexion.execute(
                "SELECT id, ha_votado FROM usuarios WHERE id = ?",
                (usuario_id,),
            )
            usuario = cursor.fetchone()
            if usuario is None:
                return respuesta_error("Usuario no encontrado")

            if not verificar_opcion_existe(conexion, opcion_id):
                return respuesta_error("La opción seleccionada no existe")

            cursor = conexion.execute(
                "SELECT id FROM votos WHERE usuario_id = ?",
                (usuario_id,),
            )
            voto_existente = cursor.fetchone()
            if usuario["ha_votado"] == 1 or voto_existente is not None:
                return respuesta_error("El alumno ya emitió su voto. No puede votar dos veces.")

            hash_esperado = generar_hash_voto(usuario_id, opcion_id, fecha_hora)
            if hash_voto != hash_esperado:
                return respuesta_error("El hash del voto no coincide con los datos recibidos")

            conexion.execute(
                """
                INSERT INTO votos (usuario_id, opcion_id, fecha_hora, hash_voto)
                VALUES (?, ?, ?, ?)
                """,
                (usuario_id, opcion_id, fecha_hora, hash_voto),
            )
            conexion.execute(
                "UPDATE usuarios SET ha_votado = 1 WHERE id = ?",
                (usuario_id,),
            )
            conexion.commit()
        finally:
            conexion.close()

        return respuesta_ok("Voto registrado correctamente")
    except sqlite3.IntegrityError:
        return respuesta_error("El alumno ya emitió su voto. No puede votar dos veces.")


def obtener_resultados(_solicitud):
    conexion = conectar_db()
    try:
        cursor = conexion.execute(
            """
            SELECT o.nombre AS opcion, COUNT(v.id) AS votos
            FROM opciones o
            LEFT JOIN votos v ON v.opcion_id = o.id
            GROUP BY o.id, o.nombre
            ORDER BY o.id
            """
        )
        resultados = [
            {"opcion": fila["opcion"], "votos": fila["votos"]}
            for fila in cursor.fetchall()
        ]
    finally:
        conexion.close()

    return respuesta_ok("Resultados consultados correctamente", resultados=resultados)


def verificar_integridad(_solicitud):
    votos_alterados = []

    conexion = conectar_db()
    try:
        cursor = conexion.execute(
            "SELECT id, usuario_id, opcion_id, fecha_hora, hash_voto FROM votos ORDER BY id"
        )
        for fila in cursor.fetchall():
            hash_calculado = generar_hash_voto(
                fila["usuario_id"],
                fila["opcion_id"],
                fila["fecha_hora"],
            )
            if hash_calculado != fila["hash_voto"]:
                votos_alterados.append(fila["id"])
    finally:
        conexion.close()

    if votos_alterados:
        return respuesta_error(
            "Se detectaron votos alterados",
            votos_alterados=votos_alterados,
        )

    return respuesta_ok("Todos los votos mantienen su integridad")


ACCIONES = {
    "obtener_usuario": obtener_usuario,
    "listar_opciones": listar_opciones,
    "verificar_voto_usuario": verificar_voto_usuario,
    "registrar_voto": registrar_voto,
    "obtener_resultados": obtener_resultados,
    "verificar_integridad": verificar_integridad,
}


def procesar_solicitud(solicitud):
    accion = solicitud.get("accion")
    if not accion:
        return respuesta_error("Debe enviar una acción")

    manejador = ACCIONES.get(accion)
    if manejador is None:
        return respuesta_error("Acción no reconocida")

    return manejador(solicitud)


def manejar_cliente(conexion, direccion):
    try:
        solicitud = recibir_json(conexion)
        respuesta = procesar_solicitud(solicitud)
        enviar_json(conexion, respuesta)
    except json.JSONDecodeError:
        enviar_json(conexion, respuesta_error("JSON inválido"))
    except Exception:
        try:
            enviar_json(conexion, respuesta_error("Error interno del servidor"))
        except Exception:
            pass
    finally:
        conexion.close()


def iniciar_servidor():
    if not os.path.exists(DB_PATH):
        print("No existe votacion.db. Ejecute primero: python init_db.py")
        return

    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    servidor.bind((HOST, PUERTO))
    servidor.listen()
    print(f"Servidor de datos escuchando en {HOST}:{PUERTO}")

    try:
        while True:
            conexion, direccion = servidor.accept()
            hilo = threading.Thread(target=manejar_cliente, args=(conexion, direccion))
            hilo.daemon = True
            hilo.start()
    except KeyboardInterrupt:
        print("\nServidor de datos detenido")
    finally:
        servidor.close()


if __name__ == "__main__":
    iniciar_servidor()
