# PLAN-CONTEXT

## FASE-001 — Status humano determinístico
- phase: FASE-001
- ADRs: ADR-0001, ADR-0002, ADR-0003, ADR-0004
- BLs: none
- delivery-units: DU-001, DU-002
- development-type: backend, qa

### HOW
Preservar o caminho atual de automação: `grill_workspace.py status` continua emitindo o objeto JSON `grill-status/v1`, incluindo work items fechados. Acrescentar `--format json|markdown`, com `json` como default. O adaptador continua delegando a coleta read-only a `grill_status.py`; a projeção Markdown deve ser produzida por código canônico, nunca por interpretação do agente. A skill invoca explicitamente `--format markdown` e reproduz o stdout literalmente.

A classificação nasce junto do item JSON como campo aditivo. `closed=true` somente quando `state.status=complete`, `milestone_status=completed`, `active_phase=null`, todas as fases estão em `complete|superseded`, `audit_verdict=GO`, as onze etapas GWD estão `complete` e não há finding nem blocker. Recibo de reconciliação não participa. Marcadores terminais com qualquer invariante divergente formam estado bloqueado visível, não item oculto.

Cada item não fechado recebe estado operacional e motivos ordenados. A precedência é: findings e blockers; etapa GWD explicitamente bloqueada; etapa em andamento; primeira etapa pendente; invariantes de fechamento ausentes. `blocked` cobre finding, blocker, etapa bloqueada e fechamento contraditório; `in-progress` cobre trabalho ativo; `pending` cobre trabalho ainda não iniciado ou fechamento incompleto. Motivos múltiplos são deduplicados, ordenados e unidos por `; `.

O renderer filtra somente itens com `closed=true` e ordena os demais por `work_id`. Sem pendências e sem erro global, emite os bytes `all good\n`. Caso contrário emite exatamente o cabeçalho `| Item | Status | Pendência |` e uma linha por item. Pipes, barras invertidas e quebras de linha vindos dos dados precisam de escaping determinístico. Workspace sem work item produz a linha sintética `workspace | pending | GWD não inicializado`; erro global sem item produz `workspace | blocked | <código: causa>`. Exit codes permanecem os do inventário JSON.

Os testes exercitam a entrada pública, não apenas o renderer interno: compatibilidade JSON, filtragem, caso misto, estados GWD, inconsistência terminal, ausência de itens, erros, escaping, ordenação, repetição byte-idêntica e prova read-only. A alteração pública exige bump minor `3.3.2 → 3.4.0`, replicado em todas as superfícies validadas, entrada no changelog e release automática correspondente após merge na `main`.

> Mantenha um bloco por fase e referências ADR/BL exatamente equivalentes ao ROADMAP e ao handoff. Nunca registre `selected-handoff` aqui.
