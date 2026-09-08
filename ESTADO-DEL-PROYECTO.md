# Reminia — Estado del proyecto

> Documento único y actualizado de **qué es Reminia, qué está hecho y qué queda**.
> Sustituye a los antiguos PENDIENTE / BACKLOG / CAMBIOS / PLAN (borrados: su
> contenido, ya realizado, vive en el código y en el historial de git).
> Última actualización: 2026-09-08.

## Qué es
SaaS de **estimulación cognitiva para centros de día y residencias de mayores**.
La persona mayor juega en una **tablet** (kiosco); la integradora/maestra supervisa
y el **panel web** mide la evolución y avisa de cambios. Multi-tenant (cada centro
aislado), RGPD por diseño. Marca: **Reminia**. Dominio: **reminia.es**.

## En producción (LIVE)
| Pieza | URL | Estado |
|---|---|---|
| Vitrina/landing | `reminia.es` | ✅ Reminia |
| Panel del centro | `panel.reminia.es` | ✅ Reminia |
| Tablet (kiosco) | `app.reminia.es` | ✅ Reminia |
| Super-admin | (Cloudflare `trazo-admin`) | ✅ |
| API | Cloud Run `trazo-api` (europe-southwest1) | ✅ |
| Base de datos | **Neon** Postgres (plan free, eu-west-2) | ✅ |
| Correo | **Resend** (dominio `reminia.es` verificado) | ✅ |

Coste ≈ **0 €**: Neon free + Cloud Run escala-a-cero + Cloudflare Pages gratis +
Resend gratis. Único fijo: el dominio (~10 €/año).

## Arquitectura (resumen)
- **backend/api**: FastAPI + SQLAlchemy async + Postgres. Migraciones idempotentes
  al arrancar. Catálogo de ~2.900 actividades (9 plantillas) que se sincroniza solo.
- **apps/web**: panel React + Vite (integradora/admin).
- **apps/tablet**: Flutter (kiosco participante + pantalla maestra).
- **apps/superadmin**: HTML (token de plataforma).
- **apps/landing**: vitrina + demo de la tablet.
- Detalle técnico y principios clínicos: `AGENTS.md` y `docs/MODELO-OPERATIVO.md`.

## Flujos clave (funcionando)
- **Alta self-service**: pagar (Stripe) → webhook crea centro + admin → correo con
  enlace de un solo uso para crear contraseña → panel. Aviso al super-admin en cada alta.
- **Onboarding guiado** en el panel: dar de alta equipo → personas → emparejar
  tablet → planificar. La tablet exige **emparejar primero**.
- **Jerarquía**: admin_centro crea trabajadores y personas; la integradora crea
  solo personas.
- **RGPD**: no se abre sesión real sin DPA del centro + consentimiento por persona.
- **Impago (dunning)**: cobro fallido → aviso por correo (con enlace de pago) → al
  **3er fallo** se suspende el acceso (datos intactos) → un pago reactiva.
- **Suscripción**: prueba 30 días / activa / cortesía / suspendido / cancelada.
- **Cortesía a medida (super-admin)**: al crear un centro se eligen los días de
  prueba (15/30/45/60 o a medida). Al caducar, el acceso se **corta del todo — panel
  Y tablets** (todos los endpoints de kiosco pasan por la compuerta de suscripción;
  test que lo blinda) y el panel muestra un **paywall** «Activar suscripción (pagar)».
  Los datos se conservan; un pago reactiva.

## Seguridad (auditada)
Cuatro rondas adversariales multi-agente (17–20). Base **sólida**: sin fugas entre
centros (IDOR), sin escalada de rol, sin bypass del token de plataforma, tokens de
enlace no reutilizables como sesión, webhook de Stripe con firma verificada. La
salida de PII (documentos con DNI, export con nombre real) está restringida a
`admin_centro`. No se pueden "saltar pasos" por URL (mediciones solo en sala abierta
y fresca; puerta RGPD incondicional).

## Validación de contenido (en curso)
- El equipo (Saulo, José) revisa las actividades **jugándolas** en
  `app.reminia.es/pendientes-valoracion` (marca Válida/Dudosa/No válida; se guarda en
  el servidor, tabla `BancoVeredicto`). En cuanto alguien valora una, no vuelve a salir
  para nadie. Catálogo: ~1.997 validadas, ~931 pendientes.
- **Aplicar al catálogo**: `python herramientas/aplicar_veredictos_banco.py` (lee los
  veredictos del servidor: válida→`validada`, no válida→`descartada`; dudosas se listan)
  y redesplegar el backend. Estado a 2026-09-08: **284 válidas** marcadas, **10 dudosas**.
- **Dudosas por resolver**: 4 «Busca …» (ya corregidas a plural, desplegadas), 4 fotos
  a cambiar (patata roja, espejo, pollo, bolígrafo) + «perro» que parece zorro, la
  categoría de «Memoria: herramientas del taller» (dibujos vs fotos) y el trazo de la Ñ.
- **Imágenes**: se cambiarán con fotos reales (Pexels/Pixabay o el MCP de imágenes).

## Lo que queda (acción de Saulo)
1. 💳 **Stripe a cobro real** (cuando quieras): claves LIVE en Cloud Run + suscribir
   el webhook a `checkout.session.completed`, `customer.subscription.updated/deleted`,
   **`invoice.payment_failed`** y **`invoice.payment_succeeded`** (estos dos activan
   el impago) + prueba con la tarjeta `4242 4242 4242 4242`. Lo hacemos juntos.
2. 🔐 **Revocar el token de Cloudflare** `reminia-pages-deploy` (se usó para desplegar).
3. (Opcional) Desactivar la service account de GCP `reminia-deploy` cuando no haya
   más despliegues; borrar el centro de pruebas `pruebas@reminia.es`.

## Cómo trabajar (comandos y skills)
- Verificar antes de dar por bueno: `pytest` (backend) + `npx tsc --noEmit` (panel)
  + `flutter analyze lib` (tablet). Skill `verificar`.
- Desplegar: skill `desplegar` (backend a Cloud Run, frontends a Cloudflare).
- Añadir contenido: skill `contenido`. Rondas QA: skill `ronda-qa`.
