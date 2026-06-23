import argparse
import socket
import subprocess
import sys
import time
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
PYTHON = sys.executable

HOST_DATOS = "localhost"
PUERTO_DATOS = 9001
HOST_LOGICA = "localhost"
PUERTO_LOGICA = 9000
TIMEOUT_ARRANQUE = 15


def ruta_script(nombre):
    return str(BASE_DIR / nombre)


def ejecutar_script(nombre):
    return subprocess.call([PYTHON, ruta_script(nombre)], cwd=BASE_DIR)


def iniciar_proceso(nombre):
    print(f"Iniciando {nombre}...")
    return subprocess.Popen([PYTHON, ruta_script(nombre)], cwd=BASE_DIR)


def puerto_disponible(host, puerto):
    try:
        with socket.create_connection((host, puerto), timeout=1):
            return True
    except OSError:
        return False


def esperar_puerto(host, puerto, proceso, nombre, timeout=TIMEOUT_ARRANQUE):
    inicio = time.time()
    while time.time() - inicio < timeout:
        if proceso.poll() is not None:
            print(f"{nombre} termino antes de abrir {host}:{puerto}.")
            return False
        if puerto_disponible(host, puerto):
            print(f"{nombre} listo en {host}:{puerto}.")
            return True
        time.sleep(0.3)

    print(f"No se pudo confirmar {nombre} en {host}:{puerto}.")
    return False


def detener_proceso(proceso, nombre):
    if proceso is None or proceso.poll() is not None:
        return

    print(f"Deteniendo {nombre}...")
    proceso.terminate()
    try:
        proceso.wait(timeout=5)
    except subprocess.TimeoutExpired:
        proceso.kill()
        proceso.wait(timeout=5)


def comando_initdb(_args):
    return ejecutar_script("init_db_postgres.py")


def comando_datos(_args):
    return ejecutar_script("datos.py")


def comando_logica(_args):
    return ejecutar_script("logica.py")


def comando_presentacion(_args):
    return ejecutar_script("presentacion.py")


def comando_runserver(_args):
    proceso_datos = None
    proceso_logica = None

    try:
        proceso_datos = iniciar_proceso("datos.py")
        if not esperar_puerto(HOST_DATOS, PUERTO_DATOS, proceso_datos, "datos.py"):
            return 1

        proceso_logica = iniciar_proceso("logica.py")
        if not esperar_puerto(HOST_LOGICA, PUERTO_LOGICA, proceso_logica, "logica.py"):
            return 1

        print("Iniciando presentacion.py...")
        print("Cierre la ventana de presentacion para detener datos.py y logica.py.")
        return ejecutar_script("presentacion.py")
    except KeyboardInterrupt:
        print("\nEjecucion interrumpida por el usuario.")
        return 130
    finally:
        detener_proceso(proceso_logica, "logica.py")
        detener_proceso(proceso_datos, "datos.py")


def construir_parser():
    parser = argparse.ArgumentParser(
        description="Comandos de administracion del sistema de votacion TCP."
    )
    subparsers = parser.add_subparsers(dest="comando", required=True)

    comandos = {
        "initdb": (
            comando_initdb,
            "Inicializa tablas y datos en PostgreSQL.",
            ["init_db", "init-db"],
        ),
        "runserver": (comando_runserver, "Ejecuta datos, logica y presentacion.", []),
        "datos": (comando_datos, "Ejecuta solo la capa de datos.", []),
        "logica": (comando_logica, "Ejecuta solo la capa de logica.", []),
        "presentacion": (comando_presentacion, "Ejecuta solo la capa de presentacion.", []),
    }

    for nombre, (funcion, ayuda, alias) in comandos.items():
        subparser = subparsers.add_parser(nombre, aliases=alias, help=ayuda)
        subparser.set_defaults(funcion=funcion)

    return parser


def main():
    parser = construir_parser()
    args = parser.parse_args()
    return args.funcion(args)


if __name__ == "__main__":
    raise SystemExit(main())
