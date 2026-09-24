# DELIVERY-MAP

decomposition-schema: v1

## MOD-001 — Continuidade do líder (core CLI)
- module-kind: platform
- responsibility: Levar atividades órfãs ou de sessão retida a estado terminal não aceito, sob prova terminal Orca, prova de readiness do solicitante e autorização humana exata, para que takeover e prepare-switch voltem a admitir o work item
- boundary: `grill_workspace.py` (verbo, admissão, mutação CAS), `grill_core/agent_orchestration.py` (aresta `RESULT_RECORDED → FAILED`, DQ-0009), `tests/validate_agent_orchestration_contract.py`, `references/session-protocol.md`, oito pontos de distribuição; sem tocar `attestation.py`, `agent_runtime.py`, policy, registries, Constituição ou WORKFLOW
- depends-on: none

### DU-001 — Verbo de fence autorizado
- development-type: platform-devops
- phase: FASE-001
- scope-in: verbo preview-first com `--apply --expected-sha256`; provas terminais do especialista (por `orca:<owner_dispatch>`) e do líder pela observação do takeover; readiness do solicitante sucessor por `_session_readiness`; `human-authorization/v1` com escopo `work_id + context_id + activity_id`; atividade `FAILED` com `diagnostic_ref`; recurso `CLOSED` com receipt; operação `CONFIRMED` com evidência, solicitante e autorização verbatim; testes negativos e positivos; parágrafo no protocolo de sessão; bump de versão 6.0.31
- scope-out: aceite, transferência ou reaproveitamento de resultado; fence de workers de run; SGD-37; SGD-38; SGD-39; checkpoint automático; mudanças no Orca, na policy ou nos registries; encerramento do work item de origem
- depends-on: none
- acceptance: `tests/run_validators.py` verde sem rede em ubuntu/windows/macos × Python 3.10/3.13; os quatro negativos de DQ-0006 mais inconclusivo, readiness do solicitante, stale e replay deixam o Store bit a bit igual; forma X7 fenced e em seguida `TAKEOVER-APPLIED`; forma retida fenced pela aresta nova; aceite tardio recusado; `validate_distribution.py` casando 6.0.31 nos oito pontos

## MOD-002 — Encerramento do work item de origem
- module-kind: cross-cutting
- responsibility: Levar o work item fix-continuidade-sem-checkpoint-d62bb2a5380d4409ace677fa741af28d a `superseded` com o verbo de MOD-001, sem aceitar nem reexecutar `interview-author-001`
- boundary: bundle `.grill/work-items/fix-continuidade-sem-checkpoint-d62bb2a5380d4409ace677fa741af28d/` (ROADMAP.md, state.json, docs/adr/ADR-0001.md) e o Store de orquestração deste repositório, somente pelos verbos públicos; nenhum byte em `plugin/**`
- depends-on: MOD-001

### DU-002 — Fence de `interview-author-001` de origem e supersede do bundle
- development-type: platform-devops
- phase: FASE-002
- scope-in: prévia e aplicação do fence sobre `interview-author-001` do work item de origem com autorização exata; marcação `superseded` da fase de origem, milestone de origem completo, `superseded-by` no ADR de origem
- scope-out: código e distribuição; Store do X7; attempt 2 do autor de origem; aceite do resultado retido
- depends-on: DU-001
- acceptance: fence devolve `FENCE-APPLIED` (ou `FENCE-REUSED` no replay) com receipt e autorização verbatim; quiescência do work item de origem vazia; `audit` do bundle de origem devolve `MILESTONE-COMPLETE`; `gauntlet-activity --phase accept` sobre a atividade cercada recusa `ACTIVITY-STATE-DIVERGENCE`

> IDs are stable within this work item. `module-kind` is one of `domain|platform|cross-cutting`; each DU has exactly one closed development type.
