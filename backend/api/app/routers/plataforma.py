"""Plataforma (nivel 0): alta de CENTROS y su primer admin. Reservado al dueño de
la plataforma (tú), fuera del flujo del panel.

Se protege con un token secreto (`PLATFORM_TOKEN`) enviado en la cabecera
`X-Platform-Token`. Si el token no está configurado, el endpoint queda
DESHABILITADO (responde 404) para no dejar una puerta abierta por descuido.
"""
from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, status
from sqlalchemy import Integer, cast, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.bootstrap import alta_centro_admin
from app.config import settings
from app.database import get_db
from app.models import ESTADOS_SUSCRIPCION, Centro, Intento, UsuarioFinal, UsuarioStaff
from app.schemas import (
    CentroEstadoIn,
    CentroInfoOut,
    CentroPlataformaIn,
    CentroPlataformaOut,
    CentroSuscripcionIn,
    StaffOut,
)

router = APIRouter(prefix="/plataforma", tags=["plataforma"])


def _exigir_token(x_platform_token: str | None) -> None:
    esperado = settings.platform_token or ""
    if not esperado:
        # Sin token configurado, el alta de centros no existe (puerta cerrada).
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No disponible")
    if not x_platform_token or not secrets.compare_digest(x_platform_token, esperado):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token de plataforma inválido")


@router.post("/centros", response_model=CentroPlataformaOut)
async def crear_centro(
    body: CentroPlataformaIn,
    x_platform_token: str | None = Header(default=None, alias="X-Platform-Token"),
    db: AsyncSession = Depends(get_db),
):
    """Crea (idempotente) un centro y su cuenta admin. Requiere X-Platform-Token."""
    _exigir_token(x_platform_token)
    mensaje, creado = await alta_centro_admin(
        db, body.centro, body.email, body.password, body.nombre,
        dias_prueba=body.dias_prueba)
    return CentroPlataformaOut(mensaje=mensaje, creado=creado)


@router.get("/centros", response_model=list[CentroInfoOut])
async def listar_centros(
    x_platform_token: str | None = Header(default=None, alias="X-Platform-Token"),
    db: AsyncSession = Depends(get_db),
):
    """Todos los centros con su estado (activo/bloqueado) y nº de cuentas/pacientes."""
    _exigir_token(x_platform_token)
    centros = (await db.execute(
        select(Centro).order_by(Centro.creado_en.asc())
    )).scalars().all()

    # Conteos por centro en 2 consultas (sin N+1).
    staff_tot: dict[str, int] = {}
    staff_act: dict[str, int] = {}
    for cid, tot, act in (await db.execute(
        select(UsuarioStaff.centro_id, func.count(),
               func.sum(cast(UsuarioStaff.activo, Integer)))
        .group_by(UsuarioStaff.centro_id)
    )).all():
        staff_tot[cid] = int(tot or 0)
        staff_act[cid] = int(act or 0)
    pac_tot: dict[str, int] = {}
    for cid, tot in (await db.execute(
        select(UsuarioFinal.centro_id, func.count())
        .where(UsuarioFinal.activo.is_(True))
        .group_by(UsuarioFinal.centro_id)
    )).all():
        pac_tot[cid] = int(tot or 0)

    # Personas ACTIVAS del mes (con al menos 1 intento en 30 días) por centro:
    # es la base del control de plan / facturación por excedente.
    desde = datetime.now(timezone.utc) - timedelta(days=30)
    activas: dict[str, int] = {}
    for cid, n in (await db.execute(
        select(UsuarioFinal.centro_id,
               func.count(func.distinct(Intento.usuario_final_id)))
        .join(Intento, Intento.usuario_final_id == UsuarioFinal.id)
        .where(Intento.timestamp_inicio >= desde)
        .group_by(UsuarioFinal.centro_id)
    )).all():
        activas[cid] = int(n or 0)

    salida = []
    for c in centros:
        act = activas.get(c.id, 0)
        tope = c.tope_personas or 0
        extra = max(0, act - tope) if tope else 0
        salida.append(CentroInfoOut(
            id=c.id, nombre=c.nombre, activo=c.activo, creado_en=c.creado_en,
            n_staff=staff_tot.get(c.id, 0),
            n_staff_activos=staff_act.get(c.id, 0),
            n_pacientes=pac_tot.get(c.id, 0),
            tope_personas=tope,
            personas_activas=act,
            sobre_tope=bool(tope) and act > tope,
            personas_extra=extra,
            estado_suscripcion=getattr(c, "estado_suscripcion", "cortesia"),
            fecha_fin_prueba=getattr(c, "fecha_fin_prueba", None),
            avisos_impago=getattr(c, "avisos_impago", 0) or 0,
        ))
    return salida


async def _centro_info_completo(db: AsyncSession, c: Centro) -> CentroInfoOut:
    """Ficha COMPLETA de un centro (mismos conteos que listar_centros) para que la
    respuesta de un PATCH no salga con contadores a 0 / tope 30 por defecto."""
    async def _n(q) -> int:
        return int(await db.scalar(q) or 0)
    n_staff = await _n(select(func.count()).select_from(UsuarioStaff)
                       .where(UsuarioStaff.centro_id == c.id))
    n_staff_act = await _n(select(func.count()).select_from(UsuarioStaff)
                           .where(UsuarioStaff.centro_id == c.id, UsuarioStaff.activo.is_(True)))
    n_pac = await _n(select(func.count()).select_from(UsuarioFinal)
                     .where(UsuarioFinal.centro_id == c.id, UsuarioFinal.activo.is_(True)))
    desde = datetime.now(timezone.utc) - timedelta(days=30)
    act = await _n(
        select(func.count(func.distinct(Intento.usuario_final_id)))
        .select_from(Intento)
        .join(UsuarioFinal, Intento.usuario_final_id == UsuarioFinal.id)
        .where(UsuarioFinal.centro_id == c.id, Intento.timestamp_inicio >= desde))
    tope = c.tope_personas or 0
    return CentroInfoOut(
        id=c.id, nombre=c.nombre, activo=c.activo, creado_en=c.creado_en,
        n_staff=n_staff, n_staff_activos=n_staff_act, n_pacientes=n_pac,
        tope_personas=tope, personas_activas=act,
        sobre_tope=bool(tope) and act > tope,
        personas_extra=max(0, act - tope) if tope else 0,
        estado_suscripcion=getattr(c, "estado_suscripcion", "cortesia"),
        fecha_fin_prueba=getattr(c, "fecha_fin_prueba", None),
        avisos_impago=getattr(c, "avisos_impago", 0) or 0,
    )


@router.get("/centros/{centro_id}/staff", response_model=list[StaffOut])
async def staff_de_centro(
    centro_id: str,
    x_platform_token: str | None = Header(default=None, alias="X-Platform-Token"),
    db: AsyncSession = Depends(get_db),
):
    """Cuentas de un centro (para que el super-admin vea quién puede entrar)."""
    _exigir_token(x_platform_token)
    filas = (await db.execute(
        select(UsuarioStaff)
        .where(UsuarioStaff.centro_id == centro_id)
        .order_by(UsuarioStaff.creado_en.asc())
    )).scalars().all()
    # tiene_pin es derivado (el ORM tiene pin_hash, no tiene_pin): mapearlo explícito
    # o el super-admin siempre vería tiene_pin=False.
    return [
        StaffOut(id=s.id, centro_id=s.centro_id, nombre=s.nombre, email=s.email,
                 rol=s.rol, activo=s.activo, tiene_pin=s.pin_hash is not None)
        for s in filas
    ]


@router.patch("/centros/{centro_id}", response_model=CentroInfoOut)
async def cambiar_estado_centro(
    centro_id: str,
    body: CentroEstadoIn,
    x_platform_token: str | None = Header(default=None, alias="X-Platform-Token"),
    db: AsyncSession = Depends(get_db),
):
    """Bloquea (activo=false) o reactiva (activo=true) un centro. No borra datos.

    Al bloquear, nadie de ese centro puede entrar ni usar la API (el estado se
    comprueba en cada petición). Al reactivar, todo vuelve a funcionar igual."""
    _exigir_token(x_platform_token)
    centro = await db.get(Centro, centro_id)
    if centro is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Centro no encontrado")
    centro.activo = body.activo
    await db.commit()
    await db.refresh(centro)
    return await _centro_info_completo(db, centro)


@router.patch("/centros/{centro_id}/suscripcion", response_model=CentroInfoOut)
async def cambiar_suscripcion(
    centro_id: str,
    body: CentroSuscripcionIn,
    x_platform_token: str | None = Header(default=None, alias="X-Platform-Token"),
    db: AsyncSession = Depends(get_db),
):
    """Super-admin ajusta la suscripción de un centro a mano: darle CORTESÍA (gratis
    sin caducar), SUSPENDER, reactivar, o extender la PRUEBA unos días. Útil para
    dar acceso gratis a un centro concreto o para gestionar impagos sin Stripe."""
    _exigir_token(x_platform_token)
    centro = await db.get(Centro, centro_id)
    if centro is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Centro no encontrado")
    # Validar el estado ANTES de tocar nada (no dejar mutaciones a medias).
    if body.estado is not None and body.estado not in ESTADOS_SUSCRIPCION:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_ENTITY,
            f"estado inválido (usa: {', '.join(ESTADOS_SUSCRIPCION)})")
    if body.dias_prueba is not None:
        centro.estado_suscripcion = "prueba"
        centro.fecha_fin_prueba = datetime.now(timezone.utc) + timedelta(
            days=body.dias_prueba)
    if body.estado is not None:
        centro.estado_suscripcion = body.estado
        # Al salir de 'prueba' no dejar una fecha_fin_prueba colgada (ya no aplica).
        if body.estado != "prueba":
            centro.fecha_fin_prueba = None
    await db.commit()
    await db.refresh(centro)
    return await _centro_info_completo(db, centro)
