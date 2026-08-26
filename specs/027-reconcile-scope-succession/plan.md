# Implementation Plan: Sucessão explícita de escopo reconciliado

**Branch**: `fix/reconcile-scope-succession` | **Date**: 2026-08-26 | **Spec**: [spec.md](./spec.md)

**Input**: Feature specification from `/specs/027-reconcile-scope-succession/spec.md`

## Summary

O reconciliador classifica `SCOPE-OVERLAP` antes de olhar para
`depends-on-work`, nos dois caminhos (targeted e full). Consequência: um recibo
concluído vira ownership perpétuo dos caminhos que cobriu.

A correção introduz uma única regra, aplicada pelos dois caminhos: uma
sobreposição de escopo é autorizada quando, e somente quando, existe dependência
**direta declarada** ligando os dois trabalhos. Implementação: um helper puro que
recebe os dois identificadores e o mapa de dependências já validado, e devolve se
o par está autorizado. Os dois laços de sobreposição consultam esse helper antes
de anotar o conflito. Nenhuma outra recusa muda de comportamento, nenhum schema
muda, nenhum recibo precisa de migração.

Bump patch 5.2.0 → 5.2.1 nos oito pontos que `tests/validate_distribution.py`
fixa.

## Technical Context

**Language/Version**: Python >=3.10, somente biblioteca padrão (restrição do core)

**Primary Dependencies**: nenhuma. `grill_workspace.py` e `grill_core/` não
importam nada fora da stdlib.

**Storage**: arquivos JSON sob `.grill/global/receipts/` (recibos) e
`.grill/work-items/<id>/WORK-ITEM.json` (metadados declarados). Formato
inalterado por esta mudança.

**Testing**: `python3 tests/run_validators.py` (glob de `tests/validate_*.py`,
`unittest`). Os casos desta mudança entram em
`tests/validate_workspace_contract.py`, que já é o dono do contrato de
`reconcile`; `tests/validate_distribution.py` fixa a versão.

**Target Platform**: CLI multiplataforma. Matriz de CI: ubuntu/windows/macos ×
Python 3.10 e 3.13. Nenhum teste pode tocar a rede nem exigir `specify`, `node`
ou `backlogctl` reais.

**Project Type**: CLI/biblioteca de governança distribuída como plugin.

**Performance Goals**: o laço de sobreposição do caminho full é O(n² · p²) sobre
trabalhos × caminhos. A consulta de autorização é um teste de pertinência em
conjunto, O(1) amortizado, e não altera a classe de complexidade.

**Constraints**: preview permanece read-only; apply permanece atômico e
idempotente; recibos existentes permanecem legíveis sem migração; formato de
recibo inalterado; `WORKFLOW.md`, a Constituição e o registry não são tocados.

**Scale/Scope**: escopo fechado em `WORK-ITEM.json` — 11 caminhos, dos quais
apenas 3 recebem mudança de comportamento (`grill_workspace.py`,
`tests/validate_workspace_contract.py`, `tests/validate_distribution.py`); os
outros 8 são pontos de versão e documentação.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Constituição v2.1.0, sha256 `54d5522b…5667569` — o mesmo selado em
`WORK-ITEM.json`.

| Cláusula | Como este plano satisfaz | Veredito |
|---|---|---|
| Evidência antes de afirmação | Causa raiz provada em `.grill/triage-evidence/SGD-24-debug.md` e localizada em `grill_workspace.py:1775-1780,1997-2016`; cada FR do spec vira caso de teste executável | PASS |
| Work item isolado e ownership | Trabalho corre sob `fix-reconcile-scope-succession-…f245`, branch imutável `fix/reconcile-scope-succession`, worktree próprio | PASS |
| Feature/fix plan-only | A sessão `grill-with-docs` já parou em `PLAN_ONLY_STOP`; este é o ciclo executor externo, autorizado pelo handoff | PASS |
| Sequência obrigatória do desenvolvimento | Onze etapas invocadas na ordem, cada uma pela skill canônica do registry, com cadeia de receipts | PASS |
| Verify/review antes de ship | `ship` só é invocado após `verify` e `review` fecharem com receipt aceito | PASS |
| Fail-closed sem waiver | A autorização é a mais estreita possível — dependência direta declarada. Ausência, terceiro, transitividade, self, ciclo e conflito ADR permanecem bloqueando, e FR-012 exige casos negativos dedicados para cada um | PASS |
| Rastreabilidade | ADR-0001 fixa a decisão; FR→task→teste→receipt→commit encadeados | PASS |
| Tier de modelo e esforço do worker Orca | Workers de `implement-parallel` são despachados pela skill `grill-implement-parallel`, que aplica o binding de tier do próprio bundle (`grill_core/tier_models.py`) | PASS |
| Bump obrigatório do plugin | `plugin/**` muda ⇒ 5.2.0 → 5.2.1 nos oito pontos, com `tests/validate_distribution.py` como gate | PASS |
| Release obrigatória por versão | `ship` faz push direto para `main`; `publish.yml` cria tag e release ancoradas no mesmo commit | PASS |

Governança: `WORKFLOW.md`, `.specify/memory/constitution.md` e
`assets/workflow-step-skills.v4.json` não estão no escopo declarado e não são
tocados.

**Nenhuma violação. Complexity Tracking fica vazio.**

## Project Structure

### Documentation (this feature)

```text
specs/027-reconcile-scope-succession/
├── plan.md              # This file
├── spec.md              # /speckit-specify output
├── research.md          # Phase 0 output
├── data-model.md        # Phase 1 output
├── quickstart.md        # Phase 1 output
├── contracts/
│   └── reconcile-scope-authorization.md
├── checklists/
│   └── requirements.md
└── tasks.md             # /speckit-tasks output (não criado aqui)
```

### Source Code (repository root)

```text
plugin/
├── .claude-plugin/plugin.json                      # versão
├── .codex-plugin/plugin.json                       # versão
└── skills/grill-with-docs/
    ├── SKILL.md                                    # heading de versão
    ├── references/session-protocol.md              # heading de versão
    └── scripts/
        └── grill_workspace.py                      # a correção

tests/
├── validate_workspace_contract.py                  # contrato de reconcile
└── validate_distribution.py                        # constante VERSION

.claude-plugin/marketplace.json                     # versão
.agents/plugins/marketplace.json                    # versão
README.md                                           # heading de versão
CHANGELOG.md                                        # entrada 5.2.1

.grill/work-items/<work_id>/AUDIT.md                # evidência de coordenador
```

**Artefato de coordenador**: `.grill/work-items/<work_id>/AUDIT.md` registra a
conferência dos oito pontos de distribuição. Ele **não** entra em `scope.paths`
do `WORK-ITEM.json`: `.grill/` é estado do próprio work item, não superfície
reconciliável entre trabalhos, e declará-lo como escopo criaria colisão artificial
com todo outro work item do repositório. Nomeá-lo em uma tarefa é também o que
faz o `partition` devolver aquela tarefa em `deferred_to_leader`, que é o
comportamento pretendido: `README.md` e `CHANGELOG.md` estão na raiz e nenhum
worker consegue fenceá-los.

**Structure Decision**: repositório existente, sem estrutura nova. A lógica de
autorização entra em `grill_workspace.py`, junto de `scopes_overlap`, e não em um
módulo novo de `grill_core/`: o dado de que ela depende (`depends-on-work` do
bundle e o mapa de recibos) só existe nas duas funções chamadoras, e um módulo
novo obrigaria a exportar essas estruturas sem ganho de reuso. O escopo declarado
no `WORK-ITEM.json` também não inclui nenhum arquivo de `grill_core/`, então criar
um lá seria escopo não declarado.

## Complexity Tracking

Sem violações constitucionais. Nada a justificar.
