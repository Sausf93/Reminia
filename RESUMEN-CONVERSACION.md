# Reminia — Resumen de la conversación (traspaso)

> Escrito el **2026-09-09** para poder **retomar el trabajo desde cualquier
> sitio/usuario** (incl. abrir Claude Code en `C:\Users\Public\Trazo`). Es el
> resumen humano de lo que hemos hecho y de cómo seguir. El estado técnico
> "oficial" está en [`ESTADO-DEL-PROYECTO.md`](ESTADO-DEL-PROYECTO.md); la
> arquitectura en [`AGENTS.md`](AGENTS.md). Para poner el entorno a punto en otro
> usuario: [`SETUP-ENTORNO.md`](SETUP-ENTORNO.md).

## Qué es Reminia
SaaS de **estimulación cognitiva para centros de día y residencias de mayores**.
La persona mayor juega en una **tablet** (modo kiosco); la integradora/maestra
supervisa desde el **panel web**; se mide la evolución y se avisa de cambios.
Multi-tenant (cada centro aislado), RGPD por diseño. Marca **Reminia**, dominio
**reminia.es**. Cliente ancla: la empresa de Laura (5 centros). Competencia: NeuronUP.

## En producción (todo LIVE, coste ≈ 0 €)
- **Vitrina** `reminia.es` · **Panel** `panel.reminia.es` · **Tablet** `app.reminia.es`
- **API**: Cloud Run `trazo-api` (europe-southwest1), proyecto GCP `trazo-505414`.
- **BD**: **Neon Postgres en Frankfurt** (`eu-central-1`) — datos de salud en el EEE.
- **Correo**: Resend (dominio `reminia.es` verificado).

## Lo que se hizo en las sesiones recientes
1. **Migración de la BD a Frankfurt** (antes estaba en Londres). Datos en el EEE,
   294 veredictos reimportados, páginas legales publicadas (sin banner "borrador").
2. **Validación de contenido con José (el padre de Saulo)**, que juega en
   `app.reminia.es/pendientes-valoracion` y marca cada actividad Válida/Dudosa/No
   válida. Se guarda en el servidor (tabla `BancoVeredicto`, cabecera
   `X-Lab-Token: trazo-lab-2026`). En cuanto alguien valora una, no vuelve a salir
   para nadie.
   - **Arreglo importante**: el validador ahora muestra **solo las NO validadas**
     (las `en_pruebas`), que es lo que tiene sentido probar.
   - **Aplicar veredictos** al catálogo: `python herramientas/aplicar_veredictos_banco.py`
     (válida→`validada`, no válida→`descartada`; las dudosas se listan para arreglar
     a mano). Luego redesplegar el backend.
3. **Sesión 2026-09-09 (esta)** — mientras José jugaba:
   - Aplicadas las válidas del banco → **catálogo 2.022 validadas / ~906 pendientes**.
   - **Dudosas de José resueltas**:
     - `Comer` → **`Almorzar`** y `Comida` → **`Almuerzo`** en las secuencias de
       comidas ("El día en orden", "Ordena la rutina", "Ordena las comidas del día").
       (La frase "Vamos a comer juntos" NO se tocó: ahí "comer" es verbo.)
     - `habitación` → **`lugar de la casa`** en "¿En qué habitación?" (era ambigua:
       coloquialmente "habitación" = dormitorio, y una opción ES "el dormitorio") y
       en "Cada cosa a su cuarto" ("a su habitación" → "a su lugar").
     - Búsquedas ya en plural (cebollas, panes, puertas, tomates); fotos reales
       (Pexels) de patata/espejo/pollo/bolígrafo/perro; tilde de la Ñ.
   - **Bug de contaminación cazado**: un `martillo`/`destornillador` se había colado
     en **20 actividades temáticas** (comida, ropa, muebles, frutas, cocina, mesa
     puesta) donde no encajan. Limpiadas. Se dejaron intactas las de diseño
     ecléctico y las de material ("cosas de metal/duras", donde el martillo sí encaja).
     Quitado también el **bolígrafo** de "las herramientas" y el **espejo** de "los
     muebles" (dudosas de José).
   - **Deploy del backend a Cloud Run** (revisión `trazo-api-00130-v92`): todo lo
     anterior está **EN VIVO** en la app definitiva.

## Norma de trabajo que pidió Saulo
- **No desplegar a cada cambio.** Acumular y hacer **un solo deploy al día (~17:00)**
  por el coste de los builds. (Hoy 09/09 se adelantó el deploy por el cambio de
  usuario de Windows.)
- **Stripe a cobro real**: lo hace Saulo (pendiente, "mañana"). No tocar claves LIVE.
- **Tokens de Cloudflare / service account de GCP**: se mantienen para poder seguir
  desplegando (no revocar de momento).
- Contacto público = el **correo personal** de Saulo. UI siempre en español y con
  **vocabulario digno** (ver AGENTS.md).

## Pendiente (para retomar)
1. **Seguir aplicando veredictos** según José juega:
   `python herramientas/aplicar_veredictos_banco.py` → commit → (en el deploy del día).
2. **Dudosas ambiguas a aclarar con José** (nota de una palabra, no tocadas):
   - "¿Dónde vive cada animal?" — nota **"dónde?"** (¿qué le chirría exactamente?).
   - "¿Qué medio de transporte es?" — nota **"barca"** (hay un ítem "Un barco"; ¿lo
     quiere como "barca", o la foto parece una barca?).
3. **"Memoria: herramientas del taller"** (`en_pruebas`): faltan **fotos reales** de
   sierra, tijeras, llave inglesa… (ahora son dibujos). Requiere Pexels vía el
   navegador integrado (Cloudflare 1010 bloquea el cliente Python).
4. **Stripe LIVE** (Saulo) y **recrear el centro de pruebas** (la BD de Frankfurt
   empezó sin centros; hace falta `PLATFORM_TOKEN` o crearlo en `admin.reminia.es`).
5. **Juego cooperativo de 2 tablets** (tipo "hundir la flota"): diseño propuesto,
   sin construir.

## Cómo desplegar (cuando toque)
Skill `desplegar` o, a mano (necesita el `gcloud` autenticado):
```bash
IMAGE=europe-southwest1-docker.pkg.dev/trazo-505414/trazo/api:latest
gcloud builds submit backend/api --config=deploy/cloudbuild.yaml --substitutions=_IMAGE=$IMAGE
gcloud run deploy trazo-api --image=$IMAGE --region=europe-southwest1   # NO tocar env vars
```
- Frontends a Cloudflare Pages por wrangler (ver AGENTS.md: cada dir a SU proyecto).
- **El contenido nuevo solo necesita redesplegar el backend** (el catálogo se
  re-sincroniza en cada arranque).

## Git
- Remoto: `github.com/Sausf93/Reminia`. Ramas `main` y `rebrand/reminia` (sincronizadas).
- **Todo el trabajo está subido a GitHub** — es la fuente de la verdad. Clonar desde
  ahí + recrear `backend/api/.env` (ver SETUP) reconstruye el proyecto en cualquier sitio.
