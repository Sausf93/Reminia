#!/usr/bin/env python3
"""Aplica al catálogo las decisiones exportadas por el revisor del banco.

Lee `decisiones-banco.json` ({"validar":[idx...], "descartar":[idx...]}) y marca
en `backend/api/app/data/catalogo.json` cada actividad por su índice:
  - validar   -> "estado": "validada"  (el generador ya la sirve a los mayores)
  - descartar -> "estado": "descartada" (nunca se sirve; queda el registro)
Idempotente y verificable: no toca las que no aparecen. Tras aplicarlo, redespliega
el backend (skill `desplegar`); el catálogo se re-sincroniza solo al arrancar.

Uso:
    python herramientas/aplicar_decisiones_banco.py [ruta/decisiones-banco.json]
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
CATALOGO = RAIZ / "backend/api/app/data/catalogo.json"


def main() -> None:
    dec_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("decisiones-banco.json")
    dec = json.loads(dec_path.read_text(encoding="utf-8"))
    acts = json.loads(CATALOGO.read_text(encoding="utf-8"))
    n = len(acts)

    def aplicar(indices, estado):
        hechos = 0
        for i in indices:
            if not isinstance(i, int) or not (0 <= i < n) or not isinstance(acts[i], dict):
                print(f"  ⚠️ índice inválido, salto: {i!r}")
                continue
            acts[i]["estado"] = estado
            hechos += 1
        return hechos

    v = aplicar(dec.get("validar", []), "validada")
    d = aplicar(dec.get("descartar", []), "descartada")
    CATALOGO.write_text(json.dumps(acts, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    val = sum(1 for a in acts if isinstance(a, dict) and a.get("estado") == "validada")
    pru = sum(1 for a in acts if isinstance(a, dict) and a.get("estado", "en_pruebas") == "en_pruebas")
    print(f"Aplicado: {v} validadas, {d} descartadas.")
    print(f"Catálogo ahora: total={n}  validadas={val}  en_pruebas={pru}")
    print("Siguiente: redesplegar el backend (skill `desplegar`).")


if __name__ == "__main__":
    main()
