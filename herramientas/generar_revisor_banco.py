#!/usr/bin/env python3
"""Genera un REVISOR OFFLINE de las actividades pendientes de validar (banco).

La compuerta de calidad vive en `backend/api/app/data/catalogo.json`: una
actividad se sirve a los mayores solo cuando tiene `"estado": "validada"`. El
resto (`en_pruebas`) espera revisión humana.

Este script lee el catálogo, extrae las `en_pruebas` y escribe un HTML
autocontenido (`revisor-banco.html`) que Saulo abre en el navegador para
revisarlas rápido (atajos V=validar, D=descartar, S=saltar) y EXPORTAR sus
decisiones a un JSON. Ese JSON se aplica luego al catálogo con
`aplicar_decisiones_banco.py` y se redespliega. Es OFFLINE a propósito: la
fuente de verdad es el JSON versionado, no la base de datos (que se re-sincroniza
desde el JSON en cada arranque).

Uso:
    python herramientas/generar_revisor_banco.py
"""
from __future__ import annotations

import ast
import html
import json
from pathlib import Path

RAIZ = Path(__file__).resolve().parents[1]
CATALOGO = RAIZ / "backend/api/app/data/catalogo.json"
SALIDA = Path(__file__).resolve().parent / "revisor-banco.html"


def _params(cfg: dict) -> dict:
    p = cfg.get("parametros_json")
    if isinstance(p, dict):
        return p
    if isinstance(p, str):
        for parser in (json.loads, ast.literal_eval):
            try:
                v = parser(p)
                if isinstance(v, dict):
                    return v
            except Exception:
                pass
    return {}


def main() -> None:
    acts = json.loads(CATALOGO.read_text(encoding="utf-8"))
    pend = [
        {"i": i, "nombre": a.get("nombre", "(sin nombre)"),
         "descripcion": a.get("descripcion", ""),
         "plantilla": a.get("plantilla_tipo", "?"),
         "bloque": a.get("bloque", "?"),
         "params": _params(a)}
        for i, a in enumerate(acts)
        if isinstance(a, dict) and a.get("estado", "en_pruebas") == "en_pruebas"
    ]
    datos = json.dumps(pend, ensure_ascii=False)
    total = len(pend)
    plantillas = sorted({p["plantilla"] for p in pend})
    opts = "".join(f'<option value="{html.escape(t)}">{html.escape(t)}</option>' for t in plantillas)

    doc = _PLANTILLA.replace("__TOTAL__", str(total)).replace("__OPCIONES__", opts).replace("__DATOS__", datos)
    SALIDA.write_text(doc, encoding="utf-8")
    print(f"Escrito {SALIDA} con {total} actividades pendientes.")


_PLANTILLA = r"""<!doctype html><html lang="es"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Reminia — Revisor del banco</title>
<style>
:root{--sage:#12A99B;--sageDark:#1F7A70;--ink:#12312E;--ivory:#F5FBFA;--card:#fff;--sand:#D2E6E2;--coral:#C4553A;--ok:#1F7A70}
*{box-sizing:border-box}body{margin:0;font:15px/1.5 -apple-system,Segoe UI,Roboto,Arial,sans-serif;background:var(--ivory);color:var(--ink)}
header{position:sticky;top:0;background:var(--card);border-bottom:1px solid var(--sand);padding:12px 20px;display:flex;gap:16px;align-items:center;flex-wrap:wrap}
h1{font-size:18px;margin:0}.logo{width:26px;height:26px;vertical-align:middle}
.muted{color:#5A716E}.pill{background:var(--ivory);border:1px solid var(--sand);border-radius:999px;padding:3px 10px;font-size:13px}
main{max-width:760px;margin:0 auto;padding:20px}
.card{background:var(--card);border:1px solid var(--sand);border-radius:14px;padding:18px 20px;margin-bottom:14px}
.card h2{font-size:19px;margin:0 0 4px}.tags{margin:6px 0 10px}.tag{font-size:12px;background:var(--ivory);border:1px solid var(--sand);border-radius:8px;padding:2px 8px;margin-right:6px}
.params{font-family:ui-monospace,Consolas,monospace;font-size:12.5px;background:var(--ivory);border:1px solid var(--sand);border-radius:8px;padding:8px 10px;white-space:pre-wrap;color:#425}
.acts{display:flex;gap:10px;margin-top:12px}
button{font:inherit;font-weight:700;border-radius:10px;padding:9px 16px;border:1.5px solid transparent;cursor:pointer}
.v{background:var(--ok);color:#fff}.d{background:#fff;color:var(--coral);border-color:var(--coral)}.s{background:#fff;color:#5A716E;border-color:var(--sand)}
.estado{margin-left:auto;font-weight:700}.estado.validada{color:var(--ok)}.estado.descartar{color:var(--coral)}
.top-actions{margin-left:auto;display:flex;gap:10px;align-items:center}
.exp{background:var(--sageDark);color:#fff}
select{font:inherit;padding:7px 10px;border-radius:8px;border:1.5px solid var(--sand)}
.done{opacity:.5}
kbd{background:var(--ivory);border:1px solid var(--sand);border-radius:5px;padding:1px 6px;font-size:12px}
</style></head><body>
<header>
  <svg class="logo" viewBox="0 0 40 40"><rect width="40" height="40" rx="11" fill="#12A99B"/><circle cx="20" cy="20" r="12.5" fill="none" stroke="#fff" stroke-width="2.6"/><circle cx="20" cy="20" r="7" fill="none" stroke="#fff" stroke-width="2.6"/><circle cx="20" cy="20" r="2.4" fill="#F08A6B"/></svg>
  <h1>Revisor del banco — Reminia</h1>
  <span class="pill" id="prog">0 / __TOTAL__</span>
  <select id="filtro"><option value="">Todas las plantillas</option>__OPCIONES__</select>
  <div class="top-actions">
    <span class="muted">Atajos: <kbd>V</kbd> validar · <kbd>D</kbd> descartar · <kbd>S</kbd> saltar</span>
    <button class="exp" onclick="exportar()">Exportar decisiones</button>
  </div>
</header>
<main id="lista"></main>
<script>
const ACTS = __DATOS__;
const KEY = 'reminia_banco_decisiones';
let dec = {};
try { dec = JSON.parse(localStorage.getItem(KEY) || '{}'); } catch(e){}
const esc = s => String(s??'').replace(/[&<>]/g, c=>({'&':'&amp;','<':'&lt;','>':'&gt;'}[c]));

function render(){
  const filtro = document.getElementById('filtro').value;
  const cont = document.getElementById('lista'); cont.innerHTML='';
  let shown=0;
  for(const a of ACTS){
    if(filtro && a.plantilla!==filtro) continue;
    shown++;
    const st = dec[a.i] || '';
    const params = Object.entries(a.params||{}).map(([k,v])=>k+': '+JSON.stringify(v)).join('\n');
    const div = document.createElement('div');
    div.className = 'card' + (st?' done':'');
    div.id = 'c'+a.i;
    div.innerHTML = `
      <div style="display:flex;align-items:baseline">
        <h2>${esc(a.nombre)}</h2>
        <span class="estado ${st}">${st?(st==='validada'?'✓ validada':'✗ descartar'):''}</span>
      </div>
      <div class="tags"><span class="tag">${esc(a.plantilla)}</span><span class="tag">${esc(a.bloque)}</span></div>
      <div class="muted">${esc(a.descripcion)}</div>
      ${params?`<div class="params">${esc(params)}</div>`:''}
      <div class="acts">
        <button class="v" onclick="marcar(${a.i},'validada')">Validar</button>
        <button class="d" onclick="marcar(${a.i},'descartar')">Descartar</button>
        <button class="s" onclick="marcar(${a.i},'')">Saltar</button>
      </div>`;
    cont.appendChild(div);
  }
  const n = Object.values(dec).filter(Boolean).length;
  document.getElementById('prog').textContent = n + ' / ' + ACTS.length + (filtro? ' (mostrando '+shown+')':'');
}
function marcar(i, estado){
  if(estado) dec[i]=estado; else delete dec[i];
  localStorage.setItem(KEY, JSON.stringify(dec));
  render();
}
function exportar(){
  const out = {validar: [], descartar: []};
  for(const [i,e] of Object.entries(dec)){
    if(e==='validada') out.validar.push(Number(i));
    else if(e==='descartar') out.descartar.push(Number(i));
  }
  const blob = new Blob([JSON.stringify(out,null,2)], {type:'application/json'});
  const a = document.createElement('a'); a.href = URL.createObjectURL(blob);
  a.download = 'decisiones-banco.json'; a.click();
}
// Atajos de teclado sobre la primera tarjeta sin decidir visible
document.addEventListener('keydown', e=>{
  const map={v:'validada',d:'descartar',s:''};
  if(!(e.key.toLowerCase() in map)) return;
  const filtro=document.getElementById('filtro').value;
  const next = ACTS.find(a=>(!filtro||a.plantilla===filtro) && !dec[a.i]);
  if(next){ marcar(next.i, map[e.key.toLowerCase()]); const el=document.getElementById('c'+next.i); if(el) el.scrollIntoView({block:'center'}); }
});
document.getElementById('filtro').addEventListener('change', render);
render();
</script></body></html>"""


if __name__ == "__main__":
    main()
