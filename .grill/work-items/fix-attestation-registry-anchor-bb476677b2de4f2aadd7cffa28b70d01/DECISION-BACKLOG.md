# DECISION-BACKLOG

## BL-0001 — Recibos concluídos bloqueiam reutilização legítima de escopo
- phase: FASE-001
- state: open
- owner: Carlos Araujo
- decisão adiada: no caminho incremental `reconcile --work-id`, deixar de tratar escopo preservado em receipt como ownership exclusivo perpétuo; manter a detecção entre bundles de uma reconciliação batch, os conflitos ADR e os gates de dependência.
- evidência: `.grill/global/receipts/feature-workflow-v3-7dc283c84fb54e6b8f10a9c4546cd473.json` reivindica `plugin/skills/grill-with-docs/scripts/grill_core` e `plugin/skills/grill-with-docs/scripts/grill_workspace.py`; `grill_workspace.py:2045-2050` compara o alvo incremental contra todos os receipts. Receipts só são emitidos por `targeted_bundle` depois de `state.status=complete`, `milestone_status=completed`, `active_phase=null`, `audit_verdict=GO` e ROADMAP terminal (`grill_workspace.py:1989-2008`), logo não representam trabalho concorrente. A reconciliação batch preserva sua comparação entre bundles em `grill_workspace.py:1818-1826`.
- impacto: este work item precisa declarar os arquivos realmente alterados, mas sua reconciliação global permanecerá bloqueada contra um recibo concluído até o defeito ser resolvido.
- evidence-needed: testes em `tests/validate_workspace_contract.py` provando que (1) alvo incremental pode reutilizar escopo de receipt concluído, (2) reconciliação batch continua recusando dois bundles sobrepostos, (3) dependência ausente e conflito ADR continuam NO-GO, e (4) reaplicação incremental permanece determinística.
- next-action: acompanhar SGD-24 em work item separado, limitado ao ramo incremental de `reconcile_command` e aos testes de workspace; não reduzir nem esvaziar `scope.paths` deste work item.
- gatilho de retomada: antes de reconciliar globalmente este work item.
- ponto de parada: qualquer tentativa de `reconcile --apply` que ainda retorne `SCOPE-OVERLAP` contra o recibo concluído.

> Estados: `open | resolved | superseded`; `resolved` e `superseded` são terminais. Todo BL pertence a exatamente uma fase e deve ser referenciado no ROADMAP, handoff e PLAN-CONTEXT. Não fabrique um BL apenas para preencher o template.
