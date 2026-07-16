const fs = require("fs");
const http = require("http");
const net = require("net");
const path = require("path");

const HOST_LOGICA = process.env.LOGICA_HOST || "localhost";
const PUERTO_LOGICA = Number(process.env.LOGICA_PORT || 9000);
const WEB_HOST = process.env.WEB_HOST || "localhost";
const WEB_PORT = Number(process.env.WEB_PORT || 3000);
const BUFFER_MAXIMO = 1024 * 1024;
const TIMEOUT_MS = 10000;

const PUBLIC_DIR = path.join(__dirname, "public");

function respuestaError(mensaje, extra = {}) {
  return { estado: "error", mensaje, ...extra };
}

function enviarALogica(solicitud) {
  return new Promise((resolve) => {
    const cliente = net.createConnection({ host: HOST_LOGICA, port: PUERTO_LOGICA });
    const partes = [];
    let total = 0;
    let finalizado = false;

    function finalizar(respuesta) {
      if (finalizado) return;
      finalizado = true;
      cliente.destroy();
      resolve(respuesta);
    }

    cliente.setTimeout(TIMEOUT_MS);

    cliente.on("connect", () => {
      cliente.write(`${JSON.stringify(solicitud)}\n`, "utf8");
    });

    cliente.on("data", (bloque) => {
      partes.push(bloque);
      total += bloque.length;

      if (total > BUFFER_MAXIMO) {
        finalizar(respuestaError("Respuesta demasiado grande del servidor de lógica."));
        return;
      }

      const datos = Buffer.concat(partes);
      const finMensaje = datos.indexOf(10);
      if (finMensaje === -1) return;

      try {
        const linea = datos.subarray(0, finMensaje).toString("utf8");
        finalizar(JSON.parse(linea));
      } catch (_error) {
        finalizar(respuestaError("Respuesta inválida del servidor de lógica."));
      }
    });

    cliente.on("timeout", () => {
      finalizar(respuestaError("Tiempo de espera agotado con el servidor de lógica."));
    });

    cliente.on("error", () => {
      finalizar(
        respuestaError(
          "No se pudo conectar con el servidor de lógica. Verifique que logica.py esté en ejecución."
        )
      );
    });
  });
}

function leerCuerpoJson(req) {
  return new Promise((resolve, reject) => {
    const partes = [];
    let total = 0;

    req.on("data", (bloque) => {
      total += bloque.length;
      if (total > BUFFER_MAXIMO) {
        reject(Object.assign(new Error("Solicitud demasiado grande."), { statusCode: 413 }));
        req.destroy();
        return;
      }
      partes.push(bloque);
    });

    req.on("end", () => {
      const texto = Buffer.concat(partes).toString("utf8").trim();
      if (!texto) {
        resolve({});
        return;
      }

      try {
        resolve(JSON.parse(texto));
      } catch (_error) {
        reject(Object.assign(new Error("JSON inválido."), { statusCode: 400 }));
      }
    });

    req.on("error", reject);
  });
}

function responderJson(res, statusCode, datos) {
  const contenido = JSON.stringify(datos);
  res.writeHead(statusCode, {
    "Content-Type": "application/json; charset=utf-8",
    "Content-Length": Buffer.byteLength(contenido),
  });
  res.end(contenido);
}

async function manejarApi(req, res, pathname) {
  try {
    if (req.method === "POST" && pathname === "/api/login") {
      const cuerpo = await leerCuerpoJson(req);
      responderJson(res, 200, await enviarALogica({
        accion: "login",
        codigo: cuerpo.codigo,
        password: cuerpo.password,
      }));
      return;
    }

    if (req.method === "GET" && pathname === "/api/opciones") {
      responderJson(res, 200, await enviarALogica({ accion: "listar_opciones" }));
      return;
    }

    if (req.method === "POST" && pathname === "/api/votar") {
      const cuerpo = await leerCuerpoJson(req);
      responderJson(res, 200, await enviarALogica({
        accion: "votar",
        usuario_id: cuerpo.usuario_id,
        opcion_id: cuerpo.opcion_id,
      }));
      return;
    }

    if (req.method === "GET" && pathname === "/api/resultados") {
      responderJson(res, 200, await enviarALogica({ accion: "resultados" }));
      return;
    }

    if (req.method === "GET" && pathname === "/api/integridad") {
      responderJson(res, 200, await enviarALogica({ accion: "verificar_integridad" }));
      return;
    }

    responderJson(res, 404, respuestaError("Ruta API no encontrada."));
  } catch (error) {
    responderJson(res, error.statusCode || 500, respuestaError(error.message || "Error interno."));
  }
}

function tipoContenido(ruta) {
  const extension = path.extname(ruta).toLowerCase();
  const tipos = {
    ".html": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".svg": "image/svg+xml",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
  };
  return tipos[extension] || "application/octet-stream";
}

function servirArchivo(req, res, pathname) {
  const rutaSolicitada = pathname === "/" ? "/index.html" : pathname;
  const rutaArchivo = path.normalize(path.join(PUBLIC_DIR, rutaSolicitada));

  if (!rutaArchivo.startsWith(`${PUBLIC_DIR}${path.sep}`) && rutaArchivo !== PUBLIC_DIR) {
    res.writeHead(403);
    res.end("Acceso denegado");
    return;
  }

  fs.readFile(rutaArchivo, (error, contenido) => {
    if (error) {
      res.writeHead(404, { "Content-Type": "text/plain; charset=utf-8" });
      res.end("Archivo no encontrado");
      return;
    }

    res.writeHead(200, { "Content-Type": tipoContenido(rutaArchivo) });
    res.end(contenido);
  });
}

const servidor = http.createServer((req, res) => {
  const url = new URL(req.url, `http://${req.headers.host}`);

  if (url.pathname.startsWith("/api/")) {
    manejarApi(req, res, url.pathname);
    return;
  }

  servirArchivo(req, res, url.pathname);
});

servidor.listen(WEB_PORT, WEB_HOST, () => {
  console.log(`Presentación web disponible en http://${WEB_HOST}:${WEB_PORT}`);
  console.log(`Conectando con lógica en ${HOST_LOGICA}:${PUERTO_LOGICA}`);
});
