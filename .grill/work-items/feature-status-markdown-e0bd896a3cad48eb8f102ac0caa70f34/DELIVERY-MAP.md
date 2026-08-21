# DELIVERY-MAP

decomposition-schema: v1

## MOD-001 — Projeção de status
- module-kind: platform
- responsibility: Classificar o estado operacional dos work items e renderizar uma resposta humana determinística sem quebrar o contrato JSON
- boundary: `plugin/skills/grill-with-docs/scripts/grill_status.py` e adaptador público `grill_workspace.py status`
- depends-on: none

### DU-001 — Classificação e renderer Markdown
- development-type: backend
- phase: FASE-001
- scope-in: Predicado de fechamento, motivos ordenados, opção de formato, filtragem de fechados, `all good`, tabela e linhas sintéticas de workspace
- scope-out: `gauntlet-status`, mudança dos exit codes, remoção de itens do JSON, requisito de reconciliação
- depends-on: none
- acceptance: A CLI JSON permanece compatível e completa; `--format markdown` emite bytes determinísticos, omite apenas fechados coerentes e nunca produz `all good` para workspace não inicializado ou item inconsistente

## MOD-002 — Contrato e verificação
- module-kind: cross-cutting
- responsibility: Fixar o comportamento da skill, a compatibilidade pública e a distribuição da nova versão
- boundary: skill, validadores públicos, documentação, manifests e changelog
- depends-on: MOD-001

### DU-002 — Skill, regressões e distribuição
- development-type: qa
- phase: FASE-001
- scope-in: Instrução de reprodução literal, matriz de contrato Markdown/JSON, escaping, determinismo, read-only, bump minor e release correspondente
- scope-out: Reescrita do resumo compacto dos hooks, testes dependentes de serviços externos
- depends-on: DU-001
- acceptance: A suíte pública cobre todos os estados acordados, o bundle distribuído contém a instrução canônica e a versão `3.4.0` é idêntica em todas as superfícies fixadas

> IDs are stable within this work item. `module-kind` is one of `domain|platform|cross-cutting`; each DU has exactly one closed development type.
