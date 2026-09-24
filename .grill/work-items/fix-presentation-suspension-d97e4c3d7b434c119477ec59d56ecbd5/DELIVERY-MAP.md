# DELIVERY-MAP

decomposition-schema: v1

## MOD-001 — Apresentação local do fluxo GWD
- module-kind: platform
- responsibility: Projetar o estado de apresentação do líder (carga, suspensão, reativação) a partir de observações nativas da sessão
- boundary: `plugin/skills/grill-with-docs/scripts/grill_core/agent_runtime.py` (projeção e normalização do transcript) e `plugin/skills/grill-with-docs/scripts/grill_workspace.py` (gate de upgrade); contratos em `tests/`
- depends-on: none

### DU-001 — Suspensão, reativação e upgrade suspenso
- development-type: platform-devops
- phase: FASE-001
- scope-in: suspensão por mensagem de usuário da sessão (ADR-0001); reativação por `start adhd mode` (ADR-0002); upgrade durante a suspensão (ADR-0003); teste de `compact_boundary`/`compacted`
- scope-out: conformidade das respostas do modelo (F1); matriz T029
- depends-on: none
- acceptance: stop suspende antes e depois da compactação sem recarga; start reativa exigindo leitura; autorrelato não suspende; upgrade suspenso não trava; boundary nativo vira bloco de compactação; suíte completa em exit 0

> IDs are stable within this work item. `module-kind` is one of `domain|platform|cross-cutting`; each DU has exactly one closed development type.
