# Implementation Plan: Fence autorizado de atividade órfã

**Branch**: `cadugevaerd/fix-leader` | **Date**: 2026-09-24 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/034-fence-autorizado-atividade/spec.md`

## Summary

Uma atividade de especialista `DISPATCHED` cujo dispatch terminou sem gravar resultado, ou `RESULT_RECORDED` cuja sessão ficou retida pelo Orca, conta para sempre como trabalho ativo: `_continuity_quiescence` (`grill_workspace.py:3654-3672`) a lista em `active`, `gauntlet-context-takeover` recusa `TAKEOVER-WORK-ACTIVE` (4170-4174) e nenhum verbo a leva a estado terminal, porque `gauntlet-activity` exige o líder corrente (`@_gauntlet_authorized`, 5952) e `RESULT_RECORDED → FAILED` não é aresta (`agent_orchestration.py:48`). A entrega acrescenta um **verbo de fence autorizado**, `gauntlet-activity-fence`, preview-first e não decorado, ao lado do takeover (4126-4350) e na forma do `gauntlet-run-abandon` (5152-5189): exige prova terminal Orca do dispatch do especialista e do líder da atividade, prova de readiness do solicitante quando o líder terminou, e `human-authorization/v1` com `scope = work_id:context_id:activity_id`. A aplicação registra uma operação `activity-fence` `CONFIRMED`, leva a atividade a `FAILED` com `diagnostic_ref` apontando a operação e fecha o recurso de sessão em `CLOSED` com receipt correlacionado, em dois `transact` na forma órfã e em um na forma retida (research R7). O resultado gravado nunca é aceito; o autor é reexecutado como atividade nova — pelo sucessor depois do takeover na forma órfã, ou pelo próprio líder vivo no mesmo contexto na forma retida (research R10). Uma aresta nova `RESULT_RECORDED → FAILED` (ADR-0001, DQ-0009) e o bump 6.0.30 → 6.0.31 completam o escopo.

## Technical Context

**Language/Version**: Python >=3.10, somente biblioteca padrão

**Primary Dependencies**: nenhuma nova; reuso de `_takeover_observation`, `_session_readiness`, `_require_current_leader`, `load_checkpoint_attestation`, `attestation._validate_human_authorization` e `store.transact`

**Storage**: store JSON do orquestrador em `.git/grill/orchestrator.json`, por CAS com revisão (`store.py:1605-1631`)

**Testing**: `unittest` via `python3 tests/run_validators.py`; `tests/validate_agent_orchestration_contract.py` (verbo, com os seams `takeover_show`, `guarded_run`, `assert_refused_and_unwritten`) e `tests/validate_orchestrator_store_contract.py` (aresta nova); `tests/validate_distribution.py` (bump)

**Target Platform**: Linux, macOS e Windows (matriz CI: 3 SOs × Python 3.10 e 3.13), sem rede e sem `orca` real

**Project Type**: plugin CLI / biblioteca do core GWD

**Performance Goals**: duas observações do host por fence (especialista e líder) mais uma de readiness quando o líder terminou; nenhuma leitura no caminho quente de outros verbos

**Constraints**: fail-closed; ausência, silêncio, expiry e observação inconclusiva nunca autorizam; prévia não escreve; toda recusa deixa o Store bit a bit igual; nada muda em Constituição, WORKFLOW, `ESSENTIAL`, registries, `attestation.py`, `agent_runtime.py` nem na policy `agent-orchestration.v1.json`

**Scale/Scope**: 1 verbo novo em `grill_workspace.py`, 1 literal de aresta em `agent_orchestration.py`, testes nos dois validadores existentes, 2 parágrafos de documentação, 9 arquivos de versão (8 pontos + `CHANGELOG.md`)

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Constituição 2.1.0, sha256 `54d5522b18e43efa05311dbf13ed79694b79ccfcb01509384b3572b2d5667569` (11 cláusulas, `.specify/memory/constitution.md:34-62`).

| Cláusula | Situação | Evidência |
|---|---|---|
| Evidência antes de afirmação | PASS | leituras literais do Store do X7 (DQ-0001, DQ-0005); estado vivo de `interview-author-001` do work item de origem (DQ-0007); 23 arquivos (`plan-author-001`) e 30 arquivos (`plan-author-002`) do input manifest conferidos por sha256; toda citação file:line deste plano reconferida no HEAD `ad42a65` (código idêntico ao `39380f7` pelos sha256 do manifest; `plan-reviewer-001` reconferiu em `4cad807`) |
| Work item isolado e ownership | PASS | bundle `fix-fence-autorizado-atividade-f831232ae30e4087adbaa988bc0f7b24`, tipo fix, branch `cadugevaerd/fix-leader`, contexto `ctx-146fb68d0d6e` |
| Feature/fix plan-only | PASS | este plano não altera produto; mudanças só em `implement-parallel`, por worker; o ciclo termina em `PLAN_ONLY_STOP` |
| Sequência obrigatória | PASS | specify aceito (`specify-reviewer-001` e `specify-reviewer-002` APPROVED); plan em andamento |
| Verify/review antes de ship | PASS | etapas pending, precedem ship |
| Fail-closed sem waiver | PASS | cada prova tem código próprio (contracts/activity-fence.md); `not_observable`, `indeterminate`, autorização ausente ou de outro alvo, líder vivo que não é o chamador, especialista vivo e hash stale recusam sem escrever (FR-003, FR-004, FR-005, FR-013) |
| Rastreabilidade | PASS | FR-001..FR-015 → research R1..R13 → tarefas; ADR-0001; DQ-0001..DQ-0014 seladas (DQ-0013 opção A → SGD-40; DQ-0014 opção A → SGD-41); SGD-37, SGD-38, SGD-39, SGD-40 e SGD-41 fora do escopo, registrados |
| Tier de modelo do worker Orca | PASS | tier derivado do nó do DAG (implementação delimitada = intermediário; revisão final = forte/alto); nenhum modelo de fronteira como worker |
| Bump obrigatório | PASS | FR-014: 6.0.30 → 6.0.31 nos 8 pontos de `CLAUDE.md` mais a seção `## 6.0.31` em `CHANGELOG.md`, que `tests/validate_distribution.py:41-43` também fixa (research R12) |
| Release por versão | PASS | criada por `publish.yml` no push para `main`, ancorada na tag |
| Governance | PASS | Constituição lida, hash igual ao selado no work item; sem emenda (FR-015) |

**Re-check pós-design**: sem mudança. O design (Phase 1) não acrescenta dependência, não toca Constituição/WORKFLOW/registries, e cada recusa continua nomeada e sem efeito.

## Project Structure

### Documentation (this feature)

```text
specs/034-fence-autorizado-atividade/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── activity-fence.md
└── tasks.md            # /speckit-tasks
```

### Source Code (repository root)

Agrupado pelo nó do Execution DAG que cada arquivo toca; arquivos disjuntos entre nós da mesma fase (research R11 e R12).

```text
# Fase 1 — nó A: aresta nova (DQ-0009)
plugin/skills/grill-with-docs/scripts/grill_core/agent_orchestration.py   # _ACTIVITY_EDGES["RESULT_RECORDED"] += "FAILED" (48)
tests/validate_orchestrator_store_contract.py                              # lock da aresta: FAILED só com diagnostic_ref; BLOCKED continua inválido

# Fase 2 — nó B: verbo, parser e testes de contrato
plugin/skills/grill-with-docs/scripts/grill_workspace.py                   # gauntlet_activity_fence_command + parser + tabela de dispatch
tests/validate_agent_orchestration_contract.py                             # test_activity_fence (n1..n9, p1..p5)

# Fase 2 — nó C: documentação e distribuição (independente do nó B)
plugin/skills/grill-with-docs/references/session-protocol.md              # heading v6.0.31 (1) + parágrafo do verbo (85-89)
plugin/skills/grill-with-docs/SKILL.md                                     # heading v6.0.31 (6) + frase do verbo (94)
plugin/.claude-plugin/plugin.json                                          # 6.0.31 (3)
plugin/.codex-plugin/plugin.json                                           # 6.0.31 (3)
.claude-plugin/marketplace.json                                            # 6.0.31 (11)
.agents/plugins/marketplace.json                                           # 6.0.31 (7)
tests/validate_distribution.py                                             # VERSION = "6.0.31" (8)
README.md                                                                  # **v6.0.31 (3)
CHANGELOG.md                                                               # nova seção ## 6.0.31 (acima de ## 6.0.30, linha 3)
```

**Structure Decision**: mudanças locais nos pontos já existentes, sem módulo novo. O verbo entra ao lado de `gauntlet-context-takeover` (parser em `grill_workspace.py:7131-7136`, tabela de dispatch em 7212) e reusa a forma dele: mesmas checagens em prévia e aplicação, apply só acrescenta o hash e a mutação CAS. A prova terminal vem de `_takeover_observation` (1565-1609), a prova de readiness de `_session_readiness` (1612-1655) e a autorização de `load_checkpoint_attestation` (5340-5359) com `attestation._validate_human_authorization` (773-781), sem alterar nenhuma dessas funções. `attestation.py` e `agent_runtime.py` não são tocados (DELIVERY-MAP MOD-001 boundary).

## Complexity Tracking

Sem violações.
