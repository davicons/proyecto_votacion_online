# Protocolo TCP + JSON

## Descripción

El sistema usa sockets TCP y mensajes JSON para comunicar sus capas. Cada mensaje JSON termina con salto de línea `\n`, lo que permite detectar el final del mensaje recibido por el socket.

Formato mínimo de respuesta:

```json
{
  "estado": "ok",
  "mensaje": "Texto descriptivo"
}
```

Formato mínimo de error:

```json
{
  "estado": "error",
  "mensaje": "Texto descriptivo"
}
```

## Puertos usados

- `presentacion.py` se conecta a `logica.py` en `localhost:9000`.
- `logica.py` se conecta a `datos.py` en `localhost:9001`.
- `datos.py` escucha en `localhost:9001`.
- `logica.py` escucha en `localhost:9000`.

## Acciones entre presentación y lógica

### Login

Solicitud:

```json
{
  "accion": "login",
  "codigo": "A001",
  "password": "123456"
}
```

Respuesta correcta:

```json
{
  "estado": "ok",
  "mensaje": "Login correcto",
  "usuario": {
    "id": 1,
    "codigo": "A001",
    "nombre": "Alumno Uno",
    "ha_votado": 0
  }
}
```

Respuesta incorrecta:

```json
{
  "estado": "error",
  "mensaje": "Código o contraseña incorrectos"
}
```

### Listar opciones

Solicitud:

```json
{
  "accion": "listar_opciones"
}
```

Respuesta:

```json
{
  "estado": "ok",
  "mensaje": "Opciones consultadas correctamente",
  "opciones": [
    { "id": 1, "nombre": "Lista A" },
    { "id": 2, "nombre": "Lista B" },
    { "id": 3, "nombre": "Lista C" }
  ]
}
```

### Votar

Solicitud:

```json
{
  "accion": "votar",
  "usuario_id": 1,
  "opcion_id": 2
}
```

Respuesta correcta:

```json
{
  "estado": "ok",
  "mensaje": "Voto registrado correctamente"
}
```

Respuesta si ya votó:

```json
{
  "estado": "error",
  "mensaje": "El alumno ya emitió su voto. No puede votar dos veces."
}
```

Respuesta si la opción no existe:

```json
{
  "estado": "error",
  "mensaje": "La opción seleccionada no existe"
}
```

### Resultados

Solicitud:

```json
{
  "accion": "resultados"
}
```

Respuesta:

```json
{
  "estado": "ok",
  "mensaje": "Resultados consultados correctamente",
  "resultados": [
    { "opcion": "Lista A", "votos": 2 },
    { "opcion": "Lista B", "votos": 1 },
    { "opcion": "Lista C", "votos": 0 }
  ]
}
```

### Verificar integridad

Solicitud:

```json
{
  "accion": "verificar_integridad"
}
```

Respuesta correcta:

```json
{
  "estado": "ok",
  "mensaje": "Todos los votos mantienen su integridad"
}
```

Respuesta con alteraciones:

```json
{
  "estado": "error",
  "mensaje": "Se detectaron votos alterados",
  "votos_alterados": [1, 3]
}
```

## Acciones internas entre lógica y datos

- `obtener_usuario`: consulta usuario por código.
- `listar_opciones`: obtiene opciones de votación.
- `verificar_voto_usuario`: confirma si un alumno ya votó.
- `registrar_voto`: guarda voto con fecha y hash.
- `obtener_resultados`: calcula votos por opción.
- `verificar_integridad`: recalcula hashes y detecta votos alterados.

Ejemplo interno para registrar voto:

```json
{
  "accion": "registrar_voto",
  "usuario_id": 1,
  "opcion_id": 2,
  "fecha_hora": "2026-06-22T10:30:00",
  "hash_voto": "hash_sha256_generado"
}
```

## Errores posibles

- `Código o contraseña incorrectos`
- `El alumno ya emitió su voto. No puede votar dos veces.`
- `La opción seleccionada no existe`
- `No se pudo conectar con el servidor de lógica.`
- `No se pudo conectar con el servidor de datos.`
- `Acción no reconocida`
- `JSON inválido`
- `Error interno del servidor`

## Flujo de comunicación entre capas

1. `presentacion.py` solicita login a `logica.py` por TCP/JSON.
2. `logica.py` solicita el usuario a `datos.py`.
3. `datos.py` consulta SQLite y responde a `logica.py`.
4. `logica.py` valida contraseña y responde a `presentacion.py`.
5. Para votar, `presentacion.py` envía `usuario_id` y `opcion_id` a `logica.py`.
6. `logica.py` verifica opción, doble voto, fecha y hash.
7. `logica.py` ordena a `datos.py` registrar el voto.
8. `datos.py` inserta el voto, actualiza `ha_votado` y responde.
9. `presentacion.py` muestra el resultado al alumno.
