# Constitution Check

<!-- grill-constitution-check:start -->
```json
{
  "clauses": [
    {
      "evidence": [
        "../../triage-evidence/presentation-suspension-debug.md",
        "docs/adr/ADR-0001.md#Contexto",
        "ROUND-LOG.jsonl"
      ],
      "heading": "Evidência antes de afirmação",
      "id": "evid-ncia-antes-de-afirma-o",
      "justification": "Causa raiz reproduzida offline pelo worker de diagnostico com fixture oficial e transcript sintetico no formato real do Claude: project_leader_presentation (agent_runtime.py:1121-1128) nunca passa suspension; triagem tri-presentation-suspension selada com causa raiz comprovada.",
      "status": "PASS"
    },
    {
      "evidence": [
        "WORK-ITEM.json",
        "state.json#work_id"
      ],
      "heading": "Work item isolado e ownership",
      "id": "work-item-isolado-e-ownership",
      "justification": "Bundle proprio fix-presentation-suspension-d97e4c3d7b434c119477ec59d56ecbd5 na branch cadugevaerd/feat-new-subagents; nada escrito no diretorio de outro work item.",
      "status": "PASS"
    },
    {
      "evidence": [
        "git status",
        "handoffs/FASE-001-SPECIFY-HANDOFF.md"
      ],
      "heading": "Feature/fix plan-only",
      "id": "feature-fix-plan-only",
      "justification": "Trabalho do tipo fix: nenhum arquivo de produto ou de teste alterado nesta etapa; entrega o handoff e termina em PLAN_ONLY_STOP.",
      "status": "PASS"
    },
    {
      "evidence": [
        "state.json#development.sequence",
        "state.json#development.workflow_version=v4"
      ],
      "heading": "Sequência obrigatória do desenvolvimento",
      "id": "sequ-ncia-obrigat-ria-do-desenvolvimento",
      "justification": "Sequencia v4 completa declarada, current_step=specify e demais etapas pending; o handoff alimenta specify.",
      "status": "PASS"
    },
    {
      "evidence": [
        "state.json#development.steps",
        "handoffs/FASE-001-SPECIFY-HANDOFF.md#WHAT"
      ],
      "heading": "Verify/review antes de ship",
      "id": "verify-review-antes-de-ship",
      "justification": "verify e review pending e precedem ship; o handoff carrega suite verde, diff limpo e os sete cenarios como aceite.",
      "status": "PASS"
    },
    {
      "evidence": [
        "docs/adr/ADR-0001.md#Decisão",
        "docs/adr/ADR-0003.md#Decisão"
      ],
      "heading": "Fail-closed sem waiver",
      "id": "fail-closed-sem-waiver",
      "justification": "Suspensao so por mensagem role=user da propria sessao; autorrelato do agente e resumo de compactacao nunca suspendem nem reativam; STYLE-SCOPE-CONFLICT permanece durante upgrade suspenso. Nenhum waiver pedido.",
      "status": "PASS"
    },
    {
      "evidence": [
        "ROUND-LOG.jsonl",
        "DECISION-FRONTIER.md",
        "ROADMAP.md",
        "PLAN-CONTEXT.md",
        "DELIVERY-MAP.md",
        "REQUEST.md"
      ],
      "heading": "Rastreabilidade",
      "id": "rastreabilidade",
      "justification": "Tres rounds ligam DQ-0001..0003 a ADR-0001..0003; ROADMAP, PLAN-CONTEXT, DELIVERY-MAP e handoff referenciam os mesmos ADRs e DU-001; triagem tri-presentation-suspension aponta o laudo.",
      "status": "PASS"
    },
    {
      "evidence": [
        "../../triage-evidence/presentation-suspension-debug.md",
        "dispatch ctx_9d06feeaee68"
      ],
      "heading": "Tier de modelo e esforço do worker Orca",
      "id": "tier-de-modelo-e-esfor-o-do-worker-orca",
      "justification": "Diagnostico despachado a worker Orca com --model claude-fable-5-1 --effort high; launch.effective conferido igual a launch.requested antes do trabalho.",
      "status": "PASS"
    },
    {
      "evidence": [
        "git status: nenhum caminho sob plugin/** modificado por este work item",
        "handoffs/FASE-001-SPECIFY-HANDOFF.md#WHY"
      ],
      "heading": "Bump obrigatório do plugin",
      "id": "bump-obrigat-rio-do-plugin",
      "justification": "Nenhum byte de plugin/** alterado neste trabalho plan-only. O handoff registra bump patch acima da versao publicada no ship como pre-requisito.",
      "status": "NOT-APPLICABLE"
    },
    {
      "evidence": [
        "state.json#status=in-progress"
      ],
      "heading": "Release obrigatória por versão",
      "id": "release-obrigat-ria-por-vers-o",
      "justification": "Trabalho plan-only nao publica versao, tag nem release; clausula exercida pelo pipeline no merge do ciclo executor.",
      "status": "NOT-APPLICABLE"
    },
    {
      "evidence": [
        "state.json#constitution.sha256=54d5522b18e43efa05311dbf13ed79694b79ccfcb01509384b3572b2d5667569",
        "CONSTITUTION-CHECK.md#constitution_sha256"
      ],
      "heading": "Governance",
      "id": "governance",
      "justification": "Constituicao lida somente leitura; hash gravado coincide com o arquivo em disco. Nenhuma emenda proposta e nenhum ADR pede waiver.",
      "status": "PASS"
    }
  ],
  "constitution_sha256": "54d5522b18e43efa05311dbf13ed79694b79ccfcb01509384b3572b2d5667569",
  "constitution_state": "present"
}
```
<!-- grill-constitution-check:end -->
