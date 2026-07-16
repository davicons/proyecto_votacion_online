# Presentación web

Capa de presentación alternativa para el sistema de votación. Mantiene la arquitectura original porque el navegador se comunica con Node.js por HTTP y Node.js traduce cada operación al protocolo TCP + JSON de `logica.py`.

```text
Navegador + TailwindCSS
        ↓ HTTP
Node.js presentacion_web/server.js
        ↓ TCP + JSON localhost:9000
logica.py
        ↓ TCP + JSON localhost:9001
datos.py
```

## Ejecución

Primero ejecute las capas de datos y lógica:

```bash
py manage.py datos
py manage.py logica
```

Luego, en otra terminal:

```bash
cd presentacion_web
npm start
```

Abra:

```text
http://localhost:3000
```

## Configuración opcional

- `WEB_PORT`: puerto de la interfaz web. Por defecto `3000`.
- `LOGICA_HOST`: host de `logica.py`. Por defecto `localhost`.
- `LOGICA_PORT`: puerto de `logica.py`. Por defecto `9000`.
