# DECISION-BACKLOG

## BL-0001 — Backstop para juiz que ignora GOAL-HOLD
- state: resolved
- phase: FASE-001
- owner: carlosaraujo
- evidence-needed: none
- next-action: none
- evidência: `hermes_cli/goals.py` — falha do juiz é *fail-OPEN* (continua) e o único backstop é `DEFAULT_MAX_TURNS = 20`; o comentário do módulo registra que modelos com raciocínio já truncaram o JSON do veredito sob cap apertado.
- risco: o laço desconsidera `GOAL-HOLD`, reinjeta a continuação e pressiona o agente a atravessar um gate que deveria ter parado.
- resolução: o próprio `goal.md` instrui o operador a declarar orçamento de turnos curto na trilha de entrevista, de modo que o backstop seja explícito e dimensionado, em vez de herdado do default do runtime. O documento também instrui a repetir a linha `GOAL-HOLD:` como última linha da resposta, isolada, para reduzir a chance de o juiz não a pesar.
- final-ref: ADR-0004

> Estados: `open | resolved | superseded`; `resolved` e `superseded` são terminais. Todo BL pertence a exatamente uma fase e deve ser referenciado no ROADMAP, handoff e PLAN-CONTEXT. Não fabrique um BL apenas para preencher o template.
