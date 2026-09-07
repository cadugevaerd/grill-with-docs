# PLAN-CONTEXT

## FASE-001 — Atestação ancorada na versão declarada
- phase: FASE-001
- ADRs: ADR-0001, ADR-0002
- BLs: BL-0001
- delivery-units: DU-001
- development-type: platform-devops

### HOW

**Autoridade e fluxo.** `verify_checkpoint_attestation` lê a versão já declarada em `development.workflow_version` e a entrega obrigatoriamente a `judge_checkpoint_attestation`. Esta a passa a `judge_step_output`; o mesmo valor entra nas duas validações de invocation e segue por `_correlate_with_resolution` e `_anchor_resolution_to_registry`. Quando `registry` não foi injetado, o último ponto chama `load_registry(workflow_version=workflow_version)`. Bytes injetados continuam sendo analisados diretamente, mas o argumento permanece obrigatório para impedir que algum chamador volte ao default ativo.

**Assinaturas fail-closed.** `validate_skill_invocation`, `judge_step_output` e `judge_checkpoint_attestation` recebem `workflow_version` keyword-only, sem default. Chamadores internos e testes declaram o valor. A ausência deve produzir `TypeError` na fronteira Python; não existe compatibilidade silenciosa com `WORKFLOW_VERSION`.

**Fronteira do CLI.** O checkpoint passa exatamente o valor validado do estado. A captura de erro inclui a classe `SkillResolutionError` obtida do módulo irmão `step_skills`, e traduz `exc.code` com `translate_v3_code`, preservando `exc.reason`. `CliFailure`, `AttestationError` e `StoreError` mantêm precedência e comportamento atual.

**Matriz mínima de prova.** Cobrir: resolução v3 de `agent-assign`/`agent-execute` contra registry v3; v4 contra v4; mismatch de digest entre versões; ausência de `workflow_version` nas três entradas; propagação pelo checkpoint real; skill não resolvida retornando `UNATTESTED-STEP-OUTPUT` e razão `RESOLUTION_*`, sem `UNEXPECTED-FAILURE`; regressões de contexto, predecessor e campanha existentes. Os testes pertencem aos validadores de registry, atestação, wiring v3 e scheduler/checkpoint já declarados em `scope.paths`.

**Dependência.** O trabalho parte de `fix/audit` e depende do work item `fix-audit-workflow-version-2a9e7a7ba01f42dcb24b3bb83d801b03`, porque só ele faz um bundle v3 declarar a própria versão e torna o defeito observável. A implementação não duplica nem altera essa derivação.

**Distribuição.** Alteração em `plugin/**` exige patch 5.0.1 sincronizado nos dois manifests do plugin, dois marketplaces, `tests/validate_distribution.py`, `README.md`, heading da skill e protocolo de sessão. O ciclo de ship deve criar tag e release no mesmo commit via pipeline.

**Bloqueio externo.** `scope.paths` permanece honesto. BL-0001/SGD-24 precisa corrigir a política que trata recibo concluído como ownership perpétuo; até isso ocorrer, a fase permanece `blocked` e não recebe GO. Esvaziar ou truncar o escopo não é mitigação válida.

> Mantenha um bloco por fase e referências ADR/BL exatamente equivalentes ao ROADMAP e ao handoff. Nunca registre `selected-handoff` aqui.
