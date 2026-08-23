# DECISION-BACKLOG

## BL-0001 — Dispatch do módulo de gate por versão, no SSOT
- phase: FASE-001
- state: superseded
- owner: cadugevaerd
- decisão adiada: introduzir `GATE_MODULE_BY_VERSION` em `grill_core/workflow_versions.py` e resolver o módulo de gate por tabela, em vez de literal no ponto de injeção.
- evidência: `gauntlet.py:33-60` já resolve registry, catálogo, sequência e tier por tabela `*_BY_VERSION`; só o gate ficou fora. ADR-0001 fixa `workflow_v4` diretamente nos quatro pontos, o que não impede a v5 de repetir o defeito.
- superseded-by: ADR-0003, ADR-0004, ADR-0002
- motivo: ADR-0003 tirou v3 da superfície de execução, então `EXECUTABLE_VERSIONS` passa a ter um elemento só e não há N gates a despachar — a decisão adiada deixou de existir, em vez de continuar pendente. O risco que ela cobria (a v5 repetir o defeito nos quatro pontos de injeção) passou para o teste ancorado em `ACTIVE_VERSION` do ADR-0002, que reprova sozinho quando a frontier se move.

> Estados: `open | resolved | superseded`; `resolved` e `superseded` são terminais. Todo BL pertence a exatamente uma fase e deve ser referenciado no ROADMAP, handoff e PLAN-CONTEXT. Não fabrique um BL apenas para preencher o template.
