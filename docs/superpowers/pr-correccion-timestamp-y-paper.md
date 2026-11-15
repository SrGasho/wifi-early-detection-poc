# Borrador de PR: docs/correccion-timestamp-y-paper → main

Lo abre el autor (CLAUDE.md: Claude no hace commits, push ni PR). Título sugerido:

**docs: correcciones de timestamp, paper y guía de Packet Tracer**

## Resumen

- `f656d11` Corrige la afirmación de timestamp por tipo de trama (Fase 1).
- `8c06c14` Alinea la docstring de `case_c` con la validación real.
- `446c5be` Añade la guía paso a paso de Packet Tracer y la lista de pendientes de diseño e implementación.

Commits del 2026-11-15:

- `21bb66e` `scripts/figuras_evaluacion.py` + pruebas: figuras de evaluación leyendo solo resultados ya guardados (no toca R6).
- `efc026e` `paper.tex` movido a `docs/paper/` (versionado); VLAN 30 sin condicional; criterios de aceptación declarados como de diseño.
- `545bf2e` Plan de cierre de pendientes en `docs/superpowers/`, acuerdos en `seguimiento.md` y corrección del residuo de Caso B en `plan-implementacion-codigo.md`.
- `2b3fb91` Replay y mitigación simulada ejecutados con `--final` (4 experimentos, reproducción válida); cifras en `docs/resultados.md` §2; paper alineado.
- Tabla de trazabilidad paper → evidencia en `docs/trazabilidad-paper.md`.

## Verificación

- `.venv/Scripts/python.exe -m pytest -q` → 97 pruebas en verde.
- Ningún cambio en `src/`, `configs/` ni `data/raw/`.
- `replay.done` y `mitigation.done` creados una sola vez por experimento (R6).

## Notas

- `docs/decisiones.md` y `configs/splits/*.json` sin cambios (congelados tras `gate-d`).
