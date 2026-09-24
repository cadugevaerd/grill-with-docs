# PLAN-CONTEXT

## FASE-001 — Suspensão e reativação da apresentação local no core
- phase: FASE-001
- ADRs: ADR-0001, ADR-0002, ADR-0003
- BLs: none
- delivery-units: DU-001
- development-type: platform-devops

### HOW
- Ponto único de produção: `project_leader_presentation` em `plugin/skills/grill-with-docs/scripts/grill_core/agent_runtime.py:1121-1128`, que hoje chama `presentation_state` sem `suspension`/`application`. Uma função pura percorre `transcript["messages"]` e devolve a última frase de controle (`stop adhd mode` ou `start adhd mode`) de mensagem `role=user` com um único bloco de texto; o normalizador já rebaixa `isMeta`, `isSynthetic` e `isCompactSummary` para `system`.
- Com suspensão vigente: `application=suspended_by_user`, `loading` stale, sem `_full_read` e sem `load_request`; `suspension` carrega comando, `source_ref` do transcript mais o id da mensagem, digest do texto, identidade de sessão, config e escopo. Não filtrar pelo último bloco `compaction`: a suspensão atravessa a compactação.
- Com reativação posterior: fluxo atual de carga, exigindo leitura integral posterior à reativação.
- `grill_workspace.py:3468-3473`: a recusa `STYLE-LOAD-UNCONFIRMED` por mudança de `config_fingerprint`/`gwd_skill_sha256` não se aplica quando a apresentação observada está `suspended_by_user` na mesma sessão/escopo; o refresh grava a apresentação nova. `STYLE-SCOPE-CONFLICT` permanece.
- `presentation_state` hoje só valida forma: a suspensão aceita pelo core é a que o adapter produz a partir do transcript; nenhum verbo aceita suspensão vinda do chamador.
- Testes offline em `tests/validate_agent_orchestration_contract.py` (cenário da l.486-492): stop antes e depois de `compaction`; start posterior reativando com leitura exigida; negativos com a frase em `assistant` e em resumo de compactação; upgrade de config durante suspensão. Um teste de `_native_messages` com registro `compact_boundary` (Claude) e `compacted` (Codex) fecha a lacuna de Q2.
- Somente biblioteca padrão; sem processo novo; sem rede. Fixtures com a forma real dos eventos do harness, nunca derivadas do código.
- Risco: um coordenador Orca pode suspender a apresentação de um worker (ADR-0001, consequência declarada).
