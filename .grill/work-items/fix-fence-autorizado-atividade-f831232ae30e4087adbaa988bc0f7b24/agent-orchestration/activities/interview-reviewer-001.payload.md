# Payload técnico — interview-reviewer-001 (REVISOR, fable/high)

Activity payload do core: activity_id=interview-reviewer-001, context_id=ctx-146fb68d0d6e, fence=1, runtime=claude, scope=interview, write_files=[] (você NÃO escreve no repositório), author_activity_ids=[interview-author-001].

Worktree: `/home/carlosaraujo/orca/workspaces/grill-with-docs/fix-leader`, HEAD `39380f7` (plugin 6.0.30 + cherry-pick de `f1475f4`).

- NOVO = `.grill/work-items/fix-fence-autorizado-atividade-f831232ae30e4087adbaa988bc0f7b24` (work item sob revisão)
- ANTIGO = `.grill/work-items/fix-continuidade-sem-checkpoint-d62bb2a5380d4409ace677fa741af28d` (fonte das decisões seladas)

Input manifest: `NOVO/agent-orchestration/activities/interview-reviewer-001.input.json` (28 arquivos). Leia todos por inteiro e confira os sha256.

## Contexto

O ANTIGO ficou auto-bloqueado: o takeover do contexto dele recusa `TAKEOVER-WORK-ACTIVE` por `interview-author-001`, uma atividade `RESULT_RECORDED` com sessão retida. É o defeito que este fix corrige. Por decisão humana (coordenador, plano E), as decisões seladas DQ-0001..DQ-0011 foram migradas para o NOVO, sem reabrir nenhuma, e o ciclo v4 roda no NOVO.

Os bytes revisados foram escritos pelo autor `interview-author-001` do NOVO (resultado em `NOVO/agent-orchestration/activities/interview-author-001.result.md`, payload em `…/interview-author-001.payload.md`). O líder fez só edições mecânicas de registro:

- extraiu os blocos do resultado para os arquivos;
- trocou `<líder>` por `orca:ctx_bf15a89923e5` no `CONSTITUTION-CHECK.md`;
- espelhou verbatim em `ROUND-LOG.jsonl` as linhas R-0002..R-0010 do ANTIGO;
- registrou a DQ-0012 e a R-0011 (DQ proposta A do autor; decisão do coordenador, opção A).

Compare o resultado do autor com os artefatos persistidos para confirmar que não houve outra edição.

## Julgue, citando file:line

1. **Fidelidade às decisões**: DQ-0001..DQ-0012 do `NOVO/DECISION-FRONTIER.md` contra as do ANTIGO. Nenhuma pode ter sido reaberta, ampliada, estreitada ou omitida. Isso inclui resultado nunca aceito, autorização exata `work_id + context_id + activity_id`, prova terminal Orca, autoridade derivada do líder (DQ-0008), aresta `RESULT_RECORDED → FAILED` só pelo fence (DQ-0009), attempt 2 como atividade nova (DQ-0010), SGD-37/38/39 fora do escopo e a DQ-0012.
2. **Findings obrigatórios da revisão anterior** (`ANTIGO/agent-orchestration/activities/interview-reviewer-001.result.md`): F1, F2, F4 e F5 aplicados corretamente e sem abrir brecha fail-open. Confira contra o código do HEAD.
3. **Correção técnica do HOW** (`PLAN-CONTEXT.md`, `ADR-0001.md`) contra o código do HEAD: citações file:line, arestas e estados reais, interação com `_continuity_quiescence`, takeover, cleanup e `accept_activity`. Aponte premissa falsa ou lacuna que faria o ciclo executor falhar.
4. **Separação WHAT/WHY × HOW** nos dois handoffs.
5. **Coerência entre artefatos**: ROADMAP (FASE-001 e FASE-002), handoffs, PLAN-CONTEXT, DELIVERY-MAP e DECISION-BACKLOG (BL-0001) com os mesmos ADRs, BLs, DUs e `development-type`. Os testes negativos exigidos precisam estar presentes. Rode `audit` read-only se quiser: `python3 -B plugin/skills/grill-with-docs/scripts/grill_workspace.py audit . --work-id fix-fence-autorizado-atividade-f831232ae30e4087adbaa988bc0f7b24`.
6. **Constituição**: no `CONSTITUTION-CHECK.md`, cada PASS/NOT-APPLICABLE tem evidência real e justificativa honesta?

Não decida questões novas. Decisão material não coberta vira DQ proposta (pergunta atômica, opções, recomendação).

## Veredicto

`APPROVED` somente se não houver finding bloqueante. Caso contrário, `CHANGES_REQUIRED`, com cada finding numerado, severidade (bloqueante ou menor), evidência file:line e correção sugerida.

## Entrega

Grave um único arquivo Markdown no SEU scratchpad. A primeira linha é `VERDICT: APPROVED` ou `VERDICT: CHANGES_REQUIRED`; depois vêm os findings e as DQs propostas. Finalize com `worker_done --outcome succeeded --report-path <arquivo>`, usando só flags estruturadas (sem `--payload`) e corpo de 3 frases. Não escreva em `.grill/` nem em `.specify/reports/`.
