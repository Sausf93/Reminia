"""Utilidades de seguridad: hashing de contraseñas y JWT."""
import hashlib
import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
import jwt

from app.config import settings

# Alfabeto sin caracteres ambiguos (O/0, I/l/1) para contraseñas temporales
# fáciles de teclear si hiciera falta copiarlas del correo.
_ALFABETO_PASS = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnpqrstuvwxyz23456789"


# ---- Contraseñas (bcrypt directo, sin passlib para evitar problemas de compat) ----

def hash_password(plain: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(plain.encode("utf-8"), salt).decode("utf-8")


def verify_password(plain: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))
    except (ValueError, TypeError):
        return False


def generar_password(longitud: int = 12) -> str:
    """Contraseña temporal fuerte para el alta automática (se envía por correo y
    el admin la cambia al entrar). Usa un alfabeto sin caracteres ambiguos."""
    return "".join(secrets.choice(_ALFABETO_PASS) for _ in range(longitud))


# ---- JWT ----

def create_access_token(subject: str, extra: dict | None = None) -> str:
    now = datetime.now(timezone.utc)
    payload: dict = {
        "sub": subject,
        "iat": now,
        "exp": now + timedelta(minutes=settings.jwt_expire_minutes),
    }
    if extra:
        payload.update(extra)
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def decode_access_token(token: str) -> dict:
    """Devuelve el payload de un token de ACCESO; lanza jwt.PyJWTError si es
    inválido/expirado.

    SEGURIDAD (confused-deputy): rechaza cualquier token que lleve el claim
    `purpose`. Los tokens de "crear/recuperar contraseña" (purpose='set_password')
    se firman con el MISMO secreto que los de acceso; sin este control servirían
    como Bearer de sesión (el enlace del correo daría acceso admin completo). Los
    tokens de acceso legítimos (create_access_token) nunca ponen `purpose`, así
    que este filtro no afecta al login normal."""
    payload = jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=[settings.jwt_algorithm],
    )
    if payload.get("purpose") is not None:
        raise jwt.InvalidTokenError("token de propósito no válido para sesión")
    return payload


# ---- Token de "crear/recuperar contraseña" (enlace por correo) ----
#
# En vez de mandar la contraseña en claro por email (que quedaría escrita en el
# buzón), el alta y la recuperación envían un ENLACE con este token. Lleva
# embebida la huella del hash de la contraseña ACTUAL (`pn`): en cuanto la
# contraseña se cambia, el hash (y su huella) cambian, así que el token deja de
# valer — efecto de un solo uso SIN necesidad de almacenar nada.

def nonce_de_hash(password_hash: str) -> str:
    return hashlib.sha256(password_hash.encode("utf-8")).hexdigest()[:16]


def crear_token_password(staff_id: str, password_hash: str, minutos: int) -> str:
    now = datetime.now(timezone.utc)
    payload = {
        "sub": staff_id,
        "purpose": "set_password",
        "pn": nonce_de_hash(password_hash),
        "iat": now,
        "exp": now + timedelta(minutes=minutos),
    }
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def leer_token_password(token: str) -> dict:
    """Devuelve el payload si es un token de contraseña válido; lanza
    jwt.PyJWTError si es inválido/expirado o de otro propósito."""
    payload = jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    if payload.get("purpose") != "set_password":
        raise jwt.InvalidTokenError("propósito de token inválido")
    return payload
