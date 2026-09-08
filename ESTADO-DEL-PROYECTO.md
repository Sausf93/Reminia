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
  y redesplegar el backend.
- **Al 2026-09-08 (sesión 2)**: aplicados **281 válidas** → catálogo **2.018 validadas /
  910 pendientes**. Fotos flojas sustituidas por reales (Pexels): patata, espejo, pollo,
  bolígrafo y **perro** (labrador; se acabó el «zorro»). Bugs de contenido de la ronda QA
  corregidos (cuenta atrás descendente, ranas 5×5, elefante, «¿cuál tiene menos?»,
  «Estó»→«Estás», «horas del reloj»→«de la mañana», tilde de la Ñ). Retos de-enfatizados
  (poco usados). Backup de veredictos en `_deploy/veredictos-backup.json`.
- **Pendiente**: seguir validando las ~910; «Memoria: herramientas del taller» (en_pruebas,
  faltan fotos de 4 herramientas); juego cooperativo de 2 tablets (diseño propuesto, sin
  construir).

## Legal (sesión 2026-09-08)
- Borradores revisados por 2 agentes especialistas (RGPD y LSSI). Rebrandados (Trazo→
  Reminia), infra corregida (Aiven→Neon), `apps/landing/privacidad.html` con proveedores
  reales (Neon, Resend) + cláusula de cookies. `facilitadora`→`integradora`. Eliminado el
  envío de contraseña en claro por correo (I8).
- **BLOQUEANTE para publicar**: la BD estaba en Neon `eu-west-2` (Londres, **fuera del
  EEE**) y la política decía «se realiza en el EEE». Decisión tomada: **migrar la BD a
  Neon Frankfurt `eu-central-1`** (Saulo crea el proyecto y pasa la connection string;
  el resto lo hace el asistente: Cloud Run + redeploy + reimportar veredictos + recrear
  centro de pruebas). Hasta migrar + visto bueno de abogado, se conserva el banner
  «borrador» + `noindex` en las páginas legales públicas.

## Lo que queda (acción de Saulo)
1. 🇪🇺 **Crear proyecto Neon en Frankfurt (`eu-central-1`)** y pasar la connection string
   → el asistente migra (Cloud Run + redeploy + reimportar veredictos) y recrea el centro
   de pruebas. Cierra el bloqueante legal.
2. 💳 **Stripe a cobro real** (cuando quieras): claves LIVE en Cloud Run + suscribir
   el webhook a `checkout.session.completed`, `customer.subscription.updated/deleted`,
   **`invoice.payment_failed`** y **`invoice.payment_succeeded`** (estos dos activan
   el impago) + prueba con la tarjeta `4242 4242 4242 4242`. Lo hacemos juntos.
3. 🔐 Token de Cloudflare y service account de GCP: **de momento se mantienen** (Saulo
   quiere que el asistente pueda seguir desplegando). Revocar al terminar la fase de cambios.

## Cómo trabajar (comandos y skills)
- Verificar antes de dar por bueno: `pytest` (backend) + `npx tsc --noEmit` (panel)
  + `flutter analyze lib` (tablet). Skill `verificar`.
- Desplegar: skill `desplegar` (backend a Cloud Run, frontends a Cloudflare).
- Añadir contenido: skill `contenido`. Rondas QA: skill `ronda-qa`.
