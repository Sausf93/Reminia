"""Auto-alta self-service tras el pago (provisioning en el webhook).

El correo (Resend) queda desactivado en tests (sin RESEND_API_KEY): enviar_*
devuelve False sin llamar a la red, así que estos tests no tocan servicios
externos ni Stripe (se prueba la LÓGICA de provisioning directamente)."""
from __future__ import annotations

import pytest
from sqlalchemy import select

from app.models import Centro, UsuarioStaff
from app.routers.facturacion import _provisionar_signup


@pytest.mark.asyncio
async def test_signup_endpoint_es_publico_y_sin_stripe_da_503(client):
    # Sin cabeceras de auth (endpoint PÚBLICO): no debe dar 401, sino 503 porque
    # Stripe no está configurado en tests.
    r = await client.post("/facturacion/signup",
                          json={"centro": "Centro Nuevo", "email": "nuevo@ejemplo.es",
                                "nombre": "Ana"})
    assert r.status_code == 503, r.text


@pytest.mark.asyncio
async def test_provisionar_signup_crea_centro_admin_y_activa(Session):
    meta = {"signup": "1", "centro": "Residencia Los Olivos",
            "email": "Direccion@Olivos.es", "nombre": "Ana Ruiz"}
    async with Session() as db:
        await _provisionar_signup(db, meta, "cus_123", "sub_456")

    async with Session() as db:
        staff = (await db.execute(
            select(UsuarioStaff).where(UsuarioStaff.email == "direccion@olivos.es")
        )).scalars().first()
        assert staff is not None, "debe crearse la cuenta admin"
        assert staff.rol == "admin_centro"
        assert staff.password_hash, "debe tener contraseña (hash)"
        centro = await db.get(Centro, staff.centro_id)
        assert centro is not None
        assert centro.nombre == "Residencia Los Olivos"
        assert centro.estado_suscripcion == "activa"
        assert centro.stripe_customer_id == "cus_123"
        assert centro.stripe_subscription_id == "sub_456"


@pytest.mark.asyncio
async def test_provisionar_signup_es_idempotente(Session):
    meta = {"signup": "1", "centro": "Centro Doble", "email": "doble@ejemplo.es",
            "nombre": "X"}
    async with Session() as db:
        await _provisionar_signup(db, meta, "cus_1", "sub_1")
    async with Session() as db:
        await _provisionar_signup(db, meta, "cus_1", "sub_1")  # reproceso del webhook

    async with Session() as db:
        cuentas = (await db.execute(
            select(UsuarioStaff).where(UsuarioStaff.email == "doble@ejemplo.es")
        )).scalars().all()
        assert len(cuentas) == 1, "no debe duplicar la cuenta al reprocesar"
        centros = (await db.execute(
            select(Centro).where(Centro.nombre == "Centro Doble")
        )).scalars().all()
        assert len(centros) == 1, "no debe duplicar el centro"
