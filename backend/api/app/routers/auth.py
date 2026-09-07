"""Autenticación: login por email/contraseña -> JWT."""
from __future__ import annotations

import jwt
from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Request,
    status,
)
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.deps import Acceso, acceso_centro
from app.models import Centro, UsuarioStaff
from app.schemas import ForgotPasswordIn, SetPasswordIn, TabletLoginIn, TokenOut
from app.security import (
    create_access_token,
    crear_token_password,
    hash_password,
    leer_token_password,
    nonce_de_hash,
    verify_password,
)
from app.services.email import enviar_enlace_recuperacion
from app.services.rate_limit import ip_de_request, limitador_login, limitador_publico

router = APIRouter(prefix="/auth", tags=["auth"])


def _ip_cliente(request: Request) -> str:
    """IP real del cliente. Tras el proxy de Cloud Run, `request.client.host` es una
    IP interna. Cloud Run AÑADE la IP real al FINAL de X-Forwarded-For y conserva lo
    que el cliente mandara antes; por eso hay que tomar el ÚLTIMO valor, no el
    primero (que el cliente puede falsificar para rotar la clave y saltarse el
    rate-limit del login — hallazgo de auditoría de seguridad)."""
    xff = request.headers.get("x-forwarded-for")
    if xff:
        partes = [p.strip() for p in xff.split(",") if p.strip()]
        if partes:
            return partes[-1]
    return request.client.host if request.client else "desconocida"


def _clave_limite(request: Request, email: str) -> str:
    """Clave del rate-limit: IP del cliente + email (en minúsculas)."""
    return f"{_ip_cliente(request)}:{email.strip().lower()}"


@router.post("/login", response_model=TokenOut)
async def login(
    request: Request,
    form: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """`username` = email del staff. Devuelve un JWT Bearer.

    Protegido con rate-limit: tras varios fallos seguidos desde la misma IP y
    email se bloquea temporalmente (429) para frenar la fuerza bruta.
    """
    clave = _clave_limite(request, form.username)
    espera = limitador_login.segundos_bloqueo(clave)
    if espera > 0:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Demasiados intentos. Espera unos minutos e inténtalo de nuevo.",
            headers={"Retry-After": str(espera)},
        )

    # El email se guarda en minúsculas al dar de alta: normalizamos aquí también
    # para que la mayúscula/minúscula con la que se teclee no impida entrar.
    email = form.username.strip().lower()
    staff = (
        await db.execute(select(UsuarioStaff).where(UsuarioStaff.email == email))
    ).scalars().first()

    if staff is None or not verify_password(form.password, staff.password_hash) or not staff.activo:
        limitador_login.registrar_fallo(clave)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Email o contraseña incorrectos",
        )

    # Centro suspendido por la plataforma (p. ej. impago): se corta el acceso,
    # pero los datos siguen intactos hasta que se reactive.
    centro = await db.get(Centro, staff.centro_id)
    if centro is None or not centro.activo:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Centro suspendido. Contacta con Reminia para reactivarlo.",
        )

    # Login correcto: se olvida el historial de fallos de esa IP+email.
    limitador_login.limpiar(clave)

    token = create_access_token(
        subject=staff.id,
        extra={"rol": staff.rol, "centro_id": staff.centro_id},
    )
    return TokenOut(
        access_token=token,
        id=staff.id,
        rol=staff.rol,
        nombre=staff.nombre,
        centro_id=staff.centro_id,
        centro_nombre=centro.nombre,
    )


@router.post("/tablet", response_model=TokenOut)
async def login_tablet(
    request: Request,
    body: TabletLoginIn,
    db: AsyncSession = Depends(get_db),
    acceso: Acceso = Depends(acceso_centro),
):
    """Login de la MAESTRA en la tablet EMPAREJADA: elige su nombre (staff_id) y
    entra. Va por token de dispositivo (acota al centro de la tablet); solo vale
    para staff de ESE centro. Mismo JWT que el login normal.

    Por defecto NADIE tiene PIN → entra solo eligiendo su nombre. El PIN es un
    extra OPCIONAL: si ese profesional tiene PIN puesto, se le pide (y se valida).
    Rate-limit por IP+staff para el caso con PIN (frena la fuerza bruta)."""
    clave = _clave_limite(request, f"tablet:{body.staff_id}")
    espera = limitador_login.segundos_bloqueo(clave)
    if espera > 0:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Demasiados intentos. Espera unos minutos e inténtalo de nuevo.",
            headers={"Retry-After": str(espera)},
        )
    staff = await db.get(UsuarioStaff, body.staff_id)
    # Debe ser staff activo del centro de ESTA tablet.
    if staff is None or staff.centro_id != acceso.centro_id or not staff.activo:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "No autorizado")
    # SEGURIDAD: el ADMIN del centro NO entra por nombre sin contraseña (una tablet
    # perdida no debe dar acceso de administración: gestionar equipo, RGPD, export).
    # El admin usa email+contraseña (en la tablet o en el panel).
    if staff.rol == "admin_centro":
        raise HTTPException(
            status.HTTP_403_FORBIDDEN,
            "La administración entra con email y contraseña.")
    # Si tiene PIN (opcional), hay que acertarlo; si no, entra directo.
    if staff.pin_hash is not None:
        if body.pin is None or not verify_password(body.pin, staff.pin_hash):
            limitador_login.registrar_fallo(clave)
            raise HTTPException(status.HTTP_401_UNAUTHORIZED,
                                "PIN incorrecto", headers={"X-Requiere-Pin": "1"})

    centro = await db.get(Centro, staff.centro_id)
    if centro is None or not centro.activo:
        raise HTTPException(status.HTTP_403_FORBIDDEN,
                            "Centro suspendido. Contacta con Reminia para reactivarlo.")
    limitador_login.limpiar(clave)
    token = create_access_token(
        subject=staff.id,
        extra={"rol": staff.rol, "centro_id": staff.centro_id},
    )
    return TokenOut(
        access_token=token, id=staff.id, rol=staff.rol, nombre=staff.nombre,
        centro_id=staff.centro_id, centro_nombre=centro.nombre,
    )


@router.post("/set-password", response_model=TokenOut)
async def set_password(body: SetPasswordIn, db: AsyncSession = Depends(get_db)):
    """Fija la contraseña desde un enlace de alta/recuperación (token de un solo
    uso) y devuelve un JWT (auto-login). Público — el token es la credencial."""
    try:
        payload = leer_token_password(body.token)
    except jwt.PyJWTError:
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            "El enlace no es válido o ha caducado.")
    staff = await db.get(UsuarioStaff, payload.get("sub"))
    if staff is None or not staff.activo:
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            "El enlace no es válido o ha caducado.")
    if payload.get("pn") != nonce_de_hash(staff.password_hash):
        # El enlace ya se usó (la contraseña cambió) o es de una versión anterior.
        raise HTTPException(status.HTTP_400_BAD_REQUEST,
                            "Este enlace ya se usó. Pide uno nuevo.")
    staff.password_hash = hash_password(body.password)
    await db.commit()
    centro = await db.get(Centro, staff.centro_id)
    token = create_access_token(subject=staff.id,
                                extra={"rol": staff.rol, "centro_id": staff.centro_id})
    return TokenOut(
        access_token=token, id=staff.id, rol=staff.rol, nombre=staff.nombre,
        centro_id=staff.centro_id, centro_nombre=centro.nombre if centro else "",
    )


@router.post("/forgot-password")
async def forgot_password(
    body: ForgotPasswordIn,
    request: Request,
    background: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
):
    """Envía un enlace de recuperación si existe una cuenta con ese correo.
    Responde SIEMPRE igual (no revela qué correos están registrados).

    El correo se envía en SEGUNDO PLANO (BackgroundTasks): así el tiempo de
    respuesta es el mismo exista o no la cuenta. Si se esperara al envío en línea,
    la diferencia de latencia (POST a Resend vs respuesta inmediata) sería un
    oráculo de temporización que revelaría qué correos existen, anulando la
    protección de cuerpo idéntico. Rate-limit por IP contra barrido/bombardeo."""
    clave = f"forgot:{ip_de_request(request)}"
    espera = limitador_publico.segundos_bloqueo(clave)
    if espera > 0:
        raise HTTPException(
            status.HTTP_429_TOO_MANY_REQUESTS,
            "Demasiados intentos. Espera unos minutos e inténtalo de nuevo.",
            headers={"Retry-After": str(espera)})
    limitador_publico.registrar_fallo(clave)

    email = body.email.strip().lower()
    staff = (await db.execute(
        select(UsuarioStaff).where(UsuarioStaff.email == email)
    )).scalars().first()
    if staff is not None and staff.activo:
        token = crear_token_password(staff.id, staff.password_hash, minutos=60)
        url = f"{settings.panel_url}/crear-password?token={token}"
        background.add_task(enviar_enlace_recuperacion, destino=email, url=url)
    return {"mensaje": ("Si ese correo tiene una cuenta, te hemos enviado un "
                        "enlace para recuperar el acceso.")}
