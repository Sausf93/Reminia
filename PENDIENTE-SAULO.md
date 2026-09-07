# Pendiente de Saulo — acciones que solo puedes hacer tú

> Documento vivo que deja Claude durante la sesión autónoma del 2026-09-04.
> Todo lo que aparece aquí **necesita una acción tuya** (credenciales, login en
> paneles externos, reinicio, o decisiones). Lo que Claude sí puede hacer solo,
> lo va haciendo en la rama `rebrand/reminia` (commits, sin `push`).
> Al volver, repasamos esta lista juntos.

## 1. Reiniciar Claude Code (desbloquea la verificación) — PRIORITARIO
El clasificador de seguridad me bloquea `pip`/`venv` y editar el archivo de
permisos. Sin eso **no puedo montar el backend local ni correr `pytest`/`tsc`/
`flutter analyze`**, así que todos mis arreglos de hoy están **sin verificar**
(solo comprobados por sintaxis).

**Acción tuya:** cuando cierres las otras conversaciones, pega esto en
`.claude/settings.local.json` y reinicia Claude:
```json
{
  "permissions": {
    "allow": [
      "Skill(update-config)", "Skill(update-config:*)",
      "Bash(python -m pip install:*)", "Bash(py -m pip install:*)",
      "Bash(npm install:*)", "Bash(npm ci:*)"
    ]
  }
}
```
Con eso, monto Python 3.12 + venv + deps, `npm install`, y **verifico todo**.

## 2. Dominio reminia.es (enlazar con los frontends)
- [x] Zona `reminia.es` añadida a Cloudflare + nameservers `boyd/lara.ns.cloudflare.com` puestos en IONOS. (Propagando.)
- [ ] **Comprobar en Cloudflare que la zona pasó a "Active"** (pulsa *Check nameservers* si sigue en Pending).
- [ ] **Pasarme un token de Cloudflare puntual** (Account → *Pages: Edit* + Zone → *DNS: Edit*) para que enganche los subdominios: `reminia.es`+`www`→vitrina, `panel.`→panel, `app.`→tablet, `admin.`→superadmin. *(O los clicas tú en cada proyecto Pages → Custom domains.)*
- [ ] **CORS del backend:** hay que añadir `https://panel.reminia.es` a `CORS_ORIGINS` en Cloud Run y redesplegar, o **el login del panel se rompe**. Necesito `gcloud` autenticado (¿lo tienes?) o lo haces desde la consola de Cloud Run. **No lo hago desatendido (es producción).**

## 3. Correo (Resend) — para el auto-alta
- [ ] **Crear API key** en Resend (nombre `reminia-backend`, permiso *Sending*). **No la pegues en el chat**; ponla como variable de entorno `RESEND_API_KEY` en Cloud Run (y `.env` local). También `RESEND_FROM` (p. ej. `Reminia <noreply@reminia.es>`).
- [ ] **Verificar el dominio en Resend:** añadir los ~3 registros DNS que Resend indique (SPF/DKIM/DMARC) en la zona de Cloudflare de reminia.es. Te los daré cuando montemos el correo.

## 4. Stripe — pasar a cobro real (lo ÚLTIMO)
- [ ] Cuando todo esté probado en test, **cambiar las claves de Stripe a las de LIVE** (secret key + webhook secret + price id de producción) en Cloud Run. Lo hacemos juntos.
- [ ] **Probar el checkout con la tarjeta de test `4242 4242 4242 4242`** (yo NO tecleo tarjetas ni contraseñas: esta prueba la haces tú).

## 5. Rebrand total Trazo → Reminia
- **Yo hago:** el texto visible en código (títulos, manifests, `android:label`, strings de UI, legal), el app id Android, y regenerar documentos. (En curso, rama `rebrand/reminia`.)
- **Necesita tu acción:**
  - [ ] **Renombrar el repositorio de GitHub** `Sausf93/Trazo` → `.../Reminia` (Settings → Rename). GitHub redirige las URLs viejas; luego actualizo enlaces del APK/badges y `git remote set-url`.
  - [ ] **Proyectos Cloudflare Pages** (`trazo-panel/tablet/web/admin`): NO se renombran (crear nuevos cambiaría las URLs y rompería CORS). Con **dominio propio reminia.es** delante, el cliente ya no ve los `*.pages.dev`, así que **no hace falta** tocarlos. Si aun así los quieres "limpios", es una migración aparte (crear proyectos nuevos + reapuntar + borrar viejos) que hacemos con calma.
  - [ ] **Proyecto GCP** `trazo-505414`: el id es **inmutable**; no se ve con dominio propio. No tocar salvo que quieras migrar (mudanza grande).
  - [ ] **Cuenta/producto de Stripe**: renombrar el producto "Trazo — Centro" (1 clic; el `price_…` no cambia).

## 6. Verificación y despliegue (cuando haya toolchain, tras el punto 1)
- [ ] `pytest` + `tsc` + `flutter analyze` + E2E de escenario en verde (lo corro yo).
- [ ] Desplegar backend (Cloud Run) + frontends (Cloudflare) con la skill `desplegar`. **No despliego desatendido**; lo hacemos juntos.

## 7. Decisiones de seguridad que necesitan tu criterio (ronda 15)
La auditoría de seguridad salió **"casi"**: el aislamiento entre centros (IDOR) es **sólido, sin fugas**. Estas dos son decisiones de producto que **no he forzado** (no son exploits, están scoped por centro):
- [ ] **Documentos legales (DPA, consentimientos con DNI/NIE): ¿quién los descarga/borra?** Hoy **cualquier integradora** del centro puede (el test actual lo da por intencionado). El auditor recomienda restringirlo a **admin_centro** por ser PII sensible. Dime si lo restrinjo.
- [ ] **El token de la tablet (kiosco) escala a una sesión de staff completa.** `POST /auth/tablet` con el token del dispositivo + elegir un nombre acuña un JWT de profesional (no admin) **sin contraseña** (el PIN es opcional y por defecto nadie lo tiene). Ese JWT abre todos los endpoints de staff (datos de salud del centro, export CSV, documentos). Es inherente a que la tablet en modo "maestra" necesita acceso de staff. Fix robusto (a diseñar con cuidado para no romper el kiosco): token de **alcance reducido** + exigir contraseña/PIN para lo sensible. Lo vemos juntos.

## 8. Auto-alta self-service: backend LISTO y AUDITADO, falta frontend + 1 decisión
El **backend del alta self-service está construido, seguro y probado** (todo en la rama, con tests):
- `POST /facturacion/signup` (público) → checkout de Stripe.
- Webhook crea centro + admin y envía un **enlace de "crea tu contraseña"** (token de un solo uso, **no** se manda la contraseña en claro).
- `POST /auth/set-password` (crea la contraseña desde el enlace + auto-login) y `POST /auth/forgot-password` (recuperación, sin revelar qué correos existen).
- `GET /facturacion/estado` (estado de suscripción + precio para la conversión).

**Auditoría de seguridad (ronda 17, multiagente adversarial): 2 fallos CRÍTICOS encontrados y CERRADOS** (con test de regresión), más 4 recomendados aplicados:
- 🔴 **Confusión de propósito** — el enlace del correo (token "crear contraseña") valía como sesión admin completa si se usaba de `Bearer`. Cerrado: `decode_access_token` rechaza cualquier token con propósito; TTL del enlace 7 días → 72 h.
- 🔴 **Secuestro cross-tenant** — pagar un alta con el nombre EXACTO de un centro ya cliente te metía como admin de ESE centro (datos de salud ajenos). Cerrado: el alta pública SIEMPRE crea un centro nuevo y aislado (nunca reutiliza por nombre).
- 🟠 Aplicados además: forgot-password sin oráculo de temporización (envío en 2º plano), rate-limit por IP en signup y forgot-password, errores de Stripe sin filtrar detalles, y log de ERROR si un alta pagada se queda sin poder enviar el correo.
- ⚪ **Recomendados NO forzados (tu criterio):** (a) el signup responde 409 "ya existe una cuenta con ese correo" → revela qué correos están registrados; quitarlo mejora la privacidad pero cambia la UX del embudo (habría que decir "revisa tu correo" en vez de redirigir a Stripe). (b) **Verificación de email antes de cobrar** (doble opt-in): evita que un typo deje un centro pagado e inaccesible; es una mejora de producto para cuando montemos el frontend. (c) Idempotencia del webhook por `event.id` (hoy es por email, suficiente para reintentos normales de Stripe).

**Falta para que funcione de cara al cliente:**
- [ ] **DECISIÓN de producto:** ¿enlazar el "pagar y empezar" en la **landing**? Hoy la landing vende *piloto sin coste → contacto por correo*. El self-service (pagar ya) es otro embudo. Si lo quieres, añado un botón "Empezar ahora" → mini-form (centro, nombre, email) → `POST <API>/facturacion/signup` → redirige a Stripe. Dime si va, y si conviven con el "piloto".
- [ ] **Panel:** falta la página `/crear-password?token=…` (llama a `POST /auth/set-password`) y una de `/recuperar` (forgot). Y que el login interprete `?alta=ok` mostrando "pago confirmado, revisa tu correo". Es frontend del panel (React); lo hago cuando retomemos (o en la próxima sesión).
- [ ] **Resend imprescindible:** sin `RESEND_API_KEY` + dominio verificado, el correo con el enlace **no sale** (el alta no se rompe, pero el admin no recibe el acceso). Ver §3.

---
### Estado de lo que Claude va avanzando solo (rama `rebrand/reminia`, sin push)
- Arreglados los 4 bloqueantes de la ronda 13 + pulidos + fix del bypass RGPD de la compuerta legal + 2 fixes de Stripe. (Commits en la rama.)
- Rondas multiagente de QA/seguridad lanzadas (13 hecha, 14 hecha, 15 en curso), aplicando hallazgos.
- Barrido visual del onboarding público (landing, instalación, emparejado) con navegador.
- **Todo sin verificar hasta el punto 1.** Detalle completo en la memoria del proyecto (engram) y en `CAMBIOS-*.md`.
