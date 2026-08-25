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

## BL-0202 — `worker-required` bloqueia quem deveria emitir o receipt
- state: resolved
- phase: FASE-001
- owner: carlosaraujo
- evidence-needed: A semântica correta de `worker-required`. A skill `implement-parallel` é explícita: "O receipt da etapa é seu [do leader]. Nenhum worker faz checkpoint da etapa." Logo a classe não pode significar "o receipt é do worker" — nenhum receipt de etapa é. Ela deveria significar "o trabalho é feito por workers isolados", e a emissão do leader para essa etapa deveria exigir **prova de que isso aconteceu**: waves convergidas na run corrente.
- next-action: Trocar a recusa incondicional por uma condicional — `require_leader_allowed` passa a aceitar etapa `worker-required` quando a run tem waves convergidas cobrindo os nós do DAG, e a recusar quando não tem. O nome da função também mente hoje e precisa mudar junto.
- evidência: `attest --step implement-parallel` recusa com `WORKER_REQUIRED_STEP` neste work item, cujas quatro waves foram declaradas, despachadas a workers reais e convergidas. A etapa não tem como ser concluída, e o ciclo trava na única etapa que de fato usou workers.
- risco: `implement-parallel` é inalcançável por checkpoint. O erro é meu, em ADR-0203: confundi quem faz o trabalho com quem emite o receipt, e a regra passou a bloquear exatamente quem o desenho manda emitir.
- resolução: `require_leader_allowed` deu lugar a `require_emission_allowed`, que gateia por prova de execução por workers em vez de por quem pede. A prova é lida do estado durável das runs — waves com `converged: true` — e nunca declarada por quem pede a emissão, porque uma flag do operador seria a autocertificação que a classe existe para impedir. A recusa passa a ser `WORKER_EXECUTION_UNPROVEN`. ADR-0203 emendado. `implement-parallel` deste work item fechou como `worker-required` com prova.
- final-ref: ADR-0203

> Estados: `open | resolved | superseded`; `resolved` e `superseded` são terminais. Todo BL pertence a exatamente uma fase e deve ser referenciado no ROADMAP, handoff e PLAN-CONTEXT.
