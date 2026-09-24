# Payload técnico — plan-author-001 (AUTOR, fable/xhigh)

Activity payload do core: activity_id=plan-author-001, step=plan, context_id=ctx-146fb68d0d6e, fence=1, runtime=claude.

Grant de escrita (somente estes cinco arquivos, relativos ao worktree `/home/carlosaraujo/orca/workspaces/grill-with-docs/fix-leader`):

- `specs/034-fence-autorizado-atividade/plan.md` (já existe: template copiado por `setup-plan.sh`; substitua o conteúdo inteiro)
- `specs/034-fence-autorizado-atividade/research.md`
- `specs/034-fence-autorizado-atividade/data-model.md`
- `specs/034-fence-autorizado-atividade/quickstart.md`
- `specs/034-fence-autorizado-atividade/contracts/activity-fence.md`

Não escreva em nenhum outro arquivo: nem código, nem testes, nem `.grill/`, nem `.specify/`, nem `CLAUDE.md`. Não faça commit.

Work item: W = `.grill/work-items/fix-fence-autorizado-atividade-f831232ae30e4087adbaa988bc0f7b24`. Input manifest: `W/agent-orchestration/activities/plan-author-001.input.json` (23 arquivos). Confira os sha256 antes de usar.

## Tarefa

O líder invocou `/speckit-plan` para a feature `specs/034-fence-autorizado-atividade` (etapa `plan` do ciclo v4). Você é o autor técnico do plano. Preencha os cinco artefatos acima seguindo a estrutura do template `plan.md`:

- Technical Context
- Constitution Check, contra `.specify/memory/constitution.md`
- Phase 0: `research.md`
- Phase 1: `data-model.md`, `contracts/activity-fence.md` e `quickstart.md`
- Constitution Check reavaliado depois do design

Use como forma o plano da spec 032 (`specs/032-continuity-context/plan.md`, `research.md`, `contracts/context-takeover.md`): mesma densidade, mesmo idioma (pt-BR) e o mesmo estilo de citação file:line.

Fontes, em ordem de autoridade:

1. `specs/034-fence-autorizado-atividade/spec.md` — WHAT/WHY aprovado. O plano não pode ampliar, estreitar nem contradizer a spec.
2. `W/DECISION-FRONTIER.md` — DQ-0001..DQ-0012 seladas. Não reabra nenhuma.
3. `W/PLAN-CONTEXT.md` (bloco FASE-001) e `W/docs/adr/ADR-0001.md` — o HOW já decidido. O plano o detalha e corrige; não o substitui.
4. Achados de revisão, **insumo obrigatório**:
   - `W/agent-orchestration/activities/interview-reviewer-001.result.md` (APPROVED). **Resolva no plano os Findings 1, 4 e 6**: ordem das checagens com o `operation_id` determinístico e o reuso decidido antes de estado/hash; forma completa da operação (`expected_before`, `idempotency_key`, `error`); nenhum "no-op" dentro de `mutate`. Os Findings 2, 3 e 5 tocam só a FASE-002 ou o glossário: registre-os no `research.md` como fora desta fase.
   - `W/agent-orchestration/activities/specify-reviewer-002.result.md` (APPROVED). O F2 ("veredicto indeterminado" do especialista, do líder e da sessão do sucessor) precisa estar coberto no contrato e nos testes negativos.
   - A revisão do work item de origem (`.grill/work-items/fix-continuidade-sem-checkpoint-…/agent-orchestration/activities/interview-reviewer-001.result.md`): F1, F2 e F4 já estão aplicados no PLAN-CONTEXT. Confira contra o código e mantenha.
5. Código do HEAD (manifest): `grill_workspace.py`, `grill_core/agent_orchestration.py`, `agent_runtime.py`, `attestation.py`, `store.py`, `tests/validate_agent_orchestration_contract.py`. Reconfira toda citação file:line que você usar.

### Decisão de HOW que cabe a você

**Mutação em um salto (`PRESERVED`, precedente `_transferred_activity_sessions`) ou em dois saltos (`CLOSE_PENDING → CLOSED`)?** O PLAN-CONTEXT deixou a escolha para o ciclo executor. Escolha pelo menor diff correto (Ponytail), registre alternativas e custos no `research.md` e mantenha a escolha coerente com a spec. A spec aprovada não tem cenário de aplicação interrompida: se você escolher dois saltos, a retomada vira detalhe de implementação coberto por teste, não critério da spec.

### Restrições

- Somente stdlib, Python >= 3.10, sem rede, sem tocar Constituição, WORKFLOW, `ESSENTIAL`, tabelas nem registries/catálogos.
- Bump de distribuição 6.0.30 → 6.0.31 nos oito pontos do `CLAUDE.md` (seção "Distribuição").
- Os testes precisam ser determinísticos e usar os seams existentes (`takeover_show`, `guarded_run`, `assert_refused_and_unwritten`), sem Orca real.
- O plano tem de ser particionável depois: nomeie os arquivos que cada parte do trabalho toca, para que `tasks` consiga declarar `Files:` disjuntos por fase.
- Decisão material não coberta vira "DQ proposta" no fim do `research.md` (pergunta atômica, opções, recomendação), sem decidir.

## Entrega

1. Escreva os cinco arquivos do grant.
2. Grave no SEU scratchpad um relatório curto com:
   - os sha256 dos cinco arquivos;
   - onde cada Finding obrigatório (interview-reviewer-001 NOVO: 1, 4, 6; specify-reviewer-002: F2) foi resolvido;
   - a decisão um salto × dois saltos;
   - as DQs propostas.
3. Finalize com `worker_done --outcome succeeded --files-modified <csv dos cinco paths> --report-path <relatório>`, usando só flags estruturadas (sem `--payload`) e corpo de 3 frases.
