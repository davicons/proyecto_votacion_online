import hashlib
import json
import os
import socket
import threading

import psycopg
from psycopg.rows import dict_row


HOST = "localhost"
PUERTO = 9001
BUFFER_SIZE = 4096
MAX_MENSAJE = 1024 * 1024
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def cargar_env():
    ruta_env = os.path.join(BASE_DIR, ".env")
    if not os.path.exists(ruta_env):
        return

    with open(ruta_env, "r", encoding="utf-8") as archivo:
        for linea in archivo:
            linea = linea.strip()
            if not linea or linea.startswith("#") or "=" not in linea:
                continue
            clave, valor = linea.split("=", 1)
            clave = clave.strip()
            valor = valor.strip().strip('"').strip("'")
            os.environ.setdefault(clave, valor)


cargar_env()

DB_HOST = os.getenv("DB_HOST", "localhost")
DB_PORT = os.getenv("DB_PORT", "5432")
DB_NAME = os.getenv("DB_NAME", "votacion_db")
DB_USER = os.getenv("DB_USER", "postgres")
DB_PASSWORD = os.getenv("DB_PASSWORD", "postgres")


def conectar_db():
    return psycopg.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
        row_factory=dict_row,
    )


def respuesta_ok(mensaje="Operación realizada correctamente", **datos):
    respuesta = {"estado": "ok", "mensaje": mensaje}
    respuesta.update(datos)
    return respuesta


def respuesta_error(mensaje="Error interno del servidor de datos.", **datos):
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


def normalizar_fecha_hora(fecha_hora):
    if hasattr(fecha_hora, "isoformat"):
        return fecha_hora.isoformat(timespec="seconds")
    return str(fecha_hora)


def obtener_usuario(codigo):
    with conectar_db() as conexion:
        fila = conexion.execute(
            """
            SELECT id, codigo, nombre, password, ha_votado
            FROM usuarios
            WHERE codigo = %s
            """,
            (codigo,),
        ).fetchone()

    if fila is None:
        return None

    return {
        "id": fila["id"],
        "codigo": fila["codigo"],
        "nombre": fila["nombre"],
        "password": fila["password"],
        "ha_votado": fila["ha_votado"],
    }


def listar_opciones():
    with conectar_db() as conexion:
        filas = conexion.execute(
            "SELECT id, nombre FROM opciones ORDER BY id"
        ).fetchall()
    return [{"id": fila["id"], "nombre": fila["nombre"]} for fila in filas]


def existe_opcion(opcion_id):
    with conectar_db() as conexion:
        fila = conexion.execute(
            "SELECT id FROM opciones WHERE id = %s",
            (opcion_id,),
        ).fetchone()
    return fila is not None


def usuario_ya_voto(usuario_id):
    with conectar_db() as conexion:
        fila = conexion.execute(
            """
            SELECT u.ha_votado, v.id AS voto_id
            FROM usuarios u
            LEFT JOIN votos v ON v.usuario_id = u.id
            WHERE u.id = %s
            """,
            (usuario_id,),
        ).fetchone()

    if fila is None:
        return None

    return bool(fila["ha_votado"] or fila["voto_id"] is not None)


def registrar_voto(usuario_id, opcion_id, fecha_hora, hash_voto):
    if len(hash_voto) != 64:
        return respuesta_error("El hash del voto no es válido")

    hash_esperado = generar_hash_voto(usuario_id, opcion_id, fecha_hora)
    if hash_voto != hash_esperado:
        return respuesta_error("El hash del voto no coincide con los datos recibidos")

    conexion = conectar_db()
    try:
        with conexion.transaction():
            usuario = conexion.execute(
                "SELECT id, ha_votado FROM usuarios WHERE id = %s FOR UPDATE",
                (usuario_id,),
            ).fetchone()
            if usuario is None:
                return respuesta_error("Usuario no encontrado.")

            opcion = conexion.execute(
                "SELECT id FROM opciones WHERE id = %s",
                (opcion_id,),
            ).fetchone()
            if opcion is None:
                return respuesta_error("La opción seleccionada no existe.")

            voto_existente = conexion.execute(
                "SELECT id FROM votos WHERE usuario_id = %s",
                (usuario_id,),
            ).fetchone()
            if usuario["ha_votado"] or voto_existente is not None:
                return respuesta_error("El alumno ya emitió su voto. No puede votar dos veces.")

            conexion.execute(
                """
                INSERT INTO votos (usuario_id, opcion_id, fecha_hora, hash_voto)
                VALUES (%s, %s, %s, %s)
                """,
                (usuario_id, opcion_id, fecha_hora, hash_voto),
            )
            conexion.execute(
                "UPDATE usuarios SET ha_votado = TRUE WHERE id = %s",
                (usuario_id,),
            )
    except psycopg.errors.UniqueViolation:
        return respuesta_error("El alumno ya emitió su voto. No puede votar dos veces.")
    except Exception:
        raise
    finally:
        conexion.close()

    return respuesta_ok("Voto registrado correctamente")


def obtener_resultados():
    with conectar_db() as conexion:
        filas = conexion.execute(
            """
            SELECT o.nombre AS opcion, COUNT(v.id) AS votos
            FROM opciones o
            LEFT JOIN votos v ON v.opcion_id = o.id
            GROUP BY o.id, o.nombre
            ORDER BY o.id
            """
        ).fetchall()
    return [{"opcion": fila["opcion"], "votos": fila["votos"]} for fila in filas]


def verificar_integridad():
    votos_alterados = []

    with conectar_db() as conexion:
        filas = conexion.execute(
            "SELECT id, usuario_id, opcion_id, fecha_hora, hash_voto FROM votos ORDER BY id"
        ).fetchall()

    for fila in filas:
        fecha_hora = normalizar_fecha_hora(fila["fecha_hora"])
        hash_calculado = generar_hash_voto(
            fila["usuario_id"],
            fila["opcion_id"],
            fecha_hora,
        )
        if hash_calculado != fila["hash_voto"]:
            votos_alterados.append(fila["id"])

    if votos_alterados:
        return respuesta_error(
            "Se detectaron votos alterados",
            votos_alterados=votos_alterados,
        )

    return respuesta_ok("Todos los votos mantienen su integridad")


def accion_obtener_usuario(solicitud):
    codigo = solicitud.get("codigo")
    if not codigo:
        return respuesta_error("Debe enviar el código del alumno")

    usuario = obtener_usuario(codigo)
    if usuario is None:
        return respuesta_error("Usuario no encontrado.")

    return respuesta_ok("Usuario encontrado", usuario=usuario)


def accion_listar_opciones(_solicitud):
    return respuesta_ok("Opciones consultadas correctamente", opciones=listar_opciones())


def accion_verificar_voto_usuario(solicitud):
    usuario_id = solicitud.get("usuario_id")
    if not usuario_id:
        return respuesta_error("Debe enviar el id del usuario")

    ya_voto = usuario_ya_voto(usuario_id)
    if ya_voto is None:
        return respuesta_error("Usuario no encontrado.")

    return respuesta_ok("Estado de voto consultado", ya_voto=ya_voto)


def accion_registrar_voto(solicitud):
    usuario_id = solicitud.get("usuario_id")
    opcion_id = solicitud.get("opcion_id")
    fecha_hora = solicitud.get("fecha_hora")
    hash_voto = solicitud.get("hash_voto")

    if not usuario_id or not opcion_id or not fecha_hora or not hash_voto:
        return respuesta_error("Datos incompletos para registrar el voto")

    return registrar_voto(usuario_id, opcion_id, fecha_hora, hash_voto)


def accion_obtener_resultados(_solicitud):
    return respuesta_ok("Resultados consultados correctamente", resultados=obtener_resultados())


ACCIONES = {
    "obtener_usuario": accion_obtener_usuario,
    "listar_opciones": accion_listar_opciones,
    "verificar_voto_usuario": accion_verificar_voto_usuario,
    "registrar_voto": accion_registrar_voto,
    "obtener_resultados": accion_obtener_resultados,
    "verificar_integridad": lambda _solicitud: verificar_integridad(),
}


def procesar_solicitud(solicitud):
    accion = solicitud.get("accion")
    if not accion:
        return respuesta_error("Debe enviar una acción")

    manejador = ACCIONES.get(accion)
    if manejador is None:
        return respuesta_error("Acción no reconocida.")

    try:
        return manejador(solicitud)
    except (psycopg.OperationalError, psycopg.InterfaceError):
        return respuesta_error("No se pudo conectar a PostgreSQL.")
    except Exception:
        return respuesta_error("Error interno del servidor de datos.")


def manejar_cliente(conexion, direccion):
    try:
        solicitud = recibir_json(conexion)
        respuesta = procesar_solicitud(solicitud)
        enviar_json(conexion, respuesta)
    except json.JSONDecodeError:
        enviar_json(conexion, respuesta_error("JSON inválido"))
    except Exception:
        try:
            enviar_json(conexion, respuesta_error("Error interno del servidor de datos."))
        except Exception:
            pass
    finally:
        conexion.close()


def iniciar_servidor():
    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    servidor.bind((HOST, PUERTO))
    servidor.listen()
    print(f"Servidor de datos escuchando en {HOST}:{PUERTO}")
    print(f"Base de datos PostgreSQL: {DB_NAME} en {DB_HOST}:{DB_PORT}")

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
