import hashlib
from unittest.mock import MagicMock, patch

import pytest

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


# --- respuesta_ok / respuesta_error ---

def test_respuesta_ok_basica():
    from datos import respuesta_ok
    resultado = respuesta_ok("Todo bien")
    assert resultado["estado"] == "ok"
    assert resultado["mensaje"] == "Todo bien"


def test_respuesta_ok_con_datos_extra():
    from datos import respuesta_ok
    resultado = respuesta_ok("Usuario encontrado", usuario={"id": 1, "nombre": "Ana"})
    assert resultado["estado"] == "ok"
    assert resultado["usuario"]["nombre"] == "Ana"


def test_respuesta_error_basica():
    from datos import respuesta_error
    resultado = respuesta_error("Algo falló")
    assert resultado["estado"] == "error"
    assert resultado["mensaje"] == "Algo falló"


def test_respuesta_error_con_datos_extra():
    from datos import respuesta_error
    resultado = respuesta_error("Votos alterados", votos_alterados=[1, 3])
    assert resultado["estado"] == "error"
    assert resultado["votos_alterados"] == [1, 3]


# --- generar_hash_voto ---

def test_generar_hash_voto_formato():
    from datos import generar_hash_voto
    hash_voto = generar_hash_voto(1, 2, "2026-07-30T10:00:00")
    assert len(hash_voto) == 64
    assert all(c in "0123456789abcdef" for c in hash_voto)


def test_generar_hash_voto_es_determinista():
    from datos import generar_hash_voto
    h1 = generar_hash_voto(1, 2, "2026-07-30T10:00:00")
    h2 = generar_hash_voto(1, 2, "2026-07-30T10:00:00")
    assert h1 == h2


def test_generar_hash_voto_difiere_por_usuario():
    from datos import generar_hash_voto
    h1 = generar_hash_voto(1, 2, "2026-07-30T10:00:00")
    h2 = generar_hash_voto(2, 2, "2026-07-30T10:00:00")
    assert h1 != h2


def test_generar_hash_voto_difiere_por_opcion():
    from datos import generar_hash_voto
    h1 = generar_hash_voto(1, 1, "2026-07-30T10:00:00")
    h2 = generar_hash_voto(1, 2, "2026-07-30T10:00:00")
    assert h1 != h2


def test_generar_hash_voto_difiere_por_fecha():
    from datos import generar_hash_voto
    h1 = generar_hash_voto(1, 2, "2026-07-30T10:00:00")
    h2 = generar_hash_voto(1, 2, "2026-07-30T11:00:00")
    assert h1 != h2


def test_generar_hash_voto_valor_correcto():
    from datos import generar_hash_voto
    contenido = "122026-07-30T10:00:00"
    esperado = hashlib.sha256(contenido.encode("utf-8")).hexdigest()
    assert generar_hash_voto(1, 2, "2026-07-30T10:00:00") == esperado


# --- normalizar_fecha_hora ---

def test_normalizar_fecha_hora_con_string():
    from datos import normalizar_fecha_hora
    resultado = normalizar_fecha_hora("2026-07-30T10:00:00")
    assert resultado == "2026-07-30T10:00:00"


def test_normalizar_fecha_hora_con_datetime():
    from datos import normalizar_fecha_hora
    from datetime import datetime
    dt = datetime(2026, 7, 30, 10, 0, 0)
    resultado = normalizar_fecha_hora(dt)
    assert resultado == "2026-07-30T10:00:00"
