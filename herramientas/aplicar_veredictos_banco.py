#!/usr/bin/env python3
"""Aplica al catálogo los veredictos que Saulo (y el equipo) marcan JUGANDO en el
validador de la tablet (`app.reminia.es/pendientes-valoracion`).

Esos veredictos se guardan en el backend (tabla `BancoVeredicto`, endpoint
`/banco/veredictos`, cabecera `X-Lab-Token`). Aquí se leen y se vuelcan sobre
`backend/api/app/data/catalogo.json` por NOMBRE de actividad:

  - valida     -> "estado": "validada"    (pasa a servirse a los mayores)
  - descartar  -> "estado": "descartada"  (nunca se sirve; queda el registro)
  - revisar / otro_grupo -> NO se tocan; se listan para arreglarlas a mano.

Si hay varios veredictos para la misma actividad (varios revisores), gana el más
reciente (por fecha). Es idempotente y seguro: solo cambia el estado.

Tras aplicarlo, redesplegar el backend (skill `desplegar`): el catálogo se
re-sincroniza solo al arrancar.

Uso:
    python herramientas/aplicar_veredictos_banco.py            # producción
    API_URL=http://localhost:8000 python herramientas/aplicar_veredictos_banco.py
    python herramientas/aplicar_veredictos_banco.py --dry-run  # solo informa
"""
from __future__ import annotations

import json
import os
import sys
import urllib.request
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
CATALOGO = RAIZ / "backend/api/app/data/catalogo.json"

API_URL = os.environ.get(
    "API_URL", "https://trazo-api-11684717030.europe-southwest1.run.app"
).rstrip("/")
def _token_banco() -> str:
    """Mismo token que valida el backend (app/config.py `lab_token`): si no se fija
    BANCO_TOKEN, se DERIVA del JWT_SECRET del `.env` con HMAC. Así no hay un token
    público en el repo ni hay que pasar nada a mano."""
    override = os.environ.get("BANCO_TOKEN")
    if override:
        return override
    import hashlib
    import hmac
    import re

    secreto = "dev-secret-cambiar"
    env = RAIZ / "backend/api/.env"
    if env.exists():
        m = re.search(r"^JWT_SECRET=(.*)$", env.read_text(encoding="utf-8"),
                      re.MULTILINE)
        if m:
            secreto = m.group(1).strip()
    return hmac.new(secreto.encode(), b"banco-veredictos", hashlib.sha256).hexdigest()


TOKEN = _token_banco()

_MAPA_ESTADO = {"valida": "validada", "descartar": "descartada"}


def _traer_veredictos() -> list[dict]:
    req = urllib.request.Request(
        f"{API_URL}/banco/veredictos", headers={"X-Lab-Token": TOKEN}
    )
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))


def main() -> None:
    dry = "--dry-run" in sys.argv
    try:
        veredictos = _traer_veredictos()
    except Exception as e:  # noqa: BLE001
        print(f"❌ No se pudieron leer los veredictos de {API_URL}: {e}")
        sys.exit(1)

    # Gana el más reciente por actividad.
    ultimo: dict[str, dict] = {}
    for v in veredictos:
        act = v.get("actividad", "")
        if not act:
            continue
        prev = ultimo.get(act)
        if prev is None or str(v.get("fecha", "")) >= str(prev.get("fecha", "")):
            ultimo[act] = v

    acts = json.loads(CATALOGO.read_text(encoding="utf-8"))
    por_nombre: dict[str, list[dict]] = {}
    for a in acts:
        if isinstance(a, dict):
            por_nombre.setdefault(a.get("nombre", ""), []).append(a)

    aplicados = {"validada": 0, "descartada": 0}
    a_mano: list[tuple[str, str, str]] = []  # (actividad, estado, nota)
    sin_match: list[str] = []

    for act, v in sorted(ultimo.items()):
        estado = v.get("estado", "")
        if estado in ("revisar", "otro_grupo"):
            a_mano.append((act, estado, v.get("nota", "")))
            continue
        nuevo = _MAPA_ESTADO.get(estado)
        if not nuevo:
            continue
        objetivos = por_nombre.get(act)
        if not objetivos:
            sin_match.append(act)
            continue
        for a in objetivos:
            if a.get("estado") != nuevo:
                a["estado"] = nuevo
            aplicados[nuevo] += 1

    if not dry:
        CATALOGO.write_text(
            json.dumps(acts, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )

    val = sum(1 for a in acts if isinstance(a, dict) and a.get("estado") == "validada")
    pru = sum(
        1 for a in acts if isinstance(a, dict) and a.get("estado", "en_pruebas") == "en_pruebas"
    )
    print(f"Veredictos leídos: {len(veredictos)} · actividades distintas: {len(ultimo)}")
    print(
        f"{'(DRY-RUN) ' if dry else ''}Aplicado: "
        f"{aplicados['validada']} validadas, {aplicados['descartada']} descartadas."
    )
    if a_mano:
        print(f"\n⚠️  A ARREGLAR A MANO ({len(a_mano)}) — no se tocan:")
        for act, estado, nota in a_mano:
            etq = "dudosa" if estado == "revisar" else "otro grupo"
            print(f"  · {act} [{etq}]{f' — {nota}' if nota else ''}")
    if sin_match:
        print(f"\n❓ Veredicto sin actividad en el catálogo ({len(sin_match)}):")
        for act in sin_match:
            print(f"  · {act}")
    print(f"\nCatálogo ahora: validadas={val}  en_pruebas={pru}")
    if not dry:
        print("Siguiente: redesplegar el backend (skill `desplegar`).")


if __name__ == "__main__":
    main()
