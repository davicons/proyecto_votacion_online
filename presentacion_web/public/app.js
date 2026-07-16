const estado = {
  usuario: null,
  opciones: [],
};

const loginView = document.getElementById("loginView");
const appView = document.getElementById("appView");
const loginForm = document.getElementById("loginForm");
const loginMensaje = document.getElementById("loginMensaje");
const loginButton = document.getElementById("loginButton");
const usuarioNombre = document.getElementById("usuarioNombre");
const usuarioCodigo = document.getElementById("usuarioCodigo");
const contenido = document.getElementById("contenido");
const alerta = document.getElementById("alerta");
const loadingTemplate = document.getElementById("loadingTemplate");

async function api(ruta, opciones = {}) {
  const respuesta = await fetch(ruta, {
    headers: { "Content-Type": "application/json" },
    ...opciones,
  });

  if (!respuesta.ok) {
    throw new Error("No se pudo completar la solicitud web.");
  }

  return respuesta.json();
}

function mostrarAlerta(mensaje, tipo = "error") {
  alerta.className = `mb-5 rounded-2xl px-4 py-3 text-sm font-bold ${
    tipo === "ok"
      ? "bg-emerald-100 text-emerald-800 ring-1 ring-emerald-200"
      : "bg-red-100 text-red-800 ring-1 ring-red-200"
  }`;
  alerta.textContent = mensaje;
  alerta.classList.remove("hidden");
}

function ocultarAlerta() {
  alerta.classList.add("hidden");
  alerta.textContent = "";
}

function mostrarCargando() {
  contenido.replaceChildren(loadingTemplate.content.cloneNode(true));
}

function escapar(texto) {
  return String(texto ?? "")
    .replaceAll("&", "&amp;")
    .replaceAll("<", "&lt;")
    .replaceAll(">", "&gt;")
    .replaceAll('"', "&quot;")
    .replaceAll("'", "&#039;");
}

function activarApp(usuario) {
  estado.usuario = usuario;
  usuarioNombre.textContent = usuario.nombre;
  usuarioCodigo.textContent = `Código: ${usuario.codigo}`;
  loginView.classList.add("hidden");
  appView.classList.remove("hidden");
  mostrarInicio();
}

function mostrarInicio() {
  ocultarAlerta();
  contenido.innerHTML = `
    <div class="rounded-3xl bg-white p-7 ring-1 ring-slate-200">
      <p class="text-sm font-black uppercase tracking-[0.24em] text-blue-600">Panel principal</p>
      <h2 class="mt-3 text-4xl font-black text-slate-950">Bienvenido, ${escapar(estado.usuario.nombre)}</h2>
      <p class="mt-4 max-w-2xl text-slate-600">
        Seleccione una opción del menú. Las acciones se envían al servidor Node.js y luego a la capa de lógica mediante socket TCP.
      </p>
      <div class="mt-7 grid gap-4 md:grid-cols-3">
        <article class="rounded-2xl bg-blue-50 p-5 ring-1 ring-blue-100">
          <p class="text-2xl font-black text-blue-700">Opciones</p>
          <p class="mt-2 text-sm text-blue-900/70">Consulta las listas disponibles.</p>
        </article>
        <article class="rounded-2xl bg-emerald-50 p-5 ring-1 ring-emerald-100">
          <p class="text-2xl font-black text-emerald-700">Voto único</p>
          <p class="mt-2 text-sm text-emerald-900/70">La lógica impide votar dos veces.</p>
        </article>
        <article class="rounded-2xl bg-violet-50 p-5 ring-1 ring-violet-100">
          <p class="text-2xl font-black text-violet-700">Integridad</p>
          <p class="mt-2 text-sm text-violet-900/70">Los votos se verifican con SHA-256.</p>
        </article>
      </div>
    </div>
  `;
}

function renderTablaOpciones(opciones) {
  if (!opciones.length) {
    return `<p class="rounded-2xl bg-white p-5 text-slate-600 ring-1 ring-slate-200">No hay opciones disponibles.</p>`;
  }

  return `
    <div class="overflow-hidden rounded-3xl bg-white ring-1 ring-slate-200">
      <table class="w-full text-left">
        <thead class="bg-slate-950 text-white">
          <tr>
            <th class="px-5 py-4">ID</th>
            <th class="px-5 py-4">Opción</th>
          </tr>
        </thead>
        <tbody class="divide-y divide-slate-100">
          ${opciones.map((opcion) => `
            <tr>
              <td class="px-5 py-4 font-black text-blue-700">${escapar(opcion.id)}</td>
              <td class="px-5 py-4 font-semibold text-slate-700">${escapar(opcion.nombre)}</td>
            </tr>
          `).join("")}
        </tbody>
      </table>
    </div>
  `;
}

async function cargarOpciones() {
  ocultarAlerta();
  mostrarCargando();
  const respuesta = await api("/api/opciones");
  if (respuesta.estado !== "ok") {
    mostrarAlerta(respuesta.mensaje || "No se pudieron consultar las opciones.");
    contenido.innerHTML = "";
    return [];
  }
  estado.opciones = respuesta.opciones || [];
  return estado.opciones;
}

async function mostrarOpciones() {
  const opciones = await cargarOpciones();
  contenido.innerHTML = `
    <div class="mb-5">
      <p class="text-sm font-black uppercase tracking-[0.24em] text-blue-600">Consulta</p>
      <h2 class="mt-2 text-3xl font-black text-slate-950">Opciones disponibles</h2>
    </div>
    ${renderTablaOpciones(opciones)}
  `;
}

async function mostrarFormularioVoto() {
  const opciones = await cargarOpciones();
  contenido.innerHTML = `
    <div class="mb-5">
      <p class="text-sm font-black uppercase tracking-[0.24em] text-emerald-600">Emisión de voto</p>
      <h2 class="mt-2 text-3xl font-black text-slate-950">Seleccione una opción</h2>
      <p class="mt-2 text-slate-600">Esta acción será validada por la capa de lógica y no se podrá repetir.</p>
    </div>
    <form id="votoForm" class="grid gap-3">
      ${opciones.map((opcion) => `
        <label class="flex cursor-pointer items-center gap-4 rounded-2xl bg-white p-4 ring-1 ring-slate-200 transition hover:ring-blue-300">
          <input class="h-5 w-5 accent-blue-600" type="radio" name="opcion_id" value="${escapar(opcion.id)}" required />
          <span>
            <span class="block text-lg font-black text-slate-900">${escapar(opcion.nombre)}</span>
            <span class="text-sm text-slate-500">Opción ${escapar(opcion.id)}</span>
          </span>
        </label>
      `).join("")}
      <button class="mt-4 rounded-2xl bg-emerald-600 px-5 py-3 font-black text-white shadow-lg shadow-emerald-600/20 transition hover:bg-emerald-700" type="submit">
        Confirmar voto
      </button>
    </form>
  `;

  document.getElementById("votoForm")?.addEventListener("submit", confirmarVoto);
}

async function confirmarVoto(evento) {
  evento.preventDefault();
  ocultarAlerta();

  const datos = new FormData(evento.currentTarget);
  const opcionId = Number(datos.get("opcion_id"));
  if (!opcionId) {
    mostrarAlerta("Debe seleccionar una opción para votar.");
    return;
  }

  const confirmado = confirm("¿Está seguro de emitir su voto? Esta acción no se puede modificar.");
  if (!confirmado) return;

  try {
    mostrarCargando();
    const respuesta = await api("/api/votar", {
      method: "POST",
      body: JSON.stringify({ usuario_id: estado.usuario.id, opcion_id: opcionId }),
    });

    if (respuesta.estado === "ok") {
      estado.usuario.ha_votado = true;
      mostrarInicio();
      mostrarAlerta(respuesta.mensaje || "Voto registrado correctamente.", "ok");
    } else {
      await mostrarFormularioVoto();
      mostrarAlerta(respuesta.mensaje || "No se pudo registrar el voto.");
    }
  } catch (error) {
    mostrarAlerta(error.message || "No se pudo registrar el voto.");
  }
}

async function mostrarResultados() {
  ocultarAlerta();
  mostrarCargando();
  const respuesta = await api("/api/resultados");
  if (respuesta.estado !== "ok") {
    mostrarAlerta(respuesta.mensaje || "No se pudieron consultar los resultados.");
    contenido.innerHTML = "";
    return;
  }

  const resultados = respuesta.resultados || [];
  const maximo = Math.max(...resultados.map((resultado) => Number(resultado.votos)), 1);

  contenido.innerHTML = `
    <div class="mb-5">
      <p class="text-sm font-black uppercase tracking-[0.24em] text-violet-600">Conteo actual</p>
      <h2 class="mt-2 text-3xl font-black text-slate-950">Resultados</h2>
    </div>
    <div class="grid gap-4">
      ${resultados.map((resultado) => {
        const votos = Number(resultado.votos);
        const porcentaje = Math.round((votos / maximo) * 100);
        return `
          <article class="rounded-3xl bg-white p-5 ring-1 ring-slate-200">
            <div class="flex items-center justify-between gap-4">
              <h3 class="text-xl font-black text-slate-900">${escapar(resultado.opcion)}</h3>
              <span class="rounded-full bg-blue-100 px-4 py-2 text-sm font-black text-blue-700">${votos} votos</span>
            </div>
            <div class="mt-4 h-3 overflow-hidden rounded-full bg-slate-100">
              <div class="h-full rounded-full bg-blue-600" style="width: ${porcentaje}%"></div>
            </div>
          </article>
        `;
      }).join("")}
    </div>
  `;
}

async function verificarIntegridad() {
  ocultarAlerta();
  mostrarCargando();
  const respuesta = await api("/api/integridad");
  const alterados = respuesta.votos_alterados?.length
    ? `<p class="mt-3 font-bold">Votos alterados: ${escapar(respuesta.votos_alterados.join(", "))}</p>`
    : "";

  contenido.innerHTML = `
    <div class="rounded-3xl bg-white p-7 ring-1 ring-slate-200">
      <p class="text-sm font-black uppercase tracking-[0.24em] ${respuesta.estado === "ok" ? "text-emerald-600" : "text-red-600"}">Integridad de votos</p>
      <h2 class="mt-3 text-3xl font-black text-slate-950">${escapar(respuesta.mensaje || "Resultado de verificación")}</h2>
      ${alterados}
      <p class="mt-4 text-slate-600">La verificación compara el hash guardado con el hash recalculado desde los datos del voto.</p>
    </div>
  `;

  mostrarAlerta(respuesta.mensaje || "Verificación finalizada.", respuesta.estado === "ok" ? "ok" : "error");
}

loginForm.addEventListener("submit", async (evento) => {
  evento.preventDefault();
  loginMensaje.textContent = "Conectando con la capa de lógica...";
  loginMensaje.className = "mt-4 min-h-6 text-sm font-semibold text-blue-700";
  loginButton.disabled = true;

  try {
    const datos = new FormData(loginForm);
    const respuesta = await api("/api/login", {
      method: "POST",
      body: JSON.stringify({
        codigo: datos.get("codigo"),
        password: datos.get("password"),
      }),
    });

    if (respuesta.estado === "ok") {
      loginMensaje.textContent = "Login correcto.";
      loginMensaje.className = "mt-4 min-h-6 text-sm font-semibold text-emerald-700";
      loginForm.reset();
      activarApp(respuesta.usuario);
      return;
    }

    loginMensaje.textContent = respuesta.mensaje || "Código o contraseña incorrectos.";
    loginMensaje.className = "mt-4 min-h-6 text-sm font-semibold text-red-700";
  } catch (error) {
    loginMensaje.textContent = error.message || "No se pudo iniciar sesión.";
    loginMensaje.className = "mt-4 min-h-6 text-sm font-semibold text-red-700";
  } finally {
    loginButton.disabled = false;
  }
});

document.querySelectorAll(".menu-btn").forEach((boton) => {
  boton.className = "rounded-2xl bg-white/10 px-4 py-3 text-left font-bold text-slate-200 transition hover:bg-blue-600 hover:text-white";
  boton.addEventListener("click", async () => {
    try {
      const vista = boton.dataset.vista;
      if (vista === "opciones") await mostrarOpciones();
      if (vista === "votar") await mostrarFormularioVoto();
      if (vista === "resultados") await mostrarResultados();
      if (vista === "integridad") await verificarIntegridad();
    } catch (error) {
      mostrarAlerta(error.message || "No se pudo completar la acción.");
    }
  });
});

document.getElementById("salirButton").addEventListener("click", () => {
  estado.usuario = null;
  estado.opciones = [];
  appView.classList.add("hidden");
  loginView.classList.remove("hidden");
  ocultarAlerta();
});
