import json
import socket
import threading
import tkinter as tk
from tkinter import messagebox, ttk


HOST_LOGICA = "localhost"
PUERTO_LOGICA = 9000
BUFFER_SIZE = 4096
MAX_MENSAJE = 1024 * 1024
TIMEOUT_SEGUNDOS = 10

COLOR_FONDO = "#F4F6F8"
COLOR_PRIMARIO = "#1E3A8A"
COLOR_SECUNDARIO = "#2563EB"
COLOR_TEXTO = "#111827"
COLOR_EXITO = "#15803D"
COLOR_ERROR = "#B91C1C"
COLOR_BLANCO = "#FFFFFF"


class SistemaVotacionApp:
    def __init__(self):
        self.ventana = tk.Tk()
        self.ventana.title("Sistema de Votación en Línea")
        self.ventana.geometry("720x520")
        self.ventana.minsize(640, 480)
        self.ventana.configure(bg=COLOR_FONDO)

        self.usuario = None
        self.codigo_var = tk.StringVar()
        self.password_var = tk.StringVar()
        self.mensaje_var = tk.StringVar()
        self.opcion_voto_var = tk.IntVar(value=0)

        self.configurar_estilos()
        self.crear_login()

    def configurar_estilos(self):
        estilo = ttk.Style()
        estilo.theme_use("clam")

        estilo.configure("TFrame", background=COLOR_FONDO)
        estilo.configure("Card.TFrame", background=COLOR_BLANCO)
        estilo.configure(
            "Title.TLabel",
            background=COLOR_FONDO,
            foreground=COLOR_PRIMARIO,
            font=("Segoe UI", 20, "bold"),
        )
        estilo.configure(
            "Subtitle.TLabel",
            background=COLOR_FONDO,
            foreground=COLOR_TEXTO,
            font=("Segoe UI", 11),
        )
        estilo.configure(
            "CardTitle.TLabel",
            background=COLOR_BLANCO,
            foreground=COLOR_PRIMARIO,
            font=("Segoe UI", 14, "bold"),
        )
        estilo.configure(
            "Text.TLabel",
            background=COLOR_BLANCO,
            foreground=COLOR_TEXTO,
            font=("Segoe UI", 10),
        )
        estilo.configure(
            "Primary.TButton",
            background=COLOR_SECUNDARIO,
            foreground=COLOR_BLANCO,
            font=("Segoe UI", 10, "bold"),
            padding=(12, 8),
        )
        estilo.map(
            "Primary.TButton",
            background=[("active", COLOR_PRIMARIO), ("disabled", "#9CA3AF")],
            foreground=[("disabled", COLOR_BLANCO)],
        )
        estilo.configure("TEntry", padding=6, font=("Segoe UI", 10))
        estilo.configure("Treeview", font=("Segoe UI", 10), rowheight=28)
        estilo.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"))

    def ejecutar(self):
        self.ventana.mainloop()

    def limpiar_ventana(self):
        for widget in self.ventana.winfo_children():
            widget.destroy()
        self.mensaje_var.set("")

    def crear_login(self):
        self.limpiar_ventana()

        contenedor = ttk.Frame(self.ventana, padding=30)
        contenedor.pack(fill="both", expand=True)

        ttk.Label(
            contenedor,
            text="SISTEMA DE VOTACIÓN EN LÍNEA",
            style="Title.TLabel",
        ).pack(pady=(20, 6))
        ttk.Label(
            contenedor,
            text="Ingrese sus credenciales para continuar",
            style="Subtitle.TLabel",
        ).pack(pady=(0, 24))

        tarjeta = ttk.Frame(contenedor, style="Card.TFrame", padding=28)
        tarjeta.pack(ipadx=40, ipady=20)

        ttk.Label(tarjeta, text="Inicio de sesión", style="CardTitle.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 18)
        )
        ttk.Label(tarjeta, text="Código del alumno", style="Text.TLabel").grid(
            row=1, column=0, sticky="w", pady=6
        )
        codigo_entry = ttk.Entry(tarjeta, textvariable=self.codigo_var, width=30)
        codigo_entry.grid(row=1, column=1, pady=6, padx=(12, 0))

        ttk.Label(tarjeta, text="Contraseña", style="Text.TLabel").grid(
            row=2, column=0, sticky="w", pady=6
        )
        password_entry = ttk.Entry(
            tarjeta,
            textvariable=self.password_var,
            width=30,
            show="*",
        )
        password_entry.grid(row=2, column=1, pady=6, padx=(12, 0))

        ttk.Button(
            tarjeta,
            text="Iniciar sesión",
            style="Primary.TButton",
            command=self.iniciar_sesion,
        ).grid(row=3, column=0, columnspan=2, sticky="ew", pady=(20, 10))

        mensaje = tk.Label(
            tarjeta,
            textvariable=self.mensaje_var,
            bg=COLOR_BLANCO,
            fg=COLOR_ERROR,
            font=("Segoe UI", 10),
            wraplength=380,
        )
        mensaje.grid(row=4, column=0, columnspan=2, sticky="ew")

        self.ventana.bind("<Return>", lambda _evento: self.iniciar_sesion())
        codigo_entry.focus_set()

    def iniciar_sesion(self):
        codigo = self.codigo_var.get().strip()
        password = self.password_var.get().strip()

        if not codigo or not password:
            self.mostrar_mensaje("Debe ingresar código y contraseña.", es_error=True)
            return

        self.mostrar_mensaje("Conectando con el servidor de lógica...", es_error=False)
        self.ejecutar_solicitud_async(
            {"accion": "login", "codigo": codigo, "password": password},
            self.procesar_respuesta_login,
        )

    def procesar_respuesta_login(self, respuesta):
        if respuesta.get("estado") == "ok":
            self.usuario = respuesta.get("usuario")
            self.codigo_var.set("")
            self.password_var.set("")
            self.crear_menu_principal()
            messagebox.showinfo("Login correcto", respuesta.get("mensaje", "Login correcto"))
        else:
            self.mostrar_mensaje(
                respuesta.get("mensaje", "Código o contraseña incorrectos."),
                es_error=True,
            )

    def crear_menu_principal(self):
        self.limpiar_ventana()
        self.ventana.bind("<Return>", lambda _evento: None)

        contenedor = ttk.Frame(self.ventana, padding=28)
        contenedor.pack(fill="both", expand=True)

        ttk.Label(
            contenedor,
            text="SISTEMA DE VOTACIÓN EN LÍNEA",
            style="Title.TLabel",
        ).pack(anchor="w")

        datos_alumno = (
            f"Alumno autenticado: {self.usuario['nombre']} "
            f"({self.usuario['codigo']})"
        )
        ttk.Label(contenedor, text=datos_alumno, style="Subtitle.TLabel").pack(
            anchor="w", pady=(4, 18)
        )

        cuerpo = ttk.Frame(contenedor)
        cuerpo.pack(fill="both", expand=True)

        panel_botones = ttk.Frame(cuerpo, style="Card.TFrame", padding=18)
        panel_botones.pack(side="left", fill="y", padx=(0, 18))

        ttk.Label(panel_botones, text="Menú principal", style="CardTitle.TLabel").pack(
            anchor="w", pady=(0, 14)
        )

        botones = [
            ("Ver opciones", self.ver_opciones),
            ("Votar", self.votar),
            ("Ver resultados", self.ver_resultados),
            ("Verificar integridad", self.verificar_integridad),
            ("Salir", self.salir),
        ]

        for texto, comando in botones:
            ttk.Button(
                panel_botones,
                text=texto,
                style="Primary.TButton",
                command=comando,
                width=24,
            ).pack(fill="x", pady=5)

        self.panel_contenido = ttk.Frame(cuerpo, style="Card.TFrame", padding=18)
        self.panel_contenido.pack(side="left", fill="both", expand=True)

        self.mostrar_panel_inicio()

    def mostrar_panel_inicio(self):
        self.limpiar_panel_contenido()
        ttk.Label(
            self.panel_contenido,
            text="Bienvenido al sistema",
            style="CardTitle.TLabel",
        ).pack(anchor="w", pady=(0, 10))
        ttk.Label(
            self.panel_contenido,
            text="Seleccione una opción del menú para continuar.",
            style="Text.TLabel",
        ).pack(anchor="w")

    def limpiar_panel_contenido(self):
        for widget in self.panel_contenido.winfo_children():
            widget.destroy()

    def enviar_json(self, conexion, mensaje):
        datos = json.dumps(mensaje, ensure_ascii=False) + "\n"
        conexion.sendall(datos.encode("utf-8"))

    def recibir_json(self, conexion):
        partes = []
        total = 0

        while True:
            bloque = conexion.recv(BUFFER_SIZE)
            if not bloque:
                break

            partes.append(bloque)
            total += len(bloque)
            if total > MAX_MENSAJE:
                raise ValueError("Mensaje demasiado grande")
            if b"\n" in bloque:
                break

        if not partes:
            raise ValueError("No se recibió respuesta")

        linea = b"".join(partes).split(b"\n", 1)[0]
        return json.loads(linea.decode("utf-8"))

    def enviar_solicitud_logica(self, solicitud):
        try:
            with socket.create_connection(
                (HOST_LOGICA, PUERTO_LOGICA), timeout=TIMEOUT_SEGUNDOS
            ) as conexion:
                self.enviar_json(conexion, solicitud)
                return self.recibir_json(conexion)
        except (ConnectionRefusedError, TimeoutError, socket.timeout, OSError):
            return {
                "estado": "error",
                "mensaje": (
                    "No se pudo conectar con el servidor de lógica. "
                    "Verifique que logica.py esté en ejecución."
                ),
            }
        except json.JSONDecodeError:
            return {
                "estado": "error",
                "mensaje": "Respuesta inválida del servidor de lógica.",
            }
        except ValueError as error:
            return {"estado": "error", "mensaje": str(error)}

    def ejecutar_solicitud_async(self, solicitud, callback):
        self.ventana.config(cursor="watch")

        def tarea():
            respuesta = self.enviar_solicitud_logica(solicitud)
            self.ventana.after(0, lambda: self.finalizar_solicitud(callback, respuesta))

        threading.Thread(target=tarea, daemon=True).start()

    def finalizar_solicitud(self, callback, respuesta):
        self.ventana.config(cursor="")
        callback(respuesta)

    def ver_opciones(self):
        self.ejecutar_solicitud_async(
            {"accion": "listar_opciones"},
            self.mostrar_opciones_respuesta,
        )

    def mostrar_opciones_respuesta(self, respuesta):
        if respuesta.get("estado") != "ok":
            self.mostrar_error(respuesta.get("mensaje", "No se pudieron consultar las opciones."))
            return

        self.limpiar_panel_contenido()
        ttk.Label(
            self.panel_contenido,
            text="Opciones disponibles",
            style="CardTitle.TLabel",
        ).pack(anchor="w", pady=(0, 12))

        tabla = self.crear_tabla(("id", "nombre"), ("ID", "Opción"))
        for opcion in respuesta.get("opciones", []):
            tabla.insert("", "end", values=(opcion["id"], opcion["nombre"]))

    def votar(self):
        self.ejecutar_solicitud_async(
            {"accion": "listar_opciones"},
            self.mostrar_formulario_voto,
        )

    def mostrar_formulario_voto(self, respuesta):
        if respuesta.get("estado") != "ok":
            self.mostrar_error(respuesta.get("mensaje", "No se pudieron consultar las opciones."))
            return

        opciones = respuesta.get("opciones", [])
        if not opciones:
            self.mostrar_error("No hay opciones disponibles para votar.")
            return

        self.opcion_voto_var.set(0)
        self.limpiar_panel_contenido()

        ttk.Label(
            self.panel_contenido,
            text="Emitir voto",
            style="CardTitle.TLabel",
        ).pack(anchor="w", pady=(0, 10))
        ttk.Label(
            self.panel_contenido,
            text="Seleccione una opción y confirme su voto.",
            style="Text.TLabel",
        ).pack(anchor="w", pady=(0, 12))

        opciones_frame = ttk.Frame(self.panel_contenido, style="Card.TFrame")
        opciones_frame.pack(anchor="w", fill="x", pady=(0, 16))

        for opcion in opciones:
            tk.Radiobutton(
                opciones_frame,
                text=f"{opcion['id']}. {opcion['nombre']}",
                variable=self.opcion_voto_var,
                value=opcion["id"],
                bg=COLOR_BLANCO,
                fg=COLOR_TEXTO,
                activebackground=COLOR_BLANCO,
                activeforeground=COLOR_PRIMARIO,
                selectcolor=COLOR_FONDO,
                font=("Segoe UI", 10),
            ).pack(anchor="w", pady=4)

        ttk.Button(
            self.panel_contenido,
            text="Confirmar voto",
            style="Primary.TButton",
            command=self.confirmar_voto,
        ).pack(anchor="w")

    def confirmar_voto(self):
        opcion_id = self.opcion_voto_var.get()
        if not opcion_id:
            self.mostrar_error("Debe seleccionar una opción para votar.")
            return

        confirmar = messagebox.askyesno(
            "Confirmar voto",
            "¿Está seguro de emitir su voto? Esta acción no se puede modificar.",
        )
        if not confirmar:
            return

        self.ejecutar_solicitud_async(
            {
                "accion": "votar",
                "usuario_id": self.usuario["id"],
                "opcion_id": opcion_id,
            },
            self.procesar_respuesta_voto,
        )

    def procesar_respuesta_voto(self, respuesta):
        mensaje = respuesta.get("mensaje", "Respuesta sin mensaje.")
        if respuesta.get("estado") == "ok":
            self.usuario["ha_votado"] = 1
            messagebox.showinfo("Voto registrado", mensaje)
            self.mostrar_panel_inicio()
        else:
            self.mostrar_error(mensaje)

    def ver_resultados(self):
        self.ejecutar_solicitud_async(
            {"accion": "resultados"},
            self.mostrar_resultados_respuesta,
        )

    def mostrar_resultados_respuesta(self, respuesta):
        if respuesta.get("estado") != "ok":
            self.mostrar_error(respuesta.get("mensaje", "No se pudieron consultar los resultados."))
            return

        self.limpiar_panel_contenido()
        ttk.Label(
            self.panel_contenido,
            text="Resultados actuales",
            style="CardTitle.TLabel",
        ).pack(anchor="w", pady=(0, 12))

        tabla = self.crear_tabla(("opcion", "votos"), ("Opción", "Votos"))
        for resultado in respuesta.get("resultados", []):
            tabla.insert("", "end", values=(resultado["opcion"], resultado["votos"]))

    def verificar_integridad(self):
        self.ejecutar_solicitud_async(
            {"accion": "verificar_integridad"},
            self.mostrar_integridad_respuesta,
        )

    def mostrar_integridad_respuesta(self, respuesta):
        mensaje = respuesta.get("mensaje", "Respuesta sin mensaje.")

        if respuesta.get("votos_alterados"):
            mensaje = f"{mensaje}\nVotos alterados: {respuesta['votos_alterados']}"

        if respuesta.get("estado") == "ok":
            messagebox.showinfo("Integridad de votos", mensaje)
        else:
            messagebox.showerror("Integridad de votos", mensaje)

    def crear_tabla(self, columnas, encabezados):
        tabla = ttk.Treeview(
            self.panel_contenido,
            columns=columnas,
            show="headings",
            height=8,
        )

        for columna, encabezado in zip(columnas, encabezados):
            tabla.heading(columna, text=encabezado)
            tabla.column(columna, anchor="center", width=160)

        tabla.pack(fill="both", expand=True)
        return tabla

    def mostrar_mensaje(self, mensaje, es_error=False):
        self.mensaje_var.set(mensaje)
        color = COLOR_ERROR if es_error else COLOR_EXITO
        for widget in self.ventana.winfo_children():
            self.actualizar_color_mensaje(widget, color)

    def actualizar_color_mensaje(self, widget, color):
        if isinstance(widget, tk.Label) and str(widget.cget("textvariable")):
            widget.configure(fg=color)
        for hijo in widget.winfo_children():
            self.actualizar_color_mensaje(hijo, color)

    def mostrar_error(self, mensaje):
        messagebox.showerror("Error", mensaje)

    def salir(self):
        if messagebox.askyesno("Salir", "¿Desea cerrar el sistema?"):
            self.ventana.destroy()


if __name__ == "__main__":
    app = SistemaVotacionApp()
    app.ejecutar()
