# PROYECTO 2 - SISTEMA DE VOTACION EN LINEA

## Descripcion general

Sistema academico de votacion en linea desarrollado en Python 3 para Sistemas Distribuidos SI803. Los alumnos se autentican con codigo y contrasena, consultan opciones predefinidas, emiten un unico voto y pueden ver resultados actuales.

No es una aplicacion web. La solucion mantiene una arquitectura distribuida de 3 capas comunicadas por sockets TCP y mensajes JSON.

## Arquitectura usada

Se mantiene la arquitectura de 3 capas separadas:

1. Capa de presentacion: `presentacion.py`.
2. Capa de logica de negocio: `logica.py`.
3. Capa de datos: `datos.py`.

La presentacion solo se conecta a `logica.py` por TCP + JSON en `localhost:9000`. La logica solo se conecta a `datos.py` por TCP + JSON en `localhost:9001`. La unica capa que se conecta a PostgreSQL es `datos.py`.

```text
[ Capa de Presentacion ]
presentacion.py
- Login
- Menu
- Ver opciones
- Votar
- Ver resultados
- Verificar integridad

        ↓ TCP + JSON
        localhost:9000

[ Capa de Logica de Negocio ]
logica.py
- Validar usuario
- Verificar contrasena
- Rechazar doble voto
- Generar hash SHA-256
- Procesar reglas del sistema

        ↓ TCP + JSON
        localhost:9001

[ Capa de Datos ]
datos.py
- Conectarse a PostgreSQL
- Consultar usuarios
- Consultar opciones
- Registrar votos
- Consultar resultados
- Verificar integridad
```

## Stack tecnologico

- Lenguaje: Python 3
- Comunicacion: sockets TCP
- Formato de mensajes: JSON
- Base de datos: PostgreSQL
- Libreria PostgreSQL: `psycopg[binary]`
- Integridad: SHA-256 con `hashlib`

## Estructura de archivos

```text
sistema_votacion_tcp/
├── manage.py
├── presentacion.py
├── logica.py
├── datos.py
├── init_db_postgres.py
├── protocolo.md
├── README.md
├── requirements.txt
└── .env.example
```

## Explicacion de archivos

- `manage.py`: comando auxiliar para inicializar la base y ejecutar las capas en orden sin cambiar la arquitectura del sistema.
- `presentacion.py`: interfaz grafica de escritorio. Permite login, menu, votacion, resultados e integridad. Solo se conecta con `logica.py`.
- `logica.py`: servidor TCP en `localhost:9000`. Aplica reglas de negocio, verifica credenciales, evita doble voto y genera el hash SHA-256.
- `datos.py`: servidor TCP en `localhost:9001`. Es la unica capa que accede a PostgreSQL.
- `init_db_postgres.py`: crea tablas e inserta usuarios y opciones de prueba en PostgreSQL de forma idempotente.
- `protocolo.md`: documenta el protocolo TCP + JSON y ejemplos de mensajes.
- `requirements.txt`: contiene la dependencia `psycopg[binary]`.
- `.env.example`: muestra las variables de configuracion de la base de datos.

## Configuracion de PostgreSQL

Base de datos requerida:

```text
votacion_db
```

Credenciales por defecto:

```text
DB_HOST=localhost
DB_PORT=5432
DB_NAME=votacion_db
DB_USER=postgres
DB_PASSWORD=postgres
```

Puede configurar estos valores como variables de entorno o crear un archivo `.env` tomando como referencia `.env.example`.

Crear la base de datos desde terminal:

```bash
createdb votacion_db
```

Tambien puede crear la base `votacion_db` desde pgAdmin.

## Tablas

Tabla `usuarios`:

- `id SERIAL PRIMARY KEY`
- `codigo VARCHAR(20) UNIQUE NOT NULL`
- `nombre VARCHAR(100) NOT NULL`
- `password VARCHAR(100) NOT NULL`
- `ha_votado BOOLEAN DEFAULT FALSE`

Tabla `opciones`:

- `id SERIAL PRIMARY KEY`
- `nombre VARCHAR(100) NOT NULL UNIQUE`

Tabla `votos`:

- `id SERIAL PRIMARY KEY`
- `usuario_id INTEGER UNIQUE NOT NULL REFERENCES usuarios(id)`
- `opcion_id INTEGER NOT NULL REFERENCES opciones(id)`
- `fecha_hora TIMESTAMP NOT NULL`
- `hash_voto VARCHAR(64) NOT NULL`

La restriccion `UNIQUE` sobre `votos.usuario_id` impide doble voto a nivel de base de datos. Ademas, al registrar un voto se actualiza `usuarios.ha_votado = TRUE`.

## Datos de prueba

Usuarios iniciales:

| Codigo | Nombre | Contrasena |
| --- | --- | --- |
| A001 | Alumno Uno | 123456 |
| A002 | Alumno Dos | 123456 |
| A003 | Alumno Tres | 123456 |

Opciones iniciales:

- Lista A
- Lista B
- Lista C

## Instalacion

Crear entorno virtual:

```bash
python -m venv venv
```

Activar entorno virtual en Windows:

```bash
venv\Scripts\activate
```

Instalar dependencias:

```bash
pip install -r requirements.txt
```

## Inicializacion de la base de datos

Primero cree la base `votacion_db` en PostgreSQL. Luego ejecute:

```bash
py manage.py initdb
```

Tambien se acepta el alias:

```bash
py manage.py init_db
```

El script crea las tablas necesarias e inserta los datos de prueba sin duplicarlos si se ejecuta mas de una vez. Si la base ya estaba inicializada, muestra un mensaje de validacion con la cantidad de usuarios, opciones y votos registrados.

## Ejecucion

Forma recomendada:

```bash
py manage.py runserver
```

Este comando inicia `datos.py`, espera que escuche en `localhost:9001`, inicia `logica.py`, espera que escuche en `localhost:9000` y luego abre `presentacion.py`. Al cerrar la ventana de presentacion, detiene automaticamente las capas de logica y datos.

Tambien puede ejecutar cada capa de forma individual con `manage.py`:

```bash
py manage.py datos
py manage.py logica
py manage.py presentacion
```

Ejecucion manual equivalente:

```bash
python datos.py
python logica.py
python presentacion.py
```

En modo manual se recomienda abrir una terminal distinta para `datos.py`, `logica.py` y `presentacion.py`.

## Protocolo TCP + JSON

Todas las comunicaciones usan JSON terminado en salto de linea `\n`. Esto evita problemas de lectura parcial en sockets TCP.

Formato minimo de respuesta correcta:

```json
{
  "estado": "ok",
  "mensaje": "Texto descriptivo"
}
```

Formato minimo de error:

```json
{
  "estado": "error",
  "mensaje": "Texto descriptivo"
}
```

Las acciones externas se mantienen:

- `login`
- `listar_opciones`
- `votar`
- `resultados`
- `verificar_integridad`

Las acciones internas entre `logica.py` y `datos.py` tambien se mantienen:

- `obtener_usuario`
- `listar_opciones`
- `verificar_voto_usuario`
- `registrar_voto`
- `obtener_resultados`
- `verificar_integridad`

## Hash SHA-256

Cuando un alumno vota, `logica.py` genera la fecha y calcula:

```text
SHA256(str(usuario_id) + str(opcion_id) + fecha_hora)
```

Ese valor se guarda en `votos.hash_voto`. `datos.py` no genera el hash original del voto; solo almacena el hash recibido y luego lo recalcula al verificar integridad usando los datos guardados.

No se registran votos sin hash y se valida que el hash recibido coincida con `usuario_id`, `opcion_id` y `fecha_hora`.

## Concurrencia e integridad

PostgreSQL mejora la concurrencia frente a SQLite porque maneja multiples conexiones concurrentes con MVCC y bloqueo por filas. En este proyecto, `datos.py` usa una transaccion al registrar votos, bloquea el registro del usuario con `FOR UPDATE`, valida que no haya votado, valida que la opcion exista, inserta el voto y actualiza `usuarios.ha_votado`.

La integridad contra doble voto se protege en tres niveles:

- `logica.py` consulta si el alumno ya voto antes de registrar.
- `datos.py` valida nuevamente dentro de una transaccion.
- PostgreSQL impone `UNIQUE` sobre `votos.usuario_id`.

## Casos de prueba

1. Ejecutar `py manage.py initdb` y verificar que se creen las tablas.
2. Ejecutar `py manage.py runserver`.
3. Confirmar que `datos.py` escuche en `localhost:9001` y `logica.py` en `localhost:9000`.
4. Iniciar sesion con `A001` y contrasena `123456`.
5. Consultar opciones disponibles.
6. Votar por una opcion valida.
7. Intentar votar nuevamente con el mismo alumno y verificar rechazo.
8. Consultar resultados.
9. Verificar integridad de votos.
10. Intentar iniciar sesion con contrasena incorrecta y verificar rechazo.

## Limitaciones del sistema

- Las contrasenas se guardan en texto plano por simplicidad academica.
- No hay cifrado TLS en la comunicacion TCP.
- No existe panel administrativo.
- No hay control avanzado de sesiones.
- El hash detecta alteraciones, pero no reemplaza controles criptograficos avanzados.

## Conclusion

El proyecto mantiene su arquitectura distribuida de 3 capas con sockets TCP y JSON, migrando la capa de almacenamiento de SQLite a PostgreSQL sin mezclar responsabilidades entre presentacion, logica y datos.
