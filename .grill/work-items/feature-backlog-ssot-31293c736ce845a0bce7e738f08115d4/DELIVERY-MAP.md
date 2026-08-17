# DELIVERY-MAP

decomposition-schema: v1

## MOD-001 — Ponte com o backlog operacional
- module-kind: platform
- responsibility: Traduzir referências de decisão em itens do backlog operacional e reconciliar estado
- boundary: scripts/backlog_bridge.py e o contrato backlogctl --json
- depends-on: none

### DU-001 — Destravar a ponte
- development-type: backend
- phase: FASE-001
- scope-in: Gate de integridade do sync, remoção do filtro open-only, mapa de estados da FSM, deduplicação por (work_id, BL)
- scope-out: Geração da projeção, migração, mudança de pré-requisito
- depends-on: none
- acceptance: Sync opera sobre bundle com artefatos escritos e nunca cria item duplicado ao reexecutar

### DU-004 — Migração de bundles legados
- development-type: backend
- phase: FASE-004
- scope-in: Marcador de modo no bundle, comando de migração preview-first idempotente, estados históricos, recusa de mutação em bundle não migrado
- scope-out: Backfill manual, alteração de itens já existentes no backlog operacional
- depends-on: DU-002, DU-003
- acceptance: Bundle autoral migra uma única vez, reexecução é no-op, e comando read-only reporta a pendência sem abortar

## MOD-002 — Projeção versionada
- module-kind: cross-cutting
- responsibility: Produzir e verificar o artefato de evidência no commit derivado da autoridade
- boundary: DECISION-BACKLOG.md e o gate de auditoria
- depends-on: MOD-001

### DU-002 — Projeção determinística
- development-type: backend
- phase: FASE-002
- scope-in: Geração canônica de DECISION-BACKLOG.md, fingerprint da autoridade, comando explícito de verificação de frescor, auditoria offline da projeção
- scope-out: Consulta à autoridade dentro do gate de auditoria
- depends-on: DU-001
- acceptance: Reexecução da geração é byte-idêntica e a auditoria valida a projeção sem processo externo

## MOD-003 — Pré-requisito e distribuição
- module-kind: platform
- responsibility: Tornar o backlog operacional exigência declarada e publicar a versão incompatível
- boundary: assets/dependencies.json, init e o contrato de distribuição
- depends-on: MOD-002

### DU-003 — Pré-requisito fail-closed
- development-type: platform-devops
- phase: FASE-003
- scope-in: backlogctl como dependência exigida, bind no init, saída --skip-backlog carimbada no bundle
- scope-out: Remoção da saída explícita, alteração da matriz de CI
- depends-on: DU-001
- acceptance: init recusa sem backlog vinculado e bundle criado com a saída explícita não alcança GO

### DU-006 — Detecção de skill sombreada
- development-type: platform-devops
- phase: FASE-006
- scope-in: Detecção das skills publicadas pelo plugin quando sombreadas por skill pessoal ou de projeto, relato no preflight e no init, remoção sob flag explícita
- scope-out: Colisão entre skills de terceiros e remoção automática
- depends-on: DU-003
- acceptance: Nome sombreado é reportado sem bloquear por padrão, e a remoção só ocorre sob autorização explícita

### DU-005 — Verificação e publicação
- development-type: qa
- phase: FASE-005
- scope-in: Regressões dos quatro defeitos, backlogctl falso pelo seam resolve_cli, bump de versão nos oito lugares
- scope-out: Registro de required status check, que é ato humano
- depends-on: DU-001, DU-002, DU-003, DU-004, DU-006
- acceptance: Suíte verde na matriz sem backlogctl real e versão idêntica nos oito surfaces

> IDs are stable within this work item. `module-kind` is one of `domain|platform|cross-cutting`; each DU has exactly one closed development type.
