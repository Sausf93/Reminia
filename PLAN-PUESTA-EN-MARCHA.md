# Plan de puesta en marcha de Reminia — paso a paso

> Runbook **ordenado**: haz los bloques de arriba abajo. Cada bloque acaba con un
> **✅ Comprueba** para no seguir hasta que ese trozo funcione. Lo que pone
> **(TÚ)** lo haces tú (son cuentas/credenciales que yo no tengo); lo que pone
> **(YO)** lo hago yo cuando me des el ok (tengo tu permiso para subir/desplegar
> cuando esté todo fino).
>
> Estado del código: rama `rebrand/reminia`, backend `pytest` verde, panel `tsc`
> + build verde. Marca "Reminia" y logo de anillos en panel, super-admin, tablet
> y landing. Auto-alta (backend + páginas del panel) listo y auditado.

---

## Bloque 0 — Cierre del código (YO, con tu ok)
1. **(YO)** Merge de `rebrand/reminia` → `main` (tras repasar juntos este plan).
2. **(YO)** `flutter analyze lib` de la tablet en una máquina con Flutter (aquí no lo tengo). Los cambios de la tablet son mínimos (textos + logo), pero conviene el check.
- ✅ **Comprueba:** `main` con todo el rebrand + auto-alta + seguridad.

## Bloque 1 — Renombrar el repositorio en GitHub (TÚ)
1. GitHub → repo **Trazo** → *Settings* → *Rename* → `Reminia`.
- ✅ **Comprueba:** entrar a la URL vieja redirige a la nueva (GitHub lo hace solo).
2. **(YO)** Actualizo `git remote set-url` y los enlaces del APK/insignias en el código.
> Nota: el APK y sus URLs (`github.com/Sausf93/...`) seguirán funcionando por el redirect; los dejamos afinados después.

## Bloque 2 — Correo con Resend (TÚ) — *sin esto el auto-alta no envía el acceso*
1. Entra en **Resend** → *API Keys* → **Create** una llamada `reminia-backend`, permiso **Sending**. **No la pegues en el chat**; guárdala para el Bloque 4.
2. Resend → *Domains* → **Add** `reminia.es`. Te dará ~3 registros DNS (SPF, DKIM, DMARC).
3. Cloudflare → `reminia.es` → *DNS* → añade esos 3 registros tal cual.
- ✅ **Comprueba:** en Resend el dominio pasa a **Verified** (puede tardar minutos).

## Bloque 3 — Subdominios en Cloudflare (TÚ, o me pasas un token y lo hago YO)
En Cloudflare, en cada proyecto **Pages**, *Custom domains* → *Set up a domain*:
| Proyecto Pages | Dominio a añadir |
|---|---|
| `trazo-web`   | `reminia.es` **y** `www.reminia.es` (la vitrina) |
| `trazo-panel` | `panel.reminia.es` |
| `trazo-tablet`| `app.reminia.es` |
| `trazo-admin` | `admin.reminia.es` |
- ✅ **Comprueba:** cada subdominio abre (aún mostrará el contenido viejo hasta el Bloque 4; es normal).
> Alternativa: me pasas un **token puntual de Cloudflare** (*Account → Pages: Edit* + *Zone → DNS: Edit*), lo hago yo y me lo revocas al acabar.

## Bloque 4 — Desplegar backend + frontends con la marca nueva (YO, con tu ok)
> Necesito `gcloud` autenticado (o me lees los pasos y los ejecutas tú) y la API key de Resend del Bloque 2. **Stripe sigue en TEST** todavía.
>
> ✅ **BASE DE DATOS YA LISTA (Neon):** proyecto "Reminia" creado, conexión probada
> con la config real de la app (`postgresql+asyncpg` + `DB_SSL=true`, Postgres 18),
> y **esquema + catálogo (2.928 actividades) ya provisionados** (sin datos demo).
> Las variables exactas de Cloud Run están en `_deploy/reminia-cloudrun.secret`
> (git-ignorado), con el `JWT_SECRET` de prod ya generado. Al desplegar: **preservar
> las claves de Stripe actuales** (leer con `gcloud run services describe trazo-api`
> antes de tocar) y **añadir `RESEND_API_KEY`** (está en el archivo `ApiKeyResend`).
> ⚠️ El backend de prod está caído porque apuntaba a la BD vieja (Aiven, muerta);
> al redesplegar apuntando a Neon, vuelve a la vida.
1. **Backend (Cloud Run)** con estas variables nuevas (con `--env-vars-file`, no comas):
   - `RESEND_API_KEY` = (la del Bloque 2)
   - `RESEND_FROM` = `Reminia <noreply@reminia.es>`
   - `PANEL_URL` = `https://panel.reminia.es`
   - `LANDING_URL` = `https://reminia.es`
   - `CORS_ORIGINS` = incluir `https://panel.reminia.es` (mantengo también los `*.pages.dev` actuales por seguridad).
2. **Frontends (Cloudflare Pages, wrangler)** con la build del rebrand:
   - panel `apps/web/dist` → **trazo-panel**
   - tablet `apps/tablet/build/web` → **trazo-tablet** (con `--dart-define=API_URL=<api>`)
   - vitrina `apps/landing` → **trazo-web**
   - super-admin `apps/superadmin` → **trazo-admin**
- ✅ **Comprueba:** `https://panel.reminia.es` abre, dice **Reminia**, logo de anillos, y el **login funciona** (si no, revisar CORS).

## Bloque 5 — Probar el auto-alta de punta a punta, en TEST (TÚ tecleas la tarjeta)
> Requiere decidir antes el **Bloque 5-bis** (cómo se llega al pago). Stripe en TEST.
1. Iniciar el alta (botón "empezar ahora" de la landing, o llamando a `POST /facturacion/signup`): centro + nombre + tu email.
2. Stripe Checkout → tarjeta de prueba **`4242 4242 4242 4242`**, fecha futura, CVC cualquiera.
3. Al pagar: te redirige a `panel.reminia.es/?alta=ok` ("Pago confirmado, revisa tu correo").
4. Llega el **correo de Resend** con el enlace → **crea tu contraseña** → entras al panel.
- ✅ **Comprueba:** se creó el centro, llegó el correo, creaste la contraseña y entraste. Prueba también "¿olvidaste tu contraseña?".

### Bloque 5-bis — DECISIÓN de producto (TÚ)
- ¿Añadimos a la **landing** un botón **"Empezar ahora / pagar"** (mini-form → Stripe) conviviendo con el "piloto sin coste → contacto"? Hoy la landing vende el piloto; el auto-alta (pagar ya) es otro embudo. Si lo quieres, lo monto (es rápido).

## Bloque 6 — Pasar Stripe a COBRO REAL (lo ÚLTIMO, juntos)
1. **(TÚ)** Stripe → modo **Live** → copiar: *secret key* live, *webhook signing secret* live, y el *price id* del producto de producción. **No los pegues en el chat.**
2. **(YO)** Actualizo esas 3 variables en Cloud Run y redepliego.
3. **(TÚ/JUNTOS)** En Stripe (Live) → *Webhooks* → endpoint `https://<api-cloud-run>/facturacion/webhook`, eventos `checkout.session.completed`, `customer.subscription.updated/deleted`.
- ✅ **Comprueba:** un alta real (o de bajo importe) entra, cobra y provisiona.

---

## Cosas que decides tú (no urgentes)
- **DNI en documentos / export con nombre real:** ya lo he restringido a **admin_centro** (más seguro; una tablet perdida no puede sacar esa PII). Si prefieres que las integradoras también puedan, dímelo y lo aflojo.
- **PIN en la tablet** para acciones sensibles (hoy opcional): lo vemos si quieres reforzarlo.
- **Renombrar** proyectos Cloudflare `trazo-*` y el `applicationId` de la app Android: **no hace falta** (con dominio propio el cliente no ve esos nombres; cambiarlos rompería URLs/actualizaciones). Solo si algún día migramos con calma.
