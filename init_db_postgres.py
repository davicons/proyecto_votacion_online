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

TABLAS_REQUERIDAS = ("usuarios", "opciones", "votos")


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


def obtener_tablas_existentes(conexion):
    filas = conexion.execute(
        """
        SELECT table_name
        FROM information_schema.tables
        WHERE table_schema = 'public'
        AND table_name IN ('usuarios', 'opciones', 'votos')
        """
    ).fetchall()
    return {fila[0] for fila in filas}


def contar_registros(conexion, tabla):
    if tabla not in TABLAS_REQUERIDAS:
        raise ValueError("Tabla no permitida")

    fila = conexion.execute(f"SELECT COUNT(*) FROM {tabla}").fetchone()
    return fila[0]


def obtener_estado(conexion):
    tablas = obtener_tablas_existentes(conexion)
    conteos = {}

    for tabla in TABLAS_REQUERIDAS:
        conteos[tabla] = contar_registros(conexion, tabla) if tabla in tablas else 0

    return {
        "tablas": tablas,
        "conteos": conteos,
        "inicializada": set(TABLAS_REQUERIDAS).issubset(tablas)
        and conteos["usuarios"] >= len(USUARIOS_PRUEBA)
        and conteos["opciones"] >= len(OPCIONES_PRUEBA),
    }


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
        estado_antes = obtener_estado(conexion)
        crear_tablas(conexion)
        insertar_datos_prueba(conexion)
        estado_despues = obtener_estado(conexion)

    return {
        "ya_estaba_inicializada": estado_antes["inicializada"],
        "estado": estado_despues,
    }


if __name__ == "__main__":
    try:
        resultado = inicializar_base_datos()
        if resultado["ya_estaba_inicializada"]:
            print("La base de datos PostgreSQL ya estaba inicializada.")
        else:
            print("Base de datos PostgreSQL inicializada correctamente.")

        conteos = resultado["estado"]["conteos"]
        print(f"Base de datos: {DB_NAME} en {DB_HOST}:{DB_PORT}")
        print(
            "Validacion: "
            f"usuarios={conteos['usuarios']}, "
            f"opciones={conteos['opciones']}, "
            f"votos={conteos['votos']}"
        )
    except psycopg.OperationalError:
        print("No se pudo conectar a PostgreSQL.")
        print("Verifique que PostgreSQL esté activo y que exista la base de datos votacion_db.")
