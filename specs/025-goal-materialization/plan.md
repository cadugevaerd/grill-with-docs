# Implementation Plan: Materialização e validação do goal.md

**Branch**: `feature/goal-instruct` | **Date**: 2026-08-26 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/025-goal-materialization/spec.md`

## Summary

`init` passa a fixar o `goal.md` na raiz do projeto consumidor, no-clobber, e a
reportar em qual dos três estados o encontrou — `CREATED`, `REUSED` ou
`PRESERVED` —, gravando caminho e hash dos bytes efetivamente materializados no
`state.json` do work item. O contrato do documento (marcador de versão e tupla
de partes exigidas) passa a viver num SSOT único em `grill_core`, do qual o
materializador e o validador leem, e um validador novo na suíte canônica reprova
qualquer documento a que falte uma parte exigida, nomeando-a.

A abordagem técnica é espelhar `ensure_workflow.py` no **comportamento**
(criação atômica por `os.link`, leitura por descritor com `O_NOFOLLOW`,
vocabulário de estado) e divergir dele na **organização** (SSOT em `grill_core`,
script fino), conforme ADR-0101.

O texto normativo do `goal.md` não é reaberto: já foi entregue pelo work item
`feature-goal-autopilot` como `assets/GOAL.template.md`. Esta entrega o
transporta e o protege.

## Technical Context

**Language/Version**: Python >=3.10, somente biblioteca padrão

**Primary Dependencies**: nenhuma. O core não tem dependência externa e nunca
baixa bytes.

**Storage**: sistema de arquivos. `goal.md` na raiz do projeto consumidor;
registro em `.grill/work-items/<work_id>/state.json`.

**Testing**: `python3 tests/run_validators.py` (glob de `validate_*.py`; um
arquivo novo entra na suíte sozinho). Validador novo:
`tests/validate_goal_document_contract.py`.

**Target Platform**: Linux, Windows e macOS — a matriz de CI cobre os três SOs
em Python 3.10 e 3.13. Nenhum teste pode tocar a rede nem exigir `specify`,
`node` ou `backlogctl` reais.

**Project Type**: CLI / biblioteca interna de plugin

**Performance Goals**: N/A. A materialização é uma escrita única por `init`.

**Constraints**: sem rede; sem dependência externa; no-clobber absoluto; hooks
permanecem read-only; nenhuma escrita fora da raiz do projeto.

**Scale/Scope**: um arquivo novo em `grill_core`, um script novo, uma função e
um bloco de payload em `grill_workspace.py`, um validador novo, e o bump
sincronizado em oito lugares.

## Constitution Check

*GATE: passa antes da Phase 0 e revalidado após a Phase 1.*

| Cláusula | Como esta entrega a satisfaz | Veredicto |
|---|---|---|
| Evidência antes de afirmação | O estado reportado vem do read-back do disco, não do conteúdo esperado (FR-005). O hash registrado é dos bytes materializados. | PASS |
| Work item isolado e ownership | Toda a entrega pertence a `feature-goal-materialization-c29d98e49a524ca8a482615d8d528dab`, cujo `WORK-ITEM.json` já declara os treze caminhos do escopo. | PASS |
| Feature/fix plan-only | Este plano não altera código. A execução pertence ao ciclo externo. | PASS |
| Sequência obrigatória do desenvolvimento | `plan` é a segunda etapa e roda depois de `specify` complete e atestado. | PASS |
| Verify/review antes de ship | Nada aqui autoriza publicação. | PASS |
| Fail-closed sem waiver | Impedimento de escrita vira `GOAL-UNAVAILABLE` e bloqueia; documento divergente é `PRESERVED` e não é tratado como sucesso. | PASS |
| Rastreabilidade | ADR-0101 e ADR-0102 no work item; FRs numerados; caminhos exatos no `WORK-ITEM.json`. | PASS |
| Tier de modelo e esforço do worker Orca | Aplica-se a `implement-parallel`, cujos workers derivam o tier do binding `assets/workflow-tier-models.json`. Nada neste plano escolhe modelo. | PASS |
| Bump obrigatório do plugin | FR-017; o plano fixa o bump MINOR sincronizado nos oito lugares como parte da entrega, não como follow-up. | PASS |
| Release obrigatória por versão | Cumprida pelo pipeline no merge para `main`; nada aqui a contorna. | PASS |

**Nenhuma violação.** A seção Complexity Tracking permanece vazia.

**Re-check pós-Phase 1**: os artefatos de design não introduziram entidade,
camada ou dependência nova além das declaradas acima. Veredicto inalterado.

## Project Structure

### Documentation (this feature)

```text
specs/025-goal-materialization/
├── plan.md              # Este arquivo
├── research.md          # Phase 0
├── data-model.md        # Phase 1
├── quickstart.md        # Phase 1
├── contracts/
│   ├── goal-document.md         # O contrato do documento: marcador e ESSENTIAL
│   └── materialization-cli.md   # O contrato de saída: init e ensure_goal.py
├── checklists/
│   └── requirements.md  # Já existente (etapa checklist)
└── tasks.md             # Phase 2 — NÃO criado por /speckit-plan
```

### Source Code (repository root)

```text
plugin/skills/grill-with-docs/
├── assets/
│   └── GOAL.template.md                   # existente, byte-intacto nesta entrega
├── scripts/
│   ├── grill_core/
│   │   └── goal_document.py               # NOVO — SSOT: MARKER, VERSION, ESSENTIAL, compatible()
│   ├── ensure_goal.py                     # NOVO — script fino: resolve_goal(), CLI --ensure
│   ├── ensure_workflow.py                 # NÃO TOCADO (ADR-0101)
│   └── grill_workspace.py                 # ALTERADO — ensure_project_goal() + payload + state
├── SKILL.md                               # ALTERADO — heading de versão
└── references/
    └── session-protocol.md                # ALTERADO — heading de versão

tests/
├── validate_goal_document_contract.py     # NOVO — trava o contrato do documento
└── validate_distribution.py               # ALTERADO — constante VERSION

plugin/.claude-plugin/plugin.json           # ALTERADO — bump
plugin/.codex-plugin/plugin.json            # ALTERADO — bump
.claude-plugin/marketplace.json             # ALTERADO — bump
.agents/plugins/marketplace.json            # ALTERADO — bump
README.md                                   # ALTERADO — heading de versão
CHANGELOG.md                                # ALTERADO — entrada da versão
```

**Structure Decision**: o repositório não tem `src/`; o código do plugin vive em
`plugin/skills/grill-with-docs/scripts/`, com a lógica pura em
`scripts/grill_core/` e as fronteiras de I/O nos scripts irmãos. Esta entrega
segue essa divisão existente: `grill_core/goal_document.py` é lógica pura sobre
texto já lido — não toca disco, não importa `grill_workspace` — e `ensure_goal.py`
é a fronteira que abre descritores e escreve. É a mesma separação que
`grill_core/triage.py` já mantém em relação ao seu CLI, e é o que permite ao
validador exercitar o contrato sem tocar o sistema de arquivos.

`grill_workspace.py` recebe apenas a costura: uma função `ensure_project_goal`
simétrica a `ensure_project_workflow`, a chamada dentro de `init_command`, o
bloco no payload e o bloco em `state_template`.

## Complexity Tracking

> Nenhuma violação de Constitution Check. Seção vazia por design.
