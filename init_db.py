import os
import sqlite3


BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, "votacion.db")


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
    conexion = sqlite3.connect(DB_PATH)
    conexion.execute("PRAGMA foreign_keys = ON")
    return conexion


def crear_tablas(conexion):
    cursor = conexion.cursor()

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT UNIQUE NOT NULL,
            nombre TEXT NOT NULL,
            password TEXT NOT NULL,
            ha_votado INTEGER DEFAULT 0
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS opciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL
        )
        """
    )

    cursor.execute(
        """
        CREATE TABLE IF NOT EXISTS votos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER UNIQUE NOT NULL,
            opcion_id INTEGER NOT NULL,
            fecha_hora TEXT NOT NULL,
            hash_voto TEXT NOT NULL,
            FOREIGN KEY(usuario_id) REFERENCES usuarios(id),
            FOREIGN KEY(opcion_id) REFERENCES opciones(id)
        )
        """
    )

    conexion.commit()


def insertar_datos_prueba(conexion):
    cursor = conexion.cursor()

    cursor.executemany(
        """
        INSERT OR IGNORE INTO usuarios (codigo, nombre, password)
        VALUES (?, ?, ?)
        """,
        USUARIOS_PRUEBA,
    )

    for nombre in OPCIONES_PRUEBA:
        cursor.execute(
            """
            INSERT INTO opciones (nombre)
            SELECT ?
            WHERE NOT EXISTS (SELECT 1 FROM opciones WHERE nombre = ?)
            """,
            (nombre, nombre),
        )

    conexion.commit()


def inicializar_base_datos():
    with conectar_db() as conexion:
        crear_tablas(conexion)
        insertar_datos_prueba(conexion)


if __name__ == "__main__":
    inicializar_base_datos()
    print("Base de datos inicializada correctamente en votacion.db")
