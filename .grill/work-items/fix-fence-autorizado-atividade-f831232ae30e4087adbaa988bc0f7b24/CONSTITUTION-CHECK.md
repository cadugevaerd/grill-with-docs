# Constitution Check

<!-- grill-constitution-check:start -->
```json
{
  "clauses": [
    {
      "evidence": [
        "DECISION-FRONTIER.md",
        "docs/adr/ADR-0001.md#Contexto",
        "PLAN-CONTEXT.md",
        "agent-orchestration/activities/interview-author-001.input.json",
        "agent-orchestration/activities/interview-author-001.result.md",
        ".grill/work-items/fix-continuidade-sem-checkpoint-d62bb2a5380d4409ace677fa741af28d/DECISION-FRONTIER.md",
        ".grill/work-items/fix-continuidade-sem-checkpoint-d62bb2a5380d4409ace677fa741af28d/ROUND-LOG.jsonl"
      ],
      "heading": "Evidência antes de afirmação",
      "id": "evid-ncia-antes-de-afirma-o",
      "justification": "As onze DQs migradas mantêm a evidência original (leituras literais do Store do X7 pelo coordenador; file:line da 6.0.30) e ganharam `migrated-from` apontando o work item de origem. Toda citação file:line herdada foi reconferida no HEAD 39380f7, incluindo o deslocamento +3 em agent_orchestration.py após o cherry-pick f1475f4. O autor conferiu os 27 sha256 do input manifest. A variante retida foi observada ao vivo no work item de origem (interview-author-001/ctx_2923e0218c89, SESSION-CLOSE-UNPROVEN e depois TAKEOVER-WORK-ACTIVE).",
      "status": "PASS"
    },
    {
      "evidence": [
        "WORK-ITEM.json",
        "state.json"
      ],
      "heading": "Work item isolado e ownership",
      "id": "work-item-isolado-e-ownership",
      "justification": "Work item fix criado por init com identidade collision-resistant fix-fence-autorizado-atividade-f831232ae30e4087adbaa988bc0f7b24 (base_commit 39380f7, branch cadugevaerd/fix-leader), contexto ctx-146fb68d0d6e com líder orca:ctx_bf15a89923e5. O work item de origem não foi tocado: a migração copia decisões seladas e o encerramento dele é fase própria (FASE-002, BL-0001), depois do ship.",
      "status": "PASS"
    },
    {
      "evidence": [
        "ROADMAP.md#FASE-001 — Fence autorizado de atividade órfã",
        "handoffs/FASE-001-SPECIFY-HANDOFF.md#WHY"
      ],
      "heading": "Feature/fix plan-only",
      "id": "feature-fix-plan-only",
      "justification": "Nenhum byte fora de .grill/ foi alterado nesta sessão: `git status --porcelain` só lista o bundle deste work item como untracked; plugin/**, tests/ e docs estão intocados. A sessão termina em PLAN_ONLY_STOP; implementação e ship ficam para o ciclo executor.",
      "status": "PASS"
    },
    {
      "evidence": [
        "state.json",
        "handoffs/FASE-001-SPECIFY-HANDOFF.md"
      ],
      "heading": "Sequência obrigatória do desenvolvimento",
      "id": "sequ-ncia-obrigat-ria-do-desenvolvimento",
      "justification": "state.json mantém os onze passos pending, com current_step=specify e workflow_version=v4. O handoff é o insumo da etapa specify e não autoriza saltos; o ciclo executor segue specify → ... → ship.",
      "status": "PASS"
    },
    {
      "evidence": [
        "state.json"
      ],
      "heading": "Verify/review antes de ship",
      "id": "verify-review-antes-de-ship",
      "justification": "Não há ship nesta sessão plan-only; verify, review e ship estão pending. A obrigação vale no ciclo executor, e o DU-001 lista a suíte e o validador de distribuição como aceite.",
      "status": "NOT-APPLICABLE"
    },
    {
      "evidence": [
        "docs/adr/ADR-0001.md#Decisão",
        "PLAN-CONTEXT.md",
        "DECISION-FRONTIER.md#DQ-0006 — Qual o destino de uma atividade DISPATCHED órfã (especialista encerrado, líder liberado) para liberar a sucessão?"
      ],
      "heading": "Fail-closed sem waiver",
      "id": "fail-closed-sem-waiver",
      "justification": "A rota decidida é fail-closed: exige prova terminal Orca, prova de readiness do solicitante e autorização humana exata, e toda recusa deixa o Store igual (obrigação dos testes negativos ancorada em DQ-0006 e nesta cláusula). A recusa TAKEOVER-WORK-ACTIVE do work item de origem não foi contornada: nenhum Store foi editado à mão e a saída é um work item novo com as mesmas decisões, mais uma fase que cerca o de origem pelo verbo quando ele existir.",
      "status": "PASS"
    },
    {
      "evidence": [
        "DECISION-FRONTIER.md",
        "DELIVERY-MAP.md",
        "DECISION-BACKLOG.md",
        "agent-orchestration/activities/interview-author-001.input.json",
        "agent-orchestration/activities/interview-author-001.result.md"
      ],
      "heading": "Rastreabilidade",
      "id": "rastreabilidade",
      "justification": "Cada DQ traz `migrated-from: <work item de origem>/DQ-NNNN` e o final-ref original. MOD-001/DU-001 ligam a FASE-001 ao ADR-0001; MOD-002/DU-002 ligam a FASE-002 ao BL-0001. A atividade de autor tem input manifest com sha256 (27 arquivos), observação Orca e resultado persistido. SGD-37, SGD-38 e SGD-39 existem no backlog SGD.",
      "status": "PASS"
    },
    {
      "evidence": [
        "agent-orchestration/activities/interview-author-001.observation.json"
      ],
      "heading": "Tier de modelo e esforço do worker Orca",
      "id": "tier-de-modelo-e-esfor-o-do-worker-orca",
      "justification": "O worker de autoria (arquitetura) foi lançado com --model fable --effort xhigh, tier forte e esforço alto; a observação normalizada registra requested_model=fable, requested_effort=xhigh, effective_model=fable, effective_effort=xhigh, resolved_model_id=fable. Nenhum --terminal foi reutilizado.",
      "status": "PASS"
    },
    {
      "evidence": [
        "git status --porcelain: nenhum caminho sob plugin/** modificado por este work item",
        "PLAN-CONTEXT.md"
      ],
      "heading": "Bump obrigatório do plugin",
      "id": "bump-obrigat-rio-do-plugin",
      "justification": "Nenhum byte de plugin/** foi alterado neste work item plan-only. O PLAN-CONTEXT registra a obrigação de bump patch 6.0.30 → 6.0.31 nos oito pontos de versão, com as linhas atuais, como pré-requisito do merge no ciclo executor.",
      "status": "NOT-APPLICABLE"
    },
    {
      "evidence": [
        "PLAN-CONTEXT.md",
        "DECISION-BACKLOG.md"
      ],
      "heading": "Release obrigatória por versão",
      "id": "release-obrigat-ria-por-vers-o",
      "justification": "Nenhuma versão é publicada por esta sessão. A release da 6.0.31 é criada pelo publish.yml no merge para main do ciclo executor, ancorada na tag; a existência dessa release é o gatilho do BL-0001.",
      "status": "NOT-APPLICABLE"
    },
    {
      "evidence": [
        ".specify/memory/constitution.md"
      ],
      "heading": "Governance",
      "id": "governance",
      "justification": "A Constituição 2.1.0 (sha256 54d5522b…7569) foi lida e preservada byte a byte; WORK-ITEM.json e state.json selam o mesmo hash. Nenhuma emenda, waiver ou ADR contra ela; hooks usados só como contexto read-only.",
      "status": "PASS"
    }
  ],
  "constitution_sha256": "54d5522b18e43efa05311dbf13ed79694b79ccfcb01509384b3572b2d5667569",
  "constitution_state": "present"
}
```
<!-- grill-constitution-check:end -->
