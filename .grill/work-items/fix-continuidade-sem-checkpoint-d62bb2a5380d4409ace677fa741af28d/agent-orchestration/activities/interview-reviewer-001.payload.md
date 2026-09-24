# Payload técnico — interview-reviewer-001 (REVISOR, fable/high)

Activity payload do core: activity_id=interview-reviewer-001, context_id=ctx-0c0155ef5a94, fence=1, runtime=claude, input_sha256=569ec29a96a643217aa47ed7fbdf4fc90afd91740fc37526c239638a569e970e, write_files=[] (você NÃO escreve no repositório), author_activity_ids=[interview-author-002].

Seja W = `.grill/work-items/fix-continuidade-sem-checkpoint-d62bb2a5380d4409ace677fa741af28d` (relativo ao worktree `/home/carlosaraujo/orca/workspaces/grill-with-docs/fix-leader`, plugin 6.0.30).

## Tarefa

Revisão de julgamento independente dos artefatos da entrevista GWD (plan-only) deste work item. Leia por inteiro os arquivos do input manifest `W/agent-orchestration/activities/interview-reviewer-001.input.json` e confira os sha256. Os bytes revisados foram escritos pelo autor `interview-author-002` (resultado em `W/agent-orchestration/activities/interview-author-002.result.md`). Depois o líder fez só edições mecânicas de registro: aplicou as decisões humanas DQ-0008, DQ-0009 e DQ-0010 onde o autor deixou "DQ proposta", trocou a citação da "regra 11" e preencheu o `CONSTITUTION-CHECK.md`. Compare o resultado do autor com os artefatos persistidos para ver exatamente essas edições.

Julgue, citando file:line:

1. **Fidelidade às decisões humanas**: DQ-0001, 0002, 0005, 0006, 0007, 0008, 0009 e 0010 em `W/DECISION-FRONTIER.md` e `W/ROUND-LOG.jsonl`. Nenhum artefato pode contradizer, ampliar ou omitir uma decisão. Em especial: resultado nunca aceito; autorização exata `work_id + context_id + activity_id`; prova terminal Orca; autoridade derivada do líder (DQ-0008); aresta `RESULT_RECORDED → FAILED` só pelo fence (DQ-0009); attempt 2 como atividade nova (DQ-0010); SGD-37 e SGD-38 fora do escopo.
2. **Correção técnica do HOW** (`PLAN-CONTEXT.md`, `ADR-0001.md`) contra o código 6.0.30: citações de linha corretas, arestas e estados reais, interação com `_continuity_quiescence`, takeover, cleanup e `accept_activity`. Aponte premissas falsas e lacunas que fariam o ciclo executor falhar ou abrir brecha fail-open.
3. **Separação WHAT/WHY × HOW**: o handoff não pode conter stack, classes, API interna nem implementação.
4. **Coerência entre artefatos**: ROADMAP, handoff, PLAN-CONTEXT e DELIVERY-MAP com os mesmos ADRs/BLs/DU/`development-type`, e os testes negativos exigidos presentes.
5. **Constituição**: `CONSTITUTION-CHECK.md` — cada PASS/NOT-APPLICABLE tem evidência real e justificativa honesta?

Não decida questões novas. Se achar decisão material não coberta, liste-a como DQ proposta (pergunta atômica, opções, recomendação).

## Veredicto

`APPROVED` somente se não houver finding bloqueante. Caso contrário, `CHANGES_REQUIRED`, com cada finding numerado, com severidade (bloqueante / menor), evidência file:line e correção sugerida.

## Entrega

Grave um único arquivo Markdown no SEU scratchpad, com a primeira linha `VERDICT: APPROVED` ou `VERDICT: CHANGES_REQUIRED`, seguida dos findings e das DQs propostas. Finalize com `worker_done --outcome succeeded --report-path <arquivo>`, só com flags estruturadas (sem `--payload`) e corpo de 3 frases. Não escreva em `.grill/` nem em `.specify/reports/`.
