# Retomar Reminia en otro usuario / otra máquina

> Abre este proyecto en `C:\Users\Public\Trazo` (o clónalo de GitHub) y pega en Claude
> el **prompt de abajo**. Con eso se pone al día de todo sin perder contexto.

## Arranque rápido (una sola vez, en una terminal dentro del proyecto)
```bash
.tools/engram.exe sync --import   # carga la memoria del proyecto en tu engram local (opcional pero recomendado)
```
Si falta alguna herramienta (Node, Python 3.12, Flutter) o vas a desplegar, mira
[`SETUP-ENTORNO.md`](../SETUP-ENTORNO.md). El resto de contexto está en los `.md` del repo,
así que **aunque engram no cargue, el prompt te pone al día igual**.

---

## Prompt para pegar en Claude

Retomo este proyecto (**Reminia / Trazo**) en un usuario nuevo. El contexto fiable está en los
ficheros del repo y, si está disponible, en engram. **Antes de tocar nada**, ponte al día así:

1. **LEE SIEMPRE estos ficheros** (fuente fiable del contexto, en este orden):
   - `CLAUDE.md` y `AGENTS.md` — instrucciones, arquitectura, flujos y principios clínicos.
   - `RESUMEN-CONVERSACION.md` — qué es Reminia, todo lo que hemos hecho y por qué.
   - `ESTADO-DEL-PROYECTO.md` — estado actual, qué está hecho y qué queda.
   - `SETUP-ENTORNO.md` — cómo arrancar el entorno (MCP, `.env`, deploy, git).
   - `docs/memoria/` — memoria del proyecto en markdown (normas y decisiones).
2. **Si engram está disponible** (tras `.tools/engram.exe sync --import`): llama a
   `mem_current_project` y luego a `mem_context` y `mem_search` con palabras clave:
   *validación de contenido con José, veredictos del banco, Comer→Almorzar / Comida→Almuerzo,
   habitación→lugar, contaminación del "martillo", una-deploy-al-día, migración a Neon
   Frankfurt, banco de pruebas / pendientes-valoracion*. Haz también una búsqueda con
   `all_projects=true` para el contexto transversal. **Si engram NO está cargado, no pasa
   nada:** sigue con los ficheros del paso 1.
3. **Comprueba el estado real del repo:** `git log --oneline -8` y `git status`.
4. **Resúmeme**, en corto: qué es el proyecto, en qué estábamos, decisiones/normas clave
   y el **próximo paso**. Señala explícitamente lo que no cuadre o falte.

**Reglas al retomar:** no modifiques nada ni hagas commits todavía; primero recupera el
contexto y espera mis instrucciones. Recuerda las normas del proyecto: **un solo deploy al
día (~17:00)** por coste de builds; UI en español y con vocabulario digno; los **secretos
(tokens de Cloudflare, clave de la service account de GCP) los aporto yo en el momento** —
no están en git ni en la carpeta.

---

## Qué tienes ya montado en `C:\Users\Public\Trazo`
- Código + historial git (remoto `github.com/Sausf93/Reminia`, ramas `main` y `rebrand/reminia`).
- `backend/api/.env` (conexión a Neon Frankfurt).
- `.tools/engram.exe` + `.mcp.json` portable (engram, graphlore, playwright).
- `.engram/` (memoria del proyecto) · `graphify-out/` (grafo del código) · `.claude/skills/`.
- Este `RETOMAR.md`, `RESUMEN-CONVERSACION.md`, `SETUP-ENTORNO.md`, `ESTADO-DEL-PROYECTO.md`, `docs/memoria/`.

## Lo único que NO viaja (por seguridad o por diseño de Windows)
- Los **valores de los tokens/credenciales** (los pones tú al desplegar: token puntual de
  Cloudflare Pages:Edit + `gcloud auth`). Cuentas/proyectos/comandos sí están en `SETUP-ENTORNO.md`.
- El **historial exacto de esta conversación** (vive bajo el usuario original). Su contenido
  está resumido en `RESUMEN-CONVERSACION.md` y en engram.
