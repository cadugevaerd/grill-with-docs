# DECISION-BACKLOG

## BL-0201 — Não há caminho de re-atestação após edição legítima do artefato
- state: open
- phase: FASE-001
- owner: carlosaraujo
- evidence-needed: Decidir qual é a semântica correta quando o artefato de uma etapa já atestada precisa mudar — se a etapa deve poder ser reaberta e re-emitida, se deve existir uma cadeia sucessora que declare o que substitui (o `step_output` já tem `supersedes_step_execution_id` e `supersedes_attempt_id`, hoje sempre nulos), ou se editar artefato de etapa fechada deve simplesmente ser proibido.
- next-action: Escolher entre as três semânticas acima. O terceiro caminho é o mais barato e o mais severo; o segundo já tem campos reservados no contrato, o que sugere que era o previsto.
- evidência: `checkpoint --state in-progress` sobre etapa `complete` devolve `INVALID-TRANSITION`. As cadeias de `tasks` e `analyze` deste work item divergem dos bytes atuais de `tasks.md`, e não há comando que reconcilie.
- risco: Um artefato que precise de correção depois de atestado deixa a cadeia divergente permanentemente. Quem auditar depois vê divergência sem conseguir distinguir edição legítima de adulteração — que é exatamente a distinção que a cadeia deveria sustentar.
- gatilho: Já ocorrido, neste work item.

> Estados: `open | resolved | superseded`; `resolved` e `superseded` são terminais. Todo BL pertence a exatamente uma fase e deve ser referenciado no ROADMAP, handoff e PLAN-CONTEXT.
