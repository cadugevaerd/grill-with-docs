# Payload técnico — interview-author-002 (AUTOR, fable/xhigh)

Activity payload do core (`grill-activity-payload`): activity_id=interview-author-002, context_id=ctx-0c0155ef5a94, fence=1, runtime=claude, input_sha256=792a1625d9a6d34e0fa603754a23b21ee1eeda625ec71744a41da5956bf21c3c, write_files=[] (você NÃO escreve no repositório).

Seja W = `.grill/work-items/fix-continuidade-sem-checkpoint-d62bb2a5380d4409ace677fa741af28d` (relativo ao worktree `/home/carlosaraujo/orca/workspaces/grill-with-docs/fix-leader`, plugin 6.0.30).

## Tarefa

Você é o autor técnico da entrevista GWD (plan-only) deste work item. As decisões humanas já foram tomadas e estão em `W/DECISION-FRONTIER.md` e `W/ROUND-LOG.jsonl`. Leia os arquivos do input manifest `W/agent-orchestration/activities/interview-author-002.input.json` (confira os sha256) e redija, SEM contradizer as decisões humanas, as propostas integrais destes artefatos do bundle:

1. `CONTEXT.md` — glossário, somente linguagem ubíqua: atividade órfã, fence autorizado, prova terminal Orca, autorização humana exata, takeover, quiescência, attempt 2.
2. `docs/adr/ADR-0001.md` — decisão difícil de reverter: rota de fence autorizado para atividade DISPATCHED órfã (DQ-0006 opção A), alternativas B/C rejeitadas e trade-offs. Consequência: o resultado não é aceito, e o sucessor reexecuta o autor como attempt 2. Relacione com o princípio "Resultados de atividades nunca herdam essas exceções" (`plugin/skills/grill-with-docs/references/session-protocol.md:87`) e com o precedente `gauntlet-run-abandon` (`human-authorization/v1`, `grill_core/attestation.py:191-193, 773-781`). Siga o formato de ADR já usado em outros bundles (ex.: `.grill/work-items/feature-add-ponytail-494ea379ecc84a38b029d55ec39ffe8f/docs/adr/ADR-0001.md`).
3. `ROADMAP.md` — FASE-001 com nome estável, objetivo observável, scope-in e scope-out. Fora do escopo: SGD-37 (transcript > 16 MiB), SGD-38 (KeyError de campaign com head nulo), prevenção por checkpoint automático. Campos: `ADRs: ADR-0001`, `BLs: none`, `state: ready-for-specify`.
4. `handoffs/FASE-001-SPECIFY-HANDOFF.md` — SOMENTE WHAT/WHY, sem stack, classes, API interna ou implementação. Inclua atores (líder sucessor, humano autorizador, especialista órfão), cenários com os 4 negativos exigidos (sem autorização; autorização de outro contexto/atividade/run; líder vivo; especialista vivo), critérios de aceite e o caso X7 como evidência.
5. `PLAN-CONTEXT.md` — HOW cumulativo:
   - verbo novo preview-first, com `--apply --expected-sha256`;
   - provas exigidas: observação Orca terminal do dispatch do especialista e do líder, e `human-authorization/v1` com escopo work_id + context_id + activity_id;
   - estado terminal da atividade e fechamento do recurso de sessão com receipt;
   - interação com `_continuity_quiescence` (`grill_workspace.py:3654-3672`) e com `gauntlet-context-takeover` (`grill_workspace.py:4126-4345`);
   - attempt 2 no contexto sucessor;
   - testes negativos (regra 11);
   - stdlib only, sem tocar Constituição, WORKFLOW, ESSENTIAL ou registries;
   - bump de distribuição nos 8 pontos (ver `CLAUDE.md`, seção "Distribuição").
   Aponte riscos e lock-in.
6. `DELIVERY-MAP.md` — MOD/DU com `development-type` do vocabulário do auditor (`DEVELOPMENT_TYPES` em `plugin/skills/grill-with-docs/scripts/audit_decisions.py`). Um fix de CLI do core é `platform-devops`, e o valor tem de casar com o handoff e o PLAN-CONTEXT.

Restrições: não escreva em `.grill/` nem em `.specify/reports/`, porque o líder persiste. Não invente evidência; cite file:line. Ponytail: menor diff correto, YAGNI. Não resolva questão nova por conta própria. Se surgir decisão material não coberta, liste-a como DQ proposta (pergunta atômica, opções, recomendação), sem decidir.

Não leia nem reutilize relatórios de outras sessões de autor; produza sua própria autoria a partir dos inputs.

## Entrega

Grave um único arquivo Markdown no SEU scratchpad com as seções `## CONTEXT.md`, `## docs/adr/ADR-0001.md`, `## ROADMAP.md`, `## handoffs/FASE-001-SPECIFY-HANDOFF.md`, `## PLAN-CONTEXT.md`, `## DELIVERY-MAP.md` e `## DQs propostas`, cada artefato num bloco de código completo. Finalize com `worker_done --outcome succeeded --report-path <arquivo>`, usando só flags estruturadas (sem `--payload`) e corpo de 3 frases.
