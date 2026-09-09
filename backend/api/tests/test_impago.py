"""Impago / dunning: cobros fallidos avisan y, al AVISOS_CORTE-ésimo, suspenden.

El correo (Resend) está desactivado en tests: enviar_aviso_impago devuelve False
sin tocar la red. Se prueba la LÓGICA (contador + estado) directamente sobre los
helpers del webhook, sin depender de la firma de Stripe.
"""
from __future__ import annotations

import pytest
from sqlalchemy import select

from app.models import Centro, UsuarioStaff
from app.routers.facturacion import (
    AVISOS_CORTE,
    _mapear_estado,
    _provisionar_signup,
    _registrar_impago,
    _registrar_pago_ok,
)


async def _centro_activo(Session, email="pagador@ejemplo.es") -> str:
    """Crea un centro pagado/activo con su admin y devuelve su id."""
    meta = {"signup": "1", "centro": "Centro Pago", "email": email, "nombre": "Ana"}
    async with Session() as db:
        await _provisionar_signup(db, meta, "cus_p", "sub_p")
    async with Session() as db:
        staff = (await db.execute(
            select(UsuarioStaff).where(UsuarioStaff.email == email)
        )).scalars().first()
        return staff.centro_id


@pytest.mark.asyncio
async def test_impago_avisa_y_corta_al_tercero(Session):
    cid = await _centro_activo(Session)
    assert AVISOS_CORTE == 3

    # Avisos 1 y 2: se avisa pero NO se corta el acceso (sigue 'activa').
    for n in (1, 2):
        async with Session() as db:
            centro = await db.get(Centro, cid)
            await _registrar_impago(db, centro, n, "https://pago.stripe/x")
        async with Session() as db:
            centro = await db.get(Centro, cid)
            assert centro.avisos_impago == n
            assert centro.estado_suscripcion == "activa", f"el aviso {n} no debe cortar"

    # Aviso 3: se suspende el acceso.
    async with Session() as db:
        centro = await db.get(Centro, cid)
        await _registrar_impago(db, centro, 3, "https://pago.stripe/x")
    async with Session() as db:
        centro = await db.get(Centro, cid)
        assert centro.avisos_impago == 3
        assert centro.estado_suscripcion == "suspendido"

    # El pago vuelve a entrar: se olvidan los avisos y se reactiva el acceso.
    async with Session() as db:
        centro = await db.get(Centro, cid)
        await _registrar_pago_ok(db, centro)
    async with Session() as db:
        centro = await db.get(Centro, cid)
        assert centro.avisos_impago == 0
        assert centro.estado_suscripcion == "activa"


@pytest.mark.asyncio
async def test_impago_reentrega_mismo_evento_es_idempotente(Session):
    """Stripe puede reentregar el MISMO invoice.payment_failed. Reprocesar el mismo
    attempt_count NO debe incrementar el contador ni suspender antes de tiempo."""
    cid = await _centro_activo(Session, email="reentrega@ejemplo.es")
    # Dos fallos reales (attempt_count 1 y 2): contador a 2, sigue activa.
    for n in (1, 2):
        async with Session() as db:
            centro = await db.get(Centro, cid)
            await _registrar_impago(db, centro, n, "https://pago.stripe/x")
    # Stripe reentrega el 2º evento (mismo attempt_count=2): debe seguir en 2 y activa.
    async with Session() as db:
        centro = await db.get(Centro, cid)
        await _registrar_impago(db, centro, 2, "https://pago.stripe/x")
    async with Session() as db:
        centro = await db.get(Centro, cid)
        assert centro.avisos_impago == 2, "una reentrega no debe incrementar"
        assert centro.estado_suscripcion == "activa", "una reentrega no debe suspender"


@pytest.mark.asyncio
async def test_impago_cuenta_aunque_falte_attempt_count(Session):
    """Si Stripe no manda attempt_count, el contador incrementa igualmente."""
    cid = await _centro_activo(Session, email="otro@ejemplo.es")
    for esperado in (1, 2, 3):
        async with Session() as db:
            centro = await db.get(Centro, cid)
            await _registrar_impago(db, centro, None, "")
        async with Session() as db:
            centro = await db.get(Centro, cid)
            assert centro.avisos_impago == esperado
    async with Session() as db:
        centro = await db.get(Centro, cid)
        assert centro.estado_suscripcion == "suspendido"


def test_past_due_no_corta_directo_lo_maneja_el_dunning():
    # 'past_due' NO se traduce a suspendido aquí (lo gestiona invoice.payment_failed).
    assert _mapear_estado("past_due") is None
    assert _mapear_estado("unpaid") == "suspendido"
    assert _mapear_estado("canceled") == "cancelada"
    assert _mapear_estado("active") == "activa"
