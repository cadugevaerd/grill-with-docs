# DECISION-BACKLOG

## BL-0001 — FASE-003 specify bloqueado: faltam primitivas de engenharia, não só decisão de wording
- phase: FASE-003
- state: open
- owner: próxima sessão de specify FASE-003
- evidence-needed: (a) sinal de progresso observável pelo coordenador durante a execução de um worker — hoje a FASE-002 só grava transição no fim (`gauntlet.worker.prepared`), nada durante, então qualquer node com mais de 15min é stall por definição; (b) campo ou convenção no schema `grill-gauntlet-execution-dag/v1` que associe cada nó à sua macroetapa (hoje não existe, e os DAGs reais de 011/012 têm nós como T019/T020 que apontam pra verify/review, fora de `agent-execute`); (c) definição de "terminal" para as dez macroetapas fora de `agent-execute`, e o que acontece quando um leader delas falha ou bloqueia; (d) reconciliação entre o orçamento único de recovery (`run.recovery_count` ∈ {0,1}, já compartilhado com o resume manual da FASE-002 via `record_resume_decision`) e a recovery automática desta fase — hoje pode dar zero recovery disponível ou duas; (e) reconciliação entre o TTL de lease de 1h (`gauntlet_runs.py:663`) e a janela de stall de 15min, que colide com o gate `LEASE-NOT-ACTIVE` (exige recovery explícita). Evidência completa: `specs/013-scheduler-waves/spec.md` (REQUEST-CHANGES após 3 rodadas de crítica independente); ADR-0012/ADR-0013/ADR-0014 já fecham 3 decisões anteriores nesta mesma sessão — não reabrir essas três.
- next-action: nova sessão de specify FASE-003 parte do `spec.md` atual + ADR-0012/13/14; resolve os 5 itens de evidence-needed (provavelmente via nova DQ-entrevista; item (a) pode exigir reabrir/estender o escopo já shipado da FASE-002) antes de reenviar o spec para `plan`.

> Estados: `open | resolved | superseded`; `resolved` e `superseded` são terminais. Todo BL pertence a exatamente uma fase e deve ser referenciado no ROADMAP, handoff e PLAN-CONTEXT. Não fabrique um BL apenas para preencher o template.
