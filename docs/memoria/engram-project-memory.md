---
name: engram-project-memory
description: Trazo usa el MCP engram (local) como gestor de memoria del proyecto; consultar mem_search antes de empezar
metadata: 
  node_type: memory
  type: project
  originSessionId: 818eac11-d522-49d7-95fa-bae5a4cbab4e
  modified: 2026-09-04T12:06:00.037Z
---

Este proyecto (Trazo) usa **engram** como gestor de memoria persistente, elegido por Saulo el 2026-09-04.

- Binario local: `C:\Users\Capitole\bin\engram.exe` (v1.20.0, Gentleman-Programming/engram). Sin nube, DB en `C:\Users\Capitole\.engram\engram.db`.
- Registrado como MCP de proyecto en `.mcp.json` (raíz del repo): `engram mcp --tools=agent --project Trazo`. Requiere aprobar el servidor MCP y recargar la sesión para que aparezcan las herramientas `mem_*`.
- **Al empezar cualquier sesión de Trazo: usar `mem_search` / `mem_context` para recuperar el contexto del proyecto**, y `mem_save` para guardar decisiones/avances importantes (especialmente tras trabajo significativo o compactación).
- CLI equivalente (misma DB): `engram search "<q>" --project Trazo`, `engram save "<titulo>" "<msg>" --project Trazo`.

Pendiente de aclarar con Saulo: dijo que el proyecto está en **Vercel** además de Google Cloud, pero el repo no tiene `vercel.json` (frontends en Cloudflare Pages, backend en Cloud Run). Stripe está en modo **test**, aún no live.
