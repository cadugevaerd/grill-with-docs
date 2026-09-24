# Relatório — plan-author-001 (AUTOR, plan, work item fix-fence-autorizado-atividade-f831232ae30e4087adbaa988bc0f7b24)

- payload lido por inteiro: sha256 0e2bae2ecdeb0452e96da34321d085c9987e77daa55f4316bae3e388d7e823d7 (confere)
- input manifest: 23/23 sha256 conferidos, zero divergência; HEAD 9dd8df6 (código idêntico ao 39380f7 pelos hashes)
- escrita só nos cinco arquivos do grant; nada em .grill/, .specify/, CLAUDE.md, código ou testes; sem commit

## sha256 dos cinco artefatos

```
4dfdcf907ca0b9b064f87bcde21dae2361bf9827ae87057895e5edbfb498fc75  specs/034-fence-autorizado-atividade/plan.md
9e710a991d3d74505a1cdb0afd9acfd1ea21fddc97f4d9a59350bfa3773288e1  specs/034-fence-autorizado-atividade/research.md
b9ca00e9065378fa90bfd31301792325dfbf4a3d8e37798d0fcb9e287ece3508  specs/034-fence-autorizado-atividade/data-model.md
6ef85d548afa46b28797e3f8cca397d80700f76d00c79d1ae59170a678dbf844  specs/034-fence-autorizado-atividade/quickstart.md
742d996349bec16f45bedd16e900b77695c12c7cf552a7f0271de6b5aa7d54d0  specs/034-fence-autorizado-atividade/contracts/activity-fence.md
```

## Findings obrigatórios — onde foram resolvidos

- **interview-reviewer-001 (NOVO) Finding 1** (ordem das checagens; `operation_id` determinístico; replay/retomada antes de estado/hash): `research.md` R2 (ordem fixa em 7 passos, `operation_id = "fence-" + sha256(canonical({context, activity}))[:24]`, `_fence_recorded` classifica replay/retomada/conflito antes de `FENCE-ACTIVITY-STATE`); `contracts/activity-fence.md` ("Ordem das checagens", "Idempotência"); `data-model.md` (tabela da operação, "Transições").
- **Finding 4** (forma completa da operação): `data-model.md` tabela "Operação `activity-fence`" com `expected_before={context_id, activity_id, activity_state, resource_id, resource_state}`, `idempotency_key=operation_id`, `error=None`, `observation_ref=result_ref`; `research.md` R7 salto 1.
- **Finding 6** (nenhum no-op dentro de `mutate`): `research.md` R7 salto 2 — recurso já `CLOSED` levanta `StoreError(STATE_DIVERGENCE)`, nunca `return document`; o CLI relê o snapshot e classifica por `_fence_recorded` em `FENCE-REUSED` ou `FENCE-CAS-CONFLICT`; `FENCE-REUSED` do replay é decidido pelo snapshot lido antes de qualquer `transact` (R2).
- **Findings 2, 3 e 5** (FASE-002 / glossário): registrados como fora desta fase em `research.md` R13, sem ação.
- **specify-reviewer-002 F2** (veredicto indeterminado do especialista, do líder e do sucessor): `research.md` R3 (liveness `unverifiable` sozinha nunca decide; `*-UNPROVEN`), R4 (c) `FENCE-LEADER-UNPROVEN`, R4 (a) readiness do sucessor recusa quando não conclui; contrato ("Provas", "Solicitante", recusas); testes n3c, n5, n5b, n5c em R11. F1 e F3 (editoriais na spec) registrados em R13.
- **Revisão de origem F1/F2/F4**: conferidos contra o código e mantidos — F1 em R3 (`"orca:" + owner_dispatch`, 3700/1268/1593), F2 em R7 (salto 2 guarda só por estado; `transact` carimba `current.revision + 1` em store.py:1624), F4 em R4/R6 (`_session_readiness` 1612-1655 como no takeover 4181; `to_session_ref` no hash; `requester` em `evidence` e `intended_after`).

## Decisão um salto × dois saltos

`CLOSED`, com o número de saltos derivado do estado do recurso: forma órfã `(DISPATCHED, REGISTERED)` em dois `transact` (`REGISTERED → CLOSE_PENDING → CLOSED`), forma retida `(RESULT_RECORDED, CLOSE_PENDING)` em um. Motivo: FR-008 e a entidade "Recibo de fechamento de sessão" dizem "fechada"; `PRESERVED` não é terminal (arestas de saída em agent_orchestration.py:49), aparece em `preserved_resources`/`retained` para sempre e mudaria a prosa aprovada. Alternativas e custos (PRESERVED em um salto; `CLOSED` direto acrescentando aresta de recurso — vedado; reler snapshot entre saltos) em `research.md` R7. A retomada da janela entre saltos é detalhe de implementação coberto por p5, não critério da spec.

## Achado lateral

`tests/validate_distribution.py:41-43` exige exatamente um heading `## 6.0.31` em `CHANGELOG.md`: o bump toca nove arquivos (os oito de `CLAUDE.md` + CHANGELOG). Registrado em `plan.md` (Constitution Check, Project Structure) e `research.md` R12; não é DQ.

## Particionamento sugerido (arquivos disjuntos por fase)

- Fase 1 — nó A: `plugin/skills/grill-with-docs/scripts/grill_core/agent_orchestration.py` (aresta) + `tests/validate_orchestrator_store_contract.py` (lock).
- Fase 2 — nó B: `plugin/skills/grill-with-docs/scripts/grill_workspace.py` (verbo, parser, dispatch) + `tests/validate_agent_orchestration_contract.py` (`test_activity_fence`).
- Fase 2 — nó C: `session-protocol.md`, `SKILL.md`, os 4 manifests, `tests/validate_distribution.py`, `README.md`, `CHANGELOG.md`.

## DQs propostas

- **DQ-P1** — a prévia deve publicar um `authorization_content_sha256` que o apply exige no bundle (amarrar a autorização às observações vistas), ou `content_sha256` continua validado só na forma como no precedente do `gauntlet-run-abandon`? Recomendação: só forma nesta versão (DQ-0006 fixou a mesma forma do run-abandon; FR-003 fala de escopo, não de conteúdo); o endurecimento é aditivo e pode entrar depois sem migração. Detalhe em `research.md`, seção "DQs propostas".
