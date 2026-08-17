# Implementation Plan: Pré-requisito fail-closed do backlog operacional

**Branch**: `feat/backlog-ssot` | **Date**: 2026-08-17 | **Spec**: [spec.md](./spec.md)

## Summary

FASE-003 torna exigível o que as duas fases anteriores construíram. Três mudanças pequenas e uma consequência grande.

Pequenas: `backlogctl` passa de `required: false` para `required: true` no manifesto; o bind deixa de depender de `--allow-install`; e `init` recusa sem vínculo. Grande: a criação passa a recusar onde antes prosseguia, o que é **incompatível** com consumidores existentes e leva o marco a 3.0.0.

A parte que exige cuidado é a saída. `--skip-backlog` sobrevive porque removê-la quebraria dois pontos da própria verificação automatizada e todo consumidor que crie trabalho sem o backlog. Mas passa a ser carimbada no bundle, e o carimbo bloqueia aprovação — senão um trabalho criado pela saída ficaria indistinguível de um conforme e o portão mentiria sobre o próprio pré-requisito.

O carimbo precisa de caminho de saída. Sem ele a válvula de escape vira cela: um trabalho criado sem backlog nunca mais alcançaria aprovação, mesmo depois de vinculado.

## Technical Context

**Language/Version**: Python >=3.10, stdlib apenas.

**Primary Dependencies**: nenhuma nova. `assets/dependencies.json` muda um campo.

**Storage**: o carimbo vive no `state.json` do work item, mutável, ao lado de `decision_backlog_mode` que a FASE-002 introduziu.

**Testing**: `unittest`. `tests/validate_dependencies_contract.py` para o manifesto, `tests/validate_backlog_contract.py` para a recusa e o carimbo, e o validador de workspace para o gate de criação.

**Target Platform**: matriz sem `backlogctl`. Isto é o que torna `--skip-backlog` obrigatório e não opcional.

**Constraints**: a recusa é nomeada e sem traceback; a saída é única e explícita; o desligamento global de detecção continua não valendo como conformidade.

**Scale/Scope**: um campo de manifesto, um gate em `init`, um carimbo, um comando de limpeza e um finding novo no auditor.

## Constitution Check

| Cláusula | Status | Evidência |
|---|---|---|
| Evidência antes de afirmação | PASS | O carimbo é o que impede o bundle de afirmar conformidade que não tem. |
| Work item isolado e ownership | PASS | Carimbo no `state.json` do próprio work item. |
| Feature/fix plan-only | PASS | Implementação no ciclo externo. |
| Sequência obrigatória | PASS | `phase-turn` resetou a matriz; `specify` feito. |
| Verify/review antes de ship | PASS | Mesma ordem das fases anteriores. |
| Fail-closed sem waiver | PASS | É o tema da fase. A saída é nomeada, versionada e registrada — não implícita. Precedente: o desligamento global de dependências, que nunca conta como `OK`. |
| Rastreabilidade | PASS | ADR-0001 governa; citado no ROADMAP, PLAN-CONTEXT e handoff. |
| Bump obrigatório | PASS | **2.10.0 → 3.0.0**. Incompatível: a criação recusa onde antes prosseguia. |

Nenhuma violação.

## Project Structure

```text
plugin/skills/grill-with-docs/
├── assets/dependencies.json    # backlogctl required: true
├── scripts/
│   ├── grill_workspace.py      # gate de criacao, carimbo, comando de limpeza
│   └── audit_decisions.py      # finding para bundle carimbado
└── SKILL.md

tests/
├── validate_dependencies_contract.py
├── validate_backlog_contract.py
└── validate_workspace_contract.py
```

**Structure Decision**: nenhum arquivo novo. O carimbo acompanha `decision_backlog_mode` no `state.json`, porque ambos descrevem como o bundle foi produzido e são consumidos pelo mesmo gate.
