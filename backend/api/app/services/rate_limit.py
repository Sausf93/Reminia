"""Rate-limit en memoria para frenar fuerza bruta en el login.

MVP de un solo proceso: un diccionario en memoria basta. Si algún día se
escala a varios workers/instancias, esto se sustituye por Redis, pero la
interfaz (`comprobar` / `registrar_fallo` / `limpiar`) se mantiene.

Ventana deslizante por clave (IP + email): se guardan los instantes de los
intentos FALLIDOS; un login correcto limpia el contador de esa clave.
"""
from __future__ import annotations

import time
from collections import defaultdict
from typing import TYPE_CHECKING

if TYPE_CHECKING:  # pragma: no cover
    from fastapi import Request


def ip_de_request(request: "Request") -> str:
    """IP real del cliente detrás del proxy de Cloud Run.

    Cloud Run AÑADE la IP real al FINAL de X-Forwarded-For y conserva lo que el
    cliente mandara antes; hay que tomar el ÚLTIMO valor, no el primero (que el
    cliente puede falsificar para rotar la clave y saltarse el rate-limit)."""
    xff = request.headers.get("x-forwarded-for")
    if xff:
        partes = [p.strip() for p in xff.split(",") if p.strip()]
        if partes:
            return partes[-1]
    return request.client.host if request.client else "desconocida"


class LimitadorIntentos:
    def __init__(self, max_intentos: int = 5, ventana_seg: float = 300.0) -> None:
        self.max_intentos = max_intentos
        self.ventana_seg = ventana_seg
        self._fallos: dict[str, list[float]] = defaultdict(list)

    def _poda(self, clave: str, ahora: float) -> list[float]:
        """Descarta los fallos fuera de la ventana y devuelve los vigentes."""
        limite = ahora - self.ventana_seg
        vigentes = [t for t in self._fallos.get(clave, []) if t > limite]
        if vigentes:
            self._fallos[clave] = vigentes
        else:
            self._fallos.pop(clave, None)
        return vigentes

    def segundos_bloqueo(self, clave: str, ahora: float | None = None) -> int:
        """Si la clave está bloqueada, segundos que faltan; 0 si puede intentar."""
        ahora = time.monotonic() if ahora is None else ahora
        vigentes = self._poda(clave, ahora)
        if len(vigentes) < self.max_intentos:
            return 0
        # Se desbloquea cuando el fallo más antiguo salga de la ventana.
        libera_en = vigentes[0] + self.ventana_seg
        return max(1, int(libera_en - ahora) + 1)

    def registrar_fallo(self, clave: str, ahora: float | None = None) -> None:
        ahora = time.monotonic() if ahora is None else ahora
        self._poda(clave, ahora)
        self._fallos[clave].append(ahora)

    def limpiar(self, clave: str) -> None:
        """Login correcto: se olvida el historial de fallos de esa clave."""
        self._fallos.pop(clave, None)


# Instancia compartida por la app (5 fallos cada 5 min por IP+email).
limitador_login = LimitadorIntentos(max_intentos=5, ventana_seg=300.0)

# Límite para endpoints PÚBLICOS abusables sin login (alta self-service, olvido de
# contraseña): frena barridos de enumeración, email-bombing y spam de checkouts de
# Stripe. Más laxo en ventana que el login (una persona real usa estas rutas pocas
# veces): 5 acciones por hora y clave (normalmente la IP).
limitador_publico = LimitadorIntentos(max_intentos=5, ventana_seg=3600.0)
