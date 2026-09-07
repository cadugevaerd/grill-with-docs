# DECISION-BACKLOG

## BL-0101 — Emissor da cadeia de atestação
- state: resolved
- phase: FASE-001
- owner: carlosaraujo
- evidence-needed: Um comando, ou um runtime, que produza `skill-resolution`, `dispatch-intent`, `skill-invocation` e `step-output` a partir de uma invocação real, com os campos que `attestation.judge_checkpoint_attestation` exige — `dispatch_key`, `skill_invocation_key`, `worker_lease_id`, `worker_fencing_token`, `worktree_head`, `dispatcher_epoch`, entre outros.
- next-action: Decidir se o emissor é responsabilidade do core, do runtime de agente, ou de um adaptador entre os dois; e se o gate deve exigir a cadeia enquanto nenhum dos três existe.
- evidência: `checkpoint_attestation_required` retorna `True` neste repositório sob 5.0.0. `grill_workspace.py:3131` recusa com `ATTESTATION-REQUIRED` quando `--attestation` não é passado. Busca por emissor no core encontra apenas validadores (`validate_dispatch_intent`, `judge_checkpoint_attestation`); os únicos lugares que montam um bundle são os testes.
- risco: O ciclo de onze etapas fica inalcançável por checkpoint em qualquer projeto na frontier ativa. Não é regressão da 5.0.0 — ela **corrigiu** o gate, que antes caía silenciosamente no caminho não autenticado para documentos v4. O que a correção revelou é que a outra ponta nunca existiu.
- gatilho: Qualquer trabalho que precise concluir uma etapa do ciclo neste repositório.
- resolução: O emissor foi entregue pelo work item `feature-attestation-emitter-2a51feec6ce84a7fb1b7ebe1b6c1aa25` (`attest` + `checkpoint --attestation` no core, a partir da 5.2.0), fechado com `MILESTONE-COMPLETE` no commit `a067a7c`. Este work item concluiu as onze etapas por checkpoint atestado, o que prova o emissor em uso.
- final-ref: `.grill/work-items/feature-attestation-emitter-2a51feec6ce84a7fb1b7ebe1b6c1aa25/state.json` (`status=complete`, `audit_verdict=GO`)

> Estados: `open | resolved | superseded`; `resolved` e `superseded` são terminais. Todo BL pertence a exatamente uma fase e deve ser referenciado no ROADMAP, handoff e PLAN-CONTEXT. Não fabrique um BL apenas para preencher o template.
