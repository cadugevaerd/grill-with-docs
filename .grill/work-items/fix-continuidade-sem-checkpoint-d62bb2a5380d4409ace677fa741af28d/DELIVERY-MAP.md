# DELIVERY-MAP

decomposition-schema: v1

## MOD-001 — Continuidade do líder (core CLI)
- module-kind: platform
- responsibility: Levar atividades órfãs ou de sessão retida a estado terminal não aceito, sob prova terminal Orca e autorização humana exata, para que takeover e prepare-switch voltem a admitir o work item
- boundary: `grill_workspace.py` (verbo, admissão, mutação CAS), `grill_core/agent_orchestration.py` (aresta `RESULT_RECORDED → FAILED`, DQ-0009), `tests/validate_agent_orchestration_contract.py`, `references/session-protocol.md`, oito pontos de distribuição; sem tocar `attestation.py`, `agent_runtime.py`, policy, registries, Constituição ou WORKFLOW
- depends-on: none

### DU-001 — Verbo de fence autorizado
- development-type: platform-devops
- phase: FASE-001
- scope-in: verbo preview-first com `--apply --expected-sha256`; provas terminais do especialista e do líder pela observação do takeover; `human-authorization/v1` com escopo `work_id + context_id + activity_id`; atividade `FAILED` com `diagnostic_ref`; recurso `CLOSED` com receipt; operação `CONFIRMED` com evidência e autorização verbatim; testes negativos e positivos; parágrafo no protocolo de sessão; bump de versão
- scope-out: aceite, transferência ou reaproveitamento de resultado; fence de workers de run; SGD-37; SGD-38; checkpoint automático; mudanças no Orca, na policy ou nos registries
- depends-on: none
- acceptance: `tests/run_validators.py` verde sem rede em ubuntu/windows/macos × Python 3.10/3.13; os quatro negativos de DQ-0006 mais inconclusivo, stale e replay deixam o Store bit a bit igual; forma X7 fenced e em seguida `TAKEOVER-APPLIED`; aceite tardio recusado; `validate_distribution.py` casando a versão nova nos oito pontos

> IDs are stable within this work item. `module-kind` is one of `domain|platform|cross-cutting`; each DU has exactly one closed development type.
