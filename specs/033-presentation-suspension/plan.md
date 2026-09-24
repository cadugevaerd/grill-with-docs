# Implementation Plan: Suspensão e reativação da apresentação local no core

**Branch**: `cadugevaerd/feat-new-subagents` | **Date**: 2026-09-24 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `specs/033-presentation-suspension/spec.md`; work item `fix-presentation-suspension-d97e4c3d7b434c119477ec59d56ecbd5` (PLAN-CONTEXT, ADR-0001..0003, CONTEXT); laudo `.grill/triage-evidence/presentation-suspension-debug.md`

## Summary

`project_leader_presentation` (`grill_core/agent_runtime.py:1107-1129`) é o único ponto que observa a sessão e projeta a apresentação local, e hoje chama `presentation_state` sem `suspension` nem `application`; a função pura já sabe representar `suspended_by_user` (`agent_runtime.py:275-287`) e os consumidores a jusante já aceitam essa projeção (`agent_orchestration.py:1108-1147`). A entrega acrescenta **um produtor**: uma função pura que percorre as mensagens normalizadas do transcript e devolve a última frase de controle (`stop adhd mode` / `start adhd mode`) dita em mensagem `role=user` com um único bloco de texto. Suspensão vigente projeta `application=suspended_by_user`, `loading=stale`, `work_ready=true`, `use_ready=false`, sem `load_request` e sem chamar `_full_read`; reativação corta as leituras anteriores à frase, como a compactação já faz. O gate de upgrade em `grill_workspace.py:3470-3474` deixa de exigir releitura quando a apresentação observada está suspensa (ADR-0003). Contrato publicado (`SKILL.md` §Bootstrap e `session-protocol.md`) passa a nomear fonte não-agente da sessão e `start adhd mode` (FR-012). Testes offline com a forma real dos registros de compactação dos dois harness (FR-011). Bump patch nos oito pontos de versão.

## Technical Context

**Language/Version**: Python >=3.10, somente biblioteca padrão (`hashlib`, `json`)

**Primary Dependencies**: nenhuma nova; reaproveita `presentation_state`, `_native_messages`, `_full_read`, `leader_session_identity` e `_presentation_config_fingerprint` já existentes em `agent_runtime.py`

**Storage**: nenhum campo novo; a projeção suspensa entra no `presentation` do contexto de orquestração já persistido pelo Store (`.git/grill/orchestrator.json`) pelo refresh existente em `grill_workspace.py:3475-3482`

**Testing**: `unittest` via `python3 tests/run_validators.py`; validador `tests/validate_agent_orchestration_contract.py` estendido; fixture `tests/orchestration_fixture.py` sem alteração

**Target Platform**: Linux, macOS e Windows (matriz CI: 3 SOs × Python 3.10 e 3.13); nenhum teste toca rede, runtime real ou processo externo

**Project Type**: plugin CLI / biblioteca do core GWD

**Performance Goals**: uma varredura linear adicional sobre `transcript["messages"]` por observação, no mesmo transcript já lido para `_full_read`; nenhuma leitura extra do host

**Constraints**: fail-closed; a suspensão só nasce da observação da sessão (FR-006); códigos de recusa mantêm significado (FR-010); `presentation_state` continua pura e com a mesma assinatura; menor diff (Ponytail/YAGNI)

**Scale/Scope**: 2 pontos de mudança no core (~25 linhas + 1 linha), 2 documentos de contrato (1 parágrafo cada), ~100 linhas de teste num validador existente, 8 pontos de versão

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

Constituição `2.1.0`, sha256 `54d5522b18e43efa05311dbf13ed79694b79ccfcb01509384b3572b2d5667569` (a mesma selada no work item). Onze cláusulas: dez princípios e Governance.

| Cláusula | Pré-design | Pós-design | Evidência |
|---|---|---|---|
| Evidência antes de afirmação | PASS | PASS | laudo com reprodução offline (Exp A1/A2/A3/B); formas nativas de compactação capturadas de 34 transcripts Claude e 16 rollouts Codex (research R10) |
| Work item isolado e ownership | PASS | PASS | bundle próprio; este plano escreve só em `specs/033-presentation-suspension/` |
| Feature/fix plan-only | PASS | PASS | fix: código de produto e testes só em `implement-parallel`, por worker; plan termina em `PLAN_ONLY_STOP` |
| Sequência obrigatória do desenvolvimento | PASS | PASS | specify atestado (`c2dd807`); plan em andamento; checklist, tasks, analyze, partition a seguir |
| Verify/review antes de ship | PASS | PASS | etapas pending precedem ship; quickstart fixa os gates executáveis |
| Fail-closed sem waiver | PASS | PASS | suspensão só por mensagem `role=user` da própria sessão; forma inválida da frase, fala do agente, resumo e sintética não mudam nada; pré-requisitos seguem exigidos (C1); `STYLE-SCOPE-CONFLICT` permanece |
| Rastreabilidade | PASS | PASS | FR-001..FR-013 → research R1..R14 → contratos → tarefas; ADR-0001..0003 citados por decisão |
| Tier de modelo e esforço do worker Orca | PASS | PASS | autoria do plano em worker forte/alto (esta sessão); implementação delimitada em tier intermediário na partition; leitura/teste em tier econômico |
| Bump obrigatório do plugin | PASS | PASS | R13: patch acima da versão publicada no ship, nos 8 pontos; gate `bump-gate.yml` roda na PR |
| Release obrigatória por versão | PASS | PASS | publicada pelo pipeline no push para `main` (`publish.yml`), tag + release ancoradas |
| Governance | PASS | PASS | Constituição lida somente leitura, hash coincide com `state.json`; nenhuma emenda, nenhum waiver |

Re-check pós-design: sem mudança. Nenhuma violação a justificar.

## Project Structure

### Documentation (this feature)

```text
specs/033-presentation-suspension/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── presentation-suspension.md      # frases de controle, projeção, registro, gate de upgrade, texto do contrato publicado
│   └── native-compaction-records.md    # forma capturada dos registros nativos (Claude e Codex) usada pelos testes
└── tasks.md                             # /speckit-tasks
```

### Source Code (repository root)

```text
plugin/skills/grill-with-docs/scripts/grill_core/agent_runtime.py      # _presentation_control (nova, ~15 l.) + project_leader_presentation (~10 l. alteradas)
plugin/skills/grill-with-docs/scripts/grill_workspace.py               # _gauntlet_authorized, gate de upgrade l.3470-3474 (1 condição)
plugin/skills/grill-with-docs/SKILL.md                                 # §Bootstrap l.32 (FR-012) + heading vX.Y.Z
plugin/skills/grill-with-docs/references/session-protocol.md           # §Apresentação local l.9 (FR-012) + heading vX.Y.Z
tests/validate_agent_orchestration_contract.py                         # 4 testes novos (~100 l.), ao lado de test_presentation_context
plugin/.claude-plugin/plugin.json                                      # versão
plugin/.codex-plugin/plugin.json                                       # versão
.claude-plugin/marketplace.json                                        # versão
.agents/plugins/marketplace.json                                       # versão
tests/validate_distribution.py                                         # VERSION
README.md                                                              # heading **vX.Y.Z
```

**Structure Decision**: nenhum módulo, arquivo de produto ou fixture novo. O produtor entra ao lado de `_full_read`, no mesmo módulo que já normaliza o transcript, e é chamado de um único lugar. O teste do transcript nativo (`_native_messages`) fica no validador de orquestração, que já cobre `_full_read`, `_tool_results` e o adapter.

## Arquivos a tocar, estimativa e ordem

| # | Arquivo | Mudança | Linhas (est.) |
|---|---|---|---|
| 1 | `grill_core/agent_runtime.py` | `_presentation_control(messages)` pura; `project_leader_presentation` decide entre suspensa / reativada / fluxo atual | +25 |
| 2 | `grill_workspace.py` | condição `application != "suspended_by_user"` no gate de upgrade (l.3470-3474) | +1 |
| 3 | `tests/validate_agent_orchestration_contract.py` | `test_presentation_control_from_session_user_message`, `test_presentation_suspension_requires_prerequisites`, `test_native_compaction_records_become_compaction_blocks`, `test_presentation_upgrade_during_suspension_keeps_work_ready` | +100 |
| 4 | `SKILL.md` §Bootstrap | parágrafo l.32 reescrito (contracts/presentation-suspension.md §Texto) | ±4 |
| 5 | `references/session-protocol.md` | parágrafo l.9 reescrito (idem) | ±4 |
| 6 | 8 pontos de versão | patch acima da versão publicada no ship | 8 |

Ordem para partition: 1 e 3 são um só nó (produtor + testes do produtor); 2 é nó próprio com o teste CLI do gate; 4, 5 e 6 são um nó de documentação/versão (o heading de 4 e 5 é um dos 8 pontos, então os três arquivos ficam no mesmo grant). Nenhuma linha de tarefa pode conter token com `/` fora de caminho real (aprendizado da 028/029).

## Riscos

| Risco | Impacto | Mitigação |
|---|---|---|
| Transporte Orca live (`contentComplete=true`) entrega mensagens já normalizadas pelo Orca; a marcação de mensagem sintética/meta nesse caminho não é verificável offline (laudo H3) | uma mensagem sintética cujo texto inteiro seja a frase suspenderia | regra de igualdade exata em bloco único; o fallback local (`_local_transcript` → `_native_messages`) está provado com formato real; risco residual documentado em research R14 |
| Coordenador Orca pode suspender a apresentação de um worker (mensagem `user` do terminal despachado) | comportamento declarado, não defeito | ADR-0001; o texto do contrato (FR-012) passa a dizer isso |
| Editar `SKILL.md` muda `gwd_skill_sha256`: todo contexto ativo exige releitura após instalar a versão nova | igual a qualquer bump; contextos suspensos são exatamente os que esta entrega isenta | comportamento existente; nenhum código novo |
| Codex: ramo `event_msg.user_message` de `_native_messages` sem captura real (0 ocorrências em 60 rollouts recentes; `response_item.message` é a forma observada) | ramo permanece sem teste com forma real | não tocar o ramo; testar `response_item` e `compacted`, que são as formas capturadas (R10) |
| Codex antigo pode espelhar a mesma mensagem em `event_msg` e `response_item` | dois registros `user` com a mesma frase; `source_ref` aponta ao último em ordem de arquivo | determinístico; a decisão não muda |
| Suspensão vale por sessão; `_presentation_control` percorre o transcript inteiro (não corta na compactação) | transcript longo: varredura O(n) já paga por `_full_read` | mesma lista, sem leitura adicional |

## Complexity Tracking

Sem violações.
