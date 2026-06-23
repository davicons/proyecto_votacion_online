import hashlib
import json
import socket
import threading
from datetime import datetime


HOST = "localhost"
PUERTO_LOGICA = 9000
HOST_DATOS = "localhost"
PUERTO_DATOS = 9001
BUFFER_SIZE = 4096
MAX_MENSAJE = 1024 * 1024
TIMEOUT_SEGUNDOS = 10


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


def solicitar_a_datos(solicitud):
    try:
        with socket.create_connection((HOST_DATOS, PUERTO_DATOS), timeout=TIMEOUT_SEGUNDOS) as conexion:
            enviar_json(conexion, solicitud)
            return recibir_json(conexion)
    except (ConnectionRefusedError, TimeoutError, OSError):
        return respuesta_error("No se pudo conectar con el servidor de datos.")
    except json.JSONDecodeError:
        return respuesta_error("Respuesta inválida del servidor de datos.")


def generar_hash_voto(usuario_id, opcion_id, fecha_hora):
    contenido = f"{usuario_id}{opcion_id}{fecha_hora}"
    return hashlib.sha256(contenido.encode("utf-8")).hexdigest()


def login(solicitud):
    codigo = solicitud.get("codigo", "").strip()
    password = solicitud.get("password", "")

    if not codigo or not password:
        return respuesta_error("Debe ingresar código y contraseña")

    respuesta_datos = solicitar_a_datos({"accion": "obtener_usuario", "codigo": codigo})
    if respuesta_datos.get("estado") != "ok":
        if respuesta_datos.get("mensaje") == "No se pudo conectar con el servidor de datos.":
            return respuesta_datos
        return respuesta_error("Código o contraseña incorrectos")

    usuario = respuesta_datos.get("usuario", {})
    if usuario.get("password") != password:
        return respuesta_error("Código o contraseña incorrectos")

    usuario_seguro = {
        "id": usuario.get("id"),
        "codigo": usuario.get("codigo"),
        "nombre": usuario.get("nombre"),
        "ha_votado": usuario.get("ha_votado"),
    }
    return respuesta_ok("Login correcto", usuario=usuario_seguro)


def listar_opciones(_solicitud):
    respuesta_datos = solicitar_a_datos({"accion": "listar_opciones"})
    if respuesta_datos.get("estado") != "ok":
        return respuesta_datos

    return respuesta_ok(
        "Opciones consultadas correctamente",
        opciones=respuesta_datos.get("opciones", []),
    )


def opcion_existe(opcion_id):
    respuesta_datos = solicitar_a_datos({"accion": "listar_opciones"})
    if respuesta_datos.get("estado") != "ok":
        return False, respuesta_datos

    opciones = respuesta_datos.get("opciones", [])
    existe = any(opcion.get("id") == opcion_id for opcion in opciones)
    return existe, None


def votar(solicitud):
    usuario_id = solicitud.get("usuario_id")
    opcion_id = solicitud.get("opcion_id")

    if not usuario_id or not opcion_id:
        return respuesta_error("Debe enviar usuario_id y opcion_id")

    try:
        usuario_id = int(usuario_id)
        opcion_id = int(opcion_id)
    except (TypeError, ValueError):
        return respuesta_error("usuario_id y opcion_id deben ser números")

    existe, error_opciones = opcion_existe(opcion_id)
    if error_opciones is not None:
        return error_opciones
    if not existe:
        return respuesta_error("La opción seleccionada no existe")

    respuesta_voto = solicitar_a_datos(
        {"accion": "verificar_voto_usuario", "usuario_id": usuario_id}
    )
    if respuesta_voto.get("estado") != "ok":
        return respuesta_voto
    if respuesta_voto.get("ya_voto"):
        return respuesta_error("El alumno ya emitió su voto. No puede votar dos veces.")

    fecha_hora = datetime.now().isoformat(timespec="seconds")
    hash_voto = generar_hash_voto(usuario_id, opcion_id, fecha_hora)

    return solicitar_a_datos(
        {
            "accion": "registrar_voto",
            "usuario_id": usuario_id,
            "opcion_id": opcion_id,
            "fecha_hora": fecha_hora,
            "hash_voto": hash_voto,
        }
    )


def resultados(_solicitud):
    respuesta_datos = solicitar_a_datos({"accion": "obtener_resultados"})
    if respuesta_datos.get("estado") != "ok":
        return respuesta_datos

    return respuesta_ok(
        "Resultados consultados correctamente",
        resultados=respuesta_datos.get("resultados", []),
    )


def verificar_integridad(_solicitud):
    return solicitar_a_datos({"accion": "verificar_integridad"})


ACCIONES = {
    "login": login,
    "listar_opciones": listar_opciones,
    "votar": votar,
    "resultados": resultados,
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
    servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    servidor.bind((HOST, PUERTO_LOGICA))
    servidor.listen()
    print(f"Servidor de lógica escuchando en {HOST}:{PUERTO_LOGICA}")

    try:
        while True:
            conexion, direccion = servidor.accept()
            hilo = threading.Thread(target=manejar_cliente, args=(conexion, direccion))
            hilo.daemon = True
            hilo.start()
    except KeyboardInterrupt:
        print("\nServidor de lógica detenido")
    finally:
        servidor.close()


if __name__ == "__main__":
    iniciar_servidor()
