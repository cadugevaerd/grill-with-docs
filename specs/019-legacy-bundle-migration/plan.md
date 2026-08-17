# Implementation Plan: Migração de bundles legados

**Branch**: `feat/backlog-ssot` | **Spec**: [spec.md](./spec.md)

## Summary

Um comando novo, `backlog-migrate`, e uma recusa nova em `backlog-project`. O modo do bundle é lido da ausência da marca de origem, o que dispensa campo novo.

O ponto de desenho que importa: a recusa por estado inválido cobre o **bundle inteiro**, não a decisão isolada. Migrar pela metade deixaria o registro meio autoral e meio projetado, sem como distinguir o que já moveu — pior que não migrar.

## Technical Context

**Language/Version**: Python >=3.10, stdlib. **Testing**: `validate_backlog_contract.py`, seams existentes. **Target**: matriz sem `backlogctl`. **Constraints**: prévia por padrão; idempotente; não roda offline, porque precisa criar itens.

## Constitution Check

| Cláusula | Status | Evidência |
|---|---|---|
| Evidência antes de afirmação | PASS | Prévia conferida contra os quatro bundles reais antes de qualquer aplicação. |
| Work item isolado | PASS | Um bundle por execução. |
| Feature/fix plan-only | PASS | Ciclo externo. |
| Sequência obrigatória | PASS | Matriz resetada. |
| Verify/review antes de ship | PASS | Mesma ordem. |
| Fail-closed sem waiver | PASS | Recusa por estado inválido, por bundle autoral em comando de projeção, e por ausência de vínculo. |
| Rastreabilidade | PASS | ADR-0003 rege o mapa de estados usado na semeadura. |
| Bump obrigatório | PASS | **3.1.0 → 3.2.0**, aditivo. |

## Project Structure

```text
plugin/skills/grill-with-docs/scripts/backlog_bridge.py    # bundle_mode, migrate
plugin/skills/grill-with-docs/scripts/grill_workspace.py   # subcomando e recusa
tests/validate_backlog_contract.py                         # nove casos
```
