"""Correo transaccional vía Resend (HTTP API).

Diseño defensivo: si `resend_api_key` está vacío (dev/tests), NO se envía nada;
se registra en log y se devuelve False. El flujo que lo llama (p. ej. el alta
automática tras el pago) NUNCA debe romperse por un problema de correo: la cuenta
ya está creada; el correo es una comodidad, no un requisito de integridad.
"""
from __future__ import annotations

import html
import logging

import httpx

from app.config import settings

log = logging.getLogger("reminia.email")


def _esc(valor: str) -> str:
    """Escapa un texto que viene del usuario antes de meterlo en el HTML del
    correo. El nombre del centro (y otros campos) los teclea libremente quien se
    da de alta; sin escapar, alguien podría inyectar HTML en el correo que recibe
    OTRA persona (p. ej. dar de alta con el email de un tercero y un nombre de
    centro con un enlace de phishing). `html.escape` neutraliza < > & " '."""
    return html.escape(valor or "", quote=True)

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
    nombre_centro = _esc(nombre_centro)
    email_login = _esc(email_login)
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


def _plantilla_enlace(*, titulo: str, intro: str, cta: str, url: str, nota: str) -> str:
    teal = "#12A99B"
    return f"""\
<div style="font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;
            max-width:520px;margin:0 auto;color:#213">
  <h1 style="color:{teal};font-size:22px;margin:0 0 8px">{titulo}</h1>
  <p style="font-size:15px;line-height:1.5">{intro}</p>
  <p style="margin:22px 0">
    <a href="{url}" style="display:inline-block;background:{teal};color:#fff;
       text-decoration:none;padding:12px 24px;border-radius:10px;font-weight:700">
       {cta}</a>
  </p>
  <p style="font-size:13px;color:#5a6b68;line-height:1.5">{nota}</p>
  <p style="font-size:12px;color:#9aa8a5;margin-top:22px">— El equipo de {_MARCA}</p>
</div>"""


async def enviar_enlace_alta(*, destino: str, nombre_centro: str, url: str) -> bool:
    """Correo de bienvenida con un ENLACE para crear la contraseña (no se envía la
    contraseña en claro). El enlace es de un solo uso."""
    nombre_seguro = _esc(nombre_centro)
    html = _plantilla_enlace(
        titulo=f"Bienvenida a {_MARCA}",
        intro=(f"Ya tienes tu centro <b>{nombre_seguro}</b> listo. Solo falta que "
               "crees tu contraseña para entrar y dejar todo a punto, paso a paso."),
        cta="Crear mi contraseña",
        url=url,
        nota=("El enlace caduca en unos días. Si no reconoces este mensaje, "
              "ignóralo: sin crear la contraseña nadie puede entrar."),
    )
    return await enviar_email(destino, f"Crea tu acceso a {_MARCA} — {nombre_centro}", html)


async def enviar_aviso_impago(
    *, destino: str, nombre_centro: str, aviso_n: int, corte_en: int,
    url_pago: str, suspendido: bool,
) -> bool:
    """Aviso de cobro fallido (dunning). Mientras `suspendido` es False se avisa y
    se mantiene el acceso; al llegar al corte se comunica la suspensión. `url_pago`
    lleva a la factura/portal de Stripe para regularizar."""
    centro = _esc(nombre_centro)
    if suspendido:
        titulo = "Acceso suspendido por falta de pago"
        intro = (f"No hemos podido cobrar la suscripción de <b>{centro}</b> tras "
                 f"{corte_en} intentos, así que hemos <b>suspendido el acceso</b>. "
                 "Tus datos se conservan intactos; en cuanto se complete el pago, "
                 "el acceso vuelve automáticamente.")
        cta = "Regularizar el pago"
        nota = "Si crees que es un error, contáctanos y lo revisamos enseguida."
        asunto = f"Reminia — acceso suspendido ({nombre_centro})"
    else:
        titulo = "No pudimos cobrar tu suscripción"
        intro = (f"Ha fallado el cobro de la suscripción de <b>{centro}</b> "
                 f"(aviso {aviso_n} de {corte_en}). Actualiza tu método de pago "
                 "para no perder el acceso.")
        cta = "Actualizar el pago"
        nota = (f"Volveremos a intentarlo. Si tras {corte_en} intentos no se "
                "cobra, se suspenderá el acceso (tus datos se conservan).")
        asunto = f"Reminia — pago pendiente ({nombre_centro})"
    html = _plantilla_enlace(titulo=titulo, intro=intro, cta=cta, url=url_pago, nota=nota)
    return await enviar_email(destino, asunto, html)


async def enviar_enlace_recuperacion(*, destino: str, url: str) -> bool:
    """Correo con un ENLACE para elegir una nueva contraseña (recuperación)."""
    html = _plantilla_enlace(
        titulo="Recupera tu acceso",
        intro=("Has pedido recuperar tu acceso. Pulsa el botón para elegir una "
               "contraseña nueva."),
        cta="Elegir nueva contraseña",
        url=url,
        nota=("El enlace caduca en 1 hora. Si no lo pediste tú, ignóralo: tu "
              "contraseña actual sigue funcionando."),
    )
    return await enviar_email(destino, f"Recuperar tu acceso a {_MARCA}", html)
