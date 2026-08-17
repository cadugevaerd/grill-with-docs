# Implementation Plan: Detecção de skill sombreada

**Branch**: `feat/backlog-ssot` | **Date**: 2026-08-17 | **Spec**: [spec.md](./spec.md)

## Summary

O preflight ganha uma verificação nova: nome publicado pelo plugin que também exista fora dele. Três funções pequenas em `ensure_dependencies.py`, mais duas linhas no `preflight`.

O detalhe que decide a correção: `is_symlink()` precisa vir **antes** de `exists()`. Um atalho quebrado tem `exists()` falso e continua ocupando o nome — checar existência primeiro esconderia exatamente a forma do defeito que motivou a fase.

## Technical Context

**Language/Version**: Python >=3.10, stdlib.

**Testing**: `tests/validate_dependencies_contract.py`, com diretórios sintéticos e `HOME` injetado. Nada toca o ambiente real.

**Target Platform**: os três sistemas da matriz. Os testes de atalho pulam quando a plataforma não os suporta, em vez de falhar.

**Constraints**: reporta por padrão; remove só sob autorização; remove o atalho e nunca o destino.

**Scale/Scope**: quatro raízes de busca, um nome publicado hoje.

## Constitution Check

| Cláusula | Status | Evidência |
|---|---|---|
| Evidência antes de afirmação | PASS | A detecção nasce de defeito observado em uso, não de hipótese. |
| Work item isolado | PASS | Sem escrita fora do bundle. |
| Feature/fix plan-only | PASS | Ciclo externo. |
| Sequência obrigatória | PASS | Matriz resetada por `phase-turn`. |
| Verify/review antes de ship | PASS | Mesma ordem. |
| Fail-closed sem waiver | PASS | Reportar sem bloquear é escolha declarada: recusar o preflight por uma sombra esconderia o relatório que o operador foi buscar. A remoção, sim, exige autorização. |
| Rastreabilidade | PASS | DQ-0007 e R-0007 registram a expansão de escopo. |
| Bump obrigatório | PASS | **3.0.0 → 3.1.0**, aditivo. |

## Project Structure

```text
plugin/skills/grill-with-docs/scripts/ensure_dependencies.py   # deteccao e remocao
tests/validate_dependencies_contract.py                        # 11 casos novos
```

**Structure Decision**: a detecção vive no preflight porque é ali que o ambiente já é inspecionado e reportado. Nenhum arquivo novo.
