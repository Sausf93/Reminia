# Trazo

> ¿Retomas el proyecto en otro usuario/máquina? Empieza por **`docs/RETOMAR.md`**
> (prompt de puesta al día) y **`RESUMEN-CONVERSACION.md`**.

Contexto del proyecto (arquitectura, comandos, principios clínicos, despliegue):

@AGENTS.md

Reglas rápidas:
- Antes de dar por bueno un cambio: `pytest` (backend) + `npx tsc --noEmit` (apps/web) + `flutter analyze lib` (apps/tablet) en verde.
- UI en español y con vocabulario digno (ver AGENTS.md). El participante mayor es el usuario más frágil.
- No romper el aislamiento multi-tenant ni los principios de medición (`sin_valorar` ≠ `no_logrado`).
- Despliegue y rondas QA multi-agente: skills `desplegar` y `ronda-qa`.
