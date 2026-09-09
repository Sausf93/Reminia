# Poner el entorno a punto (otro usuario / otra máquina)

> Objetivo: abrir Claude Code sobre este proyecto y trabajar **igual que en el
> equipo original**, sin perder contexto. El contexto de lo que hemos hecho está
> en [`RESUMEN-CONVERSACION.md`](RESUMEN-CONVERSACION.md), [`ESTADO-DEL-PROYECTO.md`](ESTADO-DEL-PROYECTO.md)
> y [`AGENTS.md`](AGENTS.md). Léelos al empezar.

## 0. Qué viaja con el proyecto y qué no
**Viaja** (está en la carpeta / en git): todo el código, `AGENTS.md`/`CLAUDE.md`,
las skills (`.claude/skills/`), este setup, el resumen, el grafo (`graphify-out/`),
el binario de engram (`.tools/engram.exe`) y el `.mcp.json` portable. En la copia de
`C:\Users\Public\Trazo` también va el `backend/api/.env` y los backups de `_deploy/`.

**No viaja solo** (por usuario de Windows): el historial de conversación de Claude y
la BD interna de engram (viven en `%USERPROFILE%\.claude`), y las **autenticaciones**
(gcloud, Cloudflare). Eso se recupera con el resumen + reinstalando/reautenticando (abajo).

## 1. Herramientas necesarias (instalar si faltan; un usuario no-admin puede con `--user`)
- **Claude Code** (la app / CLI).
- **Node** (para `npx`, playwright y builds del panel/vitrina). Aquí viene por **Volta**
  en `C:\Program Files\Volta` (para todos los usuarios) → suele estar ya disponible.
- **Python 3.12** (backend y scripts). Si no está: instalar Python 3.12.
- **Flutter** (solo si vas a compilar la tablet): `~/flutter/bin` en PATH.
- **gh** (GitHub CLI) → `C:\Program Files\GitHub CLI` (compartido).

## 2. MCP (agentes/herramientas de Claude)
El proyecto trae un **`.mcp.json` portable** que apunta a rutas **dentro del proyecto**,
así funciona para cualquier usuario:
```json
{
  "mcpServers": {
    "engram":     { "command": ".tools/engram.exe", "args": ["mcp","--tools=agent","--project","Trazo"] },
    "graphlore":  { "type": "stdio", "command": "py", "args": ["-m","graphlore"],
                    "env": { "GRAPHLORE_PROJECT_DIR": "." } },
    "playwright": { "command": "npx", "args": ["-y","@playwright/mcp@latest"] }
  }
}
```
- **engram** (memoria del proyecto): el binario ya está en `.tools/engram.exe`. La
  **memoria del proyecto viaja en la carpeta `.engram/`** (chunks comprimidos, también
  en git). Al abrir por primera vez con otro usuario, impórtala a tu engram local:
  ```bash
  .tools/engram.exe sync --import        # carga .engram/ en tu engram local
  ```
  Luego, en Claude, `mem_context` / `mem_search` ya devuelven todo el histórico. El
  contexto en prosa está además en el RESUMEN y en `docs/memoria/`.
- **graphlore/graphify** (grafo del código): `py -m pip install --user graphlore` si falta.
  El grafo ya construido está en `graphify-out/`.
- **playwright**: se auto-descarga con `npx` (necesita Node).

> Si Claude Code pide **aprobar los MCP del proyecto** al abrir la carpeta, acéptalos.

## 3. Secretos y `.env`
- En la copia de `C:\Users\Public\Trazo` el fichero **`backend/api/.env` ya está**.
- Si clonas **desde GitHub** (donde `.env` NO va, por seguridad), recréalo con estas
  claves: `DATABASE_URL` (Neon Frankfurt), `DB_SSL=true`, `ENTORNO`, `JWT_SECRET`,
  `JWT_ALGORITHM`, `JWT_EXPIRE_MINUTES`, `CORS_ORIGINS`, `SEED_ON_STARTUP`,
  `APP_TIMEZONE`. Pídele a Saulo el `DATABASE_URL` real (tiene la contraseña de la BD).

## 4. Levantar en local (opcional)
```bash
# Backend
cd backend/api && py -m venv .venv && ./.venv/Scripts/python -m pip install -r requirements.txt
./.venv/Scripts/python -m uvicorn app.main:app --reload
# Panel
cd apps/web && npm install && npm run dev
```

## 5. Desplegar (necesita reautenticar)
- **gcloud** (Cloud Run): instalar el SDK y `gcloud auth login` con la cuenta de deploy
  (`reminia-deploy@trazo-505414.iam.gserviceaccount.com`) o pedirle a Saulo el acceso.
- **Cloudflare** (Pages): token puntual (Pages:Edit) que da Saulo; ver AGENTS.md.
- Recuerda la norma: **un solo deploy al día (~17:00)** por coste de builds.

## 6. Git
- Remoto: `https://github.com/Sausf93/Reminia.git` (ramas `main` y `rebrand/reminia`).
- **Todo está subido.** Trabaja normal: commit + push. GitHub es la fuente de la verdad.
