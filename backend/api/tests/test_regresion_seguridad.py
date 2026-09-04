"""Regresiones de seguridad/medición (rondas 13-14). Blindan fixes concretos:

1. La compuerta legal (RGPD) NO se puede saltar por `editar_sesion_programada`
   (bypass verificado: crear programada vacía -> PUT /config con persona sin
   consentimiento). Debe devolver 409.
2. El camino de PAGO sigue accesible con la prueba caducada (require_roles_para_pago
   salta la compuerta de suscripción): /facturacion/checkout NO devuelve 403.
3. contar/sumar puntúan 'parcial' el fallo por UNA unidad (no 0), como el dinero.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from app.models import Centro
from app.services.correccion import corregir


async def _login(client, email="integradora@trazo.local", pw="trazo1234"):
    r = await client.post("/auth/login", data={"username": email, "password": pw})
    assert r.status_code == 200, r.text
    return {"Authorization": "Bearer " + r.json()["access_token"]}


# 1) Compuerta legal RGPD: no colar personas sin consentimiento por la edición.
@pytest.mark.asyncio
async def test_editar_programada_no_salta_la_compuerta_legal(client):
    headers = await _login(client)
    # Persona nueva SIN consentimiento (el seed no le da consentimiento).
    r = await client.post("/usuarios", headers=headers,
                          json={"alias_interno": "Sin consentimiento"})
    assert r.status_code == 201, r.text
    uid = r.json()["id"]

    # Sanity: crearla directamente en una sesión -> la compuerta la bloquea (409).
    r = await client.post("/sesiones", headers=headers,
                          json={"tipo": "individual", "programar": True,
                                "participantes": [uid]})
    assert r.status_code == 409, r.text

    # BYPASS (ya cerrado): crear programada VACÍA (pasa la puerta, solo DPA) y
    # colar a la persona sin consentimiento por PUT /config.
    r = await client.post("/sesiones", headers=headers,
                          json={"tipo": "individual", "programar": True,
                                "participantes": []})
    assert r.status_code == 201, r.text
    sid = r.json()["id"]

    r = await client.put(f"/sesiones/{sid}/config", headers=headers,
                         json={"participantes": [uid], "configs": []})
    assert r.status_code == 409, r.text  # el fix cierra el bypass


# 2) El camino de pago sigue abierto con la prueba caducada.
@pytest.mark.asyncio
async def test_checkout_accesible_con_prueba_caducada(client, Session):
    headers = await _login(client, "admin@trazo.local", "trazo1234")
    ayer = datetime.now(timezone.utc) - timedelta(days=1)
    async with Session() as s:
        centro = (await s.execute(select(Centro))).scalars().first()
        centro.estado_suscripcion = "prueba"
        centro.fecha_fin_prueba = ayer
        await s.commit()

    # Un endpoint operativo normal SÍ se corta (compuerta de suscripción).
    r = await client.get("/pendientes", headers=headers)
    assert r.status_code == 403, r.text

    # Pero el checkout NO da 403: require_roles_para_pago salta la compuerta de
    # suscripción. Da 503 porque Stripe no está configurado en tests (no 403).
    r = await client.post("/facturacion/checkout", headers=headers)
    assert r.status_code == 503, r.text


# 3) contar/sumar: fallo por una unidad = parcial (no no_logrado).
def test_contar_sumar_banda_parcial():
    obj = {"solucion": {"cantidad": 12}}
    assert corregir("conteo_comparacion", {"modo": "contar", "respuesta": 12}, obj) == "logrado"
    assert corregir("conteo_comparacion", {"modo": "contar", "respuesta": 11}, obj) == "parcial"
    assert corregir("conteo_comparacion", {"modo": "contar", "respuesta": 13}, obj) == "parcial"
    assert corregir("conteo_comparacion", {"modo": "contar", "respuesta": 8}, obj) == "no_logrado"

    obj_s = {"solucion": {"total": 15}}
    assert corregir("conteo_comparacion", {"modo": "sumar", "respuesta": 15}, obj_s) == "logrado"
    assert corregir("conteo_comparacion", {"modo": "sumar", "respuesta": 14}, obj_s) == "parcial"
    assert corregir("conteo_comparacion", {"modo": "sumar", "respuesta": 3}, obj_s) == "no_logrado"
