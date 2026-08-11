# Implementation Plan: Gate de bump de versão

**Branch**: `001-bump-gate` | **Date**: 2026-08-11 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/001-bump-gate/spec.md`

## Summary

Uma pull request que altere `plugin/**` precisa subir a versão declarada em `plugin/.claude-plugin/plugin.json`. A verificação compara a versão na base de merge da pull request contra a versão no HEAD e reprova quando houve diff em `plugin/**` sem aumento estrito de versão. O HOW vem fechado de `PLAN-CONTEXT.md#FASE-001` e dos ADRs do work item; este plano apenas o materializa.

## Technical Context

**Language/Version**: Python 3.10+, apenas biblioteca padrão

**Primary Dependencies**: nenhuma. `git` como ferramenta externa, já exigida pelo repositório

**Storage**: N/A

**Testing**: `unittest`, via `tests/run_validators.py`, que faz glob de `tests/validate_*.py`

**Target Platform**: GitHub Actions — ubuntu, windows e macos; Python 3.10 e 3.13

**Project Type**: ferramenta de linha de comando de CI, não distribuída dentro do plugin

**Performance Goals**: irrelevante; a verificação é dois `git show` e uma comparação

**Constraints**: sem rede; sem dependência externa; a lógica de decisão precisa ser testável sem repositório git e sem contexto de pull request

**Scale/Scope**: um script de verificação, um conjunto de testes, um job de CI

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Constituição em `.specify/memory/constitution.md`, sha256 `789b55f4`, 8 cláusulas normativas.

| Cláusula | Avaliação |
|---|---|
| Evidência antes de afirmação | PASS — a decisão de reprovar cita as duas versões comparadas; a mensagem é a evidência. |
| Work item isolado e ownership | PASS — artefatos decisórios permanecem no work item; o código nasce em `001-bump-gate`. |
| Feature/fix plan-only | PASS — a restrição vincula a sessão grill, que já encerrou em `PLAN_ONLY_STOP`. Este é o ciclo externo, autorizado a implementar. |
| Sequência obrigatória do desenvolvimento | PASS — os 11 passos são percorridos sem salto, com checkpoint por passo. |
| Verify/review antes de ship | PASS — `verify` e `review` precedem `ship` no plano de execução. |
| Fail-closed sem waiver | PASS — versão ausente ou incomparável reprova; não há flag de exceção nem forma de aprovar conteúdo sem bump. |
| Rastreabilidade | PASS — spec, plano e tarefas referenciam FASE-001, ADR-0002 e o handoff. |
| Governance | PASS — a Constituição é lida, não alterada. |

Nenhuma violação. Seção **Complexity Tracking** removida por não haver o que justificar.

## Project Structure

### Documentation (this feature)

```text
specs/001-bump-gate/
├── plan.md              # Este arquivo
├── spec.md
├── research.md          # Fase 0
├── data-model.md        # Fase 1
├── quickstart.md        # Fase 1
├── contracts/
│   └── cli.md           # Contrato de linha de comando e exit codes
├── checklists/
│   └── requirements.md
└── tasks.md             # Gerado por /speckit-tasks
```

### Source Code (repository root)

```text
tests/
├── check_version_bump.py            # NOVO — a verificação; nome fora do glob validate_*
├── validate_bump_gate_contract.py   # NOVO — testes da lógica pura, entram na suíte pelo glob
└── run_validators.py                # existente, sem alteração

.github/workflows/
└── ci.yml                           # ALTERADO — novo job de gate, só em pull_request
```

**Structure Decision**: a verificação vive em `tests/`, junto do resto da ferramenta de repositório, e **fora** de `plugin/`. Duas consequências desejadas: o gate não é distribuído aos consumidores, e alterar o próprio gate não dispara a exigência de bump que ele impõe.

O nome `check_version_bump.py` é deliberado: `run_validators.py` faz glob de `validate_*.py`, então a verificação não é arrastada para a matriz de validadores, onde não haveria contexto de pull request. A lógica pura é exercitada por `validate_bump_gate_contract.py`, que entra na suíte normalmente e não precisa de git.
