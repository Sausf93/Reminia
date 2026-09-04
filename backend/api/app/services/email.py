"""Correo transaccional vía Resend (HTTP API).

Diseño defensivo: si `resend_api_key` está vacío (dev/tests), NO se envía nada;
se registra en log y se devuelve False. El flujo que lo llama (p. ej. el alta
automática tras el pago) NUNCA debe romperse por un problema de correo: la cuenta
ya está creada; el correo es una comodidad, no un requisito de integridad.
"""
from __future__ import annotations

import logging

import httpx

from app.config import settings

log = logging.getLogger("reminia.email")

_RESEND_URL = "https://api.resend.com/emails"
_MARCA = "Reminia"


async def enviar_email(destino: str, asunto: str, html: str) -> bool:
    """Envía un correo HTML por Resend. Devuelve True si Resend lo aceptó.

    No lanza: ante cualquier error (sin key, red, respuesta 4xx/5xx) registra y
    devuelve False, para no tumbar la operación que lo invoca."""
    if not settings.correo_activo:
        log.info("Correo desactivado (sin RESEND_API_KEY): no se envía a %s", destino)
        return False
    try:
        async with httpx.AsyncClient(timeout=15) as cli:
            r = await cli.post(
                _RESEND_URL,
                headers={"Authorization": f"Bearer {settings.resend_api_key}"},
                json={
                    "from": settings.resend_from,
                    "to": [destino],
                    "subject": asunto,
                    "html": html,
                },
            )
            r.raise_for_status()
        return True
    except Exception as e:  # noqa: BLE001 — el alta no debe romperse por el correo
        log.warning("Fallo enviando correo a %s: %s", destino, e)
        return False


def _plantilla_credenciales(
    *, nombre_centro: str, email_login: str, password: str, panel_url: str
) -> str:
    """HTML sobrio y digno (misma paleta verde agua) con las credenciales y el
    primer paso. Sin dependencias externas: estilos inline para que se vea bien
    en cualquier cliente de correo."""
    teal = "#12A99B"
    return f"""\
<div style="font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;
            max-width:520px;margin:0 auto;color:#213">
  <h1 style="color:{teal};font-size:22px;margin:0 0 4px">Bienvenida a {_MARCA}</h1>
  <p style="font-size:15px;line-height:1.5">
    Ya tienes tu cuenta de administración para <b>{nombre_centro}</b>.
    Entra al panel y deja el centro listo en unos minutos, paso a paso.
  </p>
  <div style="background:#F1F8F6;border:1px solid #D6EDE8;border-radius:12px;
              padding:16px 18px;margin:18px 0;font-size:15px">
    <div style="margin-bottom:6px"><b>Acceso al panel</b></div>
    <div>Usuario: <b>{email_login}</b></div>
    <div>Contrase&ntilde;a: <b style="font-family:monospace">{password}</b></div>
  </div>
  <a href="{panel_url}" style="display:inline-block;background:{teal};color:#fff;
     text-decoration:none;padding:12px 22px;border-radius:10px;font-weight:700">
     Entrar al panel</a>
  <p style="font-size:13px;color:#5a6b68;line-height:1.5;margin-top:18px">
    Por seguridad, <b>cambia la contrase&ntilde;a</b> la primera vez que entres.
    Si no reconoces este mensaje, ign&oacute;ralo: nadie podr&aacute; entrar sin
    esta contrase&ntilde;a.
  </p>
  <p style="font-size:12px;color:#9aa8a5;margin-top:22px">— El equipo de {_MARCA}</p>
</div>"""


async def enviar_credenciales_admin(
    *, destino: str, nombre_centro: str, email_login: str, password: str,
    panel_url: str | None = None,
) -> bool:
    """Correo de bienvenida con las credenciales del admin recién creado."""
    panel = panel_url or settings.panel_url
    asunto = f"Tu cuenta de {_MARCA} para {nombre_centro}"
    html = _plantilla_credenciales(
        nombre_centro=nombre_centro, email_login=email_login,
        password=password, panel_url=panel,
    )
    return await enviar_email(destino, asunto, html)
