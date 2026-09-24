# Payload técnico — interview-author-001 (AUTOR, fable/xhigh)

Activity payload do core: activity_id=interview-author-001, context_id=ctx-146fb68d0d6e, fence=1, runtime=claude, scope=interview, write_files=[] (você NÃO escreve no repositório).

Worktree: `/home/carlosaraujo/orca/workspaces/grill-with-docs/fix-leader`, HEAD `39380f7` (plugin 6.0.30 + cherry-pick de `f1475f4`, que acrescenta 3 linhas em `grill_core/agent_orchestration.py` perto da linha 1389).

- ANTIGO = `.grill/work-items/fix-continuidade-sem-checkpoint-d62bb2a5380d4409ace677fa741af28d`
- NOVO = `.grill/work-items/fix-fence-autorizado-atividade-f831232ae30e4087adbaa988bc0f7b24`

Input manifest: `NOVO/agent-orchestration/activities/interview-author-001.input.json` (27 arquivos). Confira os sha256 antes de usar.

## Por que existe um work item novo

O ANTIGO ficou auto-bloqueado pelo próprio defeito que corrige. O líder sucessor não consegue assumir o contexto `ctx-0c0155ef5a94`: `gauntlet-context-takeover` recusa `TAKEOVER-WORK-ACTIVE` com `activity:interview-author-001`. Essa atividade está `RESULT_RECORDED`, com sessão retida pelo Orca (`user_takeover`, dispatch `ctx_2923e0218c89`), e não há verbo que a leve a estado terminal. O líder original `orca:ctx_ad48e72ddf4c` está com o terminal desconectado. O coordenador (decisão humana, plano E) mandou migrar as decisões seladas para o NOVO, sem reabrir nenhuma, e rodar o ciclo v4 nele. O ANTIGO será marcado `superseded` depois do ship, quando o fence existir.

## Tarefa

Você é o autor técnico da migração. As decisões humanas DQ-0001..DQ-0011 do `ANTIGO/DECISION-FRONTIER.md` e do `ANTIGO/ROUND-LOG.jsonl` estão seladas. Não reabra, não amplie e não estreite nenhuma. Produza as propostas integrais dos artefatos do NOVO, partindo dos artefatos do ANTIGO como fonte e dos templates vazios do NOVO como forma:

1. `CONTEXT.md` — glossário do ANTIGO. Acrescente a desambiguação de "fence" (finding F6), como nota em "termos a evitar".
2. `docs/adr/ADR-0001.md` — mesma decisão do ANTIGO. Acrescente o ANTIGO como segundo caso observado (variante `RESULT_RECORDED` retida, que bloqueou o próprio takeover). Registre F8 como relação de backlog (SGD-39), sem tratá-lo.
3. `ROADMAP.md` — `execution-order: FASE-001, FASE-002`.
   - FASE-001: campos do ANTIGO, `ADRs: ADR-0001`, `BLs: none`, `state: ready-for-specify`. **F5 obrigatório**: o objetivo cobre o work item "cujo líder terminou **ou** que ainda tem líder vivo", como a DQ-0008 decidiu.
   - FASE-002: fase curta e operacional, `state: planned`, `depends-on: FASE-001`, `BLs: BL-0001`, com handoff próprio `handoffs/FASE-002-SPECIFY-HANDOFF.md`. Ela existe porque o auditor exige que todo BL esteja ligado a uma fase (`BL orphan`, audit_decisions.py:564-566) e recusa fase pronta ligada a BL aberto (`ready ligada a BL open`, 740-741). Confira essas linhas.
4. `handoffs/FASE-001-SPECIFY-HANDOFF.md` — SOMENTE WHAT/WHY. **F5 obrigatório**: o cenário 2 diz "pedido pelo líder corrente exato quando o líder está vivo, ou por sucessor com prova terminal do líder (DQ-0008)". Inclua o ANTIGO como evidência ao lado do X7. Nit do revisor: troque `tests/run_validators.py` por "suíte de validadores do repositório verde nos três SOs, sem rede".
5. `PLAN-CONTEXT.md` — HOW do ANTIGO com as três correções **obrigatórias** da DQ-0011:
   - **F1**: a observação do especialista usa `'orca:' + resource.identity.owner_dispatch`, na forma de `_released_activity_sessions`.
   - **F2**: o segundo salto reobserva o Store (`read_snapshot` novo) ou guarda só por estado. A alternativa é `PRESERVED` em um salto a partir de `REGISTERED`/`CLOSE_PENDING`; nesse caso cite o precedente F3 (`_transferred_activity_sessions`).
   - **F4**: com líder terminal, o sucessor é provado por `_session_readiness` sobre `--session-ref`, e `readiness.ref/sha256` entram em `evidence.requester` e em `intended_after`. O hash da prévia inclui o `to_session_ref`.
   - F3, F6 e F7 são insumo opcional. F7: ancore a obrigação dos testes negativos na DQ-0006 e na cláusula constitucional "Fail-closed sem waiver", e rebaixe a "regra 11" a nota de origem.
   - Reconfira contra o HEAD atual **todas** as citações file:line herdadas. Pelo menos `agent_orchestration.py` deslocou depois do cherry-pick. Não copie número de linha sem conferir.
   - Bump de distribuição nos 8 pontos, 6.0.30 → 6.0.31 (seção "Distribuição" do `CLAUDE.md`).
6. `DELIVERY-MAP.md` — o do ANTIGO, com `development-type` do vocabulário `DEVELOPMENT_TYPES` do auditor, coerente com o handoff e o PLAN-CONTEXT.
7. `DECISION-FRONTIER.md` — as onze DQs com os mesmos IDs, estados e resoluções. Cada uma ganha a linha `- migrated-from: <ANTIGO work_id>/DQ-NNNN` e mantém a evidência original. Se uma resolução citava "o work item corrente", deixe claro que o caso é o ANTIGO.
8. `DECISION-BACKLOG.md` — `BL-0001`, `state: open`, `phase: FASE-002`: marcar o ANTIGO como `superseded` depois do ship deste fix, cercando `interview-author-001` pelo verbo novo. Preencha owner (líder GWD), evidence-needed, gatilho (ship publicado da 6.0.31) e next-action. Use o formato do template. O handoff da FASE-002 descreve só WHAT/WHY dessa operação.
9. `CONSTITUTION-CHECK.md` — proposta de preenchimento para o NOVO, com a mesma Constituição (`54d5522b…7569`), no formato do ANTIGO. O líder confere cada evidência antes de gravar.

## Restrições

- Não escreva em `.grill/` nem em `.specify/reports/`; quem persiste é o líder.
- Não invente evidência. Cite file:line conferido no HEAD atual.
- Ponytail: menor diff correto e YAGNI.
- Decisão material não coberta vira "DQ proposta" (pergunta atômica, opções, recomendação), sem decidir.
- Não leia relatórios de outras sessões de autor além dos que estão no manifest.

## Entrega

Grave um único Markdown no SEU scratchpad com as seções `## CONTEXT.md`, `## docs/adr/ADR-0001.md`, `## ROADMAP.md`, `## handoffs/FASE-001-SPECIFY-HANDOFF.md`, `## handoffs/FASE-002-SPECIFY-HANDOFF.md`, `## PLAN-CONTEXT.md`, `## DELIVERY-MAP.md`, `## DECISION-FRONTIER.md`, `## DECISION-BACKLOG.md`, `## CONSTITUTION-CHECK.md`, `## Aplicação de F1/F2/F4/F5` (onde e como cada finding foi aplicado) e `## DQs propostas`. Cada artefato vai inteiro num bloco de código.

Finalize com `worker_done --outcome succeeded --report-path <arquivo>`, usando só flags estruturadas (sem `--payload`) e corpo de 3 frases.
