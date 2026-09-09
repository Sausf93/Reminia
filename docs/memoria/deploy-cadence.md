---
name: deploy-cadence
description: "Cadencia de despliegue en Trazo/Reminia — acumular y desplegar una sola vez al día ~17:00, no a cada cambio"
metadata: 
  node_type: memory
  type: feedback
  originSessionId: 818eac11-d522-49d7-95fa-bae5a4cbab4e
  modified: 2026-09-09T12:32:35.158Z
---

Saulo pidió (2026-09-09) NO lanzar deploys a cada cambio: acumular los cambios del día y hacer **un único deploy hacia las 17:00**.

**Why:** cada build de Cloud Build cuesta (minutos de build) y desplegar continuamente sale caro; prefiere agrupar.

**How to apply:** durante el día, commitear a git (gratis) los cambios de contenido/código, pero NO redesplegar backend (Cloud Run) ni frontends (Cloudflare) hasta ~17:00, y entonces un solo deploy con todo lo acumulado. Excepción: si Saulo pide expresamente desplegar ya.

Nota operativa: el deploy debe salir de la sesión que tiene el SDK gcloud autenticado (creds de la service account `reminia-deploy` viven en el scratchpad de ESA sesión; una sesión nueva tendría que re-bootstrapear auth). SDK que funciona: `scratchpad/gcloudsdk/google-cloud-sdk/lib/gcloud.py` con `CLOUDSDK_PYTHON=Python312` y `CLOUDSDK_CONFIG=scratchpad/gcloud-config` (la copia `gcloud-sdk` está corrupta). Ver [[engram-project-memory]].
