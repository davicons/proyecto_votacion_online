import os

import psycopg


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

USUARIOS_PRUEBA = [
    ("A001", "Alumno Uno", "123456"),
    ("A002", "Alumno Dos", "123456"),
    ("A003", "Alumno Tres", "123456"),
]

OPCIONES_PRUEBA = [
    "Lista A",
    "Lista B",
    "Lista C",
]


def conectar_db():
    return psycopg.connect(
        host=DB_HOST,
        port=DB_PORT,
        dbname=DB_NAME,
        user=DB_USER,
        password=DB_PASSWORD,
    )


def crear_tablas(conexion):
    conexion.execute(
        """
        CREATE TABLE IF NOT EXISTS usuarios (
            id SERIAL PRIMARY KEY,
            codigo VARCHAR(20) UNIQUE NOT NULL,
            nombre VARCHAR(100) NOT NULL,
            password VARCHAR(100) NOT NULL,
            ha_votado BOOLEAN DEFAULT FALSE
        )
        """
    )

    conexion.execute(
        """
        CREATE TABLE IF NOT EXISTS opciones (
            id SERIAL PRIMARY KEY,
            nombre VARCHAR(100) NOT NULL UNIQUE
        )
        """
    )

    conexion.execute(
        """
        CREATE TABLE IF NOT EXISTS votos (
            id SERIAL PRIMARY KEY,
            usuario_id INTEGER UNIQUE NOT NULL REFERENCES usuarios(id),
            opcion_id INTEGER NOT NULL REFERENCES opciones(id),
            fecha_hora TIMESTAMP NOT NULL,
            hash_voto VARCHAR(64) NOT NULL
        )
        """
    )


def insertar_datos_prueba(conexion):
    cursor = conexion.cursor()

    cursor.executemany(
        """
        INSERT INTO usuarios (codigo, nombre, password)
        VALUES (%s, %s, %s)
        ON CONFLICT (codigo) DO NOTHING
        """,
        USUARIOS_PRUEBA,
    )

    cursor.executemany(
        """
        INSERT INTO opciones (nombre)
        VALUES (%s)
        ON CONFLICT (nombre) DO NOTHING
        """,
        [(nombre,) for nombre in OPCIONES_PRUEBA],
    )


def inicializar_base_datos():
    with conectar_db() as conexion:
        crear_tablas(conexion)
        insertar_datos_prueba(conexion)


if __name__ == "__main__":
    try:
        inicializar_base_datos()
        print("Base de datos PostgreSQL inicializada correctamente.")
        print(f"Base de datos: {DB_NAME} en {DB_HOST}:{DB_PORT}")
    except psycopg.OperationalError:
        print("No se pudo conectar a PostgreSQL.")
        print("Verifique que PostgreSQL esté activo y que exista la base de datos votacion_db.")
