"""Alta/recuperación de contraseña por ENLACE (token de un solo uso).

El acceso no se entrega como contraseña en claro por correo, sino como un enlace
con token que caduca y se invalida al usarse (embebe la huella del hash actual)."""
from __future__ import annotations

import pytest
from sqlalchemy import select

from app.models import UsuarioStaff
from app.routers.facturacion import _provisionar_signup
from app.security import crear_token_password


async def _provisionar(Session, email="admin@nuevo.es", centro="Centro Nuevo"):
    meta = {"signup": "1", "centro": centro, "email": email, "nombre": "Ana"}
    async with Session() as db:
        await _provisionar_signup(db, meta, "cus_1", "sub_1")


@pytest.mark.asyncio
async def test_crear_password_desde_enlace_autologin_y_single_use(client, Session):
    await _provisionar(Session)
    async with Session() as db:
        staff = (await db.execute(
            select(UsuarioStaff).where(UsuarioStaff.email == "admin@nuevo.es")
        )).scalars().first()
        token = crear_token_password(staff.id, staff.password_hash, 60)

    # 1) Crear la contraseña desde el enlace -> auto-login (devuelve JWT).
    r = await client.post("/auth/set-password",
                          json={"token": token, "password": "MiClaveFuerte1"})
    assert r.status_code == 200, r.text
    assert r.json()["access_token"]

    # 2) Ya puedo entrar con la nueva contraseña.
    r = await client.post("/auth/login",
                          data={"username": "admin@nuevo.es", "password": "MiClaveFuerte1"})
    assert r.status_code == 200, r.text

    # 3) El enlace ya NO vale (single-use: al cambiar la contraseña cambia la huella).
    r = await client.post("/auth/set-password",
                          json={"token": token, "password": "OtraClave1234"})
    assert r.status_code == 400, r.text


@pytest.mark.asyncio
async def test_set_password_token_invalido_400(client):
    r = await client.post("/auth/set-password",
                          json={"token": "basura.no.jwt", "password": "MiClave12345"})
    assert r.status_code == 400


@pytest.mark.asyncio
async def test_forgot_password_no_revela_si_existe(client):
    # Existente y no existente -> MISMA respuesta 200 (no enumeración de correos).
    r1 = await client.post("/auth/forgot-password",
                           json={"email": "integradora@trazo.local"})
    r2 = await client.post("/auth/forgot-password",
                           json={"email": "noexiste@nada.es"})
    assert r1.status_code == 200 and r2.status_code == 200
    assert r1.json() == r2.json()
