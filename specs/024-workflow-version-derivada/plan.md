# Implementation Plan: Versão de workflow derivada do documento

**Branch**: `fix/audit` | **Date**: 2026-08-23 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/024-workflow-version-derivada/spec.md`

## Summary

O campo do `state.json` que declara qual sequência de etapas o work item fala é um literal congelado no asset, idêntico em todo bundle criado, e nunca é lido do `WORKFLOW.md` que ele descreve. A projeção de status julga cada bundle por esse campo, então um repositório que preserva um documento anterior nasce declarando a sequência corrente e é julgado por etapas que o documento dele não contém. A correção resolve a declaração do documento uma vez, na criação, e a usa como origem do campo; a resolução é estrita — exatamente uma declaração reconhecida — e a criação recusa fail-closed quando ela não resolve.

O escopo foi reduzido depois da 5.0.0, que encerrou por redefinição o caso irmão deste defeito e corrigiu o gate da camada executável. Ver ADR-0003.

## Technical Context

**Language/Version**: Python >= 3.10

**Primary Dependencies**: nenhuma. O core é biblioteca padrão apenas, por restrição do projeto; `audit_decisions.py` não importa sequer `grill_core`.

**Storage**: arquivos JSON e Markdown no repositório do consumidor (`.grill/work-items/<work-id>/`). Sem banco.

**Testing**: `python3 tests/run_validators.py` (glob de `tests/validate_*.py`, `unittest`). Baseline 1233 testes em 26 validadores, 1 skip dependente de ambiente.

**Target Platform**: CLI multiplataforma. CI cobre ubuntu-24.04, windows-2025 e macos-26, em Python 3.10 e 3.13.

**Project Type**: CLI / plugin distribuído.

**Performance Goals**: N/A. A resolução é uma regex sobre um documento já lido em memória na criação; custo desprezível e fora de qualquer laço.

**Constraints**: sem rede em teste; sem `specify`, `node` ou `backlogctl` reais; nenhum work item já publicado pode mudar de veredito; `audit_decisions.py` não é alterado e permanece stdlib puro; `managed_version` permanece com semântica first-match para seus chamadores.

**Scale/Scope**: 3 arquivos de produção, 3 validadores estendidos. Os work items deste repositório servem de frota de regressão.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Cláusula | Status | Evidência |
|---|---|---|
| Evidência antes de afirmação | PASS | Cada achado de [research.md](./research.md) cita arquivo e linha; o próprio defeito é evidenciado por `grill_workspace.py:691` e `audit_decisions.py:801` |
| Work item isolado e ownership | PASS | Planejamento inteiro sob `fix-audit-workflow-version-2a9e7a7ba01f42dcb24b3bb83d801b03`; nenhum outro bundle tocado |
| Feature/fix plan-only | PASS | Esta fase produz spec, plano e artefatos de design. Nenhum arquivo sob `plugin/` foi alterado |
| Sequência obrigatória do desenvolvimento | PASS | `specify` fechado com evidência hasheada; `plan` em curso; nenhuma etapa saltada |
| Verify/review antes de ship | NOT-APPLICABLE | Ship não iniciado; a cláusula governa uma transição que ainda não existe |
| Fail-closed sem waiver | PASS | A recusa `WORKFLOW-MARKER-UNRESOLVED` é fail-closed por design; o fallback silencioso para a versão ativa foi avaliado e rejeitado em ADR-0001 |
| Rastreabilidade | PASS | FR ↔ user story ↔ cenário de [quickstart.md](./quickstart.md) ↔ ADR-0001/ADR-0002, com identificadores estáveis |
| Tier de modelo e esforço do worker Orca | NOT-APPLICABLE | Nenhum worker despachado via Orca nesta fase |
| Bump obrigatório do plugin | PASS (planejado) | FR-010 e a fase 4 abaixo fixam o incremento nos oito pontos; nada sob `plugin/` foi alterado ainda, então a cláusula ainda não foi acionada |
| Release obrigatória por versão | NOT-APPLICABLE | Nenhuma publicação nesta fase |
| Governance | PASS | Constituição preservada byte a byte, SHA-256 `54d5522b…` registrado no bundle; nenhuma decisão deste plano a dispensa |

**Re-check pós-Phase 1**: sem violação nova. A única decisão de design que ampliou algo além do handoff é a equivalência de R3 (marcador v2 → sequência v3), e ela **reduz** escopo em vez de ampliá-lo: evita mexer em tabela de sequência, que o handoff declara fora de escopo. Registrada com alternativa e razão em [research.md](./research.md).

**Complexity Tracking**: não preenchido — nenhuma violação a justificar.

## Project Structure

### Documentation (this feature)

```text
specs/024-workflow-version-derivada/
├── plan.md              # This file
├── spec.md              # WHAT/WHY
├── research.md          # Phase 0
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/
│   └── cli.md           # Phase 1
├── checklists/
│   └── requirements.md
└── tasks.md             # Phase 2 (/speckit-tasks — não criado aqui)
```

### Source Code (repository root)

```text
plugin/skills/grill-with-docs/
├── scripts/
│   ├── grill_workspace.py        # state_template: derivação dos dois campos + recusa fail-closed
│   ├── ensure_workflow.py        # sole_managed_version (novo, ao lado de managed_version)
│   └── audit_decisions.py        # asserção de estado: pertencimento no lugar do literal
└── assets/
    └── state.template.json       # literal "v4" deixa de ser valor final

tests/
├── validate_workspace_contract.py    # carimbo do init/migrate, recusa, matriz ponta a ponta
├── validate_contract.py              # asserção de estado da auditoria
├── validate_workflow_v3_contract.py  # sole_managed_version e paridade entre detectores
├── validate_distribution.py          # constante VERSION (bump)
└── fixtures/                         # documentos da matriz, materializados pelo ensure_workflow
```

**Structure Decision**: o repositório é o próprio plugin e o consome (dogfooding). A produção vive em `plugin/skills/grill-with-docs/{scripts,assets}` e os testes em `tests/`, com `run_validators.py` fazendo glob de `validate_*.py`. Não há `src/`; nenhuma estrutura nova é criada por esta feature — os quatro arquivos de produção já existem.

## Fases de implementação

Ordem obrigatória: cada fase depende da anterior.

1. **Detector estrito.** `sole_managed_version` em `ensure_workflow.py`, com teste da matriz R5 e teste de paridade contra a verificação de marcador que o auditor já faz. Nada mais consome a função ainda — a fase é verificável sozinha. (FR-005, V-3)
2. **Writer.** `state_template` resolve o marcador, aplica o mapa de derivação de [data-model.md](./data-model.md) ao campo de sequência e recusa `WORKFLOW-MARKER-UNRESOLVED` **antes de qualquer escrita**. A recusa precede a derivação dentro da própria fase: separá-las abriria janela em que o writer grava sem saber o que fazer com declaração não resolvível. Cobre os dois chamadores, `init` e `migrate`, por construção. (FR-001, FR-002, FR-003, FR-004, FR-007, V-1)
3. **Distribuição.** Incremento SemVer nos pontos travados por `validate_distribution.py`. (FR-009)

A fase que trocava o literal da auditoria por pertencimento **saiu do plano**: o campo que ela tocava foi redefinido fora deste trabalho e o finding correspondente deixou de existir. Com ela sai também a inversão reader-antes-de-writer, que existia só para proteger a frota durante a janela entre as duas mudanças. A invariância da frota continua exigida (FR-006) e continua sendo caso de teste.

## Riscos

| Risco | Mitigação |
|---|---|
| Mudar `managed_version` por engano quebra a materialização, que depende do `or VERSION` | Função nova ao lado; teste que fixa a semântica first-match da original |
| Regex de marcador existe no detector e no auditor e pode divergir | Teste de paridade sobre a matriz completa é o SSOT da regra (ADR-0002) |
| Fixture derivada da própria regex esconde erro de parsing | FR-009: documento real materializado pelo `ensure_workflow`; precedente de bug de parsing que sobreviveu a mais de mil testes por esse motivo |
| Entrada `v2` futura em `SEQUENCE_BY_VERSION` | A 5.0.0 unificou a tabela no SSOT `grill_core.workflow_versions`, então R8 deixou de valer; uma entrada v2 agora entra num lugar só, e continua sendo work item próprio |
