# PROYECTO 2 - SISTEMA DE VOTACIÓN EN LÍNEA

## Descripción general

Sistema académico de votación en línea desarrollado en Python 3. Los alumnos se autentican con código y contraseña, consultan opciones predefinidas, emiten un voto único y pueden ver resultados actuales. El sistema guarda cada voto con un hash SHA-256 para detectar alteraciones posteriores en la base de datos.

No es una aplicación web. La solución usa una arquitectura distribuida de 3 capas comunicadas por sockets TCP y mensajes JSON.

## Objetivo del sistema

Implementar un sistema de votación que permita autenticar alumnos, registrar un único voto por alumno, consultar resultados y verificar la integridad de los votos almacenados.

## Arquitectura usada

Se usa arquitectura de 3 capas separadas:

1. Capa de presentación: interfaz de consola.
2. Capa de lógica de negocio: reglas del sistema.
3. Capa de datos: acceso a SQLite.

Cada capa se ejecuta en un archivo independiente. La presentación no accede a SQLite y la lógica tampoco accede directamente a la base de datos.

## Diagrama textual

```text
[ Capa de Presentación ]
presentacion.py
- Login
- Menú
- Ver opciones
- Votar
- Ver resultados
- Verificar integridad

        ↓ TCP + JSON
        Puerto 9000

[ Capa de Lógica de Negocio ]
logica.py
- Validar usuario
- Verificar contraseña
- Rechazar doble voto
- Generar hash SHA-256
- Solicitar registro de voto
- Solicitar resultados

        ↓ TCP + JSON
        Puerto 9001

[ Capa de Datos ]
datos.py
- Administrar SQLite
- Consultar usuarios
- Consultar opciones
- Guardar votos
- Consultar resultados
- Verificar integridad
```

## Stack tecnológico

- Lenguaje: Python 3
- Comunicación: sockets TCP
- Formato de mensajes: JSON
- Base de datos: SQLite
- Integridad: SHA-256 con `hashlib`

## Librerías usadas

Solo se usan librerías estándar de Python:

- `socket`
- `json`
- `sqlite3`
- `hashlib`
- `threading`
- `datetime`
- `os`

## Estructura de carpetas

```text
proyecto_votacion/
├── presentacion.py
├── logica.py
├── datos.py
├── init_db.py
├── protocolo.md
├── README.md
├── requirements.txt
└── votacion.db
```

`votacion.db` se crea al ejecutar `python init_db.py`.

## Explicación de cada archivo

- `init_db.py`: crea la base de datos, tablas, usuarios de prueba y opciones iniciales. Usa inserciones idempotentes para evitar duplicados.
- `datos.py`: servidor TCP del puerto `9001`. Es la única capa que accede a SQLite. Consulta usuarios, opciones, votos, resultados e integridad.
- `logica.py`: servidor TCP del puerto `9000`. Recibe solicitudes de presentación, valida reglas de negocio, genera hash SHA-256 y consulta a datos.
- `presentacion.py`: cliente de consola. Permite login, menú, votación, resultados e integridad. Solo se conecta con `logica.py`.
- `protocolo.md`: documenta el protocolo TCP + JSON y ejemplos de mensajes.
- `requirements.txt`: indica que no hay dependencias externas.

## Protocolo TCP + JSON

Todas las comunicaciones usan JSON terminado en salto de línea `\n`. Esto evita problemas de lectura parcial en sockets TCP.

Toda respuesta tiene como mínimo:

```json
{
  "estado": "ok",
  "mensaje": "Texto descriptivo"
}
```

o:

```json
{
  "estado": "error",
  "mensaje": "Texto descriptivo"
}
```

## Hash SHA-256

Cuando un alumno vota, `logica.py` genera la fecha y calcula:

```text
SHA256(str(usuario_id) + str(opcion_id) + fecha_hora)
```

Ese valor se guarda en la columna `hash_voto`. Al verificar integridad, `datos.py` recalcula el hash con `usuario_id`, `opcion_id` y `fecha_hora` guardados, y lo compara con `hash_voto`.

El hash no impide físicamente que alguien modifique la base de datos si tiene acceso directo al archivo SQLite. Su función es permitir detectar alteraciones en los datos de un voto.

## Base de datos

Base de datos: `votacion.db`

Tabla `usuarios`:

- `id INTEGER PRIMARY KEY AUTOINCREMENT`
- `codigo TEXT UNIQUE NOT NULL`
- `nombre TEXT NOT NULL`
- `password TEXT NOT NULL`
- `ha_votado INTEGER DEFAULT 0`

Tabla `opciones`:

- `id INTEGER PRIMARY KEY AUTOINCREMENT`
- `nombre TEXT NOT NULL`

Tabla `votos`:

- `id INTEGER PRIMARY KEY AUTOINCREMENT`
- `usuario_id INTEGER UNIQUE NOT NULL`
- `opcion_id INTEGER NOT NULL`
- `fecha_hora TEXT NOT NULL`
- `hash_voto TEXT NOT NULL`
- `FOREIGN KEY(usuario_id) REFERENCES usuarios(id)`
- `FOREIGN KEY(opcion_id) REFERENCES opciones(id)`

La restricción `UNIQUE(usuario_id)` evita doble voto a nivel de base de datos.

## Instalación

Requisitos:

- Python 3 instalado.

No se requieren dependencias externas.

## Ejecución

Ejecutar en este orden, desde la carpeta `proyecto_votacion`:

```bash
python init_db.py
python datos.py
python logica.py
python presentacion.py
```

Se recomienda abrir una terminal distinta para `datos.py`, `logica.py` y `presentacion.py`.

## Usuarios de prueba

| Código | Nombre | Contraseña |
| --- | --- | --- |
| A001 | Alumno Uno | 123456 |
| A002 | Alumno Dos | 123456 |
| A003 | Alumno Tres | 123456 |

Opciones iniciales:

- Lista A
- Lista B
- Lista C

## Casos de prueba

1. Ejecutar `python init_db.py` y verificar que se cree `votacion.db`.
2. Iniciar `datos.py` y confirmar que escuche en `localhost:9001`.
3. Iniciar `logica.py` y confirmar que escuche en `localhost:9000`.
4. Iniciar sesión con `A001` y contraseña `123456`.
5. Consultar opciones disponibles.
6. Votar por una opción válida.
7. Intentar votar nuevamente con el mismo alumno y verificar rechazo.
8. Consultar resultados.
9. Verificar integridad de votos.
10. Intentar iniciar sesión con contraseña incorrecta y verificar rechazo.

## Limitaciones del sistema

- Las contraseñas se guardan en texto plano por simplicidad académica.
- No hay cifrado TLS en la comunicación TCP.
- No existe panel administrativo.
- No hay control avanzado de sesiones.
- El hash detecta alteraciones, pero no bloquea modificaciones directas del archivo SQLite.

## Sustentación corta

- Arquitectura usada: 3 capas distribuidas separadas en presentación, lógica y datos.
- Sockets TCP: permiten comunicación entre procesos sin usar frameworks web.
- JSON: formato simple, legible y fácil de intercambiar entre capas.
- SQLite: base de datos ligera, local y suficiente para un proyecto académico.
- Doble voto: se evita con validación en lógica, verificación en datos y `UNIQUE(usuario_id)` en votos.
- Hash SHA-256: se genera con `usuario_id`, `opcion_id` y `fecha_hora` para cada voto.
- Integridad del voto: significa que los datos guardados coinciden con el hash calculado originalmente.
- Cada capa: presentación muestra consola, lógica aplica reglas, datos administra SQLite.
- La presentación no accede a la base de datos para mantener separación de responsabilidades.
- Limitaciones: no usa cifrado, contraseñas en texto plano y no reemplaza un sistema electoral real.

## Conclusión

El proyecto implementa una votación académica distribuida con comunicación TCP, mensajes JSON, almacenamiento SQLite, prevención de doble voto e integridad verificable mediante SHA-256.
