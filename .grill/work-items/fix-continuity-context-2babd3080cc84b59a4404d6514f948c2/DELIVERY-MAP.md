# DELIVERY-MAP

decomposition-schema: v1

## MOD-001 — Ciclo de vida do contexto de orquestração
- module-kind: platform
- responsibility: Decidir quem é o líder de um work item, quando esse vínculo pode passar a outra sessão e o que um checkpoint de continuidade carrega
- boundary: `plugin/skills/grill-with-docs/scripts/grill_workspace.py` (vínculo, adopt, prepare-switch, checkpoint) e `plugin/skills/grill-with-docs/scripts/grill_core/agent_orchestration.py` (contrato do checkpoint); contratos em `tests/`
- depends-on: none

### DU-001 — Tomada de contexto, troca desde o init e campos honestos
- development-type: platform-devops
- phase: FASE-001
- scope-in: tomada com prova de dispatch terminal (ADR-0001); `prepare-switch` sem checkpoint anterior; preview do adopt com a mesma verificação do apply; renomeação dos campos de hash em schema novo (ADR-0002)
- scope-out: BL-0001; observação de compactação e suspensão; líder que nunca foi dispatch observável
- depends-on: none
- acceptance: sessão nova assume item de líder terminal e retoma; líder vivo continua recusado; `unverifiable` continua recusado; troca preparada funciona logo após o `init`; preview do adopt e apply concordam; checkpoints antigos continuam legíveis; suíte completa em exit 0

> IDs are stable within this work item. `module-kind` is one of `domain|platform|cross-cutting`; each DU has exactly one closed development type.
