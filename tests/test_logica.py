import hashlib
from unittest.mock import patch, MagicMock

import pytest

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# --- respuesta_ok / respuesta_error ---

def test_respuesta_ok_basica():
    from logica import respuesta_ok
    resultado = respuesta_ok("Login correcto")
    assert resultado["estado"] == "ok"
    assert resultado["mensaje"] == "Login correcto"


def test_respuesta_error_basica():
    from logica import respuesta_error
    resultado = respuesta_error("Código incorrecto")
    assert resultado["estado"] == "error"
    assert resultado["mensaje"] == "Código incorrecto"


# --- generar_hash_voto ---

def test_generar_hash_voto_longitud():
    from logica import generar_hash_voto
    resultado = generar_hash_voto(1, 2, "2026-07-30T10:00:00")
    assert len(resultado) == 64


def test_generar_hash_voto_consistente_con_datos():
    from logica import generar_hash_voto as hash_logica
    from datos import generar_hash_voto as hash_datos
    h1 = hash_logica(1, 2, "2026-07-30T10:00:00")
    h2 = hash_datos(1, 2, "2026-07-30T10:00:00")
    assert h1 == h2


# --- login ---

def test_login_sin_codigo():
    from logica import login
    resultado = login({"codigo": "", "password": "123"})
    assert resultado["estado"] == "error"


def test_login_sin_password():
    from logica import login
    resultado = login({"codigo": "A001", "password": ""})
    assert resultado["estado"] == "error"


def test_login_credenciales_correctas():
    from logica import login
    usuario_mock = {
        "id": 1,
        "codigo": "A001",
        "nombre": "Alumno Uno",
        "password": "123456",
        "ha_votado": False,
    }
    respuesta_datos_mock = {"estado": "ok", "usuario": usuario_mock}

    with patch("logica.solicitar_a_datos", return_value=respuesta_datos_mock):
        resultado = login({"codigo": "A001", "password": "123456"})

    assert resultado["estado"] == "ok"
    assert resultado["usuario"]["codigo"] == "A001"
    assert "password" not in resultado["usuario"]


def test_login_password_incorrecta():
    from logica import login
    usuario_mock = {
        "id": 1,
        "codigo": "A001",
        "nombre": "Alumno Uno",
        "password": "123456",
        "ha_votado": False,
    }
    respuesta_datos_mock = {"estado": "ok", "usuario": usuario_mock}

    with patch("logica.solicitar_a_datos", return_value=respuesta_datos_mock):
        resultado = login({"codigo": "A001", "password": "incorrecta"})

    assert resultado["estado"] == "error"


def test_login_usuario_no_encontrado():
    from logica import login
    with patch("logica.solicitar_a_datos", return_value={"estado": "error", "mensaje": "Usuario no encontrado."}):
        resultado = login({"codigo": "X999", "password": "123456"})
    assert resultado["estado"] == "error"


# --- votar ---

def test_votar_sin_usuario_id():
    from logica import votar
    resultado = votar({"opcion_id": 1})
    assert resultado["estado"] == "error"


def test_votar_sin_opcion_id():
    from logica import votar
    resultado = votar({"usuario_id": 1})
    assert resultado["estado"] == "error"


def test_votar_opcion_no_existe():
    from logica import votar
    opciones_mock = {"estado": "ok", "opciones": [{"id": 1, "nombre": "Lista A"}]}

    with patch("logica.solicitar_a_datos", return_value=opciones_mock):
        resultado = votar({"usuario_id": 1, "opcion_id": 99})

    assert resultado["estado"] == "error"
    assert "no existe" in resultado["mensaje"]


def test_votar_alumno_ya_voto():
    from logica import votar

    def mock_solicitar(solicitud):
        if solicitud["accion"] == "listar_opciones":
            return {"estado": "ok", "opciones": [{"id": 2, "nombre": "Lista B"}]}
        if solicitud["accion"] == "verificar_voto_usuario":
            return {"estado": "ok", "ya_voto": True}
        return {"estado": "error"}

    with patch("logica.solicitar_a_datos", side_effect=mock_solicitar):
        resultado = votar({"usuario_id": 1, "opcion_id": 2})

    assert resultado["estado"] == "error"
    assert "ya emitió" in resultado["mensaje"]


def test_votar_exitoso():
    from logica import votar

    def mock_solicitar(solicitud):
        if solicitud["accion"] == "listar_opciones":
            return {"estado": "ok", "opciones": [{"id": 2, "nombre": "Lista B"}]}
        if solicitud["accion"] == "verificar_voto_usuario":
            return {"estado": "ok", "ya_voto": False}
        if solicitud["accion"] == "registrar_voto":
            return {"estado": "ok", "mensaje": "Voto registrado correctamente"}
        return {"estado": "error"}

    with patch("logica.solicitar_a_datos", side_effect=mock_solicitar):
        resultado = votar({"usuario_id": 1, "opcion_id": 2})

    assert resultado["estado"] == "ok"


# --- procesar_solicitud ---

def test_procesar_solicitud_sin_accion():
    from logica import procesar_solicitud
    resultado = procesar_solicitud({})
    assert resultado["estado"] == "error"


def test_procesar_solicitud_accion_invalida():
    from logica import procesar_solicitud
    resultado = procesar_solicitud({"accion": "accion_inexistente"})
    assert resultado["estado"] == "error"
