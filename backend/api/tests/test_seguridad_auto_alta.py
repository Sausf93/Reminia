"""Seguridad del alta self-service — regresiones de la ronda 17 (auditoría adversarial).

Dos agujeros CRÍTICOS, ya cerrados, con test que impide que vuelvan:
  1) Confusión de propósito: el token de "crear contraseña" (el enlace del correo,
     purpose='set_password') NO debe servir como Bearer de sesión. Si lo hiciera, el
     enlace sería una sesión admin robable por email hasta su caducidad.
  2) Secuestro cross-tenant: el signup PÚBLICO nunca debe enganchar al que paga a un
     centro existente por coincidencia de NOMBRE (nombre libre + no único = colarse
     como admin en el centro de otro y ver datos de salud ajenos).

El correo (Resend) está desactivado en tests: enviar_* devuelve False sin tocar la
red, así que se prueba la LÓGICA sin servicios externos.
"""
from __future__ import annotations

import pytest
from sqlalchemy import select

from app.models import Centro, UsuarioStaff
from app.routers.facturacion import _provisionar_signup
from app.security import crear_token_password


async def _provisionar(Session, *, centro: str, email: str) -> None:
    meta = {"signup": "1", "centro": centro, "email": email, "nombre": "Ana"}
    async with Session() as db:
        await _provisionar_signup(db, meta, f"cus_{email}", f"sub_{email}")


@pytest.mark.asyncio
async def test_token_set_password_no_vale_como_bearer(client, Session):
    """El token del enlace de contraseña NO autentica como Bearer de sesión."""
    await _provisionar(Session, centro="Centro Alfa", email="alfa@ejemplo.es")
    async with Session() as db:
        staff = (await db.execute(
            select(UsuarioStaff).where(UsuarioStaff.email == "alfa@ejemplo.es")
        )).scalars().first()
        token = crear_token_password(staff.id, staff.password_hash, 60)

    # (1) Como Bearer contra un endpoint protegido -> 401 (no es token de sesión).
    r = await client.get("/facturacion/estado",
                         headers={"Authorization": f"Bearer {token}"})
    assert r.status_code == 401, r.text

    # (2) Pero SÍ vale para su único propósito: crear la contraseña -> auto-login.
    r = await client.post("/auth/set-password",
                          json={"token": token, "password": "MiClaveFuerte1"})
    assert r.status_code == 200, r.text
    access = r.json()["access_token"]

    # (3) El access_token normal (sin 'purpose') SÍ autentica.
    r = await client.get("/facturacion/estado",
                         headers={"Authorization": f"Bearer {access}"})
    assert r.status_code == 200, r.text


@pytest.mark.asyncio
async def test_signup_no_reutiliza_centro_por_nombre(client, Session):
    """Dos altas self-service con el MISMO nombre de centro y correos distintos
    crean DOS centros separados y aislados (no se cuelan en el mismo tenant)."""
    await _provisionar(Session, centro="Residencia Laura", email="uno@ejemplo.es")
    await _provisionar(Session, centro="Residencia Laura", email="dos@ejemplo.es")

    async with Session() as db:
        a = (await db.execute(
            select(UsuarioStaff).where(UsuarioStaff.email == "uno@ejemplo.es")
        )).scalars().first()
        b = (await db.execute(
            select(UsuarioStaff).where(UsuarioStaff.email == "dos@ejemplo.es")
        )).scalars().first()
        assert a is not None and b is not None
        assert a.centro_id != b.centro_id, "cada alta debe tener su PROPIO centro"
        centros = (await db.execute(
            select(Centro).where(Centro.nombre == "Residencia Laura")
        )).scalars().all()
        assert len(centros) == 2, "dos altas con el mismo nombre = dos centros aislados"


@pytest.mark.asyncio
async def test_provisionar_no_pisa_ids_de_stripe_de_centro_existente(Session):
    """Si un webhook de signup resuelve a un email que YA existe (creado=False), el
    provisioning NO debe escribir ids de Stripe ni 'activa' sobre ese centro: son de
    otro alta. Regresion del footgun detectado en la ronda 18."""
    meta = {"signup": "1", "centro": "Centro Uno", "email": "titular@uno.es",
            "nombre": "Ana"}
    async with Session() as db:
        await _provisionar_signup(db, meta, "cus_BUENO", "sub_BUENO")

    # Segundo webhook con el MISMO email pero ids DISTINTOS (p. ej. otra sesión).
    async with Session() as db:
        await _provisionar_signup(db, meta, "cus_MALO", "sub_MALO")

    async with Session() as db:
        staff = (await db.execute(
            select(UsuarioStaff).where(UsuarioStaff.email == "titular@uno.es")
        )).scalars().first()
        centro = await db.get(Centro, staff.centro_id)
        assert centro.stripe_customer_id == "cus_BUENO", "no debe pisar el customer id"
        assert centro.stripe_subscription_id == "sub_BUENO", "no debe pisar la sub id"
